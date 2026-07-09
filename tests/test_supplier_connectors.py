"""Fase F4 do módulo de Compras — conectores de API direta (Nível 3).

Valida a interface/registro de conectores, a cifra por tenant das credenciais
e a orquestração sobre o fluxo existente: cotação via API responde pelo mesmo
answer_quote (guardas preservadas), pedido via API grava campos paralelos sem
mudar o status da PO, e o catálogo sincroniza no supplier_products.
"""

import sqlite3

import pytest

from core.schema import ensure_procurement_supplier_tables
from epi_backend.connector_crypto import (
    decrypt_connector_config,
    encrypt_connector_config,
)
from epi_backend.supplier_connectors import (
    ConnectorError,
    available_connectors,
    get_connector,
)
from epi_backend.supplier_connectors.demo import DemoConnector
from epi_backend.supplier_connectors.http_json import HttpJsonConnector
from modules.purchases.connectors_service import (
    get_supplier_integration,
    quote_via_connector,
    refresh_po_status_from_connector,
    send_po_via_connector,
    sync_catalog_from_connector,
    ping_supplier_integration,
    upsert_supplier_integration,
)
from modules.purchases.quotes_service import (
    create_authorized_supplier,
    create_quotes_for_request,
    fetch_quote_items,
    fetch_supplier_products,
    get_quote_by_id,
    get_supplier_by_id,
)

BUYER = {'id': 10, 'full_name': 'Comprador Teste', 'role': 'buyer', 'company_id': 1}


def _conn():
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        CREATE TABLE companies (id INTEGER PRIMARY KEY, name TEXT);
        CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT);
        CREATE TABLE units (id INTEGER PRIMARY KEY, company_id INTEGER, name TEXT);
        CREATE TABLE epis (id INTEGER PRIMARY KEY, company_id INTEGER, name TEXT);
        CREATE TABLE purchase_requests (
            id INTEGER PRIMARY KEY, company_id INTEGER, unit_id INTEGER,
            status TEXT DEFAULT 'sent_to_buyer', title TEXT DEFAULT '',
            created_at TEXT DEFAULT '', updated_at TEXT DEFAULT ''
        );
        CREATE TABLE purchase_request_items (
            id INTEGER PRIMARY KEY, purchase_request_id INTEGER, company_id INTEGER, unit_id INTEGER,
            epi_id INTEGER, epi_name TEXT DEFAULT '', ca TEXT DEFAULT '', unit_measure TEXT DEFAULT 'un',
            manufacturer TEXT DEFAULT '', glove_size TEXT DEFAULT 'N/A', size TEXT DEFAULT 'N/A',
            uniform_size TEXT DEFAULT 'N/A', quantity_requested INTEGER DEFAULT 1,
            status TEXT DEFAULT 'open', updated_at TEXT DEFAULT ''
        );
        CREATE TABLE purchase_orders (
            id INTEGER PRIMARY KEY, company_id INTEGER, unit_id INTEGER,
            status TEXT DEFAULT 'approved', po_number TEXT DEFAULT '',
            supplier TEXT DEFAULT '', supplier_cnpj TEXT DEFAULT '',
            expected_delivery_date TEXT DEFAULT '',
            created_at TEXT DEFAULT '', updated_at TEXT DEFAULT ''
        );
        CREATE TABLE purchase_order_items (
            id INTEGER PRIMARY KEY, purchase_order_id INTEGER, company_id INTEGER,
            epi_id INTEGER, epi_name TEXT DEFAULT '', ca TEXT DEFAULT '',
            quantity INTEGER DEFAULT 1, quantity_approved INTEGER DEFAULT 0,
            unit_price REAL DEFAULT 0
        );
        CREATE TABLE purchase_events (
            id INTEGER PRIMARY KEY, company_id INTEGER, entity_type TEXT, entity_id INTEGER,
            action TEXT, status_from TEXT DEFAULT '', status_to TEXT DEFAULT '',
            comment TEXT DEFAULT '', actor_user_id INTEGER, actor_name TEXT DEFAULT '',
            actor_role TEXT DEFAULT '', reason TEXT DEFAULT '', destination TEXT DEFAULT '',
            ip_address TEXT DEFAULT '', created_at TEXT
        );
        CREATE TABLE authorized_suppliers (
            id INTEGER PRIMARY KEY, company_id INTEGER, name TEXT,
            cnpj TEXT DEFAULT '', category TEXT DEFAULT '', contact_email TEXT DEFAULT '',
            notes TEXT DEFAULT '', active INTEGER DEFAULT 1, source TEXT DEFAULT 'manual',
            created_by_user_id INTEGER, created_at TEXT DEFAULT '', updated_at TEXT DEFAULT ''
        );
        """
    )
    ensure_procurement_supplier_tables(conn)
    conn.execute("INSERT INTO companies (id, name) VALUES (1, 'Empresa A')")
    conn.execute("INSERT INTO units (id, company_id, name) VALUES (1, 1, 'Unidade 1')")
    conn.execute("INSERT INTO epis (id, company_id, name) VALUES (5, 1, 'Luva Nitrílica')")
    conn.execute("INSERT INTO purchase_requests (id, company_id, unit_id) VALUES (100, 1, 1)")
    conn.execute(
        "INSERT INTO purchase_request_items (id, purchase_request_id, company_id, unit_id, epi_id, epi_name, ca, quantity_requested) "
        "VALUES (1000, 100, 1, 1, 5, 'Luva Nitrílica', '12345', 10)"
    )
    return conn


def _supplier_with_integration(conn, config=None, active=True):
    supplier = create_authorized_supplier(conn, BUYER, {
        'name': 'Loja API', 'contact_email': 'api@loja.com', 'cnpj': '11222333000144',
    })
    upsert_supplier_integration(conn, BUYER, 1, supplier['id'], {
        'connector_key': 'demo',
        'active': active,
        'config': config or {'price_table': {'12345': 9.9}},
    })
    return supplier


def _approved_po(conn):
    conn.execute(
        "INSERT INTO purchase_orders (id, company_id, unit_id, status, po_number, supplier, supplier_cnpj) "
        "VALUES (500, 1, 1, 'approved', 'PO-2026-001', 'Loja API', '11222333000144')"
    )
    conn.execute(
        "INSERT INTO purchase_order_items (purchase_order_id, company_id, epi_id, epi_name, ca, quantity_approved, unit_price) "
        "VALUES (500, 1, 5, 'Luva Nitrílica', '12345', 10, 9.9)"
    )
    return 500


# ── registro e interface ─────────────────────────────────────────────────────

def test_registry_lists_demo_and_http_json():
    keys = {c['key'] for c in available_connectors()}
    assert {'demo', 'http_json_v1'} <= keys
    assert isinstance(get_connector('demo', {}), DemoConnector)
    assert isinstance(get_connector('http_json_v1', {}), HttpJsonConnector)
    with pytest.raises(ValueError, match='desconhecido'):
        get_connector('inexistente', {})


def test_http_json_requires_https_base_url():
    connector = HttpJsonConnector({'base_url': 'http://inseguro.example.com'})
    with pytest.raises(ConnectorError, match='HTTPS'):
        connector.get_catalog()


def test_demo_connector_contract():
    connector = DemoConnector({'price_table': {'12345': 7.5}, 'default_lead_time_days': 3})
    catalog = connector.get_catalog()
    assert catalog and 'supplier_sku' in catalog[0]
    answers = connector.get_price_and_stock([
        {'purchase_request_item_id': 1000, 'ca': '12345', 'quantity_requested': 10},
        {'purchase_request_item_id': 1001, 'ca': '99999', 'quantity_requested': 4},
    ])
    assert answers[0]['unit_price'] == 7.5
    assert answers[1]['unit_price'] == 25.0  # default
    assert answers[0]['lead_time_days'] == 3
    order = connector.create_order({'id': 500, 'po_number': 'PO-1'}, [])
    assert order['confirmed'] and order['supplier_order_ref'].startswith('DEMO-')
    status = connector.get_order_status(order['supplier_order_ref'])
    assert status['status'] == 'delivery_update'
    assert status['tracking_code']


# ── cifra por tenant ─────────────────────────────────────────────────────────

def test_config_encrypted_per_tenant(monkeypatch):
    monkeypatch.setenv('CONNECTOR_SECRET_KEY', 'segredo-de-teste')
    token = encrypt_connector_config(1, {'api_key': 'super-secreta'})
    assert 'super-secreta' not in token
    assert decrypt_connector_config(1, token)['api_key'] == 'super-secreta'
    with pytest.raises(ValueError):
        decrypt_connector_config(2, token)  # outro tenant não decifra


def test_integration_upsert_stores_encrypted_and_hides_config():
    conn = _conn()
    supplier = _supplier_with_integration(conn, config={'api_key': 'nao-vazar'})
    raw = conn.execute(
        'SELECT config_encrypted FROM supplier_integrations WHERE supplier_id = ?',
        (supplier['id'],)
    ).fetchone()
    assert 'nao-vazar' not in str(raw['config_encrypted'])
    integration = get_supplier_integration(conn, 1, supplier['id'])
    assert integration['has_config'] is True
    assert 'config' not in integration
    assert 'config_encrypted' not in integration
    # ativar a integração promove o fornecedor ao Nível 3
    assert get_supplier_by_id(conn, 1, supplier['id'])['integration_level'] == 'api'


def test_integration_rejects_unknown_connector():
    conn = _conn()
    supplier = create_authorized_supplier(conn, BUYER, {'name': 'X', 'cnpj': '1'})
    with pytest.raises(ValueError, match='desconhecido'):
        upsert_supplier_integration(conn, BUYER, 1, supplier['id'], {'connector_key': 'nope'})


def test_operations_require_active_integration():
    conn = _conn()
    supplier = _supplier_with_integration(conn, active=False)
    with pytest.raises(ValueError, match='ativa'):
        ping_supplier_integration(conn, 1, supplier['id'])


# ── operações sobre o fluxo existente ────────────────────────────────────────

def test_catalog_sync_upserts_supplier_products():
    conn = _conn()
    supplier = _supplier_with_integration(conn)
    result = sync_catalog_from_connector(conn, BUYER, 1, supplier['id'])
    assert result['imported'] == 2
    products = fetch_supplier_products(conn, 1, supplier['id'])
    skus = {p['supplier_sku'] for p in products}
    assert 'DEMO-LUVA-01' in skus
    # idempotente: re-sincronizar não duplica
    sync_catalog_from_connector(conn, BUYER, 1, supplier['id'])
    assert len(fetch_supplier_products(conn, 1, supplier['id'])) == 2
    integration = get_supplier_integration(conn, 1, supplier['id'])
    assert integration['last_sync_at']


def test_quote_via_connector_answers_with_api_channel():
    conn = _conn()
    supplier = _supplier_with_integration(conn)  # price_table 12345 → 9.9
    quote = create_quotes_for_request(conn, BUYER, 100, {'supplier_ids': [supplier['id']]})[0]
    result = quote_via_connector(conn, BUYER, quote['id'])
    assert result['status'] == 'answered'
    assert result['channel'] == 'api'
    items = fetch_quote_items(conn, quote['id'])
    assert float(items[0]['unit_price']) == 9.9
    # guarda do answer_quote preservada: cotação já respondida não recota
    with pytest.raises(ValueError, match='não pode receber resposta'):
        quote_via_connector(conn, BUYER, quote['id'])


def test_send_po_via_connector_keeps_status_and_records_confirmation():
    conn = _conn()
    _supplier_with_integration(conn)
    po_id = _approved_po(conn)
    po = send_po_via_connector(conn, BUYER, po_id)
    assert po['status'] == 'approved'  # máquina de estados intacta
    assert po['sent_channel'] == 'api'
    assert po['supplier_order_ref'].startswith('DEMO-')
    assert po['supplier_confirmation_status'] == 'confirmed'
    row = conn.execute(
        'SELECT source, status FROM purchase_order_confirmations WHERE purchase_order_id = ?',
        (po_id,)
    ).fetchone()
    assert row['source'] == 'api' and row['status'] == 'confirmed'


def test_send_po_via_connector_requires_approved_status():
    conn = _conn()
    _supplier_with_integration(conn)
    po_id = _approved_po(conn)
    conn.execute("UPDATE purchase_orders SET status = 'draft' WHERE id = ?", (po_id,))
    with pytest.raises(ValueError, match='aprovadas'):
        send_po_via_connector(conn, BUYER, po_id)


def test_rejected_order_marks_confirmation_rejected():
    conn = _conn()
    _supplier_with_integration(conn, config={'reject_order': True})
    po_id = _approved_po(conn)
    po = send_po_via_connector(conn, BUYER, po_id)
    assert po['supplier_confirmation_status'] == 'rejected'
    assert po['status'] == 'approved'  # recusa da loja não regride a PO


def test_refresh_po_status_records_delivery_update():
    conn = _conn()
    _supplier_with_integration(conn)
    po_id = _approved_po(conn)
    with pytest.raises(ValueError, match='referência'):
        refresh_po_status_from_connector(conn, BUYER, po_id)  # ainda não enviada
    send_po_via_connector(conn, BUYER, po_id)
    po = refresh_po_status_from_connector(conn, BUYER, po_id)
    assert po['supplier_confirmation_status'] == 'confirmed'  # update não sobrescreve
    rows = conn.execute(
        "SELECT status, tracking_code FROM purchase_order_confirmations "
        'WHERE purchase_order_id = ? ORDER BY id',
        (po_id,)
    ).fetchall()
    assert [r['status'] for r in rows] == ['confirmed', 'delivery_update']
    assert rows[1]['tracking_code'].endswith('-TRK')
