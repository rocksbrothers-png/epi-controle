"""Rotas de gestão de colaboradores."""

import re
from contextlib import closing
from datetime import datetime

from core.auth import ensure_resource_company
from core.database import get_connection
from core.permissions import PERM_EMPLOYEES_VIEW
from core.repository import authorize_action, get_employee_by_id, get_unit_by_id
from core.security import resolve_actor_user_id
from epi_backend.http_utils import require_fields, send_json
from modules.units.service import ensure_unit_operational
from modules.employees.service import (
    apply_current_unit_allocation,
    close_temporary_unit_movements,
    create_employee,
    create_employee_unit_movement,
    delete_employee,
    ensure_actor_employee_scope,
    fetch_employee_movements,
    fetch_employees,
    update_employee,
    update_employee_unit,
)

_EMPLOYEE_ID_RE = re.compile(r'^/api/employees/(\d+)$')


# ── GET ───────────────────────────────────────────────────────────────────────

def handle_get_employees(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed), PERM_EMPLOYEES_VIEW)
        return send_json(handler, 200, {'employees': fetch_employees(connection, actor)})


def handle_get_employee(handler, parsed, payload, match):
    employee_id = int(match.group(1))
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed), PERM_EMPLOYEES_VIEW)
        employee = get_employee_by_id(connection, employee_id)
        if not employee:
            return send_json(handler, 404, {'error': 'Colaborador não encontrado.'})
        ensure_actor_employee_scope(connection, actor, employee)
        base_unit = get_unit_by_id(connection, int(employee['unit_id'])) if employee.get('unit_id') else None
        employee['unit_name'] = base_unit['name'] if base_unit else None
        apply_current_unit_allocation(connection, [employee])
        return send_json(handler, 200, {'employee': employee})


def handle_get_employee_unit_movements(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed), PERM_EMPLOYEES_VIEW)
        return send_json(handler, 200, {'items': fetch_employee_movements(connection, actor)})


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
        delete_employee(connection, employee_id)
        connection.commit()
        return send_json(handler, 200, {'ok': True})


# ── POST /api/employee-unit-movements ────────────────────────────────────────

def handle_post_employee_unit_movements(handler, parsed, payload, match):
    require_fields(payload, ['actor_user_id', 'employee_id', 'target_unit_id', 'movement_type', 'start_date'])
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed, payload), 'employees:update')
        employee = get_employee_by_id(connection, int(payload['employee_id']))
        if not employee:
            raise ValueError('Colaborador não encontrado.')
        ensure_resource_company(actor, employee, 'Colaborador')
        target_unit = get_unit_by_id(connection, int(payload['target_unit_id']))
        if not target_unit:
            raise ValueError('Unidade de destino não encontrada.')
        ensure_resource_company(actor, target_unit, 'Unidade de destino')
        ensure_unit_operational(connection, target_unit['id'], 'movimentações de colaboradores')
        if int(target_unit['id']) == int(employee['unit_id']):
            raise ValueError('A unidade de destino deve ser diferente da unidade atual do colaborador.')
        movement_type = str(payload.get('movement_type', '')).strip().lower()
        if movement_type not in ('temporary', 'definitive'):
            raise ValueError("Tipo de movimentação inválido. Use 'temporary' ou 'definitive'.")
        start_date = str(payload.get('start_date', '')).strip()
        end_date = str(payload.get('end_date', '')).strip()
        datetime.strptime(start_date, '%Y-%m-%d')
        if end_date:
            datetime.strptime(end_date, '%Y-%m-%d')
            if end_date < start_date:
                raise ValueError('Data final não pode ser menor que a data inicial.')
        if movement_type == 'temporary':
            close_temporary_unit_movements(connection, employee['id'], start_date)
        if movement_type == 'definitive' and not end_date:
            end_date = start_date
        source_unit_id = int(employee['unit_id'])
        create_employee_unit_movement(
            connection,
            employee['id'],
            employee['company_id'],
            source_unit_id,
            int(target_unit['id']),
            movement_type,
            start_date,
            end_date,
            str(payload.get('notes', '')).strip(),
            actor['id'],
            actor['full_name'],
            datetime.now().isoformat(timespec='seconds'),
        )
        if movement_type == 'definitive':
            update_employee_unit(connection, employee['id'], int(target_unit['id']))
            close_temporary_unit_movements(connection, employee['id'], start_date)
        connection.commit()
        return send_json(handler, 200, {'ok': True})


# ── Registro ──────────────────────────────────────────────────────────────────

def register_routes(router):
    router.register('GET',    '/api/employees',                   handle_get_employees)
    router.register('GET',    '/api/employee-unit-movements',     handle_get_employee_unit_movements)
    router.register('GET',    r'^/api/employees/(\d+)$',           handle_get_employee, regex=True)
    router.register('POST',   '/api/employees',                   handle_post_employees)
    router.register('POST',   '/api/employee-unit-movements',     handle_post_employee_unit_movements)
    router.register('PUT',    r'/api/employees/(\d+)',             handle_put_employee,    regex=True)
    router.register('DELETE', r'/api/employees/(\d+)',             handle_delete_employee, regex=True)
