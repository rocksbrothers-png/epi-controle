import re
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _index_html() -> str:
    return (_repo_root() / "static" / "index.html").read_text(encoding="utf-8")


def _local_script_sources(index_html: str) -> list[str]:
    script_src_matches = re.findall(r'<script[^>]+src="([^"]+)"', index_html)
    local_sources = []
    for src in script_src_matches:
        if not (src.startswith("/") and not src.startswith("//")):
            continue
        local_sources.append(src)
    return local_sources


def test_index_has_single_reference_for_core_scripts():
    index_html = _index_html()
    local_sources = _local_script_sources(index_html)
    local_sources_without_query = [src.split("?", 1)[0] for src in local_sources]

    required = ["/app.js", "/share-modal.js", "/colab-list.js"]
    for script in required:
        assert (
            local_sources_without_query.count(script) == 1
        ), f"index.html deve conter exatamente uma referência ativa para {script}."


def test_index_has_no_duplicate_local_js_references():
    index_html = _index_html()
    local_sources = _local_script_sources(index_html)
    local_sources_without_query = [src.split("?", 1)[0] for src in local_sources if src.endswith(".js") or ".js?" in src]
    duplicates = sorted({
        source for source in local_sources_without_query
        if local_sources_without_query.count(source) > 1
    })
    assert not duplicates, f"Scripts locais duplicados no index.html: {duplicates}"


def test_index_rejects_known_old_cache_bust_versions():
    index_html = _index_html()
    old_versions = [
        "20260424-08",
        "20260424-09",
        "20260424-10",
        "20260424-11",
        "20260424-12",
        "20260424-13",
        "20260424-14",
    ]
    for version in old_versions:
        assert f"v={version}" not in index_html, f"Cache-bust antigo ativo detectado: {version}"


def test_index_loads_single_main_app_script_without_legacy_bundle():
    root = _repo_root()
    index_html = (root / "static" / "index.html").read_text(encoding="utf-8")
    script_src_matches = re.findall(r'<script[^>]+src="([^"]+)"', index_html)
    local_sources = [src.split("?", 1)[0] for src in script_src_matches if src.startswith("/")]

    app_js_sources = [src for src in local_sources if src == "/app.js"]
    assert len(app_js_sources) == 1, "index.html deve carregar exatamente um /app.js."

    legacy_sources = [src for src in local_sources if src.startswith("/app.v") and src.endswith(".js")]
    assert not legacy_sources, "index.html não deve carregar bundles legados app.v*.js."


def test_purchase_request_review_ui_uses_single_workflow_modal_and_no_prompt_confirm():
    source = (_repo_root() / "static" / "app.js").read_text(encoding="utf-8")
    workflow_section = source[source.index("function renderPrStatusActions"):source.index("async function openPoDetail")]

    assert workflow_section.count("Solicitar revisão da cotação") == 1
    assert workflow_section.count("Solicitar revisão da requisição") == 1
    assert workflow_section.count("Retornar ao Requisitante") == 2
    assert "openPurchaseWorkflowModal" in workflow_section
    assert "prompt(" not in workflow_section
    assert "confirm(" not in workflow_section


def test_purchase_request_history_container_exists():
    index_html = _index_html()
    assert 'id="compras-req-events"' in index_html
    assert 'Aguardando Correção do Comprador' in index_html
    assert 'Aguardando Correção do Requisitante' in index_html
