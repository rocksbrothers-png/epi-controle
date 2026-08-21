"""1.1D-C3 — o Web Legado/SaaS consome a classificação que o backend já dá.

Até esta fatia o Legado ignorava a classificação por Unidade INTEIRA. Uma
varredura por `stock_status|attention_limit|unit_minimum_stock` em `static/`
devolvia zero ocorrências. A tela de Estoque exibia saldo e mínimo
CORPORATIVOS como se fossem os números operacionais da Unidade, e a lista
"Estoque baixo" classificava por `severity` — uma terceira régua, derivada no
backend de `stock <= 0` / `stock < minimum`, independente da classificação.

Nenhuma mudança de backend: `/api/stock/epis` e `/api/stock/low` já emitiam
todos os campos, com comentário no código dizendo "até os consumidores
migrarem". Esta fatia É essa migração.

O comportamento está coberto pelo harness JS (`static/js/test/run-tests.js`),
que exercita as funções de verdade. Estes testes cobrem o que o harness não
alcança: garantir que a regra não RETORNE ao JavaScript.
"""

import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
ESTOQUE_JS = RAIZ / 'static' / 'js' / 'views' / 'estoque.js'
ESTOQUE_HTML = RAIZ / 'static' / 'views' / 'estoque.html'
ESTILOS = RAIZ / 'static' / 'styles.css'

# Todo o JavaScript de tela do Legado.
FONTES_JS = sorted((RAIZ / 'static' / 'js').rglob('*.js')) + [RAIZ / 'static' / 'app.js']

TERMOS_SALDO = ('stock', 'saldo', 'quantity', 'qty')
TERMOS_MINIMO = ('minim',)  # cobre minimum, minimo, mínimo, minimumStock
COMPARADORES = ('<=', '>=', '<', '>')


def _sem_comentarios(texto):
    """Remove comentários de linha e de bloco.

    Os comentários desta fatia CITAM a comparação removida para explicá-la —
    varrer com eles dentro reprovaria a própria correção. Foi assim que a
    âncora da #271 virou falso positivo: ela passou a casar com a prosa em vez
    do código.
    """
    sem_bloco = re.sub(r'/\*.*?\*/', '', texto, flags=re.DOTALL)
    return '\n'.join(
        linha for linha in sem_bloco.splitlines()
        if not linha.lstrip().startswith('//')
    )


def _comparacoes_saldo_por_minimo(codigo):
    """Linhas onde um lado fala de saldo e o outro de mínimo.

    Uma regex única não basta: `(epi.unitStockQuantity ?? 0) <= epi.minimumStock!`
    escapou de uma tentativa anterior. Aqui a linha é PARTIDA no comparador e
    cada lado é examinado separadamente, nos dois sentidos.
    """
    achados = []
    for numero, linha in enumerate(codigo.splitlines(), 1):
        baixa = linha.lower()
        for op in COMPARADORES:
            if op not in baixa:
                continue
            esquerda, _, direita = baixa.partition(op)
            tem_saldo_esq = any(t in esquerda for t in TERMOS_SALDO)
            tem_min_esq = any(t in esquerda for t in TERMOS_MINIMO)
            tem_saldo_dir = any(t in direita for t in TERMOS_SALDO)
            tem_min_dir = any(t in direita for t in TERMOS_MINIMO)
            if (tem_saldo_esq and tem_min_dir) or (tem_min_esq and tem_saldo_dir):
                achados.append((numero, linha.strip()))
                break
    return achados


def test_o_detector_de_comparacao_funciona():
    """Um gate que não pega nada é pior que gate nenhum."""
    assert _comparacoes_saldo_por_minimo('if (stock <= minimumStock) {')
    assert _comparacoes_saldo_por_minimo('const c = (item.unit_stock_quantity ?? 0) <= item.minimum_stock;')
    assert _comparacoes_saldo_por_minimo('return minimum > saldoAtual;')
    # E não dispara no que é legítimo.
    assert not _comparacoes_saldo_por_minimo('if (stock <= 0) {')
    assert not _comparacoes_saldo_por_minimo('if (items.length > 0) {')


def test_o_detector_ignora_comentarios():
    codigo = '// aqui havia stock <= minimum_stock, removido\nconst x = 1;'
    assert not _comparacoes_saldo_por_minimo(_sem_comentarios(codigo))


@pytest.mark.parametrize('fonte', FONTES_JS, ids=lambda p: str(p.relative_to(RAIZ)))
def test_nenhum_javascript_compara_saldo_com_minimo(fonte):
    """A régua é do servidor. Reimplementá-la no cliente cria a segunda fonte
    que a #271 passou sete consumidores desfazendo."""
    achados = _comparacoes_saldo_por_minimo(_sem_comentarios(fonte.read_text(encoding='utf-8')))
    assert not achados, f'comparação saldo × mínimo em {fonte.name}: {achados}'


# ── o que a tela passou a consumir ───────────────────────────────────────────

def test_a_tela_de_estoque_consome_a_classificacao():
    corpo = _sem_comentarios(ESTOQUE_JS.read_text(encoding='utf-8'))
    for campo in ('stock_status', 'unit_minimum_stock', 'minimum_stock_source',
                  'attention_limit', 'unit_stock_quantity', 'unit_scope_id',
                  'stock_condition', 'underlying_status'):
        assert campo in corpo, f'{campo} não é lido pela tela'


def test_o_saldo_da_unidade_e_escolhido_por_presenca_e_nao_por_valor():
    corpo = _sem_comentarios(ESTOQUE_JS.read_text(encoding='utf-8'))
    assert "item.unit_scope_id !== null && item.unit_scope_id !== undefined" in corpo, \
        'a escolha voltou a depender do valor do saldo, não da existência de Unidade'


def test_a_severidade_paralela_saiu_da_lista_de_estoque_baixo():
    corpo = _sem_comentarios(ESTOQUE_JS.read_text(encoding='utf-8'))
    assert 'item.severity' not in corpo, 'a régua `severity` voltou'
    assert "severity === 'critical'" not in corpo


def test_os_quatro_estados_tem_estilo_proprio():
    css = ESTILOS.read_text(encoding='utf-8')
    for estado in ('normal', 'near_minimum', 'critical', 'disabled'):
        assert f'.badge-stock-{estado}' in css, estado


def test_disabled_nao_compartilha_estilo_com_normal():
    """Se as duas regras forem iguais, o chip cinza não existe na prática."""
    css = ESTILOS.read_text(encoding='utf-8')
    def regra(nome):
        m = re.search(rf'\.badge-stock-{nome} \{{([^}}]*)\}}', css)
        return m.group(1).strip() if m else None
    assert regra('disabled') and regra('normal')
    assert regra('disabled') != regra('normal')


def test_a_tabela_ganhou_a_coluna_de_situacao():
    html = ESTOQUE_HTML.read_text(encoding='utf-8')
    assert 'stock.statusColumn' in html
    corpo = ESTOQUE_JS.read_text(encoding='utf-8')
    assert 'colspan="10"' in corpo, 'o colspan do estado vazio ficou defasado'


def test_a_faixa_de_atencao_nao_e_recalculada_no_cliente():
    """`attention_limit` é `ceil(mínimo × (1+pct/100))` com Decimal no servidor.
    Refazer em ponto flutuante divergiria justamente na fronteira da cor."""
    corpo = _sem_comentarios(ESTOQUE_JS.read_text(encoding='utf-8'))
    assert 'item.attention_limit' in corpo
    for conta in ('/ 100', '* 1.2', 'Math.ceil('):
        assert conta not in corpo, f'a faixa voltou a ser calculada no cliente ({conta})'


def test_o_backend_nao_foi_tocado_nesta_fatia():
    """D-C3 é migração de cliente. Os campos já existiam no contrato."""
    rotas = (RAIZ / 'modules' / 'stock' / 'routes.py').read_text(encoding='utf-8')
    for campo in ('stock_status', 'attention_limit', 'unit_minimum_stock',
                  'minimum_stock_source', 'stock_condition', 'underlying_status'):
        assert f"item['{campo}']" in rotas, f'{campo} deveria já ser emitido antes da D-C3'
