"""Contrato de API: envelope {success,data,message} (aditivo) + /api/auth/me e
alias /api/auth/login. Fase 2 do plano FE/BE.
"""

import io
import json
from urllib.parse import urlparse

from epi_backend.http_utils import send_api_response
import modules.auth.routes as auth_routes


class _FakeHandler:
    def __init__(self, path='/api/test'):
        self.path = path
        self.command = 'GET'
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


# ── send_api_response ─────────────────────────────────────────────────────────

def test_success_envelope_shape():
    h = _FakeHandler()
    send_api_response(h, 200, data={'x': 1}, message='ok')
    body = h.json()
    assert h.status == 200
    assert body['success'] is True and body['ok'] is True  # ok mantido p/ compat
    assert body['data'] == {'x': 1}
    assert body['message'] == 'ok'


def test_success_defaults_empty_data():
    h = _FakeHandler()
    send_api_response(h, 201)
    body = h.json()
    assert body['success'] is True and body['data'] == {} and body['message'] == ''


def test_error_envelope_shape():
    h = _FakeHandler()
    send_api_response(h, 400, error={'code': 'VALIDATION_ERROR', 'message': 'inválido'})
    body = h.json()
    assert h.status == 400
    assert body['success'] is False and body['ok'] is False
    assert body['error']['code'] == 'VALIDATION_ERROR'
    assert 'data' not in body


def test_extra_fields_merged():
    h = _FakeHandler()
    send_api_response(h, 200, data={}, extra={'token': 'abc'})
    assert h.json()['token'] == 'abc'


# ── /api/auth/me ──────────────────────────────────────────────────────────────

def test_auth_me_returns_user_and_permissions(monkeypatch):
    actor = {'id': 9, 'role': 'general_admin', 'company_id': 1, 'full_name': 'Jeff', 'password': 'segredo'}
    monkeypatch.setattr(auth_routes, 'get_connection', lambda: type('C', (), {'close': lambda self: None})())
    monkeypatch.setattr(auth_routes, 'resolve_actor_user_id', lambda *a, **k: 9)
    # `**_k` porque `/api/auth/me` passa `allow_password_change_pending=True`:
    # é a única rota que atravessa o bloqueio de senha temporária (#909).
    monkeypatch.setattr(auth_routes, 'require_actor', lambda _c, _id, **_k: actor)

    h = _FakeHandler('/api/auth/me')
    auth_routes.handle_get_auth_me(h, urlparse('/api/auth/me?actor_user_id=9'), None, None)
    body = h.json()
    assert h.status == 200 and body['success'] is True
    assert body['data']['user']['id'] == 9
    assert 'password' not in body['data']['user']          # senha nunca exposta
    assert isinstance(body['data']['permissions'], list) and body['data']['permissions']


def test_auth_me_propagates_invalid_actor(monkeypatch):
    monkeypatch.setattr(auth_routes, 'get_connection', lambda: type('C', (), {'close': lambda self: None})())
    monkeypatch.setattr(auth_routes, 'resolve_actor_user_id', lambda *a, **k: 0)

    def _raise(_c, _id, **_k):
        raise PermissionError('Usuário executor inválido.')

    monkeypatch.setattr(auth_routes, 'require_actor', _raise)
    h = _FakeHandler('/api/auth/me')
    try:
        auth_routes.handle_get_auth_me(h, urlparse('/api/auth/me'), None, None)
        assert False, 'esperava PermissionError'
    except PermissionError:
        pass


# ── registro de rotas (alias + me + refresh) ──────────────────────────────────

def test_auth_routes_registered():
    recorded = []

    class R:
        def register(self, method, path, _h, *, regex=False):
            recorded.append((method, path))

    auth_routes.register_routes(R())
    assert ('GET', '/api/auth/me') in recorded
    assert ('POST', '/api/auth/login') in recorded     # alias do /api/login
    assert ('POST', '/api/login') in recorded          # mantido (compat)
    assert ('POST', '/api/auth/refresh') in recorded
