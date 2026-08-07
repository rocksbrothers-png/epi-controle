"""Cadastro Simplificado de Terceirizados e Prestadores — PR 3 (ADR-0002).

Cobre a wiring do lado do colaborador: ``create_employee``/``update_employee``
aceitam, opcionalmente, ``outsourced_company_id``/``service_contract_id``/
``epi_responsibility_override(_reason)`` — validados por
``modules.outsourced_companies.service.validate_employee_outsourced_reference``
— e ``get_employee_by_id``/``fetch_employees`` devolvem essas colunas.

Não testa o endpoint HTTP (isso já é coberto por ``core.repository.authorize_action``
em outros testes) — foco na camada de serviço, isolamento multi-tenant e
retrocompatibilidade (colaborador CLT sem nenhum campo novo continua
funcionando exatamente como antes).
"""

import sqlite3

import pytest

from core.schema import ensure_legal_entities, ensure_outsourced_companies, ensure_outsourced_company_unit_links
from modules.employees.service import create_employee, get_employee_by_id, fetch_employees, update_employee
from modules.outsourced_companies.service import create_outsourced_company, create_service_contract

CNPJ_A = '11.222.333/0001-81'


def _dict_factory(cursor, row):
    return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}


def _conn():
    conn = sqlite3.connect(':memory:')
    # dict-like rows (com .get()), não sqlite3.Row: core.auth.ensure_resource_company
    # e outras funções de produção assumem o mapping-like DictRow do psycopg2
    # (Postgres real). sqlite3.Row não tem .get(); o dict puro tem.
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


def _seed_company(conn, name='ACME', cnpj='00.000.000/0001-00'):
    cur = conn.execute('INSERT INTO companies (name, legal_name, cnpj) VALUES (?, ?, ?)', (name, name, cnpj))
    conn.commit()
    return int(cur.lastrowid)


def _bootstrap(conn):
    ensure_legal_entities(conn)
    ensure_outsourced_companies(conn)
    ensure_outsourced_company_unit_links(conn)


def _actor(company_id, role='general_admin', user_id=1):
    return {'id': user_id, 'role': role, 'company_id': company_id}


class _PgStyleConn:
    """Adaptador de teste: traduz os placeholders ``%s`` (estilo Postgres,
    usados em ``core.repository`` — ``update_employee`` busca o colaborador/
    unidade atuais por lá) para ``?`` do SQLite. Em produção quem faz essa
    normalização é o ``PostgresConnectionWrapper``. Mesmo padrão de
    ``tests/test_employee_legal_entity_immutability.py``."""

    def __init__(self, conn):
        self._conn = conn

    def execute(self, sql, params=()):
        return self._conn.execute(str(sql).replace('%s', '?'), params)

    def __getattr__(self, name):
        return getattr(self._conn, name)


def _minimal_payload(company_id, **overrides):
    # unit_id omitido de propósito: create_employee resolve/cria a unidade
    # padrão via SQL com placeholder '?', compatível com SQLite. Passar
    # unit_id explícito acionaria core.repository.get_unit_by_id, que usa
    # placeholder '%s' (só Postgres) — fora do escopo deste teste de serviço.
    payload = {
        'company_id': company_id,
        'employee_id_code': 'E1',
        'cpf': '111.444.777-35',
        'name': 'Trabalhador Teste',
        'email': '',
        'whatsapp': '',
        'preferred_contact_channel': 'whatsapp',
        'sector': 'Operações',
        'role_name': 'Auxiliar',
        'admission_date': '2026-01-01',
        'schedule_type': 'integral',
        'tipo_vinculo': 'Terceirizado',
        'empresa_origem': '',
    }
    payload.update(overrides)
    return payload


# ── retrocompatibilidade: CLT sem nenhum campo novo ────────────────────────

def test_create_employee_clt_without_outsourced_fields_still_works():
    conn = _conn()
    cid = _seed_company(conn)
    _bootstrap(conn)
    payload = _minimal_payload(cid, tipo_vinculo='CLT')
    employee_id = create_employee(conn, payload, actor=_actor(cid))
    employee = get_employee_by_id(conn, employee_id)
    assert employee['outsourced_company_id'] is None
    assert employee['service_contract_id'] is None
    assert employee['epi_responsibility_override'] == ''


# ── criação com vínculo a empresa terceirizada ─────────────────────────────

def test_create_employee_with_outsourced_company_same_tenant():
    conn = _conn()
    cid = _seed_company(conn)
    _bootstrap(conn)
    oc_id = create_outsourced_company(conn, {'legal_name': 'Terceirizada X'}, cid)
    payload = _minimal_payload(cid, outsourced_company_id=oc_id)
    employee_id = create_employee(conn, payload, actor=_actor(cid))
    employee = get_employee_by_id(conn, employee_id)
    assert employee['outsourced_company_id'] == oc_id


def test_create_employee_rejects_outsourced_company_from_another_tenant():
    conn = _conn()
    cid_a = _seed_company(conn, name='Tenant A')
    cid_b = _seed_company(conn, name='Tenant B')
    _bootstrap(conn)
    oc_id_b = create_outsourced_company(conn, {'legal_name': 'Terceirizada de B'}, cid_b)
    payload = _minimal_payload(cid_a, outsourced_company_id=oc_id_b)
    with pytest.raises(ValueError):
        create_employee(conn, payload, actor=_actor(cid_a))


def test_create_employee_with_service_contract_requires_matching_outsourced_company():
    conn = _conn()
    cid = _seed_company(conn)
    _bootstrap(conn)
    oc_id_1 = create_outsourced_company(conn, {'legal_name': 'Terceirizada 1'}, cid)
    oc_id_2 = create_outsourced_company(conn, {'legal_name': 'Terceirizada 2'}, cid)
    contract_id = create_service_contract(conn, {}, cid, oc_id_1)
    payload = _minimal_payload(cid, outsourced_company_id=oc_id_2, service_contract_id=contract_id)
    with pytest.raises(ValueError):
        create_employee(conn, payload, actor=_actor(cid))


def test_create_employee_with_matching_service_contract_succeeds():
    conn = _conn()
    cid = _seed_company(conn)
    _bootstrap(conn)
    oc_id = create_outsourced_company(conn, {'legal_name': 'Terceirizada X'}, cid)
    contract_id = create_service_contract(conn, {}, cid, oc_id)
    payload = _minimal_payload(cid, outsourced_company_id=oc_id, service_contract_id=contract_id)
    employee_id = create_employee(conn, payload, actor=_actor(cid))
    employee = get_employee_by_id(conn, employee_id)
    assert employee['service_contract_id'] == contract_id


def test_create_employee_override_without_reason_is_rejected():
    conn = _conn()
    cid = _seed_company(conn)
    _bootstrap(conn)
    oc_id = create_outsourced_company(conn, {'legal_name': 'Terceirizada X'}, cid)
    payload = _minimal_payload(
        cid, outsourced_company_id=oc_id, epi_responsibility_override='Empresa Contratante',
    )
    with pytest.raises(ValueError):
        create_employee(conn, payload, actor=_actor(cid))


def test_create_employee_override_with_reason_succeeds():
    conn = _conn()
    cid = _seed_company(conn)
    _bootstrap(conn)
    oc_id = create_outsourced_company(conn, {'legal_name': 'Terceirizada X'}, cid)
    payload = _minimal_payload(
        cid, outsourced_company_id=oc_id,
        epi_responsibility_override='Empresa Contratante',
        epi_responsibility_override_reason='Acordo pontual',
    )
    employee_id = create_employee(conn, payload, actor=_actor(cid))
    employee = get_employee_by_id(conn, employee_id)
    assert employee['epi_responsibility_override'] == 'Empresa Contratante'
    assert employee['epi_responsibility_override_reason'] == 'Acordo pontual'


# ── update: mutável, mas ainda escopado por tenant ─────────────────────────

def test_update_employee_can_change_outsourced_company_within_tenant(monkeypatch):
    # _PgStyleConn não é reconhecida por epi_backend.db._is_sqlite_connection
    # (checa o nome da classe) — sem isto, outsourced_companies_ready()
    # cairia no branch Postgres (information_schema) contra uma conexão
    # SQLite de teste e retornaria False silenciosamente, pulando a validação
    # em vez de exercitá-la. Produção nunca usa este adaptador — só existe
    # neste arquivo de teste.
    import epi_backend.db as db_module
    monkeypatch.setattr(db_module, '_is_sqlite_connection', lambda _conn: True)
    conn = _conn()
    cid = _seed_company(conn)
    _bootstrap(conn)
    oc_id_1 = create_outsourced_company(conn, {'legal_name': 'Terceirizada 1'}, cid)
    oc_id_2 = create_outsourced_company(conn, {'legal_name': 'Terceirizada 2'}, cid)
    employee_id = create_employee(conn, _minimal_payload(cid, outsourced_company_id=oc_id_1), actor=_actor(cid))
    current = get_employee_by_id(conn, employee_id)

    update_payload = _minimal_payload(cid, outsourced_company_id=oc_id_2, unit_id=current['unit_id'])
    update_employee(_PgStyleConn(conn), employee_id, update_payload, actor=_actor(cid))
    updated = get_employee_by_id(conn, employee_id)
    assert updated['outsourced_company_id'] == oc_id_2


def test_update_employee_rejects_outsourced_company_from_another_tenant(monkeypatch):
    import epi_backend.db as db_module
    monkeypatch.setattr(db_module, '_is_sqlite_connection', lambda _conn: True)
    conn = _conn()
    cid_a = _seed_company(conn, name='Tenant A')
    cid_b = _seed_company(conn, name='Tenant B')
    _bootstrap(conn)
    oc_id_b = create_outsourced_company(conn, {'legal_name': 'Terceirizada de B'}, cid_b)
    employee_id = create_employee(conn, _minimal_payload(cid_a), actor=_actor(cid_a))
    current = get_employee_by_id(conn, employee_id)

    update_payload = _minimal_payload(cid_a, outsourced_company_id=oc_id_b, unit_id=current['unit_id'])
    with pytest.raises(ValueError):
        update_employee(_PgStyleConn(conn), employee_id, update_payload, actor=_actor(cid_a))


# ── fetch_employees devolve as colunas novas ───────────────────────────────

def test_fetch_employees_includes_outsourced_columns():
    conn = _conn()
    cid = _seed_company(conn)
    _bootstrap(conn)
    oc_id = create_outsourced_company(conn, {'legal_name': 'Terceirizada X'}, cid)
    create_employee(conn, _minimal_payload(cid, outsourced_company_id=oc_id), actor=_actor(cid))
    employees = fetch_employees(conn, actor=_actor(cid))
    assert len(employees) == 1
    assert employees[0]['outsourced_company_id'] == oc_id
