"""PO criada a partir do arquivo de cotação (decisão de 2026-10-22, opção C + A).

Com ``source = 'quote_import'``, cada item da PO precisa de associação
confirmada pelo operador e revalidada no backend — a mesma regra do
salvamento de preços — além de o EPI enviado ser o EPI do item da requisição.
PO criada por outros caminhos (ex.: Flutter) não muda.
"""

import pytest

from modules.purchases.service import create_purchase_order
from tests.test_purchase_orders_service import ADMIN, _conn as _base_conn

STAMP = '2026-10-22T10:00:00+00:00'


def _conn():
    conn = _base_conn()
    for ddl in (
        "ALTER TABLE epis ADD COLUMN ca TEXT DEFAULT ''",
        "ALTER TABLE epis ADD COLUMN model_reference TEXT DEFAULT ''",
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


def _item(**overrides):
    item = {
        'purchase_request_item_id': 7, 'epi_id': 100, 'epi_name': 'Luva', 'ca': '12345',
        'quantity': 3, 'unit_price': 10.0, 'confirmed': True, 'expected_updated_at': STAMP,
        'quote_line': 1, 'quote_epi': 'Luva', 'quote_ca': '12345', 'quote_manufacturer': 'Danny',
    }
    item.update(overrides)
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
        quote_line=2, quote_epi='Capacete', quote_ca='67890',
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
    ({'quote_ca': '', 'quote_epi': 'Protetor auricular'}, 'sem identificação do produto'),
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
