import shutil
import subprocess
from pathlib import Path


def _node_binary():
    node = shutil.which("node")
    if not node:
        raise AssertionError("Node.js não encontrado no ambiente para validar sintaxe JS.")
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
