"""#1018 — autoridade financeira server-side em change-plan / reactivate.

ANTES: as rotas /api/subscriptions/change-plan e /reactivate aceitavam `amount`
(inclusive 0 e negativo) e `plan_id` (id de plano do Mercado Pago) do cliente,
que iam direto ao preapproval. DEPOIS: o cliente informa apenas a INTENÇÃO
comercial (plan_key/cycle); preço, moeda, recorrência e o plano do MP são
resolvidos server-side pelo catálogo canônico do #1017.

Dirige os HANDLERS reais com SQLite :memory: e um MP que captura o corpo enviado.
Stub único: routes.require_actor (empresa server-side; sem FK a semear)."""

import sqlite3

import core.security as seguranca
from modules.payments import mp_client, routes, service, subscriptions_service

C1, C2 = 1, 2
U1, U2 = 10, 20
ACTORS = {
    U1: {'id': U1, 'role': 'general_admin', 'company_id': C1},
    U2: {'id': U2, 'role': 'general_admin', 'company_id': C2},
}


class _MPSim:
    def __init__(self):
        self.calls = []   # (path, body)
        self.puts = []
        self._n = 0

    def post(self, path, body, *, idempotency_key=None):
        self.calls.append((path, dict(body)))
        self._n += 1
        return {'id': f'SUB{self._n}', 'status': 'authorized', 'init_point': 'x',
                'auto_recurring': dict(body.get('auto_recurring') or {})}

    def put(self, path, body):
        self.puts.append((path, dict(body)))
        return {'status': 'cancelled'}

    @property
    def created(self):
        return self._n

    def amount_sent(self):
        for path, body in self.calls:
            if path == '/preapproval':
                ar = body.get('auto_recurring') or {}
                if 'transaction_amount' in ar:
                    return ar['transaction_amount']
                return ('preapproval_plan_id', body.get('preapproval_plan_id'))
        return None


class _Handler:
    command = 'POST'
    client_address = ('127.0.0.1',)

    def __init__(self, token='', path='/api/subscriptions/change-plan'):
        self.headers = {'Authorization': f'Bearer {token}'} if token else {}
        self.path = path


class _Parsed:
    def __init__(self, query='', path='/api/subscriptions/change-plan'):
        self.query = query
        self.path = path


def _bearer(uid):
    a = ACTORS[uid]
    return seguranca.create_jwt_token({'id': uid, 'role': a['role'], 'company_id': a['company_id']})


def _sqlite():
    c = sqlite3.connect(':memory:', check_same_thread=False)
    c.row_factory = sqlite3.Row
    service.ensure_payment_tables(c)
    service.ensure_subscription_tables(c)

    class _NoClose:
        def __getattr__(self, n):
            return getattr(c, n)

        def close(self):
            pass

    return _NoClose(), c


def _wire(monkeypatch, conn, sim, actors=ACTORS):
    monkeypatch.setattr(routes, 'get_connection', lambda: conn)
    monkeypatch.setattr(routes, 'require_actor', lambda connection, uid: dict(actors[int(uid)]))
    monkeypatch.setattr(routes, 'send_json', lambda h, s, p: (s, p))
    monkeypatch.setattr(mp_client, 'post', sim.post)
    monkeypatch.setattr(mp_client, 'put', sim.put)


def _call(fn, *a):
    try:
        return fn(*a)
    except seguranca.AuthenticationError as e:
        return (401, {'error': str(e)})
    except PermissionError as e:
        return (403, {'error': str(e)})
    except ValueError as e:
        return (400, {'error': str(e)})


def _change(h, body):
    return _call(routes.handle_post_subscription_change_plan, h, _Parsed(), body, None)


def _react(h, body):
    return _call(routes.handle_post_subscription_reactivate,
                 h, _Parsed(path='/api/subscriptions/reactivate'), body, None)


def _subs(conn, company=C1):
    return [dict(r) for r in conn.execute(
        'SELECT * FROM subscriptions WHERE company_id=? ORDER BY id', (company,)).fetchall()]


def _audit_count(conn, company=C1):
    return conn.execute(
        'SELECT count(*) FROM subscription_audit_logs WHERE company_id=?', (company,)).fetchone()[0]


_INTENT = {'plan_key': 'start', 'cycle': 'monthly', 'payer_email': 'a@ex.com', 'card_token': 'tok'}

# ── T1/T2 — body.amount NÃO é autoridade ──────────────────────────────────────

def test_t1_change_plan_amount_rejected(monkeypatch):
    conn, raw = _sqlite(); sim = _MPSim(); _wire(monkeypatch, conn, sim)
    for amt in (1, 0, 0.01, -1, 999999):
        r = _change(_Handler(_bearer(U1)), {**_INTENT, 'amount': amt})
        assert r[0] == 400, (amt, r)
    assert sim.created == 0 and sim.calls == []
    assert _subs(raw) == [] and _audit_count(raw) == 0


def test_t2_reactivate_amount_rejected(monkeypatch):
    conn, raw = _sqlite(); sim = _MPSim(); _wire(monkeypatch, conn, sim)
    for amt in (1, 0, 0.01, -1, 999999):
        r = _react(_Handler(_bearer(U1)), {**_INTENT, 'amount': amt})
        assert r[0] == 400, (amt, r)
    assert sim.created == 0 and _subs(raw) == [] and _audit_count(raw) == 0


# ── T3/T4 — identificador de plano do MP NÃO é autoridade do cliente ──────────

def test_t3_change_plan_mp_plan_id_rejected(monkeypatch):
    conn, raw = _sqlite(); sim = _MPSim(); _wire(monkeypatch, conn, sim)
    for field in ('plan_id', 'mp_plan_id', 'preapproval_plan_id'):
        r = _change(_Handler(_bearer(U1)), {**_INTENT, field: 'MP_PLAN_CLIENT'})
        assert r[0] == 400, (field, r)
    assert sim.created == 0 and _subs(raw) == []


def test_t4_reactivate_mp_plan_id_rejected(monkeypatch):
    conn, raw = _sqlite(); sim = _MPSim(); _wire(monkeypatch, conn, sim)
    for field in ('plan_id', 'mp_plan_id', 'preapproval_plan_id'):
        r = _react(_Handler(_bearer(U1)), {**_INTENT, field: 'MP_PLAN_CLIENT'})
        assert r[0] == 400, (field, r)
    assert sim.created == 0 and _subs(raw) == []


# ── T5/T6 — demais parâmetros financeiros → 400 ───────────────────────────────

def test_t5_change_plan_financial_params_rejected(monkeypatch):
    conn, raw = _sqlite(); sim = _MPSim(); _wire(monkeypatch, conn, sim)
    for field, val in (('currency', 'USD'), ('frequency', 99), ('frequency_type', 'days'),
                       ('transaction_amount', 5), ('price', 5), ('value', 5),
                       ('auto_recurring', {'transaction_amount': 1})):
        r = _change(_Handler(_bearer(U1)), {**_INTENT, field: val})
        assert r[0] == 400, (field, r)
    assert sim.created == 0


def test_t6_reactivate_financial_params_rejected(monkeypatch):
    conn, raw = _sqlite(); sim = _MPSim(); _wire(monkeypatch, conn, sim)
    for field, val in (('currency', 'USD'), ('frequency', 99), ('frequency_type', 'days'),
                       ('transaction_amount', 5), ('price', 5), ('value', 5)):
        r = _react(_Handler(_bearer(U1)), {**_INTENT, field: val})
        assert r[0] == 400, (field, r)
    assert sim.created == 0


# ── T7 — campo financeiro na QUERY também é rejeitado ─────────────────────────

def test_t7_financial_field_in_query_rejected(monkeypatch):
    conn, raw = _sqlite(); sim = _MPSim(); _wire(monkeypatch, conn, sim)
    r = _call(routes.handle_post_subscription_change_plan,
              _Handler(_bearer(U1)), _Parsed(query='amount=1'), dict(_INTENT), None)
    assert r[0] == 400 and sim.created == 0


# ── T8/T9 — fluxo legítimo (só intenção) usa preço server-side do catálogo ────

def test_t8_change_plan_legit_server_price(monkeypatch):
    conn, raw = _sqlite(); sim = _MPSim(); _wire(monkeypatch, conn, sim)
    r = _change(_Handler(_bearer(U1)), dict(_INTENT))
    assert r[0] == 201, r
    assert sim.amount_sent() == 297.00          # catálogo start/monthly, server-side
    rows = _subs(raw)
    assert len(rows) == 1 and float(rows[0]['amount']) == 297.00
    assert rows[0]['created_by'] == U1 and rows[0]['origin'] == 'authenticated'


def test_t9_reactivate_legit_server_price(monkeypatch):
    conn, raw = _sqlite(); sim = _MPSim(); _wire(monkeypatch, conn, sim)
    r = _react(_Handler(_bearer(U1)), dict(_INTENT))
    assert r[0] == 201, r
    assert sim.amount_sent() == 297.00
    assert len(_subs(raw)) == 1


# ── T10 — preço enviado ao MP == catálogo exato, por plano/ciclo ──────────────

def test_t10_price_matches_catalog_exactly(monkeypatch):
    cases = [('start', 'monthly', 297.00), ('start', 'annual', 2970.00),
             ('business', 'monthly', 597.00), ('corporate', 'annual', 12970.00)]
    for plan_key, cycle, expected in cases:
        conn, raw = _sqlite(); sim = _MPSim(); _wire(monkeypatch, conn, sim)
        r = _change(_Handler(_bearer(U1)),
                    {'plan_key': plan_key, 'cycle': cycle, 'payer_email': 'a@ex.com', 'card_token': 't'})
        assert r[0] == 201, (plan_key, cycle, r)
        assert sim.amount_sent() == expected, (plan_key, cycle, sim.amount_sent())


# ── T11 — contact_only (enterprise) não vira bypass ───────────────────────────

def test_t11_contact_only_not_bypass(monkeypatch):
    conn, raw = _sqlite(); sim = _MPSim(); _wire(monkeypatch, conn, sim)
    r = _change(_Handler(_bearer(U1)),
                {'plan_key': 'enterprise', 'cycle': 'monthly', 'payer_email': 'a@ex.com', 'card_token': 't'})
    assert r[0] == 400 and sim.created == 0
    r2 = _react(_Handler(_bearer(U1)),
                {'plan_key': 'enterprise', 'cycle': 'monthly', 'payer_email': 'a@ex.com', 'card_token': 't'})
    assert r2[0] == 400 and sim.created == 0


# ── T12 — plano inexistente → 400 ─────────────────────────────────────────────

def test_t12_invalid_plan_rejected(monkeypatch):
    conn, raw = _sqlite(); sim = _MPSim(); _wire(monkeypatch, conn, sim)
    r = _change(_Handler(_bearer(U1)),
                {'plan_key': 'nope', 'cycle': 'monthly', 'payer_email': 'a@ex.com', 'card_token': 't'})
    assert r[0] == 400 and sim.created == 0


# ── T13 — empresa/ator server-side: company_id no corpo não troca de empresa ──

def test_t13_company_actor_server_side(monkeypatch):
    conn, raw = _sqlite(); sim = _MPSim(); _wire(monkeypatch, conn, sim)
    # ator não-master (empresa 1) tenta indicar company_id=2 no corpo
    r = _change(_Handler(_bearer(U1)), {**_INTENT, 'company_id': C2})
    assert r[0] == 201, r
    assert _subs(raw, C1) and not _subs(raw, C2)   # operou na própria empresa (1), não na 2
    assert _subs(raw, C1)[0]['created_by'] == U1


# ── T14 — cross-company: ator da empresa 2 não afeta a empresa 1 ──────────────

def test_t14_cross_company_isolated(monkeypatch):
    conn, raw = _sqlite(); sim = _MPSim(); _wire(monkeypatch, conn, sim)
    _change(_Handler(_bearer(U1)), dict(_INTENT))        # empresa 1 cria
    _react(_Handler(_bearer(U2)), dict(_INTENT))         # empresa 2 cria (própria)
    assert len(_subs(raw, C1)) == 1 and len(_subs(raw, C2)) == 1
    assert _subs(raw, C1)[0]['created_by'] == U1 and _subs(raw, C2)[0]['created_by'] == U2


# ── T15 — frontend legítimo funciona SEM enviar amount ────────────────────────

def test_t15_legit_without_amount(monkeypatch):
    conn, raw = _sqlite(); sim = _MPSim(); _wire(monkeypatch, conn, sim)
    assert 'amount' not in _INTENT
    r = _change(_Handler(_bearer(U1)), dict(_INTENT))
    assert r[0] == 201 and sim.created == 1


# ── T16 — 400 ⇒ zero efeito externo e zero mutação de DB/audit ────────────────

def test_t16_rejected_has_no_side_effects(monkeypatch):
    conn, raw = _sqlite(); sim = _MPSim(); _wire(monkeypatch, conn, sim)
    _change(_Handler(_bearer(U1)), {**_INTENT, 'amount': 0})
    _react(_Handler(_bearer(U1)), {**_INTENT, 'plan_id': 'X'})
    assert sim.created == 0 and sim.puts == []
    assert _subs(raw) == [] and _audit_count(raw) == 0


# ── T17 — change-plan legítimo cancela o anterior e cria ao preço server-side ─

def test_t17_change_plan_cancels_previous(monkeypatch):
    conn, raw = _sqlite(); sim = _MPSim(); _wire(monkeypatch, conn, sim)
    subscriptions_service.record_subscription(
        conn, company_id=C1, plan_key='start', cycle='monthly', payment_method='card',
        preapproval_id='OLD', status='authorized', amount=297.0, created_by=U1,
        origin='authenticated')
    conn.commit()
    r = _change(_Handler(_bearer(U1)),
                {'plan_key': 'business', 'cycle': 'monthly', 'payer_email': 'a@ex.com', 'card_token': 't'})
    assert r[0] == 201, r
    assert sim.puts and 'OLD' in sim.puts[0][0]        # cancelou o preapproval anterior
    assert sim.amount_sent() == 597.00                 # novo plano, preço server-side


# ── T18 — tenant_id do cliente NÃO é persistido (identidade server-side) ──────

def test_t18_client_tenant_id_not_persisted(monkeypatch):
    conn, raw = _sqlite(); sim = _MPSim(); _wire(monkeypatch, conn, sim)
    r = _change(_Handler(_bearer(U1)), {**_INTENT, 'tenant_id': 'FORJADO'})
    assert r[0] == 201, r
    rows = _subs(raw)
    assert len(rows) == 1 and (rows[0]['tenant_id'] or '') == ''   # server-side '', não 'FORJADO'
