"""Vencimento automático, baixa da unidade e dados físicos via HTTP/JWT reais."""
import json
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import pytest
from test_est_v3_5_postmerge_receipt import server as _server_fixture
from test_est_v3_5_r3_lot_receipt_http import _enforce_jwt as _jwt_fixture
from test_est_v3_5_r3_lot_receipt_http import _fresh
from test_stock_lot_evidence_http import call, prove, unknown
from test_stock_manual_receipt_validity_http import FUTURE, available, post, seed

# Fixtures reutilizadas explicitamente; o pytest as descobre pelos nomes locais.
server = _server_fixture
_enforce_jwt = _jwt_fixture

pytestmark = pytest.mark.skipif(not os.environ.get('DATABASE_URL', '').startswith('postgres'), reason='Requires isolated PostgreSQL.')


def _pieces(company, epi):
    from epi_backend.db import row_to_dict
    with _fresh() as c:
        return [row_to_dict(r) for r in c.execute('SELECT * FROM epi_stock_items WHERE company_id=? AND epi_id=? ORDER BY id', (company, epi)).fetchall()]


def aged(server):
    s = seed()
    status, response = post(server, s)
    assert status == 201, response
    s['item'] = {**response['qr_labels'][0], 'id': response['qr_labels'][0]['stock_item_id']}
    with _fresh() as c:
        c.execute('UPDATE epi_stock_items SET physical_expiry_date=? WHERE id=?',
                  ((datetime.now(timezone.utc).date() - timedelta(days=1)).isoformat(), s['item']['id']))
        c.commit()
    return s


def disposition(server, s, **changes):
    body = {'company_id': s['company'], 'unit_id': s['unit'], 'stock_item_id': s['item']['id'],
            'qr_code': s['item']['qr_code_value'], 'action': 'donation',
            'recipient': 'Destinatário indicado pela unidade', 'recipient_reference': 'Contato conferido',
            'shipment_reference': 'Guia de envio TESTE-123', 'justification': 'Retirada de estoque vencido',
            'shipment_confirmed': True}
    body.update(changes)
    return call(server, s, '/api/stock/items/disposition', body)


def balance(s):
    with _fresh() as c:
        return c.execute('SELECT quantity FROM unit_epi_stock WHERE company_id=? AND unit_id=? AND epi_id=?',
                         (s['company'], s['unit'], s['epi'])).fetchone()['quantity']


def test_aging_blocks_delivery_and_is_visible_without_manual_block_or_read_writes(server):
    s = aged(server)
    before = _pieces(s['company'], s['epi'])
    status, blocked = call(server, s, '/api/stock/blocked-items')
    assert status == 200, blocked
    assert len(blocked['items']) == 1
    item = blocked['items'][0]
    assert item['id'] == s['item']['id'] and item['automatic_block']
    assert item['status'] == 'blocked_expired' and item['stored_status'] == 'in_stock'
    assert item['can_unblock'] is False
    assert len(available(s)) == 1 and balance(s) == 2
    assert _pieces(s['company'], s['epi']) == before
    status, overview = call(server, s, '/api/stock/validity-overview')
    assert status == 200 and overview['summary']['product_expired'] == 1


@pytest.mark.parametrize('action,terminal', [('donation', 'donated'), ('supplier_return', 'supplier_returned'), ('discard', 'discarded')])
def test_confirmed_unit_disposition_decrements_once_keeps_qr_and_audit(server, action, terminal):
    s = aged(server)
    status, response = disposition(server, s, action=action)
    assert status == 200, response
    assert response['status'] == terminal and balance(s) == 1
    assert disposition(server, s, action=action)[1]['idempotent'] is True
    assert balance(s) == 1
    status, blocked = call(server, s, '/api/stock/blocked-items')
    assert status == 200 and blocked['items'] == []
    status, history = call(server, s, '/api/stock/dispositions')
    assert status == 200 and len(history['items']) == 1
    assert history['items'][0]['recipient'] == 'Destinatário indicado pela unidade'
    assert history['items'][0]['action'] == action
    assert history['items'][0]['shipment_reference'] == 'Guia de envio TESTE-123'
    with _fresh() as c:
        item = c.execute('SELECT * FROM epi_stock_items WHERE id=?', (s['item']['id'],)).fetchone()
        assert item['qr_code_value'] == s['item']['qr_code_value'] and item['status'] == terminal
        events = c.execute("SELECT * FROM epi_stock_events WHERE company_id=? AND reason_code='unit_disposition'", (s['company'],)).fetchall()
        movements = c.execute("SELECT * FROM stock_movements WHERE company_id=? AND source_type='stock_disposition'", (s['company'],)).fetchall()
        assert len(events) == len(movements) == 1
        assert events[0]['actor_user_id'] == s['actor']['id'] and events[0]['origin_unit_id'] == s['unit']
        assert (movements[0]['previous_stock'], movements[0]['new_stock']) == (2, 1)
    assert disposition(server, s, recipient='Outro destinatário')[0] == 400


def test_parallel_disposition_does_not_double_decrement(server):
    s = aged(server)
    with ThreadPoolExecutor(max_workers=2) as pool:
        replies = list(pool.map(lambda _: disposition(server, s), range(2)))
    assert all(status == 200 for status, _ in replies), replies
    assert sorted(body['idempotent'] for _, body in replies) == [False, True]
    assert balance(s) == 1


def test_failure_in_audit_rolls_back_balance_item_and_movement(server):
    s = aged(server)
    with _fresh() as c:
        c.execute("CREATE OR REPLACE FUNCTION expiry_test_audit_failure() RETURNS trigger LANGUAGE plpgsql AS $$ "
                  "BEGIN IF NEW.reason_code='unit_disposition' THEN RAISE EXCEPTION 'falha injetada'; END IF; RETURN NEW; END $$")
        c.execute('CREATE TRIGGER expiry_test_audit_failure BEFORE INSERT ON epi_stock_events '
                  'FOR EACH ROW EXECUTE FUNCTION expiry_test_audit_failure()')
        c.commit()
    try:
        status, response = disposition(server, s)
        assert status == 500, response
        assert balance(s) == 2
        with _fresh() as c:
            assert c.execute('SELECT status FROM epi_stock_items WHERE id=?', (s['item']['id'],)).fetchone()['status'] == 'in_stock'
            assert c.execute("SELECT COUNT(*) AS n FROM stock_movements WHERE company_id=? AND source_type='stock_disposition'",
                             (s['company'],)).fetchone()['n'] == 0
    finally:
        with _fresh() as c:
            c.execute('DROP TRIGGER expiry_test_audit_failure ON epi_stock_events')
            c.execute('DROP FUNCTION expiry_test_audit_failure()')
            c.commit()


def test_expiry_day_itself_remains_available(server):
    s = aged(server)
    with _fresh() as c:
        from modules.stock.eligibility import validity_policy
        today = validity_policy(c, s['company'])['as_of_date']
        c.execute('UPDATE epi_stock_items SET physical_expiry_date=? WHERE id=?', (today, s['item']['id']))
        c.commit()
    status, blocked = call(server, s, '/api/stock/blocked-items')
    assert status == 200 and blocked['items'] == []
    assert len(available(s)) == 2
    assert disposition(server, s)[0] == 400


def test_metadata_correction_alone_never_releases_unknown_validity(server):
    s = unknown(server)
    selected = s['items'][0]
    with _fresh() as c:
        c.execute("UPDATE epi_stock_items SET manufacture_date='',physical_manufacture_date=NULL,size='N/A' WHERE id=?", (selected['stock_item_id'],))
        c.commit()
    body = {'stock_item_id': selected['stock_item_id'], 'qr_code': selected['qr_code'],
            'manufacture_date': '2025-01-21', 'size': '58', 'evidence': 'Etiqueta conferida',
            'justification': 'Conferência por QR', 'physical_confirmed': True}
    assert call(server, s, '/api/stock/items/physical-metadata', body)[0] == 200
    assert available(s) == []
    assert _pieces(s['company'], s['epi'])[0]['physical_expiry_date'] is None
    foreign = seed()
    assert call(server, foreign, '/api/stock/items/physical-metadata', body)[0] == 403


@pytest.mark.parametrize('changes', [{'shipment_confirmed': False}, {'recipient': ''}, {'justification': ''},
                                    {'shipment_reference': ''}, {'action': 'unknown'}, {'qr_code': 'OTHER'}])
def test_incomplete_destination_or_wrong_qr_does_not_remove_stock(server, changes):
    s = aged(server)
    status, _ = disposition(server, s, **changes)
    assert status in (400, 403)
    assert balance(s) == 2
    assert _pieces(s['company'], s['epi'])[0]['status'] == 'in_stock'


def test_scope_terminal_and_unblock_guards(server):
    s = aged(server)
    foreign = seed()
    foreign['item'] = s['item']
    assert disposition(server, foreign)[0] == 403
    with _fresh() as c:
        other_unit = c.execute("INSERT INTO units(company_id,name,unit_type,city) VALUES (?,?,?,?)",
                               (s['company'], 'Outra', 'base', 'T')).lastrowid
        c.commit()
    assert disposition(server, s, unit_id=other_unit)[0] == 403
    assert disposition(server, s)[0] == 200
    status, response = call(server, s, '/api/stock/items/status',
                            {'actor_user_id': s['actor']['id'], 'company_id': s['company'],
                             'unit_id': s['unit'], 'stock_item_id': s['item']['id'], 'new_status': 'in_stock'})
    assert status == 400, response
    assert balance(s) == 1


def test_regularization_propagates_manufacture_and_preserves_distinct_sizes(server):
    s = unknown(server)
    with _fresh() as c:
        c.execute("UPDATE epi_stock_items SET manufacture_date='',physical_manufacture_date=NULL WHERE id IN (?,?)",
                  (s['items'][0]['stock_item_id'], s['items'][1]['stock_item_id']))
        c.execute("UPDATE epi_stock_items SET size='G',glove_size='N/A' WHERE id=?", (s['items'][1]['stock_item_id'],))
        c.commit()
    status, response = prove(server, s, manufacture_date='2025-01-21')
    assert status == 200, response
    rows = _pieces(s['company'], s['epi'])
    assert [(str(i['physical_manufacture_date']), i['manufacture_date'], i['size']) for i in rows[:2]] == [
        ('2025-01-21', '2025-01-21', 'M'), ('2025-01-21', '2025-01-21', 'G')]
    assert rows[2]['lot_id'] is None
    assert prove(server, s, manufacture_date='2025-01-21')[1]['idempotent'] is True
    status, result = call(server, s, f"/api/stock/available-items?unit_id={s['unit']}&epi_id={s['epi']}")
    assert status == 200 and all(item['manufacture_date'] == '2025-01-21' for item in result['items'])


def test_missing_size_can_be_confirmed_per_qr_in_batch(server):
    s = unknown(server)
    with _fresh() as c:
        c.execute("UPDATE epi_stock_items SET manufacture_date='',physical_manufacture_date=NULL,size='N/A',glove_size='N/A',uniform_size='N/A' WHERE id IN (?,?)", (s['items'][0]['stock_item_id'], s['items'][1]['stock_item_id']))
        c.commit()
    selected = [{**s['items'][0], 'size': '58'}, {**s['items'][1], 'size': '60'}]
    status, result = prove(server, s, manufacture_date='2025-01-21', items=selected)
    assert status == 200, result
    assert [i['size'] for i in _pieces(s['company'], s['epi'])[:2]] == ['58', '60']


def test_size_confirmation_preserves_glove_and_uniform_categories(server):
    s = unknown(server)
    with _fresh() as c:
        c.execute("UPDATE epi_stock_items SET glove_size='9',size='9' WHERE id=?", (s['items'][0]['stock_item_id'],))
        c.execute("UPDATE epi_stock_items SET uniform_size='42',size='42' WHERE id=?", (s['items'][1]['stock_item_id'],))
        c.commit()
    selected = [{**s['items'][0], 'size': '9'}, {**s['items'][1], 'size': '42'}]
    status, response = prove(server, s, items=selected)
    assert status == 200, response
    rows = _pieces(s['company'], s['epi'])
    assert rows[0]['glove_size'] == '9' and rows[1]['uniform_size'] == '42'


def test_legacy_lot_date_and_exact_movement_size_are_recovered_without_catalog_inference(server):
    s = unknown(server)
    with _fresh() as c:
        c.execute("UPDATE epi_stock_items SET manufacture_date='',physical_manufacture_date=NULL WHERE id IN (?,?)",
                  (s['items'][0]['stock_item_id'], s['items'][1]['stock_item_id']))
        c.commit()
    assert prove(server, s, manufacture_date='2025-01-21')[0] == 200
    with _fresh() as c:
        c.execute("UPDATE epi_stock_items SET manufacture_date='',physical_manufacture_date=NULL,size='N/A' WHERE id=?", (s['items'][0]['stock_item_id'],))
        c.commit()
    status, listing = call(server, s, '/api/stock/incomplete-items')
    assert status == 200, listing
    found = next(i for i in listing['items'] if i['id'] == s['items'][0]['stock_item_id'])
    assert found['manufacture_date'] == '2025-01-21' and found['size'] == 'M'
    body = {'stock_item_id': found['id'], 'qr_code': found['qr_code_value'], 'manufacture_date': '2025-01-21',
            'size': '58', 'evidence': 'Etiqueta conferida', 'justification': 'Conferência por QR', 'physical_confirmed': True}
    status, result = call(server, s, '/api/stock/items/physical-metadata', body)
    assert status == 200, result
    assert call(server, s, '/api/stock/items/physical-metadata', body)[1]['idempotent'] is True
    assert balance(s) == 3
    row = _pieces(s['company'], s['epi'])[0]
    assert row['manufacture_date'] == '2025-01-21' and row['size'] == '58' and str(row['physical_expiry_date']) == FUTURE
    assert call(server, s, '/api/stock/items/physical-metadata', {**body, 'manufacture_date': '2025-01-22'})[0] == 400
    with _fresh() as c:
        event = c.execute("SELECT after_values FROM epi_stock_events WHERE company_id=? AND reason_code='physical_metadata'", (s['company'],)).fetchone()
        details = event['after_values']
        assert (json.loads(details) if isinstance(details, str) else details)['evidence'] == 'Etiqueta conferida'
