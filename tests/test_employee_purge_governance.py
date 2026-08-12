"""Governança de exclusão definitiva com vínculo local (ADR-0002 §13.5, PR E).

Regra: vínculo local ATIVO em qualquer Unidade do tenant bloqueia a purga.
Vínculo arquivado não bloqueia por si só — as demais regras de retenção
seguem valendo e podem bloquear por conta própria.

O vínculo nunca é apagado automaticamente para liberar a exclusão. Quem quer
excluir arquiva o vínculo em cada Unidade, deliberadamente, deixando ator e
motivo registrados — em vez de sumir com a linha para destravar um botão.
"""

import os
import sqlite3
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import archival, schema
from modules.employees.service import (
    employee_blocking_unit_links,
    employee_deletion_readiness,
    ensure_employee_purge_allowed,
)

GENERAL_ADMIN = {'id': 1, 'role': 'general_admin', 'company_id': 1}
REGISTRY_ADMIN = {'id': 2, 'role': 'registry_admin', 'company_id': 1}


def _conn():
    connection = sqlite3.connect(':memory:')
    connection.row_factory = sqlite3.Row
    connection.executescript("""
        CREATE TABLE companies (id INTEGER PRIMARY KEY, name TEXT);
        CREATE TABLE units (id INTEGER PRIMARY KEY, name TEXT, company_id INTEGER);
        CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT);
        CREATE TABLE employees (
            id INTEGER PRIMARY KEY, company_id INTEGER, unit_id INTEGER, name TEXT,
            status TEXT DEFAULT 'archived', retention_until TEXT DEFAULT '',
            legal_hold INTEGER DEFAULT 0, legal_hold_reason TEXT DEFAULT ''
        );
        INSERT INTO companies (id, name) VALUES (1, 'Tenant A'), (2, 'Tenant B');
        INSERT INTO units (id, name, company_id)
            VALUES (10, 'Base Santos', 1), (11, 'Plataforma P-50', 1), (20, 'Unidade de B', 2);
        INSERT INTO users (id, name) VALUES (1, 'Geral'), (2, 'Registro');
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


# ── bloqueio por vínculo ativo ──────────────────────────────────────────────

def test_one_active_link_blocks_the_purge():
    conn = _conn()
    _link(conn, 10, 'active')
    with pytest.raises(ValueError, match='vínculo ativo'):
        ensure_employee_purge_allowed(conn, _employee(conn))


def test_several_active_links_block_and_are_all_named():
    """A mensagem precisa listar TODAS as Unidades: bloquear sem dizer onde
    obriga o operador a caçar Unidade por Unidade."""
    conn = _conn()
    _link(conn, 10, 'active')
    _link(conn, 11, 'active')
    with pytest.raises(ValueError) as excinfo:
        ensure_employee_purge_allowed(conn, _employee(conn))
    message = str(excinfo.value)
    assert '2 Unidade(s)' in message
    assert 'Base Santos' in message
    assert 'Plataforma P-50' in message


def test_an_active_link_in_another_unit_also_blocks():
    """"Qualquer Unidade do tenant" — não só a Unidade-base da pessoa.

    O colaborador mora na Unidade 10; o vínculo ativo está na 11.
    """
    conn = _conn()
    _link(conn, 11, 'active')
    with pytest.raises(ValueError, match='Plataforma P-50'):
        ensure_employee_purge_allowed(conn, _employee(conn))


def test_all_links_archived_lets_the_other_retention_rules_decide():
    """Vínculo arquivado não bloqueia por si só — a precondição passa e a
    palavra volta para `core.archival.ensure_purge_allowed`."""
    conn = _conn()
    _link(conn, 10, 'inactive')
    _link(conn, 11, 'inactive')
    ensure_employee_purge_allowed(conn, _employee(conn))


def test_no_link_at_all_does_not_block():
    conn = _conn()
    ensure_employee_purge_allowed(conn, _employee(conn))


def test_another_tenant_link_does_not_interfere():
    """Vínculo de outro tenant, mesmo com id de colaborador coincidente, não
    bloqueia — a consulta filtra por `company_id`."""
    conn = _conn()
    _link(conn, 20, 'active', employee_id=100, company_id=2)
    ensure_employee_purge_allowed(conn, _employee(conn))


def test_the_link_is_never_deleted_to_unblock():
    """A precondição é somente leitura: recusa, e não remove nada."""
    conn = _conn()
    _link(conn, 10, 'active')
    with pytest.raises(ValueError):
        ensure_employee_purge_allowed(conn, _employee(conn))
    remaining = conn.execute('SELECT COUNT(*) AS n FROM employee_unit_links').fetchone()['n']
    assert remaining == 1


# ── a regra genérica não foi contaminada ────────────────────────────────────

def test_the_generic_purge_rule_stays_free_of_employee_links():
    """`core.archival.ensure_purge_allowed` atende colaborador, EPI e empresa
    terceirizada, e é PURA (não recebe `connection`).

    Se alguém puser a checagem de `employee_unit_links` lá dentro, um EPI de
    id 5 passa a ser bloqueado pelo vínculo do colaborador de id 5 — colisão
    de ids entre tabelas, no caminho da exclusão definitiva.
    """
    import inspect

    source = inspect.getsource(archival.ensure_purge_allowed)
    assert 'employee_unit_links' not in source, (
        'a precondição de vínculo é específica de colaborador; na função '
        'genérica ela colidiria ids entre tabelas diferentes'
    )
    assert 'connection' not in inspect.signature(archival.ensure_purge_allowed).parameters


def test_archiving_and_restoring_are_untouched():
    """Arquivar e desarquivar não passam por `ensure_purge_allowed` e não
    podem ter sido afetados pela precondição nova."""
    import inspect

    for fn in (archival.archive_record, archival.restore_record):
        source = inspect.getsource(fn)
        assert 'ensure_purge_allowed' not in source, f'{fn.__name__} não deve validar purga'
        assert 'employee_unit_links' not in source, f'{fn.__name__} não deve olhar vínculo local'


def test_cancelling_a_purge_is_not_blocked_by_links():
    """Cancelar é desescalada. Exigir ausência de vínculo para DESISTIR da
    exclusão prenderia o registro em `pending_deletion`."""
    import pathlib
    import re

    body = pathlib.Path('modules/employees/routes.py').read_text(encoding='utf-8')
    match = re.search(
        r'def handle_post_employee_purge_cancel.*?(?=\ndef |\Z)', body, re.DOTALL
    )
    assert match, 'rota de cancelamento não encontrada'
    assert '_ensure_employee_purge_allowed_audited' not in match.group(0)


@pytest.mark.parametrize('func_name', [
    'handle_post_employee_purge_request',
    'handle_post_employee_purge_confirm',
])
def test_both_purge_steps_check_the_precondition(func_name):
    """A etapa 2 revalida: entre pedir e confirmar, uma Unidade pode ter criado
    vínculo novo, e confirmar sem reconferir apagaria alguém que voltou a ser
    usado no intervalo."""
    import pathlib
    import re

    body = pathlib.Path('modules/employees/routes.py').read_text(encoding='utf-8')
    match = re.search(rf'def {func_name}.*?(?=\ndef |\Z)', body, re.DOTALL)
    assert match, f'{func_name} não encontrada'
    assert '_ensure_employee_purge_allowed_audited' in match.group(0)


# ── permissão continua mandando ─────────────────────────────────────────────

@pytest.mark.parametrize('role', ['admin', 'user', 'master_admin'])
def test_profiles_without_permission_still_cannot_purge(role):
    """A precondição nova não afrouxa quem pode purgar: `ensure_purge_allowed`
    continua exigindo Administrador Geral ou de Registro."""
    record = {'id': 100, 'company_id': 1, 'status': 'archived', 'legal_hold': 0}
    with pytest.raises(PermissionError):
        archival.ensure_purge_allowed(record, {'id': 9, 'role': role, 'company_id': 1}, 'Colaborador')


@pytest.mark.parametrize('actor', [GENERAL_ADMIN, REGISTRY_ADMIN])
def test_authorised_profiles_still_pass_the_permission_check(actor):
    record = {'id': 100, 'company_id': 1, 'status': 'archived', 'legal_hold': 0}
    archival.ensure_purge_allowed(record, actor, 'Colaborador')


# ── aviso antecipado ────────────────────────────────────────────────────────

def test_the_advisory_names_the_blocking_units():
    conn = _conn()
    _link(conn, 10, 'active')
    _link(conn, 11, 'active')
    readiness = employee_deletion_readiness(conn, _employee(conn))
    assert readiness['eligible'] is False
    assert 'active_unit_links' in readiness['blocking_reasons']
    names = sorted(item['unit_name'] for item in readiness['blocking_unit_links'])
    assert names == ['Base Santos', 'Plataforma P-50']
    assert 'Arquive o vínculo local' in readiness['available_action']


def test_the_advisory_ignores_archived_links():
    conn = _conn()
    _link(conn, 10, 'inactive')
    readiness = employee_deletion_readiness(conn, _employee(conn))
    assert readiness['eligible'] is True
    assert readiness['blocking_unit_links'] == []
    assert 'Elegível' in readiness['available_action']


def test_the_advisory_reports_the_retention_date_and_days():
    from datetime import datetime, timedelta, timezone

    conn = _conn()
    until = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
    conn.execute('UPDATE employees SET retention_until = ? WHERE id = 100', (until,))
    conn.commit()
    readiness = employee_deletion_readiness(conn, _employee(conn))
    assert readiness['eligible'] is False
    assert 'retention_period' in readiness['blocking_reasons']
    assert readiness['retention_days_remaining'] > 0
    assert readiness['retention_until'] == until
    assert 'Aguarde' in readiness['available_action']


def test_the_advisory_reports_legal_hold():
    conn = _conn()
    conn.execute('UPDATE employees SET legal_hold = 1 WHERE id = 100')
    conn.commit()
    readiness = employee_deletion_readiness(conn, _employee(conn))
    assert readiness['legal_hold'] is True
    assert 'legal_hold' in readiness['blocking_reasons']


def test_the_advisory_lists_every_reason_at_once():
    """Mostrar um impedimento por vez faria o operador resolver, tentar de
    novo e descobrir o seguinte."""
    from datetime import datetime, timedelta, timezone

    conn = _conn()
    until = (datetime.now(timezone.utc) + timedelta(days=10)).isoformat()
    conn.execute(
        'UPDATE employees SET retention_until = ?, legal_hold = 1 WHERE id = 100', (until,)
    )
    conn.commit()
    _link(conn, 10, 'active')
    readiness = employee_deletion_readiness(conn, _employee(conn))
    assert set(readiness['blocking_reasons']) == {
        'legal_hold', 'retention_period', 'active_unit_links'
    }


def test_blocking_units_query_is_tenant_scoped():
    conn = _conn()
    _link(conn, 20, 'active', employee_id=100, company_id=2)
    assert employee_blocking_unit_links(conn, _employee(conn)) == []


def test_the_summary_route_exposes_the_advisory():
    import pathlib

    body = pathlib.Path('modules/employees/routes.py').read_text(encoding='utf-8')
    assert "'deletion_readiness': employee_deletion_readiness(" in body, (
        'o resumo de exclusão precisa expor o aviso antecipado'
    )
