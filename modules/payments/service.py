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
import re
from datetime import datetime, timezone
from urllib.parse import quote

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

# A RLS destas cinco tabelas mora em `supabase/migrations/20260827000000_billing_rls.sql`
# e no par `epi_backend/migrations/028_billing_rls.py` — #309. Até então era
# aplicada aqui por `_enable_rls`, que rodava em todo boot mas não era
# migration: não entrava em `app_migrations` e era invisível a qualquer gate
# derivado de migrations. Não recolocar DDL de RLS neste arquivo: existe gate
# estático proibindo `ENABLE ROW LEVEL SECURITY` e `CREATE POLICY` em
# `modules/`, `core/` e `app.py`.
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
    # Segurança: nega acesso público via PostgREST (RLS sem políticas).


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
    # origin: como o binding empresa/tenant foi estabelecido. No Corporate só
    # existe 'authenticated' (ator logado via Bearer); vazio = linha legada,
    # anterior ao binding server-side (1G-C, #1009/#1010). Coluna não-RLS: a
    # evolução idempotente dispensa migration (RLS de subscriptions já mora em
    # 028_billing_rls.py; o gate #309 proíbe apenas DDL de RLS em modules/).
    ("subscriptions", "origin", "TEXT NOT NULL DEFAULT ''"),
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
            origin TEXT NOT NULL DEFAULT '',
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
    # Segurança: nega acesso público via PostgREST (RLS sem políticas).


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


# ── Checkout autenticado seguro (preço server-side) ───────────────────────────
#
# Estas funções atendem o checkout autenticado do Corporate (1G-C, #1009/#1010).
# O PREÇO vem EXCLUSIVAMENTE do catálogo server-side (SUBSCRIPTION_PLANS) e o
# preapproval_plan do Mercado Pago é resolvido por mapeamento server-side — o
# cliente NUNCA informa `amount`/`plan_id`. A `company_id` é resolvida pelo
# chamador a partir da IDENTIDADE AUTENTICADA (Bearer), nunca do corpo.
#
# Propriedade COMPARTILHADA com o SaaS (PR #391): preço server-side por
# (plan_key, cycle). DIVERGÊNCIA INTENCIONAL: o SaaS resolve a empresa por uma
# capability de signup público (token opaco emitido no cadastro); o Corporate a
# resolve pela identidade autenticada. Por isso o Corporate NÃO introduz essa
# capability (§14).

def resolve_catalog_plan(plan_key, cycle):
    """Resolve (preço, rótulo) de um plano comprável a partir do catálogo.

    Levanta ValueError para plano inexistente, ciclo inválido, ciclo sem preço,
    ou plano `contact_only` (enterprise — não comprável pelo checkout).
    """
    key = str(plan_key or '').strip().lower()
    cyc = normalize_cycle(cycle)
    if str(cycle or '').strip().lower() not in ('monthly', 'annual', 'mensal', 'anual',
                                                'month', 'year', 'yearly'):
        raise ValueError('Ciclo inválido.')
    plan = SUBSCRIPTION_PLANS.get(key)
    if not plan:
        raise ValueError('Plano inexistente.')
    if plan.get('contact_only'):
        raise ValueError('Plano sob consulta (enterprise) não é comprável por este checkout.')
    amount = (plan.get('prices') or {}).get(cyc)
    if amount is None:
        raise ValueError('Ciclo indisponível para este plano.')
    return {'plan_key': key, 'cycle': cyc, 'amount': float(amount), 'label': plan['label']}


def _cycle_recurrence(cycle):
    """(frequency, frequency_type) do Mercado Pago para o ciclo do catálogo."""
    return (1, 'years') if normalize_cycle(cycle) == 'annual' else (1, 'months')


def create_catalog_card_subscription(connection, *, plan_key, cycle, payer_email,
                                     card_token, company_id, external_reference='',
                                     idempotency_key=None):
    """Cria uma assinatura (preapproval) com preço server-side (catálogo).

    `company_id` já vem resolvido da identidade autenticada (Bearer) — nunca do
    corpo. O cliente informa apenas plan_key/cycle/payer_email/card_token.
    """
    plan = resolve_catalog_plan(plan_key, cycle)
    if not str(payer_email or '').strip():
        raise ValueError('Campo obrigatório: payer_email')
    if not str(card_token or '').strip():
        raise ValueError('Campo obrigatório: card_token')

    mp_plan_id = _mp_plan_ids_by_key(connection).get((plan['plan_key'], plan['cycle']), '')
    body = {
        'payer_email': str(payer_email),
        'card_token_id': str(card_token),
        'status': 'authorized',
    }
    if external_reference:
        body['external_reference'] = str(external_reference)
    if mp_plan_id:
        # Preço vive no preapproval_plan do MP (criado pelo master com o preço do
        # catálogo). O cliente não o informa: resolvido server-side.
        body['preapproval_plan_id'] = str(mp_plan_id)
    else:
        # Sem preapproval_plan configurado: preço do catálogo server-side.
        frequency, frequency_type = _cycle_recurrence(plan['cycle'])
        body['reason'] = f"EPI Controle {plan['label']}"
        body['auto_recurring'] = {
            'frequency': frequency,
            'frequency_type': frequency_type,
            'transaction_amount': plan['amount'],
            'currency_id': 'BRL',
        }

    # idempotency_key → X-Idempotency-Key do MP (1J-C): mesma intenção/retry →
    # mesmo preapproval; namespaced por empresa pelo chamador. Sem a chave, o
    # mp_client geraria um uuid4() novo por chamada (o furo do #392).
    result = mp_client.post('/preapproval', body, idempotency_key=idempotency_key)
    mp_id = str(result.get('id') or '')
    status = str(result.get('status') or 'pending')

    _record_payment(
        connection,
        company_id=company_id, plan_id=plan['plan_key'], mp_payment_id=mp_id,
        resource_type='preapproval', payer_email=payer_email,
        payment_method='subscription', amount=plan['amount'], currency='BRL',
        status=status, status_detail='', external_reference=external_reference,
        qr_code='', qr_code_base64='', ticket_url=str(result.get('init_point') or ''),
        raw=result,
    )
    return {
        'subscription_id': mp_id,
        'status': status,
        'init_point': str(result.get('init_point') or ''),
        'payment_method': 'subscription',
        'preapproval_plan_id': str(mp_plan_id or ''),
        'amount': plan['amount'],
        'plan_key': plan['plan_key'],
        'cycle': plan['cycle'],
    }


def create_catalog_oneoff_payment(connection, *, method_id, plan_key, cycle,
                                  company_id, payer_payload, external_reference='',
                                  idempotency_key=None):
    """Cria um pagamento avulso (Pix/boleto) com preço server-side (catálogo).

    `company_id` vem da identidade autenticada; o preço, do catálogo. O cliente
    não informa `amount`.
    """
    plan = resolve_catalog_plan(plan_key, cycle)
    body = {
        'transaction_amount': plan['amount'],
        'description': f"Assinatura EPI Controle — {plan['label']}",
        'payment_method_id': method_id,
        'payer': _build_payer(payer_payload),
    }
    if external_reference:
        body['external_reference'] = str(external_reference)

    # idempotency_key → X-Idempotency-Key do MP (1J-C): retry da mesma intenção
    # não gera um segundo pagamento; namespaced por empresa pelo chamador.
    result = mp_client.post('/v1/payments', body, idempotency_key=idempotency_key)
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
        company_id=company_id, plan_id=plan['plan_key'], mp_payment_id=mp_id,
        resource_type='payment', payer_email=payer_payload.get('payer_email'),
        payment_method=('pix' if method_id == 'pix' else 'boleto'),
        amount=plan['amount'], currency=str(result.get('currency_id') or 'BRL'),
        status=status, status_detail=status_detail, external_reference=external_reference,
        qr_code=qr_code, qr_code_base64=qr_code_base64, ticket_url=ticket_url,
        raw=result,
    )
    return {
        'payment_id': mp_id, 'status': status, 'status_detail': status_detail,
        'payment_method': ('pix' if method_id == 'pix' else 'boleto'),
        'qr_code': qr_code, 'qr_code_base64': qr_code_base64, 'ticket_url': ticket_url,
        'amount': plan['amount'], 'plan_key': plan['plan_key'], 'cycle': plan['cycle'],
    }


# ── Identificadores do Mercado Pago (validação estrita) ───────────────────────
#
# O id recebido do cliente (status) ou da notificação (webhook) entra no caminho
# de uma chamada autenticada com o Access Token do lojista. Só formatos exatos
# passam: id de pagamento é numérico; id de preapproval é alfanumérico. Nada de
# '/', '.', '?', '#', '%', espaço ou unicode — path traversal e manipulação de
# URL ficam impossíveis antes mesmo da codificação do segmento.
RESOURCE_TYPES = ('payment', 'preapproval')
_RESOURCE_ID_PATTERNS = {
    'payment': re.compile(r'[0-9]{1,20}'),
    'preapproval': re.compile(r'[A-Za-z0-9]{1,64}'),
}
# Valores de status/status_detail do Mercado Pago são códigos curtos
# (ex.: 'approved', 'cc_rejected_bad_filled_card_number'). Qualquer outra coisa
# (objeto, lista, texto livre) não é ecoada ao cliente.
_STATUS_VALUE_RE = re.compile(r'[A-Za-z0-9_\-]{1,64}')

# Escopo interno (webhook assinado): sem restrição de empresa, porque a
# associação vem só do registro local (company_id gravado na criação).
ANY_COMPANY = object()


class PaymentNotFoundError(LookupError):
    """Pagamento desconhecido localmente ou de outra empresa → 404 genérico."""


def normalize_resource_type(value):
    raw = str(value if value is not None else '').strip()
    if raw == '':
        return 'payment'
    if raw not in RESOURCE_TYPES:
        raise ValueError('resource_type inválido.')
    return raw


def validate_mp_resource_id(value, resource_type):
    """Devolve o id como texto se casar exatamente com o formato do tipo."""
    if not isinstance(value, (str, int)) or isinstance(value, bool):
        raise ValueError('Identificador de pagamento inválido.')
    raw = str(value)
    if not _RESOURCE_ID_PATTERNS[resource_type].fullmatch(raw):
        raise ValueError('Identificador de pagamento inválido.')
    return raw


def _mp_resource_path(resource_id, resource_type):
    # Defesa em profundidade: o id já foi validado, e o segmento ainda é
    # codificado (nenhum caractere reservado sobrevive como separador).
    segment = quote(validate_mp_resource_id(resource_id, resource_type), safe='')
    return f'/preapproval/{segment}' if resource_type == 'preapproval' else f'/v1/payments/{segment}'


def _status_value(value):
    if isinstance(value, str) and _STATUS_VALUE_RE.fullmatch(value):
        return value
    return ''


def local_payment_owner(connection, resource_id, resource_type):
    """Empresa dona do recurso segundo o banco local, ou None se desconhecido.

    Retorna {'company_id', 'payment_row'}; `payment_row` é a linha de
    `payments` (ou None quando só existe a assinatura em `subscriptions`).
    A posse NUNCA vem de dado enviado pelo cliente.
    """
    row = get_payment_by_mp_id(connection, resource_id, resource_type)
    if row:
        return {'company_id': row.get('company_id'), 'payment_row': row}
    if resource_type == 'preapproval':
        try:
            sub = connection.execute(
                'SELECT company_id FROM subscriptions WHERE preapproval_id = ? ORDER BY id DESC LIMIT 1',
                (str(resource_id),),
            ).fetchone()
        except Exception:  # pragma: no cover - tabela ausente em bases antigas
            sub = None
        if sub:
            return {'company_id': sub[0], 'payment_row': None}
    return None


def _same_company(owner_company_id, company_id):
    if company_id is ANY_COMPANY:
        return True
    if owner_company_id in (None, '') or company_id in (None, ''):
        return False
    try:
        return int(owner_company_id) == int(company_id)
    except (TypeError, ValueError):
        return False


_MP_UPDATED_FIELDS = ('date_last_updated', 'last_modified')


def _mp_updated_at(raw):
    """Data de última atualização informada pelo Mercado Pago (ou None)."""
    if not isinstance(raw, dict):
        return None
    for field in _MP_UPDATED_FIELDS:
        value = raw.get(field)
        if isinstance(value, str) and value:
            try:
                parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
            except ValueError:
                continue
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=UTC)
            return parsed
    return None


def _is_stale(previous_row, fresh):
    """True quando o estado recebido é mais antigo que o já gravado.

    Protege contra respostas fora de ordem (duas notificações concorrentes):
    um estado antigo nunca sobrescreve um mais novo.
    """
    if not previous_row:
        return False
    try:
        previous_raw = json.loads(previous_row.get('raw_json') or '{}')
    except (TypeError, ValueError):
        return False
    before, after = _mp_updated_at(previous_raw), _mp_updated_at(fresh)
    return bool(before and after and after < before)


# ── Consulta de status ────────────────────────────────────────────────────────

def fetch_payment_status(connection, mp_payment_id, resource_type='payment', *, company_id):
    """Consulta o status no Mercado Pago de um recurso CONHECIDO e da empresa.

    Ordem obrigatória: valida tipo e id, confirma no banco local que o recurso
    existe e pertence a `company_id` (ou `ANY_COMPANY`, só para o webhook
    assinado) e só então chama o Mercado Pago. Id desconhecido ou de outra
    empresa → `PaymentNotFoundError`, sem chamada externa.
    """
    resource_type = normalize_resource_type(resource_type)
    resource_id = validate_mp_resource_id(mp_payment_id, resource_type)
    owner = local_payment_owner(connection, resource_id, resource_type)
    if owner is None or not _same_company(owner['company_id'], company_id):
        raise PaymentNotFoundError('Pagamento não encontrado.')

    result = mp_client.get(_mp_resource_path(resource_id, resource_type))
    if not isinstance(result, dict):
        result = {}
    status = _status_value(result.get('status'))
    status_detail = _status_value(result.get('status_detail'))

    payment_row = owner['payment_row']
    stale = _is_stale(payment_row, result)
    if payment_row and not stale:
        _update_payment_status(
            connection, mp_payment_id=resource_id, resource_type=resource_type,
            status=status, status_detail=status_detail, raw=result,
        )
    if stale:
        structured_log('info', 'payments.status_stale_ignored',
                       mp_payment_id=resource_id, resource_type=resource_type)
        status = _status_value(payment_row.get('status'))
        status_detail = _status_value(payment_row.get('status_detail'))
    return {
        'payment_id': resource_id,
        'resource_type': resource_type,
        'status': status,
        'status_detail': status_detail,
        'persisted': bool(payment_row),
        'stale': stale,
    }


# ── Webhook ───────────────────────────────────────────────────────────────────

# Assinatura HMAC-SHA256 em hexadecimal (64 caracteres) e timestamp numérico.
_SIGNATURE_HASH_RE = re.compile(r'[0-9a-f]{64}')
_SIGNATURE_TS_RE = re.compile(r'[0-9]{1,20}')
_REQUEST_ID_RE = re.compile(r'[A-Za-z0-9\-_.:]{1,128}')
_WEBHOOK_TOPICS = {
    'payment': 'payment',
    'preapproval': 'preapproval',
    'subscription_preapproval': 'preapproval',
}


def webhook_secret_configured():
    return bool(MERCADO_PAGO_WEBHOOK_SECRET)


def _query_value(query, name):
    if not isinstance(query, dict):
        return ''
    value = query.get(name)
    if isinstance(value, list):
        value = value[0] if value else ''
    return value if isinstance(value, str) else ''


def signed_data_id(query):
    """O `data.id` que entra no manifesto assinado (query string da URL)."""
    return _query_value(query, 'data.id') or _query_value(query, 'id')


def verify_webhook_signature(headers, query):
    """Valida `x-signature` do Mercado Pago (manifesto oficial).

    manifesto = 'id:{data.id em minúsculas};request-id:{x-request-id};ts:{ts};'
    v1 = HMAC-SHA256(segredo, manifesto) em hexadecimal.

    Falha FECHADA: sem segredo disponível no processo, nenhuma notificação é
    aceita (retorna False). Assinatura ausente, malformada ou divergente → False.
    A comparação é em tempo constante.
    """
    secret = MERCADO_PAGO_WEBHOOK_SECRET
    if not secret:
        return False
    headers = headers or {}
    signature = str(headers.get('x-signature', '') or headers.get('X-Signature', '') or '').strip()
    request_id = str(headers.get('x-request-id', '') or headers.get('X-Request-Id', '') or '').strip()
    if not signature or len(signature) > 512:
        return False
    parts = {}
    for item in signature.split(','):
        if '=' not in item:
            return False
        key, value = item.split('=', 1)
        key = key.strip()
        if key in parts:
            return False  # chave repetida: ambíguo, recusa
        parts[key] = value.strip()
    ts = parts.get('ts', '')
    received_hash = parts.get('v1', '').lower()
    if not _SIGNATURE_TS_RE.fullmatch(ts) or not _SIGNATURE_HASH_RE.fullmatch(received_hash):
        return False
    if request_id and not _REQUEST_ID_RE.fullmatch(request_id):
        return False
    data_id = signed_data_id(query)
    if not data_id:
        return False
    manifest = f'id:{data_id.lower()};request-id:{request_id};ts:{ts};'
    expected = hmac.new(
        secret.encode('utf-8'),
        manifest.encode('utf-8'),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected.encode('ascii'), received_hash.encode('ascii'))


def handle_webhook(connection, payload, query):
    """Processa uma notificação JÁ AUTENTICADA pela assinatura.

    - O recurso processado é sempre o `data.id` ASSINADO (query string). Um id
      diferente no corpo é recusado — o corpo não é coberto pela assinatura.
    - Só recursos conhecidos localmente são sincronizados; o resto é ignorado
      sem chamar o Mercado Pago. A empresa vem do registro local.
    - Idempotente: o estado é sempre relido do Mercado Pago, e um estado mais
      antigo que o gravado não sobrescreve o atual (notificações fora de ordem).
    """
    payload = payload if isinstance(payload, dict) else {}
    query = query or {}

    topic = payload.get('type') or payload.get('topic') or _query_value(query, 'type') or _query_value(query, 'topic')
    topic = str(topic or '').strip().lower() if isinstance(topic, str) else ''
    resource_type = _WEBHOOK_TOPICS.get(topic)
    if resource_type is None:
        structured_log('info', 'payments.webhook_ignored', reason='unsupported_topic')
        return {'ok': True, 'ignored': True, 'reason': 'unsupported_topic'}

    signed_id = signed_data_id(query)
    data = payload.get('data') if isinstance(payload.get('data'), dict) else {}
    body_id = data.get('id', payload.get('id'))
    if body_id not in (None, '') and str(body_id) != signed_id:
        structured_log('warning', 'payments.webhook_id_mismatch', resource_type=resource_type)
        return {'ok': True, 'ignored': True, 'reason': 'id_mismatch'}
    try:
        resource_id = validate_mp_resource_id(signed_id, resource_type)
    except ValueError:
        structured_log('warning', 'payments.webhook_invalid_id', resource_type=resource_type)
        return {'ok': True, 'ignored': True, 'reason': 'invalid_id'}

    structured_log('info', 'payments.webhook_received', topic=topic, resource_id=resource_id)

    try:
        status_info = fetch_payment_status(connection, resource_id, resource_type, company_id=ANY_COMPANY)
    except PaymentNotFoundError:
        structured_log('info', 'payments.webhook_ignored', reason='unknown_resource',
                       resource_type=resource_type)
        return {'ok': True, 'ignored': True, 'reason': 'unknown_resource'}
    except MercadoPagoError as exc:
        structured_log('warning', 'payments.webhook_fetch_failed', resource_id=resource_id, error=str(exc))
        # O texto do erro fica no log; ao chamador do webhook vai um código fixo.
        return {'ok': True, 'synced': False, 'reason': 'mercado_pago_unavailable'}

    # Sincroniza o ciclo de vida da assinatura (tabela subscriptions) quando o
    # recurso é um preapproval. Best-effort: não bloqueia a confirmação ao MP.
    if resource_type == 'preapproval' and not status_info.get('stale'):
        try:
            from modules.payments import subscriptions_service
            subscriptions_service.sync_subscription_status(
                connection, resource_id, status_info.get('status'), raw=status_info,
            )
        except Exception as exc:  # pragma: no cover - defensivo
            structured_log('warning', 'subscriptions.webhook_sync_failed',
                           resource_id=resource_id, error=str(exc))

    return {'ok': True, 'synced': True, 'status': status_info.get('status'), 'resource_type': resource_type}
