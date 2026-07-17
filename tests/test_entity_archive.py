"""Arquivamento (Soft Delete) de Colaboradores e EPIs — mesma política das Unidades.

Cobre: arquivar (desativado, histórico preservado), desarquivar (volta a ativo),
exclusão definitiva habilitada apenas após a retenção (mínimo 5 anos; até lá o
registro permanece arquivado), tombstone e trilha de auditoria permanente.
"""
import sqlite3
from datetime import datetime, timedelta, timezone

import pytest

from core import archival
from modules.employees.service import (
    ensure_employee_operational,
    fetch_archived_employees,
    fetch_employees,
    get_employee_lifecycle,
    purge_employee_history,
    summarize_employee_history,
)
from modules.epis.service import (
    ensure_epi_operational,
    fetch_archived_epis,
    get_epi_lifecycle,
    purge_epi_history,
    summarize_epi_history,
)

UTC = timezone.utc

ACTOR_GENERAL = {'id': 1, 'full_name': 'Admin Geral', 'role': 'general_admin', 'company_id': 1}
ACTOR_REGISTRY = {'id': 2, 'full_name': 'Admin Registro', 'role': 'registry_admin', 'company_id': 1}

LIFECYCLE_COLS = """
    status TEXT NOT NULL DEFAULT 'active', archived_at TEXT, archived_by INTEGER,
    archive_reason TEXT NOT NULL DEFAULT '', retention_until TEXT,
    legal_hold INTEGER NOT NULL DEFAULT 0, legal_hold_reason TEXT NOT NULL DEFAULT '',
    deleted_at TEXT, deleted_by INTEGER, delete_reason TEXT NOT NULL DEFAULT ''
"""


@pytest.fixture
def conn():
    connection = sqlite3.connect(':memory:')
    connection.row_factory = sqlite3.Row
    connection.executescript(
        f"""
        CREATE TABLE companies (id INTEGER PRIMARY KEY, name TEXT, cnpj TEXT DEFAULT '',
            logo_type TEXT DEFAULT '', unit_retention_years INTEGER NOT NULL DEFAULT 5);
        CREATE TABLE users (id INTEGER PRIMARY KEY, full_name TEXT, role TEXT,
            company_id INTEGER, linked_employee_id INTEGER);
        CREATE TABLE units (id INTEGER PRIMARY KEY, company_id INTEGER, name TEXT,
            unit_type TEXT DEFAULT 'base', city TEXT DEFAULT '');
        CREATE TABLE employees (
            id INTEGER PRIMARY KEY, company_id INTEGER, unit_id INTEGER,
            employee_id_code TEXT DEFAULT '', cpf TEXT DEFAULT '', name TEXT,
            email TEXT DEFAULT '', whatsapp TEXT DEFAULT '',
            preferred_contact_channel TEXT DEFAULT 'whatsapp', sector TEXT DEFAULT '',
            role_name TEXT DEFAULT '', admission_date TEXT DEFAULT '',
            schedule_type TEXT DEFAULT '', tipo_vinculo TEXT DEFAULT 'CLT',
            empresa_origem TEXT DEFAULT '', {LIFECYCLE_COLS});
        CREATE TABLE epis (
            id INTEGER PRIMARY KEY, company_id INTEGER, unit_id INTEGER, name TEXT,
            purchase_code TEXT DEFAULT '', ca TEXT DEFAULT '', sector TEXT DEFAULT '', {LIFECYCLE_COLS});
        CREATE TABLE company_audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT, company_id INTEGER NOT NULL,
            actor_user_id INTEGER NOT NULL, actor_name TEXT NOT NULL, action_type TEXT NOT NULL,
            summary TEXT NOT NULL, details_json TEXT NOT NULL DEFAULT '[]', created_at TEXT NOT NULL);
        CREATE TABLE deliveries (id INTEGER PRIMARY KEY, employee_id INTEGER, epi_id INTEGER, unit_id INTEGER);
        CREATE TABLE epi_devolutions (id INTEGER PRIMARY KEY, employee_id INTEGER, epi_id INTEGER, unit_id INTEGER);
        CREATE TABLE epi_requests (id INTEGER PRIMARY KEY, employee_id INTEGER, epi_id INTEGER, unit_id INTEGER);
        CREATE TABLE epi_request_history (id INTEGER PRIMARY KEY, request_id INTEGER);
        CREATE TABLE epi_feedbacks (id INTEGER PRIMARY KEY, employee_id INTEGER, epi_id INTEGER, unit_id INTEGER);
        CREATE TABLE epi_feedback_history (id INTEGER PRIMARY KEY, feedback_id INTEGER);
        CREATE TABLE epi_ficha_periods (id INTEGER PRIMARY KEY, employee_id INTEGER, unit_id INTEGER);
        CREATE TABLE epi_ficha_items (id INTEGER PRIMARY KEY, employee_id INTEGER, epi_id INTEGER, unit_id INTEGER);
        CREATE TABLE ficha_epi_snapshots (id INTEGER PRIMARY KEY, employee_id INTEGER, unit_id INTEGER);
        CREATE TABLE ficha_epi_audit_log (id INTEGER PRIMARY KEY, employee_id INTEGER, unit_id INTEGER);
        CREATE TABLE employee_unit_movements (id INTEGER PRIMARY KEY, employee_id INTEGER,
            source_unit_id INTEGER, target_unit_id INTEGER, movement_type TEXT DEFAULT '',
            start_date TEXT DEFAULT '', end_date TEXT DEFAULT '');
        CREATE TABLE employee_portal_links (id INTEGER PRIMARY KEY, employee_id INTEGER);
        CREATE TABLE employee_portal_audit_logs (id INTEGER PRIMARY KEY, employee_id INTEGER);
        CREATE TABLE purchase_role_unit_links (id INTEGER PRIMARY KEY, employee_id INTEGER, unit_id INTEGER);
        CREATE TABLE epi_stock_items (id INTEGER PRIMARY KEY, epi_id INTEGER, unit_id INTEGER);
        CREATE TABLE epi_stock_item_reprints (id INTEGER PRIMARY KEY, stock_item_id INTEGER);
        CREATE TABLE stock_movements (id INTEGER PRIMARY KEY, epi_id INTEGER, unit_id INTEGER);
        CREATE TABLE unit_epi_stock (id INTEGER PRIMARY KEY, epi_id INTEGER, unit_id INTEGER, company_id INTEGER, quantity INTEGER DEFAULT 0);
        CREATE TABLE purchase_request_items (id INTEGER PRIMARY KEY, epi_id INTEGER, unit_id INTEGER);
        CREATE TABLE purchase_order_items (id INTEGER PRIMARY KEY, epi_id INTEGER);

        INSERT INTO companies (id, name) VALUES (1, 'ACME');
        INSERT INTO units (id, company_id, name) VALUES (10, 1, 'Base Santos');
        INSERT INTO employees (id, company_id, unit_id, employee_id_code, name)
            VALUES (100, 1, 10, 'E-100', 'Maria Silva');
        INSERT INTO epis (id, company_id, unit_id, name, ca) VALUES (200, 1, 10, 'Capacete X', '1234');
        INSERT INTO deliveries VALUES (1, 100, 200, 10);
        INSERT INTO epi_requests VALUES (2, 100, 200, 10);
        INSERT INTO epi_request_history VALUES (1, 2);
        INSERT INTO stock_movements VALUES (3, 200, 10);
        INSERT INTO employee_portal_audit_logs VALUES (4, 100);
        """
    )
    yield connection
    connection.close()


def _expire_retention(conn, table, record_id):
    past = (datetime.now(UTC) - timedelta(days=1)).isoformat(timespec='seconds')
    conn.execute(f'UPDATE {table} SET retention_until = ? WHERE id = ?', (past, record_id))


def _archive_employee(conn, actor=ACTOR_GENERAL):
    employee = get_employee_lifecycle(conn, 100)
    return archival.archive_record(
        conn, 'employees', employee, actor,
        entity_label='Colaborador', audit_prefix='employee',
        record_label=employee['name'], reason='Desligamento', ip='10.0.0.1',
    )


def _archive_epi(conn, actor=ACTOR_GENERAL):
    epi = get_epi_lifecycle(conn, 200)
    return archival.archive_record(
        conn, 'epis', epi, actor,
        entity_label='EPI', audit_prefix='epi',
        record_label=epi['name'], reason='Descontinuado', ip='10.0.0.1',
    )


# ── Colaboradores ─────────────────────────────────────────────────────────────

def test_employee_archive_preserves_history_and_blocks_operations(conn):
    result = _archive_employee(conn)
    assert result['status'] == 'archived'
    assert result['retention_years'] == archival.MIN_RETENTION_YEARS

    # Histórico intacto.
    for table in ('deliveries', 'epi_requests', 'employee_portal_audit_logs'):
        assert conn.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0] >= 1

    # Desativado: some da listagem principal e bloqueia novas operações.
    assert all(e['id'] != 100 for e in fetch_employees(conn, ACTOR_GENERAL))
    with pytest.raises(ValueError, match='arquivado'):
        ensure_employee_operational(conn, 100, 'entregas de EPI')

    archived = fetch_archived_employees(conn, ACTOR_GENERAL)
    assert [e['id'] for e in archived] == [100]
    assert archived[0]['retention_days_remaining'] > 0

    log = conn.execute("SELECT * FROM company_audit_logs WHERE action_type = 'employee_archived'").fetchone()
    assert log is not None and 'Desligamento' in log['details_json']


def test_employee_restore_reactivates(conn):
    _archive_employee(conn)
    employee = get_employee_lifecycle(conn, 100)
    archival.restore_record(
        conn, 'employees', employee, ACTOR_GENERAL,
        entity_label='Colaborador', audit_prefix='employee', record_label=employee['name'],
    )
    assert get_employee_lifecycle(conn, 100)['status'] == 'active'
    ensure_employee_operational(conn, 100, 'entregas de EPI')
    assert any(e['id'] == 100 for e in fetch_employees(conn, ACTOR_GENERAL))


def test_employee_purge_only_after_retention(conn):
    _archive_employee(conn)
    employee = get_employee_lifecycle(conn, 100)
    # Durante a retenção: exclusão bloqueada; continua arquivado.
    with pytest.raises(ValueError, match='retenção'):
        archival.request_purge(
            conn, 'employees', employee, ACTOR_GENERAL,
            entity_label='Colaborador', audit_prefix='employee',
            record_label=employee['name'],
            summary=summarize_employee_history(conn, 100),
        )
    assert get_employee_lifecycle(conn, 100)['status'] == 'archived'

    _expire_retention(conn, 'employees', 100)
    employee = get_employee_lifecycle(conn, 100)
    summary = archival.request_purge(
        conn, 'employees', employee, ACTOR_GENERAL,
        entity_label='Colaborador', audit_prefix='employee',
        record_label=employee['name'],
        summary=summarize_employee_history(conn, 100),
    )
    assert summary['deliveries'] == 1
    employee = get_employee_lifecycle(conn, 100)
    archival.confirm_purge(
        conn, 'employees', employee, ACTOR_GENERAL,
        entity_label='Colaborador', audit_prefix='employee',
        record_label=employee['name'],
        justification='Prazo legal expirado, sem pendências.',
        confirm_name='Maria Silva',
        summary=summary, purge_history=purge_employee_history,
    )
    # Tombstone permanece; dados operacionais expurgados.
    tomb = get_employee_lifecycle(conn, 100)
    assert tomb is not None and tomb['status'] == 'deleted'
    for table in ('deliveries', 'epi_requests', 'epi_request_history', 'employee_portal_audit_logs'):
        assert conn.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0] == 0
    actions = [r['action_type'] for r in conn.execute('SELECT action_type FROM company_audit_logs ORDER BY id')]
    assert actions == ['employee_archived', 'employee_purge_requested', 'employee_purged']


def test_employee_purge_requires_admin_role(conn):
    _archive_employee(conn)
    _expire_retention(conn, 'employees', 100)
    employee = get_employee_lifecycle(conn, 100)
    with pytest.raises(PermissionError):
        archival.request_purge(
            conn, 'employees', employee, ACTOR_REGISTRY,
            entity_label='Colaborador', audit_prefix='employee',
            record_label=employee['name'], summary={},
        )


# ── EPIs ─────────────────────────────────────────────────────────────────────

def test_epi_archive_preserves_history_and_blocks_operations(conn):
    result = _archive_epi(conn)
    assert result['status'] == 'archived'

    for table in ('deliveries', 'stock_movements', 'epi_requests'):
        assert conn.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0] >= 1

    with pytest.raises(ValueError, match='arquivado'):
        ensure_epi_operational(conn, 200, 'movimentações de estoque')

    archived = fetch_archived_epis(conn, ACTOR_GENERAL)
    assert [e['id'] for e in archived] == [200]

    log = conn.execute("SELECT * FROM company_audit_logs WHERE action_type = 'epi_archived'").fetchone()
    assert log is not None and 'Descontinuado' in log['details_json']


def test_epi_restore_reactivates(conn):
    _archive_epi(conn)
    epi = get_epi_lifecycle(conn, 200)
    archival.restore_record(
        conn, 'epis', epi, ACTOR_GENERAL,
        entity_label='EPI', audit_prefix='epi', record_label=epi['name'],
    )
    assert get_epi_lifecycle(conn, 200)['status'] == 'active'
    ensure_epi_operational(conn, 200, 'movimentações de estoque')


def test_epi_purge_only_after_retention_with_tombstone(conn):
    _archive_epi(conn)
    epi = get_epi_lifecycle(conn, 200)
    with pytest.raises(ValueError, match='retenção'):
        archival.request_purge(
            conn, 'epis', epi, ACTOR_GENERAL,
            entity_label='EPI', audit_prefix='epi', record_label=epi['name'],
            summary=summarize_epi_history(conn, 200),
        )
    assert get_epi_lifecycle(conn, 200)['status'] == 'archived'

    _expire_retention(conn, 'epis', 200)
    epi = get_epi_lifecycle(conn, 200)
    summary = archival.request_purge(
        conn, 'epis', epi, ACTOR_GENERAL,
        entity_label='EPI', audit_prefix='epi', record_label=epi['name'],
        summary=summarize_epi_history(conn, 200),
    )
    assert summary['deliveries'] == 1
    assert summary['stock_movements'] == 1
    epi = get_epi_lifecycle(conn, 200)
    archival.confirm_purge(
        conn, 'epis', epi, ACTOR_GENERAL,
        entity_label='EPI', audit_prefix='epi', record_label=epi['name'],
        justification='Prazo legal expirado, sem pendências.',
        confirm_name='Capacete X',
        summary=summary, purge_history=purge_epi_history,
    )
    tomb = get_epi_lifecycle(conn, 200)
    assert tomb is not None and tomb['status'] == 'deleted'
    for table in ('deliveries', 'stock_movements', 'epi_requests'):
        assert conn.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0] == 0


def test_purge_confirm_requires_justification_and_exact_name(conn):
    _archive_epi(conn)
    _expire_retention(conn, 'epis', 200)
    epi = get_epi_lifecycle(conn, 200)
    archival.request_purge(
        conn, 'epis', epi, ACTOR_GENERAL,
        entity_label='EPI', audit_prefix='epi', record_label=epi['name'],
        summary={},
    )
    epi = get_epi_lifecycle(conn, 200)
    with pytest.raises(ValueError, match='Justificativa'):
        archival.confirm_purge(
            conn, 'epis', epi, ACTOR_GENERAL,
            entity_label='EPI', audit_prefix='epi', record_label=epi['name'],
            justification='curta', confirm_name='Capacete X',
            summary={}, purge_history=purge_epi_history,
        )
    with pytest.raises(ValueError, match='Confirmação inválida'):
        archival.confirm_purge(
            conn, 'epis', epi, ACTOR_GENERAL,
            entity_label='EPI', audit_prefix='epi', record_label=epi['name'],
            justification='Prazo legal expirado, sem pendências.', confirm_name='Errado',
            summary={}, purge_history=purge_epi_history,
        )


def test_legacy_schema_without_lifecycle_columns_still_works():
    connection = sqlite3.connect(':memory:')
    connection.row_factory = sqlite3.Row
    connection.executescript(
        """
        CREATE TABLE employees (id INTEGER PRIMARY KEY, company_id INTEGER, unit_id INTEGER, name TEXT);
        CREATE TABLE epis (id INTEGER PRIMARY KEY, company_id INTEGER, unit_id INTEGER, name TEXT);
        INSERT INTO employees (id, company_id, unit_id, name) VALUES (1, 1, 1, 'Ana');
        INSERT INTO epis (id, company_id, unit_id, name) VALUES (2, 1, 1, 'Luva');
        """
    )
    ensure_employee_operational(connection, 1, 'entregas de EPI')
    ensure_epi_operational(connection, 2, 'entregas de EPI')
    connection.close()
