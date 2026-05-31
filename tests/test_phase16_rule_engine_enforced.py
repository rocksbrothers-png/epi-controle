"""Tests for Phase 16: rule engine enforced mode and shadow diff persistence."""

import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


# ── Schema migration ──────────────────────────────────────────────────────────

def _make_connection():
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    return conn


def test_ensure_rule_engine_shadow_log_creates_table():
    from core.schema import ensure_rule_engine_shadow_log
    conn = _make_connection()
    ensure_rule_engine_shadow_log(conn)
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    assert 'rule_engine_shadow_log' in tables


def test_shadow_log_table_columns():
    from core.schema import ensure_rule_engine_shadow_log
    conn = _make_connection()
    ensure_rule_engine_shadow_log(conn)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(rule_engine_shadow_log)").fetchall()}
    expected = {'id', 'company_id', 'user_id', 'role', 'endpoint', 'dataset',
                'mode', 'legacy_count', 'new_count', 'has_diff', 'legacy_only', 'new_only', 'created_at'}
    assert expected.issubset(cols)


def test_ensure_rule_engine_shadow_log_idempotent():
    from core.schema import ensure_rule_engine_shadow_log
    conn = _make_connection()
    ensure_rule_engine_shadow_log(conn)
    ensure_rule_engine_shadow_log(conn)  # second call must not raise
    conn.execute("INSERT INTO rule_engine_shadow_log (company_id, user_id, role, endpoint, dataset, mode, legacy_count, new_count, has_diff, legacy_only, new_only, created_at) VALUES (1, 1, 'admin', '/api/bootstrap', 'units', 'shadow', 3, 3, 0, '[]', '[]', '2026-01-01T00:00:00')")
    count = conn.execute("SELECT COUNT(*) FROM rule_engine_shadow_log").fetchone()[0]
    assert count == 1


# ── canary_evaluate_visibility_dataset enforced mode ─────────────────────────

def _make_full_connection():
    """Create an in-memory SQLite connection with all required tables for canary tests."""
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.execute("CREATE TABLE companies (id INTEGER PRIMARY KEY, name TEXT)")
    conn.execute("CREATE TABLE app_meta (key TEXT PRIMARY KEY, value TEXT)")
    conn.execute("""
        CREATE TABLE rule_engine_shadow_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER, user_id INTEGER, role TEXT,
            endpoint TEXT, dataset TEXT, mode TEXT,
            legacy_count INTEGER, new_count INTEGER, has_diff INTEGER,
            legacy_only TEXT, new_only TEXT, created_at TEXT
        )
    """)
    conn.execute("INSERT INTO companies VALUES (1, 'TestCo')")
    conn.commit()
    return conn


def _enforced_framework_json():
    from epi_backend.rule_engine import default_framework_payload, normalize_framework_payload
    fw = default_framework_payload()
    fw['feature_flags'].update({
        'enable_new_rules_engine': True,
        'execution_mode': 'enforced',
        'rollout_percentage': 100,
    })
    fw['visibility_rules'] = []
    return json.dumps(normalize_framework_payload(fw))


def test_canary_evaluate_returns_legacy_when_mode_off():
    import server_postgres as sp
    conn = _make_full_connection()
    actor = {'id': 1, 'company_id': 1, 'role': 'master_admin'}
    legacy = [{'id': 10}, {'id': 20}]
    result = sp.canary_evaluate_visibility_dataset(conn, actor, endpoint_name='/api/bootstrap', dataset_name='units', legacy_items=legacy)
    assert result is legacy


def test_canary_evaluate_enforced_returns_candidate():
    import server_postgres as sp
    conn = _make_full_connection()
    conn.execute("INSERT INTO app_meta (key, value) VALUES (?, ?)", ('configuration_framework:1', _enforced_framework_json()))
    conn.commit()

    actor = {'id': 1, 'company_id': 1, 'role': 'master_admin'}
    legacy = [{'id': 10, 'unit_id': 0}, {'id': 20, 'unit_id': 0}]
    result = sp.canary_evaluate_visibility_dataset(conn, actor, endpoint_name='/api/bootstrap', dataset_name='units', legacy_items=legacy)
    # master_admin gets allow_unit=True for all items → candidate == legacy
    assert [i['id'] for i in result] == [10, 20]


def test_canary_evaluate_enforced_persists_to_shadow_log():
    import server_postgres as sp
    conn = _make_full_connection()
    conn.execute("INSERT INTO app_meta (key, value) VALUES (?, ?)", ('configuration_framework:1', _enforced_framework_json()))
    conn.commit()

    actor = {'id': 1, 'company_id': 1, 'role': 'master_admin'}
    legacy = [{'id': 10, 'unit_id': 0}]
    sp.canary_evaluate_visibility_dataset(conn, actor, endpoint_name='/api/bootstrap', dataset_name='units', legacy_items=legacy)

    row = conn.execute("SELECT * FROM rule_engine_shadow_log").fetchone()
    assert row is not None
    assert row['company_id'] == 1
    assert row['dataset'] == 'units'
    assert row['mode'] == 'enforced'


def test_canary_evaluate_shadow_mode_still_returns_legacy():
    import server_postgres as sp
    from epi_backend.rule_engine import default_framework_payload, normalize_framework_payload
    conn = _make_full_connection()
    fw = default_framework_payload()
    fw['feature_flags'].update({
        'enable_new_rules_engine': True,
        'execution_mode': 'shadow',
        'rollout_percentage': 100,
    })
    fw_json = json.dumps(normalize_framework_payload(fw))
    conn.execute("INSERT INTO app_meta (key, value) VALUES (?, ?)", ('configuration_framework:1', fw_json))
    conn.commit()

    actor = {'id': 1, 'company_id': 1, 'role': 'master_admin'}
    legacy = [{'id': 10, 'unit_id': 0}, {'id': 20, 'unit_id': 0}]
    result = sp.canary_evaluate_visibility_dataset(conn, actor, endpoint_name='/api/bootstrap', dataset_name='units', legacy_items=legacy)
    # shadow mode always returns legacy
    assert result is legacy


# ── Route registration ────────────────────────────────────────────────────────

def test_shadow_diff_route_registered():
    from modules.settings.routes import register_routes
    from core.router import Router
    r = Router()
    register_routes(r)
    paths = [(m, p) for m, p, _, _ in r._routes]
    assert ('GET', '/api/rules-engine/shadow-diff') in paths
