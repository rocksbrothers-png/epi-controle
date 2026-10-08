"""Isolamento de backend por produto (EST-V1.6-R1).

Mesmo arquivo de teste nos DOIS repositórios (contrato idêntico); o comportamento
difere pelo DADO em `ci/authorized_backend.json`. Prova detecção de BACKEND
CRUZADO — não apenas presença de `--dart-define` ou ausência de `localhost`.

Roda sob pytest e como script: `python3 tests/test_api_backend_guard.py`.
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
GUARD = REPO_ROOT / 'ci' / 'api_backend_guard.py'
ALLOWLIST = REPO_ROOT / 'ci' / 'authorized_backend.json'

# Os dois backends de produção conhecidos (auditoria EST-V1.6-I).
SAAS = 'https://epi-controle-app-livamobile-api.onrender.com'
CORPORATE = 'https://epi-controle-app-gupy.onrender.com'


def _allow():
    return json.loads(ALLOWLIST.read_text(encoding='utf-8'))


def _authorized_url():
    return _allow()['api_base_url']


def _forbidden_url():
    """A URL do OUTRO produto (cross-backend)."""
    auth = _authorized_url()
    return CORPORATE if auth == SAAS else SAAS


def _resolve(value):
    return subprocess.run(
        [sys.executable, str(GUARD), 'resolve', value],
        capture_output=True, text=True,
    )


def _validate(value):
    return subprocess.run(
        [sys.executable, str(GUARD), 'validate', value],
        capture_output=True, text=True,
    )


def test_allowlist_is_one_of_the_known_products():
    assert _authorized_url() in (SAAS, CORPORATE), _authorized_url()


# Identidade de produto ↔ backend ↔ app_id, ancorada na VERDADE do repositório
# (applicationId do Android). Impede apontar um produto para o backend do outro
# só editando a allowlist (sabotagens S1/S2).
PRODUCT_TRUTH = {
    'saas': {
        'host': 'epi-controle-app-livamobile-api.onrender.com',
        'app_id': 'com.livamobile.epicontrole',
    },
    'corporate': {
        'host': 'epi-controle-app-gupy.onrender.com',
        'app_id': 'com.rocksbrothers.epicontrole',
    },
}


def test_allowlist_matches_product_identity():
    import urllib.parse
    data = _allow()
    product = data.get('product')
    assert product in PRODUCT_TRUTH, product
    truth = PRODUCT_TRUTH[product]
    assert data['authorized_hosts'] == [truth['host']], data['authorized_hosts']
    assert urllib.parse.urlsplit(data['api_base_url']).hostname == truth['host']
    assert data.get('app_id') == truth['app_id']


def test_allowlist_app_id_matches_real_android_application_id():
    import re
    gradle = (REPO_ROOT / 'flutter' / 'apps' / 'epi_admin' / 'android' / 'app' / 'build.gradle').read_text(encoding='utf-8')
    # a applicationId de produção (ignora applicationIdSuffix de debug)
    m = re.search(r'applicationId\s+"([^"]+)"', gradle)
    assert m, 'applicationId não encontrado em build.gradle'
    assert _allow()['app_id'] == m.group(1), (
        f"allowlist app_id {_allow()['app_id']} != android applicationId {m.group(1)}"
    )


def test_T_own_backend_accepted():
    r = _validate(_authorized_url())
    assert r.returncode == 0, r.stderr
    rr = _resolve(_authorized_url())
    assert rr.returncode == 0 and rr.stdout.strip() == _authorized_url(), rr.stderr


def test_T_cross_backend_rejected():
    """SaaS rejeita Corporate / Corporate rejeita SaaS (o cerne do BLOCKER)."""
    r = _validate(_forbidden_url())
    assert r.returncode != 0, 'cross-backend deveria ser REJEITADO'
    rr = _resolve(_forbidden_url())
    assert rr.returncode != 0, 'resolve com backend cruzado deveria FALHAR'


def test_T_empty_fails():
    assert _validate('').returncode != 0


def test_T_resolve_empty_uses_own_authorized_backend():
    """input vazio → backend do PRÓPRIO produto (nunca cross-tenant, nunca localhost)."""
    rr = _resolve('')
    assert rr.returncode == 0 and rr.stdout.strip() == _authorized_url(), rr.stderr


def test_T_whitespace_fails():
    assert _validate('   ').returncode != 0
    # whitespace ao redor de uma URL válida também é rejeitado
    assert _validate(f' {_authorized_url()} ').returncode != 0


def test_T_http_and_loopback_fail():
    for bad in (
        'http://epi-controle-app-livamobile-api.onrender.com',  # http
        'http://localhost:5000',
        'https://localhost:5000',
        'http://127.0.0.1:8080',
        'https://10.0.2.2',
        'https://0.0.0.0',
    ):
        assert _validate(bad).returncode != 0, bad


def test_T_lookalike_host_fails():
    auth = _authorized_url().split('://', 1)[1]
    for bad in (
        f'https://{auth}.evil.com',           # sufixo enganoso
        f'https://evil-{auth}',               # prefixo enganoso
        f'https://{auth}x',                   # substring
    ):
        assert _validate(bad).returncode != 0, bad


def test_T_external_https_fails():
    assert _validate('https://evil.example.com').returncode != 0


def test_T_userinfo_and_fragment_fail():
    host = _authorized_url().split('://', 1)[1]
    assert _validate(f'https://user:pass@{host}').returncode != 0
    assert _validate(f'{_authorized_url()}#frag').returncode != 0


if __name__ == '__main__':
    fns = [v for k, v in sorted(globals().items()) if k.startswith('test_')]
    fails = 0
    for fn in fns:
        try:
            fn(); print(f'PASS  {fn.__name__}')
        except AssertionError as e:
            fails += 1; print(f'FAIL  {fn.__name__}: {e}')
    print(f'\n{len(fns)-fails}/{len(fns)} passed')
    raise SystemExit(1 if fails else 0)
