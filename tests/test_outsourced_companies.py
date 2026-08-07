"""Cadastro Simplificado de Terceirizados e Prestadores (ADR-014).

Cobre:
  - ensure_outsourced_companies: criação idempotente de outsourced_companies
    e service_contracts, colunas novas em employees;
  - service: validação de CNPJ (opcional no Simplificado, obrigatório no
    Padrão/promoção), unicidade por tenant (company_id + cnpj_normalized),
    normalização de company_kind/epi_responsibility/registration_mode/status;
  - isolamento multi-tenant: uma empresa terceirizada de um tenant nunca é
    visível/editável por outro, mesmo com CNPJ repetido entre tenants;
  - contratos: vínculo com a empresa terceirizada do mesmo tenant, override
    de responsabilidade pelo EPI com motivo obrigatório;
  - resolve_effective_epi_responsibility: precedência colaborador > contrato
    > empresa > 'Não Definido'.
"""

import sqlite3

import pytest

from core.schema import ensure_legal_entities, ensure_outsourced_companies, ensure_outsourced_company_unit_links
from modules.outsourced_companies.service import (
    COMPANY_KINDS,
    create_outsourced_company,
    create_service_contract,
    fetch_outsourced_companies,
    get_outsourced_company_by_id,
    normalize_company_kind,
    normalize_registration_mode,
    normalize_registration_status,
    outsourced_companies_ready,
    promote_outsourced_company,
    resolve_effective_epi_responsibility,
    update_outsourced_company,
)

CNPJ_A = '11.222.333/0001-81'
CNPJ_B = '45.723.174/0001-10'


def _conn():
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        CREATE TABLE companies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT, legal_name TEXT DEFAULT '', cnpj TEXT
        );
        CREATE TABLE units (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL, name TEXT
        );
        CREATE TABLE employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL, unit_id INTEGER, name TEXT
        );
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT, company_id INTEGER, role TEXT
        );
        """
    )
    return conn


def _seed_company(conn, name='ACME', cnpj='00.000.000/0001-00'):
    cur = conn.execute('INSERT INTO companies (name, legal_name, cnpj) VALUES (?, ?, ?)', (name, name, cnpj))
    conn.commit()
    return int(cur.lastrowid)


def _bootstrap(conn):
    # ensure_outsourced_companies depende de employees.legal_entity_id/etc.
    # criados por ensure_legal_entities — mesma ordem do init_db real.
    ensure_legal_entities(conn)
    ensure_outsourced_companies(conn)
    ensure_outsourced_company_unit_links(conn)


# ── migração ────────────────────────────────────────────────────────────────

def test_ensure_outsourced_companies_creates_tables_and_columns():
    conn = _conn()
    _seed_company(conn)
    _bootstrap(conn)

    assert outsourced_companies_ready(conn)
    cols = {row[1] for row in conn.execute('PRAGMA table_info(employees)').fetchall()}
    assert 'outsourced_company_id' in cols
    assert 'service_contract_id' in cols
    assert 'epi_responsibility_override' in cols
    assert 'epi_responsibility_override_reason' in cols

    oc_cols = {row[1] for row in conn.execute('PRAGMA table_info(outsourced_companies)').fetchall()}
    assert {'company_id', 'cnpj_normalized', 'company_kind', 'epi_responsibility',
            'registration_mode', 'registration_status'} <= oc_cols

    sc_cols = {row[1] for row in conn.execute('PRAGMA table_info(service_contracts)').fetchall()}
    assert {'outsourced_company_id', 'epi_responsibility_override', 'override_reason'} <= sc_cols


def test_ensure_outsourced_companies_is_idempotent():
    conn = _conn()
    _seed_company(conn)
    _bootstrap(conn)
    _bootstrap(conn)  # não deve levantar exceção nem duplicar colunas


# ── normalização ────────────────────────────────────────────────────────────

def test_normalize_company_kind_defaults_to_outsourced_for_unknown_value():
    assert normalize_company_kind('nonsense') == 'outsourced'
    assert normalize_company_kind('service_provider') == 'service_provider'
    assert set(COMPANY_KINDS) == {'outsourced', 'service_provider', 'other_contracted'}


def test_normalize_registration_mode_and_status_defaults():
    assert normalize_registration_mode('bogus') == 'simplified'
    assert normalize_registration_mode('standard') == 'standard'
    assert normalize_registration_status('bogus') == 'pending_completion'
    assert normalize_registration_status('complete') == 'complete'


# ── validação / criação ─────────────────────────────────────────────────────

def test_create_outsourced_company_allows_empty_cnpj_in_simplified_mode():
    conn = _conn()
    cid = _seed_company(conn)
    _bootstrap(conn)
    entity_id = create_outsourced_company(conn, {'legal_name': 'Terceirizada X'}, cid)
    entity = get_outsourced_company_by_id(conn, entity_id)
    assert entity['cnpj'] == ''
    assert entity['registration_mode'] == 'simplified'
    assert entity['registration_status'] == 'pending_completion'
    assert entity['company_kind'] == 'outsourced'
    assert entity['epi_responsibility'] == 'Conforme Contrato'


def test_create_outsourced_company_requires_legal_name():
    conn = _conn()
    cid = _seed_company(conn)
    _bootstrap(conn)
    with pytest.raises(ValueError):
        create_outsourced_company(conn, {'legal_name': '  '}, cid)


def test_standard_registration_mode_requires_cnpj():
    conn = _conn()
    cid = _seed_company(conn)
    _bootstrap(conn)
    with pytest.raises(ValueError):
        create_outsourced_company(
            conn, {'legal_name': 'Prestadora Y', 'registration_mode': 'standard'}, cid,
        )


def test_invalid_cnpj_is_rejected():
    conn = _conn()
    cid = _seed_company(conn)
    _bootstrap(conn)
    with pytest.raises(ValueError):
        create_outsourced_company(conn, {'legal_name': 'X', 'cnpj': '11.111.111/1111-11'}, cid)


def test_duplicate_cnpj_within_same_tenant_is_rejected():
    conn = _conn()
    cid = _seed_company(conn)
    _bootstrap(conn)
    create_outsourced_company(conn, {'legal_name': 'Terceirizada X', 'cnpj': CNPJ_A}, cid)
    with pytest.raises(ValueError):
        create_outsourced_company(conn, {'legal_name': 'Terceirizada X (dup)', 'cnpj': CNPJ_A}, cid)


def test_same_cnpj_allowed_across_different_tenants():
    # Isolamento multi-tenant: o mesmo CNPJ de terceirizada pode aparecer em
    # dois clientes distintos sem colisão — a unicidade é composta com
    # company_id, nunca global.
    conn = _conn()
    cid_a = _seed_company(conn, name='Tenant A')
    cid_b = _seed_company(conn, name='Tenant B')
    _bootstrap(conn)
    id_a = create_outsourced_company(conn, {'legal_name': 'Terceirizada X', 'cnpj': CNPJ_A}, cid_a)
    id_b = create_outsourced_company(conn, {'legal_name': 'Terceirizada X', 'cnpj': CNPJ_A}, cid_b)
    assert id_a != id_b


def test_multiple_companies_without_cnpj_are_allowed_in_same_tenant():
    # Regressão: a unicidade (company_id, cnpj_normalized) é um índice
    # PARCIAL (WHERE cnpj_normalized <> ''), não um UNIQUE de tabela — senão
    # a segunda empresa terceirizada cadastrada sem CNPJ no Cadastro
    # Simplificado (caso comum: serviço emergencial) colidiria com a
    # primeira, já que as duas teriam cnpj_normalized = ''.
    conn = _conn()
    cid = _seed_company(conn)
    _bootstrap(conn)
    id_1 = create_outsourced_company(conn, {'legal_name': 'Terceirizada 1'}, cid)
    id_2 = create_outsourced_company(conn, {'legal_name': 'Terceirizada 2'}, cid)
    assert id_1 != id_2


def test_unknown_company_kind_and_epi_responsibility_fall_back_to_safe_defaults():
    conn = _conn()
    cid = _seed_company(conn)
    _bootstrap(conn)
    entity_id = create_outsourced_company(
        conn, {'legal_name': 'X', 'company_kind': 'nao_existe', 'epi_responsibility': 'nao_existe'}, cid,
    )
    entity = get_outsourced_company_by_id(conn, entity_id)
    assert entity['company_kind'] == 'outsourced'
    assert entity['epi_responsibility'] == 'Conforme Contrato'


# ── isolamento multi-tenant (fetch/update/promote) ─────────────────────────

def test_fetch_outsourced_companies_is_scoped_by_tenant():
    conn = _conn()
    cid_a = _seed_company(conn, name='Tenant A')
    cid_b = _seed_company(conn, name='Tenant B')
    _bootstrap(conn)
    create_outsourced_company(conn, {'legal_name': 'Empresa A'}, cid_a)
    create_outsourced_company(conn, {'legal_name': 'Empresa B'}, cid_b)
    result_a = fetch_outsourced_companies(conn, cid_a)
    assert [r['legal_name'] for r in result_a['linked']] == ['Empresa A']
    assert result_a['available'] == []


def test_update_outsourced_company_does_not_cross_tenant_boundary():
    conn = _conn()
    cid_a = _seed_company(conn, name='Tenant A')
    cid_b = _seed_company(conn, name='Tenant B')
    _bootstrap(conn)
    entity_id = create_outsourced_company(conn, {'legal_name': 'Empresa A'}, cid_a)
    # Tentativa de update usando o company_id do outro tenant: WHERE não bate
    # nenhuma linha — atualização silenciosamente não aplicada, sem vazar dado.
    update_outsourced_company(conn, entity_id, {'legal_name': 'Hackeada'}, cid_b)
    entity = get_outsourced_company_by_id(conn, entity_id)
    assert entity['legal_name'] == 'Empresa A'


def test_promote_rejects_cross_tenant_id():
    conn = _conn()
    cid_a = _seed_company(conn, name='Tenant A')
    cid_b = _seed_company(conn, name='Tenant B')
    _bootstrap(conn)
    entity_id = create_outsourced_company(conn, {'legal_name': 'Empresa A', 'cnpj': CNPJ_A}, cid_a)
    with pytest.raises(ValueError):
        promote_outsourced_company(conn, entity_id, cid_b)


def test_promote_requires_cnpj_and_updates_registration_fields():
    conn = _conn()
    cid = _seed_company(conn)
    _bootstrap(conn)
    entity_id = create_outsourced_company(conn, {'legal_name': 'Empresa A'}, cid)
    with pytest.raises(ValueError):
        promote_outsourced_company(conn, entity_id, cid)  # sem CNPJ

    update_outsourced_company(conn, entity_id, {'legal_name': 'Empresa A', 'cnpj': CNPJ_A}, cid)
    promote_outsourced_company(conn, entity_id, cid)
    entity = get_outsourced_company_by_id(conn, entity_id)
    assert entity['registration_mode'] == 'standard'
    assert entity['registration_status'] == 'complete'
    assert entity['promoted_at']


# ── contratos ────────────────────────────────────────────────────────────────

def test_create_service_contract_requires_reason_when_overriding_responsibility():
    conn = _conn()
    cid = _seed_company(conn)
    _bootstrap(conn)
    entity_id = create_outsourced_company(conn, {'legal_name': 'Empresa A'}, cid)
    with pytest.raises(ValueError):
        create_service_contract(
            conn, {'epi_responsibility_override': 'Empresa Contratante'}, cid, entity_id,
        )
    # Com motivo, funciona.
    contract_id = create_service_contract(
        conn,
        {'epi_responsibility_override': 'Empresa Contratante', 'override_reason': 'Acordo pontual'},
        cid, entity_id,
    )
    assert contract_id


def test_create_service_contract_rejects_outsourced_company_from_another_tenant():
    conn = _conn()
    cid_a = _seed_company(conn, name='Tenant A')
    cid_b = _seed_company(conn, name='Tenant B')
    _bootstrap(conn)
    entity_id = create_outsourced_company(conn, {'legal_name': 'Empresa A'}, cid_a)
    with pytest.raises(ValueError):
        create_service_contract(conn, {}, cid_b, entity_id)


# ── resolução de responsabilidade efetiva ──────────────────────────────────

def test_resolve_effective_epi_responsibility_precedence():
    conn = _conn()
    cid = _seed_company(conn)
    _bootstrap(conn)
    entity_id = create_outsourced_company(
        conn, {'legal_name': 'Empresa A', 'epi_responsibility': 'Empresa Terceirizada'}, cid,
    )
    contract_id = create_service_contract(
        conn,
        {'epi_responsibility_override': 'Responsabilidade Compartilhada', 'override_reason': 'Obra específica'},
        cid, entity_id,
    )

    # Sem contrato nem exceção individual: usa o default da empresa.
    assert resolve_effective_epi_responsibility(
        conn, outsourced_company_id=entity_id,
    ) == 'Empresa Terceirizada'

    # Com contrato (sem exceção individual): usa o override do contrato.
    assert resolve_effective_epi_responsibility(
        conn, outsourced_company_id=entity_id, service_contract_id=contract_id,
    ) == 'Responsabilidade Compartilhada'

    # Exceção individual do colaborador vence tudo.
    assert resolve_effective_epi_responsibility(
        conn, outsourced_company_id=entity_id, service_contract_id=contract_id,
        employee_override='Empresa Contratante',
    ) == 'Empresa Contratante'


def test_resolve_effective_epi_responsibility_defaults_to_not_defined_without_company():
    conn = _conn()
    _seed_company(conn)
    _bootstrap(conn)
    assert resolve_effective_epi_responsibility(conn) == 'Não Definido'
