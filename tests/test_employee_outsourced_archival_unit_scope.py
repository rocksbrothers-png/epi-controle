"""PR22: arquivar/desarquivar colaborador terceirizado/prestador (Cadastro
de Colaboradores simplificado, ADR-0002 §10.2) para Administrador Local/
Gestor de EPI — parte que ainda faltava no Cadastro de Colaboradores: até
aqui só create/update tinham o piso técnico simplificado
(employees:create_simplified/update_simplified); archive/restore/delete
exigiam sempre employees:delete/employees:update completos
(_load_employee_for_lifecycle, modules/employees/routes.py), que
Administrador Local/Gestor de EPI nunca têm — então mesmo o colaborador que
eles próprios cadastraram não podia ser arquivado por eles.

Cobre: a alternativa (employees:update_simplified) só libera quando o
registro-alvo é genuinamente terceirizado/prestador (nunca CLT — mesma
fronteira do ADR-0002), dentro da própria Unidade operacional do ator, com
o módulo terceirizados_colaboradores habilitado para aquela Unidade
(ensure_module_enabled_for_unit, mesmo mecanismo já usado no create/update
deste cadastro).
"""

import sqlite3

import pytest

from core.schema import (
    ensure_employee_simplified_registration_columns,
    ensure_legal_entities,
    ensure_outsourced_companies,
    ensure_outsourced_company_unit_links,
    ensure_outsourced_company_archival_lifecycle_columns,
)
import modules.employees.routes as employees_routes
from modules.employees.service import create_employee_outsourced_simplified
from modules.settings.service import save_module_visibility

VALID_CPF = '111.444.777-35'
VALID_CPF_2 = '529.982.247-25'


@pytest.fixture(autouse=True)
def _sqlite_detection(monkeypatch):
    import epi_backend.db as db_module
    monkeypatch.setattr(db_module, '_is_sqlite_connection', lambda _conn: True)
    # _load_employee_for_lifecycle é chamado direto (sem handler/parsed HTTP
    # reais) — mesmo padrão de isolamento de resolve_actor_user_id usado em
    # tests/test_outsourced_pr6_routes.py.
    monkeypatch.setattr(employees_routes, 'resolve_actor_user_id', lambda _h, _p, payload: payload['actor_user_id'])
    # require_actor() passa por enforce_company_block_rules (contagem de
    # usuários faturáveis via COUNT(*) sem alias) — incompatível com o
    # row_factory de dict deste fixture (fora do escopo deste teste, que é
    # a lógica de escopo por Unidade em _load_employee_for_lifecycle).
    import core.repository as repository

    def _require_actor(connection, actor_user_id):
        row = connection.execute(
            'SELECT id, username, role, company_id, active, linked_employee_id, full_name '
            'FROM users WHERE id = ?', (int(actor_user_id),),
        ).fetchone()
        if not row:
            raise PermissionError('Usuário executor inválido.')
        return dict(row)

    monkeypatch.setattr(repository, 'require_actor', _require_actor)


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
            name TEXT, legal_name TEXT DEFAULT '', cnpj TEXT, logo_type TEXT DEFAULT '',
            user_limit INTEGER NOT NULL DEFAULT 999, license_status TEXT NOT NULL DEFAULT 'active',
            active INTEGER NOT NULL DEFAULT 1, contract_end TEXT, addendum_enabled INTEGER NOT NULL DEFAULT 0
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
            username TEXT, password TEXT DEFAULT '', company_id INTEGER, role TEXT, full_name TEXT DEFAULT '',
            active INTEGER NOT NULL DEFAULT 1, linked_employee_id INTEGER
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
    ensure_outsourced_company_unit_links(conn)
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


def _seed_user(conn, company_id, unit_id, role):
    """Cria a linha `employees` que representa a própria pessoa (vínculo
    operacional) + a linha `users` correspondente, com linked_employee_id."""
    cur = conn.execute(
        'INSERT INTO employees (company_id, unit_id, name) VALUES (?, ?, ?)',
        (company_id, unit_id, 'Responsável da Unidade'),
    )
    employee_id = int(cur.lastrowid)
    cur = conn.execute(
        'INSERT INTO users (username, password, company_id, role, full_name, active, linked_employee_id) '
        'VALUES (?, ?, ?, ?, ?, 1, ?)',
        (f'user{role}{unit_id}', 'x', company_id, role, 'Responsável', employee_id),
    )
    conn.commit()
    return int(cur.lastrowid)


def _seed_tenant_wide_user(conn, company_id, role='general_admin'):
    cur = conn.execute(
        'INSERT INTO users (username, password, company_id, role, full_name, active) VALUES (?, ?, ?, ?, ?, 1)',
        (f'user{role}', 'x', company_id, role, 'Geral'),
    )
    conn.commit()
    return int(cur.lastrowid)


def _fetch_actor(conn, user_id):
    row = conn.execute(
        'SELECT id, username, role, company_id, active, linked_employee_id, full_name '
        'FROM users WHERE id = ?', (int(user_id),),
    ).fetchone()
    return dict(row)


def _create_outsourced_employee(conn, company_id, unit_id, oc_id, actor, cpf=VALID_CPF):
    payload = {
        'company_id': company_id, 'unit_id': unit_id, 'outsourced_company_id': oc_id,
        'name': 'Trabalhador Terceirizado', 'cpf': cpf, 'role_name': 'Auxiliar',
        'tipo_vinculo': 'Terceirizado', 'admission_date': '2026-01-01',
    }
    return create_employee_outsourced_simplified(conn, payload, actor=actor)


def _create_clt_employee(conn, company_id, unit_id):
    cur = conn.execute(
        "INSERT INTO employees (company_id, unit_id, name, employee_id_code, tipo_vinculo) "
        "VALUES (?, ?, 'Colaborador CLT', 'E-001', 'CLT')",
        (company_id, unit_id),
    )
    conn.commit()
    return int(cur.lastrowid)


class _Match:
    def __init__(self, entity_id):
        self._entity_id = str(entity_id)

    def group(self, _i):
        return self._entity_id


def _load(conn, entity_id, actor_user_id, permission, outsourced_alternative):
    return employees_routes._load_employee_for_lifecycle(
        conn, None, None, {'actor_user_id': actor_user_id}, _Match(entity_id),
        permission, outsourced_alternative=outsourced_alternative,
    )


PERM_EMPLOYEES_UPDATE_SIMPLIFIED = 'employees:update_simplified'


def test_admin_can_archive_own_units_outsourced_employee_once_module_enabled():
    conn = _PgStyleConn(_conn())
    cid = _seed_company(conn)
    _bootstrap(conn)
    unit_a = _seed_unit(conn, cid, 'Unidade A')
    local_admin_id = _seed_user(conn, cid, unit_a, 'admin')
    local_admin = _fetch_actor(conn, local_admin_id)
    from modules.outsourced_companies.service import create_outsourced_company
    company_id = create_outsourced_company(conn, {'legal_name': 'Terceirizada A'}, cid, unit_id=unit_a)
    employee_id = _create_outsourced_employee(conn, cid, unit_a, company_id, local_admin)

    save_module_visibility(conn, cid, 'admin', {'terceirizados_colaboradores': True})
    actor, employee = _load(conn, employee_id, local_admin_id, 'employees:delete', PERM_EMPLOYEES_UPDATE_SIMPLIFIED)
    assert actor['role'] == 'admin'
    assert employee['id'] == employee_id


def test_admin_blocked_until_module_enabled_for_the_unit():
    conn = _PgStyleConn(_conn())
    cid = _seed_company(conn)
    _bootstrap(conn)
    unit_a = _seed_unit(conn, cid, 'Unidade A')
    local_admin_id = _seed_user(conn, cid, unit_a, 'admin')
    local_admin = _fetch_actor(conn, local_admin_id)
    from modules.outsourced_companies.service import create_outsourced_company
    company_id = create_outsourced_company(conn, {'legal_name': 'Terceirizada A'}, cid, unit_id=unit_a)
    employee_id = _create_outsourced_employee(conn, cid, unit_a, company_id, local_admin)

    with pytest.raises(PermissionError):
        _load(conn, employee_id, local_admin_id, 'employees:delete', PERM_EMPLOYEES_UPDATE_SIMPLIFIED)


def test_admin_cannot_archive_a_clt_employee_via_the_simplified_alternative():
    conn = _PgStyleConn(_conn())
    cid = _seed_company(conn)
    _bootstrap(conn)
    unit_a = _seed_unit(conn, cid, 'Unidade A')
    local_admin_id = _seed_user(conn, cid, unit_a, 'admin')
    save_module_visibility(conn, cid, 'admin', {'terceirizados_colaboradores': True})
    clt_employee_id = _create_clt_employee(conn, cid, unit_a)

    with pytest.raises(PermissionError):
        _load(conn, clt_employee_id, local_admin_id, 'employees:delete', PERM_EMPLOYEES_UPDATE_SIMPLIFIED)


def test_admin_cannot_archive_outsourced_employee_from_another_unit():
    conn = _PgStyleConn(_conn())
    cid = _seed_company(conn)
    _bootstrap(conn)
    unit_a = _seed_unit(conn, cid, 'Unidade A')
    unit_b = _seed_unit(conn, cid, 'Unidade B')
    local_admin_a_id = _seed_user(conn, cid, unit_a, 'admin')
    general_admin = {'id': _seed_tenant_wide_user(conn, cid), 'role': 'general_admin', 'company_id': cid}
    from modules.outsourced_companies.service import create_outsourced_company
    company_b = create_outsourced_company(conn, {'legal_name': 'Terceirizada B'}, cid, unit_id=unit_b)
    employee_in_b = _create_outsourced_employee(conn, cid, unit_b, company_b, general_admin)

    save_module_visibility(conn, cid, 'admin', {'terceirizados_colaboradores': True})
    with pytest.raises(PermissionError):
        _load(conn, employee_in_b, local_admin_a_id, 'employees:delete', PERM_EMPLOYEES_UPDATE_SIMPLIFIED)


def test_general_admin_still_archives_any_employee_without_the_unit_gate():
    conn = _PgStyleConn(_conn())
    cid = _seed_company(conn)
    _bootstrap(conn)
    unit_a = _seed_unit(conn, cid, 'Unidade A')
    general_admin_id = _seed_tenant_wide_user(conn, cid)
    clt_employee_id = _create_clt_employee(conn, cid, unit_a)

    # general_admin já tem employees:delete pleno — nunca passa pelo ramo
    # outsourced_alternative, módulo terceirizados_colaboradores nem
    # precisa estar habilitado.
    actor, employee = _load(
        conn, clt_employee_id, general_admin_id, 'employees:delete', PERM_EMPLOYEES_UPDATE_SIMPLIFIED,
    )
    assert actor['role'] == 'general_admin'
    assert employee['id'] == clt_employee_id
