"""SECURITY-CSP-REPORT-REDACTION-V1 — /api/csp-report não registra tokens nem credenciais.

Antes, `_handle_csp_report` gravava `document-uri`, `blocked-uri` e `source-file` como vieram:
o `?employee_token=` do portal do colaborador e o `/fornecedor/<token>` do portal do fornecedor
iam em claro para o log `security.csp_report`. Agora só campos sanitizados por
`core.csp_report` chegam ao log. Os tokens são fictícios.
"""
import http.client
import json
import threading
from http.server import ThreadingHTTPServer

import pytest

import app
from core import csp_report
from core.rate_limit import RateLimiter

SECRETS = ('qa-qa-qa-qa-qa-qa', 'T0K3N-QA', 'senha-qa', 'tokfornecedorQA1234567890', 'tokapiQA1234567890abcd',
           'frag-segredo-qa', 'amostra-secreta-qa')


@pytest.mark.parametrize('raw,expected', [
    ('https://epi.test/?employee_token=qa-qa-qa-qa-qa-qa&lang=pt', 'https://epi.test/?…'),
    ('https://epi.test/app?code=qa-qa-qa-qa-qa-qa#frag-segredo-qa', 'https://epi.test/app?…#…'),
    ('https://evil.test/x.js?token=T0K3N-QA', 'https://evil.test/x.js?…'),
    ('https://qa:senha-qa@epi.test/a', 'https://epi.test/a'),
    ('https://epi.test/fornecedor/curto', 'https://epi.test/fornecedor/***'),
    ('https://epi.test/FORNECEDOR/tokfornecedorQA1234567890', 'https://epi.test/FORNECEDOR/***'),
    ('https://epi.test/api/portal/supplier/tokapiQA1234567890abcd/quote', 'https://epi.test/api/portal/supplier/***/quote'),
    ('https://epi.test/x/abcdefghijklmnopqrstuvwxyz0123456789/y', 'https://epi.test/x/***/y'),
    ('https://epi.test/js/views/employee-portal.js', 'https://epi.test/js/views/employee-portal.js'),
    ('https://unpkg.com/htmx.org@1.9.12', 'https://unpkg.com/htmx.org@1.9.12'),
    ('inline', 'inline'), ('eval', 'eval'), ('wasm-eval', 'wasm-eval'),
    ('data:text/html;base64,PHNjcmlwdD4=', 'data:'),
    ('blob:https://epi.test/0a1b2c3d-4e5f-6789-abcd-ef0123456789', 'blob:https://epi.test/***'),
    ('about:blank', 'about:'), ('javascript:alert(document.cookie)', 'javascript:'),
    ('http://[::1]:8080/p?q=1', 'http://[::1]:8080/p?…'),
    ('https://epi.test:99999/x', csp_report.INVALID),
    ('', ''), (None, ''), ('\r\n', ''),
])
def test_sanitize_url(raw, expected):
    assert csp_report.sanitize_url(raw) == expected


def test_sanitize_url_never_raises_and_clips():
    hostile = ['https://' + 'a' * 5000, '%' * 300, 'https://[zz/', 'http://h/' + '/'.join(['x'] * 2000), 12345, {'a': 1}]
    for value in hostile:
        result = csp_report.sanitize_url(value)
        assert isinstance(result, str) and len(result) <= csp_report.MAX_FIELD_CHARS + 1


def _secret_free(obj):
    text = json.dumps(obj, ensure_ascii=False)
    return not any(secret in text for secret in SECRETS)


def test_parse_legacy_report_uri_format():
    body = {'csp-report': {
        'document-uri': 'https://epi.test/?employee_token=qa-qa-qa-qa-qa-qa',
        'referrer': 'https://epi.test/fornecedor/tokfornecedorQA1234567890',
        'violated-directive': "script-src-elem 'self'", 'effective-directive': 'script-src-elem',
        'blocked-uri': 'https://evil.test/x.js?token=T0K3N-QA', 'source-file': 'https://epi.test/app.js',
        'line-number': 12, 'column-number': '7', 'status-code': 200, 'disposition': 'report',
        'script-sample': 'amostra-secreta-qa', 'original-policy': "default-src 'self'"}}
    [fields] = csp_report.parse_reports(json.dumps(body).encode())
    assert fields == {
        'document_uri': 'https://epi.test/?…', 'blocked_uri': 'https://evil.test/x.js?…',
        'source_file': 'https://epi.test/app.js', 'referrer': 'https://epi.test/fornecedor/***',
        'violated_directive': 'script-src-elem', 'disposition': 'report', 'line_number': '12',
        'column_number': '7', 'status_code': '200'}
    assert _secret_free(fields)


def test_parse_plain_object_and_reporting_api_formats():
    plain = csp_report.parse_reports(json.dumps({'document-uri': 'https://epi.test/?token=T0K3N-QA',
                                                 'violated-directive': 'img-src', 'blocked-uri': 'data'}).encode())
    assert plain == [dict(document_uri='https://epi.test/?…', blocked_uri='data', source_file='', referrer='',
                          violated_directive='img-src', disposition='', line_number='', column_number='', status_code='')]
    reporting = [
        {'type': 'csp-violation', 'body': {'documentURL': 'https://epi.test/?employee_token=qa-qa-qa-qa-qa-qa',
                                            'blockedURL': 'inline', 'effectiveDirective': 'script-src-elem',
                                            'disposition': 'enforce', 'lineNumber': 3, 'sample': 'amostra-secreta-qa'}},
        {'type': 'deprecation', 'body': {'message': 'ignorado'}},
    ] + [{'type': 'csp-violation', 'body': {'documentURL': 'https://epi.test/'}}] * 30
    parsed = csp_report.parse_reports(json.dumps(reporting).encode())
    assert parsed[0]['document_uri'] == 'https://epi.test/?…' and parsed[0]['blocked_uri'] == 'inline'
    assert parsed[0]['disposition'] == 'enforce' and parsed[0]['line_number'] == '3'
    assert len(parsed) == csp_report.MAX_REPORTS_PER_REQUEST - 1  # 10 itens lidos, 1 não é CSP
    assert _secret_free(parsed)


@pytest.mark.parametrize('raw', [b'', b'nao-json{', b'null', b'5', b'"texto"', b'{"csp-report": 5}', b'[' * 5000,
                                 '{"document-uri": "\udcff"}'.encode('utf-8', 'surrogatepass'), b'\xff\xfe'])
def test_parse_malformed_bodies(raw):
    assert csp_report.parse_reports(raw) == []


def test_non_url_fields_only_accept_expected_shapes():
    [fields] = csp_report.parse_reports(json.dumps({'csp-report': {
        'violated-directive': 'script-src\nFAKE LOG T0K3N-QA', 'line-number': '12; drop', 'status-code': True,
        'disposition': 'qualquer', 'document-uri': 'https://epi.test/'}}).encode())
    assert fields['violated_directive'] == csp_report.INVALID
    assert fields['line_number'] == '' and fields['status_code'] == '' and fields['disposition'] == ''
    assert _secret_free(fields)


@pytest.fixture()
def server(monkeypatch):
    logged = []
    monkeypatch.setattr(app, 'structured_log', lambda level, event, **fields: logged.append((level, event, fields)))
    monkeypatch.setattr(csp_report, 'csp_report_limiter', RateLimiter(max_calls=120, period_seconds=60))
    httpd = ThreadingHTTPServer(('127.0.0.1', 0), app.EpiHandler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()

    def post(body, content_type='application/csp-report', extra_headers=None):
        conn = http.client.HTTPConnection('127.0.0.1', httpd.server_address[1], timeout=10)
        headers = {'Content-Type': content_type, **(extra_headers or {})}
        conn.request('POST', '/api/csp-report', body=body, headers=headers)
        response = conn.getresponse()
        response.read()
        conn.close()
        return response.status

    yield post, logged, monkeypatch
    httpd.shutdown()
    httpd.server_close()


def _csp_logs(logged):
    return [fields for level, event, fields in logged if event == 'security.csp_report']


def test_http_endpoint_logs_only_sanitized_fields(server):
    post, logged, _ = server
    body = json.dumps({'csp-report': {
        'document-uri': 'https://epi.test/?employee_token=qa-qa-qa-qa-qa-qa&lang=pt',
        'blocked-uri': 'https://epi.test/api/portal/supplier/tokapiQA1234567890abcd',
        'source-file': 'https://qa:senha-qa@epi.test/fornecedor/tokfornecedorQA1234567890#frag-segredo-qa',
        'effective-directive': 'script-src-elem', 'line-number': 4, 'script-sample': 'amostra-secreta-qa'}})
    assert post(body) == 204
    [fields] = _csp_logs(logged)
    assert fields['document_uri'] == 'https://epi.test/?…'
    assert fields['blocked_uri'] == 'https://epi.test/api/portal/supplier/***'
    assert fields['source_file'] == 'https://epi.test/fornecedor/***#…'
    assert fields['violated_directive'] == 'script-src-elem' and fields['line_number'] == '4'
    assert all(not any(secret in json.dumps(entry, ensure_ascii=False) for secret in SECRETS) for entry in logged)


def test_http_endpoint_reporting_api_and_malformed(server):
    post, logged, _ = server
    reports = [{'type': 'csp-violation', 'body': {'documentURL': 'https://epi.test/?token=T0K3N-QA',
                                                   'blockedURL': 'eval', 'effectiveDirective': 'script-src'}}]
    assert post(json.dumps(reports), 'application/reports+json') == 204
    assert post('nao-json{') == 204
    assert post('') == 204
    assert [f['blocked_uri'] for f in _csp_logs(logged)] == ['eval']
    assert all(not any(secret in json.dumps(entry, ensure_ascii=False) for secret in SECRETS) for entry in logged)


def test_http_endpoint_keeps_64k_cap(server):
    post, logged, _ = server
    big = json.dumps({'csp-report': {'document-uri': 'https://epi.test/?employee_token=qa-qa-qa-qa-qa-qa',
                                     'padding': 'A' * 200_000}})
    assert post(big) == 204  # só os primeiros 64 KiB são lidos: JSON incompleto, nada registrado
    assert _csp_logs(logged) == []


def test_http_endpoint_rate_limited(server):
    post, logged, monkeypatch = server
    monkeypatch.setattr(csp_report, 'csp_report_limiter', RateLimiter(max_calls=3, period_seconds=60))
    body = json.dumps({'csp-report': {'document-uri': 'https://epi.test/', 'effective-directive': 'img-src'}})
    statuses = [post(body) for _ in range(6)]
    assert statuses == [204, 204, 204, 429, 429, 429]
    assert len(_csp_logs(logged)) == 3


def test_handler_does_not_need_database_bootstrap(server, monkeypatch):
    post, logged, _ = server
    monkeypatch.setattr(app.EpiHandler, '_require_bootstrap_ready', lambda self, path: False)
    assert post(json.dumps({'csp-report': {'document-uri': 'https://epi.test/'}})) == 204


# ── Rodada da auditoria independente (P3) ────────────────────────────────────

def test_nested_blob_is_flat_and_clipped():
    result = csp_report.sanitize_url('blob:' * 13000 + 'https://epi.test/x?q=qa-qa-qa-qa-qa-qa')
    assert result == 'blob:https://epi.test/x?…'
    long_path = 'blob:https://epi.test/' + '/'.join(['abc'] * 400)
    assert len(csp_report.sanitize_url(long_path)) <= csp_report.MAX_FIELD_CHARS + 1


@pytest.mark.parametrize('raw,expected', [
    ('https://epi.test/fornecedor\\tokfornecedorQA1234567890', 'https://epi.test/fornecedor/***'),
    ('https://epi.test/%66ornecedor/curto', 'https://epi.test/%66ornecedor/***'),
    ('fornecedor/curto', 'fornecedor/***'),
    ('https://epi.test/%74%6f%6b%51%41aaaaaaaaaaaaaaaaaaaa', 'https://epi.test/***'),
])
def test_portal_token_variants_are_masked(raw, expected):
    assert csp_report.sanitize_url(raw) == expected


def test_unicode_line_separators_never_reach_the_log():
    result = csp_report.sanitize_url('https://epi.test/a b c\u0085d\x1be')
    assert result == 'https://epi.test/a b c d e'


def test_rate_limit_counts_logged_reports(server):
    post, logged, monkeypatch = server
    monkeypatch.setattr(csp_report, 'csp_report_limiter', RateLimiter(max_calls=3, period_seconds=60))
    batch = [{'type': 'csp-violation', 'body': {'documentURL': 'https://epi.test/', 'effectiveDirective': 'img-src'}}] * 10
    assert post(json.dumps(batch), 'application/reports+json') == 204
    assert len(_csp_logs(logged)) == 3  # 10 relatórios numa requisição: só 3 vagas
    assert post(json.dumps(batch), 'application/reports+json') == 429
    assert len(_csp_logs(logged)) == 3
