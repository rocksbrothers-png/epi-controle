import shutil
import subprocess
from pathlib import Path

import pytest


def _node_binary():
    node = shutil.which("node")
    if not node:
        pytest.skip("Node.js não encontrado no ambiente para validar sintaxe JS.")
    return node


def test_app_js_syntax_is_valid():
    root = Path(__file__).resolve().parents[1]
    node = _node_binary()
    subprocess.run(
        [node, "--check", str(root / "static" / "app.js")],
        check=True,
        capture_output=True,
        text=True,
    )


def test_share_modal_js_syntax_is_valid():
    root = Path(__file__).resolve().parents[1]
    node = _node_binary()
    subprocess.run(
        [node, "--check", str(root / "static" / "share-modal.js")],
        check=True,
        capture_output=True,
        text=True,
    )


def test_all_js_files_in_static_have_valid_js_syntax():
    root = Path(__file__).resolve().parents[1]
    node = _node_binary()
    local_js_paths = sorted((root / "static").glob("*.js"))
    assert local_js_paths, "Nenhum arquivo JS encontrado em static/."

    for js_path in local_js_paths:
        subprocess.run(
            [node, "--check", str(js_path.resolve())],
            check=True,
            capture_output=True,
            text=True,
        )


def test_app_js_global_esc_helper_is_defined_before_use():
    root = Path(__file__).resolve().parents[1]
    source = (root / "static" / "app.js").read_text(encoding="utf-8")
    helper_index = source.find("function esc(value)")
    first_use_index = source.find("esc(")
    assert helper_index != -1, "app.js deve definir helper esc global para escape HTML."
    assert first_use_index == helper_index or helper_index < first_use_index, "esc deve estar definido antes de qualquer uso no fluxo pós-login/bootstrap."


def test_user_profile_options_exclude_purchase_functions():
    root = Path(__file__).resolve().parents[1]
    source = (root / "static" / "app.js").read_text(encoding="utf-8")
    role_map_start = source.index("function populateRoleOptions()")
    role_map_end = source.index("function populateUserFilters()")
    role_map_source = source[role_map_start:role_map_end]
    assert "['buyer', 'Comprador']" not in role_map_source
    assert "['approver', 'Aprovador']" not in role_map_source
