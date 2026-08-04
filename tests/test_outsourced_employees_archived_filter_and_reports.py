"""PR 13 (ADR-0002 §10.4): aba "Colaboradores Arquivados" (filtro sobre
fetch_archived_employees, sem rota nova) e relatório de headcount por
empresa terceirizada (fetch_outsourced_employees_summary).
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
)
from modules.outsourced_companies.service import (
    create_outsourced_company,
    fetch_outsourced_employees_summary,
)

VALID_CPF = '111.444.777-35'
VALID_CPF_2 = '529.982.247-25'

ACTOR_GENERAL = {'id': 1, 'full_name': 'Admin Geral', 'role': 'general_admin', 'company_id': 1}


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


def _seed_unit(conn, company_id, name='Unidade 1'):
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


def _seed_clt_employee(conn, company_id, unit_id):
    cur = conn.execute(
        "INSERT INTO employees (company_id, unit_id, employee_id_code, cpf, name, tipo_vinculo) "
        "VALUES (?, ?, 'E-CLT-1', '000.000.000-00', 'Fulano CLT', 'CLT')",
        (company_id, unit_id),
    )
    conn.commit()
    return int(cur.lastrowid)


def _archive_employee(conn, employee_id, actor=ACTOR_GENERAL):
    row = conn.execute('SELECT id, company_id, name FROM employees WHERE id = ?', (employee_id,)).fetchone()
    return archival.archive_record(
        conn, 'employees', row, actor,
        entity_label='Colaborador', audit_prefix='employee', record_label=row['name'],
    )


# ── fetch_archived_employees(outsourced_only=) ──────────────────────────────

def test_outsourced_only_filter_excludes_archived_clt_employees():
    conn = _PgStyleConn(_conn())
    cid = _seed_company(conn)
    _bootstrap(conn)
    unit_id = _seed_unit(conn, cid)
    oc_id = create_outsourced_company(conn, {'legal_name': 'Terceirizada X'}, cid)
    terceirizado_id = _create_employee(conn, cid, unit_id, oc_id)
    clt_id = _seed_clt_employee(conn, cid, unit_id)
    _archive_employee(conn, terceirizado_id)
    _archive_employee(conn, clt_id)

    all_archived = fetch_archived_employees(conn, _actor(cid))
    assert {e['id'] for e in all_archived} == {terceirizado_id, clt_id}

    outsourced_only = fetch_archived_employees(conn, _actor(cid), outsourced_only=True)
    assert [e['id'] for e in outsourced_only] == [terceirizado_id]
    assert outsourced_only[0]['outsourced_company_name'] == 'Terceirizada X'
    assert outsourced_only[0]['tipo_vinculo'] == 'Terceirizado'


def test_outsourced_only_filter_is_scoped_by_tenant():
    conn = _PgStyleConn(_conn())
    cid_a = _seed_company(conn, name='Tenant A')
    cid_b = _seed_company(conn, name='Tenant B')
    _bootstrap(conn)
    unit_a = _seed_unit(conn, cid_a)
    unit_b = _seed_unit(conn, cid_b)
    oc_a = create_outsourced_company(conn, {'legal_name': 'Terceirizada A'}, cid_a)
    oc_b = create_outsourced_company(conn, {'legal_name': 'Terceirizada B'}, cid_b)
    emp_a = _create_employee(conn, cid_a, unit_a, oc_a, cpf=VALID_CPF)
    emp_b = _create_employee(conn, cid_b, unit_b, oc_b, cpf=VALID_CPF_2)
    _archive_employee(conn, emp_a, actor={**ACTOR_GENERAL, 'company_id': cid_a})
    _archive_employee(conn, emp_b, actor={**ACTOR_GENERAL, 'company_id': cid_b})

    archived_a = fetch_archived_employees(conn, _actor(cid_a), outsourced_only=True)
    assert [e['id'] for e in archived_a] == [emp_a]


def test_outsourced_only_filter_returns_empty_when_no_terceirizado_archived():
    conn = _PgStyleConn(_conn())
    cid = _seed_company(conn)
    _bootstrap(conn)
    unit_id = _seed_unit(conn, cid)
    clt_id = _seed_clt_employee(conn, cid, unit_id)
    _archive_employee(conn, clt_id)
    assert fetch_archived_employees(conn, _actor(cid), outsourced_only=True) == []


# ── fetch_outsourced_employees_summary ──────────────────────────────────────

def test_summary_counts_active_and_archived_by_tipo_vinculo():
    conn = _PgStyleConn(_conn())
    cid = _seed_company(conn)
    _bootstrap(conn)
    unit_id = _seed_unit(conn, cid)
    oc_id = create_outsourced_company(conn, {'legal_name': 'Terceirizada X'}, cid)
    active_id = _create_employee(conn, cid, unit_id, oc_id, cpf=VALID_CPF, tipo_vinculo='Terceirizado')
    archived_id = _create_employee(conn, cid, unit_id, oc_id, cpf=VALID_CPF_2, tipo_vinculo='Prestador de Serviço')
    _archive_employee(conn, archived_id)

    summary = fetch_outsourced_employees_summary(conn, cid)
    assert len(summary) == 1
    entry = summary[0]
    assert entry['outsourced_company_id'] == oc_id
    assert entry['legal_name'] == 'Terceirizada X'
    assert entry['active_count'] == 1
    assert entry['archived_count'] == 1
    assert entry['by_tipo_vinculo'] == {'Terceirizado': 1, 'Prestador de Serviço': 1}


def test_summary_includes_companies_with_no_employees():
    conn = _PgStyleConn(_conn())
    cid = _seed_company(conn)
    _bootstrap(conn)
    oc_id = create_outsourced_company(conn, {'legal_name': 'Terceirizada Vazia'}, cid)
    summary = fetch_outsourced_employees_summary(conn, cid)
    assert summary == [{
        'outsourced_company_id': oc_id, 'legal_name': 'Terceirizada Vazia', 'trade_name': '',
        'active_count': 0, 'archived_count': 0, 'by_tipo_vinculo': {},
    }]


def test_summary_is_scoped_by_tenant():
    conn = _PgStyleConn(_conn())
    cid_a = _seed_company(conn, name='Tenant A')
    cid_b = _seed_company(conn, name='Tenant B')
    _bootstrap(conn)
    create_outsourced_company(conn, {'legal_name': 'Terceirizada A'}, cid_a)
    create_outsourced_company(conn, {'legal_name': 'Terceirizada B'}, cid_b)
    summary_a = fetch_outsourced_employees_summary(conn, cid_a)
    assert [c['legal_name'] for c in summary_a] == ['Terceirizada A']
