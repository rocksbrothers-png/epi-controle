"""Arquivamento (Soft Delete) de Empresas Terceirizadas/Prestadoras — ADR-0002 §10.4.

Mesma política de Colaboradores/Unidades/EPIs (core.archival): arquivar
(desativado, histórico preservado), desarquivar (volta a ativo), auditoria
permanente. Sem exclusão definitiva por ora (colaboradores vinculados via
employees.outsourced_company_id não são apagados/desvinculados quando a
empresa é arquivada — só ficam bloqueados para NOVOS vínculos).
"""

import sqlite3

import pytest

from core import archival
from core.schema import (
    ensure_legal_entities,
    ensure_outsourced_companies,
    ensure_outsourced_company_archival_lifecycle_columns,
)
from modules.outsourced_companies.service import (
    create_outsourced_company,
    fetch_archived_outsourced_companies,
    fetch_outsourced_companies,
    get_outsourced_company_lifecycle,
)

ACTOR_GENERAL = {'id': 1, 'full_name': 'Admin Geral', 'role': 'general_admin', 'company_id': 1}


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
        CREATE TABLE employees (id INTEGER PRIMARY KEY AUTOINCREMENT, company_id INTEGER NOT NULL, unit_id INTEGER, name TEXT);
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
    ensure_outsourced_company_archival_lifecycle_columns(connection)
    yield connection
    connection.close()


def _create(conn, legal_name='Terceirizada X', **overrides):
    payload = {'legal_name': legal_name}
    payload.update(overrides)
    return create_outsourced_company(conn, payload, 1, actor_user_id=ACTOR_GENERAL['id'])


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
    assert all(c['id'] != entity_id for c in fetch_outsourced_companies(conn, 1))


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
    assert any(c['id'] == entity_id for c in fetch_outsourced_companies(conn, 1))


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
