"""GET endpoints dedicados de Colaboradores + correção da alocação atual.

Cobre:
  - active_temporary_unit_allocations / apply_current_unit_allocation /
    fetch_employees enriquecidos com current_unit_id/current_unit_name/
    unit_allocation_type (bug: a tabela lia esses campos mas nunca os recebia,
    exibindo a unidade-base durante transferências temporárias).
  - GET /api/employees, GET /api/employees/(id), GET /api/employee-unit-movements
"""

import io
import json
import sqlite3
from urllib.parse import urlparse

import pytest

import modules.employees.routes as routes
from modules.employees.service import (
    active_temporary_unit_allocations,
    apply_current_unit_allocation,
    fetch_employees,
)


def _conn():
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        CREATE TABLE companies (id INTEGER PRIMARY KEY, name TEXT, cnpj TEXT, logo_type TEXT DEFAULT '');
        CREATE TABLE units (id INTEGER PRIMARY KEY, name TEXT, unit_type TEXT DEFAULT 'base',
            city TEXT DEFAULT '', company_id INTEGER);
        CREATE TABLE employees (
            id INTEGER PRIMARY KEY, company_id INTEGER, unit_id INTEGER, employee_id_code TEXT,
            cpf TEXT DEFAULT '', name TEXT, email TEXT DEFAULT '', whatsapp TEXT DEFAULT '',
            preferred_contact_channel TEXT DEFAULT 'whatsapp', sector TEXT DEFAULT '',
            role_name TEXT DEFAULT '', admission_date TEXT DEFAULT '', schedule_type TEXT DEFAULT '',
            tipo_vinculo TEXT DEFAULT 'CLT', empresa_origem TEXT DEFAULT ''
        );
        CREATE TABLE employee_unit_movements (
            id INTEGER PRIMARY KEY AUTOINCREMENT, employee_id INTEGER, company_id INTEGER,
            source_unit_id INTEGER, target_unit_id INTEGER, movement_type TEXT,
            start_date TEXT, end_date TEXT DEFAULT ''
        );
        INSERT INTO companies (id, name, cnpj) VALUES (1, 'ACME', '1');
        INSERT INTO units (id, name, company_id) VALUES (10, 'Base Santos', 1), (20, 'Plataforma P-50', 1);
        INSERT INTO employees (id, company_id, unit_id, employee_id_code, name)
            VALUES (100, 1, 10, 'E100', 'Ana'), (200, 1, 10, 'E200', 'Bruno');
    """)
    conn.commit()
    return conn


def _temp_move(conn, employee_id, target, start, end=''):
    conn.execute(
        'INSERT INTO employee_unit_movements (employee_id, company_id, source_unit_id, target_unit_id, '
        'movement_type, start_date, end_date) VALUES (?, 1, 10, ?, ?, ?, ?)',
        (employee_id, target, 'temporary', start, end),
    )
    conn.commit()


# ── service: enriquecimento de alocação ───────────────────────────────────────

def test_active_allocation_picks_open_temporary():
    conn = _conn()
    _temp_move(conn, 100, 20, '2000-01-01', '')  # aberta -> ativa hoje
    allocations = active_temporary_unit_allocations(conn)
    assert allocations == {100: {'unit_id': 20, 'unit_name': 'Plataforma P-50'}}


def test_expired_and_future_movements_ignored():
    conn = _conn()
    _temp_move(conn, 100, 20, '2000-01-01', '2000-12-31')  # expirada
    _temp_move(conn, 200, 20, '2999-01-01', '')            # futura
    assert active_temporary_unit_allocations(conn) == {}


def test_fetch_employees_marks_temporary_and_definitive():
    conn = _conn()
    _temp_move(conn, 100, 20, '2000-01-01', '')  # Ana em movimentação temporária
    employees = {e['id']: e for e in fetch_employees(conn)}
    assert employees[100]['current_unit_name'] == 'Plataforma P-50'
    assert employees[100]['unit_allocation_type'] == 'temporary'
    assert employees[100]['current_unit_id'] == 20
    # Bruno sem movimentação -> unidade-base, definitiva
    assert employees[200]['current_unit_name'] == 'Base Santos'
    assert employees[200]['unit_allocation_type'] == 'definitive'
    assert employees[200]['current_unit_id'] == 10


def test_latest_temporary_wins():
    conn = _conn()
    _temp_move(conn, 100, 10, '2000-01-01', '')
    _temp_move(conn, 100, 20, '2001-01-01', '')  # mais recente
    assert active_temporary_unit_allocations(conn)[100]['unit_id'] == 20


def test_apply_allocation_single_uses_base_when_no_movement():
    conn = _conn()
    emp = {'id': 200, 'unit_id': 10, 'unit_name': 'Base Santos'}
    apply_current_unit_allocation(conn, [emp])
    assert emp['unit_allocation_type'] == 'definitive'
    assert emp['current_unit_name'] == 'Base Santos'


# ── handlers ──────────────────────────────────────────────────────────────────

class _FakeHandler:
    def __init__(self):
        self.path = '/api/employees'
        self.command = 'GET'
        self.status = None
        self.wfile = io.BytesIO()

    def send_response(self, status):
        self.status = status

    def send_header(self, *_a, **_k):
        pass

    def end_headers(self):
        pass

    def json(self):
        return json.loads(self.wfile.getvalue().decode('utf-8'))


def _parsed(query='actor_user_id=1'):
    return urlparse(f'/api/employees?{query}')


def _patch(monkeypatch, actor):
    monkeypatch.setattr(routes, 'get_connection', lambda: type('C', (), {'close': lambda self: None})())
    monkeypatch.setattr(routes, 'resolve_actor_user_id', lambda *a, **k: actor['id'])
    monkeypatch.setattr(routes, 'authorize_action', lambda *a, **k: actor)


def test_get_employees_returns_list(monkeypatch):
    actor = {'id': 1, 'role': 'general_admin', 'company_id': 1}
    _patch(monkeypatch, actor)
    seen = {}

    def _fetch(_c, a, *, unit_context_id=None):
        seen['actor'] = a
        seen['unit_context_id'] = unit_context_id
        return [{'id': 100}, {'id': 200}]

    monkeypatch.setattr(routes, 'fetch_employees', _fetch)
    monkeypatch.setattr(routes, 'resolve_actor_unit_context', lambda *a, **k: None)
    h = _FakeHandler()
    routes.handle_get_employees(h, _parsed(), None, None)
    assert h.status == 200 and seen['actor'] is actor
    assert len(h.json()['employees']) == 2
    # Sem Unidade selecionada, a listagem não reporta vínculo (ADR-0002 §13,
    # PR C1) — em vez de despejar todos os vínculos do tenant.
    assert seen['unit_context_id'] is None


def test_get_employee_single_enriched(monkeypatch):
    actor = {'id': 1, 'role': 'master_admin', 'company_id': None}
    _patch(monkeypatch, actor)
    monkeypatch.setattr(routes, 'get_employee_by_id', lambda _c, eid: {'id': eid, 'unit_id': 10, 'name': 'Ana'})
    monkeypatch.setattr(routes, 'get_unit_by_id', lambda _c, uid: {'id': uid, 'name': 'Base Santos'})
    monkeypatch.setattr(routes, 'ensure_actor_employee_scope', lambda *a, **k: None)
    monkeypatch.setattr(routes, 'apply_current_unit_allocation',
                        lambda _c, emps: [e.update({'unit_allocation_type': 'definitive'}) for e in emps] and emps)
    h = _FakeHandler()
    match = type('M', (), {'group': lambda self, i: '100'})()
    routes.handle_get_employee(h, _parsed(), None, match)
    body = h.json()
    assert h.status == 200 and body['employee']['unit_name'] == 'Base Santos'


def test_get_employee_404(monkeypatch):
    actor = {'id': 1, 'role': 'master_admin', 'company_id': None}
    _patch(monkeypatch, actor)
    monkeypatch.setattr(routes, 'get_employee_by_id', lambda _c, eid: None)
    h = _FakeHandler()
    match = type('M', (), {'group': lambda self, i: '999'})()
    routes.handle_get_employee(h, _parsed(), None, match)
    assert h.status == 404


def test_get_employee_scope_denied(monkeypatch):
    actor = {'id': 5, 'role': 'admin', 'company_id': 1}
    _patch(monkeypatch, actor)
    monkeypatch.setattr(routes, 'get_employee_by_id', lambda _c, eid: {'id': eid, 'unit_id': 10})

    def _deny(*a, **k):
        raise PermissionError('fora da unidade')

    monkeypatch.setattr(routes, 'ensure_actor_employee_scope', _deny)
    h = _FakeHandler()
    match = type('M', (), {'group': lambda self, i: '100'})()
    with pytest.raises(PermissionError):
        routes.handle_get_employee(h, _parsed('actor_user_id=5'), None, match)


def test_get_movements(monkeypatch):
    actor = {'id': 1, 'role': 'general_admin', 'company_id': 1}
    _patch(monkeypatch, actor)
    monkeypatch.setattr(routes, 'fetch_employee_movements', lambda _c, a: [{'id': 1, 'movement_type': 'temporary'}])
    h = _FakeHandler()
    routes.handle_get_employee_unit_movements(h, _parsed(), None, None)
    assert h.json()['items'][0]['movement_type'] == 'temporary'


def test_routes_registered():
    recorded = []

    class R:
        def register(self, method, path, _h, *, regex=False):
            recorded.append((method, path))

    routes.register_routes(R())
    assert ('GET', '/api/employees') in recorded
    assert ('GET', r'^/api/employees/(\d+)$') in recorded
    assert ('GET', '/api/employee-unit-movements') in recorded
