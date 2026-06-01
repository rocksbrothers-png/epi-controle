"""Phase 24 — canary_evaluate_visibility_dataset added to all list endpoints."""

import inspect
import json
import sqlite3


# ── helpers ───────────────────────────────────────────────────────────────────

def _conn(mode='shadow'):
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.executescript('''
        CREATE TABLE companies (id INTEGER PRIMARY KEY, name TEXT, active INTEGER DEFAULT 1);
        CREATE TABLE app_meta (key TEXT PRIMARY KEY, value TEXT);
        CREATE TABLE rule_engine_shadow_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER, user_id INTEGER, role TEXT,
            endpoint TEXT, dataset TEXT, mode TEXT,
            legacy_count INTEGER, new_count INTEGER,
            has_diff INTEGER, legacy_only TEXT, new_only TEXT, created_at TEXT
        );
        INSERT INTO companies VALUES (1, 'Test Corp', 1);
    ''')
    framework = {
        'feature_flags': {
            'execution_mode': mode,
            'enable_new_rules_engine': True,
        }
    }
    conn.execute(
        "INSERT INTO app_meta (key, value) VALUES (?, ?)",
        ('configuration_framework:1', json.dumps(framework)),
    )
    conn.commit()
    return conn


ACTOR = {'id': 42, 'company_id': 1, 'role': 'admin'}


# ── import coverage: canary wired in each route file ─────────────────────────

def test_devolutions_routes_imports_canary():
    import modules.devolutions.routes as r
    assert hasattr(r, 'canary_evaluate_visibility_dataset') or \
        'canary_evaluate_visibility_dataset' in inspect.getsource(r)


def test_feedback_routes_imports_canary():
    import modules.feedback.routes as r
    assert 'canary_evaluate_visibility_dataset' in inspect.getsource(r)


def test_ficha_routes_imports_canary():
    import modules.ficha.routes as r
    assert 'canary_evaluate_visibility_dataset' in inspect.getsource(r)


def test_purchases_routes_imports_canary():
    import modules.purchases.routes as r
    assert 'canary_evaluate_visibility_dataset' in inspect.getsource(r)


def test_stock_routes_imports_canary():
    import modules.stock.routes as r
    assert 'canary_evaluate_visibility_dataset' in inspect.getsource(r)


# ── canary called with correct dataset_name in each handler ──────────────────

def test_devolutions_handler_uses_dataset_devolutions():
    import modules.devolutions.routes as r
    src = inspect.getsource(r.handle_get_devolutions)
    assert "dataset_name='devolutions'" in src


def test_feedback_handler_uses_dataset_feedbacks():
    import modules.feedback.routes as r
    src = inspect.getsource(r.handle_get_feedbacks)
    assert "dataset_name='feedbacks'" in src


def test_ficha_handler_uses_dataset_fichas():
    import modules.ficha.routes as r
    src = inspect.getsource(r.handle_get_fichas)
    assert "dataset_name='fichas'" in src


def test_purchases_epi_requests_uses_dataset_epi_requests():
    import modules.purchases.routes as r
    src = inspect.getsource(r.handle_get_epi_requests)
    assert "dataset_name='epi_requests'" in src


def test_stock_available_items_uses_dataset_stock_items():
    import modules.stock.routes as r
    src = inspect.getsource(r.handle_get_stock_available_items)
    assert "dataset_name='stock_items'" in src


def test_stock_epis_uses_dataset_epis():
    import modules.stock.routes as r
    src = inspect.getsource(r.handle_get_stock_epis)
    assert "dataset_name='epis'" in src


# ── canary pass-through for non-unit/employee/epi datasets ───────────────────

def test_canary_passthrough_devolutions():
    from modules.settings.service import canary_evaluate_visibility_dataset
    conn = _conn('shadow')
    items = [{'id': 1, 'epi_id': 10}, {'id': 2, 'epi_id': 11}]
    result = canary_evaluate_visibility_dataset(
        conn, ACTOR,
        endpoint_name='/api/devolutions',
        dataset_name='devolutions',
        legacy_items=items,
    )
    assert result == items


def test_canary_passthrough_feedbacks():
    from modules.settings.service import canary_evaluate_visibility_dataset
    conn = _conn('shadow')
    items = [{'id': 5, 'type': 'complaint'}, {'id': 6, 'type': 'suggestion'}]
    result = canary_evaluate_visibility_dataset(
        conn, ACTOR,
        endpoint_name='/api/feedbacks',
        dataset_name='feedbacks',
        legacy_items=items,
    )
    assert result == items


def test_canary_passthrough_fichas():
    from modules.settings.service import canary_evaluate_visibility_dataset
    conn = _conn('shadow')
    items = [{'id': 3, 'employee_id': 7}, {'id': 4, 'employee_id': 8}]
    result = canary_evaluate_visibility_dataset(
        conn, ACTOR,
        endpoint_name='/api/fichas',
        dataset_name='fichas',
        legacy_items=items,
    )
    assert result == items


def test_canary_passthrough_epi_requests():
    from modules.settings.service import canary_evaluate_visibility_dataset
    conn = _conn('shadow')
    items = [{'id': 20, 'status': 'solicitado'}]
    result = canary_evaluate_visibility_dataset(
        conn, ACTOR,
        endpoint_name='/api/requests',
        dataset_name='epi_requests',
        legacy_items=items,
    )
    assert result == items


def test_canary_passthrough_stock_items():
    from modules.settings.service import canary_evaluate_visibility_dataset
    conn = _conn('shadow')
    items = [{'id': 100, 'qr_code_value': 'QR-001'}, {'id': 101, 'qr_code_value': 'QR-002'}]
    result = canary_evaluate_visibility_dataset(
        conn, ACTOR,
        endpoint_name='/api/stock/available-items',
        dataset_name='stock_items',
        legacy_items=items,
    )
    assert result == items


def test_canary_empty_list_passthrough():
    from modules.settings.service import canary_evaluate_visibility_dataset
    conn = _conn('shadow')
    result = canary_evaluate_visibility_dataset(
        conn, ACTOR,
        endpoint_name='/api/devolutions',
        dataset_name='devolutions',
        legacy_items=[],
    )
    assert result == []


# ── shadow log entry written ──────────────────────────────────────────────────

def test_canary_shadow_log_written_for_devolutions():
    from modules.settings.service import canary_evaluate_visibility_dataset
    conn = _conn('shadow')
    items = [{'id': 1}]
    canary_evaluate_visibility_dataset(
        conn, ACTOR,
        endpoint_name='/api/devolutions',
        dataset_name='devolutions',
        legacy_items=items,
    )
    row = conn.execute("SELECT * FROM rule_engine_shadow_log").fetchone()
    assert row is not None
    assert row['endpoint'] == '/api/devolutions'
    assert row['dataset'] == 'devolutions'
    assert row['legacy_count'] == 1


def test_canary_shadow_log_written_for_feedbacks():
    from modules.settings.service import canary_evaluate_visibility_dataset
    conn = _conn('shadow')
    items = [{'id': 10}, {'id': 11}]
    canary_evaluate_visibility_dataset(
        conn, ACTOR,
        endpoint_name='/api/feedbacks',
        dataset_name='feedbacks',
        legacy_items=items,
    )
    row = conn.execute("SELECT * FROM rule_engine_shadow_log").fetchone()
    assert row is not None
    assert row['dataset'] == 'feedbacks'
    assert row['legacy_count'] == 2
    assert row['new_count'] == 2


def test_canary_shadow_log_written_for_fichas():
    from modules.settings.service import canary_evaluate_visibility_dataset
    conn = _conn('shadow')
    items = [{'id': 50}]
    canary_evaluate_visibility_dataset(
        conn, ACTOR,
        endpoint_name='/api/fichas',
        dataset_name='fichas',
        legacy_items=items,
    )
    row = conn.execute("SELECT * FROM rule_engine_shadow_log").fetchone()
    assert row is not None
    assert row['dataset'] == 'fichas'
    assert row['endpoint'] == '/api/fichas'


def test_canary_shadow_log_written_for_stock_items():
    from modules.settings.service import canary_evaluate_visibility_dataset
    conn = _conn('shadow')
    items = [{'id': 200, 'qr_code_value': 'ABC'}]
    canary_evaluate_visibility_dataset(
        conn, ACTOR,
        endpoint_name='/api/stock/available-items',
        dataset_name='stock_items',
        legacy_items=items,
    )
    row = conn.execute("SELECT * FROM rule_engine_shadow_log").fetchone()
    assert row is not None
    assert row['endpoint'] == '/api/stock/available-items'
    assert row['dataset'] == 'stock_items'


def test_canary_shadow_log_written_for_epi_requests():
    from modules.settings.service import canary_evaluate_visibility_dataset
    conn = _conn('shadow')
    items = [{'id': 1, 'status': 'open'}, {'id': 2, 'status': 'open'}]
    canary_evaluate_visibility_dataset(
        conn, ACTOR,
        endpoint_name='/api/requests',
        dataset_name='epi_requests',
        legacy_items=items,
    )
    row = conn.execute("SELECT * FROM rule_engine_shadow_log").fetchone()
    assert row is not None
    assert row['dataset'] == 'epi_requests'
    assert row['legacy_count'] == 2


# ── enforced mode: still returns all items for non-filtered datasets ──────────

def test_canary_enforced_returns_all_items_for_non_filter_datasets():
    from modules.settings.service import canary_evaluate_visibility_dataset
    conn = _conn('enforced')
    items = [{'id': 1}, {'id': 2}, {'id': 3}]
    result = canary_evaluate_visibility_dataset(
        conn, ACTOR,
        endpoint_name='/api/devolutions',
        dataset_name='devolutions',
        legacy_items=items,
    )
    assert len(result) == 3


def test_canary_enforced_returns_all_fichas():
    from modules.settings.service import canary_evaluate_visibility_dataset
    conn = _conn('enforced')
    items = [{'id': 10}, {'id': 11}]
    result = canary_evaluate_visibility_dataset(
        conn, ACTOR,
        endpoint_name='/api/fichas',
        dataset_name='fichas',
        legacy_items=items,
    )
    assert len(result) == 2


# ── graceful fallback on bad framework ───────────────────────────────────────

def test_canary_falls_back_on_missing_framework():
    from modules.settings.service import canary_evaluate_visibility_dataset
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.executescript('''
        CREATE TABLE companies (id INTEGER PRIMARY KEY);
        INSERT INTO companies VALUES (1);
    ''')
    items = [{'id': 99}]
    result = canary_evaluate_visibility_dataset(
        conn, ACTOR,
        endpoint_name='/api/devolutions',
        dataset_name='devolutions',
        legacy_items=items,
    )
    assert result == items


# ── endpoint_name propagated correctly ───────────────────────────────────────

def test_canary_shadow_log_records_correct_endpoint_name():
    from modules.settings.service import canary_evaluate_visibility_dataset
    conn = _conn('shadow')
    canary_evaluate_visibility_dataset(
        conn, ACTOR,
        endpoint_name='/api/devolutions',
        dataset_name='devolutions',
        legacy_items=[{'id': 1}],
    )
    row = conn.execute("SELECT endpoint FROM rule_engine_shadow_log").fetchone()
    assert row['endpoint'] == '/api/devolutions'


def test_canary_shadow_log_records_correct_user_and_role():
    from modules.settings.service import canary_evaluate_visibility_dataset
    conn = _conn('shadow')
    actor = {'id': 77, 'company_id': 1, 'role': 'manager'}
    canary_evaluate_visibility_dataset(
        conn, actor,
        endpoint_name='/api/feedbacks',
        dataset_name='feedbacks',
        legacy_items=[{'id': 1}],
    )
    row = conn.execute("SELECT user_id, role FROM rule_engine_shadow_log").fetchone()
    assert row['user_id'] == 77
    assert row['role'] == 'manager'


# ── each route file canary call appears AFTER data fetch ─────────────────────

def test_devolutions_canary_positioned_after_fetch():
    import modules.devolutions.routes as r
    src = inspect.getsource(r.handle_get_devolutions)
    fetch_pos = src.find('fetch_devolutions(')
    canary_pos = src.find('canary_evaluate_visibility_dataset(')
    assert fetch_pos < canary_pos, "canary must come after fetch_devolutions"


def test_feedback_canary_positioned_after_fetch():
    import modules.feedback.routes as r
    src = inspect.getsource(r.handle_get_feedbacks)
    fetch_pos = src.find('fetch_feedbacks_for_manager(')
    canary_pos = src.find('canary_evaluate_visibility_dataset(')
    assert fetch_pos < canary_pos, "canary must come after fetch_feedbacks_for_manager"


def test_purchases_canary_positioned_after_fetch():
    import modules.purchases.routes as r
    src = inspect.getsource(r.handle_get_epi_requests)
    fetch_pos = src.find('fetch_epi_requests(')
    canary_pos = src.find('canary_evaluate_visibility_dataset(')
    assert fetch_pos < canary_pos, "canary must come after fetch_epi_requests"
