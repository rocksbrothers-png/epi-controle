"""Fase 2 Multi-CNPJ: cabeamento de rastreabilidade jurídica por CNPJ.

Cobre o vínculo do CNPJ derivado do colaborador nas operações:
  - helper compartilhado employee_legal_entity_sql (fonte única do gating);
  - entregas: QR → Entrega → Colaborador → CNPJ → Empresa;
  - unidades: atribuição/validação de legal_entity_id;
  - portal do colaborador: contexto e auditoria com CNPJ/unidade;
  - relatórios: filtro por legal_entity_id.

Todos os pontos degradam graciosamente quando o schema Multi-CNPJ ainda não foi
provisionado (janela de migração / fixtures de schema parcial).
"""

import json
import sqlite3

import pytest

from core.schema import ensure_legal_entities
from modules.deliveries.service import fetch_deliveries
from modules.legal_entities.service import (
    create_legal_entity,
    employee_legal_entity_sql,
    get_default_legal_entity_id,
)
from modules.units.service import create_unit, update_unit

CNPJ_A = '11.222.333/0001-81'
CNPJ_B = '45.723.174/0001-10'


# ── helper compartilhado ──────────────────────────────────────────────────────

def _minimal_conn():
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
            company_id INTEGER NOT NULL, name TEXT, unit_type TEXT,
            city TEXT, notes TEXT DEFAULT ''
        );
        CREATE TABLE employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL, unit_id INTEGER, name TEXT
        );
        """
    )
    conn.execute("INSERT INTO companies (name, legal_name, cnpj) VALUES ('ACME', 'ACME SA', ?)", (CNPJ_A,))
    conn.commit()
    return conn


def test_helper_returns_empty_fragments_on_partial_schema():
    conn = _minimal_conn()  # sem ensure_legal_entities
    select_sql, join_sql = employee_legal_entity_sql(conn)
    assert select_sql == ''
    assert join_sql == ''


def test_helper_returns_fragments_when_schema_ready():
    conn = _minimal_conn()
    ensure_legal_entities(conn)
    select_sql, join_sql = employee_legal_entity_sql(conn)
    assert 'employees.legal_entity_id' in select_sql
    assert 'legal_entity_cnpj' in select_sql
    assert 'LEFT JOIN legal_entities' in join_sql


def test_helper_honours_custom_alias():
    conn = _minimal_conn()
    ensure_legal_entities(conn)
    select_sql, join_sql = employee_legal_entity_sql(conn, employee_alias='e', prefix='cnpj')
    assert 'e.legal_entity_id' in select_sql
    assert 'cnpj_cnpj' in select_sql
    assert 'legal_entities.id = e.legal_entity_id' in join_sql


# ── unidades ──────────────────────────────────────────────────────────────────

def test_create_unit_accepts_legal_entity():
    conn = _minimal_conn()
    ensure_legal_entities(conn)
    entity_id = get_default_legal_entity_id(conn, 1)
    unit_id = create_unit(conn, 1, 'Base Santos', 'base', 'Santos', '', legal_entity_id=entity_id)
    row = conn.execute('SELECT legal_entity_id FROM units WHERE id = ?', (unit_id,)).fetchone()
    assert row['legal_entity_id'] == entity_id


def test_create_unit_rejects_legal_entity_from_other_company():
    conn = _minimal_conn()
    conn.execute("INSERT INTO companies (name, legal_name, cnpj) VALUES ('OUTRA', 'OUTRA SA', ?)", (CNPJ_B,))
    conn.commit()
    ensure_legal_entities(conn)
    other_entity = get_default_legal_entity_id(conn, 2)
    with pytest.raises(ValueError):
        create_unit(conn, 1, 'Base X', 'base', 'X', '', legal_entity_id=other_entity)


def test_create_unit_without_legal_entity_stays_backward_compatible():
    conn = _minimal_conn()
    ensure_legal_entities(conn)
    unit_id = create_unit(conn, 1, 'Base Legada', 'base', 'Rio', '')
    row = conn.execute('SELECT name, legal_entity_id FROM units WHERE id = ?', (unit_id,)).fetchone()
    assert row['name'] == 'Base Legada'
    assert row['legal_entity_id'] is None


def test_update_unit_assigns_legal_entity():
    conn = _minimal_conn()
    ensure_legal_entities(conn)
    unit_id = create_unit(conn, 1, 'Base', 'base', 'Rio', '')
    entity_id = get_default_legal_entity_id(conn, 1)
    update_unit(conn, unit_id, 1, 'Base', 'base', 'Rio', '', legal_entity_id=entity_id)
    row = conn.execute('SELECT legal_entity_id FROM units WHERE id = ?', (unit_id,)).fetchone()
    assert row['legal_entity_id'] == entity_id


def test_create_unit_ignores_legal_entity_on_partial_schema():
    """Sem o schema Multi-CNPJ o parâmetro é ignorado em vez de quebrar."""
    conn = _minimal_conn()
    unit_id = create_unit(conn, 1, 'Base', 'base', 'Rio', '', legal_entity_id=999)
    assert unit_id is not None


# ── entregas: QR → Entrega → Colaborador → CNPJ → Empresa ─────────────────────

def _deliveries_conn(with_legal_entities=True):
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        CREATE TABLE companies (id INTEGER PRIMARY KEY, name TEXT, legal_name TEXT DEFAULT '', cnpj TEXT, logo_type TEXT);
        CREATE TABLE employees (id INTEGER PRIMARY KEY, company_id INTEGER, unit_id INTEGER,
                                employee_id_code TEXT, name TEXT, schedule_type TEXT, tipo_vinculo TEXT);
        CREATE TABLE units (id INTEGER PRIMARY KEY, company_id INTEGER, name TEXT, unit_type TEXT,
                            city TEXT, notes TEXT DEFAULT '');
        CREATE TABLE epis (id INTEGER PRIMARY KEY, name TEXT, purchase_code TEXT, ca TEXT, unit_measure TEXT,
                           epi_validity_date TEXT, manufacture_date TEXT, qr_code_value TEXT);
        CREATE TABLE deliveries (
            id INTEGER PRIMARY KEY, company_id INTEGER, employee_id INTEGER, epi_id INTEGER,
            quantity INTEGER, quantity_label TEXT, sector TEXT, role_name TEXT, delivery_date TEXT,
            next_replacement_date TEXT, notes TEXT, signature_name TEXT, signature_data TEXT,
            signature_at TEXT, signature_comment TEXT, unit_id INTEGER, stock_movement_id INTEGER,
            glove_size TEXT DEFAULT 'N/A', size TEXT DEFAULT 'N/A', uniform_size TEXT DEFAULT 'N/A',
            returned_date TEXT DEFAULT '', returned_condition TEXT DEFAULT '',
            returned_notes TEXT DEFAULT '', return_movement_id INTEGER
        );
        CREATE TABLE epi_stock_items (id INTEGER PRIMARY KEY, delivery_id INTEGER,
                                      glove_size TEXT, size TEXT, uniform_size TEXT);
        CREATE TABLE epi_ficha_items (id INTEGER PRIMARY KEY, delivery_id INTEGER, ficha_period_id INTEGER);
        CREATE TABLE epi_ficha_periods (id INTEGER PRIMARY KEY, employee_id INTEGER, period_start TEXT,
                                        period_end TEXT, status TEXT);

        INSERT INTO companies (id, name, legal_name, cnpj, logo_type) VALUES (1, 'ACME', 'ACME SA', '11.222.333/0001-81', '');
        INSERT INTO units (id, company_id, name, unit_type, city) VALUES (3, 1, 'Base Santos', 'base', 'Santos');
        INSERT INTO employees (id, company_id, unit_id, employee_id_code, name, schedule_type, tipo_vinculo)
        VALUES (2, 1, 3, 'E-001', 'Ana', 'offshore', 'CLT');
        INSERT INTO epis (id, name, purchase_code, ca, unit_measure, epi_validity_date, manufacture_date, qr_code_value)
        VALUES (4, 'Luva', 'PC-1', 'CA-1', 'par', '2027-01-01', '2026-01-01', 'QR-XYZ');
        INSERT INTO deliveries (id, company_id, employee_id, epi_id, quantity, quantity_label, sector,
                                role_name, delivery_date, next_replacement_date, notes, signature_name,
                                signature_data, signature_at, signature_comment, unit_id, stock_movement_id)
        VALUES (5, 1, 2, 4, 1, 'unidade', 'Operação', 'Técnica', '2026-05-01', '2026-06-01', '', '', '', '', '', 3, NULL);
        """
    )
    conn.commit()
    if with_legal_entities:
        ensure_legal_entities(conn)
    return conn


def test_fetch_deliveries_exposes_legal_entity_chain():
    """A entrega deriva o CNPJ do colaborador — sem duplicar o dado."""
    conn = _deliveries_conn()
    items = fetch_deliveries(conn)
    assert len(items) == 1
    item = items[0]
    # cadeia completa de rastreabilidade
    assert item['qr_code_value'] == 'QR-XYZ'          # QR
    assert item['employee_name'] == 'Ana'             # Colaborador
    assert item['legal_entity_cnpj'] == CNPJ_A        # CNPJ
    assert item['company_name'] == 'ACME'             # Empresa
    assert item['legal_entity_id'] == get_default_legal_entity_id(conn, 1)


def test_fetch_deliveries_reflects_employee_specific_cnpj():
    """Colaborador vinculado a um CNPJ não-matriz reflete esse CNPJ na entrega."""
    conn = _deliveries_conn()
    filial_id = create_legal_entity(
        conn, {'cnpj': CNPJ_B, 'legal_name': 'ACME Filial RJ', 'entity_type': 'filial', 'uf': 'RJ'}, 1
    )
    conn.execute('UPDATE employees SET legal_entity_id = ? WHERE id = 2', (filial_id,))
    conn.commit()
    item = fetch_deliveries(conn)[0]
    assert item['legal_entity_cnpj'] == CNPJ_B
    assert item['legal_entity_name'] == 'ACME Filial RJ'


def test_fetch_deliveries_works_without_legal_entities_schema():
    """Retrocompatibilidade: sem o schema Multi-CNPJ a consulta segue válida."""
    conn = _deliveries_conn(with_legal_entities=False)
    items = fetch_deliveries(conn)
    assert len(items) == 1
    assert items[0]['employee_name'] == 'Ana'
    assert 'legal_entity_cnpj' not in items[0]


# ── portal do colaborador: auditoria com CNPJ ────────────────────────────────

def test_portal_audit_records_legal_entity_and_unit():
    from modules.portal.service import register_employee_portal_audit
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        CREATE TABLE employee_portal_audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT, company_id INTEGER, employee_id INTEGER,
            portal_link_id INTEGER, token_hash TEXT, action TEXT, ip_address TEXT,
            user_agent TEXT, payload TEXT, created_at TEXT
        );
        """
    )
    context = {
        'company_id': 1, 'employee_id': 2, 'portal_link_id': 7, 'token': 'tok',
        'legal_entity_id': 9, 'legal_entity_cnpj': CNPJ_A, 'unit_id': 3,
    }
    register_employee_portal_audit(conn, context, 'view_ficha', payload={'origin': 'app'})
    row = conn.execute('SELECT payload FROM employee_portal_audit_logs').fetchone()
    payload = json.loads(row['payload'])
    assert payload['legal_entity_id'] == 9
    assert payload['company_tax_id'] == CNPJ_A
    assert payload['unit_id'] == 3
    assert payload['origin'] == 'app'  # payload original preservado


def test_portal_audit_without_legal_entity_keeps_original_payload():
    from modules.portal.service import register_employee_portal_audit
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        CREATE TABLE employee_portal_audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT, company_id INTEGER, employee_id INTEGER,
            portal_link_id INTEGER, token_hash TEXT, action TEXT, ip_address TEXT,
            user_agent TEXT, payload TEXT, created_at TEXT
        );
        """
    )
    context = {'company_id': 1, 'employee_id': 2, 'portal_link_id': 7, 'token': 'tok'}
    register_employee_portal_audit(conn, context, 'login', payload={'origin': 'web'})
    payload = json.loads(conn.execute('SELECT payload FROM employee_portal_audit_logs').fetchone()['payload'])
    assert payload == {'origin': 'web'}


# ── relatórios: filtro por CNPJ ───────────────────────────────────────────────

def test_report_filters_accept_legal_entity_id():
    from modules.reports.service import normalize_report_filters
    filters = normalize_report_filters({'legal_entity_id': '12'})
    assert filters['legal_entity_id'] == 12


def test_report_filters_reject_non_numeric_legal_entity_id():
    from modules.reports.service import InvalidQueryParamError, normalize_report_filters
    with pytest.raises(InvalidQueryParamError):
        normalize_report_filters({'legal_entity_id': 'abc'})
