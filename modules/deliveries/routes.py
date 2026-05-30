"""Rotas de entregas."""

from contextlib import closing

from core.auth import ensure_resource_company
from core.database import get_connection
from core.repository import (
    actor_operational_unit_id,
    authorize_action,
    get_employee_by_id,
    get_employee_current_unit,
    get_epi_by_id,
)
from core.security import resolve_actor_user_id
from epi_backend.http_utils import require_fields, send_json
from modules.deliveries.service import create_delivery_service
from modules.ficha.service import ensure_ficha_for_delivery


def _get_server():
    import server_postgres as _sp
    return _sp


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
    sp = _get_server()
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
            get_unit_stock=sp.get_unit_stock,
            upsert_unit_stock=sp.upsert_unit_stock,
            ensure_ficha_for_delivery=ensure_ficha_for_delivery,
        )
        return send_json(handler, 201, {'ok': True, 'id': delivery_id})


# ── Registro ──────────────────────────────────────────────────────────────────

def register_routes(router):
    router.register('POST', '/api/deliveries', handle_post_deliveries)
