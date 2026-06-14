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
  build         Reconstrói index.html a partir do layout + fragmentos
  check         Reconstrói em memória e compara com index.html atual (exit!=0 se diferir)

Uso:
  python scripts/build_index.py extract
  python scripts/build_index.py split-layout
  python scripts/build_index.py build
  python scripts/build_index.py check

Fluxo de re-extração completa (raro): extract, depois split-layout.
"""

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


def _placeholder(view_id):
    return "<!-- EPI_VIEW_INCLUDE:%s -->" % view_id


def _shell_placeholder(name):
    return "<!-- EPI_SHELL_INCLUDE:%s -->" % name


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
    depth = 0
    opened = False
    for i in range(start, len(lines)):
        line = lines[i]
        opens = _count_section_opens(line)
        closes = line.count("</section>")
        if opens:
            depth += opens
            opened = True
        if closes:
            depth -= closes
        if opened and depth <= 0:
            return i + 1
    raise SystemExit("Fechamento da última view não encontrado a partir da linha %d" % start)


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
    rebuilt = _assemble()
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


def build():
    rebuilt = _assemble()
    with open(INDEX_PATH, "w", encoding="utf-8") as fh:
        fh.write(rebuilt)
    print("index.html reconstruído a partir dos fragmentos.")


def check():
    rebuilt = _assemble()
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
