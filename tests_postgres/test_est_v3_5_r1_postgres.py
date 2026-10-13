"""Regression tests reproducing independent B35 findings against native PostgreSQL.

No service mocks: native stock and delivery handlers, native JWT verification,
native RBAC, physical item claim, aggregate update, movement and ficha writes.
The in-memory HTTP response sink replaces transport only.
"""
import io
import tempfile
import json
import os
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4

import pytest

from core.bootstrap import init_db
from core.database import get_connection
from core.security import create_jwt_token
import modules.deliveries.routes as delivery_routes
from modules.stock.routes import handle_get_stock_epis
from modules.stock.reservations import create_reservation, unit_balance
from modules.stock.service import (
    create_stock_item, fetch_available_stock_items, next_company_qr_sequence,
    record_received_item_physical, set_stock_item_status, upsert_unit_stock,
)
from epi_backend.db import row_to_dict

ROOT = Path(os.environ.get('EST35_EVIDENCE_DIR') or tempfile.mkdtemp(prefix='est35-r1-regression-'))
ROOT.mkdir(parents=True, exist_ok=True)
REPO = os.environ.get('REVIEW_REPO', 'corporate')
pytestmark = pytest.mark.skipif(not os.environ.get('DATABASE_URL', '').startswith('postgres'), reason='Requires isolated PostgreSQL')
TODAY = date.today().isoformat()
PAST = (date.today()-timedelta(days=10)).isoformat()
FUTURE = (date.today()+timedelta(days=365)).isoformat()
OBSERVATIONS = []
PAYLOADS = []


def persist():
    (ROOT/f'{REPO}-business-observations.json').write_text(json.dumps(OBSERVATIONS, indent=2, default=str))
    (ROOT/f'{REPO}-stock-payloads.json').write_text(json.dumps(PAYLOADS, indent=2, default=str))


class ResponseSink:
    def __init__(self, path, actor, command='GET'):
        self.path, self.command, self.client_address = path, command, ('127.0.0.1', 0)
        self.headers = {'Authorization': 'Bearer '+create_jwt_token(actor)}
        self.wfile = io.BytesIO()
        self.status = None
    def send_response(self, status):
        self.status = status
    def send_header(self, *args):
        pass
    def end_headers(self):
        pass
    @property
    def body(self):
        return json.loads(self.wfile.getvalue()) if self.wfile.getvalue() else None


@pytest.fixture(scope='module')
def connection():
    init_db()
    conn = get_connection()
    yield conn
    conn.close()
    persist()


@pytest.fixture(autouse=True)
def reset_transaction(connection, monkeypatch):
    monkeypatch.setenv('JWT_ENFORCEMENT_MODE', 'enforce')
    connection.rollback()
    yield
    connection.rollback()


def seed(c, kinds, catalog=FUTURE, aggregate=None, ca_expiry=PAST):
    sfx = uuid4().hex
    now = datetime.now(timezone.utc).isoformat()
    company = c.execute('INSERT INTO companies(name,cnpj,logo_type) VALUES (?,?,?)', ('QA '+sfx, sfx, 'text')).lastrowid
    c.execute("UPDATE companies SET timezone='UTC' WHERE id=?", (company,))
    foreign_company = c.execute('INSERT INTO companies(name,cnpj,logo_type) VALUES (?,?,?)', ('QB '+sfx, sfx+'b', 'text')).lastrowid
    unit = c.execute('INSERT INTO units(company_id,name,unit_type,city) VALUES (?,?,?,?)', (company,'Unit A','base','Local')).lastrowid
    other_unit = c.execute('INSERT INTO units(company_id,name,unit_type,city) VALUES (?,?,?,?)', (company,'Unit B','base','Local')).lastrowid
    foreign_unit = c.execute('INSERT INTO units(company_id,name,unit_type,city) VALUES (?,?,?,?)', (foreign_company,'Foreign','base','Local')).lastrowid
    epi = c.execute('INSERT INTO epis(company_id,unit_id,name,purchase_code,ca,sector,unit_measure,ca_expiry,epi_validity_date,manufacture_date,validity_days) VALUES (?,?,?,?,?,?,?,?,?,?,?)', (company,unit,'QA EPI',sfx,'CA-'+sfx,'QA','un',ca_expiry,catalog,'',0)).lastrowid
    employee = c.execute('INSERT INTO employees(company_id,unit_id,employee_id_code,name,sector,role_name,admission_date,schedule_type) VALUES (?,?,?,?,?,?,?,?)', (company,unit,sfx,'Local Employee','QA','QA',TODAY,'administrativo')).lastrowid
    actor_id = c.execute('INSERT INTO users(username,password,full_name,role,company_id) VALUES (?,?,?,?,?)', (sfx,'local-fixture-unused','QA Admin','general_admin',company)).lastrowid
    actor = dict(id=actor_id,role='general_admin',company_id=company,full_name='QA Admin')
    items = {}
    for index, kind in enumerate(kinds):
        seqv = next_company_qr_sequence(c, company)
        qr = 'LOCAL-QA-'+uuid4().hex
        iid = create_stock_item(c,company,unit,epi,'N/A','M','N/A',seqv,qr,None,'','','unit','','',actor_id,now)
        if kind in ('valid','expired','blocked','today'):
            record_received_item_physical(c,iid,TODAY if kind == 'today' else FUTURE,actor_id,now)
        if kind == 'expired':
            # Simulates ageing after a valid receipt, preserving evidence CHECK.
            c.execute('UPDATE epi_stock_items SET physical_expiry_date=? WHERE id=?',(PAST,iid))
        if kind == 'blocked':
            row=c.execute('SELECT * FROM epi_stock_items WHERE id=?',(iid,)).fetchone()
            set_stock_item_status(c,row_to_dict(row),'blocked_rejected','QA quarantine',actor_id,'QA Admin',now)
        items[kind if kind not in items else f'{kind}_{index}'] = dict(id=iid,qr=qr)
    upsert_unit_stock(c,company,unit,epi,len(kinds) if aggregate is None else aggregate)
    c.commit()
    return dict(c=c,company=company,foreign_company=foreign_company,unit=unit,other_unit=other_unit,foreign_unit=foreign_unit,epi=epi,employee=employee,actor=actor,items=items,catalog=catalog)


def delivery(s, kind, overrides=None):
    item=s['items'][kind]
    payload=dict(actor_user_id=s['actor']['id'],company_id=s['company'],employee_id=s['employee'],unit_id=s['unit'],epi_id=s['epi'],quantity=1,stock_item_id=item['id'],stock_qr_code=item['qr'],sector='QA',role_name='QA',delivery_date=TODAY,next_replacement_date=FUTURE,idempotency_key='LOCAL-QA-'+uuid4().hex)
    payload.update(overrides or {})
    handler=ResponseSink('/api/deliveries',s['actor'],'POST')
    error=None
    try:
        delivery_routes.handle_post_deliveries(handler,urlparse(handler.path),payload,None)
    except (ValueError, PermissionError) as exc:
        error=dict(type=type(exc).__name__,message=str(exc))
    row=row_to_dict(s['c'].execute('SELECT id,status,physical_expiry_date,delivery_id FROM epi_stock_items WHERE id=?',(item['id'],)).fetchone())
    stock=row_to_dict(s['c'].execute('SELECT quantity FROM unit_epi_stock WHERE company_id=? AND unit_id=? AND epi_id=?',(s['company'],s['unit'],s['epi'])).fetchone())
    result=dict(case='delivery_'+kind,catalog=s['catalog'],payload=payload,response_status=handler.status,response=handler.body,error=error,item_after=row,aggregate_after=stock)
    from core.repository import get_epi_by_id
    from modules.stock.service import effective_delivery_expiry
    result['native_epi_projection']=get_epi_by_id(s['c'],s['epi'])
    result['helper_with_explicit_catalog']=effective_delivery_expiry(s['c'],item['id'],s['catalog'])
    if handler.body and handler.body.get('id'):
        did=handler.body['id']
        result['delivery_row']=row_to_dict(s['c'].execute('SELECT id,company_id,unit_id,epi_id,stock_movement_id FROM deliveries WHERE id=?',(did,)).fetchone())
        result['movement_row']=row_to_dict(s['c'].execute('SELECT id,movement_type,quantity,previous_stock,new_stock,company_id,unit_id FROM stock_movements WHERE id=?',(result['delivery_row']['stock_movement_id'],)).fetchone())
        result['ficha_links']=s['c'].execute('SELECT COUNT(*) AS n FROM epi_ficha_items WHERE delivery_id=?',(did,)).fetchone()['n']
    OBSERVATIONS.append(result);persist()
    return result


@pytest.mark.parametrize('kind', ['valid','today'])
def test_known_valid_piece_delivers_with_expired_catalog_and_ca(connection, kind):
    s=seed(connection,[kind],catalog=PAST)
    r=delivery(s,kind)
    assert r['response_status']==201, r
    assert r['item_after']['status']=='delivered' and r['aggregate_after']['quantity']==0
    assert r['movement_row']['movement_type']=='out' and r['ficha_links']==1


@pytest.mark.parametrize('catalog',[FUTURE,PAST,''])
def test_unknown_physical_piece_never_delivers_from_catalog(connection,catalog):
    s=seed(connection,['unknown'],catalog=catalog)
    r=delivery(s,'unknown')
    assert r['error'] is not None and r['item_after']['status']=='in_stock', 'Unknown physical validity was delivered: '+json.dumps(r,default=str)


@pytest.mark.parametrize('kind,rule',[('expired','vencida'),('blocked','bloqueada')])
def test_expired_and_blocked_pieces_rejected_without_writes(connection,kind,rule):
    s=seed(connection,[kind])
    r=delivery(s,kind)
    assert r['response_status'] is None and r['error'] is not None, r
    assert rule in r['error']['message'].lower(),r
    assert r['item_after']['delivery_id'] is None and r['aggregate_after']['quantity']==1,r


def test_mixed_available_candidates_exclude_ineligible(connection):
    s=seed(connection,['valid','expired','unknown','blocked'])
    rows=[row_to_dict(r) for r in fetch_available_stock_items(connection,s['company'],s['unit'],s['epi'])]
    OBSERVATIONS.append(dict(case='mixed_available_candidates',seed=s['items'],rows=rows));persist()
    assert [r['id'] for r in rows]==[s['items']['valid']['id']], 'Available candidates contain expired/unknown pieces: '+json.dumps(rows,default=str)


@pytest.mark.parametrize('kinds,aggregate,quantity', [(['unknown'],1,1),(['expired'],1,1),(['valid','expired','unknown','blocked'],4,2),([],5,1)])
def test_reservation_requires_enough_eligible_physical_pieces(connection,kinds,aggregate,quantity):
    s=seed(connection,kinds,aggregate=aggregate)
    before=unit_balance(connection,s['company'],s['unit'],s['epi'])
    error=None; result=None
    try:
        result=create_reservation(connection,company_id=s['company'],unit_id=s['unit'],epi_id=s['epi'],quantity=quantity,actor_user_id=s['actor']['id'])
        connection.commit()
    except ValueError as exc:
        error=str(exc)
        connection.rollback()
    r=dict(case='reservation_eligible_required',kinds=kinds,seed=s['items'],aggregate=aggregate,quantity=quantity,balance_before=before,reservation=result,error=error)
    OBSERVATIONS.append(r);persist()
    assert error is not None and result is None, 'Reservation authorized by aggregate/ineligible items: '+json.dumps(r,default=str)


def test_reservation_valid_piece_positive_control(connection):
    s=seed(connection,['valid'])
    result=create_reservation(connection,company_id=s['company'],unit_id=s['unit'],epi_id=s['epi'],quantity=1,actor_user_id=s['actor']['id'])
    connection.commit()
    assert result['status']=='active' and result['quantity']==1
    assert unit_balance(connection,s['company'],s['unit'],s['epi'])['free']==0


@pytest.mark.parametrize('scope',['unit','tenant'])
def test_delivery_refuses_cross_scope_stock_item(connection,scope):
    s=seed(connection,['valid'])
    if scope=='tenant':
        other=seed(connection,['valid'])
        iid=other['items']['valid']['id']; qr=other['items']['valid']['qr']
    else:
        qr='LOCAL-QA-'+uuid4().hex
        iid=create_stock_item(connection,s['company'],s['other_unit'],s['epi'],'N/A','M','N/A',next_company_qr_sequence(connection,s['company']),qr,None,'','','unit','','',s['actor']['id'],datetime.now(timezone.utc).isoformat())
        record_received_item_physical(connection,iid,FUTURE,s['actor']['id'],datetime.now(timezone.utc).isoformat())
    connection.commit()
    r=delivery(s,'valid',dict(stock_item_id=iid,stock_qr_code=qr))
    assert r['error'] and 'incompatível' in r['error']['message'].lower(),r
    assert r['item_after']['status']=='in_stock' and r['item_after']['delivery_id'] is None


@pytest.mark.parametrize('name,kinds,catalog,aggregate',[
    ('mixed',['valid','expired','unknown','blocked'],FUTURE,4),
    ('unknown_only',['unknown'],FUTURE,1),
    ('expired_blocked_only',['expired','blocked'],FUTURE,2),
    ('zero_pieces',[],FUTURE,0),
    ('zero_pieces_expired_catalog',[],PAST,0),
])
def test_export_native_stock_epis_payload(connection,name,kinds,catalog,aggregate):
    s=seed(connection,kinds,catalog=catalog,aggregate=aggregate,ca_expiry=FUTURE)
    path=f'/api/stock/epis?unit_id={s["unit"]}'
    handler=ResponseSink(path,s['actor'])
    handle_get_stock_epis(handler,urlparse(path),None,None)
    assert handler.status==200
    assert len(handler.body['items'])==1,handler.body
    piece_rows=[row_to_dict(r) for r in connection.execute('SELECT id,company_id,unit_id,epi_id,status,physical_expiry_date,expiry_source FROM epi_stock_items WHERE company_id=? AND unit_id=? AND epi_id=? ORDER BY id',(s['company'],s['unit'],s['epi'])).fetchall()]
    from modules.stock.service import compute_stock_compliance,fetch_available_stock_items
    compliance=compute_stock_compliance(connection,s['company'],s['unit'])
    candidates=[row_to_dict(r) for r in fetch_available_stock_items(connection,s['company'],s['unit'],s['epi'])]
    PAYLOADS.append(dict(scenario=name,today=TODAY,company_id=s['company'],unit_id=s['unit'],epi_id=s['epi'],pieces=piece_rows,response_status=handler.status,response=handler.body,compliance=compliance,available_candidates=candidates,balance=unit_balance(connection,s['company'],s['unit'],s['epi'])))
    persist()


def test_unknown_payload_does_not_claim_known_effective_validity(connection):
    s=seed(connection,['unknown'])
    path=f'/api/stock/epis?unit_id={s["unit"]}'
    handler=ResponseSink(path,s['actor'])
    handle_get_stock_epis(handler,urlparse(path),None,None)
    item=handler.body['items'][0]
    OBSERVATIONS.append(dict(case='unknown_effective_validity',stock_epi=item));persist()
    assert not item['effective_validity_date'], 'Unknown physical expiry became catalog date: '+json.dumps(item,default=str)


@pytest.mark.parametrize('scope',['unit','tenant'])
def test_reservation_does_not_use_another_scope_balance(connection,scope):
    from modules.stock.reservations import InsufficientFreeStock
    s=seed(connection,['valid'])
    company=s['company'] if scope=='unit' else s['foreign_company']
    unit=s['other_unit'] if scope=='unit' else s['foreign_unit']
    with pytest.raises(InsufficientFreeStock,match='Saldo livre insuficiente'):
        create_reservation(connection,company_id=company,unit_id=unit,epi_id=s['epi'],quantity=1,actor_user_id=s['actor']['id'])
    assert connection.execute('SELECT COUNT(*) AS n FROM stock_reservations WHERE epi_id=?',(s['epi'],)).fetchone()['n']==0


def test_stock_endpoint_refuses_foreign_tenant_unit(connection):
    s=seed(connection,['valid'])
    path=f'/api/stock/epis?unit_id={s["foreign_unit"]}'
    handler=ResponseSink(path,s['actor'])
    with pytest.raises(ValueError,match='Unidade não pertence à empresa'):
        handle_get_stock_epis(handler,urlparse(path),None,None)
    assert handler.body is None


def test_same_epi_mixed_aggregate_never_authorizes_individual_piece(connection):
    s=seed(connection,['valid','expired','unknown','blocked'],ca_expiry=FUTURE)
    path=f'/api/stock/epis?unit_id={s["unit"]}'
    handler=ResponseSink(path,s['actor'])
    handle_get_stock_epis(handler,urlparse(path),None,None)
    assert handler.status==200 and len(handler.body['items'])==1
    aggregate=handler.body['items'][0]['effective_validity_date']
    assert aggregate==PAST, handler.body
    # All four POSTs target the same real company/unit/EPI. Run every POST
    # before the unknown assertion, preserving outcomes of every guard.
    valid=delivery(s,'valid')
    expired=delivery(s,'expired')
    blocked=delivery(s,'blocked')
    unknown=delivery(s,'unknown')
    record=dict(case='same_epi_mixed_aggregate',company_id=s['company'],unit_id=s['unit'],epi_id=s['epi'],initial_stock_response=handler.body,aggregate_effective_validity_date=aggregate,seed=s['items'],outcomes=dict(valid=valid,expired=expired,blocked=blocked,unknown=unknown))
    OBSERVATIONS.append(record);persist()
    assert valid['response_status']==201 and valid['item_after']['status']=='delivered', record
    assert expired['error'] and expired['item_after']['status']=='in_stock' and expired['item_after']['delivery_id'] is None, record
    assert blocked['error'] and blocked['item_after']['status']=='blocked_rejected' and blocked['item_after']['delivery_id'] is None, record
    assert unknown['error'] and unknown['item_after']['status']=='in_stock' and unknown['item_after']['delivery_id'] is None, 'Unknown delivered inside the same mixed EPI with expired aggregate: '+json.dumps(record,default=str)


@pytest.mark.parametrize('race', ['reserve_reserve', 'deliver_deliver', 'deliver_reserve'])
@pytest.mark.parametrize('iteration', range(3))
def test_real_concurrent_operations_never_double_consume(connection, race, iteration):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    s = seed(connection, ['valid'], ca_expiry=FUTURE)
    barrier = Barrier(2)

    def worker(operation):
        c = get_connection()
        try:
            barrier.wait(timeout=15)
            if operation == 'deliver':
                result = delivery(dict(s, c=c), 'valid')
                return result['response_status'] == 201
            try:
                create_reservation(c, company_id=s['company'], unit_id=s['unit'],
                                   epi_id=s['epi'], quantity=1, actor_user_id=s['actor']['id'])
                c.commit()
                return True
            except ValueError:
                c.rollback()
                return False
        finally:
            c.close()

    operations = {'reserve_reserve': ['reserve', 'reserve'],
                  'deliver_deliver': ['deliver', 'deliver'],
                  'deliver_reserve': ['deliver', 'reserve']}[race]
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(worker, operations))
    assert sum(results) == 1, (race, iteration, results)
    balance = unit_balance(connection, s['company'], s['unit'], s['epi'])
    delivered = connection.execute('SELECT COUNT(*) AS n FROM deliveries WHERE company_id=?',
                                   (s['company'],)).fetchone()['n']
    assert balance['physical'] >= 0 and balance['free'] == 0
    assert delivered + balance['reserved'] == 1
    assert balance['reservation_shortfall'] == 0
    assert balance['reconciliation_delta'] == 0


def test_delivery_rollback_after_claim_includes_balance_movement_and_ficha(connection, monkeypatch):
    s = seed(connection, ['valid'])

    def reject_ficha(*args, **kwargs):
        raise RuntimeError('forced failure after physical claim and movement')

    monkeypatch.setattr(delivery_routes, 'ensure_ficha_for_delivery', reject_ficha)
    with pytest.raises(RuntimeError, match='forced failure'):
        delivery(s, 'valid')
    row = connection.execute('SELECT status, delivery_id FROM epi_stock_items WHERE id=?',
                             (s['items']['valid']['id'],)).fetchone()
    assert row['status'] == 'in_stock' and row['delivery_id'] is None
    assert unit_balance(connection, s['company'], s['unit'], s['epi'])['physical'] == 1
    for table in ('deliveries', 'stock_movements', 'epi_ficha_items'):
        assert connection.execute('SELECT COUNT(*) AS n FROM '+table+' WHERE company_id=?',
                                  (s['company'],)).fetchone()['n'] == 0


def test_available_handler_serializes_only_physical_eligible_candidates(connection):
    from modules.stock.routes import handle_get_stock_available_items
    s = seed(connection, ['valid', 'expired', 'unknown', 'blocked'])
    path = f'/api/stock/available-items?unit_id={s["unit"]}&epi_id={s["epi"]}'
    handler = ResponseSink(path, s['actor'])
    handle_get_stock_available_items(handler, urlparse(path), None, None)
    assert handler.status == 200
    assert [item['id'] for item in handler.body['items']] == [s['items']['valid']['id']]
    item = handler.body['items'][0]
    assert item['physical_expiry_date'] == FUTURE
    assert item['eligible_for_delivery'] is True


def test_mixed_indicators_preserve_all_physical_categories(connection):
    from modules.stock.eligibility import physical_summary_map
    s = seed(connection, ['valid', 'expired', 'unknown', 'blocked'])
    summary = physical_summary_map(connection, s['company'], s['unit'])[s['epi']]
    assert summary['physical_pieces'] == 4 and summary['eligible_pieces'] == 1
    assert summary['expired'] == 1 and summary['unknown'] == 1
    assert summary['blocked_pieces'] == 1
    assert summary['count_unit'] == 'physical_pieces'


@pytest.mark.parametrize('aggregate,expected_free,expected_delta', [(0,0,-1),(5,1,4)])
def test_reservation_reconciliation_bounds_by_real_pieces_and_ledger(connection, aggregate, expected_free, expected_delta):
    s = seed(connection, ['valid'], aggregate=aggregate)
    balance = unit_balance(connection, s['company'], s['unit'], s['epi'])
    assert balance['physical'] == aggregate and balance['eligible'] == 1
    assert balance['free'] == expected_free
    assert balance['reconciliation_delta'] == expected_delta


def test_physical_fefo_orders_multiple_eligible_lots_only(connection):
    s = seed(connection, ['valid', 'valid', 'expired', 'unknown', 'blocked'])
    sooner = (date.today() + timedelta(days=4)).isoformat()
    connection.execute('UPDATE epi_stock_items SET physical_expiry_date=? WHERE id=?',
                       (sooner, s['items']['valid_1']['id']))
    connection.commit()
    rows = fetch_available_stock_items(connection, s['company'], s['unit'], s['epi'])
    assert [row['id'] for row in rows] == [s['items']['valid_1']['id'], s['items']['valid']['id']]


def request_for(s, quantity=1):
    now = datetime.now(timezone.utc).isoformat()
    rid = s['c'].execute('INSERT INTO epi_requests(company_id,unit_id,employee_id,epi_id,quantity,'
                         'request_token,status,requested_at,last_updated_at) VALUES(?,?,?,?,?,?,?,?,?)',
                         (s['company'],s['unit'],s['employee'],s['epi'],quantity,
                          uuid4().hex,'reservado',now,now)).lastrowid
    s['c'].commit()
    return rid


def test_direct_delivery_cannot_steal_an_active_reservation(connection):
    s = seed(connection, ['valid'])
    rid = request_for(s)
    create_reservation(connection,company_id=s['company'],unit_id=s['unit'],epi_id=s['epi'],
                       quantity=1,request_id=rid,actor_user_id=s['actor']['id'])
    connection.commit()
    assert fetch_available_stock_items(connection,s['company'],s['unit'],s['epi']) == []
    assert len(fetch_available_stock_items(connection,s['company'],s['unit'],s['epi'],request_id=rid)) == 1
    refused = delivery(s, 'valid')
    assert refused['error'] and refused['item_after']['status'] == 'in_stock'
    allowed = delivery(s, 'valid', {'request_id': rid})
    assert allowed['response_status'] == 201
    assert unit_balance(connection,s['company'],s['unit'],s['epi'])['reserved'] == 0


def test_foreign_request_cannot_be_mutated_or_consume_own_stock(connection):
    s = seed(connection, ['valid'])
    foreign = seed(connection, ['valid'])
    rid = request_for(foreign)
    result = delivery(s,'valid',{'request_id':rid})
    assert result['error'] and result['item_after']['status'] == 'in_stock'
    row = connection.execute('SELECT status,delivery_id FROM epi_requests WHERE id=?', (rid,)).fetchone()
    assert row['status'] == 'reservado' and row['delivery_id'] is None


def test_partial_request_delivery_consumes_reservation_only_when_all_pieces_leave(connection):
    s = seed(connection, ['valid','valid'])
    rid = request_for(s, quantity=2)
    create_reservation(connection,company_id=s['company'],unit_id=s['unit'],epi_id=s['epi'],
                       quantity=2,request_id=rid,actor_user_id=s['actor']['id'])
    connection.commit()
    assert delivery(s,'valid',{'request_id':rid})['response_status'] == 201
    assert connection.execute('SELECT status FROM epi_requests WHERE id=?',(rid,)).fetchone()['status'] == 'reservado'
    assert delivery(s,'valid_1',{'request_id':rid})['response_status'] == 201
    assert connection.execute('SELECT status FROM epi_requests WHERE id=?',(rid,)).fetchone()['status'] == 'entregue'
    balance = unit_balance(connection,s['company'],s['unit'],s['epi'])
    assert balance['physical'] == balance['reserved'] == balance['free'] == 0


@pytest.mark.parametrize('status', ['quarantine', 'discarded', 'supplier_returned', 'reserved', 'maintenance', 'hygiene'])
def test_operationally_ineligible_or_terminal_items_never_become_available(connection,status):
    s = seed(connection,['valid'])
    connection.execute('UPDATE epi_stock_items SET status=? WHERE id=?',(status,s['items']['valid']['id']))
    connection.commit()
    assert fetch_available_stock_items(connection,s['company'],s['unit'],s['epi']) == []
    assert unit_balance(connection,s['company'],s['unit'],s['epi'])['free'] == 0
    assert delivery(s,'valid')['error'] is not None


def test_different_pieces_cannot_consume_the_same_last_ledger_unit(connection):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    s = seed(connection,['valid','valid'],aggregate=1)
    barrier = Barrier(2)

    def run(kind):
        c = get_connection()
        try:
            barrier.wait(timeout=15)
            return delivery(dict(s,c=c),kind)['response_status'] == 201
        finally:
            c.close()

    with ThreadPoolExecutor(max_workers=2) as pool:
        result = list(pool.map(run,['valid','valid_1']))
    assert sum(result) == 1
    assert unit_balance(connection,s['company'],s['unit'],s['epi'])['physical'] == 0


def test_inactive_epi_cannot_back_new_reservations(connection):
    s = seed(connection,['valid'])
    connection.execute('UPDATE epis SET active=0 WHERE id=?',(s['epi'],))
    connection.commit()
    assert unit_balance(connection,s['company'],s['unit'],s['epi'])['free'] == 0
    assert fetch_available_stock_items(connection,s['company'],s['unit'],s['epi']) == []
    with pytest.raises(ValueError):
        create_reservation(connection,company_id=s['company'],unit_id=s['unit'],epi_id=s['epi'],quantity=1)


def test_authenticated_actor_without_delivery_permission_is_refused(connection):
    s = seed(connection,['valid'])
    connection.execute("UPDATE users SET role='viewer' WHERE id=?",(s['actor']['id'],))
    connection.commit()
    s['actor']['role'] = 'viewer'
    result = delivery(s,'valid')
    assert result['error'] is not None and result['response_status'] is None
    assert result['item_after']['status'] == 'in_stock'
    assert result['aggregate_after']['quantity'] == 1


@pytest.mark.parametrize('kind,expected', [('valid',True),('expired',False),('unknown',False),('blocked',False)])
def test_qr_lookup_preserves_physical_validity_and_refuses_ineligible_selection(connection,kind,expected):
    from modules.stock.routes import handle_get_stock_lookup_qr
    s = seed(connection,[kind])
    path = f'/api/stock/lookup-qr?unit_id={s["unit"]}&qr_code={s["items"][kind]["qr"]}'
    handler = ResponseSink(path,s['actor'])
    handle_get_stock_lookup_qr(handler,urlparse(path),None,None)
    assert handler.status == 200
    item = handler.body['stock_item']
    assert item['id'] == s['items'][kind]['id']
    assert item['eligible_for_delivery'] is expected
    if kind == 'unknown':
        assert item['physical_expiry_date'] is None and item['physical_validity_status'] == 'unknown'


def test_released_reservation_cannot_expose_stock_committed_to_another_request(connection):
    from modules.stock.reservations import release_reservation
    s = seed(connection, ['valid'])
    first = request_for(s)
    reservation = create_reservation(connection, company_id=s['company'], unit_id=s['unit'],
                                     epi_id=s['epi'], quantity=1, request_id=first)
    release_reservation(connection, reservation['id'])
    second = request_for(s)
    create_reservation(connection, company_id=s['company'], unit_id=s['unit'],
                       epi_id=s['epi'], quantity=1, request_id=second)
    connection.commit()
    assert unit_balance(connection, s['company'], s['unit'], s['epi'])['free'] == 0
    with pytest.raises(ValueError, match='Reserva'):
        fetch_available_stock_items(connection, s['company'], s['unit'], s['epi'], request_id=first)
