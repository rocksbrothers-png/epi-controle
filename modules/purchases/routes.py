"""Rotas de compras: requisições, ordens de compra e fornecedores."""

import re
from contextlib import closing
from urllib.parse import parse_qs

from core.auth import ensure_resource_company
from core.database import get_connection
from core.permissions import (
    PERM_FINANCE_VIEW,
    PERM_PO_VIEW,
    PERM_PURCHASE_REQUESTS_VIEW,
    PERM_PURCHASE_REQUESTS_UPDATE,
    PERM_PURCHASE_REQUESTS_CREATE,
    PERM_UNIT_LINKS_MANAGE,
)
from core.repository import actor_operational_unit_id, authorize_action
from core.security import resolve_actor_user_id
from epi_backend.db import row_to_dict
from epi_backend.http_utils import require_fields, send_json
from modules.purchases.service import (
    actor_company_id_or_query,
    apply_purchase_request_workflow_action,
    ensure_purchase_request_action_scope,
    fetch_purchase_demands,
    fetch_purchase_function_links,
    get_actor_purchase_unit_scope,
)


# ── GET ───────────────────────────────────────────────────────────────────────

def handle_get_purchase_demands(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed), PERM_PURCHASE_REQUESTS_VIEW)
        query = parse_qs(parsed.query)
        if actor.get('role') == 'master_admin':
            requested_company = str(query.get('company_id', [''])[0] or '').strip()
            company_id = int(requested_company) if requested_company else None
        else:
            company_id = actor_company_id_or_query(connection, actor, query)
        scope_unit_id = actor_operational_unit_id(connection, actor)
        purchase_scope_units = get_actor_purchase_unit_scope(connection, actor)
        if not scope_unit_id and purchase_scope_units:
            all_demands, seen = [], set()
            for uid in purchase_scope_units:
                for d in fetch_purchase_demands(connection, company_id, uid):
                    key = (d.get('demand_type'), d.get('id') or f"{d.get('unit_id')}/{d.get('epi_id')}")
                    if key not in seen:
                        seen.add(key)
                        all_demands.append(d)
            return send_json(handler, 200, {'items': all_demands})
        demands = fetch_purchase_demands(connection, company_id, scope_unit_id)
        return send_json(handler, 200, {'items': demands})


def handle_get_purchase_requests(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed), PERM_PURCHASE_REQUESTS_VIEW)
        query = parse_qs(parsed.query)
        company_id = actor_company_id_or_query(connection, actor, query)
        scope_unit_id = actor_operational_unit_id(connection, actor)
        purchase_scope_units = get_actor_purchase_unit_scope(connection, actor)
        status_filter = str(query.get('status', [''])[0] or '').strip()
        clauses, params = ['pr.company_id = %s'], [company_id]
        if scope_unit_id:
            clauses.append('pr.unit_id = %s')
            params.append(int(scope_unit_id))
        elif purchase_scope_units:
            placeholders = ','.join(['%s'] * len(purchase_scope_units))
            clauses.append(f'pr.unit_id IN ({placeholders})')
            params.extend(purchase_scope_units)
        if status_filter:
            clauses.append('pr.status = %s')
            params.append(status_filter)
        where_sql = f"WHERE {' AND '.join(clauses)}"
        rows = connection.execute(
            f'SELECT pr.*, u.name AS unit_name, '
            f'(SELECT COUNT(*) FROM purchase_request_items pri WHERE pri.purchase_request_id = pr.id) AS items_count '
            f'FROM purchase_requests pr JOIN units u ON u.id = pr.unit_id {where_sql} ORDER BY pr.created_at DESC',
            tuple(params),
        ).fetchall()
        return send_json(handler, 200, {'items': [row_to_dict(r) for r in rows]})


def handle_get_purchase_request_detail(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed), PERM_PURCHASE_REQUESTS_VIEW)
        pr_id = int(match.group(1))
        pr = connection.execute(
            'SELECT pr.*, u.name AS unit_name FROM purchase_requests pr JOIN units u ON u.id = pr.unit_id WHERE pr.id = %s',
            (pr_id,),
        ).fetchone()
        if not pr:
            return send_json(handler, 404, {'error': 'Requisição não encontrada.'})
        ensure_resource_company(actor, pr, 'Requisição')
        ensure_purchase_request_action_scope(
            connection, actor, row_to_dict(pr), actor_operational_unit_id=actor_operational_unit_id
        )
        items = connection.execute(
            'SELECT pri.*, e.name AS epi_display_name, e.ca AS epi_ca, u.name AS unit_name '
            'FROM purchase_request_items pri '
            'JOIN epis e ON e.id = pri.epi_id '
            'JOIN units u ON u.id = pri.unit_id '
            'WHERE pri.purchase_request_id = %s ORDER BY pri.id',
            (pr_id,),
        ).fetchall()
        events = connection.execute(
            'SELECT * FROM purchase_events WHERE entity_type = %s AND entity_id = %s ORDER BY created_at DESC, id DESC',
            ('purchase_request', pr_id),
        ).fetchall()
        return send_json(handler, 200, {
            'item': row_to_dict(pr),
            'items': [row_to_dict(i) for i in items],
            'events': [row_to_dict(e) for e in events],
        })


def handle_get_purchase_orders(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed), PERM_PO_VIEW)
        query = parse_qs(parsed.query)
        company_id = actor_company_id_or_query(connection, actor, query)
        scope_unit_id = actor_operational_unit_id(connection, actor)
        purchase_scope_units = get_actor_purchase_unit_scope(connection, actor)
        status_filter = str(query.get('status', [''])[0] or '').strip()
        clauses, params = ['po.company_id = %s'], [company_id]
        if scope_unit_id:
            clauses.append('po.unit_id = %s')
            params.append(int(scope_unit_id))
        elif purchase_scope_units:
            placeholders = ','.join(['%s'] * len(purchase_scope_units))
            clauses.append(f'po.unit_id IN ({placeholders})')
            params.extend(purchase_scope_units)
        if status_filter:
            clauses.append('po.status = %s')
            params.append(status_filter)
        where_sql = f"WHERE {' AND '.join(clauses)}"
        rows = connection.execute(
            f'SELECT po.*, u.name AS unit_name, '
            f'(SELECT COUNT(*) FROM purchase_order_items poi WHERE poi.purchase_order_id = po.id) AS items_count '
            f'FROM purchase_orders po JOIN units u ON u.id = po.unit_id {where_sql} ORDER BY po.created_at DESC',
            tuple(params),
        ).fetchall()
        return send_json(handler, 200, {'items': [row_to_dict(r) for r in rows]})


def handle_get_purchase_order_detail(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed), PERM_PO_VIEW)
        po_id = int(match.group(1))
        po = connection.execute(
            'SELECT po.*, u.name AS unit_name FROM purchase_orders po JOIN units u ON u.id = po.unit_id WHERE po.id = %s',
            (po_id,),
        ).fetchone()
        if not po:
            return send_json(handler, 404, {'error': 'PO não encontrada.'})
        ensure_resource_company(actor, po, 'PO')
        items = connection.execute(
            'SELECT poi.* FROM purchase_order_items poi WHERE poi.purchase_order_id = %s', (po_id,)
        ).fetchall()
        files = connection.execute(
            'SELECT id, file_name, file_type, uploaded_by_name, created_at '
            'FROM purchase_order_files WHERE purchase_order_id = %s',
            (po_id,),
        ).fetchall()
        events = connection.execute(
            'SELECT * FROM purchase_events WHERE entity_type = %s AND entity_id = %s ORDER BY created_at DESC',
            ('purchase_order', po_id),
        ).fetchall()
        return send_json(handler, 200, {
            'item': row_to_dict(po),
            'items': [row_to_dict(i) for i in items],
            'files': [row_to_dict(f) for f in files],
            'events': [row_to_dict(e) for e in events],
        })


def handle_get_purchase_events(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed), PERM_FINANCE_VIEW)
        query = parse_qs(parsed.query)
        company_id = actor_company_id_or_query(connection, actor, query)
        entity_type = str(query.get('entity_type', [''])[0] or '').strip()
        entity_id = str(query.get('entity_id', [''])[0] or '').strip()
        clauses, params = ['company_id = %s'], [company_id]
        if entity_type:
            clauses.append('entity_type = %s')
            params.append(entity_type)
        if entity_id:
            clauses.append('entity_id = %s')
            params.append(int(entity_id))
        where_sql = f"WHERE {' AND '.join(clauses)}"
        rows = connection.execute(
            f'SELECT * FROM purchase_events {where_sql} ORDER BY created_at DESC LIMIT 200',
            tuple(params),
        ).fetchall()
        return send_json(handler, 200, {'items': [row_to_dict(r) for r in rows]})


def handle_get_purchase_functions(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        query = parse_qs(parsed.query)
        actor_id = resolve_actor_user_id(handler, parsed)
        try:
            actor = authorize_action(connection, actor_id, PERM_UNIT_LINKS_MANAGE)
        except PermissionError:
            actor = authorize_action(connection, actor_id, PERM_PURCHASE_REQUESTS_VIEW)
        company_id = actor_company_id_or_query(connection, actor, query)
        if actor.get('role') != 'master_admin' and int(actor['company_id']) != company_id:
            raise PermissionError('Empresa fora do escopo do usuário.')
        return send_json(handler, 200, {'items': fetch_purchase_function_links(connection, company_id)})


# ── POST ──────────────────────────────────────────────────────────────────────

def handle_post_purchase_request_workflow(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        require_fields(payload, ['actor_user_id', 'action'])
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed, payload), PERM_PURCHASE_REQUESTS_VIEW)
        pr_id = int(match.group(1))
        ip = str(getattr(handler, 'client_address', ('',))[0] or '')
        result = apply_purchase_request_workflow_action(
            connection, actor, pr_id, payload, ip,
            actor_operational_unit_id=actor_operational_unit_id,
        )
        connection.commit()
        return send_json(handler, 200, result)


# ── Registro ──────────────────────────────────────────────────────────────────

def register_routes(router):
    # GET
    router.register('GET', '/api/purchase-demands',                          handle_get_purchase_demands)
    router.register('GET', '/api/purchase-requests',                         handle_get_purchase_requests)
    router.register('GET', r'^/api/purchase-requests/(\d+)$',                handle_get_purchase_request_detail, regex=True)
    router.register('GET', '/api/purchase-orders',                           handle_get_purchase_orders)
    router.register('GET', r'^/api/purchase-orders/(\d+)$',                  handle_get_purchase_order_detail, regex=True)
    router.register('GET', '/api/purchase-events',                           handle_get_purchase_events)
    router.register('GET', '/api/purchase-functions',                        handle_get_purchase_functions)
    # POST
    router.register('POST', r'^/api/purchase-requests/(\d+)/workflow$',      handle_post_purchase_request_workflow, regex=True)
