"""Post-merge receipt integrity through native HTTP/JWT and PostgreSQL.

Concurrency hooks only pause native reads; SQL, services and commits are real.
They allow either a second read (the original bug) or a native lock wait (fixed).
"""
import json
import os
import threading
import time
from uuid import uuid4
from datetime import datetime, timezone
from http.server import ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from test_est_v3_5_r3_lot_receipt_http import FUTURE, _eligible, _fresh, _pieces, _seed

pytestmark = pytest.mark.skipif(
    not os.environ.get('DATABASE_URL', '').startswith('postgres'),
    reason='Requires isolated PostgreSQL.',
)


@pytest.fixture(scope='module')
def server():
    from core.bootstrap import init_db
    import app

    init_db()
    app._set_bootstrap_state(
        ready=True, completed_at=datetime.now(timezone.utc).isoformat(),
        error_code='', error_kind='', error_message='',
    )
    httpd = ThreadingHTTPServer(('127.0.0.1', 0), app.EpiHandler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield f'http://127.0.0.1:{httpd.server_port}'
    httpd.shutdown()
    httpd.server_close()
    thread.join(timeout=5)


def _post(server, s, status='checked', flags=None):
    from core.security import create_jwt_token

    request = Request(
        f"{server}/api/purchase-requests/{s['pr']}/status",
        data=json.dumps({'actor_user_id': s['actor']['id'], 'status': status,
                         'received_items': flags or []}).encode(),
        headers={'Authorization': 'Bearer ' + create_jwt_token(s['actor']),
                 'Content-Type': 'application/json'}, method='POST',
    )
    try:
        response = urlopen(request, timeout=15)
    except HTTPError as error:
        response = error
    with response:
        return response.status, json.loads(response.read())


def _flags(s):
    return [{'id': s['pri'], 'received': True, 'lots': [
        {'quantity': 1, 'manufacturer_validity_date': FUTURE,
         'evidence': 'Manufacturer label', 'lot_code': 'VERIFIED'},
    ]}]


def _add_request_item(c, s, pr_id=None, epi_id=None):
    return c.execute(
        'INSERT INTO purchase_request_items (purchase_request_id, company_id, unit_id, '
        'epi_id, epi_name, quantity_requested, status, created_at, updated_at) '
        "VALUES (?,?,?,?,?,1,'received',?,?)",
        (pr_id or s['pr'], s['company'], s['unit'], epi_id or s['epi'],
         'EPI', '2024-01-01', '2024-01-01'),
    ).lastrowid


def _second_request(s):
    with _fresh() as c:
        pr = c.execute(
            'INSERT INTO purchase_requests (company_id, unit_id, status, title, '
            'created_by_user_id, created_by_name, created_at, updated_at) '
            "VALUES (?,?,'received','Second receipt',?,'Ator',?,?)",
            (s['company'], s['unit'], s['actor']['id'], '2024-01-01', '2024-01-01'),
        ).lastrowid
        pri = _add_request_item(c, s, pr_id=pr)
        c.commit()
    return dict(s, pr=pr, pri=pri)


def _assert_no_receipt(s):
    assert _pieces(s['company'], s['epi']) == []
    with _fresh() as c:
        assert c.execute('SELECT status FROM purchase_requests WHERE id=?',
                         (s['pr'],)).fetchone()['status'] == 'received'
        for table in ('stock_movements', 'purchase_events', 'unit_epi_stock'):
            assert c.execute(f'SELECT COUNT(*) AS n FROM {table} WHERE company_id=?',
                             (s['company'],)).fetchone()['n'] == 0


@pytest.mark.parametrize('evidence', [None, '', '   '])
def test_legacy_known_expiry_without_evidence_refuses_before_writes(server, evidence):
    s = _seed()
    flag = {'id': s['pri'], 'received': True, 'manufacturer_validity_date': FUTURE}
    if evidence is not None:
        flag['evidence'] = evidence
    status, body = _post(server, s, flags=[flag])
    assert status == 400 and body['validation']['code'] == 'INVALID_RECEIPT_LOTS'
    _assert_no_receipt(s)


@pytest.mark.parametrize('second_lots', [None, [{'quantity': 1}]])
def test_each_line_needs_its_own_physical_expiry_and_evidence(server, second_lots):
    s = _seed()
    with _fresh() as c:
        second = _add_request_item(c, s)
        c.commit()
    unknown = {'id': second, 'received': True}
    if second_lots is not None:
        unknown['lots'] = second_lots
    status, body = _post(server, s, flags=[
        {'id': s['pri'], 'received': True, 'manufacturer_validity_date': FUTURE,
         'evidence': 'Verified label of the first line'}, unknown,
    ])
    assert status == 200 and body['stock_entries'] == 2
    with _fresh() as c:
        rows = c.execute(
            'SELECT sm.source_id, esi.physical_expiry_date, esi.expiry_evidence '
            'FROM epi_stock_items esi JOIN stock_movements sm ON sm.id=esi.stock_movement_id '
            'WHERE esi.company_id=? ORDER BY sm.source_id', (s['company'],)
        ).fetchall()
        by_line = {int(row['source_id']): row for row in rows}
        assert str(by_line[s['pri']]['physical_expiry_date']) == FUTURE
        assert by_line[s['pri']]['expiry_evidence'] == 'Verified label of the first line'
        assert by_line[second]['physical_expiry_date'] is None
    assert _eligible(s['company'], s['unit'], s['epi']) == 1


def test_later_line_without_evidence_cannot_commit_earlier_valid_lot(server):
    s = _seed()
    with _fresh() as c:
        second = _add_request_item(c, s)
        c.commit()
    status, _ = _post(server, s, flags=_flags(s) + [
        {'id': second, 'received': True, 'manufacturer_validity_date': FUTURE},
    ])
    assert status == 400
    _assert_no_receipt(s)


def test_legacy_unknown_can_be_received_but_cannot_become_eligible(server):
    s = _seed()
    status, body = _post(server, s, flags=[{'id': s['pri'], 'received': True}])
    assert status == 200 and body['stock_entries'] == 1
    assert _pieces(s['company'], s['epi'])[0]['physical_expiry_date'] is None
    assert _eligible(s['company'], s['unit'], s['epi']) == 0


def test_checked_request_cannot_be_reopened_and_replayed(server):
    s = _seed()
    status, body = _post(server, s, flags=_flags(s))
    assert status == 200 and body['stock_entries'] == 1
    before = _pieces(s['company'], s['epi'])
    status, _ = _post(server, s, status='received')
    assert status == 400
    status, body = _post(server, s, flags=_flags(s))
    assert status == 200 and body['stock_entries'] == 0
    assert _pieces(s['company'], s['epi']) == before
    with _fresh() as c:
        assert c.execute('SELECT COUNT(*) AS n FROM stock_movements WHERE company_id=?',
                         (s['company'],)).fetchone()['n'] == 1


@pytest.mark.parametrize(('rewound', 'action'), [('received', 'checked'), ('approved', 'received')])
def test_persisted_receipt_survives_status_rewinds(server, rewound, action):
    s = _seed()
    assert _post(server, s, flags=_flags(s))[0] == 200
    before = _pieces(s['company'], s['epi'])
    # Simulate a legacy/external rewind; persisted origins must still prevent replay.
    with _fresh() as c:
        c.execute('UPDATE purchase_requests SET status=? WHERE id=?', (rewound, s['pr']))
        c.commit()
    assert _post(server, s, status=action, flags=_flags(s))[0] == 400
    assert _pieces(s['company'], s['epi']) == before


@pytest.mark.parametrize('existing_balance', [False, True])
def test_different_requests_preserve_balance_under_concurrent_receipt(server, monkeypatch, existing_balance):
    from core.database import get_connection
    from modules.purchases import service
    from modules.stock.service import upsert_unit_stock

    first = _seed()
    second = _second_request(first)
    if existing_balance:
        with _fresh() as c:
            upsert_unit_stock(c, first['company'], first['unit'], first['epi'], 0)
            c.commit()
    first_read, second_read, release = (threading.Event() for _ in range(3))
    second_pid_ready = threading.Event()
    second_pid = []
    native_read = service.get_unit_stock

    def paused_read(c, company, unit, epi):
        row = native_read(c, company, unit, epi)
        if company == first['company']:
            if threading.current_thread().name == 'first-receipt':
                first_read.set()
                if not release.wait(timeout=15):
                    raise TimeoutError('First receipt was not released')
            else:
                second_read.set()
        return row

    monkeypatch.setattr(service, 'get_unit_stock', paused_read)
    errors, results = [], []

    def worker(s):
        c = get_connection()
        try:
            if s is second:
                second_pid.append(c.execute('SELECT pg_backend_pid() AS pid').fetchone()['pid'])
                second_pid_ready.set()
            result = service.update_purchase_request_status(
                c, s['actor'], {'id': s['pr'], 'company_id': s['company'], 'status': 'received'},
                'checked', '', '', _flags(s), '',
            )
            c.commit()
            results.append(result)
        except Exception as error:
            c.rollback()
            errors.append(error)
        finally:
            c.close()

    threads = [threading.Thread(target=worker, args=(first,), name='first-receipt'),
               threading.Thread(target=worker, args=(second,), name='second-receipt')]
    threads[0].start()
    try:
        assert first_read.wait(timeout=10)
        threads[1].start()
        assert second_pid_ready.wait(timeout=10)
        deadline = time.monotonic() + 10
        # Before the fix the second connection reads the same old balance.
        # After the fix PostgreSQL blocks it before that read. Either ordering
        # is released here; the assertion below always checks real final state.
        while not second_read.is_set():
            with _fresh() as observer:
                waiting = observer.execute(
                    'SELECT wait_event_type FROM pg_stat_activity WHERE pid=?',
                    (second_pid[0],),
                ).fetchone()
            if waiting and waiting['wait_event_type'] == 'Lock':
                break
            assert time.monotonic() < deadline, 'Second receipt neither read nor waited on a DB lock'
            second_read.wait(timeout=0.02)
    finally:
        release.set()
        for thread in threads:
            if thread.ident is not None:
                thread.join(timeout=20)
    assert not any(thread.is_alive() for thread in threads)
    assert not errors, errors
    assert len(results) == 2 and all(result['stock_entries'] == 1 for result in results)
    assert len(_pieces(first['company'], first['epi'])) == 2
    with _fresh() as c:
        assert c.execute(
            'SELECT quantity FROM unit_epi_stock WHERE company_id=? AND unit_id=? AND epi_id=?',
            (first['company'], first['unit'], first['epi']),
        ).fetchone()['quantity'] == 2
        movements = c.execute(
            'SELECT previous_stock, new_stock FROM stock_movements '
            'WHERE company_id=? ORDER BY previous_stock', (first['company'],),
        ).fetchall()
        assert [(r['previous_stock'], r['new_stock']) for r in movements] == [(0, 1), (1, 2)]


def test_multi_epi_receipts_in_reverse_line_order_do_not_deadlock(server):
    from core.database import get_connection
    from modules.purchases.service import update_purchase_request_status

    first = _seed()
    second = _second_request(first)
    with _fresh() as c:
        epi = c.execute(
            'INSERT INTO epis(company_id, unit_id, name, purchase_code, ca, sector, '
            'unit_measure, ca_expiry, epi_validity_date, manufacture_date, validity_days) '
            'VALUES (?,?,?,?,?,?,?,?,?,?,?)',
            (first['company'], first['unit'], 'Second EPI', uuid4().hex, 'CA-' + uuid4().hex, 'S', 'un',
             FUTURE, FUTURE, '', 0),
        ).lastrowid
        pri1 = _add_request_item(c, first, epi_id=epi)
        # The second request encounters the EPIs in the opposite ID order.
        c.execute('UPDATE purchase_request_items SET epi_id=? WHERE id=?', (epi, second['pri']))
        pri2 = _add_request_item(c, second)
        c.commit()
    barrier = threading.Barrier(2)
    errors = []

    def receive(s, extra):
        c = get_connection()
        try:
            barrier.wait(timeout=10)
            flags = _flags(s) + [{'id': extra, 'received': True, 'lots': [
                {'quantity': 1, 'manufacturer_validity_date': FUTURE, 'evidence': 'Label'},
            ]}]
            result = update_purchase_request_status(
                c, s['actor'], {'id': s['pr'], 'company_id': s['company'], 'status': 'received'},
                'checked', '', '', flags, '',
            )
            c.commit()
            assert result['stock_entries'] == 2
        except Exception as error:
            c.rollback()
            errors.append(error)
        finally:
            c.close()

    threads = [threading.Thread(target=receive, args=(first, pri1)),
               threading.Thread(target=receive, args=(second, pri2))]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=20)
    assert not any(thread.is_alive() for thread in threads)
    assert not errors, errors
    with _fresh() as c:
        rows = c.execute('SELECT quantity FROM unit_epi_stock WHERE company_id=?',
                         (first['company'],)).fetchall()
        assert len(rows) == 2 and all(row['quantity'] == 2 for row in rows)
    assert len(_pieces(first['company'], first['epi'])) == 2
    assert len(_pieces(first['company'], epi)) == 2


@pytest.mark.parametrize('iteration', range(3))
def test_receipt_racing_delivery_conserves_real_stock(server, iteration):
    from core.database import get_connection
    from core.security import create_jwt_token
    from test_est_v3_5_r1_postgres import seed, TODAY

    c = get_connection()
    try:
        stock = seed(c, ['valid'])
    finally:
        c.close()
    receipt = _second_request(stock)
    barrier = threading.Barrier(2)
    responses, errors = [], []

    def receive():
        try:
            barrier.wait(timeout=10)
            responses.append(_post(server, receipt, flags=_flags(receipt)))
        except Exception as error:
            errors.append(error)

    def deliver():
        try:
            barrier.wait(timeout=10)
            payload = {
                'actor_user_id': stock['actor']['id'], 'company_id': stock['company'],
                'unit_id': stock['unit'], 'employee_id': stock['employee'], 'epi_id': stock['epi'],
                'quantity': 1, 'stock_item_id': stock['items']['valid']['id'],
                'stock_qr_code': stock['items']['valid']['qr'], 'sector': 'QA', 'role_name': 'QA',
                'delivery_date': TODAY, 'next_replacement_date': FUTURE,
                'idempotency_key': f'postmerge-{iteration}-{uuid4().hex}',
            }
            request = Request(
                server + '/api/deliveries', data=json.dumps(payload).encode(),
                headers={'Authorization': 'Bearer ' + create_jwt_token(stock['actor']),
                         'Content-Type': 'application/json'}, method='POST',
            )
            with urlopen(request, timeout=15) as response:
                responses.append((response.status, json.loads(response.read())))
        except Exception as error:
            errors.append(error)

    threads = [threading.Thread(target=receive), threading.Thread(target=deliver)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=20)
    assert not any(thread.is_alive() for thread in threads)
    assert not errors, errors
    assert sorted(status for status, _ in responses) == [200, 201]
    with _fresh() as c:
        assert c.execute('SELECT quantity FROM unit_epi_stock WHERE company_id=? AND epi_id=?',
                         (stock['company'], stock['epi'])).fetchone()['quantity'] == 1
        rows = c.execute('SELECT status FROM epi_stock_items WHERE company_id=? AND epi_id=?',
                         (stock['company'], stock['epi'])).fetchall()
        assert sorted(row['status'] for row in rows) == ['delivered', 'in_stock']
