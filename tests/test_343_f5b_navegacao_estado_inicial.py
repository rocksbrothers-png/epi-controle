"""#343 F5-B — navegação sempre começa no estado padrão do módulo.

Contrato desta fatia, decidido no produto:

  Sair de um módulo e voltar a ele abre a tela inicial daquele módulo. Não se
  restaura automaticamente subtela, aba, registro, filtro, pesquisa, paginação,
  seleção nem rolagem. Isso vale INCLUSIVE para o mesmo usuário — logo,
  namespace por `user_id` não resolveria: a correção é não persistir.

Duas exceções deliberadas, que continuam valendo:

  1. Deep link explícito (`?view=`) — destino pedido pelo usuário.
  2. Voltar/Avançar do navegador — navegação explícita. O snapshot em
     `history.state` segue permitido, carimbado por `sid`, e só no `popstate`.

O que este arquivo NÃO faz é provar comportamento: quem prova são os gates
comportamentais em `static/js/test/run-tests.js`, que carregam os scripts
realmente servidos e exercitam o mecanismo de navegação. Aqui ficam as
propriedades estruturais que um teste de browser não alcança bem — ausência de
caminho de gravação, premissas medidas e paridade entre os repositórios.
"""

import hashlib
import pathlib
import re

import pytest

RAIZ = pathlib.Path(__file__).resolve().parent.parent
ESTATICO = RAIZ / 'static'


def _sem_comentarios(texto: str) -> str:
    """Remove linhas que são só comentário.

    Sem isto, um gate que procura o nome de uma chave reprovaria o próprio
    comentário que explica por que ela foi removida.
    """
    return '\n'.join(
        linha for linha in texto.split('\n')
        if not linha.strip().startswith('//')
    )


def _fonte(rel: str) -> str:
    return _sem_comentarios((RAIZ / rel).read_text(encoding='utf-8'))


# ── G10 — não existe caminho de gravação de estado de navegação ─────────────

CHAVES_PROIBIDAS = (
    ("epi_vtab_", 'static/app.js', 'última aba interna por grupo'),
    ("epi:ux:phase41:scroll:v2", 'static/ux-phase41.js', 'posição de rolagem'),
    ("epi:ux:phase42:memory:v2", 'static/ux-phase42.js', 'último colaborador/EPI/unidade + companyId'),
    ("epi:ux:phase43:state:v1", 'static/ux-phase43.js', 'estado do fluxo de entrega'),
)


@pytest.mark.parametrize('chave,arquivo,oque', CHAVES_PROIBIDAS)
def test_g10_a_chave_de_navegacao_nao_e_mais_escrita(chave, arquivo, oque):
    """A chave pode ser NOMEADA, mas só para ser apagada.

    A primeira versão deste gate proibia o nome da chave no arquivo. Estava
    errado por um detalhe que a revisão do Codex expôs: parar de gravar não
    apaga o que já está no disco de quem rodou a versão anterior, e o
    encerramento de sessão preserva `localStorage` de propósito (F2). A
    remoção da chave legada precisa citá-la — e é justamente o que se quer.

    O que continua proibido é qualquer forma de GRAVAÇÃO.
    """
    corpo = _fonte(arquivo)
    for achado in re.finditer(re.escape(chave), corpo):
        linha_ini = corpo.rfind('\n', 0, achado.start()) + 1
        linha = corpo[linha_ini:corpo.find('\n', achado.start())]
        assert 'removeItem' in linha, (
            f'{arquivo} cita `{chave}` ({oque}) fora de uma remoção: {linha.strip()[:80]}. '
            f'Estado de navegação não é persistido nesta arquitetura.'
        )
    for gravacao in ('setItem', 'queueStorageWrite'):
        for achado in re.finditer(re.escape(gravacao) + r'\(([^)]*)', corpo):
            assert chave not in achado.group(1), (
                f'{arquivo} voltou a gravar `{chave}` via {gravacao}'
            )


def test_g10_o_phase44_nao_grava_filtro_mas_ainda_limpa_o_legado():
    corpo = _fonte('static/ux-phase44.js')
    for simbolo in ('STORAGE_FILTER_PREFIX', 'persistContext', 'restoreContext',
                    'safeLocalStorageSet', 'safeLocalStorageGet'):
        assert simbolo not in corpo, f'`{simbolo}` voltou ao phase44: o filtro está sendo persistido de novo'
    # A limpeza precisa continuar: quem já rodou a versão anterior tem as
    # chaves gravadas no navegador, e ninguém mais as lê.
    assert 'removePhase44Storage();' in corpo, (
        'a limpeza das chaves legadas do phase44 sumiu — elas ficariam paradas '
        'no disco do usuário sem nunca mais serem lidas'
    )
    assert "STORAGE_NAMESPACE = 'epi.ux.phase44'" in corpo, (
        'o namespace some junto com a limpeza: `removePhase44Storage` precisa dele'
    )


def test_g10_os_modulos_de_contexto_e_filtro_nao_gravam_nada():
    """Varredura direta: phase42, phase43 e phase44 não escrevem em storage.

    O phase41 fica de fora desta varredura porque ainda persiste o RASCUNHO de
    formulário — categoria 3, escopo da F5-C. O que a F5-B tirou dele (rolagem)
    tem gate próprio acima.
    """
    for nome in ('ux-phase42.js', 'ux-phase43.js', 'ux-phase44.js'):
        corpo = _fonte(f'static/{nome}')
        assert 'localStorage.setItem' not in corpo, (
            f'{nome} voltou a gravar em localStorage: estado de navegação não persiste'
        )
        assert 'sessionStorage.setItem' not in corpo, (
            f'{nome} passou a gravar em sessionStorage — mesma proibição'
        )


def test_g10_o_reset_de_entrada_existe_e_esta_na_costura_de_troca_de_view():
    """Remover a persistência não bastaria: as views da SPA vivem no DOM e
    `setupViewTabs` roda uma vez por nav. Sem reset na entrada, a última aba
    continuaria ativa por permanência — sem storage nenhum envolvido."""
    corpo = _fonte('static/app.js')
    assert 'function resetViewTabsToInitial(' in corpo
    assert 'function resetModuleFiltersToInitial(' in corpo
    listener = corpo[corpo.index("safeOn(document, 'epi:viewchange'"):][:1200]
    assert 'resetViewTabsToInitial(nav)' in listener, 'o reset de abas saiu da troca de view'
    assert 'resetModuleFiltersToInitial(' in listener, 'o reset de filtros saiu da troca de view'
    assert 'resetModuleSelectionToInitial(' in listener, (
        'o reset de seleção saiu da troca de view: reentrar devolveria as caixas '
        'marcadas da visita anterior, com a barra de ações armada'
    )
    # Duas guardas, cada uma por um motivo distinto:
    #  - `nome === anterior`: `showView` também é chamado por fluxos internos da
    #    MESMA view (`startEditEmployee` chama `showView('colaboradores')` estando
    #    já lá). Resetar ali destruiria o filtro que o usuário usou para achar o
    #    registro que está editando.
    #  - `viaHistorico`: Voltar/Avançar é navegação explícita e fica de fora. O
    #    snapshot carrega só filtros de colaboradores/EPIs, então resetar no
    #    `popstate` apagaria aba interna e filtros de estoque que ele não devolve.
    assert 'nome === anterior' in listener, (
        'a guarda de transição real sumiu: o redesenho da mesma view voltaria a zerar a navegação'
    )
    assert 'viaHistorico' in listener, (
        'a guarda do Voltar/Avançar sumiu: o popstate voltaria a sofrer o reset de entrada'
    )


# ── Exceções deliberadas: deep link e Voltar/Avançar ────────────────────────

def test_o_deep_link_por_view_continua_existindo():
    """A correção não pode virar "tudo abre na inicial": destino explicitamente
    pedido na URL é navegação do usuário, não memória do sistema."""
    roteador = _fonte('static/js/modules/router.js')
    assert 'function resolveViewFromLocation(' in roteador
    assert "get('view')" in roteador or "searchParams.get('view')" in roteador, (
        'o roteador parou de ler `?view=`: deep links quebrariam'
    )


def test_o_snapshot_do_voltar_continua_carimbado_e_so_no_popstate():
    corpo = _fonte('static/app.js')
    assert 'function restoreInteractiveSnapshot(' in corpo
    assert 'snapshot.sid !== snapshotScopeId()' in corpo, (
        'o carimbo `sid` saiu: um snapshot de outra sessão/identidade passaria'
    )
    # Restaurar só pode acontecer no Voltar/Avançar. Qualquer outra chamada
    # transformaria o snapshot em memória automática de navegação.
    chamadas = [m.start() for m in re.finditer(r'restoreInteractiveSnapshot\(', corpo)]
    definicao = corpo.index('function restoreInteractiveSnapshot(') + len('function ')
    usos = [pos for pos in chamadas if pos != definicao]
    assert len(usos) == 1, f'restoreInteractiveSnapshot passou a ser chamada {len(usos)}x — só o popstate pode'
    trecho = corpo[corpo.index("safeOn(globalThis, 'popstate'"):]
    assert trecho.index('showView(nextView') < trecho.index('restoreInteractiveSnapshot('), (
        'o snapshot voltou a ser aplicado ANTES do showView: o reset de entrada '
        'apagaria justamente o estado que o usuário mandou restaurar'
    )


# ── Gate de premissa: o defeito pendente em `applyFilterValues` ─────────────

def test_premissa_a_flag_do_snapshot_interativo_continua_desligada():
    """Medido, não assumido.

    `restoreInteractiveSnapshot` chama `applyFilterValues()`, que NÃO existe em
    lugar nenhum da árvore servida. Hoje isso é inerte: o caminho inteiro é
    guardado por `ux_interactive_app_enabled`, cujo default é `false`. Se
    alguém ligar a flag por default sem definir a função, o `popstate` passa a
    lançar `ReferenceError` antes do `showView` e o botão Voltar para de trocar
    de tela.

    Este gate fica vermelho nesse dia. A F5-B não corrigiu o defeito de
    propósito — é anterior a ela e está fora do escopo aprovado (remoção de
    persistência). Está registrado em issue própria.
    """
    corpo = _fonte('static/app.js')
    assert "getFeatureFlag('ux_interactive_app_enabled', { defaultValue: false, allowStorage: true })" in corpo, (
        'a flag do snapshot interativo mudou de default: antes de ligá-la, '
        '`applyFilterValues` precisa existir — ver a issue do defeito'
    )
    definida = any(
        f'function applyFilterValues' in p.read_text(encoding='utf-8')
        or 'applyFilterValues =' in p.read_text(encoding='utf-8')
        for p in ESTATICO.rglob('*.js')
    )
    assert not definida, (
        '`applyFilterValues` passou a existir: o defeito foi corrigido — '
        'remova este gate de premissa e habilite o teste comportamental do '
        'snapshot com a flag ligada'
    )


# ── G11 — paridade Corporate × SaaS ────────────────────────────────────────

# ── Classes incorporadas ao plano fechado: edição, modal e wizard ──────────

def test_o_reset_de_entrada_cobre_edicao_modal_e_wizard():
    """A auditoria fechada nomeou onze classes. Estas três não estavam na
    primeira implementação e são as de maior consequência: com o modo de edição
    armado, o próximo submit ALTERA o registro da visita anterior em vez de
    criar um novo. Não é incômodo de navegação, é integridade de dado."""
    corpo = _fonte('static/app.js')
    listener = corpo[corpo.index("safeOn(document, 'epi:viewchange'"):][:1800]
    for chamada, oque in (
        ('resetModuleFormsToInitial(', 'modo de edição'),
        ('resetModuleModalsToInitial(', 'modal aberto'),
        ('resetModuleWizardsToInitial(', 'assistente/wizard'),
    ):
        assert chamada in listener, (
            f'{oque} saiu da costura de troca de view: reentrar no módulo '
            'devolveria o estado da visita anterior'
        )


def test_os_nove_modulos_de_edicao_tem_reset_declarado():
    corpo = _fonte('static/app.js')
    mapa = corpo[corpo.index('const VIEW_FORM_RESET'):corpo.index('function resetModuleFormsToInitial')]
    for view in ('empresas', 'usuarios', 'comercial', 'unidades',
                 'colaboradores', 'epis', 'cnpjs', 'terceirizados'):
        assert f'{view}:' in mapa, f'{view} entra em modo de edição e ficou de fora do reset'
    # Compras edita pelo modal — a cobertura entra pela porta dos modais.
    modais = corpo[corpo.index('const MODAIS_DE_MODULO'):corpo.index('function resetModuleModalsToInitial')]
    assert 'compras:' in modais


def test_o_modal_descarta_a_identidade_e_nao_apenas_esconde():
    """Esconder o modal sem soltar o id deixa a mesma armadilha do modo de
    edição: o registro segue apontado, e o próximo salvar o sobrescreve."""
    corpo = _fonte('static/app.js')
    modais = corpo[corpo.index('const MODAIS_DE_MODULO'):corpo.index('function resetModuleModalsToInitial')]
    assert "'edit-supplier-id'" in modais, (
        'o modal de fornecedor voltou a ser apenas escondido, sem descartar o registro editado'
    )
    reset = corpo[corpo.index('function resetModuleModalsToInitial'):][:900]
    assert "campo.value = ''" in reset, 'o reset de modais parou de limpar a identidade'


def test_o_wizard_reaproveita_o_reset_que_o_produto_ja_expoe():
    """"Estado inicial" do assistente não pode ser uma definição nova inventada
    por esta fatia: é a mesma do botão "Recomeçar" que o módulo já tinha."""
    corpo = _fonte('static/app.js')
    reset = corpo[corpo.index('function resetModuleWizardsToInitial'):][:600]
    assert 'resetDataMigrationWizard()' in reset
    assert 'refs.migracaoRestart' in corpo, (
        'o botão Recomeçar sumiu: o reset do wizard perderia a autoridade que reaproveita'
    )


# ── Passos independentes ───────────────────────────────────────────────────

def test_um_passo_de_reset_que_falha_nao_cancela_os_seguintes():
    """Achado medido: com um único `try` em volta do corpo do reset, um
    `sync*()` que lançasse impedia a limpeza dos campos seguintes, e o módulo
    reabria com metade dos filtros limpos."""
    corpo = _fonte('static/app.js')
    assert 'function passoDeReset(' in corpo
    mapa = corpo[corpo.index('const VIEW_FILTER_RESET'):corpo.index('function resetModuleFormsToInitial')]
    assert mapa.count('passoDeReset(') >= 12, (
        'passos do reset voltaram a rodar sem isolamento: a primeira falha '
        'cancela os demais. Isto vale também para os `clearFilters()` de cada '
        'módulo, não só para as ressincronizações — foi um deles lançando que '
        'impediu a limpeza dos filtros de arquivados.'
    )
    reset = corpo[corpo.index('function resetModuleFiltersToInitial'):][:900]
    assert 'finally' in reset and 'populateScopedSearchFilters()' in reset, (
        'a reafirmação do escopo de empresa saiu do `finally`: uma falha na '
        'limpeza deixaria o recorte por papel destravado'
    )


# ── Notificação da tela ────────────────────────────────────────────────────

def test_limpar_filtro_notifica_a_tela():
    """Sem `input`/`change`, o contador "Filtros ativos: N" e os status de
    módulo ficam com o número da visita anterior: estado limpo, DOM mentindo."""
    corpo = _fonte('static/app.js')
    limpador = corpo[corpo.index('const limparCamposDeFiltro'):corpo.index('const VIEW_FILTER_RESET')]
    assert "new Event('input'" in limpador and "new Event('change'" in limpador


# ── Multitab: restaurar contexto é exceção, não padrão ─────────────────────

def test_o_multitab_restaura_contexto_apenas_em_acao_explicita():
    """A flag estar desligada por padrão não elimina o requisito: com ela
    ligada, entrar pelo menu lateral restaurava os campos da visita anterior
    logo depois de o reset de entrada tê-los limpado."""
    corpo = _fonte('static/multitab-navigation.js')
    assert 'if (opts.restoreContext === true) restoreViewContext(tab);' in corpo, (
        'restoreViewContext voltou a rodar em toda ativação de aba'
    )
    ativar = corpo[corpo.index('function activateTab('):]
    assert 'viaMultitab: opts.restoreContext === true' in ativar, (
        'a ativação deixou de distinguir troca explícita de aba de reentrada no módulo'
    )
    menu = corpo[corpo.index('function onMenuIntercept('):corpo.index('function bindKeyboard(')]
    assert 'restoreContext' not in menu, (
        'entrar pelo menu lateral voltou a restaurar o contexto da visita anterior'
    )
    app = _fonte('static/app.js')
    listener = app[app.index("safeOn(document, 'epi:viewchange'"):][:1800]
    assert 'viaMultitab' in listener, (
        'o app deixou de tratar a troca explícita de aba como exceção ao reset'
    )


# ── Ponte phase42 → phase43 (contexto/sugestão em RAM) ─────────────────────

def test_registrar_uso_so_entra_no_historico_se_a_entrega_der_certo():
    """O handler de submit do phase42 é `capture: true` e roda ANTES do phase43,
    que aborta quando o resumo não foi revisado, o codigo do item esta errado ou
    a quantidade e invalida. Gravar ali punha no historico uma entrega que nunca
    existiu — e o phase43 passava a recomendar a partir dela."""
    p42 = _fonte('static/ux-phase42.js')
    p43 = _fonte('static/ux-phase43.js')
    submit = p42[p42.index("safeOn(form, 'submit'"):]
    fim = submit.index('}, { capture: true')
    assert 'ctxPendente = getContext(memory)' in submit[:fim], (
        'o contexto deixou de ser capturado no submit, com o formulário ainda cheio'
    )
    for trecho in ('appendUsageEvent(', 'saveMemory(', 'anunciarUsoRegistrado('):
        assert trecho not in submit[:fim], (
            f'"{trecho}" voltou para o pré-submit: submissão abortada entraria no histórico'
        )
    sucesso = p42.index("safeOn(document, 'epi:delivery-submit-success'")
    bloco = p42[sucesso:p42.index('}, { signal: moduleController.signal });', sucesso)]
    for trecho in ('appendUsageEvent(memory, ctxPendente)', 'saveMemory(memory)',
                   'anunciarUsoRegistrado()'):
        assert trecho in bloco, f'a conclusão da entrega deixou de executar "{trecho}"' 
    assert "CustomEvent('epi:phase42:uso-registrado')" in p42
    bind = p43[p43.index('function bindForm('):]
    escuta = bind.index("safeOn(document, 'epi:phase42:uso-registrado'")
    assert 'recomputarSugestao(ui, form)' in bind[escuta:escuta + 300], (
        'o phase43 escuta o anúncio mas não recalcula nada'
    )


# ── Rodada de convergência do Codex ────────────────────────────────────────

def test_os_sete_modais_entram_no_reset_com_suas_identidades():
    """Contagem corrigida. A auditoria achou 3 porque procurou em `app.js`; os
    modais vivem em `static/views/modals/*.html` (mais o `ppe-form-modal`,
    inline em avaliacoes, e o `smr-request-report-modal`, em `_modals.html`) e
    dois são acionados de `static/js/views/purchases.js`."""
    corpo = _fonte('static/app.js')
    modais = corpo[corpo.index('const MODAIS_DE_MODULO'):corpo.index('function resetModuleModalsToInitial')]
    for modal in ('modal-edit-supplier', 'modal-supplier-pos',
                  'aprovacoes-reprovar-modal', 'aprovacoes-prorrogar-modal',
                  'ppe-form-modal', 'aval-action-modal', 'smr-request-report-modal'):
        assert f"'{modal}'" in modais, f'{modal} ficou de fora do reset de modais'
    # Dois campos de identidade no mesmo modal: esconder sem descartar exporia,
    # na volta, uma confirmação capaz de agir sobre o feedback da visita anterior.
    assert "'aval-modal-feedback-id'" in modais and "'aval-modal-action'" in modais


def test_cnpjs_terceirizados_e_arquivados_entram_no_reset_de_filtros():
    corpo = _fonte('static/app.js')
    mapa = corpo[corpo.index('const VIEW_FILTER_RESET'):corpo.index('function limparFiltrosArquivados')]
    for view in ('cnpjs', 'terceirizados'):
        assert f'{view}:' in mapa, f'{view} retém filtros vivos e ficou de fora do reset'
    assert 'legalEntitiesShowInactive' in mapa, (
        'a caixa "mostrar inativos" ficou de fora: `value = ""` não desmarca caixa'
    )
    for kind in ('employee', 'epi', 'outsourcedCompany', 'outsourcedEmployee'):
        assert f"limparFiltrosArquivados('{kind}'" in mapa, (
            f'o grupo de arquivados de {kind} ficou de fora do reset'
        )


def test_o_editor_comercial_e_resetado_atomicamente():
    """O editor tem duas metades: a configuração principal da empresa e o
    contrato. Limpar só a segunda deixava a tela editando a empresa B com a
    identidade do contrato dela já descartada — e um "Salvar contrato" ali
    gravaria um rascunho em branco por cima do contrato existente de B."""
    corpo = _fonte('static/app.js')
    mapa = corpo[corpo.index('const VIEW_FORM_RESET'):corpo.index('function resetModuleFormsToInitial')]
    linha = next(l for l in mapa.split('\n') if l.strip().startswith('comercial:'))
    assert 'fillCommercialForm()' in linha, (
        'o reset comercial voltou a limpar só a metade do contrato'
    )
    preenche = corpo[corpo.index('function fillCommercialForm('):]
    assert 'resetCommercialContractForm(' in preenche[:preenche.index('\n}')], (
        'fillCommercialForm deixou de resetar a metade do contrato'
    )


def test_a_troca_explicita_de_aba_multitab_nao_descarta_o_assistente():
    """`activateTab()` restaura os campos daquela aba logo depois; descartar o
    assistente ali devolveria o formulário preenchido SEM a sugestão nem o
    contexto de revisão que pertenciam a ele."""
    for arquivo, descarte in (('static/ux-phase42.js', 'descartarMemoria()'),
                              ('static/ux-phase43.js', 'descartarEstado()')):
        corpo = _fonte(arquivo)
        i = corpo.index("safeOn(document, 'epi:viewchange'")
        bloco = corpo[i:corpo.index(descarte, i)]
        assert 'detalhe.anterior' in bloco, f'{arquivo}: a guarda de redesenho sumiu'
        assert 'viaMultitab' in bloco, (
            f'{arquivo}: a troca explícita de aba multitab voltou a descartar o assistente'
        )


def test_o_teardown_do_phase43_e_registrado_uma_vez():
    """`scheduleRebind()` chama `init()` a cada viewchange, htmx swap e
    popstate, e o registro fica antes da guarda `runtime.formBound`. Sem
    cadeado, cada navegação acrescentava um listener permanente de descarte."""
    corpo = _fonte('static/ux-phase43.js')
    init = corpo[corpo.index('function init()'):corpo.index('function scheduleRebind()')]
    registro = init.index("safeOn(document, 'epi:viewchange'")
    assert 'runtime.teardownBound' in init[:registro], (
        'o registro do teardown voltou a rodar sem cadeado'
    )
    assert "document.addEventListener('epi:viewchange'" not in init, (
        'o teardown voltou ao addEventListener cru, fora do AbortController da aplicação'
    )


def test_compras_avaliacoes_e_migracao_entram_no_reset_de_filtros():
    corpo = _fonte('static/app.js')
    mapa = corpo[corpo.index('const VIEW_FILTER_RESET'):corpo.index('function limparFiltrosArquivados')]
    for view in ('compras', 'avaliacoes', 'migracao'):
        assert f'{view}:' in mapa, f'{view} retém filtros vivos e ficou de fora do reset'
    # Os seletores de Compras só recarregam por `change`.
    compras = mapa[mapa.index('compras:'):mapa.index('avaliacoes:')]
    assert "new Event('change'" in compras, (
        'os seletores de Compras são limpos sem notificar: as listas continuariam '
        'com o recorte da visita anterior'
    )


def test_soltar_a_empresa_selecionada_redesenha_as_duas_superficies():
    """Problema de ordem: o reset de formulários roda antes do de seleção e
    termina em `renderCompanyDetails()`, que ainda enxerga a empresa da visita
    anterior."""
    corpo = _fonte('static/app.js')
    reset = corpo[corpo.index('function resetModuleSelectionToInitial'):]
    bloco = reset[:reset.index('} catch (error)')]
    pos = bloco.index('state.selectedCompanyId = null;')
    depois = bloco[pos:]
    assert 'renderCompanyDetails()' in depois and 'renderCompanies()' in depois, (
        'as superfícies de Empresas não são redesenhadas após soltar a seleção'
    )


def test_o_card_de_sugestao_do_phase43_cai_junto_com_o_estado():
    corpo = _fonte('static/ux-phase43.js')
    descarte = corpo[corpo.index('function descartarEstado()'):]
    bloco = descarte[:descarte.index('\n  }')]
    for node_id in ('phase43-quick-confirm', 'phase43-fast-card'):
        assert node_id in bloco, (
            f'{node_id} ficou renderizado após o descarte: a recomendação '
            'reapareceria sem memória por trás'
        )


def test_o_descarte_do_phase42_restaura_o_valor_que_a_sugestao_substituiu():
    """Só limpar a marca deixava a escolha SUGERIDA no campo, agora sem nada que
    a identificasse como sugestão: na volta ela parece escolha manual."""
    corpo = _fonte('static/ux-phase42.js')
    i = corpo.index("safeOn(document, 'epi:viewchange'")
    bloco = corpo[i:corpo.index('}, { signal: moduleController.signal });', i)]
    assert 'campo.value = anterior' in bloco, (
        'o descarte apaga a marca de autofill sem restaurar o valor anterior'
    )


# ── Decisão de contrato: clique no menu da view já ativa é no-op ───────────

def test_clique_no_menu_da_view_ativa_e_no_op_por_decisao_de_contrato():
    """Levantado em review como possível falha do contrato "reentrar no módulo
    → estado inicial". A decisão de produto foi explícita: esse gesto NÃO é
    reentrada para fins da F5-B.

    O achado não está sendo ignorado — está sendo fixado. Sem a guarda, clicar
    no item do menu do módulo em que já se está passaria a destruir, sem aviso,
    uma edição em andamento e qualquer dado ainda não salvo.
    """
    corpo = _fonte('static/app.js')
    i = corpo.index("safeOn(document, 'epi:viewchange'")
    listener = corpo[i:corpo.index('resetModuleWizardsToInitial(nome);', i)]
    assert 'if (!nome || nome === anterior) {return;}' in listener, (
        'a guarda de mesma-view saiu do listener: o clique no menu do módulo '
        'ativo passaria a resetar, com perda silenciosa de dados'
    )
    # A decisão proíbe explicitamente um desvio por sinal de menu.
    assert 'viaMenu' not in listener, (
        'apareceu um desvio por sinal de menu, que a decisão de contrato proíbe'
    )
    # E a guarda precede qualquer reset — decidir depois de zerar não adianta.
    assert listener.index('nome === anterior') < listener.index('resetViewTabsToInitial(nav)'), (
        'a guarda deixou de preceder os resets'
    )
    # As outras duas exceções continuam com a semântica já definida.
    for sinal in ('viaHistorico', 'viaMultitab'):
        assert sinal in listener, f'a exceção {sinal} sumiu do listener'


# ── F5-B.1 — ATIVAÇÃO REDUNDANTE: cinco caminhos, uma única semântica ────────
#
# Contrato aprovado (#343): reativar a view que já está ativa não é sair e
# reentrar. Logo não é transição, e nenhum efeito colateral de transição pode
# ocorrer — recarregar a página, fechar UI transitória com trabalho não salvo,
# trocar aba interna, zerar rolagem, apagar a pilha de navegação.
#
# O comportamento é provado pelos gates `#343 F5-B.1 G-*` em
# `static/js/test/run-tests.js`, que partem do CLIQUE real no item de menu. Aqui
# ficam as propriedades estruturais que um teste de comportamento não fixa bem:
# a ORDEM entre guarda e efeito destrutivo, e a existência de uma semântica só.


def _bloco(rel: str, inicio: str, fim: str) -> str:
    corpo = _fonte(rel)
    i = corpo.index(inicio)
    j = corpo.find(fim, i)
    assert j > i, f'{rel}: bloco {inicio!r} mudou de forma'
    return corpo[i:j]


def test_f5b1_a_semantica_de_ativacao_redundante_e_unica_e_sem_fallback():
    """Uma função só, e sem fallback para a view padrão.

    O `dashboard.html` é servido com `class="view active"`. Um fallback para
    `defaultView()` — que `getCurrentView()` tem — faria a resposta ser
    `dashboard` mesmo sem view ativa nenhuma, e a PRIMEIRA navegação de verdade
    pareceria redundante: a tela nunca abriria.
    """
    corpo = _fonte('static/app.js')
    assert 'function ativacaoRedundanteDeView(view) {' in corpo, (
        'a semântica canônica de ativação redundante desapareceu do app.js'
    )
    bloco = _bloco('static/app.js', 'function viewAtivaNoDom()', 'function ativacaoRedundanteDeView')
    assert 'defaultView()' not in bloco, (
        'viewAtivaNoDom ganhou fallback para defaultView(): a primeira navegação '
        'para a view padrão passaria a ser tratada como redundante'
    )
    assert 'ativacaoRedundanteDeView,' in corpo, (
        'a semântica deixou de ser publicada em __EPI_APP_NAV_API__ — o multitab '
        'voltaria a ter uma resposta própria para a mesma pergunta'
    )


def test_f5b1_achado_a_a_guarda_precede_todo_efeito_de_transicao():
    """A guarda vem antes dos TRÊS efeitos, e fora de qualquer ramo.

    `location.assign` recarrega a página e leva embora o trabalho não salvo;
    `history.pushState` empilha entrada duplicada para a mesma URL e estraga o
    Voltar; `showView` emite `epi:viewchange` e dispara a atualização parcial.

    A primeira versão deste gate conferia só o `location.assign`, e por isso
    aceitou uma guarda que vivia DENTRO do ramo de
    `SPA_NAV_CLASSIC_FALLBACK_VIEWS` — sem alcançar nenhuma das oito views de
    `SPA_NAV_SUPPORTED_VIEWS`. Conferir a ordem contra `const canUseSpa` é o que
    prende a guarda no topo da função, onde ela alcança todos os caminhos.
    """
    bloco = _bloco('static/app.js', 'function navigateToView(view, options = {})',
                   'function bindSpaNavigationHistory')
    pos_guarda = bloco.find(
        'if (ativacaoRedundanteDeView(view) && options.recarregarMesmaView !== true) {return;}'
    )
    assert pos_guarda > -1, 'a guarda de ativação redundante saiu de navigateToView'
    for nome, agulha in (
        ('a bifurcação de SPA (`const canUseSpa`)', 'const canUseSpa ='),
        ('o recarregamento clássico (`location.assign`)', 'globalThis.location.assign('),
        ('o empilhamento de histórico (`history.pushState`)', 'globalThis.history.pushState('),
    ):
        pos = bloco.find(agulha)
        assert pos > -1, f'navigateToView mudou de forma: não achei {nome}'
        assert pos_guarda < pos, (
            f'a guarda passou a vir DEPOIS de {nome}: o efeito de transição '
            f'aconteceria antes de alguém decidir se devia acontecer'
        )


def test_f5b1_achado_b_ativacao_redundante_nao_fecha_ui_transitoria():
    """O multitab não fecha modal/dropdown quando nada transiciona.

    E o contrário também é gate: troca real de contexto CONTINUA fechando.
    Tornar `closeTransientUi()` inoperante seria trocar um defeito por outro.
    """
    bloco = _bloco('static/multitab-navigation.js', 'function activateTab(tabId, options)',
                   'function pushInternalNode')
    # A medida de redundância tem de existir e de ser lida pela saída antecipada
    # (gate próprio, abaixo). Aqui o que se fixa é a ORDEM em que ela é tirada.
    assert 'closeTransientUi();' in bloco, (
        'closeTransientUi deixou de ser chamado em activateTab: a troca real de '
        'contexto pararia de fechar dropdown, modal e painel transitório'
    )
    pos_medida = bloco.find('var redundante =')
    pos_troca = bloco.find('activeTabId = tab.id;')
    assert pos_medida > -1 and pos_troca > -1, 'activateTab mudou de forma'
    assert pos_medida < pos_troca, (
        'a medida de redundância passou para depois de `activeTabId = tab.id`: '
        'a aba corrente viraria a própria aba pedida e TODA ativação pareceria '
        'redundante — nenhuma troca fecharia mais nada'
    )
    corpo = _fonte('static/multitab-navigation.js')
    assert 'function closeTransientUi()' in corpo, (
        'closeTransientUi foi removido em vez de guardado'
    )


def test_f5b1_achado_c_a_aba_de_compras_tem_guarda_de_anterior():
    """O listener independente de Compras — o único dos cinco sem feature flag."""
    bloco = _bloco('static/app.js', "safeOn(document, 'epi:viewchange', (e) => {",
                   'function applyPhase3UiVisibility')
    assert "const redundante = e?.detail?.anterior === 'compras';" in bloco, (
        'a guarda de ativação redundante saiu do listener de Compras'
    )
    pos_guarda = bloco.find('!redundante')
    pos_troca = bloco.find('switchComprasTab(defaultTab)')
    assert pos_guarda > -1 and pos_troca > -1, 'o listener de Compras mudou de forma'
    assert pos_guarda < pos_troca, (
        'a troca de aba de Compras voltou a acontecer antes da guarda: clicar no '
        'menu de Compras estando em Compras descartaria a aba aberta'
    )


def test_f5b1_achado_d_a_rolagem_so_zera_em_entrada_de_verdade():
    bloco = _bloco('static/ux-phase44.js', 'function bindScrollPattern()', "safeOn(document, 'invalid'")
    pos_guarda = bloco.find('if (anterior && anterior === nextView) return;')
    pos_scroll = bloco.find('globalThis.scrollTo({ top: 0')
    assert pos_guarda > -1, 'a guarda de ativação redundante saiu do padrão de rolagem do phase44'
    assert pos_scroll > -1, 'bindScrollPattern mudou de forma'
    assert pos_guarda < pos_scroll, (
        'a rolagem volta ao topo antes da guarda decidir: o clique no menu do '
        'módulo ativo arrancaria o usuário de onde ele estava lendo'
    )


def test_f5b1_achado_e_a_pilha_de_raiz_so_reinicia_em_transicao_real():
    bloco = _bloco('static/navigation.js', "safeOn(document, 'epi:viewchange', function (event)",
                   "safeOn(document, 'click', function (event)")
    pos_guarda = bloco.find('if (anterior && anterior === view) {')
    pos_push = bloco.find('rootPush(view);')
    assert pos_guarda > -1, 'a guarda de ativação redundante saiu do listener da hierarquia'
    assert pos_push > -1, 'o listener da hierarquia mudou de forma'
    assert pos_guarda < pos_push, (
        'rootPush volta a rodar antes da guarda: `stack.length = 0` apagaria o '
        'caminho que o usuário percorreu dentro do módulo'
    )
    corpo = _fonte('static/navigation.js')
    assert 'stack.length = 0;' in corpo, (
        'rootPush foi esvaziado em vez de guardado: a transição real de raiz '
        'precisa continuar recomeçando a pilha'
    )


def test_f5b1_os_gates_do_gesto_partem_do_clique_real():
    """Nenhum gate do F5-B.1 pode fabricar a troca de view.

    Um `dispatchEvent(new CustomEvent('epi:viewchange', ...))` não passa por
    `navigateToView` nem por `activateTab` — foi esse atalho que deixou os cinco
    achados atravessarem os gates anteriores. A verificação também existe do
    lado JS (`G-real-cobertura`); aqui ela fica fora do alcance de quem edita só
    o runner.
    """
    corpo = (RAIZ / 'static/js/test/run-tests.js').read_text(encoding='utf-8')
    i = corpo.find('MARCA_INICIO_F5B1\n')
    j = corpo.find('MARCA_FIM_F5B1\n')
    assert i > -1 and j > i, 'as marcas da seção F5-B.1 sumiram do runner'
    secao = corpo[i:j]
    blocos = secao.split("\ntest('#343 F5-B.1 ")[1:]
    assert len(blocos) >= 11, f'esperava os gates do F5-B.1 no runner, encontrei {len(blocos)}'
    isentos = ('G-real-0', 'G-real-cobertura', 'G-real-contraprova')
    for bloco in blocos:
        nome = bloco[:bloco.index(':')]
        if nome in isentos:
            continue
        assert 'clicarNoItemDeMenu(' in bloco, (
            f'o gate "{nome}" não parte do clique real no item de menu'
        )
        # `'epi:viewchange'` entra na lista porque a fabricação não precisa de
        # helper nenhum: basta um `dispatchEvent(new CustomEvent(...))` dentro do
        # gate. Sem este item, trocar o clique pelo evento cru mantinha o gate
        # verde — exatamente o falso-verde que esta seção existe para impedir.
        for atalho in ('entrarNoModulo(', 'redesenharMesmaVista(',
                       'clicarNoMenuDaViewAtiva(', "'epi:viewchange'"):
            assert atalho not in bloco, (
                f'o gate "{nome}" fabrica a troca de view com `{atalho}`'
            )


def test_f5b1_a_insuficiencia_dos_gates_anteriores_esta_registrada():
    """A evidência antiga não é apagada — é datada.

    Os `G-menu-1/2/3` continuam no runner, porque o que provam é verdade. O que
    passou a estar escrito ao lado é o limite deles, para ninguém voltar a
    tratá-los como certificação do gesto de menu.
    """
    corpo = (RAIZ / 'static/js/test/run-tests.js').read_text(encoding='utf-8')
    for gate in ('G-menu-1', 'G-menu-2', 'G-menu-3'):
        assert gate in corpo, f'{gate} foi apagado: a evidência anterior não pode desaparecer sem registro'
    assert 'INSUFICIÊNCIA DESTES TRÊS GATES' in corpo, (
        'o registro de por que os G-menu não provavam o gesto de menu foi removido'
    )
    assert 'clicarNoMenuDaViewAtiva' in corpo, (
        'o helper que fabricava o evento sumiu junto com o registro: o texto '
        'precisa continuar dizendo o que ele fazia'
    )


def test_f5b1_achado_b_ativacao_redundante_e_no_op_inteiro():
    """Sair ANTES de redesenhar, e não só pular o fechamento da UI transitária.

    A primeira versão desta correção pulava apenas `closeTransientUi()` e deixava
    passar todo o resto de uma transição: `showView` com `partial: true` (que
    rebusca e redesenha o módulo), os rebinds, a animação e o `updateHistory`
    empilhando outra entrada — `onMenuIntercept` passa `historyMode: 'push'`.
    """
    bloco = _bloco('static/multitab-navigation.js', 'function activateTab(tabId, options)',
                   'function pushInternalNode')
    pos_saida = bloco.find("if (redundante && opts.restoreContext !== true) return;")
    assert pos_saida > -1, (
        'a saída antecipada da ativação redundante saiu do activateTab: o clique no '
        'menu do módulo ativo voltaria a redesenhar o módulo e a empilhar histórico'
    )
    for nome, agulha in (
        ('a atribuição de aba ativa', 'activeTabId = tab.id;'),
        ('o redesenho da view', 'navApi.showView('),
    ):
        pos = bloco.find(agulha)
        assert pos > -1, f'activateTab mudou de forma: não achei {nome}'
        assert pos_saida < pos, f'a saída antecipada passou para depois de {nome}'
    # `restoreContext` continua sendo a exceção — e não pode virar um `viaMenu`
    # ao contrário, valendo para qualquer chamador.
    assert 'viaMenu' not in _fonte('static/multitab-navigation.js'), (
        'apareceu um sinal de menu no multitab, que a decisão de contrato proíbe'
    )


def test_f5b1_achado_f_a_aba_de_avaliacoes_tem_guarda_de_anterior():
    """Sexto caminho, mesma classe do achado C, também sem feature flag."""
    # Fim no `bindAvaliacoesView();` — a CHAMADA, que vem depois do listener; a
    # definição da função vem antes dele e não serviria de âncora.
    bloco = _bloco('static/app.js', "if (e.detail?.view === 'avaliacoes') {", 'bindAvaliacoesView();')
    pos_guarda = bloco.find("if (e.detail?.anterior === 'avaliacoes') return;")
    assert pos_guarda > -1, 'a guarda de ativação redundante saiu do listener de Avaliações'
    for nome, agulha in (
        ("a aba unificada do admin", "showAvalTab('avaliacao-final')"),
        ("a aba de pendentes", "showAvalTab('pendentes')"),
    ):
        pos = bloco.find(agulha)
        assert pos > -1, f'o listener de Avaliações mudou de forma: não achei {nome}'
        assert pos_guarda < pos, (
            f'a troca para {nome} voltou a acontecer antes da guarda: o redesenho da '
            f'mesma view descartaria o trabalho da aba aberta'
        )


# Inventário FECHADO dos listeners de `epi:viewchange` na árvore servida.
#
# O sexto caminho (Avaliações) existia porque a auditoria da F5-B inventariou por
# módulo, e não por listener. Este mapa fecha a pergunta "falta algum?": cada
# registro está aqui com o veredito de por que é guardado ou inócuo, e um
# listener novo derruba o gate — obrigando a decisão em vez de deixá-la passar.
LISTENERS_DE_VIEWCHANGE = {
    # 3 em app.js: reset central da F5-B, aba de Compras (C), aba de Avaliações (F).
    'static/app.js': (3, 'os tres com guarda de `anterior`'),
    # rootPush da hierarquia (E).
    'static/navigation.js': (1, 'guarda de `anterior` (E)'),
    # rolagem (D) e rebind de view (idempotente por WeakSet).
    'static/ux-phase44.js': (2, 'rolagem com guarda (D); o rebind e idempotente'),
    # teardown de memoria/estado: guarda `view === anterior` desde a F5-B.
    'static/ux-phase42.js': (1, 'teardown com guarda de mesma-view'),
    'static/ux-phase43.js': (2, 'teardown com guarda de mesma-view; o rebind e idempotente'),
    # titulo da aba: tem guarda propria (`view !== tab.view` retorna).
    'static/multitab-navigation.js': (1, 'guarda propria de mesma-view'),
    # melhoria progressiva: nao mexe em estado de trabalho.
    'static/ux-global.js': (1, 'apenas enriquece o DOM da view'),
    # telemetria: registra o que aconteceu, nao muda estado.
    'static/ux-analytics.js': (1, 'apenas telemetria'),
    # breadcrumb proprio: a pilha tem dedup e os overlays sao do proprio modulo.
    'static/navigation-controls.js': (1, 'pilha com dedup; overlays do proprio modulo'),
}

REGISTRO_DE_VIEWCHANGE = re.compile(
    r"(?:safeOn|bindAppListener)\(\s*[^,]+,\s*'epi:viewchange'"
    r"|\.addEventListener\(\s*'epi:viewchange'"
)


def test_f5b1_o_inventario_de_listeners_de_viewchange_esta_fechado():
    """Um listener novo de `epi:viewchange` não entra em silêncio.

    Não é auditoria aberta: é uma lista enumerável. O gate não julga o novo
    listener — ele obriga alguém a classificá-lo, que foi exatamente o passo que
    faltou quando o de Avaliações entrou sem guarda.
    """
    for rel, (esperado, motivo) in LISTENERS_DE_VIEWCHANGE.items():
        corpo = _fonte(rel)
        achados = len(REGISTRO_DE_VIEWCHANGE.findall(corpo))
        assert achados == esperado, (
            f'{rel}: {achados} listeners de `epi:viewchange`, esperados {esperado} '
            f'({motivo}). Se o listener novo mexe em estado de trabalho, ele precisa '
            f'da guarda de `anterior`; se não mexe, atualize este inventário dizendo '
            f'por quê.'
        )


ARQUIVOS_PAREADOS_F5B = (
    # o reset na entrada do módulo + a remoção do epi_vtab_
    'static/app.js',
    # rolagem (F5-B); o rascunho de formulário fica para a F5-C
    'static/ux-phase41.js',
    # contexto de negócio sai do storage e vira RAM
    'static/ux-phase42.js',
    'static/ux-phase43.js',
    # filtros por view
    'static/ux-phase44.js',
    # restauração de contexto de aba vira opt-in (só ação explícita de multitab)
    'static/multitab-navigation.js',
    # F5-B.1: a pilha de raiz da hierarquia não é mais zerada em ativação
    # redundante da mesma view
    'static/navigation.js',
    # os gates comportamentais que provam o cenário
    'static/js/test/run-tests.js',
    # estes próprios gates
    'tests/test_343_f5b_navegacao_estado_inicial.py',
)

ESTE_ARQUIVO = 'tests/test_343_f5b_navegacao_estado_inicial.py'
PREFIXO_DO_DIGESTO = 'DIGESTO_PARIDADE_F5B = '

DIGESTO_PARIDADE_F5B = '38343fedcaea6098e6bf2c3426167afc915ca1fef60fcee36f5c6bbcaa5ffdfa'


def _bytes_para_o_digesto(rel: str) -> bytes:
    """Conteúdo de um arquivo coberto.

    Este arquivo se inclui na própria cobertura. Para isso a linha que carrega
    o dígito é removida antes de hashear: sem essa exclusão o valor dependeria
    de si mesmo e não existiria número que fechasse a conta.
    """
    bruto = (RAIZ / rel).read_bytes()
    if rel != ESTE_ARQUIVO:
        return bruto
    return b'\n'.join(
        linha for linha in bruto.split(b'\n')
        if not linha.startswith(PREFIXO_DO_DIGESTO.encode('utf-8'))
    )


def _digesto_dos_pareados() -> str:
    acumulador = hashlib.sha256()
    for rel in ARQUIVOS_PAREADOS_F5B:
        acumulador.update(rel.encode('utf-8'))
        acumulador.update(b'\x00')
        acumulador.update(_bytes_para_o_digesto(rel))
        acumulador.update(b'\x00')
    return acumulador.hexdigest()


def test_g11_os_arquivos_pareados_existem_todos():
    for rel in ARQUIVOS_PAREADOS_F5B:
        assert (RAIZ / rel).is_file(), f'arquivo pareado sumiu: {rel}'
    assert len(set(ARQUIVOS_PAREADOS_F5B)) == 9


def test_g11_index_html_nao_entra_na_igualdade_byte_a_byte():
    assert 'static/index.html' not in ARQUIVOS_PAREADOS_F5B, (
        'o index.html é gerado e seu cache-buster deriva do conteúdo, que já '
        'diverge entre os repositórios de propósito'
    )


def test_g11_paridade_f5b_entre_corporate_e_saas():
    """Um único dígito sobre os 9 arquivos do contrato da F5-B/F5-B.1.

    Os dois repositórios calculam o mesmo número e comparam com a mesma
    constante. Editar um lado sem o outro derruba o gate no lado editado.

    Limite conhecido, o mesmo do G7 da F4: quem editar um arquivo coberto E
    recalcular o dígito no mesmo repositório passa. O gate não impede a
    divergência — torna-a um ato deliberado e visível, porque exige mexer em
    dois arquivos em vez de um.
    """
    assert _digesto_dos_pareados() == DIGESTO_PARIDADE_F5B, (
        'os arquivos pareados da F5-B divergiram entre Corporate e SaaS (ou '
        'mudaram sem o dígito ser atualizado). Se a mudança foi deliberada, '
        'aplique-a nos DOIS repositórios e recalcule o dígito.'
    )
