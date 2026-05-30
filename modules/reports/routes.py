"""Rotas de relatórios."""

from contextlib import closing
from urllib.parse import parse_qs

from core.database import get_connection
from core.permissions import PERM_STOCK_VIEW
from core.repository import actor_operational_unit_id, authorize_action
from core.security import resolve_actor_user_id
from epi_backend.db import row_to_dict
from epi_backend.http_utils import send_json
from modules.purchases.service import get_actor_purchase_unit_scope


# ── GET ───────────────────────────────────────────────────────────────────────

def handle_get_report_requests(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed), PERM_STOCK_VIEW)
        company_id = int(actor['company_id'])
        scope_unit_id = actor_operational_unit_id(connection, actor)
        purchase_scope = get_actor_purchase_unit_scope(connection, actor)
        clauses = ['rr.company_id = %s']
        params = [company_id]
        if scope_unit_id:
            clauses.append('rr.unit_id = %s')
            params.append(int(scope_unit_id))
        elif purchase_scope:
            ph = ','.join(['%s'] * len(purchase_scope))
            clauses.append(f'rr.unit_id IN ({ph})')
            params.extend(purchase_scope)
        where = f"WHERE {' AND '.join(clauses)}"
        rows = connection.execute(
            f'SELECT rr.*, u.name AS unit_name FROM report_requests rr '
            f'LEFT JOIN units u ON u.id = rr.unit_id '
            f'{where} ORDER BY rr.created_at DESC LIMIT 100',
            tuple(params),
        ).fetchall()
        return send_json(handler, 200, {'items': [row_to_dict(r) for r in rows]})


# ── Registro ──────────────────────────────────────────────────────────────────

def register_routes(router):
    router.register('GET', '/api/report-requests', handle_get_report_requests)
