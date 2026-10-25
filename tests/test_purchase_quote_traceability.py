"""Rastreabilidade das linhas assinadas da cotação (auditoria de 2026-10-25).

A linha sai do parse assinada para a requisição em que foi visualizada
(empresa, usuário, requisição, horário e campos): não é aceita em outra
requisição, nem para salvar preço nem para gerar PO. A PO nasce na Unidade da
requisição vinculada, o fornecedor de cada item vem da linha assinada e o
histórico guarda quem confirmou, para qual requisição/item/PO e com quais
valores.
"""

from datetime import datetime, timezone

import pytest

from modules.purchases.service import (
    _quote_row_signature,
    create_purchase_order,
    generate_po_number,
    quote_row_from_association,
    save_purchase_request_prices,
    sign_quote_rows,
)
from tests.test_purchase_orders_service import ADMIN
from tests.test_purchase_quote_association_po import STAMP, _conn, _item, _payload


def _with_price_columns(conn):
    for ddl in ("ALTER TABLE purchase_request_items ADD COLUMN unit_price REAL DEFAULT 0",
                "ALTER TABLE purchase_request_items ADD COLUMN total_price REAL DEFAULT 0"):
        conn.execute(ddl)
    return conn


def _second_request(conn, *, unit_id=10, pr_status='approved', item_status='approved'):
    """Requisição 6: mesmo EPI, mesma empresa, mesmo CA da requisição 5."""
    conn.execute("INSERT INTO purchase_requests (id, company_id, unit_id, status) VALUES (6, 1, ?, ?)", (unit_id, pr_status))
    conn.execute(
        'INSERT INTO purchase_request_items (id, purchase_request_id, company_id, unit_id, epi_id, status, '
        f"epi_name, ca, quantity_requested, updated_at) VALUES (9, 6, 1, ?, 100, ?, 'Luva', '12345', 3, '{STAMP}')",
        (unit_id, item_status),
    )


def _signed_for(pr_id, **overrides):
    item = _item(sign=False, **overrides)
    item['quote_issued_at'] = datetime.now(timezone.utc).isoformat()
    item['quote_sig'] = _quote_row_signature(ADMIN, quote_row_from_association(item), item['quote_issued_at'], pr_id)
    return item


def _pr(conn, pr_id):
    return dict(conn.execute('SELECT * FROM purchase_requests WHERE id = ?', (pr_id,)).fetchone())


def _po_count(conn):
    return conn.execute('SELECT COUNT(*) FROM purchase_orders').fetchone()[0]


# ── a linha pertence à requisição em que foi visualizada ─────────────────────

def test_parse_refuses_to_sign_without_request():
    with pytest.raises(ValueError, match='Requisição da cotação não informada'):
        sign_quote_rows(ADMIN, [{'line': 1}], 0)


def test_row_signed_for_one_request_is_refused_when_saving_prices_on_another():
    conn = _with_price_columns(_conn())
    _second_request(conn, pr_status='sent_to_buyer', item_status='open')
    reused = _item(purchase_request_item_id=9)          # assinada na requisição 5
    reused['item_id'] = 9
    with pytest.raises(ValueError, match='para esta requisição'):
        save_purchase_request_prices(conn, ADMIN, _pr(conn, 6), [reused], '')
    assert conn.execute('SELECT unit_price FROM purchase_request_items WHERE id = 9').fetchone()[0] == 0


def test_row_signed_for_the_request_saves_prices_on_it():
    conn = _with_price_columns(_conn())
    _second_request(conn, pr_status='sent_to_buyer', item_status='open')
    own = _signed_for(6, purchase_request_item_id=9)
    own['item_id'] = 9
    affected, _ = save_purchase_request_prices(conn, ADMIN, _pr(conn, 6), [own], '')
    assert affected == [9]


def test_row_signed_for_one_request_cannot_become_po_of_another():
    conn = _conn()
    _second_request(conn)
    payload = _payload(_item(purchase_request_item_id=9))   # linha da requisição 5
    payload['purchase_request_id'] = 6
    with pytest.raises(ValueError, match='para esta requisição'):
        create_purchase_order(conn, ADMIN, payload, '')
    assert _po_count(conn) == 0
    assert conn.execute('SELECT linked_po_id FROM purchase_requests WHERE id = 6').fetchone()[0] is None


def test_row_signed_by_another_user_is_refused():
    conn = _conn()
    item = _item(sign=False)
    item['quote_issued_at'] = datetime.now(timezone.utc).isoformat()
    item['quote_sig'] = _quote_row_signature({**ADMIN, 'id': 99}, quote_row_from_association(item),
                                             item['quote_issued_at'], 5)
    with pytest.raises(ValueError, match='não conferem'):
        create_purchase_order(conn, ADMIN, _payload(item), '')
    assert _po_count(conn) == 0


# ── a PO nasce na Unidade da requisição ──────────────────────────────────────

@pytest.mark.parametrize('quote_import', [False, True])
def test_po_unit_must_be_the_request_unit(quote_import):
    conn = _conn()
    conn.execute("INSERT INTO units (id, company_id, name) VALUES (11, 1, 'Base Itajai')")
    _second_request(conn, unit_id=11)
    if quote_import:
        payload = _payload(_signed_for(6, purchase_request_item_id=9))
        payload.update(purchase_request_id=6, unit_id=10)
    else:
        item = {'purchase_request_item_id': 9, 'epi_id': 100, 'epi_name': 'Luva', 'quantity': 3, 'unit_price': 10.0}
        payload = {'unit_id': 10, 'purchase_request_id': 6, 'items': [item]}
    with pytest.raises(ValueError, match='pertence a outra unidade'):
        create_purchase_order(conn, ADMIN, payload, '')
    assert _po_count(conn) == 0
    assert conn.execute('SELECT linked_po_id FROM purchase_requests WHERE id = 6').fetchone()[0] is None


def test_po_in_the_request_unit_keeps_working():
    conn = _conn()
    conn.execute("INSERT INTO units (id, company_id, name) VALUES (11, 1, 'Base Itajai')")
    _second_request(conn, unit_id=11)
    item = {'purchase_request_item_id': 9, 'epi_id': 100, 'epi_name': 'Luva', 'quantity': 3, 'unit_price': 10.0}
    res = create_purchase_order(conn, ADMIN, {'unit_id': 11, 'purchase_request_id': 6, 'items': [item]}, '')
    assert conn.execute('SELECT unit_id FROM purchase_orders WHERE id = ?', (res['id'],)).fetchone()[0] == 11


# ── fornecedor do item é o da linha assinada ─────────────────────────────────

def test_po_item_supplier_comes_from_signed_row_not_from_client():
    conn = _conn()
    item = _item(quote_supplier='Fornecedor da Cotação', supplier='Forjado')
    item['quote_sig'] = _quote_row_signature(ADMIN, quote_row_from_association(item), item['quote_issued_at'], 5)
    create_purchase_order(conn, ADMIN, _payload(item), '')
    assert conn.execute('SELECT supplier FROM purchase_order_items').fetchone()[0] == 'Fornecedor da Cotação'


def test_po_item_supplier_falls_back_to_po_supplier_when_row_has_none():
    conn = _conn()
    create_purchase_order(conn, ADMIN, _payload(_item(supplier='Forjado')), '')
    assert conn.execute('SELECT supplier FROM purchase_order_items').fetchone()[0] == 'ACME'


# ── histórico reconstrói quem confirmou, para onde e com quais valores ───────

def test_history_reconstructs_actor_request_item_po_and_values():
    conn = _conn()
    item = _item(quote_supplier='Fornecedor X')
    item['quote_sig'] = _quote_row_signature(ADMIN, quote_row_from_association(item), item['quote_issued_at'], 5)
    res = create_purchase_order(conn, ADMIN, _payload(item), '10.0.0.7')
    event = conn.execute(
        "SELECT * FROM purchase_events WHERE action = 'quote_association_confirmed'"
    ).fetchone()
    assert (event['entity_type'], event['entity_id']) == ('purchase_request', 5)
    assert (event['actor_user_id'], event['actor_name'], event['ip_address']) == (ADMIN['id'], ADMIN['full_name'], '10.0.0.7')
    assert event['created_at']
    comment = event['comment']
    for expected in (f'PO {res["po_number"]} (id {res["id"]})', 'linha 1', 'item #7', 'CA 12345',
                     'fornecedor "Fornecedor X"', 'R$ 10.00 × 3', item['quote_issued_at'], item['quote_sig'][:16]):
        assert expected in comment, expected
    po_item = conn.execute('SELECT purchase_request_item_id, unit_price, quantity FROM purchase_order_items').fetchone()
    assert tuple(po_item) == (7, 10.0, 3)


def test_failed_link_leaves_no_po_or_history_after_rollback(monkeypatch):
    conn = _conn()

    def number_while_another_po_links(connection, company_id):
        connection.execute('UPDATE purchase_requests SET linked_po_id = 999 WHERE id = 5')
        return generate_po_number(connection, company_id)

    monkeypatch.setattr('modules.purchases.service.generate_po_number', number_while_another_po_links)
    with pytest.raises(ValueError, match='Outra PO foi vinculada'):
        create_purchase_order(conn, ADMIN, _payload(_item()), '')
    conn.rollback()   # a rota só faz commit no sucesso
    assert _po_count(conn) == 0
    assert conn.execute('SELECT COUNT(*) FROM purchase_events').fetchone()[0] == 0
