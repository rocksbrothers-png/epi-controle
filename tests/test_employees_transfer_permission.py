"""`employees:transfer` vs `employees:update` — duas capacidades distintas.

`employees:update` gateava, ao mesmo tempo, três coisas diferentes:
editar dados cadastrais (PUT /api/employees/<id>), reativar colaborador
desligado (POST /api/employees/<id>/restore) e transferir colaborador entre
unidades (POST /api/employee-unit-movements). O Administrador Local
(docs/PAPEIS_E_ATRIBUICOES.md #4) precisa da terceira, mas não das duas
primeiras — que são atribuição do Administrador de Registro (#3). Uma
permissão só não permitia essa separação.

Este teste exercita a rota real `handle_post_employee_unit_movements` (não
mocka a lógica de negócio, só a conexão), passando pela checagem de permissão
de verdade (`ensure_permission`) — para provar que a permissão exigida é
exatamente `employees:transfer`, e que o Administrador Local passa enquanto o
Gestor de EPI é barrado.
"""

import io
import json
import sqlite3
from urllib.parse import urlparse

import pytest

import modules.employees.routes as routes
from core.auth import ensure_permission
from core.permissions import PERM_EMPLOYEES_TRANSFER, PERM_EMPLOYEES_UPDATE, PERMISSIONS


class _UnclosableConnection:
    """`with closing(get_connection())` fecha a conexão ao sair do bloco — o
    teste precisa consultar o :memory: depois, então ignora esse close()."""

    def __init__(self, real):
        self._real = real

    def __getattr__(self, name):
        return getattr(self._real, name)

    def close(self):
        pass


def _conn():
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        CREATE TABLE employees (
            id INTEGER PRIMARY KEY, company_id INTEGER, unit_id INTEGER, employee_id_code TEXT,
            cpf TEXT DEFAULT '', name TEXT, sector TEXT DEFAULT '', role_name TEXT DEFAULT '',
            admission_date TEXT DEFAULT '', schedule_type TEXT DEFAULT ''
        );
        CREATE TABLE units (id INTEGER PRIMARY KEY, name TEXT, company_id INTEGER);
        CREATE TABLE employee_unit_movements (
            id INTEGER PRIMARY KEY AUTOINCREMENT, employee_id INTEGER, company_id INTEGER,
            source_unit_id INTEGER, target_unit_id INTEGER, movement_type TEXT,
            start_date TEXT, end_date TEXT DEFAULT '', notes TEXT DEFAULT '',
            actor_user_id INTEGER, actor_name TEXT DEFAULT '', created_at TEXT DEFAULT ''
        );
        INSERT INTO units (id, name, company_id) VALUES (10, 'Base Santos', 1), (20, 'Plataforma P-50', 1);
        INSERT INTO employees (id, company_id, unit_id, employee_id_code, name)
            VALUES (100, 1, 10, 'E100', 'Ana');
        """
    )
    conn.commit()
    return conn


class _FakeHandler:
    def __init__(self):
        self.status = None
        self.path = '/api/employee-unit-movements'
        self.wfile = io.BytesIO()

    def send_response(self, status):
        self.status = status

    def send_header(self, *_a, **_k):
        pass

    def end_headers(self):
        pass

    def json(self):
        return json.loads(self.wfile.getvalue().decode('utf-8'))


ADMIN_LOCAL = {'id': 1, 'role': 'admin', 'company_id': 1, 'full_name': 'Admin Local'}
GESTOR_EPI = {'id': 3, 'role': 'user', 'company_id': 1, 'full_name': 'Gestor de EPI'}


def _authorize_as_real_check(actor):
    """Substitui `authorize_action` mas continua checando a permissão de
    verdade (`ensure_permission`), só sem bater no banco para carregar o
    ator — o mesmo padrão de `_patch()` em test_employees_get_endpoints.py,
    fortalecido para não mascarar a checagem de permissão real."""
    def _fn(_connection, _actor_user_id, action, _company_id=None):
        ensure_permission(actor, action)
        return actor
    return _fn


def _payload(employee_id=100, target_unit_id=20, actor_user_id=1):
    return {
        'actor_user_id': actor_user_id,
        'employee_id': employee_id,
        'target_unit_id': target_unit_id,
        'movement_type': 'definitive',
        'start_date': '2026-01-01',
    }


def test_permission_matrix_separates_update_from_transfer():
    assert PERM_EMPLOYEES_TRANSFER in PERMISSIONS['admin']
    assert PERM_EMPLOYEES_UPDATE not in PERMISSIONS['admin']
    for role in ('master_admin', 'general_admin', 'registry_admin'):
        assert PERM_EMPLOYEES_TRANSFER in PERMISSIONS[role], role
    # master_admin não retém employees:update de forma permanente
    # (docs/PAPEIS_E_ATRIBUICOES.md #1 — acesso operacional só via suporte
    # formal auditado); general_admin/registry_admin seguem com o cadastro.
    assert PERM_EMPLOYEES_UPDATE not in PERMISSIONS['master_admin']
    for role in ('general_admin', 'registry_admin'):
        assert PERM_EMPLOYEES_UPDATE in PERMISSIONS[role], role


def test_local_admin_can_transfer_employee(monkeypatch):
    conn = _conn()
    monkeypatch.setattr(routes, 'get_connection', lambda: _UnclosableConnection(conn))
    monkeypatch.setattr(routes, 'resolve_actor_user_id', lambda *a, **k: 1)
    monkeypatch.setattr(routes, 'authorize_action', _authorize_as_real_check(ADMIN_LOCAL))
    monkeypatch.setattr(routes, 'get_employee_by_id', lambda _c, eid: {'id': eid, 'company_id': 1, 'unit_id': 10})
    monkeypatch.setattr(routes, 'get_unit_by_id', lambda _c, uid: {'id': uid, 'company_id': 1, 'name': 'Plataforma P-50'})
    monkeypatch.setattr(routes, 'ensure_resource_company', lambda *a, **k: None)
    monkeypatch.setattr(routes, 'ensure_employee_operational', lambda *a, **k: None)
    monkeypatch.setattr(routes, 'ensure_unit_operational', lambda *a, **k: None)
    h = _FakeHandler()
    routes.handle_post_employee_unit_movements(
        h, urlparse('/api/employee-unit-movements'), _payload(), None
    )
    assert h.status == 200
    row = conn.execute('SELECT * FROM employee_unit_movements WHERE employee_id = 100').fetchone()
    assert row is not None
    assert row['target_unit_id'] == 20


def test_epi_manager_cannot_transfer_employee(monkeypatch):
    """Gestor de EPI (docs/PAPEIS_E_ATRIBUICOES.md #5): transferência entre
    unidades não está na lista de atribuições dele — só na do Administrador
    Local (#4)."""
    conn = _conn()
    monkeypatch.setattr(routes, 'get_connection', lambda: conn)
    monkeypatch.setattr(routes, 'resolve_actor_user_id', lambda *a, **k: 3)
    monkeypatch.setattr(routes, 'authorize_action', _authorize_as_real_check(GESTOR_EPI))
    h = _FakeHandler()
    with pytest.raises(PermissionError):
        routes.handle_post_employee_unit_movements(
            h, urlparse('/api/employee-unit-movements'), _payload(actor_user_id=3), None
        )


def test_route_requires_employees_transfer_not_employees_update():
    """A checagem de permissão da rota é `employees:transfer` — não
    `employees:update` (o que ela usava antes desta correção)."""
    actor_without_transfer = {'id': 9, 'role': 'buyer', 'company_id': 1, 'full_name': 'Comprador'}
    with pytest.raises(PermissionError):
        ensure_permission(actor_without_transfer, PERM_EMPLOYEES_TRANSFER)
    ensure_permission(ADMIN_LOCAL, PERM_EMPLOYEES_TRANSFER)  # não levanta
