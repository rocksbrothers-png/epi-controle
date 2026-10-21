"""Conferência de PR e PO materializa foto/datas de lote via HTTP/JWT real."""
import base64
import os
from concurrent.futures import ThreadPoolExecutor

import pytest
from test_est_v3_5_r3_lot_receipt_http import FUTURE, _eligible, _fresh
from test_stock_lot_evidence_http import FILE, PNG, call
from test_stock_lot_evidence_http import (
    server as server,  # noqa: PLC0414 - fixture pytest exportada
)
from test_stock_manual_receipt_validity_http import seed

pytestmark = pytest.mark.skipif(not os.environ.get('DATABASE_URL', '').startswith('postgres'), reason='Requires isolated PostgreSQL.')


def setup_receipt(kind, quantity=4):
    s = seed()
    with _fresh() as c:
        c.execute('UPDATE purchase_request_items SET quantity_requested=? WHERE id=?', (quantity, s['pri']))
        if kind == 'po':
            s['po'] = c.execute('INSERT INTO purchase_orders(company_id,unit_id,status,po_number,'
                'created_by_user_id,created_by_name,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?)',
                (s['company'], s['unit'], 'received', 'CAPTURE-' + str(s['pr']), s['actor']['id'], 'A', '2024-01-01', '2024-01-01')).lastrowid
            s['poi'] = c.execute('INSERT INTO purchase_order_items(purchase_order_id,company_id,unit_id,epi_id,epi_name,'
                'quantity,quantity_received,status,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?)',
                (s['po'], s['company'], s['unit'], s['epi'], 'EPI', quantity, quantity, 'received', '2024-01-01', '2024-01-01')).lastrowid
        c.commit()
    s['kind'] = kind
    return s


def proof(**changes):
    value = {'capture_version': 1, 'quantity': 2, 'lot_code': 'A', 'manufacture_date': '2024-01-02',
             'manufacturer_validity_date': FUTURE, 'expiry_source': 'label', 'evidence': 'Etiqueta conferida do lote A',
             'evidence_file': FILE, 'physical_lot_confirmed': True}
    value.update(changes)
    return value


def submit(server, s, lots=None):
    lots = lots if lots is not None else [proof(), proof(lot_code='B', manufacture_date='2023-01-02',
        manufacturer_validity_date='2024-01-01', expiry_source='manufacturer_document', evidence='Documento B',
        evidence_file={**FILE, 'filename': 'fabricante-B.png'})]
    flags = [{'id': s['poi'] if s['kind'] == 'po' else s['pri'], 'received': True, 'lots': lots}]
    if s['kind'] == 'po':
        return call(server, s, f"/api/purchase-orders/{s['po']}/receive", {'actor_user_id': s['actor']['id'], 'action': 'checked', 'items': flags})
    return call(server, s, f"/api/purchase-requests/{s['pr']}/status", {'actor_user_id': s['actor']['id'], 'status': 'checked', 'received_items': flags})


def rows(s):
    with _fresh() as c:
        return [dict(r) for r in c.execute('SELECT * FROM epi_stock_items WHERE company_id=? ORDER BY id', (s['company'],)).fetchall()]


def count(s, table):
    with _fresh() as c:
        return c.execute(f'SELECT COUNT(*) AS n FROM {table} WHERE company_id=?', (s['company'],)).fetchone()['n']


@pytest.mark.parametrize('kind', ['pr', 'po'])
def test_conference_saves_each_batch_and_file_once_and_carries_manufacture_to_stock(server, kind):
    s = setup_receipt(kind)
    status, result = submit(server, s)
    assert status == 200, result
    assert result.get('stock_entries', result.get('stock_units')) == 4
    pieces = rows(s)
    assert len(pieces) == 4
    assert [str(r['physical_manufacture_date']) for r in pieces] == ['2024-01-02'] * 2 + ['2023-01-02'] * 2
    assert [r['manufacture_date'] for r in pieces] == ['2024-01-02'] * 2 + ['2023-01-02'] * 2
    assert [str(r['physical_expiry_date']) for r in pieces] == [FUTURE] * 2 + ['2024-01-01'] * 2
    assert len({r['lot_id'] for r in pieces}) == 2 and all(r['lot_id'] for r in pieces)
    assert [r['status'] for r in pieces] == ['in_stock'] * 2 + ['blocked_expired'] * 2
    assert _eligible(s['company'], s['unit'], s['epi']) == 2
    if kind == 'pr':
        assert [r['manufacture_date'] for r in result['qr_labels']] == ['2024-01-02'] * 2 + ['2023-01-02'] * 2
    with _fresh() as c:
        files = c.execute("SELECT lot_id FROM epi_stock_events WHERE company_id=? AND reason_code='lot_evidence'", (s['company'],)).fetchall()
        assert len(files) == 2
        assert c.execute('SELECT quantity FROM unit_epi_stock WHERE company_id=?', (s['company'],)).fetchone()['quantity'] == 4
        assert str(c.execute('SELECT manufacture_date FROM epis WHERE id=?', (s['epi'],)).fetchone()['manufacture_date']) == '2020-01-01'
    status, listing = call(server, s, '/api/stock/lots/evidence')
    assert status == 200 and {r['manufacture_date'] for r in listing['items']} == {'2024-01-02', '2023-01-02'}
    for row in files:
        status, attachment = call(server, s, '/api/stock/lots/evidence?lot_id=' + str(row['lot_id']))
        assert status == 200 and base64.b64decode(attachment['file']['content_base64']) == PNG
    assert submit(server, s)[0] == 200
    assert len(rows(s)) == 4 and count(s, 'epi_stock_lots') == 2


@pytest.mark.parametrize('kind', ['pr', 'po'])
def test_manufacture_only_preserves_photo_without_inventing_expiry_or_releasing_stock(server, kind):
    s = setup_receipt(kind, 2)
    status, result = submit(server, s, [proof(manufacturer_validity_date='')])
    assert status == 200, result
    assert all(str(r['physical_manufacture_date']) == '2024-01-02' and r['physical_expiry_date'] is None for r in rows(s))
    assert _eligible(s['company'], s['unit'], s['epi']) == 0 and count(s, 'epi_stock_lots') == 1
    status, pending = call(server, s, '/api/stock/pending-regularization')
    assert status == 200 and pending['count'] == 2
    assert all(r['lot_id'] for r in pending['items'])


@pytest.mark.parametrize('kind', ['pr', 'po'])
@pytest.mark.parametrize('bad', ['file', 'confirm', 'future_manufacture', 'expiry_before_manufacture', 'sum'])
def test_bad_second_batch_rolls_back_receipt_stock_dates_lots_and_files(server, kind, bad):
    s = setup_receipt(kind)
    lots = [proof(), proof(lot_code='B')]
    if bad == 'file':
        lots[1]['evidence_file'] = None
    elif bad == 'confirm':
        lots[1]['physical_lot_confirmed'] = False
    elif bad == 'future_manufacture':
        lots[1]['manufacture_date'] = '2099-01-01'
    elif bad == 'sum':
        lots[1]['quantity'] = 1
    else:
        lots[1]['manufacturer_validity_date'] = '2023-01-01'
    status, result = submit(server, s, lots)
    assert status == 400, result
    for table in ['epi_stock_items', 'epi_stock_lots', 'epi_stock_events', 'stock_movements', 'unit_epi_stock']:
        assert count(s, table) == 0


@pytest.mark.parametrize('kind', ['pr', 'po'])
def test_concurrent_conference_retries_create_one_receipt_and_one_file(server, kind):
    s = setup_receipt(kind, 2)
    with ThreadPoolExecutor(max_workers=2) as pool:
        replies = list(pool.map(lambda _: submit(server, s, [proof()]), range(2)))
    assert all(status == 200 for status, result in replies), replies
    assert len(rows(s)) == 2 and count(s, 'stock_movements') == 1 and count(s, 'epi_stock_lots') == 1


def test_ocr_endpoint_requires_auth_and_returns_distinct_dates_without_saving_stock(server, monkeypatch):
    import epi_backend.lot_label_ocr as ocr
    monkeypatch.setattr(ocr, 'detect_lot_label_dates', lambda image: ocr.extract_lot_dates('FAB 02/01/2024 VAL 02/01/2032'))
    s = setup_receipt('pr')
    status, body = call(server, s, '/api/purchases/lot-label-ocr', {'actor_user_id': s['actor']['id'], 'evidence_file': FILE})
    assert status == 200 and body['manufacture_date'] == '2024-01-02' and body['physical_expiry_date'] == '2032-01-02'
    assert count(s, 'epi_stock_items') == count(s, 'epi_stock_lots') == 0
    foreign = seed('employee')
    status, _ = call(server, foreign, '/api/purchases/lot-label-ocr', {'actor_user_id': foreign['actor']['id'], 'evidence_file': FILE})
    assert status == 403


@pytest.mark.parametrize('first', ['pr', 'po'])
def test_linked_pr_and_po_cannot_launch_the_same_receipt_twice(server, first):
    s = setup_receipt('po', 2)
    with _fresh() as c:
        c.execute('UPDATE purchase_orders SET purchase_request_id=? WHERE id=?', (s['pr'], s['po']))
        c.execute('UPDATE purchase_order_items SET purchase_request_item_id=? WHERE id=?', (s['pri'], s['poi']))
        c.commit()
    a = {**s, 'kind': first}
    status, result = submit(server, a, [proof()])
    assert status == 200, result
    b = {**s, 'kind': 'po' if first == 'pr' else 'pr'}
    status, result = submit(server, b, [proof()])
    assert status == 400, result
    assert len(rows(s)) == 2 and count(s, 'stock_movements') == 1


def test_file_audit_failure_rolls_back_conference_and_physical_lot(server, monkeypatch):
    import modules.purchases.receipt_capture as capture
    s = setup_receipt('pr', 2)
    def fail(*args, **kwargs):
        raise ValueError('Audit intentionally refused in isolated fixture')
    monkeypatch.setattr(capture, 'save_lot_file', fail)
    status, result = submit(server, s, [proof()])
    assert status == 400, result
    for table in ['epi_stock_items', 'epi_stock_lots', 'epi_stock_events', 'stock_movements', 'unit_epi_stock']:
        assert count(s, table) == 0


def test_pr_and_linked_po_concurrently_launch_only_one_physical_receipt(server):
    s = setup_receipt('po', 2)
    with _fresh() as c:
        c.execute('UPDATE purchase_orders SET purchase_request_id=? WHERE id=?', (s['pr'], s['po']))
        c.execute('UPDATE purchase_order_items SET purchase_request_item_id=? WHERE id=?', (s['pri'], s['poi']))
        c.commit()
    with ThreadPoolExecutor(max_workers=2) as pool:
        replies = list(pool.map(lambda kind: submit(server, {**s, 'kind': kind}, [proof()]), ['pr', 'po']))
    assert sorted(status for status, result in replies) == [200, 400], replies
    assert len(rows(s)) == 2 and count(s, 'stock_movements') == 1
