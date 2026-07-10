"""Rotas da Fase F1 do módulo de Compras: catálogo, cotações e envio (Nível 1).

Registradas a partir de modules/purchases/routes.register_routes — contratos
existentes intactos; tudo aqui é endpoint novo (plano §5).
"""

from contextlib import closing
from urllib.parse import parse_qs

from core.auth import ensure_resource_company
from core.database import get_connection
from core.permissions import (
    PERM_PO_CREATE,
    PERM_PO_VIEW,
    PERM_QUOTES_MANAGE,
    PERM_QUOTES_VIEW,
    PERM_SUPPLIER_CATALOG_VIEW,
    PERM_SUPPLIERS_MANAGE,
)
from core.repository import authorize_action
from core.security import resolve_actor_user_id
from epi_backend.http_utils import require_fields, send_json
from modules.employees.service import actor_operational_unit_id
from modules.purchases.service import (
    ensure_purchase_order_action_scope,
    ensure_purchase_request_action_scope,
    get_purchase_order_by_id,
    get_purchase_request_by_id,
)
from modules.purchases.quotes_service import (
    answer_quote,
    build_quote_comparison,
    create_authorized_supplier,
    create_quotes_for_request,
    deactivate_supplier_product,
    ensure_quote_scope,
    fetch_po_tracking,
    fetch_quotes_for_request,
    fetch_supplier_products,
    get_quote_by_id,
    get_supplier_by_id,
    resolve_supplier_company_id,
    resolve_product_company_id,
    register_po_confirmation,
    select_quote,
    send_po_to_supplier,
    send_quote_to_supplier,
    update_supplier_procurement_fields,
    upsert_supplier_product,
)


def _client_ip(handler):
    return str(getattr(handler, 'client_address', ('',))[0] or '')


def _load_scoped_quote(connection, actor, match):
    quote = get_quote_by_id(connection, int(match.group(1)))
    if not quote:
        raise ValueError('Cotação não encontrada.')
    ensure_quote_scope(connection, actor, quote, actor_operational_unit_id=actor_operational_unit_id)
    return quote


# ── Fornecedores / catálogo ───────────────────────────────────────────────────

def handle_post_authorized_suppliers(handler, parsed, payload, match):
    require_fields(payload, ['actor_user_id', 'name'])
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed, payload), PERM_SUPPLIERS_MANAGE)
        supplier = create_authorized_supplier(connection, actor, payload)
        connection.commit()
        return send_json(handler, 201, {'ok': True, 'item': supplier})


def handle_put_authorized_supplier_procurement(handler, parsed, payload, match):
    require_fields(payload, ['actor_user_id'])
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed, payload), PERM_SUPPLIERS_MANAGE)
        supplier_id = int(match.group(1))
        company_id = resolve_supplier_company_id(connection, actor, supplier_id)
        found = update_supplier_procurement_fields(connection, company_id, supplier_id, payload)
        if not found:
            return send_json(handler, 404, {'error': 'Fornecedor não encontrado.'})
        connection.commit()
        return send_json(handler, 200, {'ok': True})


def handle_get_supplier_products(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed), PERM_SUPPLIER_CATALOG_VIEW)
        supplier_id = int(match.group(1))
        company_id = resolve_supplier_company_id(connection, actor, supplier_id)
        supplier = get_supplier_by_id(connection, company_id, supplier_id)
        if not supplier:
            return send_json(handler, 404, {'error': 'Fornecedor não encontrado.'})
        query = parse_qs(parsed.query)
        include_inactive = str(query.get('include_inactive', [''])[0] or '') in ('1', 'true')
        items = fetch_supplier_products(connection, company_id, supplier_id, include_inactive)
        return send_json(handler, 200, {'supplier': supplier, 'items': items})


def handle_post_supplier_products(handler, parsed, payload, match):
    require_fields(payload, ['actor_user_id'])
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed, payload), PERM_SUPPLIERS_MANAGE)
        supplier_id = int(match.group(1))
        company_id = resolve_supplier_company_id(connection, actor, supplier_id)
        item = upsert_supplier_product(connection, actor, company_id, supplier_id, payload)
        connection.commit()
        return send_json(handler, 201, {'ok': True, 'item': item})


def handle_delete_supplier_product(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed), PERM_SUPPLIERS_MANAGE)
        product_id = int(match.group(1))
        company_id = resolve_product_company_id(connection, actor, product_id)
        found = deactivate_supplier_product(connection, company_id, product_id)
        if not found:
            return send_json(handler, 404, {'error': 'Produto não encontrado.'})
        connection.commit()
        return send_json(handler, 200, {'ok': True})


# ── Cotações (RFQ) ────────────────────────────────────────────────────────────

def handle_post_purchase_request_quotes(handler, parsed, payload, match):
    require_fields(payload, ['actor_user_id', 'supplier_ids'])
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed, payload), PERM_QUOTES_MANAGE)
        pr_id = int(match.group(1))
        pr = get_purchase_request_by_id(connection, pr_id)
        if not pr:
            raise ValueError('Requisição não encontrada.')
        ensure_purchase_request_action_scope(connection, actor, pr, actor_operational_unit_id=actor_operational_unit_id)
        quotes = create_quotes_for_request(connection, actor, pr_id, payload, _client_ip(handler))
        connection.commit()
        return send_json(handler, 201, {'ok': True, 'items': quotes})


def handle_get_purchase_request_quotes(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed), PERM_QUOTES_VIEW)
        pr_id = int(match.group(1))
        pr = get_purchase_request_by_id(connection, pr_id)
        if not pr:
            raise ValueError('Requisição não encontrada.')
        ensure_purchase_request_action_scope(connection, actor, pr, actor_operational_unit_id=actor_operational_unit_id)
        quotes = fetch_quotes_for_request(connection, pr_id)
        return send_json(handler, 200, {'items': quotes, 'comparison': build_quote_comparison(quotes)})


def handle_post_quote_send(handler, parsed, payload, match):
    require_fields(payload, ['actor_user_id'])
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed, payload), PERM_QUOTES_MANAGE)
        _load_scoped_quote(connection, actor, match)
        quote = send_quote_to_supplier(connection, actor, int(match.group(1)), _client_ip(handler))
        connection.commit()
        return send_json(handler, 200, {'ok': True, 'item': quote})


def handle_post_quote_answer(handler, parsed, payload, match):
    require_fields(payload, ['actor_user_id', 'items'])
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed, payload), PERM_QUOTES_MANAGE)
        _load_scoped_quote(connection, actor, match)
        quote = answer_quote(connection, actor, int(match.group(1)), payload, _client_ip(handler))
        connection.commit()
        return send_json(handler, 200, {'ok': True, 'item': quote})


def handle_post_quote_select(handler, parsed, payload, match):
    require_fields(payload, ['actor_user_id'])
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed, payload), PERM_QUOTES_MANAGE)
        _load_scoped_quote(connection, actor, match)
        result = select_quote(connection, actor, int(match.group(1)), _client_ip(handler))
        connection.commit()
        return send_json(handler, 200, {'ok': True, **result})


# ── PO: envio, confirmação e acompanhamento ──────────────────────────────────

def handle_post_purchase_order_send(handler, parsed, payload, match):
    require_fields(payload, ['actor_user_id'])
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed, payload), PERM_PO_CREATE)
        po = get_purchase_order_by_id(connection, int(match.group(1)))
        if not po:
            raise ValueError('PO não encontrada.')
        ensure_purchase_order_action_scope(connection, actor, po, actor_operational_unit_id=actor_operational_unit_id)
        po = send_po_to_supplier(connection, actor, int(match.group(1)), payload, _client_ip(handler))
        connection.commit()
        return send_json(handler, 200, {'ok': True, 'item': po})


def handle_post_purchase_order_confirmation(handler, parsed, payload, match):
    require_fields(payload, ['actor_user_id', 'status'])
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed, payload), PERM_PO_CREATE)
        po = get_purchase_order_by_id(connection, int(match.group(1)))
        if not po:
            raise ValueError('PO não encontrada.')
        ensure_purchase_order_action_scope(connection, actor, po, actor_operational_unit_id=actor_operational_unit_id)
        po = register_po_confirmation(connection, actor, int(match.group(1)), payload, _client_ip(handler))
        connection.commit()
        return send_json(handler, 200, {'ok': True, 'item': po})


def handle_get_purchase_order_tracking(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed), PERM_PO_VIEW)
        po = get_purchase_order_by_id(connection, int(match.group(1)))
        if not po:
            return send_json(handler, 404, {'error': 'PO não encontrada.'})
        ensure_resource_company(actor, po, 'PO')
        return send_json(handler, 200, {'item': fetch_po_tracking(connection, int(match.group(1)))})


def register_routes(router):
    # Fornecedores / catálogo
    router.register('POST',   '/api/authorized-suppliers',                             handle_post_authorized_suppliers)
    router.register('PUT',    r'^/api/authorized-suppliers/(\d+)/procurement$',        handle_put_authorized_supplier_procurement, regex=True)
    router.register('GET',    r'^/api/authorized-suppliers/(\d+)/products$',           handle_get_supplier_products, regex=True)
    router.register('POST',   r'^/api/authorized-suppliers/(\d+)/products$',           handle_post_supplier_products, regex=True)
    router.register('DELETE', r'^/api/supplier-products/(\d+)$',                       handle_delete_supplier_product, regex=True)
    # Cotações (RFQ)
    router.register('POST',   r'^/api/purchase-requests/(\d+)/quotes$',                handle_post_purchase_request_quotes, regex=True)
    router.register('GET',    r'^/api/purchase-requests/(\d+)/quotes$',                handle_get_purchase_request_quotes, regex=True)
    router.register('POST',   r'^/api/quotes/(\d+)/send$',                             handle_post_quote_send, regex=True)
    router.register('POST',   r'^/api/quotes/(\d+)/answer$',                           handle_post_quote_answer, regex=True)
    router.register('POST',   r'^/api/quotes/(\d+)/select$',                           handle_post_quote_select, regex=True)
    # PO: envio ao fornecedor, confirmação manual e acompanhamento
    router.register('POST',   r'^/api/purchase-orders/(\d+)/send$',                    handle_post_purchase_order_send, regex=True)
    router.register('POST',   r'^/api/purchase-orders/(\d+)/confirmation$',            handle_post_purchase_order_confirmation, regex=True)
    router.register('GET',    r'^/api/purchase-orders/(\d+)/tracking$',                handle_get_purchase_order_tracking, regex=True)
