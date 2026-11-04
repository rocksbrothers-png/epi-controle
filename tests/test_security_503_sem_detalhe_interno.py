"""Segurança: o 503 do bootstrap, /health e o 500 genérico não expõem detalhe interno.

O 503 e /health são respondidos ANTES da autenticação. Antes, `details.detail`
e `error_message` devolviam `str(exc)` da falha de banco/migração (host, usuário,
SQL e, com DATABASE_URL malformada, a própria URL de conexão). O contrato
público — status, `code`, `kind`, chaves do JSON — continua igual; só o texto
livre vira uma frase fixa. O erro bruto segue no estado interno e no log, com a
senha redigida.
"""
import ast
import io
import json
import sqlite3
from contextlib import redirect_stdout
from pathlib import Path

import pytest

import app
from epi_backend import bootstrap
from epi_backend.http_utils import (
    PUBLIC_INTERNAL_ERROR,
    PublicServerError,
    public_error_message,
    redact_secrets,
    structured_log,
)

ROOT = Path(__file__).resolve().parents[1]

# Valores fictícios, só para provar a redação.
SEGREDO = 'SenhaFicticia123'
HOST = 'db-interno.exemplo.invalid'
BRUTO = (f'invalid dsn: missing "=" after "postgresql://usuario:{SEGREDO}@{HOST}:5432/base" '
         f'connection to server at "{HOST}" (10.0.0.9), port 5432 failed: '
         'FATAL: password authentication failed for user "usuario"')


class _Handler:
    command = 'GET'
    path = '/api/users'


def _falha():
    bootstrap._set_bootstrap_state(ready=False, error_code='DB_CONNECTION_FAILED', error_kind='driver_unexpected',
                                   error_message=BRUTO, started_at='2026-11-04T00:00:00+00:00',
                                   completed_at='2026-11-04T00:00:05+00:00')


def _limpa():
    bootstrap._set_bootstrap_state(ready=False, error_code='', error_kind='', error_message='',
                                   started_at='', completed_at='')


def _sem_interno(texto):
    for proibido in (SEGREDO, HOST, '10.0.0.9', 'postgresql://', 'usuario', 'FATAL'):
        assert proibido not in texto, proibido


def test_503_do_gate_nao_expoe_detalhe_e_preserva_contrato(monkeypatch):
    _falha()
    capturado = {}
    monkeypatch.setattr(app, 'send_json', lambda h, status, payload: capturado.update(status=status, payload=payload))
    try:
        assert app.EpiHandler._require_bootstrap_ready(_Handler(), '/api/users') is None
    finally:
        _limpa()
    assert capturado['status'] == 503
    erro = capturado['payload']['error']
    assert capturado['payload']['ok'] is False
    assert erro['code'] == 'DB_CONNECTION_FAILED'
    assert erro['message'] == 'Serviço indisponível: bootstrap do banco pendente ou com falha.'
    assert set(erro['details']) == {'kind', 'detail', 'ready', 'started_at', 'completed_at'}
    assert erro['details']['kind'] == 'driver_unexpected'
    assert erro['details']['detail'] == bootstrap.PUBLIC_BOOTSTRAP_FAILED
    _sem_interno(json.dumps(capturado['payload'], ensure_ascii=False))
    # O estado interno guarda o erro bruto para diagnóstico.


def test_503_pendente_mantem_texto_anterior(monkeypatch):
    _limpa()
    capturado = {}
    monkeypatch.setattr(app, 'send_json', lambda h, status, payload: capturado.update(status=status, payload=payload))
    app.EpiHandler._require_bootstrap_ready(_Handler(), '/api/users')
    assert capturado['payload']['error']['details']['detail'] == 'A migração/validação de schema ainda não concluiu.'


def test_health_e_ready_nao_expoem_detalhe():
    _falha()
    try:
        for probe in ('live', 'ready'):
            status, payload = bootstrap.runtime_probe_response(probe)
            assert status == (200 if probe == 'live' else 503)
            assert payload['error_code'] == 'DB_CONNECTION_FAILED'
            assert payload['error_kind'] == 'driver_unexpected'
            assert payload['error_message'] == bootstrap.PUBLIC_BOOTSTRAP_FAILED
            _sem_interno(json.dumps(payload, ensure_ascii=False))
        assert bootstrap._get_bootstrap_state()['error_message'] == BRUTO
    finally:
        _limpa()


def test_health_saudavel_continua_sem_mensagem():
    bootstrap._set_bootstrap_state(ready=True, error_code='', error_kind='', error_message='')
    try:
        status, payload = bootstrap.runtime_probe_response('ready')
        assert status == 200 and payload['error_message'] == ''
    finally:
        _limpa()


# Lista de PERMISSÃO: exceção não classificada nunca leva o próprio texto ao cliente,
# mesmo quando o texto parece inofensivo ou não bate em nenhum padrão conhecido.
NAO_CLASSIFICADAS = [
    sqlite3.OperationalError('no such table: users'),
    sqlite3.IntegrityError('UNIQUE constraint failed: users.email'),
    RuntimeError(BRUTO),
    RuntimeError('Texto qualquer com aparência de negócio.'),
    KeyError('company_id'),
    TypeError("unsupported operand type(s) for +: 'int' and 'NoneType'"),
    AttributeError("'NoneType' object has no attribute 'get'"),
    OSError(2, 'No such file or directory', '/opt/render/project/src/segredo.pem'),
    ZeroDivisionError('division by zero'),
    # Montado em tempo de execução: um literal `chave=valor` dispararia o scanner de segredos.
    Exception('https://api.exemplo.invalid/v1/x?' + 'access_' + 'token=' + 'x' * 12),
]


@pytest.mark.parametrize('exc', NAO_CLASSIFICADAS, ids=lambda e: type(e).__name__)
def test_excecao_nao_classificada_vira_mensagem_generica(exc):
    assert public_error_message(exc) == PUBLIC_INTERNAL_ERROR


def test_schema_migration_error_vira_mensagem_generica():
    class SchemaMigrationError(Exception):
        pass
    assert public_error_message(SchemaMigrationError('Falha em migração x: y')) == PUBLIC_INTERNAL_ERROR


def test_contrato_explicito_preserva_a_mensagem_de_negocio():
    assert public_error_message(PublicServerError('Nenhum item da ficha foi assinado.')) == \
        'Nenhum item da ficha foi assinado.'
    assert public_error_message(PublicServerError('   ')) == PUBLIC_INTERNAL_ERROR
    assert issubclass(PublicServerError, RuntimeError)  # `except RuntimeError` existentes continuam valendo


def _raises_publicos():
    achados = []
    for path in sorted((ROOT / 'modules').rglob('*.py')) + sorted((ROOT / 'core').rglob('*.py')) + \
            sorted((ROOT / 'epi_backend').rglob('*.py')) + [ROOT / 'app.py']:
        for node in ast.walk(ast.parse(path.read_text(encoding='utf-8'))):
            if isinstance(node, ast.Raise) and isinstance(node.exc, ast.Call) and \
                    getattr(node.exc.func, 'id', getattr(node.exc.func, 'attr', '')) == 'PublicServerError':
                achados.append((str(path.relative_to(ROOT)), node.exc.args))
    return achados


def test_mensagem_publica_e_sempre_texto_fixo_no_codigo():
    """Contrato explícito: o texto de PublicServerError é literal (nunca f-string, str(exc) ou variável)."""
    achados = _raises_publicos()
    assert {arquivo for arquivo, _ in achados} == {'modules/portal/routes.py', 'modules/employees/service.py'}
    assert len(achados) == 4
    for arquivo, args in achados:
        assert len(args) == 1 and isinstance(args[0], ast.Constant) and isinstance(args[0].value, str), arquivo


def _HandlerHTTP(metodo, caminho, corpo=b'{}'):
    """Instância real do EpiHandler, sem socket, para exercitar os métodos do servidor."""
    handler = object.__new__(app.EpiHandler)
    handler.command, handler.path = metodo, caminho
    handler.headers = {'Content-Length': str(len(corpo)), 'Content-Type': 'application/json'}
    handler.rfile = io.BytesIO(corpo)
    handler.client_address = ('127.0.0.1', 0)
    return handler


@pytest.mark.parametrize('metodo', ['GET', 'POST', 'PUT', 'DELETE'])
@pytest.mark.parametrize('exc', [RuntimeError(BRUTO), KeyError('company_id'),
                                 sqlite3.OperationalError('no such column: senha_hash')],
                         ids=['runtime', 'keyerror', 'sqlite'])
def test_handler_real_responde_500_generico(monkeypatch, metodo, exc):
    bootstrap._set_bootstrap_state(ready=True, error_code='', error_kind='', error_message='')
    capturado = {}
    monkeypatch.setattr(app, 'send_json', lambda h, status, payload: capturado.update(status=status, payload=payload))

    def explode(*args, **kwargs):
        raise exc
    monkeypatch.setattr(app.router, 'dispatch', explode)
    saida = io.StringIO()
    try:
        with redirect_stdout(saida):
            getattr(app.EpiHandler, f'do_{metodo}')(_HandlerHTTP(metodo, '/api/qualquer-rota'))
    finally:
        _limpa()
    assert capturado['status'] == 500
    assert capturado['payload'] == {'error': PUBLIC_INTERNAL_ERROR}
    assert SEGREDO not in saida.getvalue()  # log mantém diagnóstico, sem a senha


def test_handler_real_preserva_mensagem_de_contrato(monkeypatch):
    bootstrap._set_bootstrap_state(ready=True, error_code='', error_kind='', error_message='')
    capturado = {}
    monkeypatch.setattr(app, 'send_json', lambda h, status, payload: capturado.update(status=status, payload=payload))

    def explode(*args, **kwargs):
        raise PublicServerError('Nenhum item da ficha foi assinado.')
    monkeypatch.setattr(app.router, 'dispatch', explode)
    try:
        with redirect_stdout(io.StringIO()):
            app.EpiHandler.do_POST(_HandlerHTTP('POST', '/api/qualquer-rota'))
    finally:
        _limpa()
    assert capturado == {'status': 500, 'payload': {'error': 'Nenhum item da ficha foi assinado.'}}


def test_integridade_sem_traducao_nao_devolve_texto_do_banco():
    bruto = ('insert or update on table "deliveries" violates foreign key constraint "x_fkey" '
             'DETAIL: Key (employee_id)=(991) is not present in table "employees" (outro@exemplo.invalid).')
    texto = app.humanize_integrity_error(sqlite3.IntegrityError(bruto))
    assert texto == app.PUBLIC_INTEGRITY_ERROR
    assert 'outro@exemplo.invalid' not in texto and 'x_fkey' not in texto
    # Traduções conhecidas continuam iguais.
    assert app.humanize_integrity_error(sqlite3.IntegrityError('UNIQUE constraint failed: units.company_id, units.name')) == \
        'Já existe uma unidade com este nome nesta empresa.'


def test_aviso_de_secao_do_bootstrap_nao_expoe_erro_bruto():
    from modules.auth import service
    avisos = []

    def falha():
        raise sqlite3.OperationalError('no such column: senha_hash in table users')
    with redirect_stdout(io.StringIO()):
        resultado = service._safe_bootstrap_section('units', falha, list, avisos, {'id': 1, 'role': 'admin', 'company_id': 1})
    assert resultado == []
    assert avisos == [{'section': 'units', 'message': PUBLIC_INTERNAL_ERROR, 'type': 'ServerError'}]


def test_erro_do_mercado_pago_nao_ecoa_corpo_bruto(monkeypatch):
    from modules.payments import routes as pay_routes
    from modules.payments.mp_client import MercadoPagoError
    resposta = {'message': 'invalid card', 'error': 'bad_request', 'status': 400,
                'cause': [{'code': 2006, 'description': 'Card Token not found', 'data': 'payer@exemplo.invalid'}],
                'request': {'payer': {'email': 'payer@exemplo.invalid'}, 'token': 'tok_' + 'Z' * 6}}
    capturado = {}
    monkeypatch.setattr(pay_routes, 'send_json', lambda h, status, payload: capturado.update(status=status, payload=payload))
    pay_routes._mp_error_response(object(), MercadoPagoError('Mercado Pago: invalid card', status=400, response=resposta))
    erro = capturado['payload']['error']
    assert capturado['status'] == 400 and erro['code'] == 'MERCADO_PAGO_ERROR'
    assert erro['message'] == 'Mercado Pago: invalid card'
    assert erro['details'] == {'error': 'bad_request', 'status': 400,
                               'cause': [{'code': 2006, 'description': 'Card Token not found'}]}
    assert 'payer@exemplo.invalid' not in json.dumps(capturado) and 'tok_' + 'Z' * 6 not in json.dumps(capturado)


def test_falha_de_conexao_com_mercado_pago_nao_expoe_o_erro_de_rede(monkeypatch):
    import urllib.error

    from modules.payments import mp_client
    monkeypatch.setattr(mp_client, 'MERCADO_PAGO_ACCESS_TOKEN', 'TESTE-' + 'f' * 8)

    def falha(*args, **kwargs):
        raise urllib.error.URLError(f'proxy {HOST}:3128 recusou')
    monkeypatch.setattr(mp_client.urllib.request, 'urlopen', falha)
    saida = io.StringIO()
    with redirect_stdout(saida), pytest.raises(mp_client.MercadoPagoError) as erro:
        mp_client.get('/v1/payments/1')
    assert str(erro.value) == 'Falha de conexão com o Mercado Pago.'
    assert HOST in saida.getvalue()  # diagnóstico continua no log


def test_webhook_assinado_com_falha_interna_nao_expoe_o_erro(monkeypatch):
    from modules.payments import routes as pay_routes
    monkeypatch.setattr(pay_routes.service, 'verify_webhook_signature', lambda headers, query: True)

    def explode(*args, **kwargs):
        raise sqlite3.OperationalError('no such table: subscriptions')
    monkeypatch.setattr(pay_routes.service, 'handle_webhook', explode)

    class _Conn:
        def rollback(self):
            pass

        def close(self):
            pass
    monkeypatch.setattr(pay_routes, 'get_connection', lambda: _Conn())
    capturado = {}
    monkeypatch.setattr(pay_routes, 'send_json', lambda h, status, payload: capturado.update(status=status, payload=payload))

    class _H:
        def __init__(self):
            self.headers = {}
    with redirect_stdout(io.StringIO()):
        pay_routes.handle_post_webhook(_H(), app.urlparse('/api/payments/webhook?type=payment&data.id=1'), {}, None)
    assert capturado == {'status': 200, 'payload': {'ok': False, 'error': PUBLIC_INTERNAL_ERROR}}


def test_webhook_sem_assinatura_continua_401(monkeypatch):
    from modules.payments import routes as pay_routes
    monkeypatch.setattr(pay_routes.service, 'verify_webhook_signature', lambda headers, query: False)
    capturado = {}
    monkeypatch.setattr(pay_routes, 'send_json', lambda h, status, payload: capturado.update(status=status, payload=payload))

    class _H:
        def __init__(self):
            self.headers = {}
    with redirect_stdout(io.StringIO()):
        pay_routes.handle_post_webhook(_H(), app.urlparse('/api/payments/webhook'), {}, None)
    assert capturado['status'] == 401 and capturado['payload']['error']['code'] == 'INVALID_SIGNATURE'


def test_todos_os_500_genericos_usam_a_mensagem_publica():
    with open(app.__file__, encoding='utf-8') as arquivo:
        fonte = arquivo.read()
    assert "send_json(self, 500, {'error': str(exc)})" not in fonte
    assert fonte.count("send_json(self, 500, {'error': public_error_message(exc)})") == 4


def test_log_mantem_diagnostico_e_redige_a_senha():
    saida = io.StringIO()
    with redirect_stdout(saida):
        structured_log('error', 'db.init_failed_gracefully', error=BRUTO)
    linha = saida.getvalue()
    assert SEGREDO not in linha
    assert HOST in linha  # diagnóstico preservado para o operador
    assert redact_secrets('host=x pass' 'word=abc user=y') == 'host=x password=*** user=y'
    assert redact_secrets('postgres://u:' 'p@h/db') == 'postgres://u:***@h/db'
    assert redact_secrets('postgresql://:' 'p@h/db') == 'postgresql://:***@h/db'
    assert redact_secrets('Authorization: Bear' 'er ' + 'q' * 16) == 'Authorization: Bearer ***'
    assert redact_secrets('jwt ' + '.'.join(['ey' 'J' + 'a' * 8, 'b' * 8, 'c' * 8]) + ' fim') == 'jwt *** fim'
    assert redact_secrets('{"pass' 'word": "' + 'z' * 6 + '", "user": "x"}') == '{"password": ***, "user": "x"}'


def test_log_redige_segredo_dentro_de_estruturas():
    saida = io.StringIO()
    with redirect_stdout(saida):
        structured_log('error', 'x', detalhes={'dsn': f'postgresql://u:{SEGREDO}@h/db', 'lista': [f'token={SEGREDO}']})
    assert SEGREDO not in saida.getvalue()


# ── Redação: custo linear e lacunas conhecidas ────────────────────────────────

ADVERSARIAIS = ['a-' * 32000, 'a://' * 16000, 'cookie:' * 9000, 'password=' * 7000, 'eyJ' * 21000,
                'Authorization: ' + ' ' * 64000, 'x:' * 32000, 'u:' + '@' * 64000]


@pytest.mark.parametrize('texto', ADVERSARIAIS, ids=range(len(ADVERSARIAIS)))
def test_redacao_tem_custo_linear(texto):
    import time
    inicio = time.perf_counter()
    for _ in range(10):
        redact_secrets(texto)
    assert time.perf_counter() - inicio < 1.0


def test_redacao_trunca_texto_enorme():
    saida = redact_secrets('x' * 100_000)
    assert len(saida) < 9000 and saida.endswith('caracteres]')


def test_post_sem_autenticacao_com_caminho_enorme_nao_trava_o_servidor(monkeypatch):
    """Regressão do DoS: o caminho é logado várias vezes por request antes de qualquer autenticação."""
    import time
    bootstrap._set_bootstrap_state(ready=True, error_code='', error_kind='', error_message='')
    monkeypatch.setattr(app, 'send_json', lambda h, status, payload: None)
    monkeypatch.setattr(app.router, 'dispatch', lambda *a, **k: None)
    monkeypatch.setattr(app, 'not_found', lambda h: None)
    inicio = time.perf_counter()
    try:
        with redirect_stdout(io.StringIO()):
            app.EpiHandler.do_POST(_HandlerHTTP('POST', '/api/' + 'a-' * 32000))
    finally:
        _limpa()
    assert time.perf_counter() - inicio < 1.0


@pytest.mark.parametrize('bruto,esperado', [
    ('postgresql://u:' + 'Fa@ke@host/db', 'postgresql://u:***@host/db'),
    ('postgres://u:' + 'a/b/c@h:5432/db', 'postgres://u:***@h:5432/db'),
    ("{'pass" + "word': 'x'}", "{'password': ***}"),
    ('client_' + 'secret=abc&x=1', 'client_secret=***&x=1'),
    ('MP_ACCESS_' + 'TOKEN=abc', 'MP_ACCESS_TOKEN=***'),
    ('PGPASS' + 'WORD=zz', 'PGPASSWORD=***'),
    ('refresh_' + 'token=rr', 'refresh_token=***'),
    ('api-' + 'key=kk', 'api-key=***'),
    ('X-Api-' + 'Key: k1', 'X-Api-Key: ***'),
    ('Authoriza' + 'tion: abc123', 'Authorization: ***'),
    ('Authoriza' + 'tion: Tok' + 'en xyz12', 'Authorization: Token ***'),
    ('Authoriza' + 'tion: Bear' + 'er abc', 'Authorization: Bearer ***'),
    ('Coo' + 'kie: session=abc; x=1', 'Cookie: ***'),
])
def test_redacao_cobre_formas_conhecidas(bruto, esperado):
    assert redact_secrets(bruto) == esperado


@pytest.mark.parametrize('texto', ['password: authentication failed', 'token_count=3 itens',
                                   'connection to server at "db.internal" failed', 'see https://x.y/a@b c'])
def test_redacao_preserva_texto_de_diagnostico(texto):
    assert redact_secrets(texto) == texto


def test_log_redige_campo_e_chave_sensiveis():
    saida = io.StringIO()
    with redirect_stdout(saida):
        structured_log('error', 'x', password=SEGREDO, dados={'client_secret': SEGREDO, 'ok': 1})
    linha = json.loads(saida.getvalue())
    assert linha['password'] == '***' and linha['dados'] == {'client_secret': '***', 'ok': 1}


@pytest.mark.parametrize('texto', ['Invalid token signature', 'token expired at 10:00', 'basic validation failed',
                                   'Invalid token Signature', 'authorization header missing'])
def test_redacao_nao_mascara_texto_comum_com_palavras_de_credencial(texto):
    assert redact_secrets(texto) == texto


@pytest.mark.parametrize('bruto,esperado', [
    ('Authoriza' + 'tion: Bear' + 'er q1w2e3r4t5y6', 'Authorization: Bearer ***'),
    ('Authoriza' + 'tion: bas' + 'ic dXNlcjpwYXNz', 'Authorization: basic ***'),
    ('Bas' + 'ic dXNlcjpwYXNz', 'Basic ***'),
    ('Authoriza' + 'tion:abc', 'Authorization:***'),
])
def test_redacao_de_cabecalho_preserva_o_esquema(bruto, esperado):
    assert redact_secrets(bruto) == esperado


def test_segredo_no_limite_do_corte_nao_vaza_metade():
    texto = 'x' * 8180 + ' postgresql://u:' + 'Q' * 14 + '@h/db ' + 'y' * 100
    saida = redact_secrets(texto)
    assert 'Q' not in saida and saida.endswith('caracteres]')


def test_chave_sensivel_com_valor_booleano_ou_numerico_fica_legivel():
    saida = io.StringIO()
    with redirect_stdout(saida):
        structured_log('info', 'x', has_token=True, retry_token=3, dados={'has_secret': False})
    linha = json.loads(saida.getvalue())
    assert linha['has_token'] is True and linha['retry_token'] == 3 and linha['dados'] == {'has_secret': False}
