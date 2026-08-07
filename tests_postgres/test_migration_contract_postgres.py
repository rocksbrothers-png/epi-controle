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

def test_employee_registration_code_uniqueness_is_scoped_per_tenant():
    """Matrícula é única POR TENANT (issue #168).

    Este teste já documentou o oposto: enquanto a constraint era
    `employees_employee_id_code_key` — UNIQUE(employee_id_code) seco — ele
    travava a característica para que ninguém a mudasse sem rever o impacto.
    A revisão aconteceu, e o escopo global era o defeito: matrícula "1001" é
    banal, o segundo cliente não conseguia cadastrá-la, e a recusa revelava a
    existência de um colaborador de outro tenant.

    Agora o teste exige o inverso — e falha se alguém restaurar o escopo global.
    """
    from epi_backend.db import row_to_dict
    rows = [row_to_dict(r) for r in _conn().execute(
        "SELECT indexname, indexdef FROM pg_indexes WHERE tablename = 'employees' "
        "AND indexdef LIKE '%UNIQUE%' AND indexdef LIKE '%employee_id_code%'",
    ).fetchall()]
    assert rows, 'Nenhum índice único sobre employee_id_code — a matrícula ficou sem proteção.'
    for row in rows:
        assert 'company_id' in row['indexdef'], (
            f"{row['indexname']} torna a matrícula única fora do tenant: {row['indexdef']}. "
            'Duas empresas diferentes precisam poder usar a mesma matrícula.'
        )
    assert not [r for r in rows if r['indexname'] == 'employees_employee_id_code_key'], (
        'O UNIQUE global `employees_employee_id_code_key` voltou. A migração em '
        'core/schema.py deveria tê-lo removido.'
    )


# ── Comportamento da unicidade da matrícula (issue #168) ───────────────────
#
# Os testes acima leem o catálogo do PostgreSQL. Os abaixo EXERCITAM a
# constraint: um índice pode existir com a definição certa e ainda assim não
# fazer o que se espera. É o mesmo princípio do ADR-0003 §10 — a suíte SQLite
# passava inteira enquanto o produto não importava um único colaborador.

def _tenant(name, cnpj):
    """Cria empresa + unidade e devolve (company_id, unit_id)."""
    conn = _conn()
    company_id = int(conn.execute(
        'INSERT INTO companies (name, legal_name, cnpj, logo_type, plan_name, user_limit, '
        'license_status, active, commercial_notes, contract_start, contract_end, '
        'monthly_value, addendum_enabled) '
        "VALUES (?, ?, ?, 'text', 'basic', 10, 'active', 1, '', '', '', 0, 0)",
        (name, name, cnpj),
    ).lastrowid)
    unit_id = int(conn.execute(
        "INSERT INTO units (company_id, name, unit_type, city, notes) VALUES (?, ?, 'base', 'Cidade', '')",
        (company_id, f'Unidade {name}'),
    ).lastrowid)
    return company_id, unit_id


def _insert_employee(company_id, unit_id, code, cpf, name):
    return _conn().execute(
        'INSERT INTO employees (company_id, unit_id, employee_id_code, cpf, name, sector, '
        'role_name, admission_date, schedule_type) '
        "VALUES (?, ?, ?, ?, ?, '', 'Operador', '2024-01-10', '')",
        (company_id, unit_id, code, cpf, name),
    )


@pytest.fixture
def _rollback_after():
    """Cada teste roda isolado: nada do que ele grava sobrevive."""
    conn = _conn()
    conn.execute('SAVEPOINT sp_matricula_test')
    yield
    conn.execute('ROLLBACK TO SAVEPOINT sp_matricula_test')
    conn.execute('RELEASE SAVEPOINT sp_matricula_test')


def test_two_tenants_can_use_the_same_registration_code(_rollback_after):
    """O caso que a constraint global barrava. '1001' é uma matrícula banal:
    é esperado que o segundo cliente a use, e nada nele tem relação com o
    primeiro."""
    company_a, unit_a = _tenant('Cliente Alfa 168', '11111111000191')
    company_b, unit_b = _tenant('Cliente Beta 168', '22222222000191')

    _insert_employee(company_a, unit_a, '1001', '11144477735', 'Pessoa do Alfa')
    _insert_employee(company_b, unit_b, '1001', '12345678909', 'Pessoa do Beta')

    rows = _conn().execute(
        "SELECT company_id, name FROM employees WHERE employee_id_code = '1001' ORDER BY company_id",
    ).fetchall()
    assert len(rows) == 2, 'Os dois tenants precisam conseguir usar a mesma matrícula.'
    assert {int(r[0]) for r in rows} == {company_a, company_b}


def test_the_same_tenant_still_cannot_duplicate_a_registration_code(_rollback_after):
    """Afrouxar o escopo não pode virar afrouxar a proteção: dentro da empresa
    a matrícula continua sendo identificador único."""
    company_a, unit_a = _tenant('Cliente Gama 168', '33333333000191')
    _insert_employee(company_a, unit_a, '2002', '11144477735', 'Primeiro')

    _conn().execute('SAVEPOINT sp_dup')
    with pytest.raises(Exception) as excinfo:
        _insert_employee(company_a, unit_a, '2002', '12345678909', 'Segundo')
    _conn().execute('ROLLBACK TO SAVEPOINT sp_dup')
    _conn().execute('RELEASE SAVEPOINT sp_dup')

    assert 'employee_id_code' in str(excinfo.value), (
        f'A violação deveria citar employee_id_code; veio: {excinfo.value}'
    )


def test_registration_code_collision_message_names_the_company_scope(_rollback_after):
    """A mensagem ao operador já dizia 'para esta empresa' quando a constraint
    era global — afirmando um escopo que ela não tinha. Agora é verdade, e o
    nome novo do índice precisa continuar sendo reconhecido."""
    from app import humanize_integrity_error
    company_a, unit_a = _tenant('Cliente Delta 168', '44444444000191')
    _insert_employee(company_a, unit_a, '3003', '11144477735', 'Primeiro')

    _conn().execute('SAVEPOINT sp_msg')
    with pytest.raises(Exception) as excinfo:
        _insert_employee(company_a, unit_a, '3003', '12345678909', 'Segundo')
    _conn().execute('ROLLBACK TO SAVEPOINT sp_msg')
    _conn().execute('RELEASE SAVEPOINT sp_msg')

    assert humanize_integrity_error(excinfo.value) == 'ID do colaborador já cadastrado para esta empresa.'
