"""`stock_control_scope` é fronteira de consolidação de LEITURA (ADR-0001 §15).

Guarda estrutural, não de comportamento: varre o código dos caminhos que
**movimentam** estoque e exige que nenhum deles consulte o escopo. A decisão do
cliente é que o estoque pertence exclusivamente a uma unidade — nenhuma
entrega, reserva, baixa, ajuste, devolução ou recebimento pode escolher a
unidade de origem a partir de uma configuração de visualização.

Um teste de comportamento não pegaria isto: hoje nada consome o escopo na
escrita, então não há caso que falhe. O que precisa ser impedido é a
*introdução* futura — e isso se vê no código, não na saída.
"""

import ast
import os

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Símbolos que resolvem "até onde consolidar". Ler qualquer um deles num
# caminho de escrita é o erro que este teste existe para barrar.
SCOPE_SYMBOLS = {
    'get_stock_control_scope',
    'resolve_stock_consolidation_unit_ids',
    'resolve_stock_pool_unit_ids',
    'fetch_scoped_stock_balance',
}

# Módulos que gravam movimentação de estoque.
WRITE_PATH_MODULES = [
    ('modules', 'deliveries', 'service.py'),
    ('modules', 'deliveries', 'routes.py'),
    ('modules', 'devolutions', 'service.py'),
    ('modules', 'purchases', 'service.py'),
    ('modules', 'epis', 'service.py'),
]


def _source(parts):
    with open(os.path.join(ROOT, *parts), encoding='utf-8') as fh:
        return fh.read()


def _referenced_names(source):
    """Nomes citados no módulo, por import ou por chamada."""
    tree = ast.parse(source)
    found = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.Attribute):
            found.add(node.attr)
        elif isinstance(node, ast.Name):
            found.add(node.id)
    return found


@pytest.mark.parametrize('parts', WRITE_PATH_MODULES, ids=lambda p: '/'.join(p[1:]))
def test_write_paths_never_consult_the_consolidation_scope(parts):
    leaked = _referenced_names(_source(parts)) & SCOPE_SYMBOLS
    assert not leaked, (
        f'{"/".join(parts)} consulta {sorted(leaked)}. O escopo consolida leitura; '
        'a unidade de origem da movimentação vem da operação, não da configuração.'
    )


def test_stock_service_uses_the_scope_only_in_the_read_helper():
    """Em `modules/stock/service.py` o escopo pode aparecer — só na leitura.

    Localiza a função que consulta o escopo e exige que seja apenas
    `fetch_scoped_stock_balance`, que não escreve nada.
    """
    source = _source(('modules', 'stock', 'service.py'))
    tree = ast.parse(source)
    functions_touching_scope = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        names = _referenced_names(ast.unparse(node))
        if names & (SCOPE_SYMBOLS - {'fetch_scoped_stock_balance'}):
            functions_touching_scope.add(node.name)
    assert functions_touching_scope == {'fetch_scoped_stock_balance'}, (
        f'Funções consultando o escopo: {sorted(functions_touching_scope)}'
    )


def test_delivery_debits_the_operation_unit():
    """A baixa da entrega usa a unidade da operação, explicitamente."""
    source = _source(('modules', 'deliveries', 'service.py'))
    assert 'upsert_unit_stock(connection, int(payload[\'company_id\']), delivery_unit_id' in source


def test_consolidation_helper_documents_the_boundary():
    """A docstring é o contrato lido por quem for mexer nisso depois."""
    from modules.legal_entities.service import resolve_stock_consolidation_unit_ids

    doc = resolve_stock_consolidation_unit_ids.__doc__ or ''
    assert 'CONSOLIDAÇÃO' in doc
    assert 'nunca de saída' in doc


# ── o rótulo é parte da decisão ──────────────────────────────────────────────
#
# O texto "Controlar estoque por" induzia exatamente à leitura que a §15
# proíbe: a de que a configuração escolheria de onde o material sai. O rótulo
# correto e o texto auxiliar são, aqui, requisito — não cosmética.

def test_legacy_web_exposes_the_consolidation_control():
    html = _source(('static', 'index.html'))
    assert 'data-mc-field="stock_control_scope"' in html
    for value in ('"unit"', '"legal_entity"', '"company"'):
        assert f'<option value={value}' in html


def test_legacy_web_label_is_consolidation_not_control():
    html = _source(('static', 'index.html'))
    assert 'Consolidar saldos de estoque por' in html
    assert 'Controlar estoque por' not in html


def test_legacy_web_helper_text_closes_the_wrong_reading():
    html = _source(('static', 'index.html'))
    assert 'permanecem vinculadas ao estoque de cada unidade' in html


def test_audit_label_no_longer_says_control():
    from modules.company_settings.service import _FIELD_LABELS

    label = _FIELD_LABELS['stock_control_scope']
    assert 'Consolida' in label
    assert 'Controle de estoque' not in label


def test_flutter_and_legacy_share_the_same_helper_text():
    """Os dois clientes precisam dizer a mesma coisa ao operador."""
    import json

    arb = json.loads(_source(('flutter', 'packages', 'epi_i18n', 'lib', 'l10n', 'app_pt_BR.arb')))
    legacy = json.loads(_source(('static', 'i18n', 'pt-BR.json')))
    assert arb['myCompanyStockScope'] == legacy['myCompany']['stockScope']
    assert arb['myCompanyStockScopeHint'] == legacy['myCompany']['stockScopeHint']


def test_helper_text_exists_in_all_five_locales():
    import json

    for locale in ['pt-BR', 'en-GB', 'es-ES', 'fr-FR', 'nb-NO']:
        data = json.loads(_source(('static', 'i18n', f'{locale}.json')))
        assert data['myCompany']['stockScope'], locale
        assert data['myCompany']['stockScopeHint'], locale
    for arb in ['app_pt_BR', 'app_en_US', 'app_es_ES', 'app_fr_FR', 'app_no_NO']:
        data = json.loads(_source(('flutter', 'packages', 'epi_i18n', 'lib', 'l10n', f'{arb}.arb')))
        assert data['myCompanyStockScope'], arb
        assert data['myCompanyStockScopeHint'], arb
