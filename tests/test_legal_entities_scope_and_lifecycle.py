"""Bloco A Multi-CNPJ: escopo por CNPJ, obrigatoriedade, auditoria e inativação.

Cobre as lacunas de conformidade:
  - escopo de visibilidade por CNPJ (Geral/Registro x Administrador Local x
    Gestor de EPI). O Administrador Local não administra CNPJ nem possui
    carteira própria (docs/PAPEIS_E_ATRIBUICOES.md #4): o CNPJ é sempre
    derivado da única unidade que ele administra (``units.legal_entity_id``),
    nunca escolhido — e a ausência de unidade/CNPJ fecha o escopo (``[]``),
    nunca abre (``None``);
  - CNPJ obrigatório no colaborador quando a empresa tem mais de um CNPJ ativo;
  - auditoria registrando o CNPJ afetado;
  - inativação auditada do CNPJ (exclusão nunca é física).
"""

import json
import sqlite3

import pytest

from core.schema import ensure_company_audit_columns, ensure_legal_entities
from modules.legal_entities.service import (
    count_active_legal_entities,
    create_legal_entity,
    deactivate_legal_entity,
    ensure_legal_entity_access,
    fetch_legal_entities,
    get_default_legal_entity_id,
    resolve_actor_legal_entity_ids,
    resolve_employee_legal_entity_id,
)

CNPJ_A = '11.222.333/0001-81'
CNPJ_B = '45.723.174/0001-10'
CNPJ_C = '19.131.243/0001-97'

_EMPLOYEES_TABLE = """
    CREATE TABLE employees (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL, unit_id INTEGER, name TEXT,
        employee_id_code TEXT DEFAULT '', cpf TEXT DEFAULT '', email TEXT DEFAULT '',
        whatsapp TEXT DEFAULT '', preferred_contact_channel TEXT DEFAULT '',
        sector TEXT DEFAULT '', role_name TEXT DEFAULT '', admission_date TEXT DEFAULT '',
        schedule_type TEXT DEFAULT '', tipo_vinculo TEXT DEFAULT 'CLT', empresa_origem TEXT DEFAULT ''
    );
"""


def _conn():
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.executescript(
        f"""
        CREATE TABLE companies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT, legal_name TEXT DEFAULT '', cnpj TEXT
        );
        CREATE TABLE units (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL, name TEXT
        );
        {_EMPLOYEES_TABLE}
        CREATE TABLE employee_unit_movements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id INTEGER, movement_type TEXT, start_date TEXT, end_date TEXT DEFAULT '',
            target_unit_id INTEGER
        );
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT, company_id INTEGER, role TEXT, linked_employee_id INTEGER
        );
        CREATE TABLE company_audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER, actor_user_id INTEGER, actor_name TEXT,
            action_type TEXT, summary TEXT, created_at TEXT
        );
        """
    )
    conn.execute("INSERT INTO companies (name, legal_name, cnpj) VALUES ('ACME', 'ACME SA', ?)", (CNPJ_A,))
    conn.commit()
    ensure_company_audit_columns(conn)
    ensure_legal_entities(conn)
    return conn


def _add_filial(conn, cnpj=CNPJ_B, name='ACME Filial RJ'):
    return create_legal_entity(conn, {'cnpj': cnpj, 'legal_name': name, 'entity_type': 'filial'}, 1)


def _add_unit(conn, *, legal_entity_id=None, name='Base Santos'):
    cur = conn.execute('INSERT INTO units (company_id, name) VALUES (1, ?)', (name,))
    unit_id = cur.lastrowid
    if legal_entity_id is not None:
        conn.execute('UPDATE units SET legal_entity_id = ? WHERE id = ?', (legal_entity_id, unit_id))
    conn.commit()
    return unit_id


def _add_local_admin(conn, user_id=7, *, unit_id=None):
    # Matrícula distinta por colaborador: ela é NOT NULL e única dentro da
    # empresa (uq_employees_company_employee_code). Dois admins locais com
    # matrícula vazia não existem em produção — o cadastro manual, a importação
    # e o autocadastro exigem o campo (issue #168).
    cur = conn.execute(
        "INSERT INTO employees (id, company_id, unit_id, employee_id_code, name) "
        "VALUES (?, 1, ?, ?, 'Admin Local')",
        (user_id, unit_id, f'ADM-{user_id}'),
    )
    conn.execute(
        "INSERT INTO users (id, username, company_id, role, linked_employee_id) VALUES (?, 'local', 1, 'admin', ?)",
        (user_id, user_id),
    )
    conn.commit()
    return cur.lastrowid


# ── escopo de visibilidade ────────────────────────────────────────────────────

@pytest.mark.parametrize('role', ['master_admin', 'general_admin', 'registry_admin'])
def test_structural_roles_see_all_cnpjs(role):
    conn = _conn()
    _add_filial(conn)
    actor = {'id': 1, 'role': role, 'company_id': 1}
    assert resolve_actor_legal_entity_ids(conn, actor) is None  # sem restrição


def test_local_admin_without_operational_unit_sees_nothing():
    """Sem colaborador vinculado (ainda não provisionado), o escopo fecha —
    nunca abre."""
    conn = _conn()
    _add_filial(conn)
    actor = {'id': 7, 'role': 'admin', 'company_id': 1, 'linked_employee_id': None}
    assert resolve_actor_legal_entity_ids(conn, actor) == []


def test_local_admin_with_unit_without_cnpj_sees_nothing():
    """Unidade sem CNPJ vinculado: nada a resolver automaticamente."""
    conn = _conn()
    _add_filial(conn)
    unit_id = _add_unit(conn, legal_entity_id=None)
    _add_local_admin(conn, unit_id=unit_id)
    actor = {'id': 7, 'role': 'admin', 'company_id': 1, 'linked_employee_id': 7}
    assert resolve_actor_legal_entity_ids(conn, actor) == []


def test_local_admin_cnpj_is_derived_from_managed_unit():
    """O CNPJ nunca é escolhido — é sempre o da única unidade administrada."""
    conn = _conn()
    filial = _add_filial(conn)
    unit_id = _add_unit(conn, legal_entity_id=filial)
    _add_local_admin(conn, unit_id=unit_id)
    actor = {'id': 7, 'role': 'admin', 'company_id': 1, 'linked_employee_id': 7}
    assert resolve_actor_legal_entity_ids(conn, actor) == [filial]


def test_local_admin_scope_follows_unit_not_a_portfolio():
    """Não existe carteira de CNPJs para o Administrador Local: o escopo é
    sempre o CNPJ de uma única unidade, nunca uma lista configurável."""
    conn = _conn()
    matriz = get_default_legal_entity_id(conn, 1)
    filial = _add_filial(conn)
    unit_matriz = _add_unit(conn, legal_entity_id=matriz, name='Matriz')
    unit_filial = _add_unit(conn, legal_entity_id=filial, name='Filial')
    admin_matriz = _add_local_admin(conn, user_id=7, unit_id=unit_matriz)
    admin_filial = _add_local_admin(conn, user_id=8, unit_id=unit_filial)
    actor_matriz = {'id': admin_matriz, 'role': 'admin', 'company_id': 1, 'linked_employee_id': admin_matriz}
    actor_filial = {'id': admin_filial, 'role': 'admin', 'company_id': 1, 'linked_employee_id': admin_filial}
    assert resolve_actor_legal_entity_ids(conn, actor_matriz) == [matriz]
    assert resolve_actor_legal_entity_ids(conn, actor_filial) == [filial]


def test_user_sees_only_own_employee_cnpj():
    conn = _conn()
    filial = _add_filial(conn)
    conn.execute('INSERT INTO employees (id, company_id, unit_id, name, legal_entity_id) VALUES (5, 1, NULL, ?, ?)',
                 ('Ana', filial))
    conn.execute("INSERT INTO users (id, username, company_id, role, linked_employee_id) VALUES (9, 'ana', 1, 'user', 5)")
    conn.commit()
    actor = {'id': 9, 'role': 'user', 'company_id': 1, 'linked_employee_id': 5}
    assert resolve_actor_legal_entity_ids(conn, actor) == [filial]


def test_user_without_linked_employee_sees_nothing():
    conn = _conn()
    actor = {'id': 9, 'role': 'user', 'company_id': 1, 'linked_employee_id': None}
    assert resolve_actor_legal_entity_ids(conn, actor) == []


def test_buyer_and_approver_and_employee_see_no_cnpjs_by_default():
    """Nenhum desses papéis tem escopo de CNPJ definido hoje — o padrão é
    fechado (``[]``), nunca a lista inteira da empresa."""
    conn = _conn()
    _add_filial(conn)
    for role in ('buyer', 'approver', 'employee'):
        actor = {'id': 1, 'role': role, 'company_id': 1}
        assert resolve_actor_legal_entity_ids(conn, actor) == [], role


def test_fetch_legal_entities_applies_user_scope():
    conn = _conn()
    matriz = get_default_legal_entity_id(conn, 1)
    filial = _add_filial(conn)
    conn.execute('INSERT INTO employees (id, company_id, unit_id, name, legal_entity_id) VALUES (5, 1, NULL, ?, ?)',
                 ('Ana', filial))
    conn.commit()
    actor = {'id': 9, 'role': 'user', 'company_id': 1, 'linked_employee_id': 5}
    visible = fetch_legal_entities(conn, actor)
    assert [e['id'] for e in visible] == [filial]
    assert matriz not in [e['id'] for e in visible]


def test_fetch_legal_entities_scopes_local_admin_to_managed_unit():
    """O achado original desta correção: o bootstrap entregava todos os CNPJs
    da empresa ao Administrador Local. Agora entrega só o da unidade dele."""
    conn = _conn()
    matriz = get_default_legal_entity_id(conn, 1)
    filial = _add_filial(conn)
    unit_id = _add_unit(conn, legal_entity_id=filial)
    _add_local_admin(conn, unit_id=unit_id)
    actor = {'id': 7, 'role': 'admin', 'company_id': 1, 'linked_employee_id': 7}
    visible = fetch_legal_entities(conn, actor)
    assert [e['id'] for e in visible] == [filial]
    assert matriz not in [e['id'] for e in visible]


def test_ensure_legal_entity_access_blocks_out_of_scope():
    conn = _conn()
    matriz = get_default_legal_entity_id(conn, 1)
    filial = _add_filial(conn)
    unit_id = _add_unit(conn, legal_entity_id=filial)
    _add_local_admin(conn, unit_id=unit_id)
    actor = {'id': 7, 'role': 'admin', 'company_id': 1, 'linked_employee_id': 7}
    ensure_legal_entity_access(conn, actor, filial)  # não levanta
    with pytest.raises(PermissionError):
        ensure_legal_entity_access(conn, actor, matriz)


# ── CNPJ obrigatório no colaborador ──────────────────────────────────────────

def test_single_cnpj_company_keeps_automatic_fallback():
    conn = _conn()
    assert count_active_legal_entities(conn, 1) == 1
    assert resolve_employee_legal_entity_id(conn, 1, None) == get_default_legal_entity_id(conn, 1)


def test_multi_cnpj_company_requires_explicit_choice():
    conn = _conn()
    _add_filial(conn)
    with pytest.raises(ValueError, match='mais de um CNPJ ativo'):
        resolve_employee_legal_entity_id(conn, 1, None)


def test_multi_cnpj_company_accepts_explicit_choice():
    conn = _conn()
    filial = _add_filial(conn)
    assert resolve_employee_legal_entity_id(conn, 1, filial) == filial


def test_inactive_second_cnpj_restores_fallback():
    """Só CNPJs ativos contam para a obrigatoriedade."""
    conn = _conn()
    filial = _add_filial(conn)
    conn.execute('UPDATE legal_entities SET active = 0 WHERE id = ?', (filial,))
    conn.commit()
    assert resolve_employee_legal_entity_id(conn, 1, None) == get_default_legal_entity_id(conn, 1)


# ── inativação (DELETE) ──────────────────────────────────────────────────────

def test_deactivate_blocks_last_active_cnpj():
    conn = _conn()
    matriz = get_default_legal_entity_id(conn, 1)
    with pytest.raises(ValueError, match='único CNPJ ativo'):
        deactivate_legal_entity(conn, matriz, 1)


def test_deactivate_blocks_when_employees_linked():
    conn = _conn()
    filial = _add_filial(conn)
    conn.execute('INSERT INTO employees (company_id, unit_id, name, legal_entity_id) VALUES (1, NULL, ?, ?)',
                 ('Ana', filial))
    conn.commit()
    with pytest.raises(ValueError, match='colaborador'):
        deactivate_legal_entity(conn, filial, 1)


def test_deactivate_succeeds_and_is_not_physical():
    conn = _conn()
    filial = _add_filial(conn)
    deactivate_legal_entity(conn, filial, 1)
    row = conn.execute('SELECT active FROM legal_entities WHERE id = ?', (filial,)).fetchone()
    assert row is not None          # registro preservado (histórico jurídico)
    assert int(row['active']) == 0  # apenas inativado


def test_deactivate_is_idempotent():
    conn = _conn()
    filial = _add_filial(conn)
    deactivate_legal_entity(conn, filial, 1)
    deactivate_legal_entity(conn, filial, 1)  # não deve levantar
    assert count_active_legal_entities(conn, 1) == 1


def test_deactivate_rejects_entity_from_other_company():
    conn = _conn()
    filial = _add_filial(conn)
    with pytest.raises(ValueError):
        deactivate_legal_entity(conn, filial, 999)


# ── auditoria com CNPJ ───────────────────────────────────────────────────────

def test_company_audit_records_legal_entity():
    from modules.companies.service import register_company_audit
    conn = _conn()
    filial = _add_filial(conn)
    actor = {'id': 1, 'full_name': 'Admin Geral'}
    register_company_audit(conn, 1, actor, 'legal_entity_update', 'CNPJ alterado.',
                           [{'field': 'CNPJ', 'before': 'x', 'after': 'y'}], legal_entity_id=filial)
    row = conn.execute('SELECT legal_entity_id, details_json FROM company_audit_logs').fetchone()
    assert row['legal_entity_id'] == filial
    assert json.loads(row['details_json'])[0]['field'] == 'CNPJ'


def test_company_audit_without_legal_entity_stays_null():
    from modules.companies.service import register_company_audit
    conn = _conn()
    actor = {'id': 1, 'full_name': 'Admin Geral'}
    register_company_audit(conn, 1, actor, 'update', 'Alteração da empresa.')
    row = conn.execute('SELECT legal_entity_id FROM company_audit_logs').fetchone()
    assert row['legal_entity_id'] is None
