"""Item 2 (frontend) — o Dashboard consome a fonte ÚNICA de conformidade (#737).

Garante que os cards de validade/bloqueio do Dashboard leem as contagens do
backend (GET /api/stock/compliance) — a MESMA base da tela "Validade e
Bloqueios" (epi_stock_items) — em vez de recalcular sobre o catálogo
(state.epis). Assim o total do card = total da listagem operacional, que era o
defeito relatado (Dashboard contava catálogo, tela contava estoque).
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DASH = (ROOT / "static" / "js" / "views" / "dashboard.js").read_text(encoding="utf-8")


def test_dashboard_calls_compliance_endpoint():
    assert "/api/stock/compliance" in DASH, \
        "dashboard.js deve consumir GET /api/stock/compliance (fonte única #737)."


def test_dashboard_reads_counts_from_summary_not_catalog():
    # As contagens vêm de _compliance.summary, não de um filtro sobre state.epis.
    for key in ("product_expired", "product_expiring", "ca_expired", "ca_expiring"):
        assert re.search(rf"cVal\(\s*'{key}'\s*\)", DASH), \
            f"card '{key}' deve vir da fonte única (cVal), não do catálogo."


def test_dashboard_does_not_recompute_validity_over_catalog():
    # Não pode restar cálculo de validade sobre o catálogo no Dashboard.
    assert "_daysUntil(e.ca_expiry)" not in DASH, \
        "Dashboard não deve recalcular CA sobre o catálogo (state.epis)."
    assert "_daysUntil(e.epi_validity_date)" not in DASH, \
        "Dashboard não deve recalcular validade física sobre o catálogo."


def test_dashboard_handles_loading_and_error_states():
    assert "dashboard.loadingShort" in DASH, "faltou placeholder de carregamento (…)."
    assert "dashboard.complianceError" in DASH, "faltou tratamento de erro (—)."
    assert "comp === null" in DASH and "loadStockCompliance" in DASH, \
        "deve disparar o carregamento da fonte única quando ainda não há dados."


def test_dashboard_exposes_admin_blocked_and_gaps():
    for key in ("admin_blocked", "missing_manufacture", "missing_lot"):
        assert re.search(rf"cVal\(\s*'{key}'\s*\)", DASH), \
            f"card '{key}' ausente (categoria separada exigida pelo item 2)."


def test_i18n_keys_present_all_locales():
    import json
    for loc in ("pt-BR", "en-GB", "es-ES", "fr-FR", "nb-NO"):
        dash = json.loads((ROOT / "static" / "i18n" / f"{loc}.json").read_text(encoding="utf-8")).get("dashboard", {})
        for key in ("adminBlocked", "missingManufacture", "missingLot",
                    "complianceError", "loadingShort"):
            assert key in dash, f"{loc}: chave i18n dashboard.{key} ausente"
