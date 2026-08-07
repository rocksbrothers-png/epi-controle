"""Contrato catálogo × schema PostgreSQL REAL (ADR-0003 §12.3).

Este arquivo vive em ``tests_postgres/`` porque o schema só existe em
PostgreSQL: ``core/database.py`` não tem driver SQLite, e o schema que a
suíte padrão usa é um fixture escrito à mão. Comparar o catálogo contra um
fixture é comparar contra uma cópia — e cópia diverge. Já divergiu duas
vezes:

- ``employees.unit_id`` é NOT NULL, o catálogo dizia opcional;
- ``employees.employee_id_code`` é NOT NULL sem default, e a primeira versão
  deste contrato (com CREATE TABLE copiado à mão) declarava ``DEFAULT ''``,
  não pegando o problema.

A regra travada aqui:

    Uma coluna que o PostgreSQL exige nunca pode ser apresentada como
    opcional na importação, a menos que o catálogo declare um default
    determinístico e justificado em ``column_defaults``.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

pytestmark = pytest.mark.skipif(
    not os.environ.get('DATABASE_URL', '').startswith('postgres'),
    reason='Contrato de schema exige PostgreSQL real.',
)

_CONNECTION = None


def _conn():
    global _CONNECTION
    if _CONNECTION is None:
        from core.database import get_connection
        _CONNECTION = get_connection()
    return _CONNECTION


@pytest.fixture(scope='module', autouse=True)
def bootstrapped_schema():
    from core.bootstrap import init_db
    init_db()
    yield


def _enabled():
    from modules.data_migration.catalog import ENTITIES
    return [d for d in ENTITIES.values() if d.enabled]


def _columns(table):
    """Nullability, default e tipo direto do information_schema."""
    from epi_backend.db import row_to_dict
    rows = _conn().execute(
        'SELECT column_name, is_nullable, column_default, data_type '
        'FROM information_schema.columns WHERE table_name = %s',
        (table,),
    ).fetchall()
    return {row_to_dict(r)['column_name']: row_to_dict(r) for r in rows}


def _required_without_default(table):
    return {
        name for name, meta in _columns(table).items()
        if meta['is_nullable'] == 'NO' and meta['column_default'] is None and name != 'id'
    }


def _foreign_keys(table):
    from epi_backend.db import row_to_dict
    rows = _conn().execute(
        """
        SELECT kcu.column_name, ccu.table_name AS referenced_table
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
          ON tc.constraint_name = kcu.constraint_name
        JOIN information_schema.constraint_column_usage ccu
          ON tc.constraint_name = ccu.constraint_name
        WHERE tc.constraint_type = 'FOREIGN KEY' AND tc.table_name = %s
        """,
        (table,),
    ).fetchall()
    return {row_to_dict(r)['column_name']: row_to_dict(r)['referenced_table'] for r in rows}


# ── O contrato central ─────────────────────────────────────────────────────

@pytest.mark.parametrize('entity_key', [d.key for d in _enabled()])
def test_every_column_postgres_requires_is_covered_by_the_catalog(entity_key):
    from modules.data_migration.catalog import get_entity
    descriptor = get_entity(entity_key)
    required = _required_without_default(descriptor.target_table)
    declared = {name for name, _ in descriptor.column_defaults}
    uncovered = required - set(descriptor.required_fields()) - declared - {'company_id'}
    assert not uncovered, (
        f'{entity_key}: {sorted(uncovered)} são NOT NULL sem default no PostgreSQL e '
        f'não estão nem como campo obrigatório nem em column_defaults. A importação '
        f'falharia na gravação.'
    )


@pytest.mark.parametrize('entity_key', [d.key for d in _enabled()])
def test_no_database_required_column_is_offered_as_optional(entity_key):
    from modules.data_migration.catalog import get_entity
    descriptor = get_entity(entity_key)
    required = _required_without_default(descriptor.target_table)
    declared = {name for name, _ in descriptor.column_defaults}
    offenders = [
        spec.name for spec in descriptor.fields
        if spec.name in required and not spec.required and spec.name not in declared
    ]
    assert not offenders, (
        f'{entity_key}: {offenders} aparecem como opcionais no assistente mas o '
        f'PostgreSQL os exige. O usuário deixaria de mapeá-los e a gravação falharia.'
    )


@pytest.mark.parametrize('entity_key', [d.key for d in _enabled()])
def test_declared_defaults_do_not_shadow_a_server_side_default(entity_key):
    """Default declarado numa coluna que o servidor já preenche é ruído — e
    pior, sobrescreveria o valor do servidor com string vazia."""
    from modules.data_migration.catalog import get_entity
    descriptor = get_entity(entity_key)
    columns = _columns(descriptor.target_table)
    for name, _value in descriptor.column_defaults:
        meta = columns.get(name)
        assert meta, f'{entity_key}.{name} não existe em {descriptor.target_table}.'
        assert meta['column_default'] is None, (
            f'{entity_key}.{name} já tem DEFAULT no servidor '
            f'({meta["column_default"]!r}) — remova de column_defaults.'
        )
        assert meta['is_nullable'] == 'NO', (
            f'{entity_key}.{name} aceita NULL — não precisa de default declarado.'
        )


# ── Chaves estrangeiras e resolvers ────────────────────────────────────────

@pytest.mark.parametrize('entity_key', [d.key for d in _enabled()])
def test_every_foreign_key_the_import_writes_is_either_resolvable_or_defaulted(entity_key):
    """FK obrigatória tem de ter caminho: ou é campo resolvível por nome, ou
    tem default. Senão só importa quem já souber o id interno — que nenhum
    sistema legado conhece."""
    from modules.data_migration.catalog import get_entity
    descriptor = get_entity(entity_key)
    required = _required_without_default(descriptor.target_table)
    declared = {name for name, _ in descriptor.column_defaults}
    resolvable = {spec.name for spec in descriptor.fields if spec.resolves_to}
    for column, referenced in _foreign_keys(descriptor.target_table).items():
        if column in ('company_id',) or column not in required:
            continue
        assert column in resolvable or column in declared, (
            f'{entity_key}.{column} é FK obrigatória para {referenced} e não é '
            f'resolvível por nome nem tem default — a importação seria impossível '
            f'a partir de um export legado.'
        )


@pytest.mark.parametrize('entity_key', [d.key for d in _enabled()])
def test_resolver_targets_exist_and_are_tenant_scoped(entity_key):
    from modules.data_migration.catalog import get_entity
    descriptor = get_entity(entity_key)
    for spec in descriptor.fields:
        if not spec.resolves_to:
            continue
        table, column = spec.resolves_to
        columns = _columns(table)
        assert columns, f'{entity_key}.{spec.name}: tabela {table} não existe.'
        assert column in columns, f'{entity_key}.{spec.name}: {table}.{column} não existe.'
        assert 'company_id' in columns, (
            f'{entity_key}.{spec.name}: {table} não tem company_id — o resolver não '
            f'teria como respeitar o isolamento multi-tenant.'
        )


def test_unit_reference_is_required_and_resolvable_by_name():
    from modules.data_migration.catalog import get_entity
    spec = get_entity('colaboradores').spec_for('unit_id')
    assert spec.required is True
    assert spec.resolves_to == ('units', 'name')


# ── Documentação viva de riscos de schema ──────────────────────────────────

def test_employee_registration_code_uniqueness_is_global_not_per_tenant():
    """Documenta um risco REAL do schema atual (ADR-0003 §11).

    `employees_employee_id_code_key` é UNIQUE global. Dois tenants não podem
    ter a mesma matrícula, o que pode barrar uma importação legítima. Este
    teste não corrige o schema — ele impede que a característica mude sem que
    alguém reveja o impacto na migração.
    """
    from epi_backend.db import row_to_dict
    rows = [row_to_dict(r) for r in _conn().execute(
        "SELECT indexdef FROM pg_indexes WHERE tablename = 'employees' "
        "AND indexname = 'employees_employee_id_code_key'",
    ).fetchall()]
    if not rows:
        pytest.skip('Índice não presente nesta versão do schema.')
    indexdef = rows[0]['indexdef']
    assert 'company_id' not in indexdef, (
        'O índice passou a ser por empresa — ótimo, mas revise o catálogo e o '
        'ADR-0003 §11, que documentam a limitação oposta.'
    )
