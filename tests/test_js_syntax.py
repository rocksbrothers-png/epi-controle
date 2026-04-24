import shutil
import subprocess
from pathlib import Path
import re


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


def test_all_local_scripts_loaded_by_index_have_valid_js_syntax():
    root = Path(__file__).resolve().parents[1]
    node = _node_binary()
    index_html = (root / "static" / "index.html").read_text(encoding="utf-8")
    script_src_matches = re.findall(r'<script[^>]+src="([^"]+)"', index_html)
    local_js_paths = []
    for src in script_src_matches:
        if not src.startswith("/"):
            continue
        if src.startswith("//"):
            continue
        path_without_query = src.split("?", 1)[0]
        if not path_without_query.endswith(".js"):
            continue
        local_js_paths.append(root / "static" / path_without_query.lstrip("/"))

    for js_path in local_js_paths:
        assert js_path.exists(), f"Script referenciado no index não encontrado: {js_path}"
        subprocess.run(
            [node, "--check", str(js_path)],
            check=True,
            capture_output=True,
            text=True,
        )


def test_index_loads_single_main_app_script_without_legacy_bundle():
    root = Path(__file__).resolve().parents[1]
    index_html = (root / "static" / "index.html").read_text(encoding="utf-8")
    script_src_matches = re.findall(r'<script[^>]+src="([^"]+)"', index_html)
    local_sources = [src.split("?", 1)[0] for src in script_src_matches if src.startswith("/")]

    app_js_sources = [src for src in local_sources if src == "/app.js"]
    assert len(app_js_sources) == 1, "index.html deve carregar exatamente um /app.js."

    legacy_sources = [src for src in local_sources if src.startswith("/app.v") and src.endswith(".js")]
    assert not legacy_sources, "index.html não deve carregar bundles legados app.v*.js."
