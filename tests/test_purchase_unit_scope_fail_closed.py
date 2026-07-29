"""Fix E — Comprador/Aprovador sem vínculo de unidade não podem enxergar dados
da empresa inteira (docs/PAPEIS_E_ATRIBUICOES.md #6/#7).

Antes desta correção, `handle_get_purchase_demands`, `handle_get_purchase_requests`,
`handle_get_purchase_orders`, `handle_get_epi_requests`, `handle_get_purchase_pendencies`
(compras), `handle_get_report_requests`/`handle_post_report_requests` (relatórios) e
`handle_get_stock_movements_report` (estoque) tratavam "sem `purchase_role_unit_links`"
como "sem restrição" — o mesmo antipadrão do escopo de CNPJ do Administrador Local.
A ação sobre um registro específico (`ensure_purchase_request_action_scope`) já
bloqueava corretamente; o problema era só nas listagens.
"""

import io
import json
from urllib.parse import urlparse

import pytest


class _FakeHandler:
    def __init__(self, path='/api/x'):
        self.path = path
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
    return urlparse(f'/api/x?{query}')


class _FakeConnection:
    def close(self):
        pass

    def commit(self):
        pass


def _fake_connection():
    return _FakeConnection()


BUYER_NO_SCOPE = {'id': 1, 'role': 'buyer', 'company_id': 1, 'linked_employee_id': 10, 'full_name': 'Comprador'}
BUYER_WITH_SCOPE = {'id': 1, 'role': 'buyer', 'company_id': 1, 'linked_employee_id': 10, 'full_name': 'Comprador'}
APPROVER_NO_SCOPE = {'id': 2, 'role': 'approver', 'company_id': 1, 'linked_employee_id': 20, 'full_name': 'Aprovador'}
ADMIN_ACTOR = {'id': 3, 'role': 'general_admin', 'company_id': 1, 'linked_employee_id': None, 'full_name': 'Geral'}


# ═══════════════════════════════════════════════════════════════════════════════
# actor_has_no_purchase_unit_scope
# ═══════════════════════════════════════════════════════════════════════════════

def test_actor_has_no_purchase_unit_scope_true_for_buyer_without_links():
    from modules.purchases.service import actor_has_no_purchase_unit_scope
    assert actor_has_no_purchase_unit_scope(BUYER_NO_SCOPE, None, None) is True
    assert actor_has_no_purchase_unit_scope(BUYER_NO_SCOPE, None, []) is True


def test_actor_has_no_purchase_unit_scope_false_when_linked_units_exist():
    from modules.purchases.service import actor_has_no_purchase_unit_scope
    assert actor_has_no_purchase_unit_scope(BUYER_WITH_SCOPE, None, [5]) is False


def test_actor_has_no_purchase_unit_scope_false_for_admin_roles():
    from modules.purchases.service import actor_has_no_purchase_unit_scope
    assert actor_has_no_purchase_unit_scope(ADMIN_ACTOR, None, None) is False


# ═══════════════════════════════════════════════════════════════════════════════
# modules/purchases/routes.py — listagens fail-closed
# ═══════════════════════════════════════════════════════════════════════════════

def _patch_purchases(monkeypatch, actor, *, purchase_scope=None, scope_unit_id=None):
    import modules.purchases.routes as routes
    monkeypatch.setattr(routes, 'get_connection', _fake_connection)
    monkeypatch.setattr(routes, 'resolve_actor_user_id', lambda *a, **k: actor['id'])
    monkeypatch.setattr(routes, 'authorize_action', lambda *a, **k: actor)
    monkeypatch.setattr(routes, 'actor_operational_unit_id', lambda *a, **k: scope_unit_id)
    monkeypatch.setattr(routes, 'get_actor_purchase_unit_scope', lambda *a, **k: purchase_scope)
    monkeypatch.setattr(routes, 'canary_evaluate_visibility_dataset', lambda *_a, **k: k.get('legacy_items'))

    def _boom(*_a, **_k):
        raise AssertionError('fetch should not run when actor has no purchase unit scope')

    monkeypatch.setattr(routes, 'fetch_epi_requests', _boom)
    monkeypatch.setattr(routes, 'fetch_purchase_demands', _boom)
    monkeypatch.setattr(routes, 'fetch_purchase_requests', _boom)
    monkeypatch.setattr(routes, 'fetch_purchase_orders', _boom)
    monkeypatch.setattr(routes, 'fetch_purchase_pendencies', _boom)
    return routes


def test_epi_requests_empty_for_buyer_without_links(monkeypatch):
    routes = _patch_purchases(monkeypatch, BUYER_NO_SCOPE)
    h = _FakeHandler()
    routes.handle_get_epi_requests(h, _parsed(), None, None)
    assert h.status == 200
    assert h.json()['items'] == []


def test_purchase_demands_empty_for_approver_without_links(monkeypatch):
    routes = _patch_purchases(monkeypatch, APPROVER_NO_SCOPE)
    h = _FakeHandler()
    routes.handle_get_purchase_demands(h, _parsed(), None, None)
    assert h.status == 200
    assert h.json()['items'] == []


def test_purchase_requests_empty_for_buyer_without_links(monkeypatch):
    routes = _patch_purchases(monkeypatch, BUYER_NO_SCOPE)
    h = _FakeHandler()
    routes.handle_get_purchase_requests(h, _parsed(), None, None)
    assert h.status == 200
    assert h.json()['items'] == []


def test_purchase_orders_empty_for_buyer_without_links(monkeypatch):
    routes = _patch_purchases(monkeypatch, BUYER_NO_SCOPE)
    h = _FakeHandler()
    routes.handle_get_purchase_orders(h, _parsed(), None, None)
    assert h.status == 200
    assert h.json()['items'] == []


def test_purchase_pendencies_empty_for_buyer_without_links(monkeypatch):
    routes = _patch_purchases(monkeypatch, BUYER_NO_SCOPE)
    h = _FakeHandler()
    routes.handle_get_purchase_pendencies(h, _parsed(), None, None)
    assert h.status == 200
    assert h.json()['items'] == []


def test_purchase_requests_scoped_result_reaches_buyer_with_links(monkeypatch):
    routes = _patch_purchases(monkeypatch, BUYER_WITH_SCOPE, purchase_scope=[5])
    monkeypatch.setattr(routes, 'fetch_purchase_requests', lambda *a, **k: [{'id': 1, 'unit_id': 5}])
    h = _FakeHandler()
    routes.handle_get_purchase_requests(h, _parsed(), None, None)
    assert h.status == 200
    assert h.json()['items'] == [{'id': 1, 'unit_id': 5}]


def test_purchase_orders_unrestricted_for_admin_roles(monkeypatch):
    routes = _patch_purchases(monkeypatch, ADMIN_ACTOR)
    monkeypatch.setattr(routes, 'fetch_purchase_orders', lambda *a, **k: [{'id': 9}])
    h = _FakeHandler()
    routes.handle_get_purchase_orders(h, _parsed(), None, None)
    assert h.status == 200
    assert h.json()['items'] == [{'id': 9}]


# ═══════════════════════════════════════════════════════════════════════════════
# fetch_purchase_pendencies — suporte a purchase_scope_units (lista)
# ═══════════════════════════════════════════════════════════════════════════════

def test_fetch_purchase_pendencies_filters_by_purchase_scope_units():
    import sqlite3
    from modules.purchases.service import fetch_purchase_pendencies
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        CREATE TABLE purchase_pendencies (
            id INTEGER PRIMARY KEY, company_id INTEGER, unit_id INTEGER,
            purchase_request_id INTEGER, status TEXT, created_at TEXT
        );
        CREATE TABLE units (id INTEGER PRIMARY KEY, name TEXT);
        CREATE TABLE purchase_requests (id INTEGER PRIMARY KEY, title TEXT);
    """)
    conn.execute("INSERT INTO purchase_pendencies VALUES (1,1,5,NULL,'open','2024-01-01')")
    conn.execute("INSERT INTO purchase_pendencies VALUES (2,1,6,NULL,'open','2024-01-01')")
    conn.commit()
    result = fetch_purchase_pendencies(conn, 1, None, 'open', purchase_scope_units=[5])
    ids = [r['id'] for r in result]
    assert 1 in ids
    assert 2 not in ids


# ═══════════════════════════════════════════════════════════════════════════════
# modules/reports/routes.py — listagem e criação
# ═══════════════════════════════════════════════════════════════════════════════

def _patch_reports(monkeypatch, actor, *, purchase_scope=None, scope_unit_id=None, fetch_items=None):
    import modules.reports.routes as routes
    monkeypatch.setattr(routes, 'get_connection', _fake_connection)
    monkeypatch.setattr(routes, 'resolve_actor_user_id', lambda *a, **k: actor['id'])
    monkeypatch.setattr(routes, 'authorize_action', lambda *a, **k: actor)
    monkeypatch.setattr(routes, 'actor_operational_unit_id', lambda *a, **k: scope_unit_id)
    monkeypatch.setattr(routes, 'get_actor_purchase_unit_scope', lambda *a, **k: purchase_scope)
    monkeypatch.setattr(routes, 'canary_evaluate_visibility_dataset', lambda *_a, **k: k.get('legacy_items'))
    monkeypatch.setattr(routes, 'fetch_report_requests', fetch_items or (lambda *a, **k: [{'id': 1}]))
    return routes


def test_report_requests_empty_for_approver_without_links(monkeypatch):
    def _boom(*_a, **_k):
        raise AssertionError('fetch should not run')
    routes = _patch_reports(monkeypatch, APPROVER_NO_SCOPE, fetch_items=_boom)
    h = _FakeHandler(path='/api/report-requests')
    routes.handle_get_report_requests(h, _parsed('actor_user_id=2'), None, None)
    assert h.status == 200
    assert h.json()['items'] == []


def test_report_requests_visible_to_approver_with_links(monkeypatch):
    routes = _patch_reports(monkeypatch, APPROVER_NO_SCOPE, purchase_scope=[5])
    h = _FakeHandler(path='/api/report-requests')
    routes.handle_get_report_requests(h, _parsed('actor_user_id=2'), None, None)
    assert h.status == 200
    assert h.json()['items'] == [{'id': 1}]


def test_post_report_requests_approver_without_links_rejected(monkeypatch):
    routes = _patch_reports(monkeypatch, APPROVER_NO_SCOPE, purchase_scope=None)
    h = _FakeHandler(path='/api/report-requests')
    h.command = 'POST'
    with pytest.raises(PermissionError):
        routes.handle_post_report_requests(h, _parsed(), {'actor_user_id': 2, 'unit_id': 5}, None)


def test_post_report_requests_approver_wrong_unit_rejected(monkeypatch):
    routes = _patch_reports(monkeypatch, APPROVER_NO_SCOPE, purchase_scope=[5])
    h = _FakeHandler(path='/api/report-requests')
    h.command = 'POST'
    with pytest.raises(PermissionError):
        routes.handle_post_report_requests(h, _parsed(), {'actor_user_id': 2, 'unit_id': 99}, None)


def test_post_report_requests_approver_own_unit_allowed(monkeypatch):
    routes = _patch_reports(monkeypatch, APPROVER_NO_SCOPE, purchase_scope=[5])
    monkeypatch.setattr(routes, 'get_connection', _fake_connection)
    monkeypatch.setattr(routes, 'create_report_request', lambda *a, **k: None)
    h = _FakeHandler(path='/api/report-requests')
    h.command = 'POST'
    routes.handle_post_report_requests(h, _parsed(), {'actor_user_id': 2, 'unit_id': 5}, None)
    assert h.status == 201


# ═══════════════════════════════════════════════════════════════════════════════
# modules/stock/routes.py — relatório de movimentações
# ═══════════════════════════════════════════════════════════════════════════════

def test_stock_movements_report_empty_for_buyer_without_links(monkeypatch):
    import modules.stock.routes as routes

    def _boom(*_a, **_k):
        raise AssertionError('fetch should not run')

    monkeypatch.setattr(routes, 'get_connection', _fake_connection)
    monkeypatch.setattr(routes, 'resolve_actor_user_id', lambda *a, **k: BUYER_NO_SCOPE['id'])
    monkeypatch.setattr(routes, 'authorize_action', lambda *a, **k: BUYER_NO_SCOPE)
    monkeypatch.setattr(routes, 'actor_operational_unit_id', lambda *a, **k: None)
    monkeypatch.setattr(routes, 'get_actor_purchase_unit_scope', lambda *a, **k: None)
    monkeypatch.setattr(routes, 'fetch_stock_movements', _boom)
    h = _FakeHandler(path='/api/stock/movements/report')
    routes.handle_get_stock_movements_report(h, _parsed('actor_user_id=1'), None, None)
    assert h.status == 200
    assert h.json()['items'] == []
