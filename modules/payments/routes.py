"""Rotas de pagamento/assinatura (Mercado Pago).

Endpoints seguros consumidos pelo website/app. Toda a lógica sensível (Access
Token, criação de planos, assinaturas e pagamentos) roda aqui no backend; o
frontend nunca recebe o Access Token.

Endpoints:
  GET  /api/payments/config        → public key + ambiente (seguro p/ frontend)
  GET  /api/payments/catalog       → catálogo público de planos (site/app)
  GET  /api/payments/plans         → lista planos persistidos (master)
  POST /api/payments/plans         → cria preapproval plan (master)
  POST /api/payments/subscriptions → cria assinatura com cartão tokenizado
  POST /api/payments/pix           → cria pagamento Pix
  POST /api/payments/boleto        → cria pagamento boleto
  POST /api/payments/webhook       → recebe notificações do Mercado Pago
  GET  /api/payments/status        → consulta status de um pagamento

Páginas servidas pelo backend (mesma origem da API, sem CORS):
  GET  /pagamento                  → página de checkout (Pix/boleto/cartão)
  GET  /checkout                   → alias de /pagamento
"""

from contextlib import closing
from pathlib import Path
from urllib.parse import parse_qs

from core.database import get_connection
from core.repository import require_master_actor
from core.security import resolve_actor_user_id
from epi_backend.config import BASE_DIR
from epi_backend.http_utils import send_bytes, send_json, structured_log
from modules.payments import service
from modules.payments.mp_client import MercadoPagoError

_CHECKOUT_PAGE = Path(BASE_DIR) / 'pagamento.html'


def _mp_error_response(handler, exc):
    status = exc.status if isinstance(exc.status, int) and 400 <= exc.status < 600 else 502
    return send_json(handler, status, {
        'ok': False,
        'error': {'code': 'MERCADO_PAGO_ERROR', 'message': str(exc), 'details': exc.response},
    })


# ── GET ───────────────────────────────────────────────────────────────────────

def handle_get_config(handler, parsed, payload, match):
    return send_json(handler, 200, {'ok': True, 'config': service.public_config()})


def handle_get_catalog(handler, parsed, payload, match):
    query = parse_qs(parsed.query)
    cycle = service.normalize_cycle(query.get('cycle', ['monthly'])[0])
    with closing(get_connection()) as connection:
        catalog = service.list_public_catalog(connection, cycle)
        return send_json(handler, 200, {'ok': True, 'cycle': cycle, 'catalog': catalog})


def handle_get_checkout_page(handler, parsed, payload, match):
    """Serve a página de checkout em URL limpa (/pagamento, /checkout).

    A página vive na mesma origem da API, então o frontend chama os endpoints
    /api/payments/* sem necessidade de CORS.
    """
    try:
        body = _CHECKOUT_PAGE.read_bytes()
    except FileNotFoundError:
        return send_json(handler, 404, {'ok': False, 'error': {'code': 'NOT_FOUND', 'message': 'Página de checkout indisponível.'}})
    return send_bytes(handler, 200, 'text/html; charset=utf-8', body)


def handle_get_plans(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        require_master_actor(connection, resolve_actor_user_id(handler, parsed))
        query = parse_qs(parsed.query)
        raw_company = query.get('company_id', [''])[0]
        company_id = int(raw_company) if str(raw_company).strip() else None
        plans = service.list_plans(connection, company_id)
        return send_json(handler, 200, {'ok': True, 'plans': plans})


def handle_get_status(handler, parsed, payload, match):
    query = parse_qs(parsed.query)
    payment_id = query.get('payment_id', [''])[0] or query.get('id', [''])[0]
    if not str(payment_id).strip():
        return send_json(handler, 400, {'ok': False, 'error': {'code': 'BAD_REQUEST', 'message': 'payment_id é obrigatório.'}})
    resource_type = query.get('resource_type', ['payment'])[0]
    with closing(get_connection()) as connection:
        try:
            result = service.fetch_payment_status(connection, payment_id, resource_type)
        except MercadoPagoError as exc:
            return _mp_error_response(handler, exc)
        connection.commit()
        return send_json(handler, 200, {'ok': True, 'payment': result})


# ── POST ──────────────────────────────────────────────────────────────────────

def handle_post_plan(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        require_master_actor(connection, resolve_actor_user_id(handler, parsed, payload))
        try:
            result = service.create_preapproval_plan(connection, payload or {})
        except MercadoPagoError as exc:
            connection.rollback()
            return _mp_error_response(handler, exc)
        connection.commit()
        return send_json(handler, 201, {'ok': True, 'plan': result})


def handle_post_subscription(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        try:
            result = service.create_card_subscription(connection, payload or {})
        except MercadoPagoError as exc:
            connection.rollback()
            return _mp_error_response(handler, exc)
        connection.commit()
        return send_json(handler, 201, {'ok': True, 'subscription': result})


def handle_post_pix(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        try:
            result = service.create_pix_payment(connection, payload or {})
        except MercadoPagoError as exc:
            connection.rollback()
            return _mp_error_response(handler, exc)
        connection.commit()
        return send_json(handler, 201, {'ok': True, 'payment': result})


def handle_post_boleto(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        try:
            result = service.create_boleto_payment(connection, payload or {})
        except MercadoPagoError as exc:
            connection.rollback()
            return _mp_error_response(handler, exc)
        connection.commit()
        return send_json(handler, 201, {'ok': True, 'payment': result})


def handle_post_webhook(handler, parsed, payload, match):
    query = parse_qs(parsed.query)
    if not service.verify_webhook_signature(handler.headers, query):
        structured_log('warning', 'payments.webhook_invalid_signature', path=parsed.path)
        return send_json(handler, 401, {'ok': False, 'error': {'code': 'INVALID_SIGNATURE', 'message': 'Assinatura inválida.'}})
    with closing(get_connection()) as connection:
        try:
            result = service.handle_webhook(connection, payload or {}, query)
            connection.commit()
        except Exception as exc:  # nunca devolver 5xx evitável ao MP
            try:
                connection.rollback()
            except Exception:
                pass
            structured_log('error', 'payments.webhook_error', path=parsed.path, error=str(exc))
            # 200 para o MP não reenfileirar indefinidamente um erro não recuperável.
            return send_json(handler, 200, {'ok': False, 'error': str(exc)})
    return send_json(handler, 200, result)


# ── Registro ──────────────────────────────────────────────────────────────────

def register_routes(router):
    router.register('GET', '/api/payments/config', handle_get_config)
    router.register('GET', '/api/payments/catalog', handle_get_catalog)
    router.register('GET', '/api/payments/plans', handle_get_plans)
    router.register('GET', '/api/payments/status', handle_get_status)
    router.register('GET', '/pagamento', handle_get_checkout_page)
    router.register('GET', '/checkout', handle_get_checkout_page)
    router.register('POST', '/api/payments/plans', handle_post_plan)
    router.register('POST', '/api/payments/subscriptions', handle_post_subscription)
    router.register('POST', '/api/payments/pix', handle_post_pix)
    router.register('POST', '/api/payments/boleto', handle_post_boleto)
    router.register('POST', '/api/payments/webhook', handle_post_webhook)
