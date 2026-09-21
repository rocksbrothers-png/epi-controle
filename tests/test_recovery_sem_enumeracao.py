"""Não enumeração nos endpoints de recuperação de senha.

## Os dois endpoints, e por que o contrato deles é diferente

**A — `POST /api/auth/request-email-recovery`** ("me mande instruções"). Recebe
só o usuário e dispara o e-mail com o token.

**B — `POST /api/recover-password`** ("redefinir com a chave"). Recebe usuário,
senha nova e chave; troca a senha.

A mensagem "se os dados estiverem cadastrados você receberá instruções" descreve
**A**. Em **B** ela não faria sentido: quem chama B está enviando uma senha
nova, não pedindo instruções. São contratos distintos, e os gates tratam cada um
no seu.

## O que foi medido ANTES (estado atual)

**A** já respondia 200 com mensagem genérica nos três caminhos felizes — e
mesmo assim era enumerável por dois canais:

    A4 SMTP falha  ->  400 'Falha ao enviar e-mail: <detalhe interno>'
                       alcançável SÓ para usuário existente COM e-mail
    timing         ->  268 ms contra 0,09 ms  =  5207x
                       `generate_user_recovery_token` chama `hash_password`
                       (bcrypt), e só o caminho do usuário existente paga

É o caso exato de "não basta uniformizar a mensagem visual": a mensagem já
estava uniforme e o endpoint continuava respondendo a pergunta.

**B** distinguia por mensagem E por status:

    B1 não existe                    400  'Usuário não encontrado.'
    B2 existe, sem token, chave má   403  'Chave de recuperação inválida.'
    B3 existe, com token, chave má   400  'Chave de recuperação inválida.'
    B4 existe, token expirado        400  'Chave de recuperação expirada...'

B2 e B3 têm a MESMA mensagem e status diferente: o status sozinho revela se a
conta tem token próprio. E B3 paga bcrypt (268 ms) enquanto B1/B2/B4 não.

## O contrato

Para o solicitante, qualquer requisição de formato válido recebe UMA resposta
por endpoint, gastando trabalho equivalente. A operação interna continua
distinguindo tudo — no log, nunca na resposta.

Validação estrutural (campo obrigatório ausente) não entra: nada chegou a ser
consultado.

Nenhum teste aqui usa credencial real.
"""

import json
import time
import statistics

import modules.auth.routes as R
import modules.auth.service as S
from core.security import hash_password


SENHA_NOVA = 'NovaSenhaForte#2026'
EMAIL = 'ana@exemplo.com'
TOKEN_BOM = 'token-de-recuperacao-valido'


# ── Dublês ───────────────────────────────────────────────────────────────────

class _Cur:
    def __init__(self, rows): self._r = rows
    def fetchone(self): return self._r[0] if self._r else None
    def fetchall(self): return self._r


class _Conn:
    def __init__(self, existe=True, email=EMAIL, token_hash=None, expira=None):
        self.existe, self.email = existe, email
        self.token_hash, self.expira = token_hash, expira
        self.updates = []

    def execute(self, sql, params=()):
        s = ' '.join(sql.lower().split())
        if s.startswith('select id from users where lower(username)'):
            return _Cur([{'id': 7}] if self.existe else [])
        if s.startswith('select recovery_token_hash from users'):
            return _Cur([{'recovery_token_hash': self.token_hash}])
        if s.startswith('select id, username, email from users'):
            return _Cur([{'id': 7, 'username': 'ana.silva', 'email': self.email}])
        if s.startswith('select id, username, password, full_name, role, recovery_token_hash'):
            return _Cur([{'id': 7, 'username': 'ana.silva', 'password': 'x',
                          'full_name': 'Ana', 'role': 'admin',
                          'recovery_token_hash': self.token_hash,
                          'recovery_token_expires_at': self.expira}])
        if s.startswith('update users'):
            self.updates.append(params)
            return _Cur([])
        return _Cur([])

    def commit(self): pass
    def rollback(self): pass
    def close(self): pass


# O endpoint B é limitado a 5 chamadas por IP a cada 5 minutos. Um harness que
# reusasse o mesmo IP começaria a receber 429 no meio da bateria e passaria a
# medir o LIMITADOR em vez do contrato — dois controles que deveriam ficar
# verdes ficaram vermelhos assim, na primeira rodada. Cada chamada usa um IP
# próprio, o que isola o contrato sem desligar a proteção.
_PROXIMO_IP = iter(f'198.51.100.{n}' for n in range(1, 255))


class _Handler:
    def __init__(self):
        self.status, self.corpo = None, None
        self.path, self.command = '/api/x', 'POST'
        self.headers = {'X-Forwarded-For': next(_PROXIMO_IP), 'Host': 'local'}
        handler = self

        class _W:
            def write(self, b): handler.corpo = json.loads(b.decode('utf-8'))

        self.wfile = _W()

    def send_response(self, s): self.status = s
    def send_header(self, *a): pass
    def end_headers(self): pass


def _chamar(fn, payload, conn, smtp=None):
    """Executa o handler e mapeia a exceção como o `app.py` faz (400/403).

    Devolve (status, payload_publico, ms, emails_enviados).
    """
    h = _Handler()
    enviados = []
    orig_conn, orig_smtp = R.get_connection, R.send_recovery_email_smtp
    R.get_connection = lambda: conn
    R.send_recovery_email_smtp = smtp or (lambda *a, **k: enviados.append(a))
    t0 = time.perf_counter()
    try:
        fn(h, type('P', (), {'path': '/api/x'})(), payload, None)
    except PermissionError as e:
        h.status, h.corpo = 403, {'error': str(e)}
    except ValueError as e:
        h.status, h.corpo = 400, {'error': str(e)}
    finally:
        # O relógio para AQUI, antes de esperar a thread. O que o solicitante
        # mede é a linha da resposta; somar o trabalho de segundo plano
        # mediria justamente o que saiu de lá — e o gate de tempo acusaria uma
        # diferença que o cliente não enxerga. Foi o que aconteceu na primeira
        # rodada depois da correção.
        ms = (time.perf_counter() - t0) * 1000
        # Esperar ANTES de restaurar: a thread ainda precisa dos dublês.
        _aguardar_envio_em_segundo_plano()
        R.get_connection, R.send_recovery_email_smtp = orig_conn, orig_smtp
    return h.status, h.corpo, ms, enviados


def _aguardar_envio_em_segundo_plano():
    """O envio pode sair da linha da resposta. O gate precisa esperá-lo para
    poder afirmar que o e-mail SAIU (ou não saiu) — senão mediria só a corrida."""
    import threading
    for t in threading.enumerate():
        if t.name.startswith('recovery_email') and t.is_alive():
            t.join(timeout=5)


# ── A: POST /api/auth/request-email-recovery ────────────────────────────────

def _pedir_email(conn, usuario='ana.silva', smtp=None):
    return _chamar(R.handle_post_request_email_recovery, {'username': usuario}, conn, smtp)


def test_a_resposta_publica_e_a_mesma_exista_ou_nao():
    existe = _pedir_email(_Conn(True, EMAIL))
    ausente = _pedir_email(_Conn(False), 'nao.existe')
    sem_email = _pedir_email(_Conn(True, None))
    assert existe[0] == ausente[0] == sem_email[0], (
        f'o status separa os casos: {existe[0]} / {ausente[0]} / {sem_email[0]}')
    assert existe[1] == ausente[1] == sem_email[1], (
        'o payload público separa os casos:\n'
        f'  existe:      {existe[1]}\n  não existe:  {ausente[1]}\n  sem e-mail:  {sem_email[1]}')


def test_a_falha_de_smtp_nao_vira_confirmacao_de_existencia():
    """O canal mais direto. A falha de SMTP só acontece para usuário que existe
    E tem e-mail: entregá-la ao solicitante responde exatamente a pergunta que o
    endpoint não pode responder — e ainda expõe detalhe interno de infra."""
    def explode(*a, **k):
        raise RuntimeError('conexão SMTP recusada pelo relay interno')

    com_falha = _pedir_email(_Conn(True, EMAIL), smtp=explode)
    ausente = _pedir_email(_Conn(False), 'nao.existe')
    assert com_falha[0] == ausente[0], (
        f'falha de SMTP muda o status: {com_falha[0]} contra {ausente[0]}')
    assert com_falha[1] == ausente[1], (
        f'falha de SMTP muda o payload: {com_falha[1]}')
    assert 'SMTP' not in json.dumps(com_falha[1], ensure_ascii=False), (
        f'detalhe interno de infraestrutura vazou: {com_falha[1]}')


def test_a_email_so_sai_para_conta_existente_com_endereco():
    """O contrapeso: uniformizar a resposta não pode virar "manda e-mail para
    todo mundo". Sem este gate, "não vaza" seria satisfeito por um endpoint que
    dispara mensagem para endereço de terceiro."""
    assert _pedir_email(_Conn(True, EMAIL))[3], 'o e-mail deixou de sair para quem tem conta'
    assert not _pedir_email(_Conn(False), 'nao.existe')[3], 'e-mail disparado para conta inexistente'
    assert not _pedir_email(_Conn(True, None))[3], 'e-mail disparado para conta sem endereço'


def test_a_campo_ausente_continua_sendo_validacao_estrutural():
    status, corpo, _, enviados = _chamar(R.handle_post_request_email_recovery, {}, _Conn(True, EMAIL))
    assert status == 400 and 'obrigat' in json.dumps(corpo, ensure_ascii=False).lower(), (
        f'campo ausente deixou de ser validação estrutural: {status} {corpo}')
    assert not enviados


# ── B: POST /api/recover-password ───────────────────────────────────────────

def _redefinir(conn, usuario='ana.silva', chave='chave-errada'):
    return _chamar(R.handle_post_recover_password,
                   {'username': usuario, 'new_password': SENHA_NOVA, 'recovery_key': chave},
                   conn)


def _cenarios_de_falha_de_b():
    return {
        'B1 usuário não existe': _redefinir(_Conn(False), 'nao.existe'),
        'B2 sem token, chave global errada': _redefinir(_Conn(True, token_hash=None)),
        'B3 com token, chave errada': _redefinir(_Conn(True, token_hash=hash_password(TOKEN_BOM))),
        'B4 token expirado': _redefinir(_Conn(True, token_hash=hash_password(TOKEN_BOM),
                                              expira='2020-01-01T00:00:00+00:00')),
    }


def test_b_nenhum_campo_publico_distingue_as_falhas():
    """O gate central de B. Compara status E payload de todos os cenários."""
    cenarios = _cenarios_de_falha_de_b()
    status = {nome: v[0] for nome, v in cenarios.items()}
    corpos = {nome: v[1] for nome, v in cenarios.items()}
    assert len(set(status.values())) == 1, f'o status separa os casos: {status}'
    distintos = {json.dumps(c, ensure_ascii=False, sort_keys=True) for c in corpos.values()}
    assert len(distintos) == 1, (
        'o payload público separa os casos:\n' +
        '\n'.join(f'  {n}: {c}' for n, c in corpos.items()))


def test_b_a_mensagem_nao_nomeia_a_causa():
    _, corpo, _, _ = _redefinir(_Conn(False), 'nao.existe')
    texto = json.dumps(corpo, ensure_ascii=False)
    for revelador in ('não encontrado', 'nao encontrado', 'expirada', 'inexistente'):
        assert revelador not in texto.lower(), f'a mensagem nomeia a causa: {corpo}'


def test_b_redefinicao_valida_continua_funcionando():
    """A metade que impede o falso verde: uniformizar tudo em erro passaria nos
    gates acima e deixaria o produto sem recuperação de senha."""
    R.PASSWORD_RECOVERY_KEY = 'CHAVE-GLOBAL-CORRETA'
    conn = _Conn(True, token_hash=None)
    status, corpo, _, _ = _redefinir(conn, chave='CHAVE-GLOBAL-CORRETA')
    assert status == 200, f'a redefinição legítima foi recusada: {status} {corpo}'
    assert conn.updates, 'a senha não chegou a ser gravada'


def test_b_campo_ausente_continua_sendo_validacao_estrutural():
    status, corpo, _, _ = _chamar(R.handle_post_recover_password, {'username': 'ana.silva'}, _Conn(True))
    assert status == 400 and 'obrigat' in json.dumps(corpo, ensure_ascii=False).lower(), (
        f'campo ausente deixou de ser validação estrutural: {status} {corpo}')


# ── Timing ───────────────────────────────────────────────────────────────────

def _contando_bcrypt(fn):
    """Conta invocações de bcrypt NA LINHA DA RESPOSTA. Determinístico —
    cronômetro em CI é instável, e o que importa é se o trabalho é equivalente.

    O contador é lido antes de a thread de segundo plano ser esperada: o que
    ela gasta não é observável pelo solicitante e não entra na conta.
    """
    import threading
    S._hash_ficticio()  # aquece: a primeira chamada gera o hash e contaria a mais
    principal = threading.main_thread()
    chamadas = []

    def _marcar(rotulo):
        # Só a thread principal conta. A de segundo plano roda em paralelo e o
        # contador a via por corrida — foi assim que este gate acusou um bcrypt
        # que o solicitante não paga.
        if threading.current_thread() is principal:
            chamadas.append(rotulo)

    orig = {'S.hash': S.hash_password, 'S.verify': S.verify_password,
            'R.hash': R.hash_password, 'R.verify': R.verify_password}
    S.hash_password = R.hash_password = lambda p: (_marcar('hash'), orig['S.hash'](p))[1]
    S.verify_password = R.verify_password = lambda a, b: (_marcar('verify'), orig['S.verify'](a, b))[1]
    try:
        fn()
        na_resposta = list(chamadas)
    finally:
        S.hash_password, S.verify_password = orig['S.hash'], orig['S.verify']
        R.hash_password, R.verify_password = orig['R.hash'], orig['R.verify']
    return na_resposta


def test_a_nenhum_caminho_paga_bcrypt_na_linha_da_resposta():
    """O `bcrypt` da geração do token saiu da linha da resposta.

    A primeira versão deste gate perguntava se os dois caminhos pagavam o MESMO
    número de operações, o que admitiria igualar por cima — pagar um `bcrypt`
    também para quem não existe. Isso fecharia o tempo e encareceria toda
    requisição num endpoint sem limitador. O contrato é mais forte: nenhum dos
    dois paga, porque o trabalho saiu de lá.
    """
    com = _contando_bcrypt(lambda: _pedir_email(_Conn(True, EMAIL)))
    sem = _contando_bcrypt(lambda: _pedir_email(_Conn(False), 'nao.existe'))
    assert not com and not sem, (
        f'ainda há bcrypt na linha da resposta: existe={com} / não existe={sem}')


def test_b_todas_as_falhas_pagam_o_mesmo_trabalho():
    custos = {
        'B1 não existe': _contando_bcrypt(lambda: _redefinir(_Conn(False), 'nao.existe')),
        'B2 sem token': _contando_bcrypt(lambda: _redefinir(_Conn(True, token_hash=None))),
        'B3 com token': _contando_bcrypt(lambda: _redefinir(_Conn(True, token_hash=hash_password(TOKEN_BOM)))),
    }
    tamanhos = {n: len(c) for n, c in custos.items()}
    assert len(set(tamanhos.values())) == 1, (
        f'as falhas custam trabalho diferente e se separam por tempo: {tamanhos}')


def test_o_tempo_medido_de_a_nao_separa_os_caminhos():
    """Confirmação empírica. Faixa larga: antes era 5207×."""
    def med(conn, usuario):
        return statistics.median([_pedir_email(conn, usuario)[2] for _ in range(5)])

    com = med(_Conn(True, EMAIL), 'ana.silva')
    sem = med(_Conn(False), 'nao.existe')
    razao = max(com, sem) / max(min(com, sem), 1e-9)
    assert razao < 3.0, (
        f'os caminhos se separam por tempo: {razao:.1f}× '
        f'(existe {com:.1f} ms, não existe {sem:.1f} ms)')


# ── Estrutural ───────────────────────────────────────────────────────────────

def _fonte(rel, sem_comentarios=True):
    import pathlib
    raiz = pathlib.Path(__file__).resolve().parent.parent
    texto = (raiz / rel).read_text(encoding='utf-8')
    if not sem_comentarios:
        return texto
    return '\n'.join(l for l in texto.splitlines() if not l.lstrip().startswith('#'))


def _corpo_de(fonte, nome):
    linhas = fonte.splitlines()
    i = next(k for k, l in enumerate(linhas) if l.startswith(f'def {nome}('))
    fim = next((k for k in range(i + 1, len(linhas))
                if linhas[k] and not linhas[k][0].isspace()), len(linhas))
    return '\n'.join(linhas[i:fim])


def test_nenhuma_mensagem_reveladora_no_caminho_de_recuperacao():
    """Par estrutural dos gates comportamentais: pega as sabotagens α e β.

    ESCOPADO aos três donos da recuperação. O login foi fechado em frente
    própria e não é tocado aqui.
    """
    rotas = _fonte('modules/auth/routes.py')
    servico = _fonte('modules/auth/service.py')
    caminho = (
        _corpo_de(rotas, 'handle_post_recover_password')
        + _corpo_de(rotas, 'handle_post_request_email_recovery')
        + _corpo_de(servico, 'validate_and_clear_recovery_token')
    )
    for proibida in ('Usuário não encontrado', 'USER_NOT_FOUND',
                     'Chave de recuperação expirada', 'Falha ao enviar e-mail'):
        assert proibida not in caminho, (
            f'{proibida!r} voltou ao caminho de recuperação — ver Hardening do Recovery')
