import shutil
import subprocess
from pathlib import Path

import pytest


def _node_binary():
    node = shutil.which("node")
    if not node:
        pytest.skip("Node.js não encontrado no ambiente para validar sintaxe JS.")
    return node


def _eslint_binary():
    root = Path(__file__).resolve().parents[1]
    eslint = root / "node_modules" / ".bin" / "eslint"
    if not eslint.exists():
        pytest.skip("ESLint não encontrado. Rode: npm install")
    return str(eslint)


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


def test_js_modules_pass_eslint():
    """Todos os arquivos em static/js/ devem passar no ESLint sem erros."""
    root = Path(__file__).resolve().parents[1]
    eslint = _eslint_binary()
    result = subprocess.run(
        [eslint, str(root / "static" / "js"), "--ext", ".js", "--format", "compact"],
        capture_output=True,
        text=True,
    )
    errors = [
        line for line in result.stdout.splitlines()
        if ": error " in line
    ]
    assert not errors, (
        f"ESLint encontrou {len(errors)} erro(s) nos módulos JS:\n"
        + "\n".join(errors[:20])
    )
