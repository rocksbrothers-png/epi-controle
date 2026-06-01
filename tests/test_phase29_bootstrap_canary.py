"""Phase 29 — Bootstrap canary + allow_new_engine_response."""

import inspect
import json
import sqlite3


# ── helpers ───────────────────────────────────────────────────────────────────

def _conn(mode='enforced', rollout=100, allow_new=True, company_ids=(1,)):
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
    ''')
    for cid in company_ids:
        conn.execute('INSERT INTO companies VALUES (?, ?, 1)', (cid, f'Empresa {cid}'))
    framework = {
        'feature_flags': {
            'execution_mode': mode,
            'enable_new_rules_engine': True,
            'rollout_percentage': rollout,
            'allow_new_engine_response': allow_new,
        }
    }
    for cid in company_ids:
        conn.execute(
            "INSERT INTO app_meta (key, value) VALUES (?, ?)",
            (f'configuration_framework:{cid}', json.dumps(framework)),
        )
    conn.commit()
    return conn


ACTOR = {'id': 1, 'company_id': 1, 'role': 'admin'}


# ── ensure_rule_engine_enforced_all_companies ─────────────────────────────────

def test_enforced_sets_allow_new_engine_response_true():
    from core.schema import ensure_rule_engine_enforced_all_companies
    conn = _conn(mode='off', rollout=0, allow_new=False)
    ensure_rule_engine_enforced_all_companies(conn)
    row = conn.execute("SELECT value FROM app_meta WHERE key = 'configuration_framework:1'").fetchone()
    fw = json.loads(row['value'])
    assert fw['feature_flags']['allow_new_engine_response'] is True


def test_enforced_sets_execution_mode_enforced():
    from core.schema import ensure_rule_engine_enforced_all_companies
    conn = _conn(mode='shadow', rollout=50, allow_new=False)
    ensure_rule_engine_enforced_all_companies(conn)
    row = conn.execute("SELECT value FROM app_meta WHERE key = 'configuration_framework:1'").fetchone()
    fw = json.loads(row['value'])
    assert fw['feature_flags']['execution_mode'] == 'enforced'
    assert fw['feature_flags']['rollout_percentage'] == 100


def test_enforced_idempotent_when_already_complete():
    from core.schema import ensure_rule_engine_enforced_all_companies
    conn = _conn(mode='enforced', rollout=100, allow_new=True)
    conn.execute("UPDATE app_meta SET value = ? WHERE key = 'configuration_framework:1'",
                 (json.dumps({'feature_flags': {'execution_mode': 'enforced', 'rollout_percentage': 100,
                                                'enable_new_rules_engine': True, 'allow_new_engine_response': True}}),))
    conn.commit()
    ensure_rule_engine_enforced_all_companies(conn)
    row = conn.execute("SELECT value FROM app_meta WHERE key = 'configuration_framework:1'").fetchone()
    fw = json.loads(row['value'])
    assert fw['feature_flags']['allow_new_engine_response'] is True


def test_enforced_upgrades_partial_state_missing_allow_flag():
    """Companies already in enforced+100 but without allow_new_engine_response must be upgraded."""
    from core.schema import ensure_rule_engine_enforced_all_companies
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.executescript('''
        CREATE TABLE companies (id INTEGER PRIMARY KEY, name TEXT, active INTEGER DEFAULT 1);
        CREATE TABLE app_meta (key TEXT PRIMARY KEY, value TEXT);
        INSERT INTO companies VALUES (1, 'Empresa', 1);
    ''')
    conn.execute(
        "INSERT INTO app_meta VALUES (?, ?)",
        ('configuration_framework:1', json.dumps({
            'feature_flags': {'execution_mode': 'enforced', 'rollout_percentage': 100,
                              'enable_new_rules_engine': True}
        })),
    )
    conn.commit()
    ensure_rule_engine_enforced_all_companies(conn)
    row = conn.execute("SELECT value FROM app_meta WHERE key = 'configuration_framework:1'").fetchone()
    fw = json.loads(row['value'])
    assert fw['feature_flags']['allow_new_engine_response'] is True


def test_enforced_applies_to_multiple_companies():
    from core.schema import ensure_rule_engine_enforced_all_companies
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.executescript('''
        CREATE TABLE companies (id INTEGER PRIMARY KEY, name TEXT, active INTEGER DEFAULT 1);
        CREATE TABLE app_meta (key TEXT PRIMARY KEY, value TEXT);
        INSERT INTO companies VALUES (1, 'A', 1);
        INSERT INTO companies VALUES (2, 'B', 1);
        INSERT INTO companies VALUES (3, 'C', 1);
    ''')
    conn.commit()
    ensure_rule_engine_enforced_all_companies(conn)
    for cid in (1, 2, 3):
        row = conn.execute(f"SELECT value FROM app_meta WHERE key = 'configuration_framework:{cid}'").fetchone()
        fw = json.loads(row['value'])
        assert fw['feature_flags']['allow_new_engine_response'] is True
        assert fw['feature_flags']['execution_mode'] == 'enforced'


# ── canary returns candidate_items in enforced mode ───────────────────────────

def test_canary_returns_candidate_items_in_enforced_mode_for_units():
    from modules.settings.service import canary_evaluate_visibility_dataset
    conn = _conn(mode='enforced', rollout=100, allow_new=True)
    items = [
        {'id': 1, 'unit_id': 10, 'active_joinventure': ''},
        {'id': 2, 'unit_id': 20, 'active_joinventure': ''},
    ]
    result = canary_evaluate_visibility_dataset(
        conn, ACTOR,
        endpoint_name='/api/bootstrap',
        dataset_name='units',
        legacy_items=items,
    )
    assert isinstance(result, list)


def test_canary_returns_candidate_items_in_enforced_mode_for_employees():
    from modules.settings.service import canary_evaluate_visibility_dataset
    conn = _conn(mode='enforced', rollout=100, allow_new=True)
    items = [{'id': 5, 'unit_id': 10, 'active_joinventure': ''}]
    result = canary_evaluate_visibility_dataset(
        conn, ACTOR,
        endpoint_name='/api/bootstrap',
        dataset_name='employees',
        legacy_items=items,
    )
    assert isinstance(result, list)


def test_canary_returns_candidate_items_in_enforced_mode_for_epis():
    from modules.settings.service import canary_evaluate_visibility_dataset
    conn = _conn(mode='enforced', rollout=100, allow_new=True)
    items = [{'id': 99, 'unit_id': 10, 'active_joinventure': ''}]
    result = canary_evaluate_visibility_dataset(
        conn, ACTOR,
        endpoint_name='/api/bootstrap',
        dataset_name='epis',
        legacy_items=items,
    )
    assert isinstance(result, list)


# ── build_bootstrap has canary for units, employees, epis ────────────────────

def test_bootstrap_calls_canary_for_units():
    from modules.auth.service import build_bootstrap
    src = inspect.getsource(build_bootstrap)
    assert "dataset_name='units'" in src
    assert "endpoint_name='/api/bootstrap'" in src
    assert 'units_visibility_canary' in src


def test_bootstrap_calls_canary_for_employees():
    from modules.auth.service import build_bootstrap
    src = inspect.getsource(build_bootstrap)
    assert "dataset_name='employees'" in src
    assert 'employees_visibility_canary' in src


def test_bootstrap_calls_canary_for_epis():
    from modules.auth.service import build_bootstrap
    src = inspect.getsource(build_bootstrap)
    assert "dataset_name='epis'" in src
    assert 'epis_visibility_canary' in src


def test_bootstrap_canary_wrapped_in_safe_section():
    """Each canary call must be inside _safe_bootstrap_section for graceful degradation."""
    from modules.auth.service import build_bootstrap
    src = inspect.getsource(build_bootstrap)
    assert src.count('_safe_bootstrap_section') >= 3
    assert 'units_visibility_canary' in src
    assert 'employees_visibility_canary' in src
    assert 'epis_visibility_canary' in src


# ── portal/handle_get_employee_access: NOT a canary candidate ────────────────

def test_portal_employee_access_uses_epi_scope_not_canary():
    """Portal employee access uses is_epi_visible_for_unit (JV-aware unit scope),
    not the rule engine canary. Actor is a portal token holder, not an admin."""
    import modules.portal.routes as r
    src = inspect.getsource(r.handle_get_employee_access)
    assert 'is_epi_visible_for_unit' in src
    assert 'canary_evaluate_visibility_dataset' not in src


# ── settings/handle_get_rules_engine_shadow_diff: NOT a canary candidate ─────

def test_shadow_diff_handler_does_not_wrap_itself_in_canary():
    """The shadow diff endpoint IS the canary log — wrapping it in canary would be circular."""
    import modules.settings.routes as r
    src = inspect.getsource(r.handle_get_rules_engine_shadow_diff)
    assert 'canary_evaluate_visibility_dataset' not in src
    assert 'fetch_shadow_log' in src


# ── shadow log written in enforced mode ──────────────────────────────────────

def test_shadow_log_written_for_bootstrap_units_in_enforced_mode():
    from modules.settings.service import canary_evaluate_visibility_dataset
    conn = _conn(mode='enforced', rollout=100, allow_new=True)
    conn.execute('''CREATE TABLE IF NOT EXISTS rule_engine_shadow_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT, company_id INTEGER, user_id INTEGER,
        role TEXT, endpoint TEXT, dataset TEXT, mode TEXT,
        legacy_count INTEGER, new_count INTEGER, has_diff INTEGER,
        legacy_only TEXT, new_only TEXT, created_at TEXT)''')
    conn.commit()
    items = [{'id': 1, 'unit_id': 10, 'active_joinventure': ''}]
    canary_evaluate_visibility_dataset(
        conn, ACTOR,
        endpoint_name='/api/bootstrap',
        dataset_name='units',
        legacy_items=items,
    )
    row = conn.execute("SELECT * FROM rule_engine_shadow_log").fetchone()
    assert row is not None
    assert row['endpoint'] == '/api/bootstrap'
    assert row['dataset'] == 'units'
    assert row['mode'] == 'enforced'
