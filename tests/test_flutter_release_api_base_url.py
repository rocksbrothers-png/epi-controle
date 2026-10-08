"""Contrato de release nativo Flutter: API_BASE_URL sempre explícito (BP1).

Um build RELEASE nativo (Android AAB / iOS IPA) NÃO pode ser gerado sem
`--dart-define=API_BASE_URL`, senão o app publicado cai no fallback
`localhost:5000` de `main.dart` (que agora falha explicitamente). Este teste
inspeciona os workflows de forma tolerante a formatação YAML: procura cada
comando de build de release que PRODUZ artefato publicável e exige o define no
mesmo bloco de comando. Não valida espaços/indentação.

Roda sob pytest e também como script: `python3 tests/test_flutter_release_api_base_url.py`.
"""

from __future__ import annotations

import pathlib
import re

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
WORKFLOWS = REPO_ROOT / '.github' / 'workflows'
PUBSPEC = REPO_ROOT / 'flutter' / 'pubspec.yaml'

# Builds de release que PRODUZEM o artefato publicável nativo. O `--config-only`
# do iOS é descartável (gera só o projeto Xcode) e não entra aqui.
#
# Ancorado no INÍCIO da linha (após indentação): um comando real de `run:`
# começa com `flutter build ...`; comentários começam com `#` e prosa com
# crase/outras palavras — ambos ignorados, evitando falso positivo com o texto
# explicativo dos workflows.
SHIPPABLE_RELEASE = re.compile(r'^flutter build (?:appbundle|ipa) --release\b')
DART_DEFINE = 'API_BASE_URL'


def _shippable_builds(text: str) -> list[str]:
    """Blocos de comando (multi-linha, até linha sem `\\`) de cada build real."""
    lines = text.splitlines()
    builds: list[str] = []
    i = 0
    while i < len(lines):
        if SHIPPABLE_RELEASE.match(lines[i].strip()):
            window = [lines[i]]
            while window[-1].rstrip().endswith('\\') and i + 1 < len(lines):
                i += 1
                window.append(lines[i])
            builds.append('\n'.join(window))
        i += 1
    return builds


def _deploy_workflows() -> list[pathlib.Path]:
    return sorted(
        p for p in WORKFLOWS.glob('deploy-*.yml') if p.name in
        {'deploy-android.yml', 'deploy-ios.yml'}
    )


def test_deploy_workflows_exist():
    found = {p.name for p in _deploy_workflows()}
    assert found == {'deploy-android.yml', 'deploy-ios.yml'}, found


def test_every_shippable_release_build_passes_api_base_url():
    """T5/T6/T9 — todo build de release publicável passa API_BASE_URL."""
    offenders: list[str] = []
    for wf in sorted(WORKFLOWS.glob('*.yml')):
        text = wf.read_text(encoding='utf-8')
        for cmd in _shippable_builds(text):
            if f'--dart-define={DART_DEFINE}=' not in cmd:
                offenders.append(f'{wf.name}: {cmd.splitlines()[0].strip()}')
    assert not offenders, (
        'Build de release nativo sem --dart-define=API_BASE_URL '
        '(cairia em localhost:5000):\n  ' + '\n  '.join(offenders)
    )


def test_deploy_workflows_declare_api_base_url_owner():
    """Owner da URL = GitHub Variable vars.API_BASE_URL (mesmo do ios_ci.yml)."""
    for wf in _deploy_workflows():
        text = wf.read_text(encoding='utf-8')
        assert 'vars.API_BASE_URL' in text, (
            f'{wf.name}: API_BASE_URL deve vir de vars.API_BASE_URL '
            '(owner operacional), não hardcoded isolado.'
        )
        assert f'--dart-define={DART_DEFINE}=' in text, wf.name


def test_deploy_api_base_url_is_not_localhost():
    """S6 — nenhum workflow de publicação pode apontar o release para localhost."""
    for wf in _deploy_workflows():
        for raw in wf.read_text(encoding='utf-8').splitlines():
            if 'API_BASE_URL' in raw and (
                'localhost' in raw or '127.0.0.1' in raw or '10.0.2.2' in raw
            ):
                raise AssertionError(f'{wf.name}: release aponta para localhost: {raw.strip()}')


def test_ci_ios_still_passes_api_base_url():
    """T8 — CI iOS continua injetando API_BASE_URL."""
    ios_ci = WORKFLOWS / 'ios_ci.yml'
    if not ios_ci.exists():
        return  # repo sem ios_ci dedicado
    assert f'--dart-define={DART_DEFINE}=' in ios_ci.read_text(encoding='utf-8')


def test_ci_android_melos_scripts_pass_api_base_url():
    """T7 — a CI Android usa `melos run build:apk/android`, cujos scripts no
    pubspec carregam API_BASE_URL. Garante que esse caminho não regrediu."""
    text = PUBSPEC.read_text(encoding='utf-8')
    # Isola os scripts build:apk e build:android e exige o define em cada um.
    for script in ('build:apk', 'build:android'):
        idx = text.find(f'{script}:')
        assert idx != -1, f'script melos {script} ausente no pubspec'
        # janela do bloco do script (até o próximo `build:`/fim razoável)
        window = text[idx: idx + 1200]
        assert f'--dart-define={DART_DEFINE}=' in window, (
            f'melos {script} não passa API_BASE_URL'
        )


def test_web_build_stays_same_origin():
    """T10 — build:web NÃO exige API_BASE_URL (mantém same-origin)."""
    text = PUBSPEC.read_text(encoding='utf-8')
    idx = text.find('build:web:')
    assert idx != -1
    window = text[idx: idx + 1200]
    assert f'--dart-define={DART_DEFINE}=' not in window, (
        'build:web não deve forçar API_BASE_URL (web = same-origin).'
    )


# ── EST-V1.6-R1: isolamento de backend por produto ──────────────────────────
import json  # noqa: E402

CI_DIR = REPO_ROOT / 'ci'
GUARD = CI_DIR / 'api_backend_guard.py'
ALLOWLIST = CI_DIR / 'authorized_backend.json'
KNOWN_BACKENDS = {
    'saas': 'epi-controle-app-livamobile-api.onrender.com',
    'corporate': 'epi-controle-app-gupy.onrender.com',
}
# Arquivos que NÃO podem conter o host do OUTRO produto (comandos de build/config).
_BUILD_FILES = (
    [WORKFLOWS / n for n in ('deploy-android.yml', 'deploy-ios.yml', 'ios_ci.yml', 'flutter.yml')]
    + [PUBSPEC, REPO_ROOT / 'flutter' / 'apps' / 'epi_admin' / 'ios' / 'fastlane' / 'Fastfile']
)


def _authorized_host():
    data = json.loads(ALLOWLIST.read_text(encoding='utf-8'))
    return data['authorized_hosts'][0]


def _forbidden_host():
    auth = _authorized_host()
    return KNOWN_BACKENDS['corporate'] if auth == KNOWN_BACKENDS['saas'] else KNOWN_BACKENDS['saas']


def test_guard_and_allowlist_exist():
    assert GUARD.exists(), 'ci/api_backend_guard.py ausente'
    assert ALLOWLIST.exists(), 'ci/authorized_backend.json ausente'
    assert _authorized_host() in KNOWN_BACKENDS.values(), _authorized_host()


def test_no_cross_tenant_host_in_build_or_config():
    """O host do OUTRO produto não pode aparecer em NENHUM arquivo de build/config."""
    forbidden = _forbidden_host()
    offenders = []
    for p in _BUILD_FILES:
        if p.exists() and forbidden in p.read_text(encoding='utf-8'):
            offenders.append(p.name)
    assert not offenders, (
        f'host cross-tenant {forbidden} presente em: {offenders} (deve ser removido)'
    )


def test_release_paths_invoke_guard():
    """Deploy Android/iOS, ios_ci e flutter.yml resolvem via o guard."""
    for n in ('deploy-android.yml', 'deploy-ios.yml', 'ios_ci.yml', 'flutter.yml'):
        text = (WORKFLOWS / n).read_text(encoding='utf-8')
        assert 'api_backend_guard.py' in text, f'{n} não chama o guard de backend'


def test_melos_native_builds_have_no_hardcoded_url():
    """melos build:android/apk/ios não hardcodam URL — são env-driven (fail-closed)."""
    text = PUBSPEC.read_text(encoding='utf-8')
    for host in KNOWN_BACKENDS.values():
        assert host not in text, f'pubspec melos hardcoda {host} (deve ser ${{API_BASE_URL}})'
    # os 3 nativos exigem API_BASE_URL do ambiente
    for script in ('build:android', 'build:apk', 'build:ios'):
        i = text.find(f'{script}:')
        assert i != -1, script
        assert 'API_BASE_URL' in text[i:i + 1400], f'{script} não consome API_BASE_URL'


def test_fastfile_validates_and_passes_define():
    """Fastlane beta/release resolve+valida o backend e passa o define (S8)."""
    ff = REPO_ROOT / 'flutter' / 'apps' / 'epi_admin' / 'ios' / 'fastlane' / 'Fastfile'
    text = ff.read_text(encoding='utf-8')
    assert 'resolve_api_base_url!' in text, 'Fastfile não valida o backend via guard'
    assert '--dart-define=API_BASE_URL' in text, 'Fastfile build sem --dart-define=API_BASE_URL'


def test_deploy_has_no_cross_tenant_fallback():
    """Os deploys não usam `vars.API_BASE_URL || '<url>'` (fallback removido)."""
    for n in ('deploy-android.yml', 'deploy-ios.yml'):
        text = (WORKFLOWS / n).read_text(encoding='utf-8')
        assert 'vars.API_BASE_URL ||' not in text, f'{n} ainda tem fallback cross-tenant'


def test_publication_paths_are_fail_closed():
    """T5/S3 — PUBLICAÇÃO (store) exige a variável: usa `resolve` (fail-closed),
    nunca `resolve-ci`. Sem a variável do operador, o job de publicação falha
    antes do build. Cobre deploy Android/iOS e o Fastlane."""
    fastfile = REPO_ROOT / 'flutter' / 'apps' / 'epi_admin' / 'ios' / 'fastlane' / 'Fastfile'
    for p in (WORKFLOWS / 'deploy-android.yml', WORKFLOWS / 'deploy-ios.yml', fastfile):
        text = p.read_text(encoding='utf-8')
        assert 'api_backend_guard.py' in text, f'{p.name} não chama o guard'
        assert 'resolve-ci' not in text, (
            f'{p.name} é PUBLICAÇÃO: deve usar `resolve` (fail-closed), nunca `resolve-ci`'
        )
        # Invoca o subcomando `resolve` (fail-closed). `resolve-ci` já foi
        # excluído acima, então um `resolve` isolado é necessariamente o
        # fail-closed de publicação.
        assert re.search(r'\bresolve\b', text), (
            f'{p.name} deve invocar o subcomando `resolve` (fail-closed)'
        )


def test_ci_build_paths_use_resolve_ci():
    """CI de build/teste (não publicado) usa `resolve-ci`: sem vars.API_BASE_URL
    cai no backend AUTORIZADO do próprio produto (allowlist), mantendo o CI verde
    sem jamais aceitar backend cruzado/localhost."""
    for n in ('ios_ci.yml', 'flutter.yml'):
        text = (WORKFLOWS / n).read_text(encoding='utf-8')
        assert 'resolve-ci' in text, f'{n} (CI) deveria usar `resolve-ci`'


if __name__ == '__main__':
    fns = [v for k, v in sorted(globals().items()) if k.startswith('test_')]
    failures = 0
    for fn in fns:
        try:
            fn()
            print(f'PASS  {fn.__name__}')
        except AssertionError as exc:
            failures += 1
            print(f'FAIL  {fn.__name__}\n      {exc}')
    print(f'\n{len(fns) - failures}/{len(fns)} passed')
    raise SystemExit(1 if failures else 0)
