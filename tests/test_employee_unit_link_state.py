"""Estado do vínculo local exposto na listagem (ADR-0002 §13, PR C1).

O frontend não reconstrói esta regra — ele lê `local_unit_link_status` e
`is_linked_to_actor_unit` do backend. Por isso os seis cenários que a decisão
do projeto exigiu estão travados aqui: vínculo ativo, arquivado, sem vínculo,
isolamento por tenant, isolamento por Unidade, e Administrador Geral com
Unidade selecionada.
"""

import os
import sqlite3
import sys
from typing import ClassVar

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import schema
from modules.employees.service import (
    UNIT_LINK_STATUS_ACTIVE,
    UNIT_LINK_STATUS_INACTIVE,
    UNIT_LINK_STATUS_NONE,
    annotate_employee_unit_link_state,
    resolve_actor_unit_context,
)


def _conn():
    connection = sqlite3.connect(':memory:')
    connection.row_factory = sqlite3.Row
    connection.executescript("""
        CREATE TABLE companies (id INTEGER PRIMARY KEY, name TEXT);
        CREATE TABLE units (id INTEGER PRIMARY KEY, name TEXT, company_id INTEGER);
        CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT);
        CREATE TABLE employees (
            id INTEGER PRIMARY KEY, company_id INTEGER, unit_id INTEGER, name TEXT,
            tipo_vinculo TEXT DEFAULT 'CLT', empresa_origem TEXT DEFAULT '',
            outsourced_company_id INTEGER
        );
        INSERT INTO companies (id, name) VALUES (1, 'Tenant A'), (2, 'Tenant B');
        INSERT INTO units (id, name, company_id) VALUES (10, 'A1', 1), (11, 'A2', 1), (20, 'B1', 2);
        INSERT INTO users (id, name) VALUES (5, 'Ator');
        INSERT INTO employees (id, company_id, unit_id, name, tipo_vinculo, outsourced_company_id)
            VALUES (100, 1, 10, 'Terceirizado', 'Terceirizado', 7);
        INSERT INTO employees (id, company_id, unit_id, name, tipo_vinculo)
            VALUES (101, 1, 10, 'Proprio', 'CLT');
    """)
    connection.commit()
    schema.ensure_employee_unit_links(connection)
    return connection


def _link(connection, employee_id, unit_id, status='active', company_id=1):
    connection.execute(
        'INSERT INTO employee_unit_links (company_id, employee_id, unit_id, local_status) '
        'VALUES (?, ?, ?, ?)',
        (company_id, employee_id, unit_id, status),
    )
    connection.commit()


def _annotate(connection, unit_id, employee_ids=(100,)):
    rows = [
        dict(connection.execute('SELECT * FROM employees WHERE id = ?', (eid,)).fetchone())
        for eid in employee_ids
    ]
    return {row['id']: row for row in annotate_employee_unit_link_state(connection, rows, unit_id)}


# ── os três estados ─────────────────────────────────────────────────────────

def test_active_link_is_reported_as_linked():
    conn = _conn()
    _link(conn, 100, 10, 'active')
    result = _annotate(conn, 10)[100]
    assert result['local_unit_link_status'] == UNIT_LINK_STATUS_ACTIVE
    assert result['is_linked_to_actor_unit'] is True


def test_archived_link_is_reported_but_not_linked():
    """Arquivado nesta Unidade não é "sem vínculo": a UI precisa distinguir
    para oferecer "Reativar" em vez de "Vincular"."""
    conn = _conn()
    _link(conn, 100, 10, 'inactive')
    result = _annotate(conn, 10)[100]
    assert result['local_unit_link_status'] == UNIT_LINK_STATUS_INACTIVE
    assert result['is_linked_to_actor_unit'] is False


def test_absent_link_is_reported_as_none():
    conn = _conn()
    result = _annotate(conn, 10)[100]
    assert result['local_unit_link_status'] == UNIT_LINK_STATUS_NONE
    assert result['is_linked_to_actor_unit'] is False


def test_own_workforce_is_not_applicable_rather_than_unlinked():
    """`None` é diferente de 'none'. Mão de obra própria não pode ser
    vinculada (a rota recusa), então reportar 'none' faria a UI oferecer um
    botão que o backend rejeitaria."""
    conn = _conn()
    result = _annotate(conn, 10, employee_ids=(101,))[101]
    assert result['local_unit_link_status'] is None
    assert result['is_linked_to_actor_unit'] is False


def test_without_unit_context_nothing_is_reported():
    """Sem Unidade selecionada a listagem não vira relatório de vínculos."""
    conn = _conn()
    _link(conn, 100, 10, 'active')
    result = _annotate(conn, None)[100]
    assert result['local_unit_link_status'] is None
    assert result['is_linked_to_actor_unit'] is False


# ── isolamento ──────────────────────────────────────────────────────────────

def test_link_in_another_unit_does_not_leak_into_this_one():
    """Isolamento por Unidade: vínculo ativo na A2 não faz a pessoa aparecer
    como vinculada na A1."""
    conn = _conn()
    _link(conn, 100, 11, 'active')
    result = _annotate(conn, 10)[100]
    assert result['local_unit_link_status'] == UNIT_LINK_STATUS_NONE
    assert result['is_linked_to_actor_unit'] is False


def test_actor_from_another_tenant_gets_no_unit_context():
    """Isolamento por tenant: a Unidade pedida é de outro tenant, então é
    tratada como ausente — e não como uma Unidade válida qualquer."""
    conn = _conn()
    actor = {'id': 5, 'role': 'general_admin', 'company_id': 1}
    assert resolve_actor_unit_context(conn, actor, 20) is None


def test_master_admin_may_select_any_tenant_unit():
    conn = _conn()
    actor = {'id': 5, 'role': 'master_admin', 'company_id': None}
    assert resolve_actor_unit_context(conn, actor, 20) == 20


def test_unknown_unit_is_treated_as_absent():
    conn = _conn()
    actor = {'id': 5, 'role': 'general_admin', 'company_id': 1}
    assert resolve_actor_unit_context(conn, actor, 9999) is None


@pytest.mark.parametrize('raw', ['', None, 'abc', 0])
def test_garbage_unit_id_is_treated_as_absent(raw):
    conn = _conn()
    actor = {'id': 5, 'role': 'general_admin', 'company_id': 1}
    assert resolve_actor_unit_context(conn, actor, raw) is None


# ── quem escolhe a Unidade ──────────────────────────────────────────────────

def test_general_admin_gets_the_selected_unit():
    """Administrador Geral com Unidade selecionada: a resposta é coerente com
    o contexto escolhido."""
    conn = _conn()
    actor = {'id': 5, 'role': 'general_admin', 'company_id': 1}
    assert resolve_actor_unit_context(conn, actor, 11) == 11


def test_general_admin_without_selection_gets_no_context():
    conn = _conn()
    actor = {'id': 5, 'role': 'general_admin', 'company_id': 1}
    assert resolve_actor_unit_context(conn, actor, None) is None


@pytest.mark.parametrize('role', ['admin', 'user'])
def test_scoped_actor_ignores_the_requested_unit(monkeypatch, role):
    """Mesma regra das rotas de escrita do PR B: quem é escopado não escolhe
    Unidade. Aqui o ator pede a A2 e recebe a Unidade operacional dele."""
    from modules.employees import service

    conn = _conn()
    monkeypatch.setattr(service, 'actor_operational_unit_id', lambda *a, **k: 10)
    actor = {'id': 5, 'role': role, 'company_id': 1}
    assert resolve_actor_unit_context(conn, actor, 11) == 10


@pytest.mark.parametrize('role', ['admin', 'user'])
def test_scoped_actor_without_operational_unit_gets_no_context(monkeypatch, role):
    from modules.employees import service

    conn = _conn()
    monkeypatch.setattr(service, 'actor_operational_unit_id', lambda *a, **k: None)
    actor = {'id': 5, 'role': role, 'company_id': 1}
    assert resolve_actor_unit_context(conn, actor, 11) is None


# ── sem N+1 ─────────────────────────────────────────────────────────────────

class _SqliteCountingConnection(sqlite3.Connection):
    """Conta consultas a `employee_unit_links`.

    Subclasse em vez de proxy, e o NOME importa: `_is_sqlite_connection`
    decide procurando a substring "sqlite" no módulo ou no nome da classe do
    tipo. Um proxy — ou uma subclasse chamada `_CountingConnection` — cai no
    ramo do PostgreSQL, `table_exists` devolve False, e a anotação nem chega a
    rodar. O teste então mediria zero consultas e passaria por "eficiente"
    quando na verdade era "não executou". Foi exatamente o que aconteceu nas
    duas primeiras tentativas deste teste.
    """

    queries: ClassVar[list] = []

    def execute(self, sql, *args):
        if 'employee_unit_links' in str(sql):
            type(self).queries.append(sql)
        return super().execute(sql, *args)


def test_the_whole_list_costs_one_query():
    """A alternativa descartada (rota por colaborador) seria N+1 na tela.
    Este teste trava a decisão: a anotação faz UMA consulta para a lista."""
    conn = sqlite3.connect(':memory:', factory=_SqliteCountingConnection)
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        CREATE TABLE employees (
            id INTEGER PRIMARY KEY, company_id INTEGER, unit_id INTEGER, name TEXT,
            tipo_vinculo TEXT DEFAULT 'CLT', empresa_origem TEXT DEFAULT '',
            outsourced_company_id INTEGER
        );
    """)
    schema.ensure_employee_unit_links(conn)
    for eid in range(200, 260):
        conn.execute(
            'INSERT INTO employees (id, company_id, unit_id, name, tipo_vinculo, outsourced_company_id) '
            "VALUES (?, 1, 10, ?, 'Terceirizado', 7)",
            (eid, f'T{eid}'),
        )
    conn.commit()
    rows = [
        dict(conn.execute('SELECT * FROM employees WHERE id = ?', (eid,)).fetchone())
        for eid in range(200, 260)
    ]

    _SqliteCountingConnection.queries = []
    annotate_employee_unit_link_state(conn, rows, 10)
    assert len(_SqliteCountingConnection.queries) == 1, (
        f'esperava 1 consulta, veio {len(_SqliteCountingConnection.queries)}'
    )
    # E a anotação realmente rodou — sem isto, zero consultas passaria por
    # "eficiente" quando na verdade seria "não executou".
    assert all(row['local_unit_link_status'] == UNIT_LINK_STATUS_NONE for row in rows)
