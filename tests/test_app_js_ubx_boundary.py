"""Guarda arquitetural UBX do static/app.js.

Executa static/js/test/app-js-boundary.js na árvore versionada (deve passar) e
prova, por sabotagem numa cópia isolada, que cada regra reprova o que deve
reprovar: um gate que nunca fica vermelho não é gate.

A guarda não mede linhas. Ela impede que o monólito ganhe responsabilidades
(declarações de nível superior e endpoints HTTP novos), impede que uma função
extraída volte ao app.js, exige que o módulo extraído carregue antes do app.js
e aplica as regras de camada (business sem DOM/HTTP/storage/estado global,
integrations sem DOM).
"""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
GUARD = Path("static/js/test/app-js-boundary.js")
BASELINE = Path("static/js/test/app-js-baseline.json")

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="Node.js não disponível")


def _run(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["node", str(root / GUARD), *args],
        capture_output=True,
        text=True,
        cwd=root,
        check=False,
    )


@pytest.fixture()
def sandbox(tmp_path: Path) -> Path:
    for rel in (
        "static/app.js",
        "static/views/_scripts.html",
        str(GUARD),
        str(BASELINE),
        "static/js/utils/debug.js",
    ):
        dst = tmp_path / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / rel, dst)
    shutil.copytree(ROOT / "static/js/modules", tmp_path / "static/js/modules")
    return tmp_path


def _append_to_app_js(root: Path, code: str) -> None:
    app = root / "static/app.js"
    text = app.read_text(encoding="utf-8")
    closing = "// fechamento do runtime guard global __EPI_APP_RUNTIME_LOADED__\n}"
    assert closing in text
    app.write_text(text.replace(closing, code + "\n" + closing), encoding="utf-8")


def test_arvore_versionada_passa_na_guarda():
    result = _run(ROOT)
    assert result.returncode == 0, result.stdout + result.stderr


def test_baseline_nao_lista_nomes_extraidos():
    baseline = json.loads((ROOT / BASELINE).read_text(encoding="utf-8"))
    declared = set(baseline["declarations"])
    for module, names in baseline["extracted"].items():
        assert not declared & set(names), f"{module}: nomes extraídos ainda no baseline"


def test_sabotagem_nova_funcao_no_app_js_reprova(sandbox: Path):
    _append_to_app_js(sandbox, "function novaRegraDeNegocioNoMonolito() { return 1; }")
    result = _run(sandbox)
    assert result.returncode == 1
    assert "novaRegraDeNegocioNoMonolito" in result.stderr


def test_sabotagem_novo_endpoint_no_app_js_reprova(sandbox: Path):
    _append_to_app_js(sandbox, "globalThis.__x = () => api('/api/endpoint-novo-no-monolito');")
    result = _run(sandbox)
    assert result.returncode == 1
    assert "/api/endpoint-novo-no-monolito" in result.stderr


def test_sabotagem_funcao_extraida_volta_ao_app_js_reprova(sandbox: Path):
    _append_to_app_js(sandbox, "function _parsePurchaseMoney(v) { return Number(v); }")
    result = _run(sandbox)
    assert result.returncode == 1
    assert "_parsePurchaseMoney foi extraído" in result.stderr


def test_sabotagem_business_tocando_dom_reprova(sandbox: Path):
    module = sandbox / "static/js/modules/purchases/business/purchase-import-matching.js"
    module.write_text(
        module.read_text(encoding="utf-8") + "\ndocument.title = 'x';\n", encoding="utf-8"
    )
    result = _run(sandbox)
    assert result.returncode == 1
    assert "camada business" in result.stderr


def test_sabotagem_business_chamando_http_reprova(sandbox: Path):
    module = sandbox / "static/js/modules/purchases/business/purchase-import-matching.js"
    module.write_text(
        module.read_text(encoding="utf-8") + "\nfetch('/api/x');\n", encoding="utf-8"
    )
    result = _run(sandbox)
    assert result.returncode == 1
    assert "HTTP" in result.stderr


def test_sabotagem_modulo_carregado_depois_do_app_js_reprova(sandbox: Path):
    scripts = sandbox / "static/views/_scripts.html"
    tag = (
        '  <script defer src="/js/modules/purchases/business/'
        'purchase-import-matching.js?v=__ASSET_VERSION__"></script>\n'
    )
    text = scripts.read_text(encoding="utf-8")
    assert tag in text
    text = text.replace(tag, "")
    text = text.replace("</body>", tag + "</body>")
    scripts.write_text(text, encoding="utf-8")
    result = _run(sandbox)
    assert result.returncode == 1
    assert "precisa carregar antes de /app.js" in result.stderr


def test_catraca_extracao_exige_atualizar_baseline_e_update_so_remove(sandbox: Path):
    app = sandbox / "static/app.js"
    text = app.read_text(encoding="utf-8")
    target = "function _readFileAsBase64(file) {"
    assert target in text
    app.write_text(text.replace(target, "globalThis.__removed = function (file) {"), encoding="utf-8")

    result = _run(sandbox)
    assert result.returncode == 1
    assert "baseline desatualizado" in result.stderr

    before = json.loads((sandbox / BASELINE).read_text(encoding="utf-8"))
    result = _run(sandbox, "--update")
    assert result.returncode == 0, result.stdout + result.stderr
    after = json.loads((sandbox / BASELINE).read_text(encoding="utf-8"))
    assert "_readFileAsBase64" in before["declarations"]
    assert "_readFileAsBase64" not in after["declarations"]
    assert set(after["declarations"]) <= set(before["declarations"])
    assert set(after["endpoints"]) <= set(before["endpoints"])
