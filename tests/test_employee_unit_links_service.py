"""Serviço de vínculo local do colaborador com a Unidade (ADR-0002 §13, PR B).

Cobre a idempotência do "Vincular à minha unidade", a ativação/desativação
local e — o ponto que a issue #180 exige — que nada disso toque
`employees.unit_id`, a transferência ou a movimentação temporária.
"""

import os
import sqlite3
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import schema
from modules.employees.service import (
    create_employee_unit_link,
    ensure_employee_is_linkable_to_units,
    fetch_employee_unit_link,
    fetch_employee_unit_links,
    set_employee_unit_link_status,
)


def _conn():
    connection = sqlite3.connect(':memory:')
    connection.row_factory = sqlite3.Row
    return connection


def _base_schema(connection):
    connection.execute('CREATE TABLE companies (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT)')
    connection.execute(
        'CREATE TABLE units (id INTEGER PRIMARY KEY AUTOINCREMENT, company_id INTEGER, name TEXT)'
    )
    connection.execute('CREATE TABLE users (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT)')
    connection.execute(
        'CREATE TABLE employees ('
        ' id INTEGER PRIMARY KEY AUTOINCREMENT, company_id INTEGER, unit_id INTEGER,'
        " name TEXT, tipo_vinculo TEXT DEFAULT 'CLT', empresa_origem TEXT DEFAULT '',"
        ' outsourced_company_id INTEGER)'
    )
    connection.execute("INSERT INTO companies (id, name) VALUES (1, 'Tenant A')")
    connection.execute("INSERT INTO companies (id, name) VALUES (2, 'Tenant B')")
    connection.execute("INSERT INTO units (id, company_id, name) VALUES (10, 1, 'A1')")
    connection.execute("INSERT INTO units (id, company_id, name) VALUES (11, 1, 'A2')")
    connection.execute("INSERT INTO users (id, name) VALUES (5, 'Ator')")
    connection.execute(
        'INSERT INTO employees (id, company_id, unit_id, name, tipo_vinculo, outsourced_company_id) '
        "VALUES (100, 1, 10, 'Terceirizado', 'Terceirizado', 7)"
    )
    connection.commit()
    schema.ensure_employee_unit_links(connection)


def _status(connection, employee_id, unit_id):
    link = fetch_employee_unit_link(connection, employee_id, unit_id)
    return link['local_status'] if link else None


# ── quem pode ser vinculado ─────────────────────────────────────────────────

@pytest.mark.parametrize('vinculo', ['CLT', 'Menor Aprendiz', 'Praticante', 'Estagiário'])
def test_own_workforce_cannot_be_linked_to_units(vinculo):
    """A rota e o backfill precisam contar a MESMA história. O backfill filtra
    mão de obra contratada; se a rota aceitasse um CLT, criaria linha que o
    backfill jamais criaria e as duas fontes passariam a discordar."""
    with pytest.raises(ValueError, match='mão de obra própria'):
        ensure_employee_is_linkable_to_units({'tipo_vinculo': vinculo, 'name': 'X'})


@pytest.mark.parametrize('vinculo', ['Terceirizado', 'Prestador de Serviço', 'Temporário'])
def test_contracted_workforce_can_be_linked(vinculo):
    ensure_employee_is_linkable_to_units({'tipo_vinculo': vinculo, 'name': 'X'})


# ── vincular ────────────────────────────────────────────────────────────────

def test_linking_creates_an_active_link():
    conn = _conn()
    _base_schema(conn)
    link_id = create_employee_unit_link(conn, 100, 1, 11, 5)
    assert link_id > 0
    assert _status(conn, 100, 11) == 'active'


def test_linking_twice_returns_the_same_link_without_duplicating():
    conn = _conn()
    _base_schema(conn)
    first = create_employee_unit_link(conn, 100, 1, 11, 5)
    second = create_employee_unit_link(conn, 100, 1, 11, 5)
    assert first == second
    assert len(fetch_employee_unit_links(conn, 100)) == 1


def test_linking_again_does_not_revive_a_deactivated_link():
    """Reativar é ação explícita, não efeito de clicar "vincular" de novo."""
    conn = _conn()
    _base_schema(conn)
    link_id = create_employee_unit_link(conn, 100, 1, 11, 5)
    set_employee_unit_link_status(conn, link_id, 1, 'inactive', 5, reason='fim do contrato')
    create_employee_unit_link(conn, 100, 1, 11, 5)
    assert _status(conn, 100, 11) == 'inactive'


def test_the_same_person_can_be_linked_to_two_units():
    conn = _conn()
    _base_schema(conn)
    create_employee_unit_link(conn, 100, 1, 10, 5)
    create_employee_unit_link(conn, 100, 1, 11, 5)
    assert sorted(link['unit_id'] for link in fetch_employee_unit_links(conn, 100)) == [10, 11]


# ── ativar / desativar ──────────────────────────────────────────────────────

def test_deactivating_records_reason_and_actor():
    conn = _conn()
    _base_schema(conn)
    link_id = create_employee_unit_link(conn, 100, 1, 11, 5)
    set_employee_unit_link_status(conn, link_id, 1, 'inactive', 5, reason='contrato encerrado')
    link = fetch_employee_unit_link(conn, 100, 11)
    assert link['local_status'] == 'inactive'
    assert link['deactivation_reason'] == 'contrato encerrado'
    assert link['deactivated_by_user_id'] == 5


def test_reactivating_clears_the_deactivation_trail():
    conn = _conn()
    _base_schema(conn)
    link_id = create_employee_unit_link(conn, 100, 1, 11, 5)
    set_employee_unit_link_status(conn, link_id, 1, 'inactive', 5, reason='engano')
    set_employee_unit_link_status(conn, link_id, 1, 'active', 5)
    link = fetch_employee_unit_link(conn, 100, 11)
    assert link['local_status'] == 'active'
    assert link['deactivated_at'] is None
    assert link['deactivation_reason'] == ''


def test_deactivating_one_unit_does_not_touch_the_other():
    """É a razão de o status ser LOCAL: cada Unidade decide a sua."""
    conn = _conn()
    _base_schema(conn)
    link_a = create_employee_unit_link(conn, 100, 1, 10, 5)
    create_employee_unit_link(conn, 100, 1, 11, 5)
    set_employee_unit_link_status(conn, link_a, 1, 'inactive', 5)
    assert _status(conn, 100, 10) == 'inactive'
    assert _status(conn, 100, 11) == 'active'


def test_status_change_is_scoped_by_company_id():
    """O `WHERE ... AND company_id = ?` do UPDATE é o que impede um id de
    vínculo de outro tenant de ser alterado. Sem ele, o id sozinho bastaria."""
    conn = _conn()
    _base_schema(conn)
    link_id = create_employee_unit_link(conn, 100, 1, 11, 5)
    set_employee_unit_link_status(conn, link_id, 2, 'inactive', 5)  # tenant errado
    assert _status(conn, 100, 11) == 'active'


# ── não regressão exigida pela issue #180 ───────────────────────────────────

def test_linking_does_not_change_employee_unit_id():
    conn = _conn()
    _base_schema(conn)
    create_employee_unit_link(conn, 100, 1, 11, 5)
    assert conn.execute(
        'SELECT unit_id FROM employees WHERE id = 100'
    ).fetchone()['unit_id'] == 10


def test_deactivating_the_link_does_not_change_employee_unit_id():
    """Desativar vínculo local não é transferir nem arquivar a pessoa."""
    conn = _conn()
    _base_schema(conn)
    link_id = create_employee_unit_link(conn, 100, 1, 10, 5)
    set_employee_unit_link_status(conn, link_id, 1, 'inactive', 5)
    assert conn.execute(
        'SELECT unit_id FROM employees WHERE id = 100'
    ).fetchone()['unit_id'] == 10
