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


# ── Shadow diff with visibility_rules configured ──────────────────────────────

def _shadow_framework_with_rules(rules):
    from epi_backend.rule_engine import default_framework_payload, normalize_framework_payload
    fw = default_framework_payload()
    fw['feature_flags'].update({
        'enable_new_rules_engine': True,
        'execution_mode': 'shadow',
        'rollout_percentage': 100,
    })
    fw['visibility_rules'] = rules
    return json.dumps(normalize_framework_payload(fw))


def test_shadow_diff_detected_when_rules_restrict_visibility():
    """When visibility_rules block some items, shadow log must record has_diff=1."""
    import server_postgres as sp
    conn = _make_full_connection()
    # Rule: role=user, unit_id=99 → can_view_unit=False
    rules = [{
        'id': 'r1', 'role': 'user', 'unit_id': 99,
        'unit_context': 'outside_jv',
        'can_view_unit': False, 'can_view_epis': False, 'can_view_employees': False,
    }]
    conn.execute("INSERT INTO app_meta (key, value) VALUES (?, ?)", ('configuration_framework:1', _shadow_framework_with_rules(rules)))
    conn.commit()

    actor = {'id': 1, 'company_id': 1, 'role': 'user'}
    # Two units: unit 99 should be filtered by the rule, unit 100 should pass
    legacy = [
        {'id': 99, 'unit_id': 99, 'active_joinventure': ''},
        {'id': 100, 'unit_id': 100, 'active_joinventure': ''},
    ]
    result = sp.canary_evaluate_visibility_dataset(conn, actor, endpoint_name='/api/bootstrap', dataset_name='units', legacy_items=legacy)
    # Shadow mode always returns legacy
    assert result is legacy

    row = conn.execute("SELECT * FROM rule_engine_shadow_log").fetchone()
    assert row is not None
    assert int(row['has_diff']) == 1
    assert row['legacy_count'] == 2
    assert row['new_count'] == 1
    legacy_only = json.loads(row['legacy_only'])
    assert '99' in legacy_only


def test_shadow_no_diff_when_rules_match_legacy():
    import server_postgres as sp
    conn = _make_full_connection()
    # No visibility rules → engine allows everything → same as legacy
    conn.execute("INSERT INTO app_meta (key, value) VALUES (?, ?)", ('configuration_framework:1', _shadow_framework_with_rules([])))
    conn.commit()

    actor = {'id': 1, 'company_id': 1, 'role': 'user'}
    legacy = [{'id': 50, 'unit_id': 50, 'active_joinventure': ''}]
    sp.canary_evaluate_visibility_dataset(conn, actor, endpoint_name='/api/bootstrap', dataset_name='units', legacy_items=legacy)

    row = conn.execute("SELECT * FROM rule_engine_shadow_log").fetchone()
    assert row is not None
    assert int(row['has_diff']) == 0


# ── promote_rule_engine service ───────────────────────────────────────────────

def test_promote_rule_engine_updates_mode():
    from modules.settings.service import promote_rule_engine
    conn = _make_full_connection()
    framework = promote_rule_engine(conn, 1, mode='shadow', rollout_percentage=10, enable=True)
    conn.commit()
    assert framework['feature_flags']['execution_mode'] == 'shadow'
    assert framework['feature_flags']['rollout_percentage'] == 10
    assert framework['feature_flags']['enable_new_rules_engine'] is True

    framework2 = promote_rule_engine(conn, 1, mode='canary', rollout_percentage=50, enable=True)
    conn.commit()
    assert framework2['feature_flags']['execution_mode'] == 'canary'
    assert framework2['feature_flags']['rollout_percentage'] == 50


def test_promote_rule_engine_rejects_invalid_mode():
    import pytest
    from modules.settings.service import promote_rule_engine
    conn = _make_full_connection()
    with pytest.raises(ValueError, match='execution_mode inválido'):
        promote_rule_engine(conn, 1, mode='invalid', rollout_percentage=0)


def test_promote_rule_engine_rejects_invalid_rollout():
    import pytest
    from modules.settings.service import promote_rule_engine
    conn = _make_full_connection()
    with pytest.raises(ValueError, match='rollout_percentage'):
        promote_rule_engine(conn, 1, mode='shadow', rollout_percentage=150)


def test_get_rule_engine_status_empty_log():
    from modules.settings.service import get_rule_engine_status
    conn = _make_full_connection()
    status = get_rule_engine_status(conn, 1)
    assert status['enabled'] is False
    assert status['mode'] == 'off'
    assert status['rollout_percentage'] == 0
    assert status['shadow_log']['total'] == 0


def test_get_rule_engine_status_with_log_entries():
    from modules.settings.service import promote_rule_engine, get_rule_engine_status
    conn = _make_full_connection()
    promote_rule_engine(conn, 1, mode='shadow', rollout_percentage=100, enable=True)
    conn.commit()
    now = '2026-05-31T00:00:00'
    conn.execute(
        'INSERT INTO rule_engine_shadow_log (company_id, user_id, role, endpoint, dataset, mode, legacy_count, new_count, has_diff, legacy_only, new_only, created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',
        (1, 1, 'admin', '/api/bootstrap', 'units', 'shadow', 5, 4, 1, '["99"]', '[]', now),
    )
    conn.execute(
        'INSERT INTO rule_engine_shadow_log (company_id, user_id, role, endpoint, dataset, mode, legacy_count, new_count, has_diff, legacy_only, new_only, created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',
        (1, 1, 'admin', '/api/bootstrap', 'epis', 'shadow', 3, 3, 0, '[]', '[]', now),
    )
    conn.commit()
    status = get_rule_engine_status(conn, 1)
    assert status['mode'] == 'shadow'
    assert status['shadow_log']['total'] == 2
    assert status['shadow_log']['diff_count'] == 1
    assert status['shadow_log']['no_diff_count'] == 1


# ── Route registration ────────────────────────────────────────────────────────

def test_new_routes_registered():
    from modules.settings.routes import register_routes
    from core.router import Router
    r = Router()
    register_routes(r)
    paths = [(m, p) for m, p, _, _ in r._routes]
    assert ('GET', '/api/rules-engine/shadow-diff') in paths
    assert ('GET', '/api/rules-engine/status') in paths
    assert ('POST', '/api/rules-engine/promote') in paths
    assert ('DELETE', '/api/rules-engine/shadow-diff') in paths
