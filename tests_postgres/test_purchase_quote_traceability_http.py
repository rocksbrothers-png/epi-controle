"""Linhas assinadas da cotação via HTTP/JWT real em PostgreSQL isolado.

Parse → salvar preços → PO: a linha só vale na requisição em que foi
visualizada, a PO nasce na Unidade da requisição e o histórico registra a
associação confirmada.
"""
import base64
import os

import pytest
from test_est_v3_5_r3_lot_receipt_http import _fresh
from test_stock_lot_evidence_http import call
from test_stock_lot_evidence_http import (
    server as server,  # noqa: PLC0414 - fixture pytest exportada
)
from test_stock_manual_receipt_validity_http import seed

pytestmark = pytest.mark.skipif(not os.environ.get('DATABASE_URL', '').startswith('postgres'), reason='Requires isolated PostgreSQL.')

STAMP = '2026-10-25T10:00:00+00:00'
CSV = 'linha,epi,ca,fabricante,fornecedor,qtd,valor_unitario\n1,Luva Nitrilica,12345,Danny,Fornecedor Real,3,10.00\n'


def _request(s, *, unit=None):
    """Requisição em cotação com um item do EPI do seed (CA 12345)."""
    with _fresh() as c:
        c.execute("UPDATE epis SET name='Luva Nitrilica', ca='12345' WHERE id=?", (s['epi'],))
        pr = c.execute("INSERT INTO purchase_requests (company_id, unit_id, status, title, created_by_user_id, "
                       "created_by_name, created_at, updated_at) VALUES (?,?,'sent_to_buyer','Req',?,?,?,?)",
                       (s['company'], unit or s['unit'], s['actor']['id'], 'Ator', STAMP, STAMP)).lastrowid
        pri = c.execute("INSERT INTO purchase_request_items (purchase_request_id, company_id, unit_id, epi_id, epi_name, "
                        "ca, quantity_requested, status, created_at, updated_at) VALUES (?,?,?,?,?,?,?,'open',?,?)",
                        (pr, s['company'], unit or s['unit'], s['epi'], 'Luva Nitrilica', '12345', 3, STAMP, STAMP)).lastrowid
        c.commit()
    return pr, pri


def _parse(server, s, pr):
    body = {'actor_user_id': s['actor']['id'], 'filename': 'cotacao.csv',
            'content_base64': base64.b64encode(CSV.encode()).decode()}
    if pr is not None:
        body['purchase_request_id'] = pr
    return call(server, s, '/api/purchase-quote-file/parse', body)


def _association(row, item_id):
    return {'item_id': item_id, 'unit_price': 10.0, 'quantity': 3, 'confirmed': True, 'expected_updated_at': STAMP,
            'quote_line': row.get('line', ''), 'quote_item_id': row.get('item_id', ''), 'quote_epi': row.get('epi', ''),
            'quote_ca': row.get('ca', ''), 'quote_manufacturer': row.get('fabricante', ''),
            'quote_model': row.get('modelo', ''), 'quote_supplier': row.get('fornecedor', ''),
            'quote_size': row.get('tamanho', ''), 'quote_glove_size': row.get('tamanho_luva', ''),
            'quote_uniform_size': row.get('tamanho_uniforme', ''), 'quote_qty': row.get('qtd', ''),
            'quote_unit_price': row.get('valor_unitario', ''), 'quote_issued_at': row['quote_issued_at'],
            'quote_sig': row['quote_sig']}


def _price(pri):
    with _fresh() as c:
        return float(c.execute('SELECT unit_price FROM purchase_request_items WHERE id=?', (pri,)).fetchone()['unit_price'] or 0)


def test_parse_requires_the_request(server):
    s = seed('general_admin')
    status, body = _parse(server, s, None)
    assert status == 400, body


def test_row_parsed_for_one_request_is_refused_on_another_and_saves_on_its_own(server):
    s = seed('general_admin')
    pr_a, pri_a = _request(s)
    pr_b, pri_b = _request(s)
    status, body = _parse(server, s, pr_a)
    assert status == 200, body
    row = body['items'][0]
    status, body = call(server, s, f'/api/purchase-requests/{pr_b}/save-prices',
                        {'actor_user_id': s['actor']['id'], 'items': [_association(row, pri_b)]})
    assert status == 400 and 'para esta requisição' in str(body), body
    assert _price(pri_b) == 0
    status, body = call(server, s, f'/api/purchase-requests/{pr_a}/save-prices',
                        {'actor_user_id': s['actor']['id'], 'items': [_association(row, pri_a)]})
    assert status == 200, body
    assert _price(pri_a) == 10.0
    with _fresh() as c:
        event = c.execute("SELECT * FROM purchase_events WHERE entity_type='purchase_request' AND entity_id=? "
                          "AND action='quote_association_confirmed'", (pr_a,)).fetchone()
    assert event['actor_user_id'] == s['actor']['id']
    assert f'item #{pri_a}' in event['comment'] and 'fornecedor "Fornecedor Real"' in event['comment']


def test_po_for_request_of_another_unit_is_refused(server):
    s = seed('general_admin')
    with _fresh() as c:
        other_unit = c.execute('INSERT INTO units(company_id,name,unit_type,city) VALUES (?,?,?,?)',
                               (s['company'], 'U2', 'base', 'T')).lastrowid
        c.commit()
    pr, pri = _request(s, unit=other_unit)
    with _fresh() as c:
        c.execute("UPDATE purchase_requests SET status='approved' WHERE id=?", (pr,))
        c.execute("UPDATE purchase_request_items SET status='approved' WHERE id=?", (pri,))
        c.commit()
    item = {'purchase_request_item_id': pri, 'epi_id': s['epi'], 'epi_name': 'Luva Nitrilica', 'quantity': 3, 'unit_price': 10.0}
    status, body = call(server, s, '/api/purchase-orders',
                        {'actor_user_id': s['actor']['id'], 'unit_id': s['unit'], 'purchase_request_id': pr, 'items': [item]})
    assert status == 400 and 'outra unidade' in str(body), body
    with _fresh() as c:
        assert c.execute('SELECT COUNT(*) AS n FROM purchase_orders WHERE purchase_request_id=?', (pr,)).fetchone()['n'] == 0
        assert c.execute('SELECT linked_po_id FROM purchase_requests WHERE id=?', (pr,)).fetchone()['linked_po_id'] is None
