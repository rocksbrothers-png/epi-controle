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


# ── Paridade importação × cadastro manual: fornecedores (issue #169) ────────
#
# O motor de importação grava DIRETO na tabela: não passa por rota nem por
# `create_*`. Tudo que o cadastro manual transforma fora de um `normalizer`
# declarado se perde. Em `outsourced_companies` isso não era só divergência
# cosmética — `cnpj_normalized` sustenta um índice único PARCIAL
# (`WHERE cnpj_normalized <> ''`), então a linha importada ficava FORA do
# índice e o mesmo CNPJ podia entrar duas vezes.

def _valid_cnpj_from(base12: str) -> str:
    """CNPJ com dígito verificador correto — o produto valida de verdade, e
    afrouxar o validador para o teste passar não é opção."""
    digits = base12
    for weights in ([5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2],
                    [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]):
        total = sum(int(digits[i]) * weights[i] for i in range(len(weights)))
        rest = total % 11
        digits += str(0 if rest < 2 else 11 - rest)
    return digits


@pytest.fixture
def _isolated_tenant():
    """Tenant descartável com nome e CNPJ únicos.

    Não dá para usar o SAVEPOINT de ``_rollback_after`` nestes testes:
    ``create_outsourced_company`` faz ``commit()`` interno, o que descarta o
    savepoint e persiste as linhas. Aqui o tenant é único por execução e é
    apagado no teardown — o ``ON DELETE CASCADE`` de ``companies`` leva junto
    unidades e empresas terceirizadas.
    """
    import uuid
    tag = uuid.uuid4().hex[:8]
    conn = _conn()
    cnpj = _valid_cnpj_from(f'{int(tag, 16) % 10**12:012d}')
    company_id = int(conn.execute(
        'INSERT INTO companies (name, legal_name, cnpj, logo_type, plan_name, user_limit, '
        'license_status, active, commercial_notes, contract_start, contract_end, '
        "monthly_value, addendum_enabled) VALUES (?, ?, ?, 'text', 'basic', 10, 'active', 1, '', '', '', 0, 0)",
        (f'Tenant 169 {tag}', f'Tenant 169 {tag}', cnpj),
    ).lastrowid)
    conn.commit()
    try:
        yield company_id
    finally:
        conn.execute('DELETE FROM outsourced_companies WHERE company_id = ?', (company_id,))
        conn.execute('DELETE FROM companies WHERE id = ?', (company_id,))
        conn.commit()


def _import_outsourced(company_id, record):
    """Grava como o motor grava: normalizador do catálogo + colunas graváveis."""
    from modules.data_migration.catalog import get_entity
    from modules.data_migration.service import apply_domain_rules, _writable_columns
    descriptor = get_entity('fornecedores')
    normalized = apply_domain_rules(descriptor, [record])[0]
    assert not normalized.get('__domain_error__'), normalized.get('__domain_error__')
    writable = _writable_columns(_conn(), descriptor)
    payload = {k: v for k, v in normalized.items() if k in writable and str(v or '').strip()}
    columns = ['company_id', *sorted(payload)]
    values = [company_id, *[payload[k] for k in sorted(payload)]]
    placeholders = ', '.join(['?'] * len(values))
    return int(_conn().execute(
        f"INSERT INTO outsourced_companies ({', '.join(columns)}, created_at, updated_at) "  # noqa: S608 - allowlist do catálogo
        f"VALUES ({placeholders}, '', '')",
        tuple(values),
    ).lastrowid)


def test_import_and_manual_registration_store_the_same_canonical_cnpj(_isolated_tenant):
    """O defeito que originou a issue: a importação gravava o CNPJ como veio
    da planilha e deixava a coluna canônica vazia."""
    from modules.outsourced_companies.service import create_outsourced_company
    company_id = _isolated_tenant

    imported = _import_outsourced(company_id, {
        'legal_name': 'Alfa Servicos LTDA', 'cnpj': '11.222.333/0001-81',
        'company_kind': 'Terceirizada',
    })
    manual = create_outsourced_company(_conn(), {
        'legal_name': 'Beta Servicos LTDA', 'cnpj': '44.555.666/0001-81',
        'company_kind': 'Terceirizada',
    }, company_id)

    rows = {int(r[0]): dict(r) for r in _conn().execute(
        'SELECT id, cnpj, cnpj_normalized, company_kind FROM outsourced_companies '
        'WHERE company_id = ? AND id IN (?, ?)', (company_id, imported, manual)).fetchall()}

    assert rows[imported]['cnpj_normalized'] == '11222333000181', (
        'Importação deixou a coluna canônica vazia — a linha fica fora do índice '
        'parcial de deduplicação.'
    )
    # Mesma forma canônica dos dois lados: formatado em `cnpj`, dígitos em
    # `cnpj_normalized`, vocabulário controlado em `company_kind`.
    for row in rows.values():
        assert row['cnpj'] == row['cnpj'].strip() and '/' in row['cnpj']
        assert row['cnpj_normalized'].isdigit() and len(row['cnpj_normalized']) == 14
        assert row['company_kind'] == 'outsourced', (
            f"company_kind={row['company_kind']!r} fora do vocabulário controlado."
        )


def test_manual_registration_detects_a_company_that_was_imported(_isolated_tenant):
    """Antes desta correção o cadastro manual aceitava o MESMO CNPJ de uma
    empresa importada, porque procura por `cnpj_normalized` — que a
    importação deixava vazio. Duas empresas, mesmo CNPJ, mesmo tenant."""
    from modules.outsourced_companies.service import (
        DuplicateOutsourcedCompanyError,
        create_outsourced_company,
        find_outsourced_company_by_cnpj,
    )
    company_id = _isolated_tenant
    imported = _import_outsourced(company_id, {
        'legal_name': 'Gama Servicos LTDA', 'cnpj': '11.222.333/0001-81',
    })

    assert find_outsourced_company_by_cnpj(_conn(), company_id, '11222333000181') == imported

    _conn().execute('SAVEPOINT sp_dup_cnpj')
    with pytest.raises(DuplicateOutsourcedCompanyError):
        create_outsourced_company(_conn(), {
            'legal_name': 'Gama Servicos LTDA (duplicata)', 'cnpj': '11222333000181',
        }, company_id)
    _conn().execute('ROLLBACK TO SAVEPOINT sp_dup_cnpj')
    _conn().execute('RELEASE SAVEPOINT sp_dup_cnpj')


def test_the_partial_unique_index_now_covers_imported_rows(_isolated_tenant):
    """Prova no banco, não na aplicação: com a coluna canônica preenchida, o
    índice parcial passa a valer para a linha importada."""
    company_id = _isolated_tenant
    _import_outsourced(company_id, {'legal_name': 'Delta LTDA', 'cnpj': '11.222.333/0001-81'})

    _conn().execute('SAVEPOINT sp_idx')
    with pytest.raises(Exception) as excinfo:
        _import_outsourced(company_id, {'legal_name': 'Delta LTDA (outro nome)', 'cnpj': '11222333000181'})
    _conn().execute('ROLLBACK TO SAVEPOINT sp_idx')
    _conn().execute('RELEASE SAVEPOINT sp_idx')
    assert 'cnpj_normalized' in str(excinfo.value), (
        f'A violação deveria citar o índice de cnpj_normalized; veio: {excinfo.value}'
    )


def test_import_uses_the_same_domain_function_as_manual_registration():
    """Uma definição só. Se alguém criar uma segunda cópia da regra, este
    teste continua passando — mas o de paridade acima quebra na primeira
    divergência de comportamento."""
    from importlib import import_module
    from modules.data_migration.catalog import get_entity
    from modules.outsourced_companies.service import normalize_outsourced_company_domain_fields
    descriptor = get_entity('fornecedores')
    module_name, _, function_name = descriptor.normalizer.partition(':')
    assert getattr(import_module(module_name), function_name) is normalize_outsourced_company_domain_fields


def test_server_defaults_match_what_the_normalizer_would_produce_when_empty():
    """A importação não coleta `epi_responsibility`, `registration_mode` nem
    `registration_status`: eles caem no default do servidor. Isso só é
    aceitável enquanto o default do servidor for IGUAL ao que o normalizador
    produziria — senão importado e manual divergem de novo, em silêncio."""
    from modules.outsourced_companies.service import normalize_outsourced_company_domain_fields
    produced = normalize_outsourced_company_domain_fields({'legal_name': 'X'})
    columns = _columns('outsourced_companies')
    for name in ('epi_responsibility', 'registration_mode', 'registration_status'):
        server_default = str(columns[name]['column_default'] or '').split('::')[0].strip("'")
        assert produced[name] == server_default, (
            f'{name}: normalizador produz {produced[name]!r} mas o servidor grava '
            f'{server_default!r} — importado e manual divergiriam.'
        )
