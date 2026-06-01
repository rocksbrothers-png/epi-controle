"""Phase 30 — Canary para users no bootstrap + validação de filtros multitenant."""

import inspect
import json
import sqlite3


# ── helpers ───────────────────────────────────────────────────────────────────

def _conn(mode='enforced', rollout=100):
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
        INSERT INTO companies VALUES (1, 'Empresa A', 1);
    ''')
    framework = {
        'feature_flags': {
            'execution_mode': mode,
            'enable_new_rules_engine': True,
            'rollout_percentage': rollout,
            'allow_new_engine_response': True,
        }
    }
    conn.execute(
        "INSERT INTO app_meta VALUES (?, ?)",
        ('configuration_framework:1', json.dumps(framework)),
    )
    conn.commit()
    return conn


ACTOR = {'id': 1, 'company_id': 1, 'role': 'admin'}


# ── build_bootstrap wraps users in canary ────────────────────────────────────

def test_bootstrap_calls_canary_for_users():
    from modules.auth.service import build_bootstrap
    src = inspect.getsource(build_bootstrap)
    assert "dataset_name='users'" in src
    assert "endpoint_name='/api/bootstrap'" in src
    assert 'users_visibility_canary' in src


def test_bootstrap_users_extracted_before_payload():
    """users_list must be extracted before the payload dict is built."""
    from modules.auth.service import build_bootstrap
    src = inspect.getsource(build_bootstrap)
    users_list_pos = src.find('users_list =')
    payload_pos = src.find('payload = {')
    assert users_list_pos < payload_pos, "users_list must be built before the payload dict"


def test_bootstrap_users_canary_wrapped_in_safe_section():
    from modules.auth.service import build_bootstrap
    src = inspect.getsource(build_bootstrap)
    assert 'users_visibility_canary' in src
    assert src.count('_safe_bootstrap_section') >= 4


def test_bootstrap_payload_uses_users_list_variable():
    from modules.auth.service import build_bootstrap
    src = inspect.getsource(build_bootstrap)
    assert "'users': users_list" in src


# ── canary passthrough for users dataset (non-filtered) ──────────────────────

def test_canary_passthrough_for_users_dataset():
    from modules.settings.service import canary_evaluate_visibility_dataset
    conn = _conn()
    items = [
        {'id': 10, 'username': 'alice', 'role': 'admin'},
        {'id': 11, 'username': 'bob', 'role': 'user'},
    ]
    result = canary_evaluate_visibility_dataset(
        conn, ACTOR,
        endpoint_name='/api/bootstrap',
        dataset_name='users',
        legacy_items=items,
    )
    assert len(result) == 2


def test_canary_users_shadow_log_written():
    from modules.settings.service import canary_evaluate_visibility_dataset
    conn = _conn()
    items = [{'id': 1}, {'id': 2}]
    canary_evaluate_visibility_dataset(
        conn, ACTOR,
        endpoint_name='/api/bootstrap',
        dataset_name='users',
        legacy_items=items,
    )
    row = conn.execute("SELECT * FROM rule_engine_shadow_log").fetchone()
    assert row is not None
    assert row['dataset'] == 'users'
    assert row['endpoint'] == '/api/bootstrap'
    assert row['legacy_count'] == 2
    assert row['new_count'] == 2
    assert row['has_diff'] == 0


# ── inline role filters são multitenant, não legacy ──────────────────────────

def test_fetch_users_filters_by_company_id_for_non_master_admin():
    """fetch_users WHERE company_id = ? for non-master_admin is multitenancy, not legacy."""
    from modules.auth.service import fetch_users
    src = inspect.getsource(fetch_users)
    assert "actor['role'] != 'master_admin'" in src
    assert 'company_id' in src


def test_fetch_units_filters_by_company_id_for_non_master_admin():
    from modules.units.service import fetch_units
    src = inspect.getsource(fetch_units)
    assert "actor['role'] != 'master_admin'" in src
    assert 'company_id' in src


def test_fetch_employees_filters_by_company_id_for_non_master_admin():
    from modules.employees.service import fetch_employees
    src = inspect.getsource(fetch_employees)
    assert "actor['role'] != 'master_admin'" in src
    assert 'company_id' in src


def test_fetch_epis_filters_by_company_id_for_non_master_admin():
    from modules.epis.service import fetch_epis
    src = inspect.getsource(fetch_epis)
    assert "actor['role'] != 'master_admin'" in src
    assert 'company_id' in src


def test_multitenancy_filters_operate_at_company_scope_not_unit_scope():
    """Multitenancy filters use company_id. Unit/JV scope is handled by rule engine."""
    from modules.units.service import fetch_units
    from modules.employees.service import fetch_employees
    for fn in (fetch_units, fetch_employees):
        src = inspect.getsource(fn)
        # company_id filter is present
        assert 'company_id' in src
        # but no hardcoded unit_id filter based on role
        assert 'unit_id = ?' not in src or 'unit_id' not in src.split("actor['role'] != 'master_admin'")[1][:50]


# ── root duplicates removed ──────────────────────────────────────────────────

def test_no_duplicate_server_postgres_files():
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    py_files = [f.name for f in root.glob('*.py')]
    assert 'server_postgres.py server_postgres.py' not in py_files
    assert not any('locais copy' in name for name in py_files)


def test_root_has_only_expected_py_files():
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    py_files = sorted(f.name for f in root.glob('*.py'))
    assert 'app.py' in py_files
    assert 'server_postgres.py' in py_files
    # Only 2 Python files in root
    assert len(py_files) == 2, f"Unexpected py files in root: {py_files}"
