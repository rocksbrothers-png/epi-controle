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

from tests.stock_rule_scan import sem_comentarios, varrer

RAIZ = Path(__file__).resolve().parents[1]
ESTOQUE_JS = RAIZ / 'static' / 'js' / 'views' / 'estoque.js'
ESTOQUE_HTML = RAIZ / 'static' / 'views' / 'estoque.html'
ESTILOS = RAIZ / 'static' / 'styles.css'

# Todo o JavaScript de tela do Legado.
FONTES_JS = sorted((RAIZ / 'static' / 'js').rglob('*.js')) + [RAIZ / 'static' / 'app.js']

@pytest.mark.parametrize('fonte', FONTES_JS, ids=lambda p: str(p.relative_to(RAIZ)))
def test_nenhum_javascript_compara_saldo_com_minimo(fonte):
    """A régua é do servidor. Reimplementá-la no cliente cria a segunda fonte
    que a #271 passou sete consumidores desfazendo."""
    achados = varrer(fonte)
    assert not achados, f'comparação saldo × mínimo em {fonte.name}: {achados}'


# ── o que a tela passou a consumir ───────────────────────────────────────────

def test_a_tela_de_estoque_consome_a_classificacao():
    corpo = sem_comentarios(ESTOQUE_JS.read_text(encoding='utf-8'))
    for campo in ('stock_status', 'unit_minimum_stock', 'minimum_stock_source',
                  'attention_limit', 'unit_stock_quantity', 'unit_scope_id',
                  'stock_condition', 'underlying_status'):
        assert campo in corpo, f'{campo} não é lido pela tela'


def test_o_saldo_da_unidade_e_escolhido_por_presenca_e_nao_por_valor():
    corpo = sem_comentarios(ESTOQUE_JS.read_text(encoding='utf-8'))
    assert "item.unit_scope_id !== null && item.unit_scope_id !== undefined" in corpo, \
        'a escolha voltou a depender do valor do saldo, não da existência de Unidade'


def test_a_severidade_paralela_saiu_da_lista_de_estoque_baixo():
    corpo = sem_comentarios(ESTOQUE_JS.read_text(encoding='utf-8'))
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
    corpo = sem_comentarios(ESTOQUE_JS.read_text(encoding='utf-8'))
    assert 'item.attention_limit' in corpo
    for conta in ('/ 100', '* 1.2', 'Math.ceil('):
        assert conta not in corpo, f'a faixa voltou a ser calculada no cliente ({conta})'


def test_o_backend_nao_foi_tocado_nesta_fatia():
    """D-C3 é migração de cliente. Os campos já existiam no contrato."""
    rotas = (RAIZ / 'modules' / 'stock' / 'routes.py').read_text(encoding='utf-8')
    for campo in ('stock_status', 'attention_limit', 'unit_minimum_stock',
                  'minimum_stock_source', 'stock_condition', 'underlying_status'):
        assert f"item['{campo}']" in rotas, f'{campo} deveria já ser emitido antes da D-C3'
