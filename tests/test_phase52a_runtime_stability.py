from pathlib import Path


def _read(path: str) -> str:
    return Path(path).read_text(encoding='utf-8')


def test_hud_requires_query_and_master_admin_gate():
    content = _read('static/app.js')
    assert "params.get('ux_perf_debug') === '1'" in content
    assert "role === 'master_admin'" in content
    assert "EPI_PERF_RUNTIME.debugEnabled = byQuery && isMasterAdmin" in content


def test_safeon_duplicate_block_and_listener_counter_present():
    content = _read('static/app.js')
    assert 'if (handlers.has(handler)) {' in content
    assert 'duplicate listener blocked' in content
    assert 'EPI_PERF_RUNTIME.listenerCount += 1' in content


def test_storage_queue_has_flush_on_unload_and_visibilitychange():
    content = _read('static/app.js')
    assert 'function flushPendingStorageWrites()' in content
    assert "safeOn(globalThis, 'beforeunload', flushPendingStorageWrites);" in content
    assert "safeOn(globalThis, 'pagehide', flushPendingStorageWrites);" in content
    assert "if (document.visibilityState === 'hidden') flushPendingStorageWrites();" in content


def test_analytics_keeps_critical_events_and_dedupes_only_repetitive():
    content = _read('static/ux-analytics.js')
    assert "var REPETITIVE_EVENTS = new Set(['ui:click', 'ui:hover', 'ui:input', 'ui:filter', 'ui:search']);" in content
    assert "if (REPETITIVE_EVENTS.has(name))" in content
    assert "pushEvent('form:error'" in content
    assert "pushEvent('form:submit'" in content
    assert "pushEvent('flow:confirm'" in content
    assert "pushEvent('flow:start'" in content
    assert "pushEvent('flow:complete'" in content


def test_abort_scopes_are_module_specific():
    phase41 = _read('static/ux-phase41.js')
    phase42 = _read('static/ux-phase42.js')
    phase44 = _read('static/ux-phase44.js')
    assert "createScopedAbortController('phase41')" in phase41
    assert "createScopedAbortController('phase42')" in phase42
    assert "createScopedAbortController('phase44')" in phase44


def test_analytics_and_phase42_buffers_remain_limited():
    analytics = _read('static/ux-analytics.js')
    phase42 = _read('static/ux-phase42.js')
    assert 'var MAX_EVENTS = 100;' in analytics
    assert 'var MAX_BYTES = 28000;' in analytics
    assert 'var MAX_EVENTS = 120;' in phase42
    assert 'var MAX_STORAGE_BYTES = 45000;' in phase42
