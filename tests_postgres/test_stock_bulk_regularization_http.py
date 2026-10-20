"""Regularização multilote: prova própria, atomicidade e RBAC por HTTP/JWT real."""
import base64
import os
from concurrent.futures import ThreadPoolExecutor

import pytest
from test_est_v3_5_r3_lot_receipt_http import _fresh, _pieces
from test_stock_lot_evidence_http import FILE, FUTURE, PAST, PNG, call, counts, unknown
from test_stock_lot_evidence_http import (
    server as server,  # noqa: PLC0414 - fixture pytest exportada
)
from test_stock_manual_receipt_validity_http import available, seed
from test_stock_manual_receipt_validity_http import post as manual

pytestmark = pytest.mark.skipif(not os.environ.get('DATABASE_URL', '').startswith('postgres'), reason='Requires isolated PostgreSQL.')

ENDPOINT = '/api/stock/lots/regularize-validity'


def lots(s):
    return [{'items': s['items'][index:index + 2], 'lot_code': f'REAL-{index}',
             'physical_expiry_date': expiry, 'expiry_source': source,
             'evidence': f'Comprovação do lote {index}', 'justification': f'Conferência {index}',
             'evidence_file': {**FILE, 'filename': f'lote-{index}.png'}, 'physical_lot_confirmed': True}
            for index, expiry, source in [(0, FUTURE, 'label'), (2, PAST, 'manufacturer_document')]]


def submit(server, s, selected):
    return call(server, s, ENDPOINT, {'company_id': s['company'], 'unit_id': s['unit'], 'lots': selected})


@pytest.mark.parametrize('role', ['admin', 'user'])
def test_one_submission_preserves_separate_expiry_evidence_and_expired_gate(server, role):
    s = unknown(server, role, qty=5)
    status, body = submit(server, s, lots(s))
    assert status == 200, body
    assert body['count'] == 4 and len(body['lots']) == 2
    assert counts(s) == (2, 6) and len(available(s)) == 2
    rows = _pieces(s['company'], s['epi'])
    assert [r['physical_expiry_date'] for r in rows] == [FUTURE, FUTURE, PAST, PAST, None]
    assert [r['lot_code'] for r in rows] == ['REAL-0', 'REAL-0', 'REAL-2', 'REAL-2', '']
    for index, lot in enumerate(body['lots']):
        status, download = call(server, s, '/api/stock/lots/evidence?lot_id=' + str(lot['lot_id']))
        assert status == 200 and download['file']['filename'] == f'lote-{index * 2}.png'
        assert base64.b64decode(download['file']['content_base64']) == PNG
    with _fresh() as c:
        assert c.execute('SELECT quantity FROM unit_epi_stock WHERE company_id=?', (s['company'],)).fetchone()['quantity'] == 5


@pytest.mark.parametrize('invalid', ['date', 'evidence', 'file', 'confirmation', 'qr', 'company', 'unit', 'duplicate', 'late_manufacture', 'invalid_company', 'invalid_unit'])
def test_bad_second_lot_rolls_back_every_lot_and_file(server, invalid):
    s = unknown(server, qty=4)
    selected = lots(s)
    if invalid == 'date':
        selected[1]['physical_expiry_date'] = ''
    elif invalid == 'evidence':
        selected[1]['evidence'] = ''
    elif invalid == 'file':
        selected[1]['evidence_file'] = None
    elif invalid == 'confirmation':
        selected[1]['physical_lot_confirmed'] = False
    elif invalid == 'qr':
        selected[1]['items'][1]['qr_code'] = 'WRONG'
    elif invalid in ('company', 'unit'):
        selected[1][invalid + '_id'] = s[invalid] + 10000
    elif invalid.startswith('invalid_'):
        selected[1][invalid.removeprefix('invalid_') + '_id'] = {'invalid': True}
    elif invalid == 'duplicate':
        selected[1]['items'][0] = selected[0]['items'][0]
    else:
        with _fresh() as c:
            c.execute("UPDATE epi_stock_items SET physical_manufacture_date='9999-12-31' WHERE id=?",
                      (s['items'][-1]['stock_item_id'],))
            c.commit()
    status, body = submit(server, s, selected)
    assert status in (400, 403), body
    assert counts(s) == (0, 0) and available(s) == []
    assert all(r['physical_expiry_date'] is None for r in _pieces(s['company'], s['epi']))
    with _fresh() as c:
        assert all(r['lot_id'] is None for r in c.execute('SELECT lot_id FROM epi_stock_items WHERE company_id=?', (s['company'],)).fetchall())


@pytest.mark.parametrize('selected', [None, [], [{}] * 11, [None], [{'items': []}]])
def test_invalid_batch_shape_has_no_writes(server, selected):
    s = unknown(server)
    status, body = submit(server, s, selected)
    assert status == 400, body
    assert counts(s) == (0, 0)


def test_attachment_total_limit_is_enforced_before_writes(server):
    s = unknown(server, qty=5)
    file = {**FILE, 'content_base64': base64.b64encode(PNG + b'\0' * (3 * 1024 * 1024 - len(PNG))).decode()}
    selected = [{**lots(s)[0], 'items': [item], 'lot_code': f'L-{i}', 'evidence_file': file}
                for i, item in enumerate(s['items'])]
    status, body = submit(server, s, selected)
    assert status == 400 and '12 MiB' in str(body), body
    assert counts(s) == (0, 0)


@pytest.mark.parametrize('role', ['general_admin', 'buyer', 'employee', 'master_admin'])
def test_non_operational_roles_cannot_submit_multiple_lots(server, role):
    s = unknown(server, qty=4)
    actor = seed(role)['actor']
    status, body = submit(server, {**s, 'actor': actor}, lots(s))
    assert status == 403, body
    assert counts(s) == (0, 0)


def test_other_tenant_piece_never_changes_in_atomic_submission(server):
    s = unknown(server, qty=4)
    foreign = unknown(server)
    selected = lots(s)
    selected[1]['items'] = foreign['items'][:2]
    status, body = submit(server, s, selected)
    assert status == 403, body
    assert counts(s) == counts(foreign) == (0, 0)


def test_two_ep_is_and_opposite_request_order_are_idempotent_without_deadlock(server):
    s = unknown(server, qty=2)
    with _fresh() as c:
        other_epi = c.execute('INSERT INTO epis(company_id,name,purchase_code,ca,sector,unit_measure,ca_expiry,'
                              'epi_validity_date,manufacture_date,validity_days) VALUES (?,?,?,?,?,?,?,?,?,?)',
                              (s['company'], 'Outro EPI', 'OTHER-' + str(s['epi']), 'OTHER', 'S', 'un',
                               FUTURE, FUTURE, '2020-01-01', 0)).lastrowid
        c.commit()
    status, receipt = manual(server, {**s, 'epi': other_epi}, quantity=2, lot_code='', physical_expiry_date=None,
                             expiry_source=None, expiry_evidence=None)
    assert status == 201, receipt
    other_items = [{'stock_item_id': r['stock_item_id'], 'qr_code': r['qr_code_value']} for r in receipt['qr_labels']]
    s['items'] += other_items
    selected = lots(s)
    with ThreadPoolExecutor(max_workers=2) as pool:
        replies = list(pool.map(lambda order: submit(server, s, order), [selected, selected[::-1]]))
    assert all(status == 200 for status, body in replies), replies
    assert sorted(body['idempotent'] for status, body in replies) == [False, True]
    assert counts(s) == (2, 6)
    assert submit(server, s, selected)[1]['idempotent'] is True
    assert counts(s) == (2, 6)


def test_full_lot_above_old_100_piece_limit_and_total_500_piece_limit(server):
    s = unknown(server, qty=101)
    selected = [{**lots(s)[0], 'items': s['items']}]
    status, body = submit(server, s, selected)
    assert status == 200 and body['count'] == 101, body
    assert len(available(s)) == 101
    s2 = unknown(server, qty=1)
    selected = [{**lots(s2)[0], 'items': [{'stock_item_id': i, 'qr_code': f'Q-{i}'} for i in range(1, 502)]}]
    status, body = submit(server, s2, selected)
    assert status == 400 and '500' in str(body), body
    assert counts(s2) == (0, 0)


def test_pending_api_exposes_stable_group_identity_without_inventing_lot(server):
    s = unknown(server)
    status, body = call(server, s, '/api/stock/pending-regularization')
    assert status == 200, body
    rows = body['items']
    assert len(rows) == 3 and {r['lot_id'] for r in rows} == {None}
    assert len({r['stock_movement_id'] for r in rows}) == 1
    assert rows[0]['stock_movement_id'] and rows[0]['received_at']
    assert {r['lot_code'] for r in rows} == {''}
