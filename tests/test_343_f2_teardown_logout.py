"""#343 F2 — o encerramento de sessão elimina DOM e memória, não só esconde a tela.

## O achado

Cinco lugares encerravam sessão com o mesmo par:

    clearSession();
    showScreen(false);

`showScreen` (`static/js/modules/router.js`) apenas alterna a classe CSS
`active` entre a tela de login e a do app. Não remove nó, não limpa `innerHTML`,
não reseta campo. O DOM de quem saiu continuava montado.

E `clearSession` zera 9 das ~76 chaves de `state`. O bootstrap do usuário
seguinte sobrescreve outras 24. **As 44 restantes atravessavam a troca de
identidade** — entre elas `outsourcedCompanies`, `reports`, `reportArchiveItems`,
`commercialContract`, `signatureDraft`, `deliveryEpis`.

Não era só "o objeto continua na memória". Havia caminho de renderização:

    loadBootstrap()  termina em  renderAll()
    renderAll()      chama       renderOutsourcedCompanies()
    renderOutsourcedCompanies()  escreve state.outsourcedCompanies no innerHTML

O caso grave é o **bootstrap degradado**: com 502/503 a chamada a
`/api/bootstrap` falha, NENHUMA das 24 chaves é sobrescrita, e `renderAll()`
roda assim mesmo. O usuário B via os dados de A na própria tela.

## O contrato

    encerrar sessão elimina o DOM e a memória JS da sessão anterior
    e não depende de ninguém lembrar de listar chave nova

Por isso o mecanismo é `location.reload()` e não um teardown enumerado: 44
chaves e 72 containers HOJE, e a lista envelheceria na primeira chave nova.

## O que esta fatia NÃO faz

`localStorage` e `sessionStorage` de tema (`epi-theme`, F3) e do portal
(`employee_portal_cpf_last3_*`, F4) continuam exatamente como estavam. O gate 8
prova isso nos dois sentidos — a F2 não pode resolver F3/F4 de contrabando.

Nenhum teste usa credencial real.
"""

import pathlib
import re

import pytest

RAIZ = pathlib.Path(__file__).resolve().parent.parent
APP_JS = RAIZ / 'static' / 'app.js'
AUTH_JS = RAIZ / 'static' / 'js' / 'modules' / 'auth.js'
ROUTER_JS = RAIZ / 'static' / 'js' / 'modules' / 'router.js'


def _sem_comentarios(texto):
    """Os comentários citam o padrão antigo para explicar por que ele saiu."""
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


def _corpo_de(js_texto, nome):
    """Extrai o corpo de uma função por contagem de chaves."""
    marca = f'function {nome}('
    i = js_texto.index(marca)
    inicio = js_texto.index('{', i)
    prof, j = 0, inicio
    while j < len(js_texto):
        if js_texto[j] == '{':
            prof += 1
        elif js_texto[j] == '}':
            prof -= 1
            if prof == 0:
                return js_texto[inicio:j + 1]
        j += 1
    raise AssertionError(f'não consegui delimitar {nome}')


# ── 0. As duas categorias semânticas do contrato ─────────────────────────────
#
# O erro perigoso desta fatia seria a generalização "todo `clearSession()`
# recarrega". Ela resolveria o A→B e QUEBRARIA o login com 2FA. A classificação
# é por SEMÂNTICA — o que o caminho significa —, não por qual função ele chama.

# A: TERMINAÇÃO REAL DE SESSÃO — havia sessão, e ela acabou.
#    Estes DEVEM convergir para terminateSession().
TERMINACAO_REAL_DE_SESSAO = {
    'botão Sair': "getElementById('logout-btn')",
    'sessão revogada durante uso (401/403)': '[401, 403].includes(Number(error?.status',
    'sessão expirada': "isSessionRestoreAuthError(error)",
    'bootstrap/sessão inválida': "console.warn('[auth] bootstrap falhou, limpando sessão'",
    # A fronteira dentro do handleLogin: falha NÃO-degradada depois de
    # `saveSession`, quando já existe sessão gravada e `state` parcial.
    'falha após a sessão estabelecida': "post_login_bootstrap",
}

# B: AUTENTICAÇÃO EM ANDAMENTO — nenhuma sessão chegou a existir nesta página.
#    Estes NÃO PODEM chamar terminateSession() nem recarregar.
# A fronteira passa DENTRO do `handleLogin`, e o discriminador é `saveSession`:
# antes dele não há sessão (categoria B); depois há, e uma falha vira terminação
# real. Por isso a categoria B lista só o que é B por inteiro.
AUTENTICACAO_EM_ANDAMENTO = {
    'troca de senha obrigatória (sessão ATIVA)': 'handlePasswordChangeAfterLogin',
}


@pytest.mark.parametrize('caminho,marca', sorted(TERMINACAO_REAL_DE_SESSAO.items()))
def test_terminacao_real_converge_para_o_caminho_unico(js, caminho, marca):
    """Direção 1 do contrato: TERMINAÇÃO REAL → terminateSession().

    Não compara texto exato nem número de linha: a partir da marca do caminho,
    procura o PRÓXIMO desfecho — `terminateSession(` ou `showScreen(false)` — e
    exige que seja o primeiro. É o enunciado semântico, tolerante a reformatação.
    """
    assert marca in js, f'a marca do caminho "{caminho}" sumiu do código'
    resto = js[js.index(marca):]
    i_term = resto.find('terminateSession(')
    i_hide = resto.find('showScreen(false)')
    assert i_term != -1, f'"{caminho}" não converge para terminateSession()'
    assert i_hide == -1 or i_term < i_hide, (
        f'"{caminho}" volta a apenas esconder a tela: showScreen(false) aparece '
        'antes de terminateSession()')


@pytest.mark.parametrize('caminho,funcao', sorted(AUTENTICACAO_EM_ANDAMENTO.items()))
def test_autenticacao_em_andamento_nao_encerra_sessao(js, caminho, funcao):
    """Direção 2 do contrato: autenticação em andamento NÃO recarrega.

    É a metade que impede o falso verde perigoso — uma implementação que
    "resolve" A→B generalizando `clearSession()` → reload e, com isso, deixa o
    2FA impossível de concluir.
    """
    corpo = _corpo_de(js, funcao)
    assert 'terminateSession(' not in corpo,         f'"{caminho}" não é encerramento de sessão: recarregar ali destrói o fluxo'
    assert 'location.reload' not in corpo


def test_a_troca_de_senha_obrigatoria_continua_intacta(js):
    """O sexto `showScreen(false)`, o que prova que a categoria B é real.

    Aqui a sessão está ATIVA — `saveSession` já rodou — e só o formulário muda.
    Um gate que banisse `showScreen(false)` cegamente teria quebrado este fluxo,
    e é exatamente ele que separa "esconder a tela" de "encerrar sessão".
    """
    corpo = _corpo_de(js, 'handlePasswordChangeAfterLogin')
    assert 'showScreen(false)' in corpo, 'o fluxo de troca de senha foi quebrado'
    assert "changeForm.style.display = 'grid'" in corpo
    assert "loginForm.style.display = 'none'" in corpo
    assert 'clearSession()' not in corpo,         'a sessão está ativa aqui; limpá-la expulsaria quem precisa trocar a senha'


def test_o_campo_de_totp_sobrevive_a_falha_de_login(js):
    """A prova de que o 2FA continua possível.

    `TOTP_REQUIRED`/`TOTP_INVALID` revelam o campo e o focam. Uma recarga o
    esconderia de novo e esvaziaria o input: o usuário nunca conseguiria
    fornecer o código.
    """
    corpo = _corpo_de(js, 'handleLogin')
    assert "totpRow.style.display = ''" in corpo, 'o campo de TOTP deixou de ser revelado'
    assert "getElementById('login-totp')?.focus()" in corpo
    for codigo in ("'TOTP_REQUIRED'", "'TOTP_INVALID'"):
        assert codigo in corpo
    # E o desfecho desse bloco continua sendo a tela de login, não a recarga.
    depois = corpo[corpo.index("totpRow.style.display = ''"):]
    assert 'terminateSession(' not in depois and 'location.reload' not in depois


# ── 0b. A fronteira passa dentro do handleLogin ──────────────────────────────
#
# Achado da revisão, e era erro do contrato, não só do código: `saveSession`
# roda ANTES do `loadBootstrap`. Uma falha não-degradada depois dela deixava
# sessão gravada, `state` parcialmente preenchido e DOM montado — encerrados
# com o mecanismo antigo, que só escondia a tela.

def test_falha_apos_a_sessao_estabelecida_e_terminacao_real(js):
    corpo = _corpo_de(js, 'handleLogin')
    assert 'if (sessaoEstabelecidaNestaTentativa) {' in corpo, \
        'sem o discriminador, o sub-caminho pós-saveSession volta a só esconder'
    i_guard = corpo.index('if (sessaoEstabelecidaNestaTentativa) {')
    i_term = corpo.index('terminateSession(')
    i_clear = corpo.index('clearSession();')
    assert i_guard < i_term < i_clear, (
        'a terminação real precisa vir sob o guard e ANTES do ramo sem sessão')


def test_o_discriminador_e_o_save_session(js):
    """A premissa: se `saveSession` passasse a rodar depois do bootstrap, a
    fronteira mudaria de lugar e este contrato precisaria ser refeito."""
    corpo = _corpo_de(js, 'handleLogin')
    assert corpo.index('saveSession(') < corpo.index('await loadBootstrap();')


def test_a_falha_de_autenticacao_continua_sem_recarregar(js):
    """A outra metade: no ramo SEM sessão nada recarrega — é o que mantém o
    2FA possível."""
    corpo = _corpo_de(js, 'handleLogin')
    ramo_sem_sessao = corpo[corpo.index('clearSession();'):]
    assert 'terminateSession(' not in ramo_sem_sessao
    assert 'location.reload' not in ramo_sem_sessao
    assert "totpRow.style.display = ''" in ramo_sem_sessao


# ── 10d. A limpeza de rascunho não depende de storage ────────────────────────
#
# Achado da revisão: num ambiente onde `sessionStorage` lança — privacidade
# restritiva, embedding com storage desligado — o sinal não é gravado, o leitor
# sai cedo, e a limpeza de formulário simplesmente não acontecia. Justo o
# ambiente em que o vazamento importa.

def test_o_encerramento_limpa_rascunho_sem_depender_de_storage(js):
    corpo = _corpo_de(js, 'terminateSession')
    assert 'resetAppFormDrafts();' in corpo, \
        'sem a limpeza síncrona, um ambiente sem storage fica desprotegido'
    # Fora de qualquer try de storage: é o ponto do gate.
    antes_do_storage = corpo[:corpo.index('sessionStorage')]
    assert 'resetAppFormDrafts();' in antes_do_storage


def test_a_limpeza_na_carga_seguinte_e_reforco_e_nao_a_garantia(js):
    """As duas existem: a síncrona não depende de storage; a da carga seguinte
    cobre o caso de o navegador restaurar mesmo assim."""
    assert len(re.findall(r'(?<!function )\bresetAppFormDrafts\(', js)) == 2
    assert 'resetAppFormDrafts();' in _corpo_de(js, 'clearRestoredAppForms')


# ── 1. Inventário: todo encerramento passa pelo caminho único ────────────────

# Único lugar que chama `clearSession()` sem ser encerramento, com a razão.
# Não é isenção de conveniência: recarregar ali quebra o login com 2FA.
CLEAR_SESSION_NAO_ENCERRAMENTO = 1


def test_o_caminho_unico_de_encerramento_existe(js):
    assert js.count('function terminateSession(') == 1, \
        'o encerramento precisa ter UM caminho, não um por call site'
    assert 'function consumePendingSessionMessage(' in js


def test_todo_encerramento_de_sessao_passa_pelo_caminho_unico(js):
    """Gate de INVENTÁRIO: vale para os caminhos de hoje e para os de amanhã.

    Fixar cinco números de linha protegeria cinco linhas. Contar as chamadas a
    `clearSession()` faz um SEXTO caminho novo nascer reprovado até convergir.
    """
    chamadas = len(re.findall(r'\bclearSession\(\)', js))
    # 1 dentro de terminateSession + a exceção documentada do login com 2FA.
    assert chamadas == 1 + CLEAR_SESSION_NAO_ENCERRAMENTO, (
        f'{chamadas} chamadas a clearSession(): apareceu um caminho de '
        'encerramento que não passa por terminateSession()')
    assert 'clearSession();' in _corpo_de(js, 'terminateSession')


def test_os_quatro_encerramentos_conhecidos_continuam_convergindo(js):
    """Contraprova do inventário: se os call sites SUMIREM, o gate acima ficaria
    verde por vacuidade."""
    assert len(re.findall(r'(?<!function )\bterminateSession\(', js)) == 5, (
        'os cinco encerramentos (botão, 401/403, sessão expirada, bootstrap e a '
        'falha pós-saveSession) precisam continuar chamando o caminho único')


# ── 2. Nenhum encerramento apenas esconde a tela ─────────────────────────────

# `showScreen(false)` legítimo, sem encerrar sessão nenhuma:
#   - troca de senha obrigatória: a sessão está ATIVA, só o formulário muda;
#   - init(): estado inicial antes de tentar restaurar;
#   - falha de login: nunca houve sessão nesta página (ver gate 1).
SHOW_SCREEN_FALSE_LEGITIMOS = 3


def test_nenhum_encerramento_termina_em_show_screen_puro(js):
    ocorrencias = len(re.findall(r'showScreen\(false\)', js))
    assert ocorrencias == SHOW_SCREEN_FALSE_LEGITIMOS, (
        f'{ocorrencias} usos de showScreen(false): ou voltou um encerramento '
        'que só esconde a UI, ou um uso legítimo sumiu')
    assert 'showScreen(false)' not in _corpo_de(js, 'terminateSession'), \
        'o encerramento não pode se contentar em trocar a classe CSS'


def test_show_screen_continua_sendo_so_troca_de_classe():
    """A premissa do achado: se `showScreen` passasse a desmontar o DOM, o
    raciocínio desta fatia mudaria — e o gate precisa perceber."""
    router = _sem_comentarios(ROUTER_JS.read_text(encoding='utf-8'))
    corpo = _corpo_de(router, 'showScreen')
    assert 'classList.toggle' in corpo
    assert 'innerHTML' not in corpo and 'remove()' not in corpo


# ── 3. Chave nova de `state` não invalida a garantia ─────────────────────────

def test_a_garantia_e_a_recarga_e_nao_uma_lista_enumerada(js):
    """O ponto da estratégia A.

    Um teardown enumerado envelhece: a chave nº 77 nasce vazando e ninguém
    percebe. A recarga não depende de lista, então este gate protege o
    MECANISMO — trocar a recarga por enumeração fica vermelho.
    """
    corpo = _corpo_de(js, 'terminateSession')
    assert 'location.reload()' in corpo, \
        'sem a recarga, DOM e memória da sessão anterior sobrevivem'
    assert 'state.' not in corpo, (
        'terminateSession não pode enumerar chaves de state: é exatamente a '
        'lista que envelhece e volta a vazar')


def test_a_url_nao_carrega_a_navegacao_do_usuario_anterior(js):
    """`?view=` guarda a última tela de quem saiu.

    `location.reload()` recarrega a URL ATUAL — se `view` continuar lá, o
    próximo login herda a navegação do anterior, e a recarga não desfaz isso.
    """
    corpo = _corpo_de(js, 'terminateSession')
    assert "searchParams.delete('view')" in corpo, \
        'sem isso, B chega na última tela que A estava vendo'
    assert 'replaceState' in corpo, 'a URL precisa ser trocada ANTES da recarga'
    assert corpo.index("searchParams.delete('view')") < corpo.index('location.reload()')


def test_a_limpeza_da_url_nao_e_generica(js):
    """Só `view` sai.

    Remoção genérica exigiria um inventário de parâmetros que esta fatia não
    fez — e apagaria coisa legítima, como o `employee_token` de um link de
    portal, que tem dono e ciclo de vida próprios (F4).
    """
    corpo = _corpo_de(js, 'terminateSession')
    assert corpo.count('searchParams.delete') == 1
    for generico in ('url.search = ', 'searchParams.forEach', 'new URLSearchParams()'):
        assert generico not in corpo, f'`{generico}` apaga parâmetro sem inventário'


def test_clear_session_continua_primitiva_de_sessao():
    """Responsabilidades separadas: `auth.js` não conhece câmera, URL nem
    documento. Misturar criaria acoplamento — `auth.js` carrega ANTES de
    `app.js` e não referencia nada dele."""
    auth = _sem_comentarios(AUTH_JS.read_text(encoding='utf-8'))
    for proibido in ('location.reload', 'stopDeliveryQrCamera', 'searchParams'):
        assert proibido not in auth, \
            f'`{proibido}` não pertence à primitiva de sessão'


# ── 4. Caches de negócio de A não sobrevivem ao ciclo ────────────────────────

# As 15 chaves de maior gravidade da matriz da auditoria: dados de negócio do
# usuário anterior que `clearSession` não zera e `loadBootstrap` não sobrescreve.
CACHES_DE_NEGOCIO = (
    'reports', 'reportArchiveItems', 'commercialContract', 'commercialClauseTemplate',
    'signatureDraft', 'outsourcedCompanies', 'outsourcedCompaniesAvailable',
    'outsourcedCompanyUpdateRequests', 'outsourcedEmployeesSummary', 'archivedUnits',
    'deliveryEpis', 'deliveryReturnCandidates', 'stockGeneratedLabels',
    'stockEpiMovementItems', 'fichaRetentionPolicy',
)


def test_a_recarga_e_o_que_elimina_os_caches_de_negocio(js):
    """Prova que a recarga é load-bearing, não decorativa.

    `outsourcedCompanies` é o caso canônico: renderizado por `renderAll()` e
    NUNCA escrito por `loadBootstrap` — o próprio código documenta que o módulo
    é opt-in e a lista só é buscada ao abrir a tela. Sem a recarga, o vazamento
    volta na hora.
    """
    corpo_boot = _corpo_de(js, 'loadBootstrap')
    assert 'state.outsourcedCompanies =' not in corpo_boot, (
        'premissa do gate: se o bootstrap passasse a sobrescrever esta chave, '
        'o raciocínio da fatia mudaria e o gate precisa ser revisto')
    assert 'renderOutsourcedCompanies()' in _corpo_de(js, 'renderAll'), \
        'premissa do gate: é renderAll que leva o cache antigo até o innerHTML'
    assert 'location.reload()' in _corpo_de(js, 'terminateSession')


@pytest.mark.parametrize('chave', CACHES_DE_NEGOCIO)
def test_nenhum_cache_de_negocio_e_limpo_a_mao(js, chave):
    """Contraprova: se alguém começar a zerar estas chaves à mão dentro do
    encerramento, voltamos ao teardown enumerado que a fatia rejeitou."""
    assert f'state.{chave}' not in _corpo_de(js, 'terminateSession')


# ── 5. Mensagem sobrevive exatamente uma vez ─────────────────────────────────

def test_a_mensagem_atravessa_a_recarga(js):
    corpo = _corpo_de(js, 'terminateSession')
    assert 'sessionStorage.setItem(SESSION_END_MESSAGE_KEY' in corpo, \
        'sem isso, "Sessão expirada" some na recarga e o usuário fica sem explicação'


def test_a_mensagem_e_de_uso_unico(js):
    corpo = _corpo_de(js, 'consumePendingSessionMessage')
    assert 'sessionStorage.getItem(SESSION_END_MESSAGE_KEY' in corpo
    assert 'sessionStorage.removeItem(SESSION_END_MESSAGE_KEY' in corpo, \
        'sem o remove, o aviso reaparece em todo login seguinte'
    # Apagar ANTES de exibir: uso único de verdade, mesmo se o render falhar.
    assert corpo.index('removeItem') < corpo.index('setLoginMessage')
    assert '  consumePendingSessionMessage();' in js, 'ninguém lê a mensagem'


# Toda terminação real que NÃO é voluntária precisa dizer ao usuário o que
# houve. O botão "Sair" é a exceção deliberada: quem clicou já sabe.
MENSAGENS_DE_ENCERRAMENTO = {
    'sessão revogada durante uso (401/403)':
        'Sua sessão foi encerrada. Faça login novamente para continuar.',
    'sessão expirada':
        'Sessão expirada. Faça login novamente.',
    'bootstrap/sessão inválida':
        'Não foi possível restaurar sua sessão automaticamente. Faça login para continuar.',
}


@pytest.mark.parametrize('caminho,texto', sorted(MENSAGENS_DE_ENCERRAMENTO.items()))
def test_cada_encerramento_involuntario_avisa_pelo_mecanismo_one_shot(js, caminho, texto):
    """A mensagem tem de ir POR `terminateSession`, não por `setLoginMessage`.

    `setLoginMessage` escreve no DOM — e o DOM morre na recarga. Só o mecanismo
    de uso único atravessa.
    """
    assert f"terminateSession('{texto}')" in js, (
        f'"{caminho}" perdeu o aviso, ou passou a exibi-lo por um caminho que '
        'não sobrevive à recarga')


def test_a_saida_voluntaria_continua_sem_mensagem(js):
    """Contraprova: quem clicou em "Sair" já sabe o que houve. Um aviso ali
    seria ruído, e o gate impede que a regra vire "sempre avisa"."""
    i = js.index("getElementById('logout-btn')")
    trecho = js[i:i + 200]
    assert 'terminateSession()' in trecho, 'a saída voluntária não leva mensagem'


def test_o_aviso_do_caminho_2_nao_afirma_causa_que_nao_pode_provar(js):
    """401/403 durante o uso não prova expiração: pode ser revogação, troca de
    senha em outro dispositivo ou permissão retirada. O texto é neutro de
    propósito, e o gate impede que alguém o "melhore" para uma causa falsa."""
    aviso = MENSAGENS_DE_ENCERRAMENTO['sessão revogada durante uso (401/403)']
    i = js.index('[401, 403].includes(Number(error?.status')
    trecho = js[i:i + 400]
    assert f"terminateSession('{aviso}')" in trecho
    assert 'expirada' not in aviso.lower()
    assert 'expirou' not in aviso.lower()


def test_a_mensagem_nao_reaparece_em_recarga_seguinte(js):
    """Uso único de verdade.

    `consumePendingSessionMessage` apaga a chave ANTES de exibi-la, então uma
    segunda recarga não encontra nada. E só `terminateSession` escreve nela —
    se houvesse outro escritor, o aviso poderia ressuscitar sozinho.
    """
    corpo = _corpo_de(js, 'consumePendingSessionMessage')
    assert corpo.index('removeItem') < corpo.index('setLoginMessage')
    escritores = js.count(f'sessionStorage.setItem(SESSION_END_MESSAGE_KEY')
    assert escritores == 1, (
        f'{escritores} escritores da chave one-shot: só o encerramento pode '
        'gravá-la, senão o aviso reaparece sem encerramento nenhum')
    consumidores = len(re.findall(r'(?<!function )\bconsumePendingSessionMessage\(', js))
    assert consumidores == 1, (
        f'{consumidores} chamadas a consumePendingSessionMessage(): a mensagem '
        'é consumida em um lugar só — o init()')


@pytest.mark.parametrize('funcao', ['handleLogin', 'handlePasswordChangeAfterLogin'])
def test_o_aviso_nao_interfere_na_autenticacao_em_andamento(js, funcao):
    """Categoria B não toca no mecanismo one-shot: nem grava, nem consome, nem
    é interrompida por ele. O TOTP e a troca de senha seguem intactos."""
    corpo = _corpo_de(js, funcao)
    assert 'SESSION_END_MESSAGE_KEY' not in corpo
    assert 'consumePendingSessionMessage' not in corpo


def test_as_duas_mensagens_de_sessao_continuam_existindo(js):
    for texto in ('Sessão expirada. Faça login novamente.',
                  'Não foi possível restaurar sua sessão automaticamente.'):
        assert texto in js, f'a mensagem "{texto[:30]}…" foi perdida na conversão'


def test_a_chave_one_shot_nao_guarda_nada_sensivel(js):
    """Só texto de aviso: nunca identificador, token ou dado de sessão."""
    corpo = _corpo_de(js, 'terminateSession')
    for proibido in ('state.user', 'state.token', 'username', 'password', 'token'):
        assert f'{proibido}' not in corpo.split('sessionStorage.setItem')[1].split(')')[0]


# ── 6. Login normal e fail-closed por permissão intactos ─────────────────────

def test_o_login_normal_continua_buscando_antes_de_mostrar(js):
    corpo = _corpo_de(js, 'handleLogin')
    assert 'await loadBootstrap();' in corpo, \
        'sem o await, a tela aparece antes dos dados — o furo que a fatia fecha'
    assert corpo.index('await loadBootstrap();') < corpo.index('showScreen(true);')


def test_o_login_com_2fa_continua_possivel(js):
    """Por que o caminho de falha de login NÃO recarrega.

    Ele revela o campo de TOTP e foca nele. Uma recarga esconderia o campo de
    novo e deixaria o login com 2FA impossível de concluir.
    """
    corpo = _corpo_de(js, 'handleLogin')
    assert "TOTP_REQUIRED" in corpo and "TOTP_INVALID" in corpo
    assert "totpRow.style.display = ''" in corpo
    # O `terminateSession` do `handleLogin` é do sub-caminho pós-`saveSession`.
    # O bloco do TOTP fica DEPOIS dele, no ramo sem sessão — se a recarga
    # passasse a alcançá-lo, o campo de código sumiria e o 2FA morreria.
    assert corpo.index('terminateSession(') < corpo.index("totpRow.style.display = ''")
    assert 'location.reload' not in corpo


@pytest.mark.parametrize('chave', ['lowStock', 'stockEpis', 'requests', 'fichasPeriods'])
def test_o_fail_closed_por_permissao_sobrevive(js, chave):
    """Sem a permissão, o bootstrap zera o cache. É o comportamento correto de
    hoje e a F2 não pode quebrá-lo."""
    corpo = _corpo_de(js, 'loadBootstrap')
    assert re.search(rf'state\.{chave}\s*=\s*\[\]', corpo), \
        f'`{chave}` deixou de ser zerada para quem não tem a permissão'


# ── 7. Câmera QR encerrada em todos os caminhos ──────────────────────────────

def test_a_camera_desliga_em_todo_encerramento(js):
    """Antes, só o botão de Sair a desligava: um 401/403 ou uma falha de
    bootstrap deixavam o stream ativo com a sessão já morta."""
    assert 'stopDeliveryQrCamera()' in _corpo_de(js, 'terminateSession')
    # E fora do caminho único ela não é chamada em encerramento nenhum — se
    # fosse, haveria caminho de saída que não passa pelo orquestrador.
    corpo_logout = js[js.index("getElementById('logout-btn')"):][:220]
    assert 'clearSession()' not in corpo_logout


# ── 8. F3 e F4 permanecem intocadas ──────────────────────────────────────────

def test_a_f2_nao_toca_no_tema(js):
    """F3 é frente separada. `location.reload()` não limpa `localStorage`, e o
    encerramento não pode limpá-lo por fora."""
    corpo = _corpo_de(js, 'terminateSession')
    assert 'epi-theme' not in corpo
    assert 'localStorage' not in corpo
    assert "localStorage.setItem('epi-theme'" in js, \
        'o tema por dispositivo continua existindo: F3 não foi resolvida aqui'


def test_a_f2_nao_toca_no_cpf_do_portal(js):
    """F4 é frente separada."""
    corpo = _corpo_de(js, 'terminateSession')
    assert 'employee_portal_cpf_last3' not in corpo
    assert 'portalCpfStorageKey' not in corpo
    assert 'clear()' not in corpo, \
        'sessionStorage.clear() apagaria o cache do portal e invadiria a F4'


def test_o_encerramento_so_mexe_nas_proprias_chaves(js):
    """Três chaves, todas da F2 — o aviso de uso único, a marca de escopo dos
    snapshots e o sinal de limpeza de rascunho. Nenhuma de F3 ou F4."""
    # O encerramento toca duas chaves diretamente e delega a terceira ao
    # `rotateSnapshotScope` — as três são da F2, nenhuma é de F3 ou F4.
    corpo = _corpo_de(js, 'terminateSession')
    rotacao = _corpo_de(js, 'rotateSnapshotScope')
    chaves = sorted(set(re.findall(r'sessionStorage\.\w+\((\w+)', corpo + rotacao)))
    assert chaves == ['SESSION_END_MESSAGE_KEY', 'SESSION_TEARDOWN_KEY',
                      'SNAPSHOT_SCOPE_KEY'], f'chaves inesperadas: {chaves}'
    assert 'localStorage' not in corpo and 'localStorage' not in rotacao


# ── 10. Histórico SPA: o snapshot não atravessa identidade ───────────────────
#
# Achado da revisão automatizada, confirmado contra o código. `terminateSession`
# recarrega e troca a entrada ATIVA do histórico, mas as entradas anteriores —
# criadas por `history.pushState(collectInteractiveSnapshot(view), …)` — ficam
# na aba com os filtros de quem saiu. Um "Voltar" depois do login seguinte
# devolveria `employeesFilters`/`employeesOpsFilters`/`episFilters` do usuário
# anterior, com busca em texto livre e `company_id`/`unit_id`, para dentro do
# `state` do atual.

def test_o_snapshot_de_navegacao_carimba_o_documento_de_origem(js):
    corpo = _corpo_de(js, 'collectInteractiveSnapshot')
    assert corpo.count('sid: snapshotScopeId()') == 2, (
        'os DOIS retornos precisam carimbar: o com filtros e o do atalho, '
        'senão um deles vira snapshot sem origem')
    assert 'const DOCUMENT_INSTANCE_ID' in js


def test_o_snapshot_de_outro_documento_e_descartado(js):
    """A metade que fecha o furo: carimbar sem conferir não protege nada."""
    corpo = _corpo_de(js, 'restoreInteractiveSnapshot')
    assert 'snapshot.sid !== snapshotScopeId()' in corpo, \
        'sem a conferência, o filtro do usuário anterior volta pelo botão Voltar'
    # A rejeição vem ANTES de qualquer escrita em `state`.
    assert corpo.index('snapshot.sid !== snapshotScopeId()') < corpo.index('state.employeesFilters')


def test_o_carimbo_muda_a_cada_carga_do_documento(js):
    """É o que faz o encerramento invalidar os snapshots antigos: ele recarrega,
    a página gera outro identificador, e nada de antes casa."""
    i = js.index('const DOCUMENT_INSTANCE_ID')
    bloco = js[i:i + 600]
    # Web Crypto, não `Math.random()`: é a API correta para identificador único
    # no navegador, e um PRNG fraco aqui seria lido como credencial.
    assert 'crypto' in bloco and 'Math.random()' not in bloco
    assert js.count('const DOCUMENT_INSTANCE_ID') == 1, \
        'dois identificadores fariam snapshots casarem por acidente'


def test_a_navegacao_por_voltar_continua_funcionando(js):
    """Contraprova: descartar o snapshot não pode quebrar o botão Voltar. A
    view continua sendo resolvida e exibida; só o estado carimbado é ignorado.

    A ORDEM foi invertida na #343 F5-B, de propósito. Antes o snapshot era
    aplicado antes do `showView`; agora entra depois. A razão é que a F5-B
    passou a devolver abas e filtros ao estado inicial na ENTRADA do módulo —
    e `showView` é quem dispara essa entrada. Na ordem antiga, o reset rodaria
    depois da restauração e apagaria justamente o estado que o usuário pediu
    de volta no Voltar.

    A propriedade que este gate protege continua idêntica: as duas chamadas
    existem no handler de `popstate`, então o Voltar navega E reaplica o
    snapshot carimbado. O que mudou foi qual das duas vem primeiro.
    """
    i = js.index("safeOn(globalThis, 'popstate'")
    trecho = js[i:i + 900]
    assert 'restoreInteractiveSnapshot(event?.state)' in trecho
    assert 'showView(nextView' in trecho
    assert trecho.index('showView(nextView') < trecho.index('restoreInteractiveSnapshot(event?.state)'), \
        'o snapshot voltou a ser aplicado antes da entrada no módulo (ver #343 F5-B)' 


# ── 10b. O escopo é a SESSÃO, não a carga do documento ───────────────────────
#
# Segunda rodada da revisão: carimbar por documento invalidaria os snapshots
# também num F5 do mesmo usuário — e restaurar filtro e rolagem ao voltar
# depois de um refresh é comportamento existente da SPA. A F2 não pode
# quebrá-lo por tabela.

def test_a_marca_de_escopo_sobrevive_a_um_refresh_do_mesmo_usuario(js):
    corpo = _corpo_de(js, 'snapshotScopeId')
    assert 'sessionStorage.getItem(SNAPSHOT_SCOPE_KEY)' in corpo, \
        'sem persistir a marca, um F5 comum perde a restauração ao voltar'
    assert 'sessionStorage.setItem(SNAPSHOT_SCOPE_KEY' in corpo


def test_a_troca_de_principal_invalida_os_snapshots(js):
    """Não basta o encerramento: há troca de principal SEM encerramento.

    A logado, backend cai, F5; o `init()` mantém `state.user` de A e oferece
    login manual; B entra com sucesso e nenhum `terminateSession` aconteceu. O
    `sessionStorage` sobreviveu ao F5, e as entradas de histórico de A
    continuariam casando com o escopo.
    """
    # Um mecanismo só, chamado nos DOIS pontos.
    assert js.count('removeItem(SNAPSHOT_SCOPE_KEY)') == 1, \
        'a rotação precisa ficar num lugar só, senão as duas cópias divergem'
    assert 'removeItem(SNAPSHOT_SCOPE_KEY)' in _corpo_de(js, 'rotateSnapshotScope')
    assert 'rotateSnapshotScope();' in _corpo_de(js, 'terminateSession')
    assert 'rotateSnapshotScope();' in _corpo_de(js, 'handleLogin')


def test_a_rotacao_derruba_tambem_o_cache_em_memoria(js):
    """No login não há recarga para zerar o cache do módulo. Sem isso, o valor
    antigo continuaria valendo dentro do mesmo documento."""
    corpo = _corpo_de(js, 'rotateSnapshotScope')
    assert '_escopoDeSnapshot = null;' in corpo
    assert corpo.index('_escopoDeSnapshot = null;') < corpo.index('removeItem')


def test_a_rotacao_no_login_vem_depois_do_save_session(js):
    """Rotacionar antes seria inócuo: o escopo seria recriado pelo próprio
    snapshot seguinte, ainda com o principal antigo em cena."""
    corpo = _corpo_de(js, 'handleLogin')
    assert corpo.index('saveSession(') < corpo.index('rotateSnapshotScope();')


def test_sem_storage_o_escopo_falha_fechado(js):
    """Sem `sessionStorage` perde-se a restauração no F5 — mas nunca se aceita
    snapshot anterior ao encerramento. O lado seguro é o padrão."""
    corpo = _corpo_de(js, 'snapshotScopeId')
    assert 'catch' in corpo and 'DOCUMENT_INSTANCE_ID' in corpo.split('catch')[1]


# ── 10c. A recarga NÃO limpa campo: o navegador restaura ─────────────────────
#
# Achado da revisão que atingiu a premissa central da fatia. `location.reload()`
# preserva valores de controle de formulário — é por isso que um F5 mantém o que
# você digitou. Depois de um encerramento, esse rascunho é de quem saiu:
# `#employee-form` tem CPF, nome, e-mail e WhatsApp de um colaborador.

def test_o_encerramento_sinaliza_a_limpeza_de_rascunhos(js):
    corpo = _corpo_de(js, 'terminateSession')
    assert "sessionStorage.setItem(SESSION_TEARDOWN_KEY, '1')" in corpo


def test_a_carga_seguinte_limpa_os_rascunhos_restaurados(js):
    corpo = _corpo_de(js, 'clearRestoredAppForms')
    assert 'sessionStorage.getItem(SESSION_TEARDOWN_KEY)' in corpo
    assert 'sessionStorage.removeItem(SESSION_TEARDOWN_KEY)' in corpo, \
        'sem remover, todo F5 seguinte apagaria rascunho legítimo'
    assert corpo.index('removeItem') < corpo.index('resetAppFormDrafts')
    assert 'resetAppFormDrafts();' in corpo


def test_a_limpeza_nao_alcanca_a_tela_de_login(js):
    """O `#login-screen` fica de fora de propósito: mexer nele brigaria com o
    gerenciador de senhas, que a F1 registrou como comportamento do ambiente.

    Enunciado reformulado no achado 8: a exceção deixou de ser implícita (um
    escopo `#main-screen` que por acaso não alcançava o login) e passou a ser
    EXPLÍCITA e única. Mais forte, não mais frouxa: agora o resto do documento
    é alcançado de propósito, e só o login é poupado.
    """
    corpo = _corpo_de(js, 'resetAppFormDrafts')
    assert "closest('#login-screen')" in corpo, 'a exceção do login sumiu'
    assert '.reset()' in corpo
    # Toda varredura consulta a exceção: nenhuma limpa sem checar antes.
    seletores = re.findall(r"querySelectorAll\('([^']+)'\)", corpo)
    assert len(seletores) == 3, f'varreduras esperadas: 3, encontradas {len(seletores)}'
    # Uma consulta por varredura. A definição é `const ehDaTelaDeLogin =`, que
    # não casa com este padrão — só os pontos de chamada casam.
    assert corpo.count('ehDaTelaDeLogin(') == len(seletores), \
        'alguma varredura limpa sem consultar a exceção'
    # A exceção é UMA. Um segundo `closest` seria outra tela poupada em silêncio.
    assert corpo.count('closest(') == 1, 'apareceu uma segunda exceção'


def test_na_duvida_a_limpeza_acontece(js):
    """Se `closest` falhar, o controle NÃO é tratado como sendo do login. A
    exceção é de UX; a limpeza é de segurança, e é ela que ganha o desempate."""
    corpo = _corpo_de(js, 'resetAppFormDrafts')
    i_catch = corpo.index('catch (_erro)')
    assert 'return false;' in corpo[i_catch:i_catch + 120], \
        'o fallback da exceção passou a poupar o controle: fail-open'


def test_um_refresh_comum_nao_apaga_rascunho(js):
    """Contraprova, na direção oposta do gate 12a: com sessão autenticada E sem
    encerramento pendente — o F5 legítimo — a função sai antes de tocar em
    formulário nenhum. Rascunho do próprio dono da sessão não é apagado."""
    corpo = _corpo_de(js, 'clearRestoredAppForms')
    guarda = 'if (!semSessaoAutenticada && !encerramentoPendente) return;'
    assert guarda in corpo, 'a preservação do F5 legítimo sumiu'
    assert corpo.index(guarda) < corpo.index('resetAppFormDrafts')


def test_a_limpeza_roda_antes_dos_valores_padrao_do_init(js):
    """`init()` escreve datas padrão em campos. Limpar depois disso apagaria os
    defaults legítimos; limpar antes tira só o que o navegador restaurou."""
    corpo = _corpo_de(js, 'init')
    assert corpo.index('clearRestoredAppForms();') < corpo.index('refs.deliveryReturnedDate.value')


def test_o_discriminador_e_por_tentativa_e_nao_o_state_user(js):
    """`state.user` não serve como critério.

    O `init()` o deixa preenchido de propósito quando o bootstrap está
    temporariamente indisponível — mostra "Você pode tentar login manual agora"
    com a sessão antiga em memória. Com `state.user` como critério, um
    TOTP_REQUIRED nessa recuperação recarregaria a página e faria o campo de
    código sumir: a mesma quebra de 2FA que a separação existe para evitar.
    """
    corpo = _corpo_de(js, 'handleLogin')
    assert 'let sessaoEstabelecidaNestaTentativa = false;' in corpo
    assert 'if (state.user)' not in corpo, \
        'state.user sobrevive à recuperação de bootstrap: não discrimina a tentativa'
    # A flag é marcada logo após `saveSession`, e só depois dele.
    i_save = corpo.index('saveSession(')
    i_flag = corpo.index('sessaoEstabelecidaNestaTentativa = true;')
    i_guard = corpo.index('if (sessaoEstabelecidaNestaTentativa) {')
    assert i_save < i_flag < i_guard


def test_o_init_realmente_preserva_state_user_na_recuperacao(js):
    """A premissa do gate acima: se o `init()` passasse a limpar a sessão nesse
    ramo, o raciocínio mudaria — e o gate precisa perceber."""
    corpo = _corpo_de(js, 'init')
    i = corpo.index('isTemporaryBootstrapUnavailable(error)')
    ramo = corpo[i:corpo.index('return;', i)]
    assert 'clearSession' not in ramo and 'terminateSession' not in ramo, \
        'o ramo temporário passou a encerrar sessão: revisar o discriminador'
    assert 'login manual agora' in ramo


# ── 10e. A limpeza alcança controle solto, não só <form> ─────────────────────
#
# Achado da revisão: `form.reset()` só alcança descendentes de <form>. Os campos
# do novo fornecedor — `#compras-supplier-name`, `-cnpj`, `-email`, `-notes` —
# são inputs soltos num <div class="form-grid">. Abrir o painel só desesconde a
# div, e o rascunho de quem saiu apareceria inteiro.

def test_a_limpeza_alcanca_controles_fora_de_form(js):
    """Reformulado no achado 8: os seletores não podem voltar a ser escopados
    por lista de inclusão. `input, textarea` e `select` varrem o documento; a
    única subtração é a exceção do login, provada no gate acima."""
    corpo = _corpo_de(js, 'resetAppFormDrafts')
    assert "querySelectorAll('input, textarea')" in corpo
    assert "querySelectorAll('select')" in corpo
    assert '#main-screen' not in corpo, \
        'a limpeza voltou a ser lista de inclusão: modais irmãos ficam de fora'


def test_a_limpeza_restaura_o_padrao_e_nao_apaga_cegamente(js):
    """Semântica de `reset()`: volta ao valor PADRÃO do HTML. Apagar cegamente
    destruiria default legítimo."""
    corpo = _corpo_de(js, 'resetAppFormDrafts')
    assert 'controle.defaultValue' in corpo
    assert 'controle.defaultChecked' in corpo
    assert 'opcao.defaultSelected' in corpo
    assert "controle.value = ''" not in corpo


def test_os_campos_soltos_do_fornecedor_existem_fora_de_form():
    """A premissa do achado, verificada no HTML: se virarem <form>, o gate
    acima deixa de ser necessário — e é melhor descobrir isso pelo gate."""
    compras = (RAIZ / 'static' / 'views' / 'compras.html').read_text(encoding='utf-8')
    i = compras.index('id="compras-supplier-name"')
    antes = compras[:i]
    assert antes.rfind('<form') < antes.rfind('</form>'), \
        'os campos do fornecedor entraram num <form>: revisar o gate da limpeza'


# ── 13. A limpeza alcança os modais, que são IRMÃOS de #main-screen ──────────
#
# Terceiro achado da mesma classe: "a limpeza não alcança X". Primeiro foram os
# controles soltos fora de <form> (10e); depois a aba não recarregada (12a);
# agora os modais da aplicação, que não são descendentes de `#main-screen`.
#
# São 31 controles em quatro modais — `#signature-modal`,
# `#smr-request-report-modal`, `#master-profile-modal` e
# `#onboarding-wizard-modal` — com nome de assinante, notas de relatório,
# e-mail, código de 2FA e campos de senha.
#
# A conclusão não foi acrescentar quatro ids à lista: foi que a LISTA é o
# defeito. É o mesmo argumento que esta fatia faz contra o teardown enumerado.
# O critério inverteu — limpa tudo, menos a tela de login.
#
# O gate abaixo não casa texto: monta a árvore do `index.html` REAL e mede.

def _controles_por_tela():
    """Percorre o index.html servido e classifica cada controle de formulário
    pela tela de topo a que pertence."""
    from html.parser import HTMLParser

    class Arvore(HTMLParser):
        VAZIAS = {'input', 'br', 'hr', 'img', 'meta', 'link', 'source', 'area',
                  'base', 'col', 'embed', 'param', 'track', 'wbr'}

        def __init__(self):
            super().__init__(convert_charrefs=True)
            self.pilha, self.tags, self.controles = [], [], []

        def handle_starttag(self, tag, attrs):
            identificador = dict(attrs).get('id', '')
            if tag in ('input', 'textarea', 'select'):
                self.controles.append((identificador, list(self.pilha)))
            if tag in self.VAZIAS:
                return
            self.tags.append(tag)
            self.pilha.append(identificador)

        def handle_endtag(self, tag):
            if tag in self.VAZIAS:
                return
            while self.tags:
                if self.tags.pop() == tag:
                    self.pilha.pop()
                    break
                self.pilha.pop()

    arvore = Arvore()
    arvore.feed((RAIZ / 'static' / 'index.html').read_text(encoding='utf-8'))
    por_tela = {'login-screen': [], 'main-screen': [], 'fora': []}
    for identificador, ancestrais in arvore.controles:
        if 'login-screen' in ancestrais:
            por_tela['login-screen'].append(identificador)
        elif 'main-screen' in ancestrais:
            por_tela['main-screen'].append(identificador)
        else:
            por_tela['fora'].append(identificador)
    return por_tela


def test_existe_mesmo_controle_fora_das_duas_telas():
    """A premissa do achado, medida no HTML servido. Se um dia não houver mais
    controle fora de `#main-screen`, a inversão do critério deixa de ser
    necessária — e é melhor descobrir isso por um gate vermelho."""
    por_tela = _controles_por_tela()
    assert por_tela['fora'], \
        'não há mais controle fora das telas: revisar a inversão do critério'
    assert por_tela['login-screen'], 'a tela de login perdeu seus controles'


def test_os_modais_da_aplicacao_ficam_dentro_do_alcance():
    """Os quatro modais do achado continuam fora de `#main-screen`. Enquanto
    estiverem, um seletor escopado neles os deixaria de fora — e o gate do
    seletor acima é que garante que isso não volte."""
    conteudo = (RAIZ / 'static' / 'index.html').read_text(encoding='utf-8')
    for modal in ('signature-modal', 'smr-request-report-modal',
                  'master-profile-modal', 'onboarding-wizard-modal'):
        assert f'id="{modal}"' in conteudo, f'{modal} sumiu do HTML servido'
    por_tela = _controles_por_tela()
    assert 'smr-req-notes' in por_tela['fora'], \
        'smr-req-notes mudou de tela: reavaliar o alcance da limpeza'


def test_so_existem_duas_telas_de_topo():
    """Premissa da exceção única. Se nascer uma terceira tela de topo, alguém
    precisa decidir conscientemente de que lado dela a limpeza fica."""
    import re as _re
    conteudo = (RAIZ / 'static' / 'index.html').read_text(encoding='utf-8')
    telas = set(_re.findall(r'id="([a-z-]+-screen)"', conteudo))
    assert telas == {'login-screen', 'main-screen'}, \
        f'telas de topo mudaram: {sorted(telas)}'


# ── 12a. Carga sem sessão autenticada não restaura rascunho de ninguém ───────
#
# Achado da revisão. É o meio-termo honesto do vazamento entre abas: o marcador
# de encerramento vive em `sessionStorage`, que é POR ABA. A aba que não iniciou
# o logout nunca o recebe — recarregada, ela via `clearRestoredAppForms` sair
# cedo e mantinha CPF, e-mail e observações de fornecedor que o navegador
# restaurou.
#
# A correção NÃO é coordenação entre abas. É trocar o critério: uma carga sem
# sessão autenticada não tem razão legítima para exibir rascunho do aplicativo.
# O marcador continua, como sinal auxiliar.
#
# O que esta fatia deliberadamente NÃO resolve, e virou frente própria: a aba
# que permanece aberta sem recarregar (12b) e o escopo de snapshot ligado ao
# principal (11). Os dois exigem identidade entre abas.

def test_carga_sem_sessao_autenticada_reseta_os_rascunhos(js):
    """Direção 1: sem sessão, limpa. A guarda de saída EXIGE sessão, então
    `semSessaoAutenticada` verdadeiro nunca pode tomar o `return`."""
    corpo = _corpo_de(js, 'clearRestoredAppForms')
    assert 'const semSessaoAutenticada = !state.user;' in corpo
    guarda = 'if (!semSessaoAutenticada && !encerramentoPendente) return;'
    assert guarda in corpo, 'a condição de segurança sumiu ou mudou de forma'
    assert 'resetAppFormDrafts();' in corpo
    assert corpo.index(guarda) < corpo.index('resetAppFormDrafts();')


def test_a_condicao_de_seguranca_nao_depende_de_sessionStorage(js):
    """A ausência de sessão é lida ANTES do `try` de storage, e a falha de
    storage não pode mais abortar a limpeza: o `catch` não retorna."""
    corpo = _corpo_de(js, 'clearRestoredAppForms')
    i_condicao = corpo.index('const semSessaoAutenticada')
    i_try = corpo.index('try {')
    assert i_condicao < i_try, 'a condição de segurança caiu para dentro do try'
    i_catch = corpo.index('catch (_e)')
    i_guarda = corpo.index('if (!semSessaoAutenticada')
    assert 'return' not in corpo[i_catch:i_guarda],         'o catch voltou a abortar: storage indisponível cancelaria a limpeza'


def test_state_user_falha_fechado_quando_o_storage_nao_responde(js):
    """Premissa do gate acima. `state.user` nasce de uma leitura de storage com
    fallback nulo: storage indisponível vira "sem sessão", que LIMPA. Se essa
    origem mudar para algo que falhe aberto, o raciocínio cai — e o gate vê."""
    assert "user: safeJsonParse(safeStorageRead(STORAGE_KEYS.session, 'null'), null)" in js


def test_o_init_usa_o_mesmo_discriminador_de_sessao(js):
    """Premissa: `state.user` não é critério inventado para esta fatia — é o que
    o próprio `init()` usa para decidir se há sessão a restaurar."""
    corpo = _corpo_de(js, 'init')
    assert 'if (state.user) {' in corpo


def test_a_limpeza_roda_antes_de_qualquer_return_do_init(js):
    """O caminho do portal do colaborador retorna cedo. Com a limpeza embaixo
    dele, uma carga de portal passaria por fora e manteria o rascunho."""
    corpo = _corpo_de(js, 'init')
    i_limpeza = corpo.index('clearRestoredAppForms();')
    assert i_limpeza < corpo.index("get('employee_token')")
    assert i_limpeza < corpo.index('return;'),         'existe um return antes da limpeza: há carga que escapa'


def test_a_fatia_nao_introduz_coordenacao_entre_abas(js):
    """Escopo negativo explícito: o 12(a) se resolve dentro da própria aba. Se
    aparecer broadcast ou evento de storage, é a frente cross-tab entrando de
    contrabando aqui em vez de no contrato próprio dela."""
    assert 'BroadcastChannel' not in js
    assert "addEventListener('storage'" not in js
    assert 'onstorage' not in js


# ── 11. A invariante não tem ponto cego fora do app.js ───────────────────────
#
# Segundo achado da revisão, na parte que procede: `clearSession` é exportado no
# `globalThis` por `auth.js` (`globalThis[name] = fn`, `__EPI_AUTH__`,
# `__EPI_FRONTEND_HELPERS__`), então qualquer módulo pode chamá-lo e pular o
# teardown. Os gates 1 e 2 leem só o `app.js` — este cobre o resto.

def _outros_js_servidos():
    raiz = RAIZ / 'static'
    for caminho in sorted(raiz.rglob('*.js')):
        rel = caminho.relative_to(RAIZ).as_posix()
        if '/test/' in rel or rel == 'static/app.js':
            continue
        yield rel, caminho


def test_nenhum_outro_arquivo_servido_chama_clear_session_por_fora():
    """O orquestrador vive no `app.js`; `clearSession` é global. Um módulo que
    o chamasse encerraria sessão sem teardown, e os gates 1 e 2 não veriam."""
    infratores = []
    for rel, caminho in _outros_js_servidos():
        texto = _sem_comentarios(caminho.read_text(encoding='utf-8'))
        if rel == 'static/js/modules/auth.js':
            continue  # é quem DEFINE a primitiva
        if re.search(r'\bclearSession\s*\(', texto):
            infratores.append(rel)
    assert not infratores, (
        'arquivo servido chamando clearSession() fora do orquestrador: '
        + ', '.join(infratores))


def test_nenhum_outro_arquivo_servido_esconde_a_tela_para_encerrar():
    """Mesmo ponto cego, pelo outro lado: um módulo que fizesse
    `showScreen(false)` como encerramento repetiria o defeito original."""
    infratores = []
    for rel, caminho in _outros_js_servidos():
        texto = _sem_comentarios(caminho.read_text(encoding='utf-8'))
        if rel == 'static/js/modules/router.js':
            continue  # é quem DEFINE showScreen
        if 'showScreen(false)' in texto:
            infratores.append(rel)
    assert not infratores, (
        'arquivo servido escondendo a tela por conta própria: ' + ', '.join(infratores))


# ── 9. Bootstrap degradado: o cenário que virava vazamento visível ───────────

def test_o_bootstrap_degradado_nao_pode_mais_renderizar_dados_de_outro(js):
    """O gate obrigatório.

        A tem dados → logout → B entra → /api/bootstrap de B falha 502/503
        → renderAll() roda sem nenhuma das 24 chaves sobrescritas

    A cadeia que fecha isso é causal, não pontual: TODO encerramento recarrega o
    documento, logo não existe memória de A viva quando B faz login — degradado
    ou não. Este gate prende os três elos.
    """
    # Elo 1: o caminho degradado continua existindo (o gate não é vacuoso).
    corpo_login = _corpo_de(js, 'handleLogin')
    assert 'isBootstrapRequestError(bootstrapError)' in corpo_login
    assert 'renderAll();' in corpo_login, \
        'premissa: é este renderAll que pintava os dados do usuário anterior'

    # Elo 2: todo encerramento passa pelo caminho único (gate 1 já garante a
    # contagem; aqui prendemos que o caminho único é o que recarrega).
    assert 'location.reload()' in _corpo_de(js, 'terminateSession')

    # Elo 3: o RAMO DEGRADADO não pode ter atalho próprio que dispense a
    # recarga. O `terminateSession` do `handleLogin` pertence ao sub-caminho
    # pós-`saveSession`, que é terminação real — outro ramo, outra semântica.
    i_deg = corpo_login.index('isBootstrapRequestError(bootstrapError)')
    ramo_degradado = corpo_login[i_deg:corpo_login.index('} else {', i_deg)]
    assert 'terminateSession(' not in ramo_degradado
    assert 'renderAll();' in ramo_degradado


def test_o_modo_degradado_continua_avisando_o_usuario(js):
    """Não basta ficar seguro: o banner de modo degradado precisa continuar."""
    assert 'setBootstrapDegraded(' in js
    assert 'updateBootstrapDegradedUi' in js
