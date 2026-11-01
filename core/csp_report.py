"""Relatórios de violação de CSP: leitura tolerante e sanitização antes do log (SECURITY-CSP-REPORT-REDACTION-V1).

O endpoint `/api/csp-report` é público por necessidade (o navegador envia sem credencial) e o
conteúdo do relatório é controlado pelo cliente. As URLs de um relatório (`document-uri`,
`blocked-uri`, `source-file`, `referrer`) carregam o endereço completo da página — inclusive o
`?employee_token=` do portal do colaborador e o `/fornecedor/<token>` do portal do fornecedor.

Regras aplicadas a TODO campo de URL antes do log:
- query e fragmento são descartados por inteiro (só fica o marcador `?…`/`#…`): nenhum nome de
  parâmetro precisa estar numa lista para não vazar;
- usuário/senha embutidos (`https://u:p@host`) são removidos;
- segmentos de caminho que identificam um portal por token, e qualquer segmento longo com cara de
  token, viram `***`;
- `data:`/`blob:` ficam só com o esquema (e a origem, no `blob:`); palavras-chave da CSP
  (`inline`, `eval`, …) passam como estão.
Campos que não são URL só passam se tiverem o formato esperado (diretiva, número, disposição).
`script-sample`/`sample` e `original-policy` nunca são registrados.

Formatos aceitos: `{"csp-report": {...}}` (report-uri, `application/csp-report`), o mesmo objeto
sem o envelope, e a Reporting API (`application/reports+json`: lista de `{"type": "csp-violation",
"body": {...}}`), até `MAX_REPORTS_PER_REQUEST` itens por requisição.
"""
from __future__ import annotations

import json
import re
from urllib.parse import urlsplit

from core.rate_limit import RateLimiter

MAX_BODY_BYTES = 64 * 1024
MAX_REPORTS_PER_REQUEST = 10
MAX_FIELD_CHARS = 240

# Teto de relatórios por chave de origem (`core.rate_limit.get_client_ip`). Atrás de proxy com
# TRUSTED_PROXY_HOPS=0 a chave é o IP do proxy e o limite vira um teto global — que é o objetivo:
# impedir que alguém inunde o log de segurança. Relatórios legítimos são poucos por página.
# Instância própria (core/rate_limit.py tem digesto fixado e não muda nesta fatia).
csp_report_limiter = RateLimiter(max_calls=120, period_seconds=60)

QUERY_MARKER = '?…'
FRAGMENT_MARKER = '#…'
INVALID = '[inválido]'

# Rotas cujo segmento seguinte é um token de acesso (portal do fornecedor).
_TOKEN_PATH_PREFIXES = (('fornecedor',), ('api', 'portal', 'supplier'))
# Segmento "com cara de token": longo e só com caracteres de token urlsafe/hex.
_TOKENISH_SEGMENT = re.compile(r'^[A-Za-z0-9_\-.~%]{20,}$')
_KEYWORD = re.compile(r'^[a-z][a-z0-9-]{0,39}$')
_DIRECTIVE = re.compile(r'^[a-z][a-z0-9-]{0,39}$')

# Nomes dos campos nos dois formatos (report-uri legado e Reporting API).
_URL_FIELDS = {
    'document_uri': ('document-uri', 'documentURL'),
    'blocked_uri': ('blocked-uri', 'blockedURL'),
    'source_file': ('source-file', 'sourceFile'),
    'referrer': ('referrer',),
}


def _first(report, names):
    for name in names:
        if name in report:
            return report.get(name)
    return None


def _clip(text):
    return text if len(text) <= MAX_FIELD_CHARS else text[:MAX_FIELD_CHARS] + '…'


def _sanitize_path(path):
    segments = path.split('/')
    lowered = [segment.lower() for segment in segments]
    for prefix in _TOKEN_PATH_PREFIXES:
        size = len(prefix)
        for start in range(1, len(segments) - size):
            if tuple(lowered[start:start + size]) == prefix and segments[start + size]:
                segments[start + size] = '***'
    return '/'.join('***' if _TOKENISH_SEGMENT.match(segment) else segment for segment in segments)


def sanitize_url(value):
    """URL de relatório → origem + caminho sem query/fragmento/credenciais/tokens. Nunca levanta."""
    if value is None:
        return ''
    text = str(value).replace('\r', ' ').replace('\n', ' ').strip()
    if not text:
        return ''
    try:
        if _KEYWORD.match(text):  # inline, eval, self, data, blob, wasm-eval, trusted-types-…
            return text
        lowered = text.lower()
        if lowered.startswith('data:'):
            return 'data:'
        if lowered.startswith('blob:'):
            inner = sanitize_url(text[5:])
            return 'blob:' + (inner if inner not in (INVALID, '') else '')
        parts = urlsplit(text)
        scheme = parts.scheme.lower()
        if parts.netloc:
            host = parts.hostname or ''
            if ':' in host:  # IPv6
                host = f'[{host}]'
            try:
                port = parts.port
            except ValueError:
                return INVALID
            netloc = host + (f':{port}' if port else '')
            if not re.fullmatch(r'[A-Za-z0-9.\-\[\]:]*', netloc):
                return INVALID
            prefix = f'{scheme}://{netloc}' if scheme else f'//{netloc}'
        elif scheme and not parts.path.startswith('/'):
            # about:blank, chrome-extension sem host etc.: só o esquema.
            return f'{scheme}:'
        else:
            prefix = f'{scheme}:' if scheme else ''
        path = _sanitize_path(parts.path)
        result = prefix + path
        if parts.query:
            result += QUERY_MARKER
        if parts.fragment:
            result += FRAGMENT_MARKER
        return _clip(result)
    except Exception:  # noqa: BLE001 — entrada hostil: nunca propaga nem ecoa o valor
        return INVALID


def _directive(value):
    text = str(value or '').strip().lower().split(' ', 1)[0]
    return text if _DIRECTIVE.match(text) else (INVALID if text else '')


def _integer(value):
    if isinstance(value, bool):
        return ''
    if isinstance(value, int) and 0 <= value <= 10_000_000:
        return str(value)
    if isinstance(value, str) and value.isdigit() and len(value) <= 8:
        return value
    return ''


def _disposition(value):
    text = str(value or '').strip().lower()
    return text if text in ('enforce', 'report') else ''


def sanitize_report(report):
    """Dicionário de um relatório (qualquer formato aceito) → campos seguros para o log."""
    if not isinstance(report, dict):
        return None
    fields = {key: sanitize_url(_first(report, names)) for key, names in _URL_FIELDS.items()}
    fields['violated_directive'] = _directive(
        _first(report, ('effective-directive', 'effectiveDirective', 'violated-directive')))
    fields['disposition'] = _disposition(report.get('disposition'))
    fields['line_number'] = _integer(_first(report, ('line-number', 'lineNumber')))
    fields['column_number'] = _integer(_first(report, ('column-number', 'columnNumber')))
    fields['status_code'] = _integer(_first(report, ('status-code', 'statusCode')))
    return fields


def parse_reports(raw):
    """Bytes do corpo → lista de relatórios sanitizados (vazia se nada for utilizável). Nunca levanta."""
    try:
        payload = json.loads(raw.decode('utf-8') or 'null')
    except (UnicodeDecodeError, ValueError, RecursionError):
        return []
    candidates = []
    if isinstance(payload, list):  # Reporting API
        for item in payload[:MAX_REPORTS_PER_REQUEST]:
            if isinstance(item, dict) and item.get('type') == 'csp-violation' and isinstance(item.get('body'), dict):
                candidates.append(item['body'])
    elif isinstance(payload, dict):
        inner = payload.get('csp-report')
        candidates.append(inner if isinstance(inner, dict) else payload)
    reports = []
    for candidate in candidates:
        fields = sanitize_report(candidate)
        if fields and any(fields.values()):
            reports.append(fields)
    return reports
