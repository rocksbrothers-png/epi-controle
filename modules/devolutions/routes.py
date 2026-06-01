"""Rotas de devoluções de EPIs."""

from contextlib import closing
from urllib.parse import parse_qs

from core.database import get_connection
from core.repository import authorize_action
from core.security import resolve_actor_user_id
from epi_backend.http_utils import require_fields, send_json
from modules.settings.service import canary_evaluate_visibility_dataset
from modules.devolutions.service import (
    fetch_devolutions,
    fetch_open_deliveries_for_devolution,
)


def _get_server():
    import server_postgres as _sp
    return _sp


# ── GET ───────────────────────────────────────────────────────────────────────

def handle_get_devolutions_open_deliveries(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed), 'deliveries:view')
        query = parse_qs(parsed.query)
        employee_id = str(query.get('employee_id', [''])[0] or '').strip()
        epi_id = str(query.get('epi_id', [''])[0] or '').strip()
        unit_id = str(query.get('unit_id', [''])[0] or '').strip()
        if not employee_id or not epi_id:
            raise ValueError('Parâmetros employee_id e epi_id são obrigatórios.')
        items = fetch_open_deliveries_for_devolution(
            connection, actor, int(employee_id), int(epi_id), unit_id=unit_id or None
        )
        return send_json(handler, 200, {'items': items, 'total_open': len(items)})


def handle_get_devolutions(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed), 'stock:view')
        q = parse_qs(parsed.query)
        filters = {k: q[k][0] for k in ('employee_id', 'epi_id', 'delivery_id') if q.get(k)}
        items = fetch_devolutions(connection, actor, filters)
        items = canary_evaluate_visibility_dataset(
            connection, actor, endpoint_name='/api/devolutions', dataset_name='devolutions', legacy_items=items
        )
        return send_json(handler, 200, {'items': items})


# ── POST ──────────────────────────────────────────────────────────────────────

def handle_post_devolutions(handler, parsed, payload, match):
    require_fields(payload, ['actor_user_id', 'delivery_id', 'returned_date', 'condition', 'destination'])
    if not str(payload.get('signature_data') or '').strip():
        raise ValueError('Assinatura digital obrigatória para registrar devolução.')
    sp = _get_server()
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed, payload), 'deliveries:create')
        enriched_payload = dict(payload)
        enriched_payload['signature_ip'] = str(getattr(handler, 'client_address', ('',))[0] or '')
        devolution_id = sp.register_epi_devolution(connection, enriched_payload, actor)
        return send_json(handler, 201, {'ok': True, 'id': devolution_id})


# ── Registro ──────────────────────────────────────────────────────────────────

def register_routes(router):
    router.register('GET',  '/api/devolutions/open-deliveries', handle_get_devolutions_open_deliveries)
    router.register('GET',  '/api/devolutions',                 handle_get_devolutions)
    router.register('POST', '/api/devolutions',                 handle_post_devolutions)
