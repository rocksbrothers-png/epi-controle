"""Fase F0 do módulo de Compras: schema aditivo, mailer genérico e permissões.

Cobre exatamente o escopo da F0 do docs/PLANO_TECNICO_MODULO_COMPRAS.md:
  - ensure_procurement_supplier_tables cria as 7 tabelas novas (idempotente);
  - colunas aditivas em authorized_suppliers e purchase_orders com default
    que preserva o comportamento atual;
  - epi_backend.mailer.send_email (extraído da recuperação de senha);
  - permissões quotes:*/supplier_catalog:view por perfil;
  - migration 010 (RLS) registrada no runner.
"""

import sqlite3

import pytest

from core.schema import (
    _discover_migration_modules,
    _load_migration_module,
    ensure_procurement_supplier_tables,
)


# ── fixtures ──────────────────────────────────────────────────────────────────

def _conn():
    """Conexão SQLite com as tabelas-pai mínimas no formato ANTERIOR à F0."""
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        CREATE TABLE companies (id INTEGER PRIMARY KEY, name TEXT);
        CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT);
        CREATE TABLE units (id INTEGER PRIMARY KEY, company_id INTEGER);
        CREATE TABLE epis (id INTEGER PRIMARY KEY, company_id INTEGER, name TEXT);
        CREATE TABLE purchase_requests (id INTEGER PRIMARY KEY, company_id INTEGER);
        CREATE TABLE purchase_request_items (id INTEGER PRIMARY KEY, company_id INTEGER);
        CREATE TABLE purchase_order_files (id INTEGER PRIMARY KEY, company_id INTEGER);
        CREATE TABLE authorized_suppliers (
            id INTEGER PRIMARY KEY, company_id INTEGER, name TEXT,
            cnpj TEXT DEFAULT '', category TEXT DEFAULT '', contact_email TEXT DEFAULT '',
            notes TEXT DEFAULT '', active INTEGER DEFAULT 1, source TEXT DEFAULT 'manual',
            created_by_user_id INTEGER, created_at TEXT, updated_at TEXT
        );
        CREATE TABLE purchase_orders (
            id INTEGER PRIMARY KEY, company_id INTEGER, unit_id INTEGER,
            status TEXT DEFAULT 'draft', po_number TEXT DEFAULT '',
            supplier TEXT DEFAULT '', supplier_cnpj TEXT DEFAULT '',
            created_at TEXT, updated_at TEXT
        );
        """
    )
    return conn


def _tables(conn):
    rows = conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
    return {row['name'] for row in rows}


def _columns(conn, table):
    return {row['name'] for row in conn.execute(f'PRAGMA table_info({table})').fetchall()}


F0_TABLES = {
    'supplier_products',
    'purchase_quotes',
    'purchase_quote_items',
    'supplier_portal_links',
    'supplier_portal_audit_logs',
    'purchase_order_confirmations',
    'supplier_integrations',
}


# ── schema ────────────────────────────────────────────────────────────────────

def test_ensure_creates_all_f0_tables():
    conn = _conn()
    ensure_procurement_supplier_tables(conn)
    assert F0_TABLES <= _tables(conn)


def test_ensure_is_idempotent():
    conn = _conn()
    ensure_procurement_supplier_tables(conn)
    ensure_procurement_supplier_tables(conn)
    assert F0_TABLES <= _tables(conn)


def test_f0_tables_are_multi_tenant():
    conn = _conn()
    ensure_procurement_supplier_tables(conn)
    for table in sorted(F0_TABLES):
        assert 'company_id' in _columns(conn, table), f'{table} sem company_id'


def test_authorized_suppliers_additive_columns():
    conn = _conn()
    ensure_procurement_supplier_tables(conn)
    cols = _columns(conn, 'authorized_suppliers')
    assert {'phone', 'address', 'payment_terms', 'integration_level'} <= cols
    # default preserva comportamento: fornecedores existentes ficam no Nível 1
    conn.execute(
        "INSERT INTO authorized_suppliers (company_id, name, created_at, updated_at) "
        "VALUES (1, 'Loja EPI', '2026-07-08', '2026-07-08')"
    )
    row = conn.execute('SELECT integration_level, phone FROM authorized_suppliers').fetchone()
    assert row['integration_level'] == 'email'
    assert row['phone'] == ''


def test_purchase_orders_additive_columns_default_empty():
    conn = _conn()
    ensure_procurement_supplier_tables(conn)
    cols = _columns(conn, 'purchase_orders')
    assert {'sent_to_supplier_at', 'sent_channel', 'supplier_confirmation_status'} <= cols
    # POs existentes não ganham status de confirmação retroativo (regra intacta)
    conn.execute("INSERT INTO purchase_orders (company_id, created_at, updated_at) VALUES (1, 'x', 'x')")
    row = conn.execute('SELECT sent_to_supplier_at, sent_channel, supplier_confirmation_status FROM purchase_orders').fetchone()
    assert row['sent_to_supplier_at'] == ''
    assert row['sent_channel'] == ''
    assert row['supplier_confirmation_status'] == ''


def test_supplier_portal_links_stores_hash_not_token():
    conn = _conn()
    ensure_procurement_supplier_tables(conn)
    cols = _columns(conn, 'supplier_portal_links')
    assert 'token_hash' in cols
    assert 'token' not in cols


def test_quote_item_unique_per_quote_and_request_item():
    conn = _conn()
    ensure_procurement_supplier_tables(conn)
    conn.execute(
        "INSERT INTO purchase_quote_items (company_id, quote_id, purchase_request_item_id, created_at, updated_at) "
        "VALUES (1, 10, 20, 'x', 'x')"
    )
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO purchase_quote_items (company_id, quote_id, purchase_request_item_id, created_at, updated_at) "
            "VALUES (1, 10, 20, 'y', 'y')"
        )


# ── migration RLS (runner) ────────────────────────────────────────────────────

def test_migration_010_registered_and_valid():
    discovered = {module_name.rsplit('.', 1)[-1]: path for path, module_name in _discover_migration_modules()}
    assert '010_rls_procurement_supplier_tables' in discovered
    path = discovered['010_rls_procurement_supplier_tables']
    module = _load_migration_module(path, 'epi_backend.migrations.010_rls_procurement_supplier_tables')
    assert module.MIGRATION_ID == '010_rls_procurement_supplier_tables'
    assert callable(module.run)


def test_migration_010_sql_covers_all_f0_tables():
    from pathlib import Path
    sql = (
        Path(__file__).resolve().parent.parent
        / 'supabase' / 'migrations' / '20260708000000_rls_procurement_supplier_tables.sql'
    ).read_text(encoding='utf-8')
    for table in sorted(F0_TABLES):
        assert f"'{table}'" in sql, f'{table} fora da migration RLS'
    assert 'ENABLE ROW LEVEL SECURITY' in sql
    assert 'block_direct_api_access' in sql


# ── mailer genérico ───────────────────────────────────────────────────────────

def test_send_email_requires_smtp_config(monkeypatch):
    import epi_backend.config as config
    from epi_backend.mailer import send_email
    monkeypatch.setattr(config, 'SMTP_HOST', '')
    monkeypatch.setattr(config, 'SMTP_USER', '')
    with pytest.raises(ValueError, match='SMTP_HOST e SMTP_USER'):
        send_email('loja@example.com', 'Assunto', 'Corpo')


def test_send_email_requires_recipient(monkeypatch):
    import epi_backend.config as config
    from epi_backend.mailer import send_email
    monkeypatch.setattr(config, 'SMTP_HOST', 'smtp.example.com')
    monkeypatch.setattr(config, 'SMTP_USER', 'user@example.com')
    with pytest.raises(ValueError, match='Destinatário'):
        send_email('', 'Assunto', 'Corpo')


class _FakeSMTP:
    sent = []

    def __init__(self, host, port):
        self.host = host
        self.port = port

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def ehlo(self):
        pass

    def starttls(self):
        pass

    def login(self, user, password):
        pass

    def sendmail(self, from_addr, recipients, message):
        _FakeSMTP.sent.append({'from': from_addr, 'to': recipients, 'message': message})


def _configure_fake_smtp(monkeypatch):
    import epi_backend.config as config
    import epi_backend.mailer as mailer
    monkeypatch.setattr(config, 'SMTP_HOST', 'smtp.example.com')
    monkeypatch.setattr(config, 'SMTP_PORT', 587)
    monkeypatch.setattr(config, 'SMTP_USER', 'sistema@example.com')
    monkeypatch.setattr(config, 'SMTP_PASSWORD', 'secret')
    monkeypatch.setattr(config, 'SMTP_FROM', 'compras@example.com')
    monkeypatch.setattr(mailer.smtplib, 'SMTP', _FakeSMTP)
    _FakeSMTP.sent = []


def _parse_sent(sent):
    import email
    import email.policy
    return email.message_from_string(sent['message'], policy=email.policy.default)


def test_send_email_plain_text(monkeypatch):
    from epi_backend.mailer import send_email
    _configure_fake_smtp(monkeypatch)
    send_email('loja@example.com', 'Cotação 123', 'Segue a cotação.')
    assert len(_FakeSMTP.sent) == 1
    sent = _FakeSMTP.sent[0]
    assert sent['from'] == 'compras@example.com'
    assert sent['to'] == ['loja@example.com']
    parsed = _parse_sent(sent)
    assert parsed['Subject'] == 'Cotação 123'
    assert 'Segue a cotação.' in parsed.get_content()


def test_send_email_multiple_recipients_and_attachment(monkeypatch):
    from epi_backend.mailer import send_email
    _configure_fake_smtp(monkeypatch)
    send_email(
        ['a@example.com', 'b@example.com'],
        'PO-42',
        'Segue pedido.',
        html_body='<p>Segue pedido.</p>',
        attachments=[('po42.pdf', b'%PDF-fake')],
    )
    sent = _FakeSMTP.sent[0]
    assert sent['to'] == ['a@example.com', 'b@example.com']
    assert 'po42.pdf' in sent['message']


def test_recovery_email_delegates_to_mailer(monkeypatch):
    """Comportamento da recuperação de senha não muda (regra intacta)."""
    from epi_backend.mailer import send_email
    from modules.auth.service import send_recovery_email_smtp
    _configure_fake_smtp(monkeypatch)
    send_recovery_email_smtp('user@example.com', 'joao', 'TOKEN123')
    sent = _FakeSMTP.sent[0]
    assert sent['to'] == ['user@example.com']
    parsed = _parse_sent(sent)
    assert parsed['Subject'] == 'Recuperação de Senha — EPI Controle'
    body = parsed.get_content()
    assert 'TOKEN123' in body
    assert 'joao' in body


# ── permissões ────────────────────────────────────────────────────────────────

def test_buyer_manages_quotes():
    from core.permissions import PERMISSIONS
    assert 'quotes:view' in PERMISSIONS['buyer']
    assert 'quotes:manage' in PERMISSIONS['buyer']
    assert 'supplier_catalog:view' in PERMISSIONS['buyer']


def test_approver_views_but_does_not_manage_quotes():
    from core.permissions import PERMISSIONS
    assert 'quotes:view' in PERMISSIONS['approver']
    assert 'quotes:manage' not in PERMISSIONS['approver']


def test_admins_view_quotes():
    from core.permissions import PERMISSIONS
    for role in ('master_admin', 'general_admin', 'admin'):
        assert 'quotes:view' in PERMISSIONS[role], role


def test_employee_has_no_quote_permissions():
    from core.permissions import PERMISSIONS
    assert 'quotes:view' not in PERMISSIONS['employee']
    assert 'quotes:manage' not in PERMISSIONS['employee']
