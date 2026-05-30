"""Rotas de gestão de estoque de EPIs."""

from contextlib import closing

from core.database import get_connection
from core.repository import actor_operational_unit_id, authorize_action, get_unit_active_jv_name
from core.security import resolve_actor_user_id
from epi_backend.epi_scope import is_epi_visible_for_unit
from epi_backend.http_utils import send_json
from modules.stock.service import build_low_stock


# ── GET ───────────────────────────────────────────────────────────────────────

def handle_get_stock_low(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed), 'stock:view')
        result = build_low_stock(
            connection,
            actor,
            actor_operational_unit_id=actor_operational_unit_id,
            get_unit_active_jv_name=get_unit_active_jv_name,
            is_epi_visible_for_unit=is_epi_visible_for_unit,
        )
        return send_json(handler, 200, result)


# ── Registro ──────────────────────────────────────────────────────────────────

def register_routes(router):
    router.register('GET', '/api/stock/low', handle_get_stock_low)
