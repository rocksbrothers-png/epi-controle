"""SECURITY HARDENING LOTE 1-A — Mercado Pago: status, webhook e mensagens.

Testes adversariais de S1 (consulta de status), S2 (webhook) e S5/S6 (texto do
Mercado Pago ao cliente). O mesmo arquivo roda no Corporate e no SaaS; o que
muda é só a credencial de status (Bearer no Corporate; Bearer ou
`X-Checkout-Token` no SaaS), detectada pela presença de `core/checkout_sessions`.

Cada cenário roda contra um servidor HTTP REAL (`app.EpiHandler`), para que o
mapeamento de exceções → status HTTP seja o de produção. O banco é SQLite em
memória por padrão e PostgreSQL REAL quando `DATABASE_URL` aponta para uma base
de teste (marcador `pg`): a mesma bateria multi-tenant roda nos dois.

Nenhum segredo real é usado: o segredo de webhook é um marcador de teste
aplicado por monkeypatch, nunca lido do ambiente nem impresso.
"""

import hashlib
import hmac
import http.client
import importlib.util
import io
import json
import os
import sqlite3
import threading
import uuid
from contextlib import redirect_stdout
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

import app as aplicacao
import core.security as seguranca
from modules.payments import mp_client, routes, service, subscriptions_service
from modules.payments.mp_client import MercadoPagoError

ROOT = Path(__file__).resolve().parents[1]
SAAS = importlib.util.find_spec('core.checkout_sessions') is not None
if SAAS:
    from core import checkout_sessions

PG_DSN = os.environ.get('DATABASE_URL', '')
SEGREDO_TESTE = 'segredo-de-teste-lote-1a-nao-e-real'
# Marcador com o formato de prefixo de um Access Token (montado, não é credencial).
MARCADOR_TOKEN = 'APP_USR' + '-' + '9' * 20

EMPRESA_A, EMPRESA_B = 101, 202
ATORES = {
    11: {'id': 11, 'role': 'general_admin', 'company_id': EMPRESA_A},
    22: {'id': 22, 'role': 'general_admin', 'company_id': EMPRESA_B},
    33: {'id': 33, 'role': 'general_admin', 'company_id': None},
}

# Ids "legítimos" — números diferentes por execução para não colidir no PG.
_BASE = int(uuid.uuid4().int % 10**9) * 1000
PAG_A = str(_BASE + 1)        # pagamento Pix da empresa A
PAG_B = str(_BASE + 2)        # pagamento Pix da empresa B
PRE_A = f'pre{_BASE}a'        # preapproval (assinatura) da empresa A
DESCONHECIDO = str(_BASE + 9)


# ── Infraestrutura ────────────────────────────────────────────────────────────

class _SemFechar:
    """Conexão compartilhada: o `closing()` das rotas não a fecha."""

    def __init__(self, conn):
        self._conn = conn

    def __getattr__(self, nome):
        return getattr(self._conn, nome)

    def close(self):
        pass


def _sqlite():
    conn = sqlite3.connect(':memory:', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _pg():
    from core import database
    return database.get_connection()


def _preparar(conn):
    service.ensure_payment_tables(conn)
    service.ensure_subscription_tables(conn)
    if SAAS:
        checkout_sessions.ensure_checkout_session_tables(conn)
    if importlib.util.find_spec('core.checkout_idempotency') is not None:
        from core import checkout_idempotency
        checkout_idempotency.ensure_payment_attempt_tables(conn)
    conn.commit()


def _gravar_pagamento(conn, company_id, mp_id, resource_type='payment', status='pending', raw=None):
    service._record_payment(
        conn, company_id=company_id, plan_id='start', mp_payment_id=mp_id,
        resource_type=resource_type, payer_email='pagador@exemplo.invalid',
        payment_method='pix' if resource_type == 'payment' else 'card', amount=297.0,
        currency='BRL', status=status, status_detail='', external_reference='ref',
        qr_code='', qr_code_base64='', ticket_url='', raw=raw or {},
    )


class _MP:
    """Mercado Pago simulado: registra TODA chamada externa."""

    def __init__(self):
        self.chamadas = []
        self.respostas = {}

    def get(self, path):
        self.chamadas.append(path)
        if path in self.respostas:
            valor = self.respostas[path]
            if isinstance(valor, Exception):
                raise valor
            return dict(valor)
        return {'status': 'approved', 'status_detail': 'accredited'}


@pytest.fixture(params=['sqlite', pytest.param('pg', marks=pytest.mark.skipif(
    not PG_DSN, reason='requer PostgreSQL (DATABASE_URL de teste)'))])
def ambiente(request, monkeypatch):
    bruto = _sqlite() if request.param == 'sqlite' else _pg()
    _preparar(bruto)
    conn = _SemFechar(bruto)
    if request.param == 'pg':
        conn.execute('DELETE FROM payments WHERE mp_payment_id IN (?, ?, ?, ?)', (PAG_A, PAG_B, PRE_A, DESCONHECIDO))
        conn.execute('DELETE FROM subscriptions WHERE preapproval_id = ?', (PRE_A,))
    _gravar_pagamento(conn, EMPRESA_A, PAG_A)
    _gravar_pagamento(conn, EMPRESA_B, PAG_B)
    _gravar_pagamento(conn, EMPRESA_A, PRE_A, resource_type='preapproval')
    tokens = {}
    if SAAS:
        tokens['A'] = checkout_sessions.create_checkout_session(conn, company_id=EMPRESA_A)
        tokens['B'] = checkout_sessions.create_checkout_session(conn, company_id=EMPRESA_B)
    conn.commit()

    mp = _MP()
    monkeypatch.setattr(mp_client, 'get', mp.get)
    monkeypatch.setattr(routes, 'get_connection', lambda: conn)
    monkeypatch.setattr(routes, 'require_actor', lambda connection, uid: dict(ATORES[int(uid)]))
    monkeypatch.setattr(aplicacao.EpiHandler, '_require_bootstrap_ready', lambda self, path: True)
    monkeypatch.setattr(service, 'MERCADO_PAGO_WEBHOOK_SECRET', SEGREDO_TESTE)

    servidor = ThreadingHTTPServer(('127.0.0.1', 0), aplicacao.EpiHandler)
    thread = threading.Thread(target=servidor.serve_forever, daemon=True)
    thread.start()
    try:
        yield {'conn': conn, 'mp': mp, 'porta': servidor.server_address[1], 'tokens': tokens, 'db': request.param}
    finally:
        servidor.shutdown()
        servidor.server_close()
        if request.param == 'pg':
            conn.rollback()
            conn.execute('DELETE FROM payments WHERE mp_payment_id IN (?, ?, ?, ?)', (PAG_A, PAG_B, PRE_A, DESCONHECIDO))
            conn.execute('DELETE FROM subscriptions WHERE preapproval_id = ?', (PRE_A,))
            conn.commit()
            bruto.close()


def _http(amb, metodo, caminho, *, headers=None, corpo=None):
    conexao = http.client.HTTPConnection('127.0.0.1', amb['porta'], timeout=10)
    dados = json.dumps(corpo).encode() if corpo is not None else None
    cab = {'Accept': 'application/json'}
    if dados is not None:
        cab['Content-Type'] = 'application/json'
    cab.update(headers or {})
    with redirect_stdout(io.StringIO()) as saida:
        conexao.request(metodo, caminho, body=dados, headers=cab)
        resposta = conexao.getresponse()
        bruto = resposta.read()
    conexao.close()
    try:
        payload = json.loads(bruto or b'{}')
    except json.JSONDecodeError:
        payload = {'_raw': bruto.decode('utf-8', 'replace')}
    return resposta.status, payload, saida.getvalue()


def _bearer(uid):
    ator = ATORES[uid]
    return {'Authorization': 'Bearer ' + seguranca.create_jwt_token(
        {'id': ator['id'], 'role': ator['role'], 'company_id': ator['company_id']})}


def _cred_empresa_a(amb):
    """Credencial legítima da empresa A para o fluxo de status deste projeto."""
    if SAAS:
        return {'X-Checkout-Token': amb['tokens']['A']}
    return _bearer(11)


def _status(amb, mp_id, tipo='payment', headers=None):
    from urllib.parse import quote
    return _http(amb, 'GET', f'/api/payments/status?payment_id={quote(mp_id, safe="")}&resource_type={tipo}',
                 headers=headers)


def _assinar(data_id, request_id='req-1a', ts='1700000000', segredo=SEGREDO_TESTE):
    manifesto = f'id:{data_id.lower()};request-id:{request_id};ts:{ts};'
    v1 = hmac.new(segredo.encode(), manifesto.encode(), hashlib.sha256).hexdigest()
    return {'x-signature': f'ts={ts},v1={v1}', 'x-request-id': request_id}


def _webhook(amb, data_id, *, tipo='payment', headers=None, corpo=None, query=None):
    q = query if query is not None else f'type={tipo}&data.id={data_id}'
    corpo = corpo if corpo is not None else {'type': tipo, 'data': {'id': data_id}}
    return _http(amb, 'POST', f'/api/payments/webhook?{q}', headers=headers, corpo=corpo)


def _status_local(amb, mp_id):
    row = amb['conn'].execute(
        'SELECT status FROM payments WHERE mp_payment_id = ? ORDER BY id DESC LIMIT 1', (mp_id,)).fetchone()
    return row[0] if row else None


# ── S1: consulta de status ────────────────────────────────────────────────────

def test_s1_consulta_sem_autenticacao_recusada_sem_chamar_mp(ambiente):
    status, payload, _ = _status(ambiente, PAG_A)
    assert status == 401
    assert ambiente['mp'].chamadas == []
    assert 'payment' not in payload


def test_s1_bearer_invalido_recusado(ambiente):
    status, _, _ = _status(ambiente, PAG_A, headers={'Authorization': 'Bearer nao.e.jwt'})
    assert status == 401
    assert ambiente['mp'].chamadas == []


def test_s1_dono_legitimo_consulta_e_sincroniza(ambiente):
    status, payload, _ = _status(ambiente, PAG_A, headers=_cred_empresa_a(ambiente))
    assert status == 200, payload
    assert payload == {'ok': True, 'payment': {
        'payment_id': PAG_A, 'resource_type': 'payment', 'status': 'approved',
        'status_detail': 'accredited', 'persisted': True}}
    assert ambiente['mp'].chamadas == [f'/v1/payments/{PAG_A}']
    assert _status_local(ambiente, PAG_A) == 'approved'


def test_s1_pagamento_de_outro_tenant_vira_404_sem_chamar_mp(ambiente):
    for headers in (_cred_empresa_a(ambiente), _bearer(11)):
        status, payload, _ = _status(ambiente, PAG_B, headers=headers)
        assert status == 404
        assert payload['error']['code'] == 'NOT_FOUND'
    assert ambiente['mp'].chamadas == []
    assert _status_local(ambiente, PAG_B) == 'pending'  # nada escrito no outro tenant


def test_s1_id_desconhecido_e_de_outro_tenant_sao_indistinguiveis(ambiente):
    _, outro, _ = _status(ambiente, PAG_B, headers=_bearer(11))
    _, inexistente, _ = _status(ambiente, DESCONHECIDO, headers=_bearer(11))
    assert outro == inexistente
    assert ambiente['mp'].chamadas == []


def test_s1_ator_sem_empresa_nao_consulta(ambiente):
    status, _, _ = _status(ambiente, PAG_A, headers=_bearer(33))
    assert status == 404
    assert ambiente['mp'].chamadas == []


IDS_MALICIOSOS = [
    '../../users/me', '..%2F..%2Fusers%2Fme', '%2e%2e', '1/../../users/me', '1?access_token=x',
    '1#frag', '1/2', ' 1', '1 ', '1\t', '-1', '+1', '1.0', '1e3', '0x1f', '１２３', '1' * 21,
    'search?status=approved', 'https://evil.example/1', '1;2', '1,2', '1\\2',
]


@pytest.mark.parametrize('mp_id', IDS_MALICIOSOS)
def test_s1_ids_manipulados_rejeitados_antes_do_mp(ambiente, mp_id):
    status, payload, _ = _status(ambiente, mp_id, headers=_cred_empresa_a(ambiente))
    assert status == 400, (mp_id, payload)
    assert ambiente['mp'].chamadas == []


@pytest.mark.parametrize('mp_id', ['a/b', 'a.b', '../x', 'a-b', 'á1', 'x' * 65, 'a b'])
def test_s1_preapproval_ids_manipulados_rejeitados(ambiente, mp_id):
    status, _, _ = _status(ambiente, mp_id, tipo='preapproval', headers=_cred_empresa_a(ambiente))
    assert status == 400
    assert ambiente['mp'].chamadas == []


@pytest.mark.parametrize('tipo', ['merchant_orders', '../users', 'PAYMENT', 'preapproval/../x'])
def test_s1_resource_type_fora_da_lista_rejeitado(ambiente, tipo):
    from urllib.parse import quote
    status, _, _ = _http(ambiente, 'GET', f'/api/payments/status?payment_id={PAG_A}&resource_type={quote(tipo)}',
                         headers=_cred_empresa_a(ambiente))
    assert status == 400
    assert ambiente['mp'].chamadas == []


def test_s1_parametros_repetidos_rejeitados(ambiente):
    status, _, _ = _http(ambiente, 'GET', f'/api/payments/status?payment_id={PAG_A}&payment_id={PAG_B}',
                         headers=_cred_empresa_a(ambiente))
    assert status == 400
    assert ambiente['mp'].chamadas == []


def test_s1_preapproval_do_dono_consulta_caminho_exato(ambiente):
    status, payload, _ = _status(ambiente, PRE_A, tipo='preapproval', headers=_cred_empresa_a(ambiente))
    assert status == 200, payload
    assert ambiente['mp'].chamadas == [f'/preapproval/{PRE_A}']


def test_s1_valores_nao_escalares_do_mp_nao_sao_ecoados(ambiente):
    ambiente['mp'].respostas[f'/v1/payments/{PAG_A}'] = {
        'status': {'interno': 'https://api.interna/x'}, 'status_detail': ['a', 'b']}
    status, payload, _ = _status(ambiente, PAG_A, headers=_cred_empresa_a(ambiente))
    assert status == 200
    assert payload['payment']['status'] == '' and payload['payment']['status_detail'] == ''
    assert 'api.interna' not in json.dumps(payload)


def test_s1_erro_do_mp_na_consulta_usa_mensagem_fixa(ambiente):
    ambiente['mp'].respostas[f'/v1/payments/{PAG_A}'] = MercadoPagoError(
        'Mercado Pago: unauthorized https://api.mercadopago.com/v1/payments?access_token=' + MARCADOR_TOKEN,
        status=401, response={'message': 'invalid access token ' + MARCADOR_TOKEN, 'status': 401})
    status, payload, _ = _status(ambiente, PAG_A, headers=_cred_empresa_a(ambiente))
    # 401 do MP é da credencial do LOJISTA: nunca 401 ao cliente (encerraria a sessão).
    assert status == 503
    assert payload['error']['message'] == routes.MP_PUBLIC_UNAVAILABLE
    assert 'APP_USR' not in json.dumps(payload) and 'mercadopago.com' not in json.dumps(payload)


if SAAS:
    def test_s1_saas_token_de_checkout_de_outra_empresa_vira_404(ambiente):
        status, _, _ = _status(ambiente, PAG_A, headers={'X-Checkout-Token': ambiente['tokens']['B']})
        assert status == 404
        assert ambiente['mp'].chamadas == []

    def test_s1_saas_token_forjado_vira_404(ambiente):
        for token in ('forjado', 'x' * 300, ambiente['tokens']['A'] + 'x'):
            status, _, _ = _status(ambiente, PAG_A, headers={'X-Checkout-Token': token})
            assert status == 404
        assert ambiente['mp'].chamadas == []

    def test_s1_saas_token_consumido_ainda_le_status(ambiente):
        checkout_sessions.claim_checkout_session(ambiente['conn'], ambiente['tokens']['A'])
        ambiente['conn'].commit()
        status, _, _ = _status(ambiente, PAG_A, headers={'X-Checkout-Token': ambiente['tokens']['A']})
        assert status == 200

    def test_s1_saas_token_fora_da_janela_de_status_vira_404(ambiente):
        ambiente['conn'].execute(
            "UPDATE checkout_sessions SET expires_at = '2000-01-01T00:00:00Z' WHERE token_hash = ?",
            (checkout_sessions.hash_token(ambiente['tokens']['A']),))
        ambiente['conn'].commit()
        status, _, _ = _status(ambiente, PAG_A, headers={'X-Checkout-Token': ambiente['tokens']['A']})
        assert status == 404
        assert ambiente['mp'].chamadas == []

    def test_s1_saas_resolver_de_status_nao_consome_o_token(ambiente):
        assert checkout_sessions.resolve_status_company(ambiente['conn'], ambiente['tokens']['A']) == EMPRESA_A
        binding = checkout_sessions.claim_checkout_session(ambiente['conn'], ambiente['tokens']['A'])
        assert binding['company_id'] == EMPRESA_A

    def test_s1_saas_bearer_da_mesma_empresa_tambem_consulta(ambiente):
        status, _, _ = _status(ambiente, PAG_A, headers=_bearer(11))
        assert status == 200


# ── S2: webhook ───────────────────────────────────────────────────────────────

def test_s2_webhook_assinatura_valida_sincroniza(ambiente):
    status, payload, _ = _webhook(ambiente, PAG_A, headers=_assinar(PAG_A))
    assert status == 200 and payload['synced'] is True, payload
    assert _status_local(ambiente, PAG_A) == 'approved'
    assert ambiente['mp'].chamadas == [f'/v1/payments/{PAG_A}']


def test_s2_webhook_sem_assinatura_401(ambiente):
    status, payload, _ = _webhook(ambiente, PAG_A)
    assert status == 401 and payload['error']['code'] == 'INVALID_SIGNATURE'
    assert ambiente['mp'].chamadas == [] and _status_local(ambiente, PAG_A) == 'pending'


@pytest.mark.parametrize('assinatura', [
    'ts=1700000000,v1=' + '0' * 64,                 # hash errado
    'ts=1700000000',                                # sem v1
    'v1=' + 'a' * 64,                               # sem ts
    'ts=abc,v1=' + 'a' * 64,                        # ts não numérico
    'ts=1700000000,v1=zz',                          # v1 malformado
    'ts=1700000000,v1=' + 'é' * 64,                 # não ASCII (compare_digest levantaria)
    'lixo',                                         # sem pares chave=valor
    'ts=1,ts=2,v1=' + 'a' * 64,                     # chave repetida
    'ts=1700000000,v1=' + 'a' * 600,                # longo demais
])
def test_s2_webhook_assinatura_invalida_ou_malformada_401(ambiente, assinatura):
    status, _, _ = _webhook(ambiente, PAG_A, headers={'x-signature': assinatura, 'x-request-id': 'req-1a'})
    assert status == 401
    assert ambiente['mp'].chamadas == [] and _status_local(ambiente, PAG_A) == 'pending'


def test_s2_webhook_assinado_com_outro_segredo_401(ambiente):
    status, _, _ = _webhook(ambiente, PAG_A, headers=_assinar(PAG_A, segredo='outro-segredo'))
    assert status == 401


def test_s2_webhook_assinatura_de_outro_id_nao_vale(ambiente):
    # Assinatura legítima para PAG_A reaproveitada com PAG_B na query.
    status, _, _ = _webhook(ambiente, PAG_B, headers=_assinar(PAG_A))
    assert status == 401
    assert _status_local(ambiente, PAG_B) == 'pending'


def test_s2_webhook_sem_segredo_no_processo_falha_fechado(ambiente, monkeypatch):
    monkeypatch.setattr(service, 'MERCADO_PAGO_WEBHOOK_SECRET', '')
    status, payload, _ = _webhook(ambiente, PAG_A, headers=_assinar(PAG_A))
    assert status == 503 and payload['error']['code'] == 'WEBHOOK_UNAVAILABLE'
    assert ambiente['mp'].chamadas == [] and _status_local(ambiente, PAG_A) == 'pending'


def test_s2_corpo_com_id_diferente_do_assinado_e_ignorado(ambiente):
    # Assinatura válida para PAG_A, mas o corpo (não assinado) aponta PAG_B,
    # pagamento de OUTRO tenant: nada é alterado.
    status, payload, _ = _webhook(ambiente, PAG_A, headers=_assinar(PAG_A),
                                  corpo={'type': 'payment', 'data': {'id': PAG_B}})
    assert status == 200 and payload == {'ok': True, 'ignored': True, 'reason': 'id_mismatch'}
    assert ambiente['mp'].chamadas == []
    assert _status_local(ambiente, PAG_B) == 'pending' and _status_local(ambiente, PAG_A) == 'pending'


def test_s2_webhook_de_recurso_desconhecido_nao_chama_mp(ambiente):
    status, payload, _ = _webhook(ambiente, DESCONHECIDO, headers=_assinar(DESCONHECIDO))
    assert status == 200 and payload['reason'] == 'unknown_resource'
    assert ambiente['mp'].chamadas == []


@pytest.mark.parametrize('mp_id', ['../../users/me', '1?x=1', '1/2'])
def test_s2_webhook_assinado_com_id_malicioso_nao_chama_mp(ambiente, mp_id):
    from urllib.parse import quote
    status, payload, _ = _webhook(ambiente, mp_id, headers=_assinar(mp_id),
                                  query=f'type=payment&data.id={quote(mp_id, safe="")}')
    assert status == 200 and payload['reason'] == 'invalid_id'
    assert ambiente['mp'].chamadas == []


def test_s2_topico_nao_suportado_ignorado(ambiente):
    status, payload, _ = _webhook(ambiente, PAG_A, tipo='merchant_order', headers=_assinar(PAG_A))
    assert status == 200 and payload['reason'] == 'unsupported_topic'
    assert ambiente['mp'].chamadas == []


def test_s2_notificacoes_duplicadas_sao_idempotentes(ambiente):
    for _ in range(3):
        status, payload, _ = _webhook(ambiente, PAG_A, headers=_assinar(PAG_A))
        assert status == 200 and payload['status'] == 'approved'
    linhas = ambiente['conn'].execute('SELECT COUNT(*) FROM payments WHERE mp_payment_id = ?', (PAG_A,)).fetchone()
    assert linhas[0] == 1
    assert _status_local(ambiente, PAG_A) == 'approved'


def test_s2_notificacao_fora_de_ordem_nao_regride_status(ambiente):
    novo = {'status': 'approved', 'status_detail': 'accredited', 'date_last_updated': '2026-11-05T10:00:00.000-03:00'}
    velho = {'status': 'pending', 'status_detail': 'pending_waiting_transfer',
             'date_last_updated': '2026-11-05T09:00:00.000-03:00'}
    ambiente['mp'].respostas[f'/v1/payments/{PAG_A}'] = novo
    _webhook(ambiente, PAG_A, headers=_assinar(PAG_A))
    assert _status_local(ambiente, PAG_A) == 'approved'
    ambiente['mp'].respostas[f'/v1/payments/{PAG_A}'] = velho
    status, payload, _ = _webhook(ambiente, PAG_A, headers=_assinar(PAG_A))
    assert status == 200 and payload['status'] == 'approved'
    assert _status_local(ambiente, PAG_A) == 'approved'


def test_s2_payload_nao_muda_empresa_nem_status_de_outro_tenant(ambiente):
    # Tentativa de alterar o pagamento de B: corpo traz company_id/status
    # forjados; a assinatura é válida só para PAG_A.
    corpo = {'type': 'payment', 'data': {'id': PAG_A}, 'company_id': EMPRESA_B, 'status': 'approved'}
    status, _, _ = _webhook(ambiente, PAG_A, headers=_assinar(PAG_A), corpo=corpo)
    assert status == 200
    row = ambiente['conn'].execute('SELECT company_id FROM payments WHERE mp_payment_id = ?', (PAG_A,)).fetchone()
    assert int(row[0]) == EMPRESA_A
    assert _status_local(ambiente, PAG_B) == 'pending'


def test_s2_preapproval_assinado_sincroniza_assinatura_da_empresa_persistida(ambiente):
    subscriptions_service.record_subscription(
        ambiente['conn'], company_id=EMPRESA_A, plan_key='start', cycle='monthly', payment_method='card',
        preapproval_id=PRE_A, status='pending', amount=297.0, created_by=None, origin='authenticated')
    ambiente['conn'].commit()
    # 'paused' não dispara a ativação de onboarding (fora do escopo deste lote).
    ambiente['mp'].respostas[f'/preapproval/{PRE_A}'] = {'status': 'paused'}
    status, payload, _ = _webhook(ambiente, PRE_A, tipo='preapproval', headers=_assinar(PRE_A),
                                  corpo={'type': 'preapproval', 'data': {'id': PRE_A}, 'company_id': EMPRESA_B})
    assert status == 200 and payload['synced'] is True
    sub = ambiente['conn'].execute('SELECT company_id, mp_status FROM subscriptions WHERE preapproval_id = ?',
                                   (PRE_A,)).fetchone()
    assert int(sub[0]) == EMPRESA_A and sub[1] == 'paused'


# ── S5/S6: texto do Mercado Pago nunca chega ao cliente ───────────────────────

TEXTO_HOSTIL = ('Card Token not found https://api.mercadopago.com/v1/card_tokens/abc?access_token='
                + MARCADOR_TOKEN + ' /opt/render/project/src/modules/payments pagador@exemplo.invalid')


@pytest.mark.parametrize('mp_status,esperado,mensagem', [
    (400, 400, 'MP_PUBLIC_REFUSED'),
    (422, 422, 'MP_PUBLIC_REFUSED'),
    (401, 503, 'MP_PUBLIC_UNAVAILABLE'),
    (403, 503, 'MP_PUBLIC_UNAVAILABLE'),
    (404, 502, 'MP_PUBLIC_UNAVAILABLE'),
    (429, 503, 'MP_PUBLIC_UNAVAILABLE'),
    (500, 502, 'MP_PUBLIC_UNAVAILABLE'),
    (503, 503, 'MP_PUBLIC_UNAVAILABLE'),
    (None, 502, 'MP_PUBLIC_UNAVAILABLE'),
    (True, 502, 'MP_PUBLIC_UNAVAILABLE'),
])
def test_s6_mensagem_publica_fixa_por_classe(monkeypatch, mp_status, esperado, mensagem):
    capturado = {}
    monkeypatch.setattr(routes, 'send_json', lambda h, s, p: capturado.update(status=s, payload=p))
    resposta = {'message': TEXTO_HOSTIL, 'error': TEXTO_HOSTIL, 'status': mp_status,
                'cause': [{'code': 'E301', 'description': TEXTO_HOSTIL}, {'code': TEXTO_HOSTIL},
                          {'description': 'só texto'}, {'code': True}, 'x', {'code': 2006}]}
    with redirect_stdout(io.StringIO()) as log:
        routes._mp_error_response(object(), MercadoPagoError(f'Mercado Pago: {TEXTO_HOSTIL}', status=mp_status,
                                                             response=resposta))
    assert capturado['status'] == esperado
    erro = capturado['payload']['error']
    assert erro['code'] == 'MERCADO_PAGO_ERROR'
    assert erro['message'] == getattr(routes, mensagem)
    serializado = json.dumps(capturado['payload'])
    for vazamento in ('APP_USR', 'mercadopago.com', '/opt/render', 'pagador@', 'Card Token', 'só texto'):
        assert vazamento not in serializado
    assert erro['details']['cause'] == [{'code': 'E301'}, {'code': 2006}]
    # O diagnóstico vai para o log, redigido (sem o token).
    assert 'payments.mercadopago_error' in log.getvalue()
    assert MARCADOR_TOKEN not in log.getvalue()


def test_s5_details_limitados_a_cinco_causas_e_codigos_curtos():
    detalhes = routes._public_mp_details({'cause': [{'code': f'C{i}'} for i in range(20)] + [{'code': 'x' * 41}]})
    assert detalhes == {'cause': [{'code': f'C{i}'} for i in range(5)]}
    assert routes._public_mp_details({'cause': [{'description': 'a'}]}) == {}
    assert routes._public_mp_details('texto') == {}


def test_s6_checkout_com_erro_do_mp_nao_ecoa_texto(ambiente, monkeypatch):
    """Fluxo real de criação (Pix) com o MP devolvendo texto hostil."""
    def falha(path, body, **kwargs):
        raise MercadoPagoError(f'Mercado Pago: {TEXTO_HOSTIL}', status=400,
                               response={'message': TEXTO_HOSTIL, 'cause': [{'code': 4020, 'description': TEXTO_HOSTIL}]})
    monkeypatch.setattr(mp_client, 'post', falha)
    if SAAS:
        corpo = {'checkout_token': ambiente['tokens']['A'], 'plan_key': 'start', 'cycle': 'monthly',
                 'payer_email': 'pagador@exemplo.invalid'}
        headers = {}
    else:
        corpo = {'plan_key': 'start', 'cycle': 'monthly', 'payer_email': 'pagador@exemplo.invalid',
                 'idempotency_key': 'corp-' + uuid.uuid4().hex}
        headers = _bearer(11)
    status, payload, _ = _http(ambiente, 'POST', '/api/payments/pix', headers=headers, corpo=corpo)
    if status == 400 and payload.get('error', {}).get('code') != 'MERCADO_PAGO_ERROR':
        pytest.fail(f'checkout não chegou ao Mercado Pago: {payload}')
    assert status == 400
    assert payload['error']['message'] == routes.MP_PUBLIC_REFUSED
    assert 'APP_USR' not in json.dumps(payload) and 'mercadopago.com' not in json.dumps(payload)


# ── Fluxo legítimo de ponta a ponta ───────────────────────────────────────────

def test_fluxo_legitimo_checkout_status_e_confirmacao(ambiente, monkeypatch):
    """Cria Pix → consulta status (pendente) → webhook assinado → aprovado."""
    novo_id = str(_BASE + 5)
    if ambiente['db'] == 'pg':
        ambiente['conn'].execute('DELETE FROM payments WHERE mp_payment_id = ?', (novo_id,))
        ambiente['conn'].commit()
    monkeypatch.setattr(mp_client, 'post', lambda path, body, **k: {
        'id': novo_id, 'status': 'pending', 'status_detail': 'pending_waiting_transfer', 'currency_id': 'BRL',
        'point_of_interaction': {'transaction_data': {'qr_code': 'QR', 'qr_code_base64': 'B'}}})
    if SAAS:
        corpo = {'checkout_token': ambiente['tokens']['A'], 'plan_key': 'start', 'cycle': 'monthly',
                 'payer_email': 'pagador@exemplo.invalid'}
        headers = {}
    else:
        corpo = {'plan_key': 'start', 'cycle': 'monthly', 'payer_email': 'pagador@exemplo.invalid',
                 'idempotency_key': 'corp-' + uuid.uuid4().hex}
        headers = _bearer(11)
    try:
        status, payload, _ = _http(ambiente, 'POST', '/api/payments/pix', headers=headers, corpo=corpo)
        assert status == 201, payload
        assert payload['payment']['payment_id'] == novo_id

        ambiente['mp'].respostas[f'/v1/payments/{novo_id}'] = {'status': 'pending', 'status_detail': 'pending_waiting_transfer'}
        status, payload, _ = _status(ambiente, novo_id, headers=_cred_empresa_a(ambiente))
        assert status == 200 and payload['payment']['status'] == 'pending'

        ambiente['mp'].respostas[f'/v1/payments/{novo_id}'] = {'status': 'approved', 'status_detail': 'accredited'}
        status, payload, _ = _webhook(ambiente, novo_id, headers=_assinar(novo_id))
        assert status == 200 and payload['synced'] is True

        status, payload, _ = _status(ambiente, novo_id, headers=_cred_empresa_a(ambiente))
        assert status == 200 and payload['payment']['status'] == 'approved'
        # A outra empresa continua sem enxergar.
        status, _, _ = _status(ambiente, novo_id, headers=_bearer(22))
        assert status == 404
    finally:
        if ambiente['db'] == 'pg':
            ambiente['conn'].rollback()
            ambiente['conn'].execute('DELETE FROM payments WHERE mp_payment_id = ?', (novo_id,))
            ambiente['conn'].commit()


# ── Frontend: o polling de status envia a credencial certa ────────────────────

def test_frontend_polling_envia_credencial_e_nao_usa_url():
    js = (ROOT / 'static' / 'js' / 'pagamento.js').read_text(encoding='utf-8')
    assert 'getStatusJson(`${API.status}?payment_id=' in js
    corpo = js.split('async function getStatusJson(url) {', 1)[1].split('\n}\n', 1)[0]
    if SAAS:
        assert "'X-Checkout-Token': ctx.checkoutToken" in corpo
    else:
        assert 'Authorization: `Bearer ${token}`' in corpo
    assert 'checkout_token=' not in js.split('function startStatusPolling', 1)[1].split('\n}\n', 1)[0]


# ── I18N: as frases públicas fixas têm tradução nos 5 idiomas ─────────────────

LOCALES = ['pt-BR', 'en-GB', 'es-ES', 'fr-FR', 'nb-NO']


@pytest.mark.parametrize('nome', ['MP_PUBLIC_REFUSED', 'MP_PUBLIC_UNAVAILABLE', 'PAYMENT_NOT_FOUND_MESSAGE',
                                  'WEBHOOK_UNAVAILABLE_MESSAGE'])
def test_i18n_mensagens_publicas_fixas_nos_5_idiomas(nome):
    texto = getattr(routes, nome)
    chave = 'm_' + hashlib.sha256(texto.encode('utf-8')).hexdigest()[:12]
    for loc in LOCALES:
        catalogo = json.loads((ROOT / 'static' / 'i18n' / f'{loc}.json').read_text(encoding='utf-8'))
        valor = catalogo['apiErrors']['messages'].get(chave)
        assert valor, (loc, nome)
        if loc == 'pt-BR':
            assert valor == texto
        else:
            assert valor != texto, (loc, nome)


# ── S7: paridade Corporate × SaaS dos blocos de segurança do Mercado Pago ─────
#
# Os trechos abaixo precisam ser byte a byte iguais nos dois repositórios. O
# digest é calculado por ESTE teste sobre o código de cada repositório; se um
# lado mudar sem o outro, o teste reprova no lado alterado.

BLOCOS_PAREADOS_MP = (
    ('modules/payments/routes.py', '# Mensagens PÚBLICAS fixas', '# ── GET ──'),
    ('modules/payments/routes.py', 'def handle_post_webhook', '# ── Registro'),
    ('modules/payments/service.py', '# ── Identificadores do Mercado Pago', None),
    ('modules/payments/mp_client.py', None, None),
)
PREFIXO_DO_DIGESTO_MP = 'DIGESTO_PARIDADE_MP_1A = '
DIGESTO_PARIDADE_MP_1A = '1eb57e99c5714d5f3529fac08b02e9c8c9e9461e2006f4e55242ce874c496d17'


def _digesto_mp():
    h = hashlib.sha256()
    for rel, inicio, fim in BLOCOS_PAREADOS_MP:
        texto = (ROOT / rel).read_text(encoding='utf-8')
        a = texto.index(inicio) if inicio else 0
        b = texto.index(fim, a) if fim else len(texto)
        h.update(rel.encode() + b'\0' + texto[a:b].encode('utf-8') + b'\0')
    return h.hexdigest()


def test_s7_paridade_dos_blocos_de_seguranca_mp():
    obtido = _digesto_mp()
    assert obtido == DIGESTO_PARIDADE_MP_1A, (
        'Bloco de segurança do Mercado Pago mudou. Aplique a MESMA mudança no '
        'outro repositório (Corporate/SaaS) e atualize o digest nos dois.\n'
        f'  esperado: {DIGESTO_PARIDADE_MP_1A}\n  obtido:   {obtido}')
