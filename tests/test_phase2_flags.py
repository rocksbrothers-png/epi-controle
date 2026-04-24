import re
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _read(relative_path: str) -> str:
    return (_repo_root() / relative_path).read_text(encoding="utf-8")


def test_forbidden_appversion_token_not_present():
    root = _repo_root()
    for path in sorted((root / "static").glob("*")):
        if path.suffix not in {".js", ".html"}:
            continue
        content = path.read_text(encoding="utf-8")
        assert "appVersion" not in content, f"Token proibido encontrado em {path.name}: appVersion"


def test_no_dangerous_global_appversion_redeclarations():
    root = _repo_root()
    forbidden_patterns = [
        r"\bvar\s+appVersion\b",
        r"\blet\s+appVersion\b",
        r"\bconst\s+appVersion\b",
        r"window\.appVersion\s*=",
        r"globalThis\.appVersion\s*=",
    ]
    combined = re.compile("|".join(forbidden_patterns))
    for path in sorted((root / "static").glob("*.js")):
        content = path.read_text(encoding="utf-8")
        assert not combined.search(content), f"Redeclaração global perigosa detectada em {path.name}"


def test_share_modal_uses_safeon_for_event_binding():
    share_modal = _read("static/share-modal.js")
    assert "safeOn" in share_modal, "share-modal.js deve usar safeOn."
    add_listener_calls = re.findall(r"\.addEventListener\s*\(", share_modal)
    assert len(add_listener_calls) == 1, (
        "share-modal.js deve evitar addEventListener direto fora do helper safeOn."
    )


def test_phase2_flag_definitions_have_querystring_documented():
    app_js = _read("static/app.js")
    required_flags = {
        "colaborador_htmx_enabled": "ux_phase2_colaboradores",
        "colaborador_list_htmx_enabled": "ux_phase2_colab_list",
        "gestao_colaborador_htmx_enabled": "ux_phase2_gestao_colab",
        "epi_htmx_enabled": "ux_phase2_epis",
    }
    for flag_name, query_param in required_flags.items():
        assert flag_name in app_js, f"Flag ausente: {flag_name}"
        snippet = f"{flag_name}: {{ queryParam: '{query_param}'"
        assert snippet in app_js, f"Flag {flag_name} sem querystring documentada ({query_param})."


def test_phase2_flag_resolvers_use_getfeatureflag_with_default_off():
    app_js = _read("static/app.js")
    expected_calls = [
        "getFeatureFlag('colaborador_htmx_enabled', { defaultValue: false, allowStorage: false })",
        "getFeatureFlag('colaborador_list_htmx_enabled', { defaultValue: false, allowStorage: false })",
        "getFeatureFlag('gestao_colaborador_htmx_enabled', { defaultValue: false, allowStorage: false })",
        "getFeatureFlag('epi_htmx_enabled', { defaultValue: false, allowStorage: false })",
    ]
    for call in expected_calls:
        assert call in app_js, f"Resolver de flag não padronizado: {call}"


def test_phase2_modules_are_scoped_to_their_view_selector():
    app_js = _read("static/app.js")
    expected_modules = {
        "colaboradores": "#colaboradores-view",
        "colaborador-lista": "#colaborador-list-view",
        "gestao-colaborador": "#gestao-colaborador-view",
        "epis": "#epis-view",
    }
    for module_name, view_selector in expected_modules.items():
        assert f"moduleName: '{module_name}'" in app_js, f"Módulo phase2 ausente: {module_name}"
        assert f"viewSelector: '{view_selector}'" in app_js, (
            f"Módulo {module_name} sem viewSelector correto ({view_selector})."
        )

    assert "element.closest(definition.viewSelector)" in app_js, (
        "Os triggers phase2 devem validar escopo da view para evitar ativação fora da tela correta."
    )


def test_phase2_isolated_modules_follow_minimum_hardening_pattern():
    module_files = [
        "static/colab-list.js",
        "static/gestao-colab.js",
    ]
    for module_file in module_files:
        content = _read(module_file)
        assert "(function () {" in content, f"{module_file} sem IIFE."
        assert re.search(r"__EPI_[A-Z0-9_]+_BOUND__", content), f"{module_file} sem guard global."
        assert "safeOn" in content, f"{module_file} sem safeOn."
        assert "try {" in content and "} catch" in content, f"{module_file} sem try/catch fail-safe."
        assert "if (!root) return;" in content, f"{module_file} sem retorno seguro fora da view."
