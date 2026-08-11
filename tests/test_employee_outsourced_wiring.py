"""O Cadastro Principal recusa mão de obra CONTRATADA (ADR-0002).

Este arquivo testava o contrário: que ``create_employee``/``update_employee``
aceitavam ``outsourced_company_id``/``service_contract_id``/
``epi_responsibility_override(_reason)``. Era o segundo caminho capaz de criar
um terceirizado — e o pior dos dois, porque o formulário do Cadastro Principal
não monta o vínculo estruturado: identificava o contratado apenas por um texto
livre em ``empresa_origem``, sem CNPJ, sem contrato e sem escopo por Unidade.

Por decisão de produto (2026-08-11), Terceirizado, Prestador de Serviço e
Temporário passam a existir **exclusivamente** no módulo Terceirizados e
Prestadores. Manter os dois caminhos significava duas regras para o mesmo fato.

**A cobertura dos campos de terceirizado não se perdeu** — ela mora, e sempre
morou melhor, em ``tests/test_employee_outsourced_simplified.py``, que exercita
o fluxo definitivo: os quatro campos, a recusa de empresa de outro tenant, a
recusa de unidade de outro tenant, e o bloqueio por empresa arquivada.

Uma armadilha encontrada ao converter, que vale registrar: o antigo
``test_create_employee_rejects_outsourced_company_from_another_tenant``
**continuava passando** depois da mudança — mas pelo motivo errado. Ele
esperava um ``ValueError`` genérico, que antes vinha da checagem de tenant e
passou a vir da recusa de vínculo, disparada antes. Verde, e sem testar mais
nada. Por isso os testes abaixo casam com a MENSAGEM, não com o tipo da
exceção.
"""

import sqlite3

import pytest

from core.schema import (
    ensure_legal_entities,
    ensure_outsourced_companies,
    ensure_outsourced_company_unit_links,
)
from modules.employees.service import (
    CONTRACTED_VINCULOS,
    OWN_WORKFORCE_VINCULOS,
    create_employee,
    fetch_employees,
    get_employee_by_id,
    update_employee,
)
from modules.outsourced_companies.service import create_outsourced_company

CNPJ_A = '11.222.333/0001-81'

#: Trecho estável da mensagem de recusa. Casar com ele — e não com
#: `pytest.raises(ValueError)` — é o que impede este teste de ficar verde
#: quando outra validação qualquer disparar primeiro.
REFUSAL = 'não pertence ao Cadastro Principal'


@pytest.fixture(autouse=True)
def _sqlite_detection(monkeypatch):
    """`_PgStyleConn` esconde o tipo da conexão, e `core.schema` decide entre
    `sqlite_master` e `information_schema` por ele. Mesmo fixture das demais
    suítes que usam o adaptador."""
    monkeypatch.setattr('epi_backend.db._is_sqlite_connection', lambda _conn: True)
    # Alvo em string: `core.schema` já entra neste arquivo por `from ... import`,
    # e um segundo `import core.schema as ...` só para ter o objeto do módulo
    # deixaria o mesmo módulo importado das duas formas (apontado pelo CodeQL).
    monkeypatch.setattr('core.schema._is_sqlite_connection', lambda _conn: True)


def _dict_factory(cursor, row):
    return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}


class _PgStyleConn:
    """Traduz o dialeto Postgres (%s) para SQLite (?) — mesmo adaptador das
    demais suítes. `update_employee` resolve a unidade por
    `core.repository.get_unit_by_id`, que usa `%s`."""

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
            id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, cnpj TEXT,
            logo_type TEXT NOT NULL DEFAULT ''
        );
        CREATE TABLE units (
            id INTEGER PRIMARY KEY AUTOINCREMENT, company_id INTEGER NOT NULL,
            name TEXT DEFAULT '', unit_type TEXT DEFAULT '', city TEXT DEFAULT '',
            notes TEXT DEFAULT '', status TEXT NOT NULL DEFAULT 'active'
        );
        CREATE TABLE employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT, company_id INTEGER NOT NULL,
            unit_id INTEGER NOT NULL, employee_id_code TEXT NOT NULL,
            cpf TEXT NOT NULL DEFAULT '', name TEXT NOT NULL,
            email TEXT NOT NULL DEFAULT '', whatsapp TEXT NOT NULL DEFAULT '',
            preferred_contact_channel TEXT NOT NULL DEFAULT 'whatsapp',
            sector TEXT NOT NULL, role_name TEXT NOT NULL,
            admission_date TEXT NOT NULL, schedule_type TEXT NOT NULL,
            tipo_vinculo TEXT NOT NULL DEFAULT 'CLT',
            empresa_origem TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'active'
        );
        CREATE TABLE employee_unit_movements (
            id INTEGER PRIMARY KEY AUTOINCREMENT, employee_id INTEGER NOT NULL,
            company_id INTEGER NOT NULL, source_unit_id INTEGER NOT NULL,
            target_unit_id INTEGER NOT NULL, movement_type TEXT NOT NULL,
            start_date TEXT NOT NULL, end_date TEXT NOT NULL DEFAULT ''
        );
        """
    )
    return _PgStyleConn(conn)


def _seed_company(conn, name='ACME', cnpj='00.000.000/0001-00'):
    cursor = conn.execute(
        'INSERT INTO companies (name, cnpj) VALUES (?, ?)', (name, cnpj)
    )
    return int(cursor.lastrowid)


def _bootstrap(conn):
    ensure_legal_entities(conn)
    ensure_outsourced_companies(conn)
    ensure_outsourced_company_unit_links(conn)


def _actor(company_id, role='general_admin', user_id=1):
    return {
        'id': user_id, 'role': role, 'company_id': company_id,
        'full_name': 'Ana Geral', 'unit_id': None,
    }


def _payload(company_id, **overrides):
    # unit_id omitido de propósito: create_employee resolve/cria a unidade
    # padrão via SQL com placeholder '?', compatível com SQLite.
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
        'tipo_vinculo': 'CLT',
        'empresa_origem': '',
    }
    payload.update(overrides)
    return payload


# ── mão de obra própria continua funcionando ───────────────────────────────

@pytest.mark.parametrize('vinculo', OWN_WORKFORCE_VINCULOS)
def test_main_registration_accepts_every_own_workforce_vinculo(vinculo):
    """O outro lado da regra. Fechar o cadastro para contratados não pode ter
    fechado nada para quem a empresa emprega diretamente."""
    conn = _conn()
    cid = _seed_company(conn)
    _bootstrap(conn)
    employee_id = create_employee(
        conn, _payload(cid, tipo_vinculo=vinculo), actor=_actor(cid)
    )
    saved = get_employee_by_id(conn, employee_id)
    assert saved['tipo_vinculo'] == vinculo
    assert saved['empresa_origem'] == ''


def test_fetch_employees_still_returns_own_workforce():
    conn = _conn()
    cid = _seed_company(conn)
    _bootstrap(conn)
    create_employee(conn, _payload(cid), actor=_actor(cid))
    rows = fetch_employees(conn, _actor(cid))
    assert len(rows) == 1
    assert rows[0]['tipo_vinculo'] == 'CLT'


# ── mão de obra contratada é recusada, na criação e na edição ──────────────

@pytest.mark.parametrize('vinculo', CONTRACTED_VINCULOS)
def test_main_registration_refuses_every_contracted_vinculo_on_create(vinculo):
    conn = _conn()
    cid = _seed_company(conn)
    _bootstrap(conn)
    with pytest.raises(ValueError, match=REFUSAL):
        create_employee(
            conn,
            _payload(cid, tipo_vinculo=vinculo, empresa_origem='Prestadora Legada LTDA'),
            actor=_actor(cid),
        )
    assert conn.execute('SELECT COUNT(*) AS n FROM employees').fetchone()['n'] == 0


@pytest.mark.parametrize('vinculo', CONTRACTED_VINCULOS)
def test_main_registration_refuses_every_contracted_vinculo_on_update(vinculo):
    """A recusa vale na edição também — senão o formulário que não sabe montar
    o vínculo estruturado continuaria vivo, e a pessoa seguiria identificada
    só por texto livre."""
    conn = _conn()
    cid = _seed_company(conn)
    _bootstrap(conn)
    employee_id = create_employee(conn, _payload(cid), actor=_actor(cid))
    # `update_employee` exige `unit_id` explícito (ao contrário de
    # `create_employee`, que resolve a unidade padrão).
    unit_id = get_employee_by_id(conn, employee_id)['unit_id']

    with pytest.raises(ValueError, match=REFUSAL):
        update_employee(
            conn, employee_id,
            _payload(cid, unit_id=unit_id, tipo_vinculo=vinculo,
                     empresa_origem='Prestadora Legada LTDA'),
            actor=_actor(cid),
        )
    assert get_employee_by_id(conn, employee_id)['tipo_vinculo'] == 'CLT'


def test_the_structured_link_does_not_buy_a_way_in():
    """Informar `outsourced_company_id` não reabre o caminho.

    Era a tentação óbvia: "se o vínculo estruturado está presente, o Cadastro
    Principal poderia aceitar". Não pode — o formulário não coleta contrato nem
    escopo por Unidade, e aceitar aqui recriaria o segundo caminho com um
    subconjunto dos dados.
    """
    conn = _conn()
    cid = _seed_company(conn)
    _bootstrap(conn)
    oc_id = create_outsourced_company(conn, {'legal_name': 'Terceirizada A', 'cnpj': CNPJ_A}, cid)
    with pytest.raises(ValueError, match=REFUSAL):
        create_employee(
            conn,
            _payload(cid, tipo_vinculo='Terceirizado', outsourced_company_id=oc_id),
            actor=_actor(cid),
        )


def test_the_refusal_names_the_module_that_should_be_used():
    """Mensagem de erro que só diz "não pode" obriga o operador a adivinhar.
    Esta precisa dizer para onde ir."""
    conn = _conn()
    cid = _seed_company(conn)
    _bootstrap(conn)
    with pytest.raises(ValueError) as excinfo:
        create_employee(conn, _payload(cid, tipo_vinculo='Terceirizado'), actor=_actor(cid))
    message = str(excinfo.value)
    assert 'Terceirizados e Prestadores' in message
    assert 'Terceirizado' in message


def test_the_two_registrations_cover_disjoint_universes():
    """Nenhum vínculo pode ser aceito pelos dois cadastros, nem recusado pelos
    dois por omissão. Se um vínculo novo entrar em `OWN_WORKFORCE_VINCULOS` e
    em `CONTRACTED_VINCULOS` ao mesmo tempo, o comportamento passa a depender
    de qual validação roda primeiro — que é como bugs assim nascem."""
    assert not set(OWN_WORKFORCE_VINCULOS) & set(CONTRACTED_VINCULOS)
