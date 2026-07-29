"""Auditoria (rodada 2) — Administrador Local / Gestor de EPI sem unidade
operacional ativa não podem agir fora de escopo, mesmo dentro do mesmo CNPJ
(docs/PAPEIS_E_ATRIBUICOES.md #4/#5).

Vínculo único confirmado pelo cliente: nunca carteira de unidades para estes
dois perfis. `actor_operational_unit_id` já é a fonte única; o problema
encontrado na auditoria foi a falta de um `else` fail-closed em ~20 pontos
que a consomem — o mesmo antipadrão já corrigido para CNPJ (Administrador
Local) e para Comprador/Aprovador (purchase_role_unit_links).
"""

import io
import json
import sqlite3
from urllib.parse import urlparse

import pytest


ADMIN_NO_UNIT = {'id': 12, 'role': 'admin', 'company_id': 1, 'linked_employee_id': 12, 'full_name': 'Admin Local'}
ADMIN_WITH_UNIT = {'id': 12, 'role': 'admin', 'company_id': 1, 'linked_employee_id': 12, 'full_name': 'Admin Local'}
GENERAL_ADMIN = {'id': 3, 'role': 'general_admin', 'company_id': 1, 'linked_employee_id': None, 'full_name': 'Geral'}


# ═══════════════════════════════════════════════════════════════════════════════
# actor_has_no_operational_unit
# ═══════════════════════════════════════════════════════════════════════════════

def test_actor_has_no_operational_unit_true_for_admin_without_unit():
    from modules.employees.service import actor_has_no_operational_unit
    assert actor_has_no_operational_unit(ADMIN_NO_UNIT, None) is True


def test_actor_has_no_operational_unit_false_when_unit_present():
    from modules.employees.service import actor_has_no_operational_unit
    assert actor_has_no_operational_unit(ADMIN_WITH_UNIT, 5) is False


def test_actor_has_no_operational_unit_false_for_structural_roles():
    from modules.employees.service import actor_has_no_operational_unit
    assert actor_has_no_operational_unit(GENERAL_ADMIN, None) is False


# ═══════════════════════════════════════════════════════════════════════════════
# modules/purchases/service.py — ensure_purchase_request_action_scope /
# ensure_purchase_order_action_scope (resolver *wired* mas sem unidade)
# ═══════════════════════════════════════════════════════════════════════════════

def test_ensure_purchase_request_action_scope_denies_admin_without_unit():
    from modules.purchases.service import ensure_purchase_request_action_scope
    pr = {'id': 1, 'company_id': 1, 'unit_id': 5}
    with pytest.raises(PermissionError, match='unidade operacional'):
        ensure_purchase_request_action_scope(
            None, ADMIN_NO_UNIT, pr, actor_operational_unit_id=lambda conn, act: None,
        )


def test_ensure_purchase_request_action_scope_denies_cross_unit():
    from modules.purchases.service import ensure_purchase_request_action_scope
    pr = {'id': 1, 'company_id': 1, 'unit_id': 9}
    with pytest.raises(PermissionError, match='fora da unidade'):
        ensure_purchase_request_action_scope(
            None, ADMIN_WITH_UNIT, pr, actor_operational_unit_id=lambda conn, act: 5,
        )


def _purchase_links_conn():
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.execute(
        'CREATE TABLE purchase_role_unit_links (id INTEGER PRIMARY KEY, company_id INTEGER, '
        'unit_id INTEGER, employee_id INTEGER, role_type TEXT)'
    )
    conn.commit()
    return conn


def test_ensure_purchase_request_action_scope_allows_matching_unit():
    from modules.purchases.service import ensure_purchase_request_action_scope
    pr = {'id': 1, 'company_id': 1, 'unit_id': 5}
    ensure_purchase_request_action_scope(
        _purchase_links_conn(), ADMIN_WITH_UNIT, pr, actor_operational_unit_id=lambda conn, act: 5,
    )


def test_ensure_purchase_request_action_scope_skips_when_resolver_not_wired():
    """Contrato de DI existente: chamador que não passa o resolvedor (testes
    de lógica de negócio que não se importam com escopo) mantém o comportamento
    anterior — só a produção (que sempre injeta o resolvedor real) fica sujeita
    ao fail-closed."""
    from modules.purchases.service import ensure_purchase_request_action_scope
    pr = {'id': 1, 'company_id': 1, 'unit_id': 9}
    ensure_purchase_request_action_scope(_purchase_links_conn(), ADMIN_NO_UNIT, pr)


def test_ensure_purchase_order_action_scope_denies_admin_without_unit():
    from modules.purchases.service import ensure_purchase_order_action_scope
    po = {'id': 1, 'company_id': 1, 'unit_id': 5}
    with pytest.raises(PermissionError, match='unidade operacional'):
        ensure_purchase_order_action_scope(
            None, ADMIN_NO_UNIT, po, actor_operational_unit_id=lambda conn, act: None,
        )


# ═══════════════════════════════════════════════════════════════════════════════
# modules/purchases/service.py — bulk_update_epi_request_statuses
# ═══════════════════════════════════════════════════════════════════════════════

def _bulk_conn():
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        CREATE TABLE epi_requests (
            id INTEGER PRIMARY KEY, company_id INTEGER, unit_id INTEGER,
            employee_id INTEGER, epi_id INTEGER, status TEXT,
            approver_user_id INTEGER, approver_name TEXT, approved_at TEXT,
            rejection_reason TEXT, postponed_until TEXT, last_updated_at TEXT
        );
        CREATE TABLE epi_request_history (
            id INTEGER PRIMARY KEY, request_id INTEGER, company_id INTEGER,
            status TEXT, notes TEXT, actor_user_id INTEGER, actor_name TEXT, created_at TEXT
        );
    """)
    conn.execute("INSERT INTO epi_requests VALUES (1,1,9,10,100,'solicitado',NULL,NULL,NULL,NULL,NULL,NULL)")
    conn.commit()
    return conn


def test_bulk_update_denies_admin_without_unit():
    from modules.purchases.service import bulk_update_epi_request_statuses
    conn = _bulk_conn()
    with pytest.raises(PermissionError, match='unidade operacional'):
        bulk_update_epi_request_statuses(
            conn, ADMIN_NO_UNIT, [{'request_id': 1, 'status': 'aprovado'}],
            actor_operational_unit_id=lambda c, a: None,
        )


def test_bulk_update_denies_cross_unit():
    from modules.purchases.service import bulk_update_epi_request_statuses
    conn = _bulk_conn()
    with pytest.raises(PermissionError, match='fora da unidade'):
        bulk_update_epi_request_statuses(
            conn, ADMIN_WITH_UNIT, [{'request_id': 1, 'status': 'aprovado'}],
            actor_operational_unit_id=lambda c, a: 5,
        )


def test_bulk_update_allows_matching_unit():
    from modules.purchases.service import bulk_update_epi_request_statuses
    conn = _bulk_conn()
    bulk_update_epi_request_statuses(
        conn, ADMIN_WITH_UNIT, [{'request_id': 1, 'status': 'aprovado'}],
        actor_operational_unit_id=lambda c, a: 9,
    )
    row = conn.execute('SELECT status FROM epi_requests WHERE id = 1').fetchone()
    assert row['status'] == 'aprovado'


# ═══════════════════════════════════════════════════════════════════════════════
# modules/purchases/routes.py — rotas fail-closed para admin/user
# ═══════════════════════════════════════════════════════════════════════════════

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


class _Match:
    def __init__(self, value):
        self._value = value

    def group(self, _n):
        return self._value


class _FakeConnection:
    def close(self):
        pass

    def commit(self):
        pass


def _fake_connection():
    return _FakeConnection()


def _patch_purchases_routes(monkeypatch, actor, *, scope_unit_id=None):
    import modules.purchases.routes as routes
    monkeypatch.setattr(routes, 'get_connection', _fake_connection)
    monkeypatch.setattr(routes, 'resolve_actor_user_id', lambda *a, **k: actor['id'])
    monkeypatch.setattr(routes, 'authorize_action', lambda *a, **k: actor)
    monkeypatch.setattr(routes, 'actor_operational_unit_id', lambda *a, **k: scope_unit_id)
    monkeypatch.setattr(routes, 'get_actor_purchase_unit_scope', lambda *a, **k: None)
    monkeypatch.setattr(routes, 'canary_evaluate_visibility_dataset', lambda *_a, **k: k.get('legacy_items'))

    def _boom(*_a, **_k):
        raise AssertionError('fetch should not run when admin/user has no operational unit')

    monkeypatch.setattr(routes, 'fetch_epi_requests', _boom)
    monkeypatch.setattr(routes, 'fetch_purchase_demands', _boom)
    monkeypatch.setattr(routes, 'fetch_purchase_requests', _boom)
    monkeypatch.setattr(routes, 'fetch_purchase_orders', _boom)
    monkeypatch.setattr(routes, 'fetch_purchase_pendencies', _boom)
    return routes


@pytest.mark.parametrize('handler_name', [
    'handle_get_epi_requests',
    'handle_get_purchase_demands',
    'handle_get_purchase_requests',
    'handle_get_purchase_pendencies',
    'handle_get_purchase_orders',
])
def test_purchases_listing_empty_for_admin_without_unit(monkeypatch, handler_name):
    routes = _patch_purchases_routes(monkeypatch, ADMIN_NO_UNIT)
    h = _FakeHandler()
    getattr(routes, handler_name)(h, _parsed(), None, None)
    assert h.status == 200
    assert h.json()['items'] == []


def test_handle_post_purchase_requests_denies_admin_without_unit(monkeypatch):
    import modules.purchases.routes as routes
    routes = _patch_purchases_routes(monkeypatch, ADMIN_NO_UNIT)
    monkeypatch.setattr(routes, 'get_unit_by_id', lambda *a, **k: {'id': 5, 'company_id': 1})
    monkeypatch.setattr(routes, 'ensure_unit_operational', lambda *a, **k: None)
    h = _FakeHandler()
    h.command = 'POST'
    routes.handle_post_purchase_requests(
        h, _parsed(), {'actor_user_id': 12, 'unit_id': 5, 'items': [{'epi_id': 1}]}, None,
    )
    assert h.status == 403
    assert h.json()['error']['code'] == 'UNIT_SCOPE_VIOLATION'


def test_handle_post_purchase_orders_denies_admin_without_unit(monkeypatch):
    import modules.purchases.routes as routes
    routes = _patch_purchases_routes(monkeypatch, ADMIN_NO_UNIT)
    monkeypatch.setattr(routes, 'ensure_unit_operational', lambda *a, **k: None)
    h = _FakeHandler()
    h.command = 'POST'
    routes.handle_post_purchase_orders(
        h, _parsed(), {'actor_user_id': 12, 'unit_id': 5, 'items': [{'epi_id': 1}]}, None,
    )
    assert h.status == 403
    assert h.json()['error']['code'] == 'UNIT_SCOPE_VIOLATION'


def test_handle_get_purchase_order_detail_denies_cross_unit(monkeypatch):
    import modules.purchases.routes as routes
    routes = _patch_purchases_routes(monkeypatch, ADMIN_WITH_UNIT, scope_unit_id=5)
    monkeypatch.setattr(
        routes, 'get_purchase_order_detail',
        lambda *a, **k: ({'id': 1, 'company_id': 1, 'unit_id': 9}, [], [], []),
    )
    h = _FakeHandler()
    with pytest.raises(PermissionError):
        routes.handle_get_purchase_order_detail(h, _parsed(), None, _Match('1'))


def test_handle_post_requests_status_denies_cross_unit(monkeypatch):
    import modules.purchases.routes as routes
    routes = _patch_purchases_routes(monkeypatch, ADMIN_WITH_UNIT, scope_unit_id=5)
    monkeypatch.setattr(routes, 'get_epi_request_by_id', lambda *a, **k: {'id': 1, 'company_id': 1, 'unit_id': 9})
    h = _FakeHandler()
    h.command = 'POST'
    with pytest.raises(PermissionError):
        routes.handle_post_requests_status(
            h, _parsed(), {'actor_user_id': 12, 'request_id': 1, 'status': 'aprovado'}, None,
        )


def test_handle_post_feedbacks_status_denies_cross_unit(monkeypatch):
    import modules.purchases.routes as routes
    routes = _patch_purchases_routes(monkeypatch, ADMIN_WITH_UNIT, scope_unit_id=5)
    monkeypatch.setattr(routes, 'get_epi_feedback_by_id', lambda *a, **k: {'id': 1, 'company_id': 1, 'unit_id': 9})
    h = _FakeHandler()
    h.command = 'POST'
    with pytest.raises(PermissionError):
        routes.handle_post_feedbacks_status(
            h, _parsed(), {'actor_user_id': 12, 'feedback_id': 1, 'status': 'aprovada'}, None,
        )


# ═══════════════════════════════════════════════════════════════════════════════
# modules/stock — fetch_low_stock_items, item status, labels reprint, movements
# ═══════════════════════════════════════════════════════════════════════════════

def test_fetch_low_stock_items_empty_for_admin_without_unit():
    from modules.stock.service import fetch_low_stock_items
    items = fetch_low_stock_items(
        None, ADMIN_NO_UNIT,
        actor_operational_unit_id=lambda c, a: None,
        get_unit_active_jv_name=lambda c, u: '',
        is_epi_visible_for_unit=lambda **k: True,
    )
    assert items == []


def _patch_stock_routes(monkeypatch, actor, *, scope_unit_id=None):
    import modules.stock.routes as routes
    monkeypatch.setattr(routes, 'get_connection', _fake_connection)
    monkeypatch.setattr(routes, 'resolve_actor_user_id', lambda *a, **k: actor['id'])
    monkeypatch.setattr(routes, 'authorize_action', lambda *a, **k: actor)
    monkeypatch.setattr(routes, 'actor_operational_unit_id', lambda *a, **k: scope_unit_id)
    monkeypatch.setattr(routes, 'get_actor_purchase_unit_scope', lambda *a, **k: None)
    return routes


def test_handle_post_stock_item_status_denies_admin_without_unit(monkeypatch):
    routes = _patch_stock_routes(monkeypatch, ADMIN_NO_UNIT)

    def _boom(*_a, **_k):
        raise AssertionError('lookup should not run')

    monkeypatch.setattr(routes, 'lookup_stock_item_by_qr', _boom)
    h = _FakeHandler()
    h.command = 'POST'
    with pytest.raises(PermissionError):
        routes.handle_post_stock_item_status(
            h, _parsed(), {'actor_user_id': 12, 'new_status': 'bloqueado', 'unit_id': 9, 'qr_code': 'X'}, None,
        )


def test_handle_post_stock_labels_reprint_denies_cross_unit(monkeypatch):
    routes = _patch_stock_routes(monkeypatch, ADMIN_WITH_UNIT, scope_unit_id=5)
    monkeypatch.setattr(
        routes, 'get_stock_item_for_reprint',
        lambda *a, **k: {'id': 1, 'company_id': 1, 'unit_id': 9},
    )
    h = _FakeHandler()
    h.command = 'POST'
    with pytest.raises(PermissionError):
        routes.handle_post_stock_labels_reprint(
            h, _parsed(),
            {'actor_user_id': 12, 'company_id': 1, 'stock_item_id': 1, 'reason_code': 'perdeu'}, None,
        )


def test_handle_get_stock_movements_report_empty_for_admin_without_unit(monkeypatch):
    routes = _patch_stock_routes(monkeypatch, ADMIN_NO_UNIT)

    def _boom(*_a, **_k):
        raise AssertionError('fetch should not run')

    monkeypatch.setattr(routes, 'fetch_stock_movements', _boom)
    h = _FakeHandler(path='/api/stock/movements/report')
    routes.handle_get_stock_movements_report(h, _parsed('actor_user_id=12'), None, None)
    assert h.status == 200
    assert h.json()['items'] == []


# ═══════════════════════════════════════════════════════════════════════════════
# modules/deliveries/routes.py — handle_get_deliveries
# ═══════════════════════════════════════════════════════════════════════════════

def test_handle_get_deliveries_empty_for_admin_without_unit(monkeypatch):
    import modules.deliveries.routes as routes
    monkeypatch.setattr(routes, 'get_connection', _fake_connection)
    monkeypatch.setattr(routes, 'resolve_actor_user_id', lambda *a, **k: ADMIN_NO_UNIT['id'])
    monkeypatch.setattr(routes, 'authorize_action', lambda *a, **k: ADMIN_NO_UNIT)
    monkeypatch.setattr(routes, 'actor_operational_unit_id', lambda *a, **k: None)

    def _boom(*_a, **_k):
        raise AssertionError('fetch should not run')

    monkeypatch.setattr(routes, 'fetch_deliveries', _boom)
    h = _FakeHandler(path='/api/deliveries')
    routes.handle_get_deliveries(h, _parsed('actor_user_id=12'), None, None)
    assert h.status == 200
    assert h.json()['items'] == []


# ═══════════════════════════════════════════════════════════════════════════════
# modules/reports/routes.py — handle_get_report_requests (admin/user)
# ═══════════════════════════════════════════════════════════════════════════════

def test_handle_get_report_requests_empty_for_admin_without_unit(monkeypatch):
    import modules.reports.routes as routes
    monkeypatch.setattr(routes, 'get_connection', _fake_connection)
    monkeypatch.setattr(routes, 'resolve_actor_user_id', lambda *a, **k: ADMIN_NO_UNIT['id'])
    monkeypatch.setattr(routes, 'authorize_action', lambda *a, **k: ADMIN_NO_UNIT)
    monkeypatch.setattr(routes, 'actor_operational_unit_id', lambda *a, **k: None)
    monkeypatch.setattr(routes, 'get_actor_purchase_unit_scope', lambda *a, **k: None)

    def _boom(*_a, **_k):
        raise AssertionError('fetch should not run')

    monkeypatch.setattr(routes, 'fetch_report_requests', _boom)
    h = _FakeHandler(path='/api/report-requests')
    routes.handle_get_report_requests(h, _parsed('actor_user_id=12'), None, None)
    assert h.status == 200
    assert h.json()['items'] == []


# ═══════════════════════════════════════════════════════════════════════════════
# modules/alerts/service.py — compute_alerts
# ═══════════════════════════════════════════════════════════════════════════════

def test_compute_alerts_empty_for_admin_without_unit():
    from modules.alerts.service import compute_alerts

    def _boom(*_a, **_k):
        raise AssertionError('fetch should not run when actor has no operational unit')

    alerts = compute_alerts(
        None, ADMIN_NO_UNIT,
        fetch_low_stock_items=_boom,
        actor_operational_unit_id=lambda c, a: None,
        fetch_epis=_boom,
    )
    assert alerts == []


def test_compute_alerts_scoped_for_admin_with_unit():
    from modules.alerts.service import compute_alerts
    alerts = compute_alerts(
        None, ADMIN_WITH_UNIT,
        fetch_low_stock_items=lambda conn, act: [],
        actor_operational_unit_id=lambda c, a: 5,
        fetch_epis=lambda conn, act, unit: [],
    )
    assert alerts == []


# ═══════════════════════════════════════════════════════════════════════════════
# modules/ficha/service.py
# ═══════════════════════════════════════════════════════════════════════════════

def _ficha_conn():
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        CREATE TABLE companies (id INTEGER PRIMARY KEY, name TEXT, cnpj TEXT, logo_type TEXT);
        CREATE TABLE units (id INTEGER PRIMARY KEY, company_id INTEGER, name TEXT, unit_type TEXT);
        CREATE TABLE employees (id INTEGER PRIMARY KEY, company_id INTEGER, unit_id INTEGER, name TEXT);
        CREATE TABLE epi_ficha_periods (
            id INTEGER PRIMARY KEY, company_id INTEGER, employee_id INTEGER, unit_id INTEGER,
            period_start TEXT, period_end TEXT
        );
        CREATE TABLE ficha_epi_audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT, actor_user_id INTEGER, actor_name TEXT,
            actor_role TEXT, employee_id INTEGER, employee_name TEXT, unit_id INTEGER,
            company_id INTEGER, action TEXT, ip_address TEXT, user_agent TEXT, accessed_at TEXT
        );
        CREATE TABLE ficha_epi_snapshots (
            id INTEGER PRIMARY KEY, ficha_period_id INTEGER, company_id INTEGER,
            unit_id INTEGER, employee_id INTEGER, generated_by_user_id INTEGER,
            generated_at TEXT, expires_at TEXT, expired_at TEXT, status TEXT, retention_years INTEGER,
            html_sha256 TEXT, payload_sha256 TEXT
        );
        CREATE TABLE app_meta (key TEXT PRIMARY KEY, value TEXT);
    """)
    conn.execute(
        'ALTER TABLE employees ADD COLUMN employee_id_code TEXT'
    )
    conn.execute('ALTER TABLE employees ADD COLUMN sector TEXT')
    conn.execute('ALTER TABLE employees ADD COLUMN role_name TEXT')
    conn.execute("INSERT INTO companies VALUES (1, 'ACME', '00.000.000/0001-00', '')")
    conn.execute("INSERT INTO units VALUES (5, 1, 'Unidade A', 'fabrica')")
    conn.execute("INSERT INTO units VALUES (9, 1, 'Unidade B', 'fabrica')")
    conn.execute("INSERT INTO employees (id, company_id, unit_id, name) VALUES (100, 1, 9, 'Colaborador B')")
    conn.execute("INSERT INTO epi_ficha_periods VALUES (1, 1, 100, 9, '2026-01-01', '2026-01-31')")
    conn.execute(
        "INSERT INTO ficha_epi_audit_log (actor_user_id, actor_name, actor_role, employee_id, "
        "employee_name, unit_id, company_id, action, ip_address, user_agent, accessed_at) "
        "VALUES (1, 'A', 'admin', 100, 'Colaborador B', 9, 1, 'view', '', '', '2026-01-01T00:00:00')"
    )
    conn.execute(
        "INSERT INTO ficha_epi_snapshots VALUES (1, 1, 1, 9, 100, 1, '2026-01-01T00:00:00', "
        "'2031-01-01T00:00:00', NULL, 'archived', 5, 'h', 'p')"
    )
    conn.commit()
    return conn


def _fake_get_employee(connection, employee_id):
    return {'id': employee_id, 'company_id': 1, 'unit_id': 9, 'name': 'Colaborador B'}


def test_build_ficha_epi_html_by_period_denies_admin_without_unit():
    from modules.ficha.service import build_ficha_epi_html_by_period
    conn = _ficha_conn()
    with pytest.raises(PermissionError, match='unidade operacional'):
        build_ficha_epi_html_by_period(
            conn, 1, ADMIN_NO_UNIT,
            get_employee_fn=_fake_get_employee, actor_unit_id_fn=lambda c, a: None,
        )


def test_build_ficha_epi_html_by_period_denies_cross_unit():
    from modules.ficha.service import build_ficha_epi_html_by_period
    conn = _ficha_conn()
    with pytest.raises(PermissionError, match='própria unidade'):
        build_ficha_epi_html_by_period(
            conn, 1, ADMIN_WITH_UNIT,
            get_employee_fn=_fake_get_employee, actor_unit_id_fn=lambda c, a: 5,
        )


def _patch_actor_unit(monkeypatch, resolver):
    """fetch_ficha_epi_audit_logs faz `from modules.employees.service import
    actor_operational_unit_id` dentro da própria função (reimport local a cada
    chamada) — para interceptar em todos os pontos, o patch precisa cobrir o
    módulo de origem, não só o nome já importado em modules.ficha.service."""
    import modules.employees.service as emp_svc
    import modules.ficha.service as ficha_svc
    monkeypatch.setattr(emp_svc, 'actor_operational_unit_id', resolver)
    monkeypatch.setattr(ficha_svc, 'actor_operational_unit_id', resolver)


def test_fetch_ficha_epi_audit_logs_empty_for_admin_without_unit(monkeypatch):
    from modules.ficha.service import fetch_ficha_epi_audit_logs
    conn = _ficha_conn()
    _patch_actor_unit(monkeypatch, lambda c, a: None)
    result = fetch_ficha_epi_audit_logs(conn, ADMIN_NO_UNIT)
    assert result == []


def test_fetch_ficha_archive_snapshots_empty_for_admin_without_unit(monkeypatch):
    from modules.ficha.service import fetch_ficha_archive_snapshots
    conn = _ficha_conn()
    _patch_actor_unit(monkeypatch, lambda c, a: None)
    result = fetch_ficha_archive_snapshots(conn, ADMIN_NO_UNIT)
    assert result['items'] == []
    assert result['total'] == 0


def test_get_ficha_archive_snapshot_by_id_denies_admin_without_unit(monkeypatch):
    from modules.ficha.service import get_ficha_archive_snapshot_by_id
    conn = _ficha_conn()
    _patch_actor_unit(monkeypatch, lambda c, a: None)
    with pytest.raises(PermissionError, match='unidade operacional'):
        get_ficha_archive_snapshot_by_id(conn, ADMIN_NO_UNIT, 1)


def test_get_ficha_archive_snapshot_by_id_denies_cross_unit(monkeypatch):
    from modules.ficha.service import get_ficha_archive_snapshot_by_id
    conn = _ficha_conn()
    _patch_actor_unit(monkeypatch, lambda c, a: 5)
    with pytest.raises(PermissionError, match='sua unidade operacional'):
        get_ficha_archive_snapshot_by_id(conn, ADMIN_WITH_UNIT, 1)
