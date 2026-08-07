"""Rotas novas do compartilhamento do cadastro corporativo por tenant +
trava pós-promoção (ADR-0002 §12): vincular à Unidade, ativar/desativar
vínculo local, buscar por nome, "Solicitar atualização cadastral" e as
respostas 409 de duplicidade em POST/PUT de outsourced-companies.

Cobre só a wiring HTTP (registro de rota, permissão reaproveitada, forma
da resposta) — a lógica de negócio já é coberta em
tests/test_outsourced_company_unit_sharing.py.
"""

import io
import json
from urllib.parse import urlparse

import pytest

import modules.outsourced_companies.routes as oc_routes
from modules.outsourced_companies.service import DuplicateOutsourcedCompanyError


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


def _match(entity_id='9'):
    return type('M', (), {'group': lambda self, i: entity_id})()


_ACTOR_GENERAL = {'id': 1, 'full_name': 'Admin Geral', 'role': 'general_admin', 'company_id': 1}
_ACTOR_LOCAL = {'id': 2, 'full_name': 'Gestor A', 'role': 'user', 'company_id': 1}
_ENTITY = {'id': 9, 'company_id': 1, 'legal_name': 'Terceirizada X', 'unit_id': None, 'registration_mode': 'simplified'}


def _audit_spy(monkeypatch):
    calls = []
    monkeypatch.setattr(
        'core.audit.register_company_audit',
        lambda _c, cid, act, action_type, summary, details=None, **k: calls.append(action_type),
    )
    return calls


def test_new_routes_are_registered():
    from core.router import Router
    router = Router()
    oc_routes.register_routes(router)
    paths = [(m, p) for m, p, _pattern, _h in router._routes]
    assert ('GET', '/api/outsourced-companies/search') in paths
    assert ('GET', '/api/outsourced-companies/update-requests') in paths
    assert (r'POST', r'^/api/outsourced-companies/(\d+)/link$') in paths
    assert (r'POST', r'^/api/outsourced-companies/(\d+)/unit-link/activate$') in paths
    assert (r'POST', r'^/api/outsourced-companies/(\d+)/unit-link/deactivate$') in paths
    assert (r'POST', r'^/api/outsourced-companies/(\d+)/update-requests$') in paths
    assert (r'POST', r'^/api/outsourced-companies/update-requests/(\d+)/resolve$') in paths


# ── Busca ────────────────────────────────────────────────────────────────

def test_search_route_returns_service_data(monkeypatch):
    monkeypatch.setattr(oc_routes, 'get_connection', _DummyConnection)
    monkeypatch.setattr(oc_routes, 'resolve_actor_user_id', lambda *a, **k: 1)
    monkeypatch.setattr(oc_routes, 'authorize_action', lambda *a, **k: _ACTOR_GENERAL)
    monkeypatch.setattr(oc_routes, 'search_outsourced_companies_by_name', lambda *a, **k: [{'id': 9, 'legal_name': 'X'}])
    h = _FakeHandler()
    oc_routes.handle_get_outsourced_company_search(h, urlparse('/api/x?q=trans'), None, None)
    assert h.status == 200
    assert h.json()['outsourced_companies'] == [{'id': 9, 'legal_name': 'X'}]


# ── Vincular à minha unidade ────────────────────────────────────────────────

def test_link_route_uses_actor_own_unit_for_local_admin(monkeypatch):
    monkeypatch.setattr(oc_routes, 'get_connection', _DummyConnection)
    monkeypatch.setattr(oc_routes, 'resolve_actor_user_id', lambda *a, **k: 2)
    monkeypatch.setattr(oc_routes, 'authorize_action_any', lambda *a, **k: _ACTOR_LOCAL)
    monkeypatch.setattr(oc_routes, 'ensure_company_access', lambda *a, **k: None)
    monkeypatch.setattr(oc_routes, 'get_outsourced_company_by_id', lambda _c, eid: dict(_ENTITY))
    monkeypatch.setattr(oc_routes, 'actor_operational_unit_id', lambda *a, **k: 55)
    monkeypatch.setattr(oc_routes, 'ensure_module_enabled_for_unit', lambda *a, **k: None)
    monkeypatch.setattr(oc_routes, 'create_outsourced_company_unit_link', lambda *a, **k: 77)
    _audit_spy(monkeypatch)
    h = _FakeHandler()
    oc_routes.handle_post_outsourced_company_link(h, _parsed(), {'actor_user_id': 2}, _match())
    assert h.status == 201
    body = h.json()
    assert body == {'ok': True, 'id': 77, 'unit_id': 55}


def test_link_route_rejects_local_admin_without_operational_unit(monkeypatch):
    monkeypatch.setattr(oc_routes, 'get_connection', _DummyConnection)
    monkeypatch.setattr(oc_routes, 'resolve_actor_user_id', lambda *a, **k: 2)
    monkeypatch.setattr(oc_routes, 'authorize_action_any', lambda *a, **k: _ACTOR_LOCAL)
    monkeypatch.setattr(oc_routes, 'ensure_company_access', lambda *a, **k: None)
    monkeypatch.setattr(oc_routes, 'get_outsourced_company_by_id', lambda _c, eid: dict(_ENTITY))
    monkeypatch.setattr(oc_routes, 'actor_operational_unit_id', lambda *a, **k: None)
    h = _FakeHandler()
    oc_routes.handle_post_outsourced_company_link(h, _parsed(), {'actor_user_id': 2}, _match())
    assert h.status == 403


def test_link_route_requires_unit_id_in_payload_for_general_admin(monkeypatch):
    monkeypatch.setattr(oc_routes, 'get_connection', _DummyConnection)
    monkeypatch.setattr(oc_routes, 'resolve_actor_user_id', lambda *a, **k: 1)
    monkeypatch.setattr(oc_routes, 'authorize_action_any', lambda *a, **k: _ACTOR_GENERAL)
    monkeypatch.setattr(oc_routes, 'ensure_company_access', lambda *a, **k: None)
    monkeypatch.setattr(oc_routes, 'get_outsourced_company_by_id', lambda _c, eid: dict(_ENTITY))
    h = _FakeHandler()
    oc_routes.handle_post_outsourced_company_link(h, _parsed(), {'actor_user_id': 1}, _match())
    assert h.status == 400


# ── Ativar/desativar vínculo local ──────────────────────────────────────────

def test_unit_link_deactivate_route(monkeypatch):
    monkeypatch.setattr(oc_routes, 'get_connection', _DummyConnection)
    monkeypatch.setattr(oc_routes, 'resolve_actor_user_id', lambda *a, **k: 2)
    monkeypatch.setattr(oc_routes, 'authorize_action_any', lambda *a, **k: _ACTOR_LOCAL)
    monkeypatch.setattr(oc_routes, 'ensure_company_access', lambda *a, **k: None)
    monkeypatch.setattr(oc_routes, 'get_outsourced_company_by_id', lambda _c, eid: dict(_ENTITY))
    monkeypatch.setattr(oc_routes, 'actor_operational_unit_id', lambda *a, **k: 55)
    monkeypatch.setattr(
        oc_routes, 'fetch_outsourced_company_unit_link',
        lambda *a, **k: {'id': 3, 'local_status': 'active'},
    )
    calls = []
    monkeypatch.setattr(
        oc_routes, 'set_outsourced_company_unit_link_status',
        lambda *a, **k: calls.append((a, k)),
    )
    _audit_spy(monkeypatch)
    h = _FakeHandler()
    oc_routes.handle_post_outsourced_company_unit_link_deactivate(h, _parsed(), {'actor_user_id': 2, 'reason': 'Fim'}, _match())
    assert h.status == 200
    assert h.json() == {'ok': True, 'local_status': 'inactive'}
    assert calls[0][0][3] == 'inactive'


def test_unit_link_action_raises_when_link_missing(monkeypatch):
    monkeypatch.setattr(oc_routes, 'get_connection', _DummyConnection)
    monkeypatch.setattr(oc_routes, 'resolve_actor_user_id', lambda *a, **k: 2)
    monkeypatch.setattr(oc_routes, 'authorize_action_any', lambda *a, **k: _ACTOR_LOCAL)
    monkeypatch.setattr(oc_routes, 'ensure_company_access', lambda *a, **k: None)
    monkeypatch.setattr(oc_routes, 'get_outsourced_company_by_id', lambda _c, eid: dict(_ENTITY))
    monkeypatch.setattr(oc_routes, 'actor_operational_unit_id', lambda *a, **k: 55)
    monkeypatch.setattr(oc_routes, 'fetch_outsourced_company_unit_link', lambda *a, **k: None)
    h = _FakeHandler()
    with pytest.raises(ValueError):
        oc_routes.handle_post_outsourced_company_unit_link_activate(h, _parsed(), {'actor_user_id': 2}, _match())


def _full_audit_spy(monkeypatch):
    """Como _audit_spy, mas guarda a chamada inteira — usado quando o teste
    precisa conferir o conteúdo de `details` (usuário/perfil/unidade), não
    só o action_type."""
    calls = []
    monkeypatch.setattr(
        'core.audit.register_company_audit',
        lambda _c, cid, actor, action_type, summary, details=None, **k:
            calls.append({'company_id': cid, 'actor': actor, 'action_type': action_type,
                          'summary': summary, 'details': details or []}),
    )
    return calls


def _details_field(entry, field):
    return next((item['after'] for item in entry['details'] if item['field'] == field), None)


def test_unit_link_deactivate_route_audits_unit_and_role(monkeypatch):
    """Arquivar nesta Unidade precisa registrar usuário, perfil, tenant e
    Unidade — não só "algo mudou" (requisito de auditoria do pedido)."""
    monkeypatch.setattr(oc_routes, 'get_connection', _DummyConnection)
    monkeypatch.setattr(oc_routes, 'resolve_actor_user_id', lambda *a, **k: 2)
    monkeypatch.setattr(oc_routes, 'authorize_action_any', lambda *a, **k: _ACTOR_LOCAL)
    monkeypatch.setattr(oc_routes, 'ensure_company_access', lambda *a, **k: None)
    monkeypatch.setattr(oc_routes, 'get_outsourced_company_by_id', lambda _c, eid: dict(_ENTITY))
    monkeypatch.setattr(oc_routes, 'actor_operational_unit_id', lambda *a, **k: 55)
    monkeypatch.setattr(
        oc_routes, 'fetch_outsourced_company_unit_link',
        lambda *a, **k: {'id': 3, 'unit_id': 55, 'local_status': 'active'},
    )
    monkeypatch.setattr(oc_routes, 'set_outsourced_company_unit_link_status', lambda *a, **k: None)
    calls = _full_audit_spy(monkeypatch)
    h = _FakeHandler()
    oc_routes.handle_post_outsourced_company_unit_link_deactivate(
        h, _parsed(), {'actor_user_id': 2, 'reason': 'Fim de contrato'}, _match(),
    )
    assert h.status == 200
    assert len(calls) == 1
    entry = calls[0]
    assert entry['company_id'] == _ACTOR_LOCAL['company_id']
    assert entry['actor'] == _ACTOR_LOCAL
    assert entry['action_type'] == 'outsourced_company_unit_link_status_changed'
    assert _details_field(entry, 'local_status') == 'inactive'
    assert _details_field(entry, 'unit_id') == '55'
    assert _details_field(entry, 'actor_role') == 'user'
    assert _details_field(entry, 'reason') == 'Fim de contrato'


def test_unit_link_activate_route_audits_unit_and_role(monkeypatch):
    monkeypatch.setattr(oc_routes, 'get_connection', _DummyConnection)
    monkeypatch.setattr(oc_routes, 'resolve_actor_user_id', lambda *a, **k: 2)
    monkeypatch.setattr(oc_routes, 'authorize_action_any', lambda *a, **k: _ACTOR_LOCAL)
    monkeypatch.setattr(oc_routes, 'ensure_company_access', lambda *a, **k: None)
    monkeypatch.setattr(oc_routes, 'get_outsourced_company_by_id', lambda _c, eid: dict(_ENTITY))
    monkeypatch.setattr(oc_routes, 'actor_operational_unit_id', lambda *a, **k: 55)
    monkeypatch.setattr(
        oc_routes, 'fetch_outsourced_company_unit_link',
        lambda *a, **k: {'id': 3, 'unit_id': 55, 'local_status': 'inactive'},
    )
    monkeypatch.setattr(oc_routes, 'set_outsourced_company_unit_link_status', lambda *a, **k: None)
    calls = _full_audit_spy(monkeypatch)
    h = _FakeHandler()
    oc_routes.handle_post_outsourced_company_unit_link_activate(h, _parsed(), {'actor_user_id': 2}, _match())
    assert h.status == 200
    entry = calls[0]
    assert _details_field(entry, 'local_status') == 'active'
    assert _details_field(entry, 'unit_id') == '55'
    assert _details_field(entry, 'actor_role') == 'user'


# ── Duplicidade de CNPJ/nome (POST/PUT) ─────────────────────────────────────

def test_post_outsourced_company_returns_409_on_duplicate_cnpj(monkeypatch):
    monkeypatch.setattr(oc_routes, 'get_connection', _DummyConnection)
    monkeypatch.setattr(oc_routes, 'resolve_actor_user_id', lambda *a, **k: 1)
    monkeypatch.setattr(oc_routes, 'authorize_action_any', lambda *a, **k: _ACTOR_GENERAL)
    monkeypatch.setattr(oc_routes, 'resolve_outsourced_company_unit_id', lambda *a, **k: None)
    monkeypatch.setattr(oc_routes, 'ensure_module_enabled_for_unit', lambda *a, **k: None)

    def _raise(*_a, **_k):
        raise DuplicateOutsourcedCompanyError(42, 'CNPJ já cadastrado neste tenant.')

    monkeypatch.setattr(oc_routes, 'create_outsourced_company', _raise)
    payload = {'actor_user_id': 1, 'legal_name': 'Alfa', 'cnpj': '11.222.333/0001-81'}
    h = _FakeHandler()
    oc_routes.handle_post_outsourced_companies(h, _parsed(), payload, None)
    assert h.status == 409
    body = h.json()
    assert body['code'] == 'duplicate_cnpj'
    assert body['existing_company_id'] == 42
    assert 'CNPJ' in body['error']


def test_post_outsourced_company_returns_409_on_possible_name_duplicate(monkeypatch):
    monkeypatch.setattr(oc_routes, 'get_connection', _DummyConnection)
    monkeypatch.setattr(oc_routes, 'resolve_actor_user_id', lambda *a, **k: 1)
    monkeypatch.setattr(oc_routes, 'authorize_action_any', lambda *a, **k: _ACTOR_GENERAL)
    monkeypatch.setattr(oc_routes, 'resolve_outsourced_company_unit_id', lambda *a, **k: None)
    monkeypatch.setattr(oc_routes, 'ensure_module_enabled_for_unit', lambda *a, **k: None)
    monkeypatch.setattr(
        oc_routes, 'search_outsourced_companies_by_name',
        lambda *a, **k: [{'id': 5, 'legal_name': 'Transforma Terceirizados'}],
    )
    payload = {'actor_user_id': 1, 'legal_name': 'Transforma Terceirizados LTDA'}
    h = _FakeHandler()
    oc_routes.handle_post_outsourced_companies(h, _parsed(), payload, None)
    assert h.status == 409
    assert h.json()['code'] == 'possible_duplicate'


def test_post_outsourced_company_confirm_duplicate_skips_name_check(monkeypatch):
    monkeypatch.setattr(oc_routes, 'get_connection', _DummyConnection)
    monkeypatch.setattr(oc_routes, 'resolve_actor_user_id', lambda *a, **k: 1)
    monkeypatch.setattr(oc_routes, 'authorize_action_any', lambda *a, **k: _ACTOR_GENERAL)
    monkeypatch.setattr(oc_routes, 'resolve_outsourced_company_unit_id', lambda *a, **k: None)
    monkeypatch.setattr(oc_routes, 'ensure_module_enabled_for_unit', lambda *a, **k: None)
    search_calls = []
    monkeypatch.setattr(
        oc_routes, 'search_outsourced_companies_by_name',
        lambda *a, **k: search_calls.append(1) or [{'id': 5, 'legal_name': 'Transforma'}],
    )
    monkeypatch.setattr(oc_routes, 'create_outsourced_company', lambda *a, **k: 99)
    _audit_spy(monkeypatch)
    payload = {'actor_user_id': 1, 'legal_name': 'Transforma Terceirizados LTDA', 'confirm_duplicate': True}
    h = _FakeHandler()
    oc_routes.handle_post_outsourced_companies(h, _parsed(), payload, None)
    assert h.status == 201
    assert h.json()['id'] == 99
    assert not search_calls  # confirm_duplicate pula a checagem de nome


def test_put_outsourced_company_returns_409_on_duplicate_cnpj(monkeypatch):
    monkeypatch.setattr(oc_routes, 'get_connection', _DummyConnection)
    monkeypatch.setattr(oc_routes, 'resolve_actor_user_id', lambda *a, **k: 1)
    monkeypatch.setattr(oc_routes, 'authorize_action_any', lambda *a, **k: _ACTOR_GENERAL)
    monkeypatch.setattr(oc_routes, 'get_outsourced_company_by_id', lambda _c, eid: dict(_ENTITY))
    monkeypatch.setattr(oc_routes, 'ensure_company_access', lambda *a, **k: None)
    monkeypatch.setattr(oc_routes, 'ensure_actor_outsourced_company_scope', lambda *a, **k: None)
    monkeypatch.setattr(oc_routes, 'ensure_actor_can_edit_outsourced_company_corporate_fields', lambda *a, **k: None)
    monkeypatch.setattr(oc_routes, 'ensure_module_enabled_for_unit', lambda *a, **k: None)

    def _raise(*_a, **_k):
        raise DuplicateOutsourcedCompanyError(7, 'CNPJ já pertence a outro registro.')

    monkeypatch.setattr(oc_routes, 'update_outsourced_company', _raise)
    payload = {'actor_user_id': 1, 'legal_name': 'Alfa', 'cnpj': '99.999.999/0001-99'}
    h = _FakeHandler()
    oc_routes.handle_put_outsourced_company(h, _parsed(), payload, _match())
    assert h.status == 409
    assert h.json()['existing_company_id'] == 7


# ── Trava pós-promoção bloqueando PUT ───────────────────────────────────────

def test_put_outsourced_company_blocked_when_corporate_locked(monkeypatch):
    monkeypatch.setattr(oc_routes, 'get_connection', _DummyConnection)
    monkeypatch.setattr(oc_routes, 'resolve_actor_user_id', lambda *a, **k: 2)
    monkeypatch.setattr(oc_routes, 'authorize_action_any', lambda *a, **k: _ACTOR_LOCAL)
    monkeypatch.setattr(oc_routes, 'get_outsourced_company_by_id', lambda _c, eid: dict(_ENTITY, registration_mode='standard'))
    monkeypatch.setattr(oc_routes, 'ensure_company_access', lambda *a, **k: None)
    monkeypatch.setattr(oc_routes, 'ensure_actor_outsourced_company_scope', lambda *a, **k: None)
    payload = {'actor_user_id': 2, 'legal_name': 'Alfa Renomeada'}
    h = _FakeHandler()
    with pytest.raises(PermissionError):
        oc_routes.handle_put_outsourced_company(h, _parsed(), payload, _match())


# ── "Solicitar atualização cadastral" ───────────────────────────────────────

def test_post_update_request_route(monkeypatch):
    monkeypatch.setattr(oc_routes, 'get_connection', _DummyConnection)
    monkeypatch.setattr(oc_routes, 'resolve_actor_user_id', lambda *a, **k: 2)
    monkeypatch.setattr(oc_routes, 'authorize_action_any', lambda *a, **k: _ACTOR_LOCAL)
    monkeypatch.setattr(oc_routes, 'get_outsourced_company_by_id', lambda _c, eid: dict(_ENTITY))
    monkeypatch.setattr(oc_routes, 'ensure_company_access', lambda *a, **k: None)
    monkeypatch.setattr(oc_routes, 'ensure_actor_outsourced_company_scope', lambda *a, **k: None)
    monkeypatch.setattr(oc_routes, 'actor_operational_unit_id', lambda *a, **k: 55)
    monkeypatch.setattr(oc_routes, 'create_outsourced_company_update_request', lambda *a, **k: 12)
    _audit_spy(monkeypatch)
    payload = {'actor_user_id': 2, 'message': 'CNPJ mudou'}
    h = _FakeHandler()
    oc_routes.handle_post_outsourced_company_update_requests(h, _parsed(), payload, _match())
    assert h.status == 201
    assert h.json()['id'] == 12


def test_get_update_requests_requires_full_update_permission(monkeypatch):
    monkeypatch.setattr(oc_routes, 'get_connection', _DummyConnection)
    monkeypatch.setattr(oc_routes, 'resolve_actor_user_id', lambda *a, **k: 1)

    def _deny(*_a, **_k):
        raise PermissionError('Permissão negada.')

    monkeypatch.setattr(oc_routes, 'authorize_action', _deny)
    h = _FakeHandler()
    with pytest.raises(PermissionError):
        oc_routes.handle_get_outsourced_company_update_requests(h, _parsed(), None, None)


def test_resolve_update_request_route(monkeypatch):
    monkeypatch.setattr(oc_routes, 'get_connection', _DummyConnection)
    monkeypatch.setattr(oc_routes, 'resolve_actor_user_id', lambda *a, **k: 1)
    monkeypatch.setattr(oc_routes, 'authorize_action', lambda *a, **k: _ACTOR_GENERAL)
    monkeypatch.setattr(
        oc_routes, 'get_outsourced_company_update_request_by_id',
        lambda _c, rid: {'id': rid, 'company_id': 1, 'status': 'pending'},
    )
    monkeypatch.setattr(oc_routes, 'ensure_company_access', lambda *a, **k: None)
    monkeypatch.setattr(oc_routes, 'resolve_outsourced_company_update_request', lambda *a, **k: 'resolved')
    _audit_spy(monkeypatch)
    payload = {'actor_user_id': 1, 'status': 'resolved'}
    h = _FakeHandler()
    oc_routes.handle_post_outsourced_company_update_request_resolve(h, _parsed(), payload, _match('4'))
    assert h.status == 200
    assert h.json()['status'] == 'resolved'


def test_resolve_update_request_404_when_not_found(monkeypatch):
    monkeypatch.setattr(oc_routes, 'get_connection', _DummyConnection)
    monkeypatch.setattr(oc_routes, 'resolve_actor_user_id', lambda *a, **k: 1)
    monkeypatch.setattr(oc_routes, 'authorize_action', lambda *a, **k: _ACTOR_GENERAL)
    monkeypatch.setattr(oc_routes, 'get_outsourced_company_update_request_by_id', lambda _c, rid: None)
    h = _FakeHandler()
    oc_routes.handle_post_outsourced_company_update_request_resolve(h, _parsed(), {'actor_user_id': 1, 'status': 'resolved'}, _match('999'))
    assert h.status == 404
