"""F0 — guarda de domínio da Ficha 360° de EPI.

Roda ``static/js/test/employee-ppe-360-boundary.js`` na árvore versionada (deve
passar) e prova, por sabotagem numa cópia isolada, que cada regra reprova o que
deve reprovar: um gate que nunca fica vermelho não é gate.
"""

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
GUARD = Path('static/js/test/employee-ppe-360-boundary.js')
DOMAIN = Path('static/js/modules/employee-ppe-360')
LIFECYCLE = DOMAIN / 'ui' / 'employee-ppe-360-lifecycle.js'
BUSINESS = DOMAIN / 'business' / 'employee-ppe-360-contract.js'

pytestmark = pytest.mark.skipif(shutil.which('node') is None, reason='Node.js não disponível')


def _run(root: Path) -> subprocess.CompletedProcess:
    return subprocess.run(['node', str(root / GUARD)], capture_output=True, text=True, cwd=root, check=False)


@pytest.fixture()
def sandbox(tmp_path: Path) -> Path:
    shutil.copytree(ROOT / 'static/js', tmp_path / 'static/js')
    shutil.copy2(ROOT / 'static/app.js', tmp_path / 'static/app.js')
    return tmp_path


def _append(root: Path, rel: Path, code: str) -> None:
    target = root / rel
    text = target.read_text(encoding='utf-8')
    closing = '})();\n'
    assert text.endswith(closing)
    target.write_text(text[: -len(closing)] + code + '\n' + closing, encoding='utf-8')


def test_arvore_versionada_passa():
    result = _run(ROOT)
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize('rel,code,expected', [
    (LIFECYCLE, "  globalThis.api('/api/employees/1/ppe-360/summary');", 'chamada HTTP'),
    (LIFECYCLE, "  const url = '/api/employees';", 'caminho /api'),
    (LIFECYCLE, '  globalThis.__EPI_API_CLIENT__;', 'cliente HTTP'),
    (BUSINESS, "  const x = new XMLHttpRequest();", 'chamada HTTP'),
    (BUSINESS, '  function t(item) { return item.unit_price * item.quantity; }', 'cálculo financeiro'),
    (LIFECYCLE, '  function t(rows) { let total = 0; rows.forEach((r) => { total = total + r.amount; }); return total; }', 'cálculo financeiro'),
    (BUSINESS, '  function t(v) { return parseFloat(v); }', 'cálculo financeiro'),
    (BUSINESS, '  function t(v) { return v.toFixed(2); }', 'cálculo financeiro'),
    (LIFECYCLE, "  localStorage.setItem('ficha', '1');", 'storage'),
    (LIFECYCLE, "  globalThis.fichaAtual = 5;", 'escrita em global'),
    (LIFECYCLE, "  window['outro'] = 1;", 'escrita em global'),
    (LIFECYCLE, "  globalThis.document.addEventListener('click', () => {});", 'AbortSignal'),
    (LIFECYCLE, "  const p = globalThis.__EPI_PURCHASE_LIMITS_API__;", 'não referencia Compras'),
])
def test_sabotagem_no_dominio_reprova(sandbox: Path, rel, code, expected):
    _append(sandbox, rel, code)
    result = _run(sandbox)
    assert result.returncode == 1, result.stdout
    assert expected in result.stderr


def test_sabotagem_app_js_referencia_a_ficha(sandbox: Path):
    app = sandbox / 'static/app.js'
    app.write_text(app.read_text(encoding='utf-8') + '\nglobalThis.__EPI_EMPLOYEE_PPE_360_LIFECYCLE__;\n', encoding='utf-8')
    result = _run(sandbox)
    assert result.returncode == 1
    assert 'static/app.js referencia a Ficha' in result.stderr


def test_sabotagem_compras_depende_da_ficha(sandbox: Path):
    target = sandbox / 'static/js/views/purchases.js'
    target.write_text(target.read_text(encoding='utf-8') + '\nglobalThis.__EPI_EMPLOYEE_PPE_360_BUSINESS__;\n', encoding='utf-8')
    result = _run(sandbox)
    assert result.returncode == 1
    assert 'Compras não depende da Ficha' in result.stderr


def test_sabotagem_arquivo_fora_das_camadas(sandbox: Path):
    (sandbox / DOMAIN / 'helpers.js').write_text("'use strict';\n", encoding='utf-8')
    result = _run(sandbox)
    assert result.returncode == 1
    assert 'business/, integrations/ ou ui/' in result.stderr


def test_sabotagem_dominio_removido(sandbox: Path):
    shutil.rmtree(sandbox / DOMAIN)
    result = _run(sandbox)
    assert result.returncode == 1
    assert 'fundação F0 é obrigatória' in result.stderr


def test_integrations_pode_fazer_http(sandbox: Path):
    """A regra é de camada, não de nome: HTTP é permitido em integrations/."""
    integ = sandbox / DOMAIN / 'integrations'
    integ.mkdir(exist_ok=True)  # existe desde a F1
    (integ / 'employee-ppe-360-api.js').write_text(
        "'use strict';\n(function () {\n  globalThis.__EPI_EMPLOYEE_PPE_360_API__ = Object.freeze({\n"
        "    summary: (id) => globalThis.api(`/api/employees/${id}/ppe-360/summary`)\n  });\n})();\n",
        encoding='utf-8',
    )
    result = _run(sandbox)
    assert result.returncode == 0, result.stderr


def test_exibir_valor_pronto_nao_e_calculo(sandbox: Path):
    _append(sandbox, LIFECYCLE, '  function t(item) { return item.amount === null ? null : String(item.amount); }')
    result = _run(sandbox)
    assert result.returncode == 0, result.stderr
