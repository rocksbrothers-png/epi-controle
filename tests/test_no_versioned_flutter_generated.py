"""Artefatos gerados pelo Flutter não podem voltar ao repositório.

`flutter pub get` e o build recriam, a cada execução, `.dart_tool/`,
`.flutter-plugins(-dependencies)` e o `GeneratedPluginRegistrant.java` do
Android. Versionados, eles ficavam desatualizados (citavam versões antigas de
plugins) e carregavam caminhos absolutos da máquina de quem os gerou, inclusive
o usuário do sistema. O `.gitignore` não protege arquivo já versionado; este
teste protege. O perfil do Chrome tem guarda própria em
`tests/test_no_versioned_browser_profile.py`.
"""
import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
GENERATED = re.compile(
    r'^flutter/(?:.*/)?(?:'
    r'\.dart_tool/'
    r'|\.flutter-plugins(?:-dependencies)?$'
    r'|android/app/src/main/java/io/flutter/plugins/GeneratedPluginRegistrant\.java$'
    r')'
)
REQUIRED_RULES = [
    'flutter/**/.dart_tool/',
    'flutter/**/.flutter-plugins',
    'flutter/**/.flutter-plugins-dependencies',
    'flutter/**/android/app/src/main/java/io/flutter/plugins/GeneratedPluginRegistrant.java',
]


def _tracked_files():
    try:
        out = subprocess.run(['git', 'ls-files', '-z'], cwd=ROOT, check=True,
                             capture_output=True).stdout
    except (FileNotFoundError, subprocess.CalledProcessError) as exc:
        raise pytest.skip.Exception('repositório git indisponível neste ambiente') from exc
    return [name for name in out.decode('utf-8', 'replace').split('\0') if name]


def test_no_flutter_generated_file_is_versioned():
    offenders = [name for name in _tracked_files() if GENERATED.search(name)]
    assert offenders == [], f'artefato gerado versionado: {offenders[:5]} (+{max(0, len(offenders) - 5)})'


def test_gitignore_keeps_flutter_generated_files_out():
    rules = {rule.strip() for rule in (ROOT / '.gitignore').read_text(encoding='utf-8').splitlines()}
    assert [rule for rule in REQUIRED_RULES if rule not in rules] == []


@pytest.mark.parametrize('name', [
    'flutter/.dart_tool/package_config.json',
    'flutter/packages/epi_api/.dart_tool/version',
    'flutter/apps/epi_admin/.flutter-plugins-dependencies',
    'flutter/apps/epi_admin/.flutter-plugins',
    'flutter/apps/epi_admin/android/app/src/main/java/io/flutter/plugins/GeneratedPluginRegistrant.java',
])
def test_detector_flags_generated_files(name):
    assert GENERATED.search(name)


@pytest.mark.parametrize('name', [
    'flutter/apps/epi_admin/pubspec.yaml',
    'flutter/apps/epi_admin/android/app/build.gradle',
    'flutter/apps/epi_admin/android/app/src/main/kotlin/MainActivity.kt',
    'flutter/apps/epi_admin/lib/flutter-plugins-guide.dart',
    'docs/.dart_tool/nota.md',
])
def test_detector_keeps_source_files(name):
    assert not GENERATED.search(name)
