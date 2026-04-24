from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding='utf-8')


def test_feature_flags_have_central_resolver_and_precedence_contract():
    app_js = _read('static/app.js')
    assert 'function getFeatureFlagResolution(flagName, options = {})' in app_js
    assert "source: 'querystring'" in app_js
    assert "source: 'localStorage'" in app_js
    assert "source: 'default'" in app_js
    assert "source: 'kill_switch'" in app_js
    assert "ux_global_kill_switch: { queryParam: 'ux_kill_switch'" in app_js
    assert "if (flagName !== 'ux_global_kill_switch' && UX_FORCE_CLASSIC_FLAGS.has(flagName) && isGlobalUxKillSwitchEnabled()) {" in app_js
    assert "Object.defineProperty(globalThis, '__EPI_FEATURE_FLAGS__'" in app_js
    assert 'resolve: getFeatureFlagResolution' in app_js
    assert 'writable: false' in app_js
    assert 'configurable: false' in app_js


def test_error_monitor_exposes_counters_and_snapshot_api():
    monitor_js = _read('static/error-monitor.js')
    assert 'MAX_ERRORS_PER_MODULE = 50' in monitor_js
    assert 'MAX_UNSTABLE_APIS = 50' in monitor_js
    assert 'MAX_CRITICAL_BUFFER = 100' in monitor_js
    assert 'errorsByModule' in monitor_js
    assert 'unstableApis' in monitor_js
    assert 'criticalFailures' in monitor_js
    assert 'Object.defineProperty(monitoredFetch, \'__EPI_MONITORED_FETCH__\'' in monitor_js
    assert 'const response = await originalFetch.apply(this, args);' in monitor_js
    assert "Object.defineProperty(globalScope, '__EPI_MONITORING__'" in monitor_js
    assert 'getSnapshot: () => ({' in monitor_js
    assert 'autoRollbackActive' in monitor_js
    assert 'message: payload.message' not in monitor_js
    assert 'file: payload.file' not in monitor_js
