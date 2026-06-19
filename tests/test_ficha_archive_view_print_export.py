"""Integração: visualizar/imprimir/baixar fichas de EPI arquivadas.

Cobre as correções:
  - handle_get_ficha_archive_html agora chama end_headers() (resposta HTTP válida);
  - action=snapshot_print injeta window.print();
  - action=snapshot_export envia Content-Disposition: attachment;
  - get_ficha_archive_snapshot_by_id usa LEFT JOIN: a ficha arquivada permanece
    acessível mesmo após exclusão do colaborador/unidade (retenção legal).
"""

import sqlite3

import pytest

import modules.ficha.routes as routes
from modules.ficha.service import get_ficha_archive_snapshot_by_id

HTML_DOC = (
    '<!DOCTYPE html>\n<html lang="pt-BR"><head><meta charset="UTF-8"></head>'
    '<body><h1>Ficha de EPI</h1></body></html>'
)


class _NonClosing:
    """Proxy que delega ao sqlite mas ignora close() (conexão :memory: persistente)."""

    def __init__(self, conn):
        self._conn = conn

    def close(self):
        pass

    def __getattr__(self, name):
        return getattr(self._conn, name)


class _FakeWFile:
    def __init__(self):
        self.body = b''

    def write(self, data):
        self.body += data


class _FakeHandler:
    def __init__(self):
        self.client_address = ('10.0.0.1', 1234)
        self.headers = {'User-Agent': 'pytest'}
        self.status = None
        self.sent_headers = {}
        self.end_headers_called = False
        self.wfile = _FakeWFile()

    def send_response(self, code):
        self.status = code

    def send_header(self, key, value):
        self.sent_headers[key] = value

    def end_headers(self):
        self.end_headers_called = True


def _build_db():
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        CREATE TABLE companies (id INTEGER PRIMARY KEY, name TEXT);
        CREATE TABLE units (id INTEGER PRIMARY KEY, company_id INTEGER, name TEXT);
        CREATE TABLE employees (id INTEGER PRIMARY KEY, company_id INTEGER, unit_id INTEGER,
            name TEXT, employee_id_code TEXT, sector TEXT, role_name TEXT);
        CREATE TABLE ficha_epi_snapshots (
            id INTEGER PRIMARY KEY, ficha_period_id INTEGER, company_id INTEGER,
            unit_id INTEGER, employee_id INTEGER, generated_by_user_id INTEGER,
            generated_at TEXT, expires_at TEXT, status TEXT, retention_years INTEGER,
            html_sha256 TEXT, payload_sha256 TEXT, html_content TEXT, snapshot_payload TEXT);
        CREATE TABLE ficha_epi_audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT, actor_user_id INTEGER, actor_name TEXT,
            actor_role TEXT, employee_id INTEGER, employee_name TEXT, unit_id INTEGER,
            company_id INTEGER, action TEXT, ip_address TEXT, user_agent TEXT, accessed_at TEXT);
        INSERT INTO companies VALUES (1, 'ACME');
        INSERT INTO units VALUES (1, 1, 'Unidade Central');
        INSERT INTO employees VALUES (5, 1, 1, 'Maria Silva', 'E-5', 'Operação', 'Operadora');
        """
    )
    conn.execute(
        'INSERT INTO ficha_epi_snapshots '
        '(id, ficha_period_id, company_id, unit_id, employee_id, generated_by_user_id, '
        'generated_at, expires_at, status, retention_years, html_sha256, payload_sha256, '
        'html_content, snapshot_payload) '
        "VALUES (1, 10, 1, 1, 5, 1, '2026-01-01T00:00:00+00:00', '2031-01-01T00:00:00+00:00', "
        "'archived', 5, 'h', 'p', ?, '{}')",
        (HTML_DOC,),
    )
    conn.commit()
    return conn


ACTOR = {'id': 1, 'role': 'general_admin', 'company_id': 1, 'username': 'admin', 'full_name': 'Admin'}


@pytest.fixture()
def patched(monkeypatch):
    conn = _build_db()
    monkeypatch.setattr(routes, 'get_connection', lambda: _NonClosing(conn))
    monkeypatch.setattr(routes, 'authorize_action', lambda connection, uid, perm: dict(ACTOR))
    monkeypatch.setattr(routes, 'resolve_actor_user_id', lambda handler, parsed: 1)
    return conn


class _Parsed:
    def __init__(self, query):
        self.query = query


class _Match:
    def __init__(self, value):
        self._value = value

    def group(self, _n):
        return self._value


def _call(action):
    handler = _FakeHandler()
    routes.handle_get_ficha_archive_html(handler, _Parsed(f'action={action}'), None, _Match('1'))
    return handler


def test_view_returns_valid_http_with_end_headers(patched):
    h = _call('snapshot_view')
    assert h.status == 200
    assert h.end_headers_called is True  # regressão: faltava end_headers()
    assert h.sent_headers['Content-Type'] == 'text/html; charset=utf-8'
    assert int(h.sent_headers['Content-Length']) == len(h.wfile.body)
    assert b'Ficha de EPI' in h.wfile.body
    assert b'window.print()' not in h.wfile.body
    assert 'Content-Disposition' not in h.sent_headers


def test_print_injects_window_print(patched):
    h = _call('snapshot_print')
    assert h.status == 200
    assert h.end_headers_called is True
    assert b'window.print()' in h.wfile.body
    assert b'</body>' in h.wfile.body
    assert int(h.sent_headers['Content-Length']) == len(h.wfile.body)


def test_export_sets_attachment_disposition(patched):
    h = _call('snapshot_export')
    assert h.status == 200
    assert h.end_headers_called is True
    disp = h.sent_headers.get('Content-Disposition', '')
    assert disp.startswith('attachment;')
    assert '.html' in disp
    assert 'Maria' in disp  # nome do colaborador no filename


def test_archive_view_survives_employee_deletion_left_join(patched):
    # Remove o colaborador: com LEFT JOIN a ficha arquivada (autocontida) continua acessível.
    patched.execute('DELETE FROM employees WHERE id = 5')
    patched.commit()
    snapshot = get_ficha_archive_snapshot_by_id(_NonClosing(patched), dict(ACTOR), 1)
    assert snapshot['html_content'] == HTML_DOC
    assert snapshot['employee_name'] is None  # juntada ausente, mas não quebra

    h = _call('snapshot_view')
    assert h.status == 200
    assert b'Ficha de EPI' in h.wfile.body


def test_unknown_snapshot_raises(patched):
    with pytest.raises(ValueError):
        get_ficha_archive_snapshot_by_id(_NonClosing(patched), dict(ACTOR), 999)
