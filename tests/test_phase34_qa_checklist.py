import re
import subprocess
from pathlib import Path


PHASE3_FLAGS = {
    "dashboard_interativo_enabled": "ux_dashboard_interativo",
    "spa_navigation_enabled": "ux_spa_navigation",
    "ux_global_enabled": "ux_global",
    "ux_performance_hardening_enabled": "ux_perf_hardening",
}


FORBIDDEN_OLD_VERSIONS = {
    "20260424-08",
    "20260424-09",
    "20260424-10",
    "20260424-11",
    "20260424-12",
    "20260424-13",
    "20260424-14",
    "20260424-32",
    "20260424-33",
}


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _read(relative_path: str) -> str:
    return (_repo_root() / relative_path).read_text(encoding="utf-8")


def test_all_static_js_files_have_valid_syntax_with_node_check():
    root = _repo_root()
    js_files = sorted((root / "static").glob("*.js"))
    assert js_files, "Nenhum arquivo JS encontrado em static/."

    for js_file in js_files:
        result = subprocess.run(
            ["node", "--check", str(js_file)],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, (
            f"Falha de sintaxe em {js_file.name}. stdout={result.stdout!r} stderr={result.stderr!r}"
        )


def test_phase3_flags_have_querystring_and_default_off_resolvers():
    app_js = _read("static/app.js")
    ux_global_js = _read("static/ux-global.js")

    for flag_name, query_param in PHASE3_FLAGS.items():
        assert f"{flag_name}: {{ queryParam: '{query_param}'" in app_js, (
            f"Flag {flag_name} sem queryParam esperado ({query_param})."
        )

    resolver_sources = [app_js, ux_global_js]
    for flag_name in PHASE3_FLAGS:
        expected = f"getFeatureFlag('{flag_name}', {{ defaultValue: false"
        assert any(expected in source for source in resolver_sources), (
            f"Flag {flag_name} deve ter resolver com default OFF."
        )


def test_index_html_has_no_old_cache_bust_versions():
    index_html = _read("static/index.html")
    for version in sorted(FORBIDDEN_OLD_VERSIONS):
        assert f"v={version}" not in index_html, f"Versão antiga ainda ativa no index.html: {version}"


def test_index_html_has_no_duplicate_local_script_sources():
    index_html = _read("static/index.html")
    local_scripts = re.findall(r'<script[^>]+src="(/[^\"]+)"', index_html)
    js_sources = [src.split("?", 1)[0] for src in local_scripts if ".js" in src]

    duplicates = sorted({source for source in js_sources if js_sources.count(source) > 1})
    assert not duplicates, f"Scripts JS locais duplicados no index.html: {duplicates}"


def test_share_modal_uses_safeon_and_no_unsafe_binding():
    content = _read("static/share-modal.js")
    assert "safeOn" in content, "share-modal.js deve utilizar safeOn."

    direct_add_listener_calls = re.findall(r"\.addEventListener\s*\(", content)
    assert len(direct_add_listener_calls) == 1, (
        "share-modal.js deve restringir addEventListener direto ao fallback interno de safeOn."
    )


def test_forbidden_appversion_token_not_present_in_static_sources():
    root = _repo_root()
    for path in sorted((root / "static").glob("*")):
        if path.suffix not in {".js", ".html"}:
            continue
        content = path.read_text(encoding="utf-8")
        assert "appVersion" not in content, f"Token proibido encontrado em {path.name}: appVersion"
