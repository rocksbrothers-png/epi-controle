"""1G-C — contrato seguro de checkout autenticado do Corporate (#1009/#1010).

ANTES: `POST /api/payments/{subscriptions,pix,boleto}` eram ANÔNIMOS e confiavam
no corpo — o cliente escolhia empresa, tenant, ator (created_by), preço e o
plano do Mercado Pago. DEPOIS:

  - AUTORIDADE DE IDENTIDADE = Bearer autenticado (exigência LOCAL, independente
    de JWT_ENFORCEMENT_MODE — F-01). Sem/ inválido → 401 nos três modos.
  - AUTORIDADE DE EMPRESA   = identidade server-side do ator (nunca o corpo).
  - AUTORIDADE DE PREÇO     = catálogo server-side (SUBSCRIPTION_PLANS).
  - created_by              = ator autenticado; origin = 'authenticated'.
  - Campos de autoridade no corpo (company_id/tenant_id/actor_user_id/created_by/
    amount/plan_id/frequency/frequency_type/currency) → 400 explícito.

Os testes dirigem os HANDLERS REAIS. As recusas (T1–T6, T11) levantam ANTES de
`get_connection`/Mercado Pago — um sentinela prova que o banco/MP nunca é tocado.
Os fluxos legítimos usam SQLite em memória + `mp_client` mockado, e medem corpo
do MP, estado do banco, company/tenant, created_by, origin e a assinatura
vigente — não apenas o status HTTP.

DIVERGÊNCIA INTENCIONAL vs. SaaS (PR #391): o Corporate NÃO usa checkout_token
(T18). A empresa vem da identidade autenticada, não de uma capability de signup.
"""

import re
import sqlite3
from pathlib import Path

import pytest

import core.security as seguranca
from modules.payments import mp_client, routes, service, subscriptions_service

AuthenticationError = seguranca.AuthenticationError
MODES = ('off', 'shadow', 'enforce')
REPO_ROOT = Path(__file__).resolve().parents[1]


# ── Dublês mínimos ────────────────────────────────────────────────────────────

class _Handler:
    command = 'POST'
    client_address = ('127.0.0.1',)

    def __init__(self, auth=''):
        self.headers = {'Authorization': auth} if auth else {}


class _Parsed:
    def __init__(self, query='', path='/api/payments/subscriptions'):
        self.query = query
        self.path = path


def _bearer(user_id, role='general_admin', company_id=1):
    return 'Bearer ' + seguranca.create_jwt_token(
        {'id': user_id, 'role': role, 'company_id': company_id}
    )


class _ReachedDB(Exception):
    """Sentinela: a rota chegou a `get_connection`. Numa recusa correta isso
    NUNCA acontece — a negativa (401/400) vem antes de qualquer banco/MP."""


class NoCloseConn:
    """SQLite :memory: cujo close() é no-op, para inspecionar o estado após o
    handler (que usa `with closing(get_connection())`)."""

    def __init__(self):
        self._c = sqlite3.connect(':memory:')
        self._c.row_factory = sqlite3.Row
        service.ensure_payment_tables(self._c)
        service.ensure_subscription_tables(self._c)

    def __getattr__(self, name):
        return getattr(self._c, name)

    def close(self):  # no-op: preserva o :memory: para asserção pós-handler
        pass


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def mp_calls(monkeypatch):
    """Captura toda chamada ao Mercado Pago e devolve um resultado controlado."""
    calls = []

    def fake_post(path, body, **kwargs):
        calls.append({'path': path, 'body': body})
        if path == '/preapproval':
            return {'id': 'SUB_MP', 'status': 'authorized', 'init_point': 'https://mp/sub'}
        return {
            'id': 'PAY_MP', 'status': 'pending', 'status_detail': 'pending', 'currency_id': 'BRL',
            'point_of_interaction': {'transaction_data': {'qr_code': 'QR', 'qr_code_base64': 'B64'}},
            'transaction_details': {'external_resource_url': 'https://mp/boleto.pdf'},
        }

    monkeypatch.setattr(mp_client, 'post', fake_post)
    return calls


@pytest.fixture
def no_db(monkeypatch):
    """Para recusas: qualquer acesso a banco é 'passou indevido'."""
    def _boom():
        raise _ReachedDB
    monkeypatch.setattr(routes, 'get_connection', _boom)


def _wire_authenticated(monkeypatch, *, actor):
    """Conexão real (SQLite) + ator server-side controlado. Devolve a conexão.

    `require_actor` é substituído para devolver o ator — provando que a empresa
    vem da IDENTIDADE (não do corpo); o teste confere que o uid recebido é o do
    TOKEN."""
    conn = NoCloseConn()
    monkeypatch.setattr(routes, 'get_connection', lambda: conn)
    # send_json escreve no handler HTTP real; aqui capturamos (status, payload).
    monkeypatch.setattr(routes, 'send_json', lambda handler, status, payload: (status, payload))

    def fake_require_actor(connection, actor_user_id):
        assert int(actor_user_id) == int(actor['id']), 'rota resolveu ator fora do token'
        return dict(actor)

    monkeypatch.setattr(routes, 'require_actor', fake_require_actor)
    return conn


def _sub_rows(conn):
    return [dict(r) for r in conn.execute('SELECT * FROM subscriptions ORDER BY id').fetchall()]


def _pay_rows(conn):
    return [dict(r) for r in conn.execute('SELECT * FROM payments ORDER BY id').fetchall()]


_CARD_BODY = {'plan_key': 'start', 'cycle': 'monthly',
              'payer_email': 'adm@empresa.com', 'card_token': 'tok_abc'}
_PIX_BODY = {'plan_key': 'start', 'cycle': 'monthly', 'payer_email': 'adm@empresa.com'}


# ── T1/T2 — Bearer obrigatório LOCAL (401) nos três modos ─────────────────────

class TestAuthMatrix:
    @pytest.mark.parametrize('mode', MODES)
    def test_t1_sem_bearer_401(self, monkeypatch, no_db, mp_calls, mode):
        monkeypatch.setattr(seguranca, 'JWT_ENFORCEMENT_MODE', mode)
        with pytest.raises(AuthenticationError):
            routes.handle_post_subscription(_Handler(), _Parsed(), dict(_CARD_BODY), None)
        assert mp_calls == []

    @pytest.mark.parametrize('mode', MODES)
    def test_t1_sem_bearer_401_pix(self, monkeypatch, no_db, mp_calls, mode):
        monkeypatch.setattr(seguranca, 'JWT_ENFORCEMENT_MODE', mode)
        with pytest.raises(AuthenticationError):
            routes.handle_post_pix(_Handler(), _Parsed(path='/api/payments/pix'), dict(_PIX_BODY), None)
        assert mp_calls == []

    @pytest.mark.parametrize('mode', MODES)
    def test_t2_bearer_invalido_401(self, monkeypatch, no_db, mp_calls, mode):
        monkeypatch.setattr(seguranca, 'JWT_ENFORCEMENT_MODE', mode)
        for auth in ('Token xyz', 'Bearer garbage'):
            with pytest.raises(AuthenticationError):
                routes.handle_post_subscription(_Handler(auth=auth), _Parsed(), dict(_CARD_BODY), None)
        assert mp_calls == []

    @pytest.mark.parametrize('mode', MODES)
    def test_bearer_obrigatorio_mesmo_com_actor_no_corpo(self, monkeypatch, no_db, mp_calls, mode):
        # F-01 aplicado ao checkout: sem Bearer, um actor_user_id FORJADO no corpo
        # NÃO autentica — a recusa (401 pelo gate local) vem nos três modos, nunca
        # um "aceito porque o modo global é off". (Isola o gate require_bearer_actor.)
        monkeypatch.setattr(seguranca, 'JWT_ENFORCEMENT_MODE', mode)
        body = {**_CARD_BODY, 'actor_user_id': 7}
        with pytest.raises(AuthenticationError):
            routes.handle_post_subscription(_Handler(), _Parsed(), body, None)
        assert mp_calls == []

    @pytest.mark.parametrize('mode', MODES)
    def test_bearer_valido_passa(self, monkeypatch, mp_calls, mode):
        # Prova positiva: com Bearer válido, o fluxo chega ao MP nos três modos.
        monkeypatch.setattr(seguranca, 'JWT_ENFORCEMENT_MODE', mode)
        _wire_authenticated(monkeypatch, actor={'id': 7, 'role': 'general_admin', 'company_id': 1})
        routes.handle_post_subscription(_Handler(auth=_bearer(7)), _Parsed(), dict(_CARD_BODY), None)
        assert len(mp_calls) == 1 and mp_calls[0]['path'] == '/preapproval'


# ── T3–T6 — campos de autoridade no corpo → 400, MP não chamado ───────────────

class TestRejectAuthorityFields:
    @pytest.mark.parametrize('field,value', [
        ('amount', 1),            # T3
        ('amount', -5),           # T3 (negativo)
        ('plan_id', 'PLAN_X'),    # T4
        ('frequency', 1),         # T4
        ('frequency_type', 'months'),  # T4
        ('currency', 'USD'),      # T4
        ('company_id', 2),        # T5
        ('tenant_id', 'other'),   # T5
        ('actor_user_id', 1),     # T6
        ('created_by', 1),        # T6
    ])
    def test_t3_t6_corpo_com_autoridade_400(self, monkeypatch, no_db, mp_calls, field, value):
        body = {**_CARD_BODY, field: value}
        with pytest.raises(ValueError):
            routes.handle_post_subscription(_Handler(auth=_bearer(7)), _Parsed(), body, None)
        assert mp_calls == [], 'MP foi chamado apesar do campo de autoridade'

    def test_t3_amount_no_pix_400(self, monkeypatch, no_db, mp_calls):
        body = {**_PIX_BODY, 'amount': 1}
        with pytest.raises(ValueError):
            routes.handle_post_pix(_Handler(auth=_bearer(7)), _Parsed(path='/api/payments/pix'), body, None)
        assert mp_calls == []

    def test_t5_company_id_na_query_400(self, monkeypatch, no_db, mp_calls):
        # Robustez: autoridade na QUERY também é recusada (nunca consultada).
        with pytest.raises(ValueError):
            routes.handle_post_subscription(
                _Handler(auth=_bearer(7)), _Parsed(query='company_id=2'), dict(_CARD_BODY), None)
        assert mp_calls == []


# ── T7/T8 — empresa vem do ator; A não opera B ────────────────────────────────

class TestCompanyAuthority:
    def test_t7_bearer_a_com_company_b_no_corpo_400(self, monkeypatch, no_db, mp_calls):
        body = {**_CARD_BODY, 'company_id': 2}  # ator A (empresa 1) tenta empresa 2
        with pytest.raises(ValueError):
            routes.handle_post_subscription(_Handler(auth=_bearer(7, company_id=1)), _Parsed(), body, None)
        assert mp_calls == []

    def test_t8_fluxo_legitimo_usa_company_do_ator(self, monkeypatch, mp_calls):
        # Sem campo proibido: a empresa persistida é a do ATOR (1), não do corpo.
        conn = _wire_authenticated(monkeypatch, actor={'id': 7, 'role': 'general_admin', 'company_id': 1})
        routes.handle_post_subscription(_Handler(auth=_bearer(7)), _Parsed(), dict(_CARD_BODY), None)
        rows = _sub_rows(conn)
        assert len(rows) == 1
        assert rows[0]['company_id'] == 1
        assert str(rows[0]['tenant_id'] or '') == ''  # Corporate: tenant server-side vazio


# ── T9 — created_by = ator autenticado ────────────────────────────────────────

class TestCreatedBy:
    def test_t9_created_by_eh_ator_autenticado(self, monkeypatch, mp_calls):
        conn = _wire_authenticated(monkeypatch, actor={'id': 42, 'role': 'general_admin', 'company_id': 3})
        routes.handle_post_subscription(_Handler(auth=_bearer(42, company_id=3)), _Parsed(), dict(_CARD_BODY), None)
        row = _sub_rows(conn)[0]
        assert row['created_by'] == 42
        assert row['updated_by'] == 42
        assert row['origin'] == 'authenticated'
        # Auditoria registra o ator autenticado.
        audit = conn.execute(
            "SELECT * FROM subscription_audit_logs WHERE action='created'").fetchone()
        assert dict(audit)['actor_user_id'] == 42


# ── T10/T12/T13 — preço enviado ao MP = catálogo server-side ──────────────────

class TestPriceAuthority:
    def test_t10_card_preco_catalogo(self, monkeypatch, mp_calls):
        conn = _wire_authenticated(monkeypatch, actor={'id': 7, 'role': 'general_admin', 'company_id': 1})
        routes.handle_post_subscription(_Handler(auth=_bearer(7)), _Parsed(),
                                        {'plan_key': 'start', 'cycle': 'monthly',
                                         'payer_email': 'a@b.com', 'card_token': 't'}, None)
        body = mp_calls[0]['body']
        # Sem preapproval_plan criado, o preço vai no auto_recurring — do CATÁLOGO.
        assert body['auto_recurring']['transaction_amount'] == 297.00
        assert body['auto_recurring']['currency_id'] == 'BRL'
        assert _sub_rows(conn)[0]['amount'] == 297.00

    def test_t10b_card_annual_preco_catalogo(self, monkeypatch, mp_calls):
        _wire_authenticated(monkeypatch, actor={'id': 7, 'role': 'general_admin', 'company_id': 1})
        routes.handle_post_subscription(_Handler(auth=_bearer(7)), _Parsed(),
                                        {'plan_key': 'corporate', 'cycle': 'annual',
                                         'payer_email': 'a@b.com', 'card_token': 't'}, None)
        body = mp_calls[0]['body']
        assert body['auto_recurring']['transaction_amount'] == 12970.00
        assert body['auto_recurring']['frequency_type'] == 'years'

    def test_t12_pix_preco_catalogo(self, monkeypatch, mp_calls):
        conn = _wire_authenticated(monkeypatch, actor={'id': 7, 'role': 'general_admin', 'company_id': 1})
        routes.handle_post_pix(_Handler(auth=_bearer(7)), _Parsed(path='/api/payments/pix'),
                               {'plan_key': 'business', 'cycle': 'monthly', 'payer_email': 'a@b.com'}, None)
        body = mp_calls[0]['body']
        assert body['payment_method_id'] == 'pix'
        assert body['transaction_amount'] == 597.00
        assert _pay_rows(conn)[0]['amount'] == 597.00
        assert _pay_rows(conn)[0]['company_id'] == 1

    def test_t13_boleto_preco_catalogo(self, monkeypatch, mp_calls):
        _wire_authenticated(monkeypatch, actor={'id': 7, 'role': 'general_admin', 'company_id': 1})
        routes.handle_post_boleto(_Handler(auth=_bearer(7)), _Parsed(path='/api/payments/boleto'),
                                  {'plan_key': 'start', 'cycle': 'monthly', 'payer_email': 'a@b.com'}, None)
        body = mp_calls[0]['body']
        assert body['payment_method_id'] == 'bolbradesco'
        assert body['transaction_amount'] == 297.00


# ── T11 — contact_only/enterprise recusado (400), MP não chamado ──────────────

class TestContactOnly:
    def test_t11_enterprise_recusado(self, monkeypatch, no_db, mp_calls):
        body = {'plan_key': 'enterprise', 'cycle': 'monthly',
                'payer_email': 'a@b.com', 'card_token': 't'}
        with pytest.raises(ValueError):
            routes.handle_post_subscription(_Handler(auth=_bearer(7)), _Parsed(), body, None)
        assert mp_calls == []

    def test_t11b_plano_inexistente_recusado(self, monkeypatch, no_db, mp_calls):
        body = {'plan_key': 'nao_existe', 'cycle': 'monthly',
                'payer_email': 'a@b.com', 'card_token': 't'}
        with pytest.raises(ValueError):
            routes.handle_post_subscription(_Handler(auth=_bearer(7)), _Parsed(), body, None)
        assert mp_calls == []


# ── T14/T15 — vigência: linha não-bound não sombreia; histórico legítimo ──────

class TestCurrentSubscriptionEligibility:
    def _conn(self):
        return NoCloseConn()

    def test_t14_linha_nao_bound_nao_sombreia(self):
        conn = self._conn()
        # Legítima autenticada (bound) primeiro…
        subscriptions_service.record_subscription(
            conn, company_id=1, plan_key='start', cycle='monthly', payment_method='card',
            preapproval_id='PRE_BOUND', status='authorized', amount=297.0,
            created_by=7, origin='authenticated')
        # …e DEPOIS uma linha SEM binding (origin=''), mais recente (id maior),
        # como a rota pública vulnerável anterior poderia ter injetado.
        subscriptions_service.record_subscription(
            conn, company_id=1, plan_key='corporate', cycle='monthly', payment_method='card',
            preapproval_id='PRE_UNBOUND', status='authorized', amount=1.0,
            created_by=None, origin='')
        cur = subscriptions_service.get_current_subscription(conn, 1)
        assert cur['preapproval_id'] == 'PRE_BOUND', 'linha sem binding sombreou a legítima'
        assert cur['origin'] == 'authenticated'

    def test_t15_historico_legado_continua_encontravel(self):
        conn = self._conn()
        # Empresa que só tem linha LEGADA (origin='') — compat histórica: ainda
        # encontrável (não invalidamos registros pré-binding).
        subscriptions_service.record_subscription(
            conn, company_id=2, plan_key='start', cycle='monthly', payment_method='card',
            preapproval_id='PRE_LEGACY', status='authorized', amount=297.0,
            created_by=None, origin='')
        cur = subscriptions_service.get_current_subscription(conn, 2)
        assert cur is not None and cur['preapproval_id'] == 'PRE_LEGACY'


# ── T16 — webhook/lifecycle usa company PERSISTIDA, não payload ───────────────

class TestWebhookUsesPersistedCompany:
    def test_t16_sync_usa_company_da_linha(self):
        conn = NoCloseConn()
        subscriptions_service.record_subscription(
            conn, company_id=5, plan_key='start', cycle='monthly', payment_method='card',
            preapproval_id='PRE_WH', status='pending', amount=297.0,
            created_by=7, origin='authenticated')
        ok = subscriptions_service.sync_subscription_status(conn, 'PRE_WH', 'authorized')
        assert ok is True
        # A empresa na auditoria do sync veio da LINHA (5), não de qualquer payload.
        audit = conn.execute(
            "SELECT * FROM subscription_audit_logs WHERE action='status_synced'").fetchone()
        assert dict(audit)['company_id'] == 5
        row = conn.execute(
            "SELECT * FROM subscriptions WHERE preapproval_id='PRE_WH'").fetchone()
        assert dict(row)['status'] == 'active'


# ── T17 — cliente first-party envia Bearer e só campos permitidos ─────────────

class TestFirstPartyClientContract:
    def _js(self):
        return (REPO_ROOT / 'static' / 'js' / 'pagamento.js').read_text(encoding='utf-8')

    def test_t17_envia_bearer(self):
        js = self._js()
        assert 'epi-session-v4-token' in js
        assert re.search(r'Authorization:\s*`Bearer \$\{token\}`', js)

    def test_t17_basepayload_so_campos_permitidos(self):
        js = self._js()
        m = re.search(r'function basePayload\(\)\s*\{(.*?)\n\}', js, re.DOTALL)
        assert m, 'basePayload não encontrado'
        body = m.group(1)
        assert 'plan_key' in body and 'cycle' in body and 'payer_email' in body
        for forbidden in ('plan_id', 'amount', 'company_id', 'tenant_id', 'actor_user_id',
                          'created_by', 'frequency', 'currency'):
            assert forbidden not in body, f'basePayload ainda envia {forbidden}'


# ── T18 — NENHUM checkout_token/capability foi introduzido no Corporate ───────

class TestNoCheckoutToken:
    def test_t18_sem_modulo_checkout_sessions(self):
        assert not (REPO_ROOT / 'core' / 'checkout_sessions.py').exists()
        with pytest.raises(ImportError):
            __import__('core.checkout_sessions')

    def test_t18_sem_checkout_token_no_backend(self):
        for rel in ('modules/payments/routes.py', 'modules/payments/service.py',
                    'modules/payments/subscriptions_service.py'):
            src = (REPO_ROOT / rel).read_text(encoding='utf-8')
            assert 'checkout_token' not in src, f'{rel} menciona checkout_token'
            assert 'checkout_sessions' not in src, f'{rel} menciona checkout_sessions'

    def test_t18_sem_migration_de_checkout_sessions(self):
        mig_dir = REPO_ROOT / 'epi_backend' / 'migrations'
        if mig_dir.exists():
            for p in mig_dir.glob('*.py'):
                assert 'checkout_sessions' not in p.read_text(encoding='utf-8'), \
                    f'{p.name} cria checkout_sessions'
