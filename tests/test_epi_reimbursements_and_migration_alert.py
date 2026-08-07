"""Ressarcimento de EPI + alerta de sugestão de migração — PR 6 (ADR-0002).

Cobre:
  - ensure_epi_reimbursements: migração idempotente, unicidade por entrega
    (uma entrega tem no máximo um registro de ressarcimento);
  - validate_reimbursement_payload / create_reimbursement: entrega e empresa
    terceirizada precisam pertencer ao mesmo tenant; total_value calculado
    automaticamente quando não informado;
  - update_reimbursement_status: normaliza para o enum de 8 estados,
    nunca cobrança/integração automática — só troca a coluna status;
  - fetch_reimbursements: escopado por tenant, filtrável por empresa/status;
  - get_simplified_duration_threshold_days: default de sistema (30 dias),
    configurável por tenant via configuration_framework;
  - fetch_migration_suggestions: sugere promoção só para empresas
    Simplificado além do limiar, nunca bloqueia nada.
"""

import sqlite3

import pytest

from core.schema import ensure_epi_reimbursements, ensure_legal_entities, ensure_outsourced_companies, ensure_outsourced_company_unit_links
from modules.outsourced_companies.service import (
    REIMBURSEMENT_STATUSES,
    create_outsourced_company,
    create_reimbursement,
    fetch_migration_suggestions,
    fetch_reimbursements,
    get_reimbursement_by_id,
    get_simplified_duration_threshold_days,
    normalize_reimbursement_status,
    update_reimbursement_status,
)
from modules.settings.service import save_configuration_framework


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
        CREATE TABLE deliveries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL, employee_id INTEGER, epi_id INTEGER, quantity INTEGER
        );
        CREATE TABLE app_meta (
            key TEXT PRIMARY KEY,
            value TEXT
        );
        """
    )
    return conn


def _seed_company(conn, name='ACME', cnpj='00.000.000/0001-00'):
    cur = conn.execute('INSERT INTO companies (name, legal_name, cnpj) VALUES (?, ?, ?)', (name, name, cnpj))
    conn.commit()
    return int(cur.lastrowid)


def _seed_delivery(conn, company_id, quantity=1):
    cur = conn.execute(
        'INSERT INTO deliveries (company_id, employee_id, epi_id, quantity) VALUES (?, 1, 1, ?)',
        (company_id, quantity),
    )
    conn.commit()
    return int(cur.lastrowid)


def _bootstrap(conn):
    ensure_legal_entities(conn)
    ensure_outsourced_companies(conn)
    ensure_outsourced_company_unit_links(conn)
    ensure_epi_reimbursements(conn)


# ── migração ────────────────────────────────────────────────────────────────

def test_ensure_epi_reimbursements_creates_table_idempotently():
    conn = _conn()
    _seed_company(conn)
    _bootstrap(conn)
    _bootstrap(conn)  # idempotente
    cols = {row[1] for row in conn.execute('PRAGMA table_info(epi_reimbursements)').fetchall()}
    assert {'company_id', 'delivery_id', 'outsourced_company_id', 'unit_cost', 'quantity',
            'total_value', 'reason', 'contract_ref', 'status'} <= cols


def test_one_reimbursement_per_delivery():
    conn = _conn()
    cid = _seed_company(conn)
    _bootstrap(conn)
    oc_id = create_outsourced_company(conn, {'legal_name': 'Terceirizada X'}, cid)
    delivery_id = _seed_delivery(conn, cid)
    create_reimbursement(conn, {'delivery_id': delivery_id, 'outsourced_company_id': oc_id}, cid)
    with pytest.raises(sqlite3.IntegrityError):
        create_reimbursement(conn, {'delivery_id': delivery_id, 'outsourced_company_id': oc_id}, cid)


# ── validação / criação ─────────────────────────────────────────────────────

def test_create_reimbursement_computes_total_value_from_unit_cost_and_quantity():
    conn = _conn()
    cid = _seed_company(conn)
    _bootstrap(conn)
    oc_id = create_outsourced_company(conn, {'legal_name': 'Terceirizada X'}, cid)
    delivery_id = _seed_delivery(conn, cid)
    reimbursement_id = create_reimbursement(
        conn, {'delivery_id': delivery_id, 'outsourced_company_id': oc_id, 'unit_cost': 12.5, 'quantity': 3}, cid,
    )
    reimbursement = get_reimbursement_by_id(conn, reimbursement_id)
    assert reimbursement['total_value'] == 37.5
    assert reimbursement['status'] == 'Pendente de Análise'


def test_create_reimbursement_rejects_delivery_from_another_tenant():
    conn = _conn()
    cid_a = _seed_company(conn, name='Tenant A')
    cid_b = _seed_company(conn, name='Tenant B')
    _bootstrap(conn)
    oc_id = create_outsourced_company(conn, {'legal_name': 'Terceirizada X'}, cid_a)
    delivery_id_b = _seed_delivery(conn, cid_b)
    with pytest.raises(ValueError):
        create_reimbursement(conn, {'delivery_id': delivery_id_b, 'outsourced_company_id': oc_id}, cid_a)


def test_create_reimbursement_rejects_outsourced_company_from_another_tenant():
    conn = _conn()
    cid_a = _seed_company(conn, name='Tenant A')
    cid_b = _seed_company(conn, name='Tenant B')
    _bootstrap(conn)
    oc_id_b = create_outsourced_company(conn, {'legal_name': 'Terceirizada de B'}, cid_b)
    delivery_id_a = _seed_delivery(conn, cid_a)
    with pytest.raises(ValueError):
        create_reimbursement(conn, {'delivery_id': delivery_id_a, 'outsourced_company_id': oc_id_b}, cid_a)


def test_create_reimbursement_requires_delivery_and_outsourced_company():
    conn = _conn()
    cid = _seed_company(conn)
    _bootstrap(conn)
    oc_id = create_outsourced_company(conn, {'legal_name': 'Terceirizada X'}, cid)
    delivery_id = _seed_delivery(conn, cid)
    with pytest.raises(ValueError):
        create_reimbursement(conn, {'outsourced_company_id': oc_id}, cid)
    with pytest.raises(ValueError):
        create_reimbursement(conn, {'delivery_id': delivery_id}, cid)


# ── status ──────────────────────────────────────────────────────────────────

def test_normalize_reimbursement_status_defaults_to_not_applicable():
    assert normalize_reimbursement_status('lixo') == 'Não Aplicável'
    assert normalize_reimbursement_status('Ressarcida') == 'Ressarcida'
    assert set(REIMBURSEMENT_STATUSES) == {
        'Não Aplicável', 'Pendente de Análise', 'Passível de Ressarcimento', 'Apta para Cobrança',
        'Incluída em Relatório', 'Ressarcida', 'Contestada', 'Dispensada',
    }


def test_update_reimbursement_status_is_scoped_by_tenant():
    conn = _conn()
    cid_a = _seed_company(conn, name='Tenant A')
    cid_b = _seed_company(conn, name='Tenant B')
    _bootstrap(conn)
    oc_id = create_outsourced_company(conn, {'legal_name': 'Terceirizada X'}, cid_a)
    delivery_id = _seed_delivery(conn, cid_a)
    reimbursement_id = create_reimbursement(conn, {'delivery_id': delivery_id, 'outsourced_company_id': oc_id}, cid_a)

    # tentativa com company_id de outro tenant não aplica (WHERE não bate)
    update_reimbursement_status(conn, reimbursement_id, cid_b, 'Ressarcida')
    unchanged = get_reimbursement_by_id(conn, reimbursement_id)
    assert unchanged['status'] == 'Pendente de Análise'

    update_reimbursement_status(conn, reimbursement_id, cid_a, 'Ressarcida')
    updated = get_reimbursement_by_id(conn, reimbursement_id)
    assert updated['status'] == 'Ressarcida'


# ── fetch escopado ──────────────────────────────────────────────────────────

def test_fetch_reimbursements_is_scoped_and_filterable():
    conn = _conn()
    cid_a = _seed_company(conn, name='Tenant A')
    cid_b = _seed_company(conn, name='Tenant B')
    _bootstrap(conn)
    oc_id_1 = create_outsourced_company(conn, {'legal_name': 'Terceirizada 1'}, cid_a)
    oc_id_2 = create_outsourced_company(conn, {'legal_name': 'Terceirizada 2'}, cid_a)
    create_outsourced_company(conn, {'legal_name': 'Terceirizada de B'}, cid_b)

    d1, d2, d3 = _seed_delivery(conn, cid_a), _seed_delivery(conn, cid_a), _seed_delivery(conn, cid_b)
    create_reimbursement(conn, {'delivery_id': d1, 'outsourced_company_id': oc_id_1}, cid_a)
    create_reimbursement(conn, {'delivery_id': d2, 'outsourced_company_id': oc_id_2, 'status': 'Ressarcida'}, cid_a)

    all_a = fetch_reimbursements(conn, cid_a)
    assert len(all_a) == 2

    only_oc1 = fetch_reimbursements(conn, cid_a, outsourced_company_id=oc_id_1)
    assert len(only_oc1) == 1

    only_reimbursed = fetch_reimbursements(conn, cid_a, status='Ressarcida')
    assert len(only_reimbursed) == 1
    assert only_reimbursed[0]['outsourced_company_id'] == oc_id_2


# ── limiar configurável (alerta de migração) ────────────────────────────────

def test_default_threshold_is_30_days_when_not_configured():
    conn = _conn()
    cid = _seed_company(conn)
    _bootstrap(conn)
    assert get_simplified_duration_threshold_days(conn, cid) == 30


def test_configured_threshold_overrides_default():
    conn = _conn()
    cid = _seed_company(conn)
    _bootstrap(conn)
    save_configuration_framework(conn, cid, {'outsourced_simplified_duration_threshold_days': 7})
    assert get_simplified_duration_threshold_days(conn, cid) == 7


# ── sugestão de migração ────────────────────────────────────────────────────

def test_migration_suggestions_only_lists_simplified_past_threshold():
    conn = _conn()
    cid = _seed_company(conn)
    _bootstrap(conn)
    save_configuration_framework(conn, cid, {'outsourced_simplified_duration_threshold_days': 0})

    recent_id = create_outsourced_company(conn, {'legal_name': 'Recem Cadastrada'}, cid)
    standard_id = create_outsourced_company(
        conn, {'legal_name': 'Ja Padrao', 'cnpj': '11.222.333/0001-81', 'registration_mode': 'standard'}, cid,
    )

    suggestions = fetch_migration_suggestions(conn, cid)
    suggested_ids = {s['outsourced_company_id'] for s in suggestions}
    assert recent_id in suggested_ids     # simplificado, limiar 0 dias -> sempre sugere
    assert standard_id not in suggested_ids  # já é Padrão, não entra na lista


def test_migration_suggestions_excludes_archived():
    conn = _conn()
    cid = _seed_company(conn)
    _bootstrap(conn)
    save_configuration_framework(conn, cid, {'outsourced_simplified_duration_threshold_days': 0})
    from modules.outsourced_companies.service import update_outsourced_company
    oc_id = create_outsourced_company(conn, {'legal_name': 'Arquivada'}, cid)
    update_outsourced_company(conn, oc_id, {'legal_name': 'Arquivada', 'registration_status': 'archived'}, cid)

    suggestions = fetch_migration_suggestions(conn, cid)
    assert oc_id not in {s['outsourced_company_id'] for s in suggestions}


def test_migration_suggestions_is_scoped_by_tenant():
    conn = _conn()
    cid_a = _seed_company(conn, name='Tenant A')
    cid_b = _seed_company(conn, name='Tenant B')
    _bootstrap(conn)
    save_configuration_framework(conn, cid_a, {'outsourced_simplified_duration_threshold_days': 0})
    create_outsourced_company(conn, {'legal_name': 'Empresa de B'}, cid_b)

    suggestions_a = fetch_migration_suggestions(conn, cid_a)
    assert suggestions_a == []
