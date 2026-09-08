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
    # os gates comportamentais que provam o cenário
    'static/js/test/run-tests.js',
    # estes próprios gates
    'tests/test_343_f5b_navegacao_estado_inicial.py',
)

ESTE_ARQUIVO = 'tests/test_343_f5b_navegacao_estado_inicial.py'
PREFIXO_DO_DIGESTO = 'DIGESTO_PARIDADE_F5B = '

DIGESTO_PARIDADE_F5B = '21065534b0d8dde7c10c2ad64c8b7b8e85a7688ceee218638ae2e9ea26abc2d7'


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
    assert len(set(ARQUIVOS_PAREADOS_F5B)) == 7


def test_g11_index_html_nao_entra_na_igualdade_byte_a_byte():
    assert 'static/index.html' not in ARQUIVOS_PAREADOS_F5B, (
        'o index.html é gerado e seu cache-buster deriva do conteúdo, que já '
        'diverge entre os repositórios de propósito'
    )


def test_g11_paridade_f5b_entre_corporate_e_saas():
    """Um único dígito sobre os 7 arquivos do contrato da F5-B.

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
