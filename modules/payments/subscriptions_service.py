"""Ciclo de vida de assinaturas (PR 2) — backend como fonte única de verdade.

Consome as tabelas `subscriptions`, `invoices` e `subscription_audit_logs`
(criadas em modules/payments/service.py::ensure_subscription_tables, PR 3) e o
Mercado Pago (recurso `preapproval`). Toda a lógica sensível roda no backend; o
Access Token nunca chega ao frontend.

Decisões de MVP (ver docs/ARQUITETURA_ASSINATURAS.md §4.3 e §13 — ajustáveis):
  - upgrade/downgrade: troca imediata — cancela o preapproval atual e cria um
    novo para o novo plano/ciclo. **Sem proração** no MVP.
  - dunning (retentativa de cobrança recusada): comportamento padrão do MP.
  - NF-e/NFS-e e notificações (e-mail/push): fora do MVP (campos já previstos).

As operações são idempotentes onde possível e sempre registram auditoria.
"""

import json
import uuid
from datetime import datetime, timezone

from epi_backend.db import row_to_dict
from epi_backend.http_utils import structured_log
from modules.payments import mp_client

UTC = timezone.utc

# Status canônicos da assinatura (espelham e normalizam o status do MP).
ACTIVE_STATUSES = ('authorized', 'active', 'pending')
CANCELLED_STATUSES = ('cancelled', 'canceled')


def _now_iso():
    return datetime.now(UTC).isoformat().replace('+00:00', 'Z')


def _add_months(base, months):
    month_index = base.month - 1 + months
    year = base.year + month_index // 12
    month = month_index % 12 + 1
    # Mantém o dia, ajustando para o último dia do mês quando necessário.
    day = min(base.day, [31, 29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28,
                         31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1])
    return base.replace(year=year, month=month, day=day)


def _cycle_to_months(cycle):
    return 12 if str(cycle or '').lower() == 'annual' else 1


def normalize_status(mp_status):
    raw = str(mp_status or '').strip().lower()
    if raw in CANCELLED_STATUSES:
        return 'cancelled'
    if raw in ('authorized', 'active'):
        return 'active'
    if raw == 'paused':
        return 'paused'
    if raw in ('pending',):
        return 'pending'
    return raw or 'pending'


# ── Auditoria ─────────────────────────────────────────────────────────────────

def record_audit(connection, *, subscription_id, action, actor_user_id=None,
                 company_id=None, tenant_id='', ip='', detail=None):
    connection.execute(
        '''
        INSERT INTO subscription_audit_logs
            (subscription_id, action, actor_user_id, company_id, tenant_id, ip, detail_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''',
        (
            str(subscription_id or ''), str(action or ''),
            int(actor_user_id) if actor_user_id not in (None, '') else None,
            int(company_id) if company_id not in (None, '') else None,
            str(tenant_id or ''), str(ip or ''),
            json.dumps(detail or {}, ensure_ascii=False), _now_iso(),
        ),
    )
    structured_log('info', 'subscriptions.audit', subscription_id=subscription_id,
                   action=action, actor_user_id=actor_user_id, company_id=company_id)


# ── Persistência ──────────────────────────────────────────────────────────────

def record_subscription(connection, *, company_id, plan_key, cycle, payment_method,
                        preapproval_id, preapproval_plan_id='', status='pending',
                        amount=0, currency='BRL', tenant_id='', created_by=None,
                        is_recurring=True, raw=None):
    """Insere uma assinatura e devolve o dict persistido (com subscription_id)."""
    now = datetime.now(UTC)
    subscription_id = str(uuid.uuid4())
    norm = normalize_status(status)
    next_date = ''
    renewal_date = ''
    if is_recurring and norm in ('active', 'pending'):
        nxt = _add_months(now, _cycle_to_months(cycle))
        next_date = nxt.isoformat().replace('+00:00', 'Z')
        renewal_date = next_date
    connection.execute(
        '''
        INSERT INTO subscriptions
            (company_id, tenant_id, subscription_id, plan_key, payment_cycle,
             payment_method, is_recurring, preapproval_id, preapproval_plan_id,
             status, mp_status, amount, currency, renewal_date, next_payment_date,
             last_payment_date, cancel_date, cancel_reason, created_by, updated_by,
             created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '', '', '', ?, ?, ?, ?)
        ''',
        (
            int(company_id) if company_id not in (None, '') else None,
            str(tenant_id or ''), subscription_id, str(plan_key or ''), str(cycle or 'monthly'),
            str(payment_method or 'card'), 1 if is_recurring else 0,
            str(preapproval_id or ''), str(preapproval_plan_id or ''),
            norm, str(status or ''), float(amount or 0), str(currency or 'BRL'),
            renewal_date, next_date,
            int(created_by) if created_by not in (None, '') else None,
            int(created_by) if created_by not in (None, '') else None,
            _now_iso(), _now_iso(),
        ),
    )
    record_audit(connection, subscription_id=subscription_id, action='created',
                 actor_user_id=created_by, company_id=company_id, tenant_id=tenant_id,
                 detail={'plan_key': plan_key, 'cycle': cycle, 'payment_method': payment_method,
                         'preapproval_id': preapproval_id})
    return get_subscription(connection, subscription_id)


def record_invoice(connection, *, subscription_id, company_id, mp_payment_id,
                   payment_method, amount, currency='BRL', status='pending',
                   tenant_id='', paid_at='', receipt_url='', raw=None):
    connection.execute(
        '''
        INSERT INTO invoices
            (subscription_id, company_id, tenant_id, mp_payment_id, payment_method,
             amount, currency, status, due_date, paid_at, receipt_url, invoice_url,
             raw_json, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, '', ?, ?, '', ?, ?, ?)
        ''',
        (
            str(subscription_id or ''), int(company_id) if company_id not in (None, '') else None,
            str(tenant_id or ''), str(mp_payment_id or ''), str(payment_method or ''),
            float(amount or 0), str(currency or 'BRL'), str(status or 'pending'),
            str(paid_at or ''), str(receipt_url or ''),
            json.dumps(raw or {}, ensure_ascii=False), _now_iso(), _now_iso(),
        ),
    )


# ── Consultas ─────────────────────────────────────────────────────────────────

def get_subscription(connection, subscription_id):
    row = connection.execute(
        'SELECT * FROM subscriptions WHERE subscription_id = ? ORDER BY id DESC LIMIT 1',
        (str(subscription_id),),
    ).fetchone()
    return row_to_dict(row) if row else None


def get_current_subscription(connection, company_id):
    """Assinatura "vigente" da empresa: prioriza não-cancelada mais recente."""
    rows = connection.execute(
        'SELECT * FROM subscriptions WHERE company_id = ? ORDER BY id DESC',
        (int(company_id),),
    ).fetchall()
    items = [row_to_dict(r) for r in rows]
    if not items:
        return None
    for item in items:
        if normalize_status(item.get('status')) not in ('cancelled', 'expired'):
            return item
    return items[0]


def list_invoices(connection, company_id, *, limit=50, offset=0, status=None, method=None):
    clauses = ['company_id = ?']
    args = [int(company_id)]
    if status:
        clauses.append('status = ?')
        args.append(str(status))
    if method:
        clauses.append('payment_method = ?')
        args.append(str(method))
    where = ' AND '.join(clauses)
    args.extend([int(limit), int(offset)])
    rows = connection.execute(
        f'SELECT * FROM invoices WHERE {where} ORDER BY id DESC LIMIT ? OFFSET ?',
        tuple(args),
    ).fetchall()
    return [row_to_dict(r) for r in rows]


# ── Atualização de status (criação/webhook) ───────────────────────────────────

def _update_subscription_fields(connection, subscription_id, **fields):
    if not fields:
        return
    fields['updated_at'] = _now_iso()
    sets = ', '.join(f'{key} = ?' for key in fields)
    args = list(fields.values()) + [str(subscription_id)]
    connection.execute(
        f'UPDATE subscriptions SET {sets} WHERE subscription_id = ?', tuple(args)
    )


def sync_subscription_status(connection, preapproval_id, mp_status, *, raw=None):
    """Sincroniza o status de uma assinatura a partir do preapproval do MP
    (chamado pelo webhook). Idempotente."""
    row = connection.execute(
        'SELECT * FROM subscriptions WHERE preapproval_id = ? ORDER BY id DESC LIMIT 1',
        (str(preapproval_id),),
    ).fetchone()
    if not row:
        return False
    item = row_to_dict(row)
    norm = normalize_status(mp_status)
    updates = {'status': norm, 'mp_status': str(mp_status or '')}
    if norm == 'cancelled' and not item.get('cancel_date'):
        updates['cancel_date'] = _now_iso()
    _update_subscription_fields(connection, item['subscription_id'], **updates)
    record_audit(connection, subscription_id=item['subscription_id'],
                 action='status_synced', company_id=item.get('company_id'),
                 tenant_id=item.get('tenant_id') or '',
                 detail={'mp_status': mp_status, 'normalized': norm})
    return True


# ── Operações de ciclo de vida ────────────────────────────────────────────────

def cancel_subscription(connection, *, company_id, actor_user_id=None, ip='', reason=''):
    """Cancela a assinatura vigente no Mercado Pago e atualiza o banco.

    Acesso permanece até o fim do período já pago (não alteramos next_payment_date);
    apenas marcamos como cancelada e registramos auditoria.
    """
    sub = get_current_subscription(connection, company_id)
    if not sub:
        raise ValueError('Nenhuma assinatura encontrada para esta empresa.')
    if normalize_status(sub.get('status')) == 'cancelled':
        return sub
    preapproval_id = str(sub.get('preapproval_id') or '')
    if preapproval_id:
        mp_client.put(f'/preapproval/{preapproval_id}', {'status': 'cancelled'})
    _update_subscription_fields(
        connection, sub['subscription_id'],
        status='cancelled', mp_status='cancelled',
        cancel_date=_now_iso(), cancel_reason=str(reason or ''),
        updated_by=int(actor_user_id) if actor_user_id not in (None, '') else None,
    )
    record_audit(connection, subscription_id=sub['subscription_id'], action='cancelled',
                 actor_user_id=actor_user_id, company_id=company_id,
                 tenant_id=sub.get('tenant_id') or '', ip=ip,
                 detail={'reason': reason, 'preapproval_id': preapproval_id})
    return get_subscription(connection, sub['subscription_id'])


def change_card(connection, *, company_id, card_token, actor_user_id=None, ip=''):
    """Atualiza o cartão (card_token) do preapproval vigente."""
    if not card_token:
        raise ValueError('card_token é obrigatório.')
    sub = get_current_subscription(connection, company_id)
    if not sub:
        raise ValueError('Nenhuma assinatura encontrada para esta empresa.')
    preapproval_id = str(sub.get('preapproval_id') or '')
    if not preapproval_id:
        raise ValueError('Assinatura sem preapproval no Mercado Pago.')
    mp_client.put(f'/preapproval/{preapproval_id}', {'card_token_id': str(card_token)})
    _update_subscription_fields(
        connection, sub['subscription_id'],
        updated_by=int(actor_user_id) if actor_user_id not in (None, '') else None,
    )
    record_audit(connection, subscription_id=sub['subscription_id'], action='changed_card',
                 actor_user_id=actor_user_id, company_id=company_id,
                 tenant_id=sub.get('tenant_id') or '', ip=ip,
                 detail={'preapproval_id': preapproval_id})
    return get_subscription(connection, sub['subscription_id'])


def change_plan(connection, *, company_id, plan_id, plan_key, cycle, payer_email,
                card_token, amount=None, actor_user_id=None, ip='', tenant_id=''):
    """Troca de plano (upgrade/downgrade) — MVP: troca imediata sem proração.

    Cancela o preapproval atual (se houver) e cria um novo para o novo
    plano/ciclo. Registra auditoria ligando a assinatura antiga à nova.
    """
    from modules.payments import service  # import tardio evita ciclo de import

    previous = get_current_subscription(connection, company_id)
    # Cancela o preapproval anterior no MP (best-effort) e marca no banco.
    if previous and normalize_status(previous.get('status')) != 'cancelled':
        prev_preapproval = str(previous.get('preapproval_id') or '')
        if prev_preapproval:
            try:
                mp_client.put(f'/preapproval/{prev_preapproval}', {'status': 'cancelled'})
            except Exception as exc:  # não bloqueia a troca por falha no cancelamento
                structured_log('warning', 'subscriptions.change_plan_cancel_failed',
                               preapproval_id=prev_preapproval, error=str(exc))
        _update_subscription_fields(
            connection, previous['subscription_id'],
            status='cancelled', mp_status='cancelled', cancel_date=_now_iso(),
            cancel_reason='plan_change',
            updated_by=int(actor_user_id) if actor_user_id not in (None, '') else None,
        )

    created = service.create_card_subscription(connection, {
        'plan_id': plan_id, 'payer_email': payer_email, 'card_token': card_token,
        'company_id': company_id, 'amount': amount,
        'external_reference': f'change_plan|{plan_key}|{cycle}',
    })
    new_sub = record_subscription(
        connection, company_id=company_id, plan_key=plan_key, cycle=cycle,
        payment_method='card', preapproval_id=created.get('subscription_id'),
        preapproval_plan_id=str(plan_id), status=created.get('status') or 'pending',
        amount=amount or 0, tenant_id=tenant_id, created_by=actor_user_id,
        is_recurring=True, raw=created,
    )
    record_audit(connection, subscription_id=new_sub['subscription_id'], action='changed_plan',
                 actor_user_id=actor_user_id, company_id=company_id, tenant_id=tenant_id, ip=ip,
                 detail={'from': previous and previous.get('subscription_id'),
                         'to_plan_key': plan_key, 'to_cycle': cycle})
    return new_sub


def reactivate_subscription(connection, *, company_id, plan_id, plan_key, cycle,
                            payer_email, card_token, amount=None, actor_user_id=None,
                            ip='', tenant_id=''):
    """Reativa criando um novo preapproval (assinaturas canceladas no MP não
    voltam ao ar). Reusa o fluxo de criação e registra auditoria."""
    from modules.payments import service  # import tardio evita ciclo de import

    created = service.create_card_subscription(connection, {
        'plan_id': plan_id, 'payer_email': payer_email, 'card_token': card_token,
        'company_id': company_id, 'amount': amount,
        'external_reference': f'reactivate|{plan_key}|{cycle}',
    })
    new_sub = record_subscription(
        connection, company_id=company_id, plan_key=plan_key, cycle=cycle,
        payment_method='card', preapproval_id=created.get('subscription_id'),
        preapproval_plan_id=str(plan_id), status=created.get('status') or 'pending',
        amount=amount or 0, tenant_id=tenant_id, created_by=actor_user_id,
        is_recurring=True, raw=created,
    )
    record_audit(connection, subscription_id=new_sub['subscription_id'], action='reactivated',
                 actor_user_id=actor_user_id, company_id=company_id, tenant_id=tenant_id, ip=ip,
                 detail={'plan_key': plan_key, 'cycle': cycle})
    return new_sub
