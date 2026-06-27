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
from core.repository import require_actor, require_master_actor
from core.security import resolve_actor_user_id
from epi_backend.config import BASE_DIR
from epi_backend.http_utils import send_bytes, send_json, structured_log
from modules.payments import service, subscriptions_service
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
    payload = payload or {}
    with closing(get_connection()) as connection:
        try:
            result = service.create_card_subscription(connection, payload)
        except MercadoPagoError as exc:
            connection.rollback()
            return _mp_error_response(handler, exc)
        # Persiste a assinatura para o ciclo de vida (Minha Assinatura/histórico).
        # Best-effort: uma falha aqui não invalida a assinatura já criada no MP.
        try:
            subscriptions_service.record_subscription(
                connection,
                company_id=payload.get('company_id'),
                plan_key=str(payload.get('plan_key') or payload.get('plan_id') or ''),
                cycle=service.normalize_cycle(payload.get('cycle')),
                payment_method='card',
                preapproval_id=result.get('subscription_id'),
                preapproval_plan_id=str(payload.get('plan_id') or ''),
                status=result.get('status') or 'pending',
                amount=payload.get('amount') or 0,
                tenant_id=str(payload.get('tenant_id') or ''),
                created_by=payload.get('actor_user_id'),
                is_recurring=True, raw=result,
            )
        except Exception as exc:  # pragma: no cover - defensivo
            structured_log('warning', 'subscriptions.record_failed', error=str(exc))
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


# ── Assinaturas (ciclo de vida, autenticado e escopado por empresa) ────────────

def _client_ip(handler):
    addr = getattr(handler, 'client_address', None)
    if isinstance(addr, (list, tuple)) and addr:
        return str(addr[0])
    return ''


def _actor_and_company(connection, handler, parsed, payload=None):
    """Resolve o ator autenticado e o company_id a operar.

    Empresas comuns operam sobre a própria empresa; o master_admin pode indicar
    company_id explícito (query/body) para suporte.
    """
    actor = require_actor(connection, resolve_actor_user_id(handler, parsed, payload))
    company_id = actor.get('company_id')
    if actor.get('role') == 'master_admin':
        explicit = (payload or {}).get('company_id') or parse_qs(parsed.query).get('company_id', [''])[0]
        if str(explicit or '').strip():
            company_id = int(explicit)
    if company_id in (None, ''):
        raise PermissionError('Usuário sem empresa associada.')
    return actor, int(company_id)


def handle_get_subscription_current(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        _actor, company_id = _actor_and_company(connection, handler, parsed)
        sub = subscriptions_service.get_current_subscription(connection, company_id)
        return send_json(handler, 200, {'ok': True, 'subscription': sub})


def handle_get_subscription_invoices(handler, parsed, payload, match):
    query = parse_qs(parsed.query)
    with closing(get_connection()) as connection:
        _actor, company_id = _actor_and_company(connection, handler, parsed)
        invoices = subscriptions_service.list_invoices(
            connection, company_id,
            limit=int(query.get('limit', ['50'])[0] or 50),
            offset=int(query.get('offset', ['0'])[0] or 0),
            status=query.get('status', [None])[0] or None,
            method=query.get('method', [None])[0] or None,
        )
        return send_json(handler, 200, {'ok': True, 'invoices': invoices})


def handle_post_subscription_cancel(handler, parsed, payload, match):
    payload = payload or {}
    with closing(get_connection()) as connection:
        actor, company_id = _actor_and_company(connection, handler, parsed, payload)
        try:
            result = subscriptions_service.cancel_subscription(
                connection, company_id=company_id, actor_user_id=actor['id'],
                ip=_client_ip(handler), reason=str(payload.get('reason') or ''),
            )
        except MercadoPagoError as exc:
            connection.rollback()
            return _mp_error_response(handler, exc)
        connection.commit()
        return send_json(handler, 200, {'ok': True, 'subscription': result})


def handle_post_subscription_change_card(handler, parsed, payload, match):
    payload = payload or {}
    with closing(get_connection()) as connection:
        actor, company_id = _actor_and_company(connection, handler, parsed, payload)
        try:
            result = subscriptions_service.change_card(
                connection, company_id=company_id, card_token=payload.get('card_token'),
                actor_user_id=actor['id'], ip=_client_ip(handler),
            )
        except MercadoPagoError as exc:
            connection.rollback()
            return _mp_error_response(handler, exc)
        connection.commit()
        return send_json(handler, 200, {'ok': True, 'subscription': result})


def handle_post_subscription_change_plan(handler, parsed, payload, match):
    payload = payload or {}
    with closing(get_connection()) as connection:
        actor, company_id = _actor_and_company(connection, handler, parsed, payload)
        try:
            result = subscriptions_service.change_plan(
                connection, company_id=company_id,
                plan_id=payload.get('plan_id'), plan_key=payload.get('plan_key'),
                cycle=service.normalize_cycle(payload.get('cycle')),
                payer_email=payload.get('payer_email'), card_token=payload.get('card_token'),
                amount=payload.get('amount'), actor_user_id=actor['id'],
                ip=_client_ip(handler), tenant_id=str(payload.get('tenant_id') or ''),
            )
        except MercadoPagoError as exc:
            connection.rollback()
            return _mp_error_response(handler, exc)
        connection.commit()
        return send_json(handler, 201, {'ok': True, 'subscription': result})


def handle_post_subscription_reactivate(handler, parsed, payload, match):
    payload = payload or {}
    with closing(get_connection()) as connection:
        actor, company_id = _actor_and_company(connection, handler, parsed, payload)
        try:
            result = subscriptions_service.reactivate_subscription(
                connection, company_id=company_id,
                plan_id=payload.get('plan_id'), plan_key=payload.get('plan_key'),
                cycle=service.normalize_cycle(payload.get('cycle')),
                payer_email=payload.get('payer_email'), card_token=payload.get('card_token'),
                amount=payload.get('amount'), actor_user_id=actor['id'],
                ip=_client_ip(handler), tenant_id=str(payload.get('tenant_id') or ''),
            )
        except MercadoPagoError as exc:
            connection.rollback()
            return _mp_error_response(handler, exc)
        connection.commit()
        return send_json(handler, 201, {'ok': True, 'subscription': result})


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
    router.register('GET', '/api/subscriptions/current', handle_get_subscription_current)
    router.register('GET', '/api/subscriptions/invoices', handle_get_subscription_invoices)
    router.register('POST', '/api/subscriptions/cancel', handle_post_subscription_cancel)
    router.register('POST', '/api/subscriptions/change-card', handle_post_subscription_change_card)
    router.register('POST', '/api/subscriptions/change-plan', handle_post_subscription_change_plan)
    router.register('POST', '/api/subscriptions/reactivate', handle_post_subscription_reactivate)
    router.register('GET', '/pagamento', handle_get_checkout_page)
    router.register('GET', '/checkout', handle_get_checkout_page)
    router.register('POST', '/api/payments/plans', handle_post_plan)
    router.register('POST', '/api/payments/subscriptions', handle_post_subscription)
    router.register('POST', '/api/payments/pix', handle_post_pix)
    router.register('POST', '/api/payments/boleto', handle_post_boleto)
    router.register('POST', '/api/payments/webhook', handle_post_webhook)
