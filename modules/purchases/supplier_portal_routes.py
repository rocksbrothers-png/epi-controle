"""Rotas da Fase F2 — Portal do Fornecedor.

Internas (autenticadas): gerar/enviar/revogar/listar links do portal.
Públicas (token + rate limit por IP): página HTML, payload da entidade,
resposta de cotação e confirmação/status de entrega. As públicas nunca
usam authorize_action — o token É a credencial, com escopo de 1 entidade.
"""

from contextlib import closing

from urllib.parse import parse_qs

from core.database import get_connection
from core.permissions import PERM_PO_CREATE, PERM_QUOTES_MANAGE, PERM_QUOTES_VIEW
from core.rate_limit import get_client_ip, supplier_portal_limiter
from core.repository import authorize_action
from core.security import resolve_actor_user_id
from epi_backend.http_utils import require_fields, send_bytes, send_json, structured_log
from modules.employees.service import actor_operational_unit_id
from modules.purchases.quotes_service import ensure_quote_scope, get_quote_by_id
from modules.purchases.service import (
    ensure_purchase_order_action_scope,
    get_purchase_order_by_id,
)
from modules.purchases.supplier_portal_page import PORTAL_PAGE_HTML
from modules.purchases.supplier_portal_service import (
    fetch_supplier_portal_links,
    get_portal_payload,
    portal_answer_quote,
    portal_confirm_po,
    resolve_portal_token,
    revoke_supplier_portal_link,
    send_portal_link_email,
)


def _client_ip(handler):
    return str(getattr(handler, 'client_address', ('',))[0] or '')


def _user_agent(handler):
    try:
        return str(handler.headers.get('User-Agent', '') or '')
    except Exception:
        return ''


def _rate_limited(handler):
    ip = get_client_ip(handler)
    if not supplier_portal_limiter.is_allowed(ip):
        structured_log('warning', 'supplier_portal.rate_limited', ip=ip)
        send_json(handler, 429, {'error': {'code': 'RATE_LIMITED', 'message': 'Muitas requisições. Tente novamente em instantes.'}})
        return True
    return False


# ── Internas (comprador) ──────────────────────────────────────────────────────

def handle_post_quote_portal_link(handler, parsed, payload, match):
    require_fields(payload, ['actor_user_id'])
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed, payload), PERM_QUOTES_MANAGE)
        quote = get_quote_by_id(connection, int(match.group(1)))
        if not quote:
            raise ValueError('Cotação não encontrada.')
        ensure_quote_scope(connection, actor, quote, actor_operational_unit_id=actor_operational_unit_id)
        link = send_portal_link_email(
            connection, actor, 'quote', int(match.group(1)),
            expires_days=payload.get('expires_days'),
            base_url=str(payload.get('base_url') or '').strip(),
        )
        connection.commit()
        return send_json(handler, 201, {'ok': True, 'item': link})


def handle_post_po_portal_link(handler, parsed, payload, match):
    require_fields(payload, ['actor_user_id'])
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed, payload), PERM_PO_CREATE)
        po = get_purchase_order_by_id(connection, int(match.group(1)))
        if not po:
            raise ValueError('PO não encontrada.')
        ensure_purchase_order_action_scope(connection, actor, po, actor_operational_unit_id=actor_operational_unit_id)
        link = send_portal_link_email(
            connection, actor, 'purchase_order', int(match.group(1)),
            expires_days=payload.get('expires_days'),
            base_url=str(payload.get('base_url') or '').strip(),
        )
        connection.commit()
        return send_json(handler, 201, {'ok': True, 'item': link})


def handle_get_supplier_portal_links(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed), PERM_QUOTES_VIEW)
        query = parse_qs(parsed.query)
        entity_type = str(query.get('entity_type', [''])[0] or '').strip() or None
        entity_id = str(query.get('entity_id', [''])[0] or '').strip() or None
        items = fetch_supplier_portal_links(connection, int(actor['company_id']), entity_type, entity_id)
        return send_json(handler, 200, {'items': items})


def handle_delete_supplier_portal_link(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed), PERM_QUOTES_MANAGE)
        found = revoke_supplier_portal_link(connection, actor, int(actor['company_id']), int(match.group(1)))
        if not found:
            return send_json(handler, 404, {'error': 'Link não encontrado.'})
        connection.commit()
        return send_json(handler, 200, {'ok': True})


# ── Públicas (fornecedor, via token) ─────────────────────────────────────────

def handle_get_supplier_portal_page(handler, parsed, payload, match):
    if _rate_limited(handler):
        return True
    return send_bytes(handler, 200, 'text/html; charset=utf-8', PORTAL_PAGE_HTML.encode('utf-8')) or True


def handle_get_supplier_portal_data(handler, parsed, payload, match):
    if _rate_limited(handler):
        return True
    with closing(get_connection()) as connection:
        link = resolve_portal_token(connection, match.group(1), _client_ip(handler), _user_agent(handler))
        payload_out = get_portal_payload(connection, link)
        connection.commit()
        return send_json(handler, 200, {'item': payload_out})


def handle_post_supplier_portal_quote(handler, parsed, payload, match):
    if _rate_limited(handler):
        return True
    require_fields(payload, ['items'])
    with closing(get_connection()) as connection:
        link = resolve_portal_token(connection, match.group(1), _client_ip(handler), _user_agent(handler))
        quote = portal_answer_quote(connection, link, payload, _client_ip(handler), _user_agent(handler))
        connection.commit()
        return send_json(handler, 200, {'ok': True, 'status': quote.get('status')})


def handle_post_supplier_portal_confirm(handler, parsed, payload, match):
    if _rate_limited(handler):
        return True
    require_fields(payload, ['status'])
    with closing(get_connection()) as connection:
        link = resolve_portal_token(connection, match.group(1), _client_ip(handler), _user_agent(handler))
        po = portal_confirm_po(connection, link, payload, _client_ip(handler), _user_agent(handler))
        connection.commit()
        return send_json(handler, 200, {'ok': True, 'supplier_confirmation_status': po.get('supplier_confirmation_status')})


def register_routes(router):
    # Internas
    router.register('POST',   r'^/api/quotes/(\d+)/portal-link$',          handle_post_quote_portal_link, regex=True)
    router.register('POST',   r'^/api/purchase-orders/(\d+)/portal-link$', handle_post_po_portal_link, regex=True)
    router.register('GET',    '/api/supplier-portal-links',                handle_get_supplier_portal_links)
    router.register('DELETE', r'^/api/supplier-portal-links/(\d+)$',       handle_delete_supplier_portal_link, regex=True)
    # Públicas (token)
    router.register('GET',    r'^/fornecedor/([A-Za-z0-9_\-]+)$',                     handle_get_supplier_portal_page, regex=True)
    router.register('GET',    r'^/api/portal/supplier/([A-Za-z0-9_\-]+)$',            handle_get_supplier_portal_data, regex=True)
    router.register('POST',   r'^/api/portal/supplier/([A-Za-z0-9_\-]+)/quote$',      handle_post_supplier_portal_quote, regex=True)
    router.register('POST',   r'^/api/portal/supplier/([A-Za-z0-9_\-]+)/confirm$',    handle_post_supplier_portal_confirm, regex=True)
