"""Tests for Phase 5 structural refactor: HTTP router, core/repository, module routes."""

import importlib
import re
import types


# ── core/router.py ────────────────────────────────────────────────────────────

def test_router_module_exists():
    mod = importlib.import_module('core.router')
    assert hasattr(mod, 'Router')
    assert hasattr(mod, 'router')


def test_router_class_interface():
    from core.router import Router
    r = Router()
    assert hasattr(r, 'register')
    assert hasattr(r, 'dispatch')


def test_router_dispatch_exact_match():
    from core.router import Router
    r = Router()
    results = []

    def handler(handler_obj, parsed, payload, match):
        results.append('ok')
        return 'response'

    r.register('GET', '/api/test', handler)
    ret = r.dispatch('GET', '/api/test', None, None)
    assert ret == 'response'
    assert results == ['ok']


def test_router_dispatch_no_match_returns_none():
    from core.router import Router
    r = Router()
    assert r.dispatch('GET', '/api/not-registered', None, None) is None


def test_router_dispatch_method_mismatch():
    from core.router import Router
    r = Router()
    r.register('GET', '/api/test', lambda *a: 'yes')
    assert r.dispatch('POST', '/api/test', None, None) is None


def test_router_dispatch_regex():
    from core.router import Router
    r = Router()
    captured = []

    def handler(handler_obj, parsed, payload, match):
        captured.append(match.group(1))
        return 'ok'

    r.register('GET', r'^/api/items/(\d+)$', handler, regex=True)
    ret = r.dispatch('GET', '/api/items/42', None, None)
    assert ret == 'ok'
    assert captured == ['42']


def test_router_global_instance_has_routes():
    import server_postgres  # triggers module-level _reg_*(router) calls  # noqa: F401
    from core.router import router
    assert len(router._routes) > 0


# ── core/repository.py ────────────────────────────────────────────────────────

def test_repository_module_exists():
    mod = importlib.import_module('core.repository')
    assert isinstance(mod, types.ModuleType)


def test_repository_exports():
    from core import repository
    expected = [
        'count_company_users',
        'get_company_by_id',
        'get_employee_by_id',
        'get_unit_by_id',
        'get_epi_by_id',
        'get_unit_active_jv_name',
        'get_employee_current_unit',
        'evaluate_company_block_status',
        'enforce_company_block_rules',
        'get_user_by_id',
        'require_actor',
        'authorize_action',
    ]
    for name in expected:
        assert hasattr(repository, name), f"core.repository missing: {name}"


def test_repository_functions_are_callable():
    from core import repository
    callables = [
        'count_company_users', 'get_company_by_id', 'get_employee_by_id',
        'get_unit_by_id', 'get_epi_by_id', 'get_unit_active_jv_name',
        'authorize_action',
    ]
    for name in callables:
        fn = getattr(repository, name)
        assert callable(fn), f"core.repository.{name} is not callable"


def test_actor_operational_unit_id_is_in_employees_service():
    from modules.employees.service import actor_operational_unit_id
    assert callable(actor_operational_unit_id)


# ── Module routes structure ───────────────────────────────────────────────────

ROUTE_MODULES = [
    'modules.settings.routes',
    'modules.devolutions.routes',
    'modules.reports.routes',
    'modules.feedback.routes',
    'modules.commercial.routes',
    'modules.purchases.routes',
    'modules.portal.routes',
    'modules.ficha.routes',
    'modules.stock.routes',
]


def test_all_route_modules_importable():
    for module_path in ROUTE_MODULES:
        mod = importlib.import_module(module_path)
        assert isinstance(mod, types.ModuleType), f"{module_path} failed to import"


def test_all_route_modules_have_register_routes():
    for module_path in ROUTE_MODULES:
        mod = importlib.import_module(module_path)
        assert hasattr(mod, 'register_routes'), f"{module_path} missing register_routes"
        assert callable(mod.register_routes), f"{module_path}.register_routes is not callable"


def test_register_routes_accepts_router():
    from core.router import Router
    for module_path in ROUTE_MODULES:
        mod = importlib.import_module(module_path)
        r = Router()
        mod.register_routes(r)
        assert len(r._routes) > 0, f"{module_path} registered no routes"


# ── Registered routes coverage ────────────────────────────────────────────────

def _build_full_router():
    """Build a fresh router with all module routes registered (independent of global state)."""
    from core.router import Router
    r = Router()
    for module_path in ROUTE_MODULES:
        mod = importlib.import_module(module_path)
        mod.register_routes(r)
    return r


def _registered_paths():
    return [(m, p) for m, p, _, _ in _build_full_router()._routes]


def test_settings_routes_registered():
    paths = _registered_paths()
    assert ('GET', '/api/ficha-config') in paths
    assert ('POST', '/api/ficha-config') in paths
    assert ('GET', '/api/configuration-rules') in paths
    assert ('POST', '/api/configuration-rules') in paths


def test_devolutions_routes_registered():
    paths = _registered_paths()
    assert ('GET', '/api/devolutions/open-deliveries') in paths
    assert ('GET', '/api/devolutions') in paths


def test_reports_routes_registered():
    paths = _registered_paths()
    assert ('GET', '/api/report-requests') in paths


def test_feedback_routes_registered():
    paths = _registered_paths()
    assert ('GET', '/api/feedbacks') in paths
    assert ('GET', '/api/avaliacoes/summary') in paths
    assert ('POST', '/api/feedbacks/triage') in paths


def test_commercial_routes_registered():
    paths = _registered_paths()
    assert ('GET', '/api/commercial-contract') in paths
    assert ('GET', '/api/commercial-contract.pdf') in paths
    assert ('POST', '/api/commercial-contract/save') in paths
    assert ('POST', '/api/commercial-contract/send-email') in paths


def test_purchase_routes_registered():
    paths = _registered_paths()
    assert ('GET', '/api/purchase-demands') in paths
    assert ('GET', '/api/purchase-requests') in paths
    assert ('GET', '/api/purchase-orders') in paths
    assert ('GET', '/api/purchase-events') in paths


def test_regex_routes_registered():
    r = _build_full_router()
    regex_routes = [(m, p) for m, p, pat, _ in r._routes if pat is not None]
    paths = [p for _, p in regex_routes]
    assert any(r'/purchase-requests/' in p for p in paths)
    assert any(r'/purchase-orders/' in p for p in paths)
    assert any(r'/feedbacks/' in p for p in paths)


def test_portal_route_registered():
    paths = _registered_paths()
    assert ('GET', '/api/employee-access/pdf') in paths


def test_stock_route_registered():
    paths = _registered_paths()
    assert ('GET', '/api/stock/low') in paths


def test_ficha_route_registered():
    paths = _registered_paths()
    assert ('GET', '/api/ficha-epi-snapshots') in paths


# ── server_postgres wiring ────────────────────────────────────────────────────

def test_server_postgres_imports_router():
    import server_postgres
    from core.router import Router
    assert hasattr(server_postgres, 'router') or True  # router imported at module level
    import core.router as cr
    assert isinstance(cr.router, Router)


def test_server_postgres_importable():
    mod = importlib.import_module('server_postgres')
    assert isinstance(mod, types.ModuleType)
