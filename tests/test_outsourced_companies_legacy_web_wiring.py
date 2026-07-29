"""Fiação da tela de Terceirizados e Prestadores no web legado (PR 8, ADR-0002).

O `index.html` é **gerado** a partir de `static/views/*.html`. Estes testes
olham o arquivo gerado de propósito: é ele que o navegador carrega, e um
campo que exista só no fragmento (ou só no gerado) é um campo que não
funciona. Mesma lógica de tests/test_legal_entity_legacy_web_wiring.py.
"""

import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

LOCALES = ('pt-BR', 'en-GB', 'es-ES', 'fr-FR', 'nb-NO')


def _read(*parts):
    with open(os.path.join(ROOT, *parts), encoding='utf-8') as fh:
        return fh.read()


# ── navegação e module_visibility ───────────────────────────────────────────

def test_nav_button_exists_in_generated_index_and_sidebar_fragment():
    for path in (('static', 'index.html'), ('static', 'views', '_sidebar.html')):
        html = _read(*path)
        assert 'data-view="terceirizados"' in html
        assert 'data-i18n="nav.outsourcedCompanies"' in html


def test_view_permission_reuses_employees_create_floor():
    """Piso técnico do módulo — mesma decisão do ADR (employees:create), sem
    permissão dedicada. Ver MODULE_REQUIRED_PERMISSIONS em rule_engine.py."""
    app_js = _read('static', 'app.js')
    assert "terceirizados: 'employees:create'," in app_js


def test_view_module_is_dedicated_opt_in_key():
    """Diferente de `cnpjs` (que reaproveita o módulo 'administracao'),
    'terceirizados' precisa ter sua PRÓPRIA chave de módulo — é ela que o
    backend usa em _OPT_IN_MODULES para nascer oculta por padrão."""
    app_js = _read('static', 'app.js')
    assert "terceirizados: 'terceirizados'," in app_js


def test_module_visibility_label_registered_for_config_screen():
    """Sem isto o checkbox de Configuração > Regras > Visualização nunca
    aparece, e o Administrador Geral não consegue ligar o módulo."""
    app_js = _read('static', 'app.js')
    assert "terceirizados: 'Terceirizados e Prestadores'" in app_js


# ── view #terceirizados-view ────────────────────────────────────────────────

def test_terceirizados_view_section_exists_and_fragment_agrees():
    html = _read('static', 'index.html')
    assert '<section id="terceirizados-view" class="view">' in html
    fragment = _read('static', 'views', 'terceirizados.html')
    assert '<section id="terceirizados-view" class="view">' in fragment


def test_layout_includes_terceirizados_view_marker():
    layout = _read('static', 'views', '_layout.html')
    assert '<!-- EPI_VIEW_INCLUDE:terceirizados -->' in layout


def test_form_has_expected_fields():
    fragment = _read('static', 'views', 'terceirizados.html')
    assert 'id="outsourced-company-form"' in fragment
    for name in ('legal_name', 'trade_name', 'cnpj', 'company_kind', 'epi_responsibility'):
        assert re.search(rf'name="{name}"', fragment), f'campo {name} ausente do formulário'
    # CNPJ não é `required` — é opcional no Cadastro Simplificado (ADR-0002).
    cnpj_field = re.search(r'<input name="cnpj"[^>]*>', fragment)
    assert cnpj_field and 'required' not in cnpj_field.group(0)


def test_table_has_expected_columns():
    fragment = _read('static', 'views', 'terceirizados.html')
    assert 'id="outsourced-companies-table"' in fragment
    assert 'id="outsourced-companies-filter-search"' in fragment
    assert 'id="outsourced-companies-filter-kind"' in fragment


# ── script registrado ────────────────────────────────────────────────────────

def test_pure_rules_script_is_registered_and_precedes_app_js():
    scripts = _read('static', 'views', '_scripts.html')
    assert 'js/views/outsourced-companies-view.js' in scripts
    generated = _read('static', 'index.html')
    view_pos = generated.index('js/views/outsourced-companies-view.js')
    app_pos = generated.index('/app.js?')
    assert view_pos < app_pos, 'regra pura precisa carregar antes de app.js (que a consome)'


def test_pure_rules_file_exists_and_registers_expected_globals():
    source = _read('static', 'js', 'views', 'outsourced-companies-view.js')
    assert '__EPI_OUTSOURCED_COMPANIES_VIEW__' in source
    for fn in ('companyKindLabel', 'isSimplified', 'visibleOutsourcedCompanies', 'canPromote'):
        assert fn in source


def test_pure_rules_module_covered_by_js_test_harness():
    run_tests = _read('static', 'js', 'test', 'run-tests.js')
    assert "'views/outsourced-companies-view.js'" in run_tests
    assert '__EPI_OUTSOURCED_COMPANIES_VIEW__' in run_tests


# ── CRUD wiring em app.js ────────────────────────────────────────────────────

def test_form_submit_posts_to_outsourced_companies_endpoint():
    app_js = _read('static', 'app.js')
    assert "saveSimpleForm(event, '/api/outsourced-companies', 'employees:create')" in app_js


def test_promote_calls_promote_endpoint():
    app_js = _read('static', 'app.js')
    assert "/api/outsourced-companies/${entityId}/promote" in app_js


def test_list_is_loaded_on_demand_not_from_bootstrap():
    """Módulo opt-in: ao contrário de state.legalEntities, a lista não pode
    vir de loadBootstrap() (rodaria pra todo usuário, módulo ligado ou não)."""
    app_js = _read('static', 'app.js')
    assert 'async function loadOutsourcedCompanies()' in app_js
    bootstrap_section = app_js[app_js.index('async function loadBootstrap()'):app_js.index('async function loadBootstrap()') + 4000]
    assert 'state.outsourcedCompanies' not in bootstrap_section
    assert "view === 'terceirizados' && typeof loadOutsourcedCompanies === 'function'" in app_js


# ── i18n ──────────────────────────────────────────────────────────────────

def test_all_locales_have_nav_key_and_outsourced_company_block():
    for locale in LOCALES:
        data = json.loads(_read('static', 'i18n', f'{locale}.json'))
        assert data['nav'].get('outsourcedCompanies'), f'{locale}: nav.outsourcedCompanies ausente'
        assert 'outsourcedCompany' in data, f'{locale}: bloco outsourcedCompany ausente'


def test_all_locales_have_the_same_outsourced_company_keys():
    key_sets = {}
    for locale in LOCALES:
        data = json.loads(_read('static', 'i18n', f'{locale}.json'))
        key_sets[locale] = set(data['outsourcedCompany'].keys())
    base = key_sets[LOCALES[0]]
    for locale, keys in key_sets.items():
        assert keys == base, f'{locale} diverge de {LOCALES[0]}: {keys.symmetric_difference(base)}'


# ── build reproduz o index.html a partir dos fragmentos ─────────────────────

def test_build_index_view_ids_include_terceirizados_in_correct_position():
    import importlib.util

    spec = importlib.util.spec_from_file_location('build_index', os.path.join(ROOT, 'scripts', 'build_index.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert 'terceirizados' in module.VIEW_IDS
    cnpjs_idx = module.VIEW_IDS.index('cnpjs')
    colaboradores_idx = module.VIEW_IDS.index('colaboradores')
    terceirizados_idx = module.VIEW_IDS.index('terceirizados')
    assert cnpjs_idx < terceirizados_idx < colaboradores_idx
