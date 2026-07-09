"""Rotas da Fase F4 — integrações de API direta com lojas de EPI (Nível 3)."""

from contextlib import closing

from core.database import get_connection
from core.permissions import (
    PERM_PO_CREATE,
    PERM_PO_VIEW,
    PERM_QUOTES_MANAGE,
    PERM_QUOTES_VIEW,
    PERM_SUPPLIERS_MANAGE,
)
from core.repository import authorize_action
from core.security import resolve_actor_user_id
from epi_backend.http_utils import require_fields, send_json
from modules.employees.service import actor_operational_unit_id
from modules.purchases.connectors_service import (
    get_supplier_integration,
    list_available_connectors,
    quote_via_connector,
    refresh_po_status_from_connector,
    send_po_via_connector,
    sync_catalog_from_connector,
    ping_supplier_integration,
    upsert_supplier_integration,
)
from modules.purchases.quotes_service import ensure_quote_scope, get_quote_by_id
from modules.purchases.service import (
    ensure_purchase_order_action_scope,
    get_purchase_order_by_id,
)


def _client_ip(handler):
    return str(getattr(handler, 'client_address', ('',))[0] or '')


def handle_get_supplier_connectors(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        authorize_action(connection, resolve_actor_user_id(handler, parsed), PERM_QUOTES_VIEW)
        return send_json(handler, 200, {'items': list_available_connectors()})


def handle_get_supplier_integration(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed), PERM_SUPPLIERS_MANAGE)
        integration = get_supplier_integration(connection, int(actor['company_id']), int(match.group(1)))
        if integration is None:
            return send_json(handler, 404, {'error': 'Fornecedor sem integração configurada.'})
        return send_json(handler, 200, {'item': integration})


def handle_post_supplier_integration(handler, parsed, payload, match):
    require_fields(payload, ['actor_user_id', 'connector_key'])
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed, payload), PERM_SUPPLIERS_MANAGE)
        integration = upsert_supplier_integration(
            connection, actor, int(actor['company_id']), int(match.group(1)), payload,
        )
        connection.commit()
        return send_json(handler, 200, {'ok': True, 'item': integration})


def handle_post_supplier_integration_test(handler, parsed, payload, match):
    require_fields(payload, ['actor_user_id'])
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed, payload), PERM_SUPPLIERS_MANAGE)
        result = ping_supplier_integration(connection, int(actor['company_id']), int(match.group(1)))
        return send_json(handler, 200, result)


def handle_post_supplier_catalog_sync(handler, parsed, payload, match):
    require_fields(payload, ['actor_user_id'])
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed, payload), PERM_SUPPLIERS_MANAGE)
        result = sync_catalog_from_connector(
            connection, actor, int(actor['company_id']), int(match.group(1)),
        )
        connection.commit()
        return send_json(handler, 200, {'ok': True, **result})


def handle_post_quote_fetch_api(handler, parsed, payload, match):
    require_fields(payload, ['actor_user_id'])
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed, payload), PERM_QUOTES_MANAGE)
        quote = get_quote_by_id(connection, int(match.group(1)))
        if not quote:
            raise ValueError('Cotação não encontrada.')
        ensure_quote_scope(connection, actor, quote, actor_operational_unit_id=actor_operational_unit_id)
        result = quote_via_connector(connection, actor, int(match.group(1)), _client_ip(handler))
        connection.commit()
        return send_json(handler, 200, {'ok': True, 'item': result})


def handle_post_po_send_api(handler, parsed, payload, match):
    require_fields(payload, ['actor_user_id'])
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed, payload), PERM_PO_CREATE)
        po = get_purchase_order_by_id(connection, int(match.group(1)))
        if not po:
            raise ValueError('PO não encontrada.')
        ensure_purchase_order_action_scope(connection, actor, po, actor_operational_unit_id=actor_operational_unit_id)
        result = send_po_via_connector(connection, actor, int(match.group(1)), _client_ip(handler))
        connection.commit()
        return send_json(handler, 200, {'ok': True, 'item': result})


def handle_post_po_refresh_status(handler, parsed, payload, match):
    require_fields(payload, ['actor_user_id'])
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed, payload), PERM_PO_VIEW)
        po = get_purchase_order_by_id(connection, int(match.group(1)))
        if not po:
            raise ValueError('PO não encontrada.')
        ensure_purchase_order_action_scope(connection, actor, po, actor_operational_unit_id=actor_operational_unit_id)
        result = refresh_po_status_from_connector(connection, actor, int(match.group(1)), _client_ip(handler))
        connection.commit()
        return send_json(handler, 200, {'ok': True, 'item': result})


def register_routes(router):
    router.register('GET',  '/api/supplier-connectors',                                handle_get_supplier_connectors)
    router.register('GET',  r'^/api/authorized-suppliers/(\d+)/integration$',          handle_get_supplier_integration, regex=True)
    router.register('POST', r'^/api/authorized-suppliers/(\d+)/integration$',          handle_post_supplier_integration, regex=True)
    router.register('POST', r'^/api/authorized-suppliers/(\d+)/integration/test$',     handle_post_supplier_integration_test, regex=True)
    router.register('POST', r'^/api/authorized-suppliers/(\d+)/catalog-sync$',         handle_post_supplier_catalog_sync, regex=True)
    router.register('POST', r'^/api/quotes/(\d+)/fetch-api$',                          handle_post_quote_fetch_api, regex=True)
    router.register('POST', r'^/api/purchase-orders/(\d+)/send-api$',                  handle_post_po_send_api, regex=True)
    router.register('POST', r'^/api/purchase-orders/(\d+)/refresh-status$',            handle_post_po_refresh_status, regex=True)
