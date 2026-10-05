"""1J-C — idempotência do checkout Corporate (efeito externo no Mercado Pago).

Dirige os HANDLERS REAIS. O Mercado Pago é mockado por um simulador que HONRA o
`X-Idempotency-Key` (mesma chave → MESMO preapproval, criado uma única vez) —
exatamente o contrato de idempotência real do MP — para que os testes provem
que retry/concorrência nunca produzem um segundo efeito externo.

Casos sequenciais rodam em SQLite :memory:. Concorrência/atomicidade real,
restart e timeout ambíguo exigem PostgreSQL (o índice UNIQUE serializa de
verdade) e são @skipif sem DATABASE_URL.
"""

import os
import sqlite3
import threading
import uuid

import pytest

import core.security as seguranca
from core import checkout_idempotency
from modules.payments import mp_client, routes, service, subscriptions_service

PG = os.environ.get('DATABASE_URL')
requires_pg = pytest.mark.skipif(not PG, reason='requer PostgreSQL (DATABASE_URL)')


# ── Dublês ──────────────────────────────────────────────────────────────────

class _Handler:
    command = 'POST'
    client_address = ('127.0.0.1',)

    def __init__(self, auth='', headers=None):
        self.headers = headers if headers is not None else ({'Authorization': auth} if auth else {})


class _Parsed:
    def __init__(self, query='', path='/api/payments/subscriptions'):
        self.query = query
        self.path = path


def _bearer(uid, role='general_admin', company_id=1):
    return 'Bearer ' + seguranca.create_jwt_token({'id': uid, 'role': role, 'company_id': company_id})


class _MPSim:
    """Simula a API do MP honrando X-Idempotency-Key: mesma chave → mesmo
    recurso (criado UMA vez). `created` conta efeitos externos DISTINTOS."""

    def __init__(self, delay=0.0):
        self.calls = []
        self._by_key = {}
        self._n = 0
        self._lock = threading.Lock()
        self._delay = delay

    def post(self, path, body, *, idempotency_key=None):
        if self._delay:
            import time
            time.sleep(self._delay)
        with self._lock:
            self.calls.append({'path': path, 'key': idempotency_key})
            if idempotency_key and idempotency_key in self._by_key:
                return dict(self._by_key[idempotency_key])
            self._n += 1
            if path == '/preapproval':
                res = {'id': f'SUB{self._n}', 'status': 'authorized', 'init_point': 'https://mp/x'}
            else:
                res = {'id': f'PAY{self._n}', 'status': 'pending', 'status_detail': 'pending',
                       'currency_id': 'BRL',
                       'point_of_interaction': {'transaction_data': {'qr_code': 'QR', 'qr_code_base64': 'B'}},
                       'transaction_details': {'external_resource_url': 'https://mp/b.pdf'}}
            if idempotency_key:
                self._by_key[idempotency_key] = res
            return dict(res)

    @property
    def created(self):
        return self._n


def _sqlite():
    c = sqlite3.connect(':memory:', check_same_thread=False)
    c.row_factory = sqlite3.Row
    service.ensure_payment_tables(c)
    service.ensure_subscription_tables(c)
    checkout_idempotency.ensure_payment_attempt_tables(c)

    class _NoClose:
        def __getattr__(self, n):
            return getattr(c, n)

        def close(self):
            pass
    return _NoClose(), c


ACTORS = {10: {'id': 10, 'role': 'general_admin', 'company_id': 1},
          20: {'id': 20, 'role': 'general_admin', 'company_id': 2}}


def _wire(monkeypatch, conn, sim):
    monkeypatch.setattr(routes, 'get_connection', lambda: conn)
    monkeypatch.setattr(routes, 'send_json', lambda h, s, p: (s, p))
    monkeypatch.setattr(routes, 'require_actor', lambda connection, uid: dict(ACTORS[int(uid)]))
    monkeypatch.setattr(mp_client, 'post', sim.post)


def _card(key, plan='start', cycle='monthly', email='a@b.com', token='t'):
    return {'idempotency_key': key, 'plan_key': plan, 'cycle': cycle,
            'payer_email': email, 'card_token': token}


def _sub(conn, company=1):
    return [dict(r) for r in conn.execute(
        'SELECT * FROM subscriptions WHERE company_id=? ORDER BY id', (company,)).fetchall()]


# ── T1 — mesma chave sequencial → 1 efeito externo ───────────────────────────

def test_t1_same_key_sequential_one_effect(monkeypatch):
    conn, raw = _sqlite()
    sim = _MPSim()
    _wire(monkeypatch, conn, sim)
    k = 'intent-aaaa-1111'
    r1 = routes.handle_post_subscription(_Handler(_bearer(10)), _Parsed(), _card(k), None)
    r2 = routes.handle_post_subscription(_Handler(_bearer(10)), _Parsed(), _card(k), None)
    assert r1[0] == 201
    assert r2[0] == 200 and r2[1].get('idempotent_replay') is True
    assert sim.created == 1
    assert len(_sub(raw)) == 1


# ── T3 — MP ok + falha de DB + retry → NÃO cria segundo preapproval ──────────

def test_t3_mp_success_db_failure_retry_no_second(monkeypatch):
    conn, raw = _sqlite()
    sim = _MPSim()
    _wire(monkeypatch, conn, sim)
    real_record = subscriptions_service.record_subscription
    state = {'fail': True}

    def flaky(*a, **k):
        if state['fail']:
            state['fail'] = False
            raise RuntimeError('db boom pós-MP')
        return real_record(*a, **k)

    monkeypatch.setattr(subscriptions_service, 'record_subscription', flaky)
    k = 'intent-bbbb-2222'
    r1 = routes.handle_post_subscription(_Handler(_bearer(10)), _Parsed(), _card(k), None)
    assert r1[0] == 503  # reconciliação pendente, sem 201 enganoso
    assert _sub(raw) == []  # nada persistido localmente (rollback total)
    r2 = routes.handle_post_subscription(_Handler(_bearer(10)), _Parsed(), _card(k), None)
    assert r2[0] == 201
    assert sim.created == 1  # MESMO preapproval (X-Idempotency-Key), nunca um 2º
    rows = _sub(raw)
    assert len(rows) == 1 and rows[0]['preapproval_id'] == 'SUB1'


# ── T4 — falha do MP antes de criar + retry → retry permitido ────────────────

def test_t4_mp_failure_then_retry_allowed(monkeypatch):
    conn, raw = _sqlite()
    sim = _MPSim()
    _wire(monkeypatch, conn, sim)
    from modules.payments.mp_client import MercadoPagoError
    state = {'fail': True}

    def maybe_fail(path, body, *, idempotency_key=None):
        if state['fail']:
            state['fail'] = False
            raise MercadoPagoError('mp down', status=502, response={})
        return sim.post(path, body, idempotency_key=idempotency_key)

    monkeypatch.setattr(mp_client, 'post', maybe_fail)
    k = 'intent-cccc-3333'
    r1 = routes.handle_post_subscription(_Handler(_bearer(10)), _Parsed(), _card(k), None)
    assert r1[0] == 502
    assert _sub(raw) == []
    r2 = routes.handle_post_subscription(_Handler(_bearer(10)), _Parsed(), _card(k), None)
    assert r2[0] == 201 and len(_sub(raw)) == 1


# ── T5 — nova chave → nova operação permitida ────────────────────────────────

def test_t5_new_key_new_operation(monkeypatch):
    conn, raw = _sqlite()
    sim = _MPSim()
    _wire(monkeypatch, conn, sim)
    routes.handle_post_subscription(_Handler(_bearer(10)), _Parsed(), _card('intent-k1-aaaa'), None)
    routes.handle_post_subscription(_Handler(_bearer(10)), _Parsed(), _card('intent-k2-bbbb'), None)
    assert sim.created == 2
    assert len(_sub(raw)) == 2


# ── T6 — mesma chave + payload diferente → conflito ──────────────────────────

def test_t6_same_key_different_payload_conflict(monkeypatch):
    conn, raw = _sqlite()
    sim = _MPSim()
    _wire(monkeypatch, conn, sim)
    k = 'intent-dddd-4444'
    r1 = routes.handle_post_subscription(_Handler(_bearer(10)), _Parsed(), _card(k, plan='start'), None)
    r2 = routes.handle_post_subscription(_Handler(_bearer(10)), _Parsed(), _card(k, plan='business'), None)
    assert r1[0] == 201
    assert r2[0] == 409 and r2[1]['error']['code'] == 'IDEMPOTENCY_KEY_CONFLICT'
    assert sim.created == 1  # o conflito não cria um segundo efeito


# ── T7 — mesma chave em empresa diferente → isolado (nunca recupera a de A) ───

def test_t7_cross_tenant_same_key_isolated(monkeypatch):
    conn, raw = _sqlite()
    sim = _MPSim()
    _wire(monkeypatch, conn, sim)
    k = 'intent-shared-5555'
    ra = routes.handle_post_subscription(_Handler(_bearer(10, company_id=1)), _Parsed(), _card(k), None)
    rb = routes.handle_post_subscription(_Handler(_bearer(20, company_id=2)), _Parsed(), _card(k), None)
    assert ra[0] == 201 and rb[0] == 201
    assert sim.created == 2  # chave namespaced por empresa → dois recursos distintos
    a = _sub(raw, company=1)
    b = _sub(raw, company=2)
    assert len(a) == 1 and len(b) == 1
    assert a[0]['preapproval_id'] != b[0]['preapproval_id']  # B nunca recebeu o de A


# ── T8/T9/T10 — autoridade #1017 preservada sob idempotência ─────────────────

def test_t8_client_amount_still_rejected(monkeypatch):
    conn, raw = _sqlite()
    sim = _MPSim()
    _wire(monkeypatch, conn, sim)
    body = {**_card('intent-eeee-6666'), 'amount': 1}
    with pytest.raises(ValueError):
        routes.handle_post_subscription(_Handler(_bearer(10)), _Parsed(), body, None)
    assert sim.created == 0


def test_t9_client_company_still_rejected(monkeypatch):
    conn, raw = _sqlite()
    sim = _MPSim()
    _wire(monkeypatch, conn, sim)
    body = {**_card('intent-ffff-7777'), 'company_id': 2}
    with pytest.raises(ValueError):
        routes.handle_post_subscription(_Handler(_bearer(10)), _Parsed(), body, None)
    assert sim.created == 0


def test_t10_created_by_is_actor(monkeypatch):
    conn, raw = _sqlite()
    sim = _MPSim()
    _wire(monkeypatch, conn, sim)
    routes.handle_post_subscription(_Handler(_bearer(10)), _Parsed(), _card('intent-gggg-8888'), None)
    row = _sub(raw)[0]
    assert row['created_by'] == 10 and row['origin'] == 'authenticated'


# ── T6b — nonce ausente/ inválido → 400 (obrigatório) ────────────────────────

def test_idempotency_key_required(monkeypatch):
    conn, raw = _sqlite()
    sim = _MPSim()
    _wire(monkeypatch, conn, sim)
    body = {'plan_key': 'start', 'cycle': 'monthly', 'payer_email': 'a@b.com', 'card_token': 't'}
    with pytest.raises(ValueError):
        routes.handle_post_subscription(_Handler(_bearer(10)), _Parsed(), body, None)
    assert sim.created == 0


# ── T13 — histórico sem idempotency continua válido ──────────────────────────

def test_t13_historical_subscription_without_attempt(monkeypatch):
    conn, raw = _sqlite()
    # assinatura legada: criada direto, sem payment_attempts
    subscriptions_service.record_subscription(
        conn, company_id=1, plan_key='start', cycle='monthly', payment_method='card',
        preapproval_id='LEGACY', status='authorized', amount=297.0, created_by=10, origin='authenticated')
    conn.commit()
    cur = subscriptions_service.get_current_subscription(conn, 1)
    assert cur and cur['preapproval_id'] == 'LEGACY'  # continua encontrável


# ── T14 — webhook usa company persistida, não do payload ─────────────────────

def test_t14_webhook_uses_persisted_company(monkeypatch):
    conn, raw = _sqlite()
    sim = _MPSim()
    _wire(monkeypatch, conn, sim)
    monkeypatch.setattr(mp_client, 'get', lambda path: {'id': 'WH', 'status': 'authorized'})
    subscriptions_service.record_subscription(
        conn, company_id=2, plan_key='start', cycle='monthly', payment_method='card',
        preapproval_id='WH', status='pending', amount=297.0, created_by=20, origin='authenticated')
    conn.commit()
    res = routes.handle_post_webhook(_Handler(headers={}), _Parsed(path='/api/payments/webhook'),
                                     {'type': 'preapproval', 'data': {'id': 'WH'}, 'company_id': 1}, None)
    assert res[0] == 200
    audit = conn.execute("SELECT company_id FROM subscription_audit_logs WHERE action='status_synced'").fetchone()
    assert dict(audit)['company_id'] == 2  # persistida (2), não payload (1)


# ── T15 — cliente first-party: chave estável no retry, nova por seleção ──────

def test_t15_client_key_lifecycle():
    js = (os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    src = open(os.path.join(js, 'static', 'js', 'pagamento.js'), encoding='utf-8').read()
    assert 'checkoutIntentKey' in src and 'function newIntentKey' in src
    # nova seleção regenera a chave…
    assert 'checkoutIntentKey = newIntentKey()' in src
    # …e basePayload a envia
    import re
    m = re.search(r'function basePayload\(\)\s*\{(.*?)\n\}', src, re.DOTALL)
    assert m and 'idempotency_key' in m.group(1)


# ── T18 — o índice UNIQUE é load-bearing (claim duplicado falha) ─────────────

def test_t18_unique_index_is_load_bearing():
    conn, raw = _sqlite()
    checkout_idempotency.claim(
        conn, company_id=1, client_key='dup-key-9999', fingerprint='fp', actor_user_id=10,
        payment_method='card', plan_key='start', cycle='monthly', external_reference='x')
    conn.commit()
    # Segundo INSERT cru com a MESMA (company, key) deve violar o UNIQUE.
    with pytest.raises(sqlite3.IntegrityError):
        raw.execute(
            "INSERT INTO payment_attempts (company_id, idempotency_key, status, created_at, updated_at) "
            "VALUES (1, 'dup-key-9999', 'processing', '', '')")
        raw.commit()
    # índice presente e UNIQUE
    idx = {r['name']: r['unique'] for r in raw.execute("PRAGMA index_list('payment_attempts')")}
    assert idx.get('idx_payment_attempts_company_key') == 1


# ═══════════════ PostgreSQL real (concorrência / restart / timeout) ═══════════

_PG_COMPANY = 940001


def _pg_cleanup():
    import psycopg2
    cn = psycopg2.connect(PG)
    cur = cn.cursor()
    for t in ('subscription_audit_logs', 'subscriptions', 'payments', 'payment_attempts'):
        cur.execute(f'DELETE FROM {t} WHERE company_id = %s', (_PG_COMPANY,))
    cn.commit()
    cn.close()


@pytest.fixture
def pg_wire(monkeypatch):
    """get_connection real (pool PG) + require_actor fake (sem FK em subscriptions)."""
    from core.database import get_connection
    _pg_cleanup()
    monkeypatch.setattr(routes, 'send_json', lambda h, s, p: (s, p))
    monkeypatch.setattr(routes, 'require_actor', lambda connection, uid:
                        {'id': int(uid), 'role': 'general_admin', 'company_id': _PG_COMPANY})
    # get_connection real: NÃO sobrescrever.
    yield get_connection
    _pg_cleanup()


def _pg_sub_count():
    import psycopg2
    cn = psycopg2.connect(PG)
    cur = cn.cursor()
    cur.execute('SELECT count(*) FROM subscriptions WHERE company_id = %s', (_PG_COMPANY,))
    n = cur.fetchone()[0]
    cn.close()
    return n


@requires_pg
def test_t2_t16_concurrency_same_key_one_effect(pg_wire, monkeypatch):
    sim = _MPSim(delay=0.03)  # amplia a janela de corrida
    monkeypatch.setattr(mp_client, 'post', sim.post)
    k = f'intent-conc-{uuid.uuid4()}'
    results = []

    def worker():
        try:
            r = routes.handle_post_subscription(
                _Handler(_bearer(10, company_id=_PG_COMPANY)), _Parsed(), _card(k), None)
            results.append(r[0])
        except Exception as e:  # noqa: BLE001 - registrado p/ asserção
            results.append(repr(e))

    threads = [threading.Thread(target=worker) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert sim.created == 1, f'mais de um efeito externo sob concorrência: {sim.calls}'
    assert _pg_sub_count() == 1, 'mais de uma assinatura persistida'
    assert results.count(201) == 1  # um vencedor cria; os demais reconciliam
    assert all(r in (201, 200) for r in results), results


@requires_pg
def test_t17_concurrency_distinct_keys_independent(pg_wire, monkeypatch):
    sim = _MPSim(delay=0.01)
    monkeypatch.setattr(mp_client, 'post', sim.post)
    keys = [f'intent-indep-{i}-{uuid.uuid4()}' for i in range(10)]

    def worker(k):
        routes.handle_post_subscription(
            _Handler(_bearer(10, company_id=_PG_COMPANY)), _Parsed(), _card(k), None)

    threads = [threading.Thread(target=worker, args=(k,)) for k in keys]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert sim.created == 10  # chaves distintas → operações independentes
    assert _pg_sub_count() == 10


@requires_pg
def test_t11_restart_recovery_via_mp_idempotency(pg_wire, monkeypatch):
    """Processo A cria no MP e 'morre' antes de persistir (rollback total);
    um retry posterior recupera o MESMO preapproval pela chave do MP."""
    sim = _MPSim()
    monkeypatch.setattr(mp_client, 'post', sim.post)
    real_record = subscriptions_service.record_subscription
    state = {'fail': True}

    def flaky(*a, **k):
        if state['fail']:
            state['fail'] = False
            raise RuntimeError('crash pós-MP')
        return real_record(*a, **k)

    monkeypatch.setattr(subscriptions_service, 'record_subscription', flaky)
    k = f'intent-restart-{uuid.uuid4()}'
    r1 = routes.handle_post_subscription(_Handler(_bearer(10, company_id=_PG_COMPANY)), _Parsed(), _card(k), None)
    assert r1[0] == 503
    r2 = routes.handle_post_subscription(_Handler(_bearer(10, company_id=_PG_COMPANY)), _Parsed(), _card(k), None)
    assert r2[0] == 201
    assert sim.created == 1  # mesmo preapproval, nenhum órfão duplicado
    assert _pg_sub_count() == 1


@requires_pg
def test_t12_ambiguous_timeout_then_retry(pg_wire, monkeypatch):
    """Timeout: o MP pode ter criado X. O retry com a MESMA chave recupera X,
    nunca cria Y."""
    sim = _MPSim()
    from modules.payments.mp_client import MercadoPagoError
    created_holder = {}
    state = {'timeout': True}

    def timeout_then_ok(path, body, *, idempotency_key=None):
        if state['timeout']:
            state['timeout'] = False
            # O MP de fato cria o recurso, mas o backend vê timeout.
            created_holder['res'] = sim.post(path, body, idempotency_key=idempotency_key)
            raise MercadoPagoError('timeout', status=504, response={})
        return sim.post(path, body, idempotency_key=idempotency_key)

    monkeypatch.setattr(mp_client, 'post', timeout_then_ok)
    k = f'intent-timeout-{uuid.uuid4()}'
    r1 = routes.handle_post_subscription(_Handler(_bearer(10, company_id=_PG_COMPANY)), _Parsed(), _card(k), None)
    assert r1[0] in (502, 503, 504)  # ambíguo, sem 201 enganoso
    r2 = routes.handle_post_subscription(_Handler(_bearer(10, company_id=_PG_COMPANY)), _Parsed(), _card(k), None)
    assert r2[0] == 201
    assert sim.created == 1  # X recuperado pela idempotência do MP, nunca Y
    assert _pg_sub_count() == 1
