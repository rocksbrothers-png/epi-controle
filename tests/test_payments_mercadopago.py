"""Testes da integração de pagamentos Mercado Pago (backend).

Usam SQLite em memória e fazem mock do cliente HTTP do Mercado Pago para não
tocar a rede. Cobrem persistência de company_id, plan_id, payer_email,
payment_method e status.
"""

import sqlite3

import pytest

from modules.payments import service
from modules.payments import mp_client


def make_connection():
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    service.ensure_payment_tables(conn)
    return conn


def fetch_payment(conn, mp_id):
    row = conn.execute('SELECT * FROM payments WHERE mp_payment_id = ?', (mp_id,)).fetchone()
    return dict(row) if row else None


def test_ensure_tables_idempotent():
    conn = make_connection()
    service.ensure_payment_tables(conn)  # segunda chamada não deve falhar
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {'payment_plans', 'payments'} <= tables


def test_create_pix_payment_persists_fields(monkeypatch):
    conn = make_connection()

    def fake_post(path, body, **kwargs):
        assert path == '/v1/payments'
        assert body['payment_method_id'] == 'pix'
        return {
            'id': 'PIX123',
            'status': 'pending',
            'status_detail': 'pending_waiting_transfer',
            'currency_id': 'BRL',
            'point_of_interaction': {'transaction_data': {
                'qr_code': '000201...',
                'qr_code_base64': 'AAAA',
            }},
        }

    monkeypatch.setattr(mp_client, 'post', fake_post)
    result = service.create_pix_payment(conn, {
        'company_id': 7,
        'plan_id': 'plan-x',
        'payer_email': 'cliente@empresa.com',
        'amount': 42.0,
    })
    assert result['payment_id'] == 'PIX123'
    assert result['payment_method'] == 'pix'
    assert result['qr_code'] == '000201...'

    row = fetch_payment(conn, 'PIX123')
    assert row['company_id'] == 7
    assert row['plan_id'] == 'plan-x'
    assert row['payer_email'] == 'cliente@empresa.com'
    assert row['payment_method'] == 'pix'
    assert row['status'] == 'pending'


def test_create_boleto_payment(monkeypatch):
    conn = make_connection()
    monkeypatch.setattr(mp_client, 'post', lambda path, body, **k: {
        'id': 'BOL1', 'status': 'pending', 'currency_id': 'BRL',
        'transaction_details': {'external_resource_url': 'https://mp/boleto.pdf'},
    })
    result = service.create_boleto_payment(conn, {
        'company_id': 1, 'payer_email': 'a@b.com', 'amount': 10.0,
    })
    assert result['payment_method'] == 'boleto'
    assert result['ticket_url'] == 'https://mp/boleto.pdf'
    assert fetch_payment(conn, 'BOL1')['payment_method'] == 'boleto'


def test_create_card_subscription(monkeypatch):
    conn = make_connection()

    def fake_post(path, body, **kwargs):
        assert path == '/preapproval'
        assert body['card_token_id'] == 'tok_abc'
        return {'id': 'SUB1', 'status': 'authorized', 'init_point': 'https://mp/sub'}

    monkeypatch.setattr(mp_client, 'post', fake_post)
    result = service.create_card_subscription(conn, {
        'company_id': 3,
        'plan_id': 'PLAN1',
        'payer_email': 'pay@er.com',
        'card_token': 'tok_abc',
    })
    assert result['subscription_id'] == 'SUB1'
    assert result['status'] == 'authorized'
    row = conn.execute("SELECT * FROM payments WHERE mp_resource_type='preapproval'").fetchone()
    assert row['payment_method'] == 'subscription'
    assert row['company_id'] == 3
    assert row['plan_id'] == 'PLAN1'


def test_create_preapproval_plan_persists(monkeypatch):
    conn = make_connection()
    monkeypatch.setattr(mp_client, 'post', lambda path, body, **k: {
        'id': 'PLANMP', 'status': 'active', 'init_point': 'https://mp/plan',
    })
    result = service.create_preapproval_plan(conn, {
        'company_id': 2, 'reason': 'Plano Start', 'amount': 99.9,
        'frequency': 1, 'frequency_type': 'months',
    })
    assert result['plan_id'] == 'PLANMP'
    row = conn.execute('SELECT * FROM payment_plans WHERE mp_plan_id = ?', ('PLANMP',)).fetchone()
    assert row['company_id'] == 2
    assert row['reason'] == 'Plano Start'
    assert row['status'] == 'active'


def test_fetch_payment_status_updates_local(monkeypatch):
    conn = make_connection()
    monkeypatch.setattr(mp_client, 'post', lambda path, body, **k: {
        'id': 'P9', 'status': 'pending', 'currency_id': 'BRL',
        'point_of_interaction': {'transaction_data': {}},
    })
    service.create_pix_payment(conn, {'company_id': 1, 'payer_email': 'a@b.com', 'amount': 5.0})
    monkeypatch.setattr(mp_client, 'get', lambda path: {'id': 'P9', 'status': 'approved', 'status_detail': 'accredited'})
    info = service.fetch_payment_status(conn, 'P9', 'payment')
    assert info['status'] == 'approved'
    assert fetch_payment(conn, 'P9')['status'] == 'approved'


def test_webhook_syncs_status(monkeypatch):
    conn = make_connection()
    monkeypatch.setattr(mp_client, 'post', lambda path, body, **k: {
        'id': 'W1', 'status': 'pending', 'currency_id': 'BRL',
        'point_of_interaction': {'transaction_data': {}},
    })
    service.create_pix_payment(conn, {'company_id': 1, 'payer_email': 'a@b.com', 'amount': 5.0})
    monkeypatch.setattr(mp_client, 'get', lambda path: {'id': 'W1', 'status': 'approved'})
    result = service.handle_webhook(conn, {'type': 'payment', 'data': {'id': 'W1'}}, {})
    assert result['synced'] is True
    assert result['status'] == 'approved'
    assert fetch_payment(conn, 'W1')['status'] == 'approved'


def test_missing_required_field_raises():
    conn = make_connection()
    with pytest.raises(ValueError):
        service.create_pix_payment(conn, {'company_id': 1, 'amount': 5.0})  # sem payer_email


def test_public_config_never_exposes_access_token():
    cfg = service.public_config()
    assert 'public_key' in cfg
    assert 'access_token' not in cfg
    assert not any('access' in k.lower() and 'token' in k.lower() for k in cfg)


def test_webhook_signature_disabled_passes():
    # Sem segredo configurado, a validação não bloqueia.
    assert service.verify_webhook_signature({}, {}) is True


def test_create_preapproval_plan_persists_plan_key(monkeypatch):
    conn = make_connection()
    monkeypatch.setattr(mp_client, 'post', lambda path, body, **k: {
        'id': 'MPBIZ', 'status': 'active', 'init_point': 'https://mp/biz',
    })
    result = service.create_preapproval_plan(conn, {
        'plan_key': 'BUSINESS', 'reason': 'EPI Controle BUSINESS', 'amount': 597.0,
    })
    assert result['plan_key'] == 'business'
    row = conn.execute('SELECT * FROM payment_plans WHERE mp_plan_id = ?', ('MPBIZ',)).fetchone()
    assert row['plan_key'] == 'business'


def test_normalize_cycle_aliases():
    assert service.normalize_cycle('mensal') == 'monthly'
    assert service.normalize_cycle('anual') == 'annual'
    assert service.normalize_cycle('yearly') == 'annual'
    assert service.normalize_cycle('') == 'monthly'


def test_catalog_matches_website_monthly_prices():
    conn = make_connection()
    catalog = {p['key']: p for p in service.list_public_catalog(conn, 'monthly')}
    assert catalog['start']['amount'] == 297.00
    assert catalog['business']['amount'] == 597.00
    assert catalog['corporate']['amount'] == 1297.00
    # Enterprise é "sob consulta" — sem preço e não comprável diretamente.
    assert catalog['enterprise']['amount'] is None
    assert catalog['enterprise']['contact_only'] is True


def test_catalog_annual_is_ten_times_monthly():
    conn = make_connection()
    catalog = {p['key']: p for p in service.list_public_catalog(conn, 'annual')}
    assert catalog['start']['amount'] == 2970.00
    assert catalog['business']['amount'] == 5970.00
    assert catalog['corporate']['amount'] == 12970.00


def test_catalog_enriches_with_created_mp_plan_id(monkeypatch):
    conn = make_connection()
    monkeypatch.setattr(mp_client, 'post', lambda path, body, **k: {
        'id': 'MP_START_M', 'status': 'active', 'init_point': '',
    })
    service.create_preapproval_plan(conn, {
        'plan_key': 'start', 'reason': 'EPI Controle START', 'amount': 297.0,
        'frequency': 1, 'frequency_type': 'months',
    })
    catalog = {p['key']: p for p in service.list_public_catalog(conn, 'monthly')}
    assert catalog['start']['plan_id'] == 'MP_START_M'
    # Sem plano anual criado, o plan_id anual fica vazio.
    annual = {p['key']: p for p in service.list_public_catalog(conn, 'annual')}
    assert annual['start']['plan_id'] == ''


def test_public_catalog_never_exposes_internal_fields():
    conn = make_connection()
    for item in service.list_public_catalog(conn, 'monthly'):
        assert 'raw_json' not in item
        assert 'access_token' not in item
        assert set(item.keys()) <= {
            'key', 'label', 'reason', 'max_users', 'cycle', 'amount',
            'currency', 'contact_only', 'highlight', 'plan_id',
        }
