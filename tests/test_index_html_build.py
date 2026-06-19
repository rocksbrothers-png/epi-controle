"""Garante que static/index.html está sincronizado com os fragmentos de view.

A montagem modular do index.html vive em scripts/build_index.py. Este teste
roda o modo 'check' para evitar drift: se alguém editar o index.html diretamente
sem atualizar os fragmentos (ou vice-versa), o teste falha e orienta o build.
"""

import importlib.util
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD_SCRIPT = os.path.join(ROOT, "scripts", "build_index.py")


def _load_build_module():
    spec = importlib.util.spec_from_file_location("build_index", BUILD_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_index_html_matches_view_fragments():
    build = _load_build_module()
    # O build resolve o cache-buster `?v=__ASSET_VERSION__` para o hash de conteúdo
    # (Fase 0 UBX), então a comparação aplica a mesma resolução.
    rebuilt = build._resolve_asset_version(build._assemble())
    with open(build.INDEX_PATH, "r", encoding="utf-8") as fh:
        current = fh.read()
    assert rebuilt == current, (
        "static/index.html difere do build dos fragmentos de view. "
        "Rode: python scripts/build_index.py build"
    )


def test_all_view_fragments_exist():
    build = _load_build_module()
    for view_id in build.VIEW_IDS:
        frag_path = os.path.join(build.VIEWS_DIR, "%s.html" % view_id)
        assert os.path.exists(frag_path), "Fragmento ausente: %s" % frag_path


def test_layout_has_all_include_markers():
    build = _load_build_module()
    with open(build.LAYOUT_PATH, "r", encoding="utf-8") as fh:
        layout = fh.read()
    for view_id in build.VIEW_IDS:
        assert build._placeholder(view_id) in layout, (
            "Marcador de inclusão ausente no layout para a view '%s'" % view_id
        )


def test_all_shell_fragments_exist():
    build = _load_build_module()
    for name in build.SHELL_FRAGMENTS:
        frag_path = os.path.join(build.VIEWS_DIR, "_%s.html" % name)
        assert os.path.exists(frag_path), "Sub-fragmento de casca ausente: %s" % frag_path


def test_layout_has_all_shell_markers():
    build = _load_build_module()
    with open(build.LAYOUT_PATH, "r", encoding="utf-8") as fh:
        layout = fh.read()
    for name in build.SHELL_FRAGMENTS:
        assert build._shell_placeholder(name) in layout, (
            "Marcador de casca ausente no layout para '%s'" % name
        )


def test_extracted_modals_exist_and_are_referenced():
    build = _load_build_module()
    for view_id, modal_id in build.MODAL_EXTRACTIONS:
        modal_path = os.path.join(build.MODALS_DIR, "%s.html" % modal_id)
        assert os.path.exists(modal_path), "Fragmento de modal ausente: %s" % modal_path
        with open(os.path.join(build.VIEWS_DIR, "%s.html" % view_id), "r", encoding="utf-8") as fh:
            view = fh.read()
        assert build._modal_placeholder(modal_id) in view, (
            "Marcador do modal '%s' ausente na view '%s'" % (modal_id, view_id)
        )
