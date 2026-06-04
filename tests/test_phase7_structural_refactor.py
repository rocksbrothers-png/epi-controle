"""Tests for Phase 7 structural refactor: units, users, auth routes/services."""

import importlib
import types


# ── Module imports ────────────────────────────────────────────────────────────

PHASE7_MODULES = [
    'modules.units.service',
    'modules.units.routes',
    'modules.users.service',
    'modules.users.routes',
    'modules.auth.service',
    'modules.auth.routes',
]


def test_phase7_modules_importable():
    for module_path in PHASE7_MODULES:
        mod = importlib.import_module(module_path)
        assert isinstance(mod, types.ModuleType), f"{module_path} failed to import"


def test_phase7_route_modules_have_register_routes():
    route_modules = [
        'modules.units.routes',
        'modules.users.routes',
        'modules.auth.routes',
    ]
    for module_path in route_modules:
        mod = importlib.import_module(module_path)
        assert hasattr(mod, 'register_routes'), f"{module_path} missing register_routes"
        assert callable(mod.register_routes)


# ── units/service.py exports ──────────────────────────────────────────────────

def test_units_service_has_normalize_unit_type():
    from modules.units import service as us
    assert callable(us.normalize_unit_type)


def test_units_service_normalize_unit_type_values():
    from modules.units.service import normalize_unit_type
    assert normalize_unit_type('navio') == 'embarcacao'
    assert normalize_unit_type('embarcação') == 'embarcacao'
    assert normalize_unit_type('base') == 'base'
    assert normalize_unit_type('plataforma') == 'plataforma'
    assert normalize_unit_type('') == 'base'
    assert normalize_unit_type(None) == 'base'


def test_units_service_has_delete_functions():
    from modules.units import service as us
    assert callable(us.delete_epi_dependencies)
    assert callable(us.delete_unit_dependencies)


def test_units_service_has_fetch_units():
    from modules.units import service as us
    assert callable(us.fetch_units)
    assert callable(us.get_unit_by_id)
    assert callable(us.get_unit_active_jv_name)


# ── units/routes.py exports ───────────────────────────────────────────────────

def test_units_routes_handlers():
    from modules.units import routes as ur
    assert callable(ur.handle_post_units)
    assert callable(ur.handle_put_unit)
    assert callable(ur.handle_delete_unit)


def test_units_routes_registration():
    from core.router import Router
    from modules.units.routes import register_routes
    r = Router()
    register_routes(r)
    paths = [(m, p) for m, p, _, _ in r._routes]
    assert ('POST', '/api/units') in paths
    put_units = [p for m, p, pat, _ in r._routes if m == 'PUT' and 'units' in p]
    del_units = [p for m, p, pat, _ in r._routes if m == 'DELETE' and 'units' in p]
    assert put_units, "PUT /api/units/{id} not registered"
    assert del_units, "DELETE /api/units/{id} not registered"


def test_units_put_regex_matches():
    from core.router import Router
    from modules.units.routes import register_routes
    r = Router()
    register_routes(r)
    captured = {}

    def fake_put(handler, parsed, payload, match):
        captured['id'] = match.group(1)
        return 'ok'

    for i, (m, p, pat, _) in enumerate(r._routes):
        if m == 'PUT' and 'units' in p and pat is not None:
            r._routes[i] = (m, p, pat, fake_put)
            break

    result = r.dispatch('PUT', '/api/units/99', None, None, None)
    assert result == 'ok'
    assert captured.get('id') == '99'


def test_units_delete_regex_matches():
    from core.router import Router
    from modules.units.routes import register_routes
    r = Router()
    register_routes(r)
    captured = {}

    def fake_del(handler, parsed, payload, match):
        captured['id'] = match.group(1)
        return 'deleted'

    for i, (m, p, pat, _) in enumerate(r._routes):
        if m == 'DELETE' and 'units' in p and pat is not None:
            r._routes[i] = (m, p, pat, fake_del)
            break

    result = r.dispatch('DELETE', '/api/units/42', None, None, None)
    assert result == 'deleted'
    assert captured.get('id') == '42'


# ── users/service.py exports ──────────────────────────────────────────────────

def test_users_service_has_authorize_user_management():
    from modules.users import service as us
    assert callable(us.authorize_user_management)


def test_users_service_has_resolve_target_company_id():
    from modules.users import service as us
    assert callable(us.resolve_target_company_id)


def test_users_service_has_ensure_operational_role_link():
    from modules.users import service as us
    assert callable(us.ensure_operational_role_link)


def test_users_service_has_resolve_user_employee_link():
    from modules.users import service as us
    assert callable(us.resolve_user_employee_link)


def test_users_service_has_sql_update_user_constant():
    from modules.users import service as us
    assert hasattr(us, 'SQL_UPDATE_USER')
    assert 'UPDATE users SET' in us.SQL_UPDATE_USER


def test_users_service_has_crud_functions():
    from modules.users import service as us
    assert callable(us.create_user)
    assert callable(us.update_user)
    assert callable(us.delete_user)



# ── users/routes.py exports ───────────────────────────────────────────────────

def test_users_routes_handlers():
    from modules.users import routes as ur
    assert callable(ur.handle_post_users)
    assert callable(ur.handle_put_user)
    assert callable(ur.handle_delete_user)


def test_users_routes_registration():
    from core.router import Router
    from modules.users.routes import register_routes
    r = Router()
    register_routes(r)
    paths = [(m, p) for m, p, _, _ in r._routes]
    assert ('POST', '/api/users') in paths
    put_users = [p for m, p, pat, _ in r._routes if m == 'PUT' and 'users' in p]
    del_users = [p for m, p, pat, _ in r._routes if m == 'DELETE' and 'users' in p]
    assert put_users, "PUT /api/users/{id} not registered"
    assert del_users, "DELETE /api/users/{id} not registered"


def test_users_put_regex_matches():
    from core.router import Router
    from modules.users.routes import register_routes
    r = Router()
    register_routes(r)
    captured = {}

    def fake_put(handler, parsed, payload, match):
        captured['id'] = match.group(1)
        return 'ok'

    for i, (m, p, pat, _) in enumerate(r._routes):
        if m == 'PUT' and 'users' in p and pat is not None:
            r._routes[i] = (m, p, pat, fake_put)

    result = r.dispatch('PUT', '/api/users/7', None, None, None)
    assert result == 'ok'
    assert captured.get('id') == '7'


# ── auth/service.py exports ───────────────────────────────────────────────────

def test_auth_service_has_authenticate_login():
    from modules.auth import service as as_
    assert callable(as_.authenticate_login)


def test_auth_service_has_msg_constants():
    from modules.auth import service as as_
    assert hasattr(as_, 'MSG_LOGIN_FAILED')
    assert hasattr(as_, 'MSG_USER_NOT_FOUND')
    assert as_.MSG_USER_NOT_FOUND == 'Usuário não encontrado.'


def test_auth_service_login_signature():
    """authenticate_login should accept (connection, username, password) without DI."""
    import inspect
    from modules.auth.service import authenticate_login
    sig = inspect.signature(authenticate_login)
    params = list(sig.parameters.keys())
    assert params == ['connection', 'username', 'password'], \
        f"Expected (connection, username, password), got {params}"


# ── auth/routes.py exports ────────────────────────────────────────────────────

def test_auth_routes_has_handle_post_login():
    from modules.auth import routes as ar
    assert callable(ar.handle_post_login)


def test_auth_routes_registration():
    from core.router import Router
    from modules.auth.routes import register_routes
    r = Router()
    register_routes(r)
    paths = [(m, p) for m, p, _, _ in r._routes]
    assert ('POST', '/api/login') in paths


# ── ficha/routes.py already has GET /api/fichas ───────────────────────────────

def test_ficha_routes_has_get_fichas():
    from core.router import Router
    from modules.ficha.routes import register_routes
    r = Router()
    register_routes(r)
    paths = [(m, p) for m, p, _, _ in r._routes]
    assert ('GET', '/api/fichas') in paths


# ── purchases/routes.py already has GET /api/requests ────────────────────────

def test_purchases_routes_has_get_requests():
    from core.router import Router
    from modules.purchases.routes import register_routes
    r = Router()
    register_routes(r)
    paths = [(m, p) for m, p, _, _ in r._routes]
    assert ('GET', '/api/requests') in paths


# ── server_postgres.py global router wiring ───────────────────────────────────

def test_server_postgres_units_routes_wired():
    import server_postgres  # noqa: F401
    from core.router import router
    paths = [(m, p) for m, p, _, _ in router._routes]
    put_units = any(m == 'PUT' and 'units' in p for m, p in paths)
    del_units = any(m == 'DELETE' and 'units' in p for m, p in paths)
    assert ('POST', '/api/units') in paths, "POST /api/units not in global router"
    assert put_units, "PUT /api/units/{id} not in global router"
    assert del_units, "DELETE /api/units/{id} not in global router"


def test_server_postgres_users_routes_wired():
    import server_postgres  # noqa: F401
    from core.router import router
    paths = [(m, p) for m, p, _, _ in router._routes]
    put_users = any(m == 'PUT' and 'users' in p for m, p in paths)
    del_users = any(m == 'DELETE' and 'users' in p for m, p in paths)
    assert ('POST', '/api/users') in paths, "POST /api/users not in global router"
    assert put_users, "PUT /api/users/{id} not in global router"
    assert del_users, "DELETE /api/users/{id} not in global router"


def test_server_postgres_auth_route_wired():
    import server_postgres  # noqa: F401
    from core.router import router
    paths = [(m, p) for m, p, _, _ in router._routes]
    assert ('POST', '/api/login') in paths, "POST /api/login not in global router"


def test_server_postgres_fichas_route_wired():
    import server_postgres  # noqa: F401
    from core.router import router
    paths = [(m, p) for m, p, _, _ in router._routes]
    assert ('GET', '/api/fichas') in paths, "GET /api/fichas not in global router"


def test_server_postgres_requests_route_wired():
    import server_postgres  # noqa: F401
    from core.router import router
    paths = [(m, p) for m, p, _, _ in router._routes]
    assert ('GET', '/api/requests') in paths, "GET /api/requests not in global router"


# ── normalize_unit_type sourced from units.service ────────────────────────────

def test_normalize_unit_type_not_inline_in_server_postgres():
    """normalize_unit_type in server_postgres should come from modules.units.service."""
    import server_postgres as sp
    from modules.units.service import normalize_unit_type as mod_fn
    sp_fn = getattr(sp, 'normalize_unit_type', None)
    assert sp_fn is not None, "normalize_unit_type not found in server_postgres namespace"
    assert sp_fn is mod_fn, \
        "server_postgres.normalize_unit_type should be the same object as units.service.normalize_unit_type"


def test_delete_unit_dependencies_not_inline_in_server_postgres():
    """delete_unit_dependencies in server_postgres should come from modules.units.service."""
    import server_postgres as sp
    from modules.units.service import delete_unit_dependencies as mod_fn
    sp_fn = getattr(sp, 'delete_unit_dependencies', None)
    assert sp_fn is not None, "delete_unit_dependencies not found in server_postgres namespace"
    assert sp_fn is mod_fn, \
        "server_postgres.delete_unit_dependencies should be the same object as units.service.delete_unit_dependencies"


def test_authorize_user_management_not_inline_in_server_postgres():
    """authorize_user_management in server_postgres should come from modules.users.service."""
    import server_postgres as sp
    from modules.users.service import authorize_user_management as mod_fn
    sp_fn = getattr(sp, 'authorize_user_management', None)
    assert sp_fn is not None, "authorize_user_management not found in server_postgres namespace"
    assert sp_fn is mod_fn, \
        "server_postgres.authorize_user_management should be the same object as users.service.authorize_user_management"


# ── server_postgres.py importable with no syntax error ────────────────────────

def test_server_postgres_importable():
    mod = importlib.import_module('server_postgres')
    assert isinstance(mod, types.ModuleType)
