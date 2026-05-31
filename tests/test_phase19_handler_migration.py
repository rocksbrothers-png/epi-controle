"""Tests for Phase 19: final handler migration from server_postgres to modules."""

import importlib

MIGRATED_ROUTES = [
    ('modules.auth.routes',    'GET', '/api/auth-diagnostics'),
    ('modules.auth.routes',    'GET', '/api/db-pool/status'),
    ('modules.auth.routes',    'GET', '/api/bootstrap'),
    ('modules.reports.routes', 'GET', '/api/reports'),
    ('modules.stock.routes',   'GET', '/api/ocr/runtime-status'),
    ('modules.stock.routes',   'GET', '/api/stock/epis'),
    ('modules.ficha.routes',   'GET', r'/api/ficha-epi/(\d+)\.html'),
    ('modules.ficha.routes',   'GET', r'/api/ficha-epi-period/(\d+)\.html'),
    ('modules.ficha.routes',   'GET', '/api/ficha-archive'),
    ('modules.ficha.routes',   'GET', r'/api/ficha-archive/(\d+)\.html'),
]

ABSENT_HANDLERS = [
    '_handle_get_auth_diagnostics',
    '_handle_get_db_pool_status',
    '_handle_get_bootstrap',
    '_handle_get_reports',
    '_handle_get_ocr_runtime_status',
    '_handle_get_stock_epis',
    '_handle_get_ficha_html',
    '_handle_get_ficha_period_html',
    '_handle_get_ficha_archive',
    '_handle_get_ficha_archive_html',
]


def test_migrated_handlers_registered_in_modules():
    from core.router import Router
    for module_path, method, path in MIGRATED_ROUTES:
        mod = importlib.import_module(module_path)
        r = Router()
        mod.register_routes(r)
        paths = [(m, p) for m, p, _, _ in r._routes]
        assert (method, path) in paths, f"{module_path} missing ({method}, {path!r})"


def test_migrated_handlers_not_defined_in_server_postgres():
    import server_postgres as sp
    for name in ABSENT_HANDLERS:
        assert not hasattr(sp, name), f"server_postgres still defines {name}"


def test_fetch_low_stock_items_not_defined_in_server_postgres():
    import server_postgres as sp
    assert not hasattr(sp, 'fetch_low_stock_items'), \
        "fetch_low_stock_items should be removed from server_postgres (use modules.stock.service)"


def test_build_bootstrap_importable_from_modules_auth():
    from modules.auth.service import build_bootstrap
    assert callable(build_bootstrap)


def test_auth_diagnostics_importable_from_modules_auth():
    from modules.auth.service import auth_diagnostics
    assert callable(auth_diagnostics)


def test_canary_evaluate_importable_from_modules_settings():
    from modules.settings.service import canary_evaluate_visibility_dataset
    assert callable(canary_evaluate_visibility_dataset)


def test_legacy_token_columns_not_added_by_ensure_user_columns():
    import sqlite3
    from core.schema import ensure_user_columns
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.execute('CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT, role TEXT, company_id INTEGER, active INTEGER, linked_employee_id INTEGER)')
    ensure_user_columns(conn)
    cols = [row[1] for row in conn.execute('PRAGMA table_info(users)').fetchall()]
    assert 'employee_access_token' not in cols
    assert 'employee_access_expires_at' not in cols
