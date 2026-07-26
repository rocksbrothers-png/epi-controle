"""Bloco A Multi-CNPJ: escopo por CNPJ, obrigatoriedade, auditoria e inativação.

Cobre as lacunas de conformidade:
  - escopo de visibilidade por CNPJ (Geral/Registro x Administrador Local x
    Usuário), com retrocompatibilidade explícita para quem nunca teve
    autorização atribuída;
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
    fetch_user_legal_entities,
    get_default_legal_entity_id,
    resolve_actor_legal_entity_ids,
    resolve_employee_legal_entity_id,
    set_user_legal_entities,
)

CNPJ_A = '11.222.333/0001-81'
CNPJ_B = '45.723.174/0001-10'
CNPJ_C = '19.131.243/0001-97'


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


# ── escopo de visibilidade ────────────────────────────────────────────────────

@pytest.mark.parametrize('role', ['master_admin', 'general_admin', 'registry_admin'])
def test_structural_roles_see_all_cnpjs(role):
    conn = _conn()
    _add_filial(conn)
    actor = {'id': 1, 'role': role, 'company_id': 1}
    assert resolve_actor_legal_entity_ids(conn, actor) is None  # sem restrição


def test_local_admin_without_authorization_is_unrestricted():
    """Retrocompatibilidade: admin local existente nunca teve autorização
    explícita e não pode perder acesso ao migrar."""
    conn = _conn()
    _add_filial(conn)
    conn.execute("INSERT INTO users (id, username, company_id, role) VALUES (7, 'local', 1, 'admin')")
    conn.commit()
    actor = {'id': 7, 'role': 'admin', 'company_id': 1}
    assert resolve_actor_legal_entity_ids(conn, actor) is None


def test_local_admin_restricted_to_authorized_cnpjs():
    conn = _conn()
    filial = _add_filial(conn)
    conn.execute("INSERT INTO users (id, username, company_id, role) VALUES (7, 'local', 1, 'admin')")
    conn.commit()
    set_user_legal_entities(conn, 7, 1, [filial])
    actor = {'id': 7, 'role': 'admin', 'company_id': 1}
    assert resolve_actor_legal_entity_ids(conn, actor) == [filial]


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


def test_ensure_legal_entity_access_blocks_out_of_scope():
    conn = _conn()
    matriz = get_default_legal_entity_id(conn, 1)
    filial = _add_filial(conn)
    conn.execute("INSERT INTO users (id, username, company_id, role) VALUES (7, 'local', 1, 'admin')")
    conn.commit()
    set_user_legal_entities(conn, 7, 1, [filial])
    actor = {'id': 7, 'role': 'admin', 'company_id': 1}
    ensure_legal_entity_access(conn, actor, filial)  # não levanta
    with pytest.raises(PermissionError):
        ensure_legal_entity_access(conn, actor, matriz)


# ── autorização usuário↔CNPJ ─────────────────────────────────────────────────

def test_set_user_legal_entities_replaces_list():
    conn = _conn()
    matriz = get_default_legal_entity_id(conn, 1)
    filial = _add_filial(conn)
    conn.execute("INSERT INTO users (id, username, company_id, role) VALUES (7, 'local', 1, 'admin')")
    conn.commit()
    set_user_legal_entities(conn, 7, 1, [matriz, filial])
    assert fetch_user_legal_entities(conn, 7) == sorted([matriz, filial])
    set_user_legal_entities(conn, 7, 1, [filial])
    assert fetch_user_legal_entities(conn, 7) == [filial]


def test_empty_authorization_removes_restriction():
    conn = _conn()
    filial = _add_filial(conn)
    conn.execute("INSERT INTO users (id, username, company_id, role) VALUES (7, 'local', 1, 'admin')")
    conn.commit()
    set_user_legal_entities(conn, 7, 1, [filial])
    set_user_legal_entities(conn, 7, 1, [])
    actor = {'id': 7, 'role': 'admin', 'company_id': 1}
    assert resolve_actor_legal_entity_ids(conn, actor) is None


def test_set_user_legal_entities_rejects_other_company_cnpj():
    conn = _conn()
    conn.execute("INSERT INTO companies (name, legal_name, cnpj) VALUES ('OUTRA', 'OUTRA SA', ?)", (CNPJ_C,))
    conn.commit()
    ensure_legal_entities(conn)
    other = get_default_legal_entity_id(conn, 2)
    conn.execute("INSERT INTO users (id, username, company_id, role) VALUES (7, 'local', 1, 'admin')")
    conn.commit()
    with pytest.raises(ValueError):
        set_user_legal_entities(conn, 7, 1, [other])


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
