"""Prova física por seleção explícita: lote, anexo imutável e escopo via HTTP real."""
import base64
import hashlib
import json
import os
from concurrent.futures import ThreadPoolExecutor
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from uuid import uuid4

import pytest

from test_est_v3_5_postmerge_receipt import server as server
from test_est_v3_5_r3_lot_receipt_http import _fresh, _pieces
from test_stock_manual_receipt_validity_http import FUTURE, PAST, available, post as manual, seed

pytestmark = pytest.mark.skipif(
    not os.environ.get('DATABASE_URL', '').startswith('postgres'), reason='Requires isolated PostgreSQL.')
PNG = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII=')
FILE = {'filename': 'etiqueta.png', 'mime': 'image/png', 'content_base64': base64.b64encode(PNG).decode()}


def call(server, s, path, body=None):
    from core.security import create_jwt_token
    request = Request(server + path, data=json.dumps(body).encode() if body is not None else None,
                      headers={'Authorization': 'Bearer ' + create_jwt_token(s['actor']),
                               'Content-Type': 'application/json'})
    try:
        response = urlopen(request, timeout=15)
    except HTTPError as error:
        response = error
    with response:
        return response.status, json.load(response)


def unknown(server, role='admin', qty=3):
    s = seed(role)
    status, body = manual(server, s, quantity=qty, lot_code='', physical_expiry_date=None,
                          expiry_source=None, expiry_evidence=None)
    assert status == 201, body
    s['items'] = [{'stock_item_id': r['stock_item_id'], 'qr_code': r['qr_code_value']} for r in body['qr_labels']]
    return s


def prove(server, s, **changes):
    body = {'company_id': s['company'], 'unit_id': s['unit'], 'items': s['items'][:2],
            'lot_code': 'LOTE-REAL', 'physical_expiry_date': FUTURE, 'expiry_source': 'label',
            'evidence': 'Etiqueta conferida presencialmente', 'justification': 'Conferência do lote físico',
            'evidence_file': FILE, 'physical_lot_confirmed': True}
    body.update(changes)
    return call(server, s, '/api/stock/lots/regularize-validity', body)


def counts(s):
    with _fresh() as c:
        return tuple(c.execute(f'SELECT COUNT(*) AS n FROM {table} WHERE company_id=?',
                               (s['company'],)).fetchone()['n']
                     for table in ('epi_stock_lots', 'epi_stock_events'))


@pytest.mark.parametrize('role', ['admin', 'user'])
def test_selected_pieces_get_real_lot_and_one_retrievable_immutable_file(server, role):
    s = unknown(server, role)
    status, body = prove(server, s)
    assert status == 200, body
    assert body['count'] == 2 and len(available(s)) == 2
    rows = _pieces(s['company'], s['epi'])
    assert [r['physical_expiry_date'] for r in rows] == [FUTURE, FUTURE, None]
    assert [r['lot_code'] for r in rows] == ['LOTE-REAL', 'LOTE-REAL', '']
    assert counts(s) == (1, 3)  # dois eventos de peça, um único anexo por lote
    status, listing = call(server, s, '/api/stock/lots/evidence')
    assert status == 200 and listing['items'][0]['has_file'] is True
    assert listing['items'][0]['received_quantity'] == 2
    status, download = call(server, s, '/api/stock/lots/evidence?lot_id=' + str(body['lot_id']))
    assert status == 200
    assert base64.b64decode(download['file']['content_base64']) == PNG
    assert download['file']['sha256'] == hashlib.sha256(PNG).hexdigest()
    with _fresh() as c:
        assert c.execute('SELECT quantity FROM unit_epi_stock WHERE company_id=?',
                         (s['company'],)).fetchone()['quantity'] == 3
        linked = c.execute('SELECT lot_id FROM epi_stock_items WHERE company_id=? ORDER BY id',
                            (s['company'],)).fetchall()
        assert [r['lot_id'] for r in linked] == [body['lot_id'], body['lot_id'], None]
        with pytest.raises(Exception, match='imutável'):
            c.execute("UPDATE epi_stock_events SET justification='changed' WHERE lot_id=?", (body['lot_id'],))
        c.rollback()


def test_receipt_upload_is_stored_once_for_all_new_pieces(server):
    s = seed()
    status, body = manual(server, s, quantity=5, evidence_file=FILE)
    assert status == 201, body
    lot_ids = {r['lot_id'] for r in body['qr_labels']}
    assert len(lot_ids) == 1 and None not in lot_ids
    assert counts(s) == (1, 6)  # cinco snapshots de peça, um arquivo
    status, download = call(server, s, '/api/stock/lots/evidence?lot_id=' + str(lot_ids.pop()))
    assert status == 200 and download['file']['content_base64'] == FILE['content_base64']


def test_expired_evidence_does_not_release_pieces(server):
    s = unknown(server)
    status, body = prove(server, s, physical_expiry_date=PAST)
    assert status == 200, body
    assert available(s) == []
    assert [r['status'] for r in _pieces(s['company'], s['epi'])] == ['blocked_expired', 'blocked_expired', 'in_stock']


@pytest.mark.parametrize('changes', [
    {'evidence_file': None}, {'evidence_file': {**FILE, 'mime': 'text/html'}},
    {'evidence_file': {**FILE, 'mime': ['image/png']}},
    {'evidence_file': {**FILE, 'filename': 'etiqueta.html'}},
    {'evidence_file': {**FILE, 'filename': '../etiqueta.png'}},
    {'evidence_file': {**FILE, 'content_base64': 'broken!'}},
    {'evidence_file': {**FILE, 'content_base64': base64.b64encode(b'not a PNG').decode()}},
    {'evidence_file': {**FILE, 'content_base64': 'A' * (4 * 1024 * 1024 + 4)}},
    {'physical_lot_confirmed': False}, {'lot_code': ''}, {'expiry_source': 'catalog'},
    {'physical_expiry_date': ''}, {'evidence': ''}, {'justification': ''},
])
def test_invalid_or_unconfirmed_proof_has_no_partial_effect(server, changes):
    s = unknown(server)
    status, body = prove(server, s, **changes)
    assert status == 400, body
    assert counts(s) == (0, 0)
    assert all(r['physical_expiry_date'] is None for r in _pieces(s['company'], s['epi']))


@pytest.mark.parametrize('violation', ['qr', 'duplicate', 'other_epi', 'other_unit', 'other_company', 'existing_lot', 'delivered'])
def test_piece_selection_must_match_physical_scope_and_lot(server, violation):
    s = unknown(server)
    selection = [dict(r) for r in s['items'][:2]]
    if violation == 'qr':
        selection[1]['qr_code'] = 'WRONG'
    elif violation == 'duplicate':
        selection[1] = selection[0]
    elif violation in ('other_epi', 'other_unit', 'other_company'):
        foreign = unknown(server)
        selection[1] = foreign['items'][0]
        if violation != 'other_company':
            with _fresh() as c:
                # Cria outra unidade/EPI NA MESMA empresa com os próprios
                # recursos, sem violar FKs nem transferir peça entre tenants.
                if violation == 'other_unit':
                    unit = c.execute('INSERT INTO units(company_id,name,unit_type,city) VALUES (?,?,?,?)',
                                     (s['company'], 'Outra', 'base', 'T')).lastrowid
                    c.execute('UPDATE epi_stock_items SET unit_id=? WHERE id=?',
                               (unit, s['items'][1]['stock_item_id']))
                else:
                    epi = c.execute('INSERT INTO epis(company_id,name,purchase_code,ca,sector,unit_measure,ca_expiry,'
                                    'epi_validity_date,manufacture_date,validity_days) VALUES (?,?,?,?,?,?,?,?,?,?)',
                                    (s['company'], 'Outro', 'OTHER-' + str(s['epi']), 'OTHER', 'S', 'un',
                                     FUTURE, FUTURE, '2020-01-01', 0)).lastrowid
                    c.execute('UPDATE epi_stock_items SET epi_id=? WHERE id=?',
                               (epi, s['items'][1]['stock_item_id']))
                c.commit()
            selection = s['items'][:2]
    else:
        with _fresh() as c:
            if violation == 'existing_lot':
                c.execute("UPDATE epi_stock_items SET lot_code='OUTRO-LOTE' WHERE id=?", (s['items'][1]['stock_item_id'],))
            else:
                c.execute("UPDATE epi_stock_items SET status='delivered' WHERE id=?", (s['items'][1]['stock_item_id'],))
            c.commit()
    status, body = prove(server, s, items=selection)
    assert status in (400, 403), body
    assert counts(s) == (0, 0)


def test_repeat_and_parallel_requests_do_not_duplicate_lot_or_file(server):
    s = unknown(server)
    with ThreadPoolExecutor(max_workers=2) as workers:
        replies = list(workers.map(lambda _: prove(server, s), range(2)))
    assert all(status == 200 for status, _body in replies), replies
    assert sorted(body['idempotent'] for _status, body in replies) == [False, True]
    assert counts(s) == (1, 3)
    assert prove(server, s)[1]['idempotent'] is True
    assert counts(s) == (1, 3)


def test_late_validation_failure_rolls_back_lot_first_piece_and_file(server):
    s = unknown(server)
    with _fresh() as c:
        c.execute("UPDATE epi_stock_items SET physical_manufacture_date='9999-12-31' WHERE id=?",
                   (s['items'][1]['stock_item_id'],))
        c.commit()
    status, body = prove(server, s)
    assert status == 400, body
    assert counts(s) == (0, 0)
    assert available(s) == []
    assert all(r['physical_expiry_date'] is None for r in _pieces(s['company'], s['epi']))


def test_file_and_listing_are_isolated_between_companies_and_units(server):
    s, foreign = unknown(server), unknown(server)
    status, body = prove(server, s)
    assert status == 200
    path = '/api/stock/lots/evidence?lot_id=' + str(body['lot_id'])
    assert call(server, foreign, path)[0] == 403
    assert call(server, foreign, '/api/stock/lots/evidence')[1]['items'] == []
    with _fresh() as c:
        unit = c.execute('INSERT INTO units(company_id,name,unit_type,city) VALUES (?,?,?,?)',
                         (s['company'], 'Nova', 'base', 'T')).lastrowid
        c.execute('UPDATE employees SET unit_id=? WHERE id=(SELECT linked_employee_id FROM users WHERE id=?)',
                   (unit, s['actor']['id']))
        c.commit()
    assert call(server, s, path)[0] == 403
    assert call(server, s, '/api/stock/lots/evidence')[1]['items'] == []


@pytest.mark.parametrize('role', ['general_admin', 'buyer', 'employee', 'master_admin'])
def test_non_operational_roles_cannot_register_lot_evidence(server, role):
    s = unknown(server)
    actor = seed(role)['actor']
    s['actor'] = actor
    assert prove(server, s)[0] == 403


def untracked(quantity=5):
    from modules.stock.service import upsert_unit_stock
    s = seed()
    with _fresh() as c:
        upsert_unit_stock(c, s['company'], s['unit'], s['epi'], quantity)
        c.commit()
    s['key'] = uuid4().hex
    return s


def reconcile(server, s, **changes):
    body = {'company_id': s['company'], 'unit_id': s['unit'], 'epi_id': s['epi'],
            'quantity': 2, 'size': 'M', 'lot_code': 'CONCILIADO',
            'physical_expiry_date': FUTURE, 'expiry_source': 'label', 'evidence': 'Etiqueta conferida',
            'evidence_file': FILE, 'justification': 'Peças contadas sem QR no saldo existente',
            'physical_lot_confirmed': True, 'idempotency_key': s['key']}
    body.update(changes)
    return call(server, s, '/api/stock/lots/reconcile', body)


def aggregate(s):
    with _fresh() as c:
        return c.execute('SELECT quantity FROM unit_epi_stock WHERE company_id=? AND unit_id=? AND epi_id=?',
                          (s['company'], s['unit'], s['epi'])).fetchone()['quantity']


def test_reconciliation_creates_backing_qrs_without_adding_stock_and_is_idempotent(server):
    s = untracked()
    status, body = reconcile(server, s)
    assert status == 200, body
    assert aggregate(s) == 5
    assert len(_pieces(s['company'], s['epi'])) == 2 and len(available(s)) == 2
    assert len({r['qr_code_value'] for r in body['qr_labels']}) == 2
    assert counts(s) == (1, 3)
    status, replay = reconcile(server, s)
    assert status == 200 and replay['idempotent'] is True
    assert replay['qr_labels'] == body['qr_labels']
    assert counts(s) == (1, 3) and aggregate(s) == 5
    assert reconcile(server, s, size='G')[0] == 400
    assert counts(s) == (1, 3)


@pytest.mark.parametrize('changes', [
    {'quantity': 6}, {'quantity': 0}, {'quantity': 1.5}, {'size': ''},
    {'evidence_file': None}, {'physical_lot_confirmed': False}, {'idempotency_key': ''},
])
def test_reconciliation_requires_real_count_proof_and_remaining_deficit(server, changes):
    s = untracked()
    status, body = reconcile(server, s, **changes)
    assert status == 400, body
    assert aggregate(s) == 5 and counts(s) == (0, 0)
    assert _pieces(s['company'], s['epi']) == []


def test_reconciliation_counts_blocked_and_unknown_backing_as_existing_pieces(server):
    from modules.stock.service import upsert_unit_stock
    s = unknown(server)
    s['key'] = uuid4().hex
    with _fresh() as c:
        c.execute("UPDATE epi_stock_items SET status='blocked_expired' WHERE company_id=?", (s['company'],))
        upsert_unit_stock(c, s['company'], s['unit'], s['epi'], 5)
        c.commit()
    assert reconcile(server, s, quantity=3)[0] == 400
    assert aggregate(s) == 5 and len(_pieces(s['company'], s['epi'])) == 3


def test_reconciliation_of_expired_lot_does_not_make_it_available(server):
    s = untracked()
    assert reconcile(server, s, physical_expiry_date=PAST)[0] == 200
    assert available(s) == [] and aggregate(s) == 5
    assert all(r['status'] == 'blocked_expired' for r in _pieces(s['company'], s['epi']))


def test_parallel_reconciliations_cannot_overrun_untracked_stock(server):
    s = untracked()
    with ThreadPoolExecutor(max_workers=2) as workers:
        replies = list(workers.map(lambda key: reconcile(server, s, quantity=3, idempotency_key=key),
                                   [uuid4().hex, uuid4().hex]))
    assert sorted(status for status, _body in replies) == [200, 400], replies
    assert aggregate(s) == 5 and len(_pieces(s['company'], s['epi'])) == 3
    assert counts(s) == (1, 4)


@pytest.mark.parametrize('scope', ['company_id', 'unit_id', 'epi_id'])
def test_reconciliation_rejects_other_scope(server, scope):
    s, other = untracked(), untracked()
    status, body = reconcile(server, s, **{scope: other[scope.replace('_id', '')]})
    assert status in (400, 403), body
    assert counts(s) == (0, 0) and aggregate(s) == 5


def test_reconciliation_audit_failure_rolls_back_pieces_and_lot(server, monkeypatch):
    import modules.stock.service as service
    s = untracked()

    def fail(*args, **kwargs):
        raise RuntimeError('Falha controlada no histórico')

    monkeypatch.setattr(service, '_append_stock_event', fail)
    assert reconcile(server, s)[0] == 500
    assert counts(s) == (0, 0) and aggregate(s) == 5
    assert _pieces(s['company'], s['epi']) == []
