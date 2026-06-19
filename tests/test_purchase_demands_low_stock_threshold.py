"""Regra de Demandas Pendentes vs. card "Estoque baixo" do dashboard.

Causa raiz investigada: a LUVA CONTRA IMPACTO (estoque 10 / mínimo 10) aparecia
no card "Estoque baixo da unidade" (que usa `stock <= minimum`) mas NÃO em
Demandas Pendentes, porque `fetch_purchase_demands` usava `quantity < minimum`
(estrito). Agora ambos usam `<=` (ponto de reposição = no mínimo ou abaixo).
"""

import sqlite3

import pytest

from modules.purchases.service import fetch_purchase_demands


def _conn():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        CREATE TABLE companies (id INTEGER PRIMARY KEY, name TEXT);
        CREATE TABLE units (id INTEGER PRIMARY KEY, name TEXT);
        CREATE TABLE employees (id INTEGER PRIMARY KEY, name TEXT, sector TEXT, role_name TEXT);
        CREATE TABLE epis (
            id INTEGER PRIMARY KEY, name TEXT, ca TEXT, unit_measure TEXT, manufacturer TEXT,
            supplier_company TEXT, sector TEXT, glove_size TEXT, size TEXT, uniform_size TEXT,
            active INTEGER, minimum_stock INTEGER);
        CREATE TABLE unit_epi_stock (
            company_id INTEGER, unit_id INTEGER, epi_id INTEGER, quantity INTEGER);
        CREATE TABLE epi_requests (
            id INTEGER PRIMARY KEY, company_id INTEGER, unit_id INTEGER, employee_id INTEGER,
            epi_id INTEGER, quantity INTEGER, glove_size TEXT, size TEXT, uniform_size TEXT,
            requested_at TEXT, status TEXT);
        CREATE TABLE epi_stock_items (
            company_id INTEGER, unit_id INTEGER, epi_id INTEGER,
            glove_size TEXT, size TEXT, uniform_size TEXT, status TEXT);
        INSERT INTO companies VALUES (2, 'Norskan Offshore');
        INSERT INTO units VALUES (4, 'Skandi Paraty');
        """
    )
    return conn


def _add_epi(conn, epi_id, minimum, quantity, active=1, name=None):
    conn.execute(
        "INSERT INTO epis (id, name, ca, unit_measure, manufacturer, supplier_company, sector, "
        "glove_size, size, uniform_size, active, minimum_stock) "
        "VALUES (?, ?, 'CA1', 'par', 'Fab', 'Forn', 'Operação', 'N/A', 'N/A', 'N/A', ?, ?)",
        (epi_id, name or f"EPI {epi_id}", active, minimum),
    )
    conn.execute(
        "INSERT INTO unit_epi_stock (company_id, unit_id, epi_id, quantity) VALUES (2, 4, ?, ?)",
        (epi_id, quantity),
    )
    conn.commit()


def _demand_epi_ids(conn):
    demands = fetch_purchase_demands(conn, company_id=2, scope_unit_id=4)
    return {int(d["epi_id"]) for d in demands if d.get("demand_type") == "low_stock"}


def test_item_at_exactly_minimum_is_a_pending_demand():
    conn = _conn()
    _add_epi(conn, 26, minimum=10, quantity=10, name="LUVA CONTRA IMPACTO")
    assert 26 in _demand_epi_ids(conn), "estoque == mínimo (10/10) deve gerar demanda pendente"


def test_item_below_minimum_is_a_pending_demand():
    conn = _conn()
    _add_epi(conn, 27, minimum=10, quantity=5)
    assert 27 in _demand_epi_ids(conn)


def test_item_above_minimum_is_not_a_demand():
    conn = _conn()
    _add_epi(conn, 28, minimum=10, quantity=15)
    assert 28 not in _demand_epi_ids(conn)


def test_inactive_item_at_minimum_is_not_a_demand():
    conn = _conn()
    _add_epi(conn, 29, minimum=10, quantity=10, active=0)
    assert 29 not in _demand_epi_ids(conn)


def test_quantity_requested_is_at_least_one_at_minimum():
    conn = _conn()
    _add_epi(conn, 30, minimum=10, quantity=10)
    demands = fetch_purchase_demands(conn, company_id=2, scope_unit_id=4)
    luva = next(d for d in demands if int(d["epi_id"]) == 30)
    assert int(luva["quantity_requested"]) >= 1


def _add_employee_request(conn, req_id, epi_id, status, employee_id=5):
    conn.execute(
        "INSERT OR IGNORE INTO employees (id, name, sector, role_name) VALUES (?, 'Maria', 'Operação', 'Operadora')",
        (employee_id,),
    )
    # EPI referenciado pela solicitação (JOIN epis na query de solicitações)
    conn.execute(
        "INSERT OR IGNORE INTO epis (id, name, ca, unit_measure, manufacturer, supplier_company, sector, "
        "glove_size, size, uniform_size, active, minimum_stock) "
        "VALUES (?, 'EPI Solic', 'CA9', 'un', 'Fab', 'Forn', 'Operação', 'N/A', 'N/A', 'N/A', 1, 999)",
        (epi_id,),
    )
    conn.execute(
        "INSERT INTO epi_requests (id, company_id, unit_id, employee_id, epi_id, quantity, "
        "glove_size, size, uniform_size, requested_at, status) "
        "VALUES (?, 2, 4, ?, ?, 1, 'N/A', 'N/A', 'N/A', '2026-06-01T00:00:00+00:00', ?)",
        (req_id, employee_id, epi_id, status),
    )
    conn.commit()


def _employee_demand_epi_ids(conn):
    demands = fetch_purchase_demands(conn, company_id=2, scope_unit_id=4)
    return {int(d["epi_id"]) for d in demands if d.get("demand_type") == "employee_request"}


def test_collaborator_request_pending_approval_is_not_a_demand():
    # status 'solicitado' fica na aba Aprovações; não deve aparecer em Demandas.
    conn = _conn()
    _add_employee_request(conn, req_id=1, epi_id=40, status="solicitado")
    assert 40 not in _employee_demand_epi_ids(conn)


def test_collaborator_request_approved_becomes_a_demand():
    # após aprovação do Administrador Local (status 'aprovado'), vira demanda.
    conn = _conn()
    _add_employee_request(conn, req_id=2, epi_id=41, status="aprovado")
    assert 41 in _employee_demand_epi_ids(conn)
