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
    assert workflow_section.count("Retornar ao Requisitante") == 3
    assert "openPurchaseWorkflowModal" in workflow_section
    assert "prompt(" not in workflow_section
    assert "confirm(" not in workflow_section


def test_purchase_request_history_container_exists():
    index_html = _index_html()
    assert 'id="compras-req-events"' in index_html
    assert 'Aguardando Correção do Comprador' in index_html
    assert 'Aguardando Correção do Requisitante' in index_html


def test_buyer_correction_status_keeps_legacy_quotation_tools_visible():
    source = (_repo_root() / "static" / "app.js").read_text(encoding="utf-8")
    setup_section = source[source.index("function _setupPrDetailActions"):source.index("function exportPrCsv")]
    workflow_section = source[source.index("function renderPrStatusActions"):source.index("async function openPoDetail")]

    assert "const PURCHASE_BUYER_QUOTE_STATUSES" in source
    assert "'waiting_buyer_correction'" in source[source.index("const PURCHASE_BUYER_QUOTE_STATUSES"):source.index("function isBuyerQuotationStatus")]
    assert "isBuyerQuotationStatus(pr.status)" in setup_section
    assert "Marcar como Cotada" in workflow_section
    assert "Reenviar ao Aprovador" in workflow_section
    assert "Retornar ao Requisitante" in workflow_section
    assert "'waiting_buyer_correction'" in workflow_section


def test_buyer_actions_are_permission_based_and_preserve_legacy_tools():
    source = (_repo_root() / "static" / "app.js").read_text(encoding="utf-8")
    workflow_section = source[source.index("function renderPrStatusActions"):source.index("async function executePurchaseWorkflowAction")]

    assert "const canQuote = isBuyer || hasPermission('purchase_orders:create') || hasPermission('purchase_orders:upload')" in workflow_section
    assert "addAction({ action: 'mark_quoted', to: 'quoted', label: 'Marcar como Cotada'" in workflow_section
    assert "addAction({ action: 'buyer_resubmit', label: 'Reenviar ao Aprovador'" in workflow_section
    assert "addAction({ action: 'buyer_return_to_requester', label: 'Retornar ao Requisitante'" in workflow_section
    assert "addAction({ action: 'send_to_approver', to: 'pending_approval', label: 'Enviar ao Aprovador'" in workflow_section
    assert "addAction({ action: 'generate_po', to: 'po_generated', label: 'Gerar PO'" in workflow_section
    assert "actionKeys" in workflow_section


def test_buyer_import_quote_tools_cover_returned_and_reopened_statuses():
    source = (_repo_root() / "static" / "app.js").read_text(encoding="utf-8")
    status_section = source[source.index("const PURCHASE_BUYER_QUOTE_STATUSES"):source.index("function isBuyerQuotationStatus")]
    setup_section = source[source.index("function _setupPrDetailActions"):source.index("function exportPrCsv")]

    for status in ["'sent_to_buyer'", "'returned_to_buyer'", "'quoted'", "'waiting_buyer_correction'", "'pending_approval'", "'postponed'"]:
        assert status in status_section
    assert "purchase_orders:create" in setup_section
    assert "purchase_orders:upload" in setup_section
    assert "req-po-csv-import-panel" in setup_section
    assert "req-import-po-btn" in setup_section


def test_optional_bootstrap_sections_are_permission_guarded_and_403_is_skipped():
    source = (_repo_root() / "static" / "app.js").read_text(encoding="utf-8")
    optional_section = source[source.index("function recordOptionalBootstrapSectionSkipped"):source.index("function buildBootstrapDegradedMessage")]
    load_bootstrap_section = source[source.index("async function loadBootstrap"):source.index("function populateSelect")]

    assert "permission && !hasPermission(permission)" in optional_section
    assert "optional_section_skipped" in optional_section
    assert "Number(error?.status || 0) === 403" in optional_section
    assert "{ permission: 'fichas:view' }" in load_bootstrap_section
    assert "{ permission: 'reports:view' }" not in load_bootstrap_section
    assert "api(`/api/fichas?${actorQuery()}`)" in load_bootstrap_section
    assert "{ permission: 'fichas:view' }" in load_bootstrap_section


def test_reports_are_not_loaded_or_alerted_when_permission_is_missing_or_forbidden():
    source = (_repo_root() / "static" / "app.js").read_text(encoding="utf-8")
    render_reports_section = source[source.index("async function renderReports"):source.index("async function loadArchiveReports")]
    render_all_section = source[source.index("function renderAll"):source.index("function init")]

    assert "recordOptionalBootstrapSectionSkipped('reports', 'missing_permission'" in render_reports_section
    assert "recordOptionalBootstrapSectionSkipped('reports', 'forbidden'" in render_reports_section
    assert "throw error" in render_reports_section
    assert "if (hasPermission('reports:view')) void renderReports();" in render_all_section


def test_approver_workflow_buttons_use_item_selection_for_both_review_paths():
    source = (_repo_root() / "static" / "app.js").read_text(encoding="utf-8")
    workflow_section = source[source.index("async function executePurchaseWorkflowAction"):source.index("async function updatePrStatus")]

    assert "['return_to_buyer', 'return_to_requester'].includes(actionConfig.action)" in workflow_section
    assert "showApprovalItems: actionConfig.action === 'approve'" in workflow_section


def test_index_app_cache_buster_was_updated_for_permission_fix():
    index_html = _index_html()
    assert "/app.js?v=20260527-01" in index_html
    assert "/app.js?v=20260509-02" not in index_html
    assert "/app.js?v=20260509-01" not in index_html
    assert "/app.js?v=20260508-03" not in index_html
