"""Regressão: os módulos de view devem ler o estado do app pelo global canônico
`globalThis.__EPI_APP_STATE__` (definido em app.js), não por `globalThis.state`
(inexistente).

Bug real: procurement.js (aba Cotações) fazia `getState()` retornar
`globalThis.state || {}` — como esse global não existe, `getState().user?.id`
era undefined e a chamada virava `/api/purchase-requests?actor_user_id=undefined`
→ 400. O módulo irmão purchases.js já usava `__EPI_APP_STATE__`. O sintoma só
apareceu quando a aba Cotações passou a abrir (fix do binding).
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP_JS = ROOT / "static" / "app.js"
VIEWS_DIR = ROOT / "static" / "js" / "views"


def test_app_exposes_canonical_state_global():
    src = APP_JS.read_text(encoding="utf-8")
    assert "globalThis.__EPI_APP_STATE__ = state" in src, \
        "app.js deve expor o estado como globalThis.__EPI_APP_STATE__."


def test_view_modules_do_not_read_bare_globalthis_state():
    """Nenhum getState de módulo pode retornar apenas globalThis.state (undefined)."""
    offenders = []
    for path in VIEWS_DIR.glob("*.js"):
        src = path.read_text(encoding="utf-8")
        # padrão do bug: retorno de globalThis.state SEM o canônico como fonte
        if re.search(r"return\s+globalThis\.state\s*\|\|", src) and "__EPI_APP_STATE__" not in src:
            offenders.append(path.name)
    assert not offenders, (
        f"Módulos lendo globalThis.state (inexistente) sem __EPI_APP_STATE__: {offenders}. "
        "Use globalThis.__EPI_APP_STATE__ (vide purchases.js)."
    )


def test_procurement_uses_canonical_state():
    src = (VIEWS_DIR / "procurement.js").read_text(encoding="utf-8")
    assert "__EPI_APP_STATE__" in src, \
        "procurement.js deve ler o estado por globalThis.__EPI_APP_STATE__."
