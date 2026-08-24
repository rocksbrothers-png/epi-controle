"""Configuração por Unidade + EPI no Web Legado/SaaS — a fatia B3 (#271).

Enquanto o legado estiver operacional ele segue o MESMO contrato do Flutter.
Deixar faixa de atenção e alerta exclusivos do app criaria duas experiências
com capacidades diferentes sobre a mesma regra — e é numa interface viva que
essa dívida cobra caro.

Este arquivo é o gate do lado JS. Ele protege cinco coisas que uma edição
bem-intencionada reabre em uma linha:

1. `minimum_stock` corporativo usado como mínimo OPERACIONAL da Unidade;
2. `stock` corporativo usado como saldo local;
3. recálculo de `saldo × mínimo` no cliente;
4. reconstrução local de `stock_status`;
5. lista hardcoded de perfis decidindo autorização.

Não há toolchain de teste JS aqui além do `run-tests.js`; estas checagens são
estáticas, sobre o fonte, e rodam junto do resto da suíte Python.
"""

import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
STATIC = RAIZ / 'static'

APP_JS = STATIC / 'app.js'
CONFIG_JS = STATIC / 'js' / 'views' / 'estoque-config.js'
ESTOQUE_JS = STATIC / 'js' / 'views' / 'estoque.js'
INDEX_HTML = STATIC / 'index.html'

#: O bloco da B3 dentro de `app.js`. Delimitado para que o gate cobre o código
#: NOVO com rigor sem reprovar o monólito inteiro, que tem 17 mil linhas de
#: histórico ainda não migrado.
MARCA_INICIO = '// ── Configuração de estoque por Unidade + EPI (#271-B3) ──'
MARCA_FIM = 'function stockEpiMatchesMovementSearch(item) {'


def _sem_comentarios(codigo: str) -> str:
    """Remove comentários de linha e de bloco.

    Os comentários desta fatia CITAM o defeito que removeram, para explicá-lo.
    Varrer com eles dentro reprovaria a própria correção — foi o que aconteceu
    com o detector da 1.1D-C4 na primeira versão.
    """
    sem_bloco = re.sub(r'/\*.*?\*/', '', codigo, flags=re.DOTALL)
    return '\n'.join(
        linha for linha in sem_bloco.splitlines()
        if not linha.lstrip().startswith('//') and not linha.lstrip().startswith('*')
    )


#: Os listeners da B3 ficam noutra região de `app.js` (junto do resto do bind
#: de eventos), então o gate precisa dos DOIS trechos. Cobrir só o primeiro
#: deixaria o comportamento do toggle fora da varredura — que é justamente o
#: ponto mais sensível da fatia.
MARCA_LISTENERS = '// ── Configuração por Unidade + EPI (#271-B3) ─────'
MARCA_LISTENERS_FIM = "bindAppListener(document.getElementById('stock-print-labels')"


def _bloco_da_b3() -> str:
    fonte = APP_JS.read_text(encoding='utf-8')
    i = fonte.index(MARCA_INICIO)
    f = fonte.index(MARCA_FIM)
    li = fonte.index(MARCA_LISTENERS)
    lf = fonte.index(MARCA_LISTENERS_FIM)
    return fonte[i:f] + '\n' + fonte[li:lf]


def _codigo_da_fatia() -> dict:
    return {
        'app.js (bloco B3)': _sem_comentarios(_bloco_da_b3()),
        'estoque-config.js': _sem_comentarios(CONFIG_JS.read_text(encoding='utf-8')),
    }


# ── Os arquivos existem e estão ligados ──────────────────────────────────────

def test_o_modulo_existe_e_esta_carregado_no_html():
    assert CONFIG_JS.exists()
    html = INDEX_HTML.read_text(encoding='utf-8')
    assert '/js/views/estoque-config.js' in html, \
        'o módulo não é carregado — a tela cairia no fallback de "sem regra"'


def test_os_tres_blocos_existem_no_html():
    """Paridade completa: mínimo, faixa e alerta, cada um com salvar e
    restaurar próprios — porque no backend cada um é rota separada."""
    html = INDEX_HTML.read_text(encoding='utf-8')
    for elemento in (
        'stock-config-unit',              # seletor de Unidade
        'stock-minimum-selected-value', 'stock-minimum-restore', 'stock-minimum-origin',
        'stock-attention-value', 'stock-attention-save', 'stock-attention-restore', 'stock-attention-origin',
        'stock-alert-toggle', 'stock-alert-save', 'stock-alert-restore', 'stock-alert-origin',
    ):
        assert f'id="{elemento}"' in html, f'{elemento} não existe no legado'


# ── 1. mínimo corporativo como mínimo operacional ────────────────────────────

def test_o_legado_le_o_minimo_da_unidade_e_nao_o_corporativo():
    """O defeito nº 1 do editor antigo.

    `minimum_stock` é o padrão da EMPRESA; `unit_minimum_stock` é o efetivo
    daquela Unidade. O campo antigo mostrava o primeiro, e o operador editava
    um número que não governava a Unidade dele.
    """
    config = _sem_comentarios(CONFIG_JS.read_text(encoding='utf-8'))
    assert 'unit_minimum_stock' in config, 'a leitura do mínimo por Unidade sumiu'
    # `minimum_stock` sozinho não pode aparecer como LEITURA nesta fatia. Como
    # chave de PAYLOAD ele é legítimo (é o nome do campo na rota), então a
    # busca é pelo acesso a propriedade do item.
    leituras = re.findall(r'\bitem\.minimum_stock\b|\bselected\.minimum_stock\b', config)
    assert not leituras, f'leitura do mínimo corporativo reintroduzida: {leituras}'

    bloco = _sem_comentarios(_bloco_da_b3())
    leituras_app = re.findall(r'\.minimum_stock\b(?!\s*:)', bloco)
    assert not leituras_app, \
        f'o bloco da B3 voltou a ler minimum_stock corporativo: {leituras_app}'


def test_a_gravacao_nao_contamina_o_cache_corporativo():
    """O defeito nº 4: `target.minimum_stock = minimumStock` gravava o valor da
    Unidade no campo corporativo do cache, contaminando a leitura seguinte.

    A fatia trocou isso por releitura do servidor."""
    bloco = _sem_comentarios(_bloco_da_b3())
    assert not re.search(r'\.minimum_stock\s*=', bloco), \
        'a gravação voltou a escrever no campo corporativo do cache local'


# ── 2. saldo corporativo como saldo local ────────────────────────────────────

def test_o_legado_nao_usa_saldo_corporativo_como_local():
    for nome, codigo in _codigo_da_fatia().items():
        # `unit_stock_quantity` é o saldo da Unidade; `stock` (legado) é o total
        # da empresa e não pode governar nada em contexto de Unidade.
        achados = re.findall(r'\bitem\.stock\b(?!_)|\bselected\.stock\b(?!_)', codigo)
        assert not achados, f'{nome}: saldo corporativo usado como local ({achados})'


# ── 3. recálculo saldo × mínimo ──────────────────────────────────────────────

def test_a_fatia_nao_recalcula_saldo_por_minimo():
    """Reusa o detector compartilhado da 1.1D-C4 em vez de uma segunda
    varredura: dois detectores divergem no primeiro ajuste feito num lado só —
    que é o defeito que estes gates existem para impedir."""
    from tests.stock_rule_scan import comparacoes_saldo_por_minimo

    for nome, codigo in _codigo_da_fatia().items():
        achados = comparacoes_saldo_por_minimo(codigo)
        assert not achados, f'{nome} recalcula saldo × mínimo: {achados}'


# ── 4. reconstrução local de stock_status ────────────────────────────────────

def test_o_status_e_lido_e_nunca_derivado():
    """`stock_status` chega pronto de `/api/stock/epis`.

    O módulo TRADUZ a chave para rótulo (o texto tem que sair do i18n, senão o
    legado fala português nos outros idiomas), mas não decide qual chave é.
    Chave desconhecida devolve vazio — nunca 'normal'.
    """
    config = _sem_comentarios(CONFIG_JS.read_text(encoding='utf-8'))
    assert 'item.stock_status' in config, 'o status deixou de ser lido do backend'
    # Nenhuma atribuição a stock_status: traduzir é ler, decidir é derivar.
    assert not re.search(r'stock_status\s*=\s*[^=]', config), \
        'stock_status passou a ser atribuído no cliente'
    # E o desconhecido não vira normal.
    assert "default: return '';" in config, \
        'a chave desconhecida deixou de cair em vazio — pode estar virando normal'


def test_o_limite_de_atencao_nao_e_calculado_no_cliente():
    """`attention_limit` é `ceil(mínimo × (1 + pct/100))` com Decimal no
    servidor. Refazer a conta em JS produz divergência de arredondamento."""
    for nome, codigo in _codigo_da_fatia().items():
        assert not re.search(r'Math\.ceil\s*\([^)]*attention', codigo, re.I), \
            f'{nome}: o limite da faixa voltou a ser calculado no cliente'
        assert not re.search(r'attention_limit\s*=\s*[^=]', codigo), \
            f'{nome}: attention_limit passou a ser atribuído localmente'


# ── 5. lista hardcoded de perfis ─────────────────────────────────────────────

def test_a_autorizacao_usa_permissao_e_nao_lista_de_papeis():
    """O defeito nº 5: `canManageMinimumStock()` testava `['admin','user']` e
    escondia o editor do Administrador Geral, que o backend autoriza."""
    config = _sem_comentarios(CONFIG_JS.read_text(encoding='utf-8'))
    assert "includes('stock:adjust')" in config, \
        'a permissão real deixou de ser consultada'

    for nome, codigo in _codigo_da_fatia().items():
        achados = re.findall(
            r"\[\s*'(?:admin|user|general_admin|registry_admin|master_admin)'[^\]]*\]",
            codigo,
        )
        assert not achados, f'{nome}: lista hardcoded de perfis reintroduzida ({achados})'


def test_a_funcao_antiga_por_papel_foi_removida():
    fonte = APP_JS.read_text(encoding='utf-8')
    assert not re.search(r'^function canManageMinimumStock\(', fonte, re.M), \
        'canManageMinimumStock voltou — use canManageStockConfig(), que lê a permissão'


# ── Escopo de Unidade ────────────────────────────────────────────────────────

def test_a_unidade_vem_do_selectable_e_nunca_de_lista_local():
    config = _sem_comentarios(CONFIG_JS.read_text(encoding='utf-8'))
    assert '/api/units/selectable' in config
    bloco = _sem_comentarios(_bloco_da_b3())
    assert 'state.units' not in bloco, \
        'a lista de Unidades voltou a sair do bootstrap, que é recortado só por tenant'


def test_todas_as_unidades_nunca_aparece_em_escrita():
    """Não existe gravar configuração em todas as Unidades."""
    config = _sem_comentarios(CONFIG_JS.read_text(encoding='utf-8'))
    corpo = config.split('function initialUnitSelection', 1)[1].split('\n}', 1)[0]
    assert 'allowsAllUnits' not in corpo, \
        'a pré-seleção passou a considerar "Todas" — isto é superfície de escrita'
    bloco = _sem_comentarios(_bloco_da_b3())
    assert 'allowsAllUnits' not in bloco, \
        'o seletor do legado passou a oferecer "Todas" em escrita'


def test_perfil_travado_nao_escolhe_unidade():
    config = _sem_comentarios(CONFIG_JS.read_text(encoding='utf-8'))
    corpo = config.split('function acceptUnit', 1)[1].split('\n  }', 1)[0]
    assert 'scope.locked' in corpo, \
        'acceptUnit deixou de tratar perfil travado — ele poderia escolher outra Unidade'


def test_gravar_exige_unidade_real_selecionada():
    config = _sem_comentarios(CONFIG_JS.read_text(encoding='utf-8'))
    corpo = config.split('function canWrite', 1)[1].split('\n  }', 1)[0]
    assert 'blocksEverything' in corpo, 'carteira vazia deixou de bloquear'
    assert 'scope.units.some' in corpo, \
        'canWrite aceita Unidade fora da lista que o servidor ofereceu'


def test_a_gravacao_confere_que_o_par_e_da_unidade_escolhida():
    """Isolamento: o seletor e a listagem podem divergir por um instante, e
    gravar nessa janela aplicaria à Unidade escolhida um valor lido da outra."""
    bloco = _sem_comentarios(_bloco_da_b3())
    assert 'Number(params.unitId) !== Number(state.stockConfigUnitId)' in bloco, \
        'a guarda de consistência entre seletor e listagem sumiu'


# ── As seis rotas ────────────────────────────────────────────────────────────

ROTAS = (
    '/api/stock/minimum',
    '/api/stock/minimum/restore-default',
    '/api/stock/attention-percentage',
    '/api/stock/attention-percentage/restore-default',
    '/api/stock/alert-enabled',
    '/api/stock/alert-enabled/restore-default',
)


def test_as_seis_rotas_estao_no_legado():
    config = CONFIG_JS.read_text(encoding='utf-8')
    for rota in ROTAS:
        assert f"'{rota}'" in config, f'{rota} não é chamada pelo legado'


def test_toda_gravacao_transporta_a_unidade():
    """O defeito nº 2: sem `unit_id`, o Administrador Geral tomava 400."""
    config = _sem_comentarios(CONFIG_JS.read_text(encoding='utf-8'))
    for construtor in ('minimumPayload', 'attentionPayload', 'alertPayload', 'restorePayload'):
        corpo = config.split(f'function {construtor}', 1)[1].split('\n  }', 1)[0]
        assert 'unit_id' in corpo, f'{construtor} não envia unit_id'


def test_restaurar_e_rota_distinta_de_salvar():
    """Salvar 20 e restaurar para 20 terminam com o mesmo número e significam
    coisas opostas — por isso o backend tem rota separada, e o cliente também."""
    config = CONFIG_JS.read_text(encoding='utf-8')
    for par in (('minimum', 'minimumRestore'), ('attention', 'attentionRestore'), ('alert', 'alertRestore')):
        assert all(chave in config for chave in par)


# ── Origem, alerta e limites ─────────────────────────────────────────────────

def test_as_tres_origens_do_contrato_estao_mapeadas():
    config = CONFIG_JS.read_text(encoding='utf-8')
    for valor in ('unit_configured', 'company_default', 'system_default'):
        assert f"'{valor}'" in config, f'origem {valor} não é reconhecida'


def test_restaurar_so_e_oferecido_quando_ha_decisao_local():
    config = _sem_comentarios(CONFIG_JS.read_text(encoding='utf-8'))
    corpo = config.split('function canRestore', 1)[1].split('\n', 1)[0]
    assert 'SOURCE_UNIT' in corpo, \
        'restaurar passou a ser oferecido para parâmetro herdado, onde é no-op'


def test_o_toggle_de_alerta_nao_grava_sozinho():
    """Silenciar o alerta é decisão operacional: o toggle mexe no rascunho e a
    persistência acontece no Salvar."""
    bloco = _sem_comentarios(_bloco_da_b3())
    listener = bloco.split("getElementById('stock-alert-toggle'), 'change'", 1)
    assert len(listener) > 1, 'o listener do toggle sumiu'
    corpo = listener[1].split('});', 1)[0]
    assert 'stockAlertEditor.draft' in corpo
    for rota in ('/api/stock/alert-enabled',):
        assert rota not in corpo, 'o toggle voltou a persistir sozinho'


def test_desligar_o_alerta_pede_confirmacao():
    config = _sem_comentarios(CONFIG_JS.read_text(encoding='utf-8'))
    corpo = config.split('function alertNeedsConfirmation', 1)[1].split('\n  }', 1)[0]
    assert 'currentEnabled === true && draftEnabled === false' in corpo, \
        'a condição da confirmação mudou — ligar não deve perguntar, desligar deve'
    bloco = _sem_comentarios(_bloco_da_b3())
    trecho = bloco.split('alertNeedsConfirmation', 1)[1]
    assert trecho.index('confirm(') < trecho.index('STOCK_CONFIG_ROUTES.alert'), \
        'a confirmação precisa vir ANTES do POST'


def test_o_minimo_nao_ganha_teto_no_cliente():
    """O backend faz `max(0, int(...))` e não publica teto."""
    config = _sem_comentarios(CONFIG_JS.read_text(encoding='utf-8'))
    corpo = config.split('function validateMinimum', 1)[1].split('\n  }', 1)[0]
    assert 'n < 0' in corpo
    assert not re.search(r'n\s*>\s*\d+', corpo), \
        'apareceu um teto para o mínimo que o backend não define'


def test_o_percentual_usa_o_teto_publicado():
    from modules.stock.service import MAX_ATTENTION_PERCENTAGE
    assert MAX_ATTENTION_PERCENTAGE == 100
    config = _sem_comentarios(CONFIG_JS.read_text(encoding='utf-8'))
    corpo = config.split('function validateAttention', 1)[1].split('\n  }', 1)[0]
    assert 'n > 100' in corpo


# ── Defeitos residuais do editor antigo ──────────────────────────────────────

def test_a_recarga_duplicada_foi_removida():
    """`await loadStockEpis(); await loadStockEpis();` — duas vezes seguidas."""
    bloco = _sem_comentarios(_bloco_da_b3())
    assert not re.search(r'loadStockEpis\(\);\s*await\s+loadStockEpis\(\);', bloco), \
        'a recarga duplicada voltou'


def test_os_derivados_sao_relidos_do_servidor_apos_gravar():
    """As respostas de escrita trazem só o campo alterado e a origem; os
    derivados são recalculados PELO SERVIDOR e chegam na releitura."""
    bloco = _sem_comentarios(_bloco_da_b3())
    corpo = bloco.split('async function runStockConfigWrite', 1)[1].split('\n}', 1)[0]
    assert 'await loadStockEpis()' in corpo, \
        'a releitura sumiu — os derivados ficariam velhos ou seriam calculados aqui'


def test_a_view_de_leitura_nao_foi_alterada():
    """`estoque.js` já foi migrado na 1.1D-C3 e está fora do escopo da B3.

    Ele continua sendo a prova de que a LEITURA consome a classificação pronta;
    mexer nele nesta fatia misturaria duas migrações.
    """
    fonte = ESTOQUE_JS.read_text(encoding='utf-8')
    assert 'unit_minimum_stock' in fonte and 'attention_limit' in fonte
    assert 'stock-config' not in fonte, \
        'a view de leitura passou a conhecer a configuração — separe as camadas'
