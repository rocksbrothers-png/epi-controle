"""Nenhum perfil de navegador gerado localmente pode voltar ao repositório.

O `flutter run -d chrome` cria um perfil completo do Chrome em
`flutter/**/.dart_tool/chrome-device/` (preferências, chaves internas do
navegador, bancos de senhas e cookies, ainda que vazios). Esse perfil entrou
no histórico antes da regra `flutter/**/.dart_tool/` do `.gitignore` e gerou
os 12 achados históricos do gitleaks documentados em
`docs/SECURITY_GITLEAKS_HISTORICO.md`. O `.gitignore` não protege arquivo já
versionado; este teste protege.
"""
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_SEGMENT = '/.dart_tool/chrome-device/'


def _tracked_files():
    try:
        out = subprocess.run(['git', 'ls-files', '-z'], cwd=ROOT, check=True,
                             capture_output=True).stdout
    except (FileNotFoundError, subprocess.CalledProcessError) as exc:
        raise pytest.skip.Exception('repositório git indisponível neste ambiente') from exc
    return [name for name in out.decode('utf-8', 'replace').split('\0') if name]


def test_no_chrome_profile_is_versioned():
    offenders = [name for name in _tracked_files() if FORBIDDEN_SEGMENT in '/' + name]
    assert offenders == [], f'perfil de navegador versionado: {offenders[:5]} (+{max(0, len(offenders) - 5)})'


def test_gitignore_keeps_dart_tool_out():
    rules = (ROOT / '.gitignore').read_text(encoding='utf-8').splitlines()
    assert 'flutter/**/.dart_tool/' in [rule.strip() for rule in rules]


def test_detector_is_not_vacuous():
    forged = ['flutter/apps/epi_admin/.dart_tool/chrome-device/Default/Preferences']
    assert [name for name in forged if FORBIDDEN_SEGMENT in '/' + name] == forged
