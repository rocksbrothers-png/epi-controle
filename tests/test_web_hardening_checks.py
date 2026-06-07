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
