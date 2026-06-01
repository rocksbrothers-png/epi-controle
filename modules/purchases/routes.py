"""Rotas de compras: requisições, ordens de compra e fornecedores."""

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
    PERM_SUPPLIERS_MANAGE,
    PERM_UNIT_LINKS_MANAGE,
)
from core.repository import get_epi_by_id, get_unit_by_id, authorize_action
from modules.employees.service import actor_operational_unit_id
from core.security import resolve_actor_user_id
from datetime import datetime, timezone
from epi_backend.http_utils import require_fields, send_json

UTC = timezone.utc


def _get_server():
    import server_postgres as _sp
    return _sp


from modules.purchases.service import (
    actor_company_id_or_query,
    apply_purchase_request_workflow_action,
    bulk_update_epi_request_statuses,
    create_purchase_request,
    delete_purchase_function_link,
    delete_user_unit_link,
    ensure_purchase_request_action_scope,
    fetch_authorized_suppliers,
    fetch_epi_requests,
    fetch_purchase_demands,
    fetch_purchase_events,
    fetch_purchase_function_links,
    fetch_purchase_orders,
    fetch_purchase_requests,
    fetch_supplier_purchase_orders,
    fetch_user_unit_links,
    get_actor_purchase_unit_scope,
    get_company_purchase_config,
    get_purchase_order_detail,
    get_purchase_request_detail,
    require_purchase_function_admin,
    review_purchase_request_items,
    update_epi_request_status,
    update_feedback_status,
    update_purchase_request_status,
    upsert_authorized_supplier,
)


# ── GET ───────────────────────────────────────────────────────────────────────

def handle_get_epi_requests(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed), PERM_PURCHASE_REQUESTS_VIEW)
        query = parse_qs(parsed.query)
        company_filter = actor['company_id'] if actor['role'] != 'master_admin' else query.get('company_id', [''])[0]
        scope_unit_id = actor_operational_unit_id(connection, actor)
        purchase_scope = get_actor_purchase_unit_scope(connection, actor)
        items = fetch_epi_requests(connection, company_filter, scope_unit_id, purchase_scope)
        return send_json(handler, 200, {'items': items})


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
        items = fetch_purchase_requests(connection, company_id, scope_unit_id, purchase_scope_units, status_filter or None)
        return send_json(handler, 200, {'items': items})


def handle_get_purchase_request_detail(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed), PERM_PURCHASE_REQUESTS_VIEW)
        pr_id = int(match.group(1))
        pr, items, events = get_purchase_request_detail(connection, pr_id)
        if not pr:
            return send_json(handler, 404, {'error': 'Requisição não encontrada.'})
        ensure_resource_company(actor, pr, 'Requisição')
        ensure_purchase_request_action_scope(connection, actor, pr, actor_operational_unit_id=actor_operational_unit_id)
        return send_json(handler, 200, {'item': pr, 'items': items, 'events': events})


def handle_get_purchase_orders(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed), PERM_PO_VIEW)
        query = parse_qs(parsed.query)
        company_id = actor_company_id_or_query(connection, actor, query)
        scope_unit_id = actor_operational_unit_id(connection, actor)
        purchase_scope_units = get_actor_purchase_unit_scope(connection, actor)
        status_filter = str(query.get('status', [''])[0] or '').strip()
        items = fetch_purchase_orders(connection, company_id, scope_unit_id, purchase_scope_units, status_filter or None)
        return send_json(handler, 200, {'items': items})


def handle_get_purchase_order_detail(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed), PERM_PO_VIEW)
        po_id = int(match.group(1))
        po, items, files, events = get_purchase_order_detail(connection, po_id)
        if not po:
            return send_json(handler, 404, {'error': 'PO não encontrada.'})
        ensure_resource_company(actor, po, 'PO')
        return send_json(handler, 200, {'item': po, 'items': items, 'files': files, 'events': events})


def handle_get_purchase_events(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed), PERM_FINANCE_VIEW)
        query = parse_qs(parsed.query)
        company_id = actor_company_id_or_query(connection, actor, query)
        entity_type = str(query.get('entity_type', [''])[0] or '').strip() or None
        entity_id = str(query.get('entity_id', [''])[0] or '').strip() or None
        items = fetch_purchase_events(connection, company_id, entity_type, entity_id)
        return send_json(handler, 200, {'items': items})


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


def handle_post_purchase_requests(handler, parsed, payload, match):
    require_fields(payload, ['actor_user_id', 'unit_id', 'items'])
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed, payload), PERM_PURCHASE_REQUESTS_CREATE)
        unit_id = int(payload['unit_id'])
        unit = get_unit_by_id(connection, unit_id)
        if not unit:
            raise ValueError('Unidade não encontrada.')
        ensure_resource_company(actor, unit, 'Unidade')
        scope_unit_id = actor_operational_unit_id(connection, actor)
        if scope_unit_id and int(unit_id) != int(scope_unit_id):
            return send_json(handler, 403, {'ok': False, 'error': {'code': 'UNIT_SCOPE_VIOLATION', 'message': 'Administrador local pode criar requisições apenas para sua própria unidade operacional.'}})
        items = payload.get('items') or []
        if not items:
            raise ValueError('A requisição precisa ter pelo menos um item.')
        now_prefix = datetime.now(UTC).isoformat()[:10]
        title = str(payload.get('title') or f'Requisição {now_prefix}').strip()
        notes = str(payload.get('notes') or '').strip()
        ip = str(getattr(handler, 'client_address', ('',))[0] or '')
        result = create_purchase_request(connection, actor, unit_id, items, title, notes, ip, get_epi_by_id_fn=get_epi_by_id)
        connection.commit()
        status_code = 200 if result.get('duplicate') else 201
        return send_json(handler, status_code, result)


def handle_post_purchase_request_review_items(handler, parsed, payload, match):
    require_fields(payload, ['actor_user_id'])
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed, payload), PERM_PURCHASE_REQUESTS_UPDATE)
        pr_id = int(match.group(1))
        pr = connection.execute('SELECT * FROM purchase_requests WHERE id = ?', (pr_id,)).fetchone()
        if not pr:
            raise ValueError('Requisição não encontrada.')
        pr = dict(pr)
        ensure_purchase_request_action_scope(connection, actor, pr, actor_operational_unit_id=actor_operational_unit_id)
        if str(pr['status']) != 'waiting_requester_correction':
            raise ValueError('Itens só podem ser revisados quando a requisição aguarda correção do requisitante.')
        updates = payload.get('updates') or []
        remove_ids = [int(iid) for iid in (payload.get('remove_item_ids') or []) if str(iid).isdigit()]
        add_items = payload.get('add_items') or []
        notes = str(payload.get('notes') or '').strip()
        reason = str(payload.get('reason') or '')
        ip = str(getattr(handler, 'client_address', ('',))[0] or '')
        affected = review_purchase_request_items(
            connection, actor, pr, updates, remove_ids, add_items, notes, reason, ip,
            get_epi_by_id_fn=get_epi_by_id,
        )
        connection.commit()
        return send_json(handler, 200, {'ok': True, 'affected_item_ids': affected})


def handle_post_purchase_request_status(handler, parsed, payload, match):
    require_fields(payload, ['actor_user_id', 'status'])
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed, payload), PERM_PURCHASE_REQUESTS_UPDATE)
        pr_id = int(match.group(1))
        pr = connection.execute('SELECT * FROM purchase_requests WHERE id = ?', (pr_id,)).fetchone()
        if not pr:
            raise ValueError('Requisição não encontrada.')
        pr = dict(pr)
        ensure_purchase_request_action_scope(connection, actor, pr, actor_operational_unit_id=actor_operational_unit_id)
        new_status = str(payload.get('status') or '').strip()
        comment = str(payload.get('comment') or '')
        postponed_until = str(payload.get('postponed_until') or '').strip()
        received_items_payload = payload.get('received_items') or []
        ip = str(getattr(handler, 'client_address', ('',))[0] or '')
        stock_entries = update_purchase_request_status(
            connection, actor, pr, new_status, comment, postponed_until, received_items_payload, ip
        )
        connection.commit()
        return send_json(handler, 200, {'ok': True, 'stock_entries': stock_entries})


def handle_post_requests_status(handler, parsed, payload, match):
    require_fields(payload, ['actor_user_id', 'request_id', 'status'])
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed, payload), 'deliveries:create')
        req = connection.execute('SELECT * FROM epi_requests WHERE id = ?', (int(payload['request_id']),)).fetchone()
        if not req:
            raise ValueError('Solicitação não encontrada.')
        req = dict(req)
        ensure_resource_company(actor, req, 'Solicitação')
        new_status = str(payload.get('status', '')).strip().lower()
        postponed_until = str(payload.get('postponed_until') or '').strip()
        rejection_reason = str(payload.get('rejection_reason', '')).strip()
        notes = str(payload.get('notes', '')).strip()
        update_epi_request_status(connection, actor, req, new_status, postponed_until, rejection_reason, notes)
        connection.commit()
        return send_json(handler, 200, {'ok': True})


def handle_post_requests_bulk_status(handler, parsed, payload, match):
    require_fields(payload, ['actor_user_id', 'updates'])
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed, payload), 'deliveries:create')
        updates = payload.get('updates') or []
        if not updates:
            raise ValueError('Nenhuma atualização enviada.')
        bulk_update_epi_request_statuses(connection, actor, updates)
        connection.commit()
        return send_json(handler, 200, {'ok': True})


def handle_post_feedbacks_status(handler, parsed, payload, match):
    require_fields(payload, ['actor_user_id', 'feedback_id', 'status'])
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed, payload), 'deliveries:view')
        feedback = connection.execute('SELECT * FROM epi_feedbacks WHERE id = ?', (int(payload['feedback_id']),)).fetchone()
        if not feedback:
            raise ValueError('Avaliação não encontrada.')
        feedback = dict(feedback)
        ensure_resource_company(actor, feedback, 'Avaliação')
        status = str(payload.get('status', '')).strip().lower()
        notes = str(payload.get('notes', '')).strip()
        update_feedback_status(connection, actor, feedback, status, notes)
        connection.commit()
        return send_json(handler, 200, {'ok': True})


def handle_put_authorized_supplier(handler, parsed, payload, match):
    supplier_id = int(match.group(1))
    require_fields(payload, ['actor_user_id', 'name'])
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed, payload), PERM_SUPPLIERS_MANAGE)
        company_id = int(actor['company_id'])
        name = str(payload['name']).strip()
        cnpj = ''.join(ch for ch in str(payload.get('cnpj') or '') if ch.isdigit())
        category = str(payload.get('category') or '').strip()
        contact_email = str(payload.get('contact_email') or '').strip().lower()
        notes = str(payload.get('notes') or '').strip()
        found = upsert_authorized_supplier(connection, company_id, supplier_id, name, cnpj, category, contact_email, notes)
        if not found:
            return send_json(handler, 404, {'error': 'Fornecedor não encontrado.'})
        connection.commit()
        return send_json(handler, 200, {'ok': True})


def handle_delete_purchase_function(handler, parsed, payload, match):
    link_id = int(match.group(1))
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed), PERM_UNIT_LINKS_MANAGE)
        require_purchase_function_admin(actor)
        company_id = int(actor['company_id'])
        delete_purchase_function_link(connection, company_id, link_id)
        connection.commit()
        return send_json(handler, 200, {'ok': True})


def handle_post_user_unit_links(handler, parsed, payload, match):
    return send_json(handler, 410, {
        'ok': False,
        'error': {
            'code': 'DEPRECATED',
            'message': (
                'Criação de vínculos via user_unit_links está desativada. '
                'Use purchase_role_unit_links para vincular compradores/aprovadores a unidades.'
            ),
        },
    })


def handle_delete_user_unit_link(handler, parsed, payload, match):
    return send_json(handler, 410, {
        'ok': False,
        'error': {
            'code': 'DEPRECATED',
            'message': 'user_unit_links foi removida. Use purchase_role_unit_links.',
        },
    })


# ── GET /api/authorized-suppliers ────────────────────────────────────────────

def handle_get_authorized_suppliers(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed), PERM_PURCHASE_REQUESTS_VIEW)
        return send_json(handler, 200, {'items': fetch_authorized_suppliers(connection, int(actor['company_id']))})


def handle_get_supplier_pos(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed), PERM_PO_VIEW)
        supplier_id = int(match.group(1))
        company_id = int(actor['company_id'])
        sup, items = fetch_supplier_purchase_orders(connection, company_id, supplier_id)
        if sup is None:
            return send_json(handler, 404, {'error': 'Fornecedor não encontrado.'})
        return send_json(handler, 200, {'supplier': sup, 'items': items})


def handle_get_company_purchase_config(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        query = parse_qs(parsed.query)
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed), PERM_PURCHASE_REQUESTS_VIEW)
        raw_cid = str(query.get('company_id', [''])[0] or '').strip() or str(actor.get('company_id') or '').strip()
        if not raw_cid or raw_cid == 'None':
            return send_json(handler, 200, {'config': {}})
        config = get_company_purchase_config(connection, int(raw_cid))
        return send_json(handler, 200, {'config': config})


def handle_get_user_unit_links(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        query = parse_qs(parsed.query)
        target_user_id_str = str(query.get('user_id', [''])[0] or '').strip()
        actor_id = resolve_actor_user_id(handler, parsed)
        if target_user_id_str and str(actor_id) == target_user_id_str:
            actor = authorize_action(connection, actor_id, PERM_PURCHASE_REQUESTS_VIEW)
            company_id = int(actor['company_id'])
            target_user_id = int(target_user_id_str)
            linked_employee_id = actor.get('linked_employee_id')
            items = fetch_user_unit_links(connection, company_id, target_user_id, linked_employee_id, is_self=True)
        else:
            actor = authorize_action(connection, actor_id, PERM_UNIT_LINKS_MANAGE)
            company_id = int(actor['company_id'])
            target_user_id = int(target_user_id_str) if target_user_id_str else None
            items = fetch_user_unit_links(connection, company_id, target_user_id)
        return send_json(handler, 200, {'items': items})


# ── Registro ──────────────────────────────────────────────────────────────────

def register_routes(router):
    # GET
    router.register('GET', '/api/requests',                                  handle_get_epi_requests)
    router.register('GET', '/api/authorized-suppliers',                           handle_get_authorized_suppliers)
    router.register('GET', r'^/api/authorized-suppliers/(\d+)/purchase-orders$',  handle_get_supplier_pos, regex=True)
    router.register('GET', '/api/company-purchase-config',                         handle_get_company_purchase_config)
    router.register('GET', '/api/user-unit-links',                                 handle_get_user_unit_links)
    router.register('GET', '/api/purchase-demands',                          handle_get_purchase_demands)
    router.register('GET', '/api/purchase-requests',                         handle_get_purchase_requests)
    router.register('GET', r'^/api/purchase-requests/(\d+)$',                handle_get_purchase_request_detail, regex=True)
    router.register('GET', '/api/purchase-orders',                           handle_get_purchase_orders)
    router.register('GET', r'^/api/purchase-orders/(\d+)$',                  handle_get_purchase_order_detail, regex=True)
    router.register('GET', '/api/purchase-events',                           handle_get_purchase_events)
    router.register('GET', '/api/purchase-functions',                        handle_get_purchase_functions)
    # POST
    router.register('POST', '/api/user-unit-links',                           handle_post_user_unit_links)
    router.register('POST', r'^/api/purchase-requests/(\d+)/workflow$',      handle_post_purchase_request_workflow, regex=True)
    router.register('POST', '/api/purchase-requests',                         handle_post_purchase_requests)
    router.register('POST', r'^/api/purchase-requests/(\d+)/review-items$',  handle_post_purchase_request_review_items, regex=True)
    router.register('POST', r'^/api/purchase-requests/(\d+)/status$',        handle_post_purchase_request_status, regex=True)
    router.register('POST', '/api/requests/status',                           handle_post_requests_status)
    router.register('POST', '/api/requests/bulk-status',                      handle_post_requests_bulk_status)
    router.register('POST', '/api/feedbacks/status',                          handle_post_feedbacks_status)
    # PUT
    router.register('PUT',  r'^/api/authorized-suppliers/(\d+)$',            handle_put_authorized_supplier, regex=True)
    # DELETE
    router.register('DELETE', r'^/api/purchase-functions/(\d+)$',            handle_delete_purchase_function, regex=True)
    router.register('DELETE', r'^/api/user-unit-links/(\d+)$',               handle_delete_user_unit_link, regex=True)
