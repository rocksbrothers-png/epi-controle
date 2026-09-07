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
