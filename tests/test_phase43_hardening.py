import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding='utf-8')


def test_phase43_uses_guard_and_fail_safe_init_gate():
    content = _read('static/ux-phase43.js')
    assert '__EPI_PHASE43_BOUND__' in content
    assert 'if (!isEnabled()) return;' in content
    assert "fluxo clássico mantido" in content


def test_phase43_requires_visible_summary_and_valid_context_before_submit():
    content = _read('static/ux-phase43.js')
    assert 'data-phase43-summary-visible="1"' in content
    assert 'if (!runtime.quickOpen || !summaryVisible || !check.valid)' in content
    assert "Dados incompletos:" in content
    assert "id=\"phase43-confirm\" " in content
    assert "disabled" in content


def test_phase43_shortcuts_are_guarded_against_editable_contexts():
    content = _read('static/ux-phase43.js')
    assert 'function isEditableContext' in content
    assert 'function isDropdownOpen' in content
    assert 'if (isEditableContext(event.target) || isDropdownOpen()) return;' in content
    assert "if (key === 'enter' && event.ctrlKey)" in content
    assert 'if (!runtime.quickOpen) return;' in content


def test_phase43_suggestion_is_optional_and_manual_mode_supported():
    content = _read('static/ux-phase43.js')
    assert 'runtime.manualMode = true' in content
    assert 'phase43-manual-flow' in content
    assert 'phase43-clear-suggestion' in content
    assert 'if (!suggestion || runtime.manualMode) return false;' in content
    assert 'runtime.userEdited.has' in content


def test_phase43_nao_persiste_mais_estado_de_navegacao():
    """Revisado na #343 F5-B — antes exigia o oposto.

    O phase43 guardava `epi:ux:phase43:state:v1` e ainda lia a memória do
    phase42, herdando a mesma travessia de identidade. As duas saíram: o estado
    do fluxo vive em RAM e é descartado ao trocar de módulo.

    O limite de bytes e o `?ux_phase43_reset=1` deixaram de existir junto —
    ambos só faziam sentido com storage.
    """
    content = _read('static/ux-phase43.js')
    corpo = "\n".join(
        linha for linha in content.split("\n")
        if not linha.strip().startswith("//")
    )
    for proibido in ("epi:ux:phase43:state:v1", "epi:ux:phase42:memory:v2"):
        assert proibido not in corpo, f"{proibido} voltou ao phase43: ver #343 F5-B"
    assert 'function descartarEstado(' in corpo, (
        'o descarte do estado ao trocar de módulo sumiu'
    )


def test_phase43_avoids_duplicate_global_listener_binding():
    content = _read('static/ux-phase43.js')
    assert 'listenersBound: false' in content
    assert 'if (runtime.listenersBound) return;' in content
    assert 'formBound: new WeakSet()' in content
    assert 'runtime.formBound.has(form)' in content


def test_phase43_flag_registration_and_script_bootstrap_remain_available():
    app_js = _read('static/app.js')
    assert "uxPhase43Enabled: 'ux_phase43_enabled'" in app_js
    assert "ux_phase43_enabled: { queryParam: 'ux_phase43'" in app_js
    assert re.search(r"phase43Script\.src = '/ux-phase43\.js\?v=[^']+'", app_js)
