"""Fase F1 do módulo de Compras — cotações (RFQ), catálogo e envio (Nível 1).

Valida o quotes_service com foco nas regras preservadas do plano:
  - criar/responder/selecionar cotação NÃO altera a requisição nem seus itens (R1);
  - selecionar vencedora apenas PRÉ-PREENCHE a PO (fluxo de aprovação intacto, R3);
  - envio da PO não muda o status dela (campos paralelos sent_*);
  - tudo por company_id e auditado em purchase_events (R6/R7).
"""

import sqlite3

import pytest

from core.schema import ensure_procurement_supplier_tables
from modules.purchases.quotes_service import (
    answer_quote,
    build_quote_comparison,
    create_authorized_supplier,
    create_quotes_for_request,
    deactivate_supplier_product,
    fetch_po_tracking,
    fetch_quote_items,
    fetch_quotes_for_request,
    fetch_supplier_products,
    get_quote_by_id,
    get_supplier_by_id,
    register_po_confirmation,
    select_quote,
    send_po_to_supplier,
    send_quote_to_supplier,
    update_supplier_procurement_fields,
    upsert_supplier_product,
)


# ── fixtures ──────────────────────────────────────────────────────────────────

BUYER = {'id': 10, 'full_name': 'Comprador Teste', 'role': 'buyer', 'company_id': 1}
MASTER = {'id': 99, 'full_name': 'Master', 'role': 'master_admin', 'company_id': None}


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
            status TEXT DEFAULT 'draft', po_number TEXT DEFAULT '',
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
    conn.execute("INSERT INTO companies (id, name) VALUES (1, 'Empresa A'), (2, 'Empresa B')")
    conn.execute("INSERT INTO units (id, company_id, name) VALUES (1, 1, 'Unidade 1')")
    conn.execute("INSERT INTO epis (id, company_id, name) VALUES (5, 1, 'Luva Nitrílica'), (6, 1, 'Capacete'), (7, 2, 'Bota')")
    conn.execute("INSERT INTO purchase_requests (id, company_id, unit_id, status) VALUES (100, 1, 1, 'sent_to_buyer')")
    conn.executescript(
        """
        INSERT INTO purchase_request_items (id, purchase_request_id, company_id, unit_id, epi_id, epi_name, ca, quantity_requested, status)
        VALUES (1000, 100, 1, 1, 5, 'Luva Nitrílica', '12345', 10, 'open'),
               (1001, 100, 1, 1, 6, 'Capacete', '67890', 4, 'open'),
               (1002, 100, 1, 1, 6, 'Capacete rejeitado', '67890', 2, 'rejected');
        """
    )
    return conn


def _supplier(conn, name='Loja EPI', email='vendas@loja.com', cnpj='11222333000144', company_id=1):
    return create_authorized_supplier(conn, BUYER if company_id == 1 else MASTER, {
        'name': name, 'contact_email': email, 'cnpj': cnpj, 'company_id': company_id,
    })


class _MailSpy:
    def __init__(self):
        self.sent = []

    def __call__(self, to_email, subject, body, html_body=None, attachments=None, reply_to=''):
        self.sent.append({'to': to_email, 'subject': subject, 'body': body, 'attachments': attachments or []})


# ── fornecedores / catálogo ───────────────────────────────────────────────────

def test_create_supplier_defaults_and_event():
    conn = _conn()
    supplier = _supplier(conn)
    assert supplier['integration_level'] == 'email'
    assert int(supplier['active']) == 1
    event = conn.execute("SELECT * FROM purchase_events WHERE entity_type = 'supplier'").fetchone()
    assert event['action'] == 'supplier_created'


def test_create_supplier_rejects_duplicate_cnpj():
    conn = _conn()
    _supplier(conn)
    with pytest.raises(ValueError, match='CNPJ'):
        _supplier(conn, name='Outra Loja')


def test_create_supplier_rejects_invalid_integration_level():
    conn = _conn()
    with pytest.raises(ValueError, match='integração'):
        create_authorized_supplier(conn, BUYER, {'name': 'X', 'integration_level': 'fax'})


def test_update_procurement_fields_partial():
    conn = _conn()
    supplier = _supplier(conn)
    ok = update_supplier_procurement_fields(conn, 1, supplier['id'], {'phone': '11 99999-0000', 'integration_level': 'portal'})
    assert ok
    updated = get_supplier_by_id(conn, 1, supplier['id'])
    assert updated['phone'] == '11 99999-0000'
    assert updated['integration_level'] == 'portal'
    assert updated['name'] == 'Loja EPI'  # campos legados intactos


def test_supplier_catalog_upsert_by_sku_and_deactivate():
    conn = _conn()
    supplier = _supplier(conn)
    product = upsert_supplier_product(conn, BUYER, 1, supplier['id'], {
        'supplier_sku': 'SKU-1', 'description': 'Luva nitrílica M', 'epi_id': 5,
        'last_price': 12.5, 'lead_time_days': 7,
    })
    assert float(product['last_price']) == 12.5
    updated = upsert_supplier_product(conn, BUYER, 1, supplier['id'], {
        'supplier_sku': 'SKU-1', 'description': 'Luva nitrílica M (nova)', 'last_price': 11.9,
    })
    assert updated['id'] == product['id']
    assert updated['description'] == 'Luva nitrílica M (nova)'
    assert len(fetch_supplier_products(conn, 1, supplier['id'])) == 1
    assert deactivate_supplier_product(conn, 1, product['id'])
    assert fetch_supplier_products(conn, 1, supplier['id']) == []
    assert len(fetch_supplier_products(conn, 1, supplier['id'], include_inactive=True)) == 1


def test_supplier_catalog_rejects_epi_of_other_company():
    conn = _conn()
    supplier = _supplier(conn)
    with pytest.raises(ValueError, match='EPI'):
        upsert_supplier_product(conn, BUYER, 1, supplier['id'], {'supplier_sku': 'S', 'description': 'Bota', 'epi_id': 7})


def test_get_supplier_is_tenant_scoped():
    conn = _conn()
    supplier = _supplier(conn)
    assert get_supplier_by_id(conn, 2, supplier['id']) is None


# ── cotações (RFQ) ────────────────────────────────────────────────────────────

def test_create_quotes_snapshots_items_without_touching_request():
    conn = _conn()
    supplier = _supplier(conn)
    before = conn.execute('SELECT id, status, quantity_requested FROM purchase_request_items ORDER BY id').fetchall()
    quotes = create_quotes_for_request(conn, BUYER, 100, {'supplier_ids': [supplier['id']]})
    assert len(quotes) == 1
    quote = quotes[0]
    assert quote['status'] == 'draft'
    assert quote['channel'] == 'email'
    items = fetch_quote_items(conn, quote['id'])
    # item rejeitado (1002) fica fora; os demais entram
    assert {i['purchase_request_item_id'] for i in items} == {1000, 1001}
    after = conn.execute('SELECT id, status, quantity_requested FROM purchase_request_items ORDER BY id').fetchall()
    assert [tuple(r) for r in before] == [tuple(r) for r in after]  # R1: requisição intacta


def test_create_quotes_rejects_duplicate_open_quote_and_inactive_supplier():
    conn = _conn()
    supplier = _supplier(conn)
    create_quotes_for_request(conn, BUYER, 100, {'supplier_ids': [supplier['id']]})
    with pytest.raises(ValueError, match='cotação aberta'):
        create_quotes_for_request(conn, BUYER, 100, {'supplier_ids': [supplier['id']]})
    inactive = _supplier(conn, name='Inativa', cnpj='99888777000166')
    update_supplier_procurement_fields(conn, 1, inactive['id'], {'active': 0})
    with pytest.raises(ValueError, match='inativo'):
        create_quotes_for_request(conn, BUYER, 100, {'supplier_ids': [inactive['id']]})


def test_answer_quote_manual_and_csv_item_link():
    conn = _conn()
    supplier = _supplier(conn)
    quote = create_quotes_for_request(conn, BUYER, 100, {'supplier_ids': [supplier['id']]})[0]
    answered = answer_quote(conn, BUYER, quote['id'], {
        'freight_value': 30.0,
        'payment_terms': '28 dias',
        'items': [
            # formato manual (quote_item_id) e formato do importador CSV
            # (purchase_request_item_id + valor_unitario) na mesma resposta
            {'quote_item_id': fetch_quote_items(conn, quote['id'])[0]['id'], 'unit_price': 10.0, 'lead_time_days': 5},
            {'purchase_request_item_id': 1001, 'valor_unitario': 55.5, 'lead_time_days': 12},
        ],
    })
    assert answered['status'] == 'answered'
    assert float(answered['freight_value']) == 30.0
    items = {i['purchase_request_item_id']: i for i in fetch_quote_items(conn, quote['id'])}
    assert float(items[1000]['unit_price']) == 10.0
    assert float(items[1001]['unit_price']) == 55.5


def test_answer_quote_requires_price_or_decline():
    conn = _conn()
    supplier = _supplier(conn)
    quote = create_quotes_for_request(conn, BUYER, 100, {'supplier_ids': [supplier['id']]})[0]
    with pytest.raises(ValueError, match='preço'):
        answer_quote(conn, BUYER, quote['id'], {'items': [{'purchase_request_item_id': 1000, 'unit_price': 0}]})
    # recusado sem preço é aceito
    answered = answer_quote(conn, BUYER, quote['id'], {'items': [
        {'purchase_request_item_id': 1000, 'declined': True},
        {'purchase_request_item_id': 1001, 'unit_price': 9.9},
    ]})
    assert answered['status'] == 'answered'


def test_comparison_flags_best_price_and_lead_time():
    conn = _conn()
    s1 = _supplier(conn, name='Loja 1', cnpj='11111111000111')
    s2 = _supplier(conn, name='Loja 2', cnpj='22222222000122')
    q1, q2 = create_quotes_for_request(conn, BUYER, 100, {'supplier_ids': [s1['id'], s2['id']]})
    answer_quote(conn, BUYER, q1['id'], {'freight_value': 0, 'items': [
        {'purchase_request_item_id': 1000, 'unit_price': 10.0, 'lead_time_days': 10},
        {'purchase_request_item_id': 1001, 'unit_price': 50.0, 'lead_time_days': 10},
    ]})
    answer_quote(conn, BUYER, q2['id'], {'freight_value': 100.0, 'items': [
        {'purchase_request_item_id': 1000, 'unit_price': 12.0, 'lead_time_days': 3},
        {'purchase_request_item_id': 1001, 'declined': True},
    ]})
    comparison = build_quote_comparison(fetch_quotes_for_request(conn, 100))
    item_1000 = next(i for i in comparison['items'] if i['purchase_request_item_id'] == 1000)
    offers = {o['supplier_name']: o for o in item_1000['offers']}
    assert offers['Loja 1']['best_price'] and not offers['Loja 2']['best_price']
    assert offers['Loja 2']['best_lead_time'] and not offers['Loja 1']['best_lead_time']
    suppliers = {s['supplier_name']: s for s in comparison['suppliers']}
    # Loja 1: 10*10 + 50*4 = 300; Loja 2: 12*10 (capacete recusado) + frete 100
    assert suppliers['Loja 1']['items_total'] == 300.0
    assert suppliers['Loja 2']['total_with_freight'] == 220.0
    assert comparison['suppliers'][0]['supplier_name'] == 'Loja 2'  # ordenado por total


def test_select_quote_discards_siblings_and_prefills_po():
    conn = _conn()
    s1 = _supplier(conn, name='Loja 1', cnpj='11111111000111')
    s2 = _supplier(conn, name='Loja 2', cnpj='22222222000122')
    q1, q2 = create_quotes_for_request(conn, BUYER, 100, {'supplier_ids': [s1['id'], s2['id']]})
    answer_quote(conn, BUYER, q1['id'], {'items': [
        {'purchase_request_item_id': 1000, 'unit_price': 10.0},
        {'purchase_request_item_id': 1001, 'declined': True},
    ]})
    with pytest.raises(ValueError, match='respondidas'):
        select_quote(conn, BUYER, q2['id'])  # ainda draft
    result = select_quote(conn, BUYER, q1['id'])
    assert result['quote']['status'] == 'selected'
    assert get_quote_by_id(conn, q2['id'])['status'] == 'discarded'
    po_draft = result['po_draft']
    assert po_draft['purchase_request_id'] == 100
    assert po_draft['supplier'] == 'Loja 1'
    # item recusado fica fora do rascunho de PO
    assert [i['purchase_request_item_id'] for i in po_draft['items']] == [1000]
    assert po_draft['items'][0]['unit_price'] == 10.0
    # R3: nenhuma PO criada automaticamente
    assert conn.execute('SELECT COUNT(*) FROM purchase_orders').fetchone()[0] == 0
    # requisição intacta (R1)
    assert conn.execute("SELECT status FROM purchase_requests WHERE id = 100").fetchone()[0] == 'sent_to_buyer'


def test_answer_rejected_after_final_status():
    conn = _conn()
    supplier = _supplier(conn)
    quote = create_quotes_for_request(conn, BUYER, 100, {'supplier_ids': [supplier['id']]})[0]
    answer_quote(conn, BUYER, quote['id'], {'items': [{'purchase_request_item_id': 1000, 'unit_price': 5.0}]})
    select_quote(conn, BUYER, quote['id'])
    with pytest.raises(ValueError, match='não pode receber resposta'):
        answer_quote(conn, BUYER, quote['id'], {'items': [{'purchase_request_item_id': 1000, 'unit_price': 4.0}]})


# ── envio por e-mail ──────────────────────────────────────────────────────────

def test_send_quote_emails_supplier_with_pdf():
    conn = _conn()
    supplier = _supplier(conn)
    quote = create_quotes_for_request(conn, BUYER, 100, {'supplier_ids': [supplier['id']]})[0]
    spy = _MailSpy()
    sent = send_quote_to_supplier(conn, BUYER, quote['id'], send_email_fn=spy)
    assert sent['status'] == 'sent'
    assert sent['sent_at']
    assert spy.sent[0]['to'] == 'vendas@loja.com'
    assert 'Luva Nitrílica' in spy.sent[0]['body']
    name, pdf = spy.sent[0]['attachments'][0]
    assert name.endswith('.pdf') and pdf.startswith(b'%PDF')
    event = conn.execute("SELECT * FROM purchase_events WHERE action = 'quote_sent'").fetchone()
    assert event['destination'] == 'vendas@loja.com'


def test_send_quote_requires_contact_email():
    conn = _conn()
    supplier = _supplier(conn, email='')
    quote = create_quotes_for_request(conn, BUYER, 100, {'supplier_ids': [supplier['id']]})[0]
    with pytest.raises(ValueError, match='e-mail'):
        send_quote_to_supplier(conn, BUYER, quote['id'], send_email_fn=_MailSpy())


def _approved_po(conn, status='approved'):
    conn.execute(
        "INSERT INTO purchase_orders (id, company_id, unit_id, status, po_number, supplier, supplier_cnpj) "
        f"VALUES (500, 1, 1, '{status}', 'PO-2026-001', 'Loja EPI', '11222333000144')"
    )
    conn.execute(
        "INSERT INTO purchase_order_items (purchase_order_id, company_id, epi_id, epi_name, ca, quantity, quantity_approved, unit_price) "
        "VALUES (500, 1, 5, 'Luva Nitrílica', '12345', 10, 10, 10.0)"
    )
    return 500


def test_send_po_only_when_approved_and_keeps_status():
    conn = _conn()
    _supplier(conn)
    po_id = _approved_po(conn, status='draft')
    with pytest.raises(ValueError, match='aprovadas'):
        send_po_to_supplier(conn, BUYER, po_id, send_email_fn=_MailSpy())
    conn.execute("UPDATE purchase_orders SET status = 'approved' WHERE id = 500")
    spy = _MailSpy()
    po = send_po_to_supplier(conn, BUYER, po_id, send_email_fn=spy)
    assert po['status'] == 'approved'  # máquina de estados intacta
    assert po['sent_to_supplier_at']
    assert po['sent_channel'] == 'email'
    # e-mail resolvido pelo CNPJ do fornecedor cadastrado
    assert spy.sent[0]['to'] == 'vendas@loja.com'
    assert 'R$ 100.00' in spy.sent[0]['body']


def test_send_po_accepts_explicit_to_email():
    conn = _conn()
    po_id = _approved_po(conn)
    spy = _MailSpy()
    send_po_to_supplier(conn, BUYER, po_id, {'to_email': 'outro@loja.com'}, send_email_fn=spy)
    assert spy.sent[0]['to'] == 'outro@loja.com'


def test_send_po_without_any_email_fails():
    conn = _conn()
    po_id = _approved_po(conn)  # fornecedor não cadastrado
    with pytest.raises(ValueError, match='e-mail'):
        send_po_to_supplier(conn, BUYER, po_id, send_email_fn=_MailSpy())


# ── confirmação manual e acompanhamento ──────────────────────────────────────

def test_confirmation_updates_parallel_field_only():
    conn = _conn()
    _supplier(conn)
    po_id = _approved_po(conn)
    po = register_po_confirmation(conn, BUYER, po_id, {'status': 'confirmed', 'delivery_forecast': '2026-07-20'})
    assert po['supplier_confirmation_status'] == 'confirmed'
    assert po['status'] == 'approved'  # status da PO intacto
    po = register_po_confirmation(conn, BUYER, po_id, {'status': 'delivery_update', 'carrier': 'Transportadora X', 'tracking_code': 'BR123'})
    assert po['supplier_confirmation_status'] == 'confirmed'  # delivery_update não sobrescreve
    tracking = fetch_po_tracking(conn, po_id)
    assert len(tracking['confirmations']) == 2
    assert tracking['confirmations'][0]['tracking_code'] == 'BR123'
    assert tracking['supplier_confirmation_status'] == 'confirmed'
    # fornecedor vinculado pelo CNPJ
    assert tracking['confirmations'][0]['supplier_id'] is not None


def test_confirmation_rejects_invalid_status():
    conn = _conn()
    po_id = _approved_po(conn)
    with pytest.raises(ValueError, match='inválido'):
        register_po_confirmation(conn, BUYER, po_id, {'status': 'maybe'})
