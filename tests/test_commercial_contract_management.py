import base64
import sqlite3

import server_postgres as sp


def make_connection():
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.execute(
        '''
        CREATE TABLE companies (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            legal_name TEXT NOT NULL DEFAULT '',
            cnpj TEXT NOT NULL DEFAULT '',
            logo_type TEXT NOT NULL DEFAULT '',
            plan_name TEXT NOT NULL DEFAULT 'start',
            user_limit INTEGER NOT NULL DEFAULT 10,
            license_status TEXT NOT NULL DEFAULT 'active',
            active INTEGER NOT NULL DEFAULT 1,
            commercial_notes TEXT NOT NULL DEFAULT '',
            contract_start TEXT NOT NULL DEFAULT '',
            contract_end TEXT NOT NULL DEFAULT '',
            monthly_value REAL NOT NULL DEFAULT 0,
            addendum_enabled INTEGER NOT NULL DEFAULT 0
        )
        '''
    )
    conn.execute('CREATE TABLE app_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)')
    conn.execute('CREATE TABLE users (id INTEGER PRIMARY KEY, company_id INTEGER, role TEXT, active INTEGER NOT NULL DEFAULT 1)')
    conn.execute("INSERT INTO companies (id, name, legal_name, cnpj, plan_name, user_limit, license_status, active, contract_start, contract_end, commercial_notes) VALUES (1, 'DOF Brasil', 'DOF LTDA', '11.222.333/0001-81', 'enterprise', 120, 'active', 1, '2026-01-01', '2026-12-31', 'Contrato ativo')")
    sp.ensure_commercial_contract_tables(conn)
    return conn


def actor():
    return {'id': 999, 'role': 'master_admin', 'company_id': None, 'full_name': 'Master'}


def patch_settings(monkeypatch):
    monkeypatch.setattr(sp, 'get_commercial_settings', lambda _conn: sp.default_commercial_settings())
    monkeypatch.setattr(sp, 'get_platform_brand', lambda _conn: {'display_name': 'LIVA', 'legal_name': 'LIVA LTDA', 'cnpj': '24.940.022/0001-08'})


def test_create_and_save_commercial_contract_draft(monkeypatch):
    patch_settings(monkeypatch)
    conn = make_connection()
    contract = sp.get_or_create_commercial_contract(conn, actor(), 1)
    assert contract['status'] == 'draft'
    updated = sp.save_commercial_contract(conn, actor(), {
        'company_id': 1,
        'status': 'draft',
        'contract_number': 'CTR-00001',
        'issue_date': '2026-04-23',
        'clauses_text': 'Texto editável SaaS',
        'contractor_email': 'cliente@dof.com',
        'provider_email': 'comercial@liva.com',
    })
    assert updated['contract_number'] == 'CTR-00001'
    assert updated['clauses_text'] == 'Texto editável SaaS'


def test_generate_sign_upload_and_email_flow_updates_status(monkeypatch):
    patch_settings(monkeypatch)
    conn = make_connection()
    generated = sp.generate_commercial_contract_pdf(conn, actor(), 1)
    assert generated['status'] == 'generated'
    signed = sp.sign_commercial_contract(conn, actor(), {'company_id': 1, 'signature_name': 'Carlos', 'signature_data': 'HASH-123'})
    assert signed['status'] == 'signed'
    payload = base64.b64encode(b'%PDF-1.4 signed').decode('ascii')
    uploaded = sp.upload_signed_contract_file(conn, actor(), {'company_id': 1, 'file_name': 'contrato-assinado.pdf', 'file_mime': 'application/pdf', 'file_base64': payload})
    assert uploaded['signed_file_name'] == 'contrato-assinado.pdf'
    emailed = sp.send_commercial_contract_email(conn, actor(), {'company_id': 1, 'email_to': 'cliente@dof.com', 'subject': 'Contrato', 'body': 'Segue contrato'})
    assert emailed['status'] == 'sent'
    assert emailed['last_email_to'] == 'cliente@dof.com'
