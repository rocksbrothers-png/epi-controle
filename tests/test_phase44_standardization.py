from pathlib import Path


def _read(path: str) -> str:
    return Path(path).read_text(encoding='utf-8')


def test_phase44_guard_flag_and_classic_fallback_are_present():
    content = _read('static/ux-phase44.js')
    assert '__EPI_PHASE44_BOUND__' in content
    assert "getFeatureFlag('ux_phase44_enabled'" in content
    assert 'if (!isEnabled()) {' in content
    assert 'fluxo clássico mantido' in content


def test_phase44_reusable_helpers_and_hardening_contract_present():
    content = _read('static/ux-phase44.js')
    assert 'function createDropdown(root)' in content
    assert 'function createActionBar(options)' in content
    assert 'function createConfirmInline(button, options)' in content
    assert 'function createBadge(label, tone)' in content
    assert 'safeOn(target, eventName, handler, options)' in content
    assert 'try {' in content and 'catch (error)' in content
    assert '__EPI_PHASE44_FETCH_BRIDGED__' in content


def test_phase44_script_and_flag_registration_available_in_app_bootstrap():
    app_js = _read('static/app.js')
    assert "uxPhase44Enabled: 'ux_phase44_enabled'" in app_js
    assert "ux_phase44_enabled: { queryParam: 'ux_phase44'" in app_js
    assert "phase44Script.src = '/ux-phase44.js?v=20260424-47'" in app_js


def test_phase44_critical_actions_support_explicit_attributes_with_text_fallback():
    content = _read('static/ux-phase44.js')
    assert "button.dataset.confirmAction === 'true'" in content
    assert "button.dataset.criticalAction === 'true'" in content
    assert "button.dataset.confirmMessage" in content
    assert "var fallbackTextMatch = /excluir|remover|inativar|desativar/.test(text);" in content


def test_phase44_feedback_avoids_timeout_success_and_uses_real_signals():
    content = _read('static/ux-phase44.js')
    assert "setScreenStatus(viewName, 'Ação enviada', 'loading');" in content
    assert 'htmx:afterRequest' in content and 'Sucesso confirmado.' in content
    assert "document.dispatchEvent(new CustomEvent(response && response.ok ? 'epi:action-success' : 'epi:action-error'" in content
    assert 'Ação concluída com sucesso.' not in content


def test_phase44_filter_restore_reset_and_sensitive_data_protection_present():
    content = _read('static/ux-phase44.js')
    assert "STORAGE_NAMESPACE = 'epi.ux.phase44'" in content
    assert "STORAGE_FILTER_PREFIX = STORAGE_NAMESPACE + '.filters.'" in content
    assert "params.get('ux_phase44_reset') === '1'" in content
    assert 'removePhase44Storage' in content
    assert 'restoreContext()' in content
    assert 'SENSITIVE_FIELD_PATTERN' in content
    assert 'safeLocalStorageSet' in content
