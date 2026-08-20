"""Fatia 1.1D-C2 — o Flutter CONSOME a classificação por Unidade (#271).

Não há toolchain Dart neste ambiente: a validação real roda no CI
(`flutter analyze` + `flutter test`). O que estes testes protegem é a fronteira
arquitetural, que uma edição bem-intencionada reabre em uma linha — comparar
saldo com mínimo no cliente, ou tratar ausência de classificação como estoque
normal.

São verificações estruturais sobre o texto dos arquivos Dart. Elas não provam
que a tela compila; provam que a regra não voltou para dentro dela.
"""

import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
FLUTTER = RAIZ / 'flutter'
APP = FLUTTER / 'apps' / 'epi_admin' / 'lib'

EPI_MODEL = FLUTTER / 'packages' / 'epi_api' / 'lib' / 'models' / 'epi.dart'
STOCK_BADGE = (FLUTTER / 'packages' / 'epi_design' / 'lib' / 'components' /
               'atoms' / 'epi_stock_badge.dart')
STATUS_UTILS = APP / 'core' / 'utils' / 'epi_status_utils.dart'
STOCK_SCREEN = APP / 'features' / 'stock' / 'stock_screen.dart'
STOCK_CUBIT = APP / 'core' / 'bloc' / 'stock_cubit.dart'
DASHBOARD_CUBIT = APP / 'core' / 'bloc' / 'dashboard_cubit.dart'
DASHBOARD_SCREEN = APP / 'features' / 'dashboard' / 'dashboard_screen.dart'
NEW_DELIVERY = APP / 'features' / 'deliveries' / 'new_delivery_screen.dart'


def _fontes_dart():
    """Todo o Dart de produção do monorepo — sem testes, sem gerado.

    `integration_test/` também sai: é código de teste, e o diretório não se
    chama exatamente `test`, então precisa ser excluído por nome.
    """
    for caminho in FLUTTER.rglob('*.dart'):
        partes = caminho.parts
        if 'test' in partes or 'integration_test' in partes:
            continue
        if 'generated' in partes:
            continue
        if caminho.name.endswith(('.g.dart', '_test.dart')):
            continue
        yield caminho


def _sem_comentarios(texto):
    """Remove comentários de linha para que a proibição não pegue a explicação.

    Os arquivos documentam a regra removida citando `stockQuantity <=
    minimumStock`. Sem esta limpeza o próprio comentário reprovaria o teste — e
    a resposta natural seria apagar a explicação, que é o oposto do desejado.
    """
    return '\n'.join(
        linha for linha in texto.splitlines()
        if not linha.lstrip().startswith('//')
    )


# ── o getter removido ────────────────────────────────────────────────────────

def test_epi_nao_tem_mais_is_critical_stock():
    corpo = EPI_MODEL.read_text(encoding='utf-8')
    assert 'bool get isCriticalStock' not in corpo
    # A explicação do porquê fica: sem ela o getter volta na próxima leitura
    # desatenta do modelo.
    assert 'isCriticalStock' in corpo, 'o comentário explicando a remoção sumiu'


def test_nenhum_consumidor_chama_is_critical_stock():
    infratores = [
        c.relative_to(FLUTTER)
        for c in _fontes_dart()
        if 'isCriticalStock' in _sem_comentarios(c.read_text(encoding='utf-8'))
    ]
    assert infratores == [], f'isCriticalStock voltou a ser usado: {infratores}'


# ── a comparação proibida ────────────────────────────────────────────────────

# A criticidade deixou de ser uma comparação: depende do mínimo efetivo, da
# faixa de atenção e de o monitoramento estar ligado. Nenhuma forma de comparar
# um campo de saldo com um campo de mínimo é aceitável no cliente.
SALDO = re.compile(r'\b(stockQuantity|unitStockQuantity|companyStock|'
                   r'companyStockQuantity)\b')
MINIMO = re.compile(r'\b(minimumStock|unitMinimumStock|attentionLimit)\b')
OPERADOR = re.compile(r'<=|>=|<|>')


def _compara_saldo_com_minimo(linha):
    """Um lado da comparação é saldo e o outro é mínimo.

    Separar pelos operadores — em vez de casar um regex único — pega o que uma
    regex direta não pega: `(epi.unitStockQuantity ?? 0) <= epi.unitMinimumStock!`
    tem quatro tokens entre os dois campos.

    O alcance é a expressão escrita na linha. Passar por uma variável local
    intermediária escapa daqui; o que este teste garante é que a comparação não
    volte de forma direta, que é como ela existia.
    """
    lados = OPERADOR.split(linha)
    for esquerda, direita in zip(lados, lados[1:]):
        if SALDO.search(esquerda) and MINIMO.search(direita):
            return True
        if MINIMO.search(esquerda) and SALDO.search(direita):
            return True
    return False


def test_nenhum_dart_compara_saldo_com_minimo():
    achados = []
    for caminho in _fontes_dart():
        corpo = _sem_comentarios(caminho.read_text(encoding='utf-8'))
        for linha in corpo.splitlines():
            if _compara_saldo_com_minimo(linha):
                achados.append(f'{caminho.relative_to(FLUTTER)}: {linha.strip()}')
    assert achados == [], (
        'comparação saldo × mínimo reintroduzida no Dart — a classificação é '
        f'do backend: {achados}'
    )


def test_o_detector_de_comparacao_reconhece_as_formas_conhecidas():
    # Sem isto o teste acima pode passar por não detectar nada.
    assert _compara_saldo_com_minimo('stockQuantity <= minimumStock')
    assert _compara_saldo_com_minimo(
        '(epi.unitStockQuantity ?? 0) <= epi.unitMinimumStock!')
    assert _compara_saldo_com_minimo('epi.attentionLimit > e.unitStockQuantity')
    assert _compara_saldo_com_minimo('if (a.companyStock < b.minimumStock) {')
    # E não confunde comparações legítimas com zero ou entre saldos.
    assert not _compara_saldo_com_minimo('if (limite <= 0) return 1.0;')
    assert not _compara_saldo_com_minimo('epi.stockQuantity > 0')
    assert not _compara_saldo_com_minimo('a.unitStockQuantity > b.stockQuantity')


# ── as duas semânticas, separadas ────────────────────────────────────────────

def test_existem_funcoes_distintas_para_catalogo_e_unidade():
    corpo = STATUS_UTILS.read_text(encoding='utf-8')
    assert 'EpiBadgeStatus epiBadgeStatus(Epi epi)' in corpo
    assert 'EpiStockStatus? epiUnitBadgeStatus(Epi epi)' in corpo
    assert 'EpiBadgeStatus? epiValidityBadgeStatus(Epi epi)' in corpo
    assert 'bool epiIsUnitCritical(Epi epi)' in corpo
    assert 'double? epiUnitStockGauge(Epi epi)' in corpo


def test_catalogo_usa_a_criticidade_corporativa_do_backend():
    corpo = _sem_comentarios(STATUS_UTILS.read_text(encoding='utf-8'))
    trecho = corpo.split('EpiBadgeStatus epiBadgeStatus')[1].split('\n}')[0]
    assert 'isCompanyStockCritical' in trecho
    # O catálogo é corporativo: ler `stock_status` aqui misturaria de novo os
    # dois escopos, agora na direção contrária.
    assert 'stockStatus' not in trecho


def test_o_mapa_de_stock_status_tem_os_quatro_literais_e_null_por_padrao():
    corpo = STATUS_UTILS.read_text(encoding='utf-8')
    trecho = corpo.split('epiUnitBadgeStatus(Epi epi)')[1].split(';')[0]
    for literal, estado in (
        ("'critical'", 'EpiStockStatus.critical'),
        ("'near_minimum'", 'EpiStockStatus.nearMinimum'),
        ("'normal'", 'EpiStockStatus.normal'),
        ("'disabled'", 'EpiStockStatus.disabled'),
    ):
        assert f'{literal} => {estado}' in trecho, literal
    # O padrão é `null`. Trocá-lo por `EpiStockStatus.normal` converteria
    # ausência de contexto em afirmação de estoque saudável.
    assert '_ => null' in trecho
    assert '_ => EpiStockStatus.normal' not in trecho


def test_o_enum_de_estoque_tem_exatamente_os_quatro_estados():
    corpo = STOCK_BADGE.read_text(encoding='utf-8')
    bloco = corpo.split('enum EpiStockStatus {')[1].split('}')[0]
    valores = {v.strip() for v in re.split(r'[,\n]', _sem_comentarios(bloco))
               if v.strip() and not v.strip().startswith('///')}
    assert valores == {'normal', 'nearMinimum', 'critical', 'disabled'}, valores
    # Não existe um quinto valor para "sem classificação": a ausência é `null`,
    # e um estado neutro no enum viraria sinônimo de `normal` com o tempo.
    assert 'unknown' not in corpo


# ── tela de estoque: é da Unidade (W5-Flutter) ───────────────────────────────

def test_tela_de_estoque_nao_usa_criticidade_corporativa():
    for caminho in (STOCK_SCREEN, STOCK_CUBIT):
        corpo = _sem_comentarios(caminho.read_text(encoding='utf-8'))
        assert 'isCompanyStockCritical' not in corpo, caminho.name


def test_tela_de_estoque_exibe_o_minimo_da_unidade():
    corpo = _sem_comentarios(STOCK_SCREEN.read_text(encoding='utf-8'))
    assert 'epi.unitMinimumStock' in corpo
    # `epi.minimumStock` é o padrão corporativo herdado: exibi-lo mostrava 100
    # a uma Unidade que configurou 40.
    assert 'epi.minimumStock' not in corpo


def test_a_barra_mede_a_faixa_de_atencao():
    corpo = _sem_comentarios(STATUS_UTILS.read_text(encoding='utf-8'))
    trecho = corpo.split('double? epiUnitStockGauge')[1]
    assert 'epi.attentionLimit' in trecho
    assert 'minimumStock' not in trecho.split('\n}')[0]
    # O múltiplo arbitrário do mínimo corporativo que existia antes.
    assert '* 3' not in corpo


def test_contagem_e_ordenacao_do_estoque_usam_a_unidade():
    corpo = _sem_comentarios(STOCK_CUBIT.read_text(encoding='utf-8'))
    assert 'epis.where(epiIsUnitCritical).length' in corpo
    assert 'epiIsUnitCritical(a)' in corpo and 'epiIsUnitCritical(b)' in corpo


# ── dashboard: consome o resumo, não recomputa ───────────────────────────────

def test_dashboard_nao_baixa_epis_nem_conta_criticos():
    corpo = _sem_comentarios(DASHBOARD_CUBIT.read_text(encoding='utf-8'))
    assert 'bootstrap.epis' not in corpo
    assert 'bootstrap.deliveries' not in corpo
    assert 'bootstrap.employees' not in corpo
    assert 'Epi.fromJson' not in corpo
    assert 'criticalStock => kpis.criticalStock' in corpo


def test_dashboard_nao_deduz_perfil_travado_do_papel():
    corpo = _sem_comentarios(DASHBOARD_CUBIT.read_text(encoding='utf-8'))
    # A trava é decisão do backend (`resolve_unit_scope`), transportada em
    # `scope.locked`. Espelhá-la em Dart foi como cliente e servidor divergiram.
    assert "role == 'admin'" not in corpo
    assert "role == 'user'" not in corpo
    assert 'isLocked => scope.locked' in corpo
    tela = _sem_comentarios(DASHBOARD_SCREEN.read_text(encoding='utf-8'))
    assert 'state.isLocked' in tela
    assert 'operationalUnitId' not in tela


def test_dashboard_consome_setores_do_servidor():
    corpo = _sem_comentarios(DASHBOARD_CUBIT.read_text(encoding='utf-8'))
    assert 'sectors => filters.sectors' in corpo
    # A varredura de `bootstrap.employees` só para montar o dropdown.
    assert '_sectorsOf' not in corpo


def test_kpi_critico_nulo_nao_vira_zero_na_tela():
    corpo = _sem_comentarios(DASHBOARD_SCREEN.read_text(encoding='utf-8'))
    assert "state.criticalStock ?? '—'" in corpo
    assert 'state.criticalStock ?? 0' not in corpo


def test_o_kpi_critico_e_anulavel_no_estado():
    corpo = DASHBOARD_CUBIT.read_text(encoding='utf-8')
    assert 'int? get criticalStock' in corpo
    assert 'int? get nearMinimumStock' in corpo


# ── a lacuna registrada, não maquiada ────────────────────────────────────────

def test_nova_entrega_nao_exibe_badge_de_criticidade():
    corpo = NEW_DELIVERY.read_text(encoding='utf-8')
    sem_comentario = _sem_comentarios(corpo)
    assert 'EpiBadgeStatus.critical' not in sem_comentario
    assert 'isCompanyStockCritical' not in sem_comentario
    assert 'stockStatus' not in sem_comentario
    # A lacuna precisa continuar visível no código: os EPIs vêm do bootstrap,
    # que não classifica por Unidade, e o saldo exibido ali é corporativo.
    assert 'bootstrap' in corpo, 'a explicação da lacuna foi removida'
