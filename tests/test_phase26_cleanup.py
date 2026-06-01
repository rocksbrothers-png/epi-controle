"""Phase 26 — Database cleanup + fechar imports de server_postgres em produção."""

import inspect


# ── epi_backend.bootstrap ────────────────────────────────────────────────────

def test_bootstrap_module_exists():
    from epi_backend.bootstrap import (
        _get_bootstrap_state,
        _set_bootstrap_state,
        current_runtime_health,
        runtime_probe_response,
        BOOTSTRAP_READY_EXEMPT_PATHS,
    )
    assert callable(_get_bootstrap_state)
    assert callable(_set_bootstrap_state)
    assert callable(current_runtime_health)
    assert callable(runtime_probe_response)
    assert '/api/login' in BOOTSTRAP_READY_EXEMPT_PATHS


def test_bootstrap_state_round_trip():
    from epi_backend.bootstrap import _get_bootstrap_state, _set_bootstrap_state
    _set_bootstrap_state(ready=True, error_code='', error_kind='', error_message='',
                         started_at='2026-06-01T00:00:00', completed_at='2026-06-01T00:00:05')
    state = _get_bootstrap_state()
    assert state['ready'] is True
    assert state['error_code'] == ''
    _set_bootstrap_state(ready=False, error_code='', error_kind='', error_message='',
                         started_at='', completed_at='')


def test_current_runtime_health_phase_ready():
    from epi_backend.bootstrap import _set_bootstrap_state, current_runtime_health
    _set_bootstrap_state(ready=True, error_code='', error_kind='', error_message='',
                         started_at='t', completed_at='t')
    h = current_runtime_health()
    assert h['phase'] == 'ready'
    assert h['ready'] is True
    _set_bootstrap_state(ready=False, error_code='', error_kind='', error_message='',
                         started_at='', completed_at='')


def test_runtime_probe_response_not_ready_503():
    from epi_backend.bootstrap import _set_bootstrap_state, runtime_probe_response
    _set_bootstrap_state(ready=False, error_code='', error_kind='', error_message='',
                         started_at='t', completed_at='')
    code, payload = runtime_probe_response('ready')
    assert code == 503
    assert payload['status'] == 'starting'
    _set_bootstrap_state(ready=False, error_code='', error_kind='', error_message='',
                         started_at='', completed_at='')


def test_runtime_probe_liveness_always_200():
    from epi_backend.bootstrap import _set_bootstrap_state, runtime_probe_response
    _set_bootstrap_state(ready=False, error_code='', error_kind='', error_message='',
                         started_at='', completed_at='')
    code, payload = runtime_probe_response('live')
    assert code == 200


# ── server_postgres re-exports bootstrap ─────────────────────────────────────

def test_server_postgres_reexports_set_bootstrap_state():
    import server_postgres
    assert callable(server_postgres._set_bootstrap_state)
    assert callable(server_postgres._get_bootstrap_state)
    assert callable(server_postgres.current_runtime_health)
    assert callable(server_postgres.runtime_probe_response)


def test_server_postgres_no_own_bootstrap_state_dict():
    """server_postgres deve importar DB_BOOTSTRAP_STATE de epi_backend.bootstrap, não definir."""
    import server_postgres
    import epi_backend.bootstrap as bs
    assert server_postgres.DB_BOOTSTRAP_STATE is bs.DB_BOOTSTRAP_STATE


# ── modules/auth/routes.py não importa server_postgres ───────────────────────

def test_auth_routes_no_server_postgres_import():
    import modules.auth.routes
    src = inspect.getsource(modules.auth.routes)
    assert 'import server_postgres' not in src


def test_auth_routes_uses_epi_backend_bootstrap():
    import modules.auth.routes
    src = inspect.getsource(modules.auth.routes)
    assert 'from epi_backend.bootstrap import' in src


# ── modules/users/service.py não importa server_postgres ─────────────────────

def test_users_service_no_server_postgres_import():
    import modules.users.service
    src = inspect.getsource(modules.users.service)
    assert 'import server_postgres' not in src
    assert '_get_ensure_company_user_limit' not in src


def test_users_service_imports_ensure_company_user_limit_directly():
    from modules.users.service import ensure_company_user_limit
    assert callable(ensure_company_user_limit)


# ── server_postgres não define mais request_base_url nem require_master_actor ─

def test_server_postgres_no_own_request_base_url():
    src = inspect.getsource(__import__('server_postgres'))
    assert 'def request_base_url' not in src


def test_server_postgres_no_own_require_master_actor():
    src = inspect.getsource(__import__('server_postgres'))
    assert 'def require_master_actor' not in src


# ── ensure_migrate_legacy_portal_tokens fora do boot ─────────────────────────

def test_ensure_migrate_legacy_portal_tokens_not_in_boot():
    src = inspect.getsource(__import__('server_postgres'))
    assert 'ensure_migrate_legacy_portal_tokens' not in src


# ── user_unit_links removida do schema ───────────────────────────────────────

def test_schema_no_create_user_unit_links():
    import core.schema
    src = inspect.getsource(core.schema)
    assert 'CREATE TABLE IF NOT EXISTS user_unit_links' not in src


def test_fetch_user_unit_links_admin_path_returns_empty():
    from modules.purchases.service import fetch_user_unit_links
    assert fetch_user_unit_links(None, 1, None) == []
    assert fetch_user_unit_links(None, 1, 5) == []


def test_delete_user_unit_link_raises_value_error():
    import pytest
    from modules.purchases.service import delete_user_unit_link
    with pytest.raises(ValueError, match='user_unit_links foi removida'):
        delete_user_unit_link(None, 1, 1)


def test_handle_delete_user_unit_link_source_returns_410():
    """handle_delete_user_unit_link deve retornar 410 (sem DB access)."""
    import modules.purchases.routes as pr
    src = inspect.getsource(pr.handle_delete_user_unit_link)
    assert '410' in src
    assert 'DEPRECATED' in src


# ── migrations criadas ────────────────────────────────────────────────────────

def test_migration_006_drop_user_unit_links_exists():
    import importlib
    m = importlib.import_module('epi_backend.migrations.006_drop_user_unit_links')
    assert m.MIGRATION_ID == '006_drop_user_unit_links'
    assert callable(m.run)


def test_migration_007_drop_epi_ficha_periods_legacy_exists():
    import importlib
    m = importlib.import_module('epi_backend.migrations.007_drop_epi_ficha_periods_legacy')
    assert m.MIGRATION_ID == '007_drop_epi_ficha_periods_legacy'
    assert callable(m.run)
