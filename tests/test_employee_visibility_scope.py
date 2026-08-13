"""Escopo de visibilidade por vínculo local (ADR-0002 §13, PR D).

A separação que este PR protege: **permissão define o que o usuário pode
fazer; vínculo local define sobre quem ele pode consultar.** Vínculo local
nunca concede uma permissão que o perfil não tem.

Por isso metade dos testes aqui prova o que NÃO foi liberado. Um `OR
employee_unit_links` colocado dentro de `ensure_actor_employee_scope` teria
passado nos testes positivos e liberado, de quebra, arquivamento, exclusão,
purga, finalização de ficha e os links de portal — que é exatamente o motivo
de existir uma função separada.
"""

import os
import sqlite3
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import schema
from modules.employees import service
from modules.employees.service import (
    ensure_actor_employee_scope,
    ensure_actor_employee_visibility_scope,
)

# Ator escopado por Unidade (Gestor de EPI), operando na Unidade 11 — o
# colaborador 100 mora na Unidade 10.
ACTOR = {'id': 5, 'role': 'user', 'company_id': 1}
OTHER_TENANT_ACTOR = {'id': 6, 'role': 'user', 'company_id': 2}


def _conn():
    connection = sqlite3.connect(':memory:')
    connection.row_factory = sqlite3.Row
    connection.executescript("""
        CREATE TABLE companies (id INTEGER PRIMARY KEY, name TEXT);
        CREATE TABLE units (id INTEGER PRIMARY KEY, name TEXT, company_id INTEGER);
        CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT);
        CREATE TABLE employees (
            id INTEGER PRIMARY KEY, company_id INTEGER, unit_id INTEGER, name TEXT,
            employee_id_code TEXT DEFAULT '', cpf TEXT DEFAULT '', email TEXT DEFAULT '',
            whatsapp TEXT DEFAULT '', preferred_contact_channel TEXT DEFAULT 'whatsapp',
            sector TEXT DEFAULT '', role_name TEXT DEFAULT '', admission_date TEXT DEFAULT '',
            schedule_type TEXT DEFAULT '', empresa_origem TEXT DEFAULT '',
            tipo_vinculo TEXT DEFAULT 'Terceirizado'
        );
        CREATE TABLE employee_unit_movements (
            id INTEGER PRIMARY KEY AUTOINCREMENT, employee_id INTEGER, company_id INTEGER,
            source_unit_id INTEGER, target_unit_id INTEGER, movement_type TEXT,
            start_date TEXT, end_date TEXT DEFAULT ''
        );
        INSERT INTO companies (id, name) VALUES (1, 'Tenant A'), (2, 'Tenant B');
        INSERT INTO units (id, name, company_id) VALUES (10, 'A1', 1), (11, 'A2', 1), (20, 'B1', 2);
        INSERT INTO users (id, name) VALUES (5, 'Gestor'), (6, 'Outro tenant');
        INSERT INTO employees (id, company_id, unit_id, name)
            VALUES (100, 1, 10, 'Terceirizado');
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


@pytest.fixture
def actor_in_unit_11(monkeypatch):
    """O ator opera na Unidade 11; o colaborador mora na 10."""
    monkeypatch.setattr(service, 'actor_operational_unit_id', lambda *a, **k: 11)


# ── o que o vínculo local LIBERA ────────────────────────────────────────────

def test_active_local_link_allows_reading(actor_in_unit_11):
    conn = _conn()
    _link(conn, 11, 'active')
    ensure_actor_employee_visibility_scope(conn, ACTOR, _employee(conn))


def test_without_any_link_reading_is_denied(actor_in_unit_11):
    conn = _conn()
    with pytest.raises(PermissionError):
        ensure_actor_employee_visibility_scope(conn, ACTOR, _employee(conn))


def test_archived_local_link_does_not_allow_reading(actor_in_unit_11):
    """Arquivar o vínculo REMOVE a visibilidade administrativa daquela Unidade."""
    conn = _conn()
    _link(conn, 11, 'inactive')
    with pytest.raises(PermissionError):
        ensure_actor_employee_visibility_scope(conn, ACTOR, _employee(conn))


def test_reactivating_restores_reading(actor_in_unit_11):
    conn = _conn()
    _link(conn, 11, 'inactive')
    conn.execute("UPDATE employee_unit_links SET local_status = 'active' WHERE unit_id = 11")
    conn.commit()
    ensure_actor_employee_visibility_scope(conn, ACTOR, _employee(conn))


def test_a_link_in_another_unit_grants_nothing_here(actor_in_unit_11):
    """Vínculo na Unidade 10 não dá acesso a quem opera na 11."""
    conn = _conn()
    _link(conn, 10, 'active')
    with pytest.raises(PermissionError):
        ensure_actor_employee_visibility_scope(conn, ACTOR, _employee(conn))


def test_nothing_crosses_tenants(actor_in_unit_11):
    """Mesmo com vínculo ativo na Unidade do ator, outro tenant é barrado.

    A checagem de tenant roda ANTES e FORA do try — envolvê-la faria a
    negativa por tenant cair no relaxamento por vínculo.
    """
    conn = _conn()
    _link(conn, 11, 'active')
    with pytest.raises(PermissionError):
        ensure_actor_employee_visibility_scope(conn, OTHER_TENANT_ACTOR, _employee(conn))


def test_the_actor_own_unit_still_works_without_any_link(monkeypatch):
    """Quem já estava no escopo operacional continua entrando pela regra
    antiga — o vínculo local só é consultado quando ela nega."""
    monkeypatch.setattr(service, 'actor_operational_unit_id', lambda *a, **k: 10)
    conn = _conn()
    ensure_actor_employee_visibility_scope(conn, ACTOR, _employee(conn))


# ── o que o vínculo local NÃO libera ────────────────────────────────────────

def test_the_operational_gate_itself_is_untouched(actor_in_unit_11):
    """`ensure_actor_employee_scope` continua negando com vínculo ativo.

    É o coração do PR D: a função original NÃO foi enfraquecida. Se alguém
    puser o OR dentro dela, este teste falha.
    """
    conn = _conn()
    _link(conn, 11, 'active')
    with pytest.raises(PermissionError):
        ensure_actor_employee_scope(conn, ACTOR, _employee(conn))


@pytest.mark.parametrize('module_path,func_name', [
    ('modules/employees/service.py', 'update_employee_outsourced_simplified'),
    ('modules/employees/routes.py', '_load_employee_for_lifecycle'),
    ('modules/ficha/routes.py', 'handle_post_fichas_finalize'),
])
def test_sensitive_paths_still_use_the_strict_scope(module_path, func_name):
    """Arquivamento, exclusão, purga, update, transferência e finalização de
    ficha continuam na função estrita.

    `_load_employee_for_lifecycle` sozinho atende sete rotas — `employees:view`,
    `employees:update` e cinco de `employees:delete`, incluindo as três etapas
    de purga. Ampliar ali liberaria exclusão por vínculo local.
    """
    import pathlib
    import re

    body = pathlib.Path(module_path).read_text(encoding='utf-8')
    match = re.search(rf'def {func_name}\(.*?(?=\ndef |\Z)', body, re.DOTALL)
    assert match, f'{func_name} não encontrada em {module_path}'
    assert 'ensure_actor_employee_scope(' in match.group(0), (
        f'{func_name} deveria usar o escopo ESTRITO'
    )
    assert 'ensure_actor_employee_visibility_scope(' not in match.group(0), (
        f'{func_name} não pode usar o escopo de visibilidade — não é leitura'
    )


@pytest.mark.parametrize('module_path', [
    'modules/portal/routes.py',
    'modules/deliveries/service.py',
])
def test_portal_and_delivery_never_use_the_visibility_scope(module_path):
    """Criação/revogação de link de portal e entrega de EPI continuam fora."""
    import pathlib

    body = pathlib.Path(module_path).read_text(encoding='utf-8')
    assert 'ensure_actor_employee_visibility_scope' not in body, (
        f'{module_path} não pode usar o escopo de visibilidade'
    )


def test_the_delivery_gate_does_not_go_through_either_scope_function():
    """O gate de entrega compara a Unidade operacional atual por conta própria
    (§13.17). Nada que se faça nas funções de escopo o alcança — a decisão de
    não ampliá-lo se sustenta na estrutura, não só na intenção."""
    import pathlib

    body = pathlib.Path('modules/deliveries/service.py').read_text(encoding='utf-8')
    assert 'ensure_actor_employee_scope' not in body
    assert 'get_employee_current_unit' in body
    assert 'Entrega só pode ocorrer na unidade operacional atual do colaborador.' in body


def test_reading_paths_use_the_visibility_scope():
    """Os quatro pontos de leitura aprovados — e só eles."""
    import pathlib

    # A contagem EXATA é o mecanismo: cada ponto de leitura novo tem de ser
    # registrado aqui, conscientemente. Se um destes números subir sozinho num
    # PR, é porque alguém ampliou o escopo sem passar por esta lista.
    expected = {
        # handle_get_employee + handle_get_employee_unit_links (F5A da #226),
        # esta última aprovada pelo mesmo critério: é leitura.
        'modules/employees/routes.py': 2,
        'modules/ficha/service.py': 1,      # filtro de assinaturas
        'modules/reports/service.py': 1,    # filtro de relatório
    }
    for path, count in expected.items():
        body = pathlib.Path(path).read_text(encoding='utf-8')
        found = body.count('ensure_actor_employee_visibility_scope(connection')
        assert found == count, f'{path}: esperava {count} uso(s), achei {found}'

    # A ficha usa duas vezes: na rota e passada ao builder, que revalida.
    ficha = pathlib.Path('modules/ficha/routes.py').read_text(encoding='utf-8')
    assert 'ensure_actor_scope_fn=ensure_actor_employee_visibility_scope' in ficha, (
        'o builder da ficha revalida o escopo; com o default estrito a rota '
        'liberaria e ele negaria logo depois, tornando a ampliação inócua'
    )


def test_fichas_view_permission_is_still_required():
    """O vínculo local amplia SOBRE QUEM, nunca concede a permissão.

    `authorize_action(..., 'fichas:view')` roda antes do escopo na rota de
    impressão; sem a permissão, nem se chega à checagem de vínculo.
    """
    import pathlib
    import re

    body = pathlib.Path('modules/ficha/routes.py').read_text(encoding='utf-8')
    match = re.search(
        r"def handle_get_ficha_html.*?(?=\ndef |\Z)", body, re.DOTALL
    )
    assert match, 'rota de impressão da ficha não encontrada'
    section = match.group(0)
    authorize_at = section.find("'fichas:view'")
    scope_at = section.find('ensure_actor_employee_visibility_scope')
    assert authorize_at != -1, 'fichas:view deixou de ser exigida'
    assert scope_at != -1, 'a rota deveria usar o escopo de visibilidade'
    assert authorize_at < scope_at, (
        'a permissão precisa ser verificada ANTES do escopo — senão o vínculo '
        'local viraria porta de entrada para quem não tem fichas:view'
    )
