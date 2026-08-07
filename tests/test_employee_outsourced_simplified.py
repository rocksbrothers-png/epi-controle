"""Cadastro de Colaboradores simplificado — ADR-0002 §10.2/§10.3.

Cobre create_employee_outsourced_simplified/update_employee_outsourced_simplified
(modules.employees.service): campos obrigatórios/opcionais do prompt do
produto, rejeição de vínculo CLT (essa aba nunca cria/edita colaborador
CLT — isso continua exclusivo de create_employee/update_employee),
isolamento multi-tenant, bloqueio de empresa terceirizada arquivada, e o
escopo por Unidade do ator (Administrador Local/Gestor de EPI só operam na
própria unidade operacional — ensure_actor_unit_scope_for_target).

Não testa a autorização por módulo/Unidade (module_unit_scope) nem a rota
HTTP — isso é coberto em tests/test_module_visibility.py e
tests/test_employee_outsourced_simplified_routes.py.
"""

import sqlite3

import pytest

from core.schema import (
    ensure_employee_simplified_registration_columns,
    ensure_legal_entities,
    ensure_outsourced_companies,
    ensure_outsourced_company_unit_links,
    ensure_outsourced_company_archival_lifecycle_columns,
)
from modules.employees.service import (
    create_employee_outsourced_simplified,
    get_employee_by_id,
    update_employee_outsourced_simplified,
)
from modules.outsourced_companies.service import create_outsourced_company, create_service_contract

VALID_CPF = '111.444.777-35'


@pytest.fixture(autouse=True)
def _sqlite_detection(monkeypatch):
    # create_employee_outsourced_simplified/update_employee_outsourced_simplified
    # sempre passam por core.repository (placeholders "%s", via _PgStyleConn) —
    # epi_backend.db._is_sqlite_connection detecta o dialeto pelo nome da
    # classe da conexão, e _PgStyleConn não "parece" sqlite. Sem isto,
    # table_exists/table_columns cairiam no branch Postgres contra um banco
    # SQLite de teste e outsourced_companies_ready() retornaria False
    # silenciosamente. Produção nunca usa este adaptador — só existe em
    # testes (mesmo padrão de test_employee_outsourced_wiring.py).
    import epi_backend.db as db_module
    monkeypatch.setattr(db_module, '_is_sqlite_connection', lambda _conn: True)


def _dict_factory(cursor, row):
    return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}


def _conn():
    conn = sqlite3.connect(':memory:')
    conn.row_factory = _dict_factory
    conn.executescript(
        """
        CREATE TABLE companies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT, legal_name TEXT DEFAULT '', cnpj TEXT, logo_type TEXT DEFAULT ''
        );
        CREATE TABLE units (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL, name TEXT, unit_type TEXT DEFAULT '',
            city TEXT DEFAULT '', notes TEXT DEFAULT ''
        );
        CREATE TABLE employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL, unit_id INTEGER, name TEXT,
            employee_id_code TEXT DEFAULT '', cpf TEXT DEFAULT '', email TEXT DEFAULT '',
            whatsapp TEXT DEFAULT '', preferred_contact_channel TEXT DEFAULT '',
            sector TEXT DEFAULT '', role_name TEXT DEFAULT '', admission_date TEXT DEFAULT '',
            schedule_type TEXT DEFAULT '', tipo_vinculo TEXT DEFAULT 'CLT', empresa_origem TEXT DEFAULT ''
        );
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT, company_id INTEGER, role TEXT
        );
        CREATE TABLE employee_unit_movements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id INTEGER, movement_type TEXT, start_date TEXT, end_date TEXT DEFAULT '',
            target_unit_id INTEGER
        );
        """
    )
    return conn


class _PgStyleConn:
    """Adaptador de teste: traduz placeholders ``%s`` (core.repository) para
    ``?`` (SQLite). Mesmo padrão de test_employee_outsourced_wiring.py."""

    def __init__(self, conn):
        self._conn = conn

    def execute(self, sql, params=()):
        return self._conn.execute(str(sql).replace('%s', '?'), params)

    def commit(self):
        self._conn.commit()

    def __getattr__(self, name):
        return getattr(self._conn, name)


def _bootstrap(conn):
    ensure_legal_entities(conn)
    ensure_outsourced_companies(conn)
    ensure_outsourced_company_unit_links(conn)
    ensure_outsourced_company_archival_lifecycle_columns(conn)
    ensure_employee_simplified_registration_columns(conn)


def _seed_company(conn, name='ACME', cnpj='00.000.000/0001-00'):
    cur = conn.execute('INSERT INTO companies (name, legal_name, cnpj) VALUES (?, ?, ?)', (name, name, cnpj))
    conn.commit()
    return int(cur.lastrowid)


def _seed_unit(conn, company_id, name='Unidade 1'):
    cur = conn.execute('INSERT INTO units (company_id, name) VALUES (?, ?)', (company_id, name))
    conn.commit()
    return int(cur.lastrowid)


def _actor(company_id, role='general_admin', user_id=1, linked_employee_id=None):
    return {'id': user_id, 'role': role, 'company_id': company_id, 'linked_employee_id': linked_employee_id}


def _minimal_payload(company_id, unit_id, outsourced_company_id, **overrides):
    payload = {
        'company_id': company_id,
        'unit_id': unit_id,
        'outsourced_company_id': outsourced_company_id,
        'name': 'Trabalhador Terceirizado',
        'cpf': VALID_CPF,
        'role_name': 'Auxiliar de Obras',
        'tipo_vinculo': 'Terceirizado',
        'admission_date': '2026-01-01',
    }
    payload.update(overrides)
    return payload


# ── campos obrigatórios ─────────────────────────────────────────────────────

@pytest.mark.parametrize('missing', ['name', 'tipo_vinculo', 'role_name', 'admission_date', 'outsourced_company_id', 'unit_id'])
def test_create_rejects_missing_required_field(missing):
    conn = _PgStyleConn(_conn())
    cid = _seed_company(conn)
    _bootstrap(conn)
    unit_id = _seed_unit(conn, cid)
    oc_id = create_outsourced_company(conn, {'legal_name': 'Terceirizada X'}, cid)
    payload = _minimal_payload(cid, unit_id, oc_id)
    payload[missing] = None
    with pytest.raises(ValueError):
        create_employee_outsourced_simplified(conn, payload, actor=_actor(cid))


def test_create_rejects_clt_tipo_vinculo():
    conn = _PgStyleConn(_conn())
    cid = _seed_company(conn)
    _bootstrap(conn)
    unit_id = _seed_unit(conn, cid)
    oc_id = create_outsourced_company(conn, {'legal_name': 'Terceirizada X'}, cid)
    payload = _minimal_payload(cid, unit_id, oc_id, tipo_vinculo='CLT')
    with pytest.raises(ValueError):
        create_employee_outsourced_simplified(conn, payload, actor=_actor(cid))


def test_create_rejects_invalid_cpf():
    conn = _PgStyleConn(_conn())
    cid = _seed_company(conn)
    _bootstrap(conn)
    unit_id = _seed_unit(conn, cid)
    oc_id = create_outsourced_company(conn, {'legal_name': 'Terceirizada X'}, cid)
    payload = _minimal_payload(cid, unit_id, oc_id, cpf='123')
    with pytest.raises(ValueError):
        create_employee_outsourced_simplified(conn, payload, actor=_actor(cid))


# ── criação bem-sucedida ─────────────────────────────────────────────────────

def test_create_succeeds_with_required_and_optional_fields():
    conn = _PgStyleConn(_conn())
    cid = _seed_company(conn)
    _bootstrap(conn)
    unit_id = _seed_unit(conn, cid)
    oc_id = create_outsourced_company(conn, {'legal_name': 'Terceirizada X', 'trade_name': 'TX'}, cid)
    payload = _minimal_payload(
        cid, unit_id, oc_id,
        origin_company_registration='MAT-123',
        badge_number='CRA-456',
        notes='Observação livre.',
    )
    employee_id = create_employee_outsourced_simplified(conn, payload, actor=_actor(cid))
    employee = get_employee_by_id(conn, employee_id)
    assert employee['name'] == 'Trabalhador Terceirizado'
    assert employee['tipo_vinculo'] == 'Terceirizado'
    assert employee['outsourced_company_id'] == oc_id
    assert employee['origin_company_registration'] == 'MAT-123'
    assert employee['badge_number'] == 'CRA-456'
    assert employee['notes'] == 'Observação livre.'
    # empresa_origem (exibida na Ficha de EPI) é populada a partir da
    # empresa terceirizada vinculada — trade_name tem prioridade.
    assert employee['empresa_origem'] == 'TX'
    # employee_id_code é gerado automaticamente (não é campo do formulário).
    assert employee['employee_id_code'].startswith(f'TERC-{cid}-')


def test_create_falls_back_to_legal_name_when_no_trade_name():
    conn = _PgStyleConn(_conn())
    cid = _seed_company(conn)
    _bootstrap(conn)
    unit_id = _seed_unit(conn, cid)
    oc_id = create_outsourced_company(conn, {'legal_name': 'Terceirizada Razão Social'}, cid)
    payload = _minimal_payload(cid, unit_id, oc_id)
    employee_id = create_employee_outsourced_simplified(conn, payload, actor=_actor(cid))
    employee = get_employee_by_id(conn, employee_id)
    assert employee['empresa_origem'] == 'Terceirizada Razão Social'


def test_create_optional_fields_default_to_empty():
    conn = _PgStyleConn(_conn())
    cid = _seed_company(conn)
    _bootstrap(conn)
    unit_id = _seed_unit(conn, cid)
    oc_id = create_outsourced_company(conn, {'legal_name': 'Terceirizada X'}, cid)
    employee_id = create_employee_outsourced_simplified(conn, _minimal_payload(cid, unit_id, oc_id), actor=_actor(cid))
    employee = get_employee_by_id(conn, employee_id)
    assert employee['origin_company_registration'] == ''
    assert employee['badge_number'] == ''
    assert employee['notes'] == ''


def test_create_links_service_contract_matching_company():
    conn = _PgStyleConn(_conn())
    cid = _seed_company(conn)
    _bootstrap(conn)
    unit_id = _seed_unit(conn, cid)
    oc_id = create_outsourced_company(conn, {'legal_name': 'Terceirizada X'}, cid)
    contract_id = create_service_contract(conn, {'service_order_ref': 'OS-1'}, cid, oc_id)
    payload = _minimal_payload(cid, unit_id, oc_id, service_contract_id=contract_id)
    employee_id = create_employee_outsourced_simplified(conn, payload, actor=_actor(cid))
    employee = get_employee_by_id(conn, employee_id)
    assert employee['service_contract_id'] == contract_id


def test_create_rejects_service_contract_from_another_outsourced_company():
    conn = _PgStyleConn(_conn())
    cid = _seed_company(conn)
    _bootstrap(conn)
    unit_id = _seed_unit(conn, cid)
    oc_id_1 = create_outsourced_company(conn, {'legal_name': 'Terceirizada 1'}, cid)
    oc_id_2 = create_outsourced_company(conn, {'legal_name': 'Terceirizada 2'}, cid)
    contract_id = create_service_contract(conn, {}, cid, oc_id_1)
    payload = _minimal_payload(cid, unit_id, oc_id_2, service_contract_id=contract_id)
    with pytest.raises(ValueError):
        create_employee_outsourced_simplified(conn, payload, actor=_actor(cid))


# ── isolamento multi-tenant ──────────────────────────────────────────────────

def test_create_rejects_outsourced_company_from_another_tenant():
    conn = _PgStyleConn(_conn())
    cid_a = _seed_company(conn, name='Tenant A')
    cid_b = _seed_company(conn, name='Tenant B')
    _bootstrap(conn)
    unit_id_a = _seed_unit(conn, cid_a)
    oc_id_b = create_outsourced_company(conn, {'legal_name': 'Terceirizada de B'}, cid_b)
    payload = _minimal_payload(cid_a, unit_id_a, oc_id_b)
    with pytest.raises(ValueError):
        create_employee_outsourced_simplified(conn, payload, actor=_actor(cid_a))


def test_create_rejects_unit_from_another_tenant():
    conn = _PgStyleConn(_conn())
    cid_a = _seed_company(conn, name='Tenant A')
    cid_b = _seed_company(conn, name='Tenant B')
    _bootstrap(conn)
    unit_id_b = _seed_unit(conn, cid_b)
    oc_id_a = create_outsourced_company(conn, {'legal_name': 'Terceirizada de A'}, cid_a)
    payload = _minimal_payload(cid_a, unit_id_b, oc_id_a)
    with pytest.raises(PermissionError):
        create_employee_outsourced_simplified(conn, payload, actor=_actor(cid_a))


# ── empresa terceirizada arquivada bloqueia novo vínculo (ADR-0002 §10.4) ────

def test_create_rejects_archived_outsourced_company():
    conn = _PgStyleConn(_conn())
    cid = _seed_company(conn)
    _bootstrap(conn)
    unit_id = _seed_unit(conn, cid)
    oc_id = create_outsourced_company(conn, {'legal_name': 'Terceirizada X'}, cid)
    conn.execute("UPDATE outsourced_companies SET status = 'archived' WHERE id = %s", (oc_id,))
    conn.commit()
    payload = _minimal_payload(cid, unit_id, oc_id)
    with pytest.raises(ValueError):
        create_employee_outsourced_simplified(conn, payload, actor=_actor(cid))


# ── escopo por Unidade do ator (Administrador Local/Gestor de EPI) ─────────

def test_create_ignores_spoofed_unit_id_for_admin_role_outside_operational_unit():
    """resolve_employee_outsourced_unit_id ignora por completo o unit_id do
    payload para Administrador Local/Gestor de EPI — não é mais "aceita e
    depois rejeita se não bater", é "nunca confia no payload": o campo
    Unidade do formulário fica `disabled` na tela para estes perfis e
    `FormData` nunca inclui campos `disabled`, então o payload real que
    chega do navegador não tem unit_id algum. Testar com unit_id_other
    ainda vale — prova que mesmo um payload malicioso/manual com uma
    Unidade estranha não desvia o colaborador para lá; ele sempre cai na
    própria unidade operacional do ator."""
    conn = _PgStyleConn(_conn())
    cid = _seed_company(conn)
    _bootstrap(conn)
    unit_id_op = _seed_unit(conn, cid, name='Unidade do Administrador Local')
    unit_id_other = _seed_unit(conn, cid, name='Outra Unidade')
    oc_id = create_outsourced_company(conn, {'legal_name': 'Terceirizada X'}, cid)
    # actor 'admin' vinculado a um colaborador cuja unidade é unit_id_op.
    linked_cur = conn.execute(
        "INSERT INTO employees (company_id, unit_id, name) VALUES (%s, %s, 'Local Admin')",
        (cid, unit_id_op),
    )
    linked_employee_id = int(linked_cur.lastrowid)
    actor = _actor(cid, role='admin', linked_employee_id=linked_employee_id)
    payload = _minimal_payload(cid, unit_id_other, oc_id)
    employee_id = create_employee_outsourced_simplified(conn, payload, actor=actor)
    row = conn.execute('SELECT unit_id FROM employees WHERE id = %s', (employee_id,)).fetchone()
    assert int(row['unit_id']) == unit_id_op


def test_create_blocked_for_admin_role_without_operational_unit():
    """Sem unidade operacional ativa, o resolver recusa antes de chegar
    a qualquer unit_id — nem o próprio, nem um de terceiros."""
    conn = _PgStyleConn(_conn())
    cid = _seed_company(conn)
    _bootstrap(conn)
    unit_id_other = _seed_unit(conn, cid, name='Outra Unidade')
    oc_id = create_outsourced_company(conn, {'legal_name': 'Terceirizada X'}, cid)
    actor = _actor(cid, role='admin', linked_employee_id=None)
    payload = _minimal_payload(cid, unit_id_other, oc_id)
    with pytest.raises(PermissionError):
        create_employee_outsourced_simplified(conn, payload, actor=actor)


def test_create_allowed_for_admin_role_inside_operational_unit():
    conn = _PgStyleConn(_conn())
    cid = _seed_company(conn)
    _bootstrap(conn)
    unit_id_op = _seed_unit(conn, cid, name='Unidade do Administrador Local')
    oc_id = create_outsourced_company(conn, {'legal_name': 'Terceirizada X'}, cid)
    linked_cur = conn.execute(
        "INSERT INTO employees (company_id, unit_id, name) VALUES (%s, %s, 'Local Admin')",
        (cid, unit_id_op),
    )
    linked_employee_id = int(linked_cur.lastrowid)
    actor = _actor(cid, role='admin', linked_employee_id=linked_employee_id)
    payload = _minimal_payload(cid, unit_id_op, oc_id)
    employee_id = create_employee_outsourced_simplified(conn, payload, actor=actor)
    assert employee_id


@pytest.mark.parametrize('role', ['admin', 'user'])
def test_create_resolves_unit_id_automatically_when_absent_from_payload(role):
    """Reproduz o bug real: o campo Unidade fica `disabled` na tela para
    Administrador Local/Gestor de EPI, e campos `disabled` nunca são
    incluídos por FormData — o payload que o navegador envia não tem
    unit_id nenhum (chave ausente, não vazia). Antes da correção isso
    batia em "Unidade é obrigatória." mesmo com a Unidade certa visível
    na tela; agora o backend resolve pela sessão do ator."""
    conn = _PgStyleConn(_conn())
    cid = _seed_company(conn)
    _bootstrap(conn)
    unit_id_op = _seed_unit(conn, cid, name='Unidade Operacional')
    oc_id = create_outsourced_company(conn, {'legal_name': 'Terceirizada X'}, cid)
    linked_cur = conn.execute(
        "INSERT INTO employees (company_id, unit_id, name) VALUES (%s, %s, 'Vínculo do ator')",
        (cid, unit_id_op),
    )
    linked_employee_id = int(linked_cur.lastrowid)
    actor = _actor(cid, role=role, linked_employee_id=linked_employee_id)
    payload = _minimal_payload(cid, unit_id_op, oc_id)
    del payload['unit_id']
    assert 'unit_id' not in payload
    employee_id = create_employee_outsourced_simplified(conn, payload, actor=actor)
    row = conn.execute('SELECT unit_id FROM employees WHERE id = %s', (employee_id,)).fetchone()
    assert int(row['unit_id']) == unit_id_op


def test_create_still_requires_explicit_unit_id_for_unrestricted_profile():
    """Administrador Geral/de Registro não têm unidade operacional única —
    o campo Unidade continua livre (não `disabled`) na tela para eles, e o
    backend continua exigindo que o payload informe qual Unidade."""
    conn = _PgStyleConn(_conn())
    cid = _seed_company(conn)
    _bootstrap(conn)
    unit_id = _seed_unit(conn, cid)
    oc_id = create_outsourced_company(conn, {'legal_name': 'Terceirizada X'}, cid)
    payload = _minimal_payload(cid, unit_id, oc_id)
    del payload['unit_id']
    with pytest.raises(ValueError):
        create_employee_outsourced_simplified(conn, payload, actor=_actor(cid, role='general_admin'))


# ── update ────────────────────────────────────────────────────────────────

def test_update_succeeds_and_changes_fields():
    conn = _PgStyleConn(_conn())
    cid = _seed_company(conn)
    _bootstrap(conn)
    unit_id = _seed_unit(conn, cid)
    oc_id = create_outsourced_company(conn, {'legal_name': 'Terceirizada X'}, cid)
    employee_id = create_employee_outsourced_simplified(
        conn, _minimal_payload(cid, unit_id, oc_id), actor=_actor(cid),
    )
    update_payload = _minimal_payload(
        cid, unit_id, oc_id, name='Nome Atualizado', badge_number='CRA-999',
    )
    update_employee_outsourced_simplified(conn, employee_id, update_payload, actor=_actor(cid))
    employee = get_employee_by_id(conn, employee_id)
    assert employee['name'] == 'Nome Atualizado'
    assert employee['badge_number'] == 'CRA-999'


def test_update_rejects_employee_from_another_tenant():
    conn = _PgStyleConn(_conn())
    cid_a = _seed_company(conn, name='Tenant A')
    cid_b = _seed_company(conn, name='Tenant B')
    _bootstrap(conn)
    unit_id_a = _seed_unit(conn, cid_a)
    oc_id_a = create_outsourced_company(conn, {'legal_name': 'Terceirizada de A'}, cid_a)
    employee_id = create_employee_outsourced_simplified(
        conn, _minimal_payload(cid_a, unit_id_a, oc_id_a), actor=_actor(cid_a),
    )
    update_payload = _minimal_payload(cid_a, unit_id_a, oc_id_a, name='Tentativa de Tenant B')
    with pytest.raises(PermissionError):
        update_employee_outsourced_simplified(conn, employee_id, update_payload, actor=_actor(cid_b))


def test_update_rejects_employee_that_is_clt():
    conn = _PgStyleConn(_conn())
    cid = _seed_company(conn)
    _bootstrap(conn)
    unit_id = _seed_unit(conn, cid)
    clt_cur = conn.execute(
        "INSERT INTO employees (company_id, unit_id, name, tipo_vinculo) VALUES (%s, %s, 'Fulano CLT', 'CLT')",
        (cid, unit_id),
    )
    clt_employee_id = int(clt_cur.lastrowid)
    oc_id = create_outsourced_company(conn, {'legal_name': 'Terceirizada X'}, cid)
    update_payload = _minimal_payload(cid, unit_id, oc_id)
    with pytest.raises(PermissionError):
        update_employee_outsourced_simplified(conn, clt_employee_id, update_payload, actor=_actor(cid))


def test_update_can_move_employee_to_another_unit_within_tenant():
    conn = _PgStyleConn(_conn())
    cid = _seed_company(conn)
    _bootstrap(conn)
    unit_id_1 = _seed_unit(conn, cid, name='Unidade 1')
    unit_id_2 = _seed_unit(conn, cid, name='Unidade 2')
    oc_id = create_outsourced_company(conn, {'legal_name': 'Terceirizada X'}, cid)
    employee_id = create_employee_outsourced_simplified(
        conn, _minimal_payload(cid, unit_id_1, oc_id), actor=_actor(cid),
    )
    update_payload = _minimal_payload(cid, unit_id_2, oc_id)
    update_employee_outsourced_simplified(conn, employee_id, update_payload, actor=_actor(cid))
    employee = get_employee_by_id(conn, employee_id)
    assert employee['unit_id'] == unit_id_2


@pytest.mark.parametrize('role', ['admin', 'user'])
def test_update_resolves_unit_id_automatically_when_absent_from_payload(role):
    """Mesmo bug do create, reproduzido na edição: o campo Unidade também
    fica `disabled` no formulário de edição para estes perfis."""
    conn = _PgStyleConn(_conn())
    cid = _seed_company(conn)
    _bootstrap(conn)
    unit_id_op = _seed_unit(conn, cid, name='Unidade Operacional')
    oc_id = create_outsourced_company(conn, {'legal_name': 'Terceirizada X'}, cid)
    linked_cur = conn.execute(
        "INSERT INTO employees (company_id, unit_id, name) VALUES (%s, %s, 'Vínculo do ator')",
        (cid, unit_id_op),
    )
    linked_employee_id = int(linked_cur.lastrowid)
    actor = _actor(cid, role=role, linked_employee_id=linked_employee_id)
    employee_id = create_employee_outsourced_simplified(
        conn, _minimal_payload(cid, unit_id_op, oc_id), actor=actor,
    )
    update_payload = _minimal_payload(cid, unit_id_op, oc_id, name='Nome Atualizado')
    del update_payload['unit_id']
    assert 'unit_id' not in update_payload
    update_employee_outsourced_simplified(conn, employee_id, update_payload, actor=actor)
    employee = get_employee_by_id(conn, employee_id)
    assert employee['unit_id'] == unit_id_op
    assert employee['name'] == 'Nome Atualizado'
