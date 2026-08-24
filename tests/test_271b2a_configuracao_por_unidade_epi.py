"""Configuração de estoque por Unidade + EPI — a fatia B2-a (#271).

Não há toolchain Dart neste ambiente: `flutter analyze` e `flutter test` só
rodam no CI. Estes testes protegem, do lado Python, as fronteiras que uma
edição bem-intencionada reabre em uma linha.

A pergunta central da fatia, e o motivo de o primeiro bloco existir: **o gate
do cliente concorda com o backend, perfil a perfil?** Um gate mais frouxo abre
uma tela cuja gravação o servidor recusará com 403; um gate mais apertado
esconde uma tela que o servidor autorizaria. Os dois são defeitos, e nenhum
aparece em teste que exercite um perfil só.
"""

import json
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from core.permissions import PERMISSIONS  # noqa: E402

FLUTTER = RAIZ / 'flutter'
APP = FLUTTER / 'apps' / 'epi_admin' / 'lib'

MODELO = FLUTTER / 'packages' / 'epi_api' / 'lib' / 'models' / 'unit_epi_stock_config.dart'
STOCK_API = FLUTTER / 'packages' / 'epi_api' / 'lib' / 'endpoints' / 'stock_api.dart'
EXPORTS = FLUTTER / 'packages' / 'epi_api' / 'lib' / 'epi_api.dart'
CUBIT = APP / 'core' / 'bloc' / 'stock_config_cubit.dart'
TELA = APP / 'features' / 'stock' / 'stock_config_screen.dart'
TELA_ESTOQUE = APP / 'features' / 'stock' / 'stock_screen.dart'
ROTAS = APP / 'core' / 'router' / 'routes.dart'
PERMISSOES_DE_ROTA = APP / 'core' / 'router' / 'route_permissions.dart'
ROUTER = APP / 'core' / 'router' / 'app_router.dart'
SELETOR_CUBIT = APP / 'core' / 'bloc' / 'unit_selector_cubit.dart'
TESTE_DART = FLUTTER / 'apps' / 'epi_admin' / 'test' / 'stock_config_cubit_test.dart'

ROTAS_BACKEND = RAIZ / 'modules' / 'stock' / 'routes.py'

LOCALES = ('app_pt_BR', 'app_en_US', 'app_es_ES', 'app_fr_FR', 'app_no_NO')
L10N = FLUTTER / 'packages' / 'epi_i18n' / 'lib' / 'l10n'

#: A permissão que o backend cobra em `_authorize_stock_config_write`.
PERM = 'stock:adjust'


def _sem_comentarios(texto: str) -> str:
    return '\n'.join(
        linha for linha in texto.split('\n')
        if not linha.lstrip().startswith('//')
    )


def _codigo(caminho: Path) -> str:
    return _sem_comentarios(caminho.read_text(encoding='utf-8'))


# ── A matriz de permissões, perfil a perfil ──────────────────────────────────
#
# O gate do Flutter é `stock:adjust`. Estes testes provam o que isso significa
# para cada papel, contra `core/permissions.py` — a mesma fonte que
# `authorize_action` consulta em produção.

def test_general_admin_configura_estoque():
    """Administrador Geral: entra e configura a Unidade selecionada.

    É o perfil livre da fatia — escolhe entre as Unidades do tenant e escreve
    na que escolheu.
    """
    assert PERM in PERMISSIONS['general_admin']


def test_admin_e_user_configuram_a_propria_unidade():
    """Administrador Local e Gestor de EPI: entram, travados na sua Unidade.

    O travamento não vem desta permissão e sim de `resolve_unit_scope`, que
    descarta o `unit_id` do cliente para perfil travado. A permissão só decide
    se a tela abre.
    """
    for papel in ('admin', 'user'):
        assert PERM in PERMISSIONS[papel], f'{papel} perdeu {PERM}'


def test_master_admin_nao_configura_estoque_por_unidade():
    """Administrador Master fica de fora, por decisão anterior.

    Ele opera cross-tenant por desenho, e configuração operacional de Unidade
    não é operação cross-tenant. A exclusão é explícita em
    `MASTER_ADMIN_OPERATIONAL_EXCLUSIONS` — não é um esquecimento do mapa.
    """
    assert PERM not in PERMISSIONS['master_admin']


def test_perfil_sem_autorizacao_nao_configura():
    """Comprador (e qualquer outro papel operacional de compras) fica fora."""
    assert PERM not in PERMISSIONS['buyer']


def test_registry_admin_nao_tem_stock_adjust_hoje():
    """⚠️ DIVERGÊNCIA REGISTRADA — o Administrador de Registro NÃO configura.

    `_authorize_stock_config_write` lista `registry_admin` entre os papéis
    aceitos e a docstring da B1a descreve o perfil configurando qualquer
    Unidade. Mas a primeira linha daquela função é
    `authorize_action(..., 'stock:adjust')`, e `registry_admin` nunca recebeu
    `STOCK_MANAGEMENT_PERMISSIONS`: a checagem de papel logo abaixo é
    **inalcançável** para ele.

    Ou seja: a divergência é INTERNA ao backend e antecede esta fatia. O gate
    do Flutter espelha o comportamento EFETIVO (o perfil não vê a tela), que é
    a única leitura que não mente para o usuário.

    Conceder `stock:adjust` a `registry_admin` resolveria pelo outro lado, mas
    a permissão também abre `POST /api/stock/movements`,
    `POST /api/stock/items/status` e a reimpressão de etiquetas — movimentação
    física de estoque para um papel que `docs/PAPEIS_E_ATRIBUICOES.md` #3
    descreve como responsável pelos cadastros da organização. É decisão de
    negócio, não de implementação, e por isso está fora da B2-a.

    Este teste falha no dia em que a decisão for tomada, pedindo que a
    divergência seja fechada dos dois lados de uma vez.
    """
    assert PERM not in PERMISSIONS['registry_admin'], (
        'registry_admin ganhou stock:adjust — feche a divergência: revise o gate '
        'do Flutter em route_permissions.dart e a docstring de '
        '_authorize_stock_config_write.'
    )
    fonte = ROTAS_BACKEND.read_text(encoding='utf-8')
    assert "'general_admin', 'registry_admin'" in fonte, (
        'a lista de papéis de _authorize_stock_config_write mudou; reavalie a '
        'divergência descrita neste teste'
    )


def test_o_gate_do_cliente_espelha_o_backend_papel_a_papel():
    """A tabela inteira, num teste só.

    Verdadeiro = o backend autoriza E o Flutter mostra. Falso = nenhum dos
    dois. Nunca um sim de um lado e um não do outro.
    """
    esperado = {
        'general_admin': True,
        'admin': True,
        'user': True,
        'master_admin': False,
        'registry_admin': False,
        'buyer': False,
    }
    for papel, pode in esperado.items():
        assert (PERM in PERMISSIONS[papel]) is pode, (
            f'{papel}: backend={PERM in PERMISSIONS[papel]}, esperado={pode}'
        )


# ── O gate de rota do Flutter ────────────────────────────────────────────────

def _mapa_de_permissoes_de_rota():
    """Extrai `routePermissions` preservando a ORDEM de inserção.

    A ordem é semântica aqui: `requiredPermissionFor` casa por `startsWith` e
    devolve o primeiro casamento.
    """
    codigo = _codigo(PERMISSOES_DE_ROTA)
    corpo = codigo.split('routePermissions = <String, String>{', 1)[1]
    corpo = corpo.split('};', 1)[0]
    return re.findall(r"Routes\.(\w+)\s*:\s*'([^']+)'", corpo)


def test_a_configuracao_exige_stock_adjust_e_nao_view():
    pares = dict(_mapa_de_permissoes_de_rota())
    assert pares.get('stockConfig') == PERM, (
        'a tela de configuração precisa exigir stock:adjust — stock:view abriria '
        'para quem só consulta estoque, e toda gravação voltaria 403'
    )


def test_a_ordem_do_mapa_impede_stock_config_cair_em_stock_view():
    """`/stock/config` ANTES de `/stock`.

    `requiredPermissionFor` devolve o primeiro casamento por `startsWith`. Com
    `/stock` primeiro, `/stock/config` resolveria para `stock:view` — o mapa
    continuaria "correto" na leitura e errado na execução. Trocar as duas
    linhas de lugar é a edição inofensiva que este teste reprova.
    """
    ordem = [nome for nome, _ in _mapa_de_permissoes_de_rota()]
    assert 'stockConfig' in ordem and 'stock' in ordem
    assert ordem.index('stockConfig') < ordem.index('stock'), (
        'Routes.stockConfig precisa vir antes de Routes.stock em routePermissions'
    )


def test_a_rota_esta_declarada_e_registrada():
    rotas = _codigo(ROTAS)
    assert "stockConfig = '/stock/config'" in rotas
    # `Routes.all` alimenta o teste que confere se o menu aponta só para rotas
    # existentes; ficar de fora dele torna a rota invisível para aquele gate.
    assert re.search(r'\ball\s*=\s*<String>\[[^\]]*stockConfig', rotas, re.S), \
        'stockConfig ficou fora de Routes.all'
    assert 'path: Routes.stockConfig' in _codigo(ROUTER)


def test_os_guardas_dart_de_rota_conhecem_a_rota_nova():
    """Os dois testes Dart que enumeram rotas precisam da entrada nova.

    Não é redundância: eles só rodam no CI, e uma rota gateada que não entre
    nos dois deixa o PR vermelho depois do push. Aqui a mesma checagem roda
    localmente, onde ainda dá para corrigir antes.

    - `route_permissions_test.dart` compara `routePermissions` com um conjunto
      EXATO. Rota nova ausente dali reprova.
    - `app_shell_navigation_test.dart` exige que toda rota gateada seja
      alcançável por clique. `/stock/config` fica fora do menu de propósito —
      é um detour a partir de Controle de Estoque —, então precisa constar de
      `reachableElsewhere` com o arquivo que navega até ela. Esse teste nasceu
      de um defeito real: a tela de CNPJs existiu por versões alcançável só
      digitando a URL.
    """
    testes = FLUTTER / 'apps' / 'epi_admin' / 'test'
    cobertura = _codigo(testes / 'route_permissions_test.dart')
    assert 'Routes.stockConfig' in cobertura, \
        'route_permissions_test.dart não conhece a rota nova — o CI reprovaria'

    navegacao = _codigo(testes / 'app_shell_navigation_test.dart')
    bloco = navegacao.split('reachableElsewhere', 1)[1].split('};', 1)[0]
    assert "'/stock/config'" in bloco, \
        'a rota precisa ser declarada em reachableElsewhere (fica fora do menu)'
    # O teste vizinho exige que a isenção aponte para um arquivo real; sem isto
    # a lista vira depósito de conveniência.
    linha = [l for l in bloco.splitlines() if '/stock/config' in l]
    assert linha, 'declaração de /stock/config não encontrada'
    origem = bloco.split("'/stock/config'", 1)[1].split(',', 1)[0]
    assert '.dart' in origem, 'a isenção precisa nomear o arquivo que navega'


def test_a_rota_nao_entra_no_menu_lateral():
    """Configuração não é destino de primeiro nível.

    Fosse um item do menu, `app_shell_navigation_test.dart` passaria pelo
    caminho errado — e a tela operacional deixaria de ser o ponto de partida,
    que é justamente o desenho aprovado.
    """
    shell = _codigo(APP / 'core' / 'shell' / 'app_shell.dart')
    assert 'Routes.stockConfig' not in shell


def test_a_navegacao_usa_push_para_permitir_voltar():
    """`push`, não `go`: a configuração é um detour e o operador volta.

    É também o que os outros acessos a tela interna usam — e o que a isenção
    em `reachableElsewhere` declara.
    """
    codigo = _codigo(TELA_ESTOQUE)
    trecho = codigo.split('Routes.stockConfig', 1)[0][-400:]
    assert 'context.push' in trecho or 'context.push' in codigo
    assert 'context.go(' not in codigo, \
        'go substitui a pilha e o operador perde o caminho de volta'


def test_o_modulo_estrutural_e_herdado_de_estoque():
    """`/stock/config` não precisa de entrada em `routeModules`.

    `requiredModuleFor` casa por `startsWith` e `/stock` já mapeia para
    `estoque` — ser subrota é o que faz a herança acontecer. Uma entrada
    própria seria uma segunda fonte para a mesma decisão.
    """
    modulos = _codigo(APP / 'core' / 'router' / 'navigation_policy.dart')
    assert 'Routes.stock: ' in modulos
    assert 'Routes.stockConfig' not in modulos


# ── O contrato do cliente com as seis rotas ──────────────────────────────────

METODOS = (
    ('setUnitEpiMinimum', '/api/stock/minimum'),
    ('restoreUnitEpiMinimum', '/api/stock/minimum/restore-default'),
    ('setUnitEpiAttentionPercentage', '/api/stock/attention-percentage'),
    ('restoreUnitEpiAttentionPercentage',
     '/api/stock/attention-percentage/restore-default'),
    ('setUnitEpiAlertEnabled', '/api/stock/alert-enabled'),
    ('restoreUnitEpiAlertEnabled', '/api/stock/alert-enabled/restore-default'),
)


def test_os_arquivos_da_fatia_existem():
    for caminho in (MODELO, CUBIT, TELA, TESTE_DART):
        assert caminho.exists(), f'{caminho.name} sumiu'


def test_o_modelo_esta_exportado():
    assert "export 'models/unit_epi_stock_config.dart';" in \
        EXPORTS.read_text(encoding='utf-8')


def test_os_seis_metodos_existem_e_apontam_para_as_rotas_certas():
    codigo = _codigo(STOCK_API)
    for metodo, rota in METODOS:
        assert f'Future<Unit' in codigo and metodo in codigo, \
            f'{metodo} não existe em StockApi'
        assert f"'{rota}'" in codigo, f'{rota} não é chamada por StockApi'


def test_as_seis_rotas_existem_no_backend():
    """O cliente não pode apontar para rota que o servidor não registra."""
    registro = ROTAS_BACKEND.read_text(encoding='utf-8')
    for _, rota in METODOS:
        assert f"'{rota}'" in registro, f'{rota} sumiu do backend'


def test_toda_gravacao_transporta_a_unidade():
    """`unit_id` é obrigatório nas seis, e não opcional.

    A tela é fail-closed sem Unidade; um parâmetro opcional modelaria um estado
    que ela proíbe. Continua sendo transporte — `resolve_unit_scope` decide.
    """
    codigo = _codigo(STOCK_API)
    for metodo, _ in METODOS:
        corpo = codigo.split(metodo, 1)[1].split('}\n', 1)[0]
        assert 'required int unitId' in corpo, f'{metodo} não exige unitId'
        assert "'unit_id': unitId" in corpo, f'{metodo} não envia unit_id'


# ── Ajuste 1: o alerta não persiste sozinho ──────────────────────────────────

def test_o_toggle_de_alerta_nao_grava_sozinho():
    """`toggleAlertDraft` mexe no rascunho; quem grava é `saveAlert`.

    Um toggle que persiste ao toque torna o silenciamento de um alerta
    reversível apenas por acidente. O rascunho é o que dá ao usuário a chance
    de desistir.
    """
    codigo = _codigo(CUBIT)
    corpo = codigo.split('void toggleAlertDraft', 1)[1].split('\n  }', 1)[0]
    assert 'stockApi' not in corpo, 'toggleAlertDraft está chamando a API'
    assert 'alertDraft:' in corpo
    assert 'Future<void> saveAlert()' in codigo
    assert 'setUnitEpiAlertEnabled' in codigo.split('Future<void> saveAlert()', 1)[1]


def test_desabilitar_pede_confirmacao_e_habilitar_nao():
    """A CONDIÇÃO da confirmação mora no cubit, para ser testável sem widget.

    Só a transição ligado → desligado pede confirmação: silenciar é a decisão
    relevante. Ligar de volta não precisa de pergunta.
    """
    codigo = _codigo(CUBIT)
    assert 'bool get alertRequiresConfirmation => alertDirty && !alertDraft;' in codigo
    # E a tela precisa CONSUMIR essa condição antes de gravar.
    tela = _codigo(TELA)
    assert 'alertRequiresConfirmation' in tela
    assert 'showDialog' in tela
    ordem_tela = tela.split('alertRequiresConfirmation', 1)[1]
    assert ordem_tela.index('showDialog') < ordem_tela.index('saveAlert()'), \
        'a confirmação precisa vir ANTES do POST'


def test_restaurar_alerta_e_operacao_distinta_de_salvar_habilitado():
    """As duas terminam com o alerta ligado e significam coisas opostas."""
    codigo = _codigo(CUBIT)
    assert 'Future<void> restoreAlert()' in codigo
    corpo = codigo.split('Future<void> restoreAlert()', 1)[1].split(';', 1)[0]
    assert 'restoreUnitEpiAlertEnabled' in corpo, \
        'restoreAlert precisa chamar a rota de restaurar, não o set com true'


# ── Ajuste 3: nenhum limite inventado no cliente ─────────────────────────────

def test_o_minimo_nao_ganha_teto_no_cliente():
    """O backend faz `max(0, int(...))` e não publica teto. O Dart não inventa.

    A validação local para na negatividade — que é o único caso em que o
    servidor normalizaria em silêncio um valor que o usuário não quis.
    """
    codigo = _codigo(CUBIT)
    corpo = codigo.split('Future<void> saveMinimum', 1)[1].split('\n  }', 1)[0]
    assert 'valor < 0' in corpo
    assert not re.search(r'valor\s*>\s*\d+', corpo), \
        'apareceu um teto para o mínimo que o backend não define'


def test_o_percentual_usa_o_teto_publicado_pelo_backend():
    """0–100 é contrato do backend (`MAX_ATTENTION_PERCENTAGE`), não invenção."""
    from modules.stock.service import MAX_ATTENTION_PERCENTAGE
    assert MAX_ATTENTION_PERCENTAGE == 100
    corpo = _codigo(CUBIT).split('Future<void> saveAttention', 1)[1].split('\n  }', 1)[0]
    assert 'percentual < 0 || percentual > 100' in corpo


# ── Ajuste 4: deep link é entrada não confiável ──────────────────────────────

def test_a_unidade_de_deep_link_e_validada_contra_o_selectable():
    """`preferredUnitId` só vale se constar de `GET /api/units/selectable`.

    A checagem vive no cubit do seletor compartilhado — que é quem tem a lista
    — e não em cada tela que aceita um `?unit_id=`.
    """
    codigo = _codigo(SELETOR_CUBIT)
    corpo = codigo.split('int? _selecaoInicial', 1)[1].split('\n  }', 1)[0]
    assert 'scope.units.any((u) => u.id == pedida)' in corpo, \
        'a Unidade pedida por deep link entrou sem conferir a lista do servidor'
    # Perfil travado ignora o pedido: a Unidade dele é a do ator, e ponto.
    assert corpo.index('scope.locked') < corpo.index('pedida'), \
        'o perfil travado precisa ser decidido ANTES do deep link'


def test_o_epi_de_deep_link_e_validado_contra_a_lista_da_unidade():
    codigo = _codigo(CUBIT)
    # Guardado sem selecionar...
    assert 'void deepLinkEpi(' in codigo
    guarda = codigo.split('void deepLinkEpi(', 1)[1].split('\n', 1)[0]
    assert '_epiPedidoPorDeepLink = epiId' in guarda
    # ...e só aplicado depois que a lista da Unidade chegou.
    corpo = codigo.split('Future<void> _carregarEpis', 1)[1].split('\n  }', 1)[0]
    assert 'epis.any((e) => e.id == pedido)' in corpo, \
        'o EPI pedido por deep link entrou sem conferir a lista daquela Unidade'


def test_selecionar_epi_recusa_o_que_nao_esta_na_lista():
    corpo = _codigo(CUBIT).split('void selectEpi(', 1)[1].split('\n  }', 1)[0]
    assert 'if (linha.isEmpty) return;' in corpo


# ── Isolamento entre Unidades e concorrência ─────────────────────────────────

def test_trocar_de_unidade_zera_o_par_antes_de_buscar():
    """Nunca exibir os números da Unidade A sob o rótulo da B."""
    corpo = _codigo(CUBIT).split('Future<void> setUnit(', 1)[1].split('\n  }', 1)[0]
    assert 'clearEpi: true' in corpo and 'clearParams: true' in corpo
    assert 'epis: const <Epi>[]' in corpo


def test_resposta_de_par_errado_e_descartada():
    """A rede por trás do desabilitar: resposta lenta não pinta o par novo."""
    codigo = _codigo(CUBIT)
    assert 'bool _parCorrente(int unitId, int epiId) =>' in codigo
    assert 'state.unitId == unitId && state.epiId == epiId' in codigo
    corpo = codigo.split('Future<void> _executar(', 1)[1]
    assert 'if (!_parCorrente(unitId, epiId)) return;' in corpo, \
        'a gravação deixou de conferir o par na volta'


def test_uma_gravacao_por_vez():
    codigo = _codigo(CUBIT)
    assert 'if (unitId == null || epiId == null || state.isBusy) return;' in codigo
    assert 'bool get isBusy =>' in codigo


def test_a_tela_desabilita_os_dois_seletores_durante_a_gravacao():
    """Trocar de par com requisição em voo é o caso que o descarte cobre; o
    desabilitar é o que evita chegar lá."""
    tela = _codigo(TELA)
    assert 'ignoring: state.isBusy' in tela, 'o seletor de Unidade não é bloqueado'
    assert 'onTap: state.isBusy' in tela, 'o seletor de EPI não é bloqueado'


def test_o_seletor_e_usado_em_modo_escrita():
    tela = _codigo(TELA)
    assert 'purpose: UnitSelectorPurpose.write' in tela
    assert 'EpiUnitSelector' in tela
    # A Unidade não pode sair de bootstrap nem do retrato de leitura do
    # stock_cubit (`unitScopeId` da listagem).
    assert 'bootstrap' not in tela.lower()


# ── A regra que o cliente não pode encostar ──────────────────────────────────

def test_a_fatia_nao_recalcula_classificacao():
    """O gate da 1.1D-C4, aplicado aos arquivos novos.

    Reusa o detector compartilhado em vez de uma segunda varredura: dois
    detectores divergem no primeiro ajuste feito num lado só — que é o defeito
    que estes gates existem para impedir.
    """
    from tests.stock_rule_scan import comparacoes_saldo_por_minimo, sem_comentarios

    for caminho in (CUBIT, TELA, MODELO, STOCK_API):
        achados = comparacoes_saldo_por_minimo(
            sem_comentarios(caminho.read_text(encoding='utf-8'))
        )
        assert not achados, f'{caminho.name} recalcula saldo × mínimo: {achados}'


def test_os_derivados_sao_relidos_do_servidor_apos_gravar():
    """As respostas de escrita não trazem `attention_limit` nem `stock_status`,
    e não existe GET de par único. Reler a listagem é a única forma de
    atualizá-los sem recalcular."""
    codigo = _codigo(CUBIT)
    assert 'Future<void> _recarregarDerivados(' in codigo
    assert 'fetchUnitStockEpis' in \
        codigo.split('Future<void> _recarregarDerivados(', 1)[1]
    assert '_recarregarDerivados(unitId, epiId)' in \
        codigo.split('Future<void> _executar(', 1)[1]


def test_a_origem_vem_do_servidor_e_nao_da_acao():
    """Salvar 20 e restaurar para 20 chegam com o mesmo número e origens
    opostas. A tela mostra a origem que o servidor devolveu."""
    codigo = _codigo(CUBIT)
    corpo = codigo.split('Future<void> _executar(', 1)[1]
    for tipo in ('UnitEpiMinimum', 'UnitEpiAttention', 'UnitEpiAlert'):
        assert f'resposta is {tipo}' in corpo, \
            f'a resposta de {tipo} não é aplicada ao estado'
    tela = _codigo(TELA)
    assert '_rotuloDaOrigem(l10n, atual.source)' in tela


def test_as_tres_origens_do_contrato_estao_mapeadas():
    """`system_default` é do alerta; `company_default` é do mínimo e do
    percentual. Hierarquias de altura diferente, e tratá-las como iguais
    mostraria uma origem que não existe."""
    modelo = _codigo(MODELO)
    for constante, valor in (
        ('kUnitEpiSourceUnit', 'unit_configured'),
        ('kUnitEpiSourceCompany', 'company_default'),
        ('kUnitEpiSourceSystem', 'system_default'),
    ):
        assert f"{constante} = '{valor}'" in modelo
    from modules.stock.service import (
        ALERT_SOURCE_SYSTEM, ALERT_SOURCE_UNIT,
        ATTENTION_SOURCE_COMPANY, ATTENTION_SOURCE_UNIT,
        MINIMUM_SOURCE_COMPANY, MINIMUM_SOURCE_UNIT,
    )
    assert MINIMUM_SOURCE_UNIT == ATTENTION_SOURCE_UNIT == ALERT_SOURCE_UNIT \
        == 'unit_configured'
    assert MINIMUM_SOURCE_COMPANY == ATTENTION_SOURCE_COMPANY == 'company_default'
    assert ALERT_SOURCE_SYSTEM == 'system_default'


# ── Entrada na tela ──────────────────────────────────────────────────────────

def test_a_entrada_exige_a_mesma_permissao_da_rota():
    """Menu e rota não podem divergir: um ponto único, e não um `if` de papel."""
    codigo = _codigo(TELA_ESTOQUE)
    assert "hasPermission('stock:adjust')" in codigo
    assert 'bool podeConfigurarEstoquePorUnidade(' in codigo
    assert codigo.count("hasPermission('stock:adjust')") == 1, \
        'a regra foi duplicada — mantenha um ponto único'
    # E nenhuma reconstrução por papel.
    assert not re.search(r"role\s*==\s*'(general_admin|admin|user)'", codigo), \
        'a tela voltou a deduzir permissão a partir do papel'


def test_o_deep_link_e_montado_por_query_string():
    """`state.extra` não sobrevive a um refresh de Web."""
    codigo = _codigo(TELA_ESTOQUE)
    assert 'epi_id=' in codigo and 'unit_id=' in codigo
    router = _codigo(ROUTER)
    assert "queryParameters['unit_id']" in router
    assert "queryParameters['epi_id']" in router
    assert 'extra' not in router.split('Routes.stockConfig', 1)[1].split('),', 1)[0]


# ── i18n ─────────────────────────────────────────────────────────────────────

CHAVES = (
    'stockConfigTitle', 'stockConfigIntro', 'stockConfigUnitLabel',
    'stockConfigSelectUnit', 'stockConfigSelectEpi', 'stockConfigEpiLabel',
    'stockConfigEpisLoadError', 'stockConfigNoEpisInUnit',
    'stockConfigUnitBalance', 'stockConfigAttentionLimit',
    'stockConfigUnderlyingStatus', 'stockConfigDerivedUnavailable',
    'stockConfigStatusCritical', 'stockConfigStatusNearMinimum',
    'stockConfigStatusNormal', 'stockConfigStatusDisabled',
    'stockConfigMinimumTitle', 'stockConfigMinimumHelp',
    'stockConfigMinimumLabel', 'stockConfigMinimumNegativeError',
    'stockConfigMinimumSaved', 'stockConfigMinimumRestored',
    'stockConfigAttentionTitle', 'stockConfigAttentionHelp',
    'stockConfigAttentionRangeError', 'stockConfigAttentionSaved',
    'stockConfigAttentionRestored', 'stockConfigAlertTitle',
    'stockConfigAlertHelp', 'stockConfigAlertToggle', 'stockConfigAlertPending',
    'stockConfigAlertDisableTitle', 'stockConfigAlertDisableBody',
    'stockConfigAlertDisableConfirm', 'stockConfigAlertSaved',
    'stockConfigAlertRestored', 'stockConfigOriginUnit',
    'stockConfigOriginCompany', 'stockConfigOriginUnknown',
    'stockConfigSave', 'stockConfigRestore',
)


def test_as_chaves_existem_nos_cinco_idiomas():
    """A CHAVE é o contrato; o rótulo sai do ARB.

    Sem isto o app falaria português nos outros quatro idiomas — foi por esse
    motivo que os rótulos de status do backend nunca são exibidos direto.
    """
    for locale in LOCALES:
        dados = json.loads((L10N / f'{locale}.arb').read_text(encoding='utf-8'))
        faltando = [c for c in CHAVES if c not in dados]
        assert not faltando, f'{locale}: faltam {faltando}'


def test_nenhuma_traducao_ficou_vazia_ou_igual_a_chave():
    for locale in LOCALES:
        dados = json.loads((L10N / f'{locale}.arb').read_text(encoding='utf-8'))
        for chave in CHAVES:
            valor = str(dados[chave]).strip()
            assert valor, f'{locale}.{chave} está vazia'
            assert valor != chave, f'{locale}.{chave} não foi traduzida'


def test_a_tela_nao_exibe_rotulo_vindo_do_backend():
    """Os status chegam como CHAVE e são traduzidos aqui. Um `stock_status`
    desconhecido devolve `null` em vez de inventar 'normal'."""
    tela = _codigo(TELA)
    assert "'critical' => l10n.stockConfigStatusCritical" in tela
    assert '_ => null' in tela.split('_rotuloDeStatus', 1)[1]
