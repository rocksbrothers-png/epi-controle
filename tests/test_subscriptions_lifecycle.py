"""Testes do ciclo de vida de assinaturas (PR 2).

Usam SQLite em memória e mockam o cliente HTTP do Mercado Pago (mp_client) para
não tocar a rede. Cobrem persistência, consulta, cancelamento, troca de cartão,
troca de plano e sincronização via webhook.
"""

import sqlite3

from modules.payments import service, subscriptions_service


def make_connection():
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    service.ensure_subscription_tables(conn)
    return conn


def test_record_and_get_current_subscription():
    conn = make_connection()
    sub = subscriptions_service.record_subscription(
        conn, company_id=7, plan_key='start', cycle='monthly', payment_method='card',
        preapproval_id='pre_1', preapproval_plan_id='plan_1', status='authorized',
        amount=297.0, created_by=3,
    )
    assert sub['subscription_id']
    assert sub['status'] == 'active'  # 'authorized' normaliza para 'active'
    assert sub['next_payment_date']  # recorrente => próxima cobrança calculada

    current = subscriptions_service.get_current_subscription(conn, 7)
    assert current['preapproval_id'] == 'pre_1'

    # Auditoria de criação registrada.
    audit = conn.execute(
        "SELECT action FROM subscription_audit_logs WHERE subscription_id = ?",
        (sub['subscription_id'],),
    ).fetchall()
    assert 'created' in {r[0] for r in audit}


def test_invoices_listing_and_filters():
    conn = make_connection()
    subscriptions_service.record_invoice(conn, subscription_id='s1', company_id=7,
                                         mp_payment_id='p1', payment_method='pix',
                                         amount=297.0, status='paid')
    subscriptions_service.record_invoice(conn, subscription_id='s1', company_id=7,
                                         mp_payment_id='p2', payment_method='card',
                                         amount=297.0, status='pending')
    all_inv = subscriptions_service.list_invoices(conn, 7)
    assert len(all_inv) == 2
    paid = subscriptions_service.list_invoices(conn, 7, status='paid')
    assert len(paid) == 1 and paid[0]['mp_payment_id'] == 'p1'
    pix = subscriptions_service.list_invoices(conn, 7, method='pix')
    assert len(pix) == 1 and pix[0]['payment_method'] == 'pix'


def test_cancel_subscription(monkeypatch):
    conn = make_connection()
    subscriptions_service.record_subscription(
        conn, company_id=7, plan_key='start', cycle='monthly', payment_method='card',
        preapproval_id='pre_cancel', status='authorized', amount=297.0,
    )
    calls = {}

    def fake_put(path, body):
        calls['path'] = path
        calls['body'] = body
        return {'id': 'pre_cancel', 'status': 'cancelled'}

    monkeypatch.setattr(subscriptions_service.mp_client, 'put', fake_put)
    result = subscriptions_service.cancel_subscription(
        conn, company_id=7, actor_user_id=3, ip='1.2.3.4', reason='cliente solicitou')
    assert result['status'] == 'cancelled'
    assert result['cancel_reason'] == 'cliente solicitou'
    assert calls['path'] == '/preapproval/pre_cancel'
    assert calls['body'] == {'status': 'cancelled'}

    actions = {r[0] for r in conn.execute(
        "SELECT action FROM subscription_audit_logs WHERE subscription_id = ?",
        (result['subscription_id'],)).fetchall()}
    assert 'cancelled' in actions


def test_change_card(monkeypatch):
    conn = make_connection()
    subscriptions_service.record_subscription(
        conn, company_id=7, plan_key='start', cycle='monthly', payment_method='card',
        preapproval_id='pre_card', status='authorized', amount=297.0,
    )
    captured = {}
    monkeypatch.setattr(subscriptions_service.mp_client, 'put',
                        lambda path, body: captured.update(path=path, body=body) or {'id': 'pre_card'})
    subscriptions_service.change_card(conn, company_id=7, card_token='tok_new', actor_user_id=3)
    assert captured['path'] == '/preapproval/pre_card'
    assert captured['body'] == {'card_token_id': 'tok_new'}


def test_sync_subscription_status_from_webhook():
    conn = make_connection()
    sub = subscriptions_service.record_subscription(
        conn, company_id=7, plan_key='start', cycle='monthly', payment_method='card',
        preapproval_id='pre_sync', status='pending', amount=297.0,
    )
    assert sub['status'] == 'pending'
    ok = subscriptions_service.sync_subscription_status(conn, 'pre_sync', 'cancelled')
    assert ok is True
    refreshed = subscriptions_service.get_subscription(conn, sub['subscription_id'])
    assert refreshed['status'] == 'cancelled'
    assert refreshed['cancel_date']
    # Sem assinatura correspondente => no-op seguro.
    assert subscriptions_service.sync_subscription_status(conn, 'inexistente', 'authorized') is False


def test_cancel_without_subscription_raises():
    conn = make_connection()
    try:
        subscriptions_service.cancel_subscription(conn, company_id=99)
        assert False, 'deveria levantar ValueError'
    except ValueError:
        pass
