"""Auditoria e correção do módulo Terceirizados e Prestadores (Prompt do
usuário desta sessão — 4 problemas):

1. unit_id não chegava no payload de Cadastro de Colaboradores para
   Administrador Local/Gestor de EPI (campo Unidade `disabled` no
   formulário, FormData nunca inclui campos `disabled`) — resolvido pelo
   backend via `resolve_employee_outsourced_unit_id` (ver
   test_employee_outsourced_simplified.py::test_create_resolves_unit_id_automatically_when_absent_from_payload).
2. Arquivamento da Empresa Terceirizada por Unidade — "Desativar vínculo
   local" (`outsourced_company_unit_links.local_status`) JÁ é o
   arquivamento por Unidade pedido (Problema 4): não afeta outras
   Unidades, não exclui/duplica nada, é reversível. Este arquivo cobre o
   que faltava estar de fato ligado a ele.
3. Empresa arquivada nesta Unidade não pode continuar aparecendo no
   seletor de Empresa Terceirizada/Prestadora do Cadastro de Colaborador
   DESSA Unidade — `is_outsourced_company_available_to_unit` passa a
   também considerar `local_status`.
4. Confirma que não foi criado nenhum conceito novo: mesma tabela
   `outsourced_company_unit_links`, mesmas funções de serviço
   (`set_outsourced_company_unit_link_status`) já cobertas em
   test_outsourced_company_unit_sharing.py.
"""

import sqlite3

import pytest

from core.schema import (
    ensure_legal_entities,
    ensure_outsourced_companies,
    ensure_outsourced_company_archival_lifecycle_columns,
    ensure_outsourced_company_unit_links,
    ensure_outsourced_company_update_requests,
)
from modules.employees.service import create_employee_outsourced_simplified
from modules.outsourced_companies.service import (
    create_outsourced_company,
    create_outsourced_company_unit_link,
    fetch_outsourced_company_unit_link,
    get_outsourced_company_by_id,
    is_outsourced_company_available_to_unit,
    set_outsourced_company_unit_link_status,
)


def _dict_factory(cursor, row):
    return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}


class _PgStyleConn:
    def __init__(self, conn):
        self._conn = conn

    def execute(self, sql, params=()):
        return self._conn.execute(str(sql).replace('%s', '?'), params)

    def commit(self):
        self._conn.commit()

    def __getattr__(self, name):
        return getattr(self._conn, name)


def _conn():
    conn = sqlite3.connect(':memory:')
    conn.row_factory = _dict_factory
    conn.executescript(
        """
        CREATE TABLE companies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT, legal_name TEXT DEFAULT '', cnpj TEXT, logo_type TEXT DEFAULT '',
            user_limit INTEGER NOT NULL DEFAULT 999, license_status TEXT NOT NULL DEFAULT 'active',
            active INTEGER NOT NULL DEFAULT 1, contract_end TEXT, addendum_enabled INTEGER NOT NULL DEFAULT 0
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
            schedule_type TEXT DEFAULT '', tipo_vinculo TEXT DEFAULT 'CLT', empresa_origem TEXT DEFAULT '',
            outsourced_company_id INTEGER, service_contract_id INTEGER,
            epi_responsibility_override TEXT DEFAULT '', epi_responsibility_override_reason TEXT DEFAULT '',
            origin_company_registration TEXT DEFAULT '', badge_number TEXT DEFAULT '', notes TEXT DEFAULT '',
            status TEXT NOT NULL DEFAULT 'active'
        );
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT, password TEXT DEFAULT '', company_id INTEGER, role TEXT, full_name TEXT DEFAULT '',
            active INTEGER NOT NULL DEFAULT 1, linked_employee_id INTEGER
        );
        CREATE TABLE employee_unit_movements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id INTEGER, movement_type TEXT, start_date TEXT, end_date TEXT DEFAULT '',
            target_unit_id INTEGER
        );
        CREATE TABLE company_audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT, company_id INTEGER NOT NULL,
            actor_user_id INTEGER NOT NULL, actor_name TEXT NOT NULL, action_type TEXT NOT NULL,
            summary TEXT NOT NULL, details_json TEXT NOT NULL DEFAULT '[]', created_at TEXT NOT NULL
        );
        CREATE TABLE app_meta (key TEXT PRIMARY KEY, value TEXT);
        """
    )
    return conn


def _bootstrap(conn):
    ensure_legal_entities(conn)
    ensure_outsourced_companies(conn)
    ensure_outsourced_company_unit_links(conn)
    ensure_outsourced_company_update_requests(conn)
    ensure_outsourced_company_archival_lifecycle_columns(conn)


def _seed_company(conn, name='ACME'):
    cur = conn.execute('INSERT INTO companies (name, legal_name, cnpj) VALUES (?, ?, ?)', (name, name, ''))
    conn.commit()
    return int(cur.lastrowid)


def _seed_unit(conn, company_id, name='Unidade'):
    cur = conn.execute('INSERT INTO units (company_id, name) VALUES (?, ?)', (company_id, name))
    conn.commit()
    return int(cur.lastrowid)


def _actor(company_id, role='general_admin', user_id=1, linked_employee_id=None):
    return {'id': user_id, 'role': role, 'company_id': company_id, 'linked_employee_id': linked_employee_id}


@pytest.fixture(autouse=True)
def _sqlite_detection(monkeypatch):
    import epi_backend.db as db_module
    monkeypatch.setattr(db_module, '_is_sqlite_connection', lambda _conn: True)


@pytest.fixture
def scoped_units(monkeypatch):
    import core.repository as repository
    mapping = {}

    def _fake(_connection, actor):
        return mapping.get(actor.get('id'))

    monkeypatch.setattr(repository, 'actor_operational_unit_id', _fake)
    return mapping


def _minimal_employee_payload(company_id, outsourced_company_id, **overrides):
    payload = {
        'company_id': company_id,
        'outsourced_company_id': outsourced_company_id,
        'name': 'Trabalhador Terceirizado',
        'cpf': '111.444.777-35',
        'role_name': 'Auxiliar',
        'tipo_vinculo': 'Terceirizado',
        'admission_date': '2026-01-01',
    }
    payload.update(overrides)
    return payload


# ── Problema 3: seletor/referência respeita o arquivamento por Unidade ────

def test_archiving_in_unit_hides_company_from_reference_availability():
    conn = _PgStyleConn(_conn())
    cid = _seed_company(conn)
    _bootstrap(conn)
    unit_a = _seed_unit(conn, cid, 'Unidade A')
    entity_id = create_outsourced_company(conn, {'legal_name': 'Alfa'}, cid, unit_id=unit_a)
    entity = get_outsourced_company_by_id(conn, entity_id)
    assert is_outsourced_company_available_to_unit(conn, entity, unit_a) is True

    link = fetch_outsourced_company_unit_link(conn, entity_id, unit_a)
    set_outsourced_company_unit_link_status(conn, link['id'], cid, 'inactive', 1, reason='Fim de contrato')
    assert is_outsourced_company_available_to_unit(conn, entity, unit_a) is False


def test_unarchiving_in_unit_restores_reference_availability():
    conn = _PgStyleConn(_conn())
    cid = _seed_company(conn)
    _bootstrap(conn)
    unit_a = _seed_unit(conn, cid, 'Unidade A')
    entity_id = create_outsourced_company(conn, {'legal_name': 'Alfa'}, cid, unit_id=unit_a)
    entity = get_outsourced_company_by_id(conn, entity_id)
    link = fetch_outsourced_company_unit_link(conn, entity_id, unit_a)
    set_outsourced_company_unit_link_status(conn, link['id'], cid, 'inactive', 1)
    assert is_outsourced_company_available_to_unit(conn, entity, unit_a) is False

    set_outsourced_company_unit_link_status(conn, link['id'], cid, 'active', 1)
    assert is_outsourced_company_available_to_unit(conn, entity, unit_a) is True


def test_create_employee_rejects_company_archived_in_actors_unit():
    """Tentativa de cadastrar colaborador em empresa arquivada nesta
    Unidade retorna erro consistente (ValueError, mesma mensagem de
    "empresa não vinculada" — a empresa arquivada nesta Unidade se
    comporta, para fins de referência, como não vinculada a ela)."""
    conn = _PgStyleConn(_conn())
    cid = _seed_company(conn)
    _bootstrap(conn)
    unit_a = _seed_unit(conn, cid, 'Unidade A')
    entity_id = create_outsourced_company(conn, {'legal_name': 'Alfa'}, cid, unit_id=unit_a)
    link = fetch_outsourced_company_unit_link(conn, entity_id, unit_a)
    set_outsourced_company_unit_link_status(conn, link['id'], cid, 'inactive', 1)

    payload = _minimal_employee_payload(cid, entity_id, unit_id=unit_a)
    with pytest.raises(ValueError, match='não está vinculada'):
        create_employee_outsourced_simplified(conn, payload, actor=_actor(cid))


def test_create_employee_succeeds_again_after_unarchiving():
    conn = _PgStyleConn(_conn())
    cid = _seed_company(conn)
    _bootstrap(conn)
    unit_a = _seed_unit(conn, cid, 'Unidade A')
    entity_id = create_outsourced_company(conn, {'legal_name': 'Alfa'}, cid, unit_id=unit_a)
    link = fetch_outsourced_company_unit_link(conn, entity_id, unit_a)
    set_outsourced_company_unit_link_status(conn, link['id'], cid, 'inactive', 1)
    set_outsourced_company_unit_link_status(conn, link['id'], cid, 'active', 1)

    payload = _minimal_employee_payload(cid, entity_id, unit_id=unit_a)
    employee_id = create_employee_outsourced_simplified(conn, payload, actor=_actor(cid))
    assert employee_id


# ── Isolamento entre Unidades (arquivar nunca é global) ────────────────────

def test_archiving_in_one_unit_does_not_affect_another_units_availability():
    """Unidade A arquiva; Unidade B, com vínculo próprio ativo, continua
    enxergando a mesma empresa normalmente — nunca um efeito colateral
    entre Unidades (Problema 2 do pedido: "arquivamento é por Unidade,
    nunca global")."""
    conn = _PgStyleConn(_conn())
    cid = _seed_company(conn)
    _bootstrap(conn)
    unit_a = _seed_unit(conn, cid, 'Unidade A')
    unit_b = _seed_unit(conn, cid, 'Unidade B')
    entity_id = create_outsourced_company(conn, {'legal_name': 'Alfa'}, cid, unit_id=unit_a)
    create_outsourced_company_unit_link(conn, entity_id, cid, unit_b, 2)
    entity = get_outsourced_company_by_id(conn, entity_id)

    link_a = fetch_outsourced_company_unit_link(conn, entity_id, unit_a)
    set_outsourced_company_unit_link_status(conn, link_a['id'], cid, 'inactive', 1)

    assert is_outsourced_company_available_to_unit(conn, entity, unit_a) is False
    assert is_outsourced_company_available_to_unit(conn, entity, unit_b) is True
    link_b = fetch_outsourced_company_unit_link(conn, entity_id, unit_b)
    assert link_b['local_status'] == 'active'


def test_archiving_in_unit_does_not_delete_or_duplicate_company_record():
    """Arquivar nunca exclui nem duplica o cadastro corporativo — só o
    vínculo local muda de estado."""
    conn = _PgStyleConn(_conn())
    cid = _seed_company(conn)
    _bootstrap(conn)
    unit_a = _seed_unit(conn, cid, 'Unidade A')
    entity_id = create_outsourced_company(conn, {'legal_name': 'Alfa', 'cnpj': '11.222.333/0001-81'}, cid, unit_id=unit_a)
    link = fetch_outsourced_company_unit_link(conn, entity_id, unit_a)
    set_outsourced_company_unit_link_status(conn, link['id'], cid, 'inactive', 1)

    entity = get_outsourced_company_by_id(conn, entity_id)
    assert entity is not None
    assert entity['legal_name'] == 'Alfa'
    assert entity['status'] == 'active'  # corporativo nunca é tocado
    count = conn.execute(
        'SELECT COUNT(*) AS n FROM outsourced_companies WHERE cnpj_normalized = ?',
        (entity['cnpj_normalized'],),
    ).fetchone()
    assert count['n'] == 1


def test_archiving_in_unit_does_not_affect_already_linked_employees():
    """Colaboradores já cadastrados contra a empresa permanecem íntegros
    (nome, vínculo, referência) depois que a Unidade arquiva a empresa —
    só bloqueia NOVOS cadastros, nunca desfaz o que já existe."""
    conn = _PgStyleConn(_conn())
    cid = _seed_company(conn)
    _bootstrap(conn)
    unit_a = _seed_unit(conn, cid, 'Unidade A')
    entity_id = create_outsourced_company(conn, {'legal_name': 'Alfa'}, cid, unit_id=unit_a)
    payload = _minimal_employee_payload(cid, entity_id, unit_id=unit_a)
    employee_id = create_employee_outsourced_simplified(conn, payload, actor=_actor(cid))

    link = fetch_outsourced_company_unit_link(conn, entity_id, unit_a)
    set_outsourced_company_unit_link_status(conn, link['id'], cid, 'inactive', 1)

    row = conn.execute('SELECT * FROM employees WHERE id = ?', (employee_id,)).fetchone()
    assert row is not None
    assert row['name'] == 'Trabalhador Terceirizado'
    assert int(row['outsourced_company_id']) == entity_id
    assert row['status'] == 'active'


# ── unit_id automático no Cadastro de Colaboradores (Problema 1) ──────────
# Cobertura principal em test_employee_outsourced_simplified.py — aqui só a
# combinação com arquivamento por Unidade, específica deste round.

def test_scoped_actor_without_unit_id_in_payload_still_respects_archival(scoped_units):
    """resolve_employee_outsourced_unit_id resolve o unit_id mesmo sem o
    campo no payload (Problema 1) — e o resultado ainda passa pela mesma
    checagem de disponibilidade (Problema 3): a trava por arquivamento não
    é enfraquecida pela correção de unit_id automático."""
    conn = _PgStyleConn(_conn())
    cid = _seed_company(conn)
    _bootstrap(conn)
    unit_a = _seed_unit(conn, cid, 'Unidade A')
    entity_id = create_outsourced_company(conn, {'legal_name': 'Alfa'}, cid, unit_id=unit_a)
    link = fetch_outsourced_company_unit_link(conn, entity_id, unit_a)
    set_outsourced_company_unit_link_status(conn, link['id'], cid, 'inactive', 1)

    linked_cur = conn.execute(
        "INSERT INTO employees (company_id, unit_id, name) VALUES (?, ?, 'Vínculo do ator')",
        (cid, unit_a),
    )
    actor = _actor(cid, role='admin', linked_employee_id=int(linked_cur.lastrowid))
    scoped_units[1] = unit_a

    payload = _minimal_employee_payload(cid, entity_id)
    assert 'unit_id' not in payload
    with pytest.raises(ValueError, match='não está vinculada'):
        create_employee_outsourced_simplified(conn, payload, actor=actor)
