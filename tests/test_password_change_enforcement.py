"""Bloqueio server-side enquanto a senha temporária não for trocada (#909, PR 2).

O porte da política (PR 1) deixou o comportamento equivalente entre os
repositórios — **incluindo um furo**: com `must_change_password = 1` o login
SUCEDE e devolve JWT válido, e a obrigatoriedade era imposta apenas pelo
redirect do router Flutter e pelo web. Quem chamasse a API direto — curl,
cliente modificado, deep link que não passasse pelo redirect — usava o sistema
inteiro com a senha provisionada pelo admin.

Estes testes cobrem o fechamento desse furo. O ponto central é
`require_actor()`: `authorize_action` e `authorize_action_any` passam os dois
por ele, então uma checagem cobre as 242 chamadas dos 21 módulos.

O risco do desenho é o inverso do furo — trancar o próprio caminho de saída.
Por isso a rota de troca de senha tem teste próprio, e a exceção de
`/api/auth/me` também: um bloqueio que impede o usuário de sair do estado
bloqueado é pior que o furo, porque não tem contorno.
"""

import pathlib
import re

import pytest

import core.repository as repo
import core.security as seguranca

PasswordChangeRequiredError = seguranca.PasswordChangeRequiredError

RAIZ = pathlib.Path(__file__).resolve().parent.parent


# ── Fakes ────────────────────────────────────────────────────────────────────

class _Conn:
    """Conexão mínima: um usuário e o estado da política."""

    def __init__(self, must_change=False, expires='', sem_colunas=False):
        self.must_change = must_change
        self.expires = expires
        self.sem_colunas = sem_colunas

    def execute(self, sql, params=()):
        low = sql.lower().strip()
        if low.startswith('select must_change_password'):
            if self.sem_colunas:
                raise Exception('column "must_change_password" does not exist')
            return _Cur([{
                'must_change_password': 1 if self.must_change else 0,
                'password_expires_at': self.expires,
            }])
        raise AssertionError(f'SQL inesperado: {sql}')

    def rollback(self):
        pass


class _Cur:
    def __init__(self, rows):
        self._rows = rows

    def fetchone(self):
        return self._rows[0] if self._rows else None


_ATOR = {'id': 42, 'active': 1, 'role': 'admin', 'company_id': 7}


@pytest.fixture
def sem_efeitos(monkeypatch):
    """Isola `require_actor` do banco: o alvo aqui é a política, não o resto."""
    monkeypatch.setattr(repo, 'get_user_by_id', lambda conn, uid: dict(_ATOR, id=uid))
    monkeypatch.setattr(repo, 'enforce_company_block_rules', lambda conn, cid: None)


# ── O bloqueio ───────────────────────────────────────────────────────────────

def test_bloqueia_operacao_autenticada_com_senha_temporaria(sem_efeitos):
    with pytest.raises(PasswordChangeRequiredError):
        repo.require_actor(_Conn(must_change=True), 42)


def test_usuario_sem_a_flag_nao_sofre_nada(sem_efeitos):
    # Não-regressão: a esmagadora maioria dos usuários não tem senha
    # temporária, e para eles nada pode mudar.
    ator = repo.require_actor(_Conn(must_change=False), 42)
    assert ator['id'] == 42


def test_base_sem_as_colunas_nao_bloqueia(sem_efeitos):
    # Fail-open deliberado: uma migration não aplicada não pode derrubar o
    # sistema inteiro. O risco aceito é ficar sem a proteção nessa janela — e
    # não travar todo mundo.
    ator = repo.require_actor(_Conn(sem_colunas=True), 42)
    assert ator['id'] == 42


def test_a_excecao_explicita_libera(sem_efeitos):
    ator = repo.require_actor(
        _Conn(must_change=True), 42, allow_password_change_pending=True,
    )
    assert ator['id'] == 42


def test_a_excecao_e_keyword_only():
    # Posicional seria fácil de passar por engano ao acrescentar um argumento
    # novo, e a exceção liberaria o bloqueio sem ninguém perceber.
    #
    # A asserção é sobre a ASSINATURA, não sobre uma chamada malformada: além
    # de dizer exatamente o que se quer garantir, evita escrever no teste uma
    # chamada que a análise estática (com razão) reporta como errada.
    import inspect
    parametro = inspect.signature(repo.require_actor).parameters
    assert 'allow_password_change_pending' in parametro
    assert parametro['allow_password_change_pending'].kind is inspect.Parameter.KEYWORD_ONLY
    assert parametro['allow_password_change_pending'].default is False, \
        'o padrão precisa ser bloquear; um default True inverteria a proteção'


def test_o_bloqueio_vem_depois_das_checagens_existentes(sem_efeitos):
    # Usuário inativo continua sendo "usuário inválido", não
    # "troque sua senha": trocar a ordem daria ao inativo uma mensagem que
    # sugere um caminho que não existe para ele.
    monkey = _Conn(must_change=True)
    original = repo.get_user_by_id
    repo.get_user_by_id = lambda conn, uid: dict(_ATOR, active=0)
    try:
        with pytest.raises(PermissionError) as exc:
            repo.require_actor(monkey, 42)
        assert not isinstance(exc.value, PasswordChangeRequiredError)
    finally:
        repo.get_user_by_id = original


# ── O contrato do erro ───────────────────────────────────────────────────────

def test_e_403_e_nao_401():
    # A propriedade que importa: 403, nunca 401. Um 401 dispararia o refresh
    # automático do cliente num laço que jamais resolveria — o refresh reemite
    # o token, e o bloqueio continua.
    assert issubclass(PasswordChangeRequiredError, PermissionError)

    app = (RAIZ / 'app.py').read_text(encoding='utf-8')
    inicio = app.index('except PasswordChangeRequiredError as exc:')
    corpo = app[inicio:app.index('except PermissionError as exc:', inicio)]
    assert 'send_json(self, 403,' in corpo
    assert 'unauthorized(' not in corpo, 'o bloqueio nunca pode virar 401'

    # `AuthenticationError` (401) só existe no repositório principal — o espelho
    # ainda responde 403 para falha de autenticação, divergência rastreada na
    # issue de allowlist backend. A asserção é condicional para que ESTE arquivo
    # seja idêntico nos dois repositórios, que é o que prova a equivalência.
    if hasattr(seguranca, 'AuthenticationError'):
        assert not issubclass(
            PasswordChangeRequiredError, seguranca.AuthenticationError,
        )

def test_o_codigo_e_estavel_para_o_frontend():
    assert PasswordChangeRequiredError.CODE == 'PASSWORD_CHANGE_REQUIRED'
    assert str(PasswordChangeRequiredError()) == PasswordChangeRequiredError.MESSAGE


def test_o_handler_http_responde_403_com_o_codigo():
    app = (RAIZ / 'app.py').read_text(encoding='utf-8')
    assert app.count('except PasswordChangeRequiredError as exc:') == 4, \
        'os quatro verbos HTTP precisam do tratamento'
    assert "'code': PasswordChangeRequiredError.CODE" in app
    assert 'send_json(self, 403, {' in app


def test_o_except_especifico_vem_antes_do_generico():
    # `PasswordChangeRequiredError` é subclasse de `PermissionError`. Na ordem
    # errada, o genérico captura primeiro e o cliente recebe um 403 sem código
    # — indistinguível de falta de permissão.
    app = (RAIZ / 'app.py').read_text(encoding='utf-8')
    for bloco in re.finditer(r'except PermissionError as exc:', app):
        anterior = app[:bloco.start()]
        assert anterior.rfind('except PasswordChangeRequiredError') > anterior.rfind('def do_'), \
            'há um `except PermissionError` sem o específico antes dele'


# ── O caminho de saída não pode se trancar ───────────────────────────────────

def test_a_rota_de_troca_de_senha_nao_passa_pelo_bloqueio():
    # A garantia estrutural: `/api/change-password` usa `get_user_by_id`
    # direto, não `authorize_action`/`require_actor`. Se alguém "padronizar"
    # esse handler para usar o gargalo, o usuário fica preso sem contorno — e
    # este teste é o que impede.
    rotas = (RAIZ / 'modules/auth/routes.py').read_text(encoding='utf-8')
    inicio = rotas.index('def handle_post_change_password')
    corpo = rotas[inicio:rotas.index('\ndef ', inicio + 1)]
    assert 'authorize_action' not in corpo, \
        'a rota de troca passaria a exigir autorização e se trancaria sozinha'
    assert 'require_actor' not in corpo, \
        'a rota de troca passaria pelo bloqueio e o usuário ficaria sem saída'
    assert 'get_user_by_id' in corpo


def test_auth_me_usa_a_excecao_explicita():
    rotas = (RAIZ / 'modules/auth/routes.py').read_text(encoding='utf-8')
    inicio = rotas.index('def handle_get_auth_me')
    corpo = rotas[inicio:rotas.index('\ndef ', inicio + 1)]
    assert 'allow_password_change_pending=True' in corpo


def test_auth_me_informa_o_estado_ao_cliente():
    # Sem isto o app reaberto com token já emitido recebe 403 em tudo e não
    # tem como descobrir que o caminho é a tela de troca.
    rotas = (RAIZ / 'modules/auth/routes.py').read_text(encoding='utf-8')
    inicio = rotas.index('def handle_get_auth_me')
    corpo = rotas[inicio:rotas.index('\ndef ', inicio + 1)]
    assert "'must_change_password': must_change" in corpo
    assert "'require_password_change': must_change" in corpo


def test_somente_auth_me_liga_a_excecao():
    # A exceção é para o caso que precisa dela. Espalhá-la reabriria o furo em
    # silêncio, uma rota por vez.
    #
    # O que se procura é quem LIGA (`=True`), não quem menciona o parâmetro:
    # `modules/auth/service.require_actor` o repassa por delegação, o que é
    # legítimo e não libera nada por conta própria.
    liga = []
    for caminho in sorted((RAIZ / 'modules').rglob('*.py')):
        texto = caminho.read_text(encoding='utf-8')
        if 'allow_password_change_pending=True' in texto:
            liga.append(str(caminho.relative_to(RAIZ)))
    assert liga == ['modules/auth/routes.py'], f'exceção ligada fora do /auth/me: {liga}'

    rotas = (RAIZ / 'modules/auth/routes.py').read_text(encoding='utf-8')
    assert rotas.count('allow_password_change_pending=True') == 1


def test_nao_ha_segunda_implementacao_de_require_actor():
    # Havia uma cópia quase idêntica em `modules/auth/service.py`. O bloqueio
    # entrou só na de `core.repository`, e a outra deixava `/api/users/{id}/email`
    # e as rotas de 2FA passarem por cima — em silêncio. Uma regra de segurança
    # não pode ter duas implementações.
    servico = (RAIZ / 'modules/auth/service.py').read_text(encoding='utf-8')
    inicio = servico.index('def require_actor(')
    corpo = servico[inicio:servico.index('\ndef ', inicio + 1)]
    assert '_require_actor(' in corpo, 'a delegação para core.repository sumiu'
    assert 'get_user_by_id' not in corpo, \
        'a segunda implementação voltou — o bloqueio ficaria só numa delas'


# ── Cobertura do gargalo: API direta, deep link, cliente modificado ──────────

def test_authorize_action_passa_pelo_bloqueio(sem_efeitos):
    # É o caminho de /api/bootstrap, /api/stock/epis, /api/employees e de todos
    # os demais módulos — curl, deep link ou cliente modificado chegam aqui do
    # mesmo jeito, porque a checagem é do servidor e não da navegação.
    with pytest.raises(PasswordChangeRequiredError):
        repo.authorize_action(_Conn(must_change=True), 42, 'stock:view')


def test_authorize_action_any_passa_pelo_bloqueio(sem_efeitos):
    with pytest.raises(PasswordChangeRequiredError):
        repo.authorize_action_any(_Conn(must_change=True), 42, ['stock:view'])


@pytest.mark.parametrize('modulo', [
    'stock', 'employees', 'epis', 'deliveries', 'units', 'reports', 'purchases',
])
def test_amostra_de_modulos_usa_o_gargalo(modulo):
    # Amostra dos 21 módulos: se algum autorizasse por conta própria, ficaria
    # fora do bloqueio sem que nada acusasse.
    rotas = (RAIZ / f'modules/{modulo}/routes.py').read_text(encoding='utf-8')
    assert 'authorize_action' in rotas, f'{modulo} não passa pelo ponto central'


def test_o_bootstrap_esta_bloqueado():
    # A maior superfície de dados do sistema. Se ficasse de fora, o bloqueio
    # seria decorativo.
    rotas = (RAIZ / 'modules/auth/routes.py').read_text(encoding='utf-8')
    inicio = rotas.index('def handle_get_bootstrap')
    corpo = rotas[inicio:rotas.index('\ndef ', inicio + 1)]
    assert 'authorize_action' in corpo
    assert 'allow_password_change_pending' not in corpo


# ── Depois da troca, sem novo login ──────────────────────────────────────────

def test_apos_a_troca_o_mesmo_token_volta_a_funcionar(sem_efeitos):
    # A autorização relê a política do banco a cada `require_actor` — não
    # depende de claim do token. Por isso limpar a flag basta: o token que
    # tomava 403 volta a funcionar, sem novo login.
    conn = _Conn(must_change=True)
    with pytest.raises(PasswordChangeRequiredError):
        repo.require_actor(conn, 42)
    conn.must_change = False  # troca válida limpou a flag
    assert repo.require_actor(conn, 42)['id'] == 42


def test_a_autorizacao_nao_depende_de_claim_do_token():
    # Se dependesse, `/api/auth/refresh` (público) reemitiria um token com a
    # flag antiga e contornaria o bloqueio.
    seguranca = (RAIZ / 'core/security.py').read_text(encoding='utf-8')
    inicio = seguranca.index('def create_jwt_token')
    corpo = seguranca[inicio:seguranca.index('\ndef ', inicio + 1)]
    assert 'must_change_password' not in corpo, \
        'a flag no token tornaria o refresh um caminho de contorno'

    repositorio = (RAIZ / 'core/repository.py').read_text(encoding='utf-8')
    inicio = repositorio.index('def require_actor(')
    corpo = repositorio[inicio:repositorio.index('\ndef ', inicio + 1)]
    assert 'get_user_by_id' in corpo, \
        'a política precisa ser relida do banco, não deduzida do token'
