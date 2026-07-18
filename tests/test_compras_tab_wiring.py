"""Regressão (item 6 da auditoria): toda aba VISÍVEL de Compras precisa ter
binding de clique em purchases.js.

Bug real: o botão "Cotações" (compras-tab-cotacoes) existia no markup e o
handler switchComprasTab('cotacoes') + loadCotacoes estavam implementados,
mas faltava o bindAppListener do botão — clicar não fazia nada (sem erro no
console nem chamada de rede). Não era módulo incompleto; era o listener
ausente.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PURCHASES_JS = ROOT / "static" / "js" / "views" / "purchases.js"
COMPRAS_VIEW = ROOT / "static" / "views" / "compras.html"


def _visible_compras_tabs():
    """IDs data-compras-tab de botões que NÃO estão display:none no markup."""
    html = COMPRAS_VIEW.read_text(encoding="utf-8")
    tabs = []
    for m in re.finditer(r'<button[^>]*data-compras-tab="([^"]+)"[^>]*>', html):
        tag = m.group(0)
        tab = m.group(1)
        if "display:none" in tag.replace(" ", ""):
            continue
        tabs.append(tab)
    return tabs


def test_every_visible_compras_tab_is_wired():
    src = PURCHASES_JS.read_text(encoding="utf-8")
    missing = []
    for tab in _visible_compras_tabs():
        # binding esperado: bindAppListener(...compras-tab-<tab>..., 'click', ...)
        pattern = re.compile(
            r"bindAppListener\([^\n]*compras-tab-" + re.escape(tab) + r"[^\n]*'click'"
        )
        if not pattern.search(src):
            missing.append(tab)
    assert not missing, (
        f"Abas de Compras visíveis sem binding de clique em purchases.js: {missing}. "
        "Cada botão data-compras-tab precisa de bindAppListener(..., 'click', () => switchComprasTab(...))."
    )


def test_cotacoes_tab_specifically_wired_and_handled():
    src = PURCHASES_JS.read_text(encoding="utf-8")
    # o binding do botão existe
    assert re.search(r"compras-tab-cotacoes'\)[^\n]*'click'", src), \
        "Botão Cotações precisa de bindAppListener de clique."
    # switchComprasTab trata 'cotacoes' chamando loadCotacoes
    assert re.search(r"tab === 'cotacoes'[^\n]*loadCotacoes", src), \
        "switchComprasTab deve carregar loadCotacoes na aba cotacoes."
