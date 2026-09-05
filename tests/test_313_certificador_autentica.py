"""Gates 8-14 da #313 — o certificador autentica sozinho, e falha fechado.

O gate 7 (GET-only tipado) vive em `tests/test_271_preflight.py`, junto do
invariante que ele protege: "o certificador não escreve em produção". Aqui
ficam as fixtures que provam que aquele matcher REPROVA cada mutação — sem
elas, uma regra estática que não casa nada é indistinguível de uma regra
quebrada — e os gates do fluxo novo.

O que estes gates existem para impedir:

1. `login() or EPI_CERT_*_TOKEN`. Um fallback silencioso devolveria verde com a
   credencial que esta frente elimina, e a falha do caminho novo ficaria
   invisível até o JWT expirar;
2. autenticar sem conferir QUEM autenticou. Um `registry_admin` passa o smoke
   inteiro carregando 26 permissões de escrita;
3. o preflight voltar a mandar credencial, reacoplando readiness a identidade;
4. o token escapar do processo.
"""

import ast
import pathlib

import pytest

RAIZ = pathlib.Path(__file__).resolve().parent.parent
SCRIPT = RAIZ / 'scripts' / 'certificar_deployment.py'

from tests.certificador_matchers import escritas_indevidas


class _Espaco:
    """Fachada de atributos sobre o dicionário de globais do módulo exec'd.

    `SimpleNamespace(**espaco)` NÃO serve: as funções resolvem `_get` no
    dicionário de globais em que foram compiladas, então injetar num namespace
    à parte deixaria a rede REAL ligada — o gate sairia da máquina, tentaria
    resolver `exemplo` e travaria. Escrever aqui escreve onde elas leem.
    """

    def __init__(self, espaco):
        object.__setattr__(self, '_espaco', espaco)

    def __getattr__(self, nome):
        try:
            return object.__getattribute__(self, '_espaco')[nome]
        except KeyError as erro:
            raise AttributeError(nome) from erro

    def __setattr__(self, nome, valor):
        object.__getattribute__(self, '_espaco')[nome] = valor


def _modulo():
    """Carrega o script SEMPRE da fonte, sem passar por `__pycache__`.

    `spec_from_file_location` + `exec_module` reaproveita o bytecode em cache,
    que é indexado por mtime e TAMANHO. Uma sabotagem que troque `TIMEOUT = 20`
    por `TIMEOUT = 90` não muda nem um nem outro: o `.pyc` da versão sabotada
    sobrevive à restauração do arquivo, e o gate seguinte lê 90 de um arquivo
    que diz 20. Isso já produziu um falso VERMELHO aqui — e produziria um falso
    VERDE se a ordem fosse a inversa, que é o defeito grave.
    """
    espaco = {'__name__': 'certificar_deployment_313', '__file__': str(SCRIPT)}
    exec(compile(SCRIPT.read_text(encoding='utf-8'), str(SCRIPT), 'exec'), espaco)  # noqa: S102
    return _Espaco(espaco)


def _fonte() -> str:
    return SCRIPT.read_text(encoding='utf-8')


class _Rede:
    """Registra toda requisição e devolve respostas roteirizadas.

    Substitui `_get` e `_login` no módulo carregado. O que interessa medir não
    é o valor devolvido e sim QUAIS requisições saíram, em que ordem, e com
    qual credencial — é assim que "fail-closed" e "preflight sem JWT" viram
    afirmações verificáveis em vez de promessas do docstring.
    """

    def __init__(self, respostas, login=('tok-novo', '')):
        self.respostas = list(respostas)
        self.login = login
        self.gets = []
        self.logins = []

    def get(self, url, token, origin='', timeout=None):
        self.gets.append((url, token, origin))
        return self.respostas.pop(0) if self.respostas else (200, {}, {})

    def entrar(self, raiz, usuario, senha):
        self.logins.append((raiz, usuario, senha))
        return self.login


def _instrumentar(m, rede):
    m._get = rede.get
    m._login = rede.entrar
    return m


# ── Gate 8: não-vacuidade do matcher GET-only ────────────────────────────────

@pytest.mark.parametrize('nome,velho,novo,esperado', [
    ('segundo POST',
     "    req = urllib.request.Request(raiz + ROTA_LOGIN, data=corpo, method='POST')",
     ("    req = urllib.request.Request(raiz + ROTA_LOGIN, data=corpo, method='POST')\n"
      "    urllib.request.Request(raiz + '/api/x', data=corpo, method='POST')"),
     'POST'),
    ('método PUT',
     "req = urllib.request.Request(url, method='GET')",
     "req = urllib.request.Request(url, method='PUT')",
     "'PUT'"),
    ('login apontado para outro endpoint',
     "ROTA_LOGIN = '/api/login'",
     "ROTA_LOGIN = '/api/auth/login'",
     'ROTA_LOGIN não é /api/login'),
    ('GET funcional ganha corpo de escrita',
     "        with urllib.request.urlopen(req, timeout=timeout) as resp:",
     ("        req.data = b''\n"
      "        with urllib.request.urlopen(req, timeout=timeout, data=b'') as resp:"),
     '`data=` fora do login'),
])
def test_o_matcher_reprova_cada_mutacao(nome, velho, novo, esperado):
    fonte = _fonte()
    assert velho in fonte, f'MUTACAO NAO APLICOU: âncora ausente ({nome})'
    motivo = escritas_indevidas(fonte.replace(velho, novo, 1))
    assert motivo, f'{nome}: o matcher aprovou uma escrita indevida'
    assert esperado in motivo, f'{nome}: reprovou pelo motivo errado — {motivo}'


def test_o_matcher_aprova_o_script_integro():
    """Contraprova: reprovar tudo não é reprovar o que importa."""
    assert escritas_indevidas(_fonte()) == ''


# ── Gate 9: preflight sem credencial ─────────────────────────────────────────

def test_o_preflight_nao_manda_authorization():
    m = _instrumentar(_modulo(), rede := _Rede([(200, {}, {})]))
    m._preflight('https://exemplo')
    assert rede.gets, 'o preflight não sondou'
    assert all(token == '' for _, token, _ in rede.gets), \
        'o preflight enviou credencial: readiness voltou a depender de identidade'


def test_certificar_api_chama_o_preflight_sem_token():
    """Estático, porque o parâmetro `token` continua existindo por compatibilidade
    com os 25 gates da #271: o que precisa ser provado é o PONTO DE CHAMADA."""
    arvore = ast.parse(_fonte())
    chamadas = [no for no in ast.walk(arvore)
                if isinstance(no, ast.Call)
                and isinstance(no.func, ast.Name) and no.func.id == '_preflight']
    assert chamadas, 'nenhuma chamada a `_preflight` — matcher quebrado'
    for chamada in chamadas:
        assert len(chamada.args) == 1 and not chamada.keywords, \
            'o preflight de produção recebeu credencial'


# ── Gate 10: constantes preservadas ──────────────────────────────────────────

def test_as_constantes_do_preflight_e_do_smoke_nao_mudaram():
    m = _modulo()
    assert m.PREFLIGHT_DEADLINE == 180
    assert m.PREFLIGHT_INTERVALO == 5
    assert m.PREFLIGHT_TIMEOUT == 60
    assert m.TIMEOUT == 20, 'lentidão de endpoint é defeito; subir isto a esconde'


# ── Gate 12: modos exclusivos ────────────────────────────────────────────────

def test_os_modos_sao_exclusivos():
    m = _modulo()
    assert m._modo('tok', '', '') == m.MODO_LEGADO
    assert m._modo('', 'u', 'p') == m.MODO_NOVO
    assert m._modo('', '', '') == m.MODO_AUSENTE
    # O caso que importa: token presente NÃO tem precedência nem preferência.
    assert m._modo('tok-antigo', 'u', 'p') == m.MODO_NOVO


def test_o_token_estatico_nao_e_usado_quando_ha_credenciais():
    m = _instrumentar(_modulo(), rede := _Rede(
        [(401, {}, {}),                    # preflight: pronta, auth recusada
         (200, {'units': [{'id': 9}], 'permissions': []}, {}),  # /api/auth/me
         (200, {'units': [{'id': 9}]}, {}),
         (200, {'items': [{}]}, {})]))
    rede.login = ('tok-NOVO', '')
    m._validar_identidade = lambda raiz, token: ''
    m.certificar_api('x', 'https://exemplo', 'tok-ANTIGO', usuario='u', senha='p')
    usados = {token for _, token, _ in rede.gets if token}
    assert 'tok-ANTIGO' not in usados, 'o JWT estático foi usado apesar das credenciais'
    assert usados == {'tok-NOVO'}


# ── Gate 11: fail-closed ─────────────────────────────────────────────────────

def test_login_recusado_nao_emite_requisicao_funcional():
    """Fail-closed com o token antigo PRESENTE — que é o caso perigoso.

    Contar requisições não basta: uma implementação que caísse no token antigo
    emitiria a mesma quantidade de GETs de um caminho legítimo. O que distingue
    é a credencial usada e o veredito registrado.
    """
    m = _instrumentar(_modulo(), rede := _Rede([(401, {}, {})]))
    rede.login = ('', 'HTTP 401 INVALID_PASSWORD')
    r = m.certificar_api('x', 'https://exemplo', 'tok-ANTIGO', usuario='u', senha='p')
    assert not r.certificado
    assert 'tok-ANTIGO' not in {token for _, token, _ in rede.gets}, \
        'o JWT estático foi usado após login recusado — fallback silencioso'
    funcionais = [url for url, _, _ in rede.gets[1:]]
    assert not funcionais, \
        f'houve requisição depois de login recusado: {funcionais}'
    autenticacao = [(nome, passou) for nome, passou, _ in r.checagens
                    if nome == 'autenticação']
    assert autenticacao == [('autenticação', False)], \
        f'o veredito de autenticação não reprovou: {autenticacao}'


def test_sem_credencial_nenhuma_o_ambiente_sai_nao_executado():
    """Ausência de execução nunca é aprovação."""
    m = _instrumentar(_modulo(), rede := _Rede([]))
    r = m.certificar_api('x', 'https://exemplo', '', usuario='', senha='')
    assert r.pulado and not r.certificado
    assert not rede.gets, 'sondou sem credencial configurada'


# ── Gate 13: identidade ──────────────────────────────────────────────────────

@pytest.mark.parametrize('nome,corpo,trecho', [
    ('papel errado',
     {'user': {'role': 'registry_admin', 'company_id': 1},
      'permissions': ['units:view', 'stock:view']}, 'registry_admin'),
    ('permissão a mais',
     {'user': {'role': 'certification_readonly', 'company_id': 1},
      'permissions': ['units:view', 'stock:view', 'stock:adjust']}, 'sobrando'),
    ('permissão a menos',
     {'user': {'role': 'certification_readonly', 'company_id': 1},
      'permissions': ['units:view']}, 'faltando'),
    ('sem empresa',
     {'user': {'role': 'certification_readonly', 'company_id': None},
      'permissions': ['units:view', 'stock:view']}, 'sem empresa'),
])
def test_identidade_divergente_reprova(nome, corpo, trecho):
    m = _instrumentar(_modulo(), _Rede([(200, {'data': corpo}, {})]))
    motivo = m._validar_identidade('https://exemplo', 'tok')
    assert motivo, f'{nome}: identidade divergente foi aceita'
    assert trecho in motivo, f'{nome}: reprovou pelo motivo errado — {motivo}'


def test_identidade_correta_e_aceita():
    corpo = {'data': {'user': {'role': 'certification_readonly', 'company_id': 4},
                      'permissions': ['stock:view', 'units:view']}}
    m = _instrumentar(_modulo(), _Rede([(200, corpo, {})]))
    assert m._validar_identidade('https://exemplo', 'tok') == ''


def test_identidade_divergente_impede_o_smoke():
    """Duas afirmações distintas, porque contar GETs não separa os casos.

    A identidade precisa ter sido CONSULTADA — remover a chamada faria o
    contador bater igual, com o smoke rodando às cegas — e o estoque não pode
    ter sido tocado depois de ela divergir.
    """
    m = _instrumentar(_modulo(), rede := _Rede(
        [(401, {}, {}),
         (200, {'data': {'user': {'role': 'registry_admin', 'company_id': 1},
                         'permissions': ['units:view', 'stock:view']}}, {})]))
    r = m.certificar_api('x', 'https://exemplo', '', usuario='u', senha='p')
    urls = [url for url, _, _ in rede.gets]
    assert not r.certificado
    assert any(m.ROTA_IDENTIDADE in url for url in urls), \
        'a identidade não foi consultada: o smoke rodaria sem saber quem é o ator'
    assert not any(m.SONDAS[1][0] in url for url in urls), \
        'o smoke funcional rodou com identidade divergente'
    assert any(nome == 'identidade' and not passou for nome, passou, _ in r.checagens)


# ── Gate 14: o token não escapa do processo ──────────────────────────────────

def _constantes_de_codigo(arvore):
    """Strings do CÓDIGO, sem docstrings.

    Necessário porque o docstring de `_login` cita `$GITHUB_ENV` justamente
    para dizer que o token não vai para lá. Um matcher por substring reprovaria
    a documentação da regra que ele existe para impor.
    """
    docs = set()
    for no in ast.walk(arvore):
        if isinstance(no, (ast.Module, ast.FunctionDef, ast.ClassDef)):
            corpo = getattr(no, 'body', [])
            if corpo and isinstance(corpo[0], ast.Expr) and \
                    isinstance(corpo[0].value, ast.Constant) and \
                    isinstance(corpo[0].value.value, str):
                docs.add(id(corpo[0].value))
    return [no.value for no in ast.walk(arvore)
            if isinstance(no, ast.Constant) and isinstance(no.value, str)
            and id(no) not in docs]


def test_o_token_nunca_sai_do_processo():
    """Varredura sintática: nada de log, arquivo, env, GITHUB_* ou subprocesso.

    A proteção principal é esta — o token não é impresso —, não o mascaramento.
    Exigir `::add-mask::` obrigaria a emitir o token no stdout do runner para
    depois cobri-lo: criar a exposição para então tapá-la.
    """
    arvore = ast.parse(_fonte())
    suspeitos = {'token', 'senha', 'password', 'usuario'}

    vistos = set()
    for no in ast.walk(arvore):
        if not isinstance(no, ast.Call):
            continue
        alvo = getattr(no.func, 'id', '') or getattr(no.func, 'attr', '')
        vistos.add(alvo)
        if alvo in ('print', 'write', 'writelines'):
            nomes = {n.id for n in ast.walk(no) if isinstance(n, ast.Name)}
            assert not (nomes & suspeitos), \
                f'`{alvo}` recebeu {sorted(nomes & suspeitos)} — credencial vazando'
        assert alvo not in ('open', 'Popen', 'run', 'check_output', 'system'), \
            f'`{alvo}` no certificador: superfície de vazamento ou persistência'

    assert 'print' in vistos, 'nenhum `print` encontrado — matcher quebrado'

    # Escrita em variável de ambiente: `os.environ[...] = ...`
    for no in ast.walk(arvore):
        if isinstance(no, ast.Assign):
            for alvo_ in no.targets:
                assert not isinstance(alvo_, ast.Subscript), \
                    'atribuição por índice no certificador — possível os.environ[...]'

    proibidas = {'GITHUB_ENV', 'GITHUB_OUTPUT', '::add-mask::'}
    literais = set(_constantes_de_codigo(arvore))
    assert literais, 'nenhuma string de código — matcher quebrado'
    assert not (literais & proibidas), \
        f'literal proibido no código: {sorted(literais & proibidas)}'


def test_o_matcher_de_vazamento_nao_e_vacuo():
    """Contraprova do gate 14: ele precisa REPROVAR um vazamento real."""
    fonte = _fonte().replace(
        "    token = str(dados.get('token') or '')",
        "    token = str(dados.get('token') or '')\n    print(token)", 1)
    arvore = ast.parse(fonte)
    achou = False
    for no in ast.walk(arvore):
        if (isinstance(no, ast.Call) and getattr(no.func, 'id', '') == 'print'
                and {n.id for n in ast.walk(no) if isinstance(n, ast.Name)} & {'token'}):
            achou = True
    assert achou, 'o matcher não veria um `print(token)` — regra inútil'
