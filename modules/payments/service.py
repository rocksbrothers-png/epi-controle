"""Serviços de pagamento/assinatura via Mercado Pago.

Concentra toda a lógica sensível (uso do Access Token, criação de planos,
assinaturas e pagamentos, tratamento de webhook e consulta de status) no
backend. O frontend apenas chama os endpoints HTTP definidos em routes.py.

Persistência:
  - payment_plans  → planos / preapproval plans criados no Mercado Pago.
  - payments       → assinaturas e pagamentos (cartão, Pix, boleto), com
                     company_id, plan_id, payer_email, payment_method e status.
"""

import hashlib
import hmac
import json
from datetime import datetime, timezone

from epi_backend.config import (
    MERCADO_PAGO_ENV,
    MERCADO_PAGO_PUBLIC_KEY,
    MERCADO_PAGO_WEBHOOK_SECRET,
    WEB_APP_URL,
    WEB_BASE_URL,
)
from epi_backend.db import row_to_dict
from epi_backend.http_utils import structured_log
from modules.payments import mp_client
from modules.payments.mp_client import MercadoPagoError

UTC = timezone.utc

PAYMENT_METHODS = {"card", "pix", "boleto", "subscription"}


def _now_iso():
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


# ── Schema ──────────────────────────────────────────────────────────────────

def ensure_payment_tables(connection):
    connection.executescript(
        '''
        CREATE TABLE IF NOT EXISTS payment_plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER,
            plan_key TEXT NOT NULL DEFAULT '',
            mp_plan_id TEXT NOT NULL DEFAULT '',
            reason TEXT NOT NULL DEFAULT '',
            amount REAL NOT NULL DEFAULT 0,
            currency TEXT NOT NULL DEFAULT 'BRL',
            frequency INTEGER NOT NULL DEFAULT 1,
            frequency_type TEXT NOT NULL DEFAULT 'months',
            status TEXT NOT NULL DEFAULT 'pending',
            init_point TEXT NOT NULL DEFAULT '',
            raw_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER,
            plan_id TEXT NOT NULL DEFAULT '',
            mp_payment_id TEXT NOT NULL DEFAULT '',
            mp_resource_type TEXT NOT NULL DEFAULT 'payment',
            payer_email TEXT NOT NULL DEFAULT '',
            payment_method TEXT NOT NULL DEFAULT '',
            amount REAL NOT NULL DEFAULT 0,
            currency TEXT NOT NULL DEFAULT 'BRL',
            status TEXT NOT NULL DEFAULT 'pending',
            status_detail TEXT NOT NULL DEFAULT '',
            external_reference TEXT NOT NULL DEFAULT '',
            qr_code TEXT NOT NULL DEFAULT '',
            qr_code_base64 TEXT NOT NULL DEFAULT '',
            ticket_url TEXT NOT NULL DEFAULT '',
            raw_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_payments_mp_payment_id ON payments(mp_payment_id);
        CREATE INDEX IF NOT EXISTS idx_payments_company_id ON payments(company_id);
        CREATE INDEX IF NOT EXISTS idx_payment_plans_mp_plan_id ON payment_plans(mp_plan_id);
        '''
    )
    # Tabelas criadas antes da coluna plan_key (PR inicial) recebem o ALTER
    # idempotente. SQLite (testes) não suporta IF NOT EXISTS no ADD COLUMN e já
    # cria a coluna no CREATE acima, então o erro é ignorado com segurança.
    # IMPORTANTE: o ALTER precisa rodar ANTES de indexar plan_key — senão, em
    # bases antigas (sem a coluna) o CREATE INDEX aborta o bootstrap (503).
    try:
        connection.execute(
            "ALTER TABLE payment_plans ADD COLUMN IF NOT EXISTS plan_key TEXT NOT NULL DEFAULT ''"
        )
    except Exception:
        try:
            connection.rollback()
        except Exception:
            pass
    # Índice de plan_key só depois de garantir que a coluna existe.
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_payment_plans_plan_key ON payment_plans(plan_key)"
    )


# Colunas evolutivas das tabelas de assinatura: (tabela, coluna, definição).
# Aplicadas de forma idempotente para bases criadas antes destes campos.
# Booleanos usam INTEGER 0/1 por compatibilidade SQLite (testes) / Postgres.
_SUBSCRIPTION_EVOLUTION_COLUMNS = (
    ("subscriptions", "tenant_id", "TEXT NOT NULL DEFAULT ''"),
    ("subscriptions", "payment_cycle", "TEXT NOT NULL DEFAULT 'monthly'"),
    ("subscriptions", "payment_method", "TEXT NOT NULL DEFAULT 'card'"),
    ("subscriptions", "is_recurring", "INTEGER NOT NULL DEFAULT 1"),
    ("subscriptions", "preapproval_id", "TEXT NOT NULL DEFAULT ''"),
    ("subscriptions", "preapproval_plan_id", "TEXT NOT NULL DEFAULT ''"),
    ("subscriptions", "mp_status", "TEXT NOT NULL DEFAULT ''"),
    ("subscriptions", "renewal_date", "TEXT NOT NULL DEFAULT ''"),
    ("subscriptions", "next_payment_date", "TEXT NOT NULL DEFAULT ''"),
    ("subscriptions", "last_payment_date", "TEXT NOT NULL DEFAULT ''"),
    ("subscriptions", "cancel_date", "TEXT NOT NULL DEFAULT ''"),
    ("subscriptions", "cancel_reason", "TEXT NOT NULL DEFAULT ''"),
    ("subscriptions", "created_by", "INTEGER"),
    ("subscriptions", "updated_by", "INTEGER"),
    ("invoices", "tenant_id", "TEXT NOT NULL DEFAULT ''"),
    ("invoices", "receipt_url", "TEXT NOT NULL DEFAULT ''"),
    ("invoices", "invoice_url", "TEXT NOT NULL DEFAULT ''"),
)


def ensure_subscription_tables(connection):
    """Cria as tabelas de assinaturas/faturas/auditoria (idempotente).

    Modelo descrito em docs/ARQUITETURA_ASSINATURAS.md. Mantém `payments` e
    `payment_plans` intactas; estas tabelas consolidam o ciclo de vida de
    assinaturas recorrentes, o histórico financeiro e a trilha de auditoria.
    """
    connection.executescript(
        '''
        CREATE TABLE IF NOT EXISTS subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER,
            tenant_id TEXT NOT NULL DEFAULT '',
            subscription_id TEXT NOT NULL DEFAULT '',
            plan_key TEXT NOT NULL DEFAULT '',
            payment_cycle TEXT NOT NULL DEFAULT 'monthly',
            payment_method TEXT NOT NULL DEFAULT 'card',
            is_recurring INTEGER NOT NULL DEFAULT 1,
            preapproval_id TEXT NOT NULL DEFAULT '',
            preapproval_plan_id TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'pending',
            mp_status TEXT NOT NULL DEFAULT '',
            amount REAL NOT NULL DEFAULT 0,
            currency TEXT NOT NULL DEFAULT 'BRL',
            renewal_date TEXT NOT NULL DEFAULT '',
            next_payment_date TEXT NOT NULL DEFAULT '',
            last_payment_date TEXT NOT NULL DEFAULT '',
            cancel_date TEXT NOT NULL DEFAULT '',
            cancel_reason TEXT NOT NULL DEFAULT '',
            created_by INTEGER,
            updated_by INTEGER,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subscription_id TEXT NOT NULL DEFAULT '',
            company_id INTEGER,
            tenant_id TEXT NOT NULL DEFAULT '',
            mp_payment_id TEXT NOT NULL DEFAULT '',
            payment_method TEXT NOT NULL DEFAULT '',
            amount REAL NOT NULL DEFAULT 0,
            currency TEXT NOT NULL DEFAULT 'BRL',
            status TEXT NOT NULL DEFAULT 'pending',
            due_date TEXT NOT NULL DEFAULT '',
            paid_at TEXT NOT NULL DEFAULT '',
            receipt_url TEXT NOT NULL DEFAULT '',
            invoice_url TEXT NOT NULL DEFAULT '',
            raw_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS subscription_audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subscription_id TEXT NOT NULL DEFAULT '',
            action TEXT NOT NULL DEFAULT '',
            actor_user_id INTEGER,
            company_id INTEGER,
            tenant_id TEXT NOT NULL DEFAULT '',
            ip TEXT NOT NULL DEFAULT '',
            detail_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL
        );
        '''
    )
    # Evolução idempotente de bases antigas: garante as colunas ANTES de indexar.
    # SQLite (testes) não suporta IF NOT EXISTS no ADD COLUMN e já cria as colunas
    # no CREATE acima, então o erro é ignorado com segurança.
    for table, column, definition in _SUBSCRIPTION_EVOLUTION_COLUMNS:
        try:
            connection.execute(
                f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column} {definition}"
            )
        except Exception:
            try:
                connection.rollback()
            except Exception:
                pass
    # Índices só depois de garantir que as colunas existem.
    connection.executescript(
        '''
        CREATE INDEX IF NOT EXISTS idx_subscriptions_company ON subscriptions(company_id);
        CREATE INDEX IF NOT EXISTS idx_subscriptions_status ON subscriptions(status);
        CREATE INDEX IF NOT EXISTS idx_subscriptions_subscription_id ON subscriptions(subscription_id);
        CREATE INDEX IF NOT EXISTS idx_subscriptions_preapproval_id ON subscriptions(preapproval_id);
        CREATE INDEX IF NOT EXISTS idx_invoices_subscription ON invoices(subscription_id);
        CREATE INDEX IF NOT EXISTS idx_invoices_company ON invoices(company_id);
        CREATE INDEX IF NOT EXISTS idx_invoices_mp_payment_id ON invoices(mp_payment_id);
        CREATE INDEX IF NOT EXISTS idx_sub_audit_subscription ON subscription_audit_logs(subscription_id);
        CREATE INDEX IF NOT EXISTS idx_sub_audit_company ON subscription_audit_logs(company_id);
        '''
    )


# ── Config pública (segura para o frontend) ───────────────────────────────────

def public_config():
    """Dados seguros para o frontend. NUNCA inclui o Access Token."""
    return {
        "public_key": MERCADO_PAGO_PUBLIC_KEY,
        "environment": MERCADO_PAGO_ENV,
        "web_base_url": WEB_BASE_URL,
        "web_app_url": WEB_APP_URL,
    }


# ── Persistência ──────────────────────────────────────────────────────────────

def _record_payment(connection, *, company_id, plan_id, mp_payment_id, resource_type,
                    payer_email, payment_method, amount, currency, status, status_detail,
                    external_reference, qr_code, qr_code_base64, ticket_url, raw):
    now = _now_iso()
    connection.execute(
        '''
        INSERT INTO payments (
            company_id, plan_id, mp_payment_id, mp_resource_type, payer_email,
            payment_method, amount, currency, status, status_detail,
            external_reference, qr_code, qr_code_base64, ticket_url, raw_json,
            created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''',
        (
            company_id, str(plan_id or ''), str(mp_payment_id or ''), resource_type,
            str(payer_email or ''), payment_method, float(amount or 0), currency,
            str(status or 'pending'), str(status_detail or ''), str(external_reference or ''),
            str(qr_code or ''), str(qr_code_base64 or ''), str(ticket_url or ''),
            json.dumps(raw, ensure_ascii=False), now, now,
        ),
    )
    structured_log(
        'info', 'payments.recorded',
        company_id=company_id, plan_id=plan_id, mp_payment_id=mp_payment_id,
        payment_method=payment_method, status=status,
    )


def _update_payment_status(connection, *, mp_payment_id, resource_type, status,
                           status_detail='', raw=None):
    now = _now_iso()
    connection.execute(
        '''
        UPDATE payments
           SET status = ?, status_detail = ?, raw_json = ?, updated_at = ?
         WHERE mp_payment_id = ? AND mp_resource_type = ?
        ''',
        (
            str(status or ''), str(status_detail or ''),
            json.dumps(raw or {}, ensure_ascii=False), now,
            str(mp_payment_id), resource_type,
        ),
    )
    structured_log(
        'info', 'payments.status_updated',
        mp_payment_id=mp_payment_id, resource_type=resource_type, status=status,
    )


def get_payment_by_mp_id(connection, mp_payment_id, resource_type='payment'):
    row = connection.execute(
        'SELECT * FROM payments WHERE mp_payment_id = ? AND mp_resource_type = ? ORDER BY id DESC LIMIT 1',
        (str(mp_payment_id), resource_type),
    ).fetchone()
    return row_to_dict(row) if row else None


# ── Helpers de validação de entrada ───────────────────────────────────────────

def _coerce_company_id(value):
    if value in (None, ''):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        raise ValueError('company_id inválido.')


def _require(payload, field):
    value = payload.get(field)
    if value in (None, ''):
        raise ValueError(f'Campo obrigatório: {field}')
    return value


# ── Planos / preapproval plans ────────────────────────────────────────────────

def create_preapproval_plan(connection, payload):
    """Cria um preapproval_plan no Mercado Pago e persiste localmente."""
    reason = _require(payload, 'reason')
    amount = float(_require(payload, 'amount'))
    currency = str(payload.get('currency') or 'BRL')
    frequency = int(payload.get('frequency') or 1)
    frequency_type = str(payload.get('frequency_type') or 'months')
    company_id = _coerce_company_id(payload.get('company_id'))
    plan_key = str(payload.get('plan_key') or '').strip().lower()

    back_url = str(payload.get('back_url') or WEB_APP_URL or WEB_BASE_URL or '')
    body = {
        'reason': reason,
        'auto_recurring': {
            'frequency': frequency,
            'frequency_type': frequency_type,
            'transaction_amount': amount,
            'currency_id': currency,
        },
        'payment_methods_allowed': {
            'payment_types': [{'id': 'credit_card'}],
        },
    }
    if back_url:
        body['back_url'] = back_url

    result = mp_client.post('/preapproval_plan', body)
    mp_plan_id = str(result.get('id') or '')
    status = str(result.get('status') or 'pending')
    init_point = str(result.get('init_point') or '')

    now = _now_iso()
    connection.execute(
        '''
        INSERT INTO payment_plans (
            company_id, plan_key, mp_plan_id, reason, amount, currency, frequency,
            frequency_type, status, init_point, raw_json, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''',
        (
            company_id, plan_key, mp_plan_id, reason, amount, currency, frequency,
            frequency_type, status, init_point,
            json.dumps(result, ensure_ascii=False), now, now,
        ),
    )
    structured_log('info', 'payments.plan_created', company_id=company_id, plan_key=plan_key, mp_plan_id=mp_plan_id, status=status)
    return {
        'plan_id': mp_plan_id,
        'plan_key': plan_key,
        'status': status,
        'init_point': init_point,
        'reason': reason,
        'amount': amount,
    }


# Catálogo canônico de planos de assinatura — fonte única de verdade no
# backend, consumida pelo site institucional, pelo checkout e pelos apps
# (Flutter Web/Android/iOS). Preços em BRL. O ciclo anual concede 2 meses
# grátis (preço anual = 10 × mensal). Enterprise é "sob consulta" (contato
# comercial), portanto não é comprável diretamente pelo checkout.
SUBSCRIPTION_PLANS = {
    'start': {
        'label': 'START',
        'max_users': 10,
        'prices': {'monthly': 297.00, 'annual': 2970.00},
        'contact_only': False,
    },
    'business': {
        'label': 'BUSINESS',
        'max_users': 25,
        'prices': {'monthly': 597.00, 'annual': 5970.00},
        'contact_only': False,
    },
    'corporate': {
        'label': 'CORPORATE',
        'max_users': 100,
        'prices': {'monthly': 1297.00, 'annual': 12970.00},
        'highlight': True,
        'contact_only': False,
    },
    'enterprise': {
        'label': 'ENTERPRISE',
        'max_users': None,
        'prices': {},
        'contact_only': True,
    },
}

# Ciclos aceitos na query string do site → frequência do Mercado Pago.
CYCLE_ALIASES = {
    'monthly': 'monthly', 'mensal': 'monthly', 'month': 'monthly',
    'annual': 'annual', 'anual': 'annual', 'yearly': 'annual', 'year': 'annual',
}


def normalize_cycle(value):
    return CYCLE_ALIASES.get(str(value or '').strip().lower(), 'monthly')


def _mp_plan_ids_by_key(connection):
    """Mapa {(plan_key, frequency_type): mp_plan_id} a partir dos preapproval
    plans já criados no Mercado Pago."""
    rows = connection.execute(
        "SELECT plan_key, frequency_type, mp_plan_id FROM payment_plans "
        "WHERE mp_plan_id <> '' ORDER BY id ASC"
    ).fetchall()
    mapping = {}
    for row in rows:
        item = row_to_dict(row)
        key = str(item.get('plan_key') or '').lower()
        freq_type = str(item.get('frequency_type') or 'months')
        cycle = 'annual' if freq_type in ('years', 'year') else 'monthly'
        mapping[(key, cycle)] = str(item.get('mp_plan_id') or '')
    return mapping


def list_public_catalog(connection, cycle='monthly'):
    """Catálogo público de planos para o site/app (fonte única no backend).

    Expõe apenas campos seguros — sem Access Token, sem dados internos. Cada
    item traz o preço do ciclo solicitado e, quando já existe um preapproval
    plan correspondente no Mercado Pago, o respectivo plan_id (para assinatura
    com cartão).
    """
    cycle = normalize_cycle(cycle)
    mp_ids = _mp_plan_ids_by_key(connection)
    catalog = []
    for key, plan in SUBSCRIPTION_PLANS.items():
        amount = plan.get('prices', {}).get(cycle)
        catalog.append({
            'key': key,
            'label': plan['label'],
            'reason': f"EPI Controle {plan['label']}",
            'max_users': plan.get('max_users'),
            'cycle': cycle,
            'amount': float(amount) if amount is not None else None,
            'currency': 'BRL',
            'contact_only': bool(plan.get('contact_only')),
            'highlight': bool(plan.get('highlight')),
            'plan_id': mp_ids.get((key, cycle), ''),
        })
    return catalog


def list_plans(connection, company_id=None):
    if company_id is None:
        rows = connection.execute(
            'SELECT * FROM payment_plans ORDER BY id DESC'
        ).fetchall()
    else:
        rows = connection.execute(
            'SELECT * FROM payment_plans WHERE company_id = ? ORDER BY id DESC',
            (int(company_id),),
        ).fetchall()
    return [row_to_dict(row) for row in rows]


# ── Assinatura com cartão (preapproval) ───────────────────────────────────────

def create_card_subscription(connection, payload):
    """Cria uma assinatura (preapproval) vinculada a um cartão tokenizado.

    O cartão é tokenizado no frontend com a Public Key; o backend recebe apenas
    o card_token (não os dados do cartão).
    """
    plan_id = _require(payload, 'plan_id')
    payer_email = _require(payload, 'payer_email')
    card_token = _require(payload, 'card_token')
    company_id = _coerce_company_id(payload.get('company_id'))
    external_reference = str(payload.get('external_reference') or '')

    body = {
        'preapproval_plan_id': str(plan_id),
        'payer_email': str(payer_email),
        'card_token_id': str(card_token),
        'status': 'authorized',
    }
    if external_reference:
        body['external_reference'] = external_reference
    # Permite sobrescrever valor/recorrência quando não atrelado a um plano fixo.
    if payload.get('amount'):
        body['auto_recurring'] = {
            'frequency': int(payload.get('frequency') or 1),
            'frequency_type': str(payload.get('frequency_type') or 'months'),
            'transaction_amount': float(payload['amount']),
            'currency_id': str(payload.get('currency') or 'BRL'),
        }
        body.pop('preapproval_plan_id', None)
        body['reason'] = str(payload.get('reason') or 'Assinatura EPI Controle')

    result = mp_client.post('/preapproval', body)
    mp_id = str(result.get('id') or '')
    status = str(result.get('status') or 'pending')
    amount = float((result.get('auto_recurring') or {}).get('transaction_amount') or payload.get('amount') or 0)

    _record_payment(
        connection,
        company_id=company_id, plan_id=plan_id, mp_payment_id=mp_id,
        resource_type='preapproval', payer_email=payer_email,
        payment_method='subscription', amount=amount, currency='BRL',
        status=status, status_detail='', external_reference=external_reference,
        qr_code='', qr_code_base64='', ticket_url=str(result.get('init_point') or ''),
        raw=result,
    )
    return {
        'subscription_id': mp_id,
        'status': status,
        'init_point': str(result.get('init_point') or ''),
        'payment_method': 'subscription',
    }


# ── Pagamentos avulsos (Pix / boleto) ─────────────────────────────────────────

def _build_payer(payload):
    payer = {'email': str(_require(payload, 'payer_email'))}
    first_name = payload.get('payer_first_name')
    last_name = payload.get('payer_last_name')
    if first_name:
        payer['first_name'] = str(first_name)
    if last_name:
        payer['last_name'] = str(last_name)
    doc_type = payload.get('payer_doc_type')
    doc_number = payload.get('payer_doc_number')
    if doc_type and doc_number:
        payer['identification'] = {'type': str(doc_type), 'number': str(doc_number)}
    return payer


def _create_payment(connection, payload, method_id):
    amount = float(_require(payload, 'amount'))
    payer_email = _require(payload, 'payer_email')
    plan_id = str(payload.get('plan_id') or '')
    company_id = _coerce_company_id(payload.get('company_id'))
    external_reference = str(payload.get('external_reference') or '')
    description = str(payload.get('description') or 'Pagamento EPI Controle')

    body = {
        'transaction_amount': amount,
        'description': description,
        'payment_method_id': method_id,
        'payer': _build_payer(payload),
    }
    if external_reference:
        body['external_reference'] = external_reference

    result = mp_client.post('/v1/payments', body)
    mp_id = str(result.get('id') or '')
    status = str(result.get('status') or 'pending')
    status_detail = str(result.get('status_detail') or '')

    transaction_data = ((result.get('point_of_interaction') or {}).get('transaction_data') or {})
    qr_code = str(transaction_data.get('qr_code') or '')
    qr_code_base64 = str(transaction_data.get('qr_code_base64') or '')
    ticket_url = str(
        transaction_data.get('ticket_url')
        or (result.get('transaction_details') or {}).get('external_resource_url')
        or ''
    )

    _record_payment(
        connection,
        company_id=company_id, plan_id=plan_id, mp_payment_id=mp_id,
        resource_type='payment', payer_email=payer_email,
        payment_method=('pix' if method_id == 'pix' else 'boleto'),
        amount=amount, currency=str(result.get('currency_id') or 'BRL'),
        status=status, status_detail=status_detail, external_reference=external_reference,
        qr_code=qr_code, qr_code_base64=qr_code_base64, ticket_url=ticket_url,
        raw=result,
    )
    return {
        'payment_id': mp_id,
        'status': status,
        'status_detail': status_detail,
        'payment_method': ('pix' if method_id == 'pix' else 'boleto'),
        'qr_code': qr_code,
        'qr_code_base64': qr_code_base64,
        'ticket_url': ticket_url,
    }


def create_pix_payment(connection, payload):
    return _create_payment(connection, payload, 'pix')


def create_boleto_payment(connection, payload):
    return _create_payment(connection, payload, 'bolbradesco')


# ── Consulta de status ────────────────────────────────────────────────────────

def fetch_payment_status(connection, mp_payment_id, resource_type='payment'):
    """Consulta o status atual no Mercado Pago e atualiza o registro local."""
    resource_type = 'preapproval' if resource_type == 'preapproval' else 'payment'
    path = (
        f'/preapproval/{mp_payment_id}'
        if resource_type == 'preapproval'
        else f'/v1/payments/{mp_payment_id}'
    )
    result = mp_client.get(path)
    status = str(result.get('status') or '')
    status_detail = str(result.get('status_detail') or '')

    existing = get_payment_by_mp_id(connection, mp_payment_id, resource_type)
    if existing:
        _update_payment_status(
            connection, mp_payment_id=mp_payment_id, resource_type=resource_type,
            status=status, status_detail=status_detail, raw=result,
        )
    return {
        'payment_id': str(mp_payment_id),
        'resource_type': resource_type,
        'status': status,
        'status_detail': status_detail,
        'persisted': bool(existing),
    }


# ── Webhook ───────────────────────────────────────────────────────────────────

def verify_webhook_signature(headers, query):
    """Valida a assinatura x-signature do Mercado Pago (quando o segredo está
    configurado). Retorna True quando válida ou quando a validação não está
    habilitada; False quando a assinatura é inválida."""
    if not MERCADO_PAGO_WEBHOOK_SECRET:
        return True
    signature = str(headers.get('x-signature', '') or headers.get('X-Signature', '')).strip()
    request_id = str(headers.get('x-request-id', '') or headers.get('X-Request-Id', '')).strip()
    if not signature:
        return False
    parts = {}
    for item in signature.split(','):
        if '=' in item:
            key, value = item.split('=', 1)
            parts[key.strip()] = value.strip()
    ts = parts.get('ts')
    received_hash = parts.get('v1')
    if not ts or not received_hash:
        return False
    data_id = ''
    if isinstance(query, dict):
        raw_id = query.get('data.id') or query.get('id')
        if isinstance(raw_id, list):
            data_id = raw_id[0] if raw_id else ''
        else:
            data_id = raw_id or ''
    manifest = f'id:{str(data_id).lower()};request-id:{request_id};ts:{ts};'
    expected = hmac.new(
        MERCADO_PAGO_WEBHOOK_SECRET.encode('utf-8'),
        manifest.encode('utf-8'),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, received_hash)


def handle_webhook(connection, payload, query):
    """Processa uma notificação do Mercado Pago.

    Identifica o tipo (payment / preapproval), busca o recurso atualizado e
    sincroniza o status no banco.
    """
    payload = payload or {}
    query = query or {}

    def _q(name):
        value = query.get(name)
        if isinstance(value, list):
            return value[0] if value else ''
        return value or ''

    topic = str(
        payload.get('type') or payload.get('topic') or _q('type') or _q('topic') or ''
    ).lower()
    data = payload.get('data') or {}
    resource_id = str(data.get('id') or payload.get('id') or _q('data.id') or _q('id') or '')

    structured_log('info', 'payments.webhook_received', topic=topic, resource_id=resource_id)

    if not resource_id:
        return {'ok': True, 'ignored': True, 'reason': 'sem resource_id'}

    if 'preapproval' in topic or 'subscription' in topic:
        resource_type = 'preapproval'
    else:
        resource_type = 'payment'

    try:
        status_info = fetch_payment_status(connection, resource_id, resource_type)
    except MercadoPagoError as exc:
        structured_log('warning', 'payments.webhook_fetch_failed', resource_id=resource_id, error=str(exc))
        return {'ok': True, 'synced': False, 'reason': str(exc)}

    return {'ok': True, 'synced': True, 'status': status_info.get('status'), 'resource_type': resource_type}
