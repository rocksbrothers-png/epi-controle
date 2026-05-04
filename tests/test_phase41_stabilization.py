from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (_repo_root() / path).read_text(encoding="utf-8")


def test_phase41_has_global_guard_and_iife():
    content = _read("static/ux-phase41.js")
    assert "(function phase41Iife()" in content
    assert "__EPI_PHASE41_BOUND__" in content


def test_phase41_uses_namespaced_storage_and_reset_query():
    content = _read("static/ux-phase41.js")
    assert "epi:ux:phase41:context:v2" in content
    assert "epi:ux:phase41:scroll:v2" in content
    assert "ux_phase41_reset" in content


def test_phase41_blocks_sensitive_field_persistence():
    content = _read("static/ux-phase41.js")
    assert "SENSITIVE_FIELD_PATTERN" in content
    assert "shouldPersistField" in content
    for token in ["password", "token", "cpf", "signature", "qr", "secret"]:
        assert token in content


def test_phase41_has_safe_enter_guards_for_critical_forms():
    content = _read("static/ux-phase41.js")
    assert "CRITICAL_FORMS" in content
    assert "delivery-form" in content
    assert "resolveSafePrimaryAction" in content
    assert "hasAutocompleteContext" in content


def test_phase41_has_loading_failsafe_and_overlay_close_controls():
    content = _read("static/ux-phase41.js")
    assert "startPendingFailsafe" in content
    assert "setTimeout(function ()" in content
    assert "closeUiOverlays({ includeModal: true })" in content
    assert "closeUiOverlays({ includeModal: false })" in content
