"""Contrato Python↔Dart da fatia 1.1D-C1.

A D-C1 entrega **só o contrato**: o modelo Dart passa a saber ler os campos de
classificação (#271) e o resumo do Dashboard (1.1D-B), mas nenhum Cubit ou tela
os consome ainda. A troca dos consumidores é a D-C2/D-C3.

Estes testes vivem em Python porque o defeito interessante atravessa a
fronteira: renomear um campo no backend **não quebra compilação nenhuma** no
Dart — o `as num?` devolve `null`, o campo some da tela em silêncio, e o
operador conclui que está tudo em ordem. Foi exatamente o modo de falha das
categorias de `compliance`, e é o que este arquivo impede.
"""

import ast
import json
import pathlib
import re
import sqlite3

import core.schema as schema
from modules.stock.service import (
    CONDITION_ABOVE_MINIMUM,
    CONDITION_AT_MINIMUM,
    CONDITION_BELOW_MINIMUM,
    CONDITION_NEGATIVE,
    CONDITION_ZERO,
    classify_unit_epi_stock,
)

RAIZ = pathlib.Path(__file__).resolve().parent.parent
EPI_MODEL = RAIZ / 'flutter/packages/epi_api/lib/models/epi.dart'
SUMMARY_MODEL = RAIZ / 'flutter/packages/epi_api/lib/models/dashboard_summary.dart'
DASHBOARD_API = RAIZ / 'flutter/packages/epi_api/lib/endpoints/dashboard_api.dart'
BARREL = RAIZ / 'flutter/packages/epi_api/lib/epi_api.dart'
API_CLIENT = RAIZ / 'flutter/apps/epi_admin/lib/core/api/api_client.dart'
STOCK_ROUTES = RAIZ / 'modules/stock/routes.py'
DASHBOARD_SERVICE = RAIZ / 'modules/dashboard/service.py'

# Campos de classificação que `/api/stock/epis` emite e o Dart precisa ler.
CAMPOS_CLASSIFICACAO = (
    'unit_minimum_stock',
    'minimum_stock_source',
    'effective_attention_percentage',
    'attention_percentage_source',
    'attention_limit',
    'stock_alert_enabled',
    'alert_source',
    'underlying_status',
    'stock_status',
    'stock_condition',
)


def _chaves_lidas(fonte: str) -> set:
    """Chaves JSON que um arquivo Dart lê — `json['x']` e `json["x"]`."""
    return set(re.findall(r"""json\[['"]([a-z_]+)['"]\]""", fonte))


# ═══════════════════════════════════════════════════════════════════════════
# /api/stock/epis  ->  Epi
# ═══════════════════════════════════════════════════════════════════════════

def test_o_dart_le_todos_os_campos_de_classificacao_que_o_backend_emite():
    """Renomear um campo no backend não quebra compilação no Dart.

    O `as num?` devolveria `null` e o valor sumiria da tela em silêncio. Este
    teste é o que transforma isso numa falha de CI.
    """
    rota = STOCK_ROUTES.read_text(encoding='utf-8')
    emitidos = {
        c for c in CAMPOS_CLASSIFICACAO if f"item['{c}']" in rota
    }
    assert emitidos == set(CAMPOS_CLASSIFICACAO), (
        f'/api/stock/epis deixou de emitir: {set(CAMPOS_CLASSIFICACAO) - emitidos}'
    )
    lidos = _chaves_lidas(EPI_MODEL.read_text(encoding='utf-8'))
    faltando = set(CAMPOS_CLASSIFICACAO) - lidos
    assert not faltando, f'o model Epi não lê: {faltando}'


def test_os_campos_de_classificacao_sao_anulaveis_no_dart():
    """Sem Unidade resolvida o backend manda `null` nos dez campos.

    Um `int` não-anulável com `?? 0` transformaria "não há unidade" em "mínimo
    zero" — a mesma classe de mentira que a 1.1B tirou do saldo.
    """
    fonte = EPI_MODEL.read_text(encoding='utf-8')
    tipos = {
        'unitMinimumStock': 'int?',
        'minimumStockSource': 'String?',
        'effectiveAttentionPercentage': 'int?',
        'attentionPercentageSource': 'String?',
        'attentionLimit': 'int?',
        'stockAlertEnabled': 'bool?',
        'alertSource': 'String?',
        'underlyingStatus': 'String?',
        'stockStatus': 'String?',
        'stockCondition': 'String?',
    }
    for campo, tipo in tipos.items():
        assert re.search(rf'final {re.escape(tipo)} {campo};', fonte), \
            f'`{campo}` deixou de ser `{tipo}` — nulo viraria um valor inventado'


def test_o_dart_nao_recalcula_a_classificacao():
    """Sabotagem: qualquer comparação saldo × mínimo no model reabre a segunda
    implementação que a #271 eliminou."""
    fonte = EPI_MODEL.read_text(encoding='utf-8')
    codigo = '\n'.join(
        l for l in fonte.split('\n') if not l.lstrip().startswith('///')
    )
    proibidos = (
        'unitStockQuantity <= unitMinimumStock',
        'unitStockQuantity <= minimumStock',
        'unitStockQuantity! <=',
        'attentionLimit =',
        '* (1 +',
    )
    for padrao in proibidos:
        assert padrao not in codigo, (
            f'`{padrao}` no model reimplementa a classificação do backend'
        )


def test_copywith_preserva_a_classificacao():
    """`copyWith` que esquece um campo o zera em silêncio — a lista de campos
    cresce e o método é o ponto onde ela envelhece."""
    fonte = EPI_MODEL.read_text(encoding='utf-8')
    inicio = fonte.index('Epi copyWith(')
    corpo = fonte[inicio:fonte.index('factory Epi.fromJson', inicio)]
    for campo in ('unitMinimumStock', 'minimumStockSource', 'attentionLimit',
                  'stockAlertEnabled', 'alertSource', 'underlyingStatus',
                  'stockStatus', 'stockCondition',
                  'effectiveAttentionPercentage', 'attentionPercentageSource'):
        assert f'{campo}: {campo}' in corpo, \
            f'`copyWith` perde `{campo}` — o valor viraria null numa cópia'


# ═══════════════════════════════════════════════════════════════════════════
# stock_condition — descritivo, não severidade
# ═══════════════════════════════════════════════════════════════════════════

def _conexao(minimo=20):
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.executescript('''
        CREATE TABLE companies (id INTEGER PRIMARY KEY);
        CREATE TABLE units (id INTEGER PRIMARY KEY);
        CREATE TABLE epis (id INTEGER PRIMARY KEY, company_id INTEGER, minimum_stock INTEGER);
        CREATE TABLE unit_epi_stock (id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER, unit_id INTEGER, epi_id INTEGER, quantity INTEGER);
    ''')
    schema.ensure_unit_epi_minimum_stock(conn)
    schema.ensure_stock_classification_config(conn)
    conn.execute('INSERT INTO epis (id, company_id, minimum_stock) VALUES (7, 1, ?)', (minimo,))
    conn.commit()
    return conn


def test_stock_condition_descreve_o_saldo_sem_opinar():
    """As cinco condições, contra mínimo 20 e limite 24."""
    esperado = {
        -5: CONDITION_NEGATIVE,
        0: CONDITION_ZERO,
        8: CONDITION_BELOW_MINIMUM,
        20: CONDITION_AT_MINIMUM,
        30: CONDITION_ABOVE_MINIMUM,
    }
    with _conexao() as conn:
        for saldo, condicao in esperado.items():
            c = classify_unit_epi_stock(conn, 1, 10, 7, unit_stock=saldo)
            assert c.stock_condition == condicao, \
                f'saldo {saldo} descrito como {c.stock_condition}, esperado {condicao}'


def test_condition_e_status_sao_dimensoes_independentes():
    """Saldo zerado com alerta desligado: a condição continua `zero` e o status
    é `disabled`. Um não determina o outro."""
    from modules.stock.service import set_unit_epi_alert_enabled
    with _conexao() as conn:
        set_unit_epi_alert_enabled(conn, 1, 10, 7, False, actor={'id': 1, 'role': 'user'})
        c = classify_unit_epi_stock(conn, 1, 10, 7, unit_stock=0)
    assert c.stock_condition == CONDITION_ZERO
    assert c.stock_status == 'disabled'
    assert c.underlying_status == 'critical'


def test_os_valores_de_condition_sao_literais_travados():
    """Contrato de API, como os quatro status: o Web vai comparar estas
    strings, e renomeá-las não quebra compilação nenhuma."""
    assert CONDITION_NEGATIVE == 'negative'
    assert CONDITION_ZERO == 'zero'
    assert CONDITION_BELOW_MINIMUM == 'below_minimum'
    assert CONDITION_AT_MINIMUM == 'at_minimum'
    assert CONDITION_ABOVE_MINIMUM == 'above_minimum'


# ═══════════════════════════════════════════════════════════════════════════
# /api/dashboard/summary  ->  DashboardSummary
# ═══════════════════════════════════════════════════════════════════════════

def _chaves_emitidas_pelo_resumo() -> dict:
    """Chaves de cada seção do payload, lidas da AST do serviço.

    Ler a AST em vez de dar `grep` evita casar com chaves citadas em
    comentários ou em outra parte do arquivo.
    """
    arvore = ast.parse(DASHBOARD_SERVICE.read_text(encoding='utf-8'))
    for no in ast.walk(arvore):
        if isinstance(no, ast.FunctionDef) and no.name == 'build_dashboard_summary':
            for filho in ast.walk(no):
                if isinstance(filho, ast.Return) and isinstance(filho.value, ast.Dict):
                    topo = filho.value
                    saida = {'_topo': [
                        k.value for k in topo.keys if isinstance(k, ast.Constant)
                    ]}
                    for chave, valor in zip(topo.keys, topo.values):
                        if isinstance(chave, ast.Constant) and isinstance(valor, ast.Dict):
                            saida[chave.value] = [
                                k.value for k in valor.keys if isinstance(k, ast.Constant)
                            ]
                    return saida
    raise AssertionError('não achei o dict de retorno de build_dashboard_summary')


def test_o_dart_le_todas_as_secoes_do_resumo():
    emitido = _chaves_emitidas_pelo_resumo()
    assert set(emitido['_topo']) == {'scope', 'kpis', 'filters', 'alerts', 'compliance'}
    fonte = SUMMARY_MODEL.read_text(encoding='utf-8')
    for secao in emitido['_topo']:
        assert f"json['{secao}']" in fonte, f'o model não lê a seção `{secao}`'


def test_o_dart_le_todas_as_chaves_de_scope_e_kpis():
    emitido = _chaves_emitidas_pelo_resumo()
    lidas = _chaves_lidas(SUMMARY_MODEL.read_text(encoding='utf-8'))
    for secao in ('scope', 'kpis'):
        faltando = set(emitido[secao]) - lidas
        assert not faltando, f'o model não lê, em `{secao}`: {faltando}'


def test_os_kpis_de_estoque_sao_anulaveis():
    """`critical_stock` e `near_minimum_stock` são `null` sem Unidade — zero
    afirmaria "nenhum EPI crítico" onde a pergunta não se aplica."""
    fonte = SUMMARY_MODEL.read_text(encoding='utf-8')
    for campo in ('criticalStock', 'nearMinimumStock'):
        assert f'final int? {campo};' in fonte, \
            f'`{campo}` deixou de ser anulável e zero viraria uma resposta'
        assert not re.search(rf"{campo}:.*\?\? 0", fonte), \
            f'`{campo}` ganhou `?? 0` e "sem unidade" virou "nenhum crítico"'


def test_locked_vem_do_servidor_e_nao_e_deduzido():
    fonte = SUMMARY_MODEL.read_text(encoding='utf-8')
    assert "json['locked']" in fonte
    codigo = '\n'.join(l for l in fonte.split('\n') if not l.lstrip().startswith('///'))
    assert "role ==" not in codigo, \
        'o model voltou a deduzir perfil travado a partir do papel'


def test_a_rota_esta_ligada_no_cliente():
    api = DASHBOARD_API.read_text(encoding='utf-8')
    assert "'/api/dashboard/summary'" in api
    assert 'DashboardSummary.fromJson' in api
    barrel = BARREL.read_text(encoding='utf-8')
    assert "export 'endpoints/dashboard_api.dart';" in barrel
    assert "export 'models/dashboard_summary.dart';" in barrel
    cliente = API_CLIENT.read_text(encoding='utf-8')
    assert 'static late final DashboardApi dashboard;' in cliente
    assert 'dashboard = DashboardApi(dio);' in cliente


# ═══════════════════════════════════════════════════════════════════════════
# Escopo da D-C1: contrato, nenhum consumidor migrado
# ═══════════════════════════════════════════════════════════════════════════

def test_o_contrato_dart_da_dc1_esta_em_uso_pela_dc2():
    """A D-C1 entregou só o modelo; a D-C2 ligou os consumidores Flutter nele.

    O Web Legado é a D-C3 e continua no bootstrap. A migração acontece por
    decisão, não por acidente — por isso o limite fica travado aqui.
    """
    cubit = (RAIZ / 'flutter/apps/epi_admin/lib/core/bloc/dashboard_cubit.dart') \
        .read_text(encoding='utf-8')
    assert 'ApiClient.dashboard' in cubit, \
        'o DashboardCubit deixou de consumir a rota nova'
    assert 'isCriticalStock' not in cubit, \
        'o cálculo antigo voltou ao Cubit'

    utils = (RAIZ / 'flutter/apps/epi_admin/lib/core/utils/epi_status_utils.dart') \
        .read_text(encoding='utf-8')
    assert 'stockStatus' in utils, 'o badge da Unidade deixou de ler stock_status'

    dashboard_js = (RAIZ / 'static/js/views/dashboard.js').read_text(encoding='utf-8')
    assert '/api/dashboard/summary' not in dashboard_js, \
        'o Web Legado já consome a rota nova — isso é D-C3'


def test_o_bootstrap_nao_perdeu_campos():
    """Remover campo do bootstrap é 1.1E, não D-C."""
    servico = (RAIZ / 'modules/auth/service.py').read_text(encoding='utf-8')
    for campo in ("'epis'", "'deliveries'", "'employees'", "'units'",
                  "'legal_entities'", "'alerts'", "'pending_purchases'"):
        assert f'{campo}:' in servico, f'o bootstrap perdeu {campo}'


def test_o_payload_real_alimenta_o_model_dart():
    """Simula o parsing do Dart sobre o payload que o backend produz.

    Sem toolchain Flutter aqui, a prova possível é: montar o item como
    `/api/stock/epis` monta, e verificar que cada chave que o Dart lê existe e
    tem o tipo que o cast espera.
    """
    with _conexao() as conn:
        c = classify_unit_epi_stock(conn, 1, 10, 7, unit_stock=8)

    item = {
        'unit_minimum_stock': c.effective_minimum_stock,
        'minimum_stock_source': c.minimum_stock_source,
        'effective_attention_percentage': c.effective_attention_percentage,
        'attention_percentage_source': c.attention_percentage_source,
        'attention_limit': c.attention_limit,
        'stock_alert_enabled': c.stock_alert_enabled,
        'alert_source': c.alert_source,
        'underlying_status': c.underlying_status,
        'stock_status': c.stock_status,
        'stock_condition': c.stock_condition,
    }
    # Serializável como JSON — o transporte real.
    json.dumps(item)

    tipos_dart = {
        'unit_minimum_stock': int, 'effective_attention_percentage': int,
        'attention_limit': int, 'stock_alert_enabled': bool,
        'minimum_stock_source': str, 'attention_percentage_source': str,
        'alert_source': str, 'underlying_status': str,
        'stock_status': str, 'stock_condition': str,
    }
    for chave, tipo in tipos_dart.items():
        assert isinstance(item[chave], tipo), (
            f'`{chave}` é {type(item[chave]).__name__}; o cast Dart espera '
            f'{tipo.__name__} e devolveria null'
        )
    assert item['stock_status'] == 'critical'
    assert item['stock_condition'] == 'below_minimum'


# ═══════════════════════════════════════════════════════════════════════════
# Gate: testes Dart precisam importar o framework que o pacote realmente tem
# ═══════════════════════════════════════════════════════════════════════════

def test_testes_dart_importam_o_framework_disponivel_no_pacote():
    """`package:test` não está nas `dev_dependencies` dos pacotes Flutter.

    Importá-lo faz `flutter analyze` falhar com dezenas de `undefined_function`
    para cada `expect`/`isNull`/`isEmpty` — e o erro é invisível em qualquer
    ambiente sem toolchain Flutter, onde os testes Dart não rodam. Só o CI
    pega, e só depois do push.

    Este gate roda no pytest, que roda em todo lugar: erra o import, reprova
    antes de chegar ao CI.
    """
    pacotes = sorted((RAIZ / 'flutter/packages').glob('*/pubspec.yaml'))
    assert pacotes, 'nenhum pacote Flutter encontrado — o gate varreria vazio'

    for pubspec in pacotes:
        raiz_pacote = pubspec.parent
        tem_package_test = re.search(
            r'^\s{2}test:', pubspec.read_text(encoding='utf-8'), re.M
        )
        for arquivo in sorted((raiz_pacote / 'test').glob('*.dart')):
            fonte = arquivo.read_text(encoding='utf-8')
            if "import 'package:test/test.dart';" in fonte and not tem_package_test:
                raise AssertionError(
                    f'{arquivo.relative_to(RAIZ)} importa `package:test`, que não '
                    f'está nas dev_dependencies de {raiz_pacote.name}. '
                    'Use `package:flutter_test/flutter_test.dart`.'
                )
