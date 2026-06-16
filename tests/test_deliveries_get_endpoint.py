"""GET /api/deliveries — corrige bug de paridade (Flutter chamava endpoint
inexistente; lista de entregas vinha quebrada). Fase 4, lote 2.
"""

import io
import json
from urllib.parse import urlparse

import modules.deliveries.routes as routes


class _FakeHandler:
    def __init__(self, path='/api/deliveries'):
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


def _parsed(query='actor_user_id=1'):
    return urlparse(f'/api/deliveries?{query}')


def _patch(monkeypatch, actor, *, scope_unit=None, captured=None):
    monkeypatch.setattr(routes, 'get_connection', lambda: type('C', (), {'close': lambda self: None})())
    monkeypatch.setattr(routes, 'resolve_actor_user_id', lambda *a, **k: actor['id'])
    monkeypatch.setattr(routes, 'authorize_action', lambda *a, **k: actor)
    monkeypatch.setattr(routes, 'actor_operational_unit_id', lambda *a, **k: scope_unit)

    def _fetch(_conn, passed_actor, where='', params=()):
        if captured is not None:
            captured['actor'] = passed_actor
            captured['where'] = where
            captured['params'] = params
        return [{'id': 3, 'epi_name': 'Luva'}, {'id': 2, 'epi_name': 'Bota'}, {'id': 1, 'epi_name': 'Capacete'}]

    monkeypatch.setattr(routes, 'fetch_deliveries', _fetch)


def test_get_deliveries_returns_items_and_deliveries(monkeypatch):
    actor = {'id': 1, 'role': 'general_admin', 'company_id': 1}
    cap = {}
    _patch(monkeypatch, actor, captured=cap)
    h = _FakeHandler()
    routes.handle_get_deliveries(h, _parsed(), None, None)
    body = h.json()
    assert h.status == 200
    assert len(body['deliveries']) == 3
    assert body['items'] == body['deliveries']  # cliente Flutter é tolerante a ambos
    assert cap['actor'] is actor                # escopo de empresa via fetch_deliveries(actor)


def test_get_deliveries_scopes_by_operational_unit(monkeypatch):
    actor = {'id': 5, 'role': 'admin', 'company_id': 1}
    cap = {}
    _patch(monkeypatch, actor, scope_unit=42, captured=cap)
    h = _FakeHandler()
    routes.handle_get_deliveries(h, _parsed('actor_user_id=5'), None, None)
    assert 'deliveries.unit_id = ?' in cap['where']
    assert cap['params'] == (42,)


def test_get_deliveries_applies_limit(monkeypatch):
    actor = {'id': 1, 'role': 'master_admin', 'company_id': None}
    _patch(monkeypatch, actor)
    h = _FakeHandler()
    routes.handle_get_deliveries(h, _parsed('actor_user_id=1&limit=2'), None, None)
    assert len(h.json()['deliveries']) == 2


def test_get_deliveries_registered():
    recorded = []

    class R:
        def register(self, method, path, _h, *, regex=False):
            recorded.append((method, path))

    routes.register_routes(R())
    assert ('GET', '/api/deliveries') in recorded
    assert ('POST', '/api/deliveries') in recorded  # POST preservado
