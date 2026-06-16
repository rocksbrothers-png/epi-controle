"""Rotas de entregas."""

from contextlib import closing
from urllib.parse import parse_qs

from core.auth import ensure_resource_company
from core.database import get_connection
from core.permissions import PERM_DELIVERIES_VIEW
from core.repository import (
    authorize_action,
    get_employee_by_id,
    get_employee_current_unit,
    get_epi_by_id,
)
from modules.employees.service import actor_operational_unit_id
from core.security import resolve_actor_user_id
from epi_backend.http_utils import require_fields, send_json
from modules.deliveries.service import create_delivery_service, fetch_deliveries
from modules.ficha.service import ensure_ficha_for_delivery
from modules.stock.service import get_unit_stock, upsert_unit_stock


# ── GET ───────────────────────────────────────────────────────────────────────

def handle_get_deliveries(handler, parsed, payload, match):
    """Lista entregas escopada por empresa/unidade operacional (mais recentes 1º)."""
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed), PERM_DELIVERIES_VIEW)
        scope_unit_id = actor_operational_unit_id(connection, actor)
        where, params = '', ()
        if scope_unit_id:
            where, params = 'WHERE deliveries.unit_id = ?', (int(scope_unit_id),)
        items = fetch_deliveries(connection, actor, where, params)
        limit_raw = str(parse_qs(parsed.query).get('limit', [''])[0] or '').strip()
        if limit_raw.isdigit():
            items = items[:int(limit_raw)]
        # `deliveries` + `items` cobrem o que o cliente Flutter consome (tolerante).
        return send_json(handler, 200, {'deliveries': items, 'items': items})


# ── POST ──────────────────────────────────────────────────────────────────────

def handle_post_deliveries(handler, parsed, payload, match):
    require_fields(payload, [
        'actor_user_id',
        'company_id',
        'employee_id',
        'epi_id',
        'quantity',
        'sector',
        'role_name',
        'delivery_date',
        'next_replacement_date',
        'stock_item_id',
        'stock_qr_code',
    ])
    with closing(get_connection()) as connection:
        delivery_id = create_delivery_service(
            connection,
            payload,
            client_ip=str(getattr(handler, 'client_address', ('',))[0] or ''),
            authorize_action=authorize_action,
            resolve_actor_user_id=lambda: resolve_actor_user_id(handler, parsed, payload),
            get_employee_by_id=get_employee_by_id,
            get_epi_by_id=get_epi_by_id,
            ensure_resource_company=ensure_resource_company,
            get_employee_current_unit=get_employee_current_unit,
            actor_operational_unit_id=actor_operational_unit_id,
            get_unit_stock=get_unit_stock,
            upsert_unit_stock=upsert_unit_stock,
            ensure_ficha_for_delivery=ensure_ficha_for_delivery,
        )
        return send_json(handler, 201, {'ok': True, 'id': delivery_id})


# ── Registro ──────────────────────────────────────────────────────────────────

def register_routes(router):
    router.register('GET',  '/api/deliveries', handle_get_deliveries)
    router.register('POST', '/api/deliveries', handle_post_deliveries)
