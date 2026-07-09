"""Fase F2 do módulo de Compras — Portal do Fornecedor (Nível 2).

Valida o ciclo de vida do link tokenizado (hash armazenado, expiração,
revogação, escopo de 1 entidade), as ações do fornecedor via portal
(responder cotação com anexo, confirmar pedido, atualizar entrega) e a
auditoria em supplier_portal_audit_logs — sem alterar nenhuma regra do
fluxo interno (a resposta usa o mesmo answer_quote do Nível 1).
"""

import base64
import sqlite3
from datetime import datetime, timedelta, timezone

import pytest

from core.schema import ensure_procurement_supplier_tables
from modules.purchases.quotes_service import (
    answer_quote,
    create_authorized_supplier,
    create_quotes_for_request,
    fetch_quote_items,
    get_quote_by_id,
)
from modules.purchases.supplier_portal_service import (
    create_supplier_portal_link,
    fetch_quote_files,
    fetch_supplier_portal_links,
    get_portal_payload,
    portal_answer_quote,
    portal_confirm_po,
    portal_link_url,
    resolve_portal_token,
    revoke_supplier_portal_link,
    send_portal_link_email,
)

UTC = timezone.utc

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


def _supplier(conn, email='vendas@loja.com'):
    return create_authorized_supplier(conn, BUYER, {
        'name': 'Loja EPI', 'contact_email': email, 'cnpj': '11222333000144',
    })


def _quote(conn, supplier):
    return create_quotes_for_request(conn, BUYER, 100, {'supplier_ids': [supplier['id']]})[0]


def _po(conn):
    conn.execute(
        "INSERT INTO purchase_orders (id, company_id, unit_id, status, po_number, supplier, supplier_cnpj) "
        "VALUES (500, 1, 1, 'approved', 'PO-2026-001', 'Loja EPI', '11222333000144')"
    )
    conn.execute(
        "INSERT INTO purchase_order_items (purchase_order_id, company_id, epi_id, epi_name, quantity_approved, unit_price) "
        "VALUES (500, 1, 5, 'Luva Nitrílica', 10, 10.0)"
    )
    return 500


class _MailSpy:
    def __init__(self):
        self.sent = []

    def __call__(self, to_email, subject, body, html_body=None, attachments=None, reply_to=''):
        self.sent.append({'to': to_email, 'subject': subject, 'body': body})


PDF_B64 = base64.b64encode(b'%PDF-proposta-fake').decode('ascii')


# ── ciclo de vida do link ─────────────────────────────────────────────────────

def test_link_stores_hash_never_plain_token():
    conn = _conn()
    quote = _quote(conn, _supplier(conn))
    link, token = create_supplier_portal_link(conn, BUYER, 'quote', quote['id'])
    assert len(token) >= 32
    assert link['token_hash'] != token
    assert token not in str(dict(link))
    stored = conn.execute('SELECT token_hash FROM supplier_portal_links WHERE id = ?', (link['id'],)).fetchone()
    assert stored['token_hash'] == link['token_hash']


def test_resolve_valid_token_and_audit():
    conn = _conn()
    quote = _quote(conn, _supplier(conn))
    link, token = create_supplier_portal_link(conn, BUYER, 'quote', quote['id'])
    resolved = resolve_portal_token(conn, token, ip_address='1.2.3.4')
    assert resolved['id'] == link['id']
    assert resolved['entity_type'] == 'quote'
    updated = conn.execute('SELECT last_access_at, access_attempts FROM supplier_portal_links WHERE id = ?', (link['id'],)).fetchone()
    assert updated['last_access_at']
    assert updated['access_attempts'] == 1


def test_resolve_rejects_wrong_expired_and_revoked():
    conn = _conn()
    quote = _quote(conn, _supplier(conn))
    link, token = create_supplier_portal_link(conn, BUYER, 'quote', quote['id'])
    with pytest.raises(PermissionError):
        resolve_portal_token(conn, 'token-invalido-token-invalido')
    # expirado
    past = (datetime.now(UTC) - timedelta(days=1)).isoformat()
    conn.execute('UPDATE supplier_portal_links SET expires_at = ? WHERE id = ?', (past, link['id']))
    with pytest.raises(PermissionError):
        resolve_portal_token(conn, token)
    denied = conn.execute("SELECT * FROM supplier_portal_audit_logs WHERE action = 'access_denied'").fetchall()
    assert len(denied) == 1 and denied[0]['detail'] == 'expired'
    # revogado
    link2, token2 = create_supplier_portal_link(conn, BUYER, 'quote', quote['id'])
    revoke_supplier_portal_link(conn, BUYER, 1, link2['id'])
    with pytest.raises(PermissionError):
        resolve_portal_token(conn, token2)


def test_new_link_revokes_previous_open_link():
    conn = _conn()
    quote = _quote(conn, _supplier(conn))
    _, token1 = create_supplier_portal_link(conn, BUYER, 'quote', quote['id'])
    create_supplier_portal_link(conn, BUYER, 'quote', quote['id'])
    with pytest.raises(PermissionError):
        resolve_portal_token(conn, token1)
    links = fetch_supplier_portal_links(conn, 1, 'quote', quote['id'])
    assert len(links) == 2
    assert sum(1 for l in links if not l['revoked_at']) == 1


def test_po_link_requires_registered_supplier():
    conn = _conn()
    po_id = _po(conn)  # fornecedor NÃO cadastrado
    with pytest.raises(ValueError, match='fornecedor'):
        create_supplier_portal_link(conn, BUYER, 'purchase_order', po_id)
    _supplier(conn)
    link, _ = create_supplier_portal_link(conn, BUYER, 'purchase_order', po_id)
    assert link['entity_type'] == 'purchase_order'


# ── payload (escopo mínimo) ───────────────────────────────────────────────────

def test_quote_payload_has_scoped_fields_only():
    conn = _conn()
    quote = _quote(conn, _supplier(conn))
    link, token = create_supplier_portal_link(conn, BUYER, 'quote', quote['id'])
    payload = get_portal_payload(conn, resolve_portal_token(conn, token))
    assert payload['entity_type'] == 'quote'
    assert payload['company_name'] == 'Empresa A'
    assert payload['quote']['items'][0]['epi_name'] == 'Luva Nitrílica'
    assert 'company_id' not in payload['quote']
    assert 'created_by_user_id' not in payload['quote']


def test_po_payload_lists_items_and_confirmations():
    conn = _conn()
    _supplier(conn)
    po_id = _po(conn)
    link, token = create_supplier_portal_link(conn, BUYER, 'purchase_order', po_id)
    payload = get_portal_payload(conn, resolve_portal_token(conn, token))
    assert payload['purchase_order']['po_number'] == 'PO-2026-001'
    assert payload['purchase_order']['items'][0]['quantity'] == 10


# ── ações do fornecedor ───────────────────────────────────────────────────────

def test_portal_answer_quote_with_proposal_attachment():
    conn = _conn()
    supplier = _supplier(conn)
    quote = _quote(conn, supplier)
    spy = _MailSpy()
    link = send_portal_link_email(conn, BUYER, 'quote', quote['id'], base_url='https://epi.example.com', send_email_fn=spy)
    resolved = dict(link)
    answered = portal_answer_quote(conn, resolved, {
        'freight_value': 12.5,
        'items': [{'quote_item_id': fetch_quote_items(conn, quote['id'])[0]['id'], 'unit_price': 9.9, 'lead_time_days': 4}],
        'proposal': {'file_name': 'proposta.pdf', 'file_type': 'application/pdf', 'content_base64': PDF_B64},
    }, ip_address='9.9.9.9', user_agent='TestBrowser')
    assert answered['status'] == 'answered'
    assert answered['channel'] == 'portal'
    files = fetch_quote_files(conn, quote['id'])
    assert files[0]['file_name'] == 'proposta.pdf'
    assert files[0]['source'] == 'supplier_portal'
    audit = conn.execute("SELECT * FROM supplier_portal_audit_logs WHERE action = 'quote_answered'").fetchone()
    assert audit['ip_address'] == '9.9.9.9'
    event = conn.execute("SELECT * FROM purchase_events WHERE action = 'quote_answered'").fetchone()
    assert event['actor_role'] == 'supplier_portal'
    assert 'Loja EPI' in event['actor_name']


def test_portal_answer_rejects_bad_proposal():
    conn = _conn()
    supplier = _supplier(conn)
    quote = _quote(conn, supplier)
    link, token = create_supplier_portal_link(conn, BUYER, 'quote', quote['id'])
    resolved = resolve_portal_token(conn, token)
    base_payload = {'items': [{'quote_item_id': fetch_quote_items(conn, quote['id'])[0]['id'], 'unit_price': 5.0}]}
    with pytest.raises(ValueError, match='Tipo de arquivo'):
        portal_answer_quote(conn, resolved, dict(base_payload, proposal={
            'file_name': 'virus.exe', 'file_type': 'application/x-msdownload', 'content_base64': PDF_B64,
        }))
    with pytest.raises(ValueError, match='inválido'):
        portal_answer_quote(conn, resolved, dict(base_payload, proposal={
            'file_name': 'p.pdf', 'file_type': 'application/pdf', 'content_base64': '###nao-e-base64###',
        }))


def test_quote_link_cannot_confirm_po_and_vice_versa():
    conn = _conn()
    supplier = _supplier(conn)
    quote = _quote(conn, supplier)
    po_id = _po(conn)
    quote_link, _ = create_supplier_portal_link(conn, BUYER, 'quote', quote['id'])
    po_link, _ = create_supplier_portal_link(conn, BUYER, 'purchase_order', po_id)
    with pytest.raises(PermissionError):
        portal_confirm_po(conn, quote_link, {'status': 'confirmed'})
    with pytest.raises(PermissionError):
        portal_answer_quote(conn, po_link, {'items': [{'quote_item_id': 1, 'unit_price': 1}]})


def test_portal_confirm_po_records_source_portal():
    conn = _conn()
    _supplier(conn)
    po_id = _po(conn)
    link, token = create_supplier_portal_link(conn, BUYER, 'purchase_order', po_id)
    resolved = resolve_portal_token(conn, token)
    po = portal_confirm_po(conn, resolved, {'status': 'confirmed', 'delivery_forecast': '2026-07-20'})
    assert po['supplier_confirmation_status'] == 'confirmed'
    assert po['status'] == 'approved'  # máquina de estados intacta
    row = conn.execute('SELECT source FROM purchase_order_confirmations WHERE purchase_order_id = ?', (po_id,)).fetchone()
    assert row['source'] == 'portal'
    po = portal_confirm_po(conn, resolved, {'status': 'delivery_update', 'carrier': 'TransX', 'tracking_code': 'BR9'})
    assert po['supplier_confirmation_status'] == 'confirmed'


# ── envio do link por e-mail ─────────────────────────────────────────────────

def test_send_portal_link_emails_url_and_marks_quote_sent():
    conn = _conn()
    supplier = _supplier(conn)
    quote = _quote(conn, supplier)
    spy = _MailSpy()
    link = send_portal_link_email(conn, BUYER, 'quote', quote['id'], base_url='https://epi.example.com', send_email_fn=spy)
    assert spy.sent[0]['to'] == 'vendas@loja.com'
    assert 'https://epi.example.com/fornecedor/' in spy.sent[0]['body']
    # o corpo carrega o token, mas o banco só tem o hash
    token_in_mail = spy.sent[0]['body'].split('/fornecedor/')[1].split()[0]
    assert token_in_mail != link['token_hash']
    updated = get_quote_by_id(conn, quote['id'])
    assert updated['status'] == 'sent'
    assert updated['channel'] == 'portal'
    event = conn.execute("SELECT * FROM purchase_events WHERE action = 'quote_sent'").fetchone()
    assert event['destination'] == 'vendas@loja.com'


def test_send_portal_link_po_requires_approved_status():
    conn = _conn()
    _supplier(conn)
    po_id = _po(conn)
    conn.execute("UPDATE purchase_orders SET status = 'draft' WHERE id = ?", (po_id,))
    with pytest.raises(ValueError, match='aprovadas'):
        send_portal_link_email(conn, BUYER, 'purchase_order', po_id, base_url='https://x.com', send_email_fn=_MailSpy())
    conn.execute("UPDATE purchase_orders SET status = 'approved' WHERE id = ?", (po_id,))
    spy = _MailSpy()
    send_portal_link_email(conn, BUYER, 'purchase_order', po_id, base_url='https://x.com', send_email_fn=spy)
    po = conn.execute('SELECT sent_channel, sent_to_supplier_at FROM purchase_orders WHERE id = ?', (po_id,)).fetchone()
    assert po['sent_channel'] == 'portal'
    assert po['sent_to_supplier_at']


def test_send_portal_link_requires_contact_email_and_base_url():
    conn = _conn()
    supplier = _supplier(conn, email='')
    quote = _quote(conn, supplier)
    with pytest.raises(ValueError, match='e-mail'):
        send_portal_link_email(conn, BUYER, 'quote', quote['id'], base_url='https://x.com', send_email_fn=_MailSpy())


def test_portal_link_url_format():
    assert portal_link_url('https://epi.example.com/', 'abc123') == 'https://epi.example.com/fornecedor/abc123'


# ── nível 1 continua intacto ─────────────────────────────────────────────────

def test_manual_answer_still_works_after_portal_send():
    """Fornecedor pode responder por e-mail mesmo com link de portal aberto."""
    conn = _conn()
    supplier = _supplier(conn)
    quote = _quote(conn, supplier)
    send_portal_link_email(conn, BUYER, 'quote', quote['id'], base_url='https://x.com', send_email_fn=_MailSpy())
    answered = answer_quote(conn, BUYER, quote['id'], {
        'items': [{'quote_item_id': fetch_quote_items(conn, quote['id'])[0]['id'], 'unit_price': 7.7}],
    })
    assert answered['status'] == 'answered'
