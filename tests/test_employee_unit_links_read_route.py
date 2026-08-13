"""Rota somente leitura de vínculos de Unidade (ADR-0002 §13, F5A da #226).

O ponto central: **o escopo é aplicado no servidor, antes da resposta**.
Devolver todos os vínculos e deixar o frontend esconder transformaria uma
regra de autorização em regra visual — o dado já teria atravessado a
fronteira, visível em qualquer inspeção de rede, e cada consumidor novo
precisaria reimplementar o filtro até um deles esquecer.

Por isso metade destes testes olha o que a função NÃO devolve.
"""

import os
import sqlite3
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import schema
from modules.employees import service
from modules.employees.service import (
    fetch_employee_unit_links,
    fetch_employee_unit_links_for_actor,
)

GENERAL_ADMIN = {'id': 1, 'role': 'general_admin', 'company_id': 1}
REGISTRY_ADMIN = {'id': 2, 'role': 'registry_admin', 'company_id': 1}
MASTER_ADMIN = {'id': 3, 'role': 'master_admin', 'company_id': None}
LOCAL_ADMIN = {'id': 4, 'role': 'admin', 'company_id': 1}
EPI_MANAGER = {'id': 5, 'role': 'user', 'company_id': 1}


def _conn():
    connection = sqlite3.connect(':memory:')
    connection.row_factory = sqlite3.Row
    connection.executescript("""
        CREATE TABLE companies (id INTEGER PRIMARY KEY, name TEXT);
        CREATE TABLE units (id INTEGER PRIMARY KEY, name TEXT, company_id INTEGER);
        CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT);
        CREATE TABLE employees (
            id INTEGER PRIMARY KEY, company_id INTEGER, unit_id INTEGER, name TEXT,
            tipo_vinculo TEXT DEFAULT 'Terceirizado'
        );
        INSERT INTO companies (id, name) VALUES (1, 'Tenant A'), (2, 'Tenant B');
        INSERT INTO units (id, name, company_id)
            VALUES (10, 'Base Santos', 1), (11, 'Plataforma P-50', 1), (20, 'Unidade de B', 2);
        INSERT INTO users (id, name) VALUES (1, 'Geral'), (2, 'Registro'), (3, 'Master'),
            (4, 'Local'), (5, 'Gestor');
        INSERT INTO employees (id, company_id, unit_id, name) VALUES (100, 1, 10, 'Terceirizado');
        INSERT INTO employees (id, company_id, unit_id, name) VALUES (200, 2, 20, 'De outro tenant');
    """)
    connection.commit()
    schema.ensure_employee_unit_links(connection)
    return connection


def _link(connection, unit_id, status='active', employee_id=100, company_id=1):
    connection.execute(
        'INSERT INTO employee_unit_links (company_id, employee_id, unit_id, local_status) '
        'VALUES (?, ?, ?, ?)',
        (company_id, employee_id, unit_id, status),
    )
    connection.commit()


def _employee(connection, employee_id=100):
    return dict(connection.execute(
        'SELECT * FROM employees WHERE id = ?', (employee_id,)
    ).fetchone())


# ── perfis NÃO escopados veem todos os vínculos do tenant ──────────────────

@pytest.mark.parametrize('actor', [GENERAL_ADMIN, REGISTRY_ADMIN, MASTER_ADMIN])
def test_unscoped_profiles_see_every_link(actor):
    conn = _conn()
    _link(conn, 10, 'active')
    _link(conn, 11, 'inactive')
    result = fetch_employee_unit_links_for_actor(conn, actor, _employee(conn))
    assert sorted(item['unit_id'] for item in result) == [10, 11]


def test_the_unit_name_comes_along():
    """Sem o nome, a tela mostraria "Unidade 11" — e o operador teria de
    decorar ids para saber de qual base está falando."""
    conn = _conn()
    _link(conn, 10, 'active')
    result = fetch_employee_unit_links_for_actor(conn, GENERAL_ADMIN, _employee(conn))
    assert result[0]['unit_name'] == 'Base Santos'


def test_archived_links_are_returned_too():
    """A lista é de vínculos, não só dos ativos: distinguir "arquivado aqui"
    de "nunca existiu" é o que permite oferecer Reativar."""
    conn = _conn()
    _link(conn, 10, 'inactive')
    result = fetch_employee_unit_links_for_actor(conn, GENERAL_ADMIN, _employee(conn))
    assert [item['local_status'] for item in result] == ['inactive']


# ── perfis escopados veem SOMENTE a própria Unidade ────────────────────────

@pytest.mark.parametrize('actor', [LOCAL_ADMIN, EPI_MANAGER])
def test_scoped_profiles_see_only_their_own_unit(monkeypatch, actor):
    """Administrador Local e Gestor de EPI operam na Unidade 11; o colaborador
    tem vínculo nas duas. Só a 11 pode sair daqui."""
    conn = _conn()
    monkeypatch.setattr(service, 'actor_operational_unit_id', lambda *a, **k: 11)
    _link(conn, 10, 'active')
    _link(conn, 11, 'active')
    result = fetch_employee_unit_links_for_actor(conn, actor, _employee(conn))
    assert [item['unit_id'] for item in result] == [11]


@pytest.mark.parametrize('actor', [LOCAL_ADMIN, EPI_MANAGER])
def test_scoped_profile_without_link_in_its_unit_gets_nothing(monkeypatch, actor):
    """Vínculo existe na 10; o ator opera na 11. Ele não vê o da outra
    Unidade — nem para saber que existe."""
    conn = _conn()
    monkeypatch.setattr(service, 'actor_operational_unit_id', lambda *a, **k: 11)
    _link(conn, 10, 'active')
    assert fetch_employee_unit_links_for_actor(conn, actor, _employee(conn)) == []


@pytest.mark.parametrize('actor', [LOCAL_ADMIN, EPI_MANAGER])
def test_scoped_profile_without_operational_unit_gets_nothing(monkeypatch, actor):
    """Na dúvida sobre o escopo, mostra-se MENOS. Cair para a lista completa
    quando a Unidade não resolve seria escalar privilégio por acidente."""
    conn = _conn()
    monkeypatch.setattr(service, 'actor_operational_unit_id', lambda *a, **k: None)
    _link(conn, 10, 'active')
    _link(conn, 11, 'active')
    assert fetch_employee_unit_links_for_actor(conn, actor, _employee(conn)) == []


# ── isolamento por tenant ──────────────────────────────────────────────────

def test_links_from_another_tenant_never_appear():
    """Vínculo de outro tenant com o MESMO employee_id não vaza."""
    conn = _conn()
    _link(conn, 20, 'active', employee_id=100, company_id=2)
    assert fetch_employee_unit_links_for_actor(conn, GENERAL_ADMIN, _employee(conn)) == []


def test_scoped_actor_does_not_cross_tenants_either(monkeypatch):
    """O caminho escopado usa `fetch_employee_unit_link`, que NÃO filtra
    tenant — por isso a função confere `company_id` antes de devolver. Sem
    essa conferência, um vínculo de outro tenant na mesma Unidade escaparia
    pelo ramo escopado enquanto o ramo não escopado o barrava."""
    conn = _conn()
    monkeypatch.setattr(service, 'actor_operational_unit_id', lambda *a, **k: 20)
    _link(conn, 20, 'active', employee_id=100, company_id=2)
    assert fetch_employee_unit_links_for_actor(conn, LOCAL_ADMIN, _employee(conn)) == []


def test_the_raw_query_requires_the_tenant():
    """`fetch_employee_unit_links` passou a exigir `company_id`.

    A assinatura anterior filtrava só por `employee_id` e deixava o
    isolamento por conta do chamador; como nunca houve chamador, o débito
    nunca apareceu. Exigir aqui fecha a porta antes da primeira rota, não
    depois.
    """
    import inspect

    params = inspect.signature(fetch_employee_unit_links).parameters
    assert 'company_id' in params
    assert params['company_id'].default is inspect.Parameter.empty, (
        'company_id não pode ter default — opcional viraria "esquecível"'
    )


def test_the_raw_query_filters_by_tenant():
    conn = _conn()
    _link(conn, 10, 'active', employee_id=100, company_id=1)
    _link(conn, 20, 'active', employee_id=100, company_id=2)
    assert [i['unit_id'] for i in fetch_employee_unit_links(conn, 100, 1)] == [10]
    assert [i['unit_id'] for i in fetch_employee_unit_links(conn, 100, 2)] == [20]


# ── retorno vazio ──────────────────────────────────────────────────────────

def test_no_links_at_all_returns_empty_list():
    conn = _conn()
    assert fetch_employee_unit_links_for_actor(conn, GENERAL_ADMIN, _employee(conn)) == []


def test_missing_employee_returns_empty_instead_of_raising():
    conn = _conn()
    assert fetch_employee_unit_links_for_actor(conn, GENERAL_ADMIN, None) == []


def test_absent_table_returns_empty():
    """Schema parcial (fixture antiga, tenant não provisionado) não pode
    derrubar a rota — mesma tolerância de `employee_blocking_unit_links`."""
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.executescript(
        'CREATE TABLE employees (id INTEGER PRIMARY KEY, company_id INTEGER, unit_id INTEGER);'
        'INSERT INTO employees (id, company_id, unit_id) VALUES (100, 1, 10);'
    )
    conn.commit()
    employee = dict(conn.execute('SELECT * FROM employees WHERE id = 100').fetchone())
    assert fetch_employee_unit_links_for_actor(conn, GENERAL_ADMIN, employee) == []


# ── a rota é somente leitura ───────────────────────────────────────────────

def test_the_route_is_registered_as_get_only():
    import pathlib
    import re

    body = pathlib.Path('modules/employees/routes.py').read_text(encoding='utf-8')
    registrations = re.findall(r"router\.register\('(\w+)',\s*r?'[^']*unit-links[^']*'", body)
    assert registrations == ['GET'], (
        f'unit-links só pode ter GET registrado, achei: {registrations}'
    )


def test_no_write_verb_targets_unit_links():
    """Nem POST, nem PUT, nem PATCH, nem DELETE. A escrita continua nas três
    rotas de vínculo que já existiam."""
    import pathlib
    import re

    body = pathlib.Path('modules/employees/routes.py').read_text(encoding='utf-8')
    for verb in ('POST', 'PUT', 'PATCH', 'DELETE'):
        offenders = re.findall(rf"router\.register\('{verb}',\s*r?'[^']*unit-links\$", body)
        assert not offenders, f'{verb} registrado para unit-links: {offenders}'


def test_the_handler_does_not_write_anything():
    """Somente leitura de verdade: sem commit, sem INSERT/UPDATE/DELETE, sem
    chamada de arquivamento ou purga."""
    import pathlib
    import re

    body = pathlib.Path('modules/employees/routes.py').read_text(encoding='utf-8')
    match = re.search(r'def handle_get_employee_unit_links.*?(?=\ndef )', body, re.DOTALL)
    assert match, 'handler não encontrado'
    # O docstring EXPLICA que a rota não escreve, não arquiva e não purga —
    # e é justamente por citar essas palavras que ele precisa sair antes da
    # varredura. Um teste que proíbe descrever o que se está evitando empurra
    # a explicação para fora do código, que é o oposto do desejado.
    handler = re.sub(r'"""!?.*?"""', '', match.group(0), flags=re.DOTALL)
    handler = re.sub(r'#[^\n]*', '', handler)
    for forbidden in (
        'connection.commit', 'INSERT', 'UPDATE ', 'DELETE',
        'set_employee_unit_link_status', 'create_employee_unit_link',
        'archive', 'purge',
    ):
        assert forbidden not in handler, f'handler de leitura não pode conter: {forbidden}'


def test_the_route_uses_the_visibility_scope_not_the_strict_one():
    """Escopo ESTRITO aqui negaria justamente a quem o vínculo local tornou
    visível — que é o caso de uso da rota (PR D permite ampliar em leitura)."""
    import pathlib
    import re

    body = pathlib.Path('modules/employees/routes.py').read_text(encoding='utf-8')
    match = re.search(r'def handle_get_employee_unit_links.*?(?=\ndef )', body, re.DOTALL)
    handler = match.group(0)
    assert 'ensure_actor_employee_visibility_scope(connection' in handler
    assert 'ensure_actor_employee_scope(connection' not in handler


def test_the_route_requires_employees_view():
    import pathlib
    import re

    body = pathlib.Path('modules/employees/routes.py').read_text(encoding='utf-8')
    match = re.search(r'def handle_get_employee_unit_links.*?(?=\ndef )', body, re.DOTALL)
    assert 'PERM_EMPLOYEES_VIEW' in match.group(0)


def test_the_scope_is_applied_in_the_service_not_in_the_handler():
    """O handler não pode filtrar por conta própria: a política mora em uma
    função só, e é ela que todo consumidor futuro vai atravessar."""
    import pathlib
    import re

    body = pathlib.Path('modules/employees/routes.py').read_text(encoding='utf-8')
    match = re.search(r'def handle_get_employee_unit_links.*?(?=\ndef )', body, re.DOTALL)
    handler = match.group(0)
    assert 'fetch_employee_unit_links_for_actor(connection, actor, employee)' in handler
    assert 'fetch_employee_unit_links(connection' not in handler, (
        'o handler não pode chamar a consulta CRUA — ela não aplica escopo'
    )
