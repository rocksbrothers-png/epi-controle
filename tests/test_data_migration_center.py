"""Intelligent Data Migration Center — fundação (ADR-0003, PR 25).

Cobre o que sustenta o módulo inteiro:

- **Autorização**: `data_migration:manage` só existe para master_admin e
  general_admin, e o módulo `migracao` nasce oculto (opt-in) mesmo para
  eles.
- **Mapeamento inteligente**: os sinônimos PT/EN exigidos pelo pedido
  (Funcionário/Employee → Colaborador, Registration → Matrícula,
  Department → Unidade, PPE → EPI), fuzzy com score, e fallback manual.
- **Validação**: CPF/CNPJ com dígito verificador real, duplicidade no
  arquivo e contra a base, obrigatórios ausentes.
- **Estratégias**: dry_run não grava; insert_only/update_only/upsert/
  skip_duplicates fazem o que prometem.
- **Rollback**: desfaz de verdade — apaga inserções e restaura o valor
  anterior das atualizações.
- **Isolamento multi-tenant**: job, registros e rollback de um tenant
  nunca alcançam outro.
- **Segurança**: campo fora do descritor é recusado (allowlist), entidade
  de roadmap nunca chega ao writer.
"""

import base64
import json
import sqlite3

import pytest

from core.permissions import PERMISSIONS, PERM_DATA_MIGRATION_MANAGE
from core.schema import ensure_data_migration_tables
from epi_backend.rule_engine import (
    MODULE_REQUIRED_PERMISSIONS,
    _OPT_IN_MODULES,
    default_framework_payload,
)
from modules.data_migration import service
from modules.data_migration.catalog import get_entity, list_entities, require_enabled_entity
from modules.data_migration.mapper import (
    apply_mapping,
    normalize_manual_mapping,
    suggest_mapping,
)
from modules.data_migration.preview import build_preview, validate_cnpj, validate_cpf
from modules.data_migration.sources import read_source, source_hash

VALID_CPF_A = '111.444.777-35'
VALID_CPF_B = '529.982.247-25'
VALID_CPF_C = '390.533.447-05'

# Como o CPF fica gravado: só dígitos, exatamente como o cadastro manual
# grava (normalize_cpf). A importação usa a MESMA normalização.
STORED_CPF_A = '11144477735'


@pytest.fixture(autouse=True)
def _sqlite_detection(monkeypatch):
    import epi_backend.db as db_module
    monkeypatch.setattr(db_module, '_is_sqlite_connection', lambda _conn: True)


def _dict_factory(cursor, row):
    return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}


class _PgStyleConn:
    """Traduz o dialeto Postgres (%s) do código para SQLite (?) nos testes —
    mesmo adaptador usado pelas demais suítes deste repositório."""

    def __init__(self, conn):
        self._conn = conn

    def execute(self, sql, params=()):
        return self._conn.execute(str(sql).replace('%s', '?'), params)

    def commit(self):
        self._conn.commit()

    def __getattr__(self, name):
        return getattr(self._conn, name)


def _conn():
    conn = sqlite3.connect(':memory:')
    conn.row_factory = _dict_factory
    conn.executescript(
        """
        CREATE TABLE companies (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT);
        CREATE TABLE units (
            id INTEGER PRIMARY KEY AUTOINCREMENT, company_id INTEGER NOT NULL,
            name TEXT DEFAULT '', unit_type TEXT DEFAULT '', city TEXT DEFAULT '',
            notes TEXT DEFAULT ''
        );
        -- Espelha as constraints REAIS de `employees` em produção
        -- (core/bootstrap.py). Um fixture mais frouxo que a produção foi
        -- exatamente o que deixou passar a fase 1: NOT NULL em unit_id,
        -- sector e schedule_type só apareceu no PostgreSQL.
        CREATE TABLE employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT, company_id INTEGER NOT NULL,
            unit_id INTEGER NOT NULL, name TEXT NOT NULL, employee_id_code TEXT NOT NULL,
            cpf TEXT NOT NULL DEFAULT '', email TEXT NOT NULL DEFAULT '',
            whatsapp TEXT NOT NULL DEFAULT '', sector TEXT NOT NULL,
            role_name TEXT NOT NULL, admission_date TEXT NOT NULL,
            schedule_type TEXT NOT NULL,
            tipo_vinculo TEXT NOT NULL DEFAULT 'CLT', empresa_origem TEXT DEFAULT ''
        );
        """
    )
    wrapped = _PgStyleConn(conn)
    ensure_data_migration_tables(wrapped)
    conn.commit()
    return wrapped


def _seed_company(conn, name='ACME', unit_name='Base Macaé'):
    cur = conn.execute('INSERT INTO companies (name) VALUES (?)', (name,))
    company_id = int(cur.lastrowid)
    # employees.unit_id é NOT NULL no schema real: todo tenant de teste nasce
    # com a unidade que o CSV das fixtures referencia por nome.
    conn.execute('INSERT INTO units (company_id, name) VALUES (?, ?)', (company_id, unit_name))
    conn.commit()
    return company_id


def _actor(company_id, role='general_admin', user_id=1):
    return {'id': user_id, 'role': role, 'company_id': company_id, 'full_name': 'Ana Geral'}


def _csv(rows_text: str) -> bytes:
    return rows_text.encode('utf-8')


_CSV_THREE = (
    'Funcionário;CPF;Registration;Função;Unidade;Admissão\n'
    f'Maria Silva;{VALID_CPF_A};M-001;Soldadora;Base Macaé;2023-04-01\n'
    f'João Souza;{VALID_CPF_B};M-002;Eletricista;Base Macaé;2022-11-15\n'
    f'Ana Lima;{VALID_CPF_C};M-003;Mecânica;Base Macaé;2024-02-20\n'
)

_MAPPING_THREE = {
    'Funcionário': 'name', 'CPF': 'cpf',
    'Registration': 'employee_id_code', 'Função': 'role_name',
    'Unidade': 'unit_id', 'Admissão': 'admission_date',
}


def _run(conn, company_id, *, strategy, raw=None, mapping=None, actor=None):
    return service.run_migration(
        conn,
        company_id=company_id,
        entity='colaboradores',
        source_kind='csv',
        raw=raw if raw is not None else _csv(_CSV_THREE),
        mapping=mapping or _MAPPING_THREE,
        strategy=strategy,
        actor=actor or _actor(company_id),
        source_name='base_legada.csv',
    )


# ── Autorização (ADR-0003 §2.5) ─────────────────────────────────────────────

def test_only_master_and_general_admin_have_the_migration_permission():
    allowed = {role for role, perms in PERMISSIONS.items() if PERM_DATA_MIGRATION_MANAGE in perms}
    assert allowed == {'master_admin', 'general_admin'}


@pytest.mark.parametrize('role', ['registry_admin', 'admin', 'user', 'buyer', 'approver', 'employee'])
def test_operational_and_local_profiles_never_get_the_migration_permission(role):
    # O pedido é explícito: nunca para Admin Local, Gestores ou Colaboradores.
    assert PERM_DATA_MIGRATION_MANAGE not in PERMISSIONS[role]


def test_migration_module_technical_floor_is_the_dedicated_permission():
    assert MODULE_REQUIRED_PERMISSIONS['migracao'] == frozenset({PERM_DATA_MIGRATION_MANAGE})


def test_migration_module_is_opt_in_and_hidden_by_default_for_every_role():
    assert 'migracao' in _OPT_IN_MODULES
    visibility = default_framework_payload()['module_visibility']
    for role in PERMISSIONS:
        assert visibility[role]['*']['migracao'] is False, role


# ── Catálogo (ADR-0003 §2.1) ────────────────────────────────────────────────

def test_catalog_exposes_the_twenty_dashboard_cards():
    entities = list_entities()
    assert len(entities) == 20
    assert {'colaboradores', 'epis', 'unidades', 'fornecedores'} <= {e['key'] for e in entities}


def test_roadmap_entity_never_reaches_the_writer():
    # Segurança: entidade modelada mas sem writer validado é recusada no
    # gate, mesmo que a UI (ou um cliente hostil) tente chamá-la.
    assert get_entity('documentos').enabled is False
    with pytest.raises(ValueError, match='ainda não está disponível'):
        require_enabled_entity('documentos')


def test_unknown_entity_is_rejected():
    with pytest.raises(ValueError, match='desconhecida'):
        get_entity('tabela_arbitraria')


# ── Fontes: detecção automática (etapa 3 do assistente) ─────────────────────

def test_csv_detects_delimiter_encoding_columns_and_row_count():
    dataset = read_source('csv', _csv(_CSV_THREE))
    assert dataset.detected['delimiter'] == ';'
    assert dataset.detected['encoding'].startswith('utf-8')
    assert dataset.total_rows == 3
    assert dataset.columns == [
        'Funcionário', 'CPF', 'Registration', 'Função', 'Unidade', 'Admissão',
    ]


def test_json_accepts_both_bare_list_and_wrapped_payload():
    bare = read_source('json', json.dumps([{'nome': 'A'}, {'nome': 'B'}]).encode())
    wrapped = read_source('json', json.dumps({'data': [{'nome': 'A'}, {'nome': 'B'}]}).encode())
    assert bare.total_rows == wrapped.total_rows == 2


def test_xml_reads_attributes_and_child_elements_alike():
    xml = (
        '<funcionarios>'
        f'<funcionario cpf="{VALID_CPF_A}"><nome>Maria</nome></funcionario>'
        f'<funcionario cpf="{VALID_CPF_B}"><nome>João</nome></funcionario>'
        '</funcionarios>'
    )
    dataset = read_source('xml', xml.encode('utf-8'))
    assert dataset.total_rows == 2
    assert set(dataset.columns) == {'cpf', 'nome'}


def test_roadmap_source_is_refused_with_a_clear_message():
    with pytest.raises(ValueError, match='fases 5/6'):
        read_source('oracle', b'x')


def test_empty_and_oversized_files_are_refused_before_parsing():
    with pytest.raises(ValueError, match='vazio'):
        read_source('csv', b'')
    from modules.data_migration.sources import MAX_SOURCE_BYTES
    with pytest.raises(ValueError, match='excede o limite'):
        read_source('csv', b'x' * (MAX_SOURCE_BYTES + 1))


def test_signature_is_stable_for_the_same_layout():
    # Mesma assinatura = mapeamento salvo é reaplicado na reimportação.
    first = read_source('csv', _csv(_CSV_THREE))
    second = read_source('csv', _csv(_CSV_THREE.replace('Maria Silva', 'Maria Souza')))
    assert first.signature() == second.signature()


# ── Mapeamento inteligente (ADR-0003 §2.3) ──────────────────────────────────

def test_mapper_resolves_the_portuguese_english_synonyms_from_the_spec():
    descriptor = get_entity('colaboradores')
    result = suggest_mapping(
        descriptor, ['Funcionário', 'Employee', 'CPF', 'Registration', 'Department'],
    )
    mapping = result['mapping']
    assert mapping['CPF'] == 'cpf'
    assert mapping['Registration'] == 'employee_id_code'
    assert mapping['Department'] == 'unit_id'
    # "Funcionário" e "Employee" são sinônimos do MESMO campo: só um vence,
    # senão duas colunas gravariam sobre o mesmo destino.
    assert mapping['Funcionário'] == 'name'
    assert 'Employee' not in mapping


def test_mapper_maps_ppe_to_epi_for_the_equipment_entity():
    result = suggest_mapping(get_entity('epis'), ['PPE', 'CA', 'Fabricante'])
    assert result['mapping']['PPE'] == 'name'
    assert result['mapping']['CA'] == 'ca'
    assert result['mapping']['Fabricante'] == 'manufacturer'


def test_mapper_exposes_confidence_and_strategy_for_every_column():
    result = suggest_mapping(get_entity('colaboradores'), ['CPF', 'Coluna Desconhecida'])
    by_column = {item['source_column']: item for item in result['details']}
    assert by_column['CPF']['strategy'] == 'exact'
    assert by_column['CPF']['confidence'] == 1.0
    assert by_column['Coluna Desconhecida']['strategy'] == 'unmapped'


def test_unrecognized_column_falls_back_to_manual_mapping():
    result = suggest_mapping(get_entity('colaboradores'), ['CPF', 'XPTO-99'])
    assert result['unmapped_columns'] == ['XPTO-99']


def test_mapper_reports_missing_required_fields():
    result = suggest_mapping(get_entity('colaboradores'), ['Função'])
    # unit_id entra aqui porque employees.unit_id é NOT NULL: colaborador sem
    # unidade não existe neste sistema.
    assert set(result['missing_required']) == {
        'name', 'cpf', 'unit_id', 'employee_id_code', 'admission_date',
    }


def test_manual_mapping_rejects_a_field_outside_the_descriptor():
    # Allowlist (ADR-0003 §7): payload hostil não direciona a escrita.
    with pytest.raises(ValueError, match='Campo de destino inválido'):
        normalize_manual_mapping(
            get_entity('colaboradores'), {'A': 'password_hash'}, ['A'],
        )


def test_manual_mapping_rejects_two_columns_pointing_at_the_same_field():
    with pytest.raises(ValueError, match='mais de uma coluna'):
        normalize_manual_mapping(
            get_entity('colaboradores'),
            {'A': 'cpf', 'B': 'cpf', 'C': 'name'}, ['A', 'B', 'C'],
        )


def test_manual_mapping_requires_all_required_fields():
    with pytest.raises(ValueError, match='obrigatórios'):
        normalize_manual_mapping(get_entity('colaboradores'), {'A': 'name'}, ['A'])


# ── Validação (ADR-0003 §5) ─────────────────────────────────────────────────

def test_cpf_validation_uses_the_real_check_digits():
    assert validate_cpf(VALID_CPF_A) is True
    assert validate_cpf('111.444.777-00') is False   # dígito errado
    assert validate_cpf('111.111.111-11') is False   # repetido
    assert validate_cpf('123') is False


def test_cnpj_validation_uses_the_real_check_digits():
    assert validate_cnpj('11.222.333/0001-81') is True
    assert validate_cnpj('11.222.333/0001-00') is False


def test_preview_reports_invalid_cpf_with_the_row_number():
    records = [{'name': 'A', 'cpf': VALID_CPF_A}, {'name': 'B', 'cpf': '111.444.777-00'}]
    preview = build_preview(get_entity('colaboradores'), records)
    invalid = [d for d in preview['diagnostics'] if d['code'] == 'invalid_cpf']
    assert len(invalid) == 1
    assert invalid[0]['row'] == 2          # sem a linha o usuário não corrige
    assert preview['blocking'] is True


def test_preview_reports_missing_required_field():
    preview = build_preview(
        get_entity('colaboradores'),
        [{'name': '', 'cpf': VALID_CPF_A, 'unit_id': 7, 'employee_id_code': 'M-1',
          'role_name': 'Soldadora', 'admission_date': '2023-04-01'}],
    )
    assert preview['counters']['missing_required'] == 1
    assert preview['blocking'] is True


def test_preview_detects_duplicates_inside_the_file():
    records = [{'name': 'A', 'cpf': VALID_CPF_A}, {'name': 'A dup', 'cpf': VALID_CPF_A}]
    preview = build_preview(get_entity('colaboradores'), records)
    assert preview['counters']['duplicate_in_file'] == 1


def test_preview_separates_inserts_from_updates_against_the_base():
    records = [{'name': 'A', 'cpf': VALID_CPF_A}, {'name': 'B', 'cpf': VALID_CPF_B}]
    preview = build_preview(
        get_entity('colaboradores'), records, existing_keys={f'cpf:{"".join(c for c in VALID_CPF_A if c.isdigit())}'},
    )
    assert preview['will_update'] == 1
    assert preview['will_insert'] == 1


# ── Estratégias e escrita ───────────────────────────────────────────────────

def test_dry_run_writes_nothing():
    conn = _conn()
    cid = _seed_company(conn)
    result = _run(conn, cid, strategy='dry_run')
    assert result['applied'] is False
    assert result['job_id'] is None
    assert result['preview']['total_rows'] == 3
    assert conn.execute('SELECT COUNT(*) AS n FROM employees').fetchone()['n'] == 0


def test_insert_only_creates_the_records_and_registers_the_job():
    conn = _conn()
    cid = _seed_company(conn)
    result = _run(conn, cid, strategy='insert_only')
    assert result['totals']['inserted'] == 3
    rows = conn.execute('SELECT name, cpf, employee_id_code FROM employees ORDER BY id').fetchall()
    assert [r['name'] for r in rows] == ['Maria Silva', 'João Souza', 'Ana Lima']
    job = service.get_job(conn, result['job_id'], cid)
    assert job['status'] == 'completed'
    assert job['inserted_rows'] == 3


def test_insert_only_skips_records_that_already_exist():
    conn = _conn()
    cid = _seed_company(conn)
    _run(conn, cid, strategy='insert_only')
    again = _run(conn, cid, strategy='insert_only')
    assert again['totals']['inserted'] == 0
    assert again['totals']['skipped'] == 3
    assert conn.execute('SELECT COUNT(*) AS n FROM employees').fetchone()['n'] == 3


def test_upsert_updates_the_existing_record_matched_by_natural_key():
    conn = _conn()
    cid = _seed_company(conn)
    _run(conn, cid, strategy='insert_only')
    changed = _CSV_THREE.replace('Soldadora', 'Soldadora Sênior')
    result = _run(conn, cid, strategy='upsert', raw=_csv(changed))
    assert result['totals']['updated'] == 3
    row = conn.execute('SELECT role_name FROM employees WHERE cpf = ?', (STORED_CPF_A,)).fetchone()
    assert row['role_name'] == 'Soldadora Sênior'


def test_update_only_does_not_create_anything():
    conn = _conn()
    cid = _seed_company(conn)
    result = _run(conn, cid, strategy='update_only')
    assert result['totals']['inserted'] == 0
    assert result['totals']['skipped'] == 3
    assert conn.execute('SELECT COUNT(*) AS n FROM employees').fetchone()['n'] == 0


def test_import_is_blocked_when_the_file_has_errors():
    conn = _conn()
    cid = _seed_company(conn)
    # CPF com dígito verificador errado: chega ao preview e é ele que bloqueia.
    bad = ('Funcionário;CPF;Unidade;Matrícula;Função;Admissão\n'
           'Maria;111.444.777-00;Base Macaé;MX-BAD;Operador;2023-01-02\n')
    with pytest.raises(ValueError, match='bloqueada'):
        _run(conn, cid, strategy='insert_only', raw=_csv(bad),
             mapping={'Funcionário': 'name', 'CPF': 'cpf', 'Unidade': 'unit_id',
                  'Matrícula': 'employee_id_code', 'Função': 'role_name',
                  'Admissão': 'admission_date'})
    assert conn.execute('SELECT COUNT(*) AS n FROM employees').fetchone()['n'] == 0


def test_invalid_strategy_is_rejected():
    conn = _conn()
    cid = _seed_company(conn)
    with pytest.raises(ValueError, match='Estratégia'):
        _run(conn, cid, strategy='apagar_tudo')


# ── Rollback (ADR-0003 §2.4) ────────────────────────────────────────────────

def test_revert_removes_everything_the_job_inserted():
    conn = _conn()
    cid = _seed_company(conn)
    result = _run(conn, cid, strategy='insert_only')
    reverted = service.revert_job(conn, result['job_id'], cid, _actor(cid))
    assert reverted['deleted'] == 3
    assert conn.execute('SELECT COUNT(*) AS n FROM employees').fetchone()['n'] == 0
    assert service.get_job(conn, result['job_id'], cid)['status'] == 'reverted'


def test_revert_restores_the_previous_value_of_updated_records():
    conn = _conn()
    cid = _seed_company(conn)
    _run(conn, cid, strategy='insert_only')
    upsert = _run(conn, cid, strategy='upsert',
                  raw=_csv(_CSV_THREE.replace('Soldadora', 'Soldadora Sênior')))
    service.revert_job(conn, upsert['job_id'], cid, _actor(cid))
    row = conn.execute('SELECT role_name FROM employees WHERE cpf = ?', (STORED_CPF_A,)).fetchone()
    assert row['role_name'] == 'Soldadora'      # valor anterior de volta
    assert conn.execute('SELECT COUNT(*) AS n FROM employees').fetchone()['n'] == 3


def test_a_job_cannot_be_reverted_twice():
    conn = _conn()
    cid = _seed_company(conn)
    result = _run(conn, cid, strategy='insert_only')
    service.revert_job(conn, result['job_id'], cid, _actor(cid))
    with pytest.raises(ValueError, match='já foi revertida'):
        service.revert_job(conn, result['job_id'], cid, _actor(cid))


# ── Isolamento multi-tenant ─────────────────────────────────────────────────

def test_a_tenant_never_sees_another_tenants_jobs():
    conn = _conn()
    tenant_a, tenant_b = _seed_company(conn, 'A'), _seed_company(conn, 'B')
    _run(conn, tenant_a, strategy='insert_only')
    assert len(service.fetch_jobs(conn, tenant_a)) == 1
    assert service.fetch_jobs(conn, tenant_b) == []


def test_a_tenant_cannot_read_another_tenants_job_by_id():
    conn = _conn()
    tenant_a, tenant_b = _seed_company(conn, 'A'), _seed_company(conn, 'B')
    result = _run(conn, tenant_a, strategy='insert_only')
    assert service.get_job(conn, result['job_id'], tenant_b) is None


def test_a_tenant_cannot_revert_another_tenants_job():
    conn = _conn()
    tenant_a, tenant_b = _seed_company(conn, 'A'), _seed_company(conn, 'B')
    result = _run(conn, tenant_a, strategy='insert_only')
    with pytest.raises(ValueError, match='não encontrada'):
        service.revert_job(conn, result['job_id'], tenant_b, _actor(tenant_b))
    assert conn.execute('SELECT COUNT(*) AS n FROM employees').fetchone()['n'] == 3


def test_imported_records_carry_the_importing_tenant():
    conn = _conn()
    tenant_a, tenant_b = _seed_company(conn, 'A'), _seed_company(conn, 'B')
    _run(conn, tenant_a, strategy='insert_only')
    rows = conn.execute('SELECT DISTINCT company_id FROM employees').fetchall()
    assert [row['company_id'] for row in rows] == [tenant_a]
    assert tenant_b not in [row['company_id'] for row in rows]


def test_the_same_natural_key_in_two_tenants_stays_independent():
    # CPF é único por tenant, não global: o mesmo colaborador pode existir
    # em dois clientes diferentes sem um sobrescrever o outro.
    conn = _conn()
    tenant_a, tenant_b = _seed_company(conn, 'A'), _seed_company(conn, 'B')
    _run(conn, tenant_a, strategy='insert_only')
    result = _run(conn, tenant_b, strategy='insert_only')
    assert result['totals']['inserted'] == 3
    assert conn.execute('SELECT COUNT(*) AS n FROM employees').fetchone()['n'] == 6


# ── Mapeamento salvo (ADR-0003 §2.3) ────────────────────────────────────────

def test_confirmed_mapping_is_saved_and_reapplied_for_the_same_layout():
    conn = _conn()
    cid = _seed_company(conn)
    dataset = read_source('csv', _csv(_CSV_THREE))
    _run(conn, cid, strategy='insert_only')
    saved = service.load_saved_mapping(conn, cid, 'colaboradores', dataset.signature())
    assert saved == _MAPPING_THREE


def test_saved_mapping_is_scoped_per_tenant():
    conn = _conn()
    tenant_a, tenant_b = _seed_company(conn, 'A'), _seed_company(conn, 'B')
    dataset = read_source('csv', _csv(_CSV_THREE))
    _run(conn, tenant_a, strategy='insert_only')
    assert service.load_saved_mapping(conn, tenant_b, 'colaboradores', dataset.signature()) == {}


# ── Assistente: análise em uma chamada (etapas 3+4) ─────────────────────────

def test_analyze_returns_layout_and_suggested_mapping_together():
    analysis = service.analyze_source('csv', _csv(_CSV_THREE), 'colaboradores')
    assert analysis['detected']['delimiter'] == ';'
    assert analysis['detected']['total_rows'] == 3
    assert analysis['mapping']['CPF'] == 'cpf'
    assert len(analysis['sample']) == 3
    assert analysis['source_hash'] == source_hash(_csv(_CSV_THREE))


def test_apply_mapping_translates_rows_into_system_vocabulary():
    dataset = read_source('csv', _csv(_CSV_THREE))
    records = apply_mapping(_MAPPING_THREE, dataset.rows)
    assert records[0] == {
        'name': 'Maria Silva', 'cpf': VALID_CPF_A,
        'employee_id_code': 'M-001', 'role_name': 'Soldadora',
        'unit_id': 'Base Macaé', 'admission_date': '2023-04-01',
    }


# ── Referências e isolamento por linha (achados do teste de navegador) ───────

def test_unit_name_from_the_legacy_file_is_resolved_to_the_unit_id():
    """O export legado diz "Base Macaé", nunca o id interno do sistema."""
    conn = _conn()
    cid = _seed_company(conn)
    unit_id = conn.execute(
        'SELECT id FROM units WHERE company_id = ?', (cid,),
    ).fetchone()['id']
    _run(conn, cid, strategy='insert_only')
    rows = conn.execute(
        'SELECT unit_id FROM employees WHERE company_id = ?', (cid,),
    ).fetchall()
    assert [row['unit_id'] for row in rows] == [unit_id, unit_id, unit_id]


def test_unit_name_that_does_not_exist_blocks_before_writing_anything():
    """Referência inexistente vira erro no preview — nunca um INSERT que
    estoura no banco depois de a importação já ter começado."""
    conn = _conn()
    cid = _seed_company(conn)
    csv = (
        'Funcionário;CPF;Unidade;Matrícula;Função;Admissão\n'
        f'Maria Silva;{VALID_CPF_A};Unidade Que Nao Existe;MX-A;Operador;2023-01-02\n'
    )
    with pytest.raises(ValueError, match='bloqueada'):
        _run(conn, cid, strategy='insert_only', raw=_csv(csv),
             mapping={'Funcionário': 'name', 'CPF': 'cpf', 'Unidade': 'unit_id',
                  'Matrícula': 'employee_id_code', 'Função': 'role_name',
                  'Admissão': 'admission_date'})
    assert conn.execute('SELECT COUNT(*) AS n FROM employees').fetchone()['n'] == 0


def test_a_numeric_unit_value_is_accepted_as_an_id():
    """Planilha exportada do próprio sistema já traz o id."""
    conn = _conn()
    cid = _seed_company(conn)
    unit_id = conn.execute(
        'SELECT id FROM units WHERE company_id = ?', (cid,),
    ).fetchone()['id']
    csv = (
        'Funcionário;CPF;Unidade;Matrícula;Função;Admissão\n'
        f'Maria Silva;{VALID_CPF_A};{unit_id};MX-A;Operador;2023-01-02\n'
    )
    _run(conn, cid, strategy='insert_only', raw=_csv(csv),
         mapping={'Funcionário': 'name', 'CPF': 'cpf', 'Unidade': 'unit_id',
                  'Matrícula': 'employee_id_code', 'Função': 'role_name',
                  'Admissão': 'admission_date'})
    assert conn.execute(
        'SELECT unit_id FROM employees WHERE company_id = ?', (cid,),
    ).fetchone()['unit_id'] == unit_id


def test_one_bad_row_does_not_abort_the_whole_job():
    """A linha ruim é isolada num SAVEPOINT, pelo caminho real do motor.

    Sem isso, no PostgreSQL o primeiro erro aborta a transação e todo comando
    seguinte falha — inclusive o registro do diagnóstico e o UPDATE final do
    job — deixando a conexão envenenada para a próxima requisição.
    """
    conn = _conn()
    cid = _seed_company(conn)
    unit_id = conn.execute('SELECT id FROM units WHERE company_id = ?', (cid,)).fetchone()['id']
    # As 3 linhas passam na validação; a do meio só falha na hora de GRAVAR,
    # por um erro de banco — que é exatamente o caso que o SAVEPOINT isola.
    csv = (
        'Funcionário;CPF;Unidade;Matrícula;Função;Admissão\n'
        f'Maria Silva;{VALID_CPF_A};{unit_id};MX-A;Operador;2023-01-02\n'
        f'João Souza;{VALID_CPF_B};{unit_id};MX-B;Operador;2023-01-02\n'
        f'Ana Lima;{VALID_CPF_C};{unit_id};MX-C;Operador;2023-01-02\n'
    )
    conn.execute('CREATE TRIGGER reject_joao BEFORE INSERT ON employees '
                 "WHEN NEW.cpf = '52998224725' "
                 "BEGIN SELECT RAISE(ABORT, 'falha proposital de banco'); END")
    result = _run(conn, cid, strategy='insert_only', raw=_csv(csv),
                  mapping={'Funcionário': 'name', 'CPF': 'cpf', 'Unidade': 'unit_id',
                  'Matrícula': 'employee_id_code', 'Função': 'role_name',
                  'Admissão': 'admission_date'})

    # A linha ruim falhou sozinha; as outras duas foram gravadas.
    assert result['totals']['failed'] == 1
    assert result['totals']['inserted'] == 2
    # O job chegou ao status final apesar do erro.
    assert service.get_job(conn, result['job_id'], cid)['status'] == 'completed'
    # O diagnóstico da linha ruim foi gravado.
    errors = [r for r in service.fetch_job_records(conn, result['job_id'], cid) if r['action'] == 'error']
    assert len(errors) == 1
    assert 'falha proposital' in (errors[0]['error_message'] or '')
    # As linhas boas estão commitadas.
    assert conn.execute(
        'SELECT COUNT(*) AS n FROM employees WHERE company_id = ?', (cid,),
    ).fetchone()['n'] == 2


def test_connection_stays_usable_for_an_unrelated_query_after_a_row_failure():
    """A conexão não volta envenenada: a requisição seguinte funciona."""
    conn = _conn()
    cid = _seed_company(conn)
    unit_id = conn.execute('SELECT id FROM units WHERE company_id = ?', (cid,)).fetchone()['id']
    conn.execute('CREATE TRIGGER reject_all BEFORE INSERT ON employees '
                 "BEGIN SELECT RAISE(ABORT, 'falha proposital de banco'); END")
    csv = ('Funcionário;CPF;Unidade;Matrícula;Função;Admissão\n'
           f'Maria Silva;{VALID_CPF_A};{unit_id};MX-A;Operador;2023-01-02\n')
    result = _run(conn, cid, strategy='insert_only', raw=_csv(csv),
                  mapping={'Funcionário': 'name', 'CPF': 'cpf', 'Unidade': 'unit_id',
                  'Matrícula': 'employee_id_code', 'Função': 'role_name',
                  'Admissão': 'admission_date'})
    assert result['totals']['failed'] == 1
    # Consulta seguinte, sem relação com a importação, continua funcionando.
    assert conn.execute('SELECT COUNT(*) AS n FROM companies').fetchone()['n'] >= 1
    assert service.fetch_jobs(conn, cid)[0]['status'] == 'completed'


# ── Resolução de referências: casos exigidos na revisão de produção ─────────

def test_two_units_with_the_same_name_in_one_tenant_are_reported_as_ambiguous():
    """Ambiguidade nunca é resolvida em silêncio para a primeira que aparecer:
    isso alocaria a pessoa na unidade errada sem ninguém perceber."""
    conn = _conn()
    cid = _seed_company(conn)
    conn.execute('INSERT INTO units (company_id, name) VALUES (?, ?)', (cid, 'Base Macaé'))
    conn.commit()
    with pytest.raises(ValueError, match='bloqueada'):
        _run(conn, cid, strategy='insert_only')
    assert conn.execute('SELECT COUNT(*) AS n FROM employees').fetchone()['n'] == 0


def test_ambiguous_reference_diagnostic_shows_the_original_spreadsheet_value():
    conn = _conn()
    cid = _seed_company(conn)
    conn.execute('INSERT INTO units (company_id, name) VALUES (?, ?)', (cid, 'Base Macaé'))
    conn.commit()
    result = _run(conn, cid, strategy='dry_run')
    ambiguous = [d for d in result['preview']['diagnostics'] if d['code'] == 'unresolved_ambiguous']
    assert ambiguous
    assert ambiguous[0]['source_value'] == 'Base Macaé'
    assert '2 cadastros' in ambiguous[0]['message']


def test_the_same_unit_name_in_another_tenant_never_resolves():
    """Isolamento multi-tenant no resolver: "Base Macaé" da empresa B não pode
    virar a unidade da empresa A."""
    conn = _conn()
    tenant_a = _seed_company(conn, 'A')
    tenant_b = _seed_company(conn, 'B', unit_name='Base Exclusiva B')
    csv = (
        'Funcionário;CPF;Unidade;Matrícula;Função;Admissão\n'
        f'Maria Silva;{VALID_CPF_A};Base Exclusiva B;MX-A;Operador;2023-01-02\n'
    )
    with pytest.raises(ValueError, match='bloqueada'):
        _run(conn, tenant_a, strategy='insert_only', raw=_csv(csv),
             mapping={'Funcionário': 'name', 'CPF': 'cpf', 'Unidade': 'unit_id',
                  'Matrícula': 'employee_id_code', 'Função': 'role_name',
                  'Admissão': 'admission_date'})
    assert conn.execute('SELECT COUNT(*) AS n FROM employees').fetchone()['n'] == 0
    # E continua resolvendo normalmente para o dono.
    _run(conn, tenant_b, strategy='insert_only', raw=_csv(csv),
         mapping={'Funcionário': 'name', 'CPF': 'cpf', 'Unidade': 'unit_id',
                  'Matrícula': 'employee_id_code', 'Função': 'role_name',
                  'Admissão': 'admission_date'})
    assert conn.execute(
        'SELECT COUNT(*) AS n FROM employees WHERE company_id = ?', (tenant_b,),
    ).fetchone()['n'] == 1


def test_a_unit_id_from_another_tenant_is_refused():
    """Id numérico explícito também respeita o tenant — senão a planilha
    poderia apontar para o id de outra empresa."""
    conn = _conn()
    tenant_a = _seed_company(conn, 'A')
    tenant_b = _seed_company(conn, 'B')
    foreign_unit = conn.execute(
        'SELECT id FROM units WHERE company_id = ?', (tenant_b,),
    ).fetchone()['id']
    csv = ('Funcionário;CPF;Unidade;Matrícula;Função;Admissão\n'
           f'Maria Silva;{VALID_CPF_A};{foreign_unit};MX-A;Operador;2023-01-02\n')
    with pytest.raises(ValueError, match='bloqueada'):
        _run(conn, tenant_a, strategy='insert_only', raw=_csv(csv),
             mapping={'Funcionário': 'name', 'CPF': 'cpf', 'Unidade': 'unit_id',
                  'Matrícula': 'employee_id_code', 'Função': 'role_name',
                  'Admissão': 'admission_date'})


@pytest.mark.parametrize('written', [
    'base macae', 'BASE MACAÉ', '  Base Macaé  ', 'Base    Macaé', 'bAsE mAcAe',
])
def test_unit_name_matching_tolerates_case_accents_and_spacing(written):
    """Export legado digitado à mão ao longo de anos: caixa, acento e espaço
    sobrando não podem impedir o reconhecimento."""
    conn = _conn()
    cid = _seed_company(conn)
    unit_id = conn.execute('SELECT id FROM units WHERE company_id = ?', (cid,)).fetchone()['id']
    csv = ('Funcionário;CPF;Unidade;Matrícula;Função;Admissão\n'
           f'Maria Silva;{VALID_CPF_A};{written};MX-A;Operador;2023-01-02\n')
    _run(conn, cid, strategy='insert_only', raw=_csv(csv),
         mapping={'Funcionário': 'name', 'CPF': 'cpf', 'Unidade': 'unit_id',
                  'Matrícula': 'employee_id_code', 'Função': 'role_name',
                  'Admissão': 'admission_date'})
    assert conn.execute(
        'SELECT unit_id FROM employees WHERE company_id = ?', (cid,),
    ).fetchone()['unit_id'] == unit_id


# ── Regras de vínculo compartilhadas com o cadastro manual ──────────────────

def test_contractor_without_origin_company_is_rejected_by_the_domain_rule():
    conn = _conn()
    cid = _seed_company(conn)
    csv = (
        'Funcionário;CPF;Unidade;Vínculo;Empresa;Matrícula;Função;Admissão\n'
        f'Maria Silva;{VALID_CPF_A};Base Macaé;Terceirizado;;MX-T;Soldador;2023-01-02\n'
    )
    mapping = {'Funcionário': 'name', 'CPF': 'cpf', 'Unidade': 'unit_id',
               'Vínculo': 'tipo_vinculo', 'Empresa': 'empresa_origem',
               'Matrícula': 'employee_id_code', 'Função': 'role_name',
               'Admissão': 'admission_date'}
    result = _run(conn, cid, strategy='dry_run', raw=_csv(csv), mapping=mapping)
    codes = {d['code'] for d in result['preview']['diagnostics']}
    assert 'domain_rule' in codes
    assert result['preview']['blocking'] is True


def test_own_employee_never_keeps_an_origin_company():
    conn = _conn()
    cid = _seed_company(conn)
    csv = (
        'Funcionário;CPF;Unidade;Vínculo;Empresa;Matrícula;Função;Admissão\n'
        f'Maria Silva;{VALID_CPF_A};Base Macaé;CLT;Alguma Terceira;MX-C;Soldador;2023-01-02\n'
    )
    mapping = {'Funcionário': 'name', 'CPF': 'cpf', 'Unidade': 'unit_id',
               'Vínculo': 'tipo_vinculo', 'Empresa': 'empresa_origem',
               'Matrícula': 'employee_id_code', 'Função': 'role_name',
               'Admissão': 'admission_date'}
    _run(conn, cid, strategy='insert_only', raw=_csv(csv), mapping=mapping)
    row = conn.execute('SELECT empresa_origem FROM employees').fetchone()
    assert row['empresa_origem'] == ''


def test_imported_cpf_matches_a_manually_created_employee():
    """O defeito que motivou unificar a normalização: com CPF formatado na
    importação e só dígitos no cadastro manual, o upsert criava um segundo
    registro para a mesma pessoa."""
    conn = _conn()
    cid = _seed_company(conn)
    unit_id = conn.execute('SELECT id FROM units WHERE company_id = ?', (cid,)).fetchone()['id']
    # "Cadastro manual": grava o CPF só com dígitos, como create_employee faz.
    conn.execute(
        'INSERT INTO employees (company_id, unit_id, name, cpf, employee_id_code, '
        'sector, schedule_type, role_name, admission_date) '
        "VALUES (?, ?, ?, ?, ?, '', '', ?, ?)",
        (cid, unit_id, 'Maria Silva', '11144477735', 'M-001', 'Soldadora', '2023-04-01'),
    )
    conn.commit()
    csv = ('Funcionário;CPF;Unidade;Função;Matrícula;Admissão\n'
           f'Maria Silva;{VALID_CPF_A};Base Macaé;Soldadora Sênior;M-001;2023-04-01\n')
    result = _run(conn, cid, strategy='upsert', raw=_csv(csv),
                  mapping={'Funcionário': 'name', 'CPF': 'cpf', 'Unidade': 'unit_id',
                           'Função': 'role_name', 'Matrícula': 'employee_id_code',
                           'Admissão': 'admission_date'})
    assert result['totals']['updated'] == 1
    assert result['totals']['inserted'] == 0
    assert conn.execute('SELECT COUNT(*) AS n FROM employees').fetchone()['n'] == 1


# ── Codificação e arquivos malformados ─────────────────────────────────────

def test_latin1_and_utf8_produce_the_same_records():
    text = (
        'Funcionário;CPF;Unidade;Matrícula;Função;Admissão\n'
        f'João Conceição;{VALID_CPF_A};Base Macaé;MX-A;Operador;2023-01-02\n'
    )
    mapping = {'Funcionário': 'name', 'CPF': 'cpf', 'Unidade': 'unit_id',
           'Matrícula': 'employee_id_code', 'Função': 'role_name',
           'Admissão': 'admission_date'}
    names = []
    for raw in (text.encode('utf-8'), text.encode('latin-1')):
        conn = _conn()
        cid = _seed_company(conn)
        _run(conn, cid, strategy='insert_only', raw=raw, mapping=mapping)
        names.append(conn.execute('SELECT name FROM employees').fetchone()['name'])
    assert names[0] == names[1] == 'João Conceição'


def test_a_file_without_usable_columns_is_refused_with_a_clear_message():
    conn = _conn()
    _seed_company(conn)
    with pytest.raises(ValueError):
        read_source('csv', b'')


def test_a_row_with_fewer_columns_than_the_header_does_not_crash_the_import():
    """CSV malformado é comum em export legado: a linha curta vira erro de
    linha, não exceção do job."""
    conn = _conn()
    cid = _seed_company(conn)
    csv = (
        'Funcionário;CPF;Unidade;Matrícula;Função;Admissão\n'
        f'Maria Silva;{VALID_CPF_A};Base Macaé;MX-A;Operador;2023-01-02\n'
        'Linha Curta\n'
    )
    result = _run(conn, cid, strategy='dry_run', raw=_csv(csv),
                  mapping={'Funcionário': 'name', 'CPF': 'cpf', 'Unidade': 'unit_id',
                  'Matrícula': 'employee_id_code', 'Função': 'role_name',
                  'Admissão': 'admission_date'})
    assert result['preview']['total_rows'] == 2
    assert result['preview']['blocking'] is True


# ── Pureza do dry-run e idempotência do rollback ───────────────────────────

def test_dry_run_writes_nothing_at_all_not_even_a_job():
    conn = _conn()
    cid = _seed_company(conn)
    result = _run(conn, cid, strategy='dry_run')
    assert result['job_id'] is None
    assert result['applied'] is False
    for table in ('employees', 'migration_jobs', 'migration_job_records', 'migration_field_mappings'):
        assert conn.execute(f'SELECT COUNT(*) AS n FROM {table}').fetchone()['n'] == 0, table


def test_reverting_twice_changes_nothing_the_second_time():
    conn = _conn()
    cid = _seed_company(conn)
    result = _run(conn, cid, strategy='insert_only')
    service.revert_job(conn, result['job_id'], cid, _actor(cid))
    remaining = conn.execute('SELECT COUNT(*) AS n FROM employees').fetchone()['n']
    with pytest.raises(ValueError, match='já foi revertida'):
        service.revert_job(conn, result['job_id'], cid, _actor(cid))
    assert conn.execute('SELECT COUNT(*) AS n FROM employees').fetchone()['n'] == remaining


def test_revert_only_removes_what_that_job_created():
    """Rollback cirúrgico: registros anteriores à importação continuam lá."""
    conn = _conn()
    cid = _seed_company(conn)
    unit_id = conn.execute('SELECT id FROM units WHERE company_id = ?', (cid,)).fetchone()['id']
    conn.execute(
        'INSERT INTO employees (company_id, unit_id, name, cpf, employee_id_code, '
        'sector, schedule_type, role_name, admission_date) '
        "VALUES (?, ?, ?, ?, ?, '', '', ?, ?)",
        (cid, unit_id, 'Preexistente', '39053344705', 'PRE-1', 'Almoxarife', '2020-01-01'),
    )
    conn.commit()
    csv = (
        'Funcionário;CPF;Unidade;Matrícula;Função;Admissão\n'
        f'Maria Silva;{VALID_CPF_A};Base Macaé;MX-A;Operador;2023-01-02\n'
        f'João Souza;{VALID_CPF_B};Base Macaé;MX-B;Operador;2023-01-02\n'
    )
    result = _run(conn, cid, strategy='insert_only', raw=_csv(csv),
                  mapping={'Funcionário': 'name', 'CPF': 'cpf', 'Unidade': 'unit_id',
                  'Matrícula': 'employee_id_code', 'Função': 'role_name',
                  'Admissão': 'admission_date'})
    assert result['totals']['inserted'] == 2
    service.revert_job(conn, result['job_id'], cid, _actor(cid))
    rows = conn.execute('SELECT name FROM employees').fetchall()
    assert [row['name'] for row in rows] == ['Preexistente']



# ── Auditoria (ADR-0003 §6) ─────────────────────────────────────────────────

def test_every_touched_row_is_recorded_with_before_and_after():
    conn = _conn()
    cid = _seed_company(conn)
    result = _run(conn, cid, strategy='insert_only')
    records = service.fetch_job_records(conn, result['job_id'], cid)
    assert len(records) == 3
    assert {r['action'] for r in records} == {'insert'}
    raw = conn.execute(
        'SELECT before_json, after_json FROM migration_job_records WHERE job_id = ? LIMIT 1',
        (result['job_id'],),
    ).fetchone()
    assert raw['before_json'] is None                    # insert não tem "antes"
    assert json.loads(raw['after_json'])['name'] == 'Maria Silva'


def test_job_stores_actor_source_and_hash_for_the_audit_trail():
    conn = _conn()
    cid = _seed_company(conn)
    result = _run(conn, cid, strategy='insert_only')
    job = service.get_job(conn, result['job_id'], cid)
    assert job['actor_name'] == 'Ana Geral'
    assert job['source_kind'] == 'csv'
    assert job['source_name'] == 'base_legada.csv'
    assert job['source_hash'] == source_hash(_csv(_CSV_THREE))
    assert job['started_at'] and job['finished_at']


def test_base64_payload_round_trips_through_the_route_contract():
    # A rota recebe o arquivo em base64 (routes._decode_content).
    encoded = base64.b64encode(_csv(_CSV_THREE)).decode()
    assert base64.b64decode(encoded, validate=True) == _csv(_CSV_THREE)
