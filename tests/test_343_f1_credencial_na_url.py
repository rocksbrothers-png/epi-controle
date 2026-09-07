"""#343 F1 — credencial nunca entra pela URL, e não sai inteira no access log.

## O achado

`static/app.js` tinha `preloadLoginFromUrl()`: lia `?username=` e `?password=`
da query string e PRÉ-PREENCHIA os campos de login, chamando em seguida um
sanitizador que apagava os parâmetros da barra de endereço.

O sanitizador dava uma falsa sensação de segurança. Quando ele roda, a senha já
viajou: está na linha de request que o servidor recebeu, na entrada de
histórico do navegador, no cabeçalho `Referer` de qualquer recurso externo e no
access log — porque o `log_message` padrão do `BaseHTTPRequestHandler` imprime a
linha de request inteira. `history.replaceState` não desfaz nada disso.

## O contrato

    credencial nunca entra pela URL
    parâmetro sensível não é reproduzido INTEIRO no access log

São duas portas, e esta fatia fecha as duas: o cliente não lê mais credencial de
`location.search`, e o servidor redige o VALOR dos parâmetros sensíveis antes de
logar — preservando método, caminho, status e os parâmetros não sensíveis, que
são observabilidade legítima.

`sanitizeLoginUrlParams` ficou de propósito, com outro papel: quem chegar por um
link ou favorito antigo ainda traz os parâmetros, e removê-los reduz a exposição
que já começou. Ela não preenche nada — e o gate 4 é o que garante isso.

Nenhum teste deste arquivo usa credencial real: os valores são marcadores.
"""

import pathlib
import re

import pytest

import app as aplicacao

RAIZ = pathlib.Path(__file__).resolve().parent.parent
APP_JS = RAIZ / 'static' / 'app.js'
LOGIN_HTML = RAIZ / 'static' / 'views' / '_login.html'
SECURITY = RAIZ / 'core' / 'security.py'

MARCADOR = 'VALOR-DE-TESTE-NAO-E-CREDENCIAL'


def _sem_comentarios(texto):
    """Os comentários explicam a regra removida citando o nome dela."""
    fora = []
    for linha in texto.splitlines():
        limpa = linha.lstrip()
        if limpa.startswith('//') or limpa.startswith('*') or limpa.startswith('/*'):
            continue
        fora.append(linha)
    return '\n'.join(fora)


@pytest.fixture(scope='module')
def js():
    return _sem_comentarios(APP_JS.read_text(encoding='utf-8'))


# ── 1, 2 e 3. A porta de entrada está fechada ────────────────────────────────

def test_o_login_nao_le_username_da_query_string(js):
    for padrao in (r"params\.get\(\s*'username'", r'searchParams\.get\(\s*.username'):
        assert not re.search(padrao, js), 'voltou a ler `username` da URL'


def test_o_login_nao_le_password_da_query_string(js):
    for padrao in (r"params\.get\(\s*'password'", r'searchParams\.get\(\s*.password'):
        assert not re.search(padrao, js), 'voltou a ler `password` da URL'


def test_preload_login_from_url_nao_existe_nem_e_chamada(js):
    assert 'function preloadLoginFromUrl' not in js
    assert 'preloadLoginFromUrl(' not in js
    assert 'preloadLoginFromUrl)' not in js


# ── 4. Nenhuma alternativa equivalente ───────────────────────────────────────

CAMPOS_DE_CREDENCIAL = ('loginUsername', 'loginPassword')


def test_nenhum_campo_de_credencial_recebe_valor_de_fonte_externa(js):
    """Atribuir a `refs.loginPassword.value` é o gesto que reintroduz o furo,
    venha o valor de `location.search`, de `hash`, de storage ou de cookie."""
    for campo in CAMPOS_DE_CREDENCIAL:
        achados = re.findall(rf'refs\.{campo}\s*\.\s*value\s*=', js)
        assert achados == [], f'{campo} voltou a ser preenchido por código: {achados}'


def test_nenhuma_leitura_de_credencial_de_location(js):
    """Cobre as formas equivalentes: `location.search`, `hash` e `URLSearchParams`
    combinados com nome de credencial na mesma expressão."""
    for linha in js.splitlines():
        tem_fonte = ('location.search' in linha or 'location.hash' in linha
                     or 'URLSearchParams' in linha)
        tem_credencial = re.search(r"['\"](username|password|senha|token)['\"]", linha)
        assert not (tem_fonte and tem_credencial), f'leitura equivalente: {linha.strip()}'


def test_o_sanitizador_continua_existindo_e_e_incondicional(js):
    """Ele não é resíduo do furo: é a limpeza de quem chega por link antigo."""
    assert 'function sanitizeLoginUrlParams' in js
    assert "runNonCriticalSetup('sanitize login URL', sanitizeLoginUrlParams)" in js
    trecho = js[js.index('function sanitizeLoginUrlParams'):]
    trecho = trecho[:trecho.index('\nfunction ', 1)]
    assert 'searchParams.delete' in trecho
    assert '.value' not in trecho, 'o sanitizador não pode preencher campo nenhum'


# ── 5. A porta de saída: o access log ────────────────────────────────────────

def test_o_access_log_redige_o_valor_dos_parametros_sensiveis():
    linha = ('"GET /?username=alguem&password=' + MARCADOR + ' HTTP/1.1" 200 -')
    saida = aplicacao.EpiHandler._redact_request_line(linha)
    assert MARCADOR not in saida, 'o valor sensível saiu inteiro no log'
    assert 'password=***' in saida
    assert 'username=***' in saida


@pytest.mark.parametrize('nome', ['username', 'password', 'token'])
def test_o_access_log_redige_cada_nome_comprovado(nome):
    """Um teste por nome, para a falha dizer QUAL parâmetro vazou."""
    saida = aplicacao.EpiHandler._redact_request_line(
        f'"GET /api/x?{nome}={MARCADOR} HTTP/1.1" 200 -')
    assert MARCADOR not in saida, f'o valor de `{nome}` saiu inteiro no log'
    assert f'{nome}=***' in saida


def test_a_lista_de_sensiveis_e_a_comprovada_pela_auditoria():
    """Fixa a lista para que ampliá-la seja ato deliberado, com evidência.

    `username` e `password` são o achado da F1 — os dois nomes que
    `preloadLoginFromUrl` aceitava e que `sanitizeLoginUrlParams` remove.
    `token` é uso ATUAL: `modules/portal/routes.py` lê `?token=`, e um link de
    capacidade na URL é credencial. Nomes como `new_password` ou `totp_code`
    viajam no corpo do POST e não na query: redigi-los seria código morto.
    """
    assert aplicacao.EpiHandler.SENSITIVE_QUERY_PARAMS == frozenset(
        {'username', 'password', 'token'})


@pytest.mark.parametrize('nome', ['code', 'qr_code', 'actor_user_id', 'user_id',
                                  'unit_id', 'company_id', 'epi_id'])
def test_os_parametros_de_negocio_nao_sao_redigidos(nome):
    """Contraprova: redigir tudo destrói a investigação de incidente, que é
    exatamente para o que o log serve."""
    linha = f'"GET /api/x?{nome}=123 HTTP/1.1" 200 -'
    assert aplicacao.EpiHandler._redact_request_line(linha) == linha


def test_a_redacao_preserva_observabilidade_legitima():
    """Redigir tudo seria tão ruim quanto não redigir nada: sem método, rota e
    parâmetros de negócio não se investiga incidente nenhum."""
    saida = aplicacao.EpiHandler._redact_request_line(
        '"GET /api/stock/epis?actor_user_id=5&unit_id=3 HTTP/1.1" 200 -')
    assert saida == '"GET /api/stock/epis?actor_user_id=5&unit_id=3 HTTP/1.1" 200 -'


def test_o_handler_sobrescreve_o_log_padrao():
    """Sem a sobrescrita, o `BaseHTTPRequestHandler` imprime a request inteira."""
    assert 'log_message' in aplicacao.EpiHandler.__dict__, \
        'o override sumiu: o log volta a imprimir a linha de request completa'


# ── 6. O login normal continua de pé ─────────────────────────────────────────

def test_o_formulario_de_login_continua_completo(js):
    html = LOGIN_HTML.read_text(encoding='utf-8')
    assert 'id="login-username"' in html
    assert 'id="login-password"' in html
    assert 'autocomplete="current-password"' in html, \
        'o autofill do navegador é comportamento esperado e não deve ser desligado aqui'
    assert "refs.loginUsername?.value" in js, 'o login parou de LER o campo'
    assert "refs.loginPassword?.value" in js


# ── 7. O contrato da #337 não foi tocado ─────────────────────────────────────

def test_o_contrato_401_403_permanece_intacto():
    corpo = _sem_comentarios(SECURITY.read_text(encoding='utf-8'))
    assert corpo.count('raise AuthenticationError') == 9
    assert corpo.count('raise PermissionError') == 1
    app_py = (RAIZ / 'app.py').read_text(encoding='utf-8')
    assert app_py.count('except AuthenticationError') == 4
    assert 'def unauthorized(handler, message):' in app_py
