"""GET endpoints dedicados de Empresas + correção do bug de user_count.

Cobre:
  - company_billable_user_counts / fetch_companies enriquecidos com user_count
    (mesma semântica de commercial.count_company_users: ativos em BILLABLE_ROLES)
  - GET /api/companies        (lista escopada: master vê todas, demais só a sua)
  - GET /api/companies/(id)   (item único; bloqueia empresa de terceiros; 404)
"""

import io
import json
import sqlite3
from urllib.parse import urlparse

import pytest

import modules.companies.routes as routes
from modules.companies.service import company_billable_user_counts, fetch_companies


# ── service: contagem e enriquecimento ────────────────────────────────────────

def _conn():
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        CREATE TABLE companies (
            id INTEGER PRIMARY KEY, name TEXT, legal_name TEXT DEFAULT '', cnpj TEXT,
            active INTEGER DEFAULT 1, logo_type TEXT DEFAULT '', plan_name TEXT DEFAULT '',
            user_limit INTEGER DEFAULT 25, license_status TEXT DEFAULT 'active',
            contract_start TEXT DEFAULT '', contract_end TEXT DEFAULT '', monthly_value REAL DEFAULT 0,
            addendum_enabled INTEGER DEFAULT 0, commercial_notes TEXT DEFAULT '', slug TEXT DEFAULT '',
            subdomain TEXT DEFAULT '', custom_domain TEXT DEFAULT '', login_logo_type TEXT DEFAULT '',
            primary_color TEXT DEFAULT '', secondary_color TEXT DEFAULT '', accent_color TEXT DEFAULT '',
            default_language TEXT DEFAULT 'pt-BR', favicon_type TEXT DEFAULT '',
            institutional_message TEXT DEFAULT '', contact_email TEXT DEFAULT '',
            contact_phone TEXT DEFAULT '', website TEXT DEFAULT ''
        );
        CREATE TABLE users (id INTEGER PRIMARY KEY, company_id INTEGER, active INTEGER, role TEXT);
        INSERT INTO companies (id, name, cnpj) VALUES (1, 'ACME', '1'), (2, 'Beta', '2');
        -- ACME: 2 faturáveis ativos + 1 inativo + 1 master_admin (não faturável)
        INSERT INTO users (company_id, active, role) VALUES
            (1, 1, 'user'), (1, 1, 'admin'), (1, 0, 'user'), (1, 1, 'master_admin'),
            (2, 1, 'buyer');
    """)
    conn.commit()
    return conn


def test_counts_exclude_inactive_and_non_billable():
    counts = company_billable_user_counts(_conn())
    assert counts == {1: 2, 2: 1}


def test_counts_single_company_filter():
    assert company_billable_user_counts(_conn(), 1) == {1: 2}


def test_fetch_companies_enriches_user_count():
    companies = fetch_companies(_conn())
    by_id = {c['id']: c for c in companies}
    assert by_id[1]['user_count'] == 2
    assert by_id[2]['user_count'] == 1


def test_fetch_companies_zero_when_no_users():
    conn = _conn()
    conn.execute('DELETE FROM users')
    conn.commit()
    companies = fetch_companies(conn)
    assert all(c['user_count'] == 0 for c in companies)


# ── handlers ──────────────────────────────────────────────────────────────────

class _FakeHandler:
    def __init__(self):
        self.path = '/api/companies'
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
    return urlparse(f'/api/companies?{query}')


def _patch(monkeypatch, actor):
    monkeypatch.setattr(routes, 'get_connection', lambda: type('C', (), {'close': lambda self: None})())
    monkeypatch.setattr(routes, 'resolve_actor_user_id', lambda *a, **k: actor['id'])
    monkeypatch.setattr(routes, 'authorize_action', lambda *a, **k: actor)


def test_get_companies_master_sees_all(monkeypatch):
    actor = {'id': 1, 'role': 'master_admin', 'company_id': None}
    _patch(monkeypatch, actor)
    seen = {}
    monkeypatch.setattr(routes, 'fetch_companies', lambda _c, scope: seen.setdefault('scope', scope) or [{'id': 1}, {'id': 2}])
    h = _FakeHandler()
    routes.handle_get_companies(h, _parsed(), None, None)
    assert h.status == 200 and seen['scope'] is None
    assert len(h.json()['companies']) == 2


def test_get_companies_general_admin_scoped(monkeypatch):
    actor = {'id': 5, 'role': 'general_admin', 'company_id': 7}
    _patch(monkeypatch, actor)
    seen = {}
    monkeypatch.setattr(routes, 'fetch_companies', lambda _c, scope: seen.setdefault('scope', scope) or [{'id': 7}])
    h = _FakeHandler()
    routes.handle_get_companies(h, _parsed('actor_user_id=5'), None, None)
    assert seen['scope'] == 7


def test_get_company_single_includes_user_count(monkeypatch):
    actor = {'id': 1, 'role': 'master_admin', 'company_id': None}
    _patch(monkeypatch, actor)
    monkeypatch.setattr(routes, 'get_company_full', lambda _c, cid: {'id': cid, 'name': 'ACME'})
    monkeypatch.setattr(routes, 'company_billable_user_counts', lambda _c, cid: {cid: 4})
    h = _FakeHandler()
    match = type('M', (), {'group': lambda self, i: '3'})()
    routes.handle_get_company(h, _parsed('actor_user_id=1'), None, match)
    body = h.json()
    assert h.status == 200 and body['company']['user_count'] == 4


def test_get_company_blocks_other_company(monkeypatch):
    actor = {'id': 5, 'role': 'general_admin', 'company_id': 7}
    _patch(monkeypatch, actor)
    match = type('M', (), {'group': lambda self, i: '99'})()
    with pytest.raises(PermissionError):
        routes.handle_get_company(h := _FakeHandler(), _parsed('actor_user_id=5'), None, match)
    assert h.status is None


def test_get_company_404(monkeypatch):
    actor = {'id': 1, 'role': 'master_admin', 'company_id': None}
    _patch(monkeypatch, actor)
    monkeypatch.setattr(routes, 'get_company_full', lambda _c, cid: None)
    match = type('M', (), {'group': lambda self, i: '404'})()
    h = _FakeHandler()
    routes.handle_get_company(h, _parsed('actor_user_id=1'), None, match)
    assert h.status == 404


def test_routes_registered():
    recorded = []

    class R:
        def register(self, method, path, _h, *, regex=False):
            recorded.append((method, path))

    routes.register_routes(R())
    assert ('GET', '/api/companies') in recorded
    assert ('GET', r'^/api/companies/(\d+)$') in recorded
