"""PR 16 (ADR-0002 §10): regressão de ponta a ponta da extensão Cadastro de
Colaboradores, Arquivamento e Escopo por Unidade.

Os testes de PR10-15 cobrem cada peça isoladamente (módulo/permissões
simplificadas, rota do Cadastro de Colaboradores, arquivamento de
outsourced_companies, filtro de Colaboradores Arquivados + relatório de
headcount, Flutter, Web Legado). Este arquivo verifica que as peças
funcionam **juntas**, na mesma jornada que um Administrador Geral e um
Administrador Local realmente percorrem: módulo oculto por padrão →
Administrador Geral habilita module_visibility para o perfil → sem
module_unit_scope configurado nenhuma Unidade é restrita → Administrador
Geral restringe o módulo a uma Unidade específica → só aquela Unidade
acessa (nunca general_admin, que não é escopado por Unidade) →
Administrador Local cadastra um colaborador terceirizado pelo Cadastro de
Colaboradores simplificado → arquivar a empresa terceirizada bloqueia novo
cadastro contra ela → arquivar o colaborador o expõe em "Colaboradores
Arquivados" → o relatório de headcount reflete ativos/arquivados →
desarquivar a empresa libera novo cadastro de novo — sempre com isolamento
multi-tenant intacto.
"""

import sqlite3

import pytest

from core import archival
from core.schema import (
    ensure_employee_simplified_registration_columns,
    ensure_legal_entities,
    ensure_outsourced_companies,
    ensure_outsourced_company_archival_lifecycle_columns,
)
from modules.employees.service import (
    create_employee_outsourced_simplified,
    fetch_archived_employees,
    validate_employee_outsourced_simplified_payload,
)
from modules.outsourced_companies.service import (
    create_outsourced_company,
    fetch_outsourced_employees_summary,
)
from modules.settings.service import (
    ensure_module_enabled_for_unit,
    save_module_unit_scope,
    save_module_visibility,
)

VALID_CPF = '111.444.777-35'
VALID_CPF_2 = '529.982.247-25'


@pytest.fixture(autouse=True)
def _sqlite_detection(monkeypatch):
    import epi_backend.db as db_module
    monkeypatch.setattr(db_module, '_is_sqlite_connection', lambda _conn: True)


def _dict_factory(cursor, row):
    return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}


class _PgStyleConn:
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
        CREATE TABLE companies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT, legal_name TEXT DEFAULT '', cnpj TEXT, logo_type TEXT DEFAULT ''
        );
        CREATE TABLE units (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL, name TEXT, unit_type TEXT DEFAULT '',
            city TEXT DEFAULT '', notes TEXT DEFAULT ''
        );
        CREATE TABLE employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL, unit_id INTEGER, name TEXT,
            employee_id_code TEXT DEFAULT '', cpf TEXT DEFAULT '', email TEXT DEFAULT '',
            whatsapp TEXT DEFAULT '', preferred_contact_channel TEXT DEFAULT '',
            sector TEXT DEFAULT '', role_name TEXT DEFAULT '', admission_date TEXT DEFAULT '',
            schedule_type TEXT DEFAULT '', tipo_vinculo TEXT DEFAULT 'CLT', empresa_origem TEXT DEFAULT '',
            status TEXT NOT NULL DEFAULT 'active', archived_at TEXT, archived_by INTEGER,
            archive_reason TEXT NOT NULL DEFAULT '', retention_until TEXT,
            legal_hold INTEGER NOT NULL DEFAULT 0, legal_hold_reason TEXT NOT NULL DEFAULT '',
            deleted_at TEXT, deleted_by INTEGER, delete_reason TEXT NOT NULL DEFAULT ''
        );
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT, company_id INTEGER, role TEXT, full_name TEXT DEFAULT ''
        );
        CREATE TABLE employee_unit_movements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id INTEGER, movement_type TEXT, start_date TEXT, end_date TEXT DEFAULT '',
            target_unit_id INTEGER
        );
        CREATE TABLE company_audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT, company_id INTEGER NOT NULL,
            actor_user_id INTEGER NOT NULL, actor_name TEXT NOT NULL, action_type TEXT NOT NULL,
            summary TEXT NOT NULL, details_json TEXT NOT NULL DEFAULT '[]', created_at TEXT NOT NULL
        );
        CREATE TABLE app_meta (key TEXT PRIMARY KEY, value TEXT);
        """
    )
    return conn


def _bootstrap(conn):
    ensure_legal_entities(conn)
    ensure_outsourced_companies(conn)
    ensure_outsourced_company_archival_lifecycle_columns(conn)
    ensure_employee_simplified_registration_columns(conn)


def _seed_company(conn, name='ACME'):
    cur = conn.execute('INSERT INTO companies (name, legal_name, cnpj) VALUES (?, ?, ?)', (name, name, ''))
    conn.commit()
    return int(cur.lastrowid)


def _seed_unit(conn, company_id, name='Unidade'):
    cur = conn.execute('INSERT INTO units (company_id, name) VALUES (?, ?)', (company_id, name))
    conn.commit()
    return int(cur.lastrowid)


def _actor(company_id, role='general_admin'):
    return {'id': 1, 'role': role, 'company_id': company_id}


def _create_employee(conn, company_id, unit_id, oc_id, cpf=VALID_CPF, **overrides):
    payload = {
        'company_id': company_id, 'unit_id': unit_id, 'outsourced_company_id': oc_id,
        'name': 'Trabalhador Terceirizado', 'cpf': cpf, 'role_name': 'Auxiliar',
        'tipo_vinculo': 'Terceirizado', 'admission_date': '2026-01-01',
    }
    payload.update(overrides)
    return create_employee_outsourced_simplified(conn, payload, actor=_actor(company_id))


_LABEL_COLUMN = {'employees': 'name', 'outsourced_companies': 'legal_name'}


def _archive(conn, table, record_id, actor, entity_label, audit_prefix):
    label_column = _LABEL_COLUMN[table]
    row = conn.execute(
        f'SELECT id, company_id, status, {label_column} FROM {table} WHERE id = ?', (record_id,),
    ).fetchone()
    return archival.archive_record(
        conn, table, row, actor, entity_label=entity_label, audit_prefix=audit_prefix,
        record_label=row[label_column],
    )


def _restore(conn, table, record_id, actor, entity_label, audit_prefix):
    label_column = _LABEL_COLUMN[table]
    row = conn.execute(
        f'SELECT id, company_id, status, {label_column} FROM {table} WHERE id = ?', (record_id,),
    ).fetchone()
    return archival.restore_record(
        conn, table, row, actor, entity_label=entity_label, audit_prefix=audit_prefix,
        record_label=row[label_column],
    )


def test_module_gating_journey_hidden_by_default_then_scoped_by_unit():
    """§10.3: módulo nasce oculto; Administrador Geral habilita para o
    perfil; sem module_unit_scope configurado nenhuma Unidade é restrita;
    configurar o escopo passa a bloquear as Unidades fora da lista — só
    para admin/user, nunca para general_admin (mesma premissa de
    actor_operational_unit_id em todo o sistema)."""
    conn = _PgStyleConn(_conn())
    cid = _seed_company(conn)
    _bootstrap(conn)
    unit_a = _seed_unit(conn, cid, 'Unidade A')
    unit_b = _seed_unit(conn, cid, 'Unidade B')
    local_admin = _actor(cid, role='admin')

    # 1) Módulo opt-in, oculto por padrão: bloqueado mesmo com permissão
    # técnica (admin já tem employees:create_simplified desde o PR10).
    with pytest.raises(PermissionError):
        ensure_module_enabled_for_unit(conn, local_admin, 'terceirizados_colaboradores', unit_a)

    # 2) Administrador Geral habilita o módulo para o perfil Administrador
    # Local — sem module_unit_scope configurado, qualquer Unidade acessa.
    save_module_visibility(conn, cid, 'admin', {'terceirizados_colaboradores': True})
    ensure_module_enabled_for_unit(conn, local_admin, 'terceirizados_colaboradores', unit_a)
    ensure_module_enabled_for_unit(conn, local_admin, 'terceirizados_colaboradores', unit_b)

    # 3) Administrador Geral restringe o módulo à Unidade A — Unidade B some
    # para o Administrador Local.
    save_module_unit_scope(conn, cid, 'terceirizados_colaboradores', [unit_a])
    ensure_module_enabled_for_unit(conn, local_admin, 'terceirizados_colaboradores', unit_a)
    with pytest.raises(PermissionError):
        ensure_module_enabled_for_unit(conn, local_admin, 'terceirizados_colaboradores', unit_b)

    # 4) general_admin nunca é escopado por Unidade, mesmo com
    # module_unit_scope restrito à Unidade A no mesmo tenant.
    general_admin = _actor(cid, role='general_admin')
    save_module_visibility(conn, cid, 'general_admin', {'terceirizados_colaboradores': True})
    ensure_module_enabled_for_unit(conn, general_admin, 'terceirizados_colaboradores', unit_b)


def test_outsourced_employee_and_company_archival_journey():
    """Jornada completa do §10.1/§10.4: cadastro simplificado (nunca CLT),
    bloqueio por empresa arquivada, exposição em Colaboradores Arquivados,
    relatório de headcount e reabertura ao desarquivar a empresa."""
    conn = _PgStyleConn(_conn())
    cid = _seed_company(conn)
    _bootstrap(conn)
    unit_id = _seed_unit(conn, cid)
    actor = _actor(cid)

    oc_id = create_outsourced_company(conn, {'legal_name': 'Terceirizada X'}, cid, actor_user_id=actor['id'])

    # 1) Cadastro de Colaboradores simplificado: grava na MESMA tabela
    # employees, indistinguível do cadastro completo para o resto do sistema.
    emp_id = _create_employee(conn, cid, unit_id, oc_id)
    employee_row = conn.execute('SELECT * FROM employees WHERE id = ?', (emp_id,)).fetchone()
    assert employee_row['tipo_vinculo'] == 'Terceirizado'
    assert employee_row['outsourced_company_id'] == oc_id

    # 2) CLT nunca é aceito por este formulário — mesma validação usada pelo
    # Flutter e pelo Web Legado.
    with pytest.raises(ValueError, match='CLT'):
        validate_employee_outsourced_simplified_payload({
            'name': 'Fulano', 'tipo_vinculo': 'CLT', 'role_name': 'Auxiliar',
            'admission_date': '2026-01-01', 'outsourced_company_id': oc_id, 'unit_id': unit_id,
        })

    # 3) Arquivar a empresa terceirizada bloqueia novo cadastro contra ela
    # (aviso, não bloqueio silencioso) — core.archival.ensure_record_operational.
    _archive(conn, 'outsourced_companies', oc_id, actor, 'Empresa Terceirizada', 'outsourced_company')
    with pytest.raises(ValueError, match='arquivad'):
        _create_employee(conn, cid, unit_id, oc_id, cpf=VALID_CPF_2)

    # 4) O colaborador já cadastrado também pode ser arquivado — linha
    # comum de employees, o motor genérico não distingue tipo_vinculo.
    _archive(conn, 'employees', emp_id, actor, 'Colaborador', 'employee')
    archived_outsourced_only = fetch_archived_employees(conn, actor, outsourced_only=True)
    assert [e['id'] for e in archived_outsourced_only] == [emp_id]
    assert archived_outsourced_only[0]['outsourced_company_name'] == 'Terceirizada X'

    # 5) Relatório de headcount reflete o colaborador arquivado.
    summary = fetch_outsourced_employees_summary(conn, cid)
    assert summary[0]['outsourced_company_id'] == oc_id
    assert summary[0]['archived_count'] == 1
    assert summary[0]['active_count'] == 0

    # 6) Desarquivar a empresa libera novo cadastro de novo.
    _restore(conn, 'outsourced_companies', oc_id, actor, 'Empresa Terceirizada', 'outsourced_company')
    new_emp_id = _create_employee(conn, cid, unit_id, oc_id, cpf=VALID_CPF_2)
    assert new_emp_id != emp_id
    summary_after_restore = fetch_outsourced_employees_summary(conn, cid)
    assert summary_after_restore[0]['active_count'] == 1
    assert summary_after_restore[0]['archived_count'] == 1


def test_outsourced_extension_isolation_across_tenants():
    """Isolamento multi-tenant de ponta a ponta: module_unit_scope, empresa
    terceirizada, colaborador e relatório de um tenant nunca vazam para
    outro — condição vinculante do ADR-0002."""
    conn = _PgStyleConn(_conn())
    cid_a = _seed_company(conn, 'Tenant A')
    cid_b = _seed_company(conn, 'Tenant B')
    _bootstrap(conn)
    unit_a = _seed_unit(conn, cid_a)
    unit_b = _seed_unit(conn, cid_b)

    save_module_visibility(conn, cid_a, 'admin', {'terceirizados_colaboradores': True})
    save_module_unit_scope(conn, cid_a, 'terceirizados_colaboradores', [unit_a])
    # Tenant B nunca configurou nada — módulo continua oculto por padrão lá,
    # mesmo o Tenant A já tendo habilitado o dele.
    with pytest.raises(PermissionError):
        ensure_module_enabled_for_unit(conn, _actor(cid_b, role='admin'), 'terceirizados_colaboradores', unit_b)

    oc_a = create_outsourced_company(conn, {'legal_name': 'Terceirizada A'}, cid_a)
    oc_b = create_outsourced_company(conn, {'legal_name': 'Terceirizada B'}, cid_b)
    emp_a = _create_employee(conn, cid_a, unit_a, oc_a, cpf=VALID_CPF)
    emp_b = _create_employee(conn, cid_b, unit_b, oc_b, cpf=VALID_CPF_2)

    summary_a = fetch_outsourced_employees_summary(conn, cid_a)
    summary_b = fetch_outsourced_employees_summary(conn, cid_b)
    assert [c['legal_name'] for c in summary_a] == ['Terceirizada A']
    assert [c['legal_name'] for c in summary_b] == ['Terceirizada B']

    _archive(conn, 'employees', emp_a, _actor(cid_a), 'Colaborador', 'employee')
    _archive(conn, 'employees', emp_b, _actor(cid_b), 'Colaborador', 'employee')
    archived_a = fetch_archived_employees(conn, _actor(cid_a), outsourced_only=True)
    archived_b = fetch_archived_employees(conn, _actor(cid_b), outsourced_only=True)
    assert [e['id'] for e in archived_a] == [emp_a]
    assert [e['id'] for e in archived_b] == [emp_b]
