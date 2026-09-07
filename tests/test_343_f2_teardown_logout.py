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
}

# B: AUTENTICAÇÃO EM ANDAMENTO — nenhuma sessão chegou a existir nesta página.
#    Estes NÃO PODEM chamar terminateSession() nem recarregar.
AUTENTICACAO_EM_ANDAMENTO = {
    'falha de login / TOTP_REQUIRED / TOTP_INVALID': 'handleLogin',
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
    assert len(re.findall(r'(?<!function )\bterminateSession\(', js)) == 4, (
        'os quatro encerramentos (botão, 401/403, sessão expirada, bootstrap) '
        'precisam continuar existindo e chamando o caminho único')


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
    assert 'terminateSession(' not in corpo, \
        'recarregar na falha de login quebra o 2FA: o campo de código some'


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


def test_o_encerramento_so_mexe_na_propria_chave(js):
    """A única escrita em storage do encerramento é o aviso de uso único."""
    corpo = _corpo_de(js, 'terminateSession')
    assert corpo.count('sessionStorage.') == 1


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
    assert corpo.count('sid: DOCUMENT_INSTANCE_ID') == 2, (
        'os DOIS retornos precisam carimbar: o com filtros e o do atalho, '
        'senão um deles vira snapshot sem origem')
    assert 'const DOCUMENT_INSTANCE_ID' in js


def test_o_snapshot_de_outro_documento_e_descartado(js):
    """A metade que fecha o furo: carimbar sem conferir não protege nada."""
    corpo = _corpo_de(js, 'restoreInteractiveSnapshot')
    assert 'snapshot.sid !== DOCUMENT_INSTANCE_ID' in corpo, \
        'sem a conferência, o filtro do usuário anterior volta pelo botão Voltar'
    # A rejeição vem ANTES de qualquer escrita em `state`.
    assert corpo.index('snapshot.sid !== DOCUMENT_INSTANCE_ID') < corpo.index('state.employeesFilters')


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
    view continua sendo resolvida e exibida; só o estado carimbado é ignorado."""
    i = js.index("safeOn(globalThis, 'popstate'")
    trecho = js[i:i + 500]
    assert 'restoreInteractiveSnapshot(event?.state)' in trecho
    assert 'showView(nextView' in trecho
    assert trecho.index('restoreInteractiveSnapshot') < trecho.index('showView(nextView')


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

    # Elo 3: e o degradado não tem atalho próprio de limpeza que dispense a
    # recarga — se alguém adicionar um, esta fatia precisa ser reavaliada.
    assert 'terminateSession(' not in corpo_login


def test_o_modo_degradado_continua_avisando_o_usuario(js):
    """Não basta ficar seguro: o banner de modo degradado precisa continuar."""
    assert 'setBootstrapDegraded(' in js
    assert 'updateBootstrapDegradedUi' in js
