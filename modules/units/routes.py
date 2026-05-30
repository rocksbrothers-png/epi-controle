"""Rotas de unidades operacionais."""
import re
from contextlib import closing
from datetime import datetime, timezone

from core.auth import ensure_resource_company, require_structural_admin
from core.database import get_connection
from core.repository import authorize_action, get_unit_active_jv_name, get_unit_by_id
from core.security import resolve_actor_user_id
from epi_backend.http_utils import require_fields, send_json
from modules.units.service import delete_unit_dependencies, normalize_unit_type

_UNIT_ID_RE = re.compile(r'^/api/units/(\d+)$')


def handle_post_units(handler, parsed, payload, match):
    require_fields(payload, ['actor_user_id', 'company_id', 'name', 'unit_type', 'city'])
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed, payload), 'units:create', int(payload['company_id']))
        require_structural_admin(actor)
        unit_type = normalize_unit_type(payload.get('unit_type'))
        cursor = connection.execute(
            'INSERT INTO units (company_id, name, unit_type, city, notes) VALUES (?, ?, ?, ?, ?)',
            (payload['company_id'], payload['name'], unit_type, payload['city'], payload.get('notes', ''))
        )
        connection.commit()
        return send_json(handler, 201, {'ok': True, 'id': cursor.lastrowid})


def handle_put_unit(handler, parsed, payload, match):
    unit_id = int(match.group(1))
    require_fields(payload, ['actor_user_id', 'company_id', 'name', 'unit_type', 'city'])
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed, payload), 'units:update', int(payload['company_id']))
        require_structural_admin(actor)
        current = get_unit_by_id(connection, unit_id)
        ensure_resource_company(actor, current, 'Unidade')
        unit_type = normalize_unit_type(payload.get('unit_type'))
        connection.execute(
            'UPDATE units SET company_id = ?, name = ?, unit_type = ?, city = ?, notes = ? WHERE id = ?',
            (payload['company_id'], payload['name'], unit_type, payload['city'], payload.get('notes', ''), unit_id)
        )
        connection.commit()
        return send_json(handler, 200, {'ok': True})


def handle_delete_unit(handler, parsed, payload, match):
    unit_id = int(match.group(1))
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed), 'units:delete')
        require_structural_admin(actor)
        current = get_unit_by_id(connection, unit_id)
        if not current:
            raise ValueError('Unidade não encontrada.')
        ensure_resource_company(actor, current, 'Unidade')
        delete_unit_dependencies(connection, unit_id)
        connection.execute('DELETE FROM units WHERE id = ?', (unit_id,))
        connection.commit()
        return send_json(handler, 200, {'ok': True})


# ── POST /api/unit-jv/start ───────────────────────────────────────────────────

def handle_post_unit_jv_start(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed), 'units:edit')
        unit_id = int(payload.get('unit_id') or 0)
        jv_name = str(payload.get('joint_venture_name') or '').strip()
        if not unit_id or not jv_name:
            raise ValueError('unit_id e joint_venture_name são obrigatórios.')
        unit = get_unit_by_id(connection, unit_id)
        ensure_resource_company(actor, unit, 'Unidade')
        existing = get_unit_active_jv_name(connection, unit_id)
        if existing:
            raise ValueError(f'Unidade já está em JV ativa: "{existing}". Encerre antes de iniciar outra.')
        connection.execute(
            'INSERT INTO unit_joint_venture_periods (company_id, unit_id, joint_venture_name, started_at, created_by) '
            'VALUES (?, ?, ?, ?, ?)',
            (int(unit['company_id']), unit_id, jv_name, datetime.now(timezone.utc).isoformat(), str(actor.get('id') or ''))
        )
        connection.commit()
        return send_json(handler, 201, {'unit_id': unit_id, 'active_jv_name': jv_name, 'started': True})


# ── POST /api/unit-jv/end ─────────────────────────────────────────────────────

def handle_post_unit_jv_end(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed), 'units:edit')
        unit_id = int(payload.get('unit_id') or 0)
        if not unit_id:
            raise ValueError('unit_id é obrigatório.')
        unit = get_unit_by_id(connection, unit_id)
        ensure_resource_company(actor, unit, 'Unidade')
        existing = get_unit_active_jv_name(connection, unit_id)
        if not existing:
            raise ValueError('Unidade não possui JV ativa para encerrar.')
        connection.execute(
            'UPDATE unit_joint_venture_periods SET ended_at = ? '
            'WHERE unit_id = ? AND ended_at IS NULL',
            (datetime.now(timezone.utc).isoformat(), unit_id)
        )
        connection.commit()
        return send_json(handler, 200, {'unit_id': unit_id, 'ended_jv_name': existing, 'ended': True})


def register_routes(router):
    router.register('POST',   '/api/units',          handle_post_units)
    router.register('POST',   '/api/unit-jv/start',  handle_post_unit_jv_start)
    router.register('POST',   '/api/unit-jv/end',    handle_post_unit_jv_end)
    router.register('PUT',    r'/api/units/(\d+)',   handle_put_unit,    regex=True)
    router.register('DELETE', r'/api/units/(\d+)',   handle_delete_unit, regex=True)
