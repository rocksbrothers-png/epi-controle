import re
from pathlib import Path


PHASE3_FLAGS = {
    "spa_navigation_enabled": "ux_spa_navigation",
    "ux_global_enabled": "ux_global",
    "dashboard_interativo_enabled": "ux_dashboard_interativo",
    "ux_performance_hardening_enabled": "ux_perf_hardening",
}


FORBIDDEN_CACHE_BUSTS = {
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


def test_phase3_rollout_matrix_is_exposed_with_default_off():
    app_js = _read("static/app.js")
    assert "const PHASE3_FLAG_MATRIX = Object.freeze([" in app_js

    for flag, query in PHASE3_FLAGS.items():
        assert f"flag: '{flag}'" in app_js, f"Flag ausente na matriz fase 3: {flag}"
        assert f"queryParam: '{query}'" in app_js, f"queryParam ausente na matriz fase 3: {query}"

    default_off_count = len(re.findall(r"defaultValue:\s*false", app_js))
    assert default_off_count >= len(PHASE3_FLAGS), "Matriz de rollout deve manter defaults OFF."

    assert "globalThis.__EPI_PHASE3_FLAG_MATRIX__ = PHASE3_FLAG_MATRIX;" in app_js


def test_phase3_flags_have_default_off_resolvers():
    app_js = _read("static/app.js")
    ux_global_js = _read("static/ux-global.js")
    joined = "\n".join([app_js, ux_global_js])

    for flag in PHASE3_FLAGS:
        assert f"getFeatureFlag('{flag}', {{ defaultValue: false" in joined, (
            f"Resolver da flag {flag} deve manter default OFF."
        )


def test_index_html_has_no_forbidden_cache_bust_or_legacy_app_bundle():
    index_html = _read("static/index.html")

    for version in FORBIDDEN_CACHE_BUSTS:
        assert f"v={version}" not in index_html, f"Cache-bust antigo ainda ativo: {version}"

    legacy_bundle_refs = re.findall(r"/app\.v\d+\.js", index_html)
    assert not legacy_bundle_refs, f"Bundle legado referenciado no index.html: {legacy_bundle_refs}"


def test_index_html_has_no_duplicate_local_js_sources():
    index_html = _read("static/index.html")
    local_scripts = re.findall(r'<script[^>]+src="(/[^"]+)"', index_html)
    local_js = [src.split("?", 1)[0] for src in local_scripts if ".js" in src]

    duplicates = sorted({src for src in local_js if local_js.count(src) > 1})
    assert not duplicates, f"Scripts locais JS duplicados: {duplicates}"


def test_share_modal_avoids_unsafe_add_event_listener():
    content = _read("static/share-modal.js")
    assert "safeOn" in content, "share-modal.js deve usar safeOn."

    add_listener_calls = re.findall(r"\.addEventListener\s*\(", content)
    assert len(add_listener_calls) == 1, (
        "share-modal.js deve restringir addEventListener ao fallback interno de safeOn."
    )


def test_static_sources_reject_forbidden_appversion_token():
    root = _repo_root()
    for path in sorted((root / "static").glob("*")):
        if path.suffix not in {".js", ".html"}:
            continue
        content = path.read_text(encoding="utf-8")
        assert "appVersion" not in content, f"Token proibido appVersion detectado em {path.name}"
