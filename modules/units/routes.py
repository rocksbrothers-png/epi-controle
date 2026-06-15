"""Rotas de unidades operacionais."""
import re
from contextlib import closing
from datetime import datetime, timezone
from urllib.parse import parse_qs

from core.auth import ensure_resource_company, require_structural_admin
from core.database import get_connection
from core.repository import authorize_action, get_unit_active_jv_name, get_unit_by_id
from core.security import resolve_actor_user_id
from epi_backend.http_utils import require_fields, send_json
from modules.units.service import (
    create_unit,
    delete_unit,
    delete_unit_dependencies,
    end_unit_jv,
    fetch_units,
    normalize_unit_type,
    start_unit_jv,
    update_unit,
)

_UNIT_ID_RE = re.compile(r'^/api/units/(\d+)$')


def handle_get_units(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed), 'units:view')
        units = fetch_units(connection, actor)
        return send_json(handler, 200, {'units': units})


def handle_get_unit(handler, parsed, payload, match):
    unit_id = int(match.group(1))
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed), 'units:view')
        unit = get_unit_by_id(connection, unit_id)
        ensure_resource_company(actor, unit, 'Unidade')
        return send_json(handler, 200, {'unit': unit})


def handle_post_units(handler, parsed, payload, match):
    require_fields(payload, ['actor_user_id', 'company_id', 'name', 'unit_type', 'city'])
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed, payload), 'units:create', int(payload['company_id']))
        require_structural_admin(actor)
        unit_type = normalize_unit_type(payload.get('unit_type'))
        unit_id = create_unit(connection, payload['company_id'], payload['name'], unit_type, payload['city'], payload.get('notes', ''))
        connection.commit()
        return send_json(handler, 201, {'ok': True, 'id': unit_id})


def handle_put_unit(handler, parsed, payload, match):
    unit_id = int(match.group(1))
    require_fields(payload, ['actor_user_id', 'company_id', 'name', 'unit_type', 'city'])
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed, payload), 'units:update', int(payload['company_id']))
        require_structural_admin(actor)
        current = get_unit_by_id(connection, unit_id)
        ensure_resource_company(actor, current, 'Unidade')
        unit_type = normalize_unit_type(payload.get('unit_type'))
        update_unit(connection, unit_id, payload['company_id'], payload['name'], unit_type, payload['city'], payload.get('notes', ''))
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
        delete_unit(connection, unit_id)
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
        start_unit_jv(connection, unit['company_id'], unit_id, jv_name, datetime.now(timezone.utc).isoformat(), actor.get('id') or '')
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
        end_unit_jv(connection, unit_id, datetime.now(timezone.utc).isoformat())
        connection.commit()
        return send_json(handler, 200, {'unit_id': unit_id, 'ended_jv_name': existing, 'ended': True})


def handle_get_unit_jv_active(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed), 'units:view')
        query = parse_qs(parsed.query)
        unit_id = int(query.get('unit_id', ['0'])[0] or 0)
        if not unit_id:
            raise ValueError('unit_id é obrigatório.')
        unit = get_unit_by_id(connection, unit_id)
        ensure_resource_company(actor, unit, 'Unidade')
        name = get_unit_active_jv_name(connection, unit_id)
        return send_json(handler, 200, {'unit_id': unit_id, 'active_jv_name': name, 'in_jv': bool(name)})


def register_routes(router):
    router.register('GET',    '/api/unit-jv/active', handle_get_unit_jv_active)
    router.register('GET',    '/api/units',          handle_get_units)
    router.register('GET',    r'/api/units/(\d+)$',  handle_get_unit,    regex=True)
    router.register('POST',   '/api/units',          handle_post_units)
    router.register('POST',   '/api/unit-jv/start',  handle_post_unit_jv_start)
    router.register('POST',   '/api/unit-jv/end',    handle_post_unit_jv_end)
    router.register('PUT',    r'/api/units/(\d+)',   handle_put_unit,    regex=True)
    router.register('DELETE', r'/api/units/(\d+)',   handle_delete_unit, regex=True)
