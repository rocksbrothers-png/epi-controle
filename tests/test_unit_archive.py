"""Política de Arquivamento (Soft Delete) de Unidades com retenção mínima.

Cobre: arquivamento preservando histórico, bloqueio de novas operações,
retenção por tenant (mínimo 5 anos), exclusão definitiva em duas etapas
com justificativa, bloqueio jurídico, tombstone e isolamento multi-tenant.
"""
import sqlite3
from datetime import datetime, timedelta, timezone

import pytest

from modules.units.service import (
    UNIT_MIN_RETENTION_YEARS,
    archive_unit,
    cancel_unit_purge,
    confirm_unit_purge,
    ensure_unit_operational,
    fetch_archived_units,
    fetch_units,
    get_company_retention_years,
    get_unit_by_id,
    request_unit_purge,
    restore_unit,
    set_company_retention_years,
    set_unit_legal_hold,
)

UTC = timezone.utc

ACTOR_GENERAL = {'id': 1, 'full_name': 'Admin Geral', 'role': 'general_admin', 'company_id': 1}
ACTOR_REGISTRY = {'id': 2, 'full_name': 'Admin Registro', 'role': 'registry_admin', 'company_id': 1}
ACTOR_MASTER = {'id': 3, 'full_name': 'Admin Master', 'role': 'master_admin', 'company_id': None}


@pytest.fixture
def conn():
    connection = sqlite3.connect(':memory:')
    connection.row_factory = sqlite3.Row
    connection.executescript(
        """
        CREATE TABLE companies (
            id INTEGER PRIMARY KEY, name TEXT, cnpj TEXT DEFAULT '', logo_type TEXT DEFAULT '',
            unit_retention_years INTEGER NOT NULL DEFAULT 5);
        CREATE TABLE users (id INTEGER PRIMARY KEY, full_name TEXT, role TEXT,
            company_id INTEGER, linked_employee_id INTEGER);
        CREATE TABLE units (
            id INTEGER PRIMARY KEY AUTOINCREMENT, company_id INTEGER NOT NULL, name TEXT NOT NULL,
            unit_type TEXT NOT NULL DEFAULT 'base', city TEXT NOT NULL DEFAULT '', notes TEXT DEFAULT '',
            status TEXT NOT NULL DEFAULT 'active', archived_at TEXT, archived_by INTEGER,
            archive_reason TEXT NOT NULL DEFAULT '', retention_until TEXT,
            legal_hold INTEGER NOT NULL DEFAULT 0, legal_hold_reason TEXT NOT NULL DEFAULT '',
            deleted_at TEXT, deleted_by INTEGER, delete_reason TEXT NOT NULL DEFAULT '');
        CREATE TABLE company_audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT, company_id INTEGER NOT NULL,
            actor_user_id INTEGER NOT NULL, actor_name TEXT NOT NULL, action_type TEXT NOT NULL,
            summary TEXT NOT NULL, details_json TEXT NOT NULL DEFAULT '[]', created_at TEXT NOT NULL);
        CREATE TABLE employees (id INTEGER PRIMARY KEY, company_id INTEGER, unit_id INTEGER, name TEXT);
        CREATE TABLE employee_unit_movements (id INTEGER PRIMARY KEY, employee_id INTEGER,
            source_unit_id INTEGER, target_unit_id INTEGER);
        CREATE TABLE employee_portal_audit_logs (id INTEGER PRIMARY KEY, employee_id INTEGER);
        CREATE TABLE employee_portal_links (id INTEGER PRIMARY KEY, employee_id INTEGER);
        CREATE TABLE epis (id INTEGER PRIMARY KEY, company_id INTEGER, unit_id INTEGER, name TEXT);
        CREATE TABLE epi_stock_items (id INTEGER PRIMARY KEY, epi_id INTEGER, unit_id INTEGER);
        CREATE TABLE epi_stock_item_reprints (id INTEGER PRIMARY KEY, stock_item_id INTEGER);
        CREATE TABLE stock_movements (id INTEGER PRIMARY KEY, epi_id INTEGER, unit_id INTEGER);
        CREATE TABLE unit_epi_stock (id INTEGER PRIMARY KEY, epi_id INTEGER, unit_id INTEGER);
        CREATE TABLE epi_ficha_items (id INTEGER PRIMARY KEY, epi_id INTEGER, unit_id INTEGER);
        CREATE TABLE epi_ficha_periods (id INTEGER PRIMARY KEY, unit_id INTEGER);
        CREATE TABLE deliveries (id INTEGER PRIMARY KEY, epi_id INTEGER, unit_id INTEGER);
        CREATE TABLE epi_devolutions (id INTEGER PRIMARY KEY, unit_id INTEGER);
        CREATE TABLE epi_requests (id INTEGER PRIMARY KEY, epi_id INTEGER, unit_id INTEGER);
        CREATE TABLE epi_request_history (id INTEGER PRIMARY KEY, request_id INTEGER);
        CREATE TABLE epi_feedbacks (id INTEGER PRIMARY KEY, epi_id INTEGER, unit_id INTEGER);
        CREATE TABLE epi_feedback_history (id INTEGER PRIMARY KEY, feedback_id INTEGER);
        CREATE TABLE ficha_epi_snapshots (id INTEGER PRIMARY KEY, unit_id INTEGER);
        CREATE TABLE ficha_epi_audit_log (id INTEGER PRIMARY KEY, unit_id INTEGER);
        CREATE TABLE purchase_requests (id INTEGER PRIMARY KEY, company_id INTEGER, unit_id INTEGER);
        CREATE TABLE purchase_request_items (id INTEGER PRIMARY KEY, purchase_request_id INTEGER, unit_id INTEGER);
        CREATE TABLE purchase_orders (id INTEGER PRIMARY KEY, company_id INTEGER, unit_id INTEGER);
        CREATE TABLE purchase_order_items (id INTEGER PRIMARY KEY, purchase_order_id INTEGER);
        CREATE TABLE purchase_order_files (id INTEGER PRIMARY KEY, purchase_order_id INTEGER);
        CREATE TABLE purchase_approvals (id INTEGER PRIMARY KEY, purchase_order_id INTEGER);
        CREATE TABLE purchase_order_confirmations (id INTEGER PRIMARY KEY, purchase_order_id INTEGER);
        CREATE TABLE purchase_pendencies (id INTEGER PRIMARY KEY, unit_id INTEGER);
        CREATE TABLE purchase_role_unit_links (id INTEGER PRIMARY KEY, unit_id INTEGER);
        CREATE TABLE unit_joint_venture_periods (id INTEGER PRIMARY KEY, unit_id INTEGER,
            joint_venture_name TEXT, started_at TEXT, ended_at TEXT);

        INSERT INTO companies (id, name) VALUES (1, 'ACME'), (2, 'Beta Corp');
        INSERT INTO units (id, company_id, name, unit_type, city) VALUES
            (10, 1, 'Base Santos', 'base', 'Santos'),
            (20, 2, 'Base Macae', 'base', 'Macaé');
        INSERT INTO employees VALUES (100, 1, 10, 'Maria');
        INSERT INTO deliveries VALUES (200, NULL, 10);
        INSERT INTO stock_movements VALUES (300, NULL, 10);
        INSERT INTO epi_requests VALUES (400, NULL, 10);
        INSERT INTO epi_feedbacks VALUES (500, NULL, 10);
        INSERT INTO purchase_requests VALUES (600, 1, 10);
        INSERT INTO purchase_orders VALUES (700, 1, 10);
        """
    )
    yield connection
    connection.close()


def _archive(conn, unit_id=10, actor=ACTOR_GENERAL, reason='Encerramento do contrato'):
    unit = get_unit_by_id(conn, unit_id)
    return archive_unit(conn, unit, actor, reason=reason, ip='10.0.0.1')


def _expire_retention(conn, unit_id=10):
    past = (datetime.now(UTC) - timedelta(days=1)).isoformat(timespec='seconds')
    conn.execute('UPDATE units SET retention_until = ? WHERE id = ?', (past, unit_id))


# ── Arquivamento preserva histórico ──────────────────────────────────────────

def test_archive_preserves_all_history(conn):
    result = _archive(conn)
    assert result['status'] == 'archived'
    assert result['retention_years'] == UNIT_MIN_RETENTION_YEARS

    unit = get_unit_by_id(conn, 10)
    assert unit['status'] == 'archived'
    assert unit['archived_by'] == 1
    assert unit['archive_reason'] == 'Encerramento do contrato'
    assert unit['retention_until']

    # Nenhum registro histórico foi tocado.
    for table in ('employees', 'deliveries', 'stock_movements', 'epi_requests',
                  'epi_feedbacks', 'purchase_requests', 'purchase_orders'):
        count = conn.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]
        assert count == 1, f'{table} não deveria ser alterada pelo arquivamento'

    # Auditoria registrada com motivo, retenção e IP.
    log = conn.execute("SELECT * FROM company_audit_logs WHERE action_type = 'unit_archived'").fetchone()
    assert log is not None
    assert '10.0.0.1' in log['details_json']
    assert 'Encerramento do contrato' in log['details_json']


def test_archive_sets_minimum_retention_of_five_years(conn):
    result = _archive(conn)
    until = datetime.fromisoformat(result['retention_until'])
    assert until.year >= datetime.now(UTC).year + UNIT_MIN_RETENTION_YEARS


def test_retention_is_configurable_per_tenant_but_never_below_minimum(conn):
    set_company_retention_years(conn, 1, 10)
    assert get_company_retention_years(conn, 1) == 10
    assert get_company_retention_years(conn, 2) == 5
    with pytest.raises(ValueError):
        set_company_retention_years(conn, 1, 3)


def test_archived_unit_leaves_main_listing_but_appears_in_archive(conn):
    _archive(conn)
    active = fetch_units(conn, ACTOR_GENERAL)
    assert all(item['id'] != 10 for item in active)
    archived = fetch_archived_units(conn, ACTOR_GENERAL)
    assert [item['id'] for item in archived] == [10]
    assert archived[0]['retention_days_remaining'] > 0


def test_multi_tenant_isolation_of_archive_listing(conn):
    _archive(conn, unit_id=10)
    unit2 = get_unit_by_id(conn, 20)
    archive_unit(conn, unit2, ACTOR_MASTER, reason='x')
    actor_company2 = {'id': 9, 'full_name': 'Admin B', 'role': 'general_admin', 'company_id': 2}
    archived = fetch_archived_units(conn, actor_company2)
    assert [item['id'] for item in archived] == [20]


# ── Bloqueio de novas operações ──────────────────────────────────────────────

def test_archived_unit_blocks_new_operations(conn):
    _archive(conn)
    with pytest.raises(ValueError, match='Unidade arquivada'):
        ensure_unit_operational(conn, 10, 'entregas de EPI')
    # Unidade ativa segue liberada.
    ensure_unit_operational(conn, 20, 'entregas de EPI')


def test_restore_reactivates_unit(conn):
    _archive(conn)
    restore_unit(conn, get_unit_by_id(conn, 10), ACTOR_GENERAL)
    unit = get_unit_by_id(conn, 10)
    assert unit['status'] == 'active'
    assert unit['archived_at'] is None
    ensure_unit_operational(conn, 10, 'entregas de EPI')


def test_double_archive_rejected(conn):
    _archive(conn)
    with pytest.raises(ValueError):
        _archive(conn)


# ── Exclusão definitiva ──────────────────────────────────────────────────────

def test_purge_blocked_while_retention_active(conn):
    _archive(conn)
    with pytest.raises(ValueError, match='retenção'):
        request_unit_purge(conn, get_unit_by_id(conn, 10), ACTOR_GENERAL)


def test_purge_blocked_without_archive(conn):
    with pytest.raises(ValueError, match='arquivada'):
        request_unit_purge(conn, get_unit_by_id(conn, 10), ACTOR_GENERAL)


def test_purge_requires_general_or_registry_admin(conn):
    _archive(conn)
    _expire_retention(conn)
    with pytest.raises(PermissionError):
        request_unit_purge(conn, get_unit_by_id(conn, 10), ACTOR_MASTER)
    summary = request_unit_purge(conn, get_unit_by_id(conn, 10), ACTOR_REGISTRY)
    assert summary['employees'] == 1


def test_purge_blocked_by_legal_hold(conn):
    _archive(conn)
    _expire_retention(conn)
    set_unit_legal_hold(conn, get_unit_by_id(conn, 10), ACTOR_GENERAL, True, reason='Auditoria em andamento')
    with pytest.raises(ValueError, match='jurídico'):
        request_unit_purge(conn, get_unit_by_id(conn, 10), ACTOR_GENERAL)


def test_purge_two_step_flow_with_summary_and_justification(conn):
    _archive(conn)
    _expire_retention(conn)

    summary = request_unit_purge(conn, get_unit_by_id(conn, 10), ACTOR_GENERAL, ip='10.0.0.2')
    assert summary['employees'] == 1
    assert summary['deliveries'] == 1
    assert summary['purchase_orders'] == 1
    assert get_unit_by_id(conn, 10)['status'] == 'pending_deletion'

    # Etapa 2 exige justificativa e o nome exato da unidade.
    with pytest.raises(ValueError, match='Justificativa'):
        confirm_unit_purge(conn, get_unit_by_id(conn, 10), ACTOR_GENERAL, 'curta', 'Base Santos')
    with pytest.raises(ValueError, match='nome exato'):
        confirm_unit_purge(conn, get_unit_by_id(conn, 10), ACTOR_GENERAL,
                           'Prazo legal expirado, sem pendências.', 'Nome Errado')

    removed = confirm_unit_purge(conn, get_unit_by_id(conn, 10), ACTOR_GENERAL,
                                 'Prazo legal expirado, sem pendências.', 'Base Santos', ip='10.0.0.2')
    assert removed['employees'] == 1

    # Tombstone: o registro da unidade permanece, com metadados da exclusão.
    unit = get_unit_by_id(conn, 10)
    assert unit is not None
    assert unit['status'] == 'deleted'
    assert unit['deleted_by'] == 1
    assert unit['delete_reason'] == 'Prazo legal expirado, sem pendências.'

    # Dados operacionais expurgados.
    for table in ('employees', 'deliveries', 'stock_movements', 'epi_requests',
                  'epi_feedbacks', 'purchase_requests', 'purchase_orders'):
        count = conn.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]
        assert count == 0, f'{table} deveria ter sido expurgada'

    # Trilha de auditoria permanente com todas as etapas.
    actions = [row['action_type'] for row in conn.execute(
        'SELECT action_type FROM company_audit_logs ORDER BY id').fetchall()]
    assert actions == ['unit_archived', 'unit_purge_requested', 'unit_purged']


def test_purge_cancel_returns_to_archived(conn):
    _archive(conn)
    _expire_retention(conn)
    request_unit_purge(conn, get_unit_by_id(conn, 10), ACTOR_GENERAL)
    cancel_unit_purge(conn, get_unit_by_id(conn, 10), ACTOR_GENERAL)
    assert get_unit_by_id(conn, 10)['status'] == 'archived'


def test_purge_confirm_requires_pending_state(conn):
    _archive(conn)
    _expire_retention(conn)
    with pytest.raises(ValueError, match='etapa 1'):
        confirm_unit_purge(conn, get_unit_by_id(conn, 10), ACTOR_GENERAL,
                           'Prazo legal expirado, sem pendências.', 'Base Santos')


# ── Compatibilidade com schemas legados (sem colunas de ciclo de vida) ───────

def test_legacy_schema_without_lifecycle_columns_still_works():
    connection = sqlite3.connect(':memory:')
    connection.row_factory = sqlite3.Row
    connection.executescript(
        """
        CREATE TABLE companies (id INTEGER PRIMARY KEY, name TEXT, cnpj TEXT DEFAULT '', logo_type TEXT DEFAULT '');
        CREATE TABLE units (id INTEGER PRIMARY KEY, company_id INTEGER, name TEXT,
            unit_type TEXT DEFAULT 'base', city TEXT DEFAULT '', notes TEXT DEFAULT '');
        INSERT INTO companies (id, name) VALUES (1, 'ACME');
        INSERT INTO units (id, company_id, name) VALUES (1, 1, 'Base');
        """
    )
    units = fetch_units(connection, ACTOR_GENERAL)
    assert len(units) == 1
    ensure_unit_operational(connection, 1, 'entregas de EPI')
    connection.close()
