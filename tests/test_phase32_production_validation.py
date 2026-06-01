"""Phase 32 — Validação em Produção: shadow health, cleanup, UBX Go-Live marker."""

import inspect
import json
import sqlite3
from datetime import datetime, timedelta, timezone

UTC = timezone.utc


# ── helpers ───────────────────────────────────────────────────────────────────

def _conn():
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
            'execution_mode': 'enforced',
            'enable_new_rules_engine': True,
            'rollout_percentage': 100,
            'allow_new_engine_response': True,
        }
    }
    conn.execute("INSERT INTO app_meta VALUES (?, ?)", ('configuration_framework:1', json.dumps(framework)))
    conn.commit()
    return conn


def _insert_log(conn, company_id=1, has_diff=0, hours_ago=1):
    created_at = (datetime.now(UTC) - timedelta(hours=hours_ago)).isoformat()
    conn.execute(
        'INSERT INTO rule_engine_shadow_log '
        '(company_id, user_id, role, endpoint, dataset, mode, legacy_count, new_count, has_diff, legacy_only, new_only, created_at) '
        'VALUES (?, 1, ?, ?, ?, ?, 5, 5, ?, ?, ?, ?)',
        (company_id, 'admin', '/api/bootstrap', 'units', 'enforced', has_diff, '[]', '[]', created_at),
    )
    conn.commit()


# ── fetch_shadow_log_health ───────────────────────────────────────────────────

def test_shadow_health_clean_when_no_entries():
    from modules.settings.service import fetch_shadow_log_health
    conn = _conn()
    health = fetch_shadow_log_health(conn, company_id=1)
    assert health['total'] == 0
    assert health['diff_count'] == 0
    assert health['is_clean'] is True
    assert health['go_live_ready'] is False  # no traffic yet → not ready


def test_shadow_health_not_ready_when_has_diffs():
    from modules.settings.service import fetch_shadow_log_health
    conn = _conn()
    _insert_log(conn, has_diff=1, hours_ago=2)
    _insert_log(conn, has_diff=0, hours_ago=1)
    health = fetch_shadow_log_health(conn, company_id=1)
    assert health['diff_count'] == 1
    assert health['is_clean'] is False
    assert health['go_live_ready'] is False


def test_shadow_health_go_live_ready_when_traffic_and_no_diffs():
    from modules.settings.service import fetch_shadow_log_health
    conn = _conn()
    _insert_log(conn, has_diff=0, hours_ago=3)
    _insert_log(conn, has_diff=0, hours_ago=1)
    health = fetch_shadow_log_health(conn, company_id=1)
    assert health['total'] == 2
    assert health['diff_count'] == 0
    assert health['is_clean'] is True
    assert health['go_live_ready'] is True


def test_shadow_health_window_excludes_entries_outside_window():
    from modules.settings.service import fetch_shadow_log_health
    conn = _conn()
    _insert_log(conn, has_diff=1, hours_ago=72)   # outside 48h window
    _insert_log(conn, has_diff=0, hours_ago=1)    # inside 48h window
    health = fetch_shadow_log_health(conn, company_id=1, window_hours=48)
    assert health['total'] == 1
    assert health['diff_count'] == 0
    assert health['is_clean'] is True


def test_shadow_health_window_hours_reflected_in_response():
    from modules.settings.service import fetch_shadow_log_health
    conn = _conn()
    _insert_log(conn, has_diff=0, hours_ago=1)
    health = fetch_shadow_log_health(conn, company_id=1, window_hours=24)
    assert health['window_hours'] == 24
    assert health['no_diff_count'] == 1


def test_shadow_health_counts_no_diff_and_diff_separately():
    from modules.settings.service import fetch_shadow_log_health
    conn = _conn()
    for _ in range(3):
        _insert_log(conn, has_diff=0, hours_ago=1)
    _insert_log(conn, has_diff=1, hours_ago=2)
    health = fetch_shadow_log_health(conn, company_id=1)
    assert health['total'] == 4
    assert health['diff_count'] == 1
    assert health['no_diff_count'] == 3


# ── cleanup_shadow_log_older_than ─────────────────────────────────────────────

def test_cleanup_removes_old_entries():
    from modules.settings.service import cleanup_shadow_log_older_than
    conn = _conn()
    _insert_log(conn, hours_ago=40 * 24)   # 40 days old
    _insert_log(conn, hours_ago=35 * 24)   # 35 days old
    _insert_log(conn, hours_ago=1)          # recent
    deleted = cleanup_shadow_log_older_than(conn, company_id=1, days_old=30)
    assert deleted == 2
    remaining = conn.execute('SELECT COUNT(*) FROM rule_engine_shadow_log').fetchone()[0]
    assert remaining == 1


def test_cleanup_keeps_recent_entries():
    from modules.settings.service import cleanup_shadow_log_older_than
    conn = _conn()
    _insert_log(conn, hours_ago=1)
    _insert_log(conn, hours_ago=5)
    deleted = cleanup_shadow_log_older_than(conn, company_id=1, days_old=30)
    assert deleted == 0


def test_cleanup_returns_zero_when_table_is_empty():
    from modules.settings.service import cleanup_shadow_log_older_than
    conn = _conn()
    deleted = cleanup_shadow_log_older_than(conn, company_id=1, days_old=30)
    assert deleted == 0


def test_cleanup_only_affects_own_company():
    from modules.settings.service import cleanup_shadow_log_older_than
    conn = _conn()
    conn.execute("INSERT INTO companies VALUES (2, 'Empresa B', 1)")
    conn.commit()
    _insert_log(conn, company_id=1, hours_ago=40 * 24)
    _insert_log(conn, company_id=2, hours_ago=40 * 24)
    deleted = cleanup_shadow_log_older_than(conn, company_id=1, days_old=30)
    assert deleted == 1
    remaining = conn.execute('SELECT COUNT(*) FROM rule_engine_shadow_log').fetchone()[0]
    assert remaining == 1  # company 2 entry untouched


# ── ensure_ubx_golive_declared ────────────────────────────────────────────────

def _meta_conn():
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.execute('CREATE TABLE app_meta (key TEXT PRIMARY KEY, value TEXT)')
    conn.commit()
    return conn


def test_ubx_golive_marker_written_on_first_call():
    from core.schema import ensure_ubx_golive_declared
    conn = _meta_conn()
    ensure_ubx_golive_declared(conn)
    row = conn.execute("SELECT value FROM app_meta WHERE key = 'ubx_golive_declared_at'").fetchone()
    assert row is not None
    assert len(str(row['value'])) > 10  # ISO timestamp written


def test_ubx_golive_marker_idempotent():
    from core.schema import ensure_ubx_golive_declared
    conn = _meta_conn()
    conn.execute("INSERT INTO app_meta VALUES ('ubx_golive_declared_at', '2026-01-01T00:00:00+00:00')")
    conn.commit()
    ensure_ubx_golive_declared(conn)
    row = conn.execute("SELECT value FROM app_meta WHERE key = 'ubx_golive_declared_at'").fetchone()
    assert row['value'] == '2026-01-01T00:00:00+00:00'  # original timestamp preserved


def test_ubx_golive_declared_in_init_db_sequence():
    from core.schema import init_db
    src = inspect.getsource(init_db)
    assert 'ensure_ubx_golive_declared' in src


# ── smoke: new route handlers exist and are wired correctly ───────────────────

def test_shadow_health_handler_exists():
    import modules.settings.routes as r
    assert callable(getattr(r, 'handle_get_rules_engine_shadow_health', None))


def test_shadow_log_cleanup_handler_exists():
    import modules.settings.routes as r
    assert callable(getattr(r, 'handle_delete_shadow_log_cleanup', None))


def test_shadow_health_handler_calls_service():
    import modules.settings.routes as r
    src = inspect.getsource(r.handle_get_rules_engine_shadow_health)
    assert 'fetch_shadow_log_health' in src
    assert 'window_hours' in src


def test_cleanup_handler_calls_service():
    import modules.settings.routes as r
    src = inspect.getsource(r.handle_delete_shadow_log_cleanup)
    assert 'cleanup_shadow_log_older_than' in src
    assert 'days_old' in src


def test_shadow_health_route_registered():
    import modules.settings.routes as r
    src = inspect.getsource(r.register_routes)
    assert '/api/rules-engine/shadow-health' in src


def test_shadow_log_cleanup_route_registered():
    import modules.settings.routes as r
    src = inspect.getsource(r.register_routes)
    assert '/api/rules-engine/shadow-log' in src
