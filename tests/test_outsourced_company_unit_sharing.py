"""Compartilhamento do cadastro corporativo de Empresa Terceirizada/
Prestadora por tenant + trava pós-promoção (ADR-0002 §12).

Cobre o que o §11 (test_outsourced_companies_unit_scope.py) não cobria:
cadastro corporativo único por tenant (não mais um por Unidade), vínculo
operacional em `outsourced_company_unit_links` (`outsourced_company_id` +
`unit_id`), trava de edição corporativa pós-promoção ao Cadastro Padrão,
"Solicitar atualização cadastral" e detecção de duplicidade por CNPJ/nome.
"""

import sqlite3

import pytest

from core.schema import (
    ensure_legal_entities,
    ensure_outsourced_companies,
    ensure_outsourced_company_archival_lifecycle_columns,
    ensure_outsourced_company_unit_links,
    ensure_outsourced_company_update_requests,
)
from modules.outsourced_companies.service import (
    DuplicateOutsourcedCompanyError,
    annotate_outsourced_company_visibility,
    create_outsourced_company,
    create_outsourced_company_unit_link,
    create_outsourced_company_update_request,
    ensure_actor_can_edit_outsourced_company_corporate_fields,
    ensure_actor_outsourced_company_scope,
    fetch_outsourced_companies,
    fetch_outsourced_company_unit_link,
    fetch_outsourced_company_update_requests,
    get_outsourced_company_by_id,
    get_outsourced_company_update_request_by_id,
    is_outsourced_company_available_to_unit,
    promote_outsourced_company,
    resolve_outsourced_company_update_request,
    search_outsourced_companies_by_name,
    set_outsourced_company_unit_link_status,
    update_outsourced_company,
    validate_employee_outsourced_reference,
)


def _dict_factory(cursor, row):
    return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}


class _PgStyleConn:
    def __init__(self, conn):
        self._conn = conn

    def execute(self, sql, params=()):
        return self._conn.execute(str(sql).replace('%s', '?'), params)

    def commit(self):
        self._conn.commit()

    def __getattr__(self, name):
        return getattr(self._conn, name)


def _conn():
    conn = sqlite3.connect(':memory:')
    conn.row_factory = _dict_factory
    conn.executescript(
        """
        CREATE TABLE companies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT, legal_name TEXT DEFAULT '', cnpj TEXT, logo_type TEXT DEFAULT '',
            user_limit INTEGER NOT NULL DEFAULT 999, license_status TEXT NOT NULL DEFAULT 'active',
            active INTEGER NOT NULL DEFAULT 1, contract_end TEXT, addendum_enabled INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE units (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL, name TEXT, unit_type TEXT DEFAULT '',
            city TEXT DEFAULT '', notes TEXT DEFAULT ''
        );
        CREATE TABLE employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL, unit_id INTEGER, name TEXT,
            employee_id_code TEXT DEFAULT '', cpf TEXT DEFAULT '', email TEXT DEFAULT '',
            whatsapp TEXT DEFAULT '', preferred_contact_channel TEXT DEFAULT '',
            sector TEXT DEFAULT '', role_name TEXT DEFAULT '', admission_date TEXT DEFAULT '',
            schedule_type TEXT DEFAULT '', tipo_vinculo TEXT DEFAULT 'CLT', empresa_origem TEXT DEFAULT '',
            status TEXT NOT NULL DEFAULT 'active'
        );
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT, password TEXT DEFAULT '', company_id INTEGER, role TEXT, full_name TEXT DEFAULT '',
            active INTEGER NOT NULL DEFAULT 1, linked_employee_id INTEGER
        );
        CREATE TABLE employee_unit_movements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id INTEGER, movement_type TEXT, start_date TEXT, end_date TEXT DEFAULT '',
            target_unit_id INTEGER
        );
        CREATE TABLE company_audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT, company_id INTEGER NOT NULL,
            actor_user_id INTEGER NOT NULL, actor_name TEXT NOT NULL, action_type TEXT NOT NULL,
            summary TEXT NOT NULL, details_json TEXT NOT NULL DEFAULT '[]', created_at TEXT NOT NULL
        );
        CREATE TABLE app_meta (key TEXT PRIMARY KEY, value TEXT);
        """
    )
    return conn


def _bootstrap(conn):
    ensure_legal_entities(conn)
    ensure_outsourced_companies(conn)
    ensure_outsourced_company_unit_links(conn)
    ensure_outsourced_company_update_requests(conn)
    ensure_outsourced_company_archival_lifecycle_columns(conn)


def _seed_company(conn, name='ACME'):
    cur = conn.execute('INSERT INTO companies (name, legal_name, cnpj) VALUES (?, ?, ?)', (name, name, ''))
    conn.commit()
    return int(cur.lastrowid)


def _seed_unit(conn, company_id, name='Unidade'):
    cur = conn.execute('INSERT INTO units (company_id, name) VALUES (?, ?)', (company_id, name))
    conn.commit()
    return int(cur.lastrowid)


def _seed_unit_scoped_actor(conn, company_id, unit_id, role='admin', actor_id=1):
    cur = conn.execute(
        'INSERT INTO employees (company_id, unit_id, name) VALUES (?, ?, ?)',
        (company_id, unit_id, 'Responsável da Unidade'),
    )
    conn.commit()
    employee_id = int(cur.lastrowid)
    return {'id': actor_id, 'role': role, 'company_id': company_id, 'linked_employee_id': employee_id}


@pytest.fixture(autouse=True)
def _sqlite_detection(monkeypatch):
    import epi_backend.db as db_module
    monkeypatch.setattr(db_module, '_is_sqlite_connection', lambda _conn: True)


@pytest.fixture
def scoped_units(monkeypatch):
    """Faz `actor_operational_unit_id` resolver via a mesma unidade que
    `_seed_unit_scoped_actor` gravou em `employees`, sem depender de
    `linked_employee_id` estar num formato específico — o próprio teste
    decide o mapeamento id-do-ator -> unidade."""
    import core.repository as repository
    mapping = {}

    def _fake(_connection, actor):
        return mapping.get(actor.get('id'))

    monkeypatch.setattr(repository, 'actor_operational_unit_id', _fake)
    import modules.outsourced_companies.service as service
    monkeypatch.setattr(service, 'actor_operational_unit_id', _fake, raising=False)
    return mapping


# ── Schema: idempotência ────────────────────────────────────────────────────

def test_ensure_outsourced_company_unit_links_is_idempotent():
    conn = _PgStyleConn(_conn())
    _seed_company(conn)
    ensure_legal_entities(conn)
    ensure_outsourced_companies(conn)
    ensure_outsourced_company_unit_links(conn)
    ensure_outsourced_company_unit_links(conn)  # reexecução segura
    row = conn.execute("SELECT COUNT(*) AS n FROM sqlite_master WHERE type='table' "
                        "AND name='outsourced_company_unit_links'").fetchone()
    assert row['n'] == 1


def test_ensure_outsourced_company_update_requests_is_idempotent():
    conn = _PgStyleConn(_conn())
    ensure_legal_entities(conn)
    ensure_outsourced_companies(conn)
    ensure_outsourced_company_update_requests(conn)
    ensure_outsourced_company_update_requests(conn)
    row = conn.execute("SELECT COUNT(*) AS n FROM sqlite_master WHERE type='table' "
                        "AND name='outsourced_company_update_requests'").fetchone()
    assert row['n'] == 1


# ── Vínculo por Unidade: criação, idempotência, ativar/desativar ──────────

def test_create_outsourced_company_auto_links_origin_unit():
    conn = _PgStyleConn(_conn())
    cid = _seed_company(conn)
    _bootstrap(conn)
    unit_a = _seed_unit(conn, cid, 'Unidade A')
    entity_id = create_outsourced_company(conn, {'legal_name': 'Alfa'}, cid, unit_id=unit_a)
    link = fetch_outsourced_company_unit_link(conn, entity_id, unit_a)
    assert link is not None
    assert link['local_status'] == 'active'


def test_create_outsourced_company_unit_link_is_idempotent():
    conn = _PgStyleConn(_conn())
    cid = _seed_company(conn)
    _bootstrap(conn)
    unit_a = _seed_unit(conn, cid, 'Unidade A')
    unit_b = _seed_unit(conn, cid, 'Unidade B')
    entity_id = create_outsourced_company(conn, {'legal_name': 'Alfa'}, cid, unit_id=unit_a)
    first = create_outsourced_company_unit_link(conn, entity_id, cid, unit_b, 1)
    second = create_outsourced_company_unit_link(conn, entity_id, cid, unit_b, 1)
    assert first == second
    rows = conn.execute(
        'SELECT COUNT(*) AS n FROM outsourced_company_unit_links WHERE outsourced_company_id = ? AND unit_id = ?',
        (entity_id, unit_b),
    ).fetchone()
    assert rows['n'] == 1


def test_set_outsourced_company_unit_link_status_activate_deactivate():
    conn = _PgStyleConn(_conn())
    cid = _seed_company(conn)
    _bootstrap(conn)
    unit_a = _seed_unit(conn, cid, 'Unidade A')
    entity_id = create_outsourced_company(conn, {'legal_name': 'Alfa'}, cid, unit_id=unit_a)
    link = fetch_outsourced_company_unit_link(conn, entity_id, unit_a)
    set_outsourced_company_unit_link_status(conn, link['id'], cid, 'inactive', 1, reason='Contrato encerrado')
    updated = fetch_outsourced_company_unit_link(conn, entity_id, unit_a)
    assert updated['local_status'] == 'inactive'
    assert updated['deactivation_reason'] == 'Contrato encerrado'
    set_outsourced_company_unit_link_status(conn, link['id'], cid, 'active', 1)
    reactivated = fetch_outsourced_company_unit_link(conn, entity_id, unit_a)
    assert reactivated['local_status'] == 'active'


def test_deactivating_local_link_never_touches_corporate_status():
    """Desativar o vínculo local (ADR-0002 §12.6) nunca é arquivamento
    corporativo — outra Unidade que também vinculou continua enxergando o
    registro corporativo ativo normalmente."""
    conn = _PgStyleConn(_conn())
    cid = _seed_company(conn)
    _bootstrap(conn)
    unit_a = _seed_unit(conn, cid, 'Unidade A')
    unit_b = _seed_unit(conn, cid, 'Unidade B')
    entity_id = create_outsourced_company(conn, {'legal_name': 'Alfa'}, cid, unit_id=unit_a)
    create_outsourced_company_unit_link(conn, entity_id, cid, unit_b, 2)
    link_a = fetch_outsourced_company_unit_link(conn, entity_id, unit_a)
    set_outsourced_company_unit_link_status(conn, link_a['id'], cid, 'inactive', 1)
    entity = get_outsourced_company_by_id(conn, entity_id)
    assert entity['status'] == 'active'
    link_b = fetch_outsourced_company_unit_link(conn, entity_id, unit_b)
    assert link_b['local_status'] == 'active'


# ── Disponibilidade para referência (colaborador terceirizado) ────────────

def test_is_outsourced_company_available_to_unit_tenant_wide_always_true():
    conn = _PgStyleConn(_conn())
    cid = _seed_company(conn)
    _bootstrap(conn)
    unit_a = _seed_unit(conn, cid, 'Unidade A')
    entity_id = create_outsourced_company(conn, {'legal_name': 'Global'}, cid)  # unit_id=None
    entity = get_outsourced_company_by_id(conn, entity_id)
    assert is_outsourced_company_available_to_unit(conn, entity, unit_a) is True


def test_is_outsourced_company_available_to_unit_requires_explicit_link():
    conn = _PgStyleConn(_conn())
    cid = _seed_company(conn)
    _bootstrap(conn)
    unit_a = _seed_unit(conn, cid, 'Unidade A')
    unit_b = _seed_unit(conn, cid, 'Unidade B')
    entity_id = create_outsourced_company(conn, {'legal_name': 'B Co'}, cid, unit_id=unit_b)
    entity = get_outsourced_company_by_id(conn, entity_id)
    assert is_outsourced_company_available_to_unit(conn, entity, unit_a) is False
    create_outsourced_company_unit_link(conn, entity_id, cid, unit_a, 1)
    assert is_outsourced_company_available_to_unit(conn, entity, unit_a) is True


def test_validate_employee_outsourced_reference_rejects_unlinked_company():
    conn = _PgStyleConn(_conn())
    cid = _seed_company(conn)
    _bootstrap(conn)
    unit_a = _seed_unit(conn, cid, 'Unidade A')
    unit_b = _seed_unit(conn, cid, 'Unidade B')
    entity_id = create_outsourced_company(conn, {'legal_name': 'B Co'}, cid, unit_id=unit_b)
    with pytest.raises(ValueError, match='não está vinculada'):
        validate_employee_outsourced_reference(conn, {'outsourced_company_id': entity_id}, cid, unit_id=unit_a)
    create_outsourced_company_unit_link(conn, entity_id, cid, unit_a, 1)
    outsourced_company_id, *_rest = validate_employee_outsourced_reference(
        conn, {'outsourced_company_id': entity_id}, cid, unit_id=unit_a,
    )
    assert outsourced_company_id == entity_id


# ── Lista: linked/available + mascaramento ─────────────────────────────────

def test_fetch_outsourced_companies_available_section_is_masked(scoped_units):
    conn = _PgStyleConn(_conn())
    cid = _seed_company(conn)
    _bootstrap(conn)
    unit_a = _seed_unit(conn, cid, 'Unidade A')
    unit_b = _seed_unit(conn, cid, 'Unidade B')
    actor_a = _seed_unit_scoped_actor(conn, cid, unit_a, role='user', actor_id=1)
    scoped_units[1] = unit_a
    entity_id = create_outsourced_company(
        conn, {'legal_name': 'B Co', 'cnpj': '11.222.333/0001-81'}, cid, unit_id=unit_b,
    )
    data = fetch_outsourced_companies(conn, cid, actor=actor_a)
    assert data['linked'] == []
    assert len(data['available']) == 1
    available = data['available'][0]
    assert available['id'] == entity_id
    assert available['cnpj'] == '11.***.***/****-81'
    assert 'notes' not in available


def test_annotate_outsourced_company_visibility_split_and_local_status(scoped_units):
    conn = _PgStyleConn(_conn())
    cid = _seed_company(conn)
    _bootstrap(conn)
    unit_a = _seed_unit(conn, cid, 'Unidade A')
    entity_id = create_outsourced_company(conn, {'legal_name': 'Alfa'}, cid, unit_id=unit_a)
    companies = [get_outsourced_company_by_id(conn, entity_id)]
    result = annotate_outsourced_company_visibility(conn, companies, unit_a, split=True)
    assert len(result['linked']) == 1
    assert result['linked'][0]['local_status'] == 'active'
    assert result['available'] == []


# ── Busca por nome + duplicidade ────────────────────────────────────────────

def test_search_outsourced_companies_by_name_matches_legal_and_trade_name():
    conn = _PgStyleConn(_conn())
    cid = _seed_company(conn)
    _bootstrap(conn)
    create_outsourced_company(conn, {'legal_name': 'Transforma Terceirizados LTDA', 'trade_name': 'Transforma'}, cid)
    create_outsourced_company(conn, {'legal_name': 'Outra Empresa'}, cid)
    matches = search_outsourced_companies_by_name(conn, cid, 'transforma')
    assert len(matches) == 1
    assert matches[0]['legal_name'] == 'Transforma Terceirizados LTDA'


def test_duplicate_cnpj_raises_with_existing_company_id():
    conn = _PgStyleConn(_conn())
    cid = _seed_company(conn)
    _bootstrap(conn)
    first_id = create_outsourced_company(conn, {'legal_name': 'Alfa', 'cnpj': '11.222.333/0001-81'}, cid)
    with pytest.raises(DuplicateOutsourcedCompanyError) as excinfo:
        create_outsourced_company(conn, {'legal_name': 'Beta', 'cnpj': '11.222.333/0001-81'}, cid)
    assert excinfo.value.existing_company_id == first_id


def test_duplicate_cnpj_allowed_across_different_tenants():
    conn = _PgStyleConn(_conn())
    cid_a = _seed_company(conn, 'Tenant A')
    cid_b = _seed_company(conn, 'Tenant B')
    _bootstrap(conn)
    create_outsourced_company(conn, {'legal_name': 'Alfa', 'cnpj': '11.222.333/0001-81'}, cid_a)
    other_id = create_outsourced_company(conn, {'legal_name': 'Beta', 'cnpj': '11.222.333/0001-81'}, cid_b)
    assert other_id


# ── Trava pós-promoção ──────────────────────────────────────────────────────

def test_corporate_lock_applies_only_after_promotion_to_standard():
    entity_simplified = {'registration_mode': 'simplified'}
    entity_standard = {'registration_mode': 'standard'}
    local_admin = {'role': 'admin'}
    general_admin = {'role': 'general_admin'}
    # Simplificado: ninguém trava.
    ensure_actor_can_edit_outsourced_company_corporate_fields(local_admin, entity_simplified)
    ensure_actor_can_edit_outsourced_company_corporate_fields(general_admin, entity_simplified)
    # Padrão: só quem tem employees:update completo passa.
    with pytest.raises(PermissionError):
        ensure_actor_can_edit_outsourced_company_corporate_fields(local_admin, entity_standard)
    ensure_actor_can_edit_outsourced_company_corporate_fields(general_admin, entity_standard)


def test_corporate_lock_excludes_master_admin_by_doctrine():
    """PAPEIS_E_ATRIBUICOES.md #1: Master é operacional/suporte, nunca
    substitui Geral/Registro em decisão de dado corporativo."""
    entity_standard = {'registration_mode': 'standard'}
    with pytest.raises(PermissionError):
        ensure_actor_can_edit_outsourced_company_corporate_fields({'role': 'master_admin'}, entity_standard)


def test_promote_then_lock_end_to_end():
    conn = _PgStyleConn(_conn())
    cid = _seed_company(conn)
    _bootstrap(conn)
    unit_a = _seed_unit(conn, cid, 'Unidade A')
    entity_id = create_outsourced_company(
        conn, {'legal_name': 'Alfa', 'cnpj': '11.222.333/0001-81'}, cid, unit_id=unit_a,
    )
    promote_outsourced_company(conn, entity_id, cid)
    entity = get_outsourced_company_by_id(conn, entity_id)
    assert entity['registration_mode'] == 'standard'
    with pytest.raises(PermissionError):
        ensure_actor_can_edit_outsourced_company_corporate_fields({'role': 'user'}, entity)
    # Vínculo/escopo continuam liberados (trava é só sobre EDITAR dado
    # corporativo, não sobre ler/gerenciar o vínculo local).
    local_admin = _seed_unit_scoped_actor(conn, cid, unit_a, role='user')
    ensure_actor_outsourced_company_scope(conn, local_admin, entity)


def test_update_outsourced_company_ignores_unit_id_even_when_promoted():
    conn = _PgStyleConn(_conn())
    cid = _seed_company(conn)
    _bootstrap(conn)
    unit_a = _seed_unit(conn, cid, 'Unidade A')
    unit_b = _seed_unit(conn, cid, 'Unidade B')
    entity_id = create_outsourced_company(
        conn, {'legal_name': 'Alfa', 'cnpj': '11.222.333/0001-81'}, cid, unit_id=unit_a,
    )
    promote_outsourced_company(conn, entity_id, cid)
    update_outsourced_company(
        conn, entity_id,
        {'legal_name': 'Alfa Renomeada', 'cnpj': '11.222.333/0001-81', 'unit_id': unit_b, 'registration_mode': 'standard'},
        cid,
    )
    entity = get_outsourced_company_by_id(conn, entity_id)
    assert entity['unit_id'] == unit_a
    assert entity['legal_name'] == 'Alfa Renomeada'


# ── "Solicitar atualização cadastral" ───────────────────────────────────────

def test_update_request_create_fetch_resolve_cycle():
    conn = _PgStyleConn(_conn())
    cid = _seed_company(conn)
    _bootstrap(conn)
    unit_a = _seed_unit(conn, cid, 'Unidade A')
    entity_id = create_outsourced_company(conn, {'legal_name': 'Alfa'}, cid, unit_id=unit_a)
    actor = {'id': 1, 'full_name': 'Gestor A'}
    request_id = create_outsourced_company_update_request(conn, entity_id, cid, unit_a, actor, 'CNPJ mudou')
    pending = fetch_outsourced_company_update_requests(conn, cid, status='pending')
    assert len(pending) == 1
    assert pending[0]['id'] == request_id
    assert pending[0]['message'] == 'CNPJ mudou'
    resolve_outsourced_company_update_request(conn, request_id, cid, 3, 'resolved', notes='Corrigido')
    resolved = get_outsourced_company_update_request_by_id(conn, request_id)
    assert resolved['status'] == 'resolved'
    assert resolved['resolution_notes'] == 'Corrigido'
    assert fetch_outsourced_company_update_requests(conn, cid, status='pending') == []


def test_update_request_requires_non_empty_message():
    conn = _PgStyleConn(_conn())
    cid = _seed_company(conn)
    _bootstrap(conn)
    unit_a = _seed_unit(conn, cid, 'Unidade A')
    entity_id = create_outsourced_company(conn, {'legal_name': 'Alfa'}, cid, unit_id=unit_a)
    with pytest.raises(ValueError):
        create_outsourced_company_update_request(conn, entity_id, cid, unit_a, {'id': 1}, '   ')
