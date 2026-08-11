"""Arquivamento (Soft Delete) de Empresas Terceirizadas/Prestadoras — ADR-0002 §10.4.

Mesma política de Colaboradores/Unidades/EPIs (core.archival): arquivar
(desativado, histórico preservado), desarquivar (volta a ativo), auditoria
permanente, exclusão definitiva em 2 etapas após o período de retenção
(general_admin/registry_admin, nunca master_admin nem Administrador Local).

Colaboradores vinculados via employees.outsourced_company_id NUNCA são
apagados/desvinculados — nem no arquivamento, nem na exclusão definitiva: só
ficam bloqueados para NOVOS vínculos/entregas (core.archival.
ensure_record_operational). O purge_history da exclusão definitiva remove
só histórico operacional PRÓPRIO da empresa (contratos, vínculos por
Unidade, solicitações de atualização, ressarcimentos) — ver
purge_outsourced_company_history.
"""

import sqlite3

import pytest

from core import archival
from core.schema import (
    ensure_epi_reimbursements,
    ensure_legal_entities,
    ensure_outsourced_companies,
    ensure_outsourced_company_unit_links,
    ensure_outsourced_company_update_requests,
    ensure_outsourced_company_archival_lifecycle_columns,
)
from modules.outsourced_companies.service import (
    create_outsourced_company,
    create_outsourced_company_unit_link,
    fetch_archived_outsourced_companies,
    fetch_outsourced_companies,
    get_outsourced_company_lifecycle,
    purge_outsourced_company_history,
    summarize_outsourced_company_history,
)

ACTOR_GENERAL = {'id': 1, 'full_name': 'Admin Geral', 'role': 'general_admin', 'company_id': 1}
ACTOR_REGISTRY = {'id': 2, 'full_name': 'Admin Registro', 'role': 'registry_admin', 'company_id': 1}
ACTOR_MASTER = {'id': 3, 'full_name': 'Admin Master', 'role': 'master_admin', 'company_id': None}
ACTOR_LOCAL_ADMIN = {'id': 4, 'full_name': 'Admin Local', 'role': 'admin', 'company_id': 1}


def _dict_factory(cursor, row):
    return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}


@pytest.fixture
def conn():
    connection = sqlite3.connect(':memory:')
    connection.row_factory = _dict_factory
    connection.executescript(
        """
        CREATE TABLE companies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT, legal_name TEXT DEFAULT '', cnpj TEXT
        );
        CREATE TABLE units (id INTEGER PRIMARY KEY AUTOINCREMENT, company_id INTEGER NOT NULL, name TEXT);
        CREATE TABLE employees (id INTEGER PRIMARY KEY AUTOINCREMENT, company_id INTEGER NOT NULL, unit_id INTEGER, name TEXT, outsourced_company_id INTEGER);
        CREATE TABLE users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, company_id INTEGER, role TEXT, full_name TEXT DEFAULT '');
        CREATE TABLE company_audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT, company_id INTEGER NOT NULL,
            actor_user_id INTEGER NOT NULL, actor_name TEXT NOT NULL, action_type TEXT NOT NULL,
            summary TEXT NOT NULL, details_json TEXT NOT NULL DEFAULT '[]', created_at TEXT NOT NULL);
        INSERT INTO companies (id, name) VALUES (1, 'ACME');
        """
    )
    ensure_legal_entities(connection)
    ensure_outsourced_companies(connection)
    ensure_outsourced_company_unit_links(connection)
    ensure_outsourced_company_update_requests(connection)
    ensure_epi_reimbursements(connection)
    ensure_outsourced_company_archival_lifecycle_columns(connection)
    yield connection
    connection.close()


def _create(conn, legal_name='Terceirizada X', **overrides):
    payload = {'legal_name': legal_name}
    payload.update(overrides)
    return create_outsourced_company(conn, payload, 1, actor_user_id=ACTOR_GENERAL['id'])


def _expire_retention(conn, entity_id):
    from datetime import datetime, timedelta, timezone
    past = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(timespec='seconds')
    conn.execute('UPDATE outsourced_companies SET retention_until = ? WHERE id = ?', (past, entity_id))


def _archive(conn, entity_id, actor=ACTOR_GENERAL, reason='Contrato encerrado'):
    entity = get_outsourced_company_lifecycle(conn, entity_id)
    return archival.archive_record(
        conn, 'outsourced_companies', entity, actor,
        entity_label='Empresa terceirizada', audit_prefix='outsourced_company',
        record_label=entity['legal_name'], reason=reason, ip='10.0.0.1',
    )


# ── arquivar ────────────────────────────────────────────────────────────────

def test_archive_sets_status_archived_and_retention(conn):
    entity_id = _create(conn)
    result = _archive(conn, entity_id)
    assert result['status'] == 'archived'
    assert result['retention_years'] == archival.MIN_RETENTION_YEARS

    entity = get_outsourced_company_lifecycle(conn, entity_id)
    assert entity['status'] == 'archived'
    assert entity['archived_at']
    assert entity['retention_until']


def test_archived_company_disappears_from_active_list(conn):
    entity_id = _create(conn)
    _archive(conn, entity_id)
    assert all(c['id'] != entity_id for c in fetch_outsourced_companies(conn, 1)['linked'])


def test_archived_company_appears_in_archived_list_with_retention_info(conn):
    entity_id = _create(conn)
    _archive(conn, entity_id, reason='Fim de contrato')
    archived = fetch_archived_outsourced_companies(conn, ACTOR_GENERAL)
    assert [c['id'] for c in archived] == [entity_id]
    assert archived[0]['retention_days_remaining'] > 0
    assert archived[0]['archive_reason'] == 'Fim de contrato'


def test_ensure_record_operational_blocks_archived_company(conn):
    entity_id = _create(conn)
    _archive(conn, entity_id)
    with pytest.raises(ValueError, match='arquivad'):
        archival.ensure_record_operational(
            conn, 'outsourced_companies', entity_id, 'Empresa terceirizada', 'novos colaboradores',
        )


def test_archive_is_audited(conn):
    entity_id = _create(conn)
    _archive(conn, entity_id, reason='Fim de contrato')
    log = conn.execute(
        "SELECT * FROM company_audit_logs WHERE action_type = 'outsourced_company_archived'"
    ).fetchone()
    assert log is not None
    assert 'Fim de contrato' in log['details_json'] or 'Fim de contrato' in log['summary']


def test_archive_twice_is_rejected(conn):
    entity_id = _create(conn)
    _archive(conn, entity_id)
    with pytest.raises(ValueError, match='já está arquivad'):
        _archive(conn, entity_id)


# ── desarquivar ───────────────────────────────────────────────────────────

def test_restore_reactivates_company(conn):
    entity_id = _create(conn)
    _archive(conn, entity_id)
    entity = get_outsourced_company_lifecycle(conn, entity_id)
    archival.restore_record(
        conn, 'outsourced_companies', entity, ACTOR_GENERAL,
        entity_label='Empresa terceirizada', audit_prefix='outsourced_company',
        record_label=entity['legal_name'],
    )
    restored = get_outsourced_company_lifecycle(conn, entity_id)
    assert restored['status'] == 'active'
    assert restored['archived_at'] is None
    # Volta a operar normalmente.
    archival.ensure_record_operational(conn, 'outsourced_companies', entity_id, 'Empresa terceirizada', 'novos colaboradores')
    assert any(c['id'] == entity_id for c in fetch_outsourced_companies(conn, 1)['linked'])


def test_restore_rejects_non_archived_company(conn):
    entity_id = _create(conn)
    entity = get_outsourced_company_lifecycle(conn, entity_id)
    with pytest.raises(ValueError, match='arquivados podem ser desarquivados'):
        archival.restore_record(
            conn, 'outsourced_companies', entity, ACTOR_GENERAL,
            entity_label='Empresa terceirizada', audit_prefix='outsourced_company',
            record_label=entity['legal_name'],
        )


def test_restore_is_audited(conn):
    entity_id = _create(conn)
    _archive(conn, entity_id)
    entity = get_outsourced_company_lifecycle(conn, entity_id)
    archival.restore_record(
        conn, 'outsourced_companies', entity, ACTOR_GENERAL,
        entity_label='Empresa terceirizada', audit_prefix='outsourced_company',
        record_label=entity['legal_name'],
    )
    log = conn.execute(
        "SELECT * FROM company_audit_logs WHERE action_type = 'outsourced_company_restored'"
    ).fetchone()
    assert log is not None


# ── isolamento multi-tenant ──────────────────────────────────────────────────

def test_fetch_archived_outsourced_companies_is_scoped_by_tenant(conn):
    conn.execute("INSERT INTO companies (id, name) VALUES (2, 'Outra Empresa')")
    conn.commit()
    entity_a = create_outsourced_company(conn, {'legal_name': 'Terceirizada A'}, 1, actor_user_id=1)
    entity_b = create_outsourced_company(conn, {'legal_name': 'Terceirizada B'}, 2, actor_user_id=1)
    _archive(conn, entity_a)
    _archive(conn, entity_b, actor={'id': 2, 'full_name': 'Admin B', 'role': 'general_admin', 'company_id': 2})

    archived_a = fetch_archived_outsourced_companies(conn, ACTOR_GENERAL)
    assert [c['id'] for c in archived_a] == [entity_a]

    archived_b = fetch_archived_outsourced_companies(
        conn, {'id': 2, 'role': 'general_admin', 'company_id': 2},
    )
    assert [c['id'] for c in archived_b] == [entity_b]


def test_master_admin_sees_archived_companies_across_tenants(conn):
    conn.execute("INSERT INTO companies (id, name) VALUES (2, 'Outra Empresa')")
    conn.commit()
    entity_a = create_outsourced_company(conn, {'legal_name': 'Terceirizada A'}, 1, actor_user_id=1)
    entity_b = create_outsourced_company(conn, {'legal_name': 'Terceirizada B'}, 2, actor_user_id=1)
    _archive(conn, entity_a)
    _archive(conn, entity_b, actor={'id': 2, 'full_name': 'Admin B', 'role': 'general_admin', 'company_id': 2})

    archived = fetch_archived_outsourced_companies(conn, {'id': 99, 'role': 'master_admin', 'company_id': None})
    assert {c['id'] for c in archived} == {entity_a, entity_b}


def test_legacy_schema_without_lifecycle_columns_still_works():
    connection = sqlite3.connect(':memory:')
    connection.row_factory = _dict_factory
    connection.executescript(
        """
        CREATE TABLE outsourced_companies (id INTEGER PRIMARY KEY, company_id INTEGER, legal_name TEXT);
        INSERT INTO outsourced_companies (id, company_id, legal_name) VALUES (1, 1, 'Legado');
        """
    )
    # Sem lifecycle: nunca bloqueia (retrocompatibilidade com schema parcial).
    archival.ensure_record_operational(connection, 'outsourced_companies', 1, 'Empresa terceirizada', 'operação')
    connection.close()


# ── Exclusão definitiva (Purge) ────────────────────────────────────────────

_PURGE_KWARGS = dict(entity_label='Empresa terceirizada', audit_prefix='outsourced_company')


def test_summarize_outsourced_company_history_counts_dependents(conn):
    unit_id = conn.execute("INSERT INTO units (company_id, name) VALUES (1, 'Unidade A')").lastrowid
    entity_id = _create(conn)
    create_outsourced_company_unit_link(conn, entity_id, 1, unit_id, ACTOR_GENERAL['id'])
    conn.execute(
        "INSERT INTO service_contracts (company_id, outsourced_company_id, contract_ref, created_at, updated_at) "
        "VALUES (1, ?, 'CT-1', '', '')", (entity_id,),
    )
    conn.execute(
        "INSERT INTO outsourced_company_update_requests (company_id, outsourced_company_id, message, created_at, updated_at) "
        "VALUES (1, ?, 'corrigir CNPJ', '', '')", (entity_id,),
    )
    conn.execute(
        "INSERT INTO epi_reimbursements (company_id, delivery_id, outsourced_company_id, created_at, updated_at) "
        "VALUES (1, 999, ?, '', '')", (entity_id,),
    )
    conn.commit()
    summary = summarize_outsourced_company_history(conn, entity_id)
    assert summary == {
        'service_contracts': 1, 'unit_links': 1, 'update_requests': 1, 'epi_reimbursements': 1,
    }


def test_purge_only_after_retention(conn):
    entity_id = _create(conn)
    _archive(conn, entity_id)
    entity = get_outsourced_company_lifecycle(conn, entity_id)
    with pytest.raises(ValueError, match='retenção'):
        archival.request_purge(
            conn, 'outsourced_companies', entity, ACTOR_GENERAL,
            record_label=entity['legal_name'], summary={}, **_PURGE_KWARGS,
        )
    assert get_outsourced_company_lifecycle(conn, entity_id)['status'] == 'archived'


def test_purge_requires_general_or_registry_admin(conn):
    entity_id = _create(conn)
    _archive(conn, entity_id)
    _expire_retention(conn, entity_id)
    entity = get_outsourced_company_lifecycle(conn, entity_id)
    with pytest.raises(PermissionError):
        archival.request_purge(
            conn, 'outsourced_companies', entity, ACTOR_MASTER,
            record_label=entity['legal_name'], summary={}, **_PURGE_KWARGS,
        )
    with pytest.raises(PermissionError):
        archival.request_purge(
            conn, 'outsourced_companies', entity, ACTOR_LOCAL_ADMIN,
            record_label=entity['legal_name'], summary={}, **_PURGE_KWARGS,
        )
    summary = archival.request_purge(
        conn, 'outsourced_companies', entity, ACTOR_REGISTRY,
        record_label=entity['legal_name'],
        summary=summarize_outsourced_company_history(conn, entity_id), **_PURGE_KWARGS,
    )
    assert summary['service_contracts'] == 0


def test_purge_cancel_returns_to_archived(conn):
    entity_id = _create(conn)
    _archive(conn, entity_id)
    _expire_retention(conn, entity_id)
    entity = get_outsourced_company_lifecycle(conn, entity_id)
    archival.request_purge(
        conn, 'outsourced_companies', entity, ACTOR_GENERAL,
        record_label=entity['legal_name'], summary={}, **_PURGE_KWARGS,
    )
    entity = get_outsourced_company_lifecycle(conn, entity_id)
    archival.cancel_purge(conn, 'outsourced_companies', entity, ACTOR_GENERAL, record_label=entity['legal_name'], **_PURGE_KWARGS)
    assert get_outsourced_company_lifecycle(conn, entity_id)['status'] == 'archived'


def test_purge_confirm_removes_operational_history_but_preserves_employees(conn):
    """A garantia central da exclusão definitiva desta entidade: contratos/
    vínculos/solicitações/ressarcimentos (histórico PRÓPRIO da empresa) são
    removidos, mas `employees` — que não é histórico, é um registro
    independente — nunca é tocado (ver nota em purge_outsourced_company_history)."""
    unit_id = conn.execute("INSERT INTO units (company_id, name) VALUES (1, 'Unidade A')").lastrowid
    entity_id = _create(conn)
    employee_id = conn.execute(
        "INSERT INTO employees (company_id, unit_id, name, outsourced_company_id) VALUES (1, ?, 'Fulano', ?)",
        (unit_id, entity_id),
    ).lastrowid
    create_outsourced_company_unit_link(conn, entity_id, 1, unit_id, ACTOR_GENERAL['id'])
    conn.execute(
        "INSERT INTO service_contracts (company_id, outsourced_company_id, contract_ref, created_at, updated_at) "
        "VALUES (1, ?, 'CT-1', '', '')", (entity_id,),
    )
    conn.execute(
        "INSERT INTO outsourced_company_update_requests (company_id, outsourced_company_id, message, created_at, updated_at) "
        "VALUES (1, ?, 'corrigir CNPJ', '', '')", (entity_id,),
    )
    conn.execute(
        "INSERT INTO epi_reimbursements (company_id, delivery_id, outsourced_company_id, created_at, updated_at) "
        "VALUES (1, 999, ?, '', '')", (entity_id,),
    )
    conn.commit()

    _archive(conn, entity_id)
    _expire_retention(conn, entity_id)
    entity = get_outsourced_company_lifecycle(conn, entity_id)
    summary = archival.request_purge(
        conn, 'outsourced_companies', entity, ACTOR_GENERAL,
        record_label=entity['legal_name'],
        summary=summarize_outsourced_company_history(conn, entity_id), **_PURGE_KWARGS,
    )
    assert summary['service_contracts'] == 1

    entity = get_outsourced_company_lifecycle(conn, entity_id)
    removed = archival.confirm_purge(
        conn, 'outsourced_companies', entity, ACTOR_GENERAL,
        record_label=entity['legal_name'],
        justification='Prazo legal expirado, sem pendências.',
        confirm_name=entity['legal_name'],
        summary=summary, purge_history=purge_outsourced_company_history,
        **_PURGE_KWARGS,
    )
    assert removed['service_contracts'] == 1
    assert removed['unit_links'] == 1
    assert removed['update_requests'] == 1
    assert removed['epi_reimbursements'] == 1

    for table in ('service_contracts', 'outsourced_company_unit_links', 'outsourced_company_update_requests', 'epi_reimbursements'):
        assert conn.execute(f'SELECT COUNT(*) AS n FROM {table} WHERE outsourced_company_id = ?', (entity_id,)).fetchone()['n'] == 0

    # Tombstone: a linha permanece, com legal_name intacto (o colaborador
    # continua resolvendo o nome da empresa por id, sem filtrar por status).
    tomb = get_outsourced_company_lifecycle(conn, entity_id)
    assert tomb is not None and tomb['status'] == 'deleted' and tomb['legal_name'] == 'Terceirizada X'

    # O colaborador nunca é tocado: continua existindo, apontando para a
    # empresa (agora tombstone) exatamente como antes.
    employee = conn.execute('SELECT * FROM employees WHERE id = ?', (employee_id,)).fetchone()
    assert employee is not None
    assert employee['outsourced_company_id'] == entity_id

    actions = [r['action_type'] for r in conn.execute('SELECT action_type FROM company_audit_logs ORDER BY id')]
    assert actions == [
        'outsourced_company_archived', 'outsourced_company_purge_requested', 'outsourced_company_purged',
    ]
