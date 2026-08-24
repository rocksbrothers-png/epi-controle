"""Paridade funcional entre superfícies — configuração de estoque (#271).

## A regra que este arquivo protege

As superfícies do produto são **permanentes e independentes**: Flutter Web,
Web/SaaS, Android, iOS e Web Legado. Não há "legado temporário" nem "Flutter
como destino". Portanto, uma regra de negócio implementada numa superfície
precisa existir em todas as que a expõem — e "não vale fazer no legado porque
será migrado" deixou de ser argumento aceitável.

Flutter (Web, Android, iOS) compartilha UM cliente: `stock_config_cubit.dart`
mais `stock_api.dart`. Web/SaaS e Web Legado compartilham outro:
`js/views/estoque-config.js`. São **dois** clientes para cinco superfícies, e é
entre esses dois que a divergência pode nascer.

Este gate compara os dois lado a lado. Ele não verifica pintura — compara o
CONTRATO: quais rotas, quais origens, quais limites, quais decisões
operacionais. Um recurso que apareça só de um lado reprova aqui.

A B4 amplia isto para as demais frentes; esta é a fundação.
"""

import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]

# ── Os dois clientes ─────────────────────────────────────────────────────────

DART_CUBIT = RAIZ / 'flutter' / 'apps' / 'epi_admin' / 'lib' / 'core' / 'bloc' / 'stock_config_cubit.dart'
DART_API = RAIZ / 'flutter' / 'packages' / 'epi_api' / 'lib' / 'endpoints' / 'stock_api.dart'
DART_MODEL = RAIZ / 'flutter' / 'packages' / 'epi_api' / 'lib' / 'models' / 'unit_epi_stock_config.dart'
JS_CONFIG = RAIZ / 'static' / 'js' / 'views' / 'estoque-config.js'
JS_APP = RAIZ / 'static' / 'app.js'


def _sem_comentarios(codigo: str) -> str:
    sem_bloco = re.sub(r'/\*.*?\*/', '', codigo, flags=re.DOTALL)
    return '\n'.join(
        linha for linha in sem_bloco.splitlines()
        if not linha.lstrip().startswith('//')
        and not linha.lstrip().startswith('///')
        and not linha.lstrip().startswith('*')
    )


def _flutter() -> str:
    return _sem_comentarios('\n'.join(
        p.read_text(encoding='utf-8') for p in (DART_CUBIT, DART_API, DART_MODEL)
    ))


def _web() -> str:
    fonte = JS_CONFIG.read_text(encoding='utf-8')
    app = JS_APP.read_text(encoding='utf-8')
    i = app.index('// ── Configuração de estoque por Unidade + EPI (#271-B3) ──')
    f = app.index('function stockEpiMatchesMovementSearch(item) {')
    return _sem_comentarios(fonte + '\n' + app[i:f])


# ── As seis rotas, nas duas superfícies ──────────────────────────────────────

ROTAS = (
    '/api/stock/minimum',
    '/api/stock/minimum/restore-default',
    '/api/stock/attention-percentage',
    '/api/stock/attention-percentage/restore-default',
    '/api/stock/alert-enabled',
    '/api/stock/alert-enabled/restore-default',
)


def test_as_seis_rotas_existem_nas_duas_superficies():
    """Nenhum parâmetro pode ser configurável de um lado só.

    É a checagem que teria pego a proposta de "corrigir só o mínimo no legado":
    faixa e alerta ficariam exclusivos do Flutter, e o mesmo operador teria
    poderes diferentes conforme por onde entrasse.
    """
    flutter, web = _flutter(), _web()
    for rota in ROTAS:
        assert f"'{rota}'" in flutter, f'Flutter não chama {rota}'
        assert f"'{rota}'" in web, f'Web Legado/SaaS não chama {rota}'


def test_restaurar_e_operacao_distinta_nas_duas():
    """Salvar 20 e restaurar para 20 terminam com o mesmo número e significam
    coisas opostas. Se uma superfície tratasse restaurar como "salvar o
    padrão", a origem exibida divergiria da outra."""
    flutter, web = _flutter(), _web()
    for rota in (r for r in ROTAS if r.endswith('restore-default')):
        assert f"'{rota}'" in flutter and f"'{rota}'" in web


# ── As três origens ──────────────────────────────────────────────────────────

def test_as_tres_origens_sao_reconhecidas_nas_duas():
    """`system_default` é do alerta; `company_default` é do mínimo e do
    percentual. Uma superfície que não distinga as duas mostraria uma origem
    que não existe."""
    flutter, web = _flutter(), _web()
    for origem in ('unit_configured', 'company_default', 'system_default'):
        assert f"'{origem}'" in flutter, f'Flutter não reconhece {origem}'
        assert f"'{origem}'" in web, f'Web Legado/SaaS não reconhece {origem}'


def test_restaurar_so_e_oferecido_quando_ha_decisao_local_nas_duas():
    flutter, web = _flutter(), _web()
    # Flutter: `isUnitConfigured` alimenta os três `canRestore*`.
    assert 'isUnitConfigured' in flutter
    assert flutter.count('canRestore') >= 3, \
        'Flutter perdeu o gate de restaurar em algum dos três blocos'
    # Web: `canRestore(source)` compartilhado pelos três.
    assert 'function canRestore' in web
    assert web.count('canRestore(') >= 3, \
        'Web Legado/SaaS perdeu o gate de restaurar em algum dos três blocos'


# ── Escopo de Unidade ────────────────────────────────────────────────────────

def test_a_unidade_vem_do_selectable_nas_duas():
    """Fonte única de escopo. `bootstrap.units` é recortado só por tenant e
    entregaria a um perfil travado todas as Unidades da empresa."""
    tela = _sem_comentarios(
        (RAIZ / 'flutter' / 'apps' / 'epi_admin' / 'lib' / 'features' / 'stock' / 'stock_config_screen.dart')
        .read_text(encoding='utf-8')
    )
    # No Flutter a fonte é o widget compartilhado, que por sua vez consome o
    # endpoint; no Web a chamada é direta. São caminhos diferentes para a MESMA
    # fonte — o que não pode acontecer é qualquer um dos dois montar a lista.
    assert 'EpiUnitSelector' in tela and 'UnitSelectorPurpose.write' in tela, \
        'Flutter deixou de usar o seletor compartilhado em modo escrita'
    api_units = _sem_comentarios(
        (RAIZ / 'flutter' / 'packages' / 'epi_api' / 'lib' / 'endpoints' / 'units_api.dart')
        .read_text(encoding='utf-8')
    )
    assert '/api/units/selectable' in api_units, \
        'o cliente Dart deixou de apontar para o selectable'
    assert '/api/units/selectable' in _web(), \
        'Web Legado/SaaS deixou de usar o selectable'


def test_todas_as_unidades_nunca_aparece_em_escrita_nas_duas():
    """Não existe gravar configuração em todas as Unidades. As duas
    superfícies precisam recusar isso na PRÉ-SELEÇÃO, não só na pintura."""
    web = _web()
    corpo = web.split('function initialUnitSelection', 1)[1].split('\n}', 1)[0]
    assert 'allowsAllUnits' not in corpo, 'Web Legado/SaaS pode pré-selecionar "Todas"'

    seletor = _sem_comentarios(
        (RAIZ / 'flutter' / 'apps' / 'epi_admin' / 'lib' / 'core' / 'bloc' / 'unit_selector_cubit.dart')
        .read_text(encoding='utf-8')
    )
    assert 'purpose == UnitSelectorPurpose.read' in seletor, \
        'Flutter deixou de condicionar "Todas" ao propósito de leitura'


def test_perfil_travado_nao_escolhe_unidade_nas_duas():
    web = _web()
    corpo = web.split('function acceptUnit', 1)[1].split('\n  }', 1)[0]
    assert 'scope.locked' in corpo, 'Web Legado/SaaS deixou perfil travado escolher'

    seletor = _sem_comentarios(
        (RAIZ / 'flutter' / 'apps' / 'epi_admin' / 'lib' / 'core' / 'bloc' / 'unit_selector_cubit.dart')
        .read_text(encoding='utf-8')
    )
    assert 'if (scope.locked) return scope.unitId;' in seletor, \
        'Flutter deixou perfil travado escolher'


def test_gravar_sem_unidade_e_fail_closed_nas_duas():
    flutter, web = _flutter(), _web()
    assert 'if (unitId == null || epiId == null || state.isBusy) return;' in flutter, \
        'Flutter deixou de ser fail-closed na gravação'
    assert 'function canWrite' in web and 'blocksEverything' in web, \
        'Web Legado/SaaS deixou de ser fail-closed na gravação'


# ── Autorização ──────────────────────────────────────────────────────────────

def test_a_autorizacao_e_por_permissao_nas_duas():
    """`stock:adjust` nos dois lados — nunca lista de papéis.

    Foi a divergência mais concreta desta frente: o legado testava
    `['admin','user']` e escondia o editor do Administrador Geral, a quem o
    backend concede a permissão.
    """
    web = _web()
    assert "includes('stock:adjust')" in web

    tela_flutter = _sem_comentarios(
        (RAIZ / 'flutter' / 'apps' / 'epi_admin' / 'lib' / 'features' / 'stock' / 'stock_screen.dart')
        .read_text(encoding='utf-8')
    )
    assert "hasPermission('stock:adjust')" in tela_flutter

    for nome, codigo in (('Flutter', tela_flutter), ('Web', web)):
        achados = re.findall(
            r"\[\s*'(?:admin|user|general_admin|registry_admin|master_admin)'[^\]]*\]",
            codigo,
        )
        assert not achados, f'{nome}: autorização por lista de papéis ({achados})'


# ── Decisões operacionais ────────────────────────────────────────────────────

def test_o_toggle_de_alerta_nao_persiste_sozinho_nas_duas():
    """Silenciar o alerta é decisão operacional nas duas superfícies.

    Uma que gravasse ao toque tornaria o silenciamento reversível só por
    acidente — e o mesmo EPI teria proteções diferentes conforme a tela.
    """
    flutter = _flutter()
    corpo = flutter.split('void toggleAlertDraft', 1)[1].split('\n  }', 1)[0]
    assert 'stockApi' not in corpo, 'Flutter: o toggle voltou a persistir sozinho'

    app = JS_APP.read_text(encoding='utf-8')
    li = app.index("bindAppListener(document.getElementById('stock-alert-toggle')")
    corpo_web = _sem_comentarios(app[li:app.index('});', li)])
    assert 'stockAlertEditor.draft' in corpo_web
    assert '/api/stock/alert-enabled' not in corpo_web, \
        'Web Legado/SaaS: o toggle voltou a persistir sozinho'


def test_desligar_o_alerta_pede_confirmacao_nas_duas():
    """E ligar não pede, nas duas. Só o silenciamento é a decisão que merece
    uma pergunta."""
    flutter, web = _flutter(), _web()
    assert 'bool get alertRequiresConfirmation => alertDirty && !alertDraft;' in flutter
    corpo = web.split('function alertNeedsConfirmation', 1)[1].split('\n  }', 1)[0]
    assert 'currentEnabled === true && draftEnabled === false' in corpo


# ── Limites: só os que o backend publica ─────────────────────────────────────

def test_o_minimo_nao_ganha_teto_em_nenhuma_superficie():
    """O backend faz `max(0, int(...))` e não publica teto. Uma superfície que
    inventasse um limite recusaria valores que a outra aceita."""
    flutter = _flutter()
    corpo_dart = flutter.split('Future<void> saveMinimum', 1)[1].split('\n  }', 1)[0]
    assert 'valor < 0' in corpo_dart
    assert not re.search(r'valor\s*>\s*\d+', corpo_dart), 'Flutter inventou teto para o mínimo'

    web = _web()
    corpo_js = web.split('function validateMinimum', 1)[1].split('\n  }', 1)[0]
    assert 'n < 0' in corpo_js
    assert not re.search(r'n\s*>\s*\d+', corpo_js), 'Web Legado/SaaS inventou teto para o mínimo'


def test_o_percentual_usa_o_mesmo_teto_publicado_nas_duas():
    from modules.stock.service import MAX_ATTENTION_PERCENTAGE
    assert MAX_ATTENTION_PERCENTAGE == 100

    flutter = _flutter()
    corpo_dart = flutter.split('Future<void> saveAttention', 1)[1].split('\n  }', 1)[0]
    assert 'percentual < 0 || percentual > 100' in corpo_dart

    web = _web()
    corpo_js = web.split('function validateAttention', 1)[1].split('\n  }', 1)[0]
    assert 'n > 100' in corpo_js


# ── Classificação continua do servidor, nas duas ─────────────────────────────

def test_nenhuma_superficie_recalcula_a_classificacao():
    from tests.stock_rule_scan import comparacoes_saldo_por_minimo

    for nome, codigo in (('Flutter', _flutter()), ('Web Legado/SaaS', _web())):
        achados = comparacoes_saldo_por_minimo(codigo)
        assert not achados, f'{nome} recalcula saldo × mínimo: {achados}'


def test_os_derivados_sao_relidos_do_servidor_nas_duas():
    """As respostas de escrita trazem só o campo alterado e a origem.
    `attention_limit` e `stock_status` vêm da releitura — calculá-los local
    faria as superfícies divergirem no arredondamento."""
    flutter, web = _flutter(), _web()
    assert '_recarregarDerivados' in flutter and 'fetchUnitStockEpis' in flutter
    corpo = web.split('async function runStockConfigWrite', 1)[1].split('\n}', 1)[0]
    assert 'await loadStockEpis()' in corpo, \
        'Web Legado/SaaS deixou de reler os derivados após gravar'


# ── O inventário, para a B4 crescer em cima ──────────────────────────────────

def test_o_inventario_de_capacidades_esta_completo():
    """Doze capacidades, presentes nas duas superfícies.

    Esta lista é o que a B4 vai expandir para as demais frentes. Ela existe
    para que "paridade" seja verificável em vez de afirmada — e para que uma
    capacidade nova nasça já com o par do outro lado.
    """
    flutter, web = _flutter(), _web()
    capacidades = {
        'mínimo — gravar': ('/api/stock/minimum', '/api/stock/minimum'),
        'mínimo — restaurar': ('/api/stock/minimum/restore-default',) * 2,
        'atenção — gravar': ('/api/stock/attention-percentage',) * 2,
        'atenção — restaurar': ('/api/stock/attention-percentage/restore-default',) * 2,
        'alerta — gravar': ('/api/stock/alert-enabled',) * 2,
        'alerta — restaurar': ('/api/stock/alert-enabled/restore-default',) * 2,
    }
    faltando = []
    for nome, (ancora_dart, ancora_js) in capacidades.items():
        if f"'{ancora_dart}'" not in flutter:
            faltando.append(f'{nome} (Flutter)')
        if f"'{ancora_js}'" not in web:
            faltando.append(f'{nome} (Web Legado/SaaS)')
    assert not faltando, f'capacidades sem par entre superfícies: {faltando}'
