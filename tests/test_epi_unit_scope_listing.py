"""Escopo de listagem de EPIs por unidade operacional.

Regra: uma unidade só pode ver os EPIs cadastrados nela (mais os de nível
empresa, unit_id NULL). Perfis operacionais (Administrador Local / Gestor de
EPI) recebem apenas esse conjunto; administradores de empresa veem todos.

Cobre o filtro usado no bootstrap (fetch_epis com unit_id), que alimenta tanto
o Web (state.epis) quanto o app Flutter (bootstrap.epis) — corrigindo o
vazamento no Controle de Estoque → Movimentações.
"""
import sqlite3

import pytest

from modules.epis.service import fetch_epis

ADMIN_COMPANY = {'id': 1, 'role': 'general_admin', 'company_id': 1}
GESTOR_UNIT_A = {'id': 2, 'role': 'user', 'company_id': 1}


@pytest.fixture
def conn():
    connection = sqlite3.connect(':memory:')
    connection.row_factory = sqlite3.Row
    connection.executescript(
        """
        CREATE TABLE companies (id INTEGER PRIMARY KEY, name TEXT, cnpj TEXT DEFAULT '', logo_type TEXT DEFAULT '');
        CREATE TABLE units (id INTEGER PRIMARY KEY, company_id INTEGER, name TEXT, unit_type TEXT DEFAULT 'base');
        CREATE TABLE unit_epi_stock (id INTEGER PRIMARY KEY, company_id INTEGER, epi_id INTEGER, quantity INTEGER DEFAULT 0);
        CREATE TABLE epis (
            id INTEGER PRIMARY KEY, company_id INTEGER, unit_id INTEGER, name TEXT,
            purchase_code TEXT DEFAULT '', ca TEXT DEFAULT '', sector TEXT DEFAULT '',
            epi_section TEXT DEFAULT '', active INTEGER DEFAULT 1, stock INTEGER DEFAULT 0,
            minimum_stock INTEGER DEFAULT 0, unit_measure TEXT DEFAULT 'un', ca_expiry TEXT DEFAULT '',
            epi_validity_date TEXT DEFAULT '', manufacture_date TEXT DEFAULT '',
            validity_days INTEGER DEFAULT 0, validity_years INTEGER DEFAULT 0, validity_months INTEGER DEFAULT 0,
            manufacturer_validity_months INTEGER DEFAULT 0, default_replacement_days INTEGER,
            manufacturer TEXT DEFAULT '', model_reference TEXT DEFAULT '', supplier_company TEXT DEFAULT '',
            manufacturer_recommendations TEXT DEFAULT '', epi_photo_data TEXT,
            glove_size TEXT DEFAULT 'N/A', size TEXT DEFAULT 'N/A', uniform_size TEXT DEFAULT 'N/A',
            joinventures_json TEXT DEFAULT '[]', active_joinventure TEXT,
            scope_type TEXT DEFAULT 'UNIT', is_joint_venture INTEGER DEFAULT 0,
            qr_code_value TEXT DEFAULT '', epi_master_sequence INTEGER DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'active');
        INSERT INTO companies (id, name) VALUES (1, 'ACME');
        INSERT INTO units (id, company_id, name) VALUES (10, 1, 'Base A'), (20, 1, 'Base B');
        -- EPI da unidade A, EPI da unidade B, e um EPI de nível empresa (global)
        INSERT INTO epis (id, company_id, unit_id, name, scope_type) VALUES
            (100, 1, 10, 'Capacete A', 'UNIT'),
            (200, 1, 20, 'Luva B', 'UNIT'),
            (300, 1, NULL, 'Bota Global', 'GLOBAL');
        """
    )
    yield connection
    connection.close()


def test_unit_scoped_actor_sees_only_own_unit_and_global(conn):
    epis = fetch_epis(conn, GESTOR_UNIT_A, 10)
    ids = sorted(e['id'] for e in epis)
    # Vê o EPI da própria unidade (100) e o global (300); NÃO vê o da unidade B (200).
    assert ids == [100, 300]
    assert all(e['id'] != 200 for e in epis)


def test_company_admin_without_unit_sees_all(conn):
    epis = fetch_epis(conn, ADMIN_COMPANY)
    ids = sorted(e['id'] for e in epis)
    assert ids == [100, 200, 300]


def test_other_unit_scope_excludes_first_unit(conn):
    epis = fetch_epis(conn, GESTOR_UNIT_A, 20)
    ids = sorted(e['id'] for e in epis)
    # Unidade B: vê a Luva B (200) e o global (300); não vê o Capacete A (100).
    assert ids == [200, 300]
