"""Fiação do Cadastro de Colaboradores no web legado (PR 15, ADR-0002 §10).

Cobre a extensão que faltava do web legado dentro da mesma tela de
Terceirizados e Prestadores: aba "Cadastro de Colaboradores" (só
terceirizado/prestador, nunca CLT), arquivamento de empresas e
colaboradores, relatório de headcount, e a correção de escopo (rota/menu
aceita employees:create OU employees:create_simplified, e o módulo
terceirizados OU terceirizados_colaboradores). Mesma lógica de
tests/test_outsourced_companies_legacy_web_wiring.py: `index.html` é
gerado a partir de `static/views/*.html`, então os testes olham o arquivo
gerado — é ele que o navegador carrega.

A antiga admin UI de module_unit_scope foi retirada no PR18 (evolução para
override por Unidade dentro de module_visibility) — o web legado ganha a
nova experiência unificada no PR20.
"""

import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

LOCALES = ('pt-BR', 'en-GB', 'es-ES', 'fr-FR', 'nb-NO')


def _read(*parts):
    with open(os.path.join(ROOT, *parts), encoding='utf-8') as fh:
        return fh.read()


# ── correção de escopo: permissão/módulo alternativos (ADR-0002 §10.3) ──────

def test_role_permissions_grant_create_simplified_to_admin_and_user():
    """admin (Administrador Local) e user (Gestor de EPI) nunca têm
    employees:create/update — só a versão simplificada (ADR-0002 §10.2).
    Sem isto, o Cadastro de Colaboradores nunca aparece pra estes papéis."""
    app_js = _read('static', 'app.js')
    admin_block = app_js[app_js.index('admin: ['):app_js.index('buyer: [')]
    assert 'employees:create_simplified' in admin_block
    assert 'employees:update_simplified' in admin_block
    user_block = app_js[app_js.index('user: ['):app_js.index('employee: []')]
    assert 'employees:create_simplified' in user_block
    assert 'employees:update_simplified' in user_block


def test_master_admin_excludes_create_simplified_like_full_create():
    """Mesma regra do backend (core/permissions.py
    MASTER_ADMIN_OPERATIONAL_EXCLUSIONS): master_admin não retém
    employees:create_simplified/update_simplified de forma permanente."""
    app_js = _read('static', 'app.js')
    exclusions = re.search(r'MASTER_ADMIN_OPERATIONAL_EXCLUSIONS = \[([^\]]+)\]', app_js)
    assert exclusions, 'MASTER_ADMIN_OPERATIONAL_EXCLUSIONS não encontrado'
    assert "'employees:create_simplified'" in exclusions.group(1)
    assert "'employees:update_simplified'" in exclusions.group(1)


def test_view_permission_alternative_and_module_alternative_registered():
    """A rota/menu de Terceirizados e Prestadores precisa aceitar
    employees:create OU employees:create_simplified, e o módulo
    terceirizados OU terceirizados_colaboradores — sem isso, admin/user (que
    só têm a permissão/módulo simplificado) nunca alcançam a tela."""
    app_js = _read('static', 'app.js')
    assert "terceirizados: 'employees:create_simplified'" in app_js
    assert "terceirizados: 'terceirizados_colaboradores'" in app_js


def test_can_access_view_checks_both_alternatives():
    app_js = _read('static', 'app.js')
    fn = app_js[app_js.index('function canAccessView(view) {'):app_js.index('globalThis.canAccessView = canAccessView;')]
    assert 'VIEW_PERMISSION_ALTERNATIVES' in fn
    assert 'VIEW_MODULE_ALTERNATIVES' in fn


def test_show_view_second_permission_gate_also_checks_the_alternative():
    """Regressão: showView() tem um segundo gate de permissão (o que dispara
    o alert "Seu perfil Não pode acessar esta área.") separado de
    canAccessView() — antes desta correção ele não conhecia
    VIEW_PERMISSION_ALTERNATIVES, então Administrador Local/Gestor de EPI
    viam "Terceirizados e Prestadores" no menu (canAccessView liberava pela
    alternativa) mas eram bloqueados com o alerta ao clicar (este segundo
    gate só checava employees:create, que eles não têm)."""
    app_js = _read('static', 'app.js')
    fn = app_js[app_js.index('function showView(view, options = {}) {'):app_js.index("if (view === 'configuracao' && !hasConfigurationAccess())")]
    assert 'VIEW_PERMISSION_ALTERNATIVES' in fn


def test_module_visibility_label_registered_for_colaboradores_module():
    app_js = _read('static', 'app.js')
    assert "terceirizados_colaboradores: 'Cadastro de Colaboradores'" in app_js


# ── view: novas abas dentro de #terceirizados-view ──────────────────────────

def test_new_vtabs_exist_in_generated_index_and_fragment():
    for path in (('static', 'index.html'), ('static', 'views', 'terceirizados.html')):
        html = _read(*path)
        for tab in ('colaboradores', 'arquivados-empresas', 'arquivados-colaboradores', 'relatorios'):
            assert f'data-vtab="{tab}"' in html, f'{path}: aba {tab} ausente'


def test_employee_form_has_expected_fields():
    fragment = _read('static', 'views', 'terceirizados.html')
    assert 'id="outsourced-employee-form"' in fragment
    for name in (
        'company_id', 'unit_id', 'outsourced_company_id', 'name', 'cpf', 'role_name',
        'tipo_vinculo', 'admission_date', 'origin_company_registration', 'badge_number', 'notes',
    ):
        assert re.search(rf'name="{name}"', fragment), f'campo {name} ausente do formulário simplificado'
    # tipo_vinculo nunca oferece CLT — Cadastro de Colaboradores é só
    # terceirizado/prestador (o backend também recusa CLT).
    tipo_select = re.search(r'<select name="tipo_vinculo"[^>]*>.*?</select>', fragment, re.S)
    assert tipo_select and 'CLT' not in tipo_select.group(0)


def test_employee_table_has_expected_columns():
    fragment = _read('static', 'views', 'terceirizados.html')
    assert 'id="outsourced-employees-table"' in fragment
    assert 'id="outsourced-employees-filter-search"' in fragment


def test_archived_tables_exist_with_filters():
    fragment = _read('static', 'views', 'terceirizados.html')
    for prefix in ('archived-outsourced-companies', 'archived-outsourced-employees'):
        assert f'id="{prefix}-table"' in fragment
        assert f'id="{prefix}-filter-company"' in fragment
        assert f'id="{prefix}-filter-date"' in fragment
        assert f'id="{prefix}-filter-reason"' in fragment
        assert f'id="{prefix}-filter-user"' in fragment


def test_reports_table_exists():
    fragment = _read('static', 'views', 'terceirizados.html')
    assert 'id="outsourced-employees-summary-table"' in fragment


# ── ARCHIVAL_ENTITIES extension ──────────────────────────────────────────────

def test_archival_entities_has_outsourced_company_with_purge():
    app_js = _read('static', 'app.js')
    entities_block = app_js[app_js.index('const ARCHIVAL_ENTITIES = {'):app_js.index('async function _epiArchivalPreflight')]
    assert 'outsourcedCompany: {' in entities_block
    outsourced_company_block = entities_block[entities_block.index('outsourcedCompany: {'):entities_block.index('outsourcedEmployee: {')]
    assert "path: '/api/outsourced-companies'" in outsourced_company_block
    assert 'supportsPurge: false' not in outsourced_company_block
    assert 'purgeLabels' in outsourced_company_block


def test_archival_entities_has_outsourced_employee_filtered_by_query():
    app_js = _read('static', 'app.js')
    entities_block = app_js[app_js.index('const ARCHIVAL_ENTITIES = {'):app_js.index('async function _epiArchivalPreflight')]
    assert 'outsourcedEmployee: {' in entities_block
    outsourced_employee_block = entities_block[entities_block.index('outsourcedEmployee: {'):]
    assert "path: '/api/employees'" in outsourced_employee_block
    assert "archivedQueryExtra: '&outsourced_only=1'" in outsourced_employee_block


def test_purge_button_and_purge_call_respect_supports_purge_flag():
    app_js = _read('static', 'app.js')
    assert 'canPurge && cfg.supportsPurge !== false' in app_js
    assert 'cfg.supportsPurge === false' in app_js


def test_load_archived_records_appends_query_extra():
    app_js = _read('static', 'app.js')
    assert 'cfg.archivedQueryExtra' in app_js


def test_archival_bindings_cover_new_kinds():
    app_js = _read('static', 'app.js')
    assert "['outsourcedCompany', 'archivedOutsourcedCompanies']" in app_js
    assert "['outsourcedEmployee', 'archivedOutsourcedEmployees']" in app_js


# ── Arquivar na lista ativa: mesma dupla de permissões do restaurar ────────
# Bug reportado em produção: o botão "Arquivar" desta tela nunca aparecia
# para Administrador Local/Gestor de EPI, que só têm
# employees:update_simplified (nunca employees:delete). O botão "Restaurar"
# da aba "Colaboradores Arquivados" já usava a dupla de permissões correta
# (ARCHIVAL_ENTITIES.outsourcedEmployee.deletePermission) — só o "Arquivar"
# da lista ativa tinha ficado de fora.

def test_archive_button_accepts_the_update_simplified_alternative():
    app_js = _read('static', 'app.js')
    fn = app_js[app_js.index('function formatOutsourcedEmployeeRow('):]
    fn = fn[:fn.index('\n}\n') + 2]
    assert "hasPermission('employees:delete') || permissions.canUpdate" in fn


def test_archive_outsourced_employee_uses_the_outsourced_kind_not_plain_employee():
    """kind errado ('employee') usava ARCHIVAL_ENTITIES.employee —
    deletePermission só 'employees:delete' (sem a alternativa) e recarregava
    a lista de arquivados do Cadastro de Colaboradores completo, não a desta
    tela (archivedOutsourcedEmployees, filtrada outsourced_only=1)."""
    app_js = _read('static', 'app.js')
    fn = app_js[app_js.index('async function archiveOutsourcedEmployee('):]
    fn = fn[:fn.index('\n}\n') + 2]
    assert "archiveEntityRecord('outsourcedEmployee', entityId)" in fn


# ── CRUD wiring em app.js ────────────────────────────────────────────────────

def test_employee_form_submit_posts_to_outsourced_simplified_endpoint():
    app_js = _read('static', 'app.js')
    assert "saveSimpleForm(event, '/api/employees/outsourced-simplified', 'employees:create_simplified')" in app_js


def test_employees_summary_loaded_from_report_endpoint():
    app_js = _read('static', 'app.js')
    assert '/api/outsourced-companies/employees-summary' in app_js


def test_employees_list_is_derived_client_side_not_from_new_route():
    """Sem rota de listagem própria — deriva de state.employees (já
    carregado pelo bootstrap), mesma estratégia do app Flutter."""
    app_js = _read('static', 'app.js')
    assert 'function outsourcedEmployeesList()' in app_js
    fn = app_js[app_js.index('function outsourcedEmployeesList()'):app_js.index('function outsourcedEmployeesList()') + 600]
    assert 'state.employees' in fn


def test_terceirizados_showview_hook_loads_new_sections():
    app_js = _read('static', 'app.js')
    hook = app_js[app_js.index("if (view === 'terceirizados' && typeof loadOutsourcedCompanies"):]
    hook = hook[:hook.index('}') + 1]
    assert "loadArchivedRecords('outsourcedCompany')" in hook
    assert "loadArchivedRecords('outsourcedEmployee')" in hook
    assert 'loadOutsourcedEmployeesSummary()' in hook


# ── script registrado (pure-view-helpers) ────────────────────────────────────

def test_pure_rules_script_is_registered_and_precedes_app_js():
    scripts = _read('static', 'views', '_scripts.html')
    assert 'js/views/outsourced-employees-view.js' in scripts
    generated = _read('static', 'index.html')
    view_pos = generated.index('js/views/outsourced-employees-view.js')
    app_pos = generated.index('/app.js?')
    assert view_pos < app_pos, 'regra pura precisa carregar antes de app.js (que a consome)'


def test_pure_rules_file_exists_and_registers_expected_globals():
    source = _read('static', 'js', 'views', 'outsourced-employees-view.js')
    assert '__EPI_OUTSOURCED_EMPLOYEES_VIEW__' in source
    for fn in ('tipoVinculoLabel', 'outsourcedEmployeesOnly', 'visibleOutsourcedEmployees'):
        assert fn in source


def test_pure_rules_module_covered_by_js_test_harness():
    run_tests = _read('static', 'js', 'test', 'run-tests.js')
    assert "'views/outsourced-employees-view.js'" in run_tests
    assert '__EPI_OUTSOURCED_EMPLOYEES_VIEW__' in run_tests


# ── i18n ──────────────────────────────────────────────────────────────────

def test_all_locales_have_the_same_outsourced_company_keys():
    key_sets = {}
    for locale in LOCALES:
        data = json.loads(_read('static', 'i18n', f'{locale}.json'))
        key_sets[locale] = set(data['outsourcedCompany'].keys())
    base = key_sets[LOCALES[0]]
    for locale, keys in key_sets.items():
        assert keys == base, f'{locale} diverge de {LOCALES[0]}: {keys.symmetric_difference(base)}'


# ── Unidade travada para Administrador Local/Gestor de EPI (PR24-1) ────────
# Bug reportado em produção: o campo Unidade do Cadastro de Colaboradores
# aparecia como um seletor livre com todas as unidades do tenant para
# admin/user, que só podem operar na própria unidade operacional
# (backend já força isso em ensure_actor_unit_scope_for_target — esta é só
# a correção de UX que faltava, para não deixar o perfil escolher algo que
# o backend vai recusar).

def test_unit_field_hint_exists_in_fragment_and_generated_index():
    for path in (('static', 'views', 'terceirizados.html'), ('static', 'index.html')):
        html = _read(*path)
        assert 'id="outsourced-employee-unit-hint"' in html


def test_sync_outsourced_employee_unit_options_locks_the_field_for_operational_profiles():
    app_js = _read('static', 'app.js')
    fn = app_js[app_js.index('function syncOutsourcedEmployeeUnitOptions('):]
    fn = fn[:fn.index('\n}\n') + 2]
    assert 'isOperationalProfile()' in fn
    assert 'operational_unit_id' in fn
    assert 'unitField.disabled = lockByOperationalProfile' in fn
