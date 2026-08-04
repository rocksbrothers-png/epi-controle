"""Rota GET /api/employees/archived — filtro ?outsourced_only=1 (PR 13,
ADR-0002 §10.4), usado pela aba "Colaboradores Arquivados" do Cadastro de
Colaboradores. Mesma rota da tela geral de arquivados — sem rota nova.
"""

import io
import json
from urllib.parse import urlparse

import modules.employees.routes as routes


class _FakeHandler:
    def __init__(self):
        self.path = '/api/employees/archived'
        self.status = None
        self.wfile = io.BytesIO()

    def send_response(self, status):
        self.status = status

    def send_header(self, *_a, **_k):
        pass

    def end_headers(self):
        pass

    def json(self):
        return json.loads(self.wfile.getvalue().decode('utf-8'))


class _FakeConn:
    def commit(self):
        pass

    def close(self):
        pass


ACTOR = {'id': 1, 'role': 'general_admin', 'company_id': 7}


def _patch_common(monkeypatch, calls):
    monkeypatch.setattr(routes, 'get_connection', _FakeConn)
    monkeypatch.setattr(routes, 'resolve_actor_user_id', lambda *a, **k: 1)
    monkeypatch.setattr(routes, 'authorize_action', lambda *a, **k: ACTOR)
    monkeypatch.setattr(
        routes, 'fetch_archived_employees',
        lambda _c, actor, outsourced_only=False: calls.append(outsourced_only) or [],
    )


def test_default_returns_all_archived_employees(monkeypatch):
    calls = []
    _patch_common(monkeypatch, calls)
    h = _FakeHandler()
    routes.handle_get_archived_employees(h, urlparse('/api/employees/archived'), None, None)
    assert h.status == 200
    assert calls == [False]


def test_outsourced_only_query_param_is_forwarded(monkeypatch):
    calls = []
    _patch_common(monkeypatch, calls)
    h = _FakeHandler()
    routes.handle_get_archived_employees(
        h, urlparse('/api/employees/archived?outsourced_only=1'), None, None,
    )
    assert h.status == 200
    assert calls == [True]


def test_outsourced_only_accepts_true_string(monkeypatch):
    calls = []
    _patch_common(monkeypatch, calls)
    h = _FakeHandler()
    routes.handle_get_archived_employees(
        h, urlparse('/api/employees/archived?outsourced_only=true'), None, None,
    )
    assert calls == [True]


def test_outsourced_only_false_for_other_values(monkeypatch):
    calls = []
    _patch_common(monkeypatch, calls)
    h = _FakeHandler()
    routes.handle_get_archived_employees(
        h, urlparse('/api/employees/archived?outsourced_only=0'), None, None,
    )
    assert calls == [False]
