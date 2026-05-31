"""Tests for Phase 20: Rule Engine Go-Live — shadow mode auto-activation."""

import json
import sqlite3

from core.schema import ensure_rule_engine_shadow_activated


def _conn():
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.executescript(
        '''
        CREATE TABLE companies (id INTEGER PRIMARY KEY, name TEXT, active INTEGER DEFAULT 1);
        CREATE TABLE app_meta (key TEXT PRIMARY KEY, value TEXT);
        INSERT INTO companies (id, name) VALUES (1, 'Empresa A');
        INSERT INTO companies (id, name) VALUES (2, 'Empresa B');
        INSERT INTO companies (id, name) VALUES (3, 'Empresa C');
        '''
    )
    return conn


def _get_framework(conn, company_id):
    row = conn.execute(
        "SELECT value FROM app_meta WHERE key = ?",
        (f'configuration_framework:{company_id}',),
    ).fetchone()
    return json.loads(row['value']) if row else {}


def _set_framework(conn, company_id, framework):
    conn.execute(
        "INSERT INTO app_meta (key, value) VALUES (?, ?) "
        "ON CONFLICT (key) DO UPDATE SET value = excluded.value",
        (f'configuration_framework:{company_id}', json.dumps(framework)),
    )


# ── Basic activation ──────────────────────────────────────────────────────────

def test_companies_with_no_framework_get_shadow_mode():
    conn = _conn()
    ensure_rule_engine_shadow_activated(conn)
    for cid in (1, 2, 3):
        fw = _get_framework(conn, cid)
        assert fw['feature_flags']['execution_mode'] == 'shadow'
        assert fw['feature_flags']['enable_new_rules_engine'] is True


def test_companies_with_off_mode_promoted_to_shadow():
    conn = _conn()
    _set_framework(conn, 1, {'feature_flags': {'execution_mode': 'off', 'enable_new_rules_engine': False}})
    ensure_rule_engine_shadow_activated(conn)
    fw = _get_framework(conn, 1)
    assert fw['feature_flags']['execution_mode'] == 'shadow'
    assert fw['feature_flags']['enable_new_rules_engine'] is True


# ── Idempotência ──────────────────────────────────────────────────────────────

def test_function_is_idempotent():
    conn = _conn()
    ensure_rule_engine_shadow_activated(conn)
    ensure_rule_engine_shadow_activated(conn)
    for cid in (1, 2, 3):
        fw = _get_framework(conn, cid)
        assert fw['feature_flags']['execution_mode'] == 'shadow'


# ── Preservação de modos avançados ────────────────────────────────────────────

def test_companies_in_enforced_mode_not_downgraded():
    conn = _conn()
    _set_framework(conn, 1, {'feature_flags': {'execution_mode': 'enforced', 'rollout_percentage': 100}})
    ensure_rule_engine_shadow_activated(conn)
    fw = _get_framework(conn, 1)
    assert fw['feature_flags']['execution_mode'] == 'enforced'


def test_companies_in_canary_mode_not_downgraded():
    conn = _conn()
    _set_framework(conn, 2, {'feature_flags': {'execution_mode': 'canary', 'rollout_percentage': 50}})
    ensure_rule_engine_shadow_activated(conn)
    fw = _get_framework(conn, 2)
    assert fw['feature_flags']['execution_mode'] == 'canary'


def test_companies_in_shadow_mode_unchanged():
    conn = _conn()
    _set_framework(conn, 3, {'feature_flags': {'execution_mode': 'shadow', 'rollout_percentage': 75}})
    ensure_rule_engine_shadow_activated(conn)
    fw = _get_framework(conn, 3)
    assert fw['feature_flags']['execution_mode'] == 'shadow'
    assert fw['feature_flags']['rollout_percentage'] == 75


def test_mixed_companies_only_off_gets_promoted():
    conn = _conn()
    _set_framework(conn, 1, {'feature_flags': {'execution_mode': 'off'}})
    _set_framework(conn, 2, {'feature_flags': {'execution_mode': 'shadow'}})
    _set_framework(conn, 3, {'feature_flags': {'execution_mode': 'enforced'}})
    ensure_rule_engine_shadow_activated(conn)
    assert _get_framework(conn, 1)['feature_flags']['execution_mode'] == 'shadow'
    assert _get_framework(conn, 2)['feature_flags']['execution_mode'] == 'shadow'
    assert _get_framework(conn, 3)['feature_flags']['execution_mode'] == 'enforced'


# ── Rollout_percentage default ────────────────────────────────────────────────

def test_rollout_percentage_defaults_to_100():
    conn = _conn()
    ensure_rule_engine_shadow_activated(conn)
    fw = _get_framework(conn, 1)
    assert fw['feature_flags']['rollout_percentage'] == 100


def test_existing_rollout_percentage_preserved_for_shadow():
    conn = _conn()
    _set_framework(conn, 1, {'feature_flags': {'execution_mode': 'shadow', 'rollout_percentage': 42}})
    ensure_rule_engine_shadow_activated(conn)
    fw = _get_framework(conn, 1)
    assert fw['feature_flags']['rollout_percentage'] == 42


# ── Ensure fn registrada no servidor ─────────────────────────────────────────

def test_ensure_fn_importable_from_core_schema():
    from core.schema import ensure_rule_engine_shadow_activated
    assert callable(ensure_rule_engine_shadow_activated)


def test_ensure_fn_registered_in_server_postgres():
    import server_postgres as sp
    import inspect
    src = inspect.getsource(sp)
    assert 'ensure_rule_engine_shadow_activated' in src
