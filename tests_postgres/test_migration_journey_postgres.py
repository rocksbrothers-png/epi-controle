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
import uuid

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


# ── Isolamento entre execuções (issue #186) ────────────────────────────────
# A jornada é module-scoped e compartilha um tenant de propósito. O problema é
# que três colunas que ela grava têm UNIQUE **global**, sem company_id:
#
#     companies_name_key      (name)
#     companies_cnpj_key      (cnpj)
#     users_username_key      (username)
#
# Com valores fixos, rodar a suíte duas vezes contra o mesmo banco quebra logo
# no setup do fixture ``tenant`` — e, como ele é module-scoped, *todas* as
# etapas viram erro de fixture de uma vez.
#
# A correção é unicidade por execução, e não limpeza no teardown, porque o
# grafo de chaves estrangeiras não permite um teardown simples:
#
#     units, employees, epis, deliveries  ->  companies   ON DELETE RESTRICT
#     users                               ->  companies   ON DELETE SET NULL
#
# Um ``DELETE FROM companies`` falha enquanto existir uma unidade, e apagar a
# empresa **não** libera o ``username``: o usuário sobrevive com company_id
# NULL e continua ocupando o índice único global. Um teardown correto exigiria
# ordem topológica e passaria a crescer a cada entidade nova habilitada (#172),
# quebrando de novo assim que alguém esquecesse uma tabela. Unicidade é O(1) e
# não depende do schema.
#
# Todo o resto que a jornada grava já é escopado por company_id
# (``units_company_id_name_key``, ``uq_employees_company_employee_code``,
# ``epis_company_id_*``, ``uq_outsourced_companies_company_cnpj``), então um
# company_id novo isola o resto automaticamente.
_RUN_TAG = uuid.uuid4().hex[:8]


def _valid_cnpj_from(base12: str) -> str:
    """CNPJ com dígitos verificadores corretos.

    O CNPJ do tenant precisa ser único por execução, mas continuar válido: a
    migration de Multi-CNPJ deriva ``legal_entities`` a partir dele. Gerar 14
    dígitos aleatórios passaria no INSERT direto e escondería um problema real
    mais adiante.
    """
    digits = base12
    for weights in ([5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2],
                    [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]):
        total = sum(int(digits[i]) * weights[i] for i in range(len(weights)))
        rest = total % 11
        digits += str(0 if rest < 2 else 11 - rest)
    return digits


def _run_cnpj(prefix: str) -> str:
    """CNPJ válido e único por execução, derivado de ``_RUN_TAG``.

    ``prefix`` distingue as empresas dentro da mesma execução (o tenant da
    jornada e o tenant vizinho usado nas provas de isolamento).
    """
    return _valid_cnpj_from(f'{prefix}{int(_RUN_TAG, 16) % 10 ** 11:011d}')


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
    # Nome e CNPJ carregam _RUN_TAG porque são UNIQUE globais — ver o bloco de
    # isolamento no topo do arquivo. O resto dos dados segue fixo de propósito:
    # é o que torna a jornada legível como cenário.
    company_id = _scalar(
        connection,
        "INSERT INTO companies (name, cnpj, logo_type) VALUES (%s, %s, '') RETURNING id",
        (f'Metalúrgica Aurora {_RUN_TAG}', _run_cnpj('1')),
    )
    other_company_id = _scalar(
        connection,
        "INSERT INTO companies (name, cnpj, logo_type) VALUES (%s, %s, '') RETURNING id",
        (f'Concorrente S.A. {_RUN_TAG}', _run_cnpj('9')),
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
        # username é UNIQUE global; full_name não é, e segue fixo porque a
        # etapa de auditoria afirma sobre ele.
        (f'rita.geral.{_RUN_TAG}', hash_password('Teste@12345'), 'Rita Admin Geral',
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


def _run(tenant, *, strategy, raw=None, mapping=None, company_id=None, entity='colaboradores'):
    from modules.data_migration.service import run_migration
    return run_migration(
        _conn(),
        company_id=company_id or tenant['company_id'],
        entity=entity,
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
    # Contagem escopada no tenant, não na tabela inteira: o que precisa ser
    # provado é que o preview não gravou nada *desta* importação, e o número
    # não pode depender do que exista no banco por outros motivos (#186).
    scope = (tenant['company_id'],)
    before_employees = _scalar(
        connection, 'SELECT COUNT(*) FROM employees WHERE company_id = %s', scope)
    before_jobs = _scalar(
        connection, 'SELECT COUNT(*) FROM migration_jobs WHERE company_id = %s', scope)

    result = _run(tenant, strategy='dry_run')
    preview = result['preview']
    assert result['applied'] is False
    assert result['job_id'] is None
    assert preview['total_rows'] == 3
    assert preview['valid_rows'] == 3
    assert preview['will_insert'] == 3
    assert preview['blocking'] is False

    assert _scalar(
        connection, 'SELECT COUNT(*) FROM employees WHERE company_id = %s', scope
    ) == before_employees
    assert _scalar(
        connection, 'SELECT COUNT(*) FROM migration_jobs WHERE company_id = %s', scope
    ) == before_jobs


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


# ═══════════════════════════════════════════════════════════════════════════
# unidades, epis e fornecedores (issue #170)
#
# A suíte acima só provava o motor genérico contra `colaboradores`. Nada
# garantia que `unidades`, `epis` e `fornecedores` — habilitadas no mesmo
# catálogo (issue #169) — sobrevivem ao PostgreSQL real: é exatamente a
# situação que a Fase 1 já viveu, com a suíte inteira verde e zero
# colaborador importável (ADR-0003 §10). Cada bloco abaixo usa uma fixture de
# export legado PRÓPRIA (separador, acentuação e cabeçalho fora do padrão de
# destino) e prova, contra o banco real, os mesmos pontos que pegaram os 3
# defeitos originais — onde eles se aplicam a esta entidade:
#
#   - preview coerente com o schema real: o teste de importação real (não só
#     o dry_run) confirma que toda coluna NOT NULL foi satisfeita e que o
#     normalizador de domínio gravou o valor CANÔNICO, não o literal da
#     planilha (é onde "preview mentindo" se materializava);
#   - linha inválida isolada sem envenenar a conexão: mesmo gatilho de banco
#     proposital usado para `colaboradores`, agora contra a tabela própria de
#     cada entidade;
#   - upsert por chave natural própria da entidade.
#
# "Referência desconhecida bloqueando" (o 3º defeito original) fica de fora
# de propósito: nenhum campo de `unidades`, `epis` ou `fornecedores` no
# catálogo hoje declara `resolves_to` — só `colaboradores.unit_id` resolve
# nome→id. Forjar uma referência que o catálogo não tem seria testar
# comportamento inventado, não o produto real.


# ── Unidades ─────────────────────────────────────────────────────────────

# Export legado de unidades: separador ',' (diferente do ';' de
# colaboradores, para não validar o motor só contra um delimitador) e
# cabeçalho com acentuação — força a mesma detecção latin-1.
LEGACY_CSV_UNIDADES = (
    'Nome da Unidade,Tipo de Unidade,Municipio,Observacoes\n'
    'Plataforma Netuno,Plataforma,Macaé,Antiga FPSO\n'
    'Base Vitória,Base,Vitória,\n'
    'Navio Search VII,Navio,Rio das Ostras,Em operação\n'
)

MAPPING_UNIDADES = {
    'Nome da Unidade': 'name',
    'Tipo de Unidade': 'unit_type',
    'Municipio': 'city',
    'Observacoes': 'notes',
}


def test_unidades_legacy_export_is_read_and_every_column_is_recognised(tenant):
    from modules.data_migration.service import analyze_source
    analysis = analyze_source('csv', LEGACY_CSV_UNIDADES.encode('latin-1'), 'unidades')
    assert analysis['detected']['delimiter'] == ','
    assert analysis['detected']['total_rows'] == 3
    assert analysis['mapping'] == MAPPING_UNIDADES
    assert analysis['missing_required'] == []


def test_unidades_import_applies_the_same_unit_type_aliases_as_manual_registration(tenant):
    """Prova que o normalizador (`normalize_unit_type`) roda dentro do motor de
    importação de verdade — 'Navio' precisa virar 'embarcacao' gravado, não
    o literal da planilha, exatamente como o cadastro manual grava."""
    result = _run(tenant, entity='unidades', strategy='insert_only',
                  raw=LEGACY_CSV_UNIDADES.encode('latin-1'), mapping=MAPPING_UNIDADES)
    assert result['totals']['inserted'] == 3
    assert result['totals']['failed'] == 0

    connection = _conn()
    from epi_backend.db import row_to_dict
    rows = {row_to_dict(r)['name']: row_to_dict(r) for r in connection.execute(
        'SELECT name, unit_type, city, notes FROM units WHERE company_id = %s '
        "AND name IN ('Plataforma Netuno', 'Base Vitória', 'Navio Search VII')",
        (tenant['company_id'],),
    ).fetchall()}
    assert set(rows) == {'Plataforma Netuno', 'Base Vitória', 'Navio Search VII'}
    assert rows['Plataforma Netuno']['unit_type'] == 'plataforma'
    assert rows['Base Vitória']['unit_type'] == 'base'
    # 'Navio' é alias de 'embarcacao' — o mesmo que create_unit/update_unit
    # aplicam via normalize_unit_type antes de gravar.
    assert rows['Navio Search VII']['unit_type'] == 'embarcacao'
    assert rows['Plataforma Netuno']['city'] == 'Macaé'
    assert (rows['Base Vitória']['notes'] or '') == ''


def test_unidades_one_invalid_row_fails_alone_while_the_valid_ones_commit(tenant):
    """Mesmo gatilho de falha de banco da jornada de colaboradores, agora
    contra `units` — prova que o SAVEPOINT por linha não foi validado só
    para a tabela `employees`."""
    connection = _conn()
    connection.execute(
        'CREATE OR REPLACE FUNCTION reject_one_unit() RETURNS trigger AS $$ '
        "BEGIN IF NEW.name = 'Unidade Rejeitada Propositalmente' THEN "
        "RAISE EXCEPTION 'falha proposital de banco'; END IF; RETURN NEW; END; "
        '$$ LANGUAGE plpgsql;'
    )
    connection.execute('DROP TRIGGER IF EXISTS reject_one_unit_trg ON units')
    connection.execute(
        'CREATE TRIGGER reject_one_unit_trg BEFORE INSERT ON units '
        'FOR EACH ROW EXECUTE FUNCTION reject_one_unit()'
    )
    connection.commit()
    try:
        csv = (
            'Nome da Unidade,Tipo de Unidade,Municipio,Observacoes\n'
            'Terminal Guanabara,Base,Rio de Janeiro,\n'
            'Unidade Rejeitada Propositalmente,Base,Niterói,\n'
            'Sonda Aurora Nova,Plataforma,Macaé,\n'
        ).encode('latin-1')
        result = _run(tenant, entity='unidades', strategy='insert_only',
                      raw=csv, mapping=MAPPING_UNIDADES)

        assert result['totals']['failed'] == 1
        assert result['totals']['inserted'] == 2
        from modules.data_migration.service import fetch_job_records, get_job
        assert get_job(connection, result['job_id'], tenant['company_id'])['status'] == 'completed'
        errors = [r for r in fetch_job_records(connection, result['job_id'], tenant['company_id'])
                  if r['action'] == 'error']
        assert len(errors) == 1
        assert 'falha proposital' in (errors[0]['error_message'] or '')
        assert _scalar(connection, 'SELECT COUNT(*) FROM units WHERE company_id = %s AND name = %s',
                       (tenant['company_id'], 'Terminal Guanabara')) == 1
        assert _scalar(connection, 'SELECT COUNT(*) FROM units WHERE company_id = %s AND name = %s',
                       (tenant['company_id'], 'Sonda Aurora Nova')) == 1
        assert _scalar(connection, "SELECT COUNT(*) FROM units WHERE name = 'Unidade Rejeitada Propositalmente'") == 0
    finally:
        connection.execute('DROP TRIGGER IF EXISTS reject_one_unit_trg ON units')
        connection.commit()

    # A conexão não voltou envenenada: uma consulta sem relação com a
    # importação, logo depois da falha, continua funcionando.
    assert _scalar(connection, 'SELECT COUNT(*) FROM companies') >= 2


def test_unidades_upsert_matches_by_name_and_updates_instead_of_duplicating(tenant):
    connection = _conn()
    before = _scalar(connection, 'SELECT COUNT(*) FROM units WHERE company_id = %s',
                     (tenant['company_id'],))
    changed = LEGACY_CSV_UNIDADES.replace('Antiga FPSO', 'Antiga FPSO - desativada em 2025').encode('latin-1')
    result = _run(tenant, entity='unidades', strategy='upsert',
                  raw=changed, mapping=MAPPING_UNIDADES)
    assert result['totals']['updated'] == 3
    assert result['totals']['inserted'] == 0
    assert _scalar(connection, 'SELECT COUNT(*) FROM units WHERE company_id = %s',
                   (tenant['company_id'],)) == before
    assert _scalar(connection, "SELECT notes FROM units WHERE company_id = %s AND name = 'Plataforma Netuno'",
                   (tenant['company_id'],)) == 'Antiga FPSO - desativada em 2025'


# ── EPIs ─────────────────────────────────────────────────────────────────

# Export legado de EPIs: separador ';' com datas em dd/mm/aaaa — o formato
# brasileiro comum em planilha antiga, e exatamente o que
# `normalize_epi_domain_fields` precisa canonizar para ISO antes de gravar
# (issue #169). Nome com acentuação força latin-1, como no export real.
LEGACY_CSV_EPIS = (
    'Description;Part Number;CA;CA Expiry;Shelf Life;UOM;Sector;Brand\n'
    'Luva Nitrílica Tam. M;LU-1001;12345;15/03/2028;15/03/2030;PAR;Produção;3M\n'
    'Óculos de Proteção Ampla Visão;OC-2002;67.890;20/11/2027;20/11/2029;UN;Manutenção;Steelflex\n'
    'Capacete de Segurança Classe B;CP-3003;34521;01/06/2027;01/06/2032;UN;Produção;MSA\n'
)

MAPPING_EPIS = {
    'Description': 'name',
    'Part Number': 'purchase_code',
    'CA': 'ca',
    'CA Expiry': 'ca_expiry',
    'Shelf Life': 'epi_validity_date',
    'UOM': 'unit_measure',
    'Sector': 'sector',
    'Brand': 'manufacturer',
}


def test_epis_legacy_export_is_read_and_every_column_is_recognised(tenant):
    from modules.data_migration.service import analyze_source
    analysis = analyze_source('csv', LEGACY_CSV_EPIS.encode('latin-1'), 'epis')
    assert analysis['detected']['delimiter'] == ';'
    assert analysis['detected']['total_rows'] == 3
    assert analysis['mapping'] == MAPPING_EPIS
    assert analysis['missing_required'] == []


def test_epis_import_canonizes_dates_to_iso_and_applies_column_defaults(tenant):
    """O defeito original, específico de `epis` (issue #170): o preview aceita
    'dd/mm/aaaa' como data válida, mas sem canonizar a gravação salvava o
    texto LITERAL e `epis.validity.parse_iso_date` o ignorava em silêncio.
    Este teste prova, contra o schema real, que o valor gravado é ISO — e
    que `manufacture_date`/`validity_days` (NOT NULL sem default, não
    coletados da planilha) vieram de `column_defaults`, não de um NULL que
    o PostgreSQL teria recusado."""
    result = _run(tenant, entity='epis', strategy='insert_only',
                  raw=LEGACY_CSV_EPIS.encode('latin-1'), mapping=MAPPING_EPIS)
    assert result['totals']['inserted'] == 3
    assert result['totals']['failed'] == 0

    connection = _conn()
    from epi_backend.db import row_to_dict
    rows = {row_to_dict(r)['purchase_code']: row_to_dict(r) for r in connection.execute(
        'SELECT purchase_code, name, ca, ca_expiry, epi_validity_date, manufacture_date, '
        'validity_days, unit_measure, sector, manufacturer FROM epis WHERE company_id = %s '
        "AND purchase_code IN ('LU-1001', 'OC-2002', 'CP-3003')",
        (tenant['company_id'],),
    ).fetchall()}
    assert set(rows) == {'LU-1001', 'OC-2002', 'CP-3003'}

    luva = rows['LU-1001']
    assert luva['name'] == 'Luva Nitrílica Tam. M'
    assert luva['ca'] == '12345'
    # Canonizado para ISO — não o "15/03/2028" que veio da planilha.
    assert luva['ca_expiry'] == '2028-03-15'
    assert luva['epi_validity_date'] == '2030-03-15'
    assert luva['unit_measure'] == 'PAR'
    assert luva['sector'] == 'Produção'
    assert luva['manufacturer'] == '3M'
    # column_defaults do catálogo — o mesmo comportamento de create_epi.
    assert luva['manufacture_date'] == ''
    assert luva['validity_days'] == 0

    # CA com pontuação de planilha ('67.890') vira só dígitos, como o
    # normalizador de employees já faz para CPF.
    assert rows['OC-2002']['ca'] == '67890'
    assert rows['OC-2002']['ca_expiry'] == '2027-11-20'


def test_epis_one_invalid_row_fails_alone_while_the_valid_ones_commit(tenant):
    connection = _conn()
    connection.execute(
        'CREATE OR REPLACE FUNCTION reject_one_epi() RETURNS trigger AS $$ '
        "BEGIN IF NEW.purchase_code = 'REJ-9999' THEN "
        "RAISE EXCEPTION 'falha proposital de banco'; END IF; RETURN NEW; END; "
        '$$ LANGUAGE plpgsql;'
    )
    connection.execute('DROP TRIGGER IF EXISTS reject_one_epi_trg ON epis')
    connection.execute(
        'CREATE TRIGGER reject_one_epi_trg BEFORE INSERT ON epis '
        'FOR EACH ROW EXECUTE FUNCTION reject_one_epi()'
    )
    connection.commit()
    try:
        csv = (
            'Description;Part Number;CA;CA Expiry;Shelf Life;UOM;Sector;Brand\n'
            'Bota de Segurança;BT-4001;11111;10/01/2028;10/01/2031;PAR;Produção;Marluvas\n'
            'Item Rejeitado;REJ-9999;22222;10/01/2028;10/01/2031;UN;Produção;X\n'
            'Protetor Auricular;PA-5001;33333;10/01/2028;10/01/2031;PAR;Manutenção;3M\n'
        ).encode('latin-1')
        result = _run(tenant, entity='epis', strategy='insert_only',
                      raw=csv, mapping=MAPPING_EPIS)

        assert result['totals']['failed'] == 1
        assert result['totals']['inserted'] == 2
        from modules.data_migration.service import fetch_job_records, get_job
        assert get_job(connection, result['job_id'], tenant['company_id'])['status'] == 'completed'
        errors = [r for r in fetch_job_records(connection, result['job_id'], tenant['company_id'])
                  if r['action'] == 'error']
        assert len(errors) == 1
        assert 'falha proposital' in (errors[0]['error_message'] or '')
        assert _scalar(connection, 'SELECT COUNT(*) FROM epis WHERE company_id = %s AND purchase_code = %s',
                       (tenant['company_id'], 'BT-4001')) == 1
        assert _scalar(connection, 'SELECT COUNT(*) FROM epis WHERE company_id = %s AND purchase_code = %s',
                       (tenant['company_id'], 'PA-5001')) == 1
        assert _scalar(connection, "SELECT COUNT(*) FROM epis WHERE purchase_code = 'REJ-9999'") == 0
    finally:
        connection.execute('DROP TRIGGER IF EXISTS reject_one_epi_trg ON epis')
        connection.commit()

    assert _scalar(connection, 'SELECT COUNT(*) FROM companies') >= 2


def test_epis_upsert_matches_by_purchase_code_and_updates_instead_of_duplicating(tenant):
    connection = _conn()
    before = _scalar(connection, 'SELECT COUNT(*) FROM epis WHERE company_id = %s',
                     (tenant['company_id'],))
    changed = LEGACY_CSV_EPIS.replace('3M', '3M do Brasil')
    result = _run(tenant, entity='epis', strategy='upsert',
                  raw=changed.encode('latin-1'), mapping=MAPPING_EPIS)
    assert result['totals']['updated'] == 3
    assert result['totals']['inserted'] == 0
    assert _scalar(connection, 'SELECT COUNT(*) FROM epis WHERE company_id = %s',
                   (tenant['company_id'],)) == before
    assert _scalar(connection, "SELECT manufacturer FROM epis WHERE company_id = %s AND purchase_code = 'LU-1001'",
                   (tenant['company_id'],)) == '3M do Brasil'


# ── Fornecedores ─────────────────────────────────────────────────────────

# Export legado de fornecedores: separador TAB (nenhuma outra fixture desta
# jornada usa tab) e SEM CNPJ na terceira linha — o caso em que a chave
# natural cai para `legal_name`, já que `cnpj` é opcional no catálogo.
LEGACY_TSV_FORNECEDORES = (
    'Razão Social\tNome Fantasia\tCNPJ\tTipo de Empresa\n'
    'Alfa Manutenção Industrial LTDA\tAlfa Manutenção\t12.345.678/0001-95\tTerceirizada\n'
    'Beta Segurança do Trabalho EIRELI\tBeta EPI\t55.667.788/0001-86\tPrestador de Serviço\n'
    'Gama Consultoria Técnica\t\t\t\n'
)

MAPPING_FORNECEDORES = {
    'Razão Social': 'legal_name',
    'Nome Fantasia': 'trade_name',
    'CNPJ': 'cnpj',
    'Tipo de Empresa': 'company_kind',
}


def test_fornecedores_legacy_export_is_read_and_every_column_is_recognised(tenant):
    from modules.data_migration.service import analyze_source
    analysis = analyze_source('csv', LEGACY_TSV_FORNECEDORES.encode('latin-1'), 'fornecedores')
    assert analysis['detected']['delimiter'] == '\t'
    assert analysis['detected']['total_rows'] == 3
    assert analysis['mapping'] == MAPPING_FORNECEDORES
    assert analysis['missing_required'] == []


def test_fornecedores_import_derives_cnpj_normalized_and_controlled_vocabulary(tenant):
    """O defeito original de `fornecedores` (issue #169, provado até agora só
    pela chamada isolada a `apply_domain_rules` em
    test_migration_contract_postgres.py): a importação gravava o CNPJ como
    veio da planilha e deixava `cnpj_normalized` vazia, tirando a linha do
    índice único PARCIAL de deduplicação. Este teste prova o mesmo através
    do motor de importação de ponta a ponta (`run_migration`), não de uma
    chamada direta à função de normalização."""
    result = _run(tenant, entity='fornecedores', strategy='insert_only',
                  raw=LEGACY_TSV_FORNECEDORES.encode('latin-1'), mapping=MAPPING_FORNECEDORES)
    assert result['totals']['inserted'] == 3
    assert result['totals']['failed'] == 0

    connection = _conn()
    from epi_backend.db import row_to_dict
    rows = {row_to_dict(r)['legal_name']: row_to_dict(r) for r in connection.execute(
        'SELECT legal_name, trade_name, cnpj, cnpj_normalized, company_kind, '
        'epi_responsibility, registration_mode, registration_status, status '
        'FROM outsourced_companies WHERE company_id = %s',
        (tenant['company_id'],),
    ).fetchall()}
    alfa = rows['Alfa Manutenção Industrial LTDA']
    assert alfa['cnpj'] == '12.345.678/0001-95'
    assert alfa['cnpj_normalized'] == '12345678000195'
    # Vocabulário controlado: 'Terceirizada' não está na lista de valores
    # aceitos, então normaliza para o default do domínio — igual ao cadastro
    # manual (normalize_company_kind).
    assert alfa['company_kind'] == 'outsourced'

    gama = rows['Gama Consultoria Técnica']
    assert (gama['cnpj'] or '') == ''
    assert (gama['cnpj_normalized'] or '') == ''

    # Colunas que a importação não coleta (não existem no catálogo de
    # `fornecedores`) e por isso o motor não grava: caem no DEFAULT do
    # servidor, que test_server_defaults_match_what_the_normalizer_would_
    # produce_when_empty (contrato) já prova ser igual ao que o
    # normalizador produziria. Aqui fechamos o loop pelo caminho real.
    for row in rows.values():
        assert row['epi_responsibility'] == 'Conforme Contrato'
        assert row['registration_mode'] == 'simplified'
        assert row['registration_status'] == 'pending_completion'
        assert row['status'] == 'active'


def test_fornecedores_one_invalid_row_fails_alone_while_the_valid_ones_commit(tenant):
    connection = _conn()
    connection.execute(
        'CREATE OR REPLACE FUNCTION reject_one_supplier() RETURNS trigger AS $$ '
        "BEGIN IF NEW.legal_name = 'Fornecedor Rejeitado Propositalmente' THEN "
        "RAISE EXCEPTION 'falha proposital de banco'; END IF; RETURN NEW; END; "
        '$$ LANGUAGE plpgsql;'
    )
    connection.execute('DROP TRIGGER IF EXISTS reject_one_supplier_trg ON outsourced_companies')
    connection.execute(
        'CREATE TRIGGER reject_one_supplier_trg BEFORE INSERT ON outsourced_companies '
        'FOR EACH ROW EXECUTE FUNCTION reject_one_supplier()'
    )
    connection.commit()
    try:
        csv = (
            'Razão Social\tNome Fantasia\tCNPJ\tTipo de Empresa\n'
            'Delta Andaimes LTDA\t\t\t\n'
            'Fornecedor Rejeitado Propositalmente\t\t\t\n'
            'Épsilon Elétrica ME\t\t\t\n'
        ).encode('latin-1')
        result = _run(tenant, entity='fornecedores', strategy='insert_only',
                      raw=csv, mapping=MAPPING_FORNECEDORES)

        assert result['totals']['failed'] == 1
        assert result['totals']['inserted'] == 2
        from modules.data_migration.service import fetch_job_records, get_job
        assert get_job(connection, result['job_id'], tenant['company_id'])['status'] == 'completed'
        errors = [r for r in fetch_job_records(connection, result['job_id'], tenant['company_id'])
                  if r['action'] == 'error']
        assert len(errors) == 1
        assert 'falha proposital' in (errors[0]['error_message'] or '')
        assert _scalar(connection,
                       'SELECT COUNT(*) FROM outsourced_companies WHERE company_id = %s AND legal_name = %s',
                       (tenant['company_id'], 'Delta Andaimes LTDA')) == 1
        assert _scalar(connection,
                       'SELECT COUNT(*) FROM outsourced_companies WHERE company_id = %s AND legal_name = %s',
                       (tenant['company_id'], 'Épsilon Elétrica ME')) == 1
        assert _scalar(
            connection,
            "SELECT COUNT(*) FROM outsourced_companies WHERE legal_name = 'Fornecedor Rejeitado Propositalmente'",
        ) == 0
    finally:
        connection.execute('DROP TRIGGER IF EXISTS reject_one_supplier_trg ON outsourced_companies')
        connection.commit()

    assert _scalar(connection, 'SELECT COUNT(*) FROM companies') >= 2


def test_fornecedores_upsert_matches_by_cnpj_or_by_legal_name_when_cnpj_is_absent(tenant):
    """As duas metades da chave natural composta (`cnpj`, `legal_name`) numa
    só reexecução: as duas primeiras linhas casam por CNPJ, a terceira —
    sem CNPJ nunca — só pode ter casado por `legal_name`."""
    connection = _conn()
    before = _scalar(connection, 'SELECT COUNT(*) FROM outsourced_companies WHERE company_id = %s',
                     (tenant['company_id'],))
    changed = (
        LEGACY_TSV_FORNECEDORES
        .replace('Alfa Manutenção\t', 'Alfa Manutenção Predial\t')
        .replace('Gama Consultoria Técnica\t\t\t',
                 'Gama Consultoria Técnica\tGama Consultoria\t\t')
    )
    result = _run(tenant, entity='fornecedores', strategy='upsert',
                  raw=changed.encode('latin-1'), mapping=MAPPING_FORNECEDORES)
    assert result['totals']['updated'] == 3
    assert result['totals']['inserted'] == 0
    assert _scalar(connection, 'SELECT COUNT(*) FROM outsourced_companies WHERE company_id = %s',
                   (tenant['company_id'],)) == before
    assert _scalar(
        connection,
        "SELECT trade_name FROM outsourced_companies WHERE company_id = %s AND cnpj_normalized = '12345678000195'",
        (tenant['company_id'],),
    ) == 'Alfa Manutenção Predial'
    assert _scalar(
        connection,
        "SELECT trade_name FROM outsourced_companies WHERE company_id = %s "
        "AND legal_name = 'Gama Consultoria Técnica'",
        (tenant['company_id'],),
    ) == 'Gama Consultoria'


# ── 8. A jornada roda duas vezes no mesmo banco (issue #186) ───────────────
#
# Esta seção não testa o produto: testa a própria suíte. A jornada é
# module-scoped e semeia um tenant; se esse setup não for reexecutável, rodar
# `pytest tests_postgres/` duas vezes contra o mesmo banco derruba TODAS as
# etapas de uma vez, como erro de fixture. Foi o que a #186 registrou.

def _global_unique_columns(connection, table):
    """Colunas cobertas por UNIQUE que **não** inclui company_id.

    Descoberto do catálogo do PostgreSQL, não de uma lista escrita à mão: um
    UNIQUE global novo passa a ser vigiado sozinho.
    """
    from epi_backend.db import row_to_dict
    rows = connection.execute(
        """
        SELECT pg_get_indexdef(i.oid) AS indexdef
          FROM pg_index x
          JOIN pg_class c ON c.oid = x.indrelid
          JOIN pg_class i ON i.oid = x.indexrelid
         WHERE x.indisunique AND c.relname = %s
        """,
        (table,),
    ).fetchall()
    found = set()
    for row in rows:
        definition = row_to_dict(row)['indexdef']
        # Índice parcial tem ` WHERE ...` depois da lista de colunas; sem cortar
        # aqui, a condição entra no nome da coluna. `companies` tem dois desses
        # (`subdomain`, `custom_domain`), e eles só apareceram quando o CI passou
        # a aplicar as migrations de verdade (#205).
        head = definition.split(' WHERE ', 1)[0]
        cols = head[head.index('(') + 1:head.rindex(')')]
        cols = [c.strip() for c in cols.split(',')]
        if 'company_id' in cols or cols == ['id']:
            continue
        found.update(cols)
    return found


def test_the_tenant_seed_only_writes_run_scoped_values_into_global_unique_columns(tenant):
    """Todo UNIQUE global que o tenant grava carrega o tag da execução.

    É o invariante que torna a suíte reexecutável. Se alguém voltar a fixar um
    nome, um CNPJ ou um username, este teste falha — em vez de a suíte inteira
    virar erro de fixture só na segunda rodada, que é como o problema aparecia.
    """
    connection = _conn()

    # As que a jornada sabidamente grava — travadas por nome, para que remover
    # o tag de qualquer uma delas falhe aqui.
    assert {'name', 'cnpj'} <= _global_unique_columns(connection, 'companies')
    assert {'username'} <= _global_unique_columns(connection, 'users')

    # E a regra geral: QUALQUER coluna de UNIQUE global que o tenant preencha
    # precisa ter valor DERIVADO desta execução. Uma coluna nova que passe a
    # ser gravada entra nesta checagem sozinha, sem precisar ser listada acima.
    #
    # Não basta procurar o tag dentro do valor: o CNPJ deriva de `_RUN_TAG` mas
    # é numérico e não o contém como texto. O que se verifica é pertencer ao
    # conjunto que ESTA execução produz.
    derived_this_run = {
        f'Metalúrgica Aurora {_RUN_TAG}',
        f'Concorrente S.A. {_RUN_TAG}',
        f'rita.geral.{_RUN_TAG}',
        _run_cnpj('1'),
        _run_cnpj('9'),
    }
    for table, row_id in (('companies', tenant['company_id']),
                          ('companies', tenant['other_company_id']),
                          ('users', tenant['user_id'])):
        for column in sorted(_global_unique_columns(connection, table)):
            value = _scalar(
                connection, f'SELECT {column} FROM {table} WHERE id = %s', (row_id,))  # noqa: S608
            if value is None or str(value).strip() == '':
                continue  # não preenchido pelo fixture: não pode colidir
            assert str(value) in derived_this_run, (
                f'{table}.{column} tem UNIQUE global e foi gravado como {value!r}, '
                f'que não deriva do tag desta execução — a suíte deixa de ser '
                f'reexecutável no mesmo banco.'
            )

    # O CNPJ é único por execução E continua válido: a migration de Multi-CNPJ
    # deriva legal_entities dele, então 14 dígitos aleatórios não serviriam.
    cnpj = _scalar(connection, 'SELECT cnpj FROM companies WHERE id = %s', (tenant['company_id'],))
    assert cnpj == _valid_cnpj_from(cnpj[:12])
    assert cnpj != _scalar(
        connection, 'SELECT cnpj FROM companies WHERE id = %s', (tenant['other_company_id'],))


def test_seeding_the_same_tenant_shape_again_does_not_collide(tenant):
    """Prova comportamental: uma segunda execução consegue semear de novo.

    Repete os INSERTs do fixture com um tag diferente — que é exatamente o que
    a próxima execução do pytest faz — e confirma que o banco aceita. Antes da
    correção, este INSERT estourava `companies_name_key`.
    """
    connection = _conn()
    next_tag = uuid.uuid4().hex[:8]
    assert next_tag != _RUN_TAG

    company_id = _scalar(
        connection,
        "INSERT INTO companies (name, cnpj, logo_type) VALUES (%s, %s, '') RETURNING id",
        (f'Metalúrgica Aurora {next_tag}',
         _valid_cnpj_from(f'1{int(next_tag, 16) % 10 ** 11:011d}')),
    )
    assert company_id and company_id != tenant['company_id']

    # Mesmo nome de unidade do tenant da jornada: só não colide porque o
    # UNIQUE de units é escopado por company_id. É essa a razão de bastar
    # tornar únicos os três identificadores globais.
    unit_id = _scalar(
        connection,
        'INSERT INTO units (company_id, name, unit_type, city) '
        "VALUES (%s, 'Produção', 'base', 'Macaé') RETURNING id",
        (company_id,),
    )
    assert unit_id

    # Este tenant sintético não tem employees/epis, então o DELETE em ordem
    # funciona. O tenant da jornada não é apagável assim — units, employees e
    # epis apontam para companies com ON DELETE RESTRICT — e é justamente por
    # isso que a correção da #186 é unicidade, não limpeza no teardown.
    connection.execute('DELETE FROM units WHERE company_id = %s', (company_id,))
    connection.execute('DELETE FROM companies WHERE id = %s', (company_id,))
    connection.commit()
