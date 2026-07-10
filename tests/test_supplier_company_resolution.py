"""Auditoria F-03 — master_admin (company_id NULL) nas rotas de fornecedores.

Antes, os handlers de catálogo/integração faziam int(actor['company_id']),
que para o master_admin (company_id NULL) levantava TypeError → 500. Agora a
empresa é resolvida a partir do próprio recurso (fornecedor/produto),
preservando o isolamento multi-tenant.
"""

import sqlite3

import pytest

from modules.purchases.quotes_service import (
    resolve_product_company_id,
    resolve_supplier_company_id,
)

MASTER = {'id': 1, 'full_name': 'Master', 'role': 'master_admin', 'company_id': None}
ADMIN_C1 = {'id': 2, 'full_name': 'Admin Empresa 1', 'role': 'general_admin', 'company_id': 1}
ADMIN_C2 = {'id': 3, 'full_name': 'Admin Empresa 2', 'role': 'general_admin', 'company_id': 2}


def _conn():
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        CREATE TABLE companies (id INTEGER PRIMARY KEY, name TEXT);
        CREATE TABLE users (id INTEGER PRIMARY KEY);
        CREATE TABLE epis (id INTEGER PRIMARY KEY, company_id INTEGER, name TEXT);
        CREATE TABLE authorized_suppliers (
            id INTEGER PRIMARY KEY, company_id INTEGER, name TEXT,
            cnpj TEXT DEFAULT '', category TEXT DEFAULT '', contact_email TEXT DEFAULT '',
            notes TEXT DEFAULT '', active INTEGER DEFAULT 1, source TEXT DEFAULT 'manual',
            created_by_user_id INTEGER, created_at TEXT DEFAULT '', updated_at TEXT DEFAULT ''
        );
        CREATE TABLE supplier_products (
            id INTEGER PRIMARY KEY, company_id INTEGER, supplier_id INTEGER,
            supplier_sku TEXT DEFAULT '', description TEXT DEFAULT '', active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT '', updated_at TEXT DEFAULT ''
        );
        """
    )
    conn.execute("INSERT INTO companies (id, name) VALUES (1, 'Empresa A'), (2, 'Empresa B')")
    # fornecedor 10 pertence à empresa 2
    conn.execute("INSERT INTO authorized_suppliers (id, company_id, name) VALUES (10, 2, 'Loja B')")
    conn.execute(
        "INSERT INTO supplier_products (id, company_id, supplier_id, supplier_sku, description, active, created_at, updated_at) "
        "VALUES (500, 2, 10, 'SKU-1', 'Item', 1, 'x', 'x')"
    )
    return conn


def test_company_admin_uses_own_company():
    conn = _conn()
    assert resolve_supplier_company_id(conn, ADMIN_C1, 10) == 1  # não olha o recurso; usa a própria
    assert resolve_product_company_id(conn, ADMIN_C1, 500) == 1


def test_master_admin_resolves_from_supplier():
    conn = _conn()
    # antes: TypeError int(None) → 500; agora resolve pela empresa do fornecedor
    assert resolve_supplier_company_id(conn, MASTER, 10) == 2
    assert resolve_product_company_id(conn, MASTER, 500) == 2


def test_master_admin_missing_resource_raises_value_error():
    conn = _conn()
    with pytest.raises(ValueError, match='Fornecedor'):
        resolve_supplier_company_id(conn, MASTER, 999)
    with pytest.raises(ValueError, match='Produto'):
        resolve_product_company_id(conn, MASTER, 999)


def test_resolution_is_not_500_for_master():
    """Regressão-guarda: master_admin nunca dispara TypeError aqui."""
    conn = _conn()
    try:
        resolve_supplier_company_id(conn, MASTER, 10)
    except TypeError:  # pragma: no cover
        pytest.fail('master_admin ainda dispara TypeError (F-03 não corrigido)')
