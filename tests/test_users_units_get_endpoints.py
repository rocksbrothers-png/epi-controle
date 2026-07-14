"""GET endpoints dedicados para usuários e unidades (desacoplados do bootstrap).

Cobre os handlers adicionados em modules/users/routes.py e modules/units/routes.py:
  - GET /api/users        -> lista escopada por empresa
  - GET /api/users/(\\d+)  -> usuário único, sem expor senha
  - GET /api/units        -> lista escopada por empresa
  - GET /api/units/(\\d+)  -> unidade única

Os testes substituem a pilha pesada de autorização (authorize_action / fetch_*)
para validar o cabeamento dos handlers de forma determinística.
"""

import io
import json
from urllib.parse import urlparse

import modules.units.routes as units_routes
import modules.users.routes as users_routes


# ── Fakes mínimos ─────────────────────────────────────────────────────────────

class _FakeHandler:
    """Substituto de EpiHandler suficiente para send_json()."""

    def __init__(self):
        self.path = '/api/test'
        self.command = 'GET'
        self.status = None
        self.wfile = io.BytesIO()

    def send_response(self, status):
        self.status = status

    def send_header(self, *_args, **_kwargs):
        pass

    def end_headers(self):
        pass

    def captured_json(self):
        return json.loads(self.wfile.getvalue().decode('utf-8'))


class _FakeConn:
    def close(self):
        pass


def _parsed(query=''):
    return urlparse(f'/api/x?{query}' if query else '/api/x')


def _install_common(monkeypatch, module, actor):
    """Neutraliza get_connection, resolve_actor_user_id e authorize_action."""
    calls = {}
    monkeypatch.setattr(module, 'get_connection', lambda: _FakeConn())
    monkeypatch.setattr(module, 'resolve_actor_user_id', lambda *a, **k: actor['id'])

    def _authorize(_conn, _actor_id, action, *a, **k):
        calls['action'] = action
        return actor

    monkeypatch.setattr(module, 'authorize_action', _authorize)
    return calls


# ── _sanitize_user ────────────────────────────────────────────────────────────

def test_sanitize_user_removes_password():
    user = {'id': 1, 'username': 'jeff', 'password': 'secret', 'role': 'general_admin'}
    safe = users_routes._sanitize_user(user)
    assert 'password' not in safe
    assert safe['username'] == 'jeff'
    # não muta o original
    assert user['password'] == 'secret'


def test_sanitize_user_passthrough_falsy():
    assert users_routes._sanitize_user(None) is None


# ── GET /api/users ────────────────────────────────────────────────────────────

def test_get_users_lists_scoped(monkeypatch):
    actor = {'id': 9, 'company_id': 1, 'role': 'general_admin'}
    calls = _install_common(monkeypatch, users_routes, actor)
    seen = {}

    def _fetch_users(_conn, passed_actor):
        seen['actor'] = passed_actor
        return [{'id': 9, 'username': 'jeff'}, {'id': 10, 'username': 'ana'}]

    monkeypatch.setattr(users_routes, 'fetch_users', _fetch_users)

    handler = _FakeHandler()
    users_routes.handle_get_users(handler, _parsed('actor_user_id=9'), None, None)

    assert handler.status == 200
    assert calls['action'] == 'users:view'
    assert seen['actor'] is actor  # escopo é aplicado pelo actor
    body = handler.captured_json()
    assert [u['username'] for u in body['users']] == ['jeff', 'ana']


def test_get_user_single_strips_password(monkeypatch):
    actor = {'id': 9, 'company_id': 1, 'role': 'general_admin'}
    _install_common(monkeypatch, users_routes, actor)
    monkeypatch.setattr(
        users_routes, 'get_user_by_id',
        lambda _conn, uid: {'id': uid, 'username': 'jeff', 'password': 'h@sh', 'company_id': 1},
    )
    monkeypatch.setattr(users_routes, 'ensure_resource_company', lambda *a, **k: None)

    handler = _FakeHandler()
    match = users_routes._USER_ID_RE.match('/api/users/9')
    users_routes.handle_get_user(handler, _parsed('actor_user_id=9'), None, match)

    assert handler.status == 200
    body = handler.captured_json()
    assert body['user']['id'] == 9
    assert 'password' not in body['user']


def test_get_user_enforces_company_scope(monkeypatch):
    actor = {'id': 9, 'company_id': 1, 'role': 'general_admin'}
    _install_common(monkeypatch, users_routes, actor)
    monkeypatch.setattr(
        users_routes, 'get_user_by_id',
        lambda _conn, uid: {'id': uid, 'username': 'outsider', 'company_id': 2},
    )

    def _deny(_actor, _resource, _label='Registro'):
        raise PermissionError('fora da empresa')

    monkeypatch.setattr(users_routes, 'ensure_resource_company', _deny)

    handler = _FakeHandler()
    match = users_routes._USER_ID_RE.match('/api/users/77')
    try:
        users_routes.handle_get_user(handler, _parsed('actor_user_id=9'), None, match)
        assert False, 'esperava PermissionError'
    except PermissionError:
        pass


# ── GET /api/units ────────────────────────────────────────────────────────────

def test_get_units_lists_scoped(monkeypatch):
    actor = {'id': 9, 'company_id': 1, 'role': 'general_admin'}
    calls = _install_common(monkeypatch, units_routes, actor)
    seen = {}

    def _fetch_units(_conn, passed_actor):
        seen['actor'] = passed_actor
        return [{'id': 1, 'name': 'Base Santos'}]

    monkeypatch.setattr(units_routes, 'fetch_units', _fetch_units)

    handler = _FakeHandler()
    units_routes.handle_get_units(handler, _parsed('actor_user_id=9'), None, None)

    assert handler.status == 200
    assert calls['action'] == 'units:view'
    assert seen['actor'] is actor
    body = handler.captured_json()
    assert body['units'][0]['name'] == 'Base Santos'


def test_get_unit_single(monkeypatch):
    actor = {'id': 9, 'company_id': 1, 'role': 'general_admin'}
    _install_common(monkeypatch, units_routes, actor)
    monkeypatch.setattr(
        units_routes, 'get_unit_with_lifecycle',
        lambda _conn, uid: {'id': uid, 'name': 'Base Santos', 'company_id': 1},
    )
    monkeypatch.setattr(units_routes, 'ensure_resource_company', lambda *a, **k: None)

    handler = _FakeHandler()
    match = units_routes._UNIT_ID_RE.match('/api/units/1')
    units_routes.handle_get_unit(handler, _parsed('actor_user_id=9'), None, match)

    assert handler.status == 200
    body = handler.captured_json()
    assert body['unit']['name'] == 'Base Santos'


# ── Registro de rotas ─────────────────────────────────────────────────────────

class _RecordingRouter:
    def __init__(self):
        self.routes = []

    def register(self, method, path, _handler, *, regex=False):
        self.routes.append((method, path))


def test_users_routes_register_get_endpoints():
    router = _RecordingRouter()
    users_routes.register_routes(router)
    assert ('GET', '/api/users') in router.routes
    assert ('GET', r'/api/users/(\d+)$') in router.routes


def test_units_routes_register_get_endpoints():
    router = _RecordingRouter()
    units_routes.register_routes(router)
    assert ('GET', '/api/units') in router.routes
    assert ('GET', r'/api/units/(\d+)$') in router.routes
