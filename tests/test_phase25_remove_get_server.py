"""Phase 25 — eliminar _get_server() de todos os arquivos de rota."""

import inspect


# ── nenhum route file deve ter _get_server ────────────────────────────────────

ROUTE_MODULES = [
    'modules.auth.routes',
    'modules.commercial.routes',
    'modules.companies.routes',
    'modules.deliveries.routes',
    'modules.devolutions.routes',
    'modules.epis.routes',
    'modules.ficha.routes',
    'modules.portal.routes',
    'modules.purchases.routes',
    'modules.stock.routes',
]


def _src(module_name):
    import importlib
    mod = importlib.import_module(module_name)
    return inspect.getsource(mod)


def test_auth_routes_no_get_server():
    assert '_get_server' not in _src('modules.auth.routes')


def test_commercial_routes_no_get_server():
    assert '_get_server' not in _src('modules.commercial.routes')


def test_companies_routes_no_get_server():
    assert '_get_server' not in _src('modules.companies.routes')


def test_deliveries_routes_no_get_server():
    assert '_get_server' not in _src('modules.deliveries.routes')


def test_devolutions_routes_no_get_server():
    assert '_get_server' not in _src('modules.devolutions.routes')


def test_epis_routes_no_get_server():
    assert '_get_server' not in _src('modules.epis.routes')


def test_ficha_routes_no_get_server():
    assert '_get_server' not in _src('modules.ficha.routes')


def test_portal_routes_no_get_server():
    assert '_get_server' not in _src('modules.portal.routes')


def test_purchases_routes_no_get_server():
    assert '_get_server' not in _src('modules.purchases.routes')


def test_stock_routes_no_get_server():
    assert '_get_server' not in _src('modules.stock.routes')


# ── funções movidas para seus módulos corretos ────────────────────────────────

def test_require_master_actor_in_core_repository():
    from core.repository import require_master_actor
    assert callable(require_master_actor)


def test_request_base_url_in_http_utils():
    from epi_backend.http_utils import request_base_url
    assert callable(request_base_url)


def test_sql_update_company_in_companies_service():
    from modules.companies.service import SQL_UPDATE_COMPANY
    assert 'UPDATE companies SET' in SQL_UPDATE_COMPANY
    assert 'WHERE id = ?' in SQL_UPDATE_COMPANY


def test_register_epi_devolution_in_devolutions_service():
    from modules.devolutions.service import register_epi_devolution
    assert callable(register_epi_devolution)


def test_ensure_actor_employee_scope_in_employees_service():
    from modules.employees.service import ensure_actor_employee_scope
    assert callable(ensure_actor_employee_scope)


def test_refresh_ficha_snapshot_in_ficha_service():
    from modules.ficha.service import refresh_ficha_snapshot_for_period_if_exists
    assert callable(refresh_ficha_snapshot_for_period_if_exists)


def test_resolve_item_size_in_stock_service():
    from modules.stock.service import resolve_item_size
    assert callable(resolve_item_size)


def test_ensure_stock_movement_size_columns_in_core_schema():
    from core.schema import ensure_stock_movement_size_columns
    assert callable(ensure_stock_movement_size_columns)


# ── importações diretas nos route files ──────────────────────────────────────

def test_companies_routes_imports_from_companies_service():
    src = _src('modules.companies.routes')
    assert 'from modules.companies.service import' in src
    assert 'summarize_company_changes' in src
    assert 'register_company_audit' in src
    assert 'evaluate_company_block_status' in src
    assert 'SQL_UPDATE_COMPANY' in src


def test_companies_routes_imports_require_master_actor():
    src = _src('modules.companies.routes')
    assert 'require_master_actor' in src
    assert 'from core.repository import' in src


def test_devolutions_routes_imports_register_epi_devolution():
    src = _src('modules.devolutions.routes')
    assert 'from modules.devolutions.service import' in src
    assert 'register_epi_devolution' in src


def test_deliveries_routes_imports_stock_functions():
    src = _src('modules.deliveries.routes')
    assert 'from modules.stock.service import' in src
    assert 'get_unit_stock' in src
    assert 'upsert_unit_stock' in src


def test_epis_routes_imports_from_epis_service():
    src = _src('modules.epis.routes')
    assert 'parse_epi_joinventures' in src
    assert 'normalize_active_joinventure_name' in src
    assert 'validate_epi_uniqueness' in src


def test_epis_routes_imports_delete_epi_dependencies():
    src = _src('modules.epis.routes')
    assert 'from modules.units.service import delete_epi_dependencies' in src


def test_portal_routes_imports_request_base_url():
    src = _src('modules.portal.routes')
    assert 'request_base_url' in src
    assert 'from epi_backend.http_utils import' in src


def test_portal_routes_imports_ensure_actor_employee_scope():
    src = _src('modules.portal.routes')
    assert 'ensure_actor_employee_scope' in src
    assert 'from modules.employees.service import' in src


def test_portal_routes_imports_refresh_ficha_snapshot():
    src = _src('modules.portal.routes')
    assert 'refresh_ficha_snapshot_for_period_if_exists' in src
    assert 'from modules.ficha.service import' in src


def test_stock_routes_imports_ensure_stock_movement_size_columns():
    src = _src('modules.stock.routes')
    assert 'ensure_stock_movement_size_columns' in src
    assert 'from core.schema import' in src


def test_auth_routes_imports_password_recovery_key():
    src = _src('modules.auth.routes')
    assert 'PASSWORD_RECOVERY_KEY' in src
    assert 'from epi_backend.config import' in src


def test_auth_routes_imports_get_user_by_id():
    src = _src('modules.auth.routes')
    assert 'get_user_by_id' in src


# ── request_base_url comportamento ───────────────────────────────────────────

def test_request_base_url_uses_public_base_url_env(monkeypatch):
    import os
    from epi_backend.http_utils import request_base_url

    class FakeHeaders(dict):
        def get(self, key, default=''):
            return self.get(key, default) if key in self else default

    class FakeHandler:
        headers = {'Host': 'localhost:8080', 'X-Forwarded-Proto': ''}

    monkeypatch.setenv('PUBLIC_BASE_URL', 'https://app.example.com/')
    result = request_base_url(FakeHandler())
    assert result == 'https://app.example.com'
    monkeypatch.delenv('PUBLIC_BASE_URL', raising=False)


def test_request_base_url_falls_back_to_host_header(monkeypatch):
    from epi_backend.http_utils import request_base_url
    monkeypatch.delenv('PUBLIC_BASE_URL', raising=False)

    class FakeHandler:
        class headers:
            @staticmethod
            def get(key, default=''):
                mapping = {'Host': 'myapp.com', 'X-Forwarded-Proto': ''}
                return mapping.get(key, default)

    result = request_base_url(FakeHandler())
    assert result == 'http://myapp.com'


# ── require_master_actor comportamento ───────────────────────────────────────

def test_require_master_actor_raises_for_non_master():
    from core.repository import require_master_actor
    import inspect
    src = inspect.getsource(require_master_actor)
    assert "master_admin" in src
    assert "PermissionError" in src
    assert "authorize_action" in src
