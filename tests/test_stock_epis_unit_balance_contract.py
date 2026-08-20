"""Fonte única de estoque: `/api/stock/epis` (#258, fatia 1.1B).

O defeito de origem estava numa linha só, em `handle_get_stock_epis`:

    item['stock'] = (stock_row or {}).get('quantity') or item['stock']

O `or` é *truthiness*, não "ausência". Uma unidade com saldo **0** caía no
segundo operando e recebia o total da EMPRESA. O mesmo campo mudava de
significado conforme o valor — e quatro pontos do Web Legado liam esse campo
como saldo local, entre eles a **Entrega de EPI**, que passava a liberar
entrega de um EPI que a unidade não tem.

A correção separa as grandezas em campos próprios:

- `stock` / `company_stock_quantity` — saldo CORPORATIVO, um significado só;
- `unit_stock_quantity` — saldo da unidade resolvida, `None` (nunca 0) quando
  não há unidade;
- `unit_scope_id` — a unidade usada, `None` exatamente quando o saldo é `None`;
- `is_company_stock_critical` — criticidade calculada no BACKEND, corporativa.

Estes testes leem o código-fonte porque o defeito é de contrato entre camadas:
nenhuma das pontas o enxerga sozinha, e um teste de unidade do handler não
impediria o Web Legado de voltar a ler `stock` como saldo local.
"""

import pathlib
import re

import pytest

RAIZ = pathlib.Path(__file__).resolve().parent.parent
ROUTES = RAIZ / 'modules/stock/routes.py'
APP_JS = RAIZ / 'static/app.js'
EPI_MODEL = RAIZ / 'flutter/packages/epi_api/lib/models/epi.dart'
STOCK_API = RAIZ / 'flutter/packages/epi_api/lib/endpoints/stock_api.dart'
STOCK_CUBIT = RAIZ / 'flutter/apps/epi_admin/lib/core/bloc/stock_cubit.dart'
STOCK_SCREEN = RAIZ / 'flutter/apps/epi_admin/lib/features/stock/stock_screen.dart'


def _handler() -> str:
    texto = ROUTES.read_text(encoding='utf-8')
    inicio = texto.index('def handle_get_stock_epis')
    fim = texto.index('\ndef ', inicio + 1)
    return texto[inicio:fim]


def _sem_comentarios_py(fonte: str) -> str:
    """Descarta comentários: eles CITAM o padrão proibido para explicá-lo."""
    return '\n'.join(
        linha for linha in fonte.split('\n')
        if not linha.lstrip().startswith('#')
    )


def _sem_comentarios_js(fonte: str) -> str:
    return '\n'.join(
        linha for linha in fonte.split('\n')
        if not linha.lstrip().startswith(('//', '*', '/*'))
    )


# ── o campo `stock` tem UM significado ───────────────────────────────────────

def test_o_fallback_por_truthiness_nao_existe_mais():
    """Nenhum caminho leva do saldo da unidade ao total da empresa.

    Cuidado com o alvo: `.get('quantity') or 0` é legítimo e continua no
    código — traduz "não há linha em `unit_epi_stock`" para zero, que é o saldo
    correto de uma unidade sem movimento. O defeito era cair no valor
    CORPORATIVO, e é exatamente isso que se proíbe aqui.
    """
    corpo = _sem_comentarios_py(_handler())
    proibidos = (
        "or item['stock']",
        'or company_stock',
        "or epi['stock']",
        "or item.get('stock')",
    )
    for padrao in proibidos:
        assert padrao not in corpo, (
            f'voltou o fallback por truthiness (`{padrao}`): saldo 0 da unidade '
            'cairia no total da empresa'
        )
    # E `stock` não é montado com nenhum fallback, seja qual for o operando.
    assert re.search(r"item\['stock'\]\s*=\s*[^\n]*\bor\b", corpo) is None, \
        "`stock` recebeu um valor com fallback — deve ser só o corporativo"


def test_stock_recebe_exatamente_o_valor_corporativo():
    corpo = _sem_comentarios_py(_handler())
    assert "item['stock'] = company_stock" in corpo
    assert "item['company_stock_quantity'] = company_stock" in corpo, \
        'os dois campos devem carregar o MESMO valor corporativo'


def test_o_saldo_corporativo_vem_do_epi_e_nao_da_unidade():
    corpo = _sem_comentarios_py(_handler())
    assert "company_stock = int(item.get('stock') or 0)" in corpo, \
        'o corporativo deixou de ser lido do próprio EPI'
    # E é lido ANTES de qualquer consulta ao estoque da unidade, para não haver
    # como sobrescrevê-lo com o saldo local.
    assert corpo.index('company_stock =') < corpo.index('get_unit_stock(')


# ── saldo da unidade: 0 é saldo, None é ausência de unidade ──────────────────

def test_unidade_sem_linha_de_estoque_recebe_zero_nao_none():
    # O EPI é visível para a unidade e o saldo é conhecido: é zero. `None` ali
    # faria a tela dizer "não há unidade" para uma unidade que existe.
    corpo = _sem_comentarios_py(_handler())
    assert "unit_stock = int((stock_row or {}).get('quantity') or 0)" in corpo


def test_sem_unidade_resolvida_o_saldo_local_e_none():
    corpo = _sem_comentarios_py(_handler())
    ramo_else = corpo[corpo.index('else:', corpo.index('stock_unit_id:')):]
    assert 'unit_stock = None' in ramo_else, \
        'zero afirmaria "esta unidade não tem estoque"; não há unidade'
    assert 'size_rows = []' in ramo_else


def test_unit_scope_id_e_none_exatamente_quando_nao_ha_unidade():
    corpo = _sem_comentarios_py(_handler())
    assert "item['unit_scope_id'] = stock_unit_id or None" in corpo, \
        'o par (saldo, escopo) precisa ser coerente: os dois nulos, ou nenhum'


def test_a_unidade_do_saldo_e_a_mesma_da_visibilidade():
    # Calcular o saldo numa unidade e filtrar a visibilidade GLOBAL/JV noutra
    # devolveria o saldo de uma unidade que o EPI nem enxerga.
    corpo = _sem_comentarios_py(_handler())
    assert 'stock_unit_id = int(unit_filter or 0)' in corpo
    assert 'target_unit_id=unit_filter' in corpo


# ── criticidade: corporativa, calculada no servidor ──────────────────────────

def test_a_criticidade_e_calculada_no_backend_contra_o_saldo_corporativo():
    corpo = _sem_comentarios_py(_handler())
    assert "item['is_company_stock_critical'] = is_stock_critical(company_stock, minimum_stock)" in corpo


def test_o_saldo_da_unidade_nunca_e_comparado_com_o_minimo_da_empresa():
    """O defeito é o PAR errado, não o operando `unit_stock`.

    Até a 1.1D-B0 este teste proibia `is_stock_critical(unit_stock` inteiro,
    porque o único mínimo existente era o corporativo — então qualquer uso do
    saldo local ali era necessariamente o cruzamento errado. Com o mínimo por
    Unidade, `is_stock_critical(unit_stock, unit_minimum.value)` passou a ser
    exatamente a comparação CERTA, e o alvo se estreita para o que sempre foi
    o defeito: saldo de UMA unidade contra o mínimo da EMPRESA, que marcaria
    como crítico todo EPI cujo estoque esteja distribuído.
    """
    corpo = _sem_comentarios_py(_handler())
    proibidos = (
        'is_stock_critical(unit_stock, minimum_stock)',
        "is_stock_critical(unit_stock, item['minimum_stock'])",
        "is_stock_critical(unit_stock, item.get('minimum_stock'))",
        'is_stock_critical(unit_stock, epi',
    )
    for padrao in proibidos:
        assert padrao not in corpo, (
            f'`{padrao}` cruza saldo da unidade com mínimo corporativo — use '
            '`resolve_unit_minimum_stock` para obter o mínimo DAQUELA unidade'
        )


def test_a_criticidade_operacional_usa_o_minimo_da_propria_unidade():
    """Na #271 a resolução do mínimo foi absorvida pelo classificador único.

    O handler não chama mais `resolve_unit_minimum_stock` direto — chama
    `classify_unit_epi_stock`, que o usa internamente junto com o percentual de
    atenção e a habilitação do alerta. O contrato que importa é o mesmo: a
    criticidade operacional não pode sair de um mínimo que não seja o da
    unidade resolvida.
    """
    corpo = _sem_comentarios_py(_handler())
    assert 'classify_unit_epi_stock(' in corpo, (
        'a criticidade operacional voltou a ser montada fora da fonte única'
    )
    assert "classificacao.stock_status == 'critical'" in corpo, (
        '`is_unit_stock_critical` deixou de derivar do status classificado'
    )
    # E o handler não recalcula nenhuma das duas comparações por conta própria.
    assert 'is_stock_critical(unit_stock' not in corpo
    assert 'attention_limit =' not in corpo


def test_os_campos_por_unidade_sao_nulos_juntos():
    """Todos os campos por Unidade são `None` exatamente quando não há unidade.

    Nunca 0/False isolados: `0` afirmaria "mínimo zero", `False` afirmaria
    "não crítico" e `'normal'` afirmaria "estoque saudável" — três mentiras
    sobre uma unidade que nem foi resolvida.
    """
    # Espaços colapsados: a atribuição pode estar quebrada em várias linhas por
    # comprimento, e isso não muda o contrato.
    corpo = re.sub(r'\s+', ' ', _sem_comentarios_py(_handler()))
    campos = (
        'unit_minimum_stock', 'minimum_stock_source',
        'effective_attention_percentage', 'attention_percentage_source',
        'attention_limit', 'stock_alert_enabled', 'alert_source',
        'underlying_status', 'stock_status', 'is_unit_stock_critical',
    )
    for campo in campos:
        assert re.search(
            rf"item\['{campo}'\] = [^;]*?if classificacao else None", corpo
        ), f'`{campo}` deixou de ser None quando não há unidade resolvida'


def test_disabled_nunca_e_emitido_como_normal():
    """O par `stock_status`/`underlying_status` é o que impede um EPI com
    alerta desligado de aparecer como saudável."""
    corpo = _sem_comentarios_py(_handler())
    assert "item['stock_status'] = classificacao.stock_status" in corpo
    assert "item['underlying_status'] = classificacao.underlying_status" in corpo, (
        'sem `underlying_status` o cliente teria de comparar saldo com mínimo '
        'para explicar um EPI desabilitado — a segunda fórmula que a #271 elimina'
    )


def test_o_minimo_efetivo_passa_pelo_helper_compartilhado():
    corpo = _sem_comentarios_py(_handler())
    assert "resolve_minimum_stock(item.get('minimum_stock'))" in corpo
    assert "item['minimum_stock'] = minimum_stock" in corpo, \
        'o cliente precisa receber o mínimo já resolvido, não o NULL cru'


def test_o_handler_importa_a_regra_em_vez_de_reescreve_la():
    texto = ROUTES.read_text(encoding='utf-8')
    assert 'is_stock_critical' in texto and 'resolve_minimum_stock' in texto
    corpo = _sem_comentarios_py(_handler())
    assert '<= minimum_stock' not in corpo and '<= int(' not in corpo, \
        'a comparação foi reintroduzida inline e vai divergir de /api/stock/low'


# ── o Flutter consome, e não recalcula ───────────────────────────────────────

@pytest.mark.parametrize('campo', [
    'unit_stock_quantity',
    'company_stock_quantity',
    'unit_scope_id',
    'is_company_stock_critical',
    'size_balances',
])
def test_cada_campo_novo_do_backend_tem_leitura_no_modelo_dart(campo):
    # Campo emitido e não lido chega e é descartado em silêncio.
    modelo = EPI_MODEL.read_text(encoding='utf-8')
    corpo = _sem_comentarios_py(_handler())
    assert f"item['{campo}']" in corpo or f"'{campo}'" in corpo
    assert f"json['{campo}']" in modelo, f'Epi.fromJson não lê {campo}'


def test_o_cubit_nao_le_mais_o_bootstrap():
    cubit = STOCK_CUBIT.read_text(encoding='utf-8')
    corpo = '\n'.join(
        linha for linha in cubit.split('\n')
        if not linha.lstrip().startswith(('///', '//'))
    )
    assert 'fetchStock()' not in corpo, \
        'o cubit voltou a ler bootstrap.epis — a fonte deixou de ser única'
    assert 'fetchStockEpis(' in corpo
    # Layering: o cubit fala só com o repositório.
    for proibido in ('ApiClient.', 'Dio(', 'bootstrap'):
        assert proibido not in corpo, f'{proibido} não pode aparecer no cubit'


def test_o_cubit_usa_a_criticidade_do_backend_e_nao_a_local():
    cubit = STOCK_CUBIT.read_text(encoding='utf-8')
    corpo = '\n'.join(
        linha for linha in cubit.split('\n')
        if not linha.lstrip().startswith(('///', '//'))
    )
    assert 'isCompanyStockCritical' in corpo
    assert 'isCriticalStock' not in corpo, \
        'o getter depreciado compara campos de escopos diferentes'


def test_a_tela_mostra_o_saldo_da_unidade_e_rotula_o_corporativo_a_parte():
    tela = STOCK_SCREEN.read_text(encoding='utf-8')
    assert 'unitStockQuantity' in tela
    # Dois números com rótulos diferentes: sem rótulo, o operador não sabe se o
    # que está vendo é da unidade dele ou da empresa toda.
    assert 'stockUnitBalanceSuffix' in tela
    assert 'stockCompanyBalanceLabel' in tela


def test_o_dart_nao_manda_company_id_nem_unit_id_para_a_rota():
    api = STOCK_API.read_text(encoding='utf-8')
    inicio = api.index('fetchStockEpis')
    fim = api.index('fetchAvailableItems')
    trecho = '\n'.join(
        linha for linha in api[inicio:fim].split('\n')
        if not linha.lstrip().startswith(('///', '//'))
    )
    assert 'company_id' not in trecho, 'escopo de empresa é do servidor'
    assert 'unit_id' not in trecho, 'a unidade é derivada do ator no servidor'


def test_os_filtros_vao_para_o_servidor():
    # Refazer o filtro no cliente divergiria do backend em acentuação e
    # maiúsculas: a mesma busca daria resultados diferentes no app e no Web.
    api = STOCK_API.read_text(encoding='utf-8')
    corpo = api[api.index('fetchStockEpis'):api.index('fetchAvailableItems')]
    for filtro in ('name', 'section', 'manufacturer', 'ca', 'protection'):
        assert f"'{filtro}'" in corpo, f'filtro {filtro} não chega na query'

    handler = _sem_comentarios_py(_handler())
    for filtro in ('name', 'section', 'manufacturer', 'ca', 'protection'):
        assert f"query.get('{filtro}'" in handler, \
            f'o backend não aplica o filtro {filtro}'


# ── Web Legado: operação por unidade lê o saldo da unidade ───────────────────

def _js_sem_comentarios() -> str:
    return _sem_comentarios_js(APP_JS.read_text(encoding='utf-8'))


def test_existe_um_unico_ponto_que_resolve_o_saldo_local_no_web():
    js = _js_sem_comentarios()
    assert 'function unitStockOf(' in js, \
        'sem um helper único, cada tela reimplementa a resolução do saldo'


def test_o_helper_do_web_nao_usa_fallback_por_truthiness():
    js = APP_JS.read_text(encoding='utf-8')
    inicio = js.index('function unitStockOf(')
    corpo = js[inicio:js.index('\n}', inicio)]
    # A decisão é pela PRESENÇA do escopo, não pelo valor do saldo.
    assert 'unit_scope_id === null' in corpo
    assert 'unit_scope_id === undefined' in corpo
    assert 'unit_stock_quantity ??' in corpo, \
        '`??` cobre só null/undefined; `||` trataria 0 como ausente'
    assert '|| item.company_stock_quantity' not in corpo


def _corpo_da_funcao_js(nome: str) -> str:
    """Corpo exato de uma função JS, por contagem de chaves.

    Uma janela de N caracteres a partir do `function` não serve: ela pega
    trechos de funções vizinhas (um `unitStockOf(` da função seguinte faria o
    teste passar sobre uma Entrega já quebrada — foi o que aconteceu na
    primeira versão deste teste, verificada por sabotagem) e, ao mesmo tempo,
    corta funções maiores que a janela.
    """
    js = _js_sem_comentarios()
    inicio = js.index(f'function {nome}')
    abertura = js.index('{', inicio)
    profundidade = 0
    for pos in range(abertura, len(js)):
        if js[pos] == '{':
            profundidade += 1
        elif js[pos] == '}':
            profundidade -= 1
            if profundidade == 0:
                return js[abertura:pos + 1]
    raise AssertionError(f'chaves desbalanceadas em {nome}')


# Leitura de saldo corporativo: `x.stock`, `x?.stock`, `x['stock']`.
_LE_STOCK = re.compile(r"""[\w\])]\??\.stock\b|\[\s*['"]stock['"]\s*\]""")


def test_a_entrega_de_epi_usa_exclusivamente_o_saldo_da_unidade():
    # O ponto mais crítico da fatia: liberar a entrega de um EPI que a unidade
    # não tem, porque o saldo exibido era o da empresa inteira.
    corpo = _corpo_da_funcao_js('populateDeliveryEpiField')
    assert 'unitStockOf(' in corpo, 'a Entrega voltou a ler outro saldo'
    assert _LE_STOCK.search(corpo) is None, \
        'a Entrega de EPI voltou a usar `stock` (corporativo) como saldo local'


@pytest.mark.parametrize('funcao', [
    'refreshStockMovementItemsFromLocal',
    'renderStockEpiSearchResults',
    'populateDeliveryEpiField',
])
def test_nenhuma_tela_operacional_de_unidade_le_stock_como_saldo_local(funcao):
    corpo = _corpo_da_funcao_js(funcao)
    assert 'unitStockOf(' in corpo, f'{funcao} não usa o saldo da unidade'
    assert _LE_STOCK.search(corpo) is None, \
        f'{funcao} lê `stock` (corporativo) numa operação por unidade'


# Nome de função que TERMINA numa palavra de saldo: `legadoStock(`,
# `saldoDoItem(`… `renderStockEpiSearchResults(` não entra — tem "Stock" no
# meio e é render, não resolução de saldo. (Foi o falso positivo da primeira
# versão desta regex.)
_RESOLVE_SALDO = re.compile(r'\b(\w*(?:Stock|Saldo|Balance)(?:Of)?)\s*\(')


def test_so_o_helper_resolve_o_saldo_local():
    # Contra a variante que os testes acima não pegam: a função continua
    # chamando `unitStockOf` — passando naquela asserção — mas passa a chamar
    # TAMBÉM um segundo helper que volta a ler `stock`.
    for funcao in ('populateDeliveryEpiField',
                   'refreshStockMovementItemsFromLocal',
                   'renderStockEpiSearchResults'):
        corpo = _corpo_da_funcao_js(funcao)
        chamadas = set(_RESOLVE_SALDO.findall(corpo))
        assert chamadas <= {'unitStockOf'}, (
            f'{funcao} resolve saldo por outro caminho além de unitStockOf: '
            f'{sorted(chamadas - {"unitStockOf"})}'
        )

# O rebuild de `index.html` NÃO é verificado aqui: `index.html` referencia
# `/app.js?v=<hash>` em vez de embutir o bundle, e `test_index_html_build.py`
# já falha quando o hash está velho (verificado por sabotagem). Um teste a mais
# procurando `unitStockOf` dentro do HTML só passaria a impressão de cobertura.
