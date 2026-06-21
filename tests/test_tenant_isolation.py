"""FASE 2 — Isolamento multi-tenant (suíte de regressão).

Prova, em nível de dados (sqlite in-memory com DUAS empresas seedadas), que as
funções de listagem do backend nunca devolvem linhas de outra empresa para um
ator não-master, e que o escopo por unidade é respeitado. Reusa o padrão de
`test_devolutions_flow.py` (schema mínimo + serviço real, sem mocks).

Critério da FASE 2: "Nenhum usuário consegue acessar dados de outra empresa."
"""
import sqlite3

import pytest

from modules.units.service import fetch_units
from modules.companies.service import fetch_companies
from modules.employees.service import fetch_employees
from modules.purchases.service import (
    fetch_purchase_requests,
    count_pending_purchase_requests,
)


@pytest.fixture()
def conn():
    c = sqlite3.connect(':memory:')
    c.row_factory = sqlite3.Row
    c.execute('PRAGMA foreign_keys = OFF')
    c.executescript(
        """
        CREATE TABLE companies (
            id INTEGER PRIMARY KEY, name TEXT, legal_name TEXT DEFAULT '',
            cnpj TEXT DEFAULT '', active INTEGER DEFAULT 1, logo_type TEXT DEFAULT ''
        );
        CREATE TABLE units (
            id INTEGER PRIMARY KEY, company_id INTEGER, name TEXT,
            unit_type TEXT DEFAULT '', city TEXT DEFAULT '', notes TEXT DEFAULT ''
        );
        CREATE TABLE users (
            id INTEGER PRIMARY KEY, company_id INTEGER, active INTEGER DEFAULT 1, role TEXT
        );
        CREATE TABLE purchase_requests (
            id INTEGER PRIMARY KEY, company_id INTEGER, unit_id INTEGER,
            status TEXT, title TEXT DEFAULT '', notes TEXT DEFAULT '', created_at TEXT DEFAULT ''
        );
        CREATE TABLE purchase_request_items (
            id INTEGER PRIMARY KEY, purchase_request_id INTEGER
        );
        CREATE TABLE employees (
            id INTEGER PRIMARY KEY, company_id INTEGER NOT NULL, unit_id INTEGER NOT NULL,
            employee_id_code TEXT NOT NULL DEFAULT '', cpf TEXT NOT NULL DEFAULT '',
            name TEXT NOT NULL, email TEXT NOT NULL DEFAULT '', whatsapp TEXT NOT NULL DEFAULT '',
            preferred_contact_channel TEXT NOT NULL DEFAULT 'whatsapp', sector TEXT NOT NULL DEFAULT '',
            role_name TEXT NOT NULL DEFAULT '', admission_date TEXT NOT NULL DEFAULT '',
            schedule_type TEXT NOT NULL DEFAULT '', tipo_vinculo TEXT NOT NULL DEFAULT 'CLT',
            empresa_origem TEXT NOT NULL DEFAULT ''
        );
        CREATE TABLE employee_unit_movements (
            id INTEGER PRIMARY KEY, employee_id INTEGER, target_unit_id INTEGER,
            movement_type TEXT, start_date TEXT, end_date TEXT
        );
        -- Empresa 1 (Alpha) e Empresa 2 (Beta)
        INSERT INTO companies (id, name, legal_name, cnpj, active) VALUES
            (1, 'Alpha', 'Alpha LTDA', '111', 1),
            (2, 'Beta',  'Beta LTDA',  '222', 1);
        INSERT INTO units (id, company_id, name) VALUES
            (10, 1, 'Alpha-Matriz'), (11, 1, 'Alpha-Filial'), (20, 2, 'Beta-Matriz');
        INSERT INTO users (id, company_id, active, role) VALUES
            (1, 1, 1, 'general_admin'), (2, 2, 1, 'general_admin');
        INSERT INTO purchase_requests (id, company_id, unit_id, status, created_at) VALUES
            (101, 1, 10, 'open', '2026-01-01'),
            (102, 1, 11, 'pending_approval', '2026-01-02'),
            (103, 1, 10, 'closed', '2026-01-03'),
            (201, 2, 20, 'open', '2026-01-04');
        INSERT INTO employees (id, company_id, unit_id, name) VALUES
            (1001, 1, 10, 'Ana'), (1002, 1, 11, 'Bruno'), (2001, 2, 20, 'Carlos');
        """
    )
    c.commit()
    return c


# ── Unidades ────────────────────────────────────────────────────────────────

def test_units_non_master_sees_only_own_company(conn):
    actor = {'role': 'general_admin', 'company_id': 1}
    ids = {u['id'] for u in fetch_units(conn, actor)}
    assert ids == {10, 11}
    assert 20 not in ids  # nunca vê unidade da empresa 2


def test_units_other_company_actor_is_isolated(conn):
    actor = {'role': 'general_admin', 'company_id': 2}
    ids = {u['id'] for u in fetch_units(conn, actor)}
    assert ids == {20}


def test_units_master_sees_all(conn):
    actor = {'role': 'master_admin', 'company_id': None}
    ids = {u['id'] for u in fetch_units(conn, actor)}
    assert ids == {10, 11, 20}


# ── Empresas ────────────────────────────────────────────────────────────────

def test_companies_scoped_returns_only_that_company(conn):
    # O bootstrap passa company_id do ator (None só p/ master) — primitivo de isolamento.
    ids = {c['id'] for c in fetch_companies(conn, company_id=1)}
    assert ids == {1}


def test_companies_unscoped_returns_all(conn):
    ids = {c['id'] for c in fetch_companies(conn, company_id=None)}
    assert ids == {1, 2}


# ── Requisições de compra ─────────────────────────────────────────────────────

def test_purchase_requests_isolated_by_company(conn):
    a = {r['id'] for r in fetch_purchase_requests(conn, company_id=1, scope_unit_id=None, purchase_scope_units=None)}
    b = {r['id'] for r in fetch_purchase_requests(conn, company_id=2, scope_unit_id=None, purchase_scope_units=None)}
    assert a == {101, 102, 103}
    assert b == {201}
    assert a.isdisjoint(b)  # zero vazamento entre empresas


def test_purchase_requests_scoped_by_unit(conn):
    only10 = {r['id'] for r in fetch_purchase_requests(conn, company_id=1, scope_unit_id=10, purchase_scope_units=None)}
    assert only10 == {101, 103}


def test_purchase_requests_scoped_by_unit_list(conn):
    only11 = {r['id'] for r in fetch_purchase_requests(conn, company_id=1, scope_unit_id=None, purchase_scope_units=[11])}
    assert only11 == {102}


# ── Funcionários ──────────────────────────────────────────────────────────────

def test_employees_non_master_sees_only_own_company(conn):
    actor = {'role': 'general_admin', 'company_id': 1}
    ids = {e['id'] for e in fetch_employees(conn, actor)}
    assert ids == {1001, 1002}
    assert 2001 not in ids


def test_employees_other_company_actor_is_isolated(conn):
    actor = {'role': 'general_admin', 'company_id': 2}
    ids = {e['id'] for e in fetch_employees(conn, actor)}
    assert ids == {2001}


def test_employees_master_sees_all(conn):
    actor = {'role': 'master_admin', 'company_id': None}
    ids = {e['id'] for e in fetch_employees(conn, actor)}
    assert ids == {1001, 1002, 2001}


def test_pending_count_isolated_by_company(conn):
    # Empresa 1: 101(open)+102(pending) pendentes; 103(closed) é terminal.
    assert count_pending_purchase_requests(conn, company_id=1) == 2
    # Empresa 2: 201(open).
    assert count_pending_purchase_requests(conn, company_id=2) == 1
