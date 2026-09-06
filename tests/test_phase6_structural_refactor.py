"""Tests for Phase 6 structural refactor: PUT/DELETE wiring, ficha, stock, portal, employees."""

import importlib
import types


# ── Module imports ────────────────────────────────────────────────────────────

def test_ficha_service_new_exports():
    from modules.ficha import service as fs
    assert callable(fs.fetch_ficha_epi_audit_logs)
    assert callable(fs.apply_snapshot_retention)
    assert callable(fs.compute_ficha_period_signature_state)
    assert callable(fs.assert_ficha_period_can_close)
    assert callable(fs.resolve_ficha_period_effective_status)
    assert callable(fs.is_valid_ficha_period_state)


def test_employees_service_exports():
    from modules.employees import service as es
    assert callable(es.normalize_cpf)
    assert callable(es.normalize_preferred_contact_channel)
    assert callable(es.ensure_employee_identity_unique)
    assert callable(es.create_employee)
    assert callable(es.update_employee)


def test_employees_service_normalize_cpf_valid():
    from modules.employees.service import normalize_cpf
    assert normalize_cpf('123.456.789-09') == '12345678909'
    assert normalize_cpf('12345678909') == '12345678909'


def test_employees_service_normalize_cpf_invalid():
    from modules.employees.service import normalize_cpf
    try:
        normalize_cpf('123')
        assert False, 'Should have raised'
    except ValueError as e:
        assert '11' in str(e)


def test_employees_service_normalize_channel():
    from modules.employees.service import normalize_preferred_contact_channel
    assert normalize_preferred_contact_channel('email') == 'email'
    assert normalize_preferred_contact_channel('whatsapp') == 'whatsapp'
    assert normalize_preferred_contact_channel(None) == 'whatsapp'
    assert normalize_preferred_contact_channel('sms') == 'whatsapp'


# ── Route module structure ────────────────────────────────────────────────────

PHASE6_MODULES = [
    'modules.ficha.routes',
    'modules.stock.routes',
    'modules.portal.routes',
    'modules.employees.routes',
]


def test_phase6_modules_importable():
    for module_path in PHASE6_MODULES:
        mod = importlib.import_module(module_path)
        assert isinstance(mod, types.ModuleType), f"{module_path} failed to import"


def test_phase6_modules_have_register_routes():
    for module_path in PHASE6_MODULES:
        mod = importlib.import_module(module_path)
        assert hasattr(mod, 'register_routes'), f"{module_path} missing register_routes"
        assert callable(mod.register_routes)


# ── Route registration coverage ───────────────────────────────────────────────

def _build_router_for(*module_paths):
    from core.router import Router
    r = Router()
    for mp in module_paths:
        importlib.import_module(mp).register_routes(r)
    return r


def _paths(router):
    return [(m, p) for m, p, _, _ in router._routes]


def test_ficha_routes_phase6():
    r = _build_router_for('modules.ficha.routes')
    paths = _paths(r)
    assert ('GET', '/api/ficha-epi-snapshots') in paths
    assert ('GET', '/api/ficha-epi-audit') in paths
    assert ('PUT', '/api/ficha-config') in paths
    assert ('PUT', '/api/ficha-retention-policy') in paths
    assert ('PUT', '/api/ficha-archive/purge-expired') in paths


def test_stock_routes_phase6():
    r = _build_router_for('modules.stock.routes')
    paths = _paths(r)
    assert ('GET', '/api/stock/low') in paths
    assert ('GET', '/api/stock/lookup-qr') in paths
    assert ('GET', '/api/stock/available-items') in paths
    assert ('GET', '/api/stock/movements/report') in paths


def test_portal_routes_phase6():
    r = _build_router_for('modules.portal.routes')
    paths = _paths(r)
    assert ('GET', '/api/employee-access') in paths
    assert ('GET', '/api/employee-access/pdf') in paths
    assert ('POST', '/api/employee-feedback') in paths


def test_employees_routes_phase6():
    r = _build_router_for('modules.employees.routes')
    paths = _paths(r)
    assert ('POST', '/api/employees') in paths
    # PUT and DELETE use regex patterns
    route_patterns = [(m, p) for m, p, pat, _ in r._routes if pat is not None]
    assert any('employees' in p for _, p in route_patterns), "No regex route for employees"
    put_employee = [p for m, p, pat, _ in r._routes if m == 'PUT' and 'employees' in p]
    del_employee = [p for m, p, pat, _ in r._routes if m == 'DELETE' and 'employees' in p]
    assert put_employee, "PUT /api/employees/{id} not registered"
    assert del_employee, "DELETE /api/employees/{id} not registered"


def test_employees_regex_route_matches():
    r = _build_router_for('modules.employees.routes')
    captured = {}

    def fake_put(handler, parsed, payload, match):
        captured['id'] = match.group(1)
        return 'ok'

    # Override the handler to test matching
    for i, (m, p, pat, _) in enumerate(r._routes):
        if m == 'PUT' and 'employees' in p:
            r._routes[i] = (m, p, pat, fake_put)
            break

    result = r.dispatch('PUT', '/api/employees/42', None, None, None)
    assert result == 'ok'
    assert captured.get('id') == '42'


# ── server_postgres wiring: PUT/DELETE dispatch ────────────────────────────────

def test_server_postgres_router_has_put_routes():
    import server_postgres  # noqa: F401
    from core.router import router
    put_routes = [(m, p) for m, p, _, _ in router._routes if m == 'PUT']
    assert len(put_routes) >= 3, f"Expected at least 3 PUT routes, got {len(put_routes)}: {put_routes}"


def test_server_postgres_router_has_delete_routes():
    import server_postgres  # noqa: F401
    from core.router import router
    del_routes = [(m, p) for m, p, _, _ in router._routes if m == 'DELETE']
    assert len(del_routes) >= 1, f"Expected at least 1 DELETE route, got {del_routes}"


def test_server_postgres_employees_routes_wired():
    import server_postgres  # noqa: F401
    from core.router import router
    paths = [(m, p) for m, p, _, _ in router._routes]
    post_emp = any(m == 'POST' and p == '/api/employees' for m, p in paths)
    put_emp = any(m == 'PUT' and 'employees' in p for m, p in paths)
    del_emp = any(m == 'DELETE' and 'employees' in p for m, p in paths)
    assert post_emp, "POST /api/employees not in global router"
    assert put_emp, "PUT /api/employees/{id} not in global router"
    assert del_emp, "DELETE /api/employees/{id} not in global router"


def test_server_postgres_ficha_audit_route_wired():
    import server_postgres  # noqa: F401
    from core.router import router
    paths = [(m, p) for m, p, _, _ in router._routes]
    assert ('GET', '/api/ficha-epi-audit') in paths, "GET /api/ficha-epi-audit not wired"


def test_server_postgres_ficha_put_routes_wired():
    import server_postgres  # noqa: F401
    from core.router import router
    paths = [(m, p) for m, p, _, _ in router._routes]
    assert ('PUT', '/api/ficha-config') in paths
    assert ('PUT', '/api/ficha-retention-policy') in paths
    assert ('PUT', '/api/ficha-archive/purge-expired') in paths


# ── No inline definitions remain in server_postgres ───────────────────────────

def test_normalize_cpf_not_defined_in_server_postgres():
    """normalize_cpf must be imported from employees.service, not defined inline."""
    import server_postgres as sp
    from modules.employees.service import normalize_cpf as mod_normalize_cpf
    sp_normalize_cpf = getattr(sp, 'normalize_cpf', None)
    if sp_normalize_cpf is not None:
        assert sp_normalize_cpf is mod_normalize_cpf, \
            "server_postgres.normalize_cpf should be the same object as employees.service.normalize_cpf"


def test_fetch_ficha_epi_audit_logs_in_ficha_service():
    """fetch_ficha_epi_audit_logs must live in ficha.service."""
    from modules.ficha.service import fetch_ficha_epi_audit_logs
    assert callable(fetch_ficha_epi_audit_logs)


def test_apply_snapshot_retention_in_ficha_service():
    """apply_snapshot_retention must live in ficha.service."""
    from modules.ficha.service import apply_snapshot_retention
    assert callable(apply_snapshot_retention)
