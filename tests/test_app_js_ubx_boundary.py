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
    ):
        dst = tmp_path / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / rel, dst)
    # UBX-V2: as regras de camada UI e de dependência entre scripts leem
    # static/js inteiro (views, modules, utils, core).
    shutil.copytree(ROOT / "static/js", tmp_path / "static/js", dirs_exist_ok=True)
    for script in (ROOT / "static").glob("*.js"):
        shutil.copy2(script, tmp_path / "static" / script.name)
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


def test_sabotagem_classe_nova_no_app_js_reprova(sandbox: Path):
    _append_to_app_js(sandbox, "class NovoServicoNoMonolito {}")
    result = _run(sandbox)
    assert result.returncode == 1
    assert "NovoServicoNoMonolito" in result.stderr


def test_sabotagem_endpoint_com_aspas_duplas_reprova(sandbox: Path):
    _append_to_app_js(sandbox, 'globalThis.__y = () => api("/api/aspas-duplas-no-monolito");')
    result = _run(sandbox)
    assert result.returncode == 1
    assert "/api/aspas-duplas-no-monolito" in result.stderr


def test_sabotagem_subpasta_de_business_herda_a_regra(sandbox: Path):
    nested = sandbox / "static/js/modules/purchases/business/import/helpers.js"
    nested.parent.mkdir(parents=True, exist_ok=True)
    nested.write_text("'use strict';\ndocument.body.innerHTML = '';\n", encoding="utf-8")
    result = _run(sandbox)
    assert result.returncode == 1
    assert "business/import/helpers.js" in result.stderr


# ── UBX-V2 ──────────────────────────────────────────────────────────────────


def _append(root: Path, rel: str, code: str) -> None:
    target = root / rel
    target.write_text(target.read_text(encoding="utf-8") + "\n" + code + "\n", encoding="utf-8")


def test_sabotagem_endpoint_novo_na_camada_ui_reprova(sandbox: Path):
    _append(sandbox, "static/js/views/purchases.js", "globalThis.__x = () => api('/api/endpoint-novo-na-view');")
    result = _run(sandbox)
    assert result.returncode == 1
    assert "camada UI) ganhou endpoints HTTP: /api/endpoint-novo-na-view" in result.stderr


def test_sabotagem_dependencia_circular_entre_scripts_reprova(sandbox: Path):
    # dashboard.js já lê __EPI_DASHBOARD_SCOPE__; o caminho inverso fecha o ciclo.
    _append(sandbox, "static/js/views/dashboard-scope.js", "globalThis.__x = () => globalThis.__EPI_DASHBOARD__;")
    result = _run(sandbox)
    assert result.returncode == 1
    assert "dependência circular entre scripts" in result.stderr
    assert "js/views/dashboard-scope.js ↔ js/views/dashboard.js" in result.stderr


def test_sabotagem_business_dependendo_da_camada_ui_reprova(sandbox: Path):
    _append(sandbox, "static/js/modules/shared/business/value-format.js", "const ui = __EPI_PURCHASES__;")
    result = _run(sandbox)
    assert result.returncode == 1
    assert "não pode depender da camada UI: lê __EPI_PURCHASES__" in result.stderr


def test_sabotagem_business_lendo_global_reprova(sandbox: Path):
    _append(sandbox, "static/js/modules/shared/business/value-format.js", "const t = globalThis.tr;")
    result = _run(sandbox)
    assert result.returncode == 1
    assert "leitura de global" in result.stderr


@pytest.mark.parametrize(
    "code",
    [
        "const s = window.state;",
        "const s = self.state;",
        "const s = globalThis['state'];",
        "const s = globalThis?.state;",
        "const u = state.user;",
        "const r = refs['x'];",
        "const t = tr('chave', 'texto');",
        "const ok = hasPermission('x');",
    ],
)
def test_sabotagem_business_lendo_global_por_outros_idiomas_reprova(sandbox: Path, code: str):
    _append(sandbox, "static/js/modules/shared/business/value-format.js", code)
    result = _run(sandbox)
    assert result.returncode == 1, code
    assert "camada business" in result.stderr


@pytest.mark.parametrize(
    "code",
    [
        "const x = new XMLHttpRequest();",
        "navigator.sendBeacon('/x', '');",
        "const w = new WebSocket('wss://x');",
    ],
)
def test_sabotagem_business_com_http_alternativo_reprova(sandbox: Path, code: str):
    _append(sandbox, "static/js/modules/shared/business/value-format.js", code)
    result = _run(sandbox)
    assert result.returncode == 1, code
    assert "HTTP" in result.stderr


def test_business_com_variavel_local_de_mesmo_sufixo_passa(sandbox: Path):
    # `item.state.x` e `options.tr(...)` são propriedades, não globais do app.js
    _append(
        sandbox,
        "static/js/modules/shared/business/value-format.js",
        "function __local(item, options) { return [item.state.x, options.tr('k')]; }",
    )
    result = _run(sandbox)
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize(
    ("rel", "code", "expected"),
    [
        (
            "static/js/views/dashboard.js",
            "const B = '/api'; globalThis.__x = () => fetch(B + '/novo');",
            "/api (prefixo concatenado)",
        ),
        (
            "static/js/views/feedback.js",
            "globalThis.__x = (id) => api(`/api/feedbacks/${id}/apagar-tudo`);",
            "/api/feedbacks/{}/apagar-tudo",
        ),
        ("static/estoque.js", "window.__x = () => fetch('/api/endpoint-legado-novo');", "/api/endpoint-legado-novo"),
    ],
)
def test_sabotagem_endpoint_ui_por_concatenacao_template_ou_script_legado_reprova(
    sandbox: Path, rel: str, code: str, expected: str
):
    _append(sandbox, rel, code)
    result = _run(sandbox)
    assert result.returncode == 1
    assert expected in result.stderr


def test_sabotagem_endpoint_em_modulo_ui_reprova(sandbox: Path):
    ui = sandbox / "static/js/modules/shared/ui/novo-painel.js"
    ui.parent.mkdir(parents=True, exist_ok=True)
    ui.write_text("globalThis.__x = () => fetch('/api/painel-novo');\n", encoding="utf-8")
    result = _run(sandbox)
    assert result.returncode == 1
    assert "modules/shared/ui/novo-painel.js (camada UI) ganhou endpoints HTTP: /api/painel-novo" in result.stderr


def test_limite_de_linhas_aceita_exatamente_500(sandbox: Path):
    module = sandbox / "static/js/modules/shared/business/limite.js"
    module.write_text("\n".join(f"// {i}" for i in range(500)) + "\n", encoding="utf-8")
    assert _run(sandbox).returncode == 0
    module.write_text("\n".join(f"// {i}" for i in range(501)) + "\n", encoding="utf-8")
    result = _run(sandbox)
    assert result.returncode == 1
    assert "limite.js tem 501 linhas" in result.stderr


def test_business_pode_publicar_o_proprio_contrato(sandbox: Path):
    _append(sandbox, "static/js/modules/shared/business/value-format.js", "globalThis.__contratoNovo = 1;")
    result = _run(sandbox)
    assert result.returncode == 0, result.stdout + result.stderr


def test_sabotagem_modulo_gigante_reprova(sandbox: Path):
    _append(sandbox, "static/js/modules/shared/business/value-format.js", "\n".join("// linha" for _ in range(600)))
    result = _run(sandbox)
    assert result.returncode == 1
    assert "novo monólito" in result.stderr


def test_catraca_ui_update_so_remove_endpoint(sandbox: Path):
    view = sandbox / "static/js/views/fichas.js"
    text = view.read_text(encoding="utf-8")
    assert "/api/ficha-epi-audit" in text
    view.write_text(text.replace("/api/ficha-epi-audit", "/api-removido"), encoding="utf-8")
    result = _run(sandbox)
    assert result.returncode == 1
    assert "baseline desatualizado" in result.stderr

    assert _run(sandbox, "--update").returncode == 0
    baseline = json.loads((sandbox / BASELINE).read_text(encoding="utf-8"))
    assert "js/views/fichas.js" not in baseline["uiEndpoints"]
    # devolver o endpoint depois do --update volta a reprovar: o modo update nunca adiciona
    view.write_text(text, encoding="utf-8")
    assert _run(sandbox).returncode == 1


# ── UBX-V3 ──────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "code",
    [
        "globalThis.__x = () => fetch('/x');",
        "globalThis.__x = () => window.fetch('/x');",
        "globalThis.__x = () => globalThis.fetch('/x');",
    ],
)
def test_sabotagem_fetch_cru_novo_na_camada_ui_reprova(sandbox: Path, code: str):
    _append(sandbox, "static/js/views/profile.js", code)
    result = _run(sandbox)
    assert result.returncode == 1, code
    assert "profile.js (camada UI) ganhou fetch cru (0 → 1)" in result.stderr


def test_metodo_fetch_de_outro_objeto_nao_conta_como_fetch_cru(sandbox: Path):
    _append(sandbox, "static/js/views/profile.js", "globalThis.__x = (client) => client.fetch('/x');")
    result = _run(sandbox)
    assert result.returncode == 0, result.stdout + result.stderr


def test_sabotagem_delegador_http_volta_ao_app_js_reprova(sandbox: Path):
    _append_to_app_js(sandbox, "async function api(path, options = {}) { return globalThis.apiFetch(path, options); }")
    result = _run(sandbox)
    assert result.returncode == 1
    assert "api foi extraído para static/js/modules/api-client.js e voltou a ser declarado no app.js" in result.stderr


def test_catraca_fetch_cru_update_so_diminui(sandbox: Path):
    view = sandbox / "static/js/views/procurement.js"
    text = view.read_text(encoding="utf-8")
    assert "fetch(path, opts)" in text
    view.write_text(text.replace("fetch(path, opts)", "globalThis.api(path, opts)"), encoding="utf-8")
    result = _run(sandbox)
    assert result.returncode == 1
    assert "js/views/procurement.js:fetch 1→0" in result.stderr
    assert _run(sandbox, "--update").returncode == 0
    baseline = json.loads((sandbox / BASELINE).read_text(encoding="utf-8"))
    assert "js/views/procurement.js" not in baseline["uiRawFetch"]
    view.write_text(text, encoding="utf-8")
    assert _run(sandbox).returncode == 1
