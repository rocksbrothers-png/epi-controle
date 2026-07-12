"""Follow-ups da migração Master → Administrador Geral.

Cobre:
  - tenant_domains: registro/verificação CNAME+TXT/ativação, unicidade entre
    tenants, resolução de tenant pela tabela e bloqueio com assinatura suspensa;
  - convite por e-mail ao Owner no provisionamento (token de primeiro acesso);
  - 2FA TOTP: geração/ativação/desativação e desafio no login.
"""

import sqlite3
import time

import pytest

import modules.tenant.domains_service as domains
from core.totp import generate_totp_secret, otpauth_uri, totp_code, verify_totp
from modules.auth.service import (
    authenticate_login,
    disable_user_totp,
    enable_user_totp,
    get_user_totp_state,
    setup_user_totp,
)
from modules.companies.service import provision_tenant_structure
from modules.tenant.service import resolve_tenant_by_host


# ── infra ─────────────────────────────────────────────────────────────────────

def _conn():
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        CREATE TABLE companies (
            id INTEGER PRIMARY KEY, name TEXT, legal_name TEXT DEFAULT '', cnpj TEXT,
            active INTEGER DEFAULT 1, logo_type TEXT DEFAULT '', plan_name TEXT DEFAULT 'start',
            user_limit INTEGER DEFAULT 25, license_status TEXT DEFAULT 'active',
            contract_start TEXT DEFAULT '', contract_end TEXT DEFAULT '', monthly_value REAL DEFAULT 0,
            addendum_enabled INTEGER DEFAULT 0, commercial_notes TEXT DEFAULT '', slug TEXT,
            subdomain TEXT, custom_domain TEXT, login_logo_type TEXT DEFAULT '',
            primary_color TEXT DEFAULT '#1565C0', secondary_color TEXT DEFAULT '#42A5F5',
            accent_color TEXT DEFAULT '#FF6F00', default_language TEXT DEFAULT 'pt-BR',
            favicon_type TEXT DEFAULT '', institutional_message TEXT DEFAULT '',
            contact_email TEXT DEFAULT '', contact_phone TEXT DEFAULT '', website TEXT DEFAULT '',
            theme_json TEXT DEFAULT '{}', state_registration TEXT DEFAULT '',
            municipal_registration TEXT DEFAULT '', address TEXT DEFAULT '',
            whatsapp TEXT DEFAULT '', display_name TEXT DEFAULT '',
            timezone TEXT DEFAULT 'America/Sao_Paulo',
            onboarding_completed INTEGER DEFAULT 1, onboarding_completed_at TEXT DEFAULT ''
        );
        CREATE TABLE users (
            id INTEGER PRIMARY KEY, username TEXT, password TEXT DEFAULT '',
            full_name TEXT DEFAULT '', role TEXT, company_id INTEGER, active INTEGER DEFAULT 1,
            linked_employee_id INTEGER, email TEXT,
            recovery_token_hash TEXT, recovery_token_expires_at TEXT,
            totp_secret TEXT, totp_enabled INTEGER DEFAULT 0, terms_accepted_at TEXT
        );
        CREATE TABLE units (
            id INTEGER PRIMARY KEY, company_id INTEGER, name TEXT, unit_type TEXT,
            city TEXT DEFAULT '', notes TEXT DEFAULT ''
        );
        CREATE TABLE tenant_domains (
            id INTEGER PRIMARY KEY, company_id INTEGER NOT NULL, domain TEXT NOT NULL,
            domain_type TEXT NOT NULL DEFAULT 'custom_domain',
            verification_token TEXT NOT NULL DEFAULT '',
            verification_status TEXT NOT NULL DEFAULT 'pending',
            ssl_status TEXT NOT NULL DEFAULT 'pending',
            is_primary INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT '', verified_at TEXT NOT NULL DEFAULT ''
        );
        INSERT INTO companies (id, name, legal_name, cnpj) VALUES
            (1, 'ACME', 'ACME LTDA', '04.252.011/0001-10'),
            (2, 'Beta', 'Beta SA', '11.222.333/0001-81');
    """)
    conn.commit()
    return conn


# ── TOTP puro ─────────────────────────────────────────────────────────────────

def test_totp_roundtrip():
    secret = generate_totp_secret()
    now = time.time()
    code = totp_code(secret, now)
    assert verify_totp(secret, code, timestamp=now)


def test_totp_rejects_wrong_and_malformed_codes():
    secret = generate_totp_secret()
    now = time.time()
    good = totp_code(secret, now)
    bad = str((int(good) + 1) % 1000000).zfill(6)
    assert not verify_totp(secret, bad, timestamp=now)
    assert not verify_totp(secret, '', timestamp=now)
    assert not verify_totp(secret, 'abc123', timestamp=now)
    assert not verify_totp('', good, timestamp=now)


def test_totp_accepts_adjacent_window():
    secret = generate_totp_secret()
    now = time.time()
    previous_code = totp_code(secret, now - 30)
    assert verify_totp(secret, previous_code, window=1, timestamp=now)


def test_otpauth_uri_contains_secret_and_issuer():
    uri = otpauth_uri('ABC234DEF567', 'owner@acme.com.br')
    assert uri.startswith('otpauth://totp/')
    assert 'secret=ABC234DEF567' in uri and 'issuer=EPI%20Controle' in uri


# ── 2FA no serviço de auth ────────────────────────────────────────────────────

def _make_user(conn, username='owner@acme.com.br', role='general_admin', company_id=1):
    from core.security import hash_password
    conn.execute(
        'INSERT INTO users (username, password, full_name, role, company_id, active) VALUES (?, ?, ?, ?, ?, 1)',
        (username, hash_password('Senha@123'), 'Owner', role, company_id),
    )
    return conn.execute('SELECT id FROM users WHERE username = ?', (username,)).fetchone()['id']


def test_setup_enable_disable_totp():
    conn = _conn()
    uid = _make_user(conn)
    result = setup_user_totp(conn, uid, 'owner@acme.com.br')
    assert result['secret'] and result['otpauth_uri'].startswith('otpauth://')
    assert not get_user_totp_state(conn, uid)['enabled']
    with pytest.raises(ValueError):
        enable_user_totp(conn, uid, '000000')
    enable_user_totp(conn, uid, totp_code(result['secret']))
    assert get_user_totp_state(conn, uid)['enabled']
    with pytest.raises(ValueError):
        setup_user_totp(conn, uid, 'owner@acme.com.br')  # exige desativar antes
    disable_user_totp(conn, uid, totp_code(result['secret']))
    state = get_user_totp_state(conn, uid)
    assert not state['enabled'] and not state['secret']


def _dict_rows(conn):
    """authenticate_login usa row.get(); espelha o row factory dict do backend."""
    conn.row_factory = lambda cursor, row: {d[0]: row[i] for i, d in enumerate(cursor.description)}
    return conn


def test_login_requires_totp_when_enabled(monkeypatch):
    import modules.auth.service as auth_service
    monkeypatch.setattr(auth_service, 'enforce_company_block_rules', lambda *_a, **_k: None)
    monkeypatch.setattr(auth_service, 'actor_operational_unit_id', lambda *_a, **_k: None)
    conn = _dict_rows(_conn())
    uid = _make_user(conn)
    secret = setup_user_totp(conn, uid, 'owner@acme.com.br')['secret']
    enable_user_totp(conn, uid, totp_code(secret))

    # sem código → desafio
    result, status, error = authenticate_login(conn, 'owner@acme.com.br', 'Senha@123')
    assert result is None and status == 401 and error['code'] == 'TOTP_REQUIRED'
    # código errado → inválido
    result, status, error = authenticate_login(conn, 'owner@acme.com.br', 'Senha@123', totp_code='000000')
    assert result is None and status == 401 and error['code'] == 'TOTP_INVALID'
    # código correto → sucesso
    result, status, error = authenticate_login(conn, 'owner@acme.com.br', 'Senha@123', totp_code=totp_code(secret))
    assert error is None and status == 200 and result['user']['id'] == uid


def test_login_without_totp_keeps_working(monkeypatch):
    import modules.auth.service as auth_service
    monkeypatch.setattr(auth_service, 'enforce_company_block_rules', lambda *_a, **_k: None)
    monkeypatch.setattr(auth_service, 'actor_operational_unit_id', lambda *_a, **_k: None)
    conn = _dict_rows(_conn())
    uid = _make_user(conn)
    result, status, error = authenticate_login(conn, 'owner@acme.com.br', 'Senha@123')
    assert error is None and status == 200 and result['user']['id'] == uid


# ── convite ao Owner ──────────────────────────────────────────────────────────

def test_provision_sends_owner_invite(monkeypatch):
    sent = {}

    def fake_send_email(to_email, subject, body, **_k):
        sent['to'] = to_email
        sent['subject'] = subject
        sent['body'] = body

    import epi_backend.mailer as mailer
    monkeypatch.setattr(mailer, 'send_email', fake_send_email)
    conn = _conn()
    details = provision_tenant_structure(conn, 1, {
        'general_admin_email': 'owner@acme.com.br', 'general_admin_name': 'Owner',
    })
    assert sent['to'] == 'owner@acme.com.br'
    assert 'Administrador Geral' in sent['subject']
    assert 'chave' in sent['body'].lower()
    owner = conn.execute("SELECT recovery_token_hash, email FROM users WHERE username = 'owner@acme.com.br'").fetchone()
    assert owner['recovery_token_hash']  # token de primeiro acesso emitido
    assert owner['email'] == 'owner@acme.com.br'
    invite_detail = next(d for d in details if d['field'] == 'Administrador Geral')
    assert 'enviado por e-mail' in invite_detail['after']


def test_provision_survives_smtp_failure(monkeypatch):
    import epi_backend.mailer as mailer

    def boom(*_a, **_k):
        raise ValueError('SMTP indisponível')

    monkeypatch.setattr(mailer, 'send_email', boom)
    conn = _conn()
    details = provision_tenant_structure(conn, 1, {'general_admin_email': 'owner@acme.com.br'})
    owner = conn.execute("SELECT id, recovery_token_hash FROM users WHERE username = 'owner@acme.com.br'").fetchone()
    assert owner is not None and owner['recovery_token_hash']
    invite_detail = next(d for d in details if d['field'] == 'Administrador Geral')
    assert 'falha no envio' in invite_detail['after']


# ── tenant_domains ────────────────────────────────────────────────────────────

def test_register_platform_subdomain_is_auto_verified():
    conn = _conn()
    record = domains.register_company_domain(conn, 1, 'acme', 'platform_subdomain')
    assert record['verification_status'] == 'verified'
    assert record['full_host'].startswith('acme.')
    assert conn.execute('SELECT subdomain FROM companies WHERE id = 1').fetchone()[0] == 'acme'


def test_register_custom_domain_pending_with_token():
    conn = _conn()
    record = domains.register_company_domain(conn, 1, 'epi.acme.com.br', 'custom_subdomain')
    assert record['verification_status'] == 'pending'
    assert record['verification_token'].startswith('epi-verify-')


def test_domain_unique_across_tenants():
    conn = _conn()
    domains.register_company_domain(conn, 1, 'epi.acme.com.br', 'custom_domain')
    with pytest.raises(ValueError):
        domains.register_company_domain(conn, 2, 'epi.acme.com.br', 'custom_domain')


def test_subdomain_conflicts_with_legacy_column():
    conn = _conn()
    conn.execute("UPDATE companies SET subdomain = 'beta' WHERE id = 2")
    with pytest.raises(ValueError):
        domains.register_company_domain(conn, 1, 'beta', 'platform_subdomain')


def test_verify_requires_cname_and_txt(monkeypatch):
    conn = _conn()
    record = domains.register_company_domain(conn, 1, 'epi.acme.com.br', 'custom_domain')
    token = record['verification_token']

    # CNAME ausente → falha e marca failed
    monkeypatch.setattr(domains, 'dns_lookup', lambda *_a, **_k: [])
    with pytest.raises(ValueError):
        domains.verify_company_domain(conn, 1, record['id'])
    assert conn.execute('SELECT verification_status FROM tenant_domains WHERE id = ?', (record['id'],)).fetchone()[0] == 'failed'

    # CNAME ok mas TXT ausente → falha por propriedade
    def dns_cname_only(name, rtype='CNAME', **_k):
        return [domains.cname_target()] if rtype == 'CNAME' else []
    monkeypatch.setattr(domains, 'dns_lookup', dns_cname_only)
    with pytest.raises(ValueError):
        domains.verify_company_domain(conn, 1, record['id'])

    # CNAME + TXT → verificado; SSL best-effort
    def dns_full(name, rtype='CNAME', **_k):
        return [domains.cname_target()] if rtype == 'CNAME' else [token]
    monkeypatch.setattr(domains, 'dns_lookup', dns_full)
    monkeypatch.setattr(domains, 'check_ssl_active', lambda *_a, **_k: True)
    verified = domains.verify_company_domain(conn, 1, record['id'])
    assert verified['verification_status'] == 'verified' and verified['ssl_status'] == 'active'
    assert conn.execute('SELECT custom_domain FROM companies WHERE id = 1').fetchone()[0] == 'epi.acme.com.br'


def test_verify_blocked_when_subscription_suspended(monkeypatch):
    conn = _conn()
    record = domains.register_company_domain(conn, 1, 'epi.acme.com.br', 'custom_domain')
    conn.execute("UPDATE companies SET license_status = 'suspended' WHERE id = 1")
    with pytest.raises(PermissionError):
        domains.verify_company_domain(conn, 1, record['id'])


def test_set_primary_requires_verified():
    conn = _conn()
    pending = domains.register_company_domain(conn, 1, 'epi.acme.com.br', 'custom_domain')
    with pytest.raises(ValueError):
        domains.set_primary_company_domain(conn, 1, pending['id'])
    verified = domains.register_company_domain(conn, 1, 'acme', 'platform_subdomain')
    result = domains.set_primary_company_domain(conn, 1, verified['id'])
    assert result['is_primary'] == 1


def test_delete_clears_legacy_routing():
    conn = _conn()
    record = domains.register_company_domain(conn, 1, 'acme', 'platform_subdomain')
    domains.delete_company_domain(conn, 1, record['id'])
    assert conn.execute('SELECT subdomain FROM companies WHERE id = 1').fetchone()[0] is None
    assert conn.execute('SELECT COUNT(*) FROM tenant_domains').fetchone()[0] == 0


def test_domain_scoped_to_own_company():
    conn = _conn()
    record = domains.register_company_domain(conn, 1, 'epi.acme.com.br', 'custom_domain')
    assert domains.get_company_domain(conn, 2, record['id']) is None
    with pytest.raises(ValueError):
        domains.delete_company_domain(conn, 2, record['id'])


# ── resolução de tenant pela tabela ───────────────────────────────────────────

def test_resolve_tenant_by_host_uses_tenant_domains(monkeypatch):
    conn = _conn()
    record = domains.register_company_domain(conn, 1, 'epi.acme.com.br', 'custom_domain')
    conn.execute(
        "UPDATE tenant_domains SET verification_status = 'verified' WHERE id = ?", (record['id'],)
    )
    resolved = resolve_tenant_by_host(conn, 'epi.acme.com.br')
    assert resolved and resolved['tenant']['id'] == 1
    assert resolved['match_type'] == 'tenant_domain'


def test_resolve_tenant_ignores_unverified_domains():
    conn = _conn()
    domains.register_company_domain(conn, 1, 'epi.acme.com.br', 'custom_domain')  # pending
    resolved = resolve_tenant_by_host(conn, 'epi.acme.com.br')
    assert resolved is None


def test_resolve_platform_subdomain_via_table():
    conn = _conn()
    domains.register_company_domain(conn, 1, 'acme', 'platform_subdomain')
    conn.execute('UPDATE companies SET subdomain = NULL WHERE id = 1')  # força uso da tabela
    resolved = resolve_tenant_by_host(conn, f'acme.{domains.platform_base_domain()}')
    assert resolved and resolved['tenant']['id'] == 1


def test_no_cross_tenant_branding_by_host():
    conn = _conn()
    domains.register_company_domain(conn, 1, 'acme', 'platform_subdomain')
    domains.register_company_domain(conn, 2, 'beta', 'platform_subdomain')
    a = resolve_tenant_by_host(conn, f'acme.{domains.platform_base_domain()}')
    b = resolve_tenant_by_host(conn, f'beta.{domains.platform_base_domain()}')
    assert a['tenant']['id'] == 1 and b['tenant']['id'] == 2
