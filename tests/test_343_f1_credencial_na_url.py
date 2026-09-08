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

import io
import json
import pathlib
import re

import pytest

import app as aplicacao
from epi_backend.http_utils import (
    SENSITIVE_QUERY_PARAMS,
    redact_sensitive_query,
    send_json,
    structured_log,
)

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


# ── 5. A porta de saída: o redator, mecanismo único ──────────────────────────

def test_o_redator_redige_o_valor_dos_parametros_sensiveis():
    linha = ('"GET /?username=alguem&password=' + MARCADOR + ' HTTP/1.1" 200 -')
    saida = redact_sensitive_query(linha)
    assert MARCADOR not in saida, 'o valor sensível saiu inteiro no log'
    assert 'password=***' in saida
    assert 'username=***' in saida


@pytest.mark.parametrize('nome', ['username', 'password', 'token', 'employee_token'])
def test_o_redator_cobre_cada_nome_comprovado(nome):
    """Um teste por nome, para a falha dizer QUAL parâmetro vazou."""
    saida = redact_sensitive_query(f'"GET /api/x?{nome}={MARCADOR} HTTP/1.1" 200 -')
    assert MARCADOR not in saida, f'o valor de `{nome}` saiu inteiro no log'
    assert f'{nome}=***' in saida


def test_a_lista_de_sensiveis_e_a_comprovada_pela_auditoria():
    """Fixa a lista para que ampliá-la seja ato deliberado, com evidência.

    `username` e `password` são o achado original da F1 — os dois nomes que
    `preloadLoginFromUrl` aceitava. `token` é uso ATUAL: `modules/portal/routes.py`
    lê `?token=`. `employee_token` é o nome que `modules/portal/service.py` GERA
    no link do portal e que `static/app.js` LÊ no carregamento — toda visita
    normal ao portal leva uma credencial de capacidade na query. Nomes como
    `new_password` ou `totp_code` viajam no corpo do POST e não na query:
    redigi-los seria código morto fingindo proteção.

    `cpf_last3` ENTROU na F4 da #343, e entrou pelo caminho certo: a auditoria
    provou que ele é o SEGUNDO FATOR do portal — posse do link mais
    conhecimento dos 3 dígitos — e que `handle_get_employee_access` e
    `..._pdf` o leem de `?cpf_last3=`. A F1 o havia classificado como
    parâmetro de negócio, o que era razoável com a evidência daquela época e
    deixou de ser com esta. Ampliar a lista continua exigindo evidência; o que
    mudou foi a evidência, não o critério.
    """
    assert SENSITIVE_QUERY_PARAMS == frozenset(
        {'username', 'password', 'token', 'employee_token', 'cpf_last3'})


@pytest.mark.parametrize('codificado,decodificado', [
    ('to%6ben', 'token'),
    ('pass%77ord', 'password'),
    ('employee%5Ftoken', 'employee_token'),
    ('user%6Eame', 'username'),
])
def test_o_redator_entende_nome_percent_encoded(codificado, decodificado):
    """`parse_qs` decodifica o NOME, e é por ele que as rotas leem a query.

    `to%6ben=…` CHEGA na rota como `token`: comparar o nome cru deixaria a
    credencial passar por um caractere de diferença.
    """
    from urllib.parse import parse_qs
    assert decodificado in parse_qs(f'{codificado}=x'), \
        'premissa do teste: o servidor precisa mesmo aceitar este nome'
    saida = redact_sensitive_query(f'/api/x?{codificado}={MARCADOR}')
    assert MARCADOR not in saida, f'`{codificado}` contornou o redator'
    assert f'{codificado}=***' in saida, 'o nome deve ficar como veio; só o valor some'


def test_o_redator_nao_decodifica_alem_do_que_o_servidor_aceita():
    """Uma passada de decode, não um laço — nem mais, nem menos que `parse_qs`.

    `%2570assword` NÃO é aceito como `password` pelo servidor, então redigi-lo
    seria o redator inventando uma ameaça que o código não tem.
    """
    from urllib.parse import parse_qs
    assert 'password' not in parse_qs('%2570assword=x')
    saida = redact_sensitive_query(f'/api/x?%2570assword={MARCADOR}')
    assert saida == f'/api/x?%2570assword={MARCADOR}'


@pytest.mark.parametrize('nome', ['username', 'PASSWORD', 'Token', 'EMPLOYEE_TOKEN'])
def test_o_redator_ignora_caixa_do_nome(nome):
    saida = redact_sensitive_query(f'/api/x?{nome}={MARCADOR}')
    assert MARCADOR not in saida


@pytest.mark.parametrize('nome', ['code', 'qr_code', 'actor_user_id', 'user_id',
                                  'unit_id', 'company_id', 'epi_id'])
def test_os_parametros_de_negocio_nao_sao_redigidos(nome):
    """Contraprova: redigir tudo destrói a investigação de incidente, que é
    exatamente para o que o log serve.

    `cpf_last3` SAIU desta lista na F4 da #343: ele não era parâmetro de
    negócio, era fator de validação. Ver o gate da lista de sensíveis."""
    linha = f'"GET /api/x?{nome}=123 HTTP/1.1" 200 -'
    assert redact_sensitive_query(linha) == linha


def test_a_redacao_preserva_observabilidade_legitima():
    """Método, rota, status e parâmetros de negócio sobrevivem inteiros."""
    assert redact_sensitive_query(
        '"GET /api/stock/epis?actor_user_id=5&unit_id=3 HTTP/1.1" 200 -'
    ) == '"GET /api/stock/epis?actor_user_id=5&unit_id=3 HTTP/1.1" 200 -'


def test_a_redacao_preserva_o_vizinho_de_negocio_do_parametro_sensivel():
    """Redigir o sensível não pode levar junto o identificador ao lado.

    O vizinho aqui é `actor_user_id`, que `resolve_actor_user_id` LÊ da query
    (`epi_backend/security.py`) — é observabilidade legítima e precisa
    sobreviver. Na F1 este teste usava `cpf_last3` como vizinho; a F4 o moveu
    para o lado dos sensíveis, e o teste passou a usar um vizinho que continua
    sendo de negócio de verdade."""
    saida = redact_sensitive_query(
        f'/api/employee-access?employee_token={MARCADOR}&actor_user_id=42')
    assert saida == '/api/employee-access?employee_token=***&actor_user_id=42'


def test_o_redator_aceita_path_cru_e_linha_de_log():
    """Os sinks passam path cru; o access log passa a linha inteira. Um só
    mecanismo atende as duas formas — é isso que evita implementações
    divergentes."""
    assert redact_sensitive_query('/x?token=' + MARCADOR) == '/x?token=***'
    assert redact_sensitive_query('"GET /x?token=' + MARCADOR + ' HTTP/1.1" 200 -') \
        == '"GET /x?token=*** HTTP/1.1" 200 -'
    assert redact_sensitive_query('/x/sem/query') == '/x/sem/query'


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


# ── 8. Os sinks estruturados ─────────────────────────────────────────────────
#
# O access log da stdlib não é o único lugar onde o path aparece. Quatro sinks
# estruturados registram o path CRU — com query, portanto com credencial. Este
# bloco prova que todos passam pelo mesmo redator, e o gate de inventário é
# escrito para pegar um sink NOVO que nasça sem ele.

SINKS_ESPERADOS = {
    'http.response': 'epi_backend/http_utils.py',
    'bootstrap.gate.check': 'app.py',
    'http.post.entry': 'app.py',
    'auth.login.entry': 'modules/auth/routes.py',
}


def _blocos_structured_log(caminho):
    """Devolve (evento, bloco) de cada chamada a `structured_log` do arquivo."""
    texto = caminho.read_text(encoding='utf-8')
    for m in re.finditer(r'structured_log\s*\(', texto):
        i, prof = m.end(), 1
        while i < len(texto) and prof:
            if texto[i] == '(':
                prof += 1
            elif texto[i] == ')':
                prof -= 1
            i += 1
        bloco = texto[m.start():i]
        evento = re.search(r"['\"]([a-z0-9_.]+)['\"]", bloco[bloco.find(',') + 1:])
        yield (evento.group(1) if evento else '?'), bloco


def _fontes_do_servidor():
    for caminho in sorted(RAIZ.rglob('*.py')):
        rel = caminho.relative_to(RAIZ).as_posix()
        if rel.startswith(('tests/', 'scripts/', 'flutter/')) or '__pycache__' in rel:
            continue
        yield caminho


def test_todo_sink_que_registra_path_cru_passa_pelo_redator():
    """Gate de INVENTÁRIO: vale para os sinks de hoje e para os de amanhã.

    Fixar os quatro nomes num assert protegeria só os quatro. Varrer a árvore
    atrás de quem registra `self.path`/`handler.path` faz um sink novo nascer
    reprovado até chamar o redator — que é o ponto de ter mecanismo único.
    """
    cru = re.compile(r"=\s*(?:self|handler)\.path\b"
                     r"|=\s*getattr\(\s*(?:self|handler)\s*,\s*['\"]path['\"]")
    desprotegidos = []
    for caminho in _fontes_do_servidor():
        for evento, bloco in _blocos_structured_log(caminho):
            if cru.search(bloco) and 'redact_sensitive_query' not in bloco:
                rel = caminho.relative_to(RAIZ).as_posix()
                desprotegidos.append(f'{rel}: {evento}')
    assert not desprotegidos, (
        'sink registrando path cru sem passar pelo redator: '
        + ', '.join(desprotegidos))


def test_os_quatro_sinks_conhecidos_continuam_cobertos():
    """Contraprova do inventário: se um sink SUMIR, o gate acima ficaria verde
    por vacuidade. Este exige que os quatro continuem existindo e protegidos."""
    encontrados = {}
    for caminho in _fontes_do_servidor():
        rel = caminho.relative_to(RAIZ).as_posix()
        for evento, bloco in _blocos_structured_log(caminho):
            if evento in SINKS_ESPERADOS:
                encontrados[evento] = (rel, 'redact_sensitive_query' in bloco)
    for evento, arquivo in SINKS_ESPERADOS.items():
        assert evento in encontrados, f'o sink `{evento}` desapareceu de {arquivo}'
        rel, protegido = encontrados[evento]
        assert rel == arquivo, f'`{evento}` mudou de arquivo: {rel}'
        assert protegido, f'o sink `{evento}` voltou a registrar path cru'


def test_o_sink_http_response_nao_imprime_credencial(capsys):
    """Prova COMPORTAMENTAL: executa o sink e lê o que foi para o stdout."""
    class _Handler:
        path = f'/api/employee-access?employee_token={MARCADOR}&cpf_last3=123'
        command = 'GET'

        def send_response(self, *a):
            pass

        def send_header(self, *a):
            pass

        def end_headers(self):
            pass

        wfile = io.BytesIO()

    send_json(_Handler(), 200, {'ok': True})
    saida = capsys.readouterr().out
    assert MARCADOR not in saida, 'o token saiu inteiro no log estruturado'
    registro = json.loads(saida.strip().splitlines()[-1])
    # Os DOIS fatores do portal somem da mesma linha: a posse (o token) e o
    # conhecimento (os 3 dígitos). Antes da F4 o segundo sobrevivia aqui.
    assert registro['path'] == '/api/employee-access?employee_token=***&cpf_last3=***'
    assert registro['method'] == 'GET', 'a observabilidade legítima sumiu junto'
    assert registro['status'] == 200


def test_nenhum_valor_sintetico_sensivel_aparece_em_log_algum(capsys):
    """Varredura final: nenhum dos quatro nomes deixa o valor escapar por
    nenhuma das duas formas (path cru e linha de request)."""
    for nome in sorted(SENSITIVE_QUERY_PARAMS):
        for forma in (f'/api/x?{nome}={MARCADOR}',
                      f'"GET /api/x?{nome}={MARCADOR} HTTP/1.1" 200 -'):
            structured_log('info', 'gate.343.f1', raw_path=redact_sensitive_query(forma))
    saida = capsys.readouterr().out
    assert MARCADOR not in saida, 'valor sensível sintético apareceu no log'
    assert saida.count('=***') == 2 * len(SENSITIVE_QUERY_PARAMS)


# ── 9. Mecanismo único, não implementações divergentes ───────────────────────

def test_existe_uma_unica_definicao_do_redator_e_da_lista():
    """Duas cópias divergem no dia em que só uma é atualizada.

    Este gate é o que transforma "usamos um helper só" de intenção em
    invariante verificável.
    """
    definicoes_lista = []
    definicoes_funcao = []
    for caminho in _fontes_do_servidor():
        texto = caminho.read_text(encoding='utf-8')
        rel = caminho.relative_to(RAIZ).as_posix()
        definicoes_lista += [rel] * len(
            re.findall(r'^\s*SENSITIVE_QUERY_PARAMS\s*=', texto, re.M))
        definicoes_funcao += [rel] * len(
            re.findall(r'^\s*def redact_sensitive_query\b', texto, re.M))
    assert definicoes_lista == ['epi_backend/http_utils.py'], \
        f'a lista de sensíveis foi duplicada: {definicoes_lista}'
    assert definicoes_funcao == ['epi_backend/http_utils.py'], \
        f'o redator foi duplicado: {definicoes_funcao}'
