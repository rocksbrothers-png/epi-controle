#!/usr/bin/env python3
"""Montagem modular do static/index.html a partir de fragmentos de view.

O index.html é um arquivo monolítico (~2600 linhas). Para permitir manutenção
por módulo sem risco em runtime, este script separa cada seção de view em um
fragmento próprio em ``static/views/`` e reconstrói o index.html a partir de um
layout (``static/views/_layout.html``) com marcadores de inclusão.

A reconstrução é byte-idêntica ao original por construção: o layout é o texto
original com cada fatia de view substituída por um marcador, e o build apenas
re-substitui o marcador pela fatia exata.

A casca (tudo que não é view) também pode ser decomposta em sub-fragmentos
(_head, _login, _sidebar, _topbar, _modals, _scripts) via 'split-layout'.

Modos:
  extract       Separa index.html -> _layout.html + views/<id>.html (primeira vez)
  split-layout  Decompõe _layout.html em sub-fragmentos de casca (_head, ...)
  split-modals  Extrai modais embutidos em views grandes para views/modals/<id>.html
  build         Reconstrói index.html a partir do layout + fragmentos
  check         Reconstrói em memória e compara com index.html atual (exit!=0 se diferir)

Uso:
  python scripts/build_index.py extract
  python scripts/build_index.py split-layout
  python scripts/build_index.py split-modals
  python scripts/build_index.py build
  python scripts/build_index.py check

Fluxo de re-extração completa (raro): extract, split-layout, split-modals.
"""

import hashlib
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_DIR = os.path.join(ROOT, "static")
INDEX_PATH = os.path.join(STATIC_DIR, "index.html")
VIEWS_DIR = os.path.join(STATIC_DIR, "views")
LAYOUT_PATH = os.path.join(VIEWS_DIR, "_layout.html")

# Ordem exata em que as views aparecem no index.html.
VIEW_IDS = [
    "dashboard",
    "empresas",
    "comercial",
    "usuarios",
    "unidades",
    "cnpjs",
    "terceirizados",
    "colaboradores",
    "gestao-colaborador",
    "epis",
    "entregas",
    "estoque",
    "fichas",
    "configuracao",
    "compras",
    "relatorios",
    "avaliacoes",
]

# Indentação das tags <section id="X-view"> de abertura no index.html.
OPEN_INDENT = "      "

# Sub-fragmentos da casca (tudo que não é view), na ordem em que aparecem.
SHELL_FRAGMENTS = ["head", "login", "sidebar", "topbar", "modals", "scripts"]

MODALS_DIR = os.path.join(VIEWS_DIR, "modals")

# Modais embutidos em views grandes que são extraídos para arquivos próprios.
# Cada par: (view_id, id do <div> do modal). A extração é byte-idêntica.
MODAL_EXTRACTIONS = [
    ("compras", "aprovacoes-reprovar-modal"),
    ("compras", "aprovacoes-prorrogar-modal"),
    ("compras", "modal-edit-supplier"),
    ("compras", "modal-supplier-pos"),
    ("avaliacoes", "aval-action-modal"),
]


# Cache-buster derivado do conteúdo (Fase 0 UBX). Os fragmentos usam o
# marcador `?v=__ASSET_VERSION__`; o build/check substitui pelo hash do conteúdo
# de todos os JS/CSS. Assim a versão nunca dessincroniza: qualquer alteração em
# JS/CSS gera nova versão e invalida o cache do navegador automaticamente.
ASSET_VERSION_PLACEHOLDER = "__ASSET_VERSION__"


def _compute_asset_version():
    """Hash determinístico do conteúdo de todos os assets JS/CSS de static/.

    Exclui o build do Flutter Web (static/app/, versionado pelo próprio build) e
    o harness de testes JS (static/js/test/), que não afetam o runtime do SPA.
    """
    flutter_prefix = os.path.join(STATIC_DIR, "app") + os.sep
    test_prefix = os.path.join(STATIC_DIR, "js", "test") + os.sep
    paths = []
    for root, _dirs, files in os.walk(STATIC_DIR):
        root_with_sep = root + os.sep
        if root_with_sep.startswith(flutter_prefix) or root_with_sep.startswith(test_prefix):
            continue
        for filename in files:
            if filename.endswith((".js", ".css")):
                paths.append(os.path.join(root, filename))
    digest = hashlib.sha256()
    for path in sorted(paths):
        rel = os.path.relpath(path, STATIC_DIR).replace(os.sep, "/")
        with open(path, "rb") as fh:
            content = fh.read()
        digest.update(rel.encode("utf-8"))
        digest.update(b"\0")
        digest.update(content)
        digest.update(b"\0")
    return digest.hexdigest()[:12]


def _resolve_asset_version(text):
    return text.replace(ASSET_VERSION_PLACEHOLDER, _compute_asset_version())


def _placeholder(view_id):
    return "<!-- EPI_VIEW_INCLUDE:%s -->" % view_id


def _shell_placeholder(name):
    return "<!-- EPI_SHELL_INCLUDE:%s -->" % name


def _modal_placeholder(modal_id):
    return "<!-- EPI_MODAL_INCLUDE:%s -->" % modal_id


def _open_marker(view_id):
    return '%s<section id="%s-view"' % (OPEN_INDENT, view_id)


def _find_view_starts(lines):
    """Retorna a lista de índices de linha onde cada view abre, em ordem."""
    starts = []
    cursor = 0
    for view_id in VIEW_IDS:
        marker = _open_marker(view_id)
        found = None
        for i in range(cursor, len(lines)):
            if lines[i].startswith(marker):
                found = i
                break
        if found is None:
            raise SystemExit("Abertura da view '%s' não encontrada após linha %d" % (view_id, cursor))
        starts.append(found)
        cursor = found + 1
    return starts


def _find_last_view_end(lines, start):
    """Índice da linha imediatamente após o fechamento da última view.

    Usa contagem de profundidade de <section>/</section> (robusta a indentação).
    """
    return _find_block_end(lines, start, _count_section_opens, "</section>")


def _count_section_opens(line):
    """Conta tags de abertura <section ...> ignorando os fechamentos </section>."""
    count = 0
    idx = 0
    while True:
        pos = line.find("<section", idx)
        if pos == -1:
            break
        # Garante que não é "</section"
        if pos == 0 or line[pos - 1] != "/":
            count += 1
        idx = pos + len("<section")
    return count


def extract():
    with open(INDEX_PATH, "r", encoding="utf-8") as fh:
        content = fh.read()
    lines = content.splitlines(keepends=True)

    starts = _find_view_starts(lines)
    last_end = _find_last_view_end(lines, starts[-1])

    os.makedirs(VIEWS_DIR, exist_ok=True)

    # Calcula fatias contíguas por view.
    slices = []
    for i, start in enumerate(starts):
        end = starts[i + 1] if i + 1 < len(starts) else last_end
        slices.append((VIEW_IDS[i], start, end))

    pre = "".join(lines[: starts[0]])
    post = "".join(lines[last_end:])

    # Grava fragmentos.
    for view_id, start, end in slices:
        frag = "".join(lines[start:end])
        frag_path = os.path.join(VIEWS_DIR, "%s.html" % view_id)
        with open(frag_path, "w", encoding="utf-8") as fh:
            fh.write(frag)

    # Monta layout: pre + placeholders adjacentes + post.
    layout = pre + "".join(_placeholder(vid) for vid in VIEW_IDS) + post
    with open(LAYOUT_PATH, "w", encoding="utf-8") as fh:
        fh.write(layout)

    print("Extraídas %d views para %s" % (len(VIEW_IDS), VIEWS_DIR))
    # Verifica round-trip imediato.
    rebuilt = _resolve_asset_version(_assemble())
    if rebuilt != content:
        raise SystemExit("ERRO: reconstrução não é byte-idêntica após extração!")
    print("Round-trip byte-idêntico verificado.")


def _read_fragment(filename):
    with open(os.path.join(VIEWS_DIR, filename), "r", encoding="utf-8") as fh:
        return fh.read()


def _assemble():
    with open(LAYOUT_PATH, "r", encoding="utf-8") as fh:
        result = fh.read()
    # Expande sub-fragmentos da casca (se o layout estiver decomposto).
    for name in SHELL_FRAGMENTS:
        placeholder = _shell_placeholder(name)
        if placeholder in result:
            result = result.replace(placeholder, _read_fragment("_%s.html" % name), 1)
    # Expande as views.
    for view_id in VIEW_IDS:
        placeholder = _placeholder(view_id)
        if placeholder not in result:
            raise SystemExit("Marcador ausente no layout para a view '%s'" % view_id)
        result = result.replace(placeholder, _read_fragment("%s.html" % view_id), 1)
    # Expande modais extraídos (marcadores presentes dentro das views).
    if os.path.isdir(MODALS_DIR):
        for filename in sorted(os.listdir(MODALS_DIR)):
            if not filename.endswith(".html"):
                continue
            modal_id = filename[: -len(".html")]
            placeholder = _modal_placeholder(modal_id)
            if placeholder in result:
                with open(os.path.join(MODALS_DIR, filename), "r", encoding="utf-8") as fh:
                    result = result.replace(placeholder, fh.read(), 1)
    return result


def _first_line_index(lines, predicate, start=0):
    for i in range(start, len(lines)):
        if predicate(lines[i]):
            return i
    return None


def split_layout():
    """Decompõe _layout.html em sub-fragmentos de casca (_head, _login, ...).

    Mantém a linha de marcadores de view intacta no centro. O resultado é
    byte-idêntico: os sub-fragmentos são fatias contíguas do _layout.html.
    """
    with open(LAYOUT_PATH, "r", encoding="utf-8") as fh:
        original_layout = fh.read()
    lines = original_layout.splitlines(keepends=True)

    i_login = _first_line_index(lines, lambda ln: ln.startswith('  <section id="login-screen"'))
    i_sidebar = _first_line_index(lines, lambda ln: ln.startswith('  <section id="main-screen"'))
    i_topbar = _first_line_index(lines, lambda ln: ln.startswith('    <main id="main-content"'))
    i_markers = _first_line_index(lines, lambda ln: ln.startswith("<!-- EPI_VIEW_INCLUDE:"))
    if None in (i_login, i_sidebar, i_topbar, i_markers):
        raise SystemExit("Âncoras da casca não encontradas no _layout.html")
    i_scripts = _first_line_index(lines, lambda ln: "<script" in ln, start=i_markers + 1)
    if i_scripts is None:
        raise SystemExit("Bloco de scripts não encontrado no _layout.html")

    parts = {
        "head": lines[0:i_login],
        "login": lines[i_login:i_sidebar],
        "sidebar": lines[i_sidebar:i_topbar],
        "topbar": lines[i_topbar:i_markers],
        "modals": lines[i_markers + 1:i_scripts],
        "scripts": lines[i_scripts:],
    }
    markers_line = "".join(lines[i_markers:i_markers + 1])

    for name in SHELL_FRAGMENTS:
        with open(os.path.join(VIEWS_DIR, "_%s.html" % name), "w", encoding="utf-8") as fh:
            fh.write("".join(parts[name]))

    new_layout = (
        _shell_placeholder("head")
        + _shell_placeholder("login")
        + _shell_placeholder("sidebar")
        + _shell_placeholder("topbar")
        + markers_line
        + _shell_placeholder("modals")
        + _shell_placeholder("scripts")
    )
    with open(LAYOUT_PATH, "w", encoding="utf-8") as fh:
        fh.write(new_layout)

    print("Casca decomposta em %d sub-fragmentos." % len(SHELL_FRAGMENTS))
    # Verifica round-trip: _layout reconstituído deve bater com o original.
    rebuilt_layout = new_layout
    for name in SHELL_FRAGMENTS:
        rebuilt_layout = rebuilt_layout.replace(
            _shell_placeholder(name), "".join(parts[name]), 1
        )
    if rebuilt_layout != original_layout:
        raise SystemExit("ERRO: reconstrução do _layout não é byte-idêntica!")
    print("Round-trip da casca byte-idêntico verificado.")


def _count_div_opens(line):
    """Conta tags de abertura <div ...> ignorando os fechamentos </div>."""
    count = 0
    idx = 0
    while True:
        pos = line.find("<div", idx)
        if pos == -1:
            break
        if pos == 0 or line[pos - 1] != "/":
            count += 1
        idx = pos + len("<div")
    return count


def _find_block_end(lines, start, open_counter, close_token):
    """Índice da linha após o fechamento do bloco aberto em `start`."""
    depth = 0
    opened = False
    for i in range(start, len(lines)):
        line = lines[i]
        opens = open_counter(line)
        closes = line.count(close_token)
        if opens:
            depth += opens
            opened = True
        if closes:
            depth -= closes
        if opened and depth <= 0:
            return i + 1
    raise SystemExit("Fechamento de bloco não encontrado a partir da linha %d" % start)


def split_modals(extractions=None):
    """Extrai modais embutidos em views para static/views/modals/<id>.html.

    Substitui cada bloco do modal por um marcador EPI_MODAL_INCLUDE. A operação
    é byte-idêntica (substituição de substring exata).
    """
    extractions = extractions or MODAL_EXTRACTIONS
    os.makedirs(MODALS_DIR, exist_ok=True)
    by_view = {}
    for view_id, modal_id in extractions:
        by_view.setdefault(view_id, []).append(modal_id)

    for view_id, modal_ids in by_view.items():
        frag_path = os.path.join(VIEWS_DIR, "%s.html" % view_id)
        with open(frag_path, "r", encoding="utf-8") as fh:
            content = fh.read()
        original = content
        for modal_id in modal_ids:
            lines = content.splitlines(keepends=True)
            marker = '<div id="%s"' % modal_id
            start = _first_line_index(lines, lambda ln, m=marker: m in ln)
            if start is None:
                raise SystemExit("Modal '%s' não encontrado em %s" % (modal_id, view_id))
            end = _find_block_end(lines, start, _count_div_opens, "</div>")
            block = "".join(lines[start:end])
            modal_path = os.path.join(MODALS_DIR, "%s.html" % modal_id)
            with open(modal_path, "w", encoding="utf-8") as fh:
                fh.write(block)
            if content.count(block) != 1:
                raise SystemExit("Bloco do modal '%s' não é único em %s" % (modal_id, view_id))
            content = content.replace(block, _modal_placeholder(modal_id), 1)
        with open(frag_path, "w", encoding="utf-8") as fh:
            fh.write(content)
        print("View '%s': %d modal(is) extraído(s)." % (view_id, len(modal_ids)))
        # Sanidade local: re-expandir reproduz o fragmento original.
        rebuilt = content
        for modal_id in modal_ids:
            with open(os.path.join(MODALS_DIR, "%s.html" % modal_id), "r", encoding="utf-8") as fh:
                rebuilt = rebuilt.replace(_modal_placeholder(modal_id), fh.read(), 1)
        if rebuilt != original:
            raise SystemExit("ERRO: reconstrução da view '%s' não é byte-idêntica!" % view_id)

    # Verificação global de round-trip.
    rebuilt_index = _assemble()
    with open(INDEX_PATH, "r", encoding="utf-8") as fh:
        if rebuilt_index != fh.read():
            raise SystemExit("ERRO: index.html não é byte-idêntico após extração de modais!")
    print("Round-trip global byte-idêntico verificado.")


def build():
    rebuilt = _resolve_asset_version(_assemble())
    with open(INDEX_PATH, "w", encoding="utf-8") as fh:
        fh.write(rebuilt)
    print("index.html reconstruído a partir dos fragmentos (asset_version=%s)." % _compute_asset_version())


def check():
    rebuilt = _resolve_asset_version(_assemble())
    with open(INDEX_PATH, "r", encoding="utf-8") as fh:
        current = fh.read()
    if rebuilt != current:
        print("DIVERGÊNCIA: index.html difere do resultado do build dos fragmentos.")
        print("Execute 'python scripts/build_index.py build' para sincronizar.")
        return 1
    print("OK: index.html está sincronizado com os fragmentos de view.")
    return 0


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "check"
    if mode == "extract":
        extract()
    elif mode == "split-layout":
        split_layout()
    elif mode == "split-modals":
        split_modals()
    elif mode == "build":
        build()
    elif mode == "check":
        return check()
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
