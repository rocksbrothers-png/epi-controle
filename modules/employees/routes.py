"""Rotas de gestão de colaboradores."""

import re
from contextlib import closing
from datetime import datetime

from core.auth import ensure_resource_company
from core.database import get_connection
from core.permissions import PERM_EMPLOYEES_LEGAL_ENTITY_TRANSFER, PERM_EMPLOYEES_VIEW
from core.repository import authorize_action, get_employee_by_id, get_unit_by_id
from core.security import resolve_actor_user_id
from epi_backend.http_utils import require_fields, send_json, structured_log
from modules.units.service import ensure_unit_operational
from modules.employees.service import (
    apply_current_unit_allocation,
    close_temporary_unit_movements,
    create_employee,
    create_employee_unit_movement,
    ensure_actor_employee_scope,
    ensure_employee_operational,
    fetch_archived_employees,
    fetch_employee_movements,
    fetch_employee_legal_entity_movements,
    fetch_employees,
    get_employee_lifecycle,
    purge_employee_history,
    summarize_employee_history,
    update_employee,
    transfer_employee_legal_entity,
    update_employee_unit,
)

from core import archival


def _client_ip(handler):
    return str(getattr(handler, 'client_address', ('',))[0] or '')


def _require_deletion_admin(actor):
    if actor.get('role') not in ('master_admin', 'general_admin'):
        raise PermissionError(
            'Apenas Administrador Geral ou Administrador Master podem gerenciar a exclusão definitiva.'
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


# ── Arquivamento (Soft Delete) — mesma política das Unidades ─────────────────

def _load_employee_for_lifecycle(connection, handler, parsed, payload, match, permission):
    actor = authorize_action(connection, resolve_actor_user_id(handler, parsed, payload), permission)
    employee = get_employee_lifecycle(connection, int(match.group(1)))
    if not employee:
        raise ValueError('Colaborador não encontrado.')
    ensure_resource_company(actor, employee, 'Colaborador')
    return actor, employee


_EMPLOYEE_ARCHIVAL = dict(entity_label='Colaborador', audit_prefix='employee')


def handle_delete_employee(handler, parsed, payload, match):
    """Política de retenção: DELETE não remove — arquiva (soft delete)."""
    from urllib.parse import parse_qs
    with closing(get_connection()) as connection:
        actor, employee = _load_employee_for_lifecycle(connection, handler, parsed, payload, match, 'employees:delete')
        reason = str(parse_qs(parsed.query).get('reason', [''])[0] or '')
        result = archival.archive_record(
            connection, 'employees', employee, actor,
            record_label=employee['name'], reason=reason, ip=_client_ip(handler),
            **_EMPLOYEE_ARCHIVAL,
        )
        connection.commit()
        return send_json(handler, 200, {'ok': True, 'archived': True, **result})


def handle_post_employee_archive(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        actor, employee = _load_employee_for_lifecycle(connection, handler, parsed, payload, match, 'employees:delete')
        result = archival.archive_record(
            connection, 'employees', employee, actor,
            record_label=employee['name'],
            reason=str((payload or {}).get('reason') or ''), ip=_client_ip(handler),
            **_EMPLOYEE_ARCHIVAL,
        )
        connection.commit()
        return send_json(handler, 200, {'ok': True, 'archived': True, **result})


def handle_post_employee_restore(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        actor, employee = _load_employee_for_lifecycle(connection, handler, parsed, payload, match, 'employees:update')
        archival.restore_record(
            connection, 'employees', employee, actor,
            record_label=employee['name'], ip=_client_ip(handler),
            **_EMPLOYEE_ARCHIVAL,
        )
        connection.commit()
        return send_json(handler, 200, {'ok': True, 'status': 'active'})


def handle_get_archived_employees(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed), PERM_EMPLOYEES_VIEW)
        return send_json(handler, 200, {'employees': fetch_archived_employees(connection, actor)})


def handle_get_employee_deletion_summary(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        actor, employee = _load_employee_for_lifecycle(connection, handler, parsed, payload, match, PERM_EMPLOYEES_VIEW)
        return send_json(handler, 200, {
            'employee': {
                'id': employee['id'],
                'name': employee['name'],
                'status': employee.get('status'),
                'archived_at': employee.get('archived_at'),
                'retention_until': employee.get('retention_until'),
                'legal_hold': int(employee.get('legal_hold') or 0),
            },
            'records': summarize_employee_history(connection, int(employee['id'])),
        })


def handle_post_employee_purge_request(handler, parsed, payload, match):
    require_fields(payload, ['actor_user_id'])
    with closing(get_connection()) as connection:
        actor, employee = _load_employee_for_lifecycle(connection, handler, parsed, payload, match, 'employees:delete')
        _require_deletion_admin(actor)
        summary = archival.request_purge(
            connection, 'employees', employee, actor,
            record_label=employee['name'],
            summary=summarize_employee_history(connection, int(employee['id'])),
            ip=_client_ip(handler), **_EMPLOYEE_ARCHIVAL,
        )
        connection.commit()
        return send_json(handler, 200, {
            'ok': True,
            'status': 'pending_deletion',
            'records': summary,
            'next_step': 'Confirme a exclusão definitiva com justificativa e o nome exato do colaborador.',
        })


def handle_post_employee_purge_cancel(handler, parsed, payload, match):
    require_fields(payload, ['actor_user_id'])
    with closing(get_connection()) as connection:
        actor, employee = _load_employee_for_lifecycle(connection, handler, parsed, payload, match, 'employees:delete')
        _require_deletion_admin(actor)
        archival.cancel_purge(
            connection, 'employees', employee, actor,
            record_label=employee['name'], ip=_client_ip(handler), **_EMPLOYEE_ARCHIVAL,
        )
        connection.commit()
        return send_json(handler, 200, {'ok': True, 'status': 'archived'})


def handle_post_employee_purge_confirm(handler, parsed, payload, match):
    require_fields(payload, ['actor_user_id', 'justification', 'confirm_name'])
    with closing(get_connection()) as connection:
        actor, employee = _load_employee_for_lifecycle(connection, handler, parsed, payload, match, 'employees:delete')
        _require_deletion_admin(actor)
        summary = archival.confirm_purge(
            connection, 'employees', employee, actor,
            record_label=employee['name'],
            justification=payload.get('justification'),
            confirm_name=payload.get('confirm_name'),
            summary=summarize_employee_history(connection, int(employee['id'])),
            purge_history=purge_employee_history,
            ip=_client_ip(handler), **_EMPLOYEE_ARCHIVAL,
        )
        connection.commit()
        return send_json(handler, 200, {'ok': True, 'status': 'deleted', 'records_removed': summary})


# ── POST /api/employee-unit-movements ────────────────────────────────────────

def handle_post_employee_unit_movements(handler, parsed, payload, match):
    require_fields(payload, ['actor_user_id', 'employee_id', 'target_unit_id', 'movement_type', 'start_date'])
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed, payload), 'employees:update')
        employee = get_employee_by_id(connection, int(payload['employee_id']))
        if not employee:
            raise ValueError('Colaborador não encontrado.')
        ensure_resource_company(actor, employee, 'Colaborador')
        ensure_employee_operational(connection, employee['id'], 'movimentações de colaboradores')
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

def handle_get_employee_legal_entity_movements(handler, parsed, payload, match):
    """Histórico de vínculo jurídico (CNPJ) do colaborador."""
    employee_id = int(match.group(1))
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed), PERM_EMPLOYEES_VIEW)
        employee = get_employee_by_id(connection, employee_id)
        if not employee:
            return send_json(handler, 404, {'error': 'Colaborador não encontrado.'})
        ensure_resource_company(actor, employee, 'Colaborador')
        return send_json(handler, 200, {
            'movements': fetch_employee_legal_entity_movements(connection, employee_id),
        })


def handle_post_employee_legal_entity_transfer(handler, parsed, payload, match):
    """Processo administrativo de mudança de CNPJ do colaborador.

    O CNPJ é o vínculo jurídico do contrato de trabalho: imutável na edição
    comum. Esta rota é a única via de alteração e exige justificativa, gerando
    histórico e auditoria completos.
    """
    employee_id = int(match.group(1))
    require_fields(payload, ['actor_user_id', 'legal_entity_id', 'reason'])
    with closing(get_connection()) as connection:
        actor = authorize_action(
            connection, resolve_actor_user_id(handler, parsed, payload),
            PERM_EMPLOYEES_LEGAL_ENTITY_TRANSFER,
        )
        employee = get_employee_by_id(connection, employee_id)
        if not employee:
            return send_json(handler, 404, {'error': 'Colaborador não encontrado.'})
        ensure_resource_company(actor, employee, 'Colaborador')
        result = transfer_employee_legal_entity(
            connection, employee_id, int(payload['legal_entity_id']),
            actor=actor, reason=payload.get('reason'),
            effective_date=payload.get('effective_date', ''),
        )
        structured_log('info', 'employee.legal_entity_transferred',
                       employee_id=employee_id, actor_user_id=actor['id'],
                       target_legal_entity_id=result['target_legal_entity_id'])
        return send_json(handler, 200, {'ok': True, **result})


def register_routes(router):
    router.register('GET',  r'^/api/employees/(\d+)/legal-entity-movements$',
                    handle_get_employee_legal_entity_movements, regex=True)
    router.register('POST', r'^/api/employees/(\d+)/legal-entity-transfer$',
                    handle_post_employee_legal_entity_transfer, regex=True)
    router.register('GET',    '/api/employees',                   handle_get_employees)
    router.register('GET',    '/api/employees/archived',          handle_get_archived_employees)
    router.register('GET',    '/api/employee-unit-movements',     handle_get_employee_unit_movements)
    router.register('GET',    r'^/api/employees/(\d+)$',           handle_get_employee, regex=True)
    router.register('GET',    r'/api/employees/(\d+)/deletion-summary$', handle_get_employee_deletion_summary, regex=True)
    router.register('POST',   '/api/employees',                   handle_post_employees)
    router.register('POST',   r'/api/employees/(\d+)/archive$',   handle_post_employee_archive,       regex=True)
    router.register('POST',   r'/api/employees/(\d+)/restore$',   handle_post_employee_restore,       regex=True)
    router.register('POST',   r'/api/employees/(\d+)/purge-request$', handle_post_employee_purge_request, regex=True)
    router.register('POST',   r'/api/employees/(\d+)/purge-cancel$',  handle_post_employee_purge_cancel,  regex=True)
    router.register('POST',   r'/api/employees/(\d+)/purge-confirm$', handle_post_employee_purge_confirm, regex=True)
    router.register('POST',   '/api/employee-unit-movements',     handle_post_employee_unit_movements)
    router.register('PUT',    r'/api/employees/(\d+)',             handle_put_employee,    regex=True)
    router.register('DELETE', r'/api/employees/(\d+)',             handle_delete_employee, regex=True)
