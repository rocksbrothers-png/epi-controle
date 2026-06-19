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
        "20260527-01",
        "20260527-02",
        "20260527-03",
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
    assert "addAction({ action: 'generate_po', label: 'Gerar PO'" in workflow_section
    assert "actionKeys" in workflow_section
    # generate_po is handled directly in executePurchaseWorkflowAction (not legacy)
    handler_section = source[source.index("async function executePurchaseWorkflowAction"):]
    assert "actionConfig.action === 'generate_po'" in handler_section
    assert "status: 'po_generated'" in handler_section


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
    assert "reportNonCriticalError('[renderReports]" in render_reports_section
    assert "if (hasPermission('reports:view')) void renderReports();" in render_all_section


def test_approver_workflow_buttons_use_item_selection_for_both_review_paths():
    source = (_repo_root() / "static" / "app.js").read_text(encoding="utf-8")
    workflow_section = source[source.index("async function executePurchaseWorkflowAction"):source.index("async function updatePrStatus")]

    assert "['return_to_buyer', 'return_to_requester'].includes(actionConfig.action)" in workflow_section
    assert "showApprovalItems: actionConfig.action === 'approve'" in workflow_section


def _build_index_module():
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "build_index", _repo_root() / "scripts" / "build_index.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_asset_cache_buster_is_build_derived_and_consistent():
    """Fase 0 UBX: o cache-buster `?v=` é derivado do conteúdo no build
    (build_index.py), não mais hardcoded. Garante que:
      - nenhum placeholder `__ASSET_VERSION__` vazou para o index.html servido;
      - todas as referências `?v=` usam a MESMA versão;
      - essa versão é exatamente o hash de conteúdo atual (sem desync);
      - versões antigas e datadas não persistem.
    """
    index_html = _index_html()
    build_index = _build_index_module()

    assert "__ASSET_VERSION__" not in index_html, "placeholder não resolvido no index.html"

    versions = set(re.findall(r"\?v=([A-Za-z0-9-]+)", index_html))
    assert versions, "index.html deveria ter assets versionados"
    assert len(versions) == 1, f"todas as referências ?v= devem usar a mesma versão; achei {versions}"

    expected = build_index._compute_asset_version()
    assert versions == {expected}, (
        f"index.html está dessincronizado: ?v={versions} mas o conteúdo gera {expected}. "
        "Rode: python scripts/build_index.py build"
    )

    # Versões datadas antigas não devem mais aparecer (eram cache-buster manual).
    for legacy in ("20260603-01", "20260528-02", "20260527-01", "20260509-01"):
        assert f"?v={legacy}" not in index_html


def test_external_scripts_are_pinned_and_sri_protected():
    index_html = _index_html()
    script_tags = re.findall(r'<script\b[^>]*\bsrc="([^"]+)"[^>]*>', index_html, flags=re.IGNORECASE)
    external_sources = [src for src in script_tags if src.startswith(("http://", "https://"))]

    assert external_sources == ["https://unpkg.com/htmx.org@1.9.12"]
    htmx_tag_match = re.search(
        r'<script\b[^>]*\bsrc="https://unpkg\.com/htmx\.org@1\.9\.12"[^>]*>',
        index_html,
        flags=re.IGNORECASE,
    )
    assert htmx_tag_match is not None
    htmx_tag = htmx_tag_match.group(0)
    assert 'integrity="sha384-ujb1lZYygJmzgSwoxRggbCHcjc0rB2XoQrxeTUQyRjrOnlCoYta87iKBWq3EsdM2"' in htmx_tag
    assert 'crossorigin="anonymous"' in htmx_tag
    assert "alpinejs@3.14.9" not in index_html


def test_static_asset_diagnostics_reads_repo_static_directory():
    from modules.auth.service import static_asset_diagnostics

    diagnostics = static_asset_diagnostics()

    index_path = _repo_root() / "static" / "index.html"
    app_path = _repo_root() / "static" / "app.js"
    assert diagnostics["index_html_bytes"] == index_path.stat().st_size
    assert diagnostics["index_html_sha256"]
    assert diagnostics["app_js_bytes"] == app_path.stat().st_size
    assert diagnostics["app_js_sha256"]
    assert "app_web_index_present" in diagnostics
    assert diagnostics["flutter_web_legacy_redirect_target"] == "/app/"


class _HeaderCapture:
    path = "/"
    headers = {}

    def __init__(self):
        self.sent_headers = []

    def send_header(self, name, value):
        self.sent_headers.append((name, value))


def test_app_static_fallback_resolver_preserves_files_and_deep_links(tmp_path, monkeypatch):
    import app

    flutter_dir = tmp_path / "app"
    flutter_dir.mkdir()
    (flutter_dir / "index.html").write_text("<html></html>", encoding="utf-8")
    (flutter_dir / "main.dart.js").write_text("console.log('flutter');", encoding="utf-8")
    monkeypatch.setattr(app, "BASE_DIR", tmp_path)

    handler = object.__new__(app.EpiHandler)

    assert app.EpiHandler._resolve_static_fallback_path(handler, "/") == "/index.html"
    assert app.EpiHandler._resolve_static_fallback_path(handler, "/app") == "/app/index.html"
    assert app.EpiHandler._resolve_static_fallback_path(handler, "/app/") == "/app/index.html"
    assert app.EpiHandler._resolve_static_fallback_path(handler, "/app/dashboard") == "/app/index.html"
    assert app.EpiHandler._resolve_static_fallback_path(handler, "/app/main.dart.js") == ""


def test_legacy_flutter_web_paths_redirect_to_official_app_url():
    import app

    handler = object.__new__(app.EpiHandler)

    assert app.EpiHandler._legacy_flutter_web_redirect(handler, app.urlparse("/flutter_web")) == "/app/"
    assert app.EpiHandler._legacy_flutter_web_redirect(handler, app.urlparse("/flutter_web/")) == "/app/"
    assert app.EpiHandler._legacy_flutter_web_redirect(
        handler,
        app.urlparse("/flutter_web/dashboard?tab=epis"),
    ) == "/app/dashboard?tab=epis"
    assert app.EpiHandler._legacy_flutter_web_redirect(handler, app.urlparse("/app/dashboard")) == ""


def test_flutter_web_build_targets_official_app_directory():
    root = _repo_root()
    melos = (root / "flutter" / "melos.yaml").read_text(encoding="utf-8")
    dockerfile = (root / "Dockerfile").read_text(encoding="utf-8")

    assert "--base-href /app/" in melos
    assert "./static/app/" in dockerfile
    assert "./static/flutter_web/" not in dockerfile


def test_default_headers_emit_single_csp_report_only_header(monkeypatch):
    import app

    monkeypatch.setenv("CSP_REPORT_URI", "/api/csp-report")
    handler = _HeaderCapture()

    app.EpiHandler._apply_default_response_headers(handler)

    csp_headers = [value for name, value in handler.sent_headers if name == "Content-Security-Policy-Report-Only"]
    assert len(csp_headers) == 1
    assert "script-src 'self' 'unsafe-inline' https://unpkg.com" in csp_headers[0]
    assert "report-uri /api/csp-report" in csp_headers[0]


def _app_js() -> str:
    return (_repo_root() / "static" / "app.js").read_text(encoding="utf-8")


def test_async_functions_consumed_by_view_modules_are_exposed_on_globalthis():
    """Regressão: o guard `if (!globalThis.__EPI_APP_RUNTIME_LOADED__) { ... }` torna
    as `async function` de app.js block-scoped (sem hoisting global). Os módulos de
    view chamam essas funções via globalThis.<fn>(); elas precisam ser expostas
    explicitamente, senão os loaders da aba Compras viram no-op silencioso e
    `globalThis.api?.()` retorna undefined (quebra em devolution.js `payload.items`).
    """
    app_js = _app_js()

    # São async functions (não ganham Annex B hoisting) e são consumidas por
    # static/js/views/*.js via globalThis.<fn>(). Devem estar expostas.
    required_global_async = [
        "api",
        "apiOptional",
        "loadBootstrap",
        "loadAuthorizedSuppliers",
        "loadPurchaseDemands",
        "loadPurchaseRequests",
        "loadPurchaseOrders",
        "loadAprovacoesSolicitacoes",
        "loadFornecedoresPurchaseFunctions",
    ]
    for name in required_global_async:
        assert re.search(rf"^async function {name}\(", app_js, flags=re.MULTILINE), (
            f"{name} deveria ser uma async function de app.js"
        )
        # Exposta em globalThis (via Object.assign(globalThis, {{ ... name ... }})
        # ou globalThis.name = name).
        exposed = (
            re.search(rf"\bglobalThis\.{name}\s*=", app_js) is not None
            or re.search(rf"Object\.assign\(\s*globalThis\s*,\s*\{{[^}}]*\b{name}\b", app_js, flags=re.DOTALL) is not None
        )
        assert exposed, f"{name} (async) não está exposta em globalThis — módulos de view a chamam via globalThis.{name}()"


def test_http_layer_delegates_to_canonical_api_client():
    """Fase 1 UBX: app.js não deve duplicar a lógica HTTP; api/apiOptional/
    apiWithBootstrapRetry delegam ao módulo canônico static/js/modules/api-client.js
    (apiFetch/apiFetchOptional/apiFetchWithRetry), fonte única de verdade."""
    app_js = _app_js()

    # app.js delega aos canônicos expostos por api-client.js
    assert "return globalThis.apiFetch(path, options);" in app_js
    assert "return globalThis.apiFetchOptional(path, options);" in app_js
    assert "return globalThis.apiFetchWithRetry(path, options, config);" in app_js

    # Não reintroduzir a lógica duplicada em app.js (deve viver só no módulo).
    assert "const { contentType, payload } = await parseApiPayload(response);" not in app_js

    # O módulo canônico continua definindo as funções de verdade.
    api_client = (_repo_root() / "static" / "js" / "modules" / "api-client.js").read_text(encoding="utf-8")
    for fn in ("apiFetch", "apiFetchOptional", "apiFetchWithRetry"):
        assert re.search(rf"\basync function {fn}\(", api_client), f"{fn} deve existir em api-client.js"
