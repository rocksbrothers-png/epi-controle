"""Rotas novas do PR 6 (ADR-0002): ressarcimento e sugestão de migração.

Cobre só a wiring HTTP (registro de rota, permissão reaproveitada,
auditoria disparada) — a lógica de negócio já é coberta em
tests/test_epi_reimbursements_and_migration_alert.py.
"""

import io
import json
from urllib.parse import urlparse

import modules.outsourced_companies.routes as oc_routes


class _FakeHandler:
    def __init__(self, path='/api/x'):
        self.path = path
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


class _DummyConnection:
    def commit(self):
        pass

    def close(self):
        pass


def _parsed(query='actor_user_id=1'):
    return urlparse(f'/api/x?{query}')


def test_new_routes_are_registered():
    from core.router import Router
    router = Router()
    oc_routes.register_routes(router)
    paths = [(m, p) for m, p, _pattern, _h in router._routes]
    assert ('GET', '/api/outsourced-companies/migration-suggestions') in paths
    assert ('GET', '/api/epi-reimbursements') in paths
    assert ('POST', '/api/epi-reimbursements') in paths
    assert (r'PUT', r'^/api/epi-reimbursements/(\d+)/status$') in paths


def test_get_migration_suggestions_returns_service_data(monkeypatch):
    actor = {'id': 1, 'role': 'general_admin', 'company_id': 1}
    monkeypatch.setattr(oc_routes, 'get_connection', _DummyConnection)
    monkeypatch.setattr(oc_routes, 'resolve_actor_user_id', lambda *a, **k: 1)
    monkeypatch.setattr(oc_routes, 'authorize_action', lambda *a, **k: actor)
    monkeypatch.setattr(oc_routes, 'fetch_migration_suggestions', lambda _c, cid: [{'outsourced_company_id': 9}])
    h = _FakeHandler()
    oc_routes.handle_get_migration_suggestions(h, _parsed(), None, None)
    assert h.status == 200
    assert h.json()['migration_suggestions'] == [{'outsourced_company_id': 9}]


def test_post_reimbursement_audits_creation(monkeypatch):
    actor = {'id': 1, 'full_name': 'Admin', 'role': 'general_admin', 'company_id': 1}
    monkeypatch.setattr(oc_routes, 'get_connection', _DummyConnection)
    monkeypatch.setattr(oc_routes, 'resolve_actor_user_id', lambda *a, **k: 1)
    monkeypatch.setattr(oc_routes, 'authorize_action', lambda *a, **k: actor)
    monkeypatch.setattr(oc_routes, 'create_reimbursement', lambda *a, **k: 55)
    calls = []
    monkeypatch.setattr(
        'core.audit.register_company_audit',
        lambda _c, cid, act, action_type, summary, details=None, **k: calls.append(action_type),
    )
    payload = {'actor_user_id': 1, 'delivery_id': 10, 'outsourced_company_id': 9}
    h = _FakeHandler()
    oc_routes.handle_post_reimbursements(h, _parsed(), payload, None)
    assert h.status == 201
    assert h.json()['id'] == 55
    assert calls == ['epi_reimbursement_recorded']


def test_put_reimbursement_status_requires_company_match(monkeypatch):
    actor = {'id': 1, 'full_name': 'Admin', 'role': 'general_admin', 'company_id': 1}
    monkeypatch.setattr(oc_routes, 'get_connection', _DummyConnection)
    monkeypatch.setattr(oc_routes, 'resolve_actor_user_id', lambda *a, **k: 1)
    monkeypatch.setattr(oc_routes, 'authorize_action', lambda *a, **k: actor)
    monkeypatch.setattr(oc_routes, 'ensure_company_access', lambda *a, **k: None)
    monkeypatch.setattr(oc_routes, 'get_reimbursement_by_id', lambda _c, rid: {
        'id': rid, 'company_id': 1, 'status': 'Pendente de Análise',
    })
    monkeypatch.setattr(oc_routes, 'update_reimbursement_status', lambda _c, rid, cid, status: 'Ressarcida')
    calls = []
    monkeypatch.setattr(
        'core.audit.register_company_audit',
        lambda _c, cid, act, action_type, summary, details=None, **k: calls.append(action_type),
    )
    payload = {'actor_user_id': 1, 'status': 'Ressarcida'}
    h = _FakeHandler()
    match = type('M', (), {'group': lambda self, i: '55'})()
    oc_routes.handle_put_reimbursement_status(h, _parsed(), payload, match)
    assert h.status == 200
    assert h.json()['status'] == 'Ressarcida'
    assert calls == ['epi_reimbursement_status_changed']


def test_put_reimbursement_status_404_when_not_found(monkeypatch):
    actor = {'id': 1, 'role': 'general_admin', 'company_id': 1}
    monkeypatch.setattr(oc_routes, 'get_connection', _DummyConnection)
    monkeypatch.setattr(oc_routes, 'resolve_actor_user_id', lambda *a, **k: 1)
    monkeypatch.setattr(oc_routes, 'authorize_action', lambda *a, **k: actor)
    monkeypatch.setattr(oc_routes, 'get_reimbursement_by_id', lambda _c, rid: None)
    payload = {'actor_user_id': 1, 'status': 'Ressarcida'}
    h = _FakeHandler()
    match = type('M', (), {'group': lambda self, i: '999'})()
    oc_routes.handle_put_reimbursement_status(h, _parsed(), payload, match)
    assert h.status == 404
