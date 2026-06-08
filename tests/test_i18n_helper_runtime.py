import shutil
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
HELPER_PATH = ROOT / "static" / "i18n-helper.js"


def _node_binary():
    node = shutil.which("node")
    if not node:
        pytest.skip("Node.js não encontrado no ambiente para validar o helper i18n.")
    return node


def _run_helper_scenario(scenario: str) -> None:
    script = f"""
const fs = require('fs');
const vm = require('vm');
const source = fs.readFileSync({str(HELPER_PATH)!r}, 'utf8');
const sandbox = {{ console }};
sandbox.globalThis = sandbox;
{scenario}
vm.runInNewContext(source, sandbox, {{ filename: 'i18n-helper.js' }});
if (!sandbox.EpiI18nHelper || typeof sandbox.EpiI18nHelper.resolveLegacyTranslator !== 'function') {{
  throw new Error('EpiI18nHelper API was not exposed');
}}
"""
    subprocess.run(
        [_node_binary(), "-e", script],
        check=True,
        capture_output=True,
        text=True,
    )


def test_i18n_helper_preserves_existing_tr_epi_ownership():
    _run_helper_scenario(
        """
const existing = function existingTranslator(key) { return `existing:${key}`; };
sandbox.trEpi = existing;
setImmediate(() => {
  const resolved = sandbox.EpiI18nHelper.resolveLegacyTranslator();
  if (resolved !== existing) throw new Error('existing translator was not preserved');
  if (sandbox.trEpi !== existing) throw new Error('global trEpi was overwritten');
});
"""
    )


def test_i18n_helper_installs_fallback_only_when_missing():
    _run_helper_scenario(
        """
setImmediate(() => {
  const resolved = sandbox.EpiI18nHelper.resolveLegacyTranslator();
  if (typeof resolved !== 'function') throw new Error('fallback translator was not returned');
  if (sandbox.trEpi !== resolved) throw new Error('fallback translator was not installed');
  if (resolved('missing.key', 'Fallback') !== 'Fallback') throw new Error('fallback argument was not respected');
});
"""
    )


def test_i18n_helper_fallback_uses_window_t_when_translation_exists():
    _run_helper_scenario(
        """
sandbox.window = { t: (key) => key === 'known.key' ? 'Translated value' : key };
setImmediate(() => {
  const resolved = sandbox.EpiI18nHelper.resolveLegacyTranslator();
  if (resolved('known.key', 'Fallback') !== 'Translated value') throw new Error('window.t translation was not used');
  if (resolved('unknown.key', 'Fallback') !== 'Fallback') throw new Error('fallback was not used for unknown key');
});
"""
    )
