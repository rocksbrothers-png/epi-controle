"""Seletor de Unidade compartilhado — o lado Flutter.

Não há toolchain Dart neste ambiente: `flutter analyze` e `flutter test` só
rodam no CI. Estes testes protegem a fronteira que uma edição bem-intencionada
reabre em uma linha — a interface voltar a decidir quem pode ver o quê.

A regra desta fatia, em uma frase: **o backend decide, o cliente desenha.**
"""

import json
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
FLUTTER = RAIZ / 'flutter'
APP = FLUTTER / 'apps' / 'epi_admin' / 'lib'

MODELO = FLUTTER / 'packages' / 'epi_api' / 'lib' / 'models' / 'selectable_units.dart'
UNITS_API = FLUTTER / 'packages' / 'epi_api' / 'lib' / 'endpoints' / 'units_api.dart'
EXPORTS = FLUTTER / 'packages' / 'epi_api' / 'lib' / 'epi_api.dart'
CUBIT = APP / 'core' / 'bloc' / 'unit_selector_cubit.dart'
WIDGET = APP / 'core' / 'widgets' / 'unit_selector.dart'
TESTE_DART = (FLUTTER / 'apps' / 'epi_admin' / 'test' / 'unit_selector_cubit_test.dart')

LOCALES = ('app_pt_BR', 'app_en_US', 'app_es_ES', 'app_fr_FR', 'app_no_NO')
L10N = FLUTTER / 'packages' / 'epi_i18n' / 'lib' / 'l10n'

CHAVES = (
    'unitSelectorLabel',
    'unitSelectorAllUnits',
    'unitSelectorLockedHint',
    'unitSelectorLoadError',
    'unitSelectorNoUnitsAssigned',
    'unitSelectorCompanyHasNoUnits',
)


def _sem_comentarios(texto: str) -> str:
    return '\n'.join(
        linha for linha in texto.split('\n')
        if not linha.lstrip().startswith('//')
    )


def _codigo(caminho: Path) -> str:
    return _sem_comentarios(caminho.read_text(encoding='utf-8'))


def test_os_arquivos_da_fatia_existem():
    for caminho in (MODELO, CUBIT, WIDGET, TESTE_DART):
        assert caminho.exists(), f'{caminho.name} sumiu'


def test_o_modelo_esta_exportado():
    assert "export 'models/selectable_units.dart';" in \
        EXPORTS.read_text(encoding='utf-8')


def test_o_cliente_consome_a_rota_recortada():
    fonte = _codigo(UNITS_API)
    assert "'/api/units/selectable'" in fonte


def test_a_rota_do_seletor_nao_recebe_unit_id_nem_company_id():
    """O escopo vem do ator. Mandar qualquer um dos dois moveria a decisão."""
    fonte = _codigo(UNITS_API)
    corpo = fonte.split('getSelectableUnits')[1].split('\n  }')[0]
    assert 'unit_id' not in corpo
    assert 'company_id' not in corpo


# ── O cliente não reconstrói permissão ──────────────────────────────────────

def test_o_seletor_nao_usa_bootstrap_units():
    """`bootstrap.units` é recortado só por tenant: entrega a empresa inteira."""
    for caminho in (CUBIT, WIDGET):
        assert 'bootstrap' not in _codigo(caminho), \
            f'{caminho.name} voltou a montar a lista a partir do bootstrap'


def test_nem_o_cubit_nem_o_widget_decidem_por_perfil():
    for caminho in (CUBIT, WIDGET):
        fonte = _codigo(caminho)
        for perfil in ("'admin'", "'user'", "'general_admin'", "'registry_admin'",
                       "'buyer'", "'approver'", "'master_admin'"):
            assert perfil not in fonte, \
                f'{caminho.name} passou a decidir por perfil ({perfil})'
        assert 'hasPermission' not in fonte, \
            f'{caminho.name} passou a avaliar permissão no cliente'


def test_todas_as_unidades_nao_e_derivado_do_tamanho_da_lista():
    """Carteira de uma Unidade tem lista não-vazia e não oferece "Todas"."""
    fonte = _codigo(CUBIT)
    assert 'allowsAllUnits' in fonte
    corpo = fonte.split('get offersAllUnits')[1].split(';')[0]
    assert 'allowsAllUnits' in corpo
    assert 'length' not in corpo, \
        '"Todas" passou a ser derivado do tamanho da lista'


def test_todas_as_unidades_nunca_aparece_em_escrita():
    fonte = _codigo(CUBIT)
    corpo = fonte.split('get offersAllUnits')[1].split(';')[0]
    assert 'UnitSelectorPurpose.read' in corpo, \
        'a conjunção com o propósito sumiu — escrita passaria a oferecer "Todas"'


def test_escrita_exige_unidade_especifica():
    fonte = _codigo(CUBIT)
    assert 'bool get canWrite => selectedUnitId != null;' in fonte, \
        'gravar deixou de exigir uma Unidade real'


def test_carteira_vazia_nao_vira_empresa_inteira():
    """`blocksEverything` é campo próprio, não inferido de lista vazia."""
    fonte = _codigo(MODELO)
    assert 'blocksEverything' in fonte
    assert "json['blocks_everything'] == true" in fonte, \
        'blocks_everything passou a ser inferido em vez de lido'


def test_payload_ausente_nao_vira_permissivo():
    """Campo faltando não pode virar "pode ver tudo"."""
    fonte = _codigo(MODELO)
    assert "json['allows_all_units'] == true" in fonte, \
        'allows_all_units passou a ter default permissivo'
    assert "json['locked'] == true" in fonte
    assert 'allowsAllUnits: true' not in fonte


def test_falha_de_carga_nao_abre_o_escopo():
    fonte = _codigo(CUBIT)
    trecho = fonte.split('} on Object catch')[1]
    assert 'SelectableUnits.empty' in trecho, \
        'erro de carga passou a manter o escopo anterior — fail-open'


def test_perfil_travado_nao_troca_de_unidade():
    fonte = _codigo(CUBIT)
    corpo = fonte.split('void select(')[1].split('\n  }')[0]
    assert 'scope.locked' in corpo, \
        'o perfil travado voltou a poder trocar de Unidade'


def test_a_escolha_e_validada_contra_a_lista_do_servidor():
    fonte = _codigo(CUBIT)
    corpo = fonte.split('void select(')[1].split('\n  }')[0]
    assert 'scope.units.any' in corpo, \
        'o cubit passou a aceitar Unidade que o servidor não ofereceu'


def test_perfil_travado_aparece_desabilitado_e_nao_escondido():
    """Saber em qual Unidade se está operando vale o controle."""
    fonte = _codigo(WIDGET)
    assert 'travado ? null : cubit.select' in fonte, \
        'o seletor deixou de desabilitar para perfil travado'
    assert 'unitSelectorLockedHint' in fonte


def test_as_duas_listas_vazias_tem_mensagens_diferentes():
    fonte = _codigo(WIDGET)
    assert 'unitSelectorNoUnitsAssigned' in fonte
    assert 'unitSelectorCompanyHasNoUnits' in fonte, \
        'carteira vazia e empresa sem Unidades voltaram a ter a mesma mensagem'


# ── i18n ────────────────────────────────────────────────────────────────────

def test_as_chaves_existem_nos_cinco_idiomas():
    for locale in LOCALES:
        dados = json.loads((L10N / f'{locale}.arb').read_text(encoding='utf-8'))
        faltando = [c for c in CHAVES if c not in dados]
        assert not faltando, f'{locale}: faltam {faltando}'


def test_o_widget_nao_tem_string_literal_de_interface():
    fonte = _codigo(WIDGET)
    literais = []
    for bruto in re.findall(r"Text\(\s*'([^']*)'", fonte):
        sem_interpolacao = re.sub(r'\$\{[^}]*\}|\$\w+', '', bruto)
        if re.search(r'[A-Za-zÀ-ÿ]{3,}', sem_interpolacao):
            literais.append(bruto)
    assert not literais, f'strings fora do ARB no seletor: {literais}'
