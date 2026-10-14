"""Adversarial receipt quantity contract against isolated PostgreSQL and JWT."""
import os
import json
from datetime import datetime, timezone
from http.server import ThreadingHTTPServer
from threading import Thread
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from uuid import uuid4

import pytest

from test_est_v3_5_r3_lot_receipt_http import _fresh, _pieces, _post, _seed

pytestmark = pytest.mark.skipif(
    not os.environ.get('DATABASE_URL', '').startswith('postgres'),
    reason='Requires isolated PostgreSQL.',
)


@pytest.fixture(scope='module', autouse=True)
def schema():
    from core.bootstrap import init_db
    init_db()


@pytest.fixture(autouse=True)
def jwt(monkeypatch):
    monkeypatch.setenv('JWT_ENFORCEMENT_MODE', 'enforce')


def link_po(s, received):
    with _fresh() as c:
        po = c.execute(
            'INSERT INTO purchase_orders (purchase_request_id, company_id, unit_id, '
            'created_by_user_id, created_at, updated_at, po_number) VALUES (?,?,?,?,?,?,?)',
            (s['pr'], s['company'], s['unit'], s['actor']['id'], '2024-01-01', '2024-01-01', uuid4().hex),
        ).lastrowid
        c.execute(
            'INSERT INTO purchase_order_items (purchase_order_id, purchase_request_item_id, '
            'company_id, unit_id, epi_id, quantity, quantity_received, created_at, updated_at) '
            'VALUES (?,?,?,?,?,?,?,?,?)',
            (po, s['pri'], s['company'], s['unit'], s['epi'], 5, received, '2024-01-01', '2024-01-01'),
        )
        c.commit()


@pytest.mark.parametrize('quantity', [0, -2])
def test_invalid_effective_quantity_refuses_and_rolls_back_http(quantity):
    s = _seed(qty=5)
    link_po(s, quantity)
    h = _post(s['actor'], s['pr'], [{'id': s['pri'], 'received': True,
        'lots': [{'quantity': 5}]}])
    assert h.status == 400 and h.body['validation']['item_id'] == s['pri']
    assert _pieces(s['company'], s['epi']) == []
    with _fresh() as c:
        assert c.execute('SELECT status FROM purchase_requests WHERE id=?', (s['pr'],)).fetchone()['status'] == 'received'
        assert c.execute('SELECT COUNT(*) AS n FROM stock_movements WHERE company_id=?', (s['company'],)).fetchone()['n'] == 0
        assert c.execute('SELECT COUNT(*) AS n FROM purchase_events WHERE entity_id=? AND entity_type=?',
                         (s['pr'], 'purchase_request')).fetchone()['n'] == 0


def test_partial_http_success_matches_persisted_count_and_qr_ids():
    s = _seed(qty=5)
    link_po(s, 2)
    h = _post(s['actor'], s['pr'], [{'id': s['pri'], 'received': True,
        'lots': [{'quantity': 2}]}])
    rows = _pieces(s['company'], s['epi'])
    assert h.status == 200 and h.body['ok'] is True
    assert h.body['stock_entries'] == len(rows) == len(h.body['qr_labels']) == 2
    assert {p['id'] for p in rows} == {p['stock_item_id'] for p in h.body['qr_labels']}
    with _fresh() as c:
        assert c.execute('SELECT quantity FROM unit_epi_stock WHERE company_id=? AND epi_id=?',
                         (s['company'], s['epi'])).fetchone()['quantity'] == 2


def test_no_piece_http_response_has_no_stock_success():
    s = _seed(qty=5)
    h = _post(s['actor'], s['pr'], [{'id': s['pri'], 'received': False}], comment='Not delivered')
    assert h.body['stock_entries'] == 0 and h.body['qr_labels'] == []
    assert _pieces(s['company'], s['epi']) == []


def test_foreign_item_http_cannot_confirm_empty_receipt():
    s, other = _seed(qty=5), _seed(qty=5)
    h = _post(s['actor'], s['pr'], [{'id': other['pri'], 'received': True}])
    assert h.status == 400 and h.body['validation']['code'] == 'INVALID_RECEIPT_LINE'
    assert _pieces(s['company'], s['epi']) == []
    with _fresh() as c:
        assert c.execute('SELECT status FROM purchase_requests WHERE id=?', (s['pr'],)).fetchone()['status'] == 'received'


@pytest.fixture(scope='module')
def wire_server():
    import app
    app._set_bootstrap_state(ready=True, completed_at=datetime.now(timezone.utc).isoformat(),
                             error_code='', error_kind='', error_message='')
    server = ThreadingHTTPServer(('127.0.0.1', 0), app.EpiHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f'http://127.0.0.1:{server.server_port}'
    server.shutdown()
    thread.join(timeout=10)
    server.server_close()


def wire_post(base, s, received=True):
    from core.security import create_jwt_token
    request = Request(f"{base}/api/purchase-requests/{s['pr']}/status",
        data=json.dumps({'actor_user_id': s['actor']['id'], 'status': 'checked',
                         'received_items': [{'id': s['pri'], 'received': received}]}).encode(),
        headers={'Content-Type': 'application/json',
                 'Authorization': 'Bearer ' + create_jwt_token(s['actor'])}, method='POST')
    try:
        response = urlopen(request, timeout=10)
    except HTTPError as error:
        response = error
    with response:
        return response.status, json.loads(response.read())


@pytest.mark.parametrize('quantity', [0, -2])
def test_wire_http_invalid_quantity_returns_400_without_commit(wire_server, quantity):
    s = _seed(qty=5)
    link_po(s, quantity)
    status, body = wire_post(wire_server, s)
    assert status == 400
    assert 'Quantidade efetivamente recebida' in body['error']
    assert _pieces(s['company'], s['epi']) == []
    with _fresh() as c:
        assert c.execute('SELECT status FROM purchase_requests WHERE id=?', (s['pr'],)).fetchone()['status'] == 'received'


def test_wire_http_partial_count_is_persisted_count(wire_server):
    s = _seed(qty=5)
    link_po(s, 2)
    status, body = wire_post(wire_server, s)
    assert status == 200 and body['ok'] is True
    assert body['stock_entries'] == len(body['qr_labels']) == len(_pieces(s['company'], s['epi'])) == 2


def test_wire_http_permission_denied_cannot_add_stock(wire_server):
    s = _seed(role='employee', qty=5)
    status, _ = wire_post(wire_server, s)
    assert status == 403
    assert _pieces(s['company'], s['epi']) == []


def wire_payload(base, s, lines):
    from core.security import create_jwt_token
    request = Request(f"{base}/api/purchase-requests/{s['pr']}/status",
        data=json.dumps({'actor_user_id': s['actor']['id'], 'status':'checked',
                         'received_items':lines, 'comment':'Conferência mista adversarial'}).encode(),
        headers={'Content-Type':'application/json','Authorization':'Bearer '+create_jwt_token(s['actor'])},method='POST')
    try:
        response=urlopen(request,timeout=10)
    except HTTPError as error:
        response=error
    with response:
        return response.status,json.loads(response.read())


@pytest.mark.parametrize('quantity',[0,-2])
@pytest.mark.parametrize('received',[True,False,None])
def test_original_mixed_attack_refuses_every_line_without_partial_persistence(wire_server,quantity,received):
    s=_seed(qty=5)
    link_po(s,2) # Valid line first: original attack persisted two pieces here.
    with _fresh() as c:
        bad=c.execute("INSERT INTO purchase_request_items (purchase_request_id,company_id,unit_id,epi_id,epi_name,quantity_requested,status,created_at,updated_at) VALUES (?,?,?,?,?,5,'received',?,?)",
            (s['pr'],s['company'],s['unit'],s['epi'],'Item problemático','2024-01-01','2024-01-01')).lastrowid
        c.commit()
    link_po(dict(s,pri=bad),quantity)
    lines=[{'id':s['pri'],'received':True}]
    if received is not None:
        lines.append({'id':bad,'received':received})
    status,body=wire_payload(wire_server,s,lines)
    assert status==400 and body['ok'] is False
    assert body['validation']['code']=='INVALID_RECEIPT_QUANTITY'
    assert body['validation']['line_index']==2 and body['validation']['item_id']==bad
    assert 'Linha 2' in body['error'] and str(bad) in body['error'] and 'Item problemático' in body['error']
    assert _pieces(s['company'],s['epi'])==[]
    with _fresh() as c:
        assert c.execute('SELECT status FROM purchase_requests WHERE id=?',(s['pr'],)).fetchone()['status']=='received'
        for table in ['stock_movements','purchase_events','purchase_pendencies','unit_epi_stock']:
            assert c.execute(f'SELECT COUNT(*) AS n FROM {table} WHERE company_id=?',(s['company'],)).fetchone()['n']==0


@pytest.mark.parametrize('value',['invalid',None,0,-2,1.5,True])
def test_numeric_lot_input_rejected_with_structured_line_error(wire_server,value):
    s=_seed(qty=2)
    status,body=wire_payload(wire_server,s,[{'id':s['pri'],'received':True,'lots':[{'quantity':value}]}])
    assert status==400 and body['validation']['code']=='INVALID_RECEIPT_LOTS'
    assert body['validation']['item_id']==s['pri'] and 'Linha 1' in body['error']
    assert 'invalid literal' not in body['error']
    assert _pieces(s['company'],s['epi'])==[]


def test_unchecked_invalid_line_alone_is_not_a_neutral_success(wire_server):
    s=_seed(qty=5)
    link_po(s,0)
    status,body=wire_payload(wire_server,s,[{'id':s['pri'],'received':False}])
    assert status==400 and body['validation']['item_id']==s['pri']
    with _fresh() as c:
        assert c.execute('SELECT COUNT(*) AS n FROM purchase_events WHERE company_id=?',(s['company'],)).fetchone()['n']==0
