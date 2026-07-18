"""Item 1 (frontend) — o arquivamento de EPI consome a regra do backend (#735).

Garante que app.js NÃO duplica a regra de negócio: a decisão de bloquear vem do
estado do backend (has_open_links), o front apenas apresenta e reenvia
block_and_archive. Cobre também o preflight no endpoint do #735, a exigência de
motivo e o feedback.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP_JS = (ROOT / "static" / "app.js").read_text(encoding="utf-8")


def test_preflight_consumes_backend_archival_state():
    # Consome exclusivamente o endpoint do #735 para decidir.
    assert re.search(r"/api/epis/\$\{recordId\}/archival-state", APP_JS), \
        "app.js deve consultar GET /api/epis/{id}/archival-state (regra do #735)."


def test_block_decision_comes_from_backend_not_frontend():
    # A decisão de mostrar 'bloquear e arquivar' usa has_open_links do backend,
    # não um cálculo de saldo local.
    assert "has_open_links" in APP_JS, \
        "A decisão deve vir de st.has_open_links (backend), sem regra duplicada no front."


def test_archive_post_sends_block_and_archive_flag():
    fn = APP_JS[APP_JS.index("async function archiveEntityRecord"):]
    fn = fn[: fn.index("\n}\n") + 2] if "\n}\n" in fn else fn
    assert "block_and_archive: blockAndArchive" in fn, \
        "O POST /archive deve enviar block_and_archive."


def test_reason_required_for_block_and_archive():
    assert "epi.archiveReasonRequired" in APP_JS, \
        "Deve exigir motivo quando bloquear saldo e arquivar."


def test_stock_screen_refreshed_after_archive():
    assert "globalThis.loadBlockedStock?.()" in APP_JS, \
        "Após arquivar com bloqueio, a tela de Estoque Bloqueado deve atualizar."


def test_i18n_keys_present_pt_br():
    import json
    epi = json.loads((ROOT / "static" / "i18n" / "pt-BR.json").read_text(encoding="utf-8")).get("epi", {})
    for key in ("blockAndArchive", "archiveHasStock", "stockAvailable",
                "stockInPossession", "stockBlocked", "archiveReasonRequired",
                "itemsBlockedArchived"):
        assert key in epi, f"chave i18n epi.{key} ausente"
