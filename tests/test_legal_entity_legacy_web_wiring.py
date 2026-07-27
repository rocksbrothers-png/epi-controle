"""Fiação dos campos de CNPJ no web legado.

O `index.html` é **gerado** a partir de `static/views/*.html`. Estes testes
olham o arquivo gerado de propósito: é ele que o navegador carrega, e um campo
que exista só no fragmento (ou só no gerado) é um campo que não funciona.

Cobrem a lacuna que motivou o trabalho: sem o seletor de CNPJ, cadastrar
colaborador em empresa com mais de um CNPJ ativo falha, porque o backend
(`resolve_employee_legal_entity_id`) recusa a operação sem o campo.
"""

import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _read(*parts):
    with open(os.path.join(ROOT, *parts), encoding='utf-8') as fh:
        return fh.read()


# ── cadastro de colaborador ──────────────────────────────────────────────────

def test_employee_form_has_legal_entity_select():
    html = _read('static', 'index.html')
    assert 'id="employee-legal-entity"' in html
    # O nome do campo é o que o serializador genérico do formulário envia.
    assert re.search(
        r'<select[^>]*name="legal_entity_id"[^>]*id="employee-legal-entity"', html
    ), 'select de CNPJ precisa enviar legal_entity_id'


def test_employee_legal_entity_field_starts_hidden():
    """Instalação sem Multi-CNPJ provisionado não mostra o campo.

    O `hidden` é o estado inicial; o app revela quando o bootstrap traz CNPJs.
    """
    html = _read('static', 'index.html')
    assert re.search(r'id="employee-legal-entity-field"[^>]*hidden', html)


def test_employee_form_fragment_and_generated_index_agree():
    """Guarda contra editar só o gerado (que o build sobrescreve) ou só a fonte."""
    fragment = _read('static', 'views', 'colaboradores.html')
    assert 'id="employee-legal-entity"' in fragment


# ── filtro de relatórios ─────────────────────────────────────────────────────

def test_report_filter_has_legal_entity_select():
    html = _read('static', 'index.html')
    assert re.search(
        r'<select[^>]*name="legal_entity_id"[^>]*id="report-legal-entity"', html
    )
    assert 'id="report-legal-entity-field"' in _read('static', 'views', 'relatorios.html')


def test_report_payload_sends_legal_entity_id():
    """O backend já filtra por `legal_entity_id`; o legado precisa enviá-lo."""
    app_js = _read('static', 'app.js')
    assert "normalizeOptionalInt('legal_entity_id'" in app_js
    assert "#report-legal-entity" in app_js


# ── cadastro de unidade ──────────────────────────────────────────────────────

def test_unit_form_has_legal_entity_select():
    """Sem este campo o vínculo unidade↔CNPJ só existia no banco.

    O backend aceita `legal_entity_id` em POST/PUT `/api/units` desde a fundação
    do Multi-CNPJ, mas nenhuma tela oferecia o campo — então na prática toda
    unidade nascia sem CNPJ definido.
    """
    html = _read('static', 'index.html')
    assert re.search(
        r'<select[^>]*name="legal_entity_id"[^>]*id="unit-legal-entity"', html
    ), 'select de CNPJ da unidade precisa enviar legal_entity_id'
    assert 'id="unit-legal-entity"' in _read('static', 'views', 'unidades.html')


def test_unit_legal_entity_field_starts_hidden():
    """Empresa sem CNPJs cadastrados não ganha um seletor vazio."""
    html = _read('static', 'index.html')
    assert re.search(r'id="unit-legal-entity-field"[^>]*hidden', html)


def test_unit_legal_entity_follows_the_company_select():
    """CNPJ de outra empresa é recusado pelo backend — a lista tem de resincronizar."""
    app_js = _read('static', 'app.js')
    assert 'function syncUnitLegalEntityOptions()' in app_js
    assert re.search(
        r"getElementById\('unit-company'\), 'change'", app_js
    ), 'trocar a empresa precisa recarregar os CNPJs'


def test_unit_edit_preselects_the_current_legal_entity():
    app_js = _read('static', 'app.js')
    assert re.search(
        r"form\.elements\.legal_entity_id\.value = item\.legal_entity_id", app_js
    )


def test_unit_table_shows_the_legal_entity_column():
    """Empresa com vários CNPJs precisa distinguir as unidades na lista."""
    app_js = _read('static', 'app.js')
    assert 'unitLegalEntityLabel(item)' in app_js
    assert 'data-i18n="unit.tableLegalEntity"' in _read('static', 'views', 'unidades.html')
    assert 'data-i18n="unit.tableLegalEntity"' in _read('static', 'index.html')


# ── módulo de helpers ────────────────────────────────────────────────────────

def test_legal_entity_helpers_module_is_loaded_by_the_page():
    assert 'js/views/legal-entity-fields.js' in _read('static', 'views', '_scripts.html')
    assert 'js/views/legal-entity-fields.js' in _read('static', 'index.html')


def test_employee_legal_entity_is_locked_on_edit():
    """CNPJ é imutável na edição: o campo é travado, não some.

    O operador precisa ver a qual CNPJ o colaborador pertence; trocar exige o
    processo administrativo auditado.
    """
    app_js = _read('static', 'app.js')
    assert 'setEmployeeLegalEntityLock' in app_js
    assert re.search(r'setEmployeeLegalEntityLock\(item\.legal_entity_id \|\| \'\', true\)', app_js)


def test_bootstrap_legal_entities_land_in_state():
    app_js = _read('static', 'app.js')
    assert 'state.legalEntities = Array.isArray(payload.legal_entities)' in app_js


# ── i18n ─────────────────────────────────────────────────────────────────────

def test_legal_entity_labels_exist_in_all_locales():
    import json

    locales = ['pt-BR', 'en-GB', 'es-ES', 'fr-FR', 'nb-NO']
    for locale in locales:
        data = json.loads(_read('static', 'i18n', f'{locale}.json'))
        assert data['employee']['legalEntity'], locale
        assert data['employee']['legalEntityHint'], locale
        for key in ('title', 'select', 'auto', 'selectOptional'):
            assert data['legalEntity'][key], f'{locale}.legalEntity.{key}'
        assert data['unit']['legalEntity'], locale
        assert data['unit']['tableLegalEntity'], locale


# ── filtro em cascata do dashboard ───────────────────────────────────────────

def test_dashboard_scope_filter_is_rendered():
    html = _read('static', 'index.html')
    for element_id in (
        'dashboard-scope-filter',
        'dashboard-scope-legal-entity',
        'dashboard-scope-unit',
        'dashboard-scope-sector',
        'dashboard-scope-clear',
    ):
        assert f'id="{element_id}"' in html, element_id
    assert 'id="dashboard-scope-filter"' in _read('static', 'views', 'dashboard.html')


def test_dashboard_scope_filter_starts_hidden():
    """Sem Multi-CNPJ provisionado o dashboard fica exatamente como era."""
    html = _read('static', 'index.html')
    assert re.search(r'id="dashboard-scope-filter"[^>]*hidden', html)


def test_dashboard_scope_module_loads_before_the_dashboard_view():
    """`dashboard.js` consome `__EPI_DASHBOARD_SCOPE__` — carrega antes dele.

    A leitura é tardia (dentro de `scopeApi()`), então hoje a ordem não
    quebraria nada. Fixamos mesmo assim: é mais barato manter a dependência
    declarada na ordem certa do que descobrir o acoplamento no dia em que
    alguém passar a lê-la no carregamento.
    """
    for source in (
        _read('static', 'views', '_scripts.html'),
        _read('static', 'index.html'),
    ):
        assert 'js/views/dashboard-scope.js' in source
        assert source.index('dashboard-scope.js') < source.index('views/dashboard.js')


def test_dashboard_reads_through_the_scope_helpers():
    """Os KPIs precisam usar o recorte, não `filterByCompany` cru."""
    view = _read('static', 'js', 'views', 'dashboard.js')
    assert 'scopedKeepingCompanyWide(state.epis' in view
    assert 'scoped(state.deliveries' in view
    assert 'scoped(state.employees' in view
    assert 'scopedUnitsList()' in view


def test_dashboard_scope_clear_label_exists_in_all_locales():
    import json

    for locale in ['pt-BR', 'en-GB', 'es-ES', 'fr-FR', 'nb-NO']:
        data = json.loads(_read('static', 'i18n', f'{locale}.json'))
        assert data['dashboard']['clearFilters'], locale
