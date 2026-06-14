"""Roda o harness de testes unitários JS (static/js/test/run-tests.js) via Node.

Pula automaticamente se o Node não estiver disponível, para não quebrar
ambientes sem runtime JS.
"""

import os
import shutil
import subprocess

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNNER = os.path.join(ROOT, "static", "js", "test", "run-tests.js")


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js não disponível")
def test_js_unit_suite_passes():
    result = subprocess.run(
        ["node", RUNNER],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    output = result.stdout + result.stderr
    assert result.returncode == 0, "Harness JS falhou:\n" + output
