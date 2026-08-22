"""1.1D-C4 — nenhum cliente recalcula `saldo × mínimo`, em Dart nem em JS.

A D-C3 migrou o Web Legado e enviou um gate só para JavaScript. Esta fatia
fecha o outro lado (Dart: Flutter Web, Android e iOS são o MESMO código) e
unifica o detector, que agora vive em `tests/stock_rule_scan.py`.

Duas coisas que a varredura de Dart revelou:

1. **O detector da D-C3 tratava `=>` como comparador.** Em Dart isso marcava
   `int? get nearMinimumStock => kpis.nearMinimumStock;` e cada getter de
   i18n `String get stockMinimumAlert => '...'` — sete falsos positivos. Em
   JavaScript o mesmo defeito só não quebrou o CI por sorte de nenhuma arrow
   function ter os dois termos. Corrigido em `_comparadores`.

2. **Uma comparação legítima existe**, e é o teste de contrato que demonstra
   por que a comparação local está errada (`unitStockQuantity <= minimumStock`
   é verdadeiro numa empresa saudável com estoque distribuído). Ela ganha o
   marcador explícito `gate:comparacao-intencional` — na linha, e não numa
   lista de arquivos isentos que ninguém revisita.
"""

from pathlib import Path

import pytest

from tests.stock_rule_scan import (
    MARCADOR_INTENCIONAL,
    comparacoes_saldo_por_minimo,
    sem_comentarios,
    varrer,
)

RAIZ = Path(__file__).resolve().parents[1]

# Dart de PRODUÇÃO e de teste. Flutter Web, Android e iOS compartilham este
# código — não são três alvos, são um.
FONTES_DART = sorted(
    p for p in (RAIZ / 'flutter').rglob('*.dart')
    if '/build/' not in str(p) and '/.dart_tool/' not in str(p)
)
FONTES_JS = sorted((RAIZ / 'static' / 'js').rglob('*.js')) + [RAIZ / 'static' / 'app.js']


# ── o detector, antes de confiar nele ────────────────────────────────────────

def test_o_detector_pega_as_formas_reais():
    """Gate que não pega nada é pior que gate nenhum."""
    assert comparacoes_saldo_por_minimo('if (stock <= minimumStock) {')
    assert comparacoes_saldo_por_minimo('final c = (epi.unitStockQuantity ?? 0) <= epi.minimumStock!;')
    assert comparacoes_saldo_por_minimo('const x = item.unit_stock_quantity < item.minimum_stock;')
    assert comparacoes_saldo_por_minimo('return minimumStock > saldoAtual;')


def test_a_seta_de_funcao_nao_e_comparacao():
    """O falso positivo que a varredura de Dart revelou no gate da D-C3."""
    assert not comparacoes_saldo_por_minimo('int? get nearMinimumStock => kpis.nearMinimumStock;')
    assert not comparacoes_saldo_por_minimo("String get stockMinimumAlert => 'Minimum stock reached';")
    assert not comparacoes_saldo_por_minimo('const f = (stock) => minimumStock;')
    assert not comparacoes_saldo_por_minimo("'near_minimum' => EpiStockStatus.nearMinimum,")


def test_igualdade_e_deslocamento_nao_sao_comparacao_de_grandeza():
    assert not comparacoes_saldo_por_minimo('if (stockQuantity == minimumStock) return;')
    assert not comparacoes_saldo_por_minimo('if (stockQuantity != minimumStock) return;')


def test_comparacoes_inocentes_nao_disparam():
    assert not comparacoes_saldo_por_minimo('if (stock <= 0) {')
    assert not comparacoes_saldo_por_minimo('if (items.length > 0) {')
    assert not comparacoes_saldo_por_minimo('if (minimumStock > 0) {')


def test_comentarios_que_citam_a_regra_nao_reprovam():
    codigo = '// antes aqui havia stock <= minimumStock, removido na D-C2\nfinal x = 1;'
    assert not comparacoes_saldo_por_minimo(sem_comentarios(codigo))


def test_o_marcador_isenta_apenas_a_propria_linha():
    isenta = 'expect(a.stockQuantity <= a.minimumStock, isTrue); // ' + MARCADOR_INTENCIONAL
    assert not comparacoes_saldo_por_minimo(isenta)
    # A linha seguinte, sem marcador, continua sendo pega.
    assert comparacoes_saldo_por_minimo(isenta + '\nfinal c = stock <= minimumStock;')


# ── a varredura ──────────────────────────────────────────────────────────────

@pytest.mark.parametrize('fonte', FONTES_DART, ids=lambda p: str(p.relative_to(RAIZ)))
def test_nenhum_dart_compara_saldo_com_minimo(fonte):
    """Flutter Web, Android e iOS saem daqui. A régua é do servidor."""
    achados = varrer(fonte)
    assert not achados, f'comparação saldo × mínimo em {fonte.name}: {achados}'


@pytest.mark.parametrize('fonte', FONTES_JS, ids=lambda p: str(p.relative_to(RAIZ)))
def test_nenhum_javascript_compara_saldo_com_minimo(fonte):
    achados = varrer(fonte)
    assert not achados, f'comparação saldo × mínimo em {fonte.name}: {achados}'


def test_a_varredura_cobre_as_duas_linguagens_de_fato():
    """Uma lista vazia de arquivos faria todos os testes acima passarem."""
    assert len(FONTES_DART) > 100, 'a varredura de Dart não encontrou o código'
    assert len(FONTES_JS) > 10, 'a varredura de JavaScript não encontrou o código'


def test_o_unico_uso_intencional_esta_marcado_e_justificado():
    """A exceção precisa se explicar, senão vira porta aberta."""
    contrato = RAIZ / 'flutter' / 'packages' / 'epi_api' / 'test' / 'epi_stock_contract_test.dart'
    corpo = contrato.read_text(encoding='utf-8')
    marcadas = [l for l in corpo.splitlines() if MARCADOR_INTENCIONAL in l]
    assert len(marcadas) == 1, 'o marcador deixou de ser exceção única'
    assert 'a comparação local daria crítico' in corpo, \
        'a justificativa da exceção sumiu'


def test_o_marcador_nao_foi_espalhado_pelo_codigo_de_producao():
    producao = [p for p in FONTES_DART if '/test/' not in str(p)] + FONTES_JS
    for fonte in producao:
        assert MARCADOR_INTENCIONAL not in fonte.read_text(encoding='utf-8'), \
            f'{fonte.name} usou o marcador para escapar do gate'
