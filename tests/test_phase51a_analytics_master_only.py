from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding='utf-8')


def test_analytics_storage_and_master_scope_contract():
    analytics_js = _read('static/ux-analytics.js')
    assert "const STORAGE_KEY = 'epi.analytics.master.events';" in analytics_js
    assert "const LEGACY_STORAGE_KEY = 'epi.analytics.events';" in analytics_js
    assert "function canAccessAnalytics()" in analytics_js
    assert "return isMasterRole(resolveCurrentRole());" in analytics_js
    assert "if (!canAccessAnalytics()) return false;" in analytics_js
    assert "ensureUnauthorizedStorageIsNotExposed();" in analytics_js


def test_analytics_querystring_and_api_are_protected_for_non_master():
    analytics_js = _read('static/ux-analytics.js')
    assert "params.get('ux_analytics')" in analytics_js
    assert "params.get('ux_analytics_reset')" in analytics_js
    assert "if (!canAccessAnalytics()) {" in analytics_js
    assert "return { allowed: false, events: [] };" in analytics_js
    assert "getEvents: () => getEventsForApi()," in analytics_js


def test_analytics_sanitization_and_primary_action_strategy():
    analytics_js = _read('static/ux-analytics.js')
    assert 'data-analytics-action' in analytics_js
    assert 'data-primary-action' in analytics_js
    assert "source: 'data_attribute'" in analytics_js
    assert 'class_fallback' in analytics_js
    assert 'messagePreview' not in analytics_js
    assert 'password' not in analytics_js.lower()
    assert 'token' not in analytics_js.lower()
    assert 'cpf' not in analytics_js.lower()
    assert 'formdata' not in analytics_js.lower()
