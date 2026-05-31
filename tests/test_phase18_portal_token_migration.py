"""Tests for Phase 18: legacy portal token migration."""

import sqlite3

import pytest

from core.schema import ensure_migrate_legacy_portal_tokens
from modules.portal.service import (
    EmployeePortalAccessDenied,
    get_employee_portal_context_by_token,
    resolve_external_employee_context,
)


def _conn():
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.executescript(
        '''
        CREATE TABLE companies (id INTEGER PRIMARY KEY, name TEXT);
        CREATE TABLE units (id INTEGER PRIMARY KEY, company_id INTEGER, name TEXT);
        CREATE TABLE employees (
            id INTEGER PRIMARY KEY,
            company_id INTEGER NOT NULL,
            unit_id INTEGER NOT NULL,
            employee_id_code TEXT NOT NULL DEFAULT '',
            cpf TEXT NOT NULL DEFAULT '12345678901',
            name TEXT NOT NULL DEFAULT 'Colaborador',
            email TEXT NOT NULL DEFAULT '',
            whatsapp TEXT NOT NULL DEFAULT '',
            preferred_contact_channel TEXT NOT NULL DEFAULT 'whatsapp',
            sector TEXT NOT NULL DEFAULT 'Operação',
            role_name TEXT NOT NULL DEFAULT 'Técnico',
            admission_date TEXT NOT NULL DEFAULT '',
            schedule_type TEXT NOT NULL DEFAULT '30x30',
            tipo_vinculo TEXT NOT NULL DEFAULT 'CLT',
            empresa_origem TEXT NOT NULL DEFAULT ''
        );
        CREATE TABLE users (
            id INTEGER PRIMARY KEY,
            username TEXT,
            password TEXT,
            full_name TEXT,
            role TEXT,
            company_id INTEGER,
            active INTEGER DEFAULT 1,
            linked_employee_id INTEGER,
            employee_access_token TEXT DEFAULT '',
            employee_access_expires_at TEXT DEFAULT ''
        );
        CREATE TABLE employee_portal_links (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL,
            employee_id INTEGER NOT NULL UNIQUE,
            token TEXT NOT NULL UNIQUE,
            qr_code_value TEXT NOT NULL UNIQUE,
            active INTEGER NOT NULL DEFAULT 1,
            expires_at TEXT NOT NULL DEFAULT '',
            created_by_user_id INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            cpf_attempts INTEGER NOT NULL DEFAULT 0,
            last_cpf_attempt_at TEXT NOT NULL DEFAULT '',
            blocked_at TEXT NOT NULL DEFAULT ''
        );
        CREATE TABLE employee_portal_audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL,
            employee_id INTEGER NOT NULL,
            portal_link_id INTEGER,
            token_hash TEXT NOT NULL DEFAULT '',
            action TEXT NOT NULL DEFAULT '',
            ip_address TEXT NOT NULL DEFAULT '',
            user_agent TEXT NOT NULL DEFAULT '',
            payload TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL
        );
        INSERT INTO companies (id, name) VALUES (1, 'Empresa A');
        INSERT INTO units (id, company_id, name) VALUES (1, 1, 'Unidade A');
        INSERT INTO employees (id, company_id, unit_id, employee_id_code, cpf, name) VALUES (10, 1, 1, 'E001', '12345678901', 'Funcionário A');
        INSERT INTO employees (id, company_id, unit_id, employee_id_code, cpf, name) VALUES (20, 1, 1, 'E002', '98765432100', 'Funcionário B');
        '''
    )
    return conn


# ── Migration function ─────────────────────────────────────────────────────────

def test_migrate_creates_portal_link_from_legacy_token():
    conn = _conn()
    conn.execute(
        "INSERT INTO users (id, username, full_name, role, company_id, active, linked_employee_id, employee_access_token) "
        "VALUES (1, 'emp', 'Funcionário A', 'employee', 1, 1, 10, 'legacy-token-abc')"
    )

    ensure_migrate_legacy_portal_tokens(conn)

    link = conn.execute("SELECT * FROM employee_portal_links WHERE token = 'legacy-token-abc'").fetchone()
    assert link is not None
    assert int(link['employee_id']) == 10
    assert int(link['company_id']) == 1
    assert int(link['active']) == 1


def test_migrate_skips_non_employee_roles():
    conn = _conn()
    conn.execute(
        "INSERT INTO users (id, username, full_name, role, company_id, active, linked_employee_id, employee_access_token) "
        "VALUES (2, 'admin', 'Admin', 'admin', 1, 1, 10, 'should-not-migrate')"
    )

    ensure_migrate_legacy_portal_tokens(conn)

    link = conn.execute("SELECT * FROM employee_portal_links WHERE token = 'should-not-migrate'").fetchone()
    assert link is None


def test_migrate_skips_users_with_empty_token():
    conn = _conn()
    conn.execute(
        "INSERT INTO users (id, username, full_name, role, company_id, active, linked_employee_id, employee_access_token) "
        "VALUES (3, 'emp2', 'Funcionário B', 'employee', 1, 1, 20, '')"
    )

    ensure_migrate_legacy_portal_tokens(conn)

    count = conn.execute("SELECT COUNT(*) AS c FROM employee_portal_links").fetchone()['c']
    assert int(count) == 0


def test_migrate_is_idempotent():
    conn = _conn()
    conn.execute(
        "INSERT INTO users (id, username, full_name, role, company_id, active, linked_employee_id, employee_access_token) "
        "VALUES (1, 'emp', 'Funcionário A', 'employee', 1, 1, 10, 'legacy-token-abc')"
    )

    ensure_migrate_legacy_portal_tokens(conn)
    ensure_migrate_legacy_portal_tokens(conn)

    count = conn.execute("SELECT COUNT(*) AS c FROM employee_portal_links WHERE token = 'legacy-token-abc'").fetchone()['c']
    assert int(count) == 1


def test_migrate_multiple_employees():
    conn = _conn()
    conn.execute(
        "INSERT INTO users (id, username, full_name, role, company_id, active, linked_employee_id, employee_access_token) "
        "VALUES (1, 'emp1', 'Funcionário A', 'employee', 1, 1, 10, 'token-for-emp10')"
    )
    conn.execute(
        "INSERT INTO users (id, username, full_name, role, company_id, active, linked_employee_id, employee_access_token) "
        "VALUES (2, 'emp2', 'Funcionário B', 'employee', 1, 1, 20, 'token-for-emp20')"
    )

    ensure_migrate_legacy_portal_tokens(conn)

    count = conn.execute("SELECT COUNT(*) AS c FROM employee_portal_links").fetchone()['c']
    assert int(count) == 2


def test_migrate_skips_if_portal_link_already_exists_for_employee():
    conn = _conn()
    conn.execute(
        "INSERT INTO users (id, username, full_name, role, company_id, active, linked_employee_id, employee_access_token) "
        "VALUES (1, 'emp', 'Funcionário A', 'employee', 1, 1, 10, 'legacy-token-abc')"
    )
    conn.execute(
        "INSERT INTO employee_portal_links (company_id, employee_id, token, qr_code_value, active, created_by_user_id, created_at, updated_at) "
        "VALUES (1, 10, 'modern-token-xyz', 'qr-xyz', 1, 1, '2026-01-01T00:00:00', '2026-01-01T00:00:00')"
    )

    ensure_migrate_legacy_portal_tokens(conn)

    count = conn.execute("SELECT COUNT(*) AS c FROM employee_portal_links WHERE employee_id = 10").fetchone()['c']
    assert int(count) == 1


# ── resolve_external_employee_context: only uses employee_portal_links now ────

def test_resolve_context_succeeds_via_portal_link():
    conn = _conn()
    conn.execute(
        "INSERT INTO employee_portal_links (company_id, employee_id, token, qr_code_value, active, expires_at, created_by_user_id, created_at, updated_at) "
        "VALUES (1, 10, 'new-token-xyz', 'qr-xyz', 1, '9999-12-31T00:00:00+00:00', 1, '2026-01-01T00:00:00', '2026-01-01T00:00:00')"
    )

    ctx = resolve_external_employee_context(conn, 'new-token-xyz', cpf_last3='901')

    assert int(ctx['employee_id']) == 10
    assert int(ctx['company_id']) == 1


def test_resolve_context_raises_for_unknown_token():
    conn = _conn()
    with pytest.raises(EmployeePortalAccessDenied) as exc_info:
        resolve_external_employee_context(conn, 'completely-unknown-token', cpf_last3='901')
    assert exc_info.value.code == 'TOKEN_NOT_FOUND'


def test_resolve_context_raises_for_empty_token():
    conn = _conn()
    with pytest.raises(EmployeePortalAccessDenied) as exc_info:
        resolve_external_employee_context(conn, '', cpf_last3='901')
    assert exc_info.value.code == 'TOKEN_MISSING'


def test_migrated_legacy_token_works_via_resolve_context():
    """After migration, a legacy token is reachable through employee_portal_links."""
    conn = _conn()
    conn.execute(
        "INSERT INTO users (id, username, full_name, role, company_id, active, linked_employee_id, employee_access_token) "
        "VALUES (1, 'emp', 'Funcionário A', 'employee', 1, 1, 10, 'legacy-token-migrated')"
    )
    ensure_migrate_legacy_portal_tokens(conn)

    ctx = resolve_external_employee_context(conn, 'legacy-token-migrated', cpf_last3='901')
    assert int(ctx['employee_id']) == 10


# ── No-generation policy ───────────────────────────────────────────────────────

def test_users_service_no_longer_has_build_employee_access_token():
    from modules.users import service as us
    assert not hasattr(us, 'build_employee_access_token'), \
        "build_employee_access_token must be removed from modules.users.service"


def test_portal_service_no_longer_has_get_employee_user_by_token():
    from modules.portal import service as ps
    assert not hasattr(ps, 'get_employee_user_by_token'), \
        "get_employee_user_by_token must be removed from modules.portal.service"


def test_sql_update_user_no_longer_includes_access_token_fields():
    from modules.users.service import SQL_UPDATE_USER
    assert 'employee_access_token' not in SQL_UPDATE_USER
    assert 'employee_access_expires_at' not in SQL_UPDATE_USER
