"""Rotas de pagamento/assinatura (Mercado Pago).

Endpoints seguros consumidos pelo website/app. Toda a lógica sensível (Access
Token, criação de planos, assinaturas e pagamentos) roda aqui no backend; o
frontend nunca recebe o Access Token.

Endpoints:
  GET  /api/payments/config        → public key + ambiente (seguro p/ frontend)
  GET  /api/payments/catalog       → catálogo público de planos (site/app)
  GET  /api/payments/plans         → lista planos persistidos (master)
  POST /api/payments/plans         → cria preapproval plan (master)
  POST /api/payments/subscriptions → assinatura com cartão (AUTENTICADO: Bearer;
                                     empresa/preço server-side — 1G-C #1009/#1010)
  POST /api/payments/pix           → pagamento Pix (AUTENTICADO; preço server-side)
  POST /api/payments/boleto        → pagamento boleto (AUTENTICADO; preço server-side)
  POST /api/payments/webhook       → recebe notificações do Mercado Pago
  GET  /api/payments/status        → consulta status de um pagamento

Páginas servidas pelo backend (mesma origem da API, sem CORS):
  GET  /pagamento                  → página de checkout (Pix/boleto/cartão)
  GET  /checkout                   → alias de /pagamento
"""

from contextlib import closing
from pathlib import Path
from urllib.parse import parse_qs

from core import checkout_idempotency
from core.database import get_connection
from core.repository import require_actor, require_master_actor
from core.security import require_bearer_actor, resolve_actor_user_id
from epi_backend.config import BASE_DIR
from epi_backend.http_utils import require_fields, send_bytes, send_json, structured_log
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


# ── Checkout AUTENTICADO seguro (1G-C, #1009/#1010) ───────────────────────────
#
# Contrato do checkout Corporate: a IDENTIDADE vem do Bearer (obrigatório LOCAL,
# independente de JWT_ENFORCEMENT_MODE — F-01); a EMPRESA vem da identidade
# server-side do ator; o PREÇO vem do catálogo server-side. O cliente NÃO pode
# informar empresa, tenant, ator, created_by, preço nem o plano do MP — esses
# campos no corpo geram 400 (falha explícita, nunca ignorados em silêncio).
#
# DIVERGÊNCIA INTENCIONAL vs. SaaS (PR #391): o SaaS liga a empresa por uma
# capability de signup público (um token opaco emitido no cadastro); o Corporate
# a liga pela identidade autenticada. Por isso o Corporate NÃO introduz essa
# capability nem o token de checkout (§14).

_FORBIDDEN_AUTHORITY_FIELDS = (
    'company_id', 'tenant_id', 'actor_user_id', 'created_by', 'amount',
    'plan_id', 'frequency', 'frequency_type', 'currency',
)

_PAYER_FIELDS = (
    'payer_email', 'payer_first_name', 'payer_last_name',
    'payer_doc_type', 'payer_doc_number',
)


def _reject_authority_fields(payload, parsed=None):
    """Nenhuma AUTORIDADE pode vir do cliente (corpo, e por robustez a query) → 400.

    Empresa, tenant, ator, created_by e preço/plano são SEMPRE server-side.
    """
    present = [f for f in _FORBIDDEN_AUTHORITY_FIELDS if f in (payload or {})]
    if parsed is not None:
        query = parse_qs(parsed.query)
        present += [f'{f} (query)' for f in _FORBIDDEN_AUTHORITY_FIELDS if f in query]
    if present:
        raise ValueError(
            'Campos não permitidos no checkout: ' + ', '.join(present)
            + '. Empresa, tenant, ator e preço são determinados pelo servidor.'
        )


def _authenticated_checkout_actor_id(handler, parsed, payload):
    """Gate de autoridade do checkout: Bearer obrigatório (401) + rejeição de
    campos de autoridade (400). Devolve o actor_user_id resolvido DO TOKEN.

    `require_bearer_actor` (F-01) sem Bearer → 401 (mesmo com
    JWT_ENFORCEMENT_MODE=off/shadow); com token, impõe a coerência token↔ator.
    `payload=None`: a identidade vem do token, nunca de `actor_user_id` do corpo
    (que, se presente, já é rejeitado como campo de autoridade)."""
    actor_user_id = require_bearer_actor(handler, parsed, None)
    _reject_authority_fields(payload, parsed)
    return actor_user_id


def _resolve_checkout_company(connection, actor_user_id):
    """Empresa/tenant SERVER-SIDE da identidade autenticada (nunca do corpo).

    O Corporate não possui `tenant_id` server-side (company_id é a autoridade de
    escopo); o tenant persistido fica vazio — nunca vem do cliente.
    """
    actor = require_actor(connection, actor_user_id)
    company_id = actor.get('company_id')
    if company_id in (None, ''):
        raise PermissionError('Usuário sem empresa associada.')
    return actor, int(company_id), ''


def _server_external_reference(company_id, plan_key, cycle):
    return f'checkout|company={company_id}|plan={plan_key}|cycle={cycle}'


# ── Idempotência do checkout (1J-C) ───────────────────────────────────────────
#
# Cada CHECKOUT carrega um `idempotency_key` (nonce da intenção; não é
# autoridade — empresa/ator/preço continuam server-side, #1017). `claim` o
# reivindica atomicamente (UNIQUE no banco); o efeito externo vai ao MP com uma
# chave DETERMINÍSTICA namespaced por empresa, de modo que retry/concorrência
# nunca produzem um segundo preapproval. Detalhes em core/checkout_idempotency.

def _checkout_in_progress(handler):
    return send_json(handler, 503, {'ok': False, 'error': {
        'code': 'CHECKOUT_IN_PROGRESS',
        'message': 'Checkout em processamento; repita com a MESMA idempotency_key.'}})


def _idempotent_replay(handler, prior, fingerprint_value, result_key):
    """Reconcilia uma intenção já registrada: replay idempotente (200) ou 409.

    Mesma chave + payload diferente → 409 (nunca reinterpretado como nova
    intenção, §18). Mesma chave + mesmo payload, já persistida → devolve o MESMO
    resultado (sem segundo efeito externo)."""
    if str(prior.get('fingerprint') or '') != fingerprint_value:
        return send_json(handler, 409, {'ok': False, 'error': {
            'code': 'IDEMPOTENCY_KEY_CONFLICT',
            'message': 'idempotency_key reutilizada para um checkout diferente.'}})
    stored = checkout_idempotency.stored_result(prior)
    if prior.get('status') == checkout_idempotency.STATUS_PERSISTED and stored is not None:
        return send_json(handler, 200, {'ok': True, result_key: stored, 'idempotent_replay': True})
    return _checkout_in_progress(handler)


def handle_post_subscription(handler, parsed, payload, match):
    payload = payload or {}
    # Bearer (401) + rejeição de autoridade (400) ANTES de tocar o banco/MP.
    actor_user_id = _authenticated_checkout_actor_id(handler, parsed, payload)
    require_fields(payload, ['idempotency_key', 'plan_key', 'cycle', 'payer_email', 'card_token'])
    client_key = checkout_idempotency.validate_key(payload.get('idempotency_key'))
    service.resolve_catalog_plan(payload.get('plan_key'), payload.get('cycle'))  # 400 cedo
    plan_key = str(payload.get('plan_key') or '')
    cycle = service.normalize_cycle(payload.get('cycle'))
    fp = checkout_idempotency.fingerprint('card', plan_key, cycle)
    with closing(get_connection()) as connection:
        actor, company_id, tenant_id = _resolve_checkout_company(connection, actor_user_id)
        ext_ref = checkout_idempotency.server_external_reference(company_id, plan_key, cycle, client_key)
        try:
            outcome, prior = checkout_idempotency.claim(
                connection, company_id=company_id, client_key=client_key, fingerprint=fp,
                actor_user_id=actor['id'], payment_method='card', plan_key=plan_key,
                cycle=cycle, external_reference=ext_ref)
        except checkout_idempotency.IdempotencyTransient:
            connection.rollback()
            return _checkout_in_progress(handler)
        if outcome == 'exists':
            return _idempotent_replay(handler, prior, fp, 'subscription')
        # Vencemos a reivindicação: efeito externo com chave estável (X-Idempotency-Key).
        mp_key = checkout_idempotency.mp_idempotency_key(company_id, client_key)
        try:
            result = service.create_catalog_card_subscription(
                connection, plan_key=plan_key, cycle=payload.get('cycle'),
                payer_email=payload.get('payer_email'), card_token=payload.get('card_token'),
                company_id=company_id, external_reference=ext_ref, idempotency_key=mp_key,
            )
        except MercadoPagoError as exc:
            connection.rollback()  # claim revertido → retry legítimo permitido (P4)
            return _mp_error_response(handler, exc)
        # Caminho crítico: NÃO engolir (§25). Se a persistência falhar, reverte
        # TUDO (inclusive o claim) e devolve 503 — o retry com a MESMA chave
        # reconcilia via idempotência do MP (nunca um segundo preapproval).
        try:
            subscriptions_service.record_subscription(
                connection,
                company_id=company_id, plan_key=result.get('plan_key') or plan_key,
                cycle=result.get('cycle') or cycle, payment_method='card',
                preapproval_id=result.get('subscription_id'),
                preapproval_plan_id=result.get('preapproval_plan_id') or '',
                status=result.get('status') or 'pending',
                amount=result.get('amount') or 0, tenant_id=tenant_id,
                created_by=actor['id'],
                origin=subscriptions_service.ORIGIN_AUTHENTICATED,
                is_recurring=True, raw=result,
            )
            checkout_idempotency.finalize(
                connection, company_id=company_id, client_key=client_key,
                status=checkout_idempotency.STATUS_PERSISTED, mp_resource_type='preapproval',
                mp_id=result.get('subscription_id'), result=result)
            connection.commit()
        except Exception as exc:
            connection.rollback()
            structured_log('error', 'checkout.persist_failed', error=str(exc))
            persist_pending = {'ok': False, 'error': {
                'code': 'CHECKOUT_PERSIST_PENDING',
                'message': 'Pagamento iniciado; reconciliação pendente. Repita com a MESMA idempotency_key.'}}
            send_json(handler, 503, persist_pending)
            return 503, persist_pending
        return send_json(handler, 201, {'ok': True, 'subscription': result})


def _handle_authenticated_oneoff(handler, parsed, payload, method_id):
    payload = payload or {}
    actor_user_id = _authenticated_checkout_actor_id(handler, parsed, payload)
    require_fields(payload, ['idempotency_key', 'plan_key', 'cycle', 'payer_email'])
    client_key = checkout_idempotency.validate_key(payload.get('idempotency_key'))
    service.resolve_catalog_plan(payload.get('plan_key'), payload.get('cycle'))  # 400 cedo
    plan_key = str(payload.get('plan_key') or '')
    cycle = service.normalize_cycle(payload.get('cycle'))
    method_label = 'pix' if method_id == 'pix' else 'boleto'
    fp = checkout_idempotency.fingerprint(method_label, plan_key, cycle)
    with closing(get_connection()) as connection:
        actor, company_id, _tenant = _resolve_checkout_company(connection, actor_user_id)
        ext_ref = checkout_idempotency.server_external_reference(company_id, plan_key, cycle, client_key)
        try:
            outcome, prior = checkout_idempotency.claim(
                connection, company_id=company_id, client_key=client_key, fingerprint=fp,
                actor_user_id=actor['id'], payment_method=method_label, plan_key=plan_key,
                cycle=cycle, external_reference=ext_ref)
        except checkout_idempotency.IdempotencyTransient:
            connection.rollback()
            return _checkout_in_progress(handler)
        if outcome == 'exists':
            return _idempotent_replay(handler, prior, fp, 'payment')
        mp_key = checkout_idempotency.mp_idempotency_key(company_id, client_key)
        payer_payload = {k: payload[k] for k in _PAYER_FIELDS if k in payload}
        try:
            result = service.create_catalog_oneoff_payment(
                connection, method_id=method_id, plan_key=plan_key, cycle=payload.get('cycle'),
                company_id=company_id, payer_payload=payer_payload,
                external_reference=ext_ref, idempotency_key=mp_key,
            )
        except MercadoPagoError as exc:
            connection.rollback()
            return _mp_error_response(handler, exc)
        try:
            checkout_idempotency.finalize(
                connection, company_id=company_id, client_key=client_key,
                status=checkout_idempotency.STATUS_PERSISTED, mp_resource_type='payment',
                mp_id=result.get('payment_id'), result=result)
            connection.commit()
        except Exception as exc:
            connection.rollback()
            structured_log('error', 'checkout.persist_failed', error=str(exc))
            persist_pending = {'ok': False, 'error': {
                'code': 'CHECKOUT_PERSIST_PENDING',
                'message': 'Pagamento iniciado; reconciliação pendente. Repita com a MESMA idempotency_key.'}}
            send_json(handler, 503, persist_pending)
            return 503, persist_pending
        return send_json(handler, 201, {'ok': True, 'payment': result})


def handle_post_pix(handler, parsed, payload, match):
    return _handle_authenticated_oneoff(handler, parsed, payload, 'pix')


def handle_post_boleto(handler, parsed, payload, match):
    return _handle_authenticated_oneoff(handler, parsed, payload, 'bolbradesco')


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
