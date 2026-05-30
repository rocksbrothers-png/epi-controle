"""Rotas de gestão de colaboradores."""

import re
from contextlib import closing

from core.auth import ensure_resource_company
from core.database import get_connection
from core.repository import authorize_action, get_employee_by_id
from core.security import resolve_actor_user_id
from epi_backend.http_utils import require_fields, send_json
from modules.employees.service import create_employee, update_employee

_EMPLOYEE_ID_RE = re.compile(r'^/api/employees/(\d+)$')


# ── POST ──────────────────────────────────────────────────────────────────────

def handle_post_employees(handler, parsed, payload, match):
    require_fields(payload, ['actor_user_id', 'company_id', 'employee_id_code', 'cpf', 'name', 'sector', 'role_name', 'admission_date', 'schedule_type'])
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed, payload), 'employees:create', int(payload['company_id']))
        employee_id = create_employee(connection, payload, actor=actor)
        return send_json(handler, 201, {'ok': True, 'id': employee_id})


# ── PUT ───────────────────────────────────────────────────────────────────────

def handle_put_employee(handler, parsed, payload, match):
    employee_id = int(match.group(1))
    require_fields(payload, ['actor_user_id', 'company_id', 'unit_id', 'employee_id_code', 'cpf', 'name', 'sector', 'role_name', 'admission_date', 'schedule_type'])
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed, payload), 'employees:update', int(payload['company_id']))
        update_employee(connection, employee_id, payload, actor=actor)
        return send_json(handler, 200, {'ok': True})


# ── DELETE ────────────────────────────────────────────────────────────────────

def handle_delete_employee(handler, parsed, payload, match):
    employee_id = int(match.group(1))
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed), 'employees:delete')
        employee = get_employee_by_id(connection, employee_id)
        if not employee:
            raise ValueError('Colaborador não encontrado.')
        ensure_resource_company(actor, employee, 'Colaborador')
        connection.execute('DELETE FROM employees WHERE id = ?', (employee_id,))
        connection.commit()
        return send_json(handler, 200, {'ok': True})


# ── Registro ──────────────────────────────────────────────────────────────────

def register_routes(router):
    router.register('POST',   '/api/employees',          handle_post_employees)
    router.register('PUT',    r'/api/employees/(\d+)',   handle_put_employee,    regex=True)
    router.register('DELETE', r'/api/employees/(\d+)',   handle_delete_employee, regex=True)
