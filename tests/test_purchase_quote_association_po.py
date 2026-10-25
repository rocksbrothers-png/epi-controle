"""PO criada a partir do arquivo de cotação (decisão de 2026-10-22, opção C + A).

Com ``source = 'quote_import'``, cada item da PO precisa de associação
confirmada pelo operador e revalidada no backend — a mesma regra do
salvamento de preços — além de o EPI enviado ser o EPI do item da requisição.
PO criada por outros caminhos (ex.: Flutter) não muda.
"""

from datetime import datetime, timezone

import pytest

from modules.purchases.service import (
    _quote_row_signature,
    create_purchase_order,
    generate_po_number,
    quote_row_from_association,
)
from tests.test_purchase_orders_service import ADMIN, _conn as _base_conn

STAMP = '2026-10-22T10:00:00+00:00'


def _conn():
    conn = _base_conn()
    for ddl in (
        "ALTER TABLE epis ADD COLUMN ca TEXT DEFAULT ''",
        "ALTER TABLE epis ADD COLUMN model_reference TEXT DEFAULT ''",
        "ALTER TABLE epis ADD COLUMN manufacturer TEXT DEFAULT ''",
        "ALTER TABLE purchase_request_items ADD COLUMN epi_name TEXT DEFAULT ''",
        "ALTER TABLE purchase_request_items ADD COLUMN ca TEXT DEFAULT ''",
        "ALTER TABLE purchase_request_items ADD COLUMN quantity_requested INTEGER DEFAULT 1",
        "ALTER TABLE purchase_request_items ADD COLUMN updated_at TEXT DEFAULT ''",
    ):
        conn.execute(ddl)
    conn.execute("UPDATE epis SET ca = '12345', model_reference = 'DA-500' WHERE id = 100")
    conn.execute("INSERT INTO epis (id, company_id, name, ca) VALUES (101, 1, 'Capacete', '67890')")
    conn.execute("INSERT INTO purchase_requests (id, company_id, unit_id, status) VALUES (5, 1, 10, 'approved')")
    conn.execute(
        'INSERT INTO purchase_request_items (id, purchase_request_id, company_id, unit_id, epi_id, status, '
        "epi_name, ca, quantity_requested, updated_at) VALUES "
        f"(7, 5, 1, 10, 100, 'approved', 'Luva', '12345', 3, '{STAMP}'), "
        f"(8, 5, 1, 10, 101, 'approved', 'Capacete', '67890', 2, '{STAMP}')"
    )
    conn.commit()
    return conn


def _item(sign=True, **overrides):
    item = {
        'purchase_request_item_id': 7, 'epi_id': 100, 'epi_name': 'Luva', 'ca': '12345',
        'quantity': 3, 'unit_price': 10.0, 'confirmed': True, 'expected_updated_at': STAMP,
        'quote_line': 1, 'quote_epi': 'Luva', 'quote_ca': '12345', 'quote_manufacturer': '',
        'quote_qty': '3', 'quote_unit_price': '10.00',
    }
    item.update(overrides)
    if sign:
        item['quote_issued_at'] = datetime.now(timezone.utc).isoformat()
        item['quote_sig'] = _quote_row_signature(ADMIN, quote_row_from_association(item), item['quote_issued_at'])
    return item


def _payload(*items):
    return {'unit_id': 10, 'purchase_request_id': 5, 'supplier': 'ACME', 'source': 'quote_import',
            'items': list(items)}


def _po_count(conn):
    return conn.execute('SELECT COUNT(*) FROM purchase_orders').fetchone()[0]


def test_quote_import_po_with_confirmed_associations_is_created_and_audited():
    conn = _conn()
    res = create_purchase_order(conn, ADMIN, _payload(_item(), _item(
        purchase_request_item_id=8, epi_id=101, epi_name='Capacete', ca='67890', quantity=2, unit_price=55.0,
        quote_line=2, quote_epi='Capacete', quote_ca='67890', quote_qty='2', quote_unit_price='55.00',
    )), '10.0.0.1')
    assert res['status'] == 'waiting_admin_review'
    events = conn.execute(
        "SELECT * FROM purchase_events WHERE action = 'quote_association_confirmed' ORDER BY id"
    ).fetchall()
    assert len(events) == 2
    assert all(ev['actor_user_id'] == ADMIN['id'] and ev['reason'] == 'operator_confirmed' for ev in events)
    assert res['po_number'] in events[0]['comment']
    assert 'item #7' in events[0]['comment'] and 'item #8' in events[1]['comment']


@pytest.mark.parametrize('overrides, message', [
    ({'confirmed': False}, 'não confirmada'),
    ({'quote_ca': '99999'}, 'CA divergente'),
    ({'quote_ca': '', 'quote_epi': 'Protetor auricular'}, 'contradiz o item #7'),
    ({'unit_price': 99.0}, 'preço confirmado difere'),
    ({'expected_updated_at': 'antigo'}, 'alterado por outra operação'),
    ({'epi_id': 101}, 'não é o EPI do item'),
])
def test_quote_import_po_rejects_unsafe_association(overrides, message):
    conn = _conn()
    with pytest.raises(ValueError, match=message):
        create_purchase_order(conn, ADMIN, _payload(_item(**overrides)), '')
    assert _po_count(conn) == 0


def test_quote_import_po_requires_linked_request():
    conn = _conn()
    payload = _payload(_item())
    payload.pop('purchase_request_id')
    with pytest.raises(ValueError, match='requisição vinculada'):
        create_purchase_order(conn, ADMIN, payload, '')


def test_po_outside_quote_import_keeps_previous_contract():
    conn = _conn()
    item = {'purchase_request_item_id': 7, 'epi_id': 100, 'epi_name': 'Luva', 'quantity': 3, 'unit_price': 10.0}
    res = create_purchase_order(conn, ADMIN, {'unit_id': 10, 'purchase_request_id': 5, 'items': [item]}, '')
    assert res['status'] == 'waiting_admin_review'
    assert conn.execute(
        "SELECT COUNT(*) FROM purchase_events WHERE action = 'quote_association_confirmed'"
    ).fetchone()[0] == 0


def test_quote_import_po_requires_signed_rows():
    conn = _conn()
    with pytest.raises(ValueError, match='sem a assinatura'):
        create_purchase_order(conn, ADMIN, _payload(_item(sign=False)), '')
    tampered = _item()
    tampered['quote_ca'] = ''
    with pytest.raises(ValueError, match='não conferem com o arquivo'):
        create_purchase_order(conn, ADMIN, _payload(tampered), '')
    assert _po_count(conn) == 0


def test_quote_import_po_stores_catalogue_identity_not_file_text():
    conn = _conn()
    hostile = '<img src=x onerror=alert(1)>'
    create_purchase_order(conn, ADMIN, _payload(_item(epi_name=hostile, ca=hostile, manufacturer=hostile)), '')
    row = conn.execute('SELECT epi_name, ca, manufacturer FROM purchase_order_items').fetchone()
    assert row['epi_name'] == 'Luva' and row['ca'] == '12345'
    assert hostile not in (row['manufacturer'] or '')


def test_quote_import_cannot_generate_a_second_po_for_the_request():
    conn = _conn()
    create_purchase_order(conn, ADMIN, _payload(_item()), '')
    with pytest.raises(ValueError, match='já tem PO vinculada'):
        create_purchase_order(conn, ADMIN, _payload(_item()), '')
    assert _po_count(conn) == 1


def test_quote_import_po_rejects_concurrent_link(monkeypatch):
    conn = _conn()

    def number_while_another_po_links(connection, company_id):
        # outra criação concorrente vinculou uma PO entre a validação e a escrita
        connection.execute('UPDATE purchase_requests SET linked_po_id = 999 WHERE id = 5')
        return generate_po_number(connection, company_id)

    monkeypatch.setattr('modules.purchases.service.generate_po_number', number_while_another_po_links)
    with pytest.raises(ValueError, match='Outra PO foi vinculada'):
        create_purchase_order(conn, ADMIN, _payload(_item()), '')


def test_quote_import_po_stores_validated_quantity_and_price_not_client_fields():
    conn = _conn()
    # quantidade omitida + quantity_requested forjado: a PO usa o que foi validado
    item = _item(quantity_requested=999, unit_price=10.004)
    item.pop('quantity')
    create_purchase_order(conn, ADMIN, _payload(item), '')
    row = conn.execute('SELECT quantity, unit_price, total_price FROM purchase_order_items').fetchone()
    assert (row['quantity'], row['unit_price'], row['total_price']) == (3, 10.0, 30.0)


@pytest.mark.parametrize('bad', [float('inf'), '2.5'])
def test_quote_import_po_rejects_non_integral_quantity(bad):
    conn = _conn()
    with pytest.raises(ValueError, match='Quantidade inválida'):
        create_purchase_order(conn, ADMIN, _payload(_item(quantity=bad)), '')
    assert _po_count(conn) == 0
