"""Fase 3 Multi-CNPJ: escopo de estoque, requisições e compras por CNPJ.

Cobre:
  - configuração `stock_control_scope` / `org_structure_type` em Minha Empresa;
  - resolução do pool de estoque (Empresa / CNPJ / Unidade) sem re-chavear a
    tabela de estoque — o pool por CNPJ é derivado de `units.legal_entity_id`;
  - saldo agregado pelo pool (`fetch_scoped_stock_balance`);
  - pedido de compra emitido para um CNPJ específico (atributo próprio, pois é
    escolha de emissão — diferente do CNPJ derivado das entregas/requisições).
"""

import sqlite3

import pytest

from core.schema import ensure_legal_entities
from modules.legal_entities.service import (
    create_legal_entity,
    get_default_legal_entity_id,
    get_stock_control_scope,
    resolve_stock_pool_unit_ids,
)
from modules.stock.service import fetch_scoped_stock_balance

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
            company_id INTEGER NOT NULL, name TEXT, unit_type TEXT,
            city TEXT, notes TEXT DEFAULT ''
        );
        CREATE TABLE employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL, unit_id INTEGER, name TEXT
        );
        CREATE TABLE unit_epi_stock (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER, unit_id INTEGER, epi_id INTEGER,
            quantity INTEGER DEFAULT 0, updated_at TEXT DEFAULT ''
        );
        """
    )
    conn.execute("INSERT INTO companies (name, legal_name, cnpj) VALUES ('ACME', 'ACME SA', ?)", (CNPJ_A,))
    conn.commit()
    ensure_legal_entities(conn)
    return conn


def _seed_two_cnpjs_with_units(conn):
    """Matriz com 2 unidades + filial (outro CNPJ) com 1 unidade, cada uma com saldo."""
    matriz = get_default_legal_entity_id(conn, 1)
    filial = create_legal_entity(
        conn, {'cnpj': CNPJ_B, 'legal_name': 'ACME Filial RJ', 'entity_type': 'filial', 'uf': 'RJ'}, 1
    )
    units = {}
    for name, entity, qty in (('Matriz A', matriz, 10), ('Matriz B', matriz, 5), ('Filial RJ', filial, 7)):
        cur = conn.execute(
            'INSERT INTO units (company_id, name, unit_type, city, legal_entity_id) VALUES (1, ?, ?, ?, ?)',
            (name, 'base', 'X', entity),
        )
        unit_id = int(cur.lastrowid)
        units[name] = unit_id
        conn.execute(
            'INSERT INTO unit_epi_stock (company_id, unit_id, epi_id, quantity) VALUES (1, ?, 99, ?)',
            (unit_id, qty),
        )
    conn.commit()
    return matriz, filial, units


def _set_scope(conn, scope):
    conn.execute('UPDATE companies SET stock_control_scope = ? WHERE id = 1', (scope,))
    conn.commit()


# ── configuração do escopo ────────────────────────────────────────────────────

def test_default_scope_is_company():
    conn = _conn()
    assert get_stock_control_scope(conn, 1) == 'company'


def test_scope_falls_back_when_column_absent():
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.executescript('CREATE TABLE companies (id INTEGER PRIMARY KEY, name TEXT);')
    conn.execute("INSERT INTO companies (id, name) VALUES (1, 'X')")
    conn.commit()
    assert get_stock_control_scope(conn, 1) == 'unit'


def test_invalid_scope_normalizes_to_company():
    conn = _conn()
    _set_scope(conn, 'invalido')
    assert get_stock_control_scope(conn, 1) == 'company'


def test_company_settings_accepts_structure_fields():
    from modules.company_settings.service import PROFILE_EDITABLE_FIELDS
    assert 'org_structure_type' in PROFILE_EDITABLE_FIELDS
    assert 'stock_control_scope' in PROFILE_EDITABLE_FIELDS


def test_company_settings_normalizes_invalid_scope():
    from modules.company_settings.service import validate_my_company_payload
    conn = _conn()
    fields = validate_my_company_payload(
        conn, {'stock_control_scope': 'xpto', 'org_structure_type': 'nope'}, 1, {}
    )
    assert fields['stock_control_scope'] == 'company'
    assert fields['org_structure_type'] == 'single_cnpj'


def test_company_settings_keeps_valid_scope():
    from modules.company_settings.service import validate_my_company_payload
    conn = _conn()
    fields = validate_my_company_payload(
        conn, {'stock_control_scope': 'legal_entity', 'org_structure_type': 'joint_venture'}, 1, {}
    )
    assert fields['stock_control_scope'] == 'legal_entity'
    assert fields['org_structure_type'] == 'joint_venture'


# ── pool de estoque ───────────────────────────────────────────────────────────

def test_pool_scope_unit_isolates_each_unit():
    conn = _conn()
    _, _, units = _seed_two_cnpjs_with_units(conn)
    _set_scope(conn, 'unit')
    assert resolve_stock_pool_unit_ids(conn, 1, units['Matriz A']) == [units['Matriz A']]


def test_pool_scope_legal_entity_groups_units_of_same_cnpj():
    conn = _conn()
    _, _, units = _seed_two_cnpjs_with_units(conn)
    _set_scope(conn, 'legal_entity')
    pool = resolve_stock_pool_unit_ids(conn, 1, units['Matriz A'])
    assert set(pool) == {units['Matriz A'], units['Matriz B']}
    assert units['Filial RJ'] not in pool  # CNPJ distinto não compartilha


def test_pool_scope_legal_entity_isolates_the_other_cnpj():
    conn = _conn()
    _, _, units = _seed_two_cnpjs_with_units(conn)
    _set_scope(conn, 'legal_entity')
    assert resolve_stock_pool_unit_ids(conn, 1, units['Filial RJ']) == [units['Filial RJ']]


def test_pool_scope_company_shares_all_units():
    conn = _conn()
    _, _, units = _seed_two_cnpjs_with_units(conn)
    _set_scope(conn, 'company')
    pool = resolve_stock_pool_unit_ids(conn, 1, units['Matriz A'])
    assert set(pool) == set(units.values())


# ── saldo agregado pelo pool ─────────────────────────────────────────────────

def test_scoped_balance_per_unit():
    conn = _conn()
    _, _, units = _seed_two_cnpjs_with_units(conn)
    _set_scope(conn, 'unit')
    balance = fetch_scoped_stock_balance(conn, 1, units['Matriz A'], 99)
    assert balance['scope'] == 'unit'
    assert balance['quantity'] == 10


def test_scoped_balance_per_legal_entity_sums_same_cnpj():
    conn = _conn()
    _, _, units = _seed_two_cnpjs_with_units(conn)
    _set_scope(conn, 'legal_entity')
    balance = fetch_scoped_stock_balance(conn, 1, units['Matriz A'], 99)
    assert balance['quantity'] == 15  # 10 + 5, sem a filial
    assert balance['quantity_by_unit'][units['Matriz B']] == 5


def test_scoped_balance_per_company_sums_everything():
    conn = _conn()
    _, _, units = _seed_two_cnpjs_with_units(conn)
    _set_scope(conn, 'company')
    balance = fetch_scoped_stock_balance(conn, 1, units['Matriz A'], 99)
    assert balance['quantity'] == 22  # 10 + 5 + 7


def test_scoped_balance_exposes_pool_composition():
    conn = _conn()
    _, _, units = _seed_two_cnpjs_with_units(conn)
    _set_scope(conn, 'legal_entity')
    balance = fetch_scoped_stock_balance(conn, 1, units['Matriz A'], 99)
    assert set(balance['pool_unit_ids']) == {units['Matriz A'], units['Matriz B']}
    assert balance['epi_id'] == 99


# ── pedido de compra por CNPJ ────────────────────────────────────────────────

def _po_conn():
    conn = _conn()
    conn.executescript('CREATE TABLE purchase_orders (id INTEGER PRIMARY KEY, legal_entity_id INTEGER);')
    conn.commit()
    return conn


def test_purchase_order_legal_entity_defaults_to_none():
    from modules.purchases.service import _resolve_order_legal_entity
    conn = _po_conn()
    assert _resolve_order_legal_entity(conn, 1, {}) is None


def test_purchase_order_accepts_own_company_cnpj():
    from modules.purchases.service import _resolve_order_legal_entity
    conn = _po_conn()
    entity_id = get_default_legal_entity_id(conn, 1)
    assert _resolve_order_legal_entity(conn, 1, {'legal_entity_id': entity_id}) == entity_id


def test_purchase_order_rejects_other_company_cnpj():
    from modules.purchases.service import _resolve_order_legal_entity
    conn = _po_conn()
    conn.execute("INSERT INTO companies (name, legal_name, cnpj) VALUES ('OUTRA', 'OUTRA SA', ?)", (CNPJ_B,))
    conn.commit()
    ensure_legal_entities(conn)
    other = get_default_legal_entity_id(conn, 2)
    with pytest.raises(ValueError):
        _resolve_order_legal_entity(conn, 1, {'legal_entity_id': other})


def test_purchase_order_rejects_inactive_cnpj():
    from modules.purchases.service import _resolve_order_legal_entity
    conn = _po_conn()
    filial = create_legal_entity(
        conn, {'cnpj': CNPJ_B, 'legal_name': 'Filial', 'entity_type': 'filial', 'active': 0}, 1
    )
    with pytest.raises(ValueError):
        _resolve_order_legal_entity(conn, 1, {'legal_entity_id': filial})
