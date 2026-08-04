"""Rotas GET/POST /api/module-unit-scope (Configuração → Regras →
Visualização, extensão ADR-0002 §10.3 — autorização por Unidade dos
módulos opt-in escopáveis).

Cobre a mesma autoridade de /api/module-visibility (require_configuration_
admin) e a auditoria de toda mudança de escopo por unidade
(register_company_audit, evento "module_unit_scope_updated").
"""

import io
import json
from urllib.parse import urlparse

import pytest

import modules.settings.routes as routes
import modules.settings.service as settings_service


class _FakeHandler:
    def __init__(self):
        self.path = '/api/module-unit-scope'
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


class _FakeConn:
    """Conexão fake com unidades 1 e 2 cadastradas para o tenant (company_id
    7 nos testes abaixo) — usada pela validação de pertencimento em
    save_module_unit_scope."""

    def commit(self):
        pass

    def close(self):
        pass

    def execute(self, _sql, _params=()):
        return _FakeRows([{'id': 1}, {'id': 2}])


class _FakeRows:
    def __init__(self, rows):
        self._rows = rows

    def fetchall(self):
        return self._rows


def _fake_meta_store(monkeypatch):
    store = {}
    monkeypatch.setattr(settings_service, 'get_meta', lambda _conn, key: store.get(key))
    monkeypatch.setattr(settings_service, 'set_meta', lambda _conn, key, value: store.__setitem__(key, value))
    return store


def _patch_common(monkeypatch, actor):
    monkeypatch.setattr(routes, 'get_connection', _FakeConn)
    monkeypatch.setattr(routes, 'resolve_actor_user_id', lambda *a, **k: actor['id'])
    monkeypatch.setattr(routes, 'authorize_action', lambda *a, **k: actor)


def _parsed(query='actor_user_id=1'):
    return urlparse(f'/api/module-unit-scope?{query}')


GENERAL_ADMIN = {'id': 1, 'role': 'general_admin', 'company_id': 7, 'full_name': 'Ana Geral'}
REGISTRY_ADMIN = {'id': 2, 'role': 'registry_admin', 'company_id': 7, 'full_name': 'Bea Registro'}
LOCAL_ADMIN = {'id': 3, 'role': 'admin', 'company_id': 7, 'full_name': 'Caio Local'}
BUYER = {'id': 4, 'role': 'buyer', 'company_id': 7, 'full_name': 'Duda Compras'}


# ── GET: leitura da configuração ────────────────────────────────────────────

def test_general_admin_can_read_module_unit_scope(monkeypatch):
    _fake_meta_store(monkeypatch)
    _patch_common(monkeypatch, GENERAL_ADMIN)
    handler = _FakeHandler()
    routes.handle_get_module_unit_scope(handler, _parsed(), {}, None)
    body = handler.json()
    assert handler.status == 200
    assert body['module_unit_scope'] == {}
    assert 'terceirizados_colaboradores' in body['unit_scopable_modules']


@pytest.mark.parametrize('actor', [LOCAL_ADMIN, BUYER])
def test_non_configuration_roles_cannot_read_module_unit_scope(monkeypatch, actor):
    _fake_meta_store(monkeypatch)
    _patch_common(monkeypatch, actor)
    handler = _FakeHandler()
    with pytest.raises(PermissionError):
        routes.handle_get_module_unit_scope(handler, _parsed(), {}, None)


# ── POST: gravação + auditoria ──────────────────────────────────────────────

def test_general_admin_saves_module_unit_scope_and_it_is_audited(monkeypatch):
    _fake_meta_store(monkeypatch)
    _patch_common(monkeypatch, GENERAL_ADMIN)
    audits = []
    monkeypatch.setattr(
        'modules.companies.service.register_company_audit',
        lambda connection, company_id, actor, action_type, summary, details=None, **kwargs:
            audits.append({
                'company_id': company_id, 'actor': actor, 'action_type': action_type,
                'summary': summary, 'details': details,
            }),
    )
    handler = _FakeHandler()
    payload = {'actor_user_id': 1, 'module': 'terceirizados_colaboradores', 'unit_ids': [1, 2]}
    routes.handle_post_module_unit_scope(handler, _parsed(), payload, None)

    assert handler.status == 200
    body = handler.json()
    assert body['ok'] is True
    assert body['before'] == []
    assert body['after'] == [1, 2]

    assert len(audits) == 1
    entry = audits[0]
    assert entry['action_type'] == 'module_unit_scope_updated'
    assert entry['company_id'] == 7
    assert entry['actor']['id'] == GENERAL_ADMIN['id']
    assert entry['details']['module'] == 'terceirizados_colaboradores'
    assert entry['details']['before'] == []
    assert entry['details']['after'] == [1, 2]


def test_module_unit_scope_drops_unit_ids_outside_the_tenant(monkeypatch):
    # A conexão fake só tem as unidades 1 e 2 — a 99 é descartada.
    _fake_meta_store(monkeypatch)
    _patch_common(monkeypatch, GENERAL_ADMIN)
    monkeypatch.setattr('modules.companies.service.register_company_audit', lambda *a, **k: None)
    handler = _FakeHandler()
    payload = {'actor_user_id': 1, 'module': 'terceirizados_colaboradores', 'unit_ids': [1, 99]}
    routes.handle_post_module_unit_scope(handler, _parsed(), payload, None)
    body = handler.json()
    assert handler.status == 200
    assert body['after'] == [1]


def test_module_unit_scope_rejects_module_outside_the_allow_list(monkeypatch):
    _fake_meta_store(monkeypatch)
    _patch_common(monkeypatch, GENERAL_ADMIN)
    handler = _FakeHandler()
    payload = {'actor_user_id': 1, 'module': 'estoque', 'unit_ids': [1]}
    with pytest.raises(ValueError):
        routes.handle_post_module_unit_scope(handler, _parsed(), payload, None)


@pytest.mark.parametrize('actor', [LOCAL_ADMIN, BUYER])
def test_non_configuration_roles_cannot_save_module_unit_scope(monkeypatch, actor):
    _fake_meta_store(monkeypatch)
    _patch_common(monkeypatch, actor)
    handler = _FakeHandler()
    payload = {'actor_user_id': actor['id'], 'module': 'terceirizados_colaboradores', 'unit_ids': [1]}
    with pytest.raises(PermissionError):
        routes.handle_post_module_unit_scope(handler, _parsed(), payload, None)
