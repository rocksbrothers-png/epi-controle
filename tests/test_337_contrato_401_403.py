"""#337 — o contrato 401 × 403, e a paridade Corporate ↔ SaaS que ele define.

## O defeito

`core/security.py` divergia entre os repositórios: o principal tinha
`AuthenticationError`, o espelho não. Todo ponto que num levantava
`AuthenticationError` (→ 401) levantava `PermissionError` (→ 403) no outro, e a
MESMA requisição sem credencial recebia 401 num deployment e 403 no outro —
medido em produção nas corridas 13, 14 e 15 da certificação B4-B.

O 401 não é cosmético: é o que dispara o refresh automático do access token no
cliente Flutter (`_BearerInterceptor`, `api_client.dart`). Com 403 o refresh
nunca ocorria e o usuário via "Sem conexão" onde bastaria renovar a sessão.

## A correção de contrato que a auditoria produziu

A issue falava em "10 pontos de autenticação". A auditoria provou que são
**nove**: o décimo — token válido cujo `sub` diverge do `actor_user_id` pedido
no corpo/query — é conflito de IDENTIDADE. Ali o servidor sabe quem é o
usuário; o que ele recusa é operar como outra pessoa. Isso é autorização:

    ausência/falha de credencial          → 401  AuthenticationError
    credencial válida + identidade alheia → 403  PermissionError
    credencial válida sem permissão       → 403  PermissionError

Um 401 no décimo ponto também seria inútil na prática: o refresh reemite o
token, e o `actor_user_id` divergente continua no corpo da request.

## Por que os testes antigos não pegavam isto

`AuthenticationError` é subclasse de `PermissionError` de propósito — para que
handlers que só capturam `PermissionError` continuem cobrindo o caso. O efeito
colateral é que `pytest.raises(PermissionError)` passa para as DUAS, e era assim
que a suíte afirmava esses pontos. Por isso **este arquivo compara a classe
exata**: `type(exc) is X`, nunca `isinstance`.

Este arquivo é idêntico nos dois repositórios; rodá-lo dos dois lados é o que
prova a paridade semântica.
"""

import pathlib
import re

import pytest

import core.security as seguranca
from core.security import (
    AuthenticationError,
    PasswordChangeRequiredError,
    create_jwt_token,
    decode_jwt_token,
    decode_token_of_type,
    parse_bearer_token,
    resolve_actor_user_id,
)

RAIZ = pathlib.Path(__file__).resolve().parent.parent
APP = RAIZ / 'app.py'
SECURITY = RAIZ / 'core' / 'security.py'
AUTH_ROUTES = RAIZ / 'modules' / 'auth' / 'routes.py'
CORE_AUTH = RAIZ / 'core' / 'auth.py'

VERBOS = ('GET', 'POST', 'PUT', 'DELETE')


# ── Fakes mínimos ────────────────────────────────────────────────────────────

class _Handler:
    def __init__(self, auth=''):
        self.headers = {'Authorization': auth} if auth else {}
        self.command = 'GET'
        self.client_address = ('127.0.0.1',)


class _Parsed:
    def __init__(self, query=''):
        self.query = query
        self.path = '/api/units/selectable'


def _token(user_id=5, **extra):
    linha = {'id': user_id, 'role': 'admin', 'company_id': 1}
    if not extra:
        return create_jwt_token(linha)
    return seguranca._encode_jwt({'sub': user_id, 'type': 'access', **extra})


def _sem_comentarios(texto):
    """Comentários citam a regra que descrevem; não podem provar nem reprovar."""
    return '\n'.join(
        linha for linha in texto.splitlines()
        if not linha.lstrip().startswith('#')
    )


def _bloco_do_verbo(app, verbo):
    """Recorta o corpo de `do_<VERBO>` até o próximo `def do_`."""
    inicio = app.index(f'def do_{verbo}(self)')
    resto = app[inicio:]
    fim = resto.find('\n    def do_', 1)
    return resto if fim == -1 else resto[:fim]


# ── 1. Os nove pontos de autenticação ────────────────────────────────────────

def _expirado():
    return _token(exp=1, iat=0)


def _assinatura_forjada():
    cabeca, corpo, _ = _token().split('.')
    return f'{cabeca}.{corpo}.YWFhYWFh'


def _payload_nao_json():
    cabeca, _, assinatura = _token().split('.')
    return f'{cabeca}.bm90LWpzb24.{assinatura}'


CASOS_DE_AUTENTICACAO = {
    'header malformado': lambda: parse_bearer_token(_Handler(auth='Basic abc')),
    'token ausente': lambda: decode_jwt_token(''),
    'token sem tres segmentos': lambda: decode_jwt_token('a.b'),
    'assinatura invalida': lambda: decode_jwt_token(_assinatura_forjada()),
    'payload nao json': lambda: decode_jwt_token(_payload_nao_json()),
    'token expirado': lambda: decode_jwt_token(_expirado()),
    'tipo errado': lambda: decode_token_of_type(_token(), 'refresh'),
    'sessao sem usuario': lambda: resolve_actor_user_id(_Handler(), _Parsed(), None),
}


@pytest.mark.parametrize('nome', sorted(CASOS_DE_AUTENTICACAO))
def test_falha_de_autenticacao_levanta_authentication_error(nome):
    with pytest.raises(PermissionError) as info:
        CASOS_DE_AUTENTICACAO[nome]()
    assert type(info.value) is AuthenticationError, (
        f'{nome}: {type(info.value).__name__} — falha de autenticação precisa '
        'da classe exata, senão o handler responde 403 e o cliente não renova '
        'a sessão'
    )


def test_enforce_sem_bearer_e_autenticacao(monkeypatch):
    """O nono ponto: modo `enforce` com actor resolvido sem Bearer."""
    monkeypatch.setattr(seguranca, 'JWT_ENFORCEMENT_MODE', 'enforce')
    with pytest.raises(PermissionError) as info:
        resolve_actor_user_id(_Handler(), _Parsed(), {'actor_user_id': 5})
    assert type(info.value) is AuthenticationError


def test_o_arquivo_tem_nove_pontos_de_autenticacao_e_um_de_autorizacao():
    corpo = _sem_comentarios(SECURITY.read_text(encoding='utf-8'))
    assert corpo.count('raise AuthenticationError') == 9
    assert corpo.count('raise PermissionError') == 1


# ── 2 e 6. O conflito de identidade é 403 ────────────────────────────────────

def test_conflito_de_identidade_e_permission_error_puro():
    """Token válido + `actor_user_id` alheio: o servidor SABE quem é o usuário.

    Recusar isso é autorização (personificação), não autenticação. Como 401 o
    cliente gastaria um refresh que jamais corrigiria o caso — o valor
    divergente está no corpo da request, não no token.
    """
    handler = _Handler(auth=f'Bearer {_token(user_id=5)}')
    with pytest.raises(PermissionError) as info:
        resolve_actor_user_id(handler, _Parsed(), {'actor_user_id': 9})
    assert type(info.value) is PermissionError, (
        f'conflito de identidade virou {type(info.value).__name__}: seria 401, '
        'e o refresh nunca resolveria'
    )
    assert not isinstance(info.value, AuthenticationError)


def test_o_conflito_de_identidade_esta_documentado_no_codigo():
    """Sem a razão escrita ao lado, o próximo leitor "corrige" de volta."""
    corpo = SECURITY.read_text(encoding='utf-8')
    trecho = corpo[corpo.index('Dados de autenticação inconsistentes') - 800:]
    assert '#337' in trecho[:800]


# ── 3, 4 e 5. O mapeamento HTTP ──────────────────────────────────────────────

def test_o_helper_de_autenticacao_responde_401():
    corpo = _sem_comentarios(APP.read_text(encoding='utf-8'))
    inicio = corpo.index('def unauthorized(handler, message):')
    assert 'send_json(handler, 401,' in corpo[inicio:inicio + 200]


def test_o_helper_de_autorizacao_continua_403():
    corpo = _sem_comentarios(APP.read_text(encoding='utf-8'))
    inicio = corpo.index('def forbidden(handler, message):')
    assert 'send_json(handler, 403,' in corpo[inicio:inicio + 200]


@pytest.mark.parametrize('verbo', VERBOS)
def test_authentication_error_vira_401_nos_quatro_verbos(verbo):
    bloco = _sem_comentarios(_bloco_do_verbo(APP.read_text(encoding='utf-8'), verbo))
    inicio = bloco.index('except AuthenticationError as exc:')
    corpo = bloco[inicio:bloco.index('except PasswordChangeRequiredError', inicio)]
    assert 'unauthorized(self, str(exc))' in corpo
    assert 'forbidden(' not in corpo


@pytest.mark.parametrize('verbo', VERBOS)
def test_permission_error_continua_403_nos_quatro_verbos(verbo):
    bloco = _sem_comentarios(_bloco_do_verbo(APP.read_text(encoding='utf-8'), verbo))
    inicio = bloco.index('except PermissionError as exc:')
    corpo = bloco[inicio:inicio + 400]
    assert 'forbidden(self, str(exc))' in corpo
    assert 'unauthorized(' not in corpo


def test_o_bootstrap_distingue_os_dois_ramos():
    """O 11º ponto, fora de `core/security.py`: `modules/auth/routes.py`."""
    corpo = _sem_comentarios(AUTH_ROUTES.read_text(encoding='utf-8'))
    auth = corpo.index('except AuthenticationError as exc:')
    perm = corpo.index('except PermissionError as exc:', auth)
    assert auth < perm, 'o ramo genérico captura primeiro e o 401 nunca acontece'
    assert 'send_json(handler, 401,' in corpo[auth:perm]
    assert 'send_json(handler, 403,' in corpo[perm:perm + 500]


# ── 7. A senha temporária continua 403 ───────────────────────────────────────

def test_password_change_required_nao_e_autenticacao():
    assert issubclass(PasswordChangeRequiredError, PermissionError)
    assert not issubclass(PasswordChangeRequiredError, AuthenticationError)


@pytest.mark.parametrize('verbo', VERBOS)
def test_password_change_required_responde_403_com_codigo(verbo):
    bloco = _sem_comentarios(_bloco_do_verbo(APP.read_text(encoding='utf-8'), verbo))
    inicio = bloco.index('except PasswordChangeRequiredError as exc:')
    corpo = bloco[inicio:bloco.index('except PermissionError', inicio)]
    assert 'send_json(self, 403,' in corpo
    assert 'PasswordChangeRequiredError.CODE' in corpo
    assert 'unauthorized(' not in corpo


# ── 8. A ordem dos `except` ──────────────────────────────────────────────────

@pytest.mark.parametrize('verbo', VERBOS)
def test_a_ordem_dos_handlers_e_do_mais_especifico_ao_mais_generico(verbo):
    """`AuthenticationError` e `PasswordChangeRequiredError` são subclasses de
    `PermissionError`: fora de ordem, o genérico captura tudo e os dois status
    específicos desaparecem sem erro nenhum."""
    bloco = _sem_comentarios(_bloco_do_verbo(APP.read_text(encoding='utf-8'), verbo))
    auth = bloco.index('except AuthenticationError as exc:')
    senha = bloco.index('except PasswordChangeRequiredError as exc:')
    generico = bloco.index('except PermissionError as exc:')
    assert auth < senha < generico


# ── 9. Nenhuma conversão em massa ────────────────────────────────────────────

PORTOES_DE_AUTORIZACAO = (
    'ensure_permission',
    'ensure_company_access',
    'require_structural_admin',
    'require_configuration_admin',
    'require_master_admin',
)


@pytest.mark.parametrize('funcao', PORTOES_DE_AUTORIZACAO)
def test_os_portoes_de_autorizacao_continuam_permission_error(funcao):
    corpo = CORE_AUTH.read_text(encoding='utf-8')
    inicio = corpo.index(f'def {funcao}(')
    resto = corpo[inicio:]
    fim = resto.find('\ndef ', 1)
    trecho = resto if fim == -1 else resto[:fim]
    assert 'raise PermissionError' in trecho
    assert 'AuthenticationError' not in trecho, (
        f'{funcao} é autorização: promovê-la a 401 mandaria o cliente renovar '
        'a sessão para um bloqueio que a sessão não resolve'
    )


def test_authentication_error_so_existe_nos_tres_arquivos_do_contrato():
    """Se aparecer num quarto arquivo, alguém está convertendo por atacado."""
    permitidos = {
        'core/security.py',
        'app.py',
        'modules/auth/routes.py',
    }
    achados = set()
    for caminho in RAIZ.rglob('*.py'):
        rel = caminho.relative_to(RAIZ).as_posix()
        if rel.startswith(('tests/', '.venv/', 'venv/')):
            continue
        if 'AuthenticationError' in caminho.read_text(encoding='utf-8'):
            achados.add(rel)
    assert achados == permitidos, f'fora do contrato: {sorted(achados - permitidos)}'


def test_o_volume_de_autorizacao_permanece():
    """Piso, não igualdade: os repositórios diferem em `modules/reports/`, e o
    gate não pode exigir contagem idêntica entre eles."""
    total = 0
    for caminho in RAIZ.rglob('*.py'):
        rel = caminho.relative_to(RAIZ).as_posix()
        if rel.startswith(('tests/', '.venv/', 'venv/')) or rel == 'core/security.py':
            continue
        total += caminho.read_text(encoding='utf-8').count('raise PermissionError')
    assert total >= 130, f'só restaram {total} PermissionError de autorização'


# ── 10. O módulo órfão segue órfão ───────────────────────────────────────────

def test_o_modulo_orfao_continua_sem_importadores():
    """`epi_backend/security.py` duplica os mesmos pontos com `PermissionError`
    puro e não é importado por ninguém. Religá-lo sem convertê-lo reintroduz a
    divergência nos dois repositórios de uma vez."""
    padrao = re.compile(r'epi_backend[\.\s]+security|from epi_backend import security')
    achados = []
    for caminho in RAIZ.rglob('*.py'):
        rel = caminho.relative_to(RAIZ).as_posix()
        if rel in ('epi_backend/security.py', 'tests/test_337_contrato_401_403.py'):
            continue
        if rel.startswith(('.venv/', 'venv/')):
            continue
        if padrao.search(caminho.read_text(encoding='utf-8')):
            achados.append(rel)
    assert achados == [], f'o órfão ganhou importadores sem ser convergido: {achados}'
