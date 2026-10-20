"""Entrada manual por lote: HTTP/JWT, elegibilidade e transação em PostgreSQL real."""
import json
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from uuid import uuid4

import pytest

from test_est_v3_5_postmerge_receipt import server as server
from test_est_v3_5_r3_lot_receipt_http import _fresh, _pieces, _seed

pytestmark = pytest.mark.skipif(
    not os.environ.get('DATABASE_URL', '').startswith('postgres'),
    reason='Entrada manual exige PostgreSQL isolado.',
)
FUTURE = (date.today() + timedelta(days=365)).isoformat()
PAST = (date.today() - timedelta(days=10)).isoformat()


@pytest.fixture(autouse=True)
def enforce(monkeypatch):
    monkeypatch.setenv('JWT_ENFORCEMENT_MODE', 'enforce')


def seed(role='admin', linked=True):
    s = _seed(role=role)
    if linked and role in ('admin', 'user'):
        with _fresh() as c:
            employee = c.execute(
                'INSERT INTO employees(company_id,unit_id,employee_id_code,name,sector,'
                'role_name,admission_date,schedule_type) VALUES (?,?,?,?,?,?,?,?)',
                (s['company'], s['unit'], uuid4().hex, 'E', 'S', 'R', '2020-01-01', 'administrativo'),
            ).lastrowid
            c.execute('UPDATE users SET linked_employee_id=? WHERE id=?', (employee, s['actor']['id']))
            c.commit()
    return s


def post(server, s, **changes):
    from core.security import create_jwt_token
    body = dict(actor_user_id=s['actor']['id'], company_id=s['company'], unit_id=s['unit'],
                epi_id=s['epi'], movement_type='in', quantity=2, size='M',
                label_measure='unidade', label_printer_name='Zebra', label_print_format='50x30mm',
                manufacture_date='2020-01-01', lot_code='LOTE-A', physical_expiry_date=FUTURE,
                expiry_source='label', expiry_evidence='Etiqueta verificável do lote A')
    body.update(changes)
    request = Request(server + '/api/stock/movements', data=json.dumps(body).encode(),
                      headers={'Authorization': 'Bearer ' + create_jwt_token(s['actor']),
                               'Content-Type': 'application/json'}, method='POST')
    try:
        response = urlopen(request, timeout=15)
    except HTTPError as error:
        response = error
    with response:
        return response.status, json.load(response)


def available(s):
    from modules.stock.service import fetch_available_stock_items
    with _fresh() as c:
        return fetch_available_stock_items(c, s['company'], s['unit'], s['epi'])


def assert_no_writes(s):
    with _fresh() as c:
        for table in ('epi_stock_items', 'stock_movements', 'unit_epi_stock', 'epi_stock_events'):
            assert c.execute(f'SELECT COUNT(*) AS n FROM {table} WHERE company_id=?',
                             (s['company'],)).fetchone()['n'] == 0


@pytest.mark.parametrize('role', ['admin', 'user'])
@pytest.mark.parametrize('source', ['label', 'manufacturer_document'])
def test_proven_batch_is_available_and_audited_without_catalog_changes(server, role, source):
    s = seed(role)
    with _fresh() as c:
        c.execute('UPDATE epis SET epi_validity_date=? WHERE id=?', (PAST, s['epi']))
        c.commit()
    status, body = post(server, s, expiry_source=source)
    assert status == 201, body
    assert body['new_stock'] == 2 and len(body['qr_labels']) == 2
    rows = _pieces(s['company'], s['epi'])
    assert len(rows) == 2
    assert all(r['physical_expiry_date'] == FUTURE and r['expiry_source'] == source
               and r['expiry_evidence'] == 'Etiqueta verificável do lote A' for r in rows)
    assert {r['id'] for r in available(s)} == {r['id'] for r in rows}
    with _fresh() as c:
        events = c.execute('SELECT * FROM epi_stock_events WHERE company_id=?', (s['company'],)).fetchall()
        assert len(events) == 2
        for event in events:
            after = event['after_values']
            after = json.loads(after) if isinstance(after, str) else after
            assert event['event_type'] == 'receipt' and event['actor_user_id'] == s['actor']['id']
            assert after['lot_code'] == 'LOTE-A' and after['physical_expiry_date'] == FUTURE
            assert after['expiry_source'] == source and after['expiry_evidence']
        assert str(c.execute('SELECT epi_validity_date FROM epis WHERE id=?',
                             (s['epi'],)).fetchone()['epi_validity_date']) == PAST


def test_batches_of_same_epi_keep_separate_expiry_and_evidence(server):
    s = seed()
    later = (date.today() + timedelta(days=600)).isoformat()
    assert post(server, s)[0] == 201
    assert post(server, s, lot_code='LOTE-B', physical_expiry_date=later,
                expiry_source='manufacturer_document', expiry_evidence='Documento do lote B')[0] == 201
    assert post(server, s, lot_code='LOTE-C', physical_expiry_date='', expiry_source='',
                expiry_evidence='', physical_validity_unknown=True)[0] == 201
    rows = _pieces(s['company'], s['epi'])
    assert [(r['lot_code'], r['physical_expiry_date']) for r in rows] == [
        ('LOTE-A', FUTURE), ('LOTE-A', FUTURE), ('LOTE-B', later), ('LOTE-B', later),
        ('LOTE-C', None), ('LOTE-C', None)]
    assert len(available(s)) == 4
    assert all(r['expiry_evidence'] == 'Documento do lote B' for r in rows if r['lot_code'] == 'LOTE-B')


def test_expired_batch_is_received_blocked(server):
    s = seed()
    assert post(server, s, physical_expiry_date=PAST)[0] == 201
    assert all(r['status'] == 'blocked_expired' for r in _pieces(s['company'], s['epi']))
    assert available(s) == []


@pytest.mark.parametrize('changes', [
    {'lot_code': ''}, {'expiry_evidence': ''}, {'expiry_evidence': '   '},
    {'expiry_source': ''}, {'expiry_source': 'catalog'}, {'expiry_source': 'regularization'},
    {'physical_expiry_date': '2026-02-30'}, {'physical_expiry_date': '20270101'},
    {'physical_expiry_date': ''}, {'manufacture_date': '9999-12-31'},
    {'physical_validity_unknown': True}, {'physical_validity_unknown': 'true'},
])
def test_incomplete_or_conflicting_proof_fails_before_writes(server, changes):
    s = seed()
    status, body = post(server, s, **changes)
    assert status == 400, body
    assert_no_writes(s)


@pytest.mark.parametrize('role', ['general_admin', 'master_admin', 'registry_admin', 'buyer', 'approver', 'employee'])
def test_other_roles_cannot_capture_proven_expiry_by_direct_api(server, role):
    s = seed(role)
    status, body = post(server, s)
    assert status == 403, body
    assert_no_writes(s)


def test_legacy_adjustment_without_proof_stays_pending_even_with_catalog_future(server):
    s = seed('general_admin')
    status, body = post(server, s, physical_expiry_date=None, expiry_source=None, expiry_evidence=None)
    assert status == 201, body
    assert all(r['physical_expiry_date'] is None and r['expiry_source'] == 'unknown'
               for r in _pieces(s['company'], s['epi']))
    assert available(s) == []


@pytest.mark.parametrize('wrong_scope', ['unit', 'company', 'epi', 'unlinked'])
def test_scope_cannot_be_changed_by_payload(server, wrong_scope):
    s = seed(linked=wrong_scope != 'unlinked')
    foreign = seed()
    changes = {}
    if wrong_scope != 'unlinked':
        changes[{'unit': 'unit_id', 'company': 'company_id', 'epi': 'epi_id'}[wrong_scope]] = foreign[wrong_scope]
    status, body = post(server, s, **changes)
    assert status in (400, 403), body
    assert_no_writes(s)
    assert_no_writes(foreign)


def test_audit_failure_rolls_back_entire_receipt(server, monkeypatch):
    import modules.stock.service as service
    s = seed()

    def fail(*args, **kwargs):
        raise RuntimeError('Falha controlada da auditoria')

    with monkeypatch.context() as patch:
        patch.setattr(service, '_append_stock_event', fail)
        status, _body = post(server, s)
        assert status == 500
    assert_no_writes(s)
    assert post(server, s)[0] == 201
    assert len(available(s)) == 2


def test_parallel_batches_preserve_stock_and_separate_proof(server, monkeypatch):
    import modules.stock.routes as routes
    s = seed()
    original = routes.get_unit_stock
    first_read, second_read, release = threading.Event(), threading.Event(), threading.Event()
    guard = threading.Lock()
    reads = 0

    def pause_read(*args):
        nonlocal reads
        row = original(*args)
        with guard:
            reads += 1
            current = reads
        if current == 1:
            first_read.set()
            assert release.wait(5), 'Primeira leitura não liberada'
        else:
            second_read.set()
        return row

    monkeypatch.setattr(routes, 'get_unit_stock', pause_read)
    with ThreadPoolExecutor(max_workers=2) as workers:
        first = workers.submit(post, server, s)
        assert first_read.wait(5)
        second = workers.submit(post, server, s, lot_code='LOTE-B', expiry_evidence='Etiqueta B')
        # A leitura antiga podia avançar; a leitura travada espera o primeiro
        # commit. Liberamos em ambos os casos e verificamos o resultado real.
        second_read.wait(0.2)
        release.set()
        assert first.result(timeout=10)[0] == 201
        assert second.result(timeout=10)[0] == 201
    with _fresh() as c:
        assert c.execute('SELECT quantity FROM unit_epi_stock WHERE company_id=?',
                         (s['company'],)).fetchone()['quantity'] == 4
        movements = c.execute('SELECT previous_stock,new_stock FROM stock_movements '
                              'WHERE company_id=? ORDER BY id', (s['company'],)).fetchall()
        assert [tuple(r) for r in movements] == [(0, 2), (2, 4)]
    assert len(available(s)) == 4
