"""Jornada completa do Centro de Migração contra PostgreSQL REAL (ADR-0003 §12).

Vive fora de ``tests/`` de propósito: a suíte padrão roda em SQLite e não deve
coletar este arquivo. O workflow ``PostgreSQL Migration Journey`` executa
``pytest tests_postgres/`` com ``DATABASE_URL`` apontando para um PostgreSQL de
verdade.

Por que existe: a Fase 1 do módulo passou com toda a suíte SQLite verde e
mesmo assim **não importava um único colaborador** em PostgreSQL. Três
defeitos (transação abortada em cascata, preview mentindo sobre NOT NULL, e
nenhuma tradução de nome para id) só apareceram no banco real. Nenhuma
funcionalidade de migração é considerada pronta sem esta jornada passar.

Cada teste é uma etapa da jornada e roda em ordem, compartilhando o tenant
criado no início — é uma jornada, não casos independentes.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

pytestmark = pytest.mark.skipif(
    not os.environ.get('DATABASE_URL', '').startswith('postgres'),
    reason='Jornada exige DATABASE_URL apontando para PostgreSQL real.',
)

VALID_CPF_A = '111.444.777-35'
VALID_CPF_B = '529.982.247-25'
VALID_CPF_C = '390.533.447-05'
STORED_CPF_A = '11144477735'

# CPFs válidos exclusivos da etapa de falha de banco — assim o resultado
# não depende do que as etapas anteriores gravaram.
FRESH_CPF_A = '12345678909'
REJECTED_CPF = '98765432100'
FRESH_CPF_C = '11122233396'

# Export legado realista: cabeçalho misturando português e inglês, separador
# ';' e codificação latin-1 — como sai de um TOTVS/Senior antigo.
LEGACY_CSV = (
    'Employee Name;Registration;CPF;Department;Job Title;Hire Date\n'
    f'Maria Silva;7781;{VALID_CPF_A};Produção;Soldadora;2023-04-01\n'
    f'João Souza;7782;{VALID_CPF_B};Manutenção;Eletricista;2022-11-15\n'
    f'Ana Lima;7783;{VALID_CPF_C};Manutenção;Mecânica;2024-02-20\n'
)

MAPPING = {
    'Employee Name': 'name',
    'Registration': 'employee_id_code',
    'CPF': 'cpf',
    'Department': 'unit_id',
    'Job Title': 'role_name',
    'Hire Date': 'admission_date',
}


_CONNECTION = None


def _conn():
    """Uma única conexão para toda a jornada.

    Pegar uma nova do pool a cada chamada o esgotaria — e, mais importante,
    a jornada precisa provar que *a mesma* conexão continua sadia depois de
    uma linha falhar.
    """
    global _CONNECTION
    if _CONNECTION is None:
        from core.database import get_connection
        _CONNECTION = get_connection()
    return _CONNECTION


def _scalar(connection, sql, params=()):
    from epi_backend.db import row_to_dict
    row = connection.execute(sql, params).fetchone()
    return next(iter(row_to_dict(row).values())) if row else None


@pytest.fixture(scope='module', autouse=True)
def bootstrapped_schema():
    """Aplica TODAS as migrations a partir de um banco vazio."""
    from core.bootstrap import init_db
    init_db()
    yield


@pytest.fixture(autouse=True)
def _request_boundary():
    """Começa cada etapa com a transação limpa, como uma requisição nova.

    Em produção cada rota faz ``closing(get_connection())``: a transação morre
    no fim do request e a seguinte começa do zero. A jornada compartilha UMA
    conexão de propósito — para provar que o motor a devolve utilizável — mas
    sem esta fronteira um erro de negócio esperado numa etapa contaminaria a
    seguinte por um motivo que produção não tem.

    A garantia forte continua sendo provada onde importa: dentro de
    ``run_migration``, o diagnóstico da linha ruim e o fechamento do job são
    gravados na MESMA conexão, depois da falha.
    """
    yield
    if _CONNECTION is not None:
        _CONNECTION.rollback()


@pytest.fixture(scope='module')
def tenant(bootstrapped_schema):
    """Tenant completo: empresa, CNPJ (quando disponível), unidades e usuário."""
    from core.security import hash_password
    connection = _conn()
    company_id = _scalar(
        connection,
        "INSERT INTO companies (name, cnpj, logo_type) VALUES (%s, %s, '') RETURNING id",
        ('Metalúrgica Aurora', '11222333000181'),
    )
    other_company_id = _scalar(
        connection,
        "INSERT INTO companies (name, cnpj, logo_type) VALUES (%s, %s, '') RETURNING id",
        ('Concorrente S.A.', '99888777000166'),
    )
    units = {}
    for name in ('Produção', 'Manutenção'):
        units[name] = _scalar(
            connection,
            'INSERT INTO units (company_id, name, unit_type, city) '
            'VALUES (%s, %s, %s, %s) RETURNING id',
            (company_id, name, 'base', 'Macaé'),
        )
    # Mesma unidade, tenant diferente: prova de isolamento do resolver.
    other_unit_id = _scalar(
        connection,
        'INSERT INTO units (company_id, name, unit_type, city) '
        'VALUES (%s, %s, %s, %s) RETURNING id',
        (other_company_id, 'Produção', 'base', 'Rio das Ostras'),
    )
    user_id = _scalar(
        connection,
        'INSERT INTO users (username, password, full_name, role, company_id, active) '
        'VALUES (%s, %s, %s, %s, %s, 1) RETURNING id',
        ('rita.geral', hash_password('Teste@12345'), 'Rita Admin Geral',
         'general_admin', company_id),
    )
    legal_entity_id = None
    from modules.legal_entities.service import legal_entities_ready
    if legal_entities_ready(connection):
        legal_entity_id = _scalar(
            connection,
            'SELECT id FROM legal_entities WHERE company_id = %s LIMIT 1', (company_id,),
        )
    connection.commit()
    return {
        'company_id': company_id,
        'other_company_id': other_company_id,
        'units': units,
        'other_unit_id': other_unit_id,
        'user_id': user_id,
        'legal_entity_id': legal_entity_id,
        'actor': {
            'id': user_id, 'role': 'general_admin', 'company_id': company_id,
            'full_name': 'Rita Admin Geral',
        },
    }


def _run(tenant, *, strategy, raw=None, mapping=None, company_id=None):
    from modules.data_migration.service import run_migration
    return run_migration(
        _conn(),
        company_id=company_id or tenant['company_id'],
        entity='colaboradores',
        source_kind='csv',
        raw=raw if raw is not None else LEGACY_CSV.encode('latin-1'),
        mapping=mapping or MAPPING,
        strategy=strategy,
        actor=tenant['actor'],
        source_name='export_legado.csv',
    )


def _expect_blocked(match, fn, *args, **kwargs):
    """Executa algo que DEVE ser recusado e devolve a conexão ao estado limpo.

    Em produção o `closing(get_connection())` de cada rota descarta a
    transação; a jornada compartilha uma conexão só para provar o reuso, então
    reproduz a fronteira do request aqui.
    """
    with pytest.raises(ValueError, match=match):
        fn(*args, **kwargs)
    _conn().rollback()


# ── 1. Leitura e mapeamento do export legado ───────────────────────────────

def test_legacy_latin1_export_is_read_and_every_column_is_recognised(tenant):
    from modules.data_migration.service import analyze_source
    analysis = analyze_source('csv', LEGACY_CSV.encode('latin-1'), 'colaboradores')
    assert analysis['detected']['delimiter'] == ';'
    assert analysis['detected']['total_rows'] == 3
    assert set(analysis['mapping']) == set(MAPPING)
    assert analysis['mapping'] == MAPPING
    assert analysis['missing_required'] == []


# ── 2. Preview não grava nada ──────────────────────────────────────────────

def test_preview_reports_the_outcome_without_writing_anything(tenant):
    connection = _conn()
    before_employees = _scalar(connection, 'SELECT COUNT(*) FROM employees')
    before_jobs = _scalar(connection, 'SELECT COUNT(*) FROM migration_jobs')

    result = _run(tenant, strategy='dry_run')
    preview = result['preview']
    assert result['applied'] is False
    assert result['job_id'] is None
    assert preview['total_rows'] == 3
    assert preview['valid_rows'] == 3
    assert preview['will_insert'] == 3
    assert preview['blocking'] is False

    assert _scalar(connection, 'SELECT COUNT(*) FROM employees') == before_employees
    assert _scalar(connection, 'SELECT COUNT(*) FROM migration_jobs') == before_jobs


# ── 3. Referência desconhecida vira erro de preview ────────────────────────

def test_unknown_unit_name_is_reported_as_a_preview_error_and_blocks(tenant):
    csv = (
        'Employee Name;Registration;CPF;Department;Job Title;Hire Date\n'
        f'Fulano de Tal;9001;{VALID_CPF_A};Unidade Que Não Existe;Soldador;2023-01-02\n'
    ).encode('latin-1')
    mapping = {'Employee Name': 'name', 'Registration': 'employee_id_code',
               'CPF': 'cpf', 'Department': 'unit_id', 'Job Title': 'role_name',
               'Hire Date': 'admission_date'}
    result = _run(tenant, strategy='dry_run', raw=csv, mapping=mapping)
    errors = [d for d in result['preview']['diagnostics'] if d['code'] == 'unresolved_unknown']
    assert errors, result['preview']['diagnostics']
    assert errors[0]['source_value'] == 'Unidade Que Não Existe'
    assert result['preview']['blocking'] is True

    _expect_blocked('bloqueada', _run, tenant, strategy='insert_only',
                    raw=csv, mapping=mapping)
    assert _scalar(_conn(), 'SELECT COUNT(*) FROM employees WHERE name = %s',
                   ('Fulano de Tal',)) == 0


# ── 4. Importação real ─────────────────────────────────────────────────────

def test_valid_employees_are_imported_with_units_resolved_by_name(tenant):
    result = _run(tenant, strategy='insert_only')
    assert result['totals']['inserted'] == 3
    assert result['totals']['failed'] == 0

    connection = _conn()
    from epi_backend.db import row_to_dict
    rows = [row_to_dict(r) for r in connection.execute(
        'SELECT name, cpf, unit_id FROM employees WHERE company_id = %s ORDER BY name',
        (tenant['company_id'],),
    ).fetchall()]
    assert [r['name'] for r in rows] == ['Ana Lima', 'João Souza', 'Maria Silva']
    # CPF gravado como o cadastro manual grava: só dígitos.
    assert all(r['cpf'].isdigit() for r in rows), rows
    assert rows[2]['cpf'] == STORED_CPF_A
    # Nome da planilha virou o id correto da unidade DESTE tenant.
    assert rows[2]['unit_id'] == tenant['units']['Produção']
    assert rows[0]['unit_id'] == tenant['units']['Manutenção']

    pytest.imported_job_id = result['job_id']


# ── 5. Isolamento multi-tenant ─────────────────────────────────────────────

def test_the_other_tenant_sees_nothing_from_this_import(tenant):
    connection = _conn()
    assert _scalar(
        connection, 'SELECT COUNT(*) FROM employees WHERE company_id = %s',
        (tenant['other_company_id'],),
    ) == 0
    from modules.data_migration.service import fetch_jobs
    other_actor = {**tenant['actor'], 'company_id': tenant['other_company_id']}
    assert fetch_jobs(connection, tenant['other_company_id']) == []
    # E não consegue reverter o job alheio.
    from modules.data_migration.service import revert_job
    _expect_blocked('não encontrada', revert_job, connection, pytest.imported_job_id,
                    tenant['other_company_id'], other_actor)


def test_the_same_unit_name_in_another_tenant_never_resolves_across_the_border(tenant):
    """"Produção" existe nos dois tenants; cada importação tem de acertar a sua."""
    csv = (
        'Employee Name;Registration;CPF;Department;Job Title;Hire Date\n'
        f'Colaborador Vizinho;9100;{VALID_CPF_A};Produção;Pintor;2021-06-10\n'
    ).encode('latin-1')
    mapping = {'Employee Name': 'name', 'Registration': 'employee_id_code',
               'CPF': 'cpf', 'Department': 'unit_id', 'Job Title': 'role_name',
               'Hire Date': 'admission_date'}
    _run(tenant, strategy='insert_only', raw=csv, mapping=mapping,
         company_id=tenant['other_company_id'])
    assert _scalar(
        _conn(), 'SELECT unit_id FROM employees WHERE company_id = %s AND name = %s',
        (tenant['other_company_id'], 'Colaborador Vizinho'),
    ) == tenant['other_unit_id']


# ── 6. Upsert ──────────────────────────────────────────────────────────────

def test_upsert_updates_the_existing_person_instead_of_duplicating(tenant):
    connection = _conn()
    before = _scalar(connection, 'SELECT COUNT(*) FROM employees WHERE company_id = %s',
                     (tenant['company_id'],))
    changed = LEGACY_CSV.replace('Soldadora', 'Soldadora Sênior').encode('latin-1')
    result = _run(tenant, strategy='upsert', raw=changed)
    assert result['totals']['updated'] == 3
    assert result['totals']['inserted'] == 0
    assert _scalar(connection, 'SELECT COUNT(*) FROM employees WHERE company_id = %s',
                   (tenant['company_id'],)) == before
    assert _scalar(connection, 'SELECT role_name FROM employees WHERE cpf = %s AND company_id = %s',
                   (STORED_CPF_A, tenant['company_id'])) == 'Soldadora Sênior'
    pytest.upsert_job_id = result['job_id']


# ── 7. Linha inválida isolada, válidas commitadas, conexão sadia ──────────

def test_one_invalid_row_fails_alone_while_the_valid_ones_commit(tenant):
    """Falha de BANCO no meio do lote (não de validação).

    É o cenário que derrubava tudo no PostgreSQL: sem SAVEPOINT por linha, o
    primeiro erro abortava a transação e nem o diagnóstico nem o fechamento
    do job conseguiam ser gravados.
    """
    connection = _conn()
    connection.execute(
        'CREATE OR REPLACE FUNCTION reject_one_employee() RETURNS trigger AS $$ '
        f"BEGIN IF NEW.cpf = '{REJECTED_CPF}' THEN "
        "RAISE EXCEPTION 'falha proposital de banco'; END IF; RETURN NEW; END; "
        '$$ LANGUAGE plpgsql;'
    )
    connection.execute('DROP TRIGGER IF EXISTS reject_one_employee_trg ON employees')
    connection.execute(
        'CREATE TRIGGER reject_one_employee_trg BEFORE INSERT ON employees '
        'FOR EACH ROW EXECUTE FUNCTION reject_one_employee()'
    )
    connection.commit()
    try:
        # Três pessoas NOVAS (CPFs que não aparecem em nenhuma outra etapa),
        # para o resultado não depender da posição na jornada. A do meio é a
        # que o trigger rejeita.
        csv = (
            'Employee Name;Registration;CPF;Department;Job Title;Hire Date\n'
            f'Novo Um;9301;{FRESH_CPF_A};Produção;Soldadora;2023-04-01\n'
            f'Novo Dois;9302;{REJECTED_CPF};Produção;Eletricista;2022-11-15\n'
            f'Novo Três;9303;{FRESH_CPF_C};Produção;Mecânica;2024-02-20\n'
        ).encode('latin-1')
        mapping = {'Employee Name': 'name', 'Registration': 'employee_id_code',
                   'CPF': 'cpf', 'Department': 'unit_id', 'Job Title': 'role_name',
                   'Hire Date': 'admission_date'}
        result = _run(tenant, strategy='upsert', raw=csv, mapping=mapping)

        assert result['totals']['failed'] == 1
        assert result['totals']['inserted'] == 2
        # O job chegou ao status final apesar do erro de banco.
        from modules.data_migration.service import fetch_job_records, get_job
        assert get_job(connection, result['job_id'], tenant['company_id'])['status'] == 'completed'
        # O diagnóstico da linha ruim foi gravado.
        errors = [r for r in fetch_job_records(connection, result['job_id'], tenant['company_id'])
                  if r['action'] == 'error']
        assert len(errors) == 1
        assert 'falha proposital' in (errors[0]['error_message'] or '')
        # As linhas boas foram commitadas.
        assert _scalar(connection, 'SELECT name FROM employees WHERE cpf = %s AND company_id = %s',
                       (FRESH_CPF_A, tenant['company_id'])) == 'Novo Um'
        assert _scalar(connection, 'SELECT name FROM employees WHERE cpf = %s AND company_id = %s',
                       (FRESH_CPF_C, tenant['company_id'])) == 'Novo Três'
        # E a rejeitada realmente não entrou.
        assert _scalar(connection, 'SELECT COUNT(*) FROM employees WHERE cpf = %s',
                       (REJECTED_CPF,)) == 0
    finally:
        connection.execute('DROP TRIGGER IF EXISTS reject_one_employee_trg ON employees')
        connection.commit()


def test_the_next_unrelated_request_still_works_after_the_row_failure(tenant):
    """A conexão não voltou envenenada para o pool.

    Antes do SAVEPOINT por linha, esta consulta — sem nenhuma relação com a
    importação — falhava com "current transaction is aborted".
    """
    connection = _conn()
    assert _scalar(connection, 'SELECT COUNT(*) FROM companies') >= 2
    assert _scalar(connection, 'SELECT COUNT(*) FROM units WHERE company_id = %s',
                   (tenant['company_id'],)) == 2
    from modules.data_migration.service import fetch_jobs
    assert fetch_jobs(connection, tenant['company_id'])


# ── 8. Rollback ────────────────────────────────────────────────────────────

def test_reverting_the_import_removes_only_what_it_created(tenant):
    connection = _conn()
    from modules.data_migration.service import revert_job
    # Marca de referência: um colaborador que NÃO veio desta importação.
    outsider_id = _scalar(
        connection,
        'INSERT INTO employees (company_id, unit_id, name, cpf, employee_id_code, '
        'role_name, admission_date, sector, schedule_type) '
        "VALUES (%s, %s, %s, %s, %s, %s, %s, '', '') RETURNING id",
        (tenant['company_id'], tenant['units']['Produção'], 'Preexistente',
         '52998224725', 'PRE-0001', 'Almoxarife', '2020-01-01'),
    )
    connection.commit()

    result = revert_job(connection, pytest.imported_job_id,
                        tenant['company_id'], tenant['actor'])
    # A rota (handle_post_migration_revert) é quem faz o commit depois de
    # registrar a auditoria; aqui reproduzimos essa fronteira.
    connection.commit()
    assert result['deleted'] + result['restored'] > 0

    # O registro alheio à importação continua lá.
    assert _scalar(connection, 'SELECT name FROM employees WHERE id = %s',
                   (outsider_id,)) == 'Preexistente'
    # E o tenant vizinho segue intacto.
    assert _scalar(connection, 'SELECT COUNT(*) FROM employees WHERE company_id = %s',
                   (tenant['other_company_id'],)) == 1


def test_a_second_revert_is_refused(tenant):
    from modules.data_migration.service import revert_job
    connection = _conn()
    before = _scalar(connection, 'SELECT COUNT(*) FROM employees WHERE company_id = %s',
                     (tenant['company_id'],))
    _expect_blocked('já foi revertida', revert_job, connection,
                    pytest.imported_job_id, tenant['company_id'], tenant['actor'])
    assert _scalar(connection, 'SELECT COUNT(*) FROM employees WHERE company_id = %s',
                   (tenant['company_id'],)) == before


# ── 9. Auditoria sobrevive à jornada ──────────────────────────────────────

def test_the_audit_trail_records_actor_source_and_every_touched_row(tenant):
    from epi_backend.db import row_to_dict
    from modules.data_migration.service import get_job
    connection = _conn()
    job = get_job(connection, pytest.upsert_job_id, tenant['company_id'])
    assert job['actor_name'] == 'Rita Admin Geral'
    assert job['source_name'] == 'export_legado.csv'
    assert job['source_hash']
    records = [row_to_dict(r) for r in connection.execute(
        'SELECT action, before_json, after_json FROM migration_job_records '
        'WHERE job_id = %s AND company_id = %s',
        (pytest.upsert_job_id, tenant['company_id']),
    ).fetchall()]
    assert records
    for record in records:
        if record['action'] == 'update':
            assert record['before_json'] and record['after_json']
