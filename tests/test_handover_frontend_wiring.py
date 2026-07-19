"""Item 4 (frontend web) — a conferência de entrega consome os endpoints do
backend (lookup/confirm) sem duplicar regra de negócio.
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP_JS = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
VIEW = (ROOT / "static" / "views" / "entregas.html").read_text(encoding="utf-8")


def test_view_has_handover_card():
    for el in ("handover-code", "handover-lookup-btn", "handover-result",
               "handover-confirm-btn"):
        assert f'id="{el}"' in VIEW, f"entregas.html sem #{el}"


def test_appjs_consumes_backend_endpoints():
    assert "/api/deliveries/handover-lookup" in APP_JS
    assert "/api/deliveries/handover-confirm" in APP_JS


def test_appjs_sends_code_and_actor_on_confirm():
    fn = APP_JS[APP_JS.index("async function handoverConfirm"):]
    fn = fn[: fn.index("\n}\n") + 2]
    assert "actor_user_id" in fn and "code" in fn


def test_i18n_handover_keys_all_locales():
    for loc in ("pt-BR", "en-GB", "es-ES", "fr-FR", "nb-NO"):
        h = json.loads((ROOT / "static" / "i18n" / f"{loc}.json").read_text(encoding="utf-8")).get("handover", {})
        for key in ("title", "lookup", "confirm", "collaborator", "registration",
                    "lot", "request", "confirmedToast"):
            assert key in h, f"{loc}: chave i18n handover.{key} ausente"
