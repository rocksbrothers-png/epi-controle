#!/usr/bin/env python3
"""Montagem modular do static/index.html a partir de fragmentos de view.

O index.html é um arquivo monolítico (~2600 linhas). Para permitir manutenção
por módulo sem risco em runtime, este script separa cada seção de view em um
fragmento próprio em ``static/views/`` e reconstrói o index.html a partir de um
layout (``static/views/_layout.html``) com marcadores de inclusão.

A reconstrução é byte-idêntica ao original por construção: o layout é o texto
original com cada fatia de view substituída por um marcador, e o build apenas
re-substitui o marcador pela fatia exata.

Modos:
  extract  Separa index.html -> _layout.html + views/<id>.html (primeira vez)
  build    Reconstrói index.html a partir do layout + fragmentos
  check    Reconstrói em memória e compara com index.html atual (exit!=0 se diferir)

Uso:
  python scripts/build_index.py extract
  python scripts/build_index.py build
  python scripts/build_index.py check
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


def _placeholder(view_id):
    return "<!-- EPI_VIEW_INCLUDE:%s -->" % view_id


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


def _assemble():
    with open(LAYOUT_PATH, "r", encoding="utf-8") as fh:
        layout = fh.read()
    result = layout
    for view_id in VIEW_IDS:
        frag_path = os.path.join(VIEWS_DIR, "%s.html" % view_id)
        with open(frag_path, "r", encoding="utf-8") as fh:
            frag = fh.read()
        placeholder = _placeholder(view_id)
        if placeholder not in result:
            raise SystemExit("Marcador ausente no layout para a view '%s'" % view_id)
        result = result.replace(placeholder, frag, 1)
    return result


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
