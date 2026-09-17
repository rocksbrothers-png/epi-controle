"""Hardening do Login — não enumeração de credenciais.

## O achado

O backend distinguia, para o cliente NÃO AUTENTICADO, qual credencial falhou:

    usuário inexistente   401  USER_NOT_FOUND           'Usuário não encontrado.'
    senha incorreta       401  INVALID_PASSWORD         'Senha incorreta.'
    conta inativa         403  USER_INACTIVE            'Usuário inativo. ...'
    perfil funcionário    403  EMPLOYEE_EXTERNAL_ONLY   'Funcionário não pode ...'

As quatro são alcançáveis SEM saber a senha, então as quatro confirmam a
existência do identificador. Com a lista de códigos acima, enumerar a base de
usuários é uma requisição por palpite.

Havia ainda um segundo canal, independente do texto: **tempo**. O caminho de
usuário inexistente retornava antes do `bcrypt`; o de senha incorreta pagava o
hash inteiro. Medido neste repositório: 0,06 ms contra 269 ms — 4260×. Trocar
só a mensagem deixaria a enumeração funcionando por cronômetro.

## O contrato

Para o cliente não autenticado, QUALQUER falha de credencial responde:

    401  INVALID_CREDENTIALS  'Usuário ou senha incorretos.'

e responde gastando o mesmo trabalho, para que os caminhos não se separem por
tempo.

## O que continua distinto, e por quê

`TOTP_REQUIRED`, `TOTP_INVALID` e `TEMP_PASSWORD_EXPIRED` só são alcançáveis
DEPOIS de a senha correta ter sido apresentada. Quem chega neles já provou
conhecer a credencial: não há o que enumerar, e uniformizá-los quebraria o 2FA
e a política de senha temporária. O mesmo vale para 429 (rate limit) e para
5xx, que precisam continuar distinguíveis de credencial inválida.

Nenhum teste aqui usa credencial real.
"""

import time
import statistics

import pytest

import modules.auth.service as auth_svc
from core.security import hash_password


SENHA_CERTA = 'SenhaCorreta#2026'
SENHA_ERRADA = 'SenhaErrada#2026'


# ── Conexão falsa ────────────────────────────────────────────────────────────
# Mesma convenção de `tests/test_password_policy.py`: o que este contrato mede
# é a resposta pública e o caminho percorrido, e nenhum dos dois depende do
# banco real.

def _linha(**sobrepor):
    base = {
        'id': 7, 'username': 'ana.silva', 'password': hash_password(SENHA_CERTA),
        'full_name': 'Ana Silva', 'role': 'admin', 'company_id': None, 'active': 1,
        'linked_employee_id': None, 'company_name': None, 'company_cnpj': None,
        'logo_type': None,
    }
    base.update(sobrepor)
    return base


class _Cur:
    def __init__(self, rows): self._r = rows
    def fetchone(self): return self._r[0] if self._r else None
    def fetchall(self): return self._r


class _Conn:
    def __init__(self, linha=None):
        self.linha = linha

    def execute(self, sql, params=()):
        s = ' '.join(sql.lower().split())
        if 'from users left join companies' in s:
            return _Cur([self.linha] if self.linha else [])
        if s.startswith('select totp_secret'):
            return _Cur([{'totp_secret': '', 'totp_enabled': 0}])
        if s.startswith('select must_change_password'):
            return _Cur([{'must_change_password': 0, 'password_expires_at': None}])
        return _Cur([])

    def commit(self): pass
    def rollback(self): pass


def _tentar(linha, usuario, senha):
    """Uma tentativa de login. Devolve (payload, status, erro_publico)."""
    return auth_svc.authenticate_login(_Conn(linha), usuario, senha)


# ── S1..S4: os quatro cenários ───────────────────────────────────────────────

def test_s1_senha_incorreta_responde_generico():
    _, status, erro = _tentar(_linha(), 'ana.silva', SENHA_ERRADA)
    assert status == 401, f'status mudou: {status}'
    assert erro['code'] == 'INVALID_CREDENTIALS', f'code revela a causa: {erro["code"]!r}'
    assert erro['error'] == 'Usuário ou senha incorretos.', f'mensagem revela a causa: {erro["error"]!r}'


def test_s2_usuario_inexistente_responde_generico():
    _, status, erro = _tentar(None, 'nao.existe', SENHA_ERRADA)
    assert status == 401, f'status mudou: {status}'
    assert erro['code'] == 'INVALID_CREDENTIALS', f'code revela a causa: {erro["code"]!r}'
    assert erro['error'] == 'Usuário ou senha incorretos.', f'mensagem revela a causa: {erro["error"]!r}'


def test_s1_vs_s2_nenhum_campo_publico_distingue():
    """O gate central. Comparação do payload INTEIRO, não só da mensagem.

    É este que pega a sabotagem γ: interface genérica com códigos distintos no
    payload continua sendo enumeração — o atacante lê a resposta HTTP, não a
    tela.
    """
    _, status_senha, erro_senha = _tentar(_linha(), 'ana.silva', SENHA_ERRADA)
    _, status_ausente, erro_ausente = _tentar(None, 'nao.existe', SENHA_ERRADA)

    assert status_senha == status_ausente, (
        f'o status separa os casos: {status_senha} vs {status_ausente}')
    assert erro_senha == erro_ausente, (
        'o payload público separa os casos:\n'
        f'  senha incorreta:    {erro_senha}\n'
        f'  usuário inexistente: {erro_ausente}')


def test_s3_credenciais_validas_continuam_entrando():
    """A metade que impede o falso verde: uniformizar tudo em 401 passaria em
    S1 e S2 e deixaria o produto sem login."""
    payload, status, erro = _tentar(_linha(), 'ana.silva', SENHA_CERTA)
    assert erro is None, f'login válido foi recusado: {erro}'
    assert status == 200, f'login válido não retornou 200: {status}'
    assert payload['user']['id'] == 7


def test_s4_campos_vazios_continuam_sendo_validacao_estrutural():
    """Campo obrigatório não é falha de autenticação e não entra no contrato
    genérico — nada foi tentado contra a base."""
    for usuario, senha in [('', ''), ('ana.silva', ''), ('', SENHA_CERTA), ('ana.silva', '   ')]:
        with pytest.raises(ValueError) as exc:
            _tentar(_linha(), usuario, senha)
        assert 'obrigat' in str(exc.value).lower(), (
            f'({usuario!r}, {senha!r}) deixou de ser validação estrutural: {exc.value}')


# ── Os outros dois oráculos, que também eram alcançáveis sem a senha ─────────

def test_conta_inativa_nao_confirma_a_existencia_do_usuario():
    _, status, erro = _tentar(_linha(active=0), 'ana.silva', SENHA_ERRADA)
    assert status == 401 and erro['code'] == 'INVALID_CREDENTIALS', (
        f'conta inativa continua identificável: {status} {erro}')


def test_perfil_funcionario_nao_confirma_a_existencia_do_usuario():
    _, status, erro = _tentar(_linha(role='employee'), 'ana.silva', SENHA_ERRADA)
    assert status == 401 and erro['code'] == 'INVALID_CREDENTIALS', (
        f'perfil funcionário continua identificável: {status} {erro}')


# ── O que NÃO pode ser uniformizado ──────────────────────────────────────────

def test_totp_e_senha_temporaria_continuam_distintos():
    """Só se alcança estes DEPOIS da senha correta: quem chega aqui já provou
    conhecer a credencial, então não há o que enumerar. Uniformizá-los
    quebraria o 2FA e a política de senha temporária."""
    codigos = [c for c in ('TOTP_REQUIRED', 'TOTP_INVALID', 'TEMP_PASSWORD_EXPIRED')
               if c in _fonte_do_servico()]
    assert codigos == ['TOTP_REQUIRED', 'TOTP_INVALID', 'TEMP_PASSWORD_EXPIRED'], (
        f'a uniformização levou junto estados pós-senha: sobraram {codigos}')


def _fonte_do_servico(sem_comentarios=False):
    import pathlib
    raiz = pathlib.Path(__file__).resolve().parent.parent
    texto = (raiz / 'modules' / 'auth' / 'service.py').read_text(encoding='utf-8')
    if not sem_comentarios:
        return texto
    # Mesma convenção de `tests/test_343_f2_teardown_logout.py`: os comentários
    # CITAM os nomes antigos para explicar por que saíram, e essa explicação é
    # parte do valor da mudança. O que o gate mede é o código.
    return '\n'.join(
        linha for linha in texto.splitlines()
        if not linha.lstrip().startswith('#')
    )


def _corpo_de(fonte, nome):
    """Extrai o corpo de uma função por indentação."""
    linhas = fonte.splitlines()
    i = next(k for k, l in enumerate(linhas) if l.startswith(f'def {nome}('))
    fim = next((k for k in range(i + 1, len(linhas))
                if linhas[k] and not linhas[k][0].isspace() and not linhas[k].startswith(')')),
               len(linhas))
    return '\n'.join(linhas[i:fim])


def test_nenhuma_mensagem_reveladora_sobrou_no_caminho_de_login():
    """Par estrutural dos gates comportamentais: pega as sabotagens α e β.

    ESCOPADO ao caminho de login, de propósito. `validate_and_clear_recovery_token`
    também responde 'Usuário não encontrado.' a um cliente não autenticado — é
    enumeração pela recuperação de senha, achado REAL e registrado, mas de
    outro endpoint e com outro contrato: a correção usual ("enviamos um e-mail
    se a conta existir") muda o fluxo visível ao usuário e é decisão de
    produto. Um gate que proibisse a frase no arquivo inteiro arrastaria essa
    mudança para dentro desta fatia sem ninguém ter decidido.
    """
    fonte = _fonte_do_servico(sem_comentarios=True)
    caminho_de_login = (
        _corpo_de(fonte, 'authenticate_login')
        + _corpo_de(fonte, '_recusa_de_credencial')
        + '\n'.join(l for l in fonte.splitlines() if l.startswith('MSG_') or l.startswith('CODIGO_'))
    )
    for proibida in ('Senha incorreta', 'Usuário não encontrado', 'Usuário inativo',
                     'USER_NOT_FOUND', 'INVALID_PASSWORD', 'USER_INACTIVE',
                     'EMPLOYEE_EXTERNAL_ONLY'):
        assert proibida not in caminho_de_login, (
            f'{proibida!r} voltou ao caminho de login — ver Hardening do Login')


# ── Timing ───────────────────────────────────────────────────────────────────

def test_usuario_inexistente_tambem_paga_a_verificacao_de_senha():
    """Determinístico, e por isso o gate principal de timing.

    Antes, `usuário inexistente` retornava ANTES do `bcrypt`. A correção não é
    `sleep()`: é fazer o MESMO trabalho, contra um hash fictício. Este gate
    conta as invocações em vez de cronometrar — cronômetro em CI é instável.
    """
    chamadas = []
    original = auth_svc.verify_password
    auth_svc.verify_password = lambda armazenada, fornecida: (
        chamadas.append(1), original(armazenada, fornecida))[1]
    try:
        _tentar(None, 'nao.existe', SENHA_ERRADA)
    finally:
        auth_svc.verify_password = original
    assert chamadas, (
        'usuário inexistente volta sem verificar senha: o caminho rápido '
        'reabre a enumeração por tempo'
    )


def test_o_tempo_medido_nao_separa_os_dois_caminhos():
    """A confirmação empírica do gate acima. Faixa larga de propósito: o que
    importa é a ordem de grandeza — antes era 4260×."""
    def medir(linha, usuario, n=7):
        amostras = []
        for _ in range(n):
            t0 = time.perf_counter()
            _tentar(linha, usuario, SENHA_ERRADA)
            amostras.append(time.perf_counter() - t0)
        return statistics.median(amostras)

    com_usuario = medir(_linha(), 'ana.silva')
    sem_usuario = medir(None, 'nao.existe')
    razao = max(com_usuario, sem_usuario) / max(min(com_usuario, sem_usuario), 1e-9)
    assert razao < 3.0, (
        f'os caminhos se separam por tempo: razão {razao:.1f}× '
        f'(com usuário {com_usuario * 1000:.1f} ms, sem usuário {sem_usuario * 1000:.1f} ms)'
    )
