import scripts.check_web_hardening as hardening


def test_local_script_paths_strip_querystrings_and_skip_external_sources():
    html = '''
    <script defer src="/i18n.js?v=20260604-02"></script>
    <script src="tenant-init.js?v=abc"></script>
    <script src="https://unpkg.com/htmx.org@1.9.12"></script>
    <script src="//example.com/external.js"></script>
    '''

    paths = hardening.local_script_paths(html)

    assert paths == [
        hardening.ROOT / "static" / "i18n.js",
        hardening.ROOT / "static" / "tenant-init.js",
    ]


def test_i18n_module_exposes_safe_dynamic_translation_helper():
    source = hardening.I18N_PATH.read_text(encoding="utf-8")

    assert "function trEpi(key, fallback)" in source
    assert "window.trEpi = trEpi" in source
    assert "trEpi," in source


def test_i18n_helper_is_loaded_between_i18n_engine_and_tenant_bootstrap():
    index = hardening.INDEX_PATH.read_text(encoding="utf-8")

    assert index.index('/i18n.js') < index.index('/i18n-helper.js') < index.index('/tenant-init.js')


def test_i18n_helper_owns_legacy_translation_fallback_resolution():
    source = (hardening.ROOT / "static" / "i18n-helper.js").read_text(encoding="utf-8")

    assert "function resolveLegacyTranslator()" in source
    assert "const existingTranslator = global.trEpi;" in source
    assert "if (typeof existingTranslator !== 'function') global.trEpi = translator;" in source
    assert "fallbackTranslate," in source
    assert "resolveLegacyTranslator," in source


def test_legacy_app_delegates_tr_epi_resolution_to_i18n_helper():
    source = (hardening.ROOT / "static" / "app.js").read_text(encoding="utf-8")

    assert "globalThis.EpiI18nHelper.resolveLegacyTranslator()" in source
    assert "typeof globalThis.EpiI18nHelper.resolveLegacyTranslator === 'function'" in source
    assert "typeof globalThis.trEpi === 'function'" in source
    assert "if (typeof globalThis.trEpi !== 'function') globalThis.trEpi = tr;" in source
    assert "\nglobalThis.trEpi = tr;" not in source


def test_dashboard_static_selectors_tables_and_help_are_i18n_ready():
    index = hardening.INDEX_PATH.read_text(encoding="utf-8")

    required_markers = [
        'data-i18n="dashboard.interactiveLoadingTitle"',
        'data-i18n="dashboard.interactiveLoadingHint"',
        'data-i18n="dashboard.interactiveErrorTitle"',
        'data-i18n="dashboard.interactiveErrorHint"',
        'data-i18n-aria-label="dashboard.kpiRegion"',
        'data-i18n="dashboard.quickOperationalView"',
        'data-i18n="dashboard.partialSummary"',
        'data-i18n="dashboard.ready"',
        'data-i18n-placeholder="dashboard.approvedSearchName"',
        'data-i18n-placeholder="dashboard.approvedSearchProtection"',
        'data-i18n-placeholder="dashboard.approvedSearchCa"',
        'data-i18n-placeholder="dashboard.approvedSearchManufacturer"',
        'data-i18n-placeholder="dashboard.approvedSearchSection"',
        'data-i18n="dashboard.tableEpi"',
        'data-i18n="dashboard.tableManufacturer"',
        'data-i18n="dashboard.tableModelReference"',
        'data-i18n="dashboard.tableCaExpiry"',
        'data-i18n="dashboard.tableUsefulLifeMonths"',
        'data-i18n="dashboard.tableRecommendationRestriction"',
    ]
    for marker in required_markers:
        assert marker in index


def test_dashboard_dynamic_indicator_labels_use_i18n_helper():
    # Search across app.js and extracted view modules — functions may live in either
    sources = [
        (hardening.ROOT / "static" / "app.js").read_text(encoding="utf-8"),
        *(p.read_text(encoding="utf-8") for p in (hardening.ROOT / "static" / "js" / "views").glob("*.js")),
    ]
    combined = "\n".join(sources)

    required_keys = [
        "dashboard.noAlertsFilter",
        "dashboard.noDeliveriesFilter",
        "dashboard.noDataFilter",
        "dashboard.returnedDeliveries",
        "dashboard.activeEmployees",
        "dashboard.feedbacks",
        "dashboard.complaintsPraise",
        "dashboard.dbPoolUse",
        "dashboard.dbPoolFree",
        "dashboard.noCompany",
        "dashboard.noUnit",
        # Painel executivo consolidado (auditoria Dashboard): grupos por prioridade
        # e novos indicadores — labels dinâmicos também via i18n.
        "dashboard.groupOperational",
        "dashboard.groupSafety",
        "dashboard.groupManagerial",
        "dashboard.criticalStock",
        "dashboard.caExpired",
        "dashboard.caExpiring",
        "dashboard.negativeEvaluations",
    ]
    for key in required_keys:
        assert f"tr('{key}'" in combined


def test_ca_static_labels_are_i18n_ready_for_ce_locales():
    index = hardening.INDEX_PATH.read_text(encoding="utf-8")

    assert 'data-i18n="epi.caShort"' in index
    assert 'data-i18n="epi.ca"' in index
    assert 'data-i18n-placeholder="epi.caNumberHint"' in index
    assert 'data-i18n="epi.withoutBrazilCa"' in index
    assert '<th>CA</th>' not in index
    assert 'placeholder="Número do CA" data-i18n-placeholder="epi.caNumberHint"' in index


def test_dynamic_ca_labels_use_i18n_helper_for_ce_locales():
    source = (hardening.ROOT / "static" / "app.js").read_text(encoding="utf-8")

    assert source.count("tr('epi.caShort', 'CA')") >= 10
    assert "| CA:" not in source
    assert " — CA" not in source
    assert "<small>CA:" not in source
