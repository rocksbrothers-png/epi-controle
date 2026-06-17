"""GET /api/epis/{id} — EPI completo para prefill de edição no cliente Flutter."""

import io
import json
from urllib.parse import urlparse

import modules.epis.routes as routes


class _FakeHandler:
    def __init__(self):
        self.path = '/api/epis/5'
        self.command = 'GET'
        self.status = None
        self.wfile = io.BytesIO()

    def send_response(self, s):
        self.status = s

    def send_header(self, *a, **k):
        pass

    def end_headers(self):
        pass

    def json(self):
        return json.loads(self.wfile.getvalue().decode('utf-8'))


def _match(epi_id):
    return type('M', (), {'group': lambda self, i: str(epi_id)})()


def _patch(monkeypatch, actor):
    monkeypatch.setattr(routes, 'get_connection', lambda: type('C', (), {'close': lambda self: None})())
    monkeypatch.setattr(routes, 'resolve_actor_user_id', lambda *a, **k: actor['id'])
    monkeypatch.setattr(routes, 'authorize_action', lambda *a, **k: actor)


def test_get_epi_returns_full_record(monkeypatch):
    actor = {'id': 1, 'role': 'general_admin', 'company_id': 1}
    _patch(monkeypatch, actor)
    monkeypatch.setattr(routes, 'get_epi_full',
                        lambda _c, eid: {'id': eid, 'company_id': 1, 'name': 'Luva', 'ca': '123'})
    monkeypatch.setattr(routes, 'ensure_resource_company', lambda *a, **k: None)
    h = _FakeHandler()
    routes.handle_get_epi(h, urlparse('/api/epis/5?actor_user_id=1'), None, _match(5))
    assert h.status == 200
    assert h.json()['epi']['id'] == 5 and h.json()['epi']['name'] == 'Luva'


def test_get_epi_404(monkeypatch):
    actor = {'id': 1, 'role': 'general_admin', 'company_id': 1}
    _patch(monkeypatch, actor)
    monkeypatch.setattr(routes, 'get_epi_full', lambda _c, eid: None)
    h = _FakeHandler()
    routes.handle_get_epi(h, urlparse('/api/epis/999?actor_user_id=1'), None, _match(999))
    assert h.status == 404


def test_get_epi_enforces_company_scope(monkeypatch):
    actor = {'id': 1, 'role': 'general_admin', 'company_id': 1}
    _patch(monkeypatch, actor)
    monkeypatch.setattr(routes, 'get_epi_full', lambda _c, eid: {'id': eid, 'company_id': 2})

    def _deny(*a, **k):
        raise PermissionError('fora da empresa')

    monkeypatch.setattr(routes, 'ensure_resource_company', _deny)
    h = _FakeHandler()
    try:
        routes.handle_get_epi(h, urlparse('/api/epis/5?actor_user_id=1'), None, _match(5))
        assert False, 'esperava PermissionError'
    except PermissionError:
        pass


def test_get_epi_route_registered():
    recorded = []

    class R:
        def register(self, method, path, _h, *, regex=False):
            recorded.append((method, path))

    routes.register_routes(R())
    assert ('GET', r'/api/epis/(\d+)$') in recorded
