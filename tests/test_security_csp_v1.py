"""SECURITY-CSP-V1 — Content Security Policy aplicada na SPA, por superfície.

Cobre o construtor (core/csp.py) e a integração com o handler (app.py):
- a SPA recebe a política estrita: script-src sem 'unsafe-inline'/'unsafe-eval', e as
  bibliotecas externas liberadas pelo caminho exato, não pelo host;
- CSP_MODE escolhe enforce/report-only; o padrão é enforce fora de produção e
  report-only em produção (não liga política restritiva em produção sem validar);
- Flutter Web e checkout ficam sempre em Report-Only;
- rota que manda a própria CSP (ficha, portal do fornecedor, biblioteca) não recebe a da
  SPA por cima — duas CSPs aplicadas valem pela interseção e quebrariam o script por hash;
- o frontend não tem mais script inline nem handler inline (on*=) — senão a política
  estrita bloquearia funcionalidade legítima.
"""
import base64
import hashlib
import re
from pathlib import Path

import pytest

import app
from core import csp
from modules.purchases import supplier_portal_page

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / 'static'


class _Capture:
    headers = {}

    def __init__(self, path='/'):
        self.path = path
        self.sent_headers = []

    def send_header(self, name, value):
        if str(name).strip().lower() == 'content-security-policy':
            self._route_csp_sent = True
        self.sent_headers.append((name, value))


def _csp_headers(path, monkeypatch, *, mode='enforce', route_csp=None, report_uri=None):
    monkeypatch.setattr(app, 'CSP_SPA_MODE', mode)
    if report_uri is None:
        monkeypatch.delenv('CSP_REPORT_URI', raising=False)
    else:
        monkeypatch.setenv('CSP_REPORT_URI', report_uri)
    handler = _Capture(path)
    if route_csp:
        handler.send_header('Content-Security-Policy', route_csp)
    app.EpiHandler._apply_default_response_headers(handler)
    return [(n, v) for n, v in handler.sent_headers if n.startswith('Content-Security-Policy')]


def _directive(value, name):
    for part in value.split(';'):
        tokens = part.split()
        if tokens and tokens[0] == name:
            return tokens[1:]
    return None


def test_spa_policy_has_no_unsafe_script_sources():
    header, value = csp.policy_for_path('/', mode=csp.ENFORCE)
    assert header == 'Content-Security-Policy'
    script = _directive(value, 'script-src')
    assert "'unsafe-inline'" not in script and "'unsafe-eval'" not in script
    assert not any(src in ('*', 'https:', 'http:', 'https://unpkg.com', 'https://cdn.jsdelivr.net') for src in script)
    assert set(csp.SPA_EXTERNAL_SCRIPTS) <= set(script)
    assert _directive(value, 'object-src') == ["'none'"]
    assert _directive(value, 'base-uri') == ["'self'"]
    assert _directive(value, 'frame-ancestors') == ["'self'"]
    assert _directive(value, 'connect-src') == ["'self'"]
    # Logotipos, fotos de EPI e assinaturas (data:) e QR codes.
    assert {"'self'", 'data:', 'blob:', 'https://api.qrserver.com'} == set(_directive(value, 'img-src'))


def test_spa_external_scripts_match_what_the_frontend_loads():
    index = (STATIC / 'index.html').read_text(encoding='utf-8')
    app_js = (STATIC / 'app.js').read_text(encoding='utf-8')
    loaded = set(re.findall(r'<script\b[^>]*\bsrc="(https://[^"]+)"', index))
    loaded |= set(re.findall(r"['\"](https://(?:unpkg\.com|cdn\.jsdelivr\.net)/[^'\"]+\.js)['\"]", app_js))
    assert loaded == set(csp.SPA_EXTERNAL_SCRIPTS)


@pytest.mark.parametrize('env_value,production,expected', [
    (None, False, 'enforce'), ('', False, 'enforce'), (None, True, 'report-only'),
    ('enforce', True, 'enforce'), ('ENFORCE', True, 'enforce'), ('report-only', False, 'report-only'),
    ('desligar', True, 'report-only'), ('desligar', False, 'enforce'),
])
def test_spa_mode_defaults(env_value, production, expected):
    assert csp.spa_mode(env_value, production) == expected


def test_report_only_mode_uses_the_same_strict_policy():
    enforce = csp.policy_for_path('/', mode=csp.ENFORCE)
    report = csp.policy_for_path('/', mode=csp.REPORT_ONLY)
    assert report[0] == 'Content-Security-Policy-Report-Only'
    assert report[1] == enforce[1]


@pytest.mark.parametrize('path', ['/app', '/app/', '/app/main.dart.js', '/flutter_web/x', '/pagamento',
                                  '/pagamento.html', '/checkout'])
def test_flutter_and_checkout_stay_report_only(path, monkeypatch):
    assert [n for n, _ in _csp_headers(path, monkeypatch)] == ['Content-Security-Policy-Report-Only']


@pytest.mark.parametrize('path', ['/', '/index.html', '/legacy/', '/api/bootstrap', '/js/app.js', '/apps'])
def test_spa_paths_get_the_enforced_policy(path, monkeypatch):
    headers = _csp_headers(path, monkeypatch)
    assert headers == [('Content-Security-Policy', csp.serialize(csp.SPA_DIRECTIVES))]


def test_production_default_is_report_only(monkeypatch):
    headers = _csp_headers('/', monkeypatch, mode='report-only')
    assert [n for n, _ in headers] == ['Content-Security-Policy-Report-Only']


def test_route_policy_is_not_stacked_with_the_spa_policy(monkeypatch):
    from modules.ficha.routes import FICHA_HTML_CSP

    headers = _csp_headers('/api/employees/1/ficha', monkeypatch, route_csp=FICHA_HTML_CSP)
    assert headers == [('Content-Security-Policy', FICHA_HTML_CSP)]


def test_library_response_keeps_only_its_own_policy(monkeypatch):
    headers = _csp_headers('/api/safety-library/1/file', monkeypatch)
    assert headers == [('Content-Security-Policy', "default-src 'none'; frame-ancestors 'none'")]


def test_route_csp_flag_is_reset_for_the_next_response():
    handler = object.__new__(app.EpiHandler)
    handler._route_csp_sent = True
    handler.request_version = 'HTTP/1.1'
    handler._headers_buffer = []
    handler.requestline = 'GET / HTTP/1.1'
    handler.client_address = ('127.0.0.1', 0)
    handler.command = 'GET'
    handler.log_request = lambda *a, **k: None
    app.EpiHandler.send_response(handler, 200)
    assert handler._route_csp_sent is False
    app.EpiHandler.send_header(handler, 'content-security-policy', "default-src 'none'")
    assert handler._route_csp_sent is True


@pytest.mark.parametrize('report_uri,expected', [
    ('/api/csp-report', '/api/csp-report'),
    ('https://csp.example.com/r', 'https://csp.example.com/r'),
    ('/x; script-src *', None),
    ('/x y', None),
    ('javascript:alert(1)', None),
])
def test_report_uri_is_appended_only_when_safe(report_uri, expected, monkeypatch):
    [(_, value)] = _csp_headers('/', monkeypatch, report_uri=report_uri)
    if expected:
        assert value.endswith(f'; report-uri {expected}')
    else:
        assert 'report-uri' not in value
        assert value == csp.serialize(csp.SPA_DIRECTIVES)


def test_supplier_portal_policy_allows_only_its_own_inline_script():
    html = supplier_portal_page.PORTAL_PAGE_HTML
    # O hash cobre exatamente os bytes entre <script> e </script> da página servida.
    start = html.index('<script>') + len('<script>')
    body = html[start:html.index('</script>', start)]
    digest = base64.b64encode(hashlib.sha256(body.encode('utf-8')).digest()).decode('ascii')
    policy = supplier_portal_page.PORTAL_PAGE_CSP
    assert _directive(policy, 'script-src') == [f"'sha256-{digest}'"]
    assert _directive(policy, 'default-src') == ["'none'"]
    assert _directive(policy, 'connect-src') == ["'self'"]
    assert html.lower().count('<script') == 1
    assert not re.search(r'\son[a-z]+\s*=', html.replace("addEventListener", ''))


def _frontend_sources():
    yield STATIC / 'index.html'
    yield STATIC / 'app.js'
    for folder in ('js', 'views', 'fragments'):
        for path in sorted((STATIC / folder).rglob('*')):
            if path.suffix in ('.js', '.html') and '/test/' not in path.as_posix():
                yield path


INLINE_HANDLER = re.compile(r'''<[a-zA-Z][^<>]*\son[a-z]{3,}\s*=\s*["'\\]''')


def test_frontend_has_no_inline_event_handlers():
    offenders = []
    for path in _frontend_sources():
        for number, line in enumerate(path.read_text(encoding='utf-8').splitlines(), 1):
            if INLINE_HANDLER.search(line):
                offenders.append(f'{path.relative_to(STATIC)}:{number}: {line.strip()[:100]}')
    assert offenders == []


def test_index_has_no_inline_script_blocks():
    index = (STATIC / 'index.html').read_text(encoding='utf-8')
    assert re.findall(r'<script\b(?![^>]*\bsrc=)[^>]*>', index, re.I) == []
    assert '/js/boot/theme-preference.js?v=' in index


def test_inline_handler_guard_detects_handlers():
    for bad in ('<button onclick="x()">', "<form onsubmit='return false'>", '`<img src=x onerror="a()">`',
                '<td><button class="b" onclick=\\"go()\\">'):
        assert INLINE_HANDLER.search(bad), bad
    for ok in ('btn.onclick = () => go();', '<button data-action="x">', 'el.addEventListener("click", f)'):
        assert not INLINE_HANDLER.search(ok), ok
