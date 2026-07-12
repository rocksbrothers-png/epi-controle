"""Migração da configuração da empresa: Master → Administrador Geral.

Cobre os três perfis da matriz de permissões:
  - Administrador Geral (Owner da tenant): configura a própria empresa via
    GET/PUT /api/my-company e conclui o assistente de implantação.
  - Administrador Master: não altera identidade visual/dados cadastrais pela
    rota operacional (PUT /api/companies/{id}); usa o suporte auditado
    (POST /api/companies/{id}/support-update) com justificativa obrigatória.
  - Administrador Local (admin): não acessa a configuração da empresa.
"""

import io
import json
import sqlite3
from urllib.parse import urlparse

import pytest

import modules.companies.routes as companies_routes
import modules.company_settings.routes as routes
from core.permissions import PERMISSIONS
from modules.companies.service import (
    MASTER_PROTECTED_COMPANY_FIELDS,
    generate_tenant_slug,
    mark_company_onboarding_pending,
    provision_tenant_structure,
)
from modules.company_settings.service import (
    PROFILE_EDITABLE_FIELDS,
    complete_onboarding,
    get_my_company_profile,
    summarize_profile_changes,
    update_my_company,
    validate_my_company_payload,
)


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
            theme_json TEXT DEFAULT '{}',
            state_registration TEXT DEFAULT '', municipal_registration TEXT DEFAULT '',
            address TEXT DEFAULT '', whatsapp TEXT DEFAULT '', display_name TEXT DEFAULT '',
            timezone TEXT DEFAULT 'America/Sao_Paulo',
            onboarding_completed INTEGER DEFAULT 1, onboarding_completed_at TEXT DEFAULT ''
        );
        CREATE TABLE users (
            id INTEGER PRIMARY KEY, username TEXT, password TEXT DEFAULT '',
            full_name TEXT DEFAULT '', role TEXT, company_id INTEGER, active INTEGER DEFAULT 1,
            linked_employee_id INTEGER
        );
        CREATE TABLE units (
            id INTEGER PRIMARY KEY, company_id INTEGER, name TEXT, unit_type TEXT,
            city TEXT DEFAULT '', notes TEXT DEFAULT ''
        );
        CREATE TABLE company_audit_logs (
            id INTEGER PRIMARY KEY, company_id INTEGER, actor_user_id INTEGER,
            actor_name TEXT, action_type TEXT, summary TEXT,
            details_json TEXT DEFAULT '[]', created_at TEXT
        );
        INSERT INTO companies (id, name, legal_name, cnpj) VALUES
            (1, 'ACME', 'ACME LTDA', '04.252.011/0001-10'),
            (2, 'Beta', 'Beta SA', '11.222.333/0001-81');
    """)
    conn.commit()
    return conn


class _FakeHandler:
    def __init__(self):
        self.path = '/api/my-company'
        self.command = 'GET'
        self.status = None
        self.wfile = io.BytesIO()

    def send_response(self, status):
        self.status = status

    def send_header(self, *_a, **_k):
        pass

    def end_headers(self):
        pass

    def json(self):
        return json.loads(self.wfile.getvalue().decode('utf-8'))


def _parsed(query='actor_user_id=1'):
    return urlparse(f'/api/my-company?{query}')


GENERAL = {'id': 5, 'role': 'general_admin', 'company_id': 1, 'full_name': 'Gal'}
MASTER = {'id': 1, 'role': 'master_admin', 'company_id': None, 'full_name': 'Master'}
LOCAL = {'id': 9, 'role': 'admin', 'company_id': 1, 'full_name': 'Local'}


class _NoCloseConn:
    """Handlers fecham a conexão via closing(); os testes reutilizam a mesma."""

    def __init__(self, conn):
        self._conn = conn

    def close(self):
        pass

    def __getattr__(self, name):
        return getattr(self._conn, name)


def _patch(monkeypatch, module, actor, conn):
    monkeypatch.setattr(module, 'get_connection', lambda: _NoCloseConn(conn))

    def fake_authorize(connection, actor_user_id, action, company_id=None):
        if action not in PERMISSIONS.get(actor['role'], frozenset()):
            raise PermissionError('Perfil sem permissão para esta ação.')
        return actor

    monkeypatch.setattr(module, 'resolve_actor_user_id', lambda *a, **k: actor['id'])
    monkeypatch.setattr(module, 'authorize_action', fake_authorize)


# ── matriz de permissões (backend) ────────────────────────────────────────────

def test_general_admin_has_company_settings_permissions():
    assert 'company_settings:view' in PERMISSIONS['general_admin']
    assert 'company_settings:update' in PERMISSIONS['general_admin']


def test_local_admin_and_registry_do_not_have_company_settings():
    for role in ('admin', 'registry_admin', 'user', 'buyer', 'approver', 'employee'):
        assert 'company_settings:update' not in PERMISSIONS.get(role, frozenset()), role
        assert 'company_settings:view' not in PERMISSIONS.get(role, frozenset()), role


def test_master_has_support_permission_but_not_self_settings():
    assert 'companies:support' in PERMISSIONS['master_admin']
    assert 'company_settings:update' not in PERMISSIONS['master_admin']


# ── service: validação e update parcial ───────────────────────────────────────

def test_validate_accepts_partial_payload_with_whitelisted_fields():
    conn = _conn()
    previous = get_my_company_profile(conn, 1)
    fields = validate_my_company_payload(conn, {'name': ' Nova ACME ', 'plan_name': 'enterprise'}, 1, previous)
    assert fields == {'name': 'Nova ACME'}


def test_validate_rejects_duplicate_cnpj():
    conn = _conn()
    previous = get_my_company_profile(conn, 1)
    with pytest.raises(ValueError):
        validate_my_company_payload(conn, {'cnpj': '11.222.333/0001-81'}, 1, previous)


def test_validate_rejects_subdomain_in_use_by_other_tenant():
    conn = _conn()
    conn.execute("UPDATE companies SET subdomain = 'beta' WHERE id = 2")
    previous = get_my_company_profile(conn, 1)
    with pytest.raises(ValueError):
        validate_my_company_payload(conn, {'subdomain': 'beta'}, 1, previous)


def test_update_never_touches_structural_fields():
    # Defesa por whitelist: plano/limite/licença/status nunca são graváveis.
    for blocked in ('plan_name', 'user_limit', 'license_status', 'active',
                    'monthly_value', 'addendum_enabled', 'id', 'company_id', 'tenant_id'):
        assert blocked not in PROFILE_EDITABLE_FIELDS


def test_update_my_company_applies_whitelisted_fields_only():
    conn = _conn()
    update_my_company(conn, 1, {'name': 'ACME Nova', 'plan_name': 'hack', 'user_limit': 9999})
    row = conn.execute('SELECT name, plan_name, user_limit FROM companies WHERE id = 1').fetchone()
    assert row['name'] == 'ACME Nova'
    assert row['plan_name'] == 'start'
    assert row['user_limit'] == 25


def test_summarize_marks_images_as_placeholder():
    summary, details = summarize_profile_changes(
        {'logo_type': '', 'name': 'ACME'},
        {'logo_type': 'data:image/png;base64,xyz', 'name': 'ACME'},
    )
    assert 'logotipo' in summary.lower()
    assert details == [{'field': 'Logotipo', 'before': '', 'after': '[imagem]'}]


def test_complete_onboarding_sets_flag():
    conn = _conn()
    mark_company_onboarding_pending(conn, 1)
    assert conn.execute('SELECT onboarding_completed FROM companies WHERE id = 1').fetchone()[0] == 0
    completed_at = complete_onboarding(conn, 1)
    row = conn.execute('SELECT onboarding_completed, onboarding_completed_at FROM companies WHERE id = 1').fetchone()
    assert row[0] == 1 and row[1] == completed_at


# ── handlers: GET/PUT /api/my-company ─────────────────────────────────────────

def test_general_admin_gets_own_company(monkeypatch):
    conn = _conn()
    _patch(monkeypatch, routes, GENERAL, conn)
    h = _FakeHandler()
    routes.handle_get_my_company(h, _parsed('actor_user_id=5'), None, None)
    assert h.status == 200
    body = h.json()
    assert body['company']['id'] == 1
    assert body['company']['name'] == 'ACME'
    # campos somente-leitura presentes para exibição
    assert body['company']['plan_name'] == 'start'


def test_local_admin_cannot_access_my_company(monkeypatch):
    conn = _conn()
    _patch(monkeypatch, routes, LOCAL, conn)
    with pytest.raises(PermissionError):
        routes.handle_get_my_company(_FakeHandler(), _parsed('actor_user_id=9'), None, None)


def test_master_without_company_cannot_use_my_company(monkeypatch):
    conn = _conn()
    _patch(monkeypatch, routes, MASTER, conn)
    with pytest.raises(PermissionError):
        routes.handle_put_my_company(_FakeHandler(), _parsed('actor_user_id=1'), {'name': 'X'}, None)


def test_general_admin_updates_own_company_and_audits(monkeypatch):
    conn = _conn()
    _patch(monkeypatch, routes, GENERAL, conn)
    h = _FakeHandler()
    payload = {'name': 'ACME Renovada', 'primary_color': '#112233', 'subdomain': 'acme'}
    routes.handle_put_my_company(h, _parsed('actor_user_id=5'), payload, None)
    assert h.status == 200
    row = conn.execute('SELECT name, primary_color, subdomain FROM companies WHERE id = 1').fetchone()
    assert (row['name'], row['primary_color'], row['subdomain']) == ('ACME Renovada', '#112233', 'acme')
    audit = conn.execute('SELECT action_type, summary FROM company_audit_logs').fetchone()
    assert audit['action_type'] == 'self_update'


def test_put_my_company_ignores_structural_fields(monkeypatch):
    conn = _conn()
    _patch(monkeypatch, routes, GENERAL, conn)
    h = _FakeHandler()
    payload = {'name': 'ACME X', 'plan_name': 'enterprise', 'user_limit': 999, 'license_status': 'trial', 'active': 0}
    routes.handle_put_my_company(h, _parsed('actor_user_id=5'), payload, None)
    row = conn.execute('SELECT plan_name, user_limit, license_status, active FROM companies WHERE id = 1').fetchone()
    assert (row['plan_name'], row['user_limit'], row['license_status'], row['active']) == ('start', 25, 'active', 1)


def test_onboarding_complete_endpoint(monkeypatch):
    conn = _conn()
    mark_company_onboarding_pending(conn, 1)
    _patch(monkeypatch, routes, GENERAL, conn)
    h = _FakeHandler()
    routes.handle_post_onboarding_complete(h, _parsed('actor_user_id=5'), {}, None)
    assert h.status == 200
    assert conn.execute('SELECT onboarding_completed FROM companies WHERE id = 1').fetchone()[0] == 1
    audit = conn.execute("SELECT action_type FROM company_audit_logs").fetchone()
    assert audit['action_type'] == 'onboarding_complete'


# ── handlers: suporte excepcional do Master ───────────────────────────────────

def _match(company_id='1'):
    return type('M', (), {'group': lambda self, i, _v=company_id: _v})()


def test_support_update_requires_reason(monkeypatch):
    conn = _conn()
    _patch(monkeypatch, routes, MASTER, conn)
    with pytest.raises(ValueError):
        routes.handle_post_company_support_update(
            _FakeHandler(), _parsed('actor_user_id=1'), {'name': 'Hack'}, _match()
        )


def test_support_update_applies_and_audits_with_reason(monkeypatch):
    conn = _conn()
    _patch(monkeypatch, routes, MASTER, conn)
    h = _FakeHandler()
    payload = {'support_reason': 'Chamado #123 — logotipo corrompido', 'name': 'ACME Suporte'}
    routes.handle_post_company_support_update(h, _parsed('actor_user_id=1'), payload, _match())
    assert h.status == 200
    assert conn.execute('SELECT name FROM companies WHERE id = 1').fetchone()[0] == 'ACME Suporte'
    audit = conn.execute('SELECT action_type, summary FROM company_audit_logs').fetchone()
    assert audit['action_type'] == 'support_update'
    assert 'Chamado #123' in audit['summary']


def test_support_update_denied_for_general_admin(monkeypatch):
    conn = _conn()
    _patch(monkeypatch, routes, GENERAL, conn)
    with pytest.raises(PermissionError):
        routes.handle_post_company_support_update(
            _FakeHandler(), _parsed('actor_user_id=5'),
            {'support_reason': 'tentativa indevida de acesso', 'name': 'X'}, _match('2')
        )


# ── rota operacional do Master preserva identidade/branding ───────────────────

def test_master_put_preserves_identity_and_branding(monkeypatch):
    conn = _conn()
    conn.execute("UPDATE companies SET logo_type = 'data:image/png;base64,logo', subdomain = 'acme' WHERE id = 1")
    _patch(monkeypatch, companies_routes, MASTER, conn)
    monkeypatch.setattr(
        companies_routes, 'validate_company_payload',
        lambda _c, p, _id: dict(p),
    )
    h = _FakeHandler()
    payload = {
        'actor_user_id': 1, 'name': 'Nome Invasor', 'legal_name': 'Razão Invasora',
        'cnpj': '99.999.999/9999-99', 'logo_type': 'data:image/png;base64,invasor',
        'plan_name': 'start', 'user_limit': 30, 'license_status': 'active', 'active': 1,
        'subdomain': 'invasor',
    }
    companies_routes.handle_put_company(h, _parsed('actor_user_id=1'), payload, _match())
    assert h.status == 200
    row = conn.execute('SELECT name, legal_name, cnpj, logo_type, subdomain, user_limit FROM companies WHERE id = 1').fetchone()
    # identidade/branding preservados do registro atual
    assert row['name'] == 'ACME'
    assert row['legal_name'] == 'ACME LTDA'
    assert row['cnpj'] == '04.252.011/0001-10'
    assert row['logo_type'] == 'data:image/png;base64,logo'
    assert row['subdomain'] == 'acme'
    # campo estrutural atualizado normalmente
    assert row['user_limit'] == 30


def test_protected_fields_cover_identity_and_branding():
    for field in ('name', 'legal_name', 'cnpj', 'logo_type', 'favicon_type',
                  'login_logo_type', 'primary_color', 'subdomain', 'custom_domain', 'theme_json'):
        assert field in MASTER_PROTECTED_COMPANY_FIELDS


# ── provisionamento inicial da tenant ─────────────────────────────────────────

def test_generate_tenant_slug_unique():
    conn = _conn()
    conn.execute("UPDATE companies SET slug = 'acme' WHERE id = 2")
    slug = generate_tenant_slug(conn, 'ACMÉ', exclude_company_id=1)
    assert slug == 'acme-2'


def test_provision_creates_matriz_owner_and_pending_onboarding():
    conn = _conn()
    details = provision_tenant_structure(conn, 1, {
        'general_admin_email': 'owner@acme.com.br',
        'general_admin_name': 'Owner ACME',
    })
    unit = conn.execute('SELECT name, company_id FROM units').fetchone()
    assert (unit['name'], unit['company_id']) == ('Matriz', 1)
    user = conn.execute('SELECT username, role, company_id, active FROM users').fetchone()
    assert (user['username'], user['role'], user['company_id'], user['active']) == (
        'owner@acme.com.br', 'general_admin', 1, 1
    )
    company = conn.execute('SELECT onboarding_completed, subdomain FROM companies WHERE id = 1').fetchone()
    assert company['onboarding_completed'] == 0
    assert company['subdomain'] == 'acme'
    fields = {d['field'] for d in details}
    assert {'Unidade matriz', 'Administrador Geral', 'Assistente de implantação'} <= fields


def test_provision_rejects_duplicate_owner_email():
    conn = _conn()
    conn.execute("INSERT INTO users (username, role, company_id) VALUES ('owner@acme.com.br', 'user', 2)")
    with pytest.raises(ValueError):
        provision_tenant_structure(conn, 1, {'general_admin_email': 'owner@acme.com.br'})


def test_routes_registered():
    recorded = []

    class R:
        def register(self, method, path, _h, *, regex=False):
            recorded.append((method, path))

    routes.register_routes(R())
    assert ('GET', '/api/my-company') in recorded
    assert ('PUT', '/api/my-company') in recorded
    assert ('POST', '/api/my-company/onboarding-complete') in recorded
    assert ('POST', r'^/api/companies/(\d+)/support-update$') in recorded
