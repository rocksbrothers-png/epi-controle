"""Seletor de Unidade na tela de Visibilidade por Módulo do web legado
(PR20, evolução do PR18/PR19: module_visibility como fonte única de
verdade para tenant + perfil + unidade + módulo).

Mesma lógica dos demais testes de fiação do web legado
(tests/test_outsourced_employees_legacy_web_wiring.py): `index.html` é
gerado a partir de `static/views/*.html`, então os testes de HTML olham o
arquivo gerado — é ele que o navegador carrega. A lógica de app.js é
verificada por inspeção estática do código-fonte (mesmo padrão dos demais
testes de fiação — app.js não é executável fora do navegador neste
harness).

Cobre: o bug pré-existente do PR18 (a leitura de `current[moduleKey]`
direto no config do perfil parou de funcionar quando o formato passou de
`{module: bool}` para `{"*": {module: bool}, "<unit_id>": {module: bool}}`
— todo módulo aparecia sempre marcado, independente do valor salvo); o
seletor de Unidade (só visível para admin/user — os únicos papéis com
vínculo de unidade única, MODULE_VISIBILITY_UNIT_SCOPED_ROLES); o fallback
do bucket da Unidade para o bucket "*"; e o envio de `unit_id` no POST.
"""

import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as fh:
        return fh.read()


LOCALES = ("pt-BR", "en-GB", "es-ES", "fr-FR", "nb-NO")


# ── HTML: seletor de Unidade presente no fragmento e no index.html gerado ───

def test_unit_selector_exists_in_fragment_and_generated_index():
    for path in (("static", "views", "configuracao.html"), ("static", "index.html")):
        html = _read(*path)
        assert 'id="module-visibility-unit-wrap"' in html, f"{path}: seletor de Unidade ausente"
        assert 'id="module-visibility-unit"' in html, f"{path}: select de Unidade ausente"
        assert 'name="unit_id"' in html


def test_unit_selector_starts_hidden():
    fragment = _read("static", "views", "configuracao.html")
    wrap = fragment[fragment.index('id="module-visibility-unit-wrap"'):]
    wrap = wrap[:wrap.index(">")]
    assert "hidden" in wrap, "o seletor de Unidade deve iniciar oculto (só aparece para admin/user)"


# ── app.js: papéis escopáveis por Unidade (espelha _UNIT_SCOPED_ROLES) ──────

def test_unit_scoped_roles_constant_matches_backend():
    app_js = _read("static", "app.js")
    match = re.search(r"MODULE_VISIBILITY_UNIT_SCOPED_ROLES = \[([^\]]+)\]", app_js)
    assert match, "MODULE_VISIBILITY_UNIT_SCOPED_ROLES não encontrado em app.js"
    roles = {r.strip().strip("'\"") for r in match.group(1).split(",")}
    assert roles == {"admin", "user"}


# ── app.js: leitura do valor efetivo (bug do PR18 corrigido) ───────────────

def test_effective_value_reads_star_bucket_not_flat_shape():
    app_js = _read("static", "app.js")
    fn = app_js[app_js.index("function moduleVisibilityEffectiveValue("):]
    fn = fn[:fn.index("\n}\n") + 2]
    # A leitura correta é sempre a partir do bucket "*" (roleConfig['*']),
    # nunca roleConfig[moduleKey] direto — essa era a leitura quebrada
    # (regressão silenciosa introduzida pelo PR18: toda checkbox aparecia
    # sempre marcada, porque roleConfig[moduleKey] nunca existia mais).
    assert "roleConfig['*']" in fn
    assert "hasOwnProperty" in fn


def test_render_checkboxes_uses_effective_value_helper():
    app_js = _read("static", "app.js")
    fn = app_js[app_js.index("function renderModuleVisibilityCheckboxes("):]
    fn = fn[:fn.index("\n}\n") + 2]
    assert "moduleVisibilityEffectiveValue(" in fn
    assert "state.moduleVisibilityAdminConfig" in fn


# ── app.js: submit inclui unit_id só quando o seletor está visível ─────────

def test_submit_sends_unit_id_only_when_selector_visible():
    app_js = _read("static", "app.js")
    fn = app_js[app_js.index("async function onSubmitModuleVisibility("):]
    fn = fn[:fn.index("\nfunction ") if "\nfunction " in fn else len(fn)]
    assert "body.unit_id = Number(unitId)" in fn
    assert "moduleVisibilityUnitWrap" in fn
    assert "moduleVisibilityUnitWrap.hidden" in fn


def test_role_change_resyncs_unit_selector_visibility():
    app_js = _read("static", "app.js")
    assert "bindAppListener(refs.moduleVisibilityRole, 'change', () => { syncModuleVisibilityUnitVisibility(); renderModuleVisibilityCheckboxes(); renderModuleVisibilityDefaultPanel(); });" in app_js
    assert "bindAppListener(refs.moduleVisibilityUnit, 'change', () => { renderModuleVisibilityCheckboxes(); });" in app_js


def test_unit_select_populated_from_state_units():
    app_js = _read("static", "app.js")
    fn = app_js[app_js.index("function populateModuleVisibilityUnitSelect("):]
    fn = fn[:fn.index("\n}\n") + 2]
    assert "state.units" in fn
    assert "'module-visibility-unit'" in fn


# ── i18n: chaves presentes e paritárias em todos os locales ────────────────

def test_module_visibility_i18n_keys_present_in_all_locales():
    required = {"unitLabel", "unitHint", "allUnitsOption", "savedForRole", "savedForRoleUnit", "noDefaultModules"}
    import json
    for locale in LOCALES:
        data = json.loads(_read("static", "i18n", f"{locale}.json"))
        block = data.get("moduleVisibility", {})
        missing = required - set(block.keys())
        assert not missing, f"{locale}: chaves moduleVisibility ausentes: {missing}"
        for key in required:
            assert str(block.get(key) or "").strip(), f"{locale}: moduleVisibility.{key} vazio"


# ── Painel "Permissões padrão deste perfil" (reestruturação da tela: a UI
# deixa de parecer a única fonte das permissões, vira uma camada de
# personalização sobre o padrão do sistema) ─────────────────────────────────

def test_default_permissions_panel_exists_in_fragment_and_generated_index():
    for path in (("static", "views", "configuracao.html"), ("static", "index.html")):
        html = _read(*path)
        assert 'id="module-visibility-default-panel"' in html
        assert 'id="module-visibility-default-list"' in html
        assert "Permissões padrão deste perfil" in html


def test_hint_text_frames_configuration_as_a_personalization_layer():
    """Regressão do pedido de produto: o texto anterior ("A permissão
    técnica do perfil é sempre o teto...") dava a entender que a tela
    define o perfil. O novo texto precisa deixar claro que existe um
    padrão do sistema e que esta tela só personaliza."""
    fragment = _read("static", "views", "configuracao.html")
    assert "Permissões padrão." in fragment
    assert "Personalizações." in fragment
    assert "A permissão técnica do perfil é sempre o teto" not in fragment


def test_bootstrap_loads_default_module_visibility_into_state():
    app_js = _read("static", "app.js")
    assert "state.moduleVisibilityDefault = " in app_js
    assert "moduleVisibilityPayload.default_module_visibility" in app_js


def test_render_default_panel_reads_immutable_default_not_admin_config():
    app_js = _read("static", "app.js")
    fn = app_js[app_js.index("function renderModuleVisibilityDefaultPanel("):]
    fn = fn[:fn.index("\n}\n") + 2]
    assert "state.moduleVisibilityDefault" in fn
    # Nunca deve ler moduleVisibilityAdminConfig (isso mostraria a
    # personalização, não o padrão imutável do sistema).
    assert "moduleVisibilityAdminConfig" not in fn


def test_default_panel_rerenders_on_role_change():
    app_js = _read("static", "app.js")
    fn = app_js[app_js.index("function hydrateModuleVisibilityForm("):]
    fn = fn[:fn.index("\n}\n") + 2]
    assert "renderModuleVisibilityDefaultPanel();" in fn
