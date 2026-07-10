"""Auditoria F-07/F-08 — endpoints POST recém-implementados.

F-08: POST /api/company-purchase-config persiste a config (require_admin_review).
F-07: POST /api/purchase-functions vincula comprador/aprovador a unidades.
Ambos existiam apenas como GET/DELETE; o frontend POSTava para rota inexistente.
"""

import sqlite3

import pytest

from modules.purchases.service import (
    create_purchase_function_links,
    get_company_purchase_config,
    set_company_purchase_config,
)

ADMIN = {'id': 3, 'full_name': 'Admin Geral', 'role': 'general_admin', 'company_id': 1}


def _conn():
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        CREATE TABLE app_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE purchase_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT, company_id INTEGER, entity_type TEXT, entity_id INTEGER,
            action TEXT, status_from TEXT DEFAULT '', status_to TEXT DEFAULT '', comment TEXT DEFAULT '',
            actor_user_id INTEGER, actor_name TEXT DEFAULT '', actor_role TEXT DEFAULT '',
            reason TEXT DEFAULT '', destination TEXT DEFAULT '', ip_address TEXT DEFAULT '',
            session_ref TEXT DEFAULT '', created_at TEXT
        );
        CREATE TABLE employees (id INTEGER PRIMARY KEY, company_id INTEGER, name TEXT);
        CREATE TABLE units (id INTEGER PRIMARY KEY, company_id INTEGER, name TEXT);
        CREATE TABLE purchase_role_unit_links (
            id INTEGER PRIMARY KEY AUTOINCREMENT, company_id INTEGER, employee_id INTEGER,
            role_type TEXT, unit_id INTEGER, created_by_user_id INTEGER, created_at TEXT,
            UNIQUE(employee_id, role_type, unit_id)
        );
        """
    )
    conn.execute("INSERT INTO employees (id, company_id, name) VALUES (50, 1, 'João'), (99, 2, 'Outra Empresa')")
    conn.execute("INSERT INTO units (id, company_id, name) VALUES (1, 1, 'Matriz'), (2, 1, 'Filial'), (7, 2, 'Outra')")
    return conn


# ── F-08: config da empresa ──────────────────────────────────────────────────

def test_set_company_config_persists_and_reads_back():
    conn = _conn()
    config = set_company_purchase_config(conn, ADMIN, 1, True)
    assert config == {'require_admin_review': True}
    assert get_company_purchase_config(conn, 1) == {'require_admin_review': True}
    # sobrescreve (upsert)
    set_company_purchase_config(conn, ADMIN, 1, False)
    assert get_company_purchase_config(conn, 1)['require_admin_review'] is False
    ev = conn.execute("SELECT action FROM purchase_events WHERE action = 'purchase_config_updated'").fetchall()
    assert len(ev) == 2


# ── F-07: vínculos de função de compras ──────────────────────────────────────

def test_create_function_links_idempotent():
    conn = _conn()
    created = create_purchase_function_links(conn, ADMIN, 1, 50, 'buyer', [1, 2])
    assert created == 2
    rows = conn.execute("SELECT unit_id FROM purchase_role_unit_links WHERE employee_id = 50 AND role_type = 'buyer' ORDER BY unit_id").fetchall()
    assert [r['unit_id'] for r in rows] == [1, 2]
    # repetir não duplica
    again = create_purchase_function_links(conn, ADMIN, 1, 50, 'buyer', [1, 2])
    assert again == 0
    assert conn.execute("SELECT COUNT(*) FROM purchase_role_unit_links").fetchone()[0] == 2


def test_create_function_links_rejects_foreign_employee():
    conn = _conn()
    with pytest.raises(ValueError, match='Colaborador'):
        create_purchase_function_links(conn, ADMIN, 1, 99, 'buyer', [1])


def test_create_function_links_rejects_foreign_unit():
    conn = _conn()
    with pytest.raises(ValueError, match='fora da empresa'):
        create_purchase_function_links(conn, ADMIN, 1, 50, 'buyer', [1, 7])


def test_create_function_links_requires_units():
    conn = _conn()
    with pytest.raises(ValueError, match='unidade'):
        create_purchase_function_links(conn, ADMIN, 1, 50, 'buyer', [])


def test_create_function_links_validates_role_type():
    conn = _conn()
    with pytest.raises(ValueError, match='comprador ou aprovador'):
        create_purchase_function_links(conn, ADMIN, 1, 50, 'chef', [1])
