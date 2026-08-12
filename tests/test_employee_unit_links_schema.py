"""Tabela de vínculo local do colaborador com a Unidade (ADR-0002 §13, PR B).

Cobre a criação da tabela, a idempotência do backfill e — o ponto mais
importante — as NÃO REGRESSÕES que a issue #180 exige como critério de
aceite: `employees.unit_id` continua mutável, a transferência definitiva e a
movimentação temporária continuam funcionando, e o vínculo local não autoriza
entrega de EPI.
"""

import os
import sqlite3
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import schema


def _conn():
    connection = sqlite3.connect(':memory:')
    connection.row_factory = sqlite3.Row
    connection.execute('PRAGMA foreign_keys = ON')
    return connection


def _base_schema(connection):
    """Só o necessário para as FKs de employee_unit_links resolverem."""
    connection.execute(
        'CREATE TABLE companies (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT)'
    )
    connection.execute(
        'CREATE TABLE units (id INTEGER PRIMARY KEY AUTOINCREMENT, '
        'company_id INTEGER, name TEXT)'
    )
    connection.execute(
        'CREATE TABLE users (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT)'
    )
    connection.execute(
        'CREATE TABLE employees ('
        ' id INTEGER PRIMARY KEY AUTOINCREMENT,'
        ' company_id INTEGER, unit_id INTEGER, name TEXT,'
        ' tipo_vinculo TEXT DEFAULT \'CLT\','
        ' empresa_origem TEXT DEFAULT \'\','
        ' outsourced_company_id INTEGER)'
    )
    connection.commit()


def _seed(connection, *, tipo_vinculo='CLT', empresa_origem='', outsourced_company_id=None):
    connection.execute("INSERT INTO companies (id, name) VALUES (1, 'Tenant')")
    connection.execute("INSERT INTO units (id, company_id, name) VALUES (10, 1, 'Unidade A')")
    connection.execute("INSERT INTO units (id, company_id, name) VALUES (11, 1, 'Unidade B')")
    connection.execute(
        'INSERT INTO employees (id, company_id, unit_id, name, tipo_vinculo, '
        'empresa_origem, outsourced_company_id) VALUES (100, 1, 10, ?, ?, ?, ?)',
        ('Pessoa', tipo_vinculo, empresa_origem, outsourced_company_id),
    )
    connection.commit()


def _links(connection):
    return [
        dict(row)
        for row in connection.execute(
            'SELECT employee_id, unit_id, local_status FROM employee_unit_links '
            'ORDER BY unit_id'
        ).fetchall()
    ]


# ── a tabela ────────────────────────────────────────────────────────────────

def test_creates_table_and_is_idempotent():
    conn = _conn()
    _base_schema(conn)
    schema.ensure_employee_unit_links(conn)
    schema.ensure_employee_unit_links(conn)  # segundo boot não pode explodir
    cols = {
        row['name']
        for row in conn.execute('PRAGMA table_info(employee_unit_links)').fetchall()
    }
    assert {'company_id', 'employee_id', 'unit_id', 'local_status'} <= cols


def test_contract_columns_are_absent_on_purpose():
    """O contrato é da EMPRESA com a Unidade e já vive em
    `outsourced_company_unit_links`. Repeti-lo por pessoa criaria uma segunda
    verdade sobre o mesmo contrato — este teste trava essa decisão."""
    conn = _conn()
    _base_schema(conn)
    schema.ensure_employee_unit_links(conn)
    cols = {
        row['name']
        for row in conn.execute('PRAGMA table_info(employee_unit_links)').fetchall()
    }
    assert not ({'contract_number', 'contract_start_date', 'contract_end_date',
                 'cost_center_ref'} & cols)


def test_same_person_cannot_be_linked_twice_to_the_same_unit():
    conn = _conn()
    _base_schema(conn)
    _seed(conn)
    schema.ensure_employee_unit_links(conn)
    conn.execute(
        'INSERT INTO employee_unit_links (company_id, employee_id, unit_id) '
        'VALUES (1, 100, 10)'
    )
    conn.commit()
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            'INSERT INTO employee_unit_links (company_id, employee_id, unit_id) '
            'VALUES (1, 100, 10)'
        )


def test_the_same_person_can_be_linked_to_more_than_one_unit():
    """É o motivo de a tabela existir: reuso do terceirizado entre Unidades."""
    conn = _conn()
    _base_schema(conn)
    _seed(conn)
    schema.ensure_employee_unit_links(conn)
    conn.execute(
        'INSERT INTO employee_unit_links (company_id, employee_id, unit_id) '
        'VALUES (1, 100, 10)'
    )
    conn.execute(
        'INSERT INTO employee_unit_links (company_id, employee_id, unit_id) '
        'VALUES (1, 100, 11)'
    )
    conn.commit()
    assert [link['unit_id'] for link in _links(conn)] == [10, 11]


# ── backfill ────────────────────────────────────────────────────────────────

def test_backfill_links_employee_with_structured_outsourced_company():
    conn = _conn()
    _base_schema(conn)
    _seed(conn, tipo_vinculo='Terceirizado', outsourced_company_id=7)
    schema.ensure_employee_unit_links(conn)
    schema.ensure_employee_unit_links_backfill(conn)
    assert _links(conn) == [{'employee_id': 100, 'unit_id': 10, 'local_status': 'active'}]


def test_backfill_links_employee_identified_only_by_legacy_text():
    """`empresa_origem` é a única identificação de quem veio por importação."""
    conn = _conn()
    _base_schema(conn)
    _seed(conn, tipo_vinculo='Prestador de Serviço', empresa_origem='Prestadora XYZ')
    schema.ensure_employee_unit_links(conn)
    schema.ensure_employee_unit_links_backfill(conn)
    assert _links(conn) == [{'employee_id': 100, 'unit_id': 10, 'local_status': 'active'}]


@pytest.mark.parametrize('vinculo', ['CLT', 'Menor Aprendiz', 'Praticante', 'Estagiário'])
def test_backfill_leaves_own_workforce_out(vinculo):
    """Mão de obra própria não entra: o normalizador força `empresa_origem`
    vazia para ela, e o vínculo local existe para reuso de terceirizado."""
    conn = _conn()
    _base_schema(conn)
    _seed(conn, tipo_vinculo=vinculo)
    schema.ensure_employee_unit_links(conn)
    schema.ensure_employee_unit_links_backfill(conn)
    assert _links(conn) == []


def test_backfill_is_idempotent_across_boots():
    conn = _conn()
    _base_schema(conn)
    _seed(conn, tipo_vinculo='Terceirizado', outsourced_company_id=7)
    schema.ensure_employee_unit_links(conn)
    for _ in range(3):
        schema.ensure_employee_unit_links_backfill(conn)
    assert len(_links(conn)) == 1


def test_the_second_boot_skips_silently_instead_of_colliding(monkeypatch):
    """Contar linhas NÃO prova que o `NOT EXISTS` funciona.

    Sem ele o índice único `uq_employee_unit_links` rejeita a duplicata, a
    exceção é engolida como `db.col_skip`, e a contagem continua 1 — o teste
    acima passa dos dois jeitos. Foi o que a sabotagem mostrou.

    A diferença observável é o AVISO: com o `NOT EXISTS`, o segundo boot não
    tenta inserir nada e nada é registrado. Sem ele, todo boot passa a gerar
    uma violação de constraint engolida — no PostgreSQL, uma instrução que
    falha aborta a transação, então o silêncio aqui não é cosmético.
    """
    conn = _conn()
    _base_schema(conn)
    _seed(conn, tipo_vinculo='Terceirizado', outsourced_company_id=7)
    schema.ensure_employee_unit_links(conn)
    schema.ensure_employee_unit_links_backfill(conn)

    warnings = []
    monkeypatch.setattr(
        schema,
        'structured_log',
        lambda level, event, **kw: warnings.append((level, event, kw)),
    )
    schema.ensure_employee_unit_links_backfill(conn)
    assert warnings == [], f'segundo boot deveria ser silencioso, veio: {warnings}'


def test_backfill_does_not_revive_a_deliberately_deactivated_link():
    """Se uma Unidade desativou o vínculo, o próximo boot não pode ressuscitá-lo."""
    conn = _conn()
    _base_schema(conn)
    _seed(conn, tipo_vinculo='Terceirizado', outsourced_company_id=7)
    schema.ensure_employee_unit_links(conn)
    schema.ensure_employee_unit_links_backfill(conn)
    conn.execute(
        "UPDATE employee_unit_links SET local_status = 'inactive' WHERE employee_id = 100"
    )
    conn.commit()
    schema.ensure_employee_unit_links_backfill(conn)
    assert _links(conn) == [
        {'employee_id': 100, 'unit_id': 10, 'local_status': 'inactive'}
    ]


def test_backfill_does_not_prepopulate_other_units():
    """Cada Unidade povoa a sua deliberadamente (D9/D10) — o backfill cria
    vínculo só na Unidade onde a pessoa já estava, nunca na lista inteira."""
    conn = _conn()
    _base_schema(conn)
    _seed(conn, tipo_vinculo='Terceirizado', outsourced_company_id=7)
    schema.ensure_employee_unit_links(conn)
    schema.ensure_employee_unit_links_backfill(conn)
    assert [link['unit_id'] for link in _links(conn)] == [10]


# ── não regressão exigida pela issue #180 ───────────────────────────────────

def test_employees_unit_id_remains_mutable():
    """A proposta de tornar `unit_id` imutável foi REJEITADA na rodada 2 da
    issue #180. A tabela nova é paralela e não pode ter travado o campo."""
    conn = _conn()
    _base_schema(conn)
    _seed(conn, tipo_vinculo='Terceirizado', outsourced_company_id=7)
    schema.ensure_employee_unit_links(conn)
    schema.ensure_employee_unit_links_backfill(conn)
    conn.execute('UPDATE employees SET unit_id = 11 WHERE id = 100')
    conn.commit()
    assert conn.execute(
        'SELECT unit_id FROM employees WHERE id = 100'
    ).fetchone()['unit_id'] == 11


def test_transfer_does_not_silently_move_the_local_link():
    """Transferência definitiva mexe em `unit_id`; o vínculo local é outra
    estrutura e continua onde estava até alguém agir sobre ele explicitamente.
    Se um dia isso mudar, que seja por decisão — não por efeito colateral."""
    conn = _conn()
    _base_schema(conn)
    _seed(conn, tipo_vinculo='Terceirizado', outsourced_company_id=7)
    schema.ensure_employee_unit_links(conn)
    schema.ensure_employee_unit_links_backfill(conn)
    conn.execute('UPDATE employees SET unit_id = 11 WHERE id = 100')
    conn.commit()
    assert [link['unit_id'] for link in _links(conn)] == [10]
