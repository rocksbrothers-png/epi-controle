"""Rotas GET/POST /api/module-visibility (Configuração → Regras →
Visualização, personalização pelo Administrador Geral).

Cobre a autoridade do endpoint (require_configuration_admin — o mesmo gate
de /api/configuration-rules, NÃO o gate master_admin-only do framework de
hardening) e a auditoria de toda mudança de visibilidade
(register_company_audit, evento "visibility_config_updated").
"""

import io
import json
from urllib.parse import urlparse

import pytest

import modules.settings.routes as routes
import modules.settings.service as settings_service


class _FakeHandler:
    def __init__(self):
        self.path = '/api/module-visibility'
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
    def commit(self):
        pass

    def close(self):
        pass


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
    return urlparse(f'/api/module-visibility?{query}')


GENERAL_ADMIN = {'id': 1, 'role': 'general_admin', 'company_id': 7, 'full_name': 'Ana Geral'}
REGISTRY_ADMIN = {'id': 2, 'role': 'registry_admin', 'company_id': 7, 'full_name': 'Bea Registro'}
LOCAL_ADMIN = {'id': 3, 'role': 'admin', 'company_id': 7, 'full_name': 'Caio Local'}
BUYER = {'id': 4, 'role': 'buyer', 'company_id': 7, 'full_name': 'Duda Compras'}


# ── GET: leitura da configuração ────────────────────────────────────────────

def test_general_admin_can_read_module_visibility(monkeypatch):
    _fake_meta_store(monkeypatch)
    _patch_common(monkeypatch, GENERAL_ADMIN)
    handler = _FakeHandler()
    routes.handle_get_module_visibility(handler, _parsed(), {}, None)
    body = handler.json()
    assert handler.status == 200
    assert 'buyer' in body['module_visibility']
    assert body['module_visibility']['buyer']['estoque'] is False


def test_registry_admin_can_read_module_visibility(monkeypatch):
    # Mesma autoridade de /api/configuration-rules — não é master_admin-only
    # como o framework de hardening.
    _fake_meta_store(monkeypatch)
    _patch_common(monkeypatch, REGISTRY_ADMIN)
    handler = _FakeHandler()
    routes.handle_get_module_visibility(handler, _parsed(), {}, None)
    assert handler.status == 200


@pytest.mark.parametrize('actor', [LOCAL_ADMIN, BUYER])
def test_non_configuration_roles_cannot_read_module_visibility(monkeypatch, actor):
    _fake_meta_store(monkeypatch)
    _patch_common(monkeypatch, actor)
    handler = _FakeHandler()
    with pytest.raises(PermissionError):
        routes.handle_get_module_visibility(handler, _parsed(), {}, None)


# ── POST: gravação + auditoria ──────────────────────────────────────────────

def test_general_admin_saves_module_visibility_and_it_is_audited(monkeypatch):
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
    payload = {'actor_user_id': 1, 'role': 'buyer', 'modules': {'estoque': True}}
    routes.handle_post_module_visibility(handler, _parsed(), payload, None)

    assert handler.status == 200
    body = handler.json()
    assert body['ok'] is True
    assert body['before'] == {'estoque': False}
    assert body['after'] == {'estoque': True}

    assert len(audits) == 1
    entry = audits[0]
    assert entry['action_type'] == 'visibility_config_updated'
    assert entry['company_id'] == 7  # empresa do Administrador Geral (tenant)
    assert entry['actor']['id'] == GENERAL_ADMIN['id']
    assert entry['details']['role'] == 'buyer'
    assert entry['details']['before'] == {'estoque': False}
    assert entry['details']['after'] == {'estoque': True}


@pytest.mark.parametrize('actor', [LOCAL_ADMIN, BUYER])
def test_non_configuration_roles_cannot_save_module_visibility(monkeypatch, actor):
    _fake_meta_store(monkeypatch)
    _patch_common(monkeypatch, actor)
    handler = _FakeHandler()
    payload = {'actor_user_id': actor['id'], 'role': 'buyer', 'modules': {'estoque': True}}
    with pytest.raises(PermissionError):
        routes.handle_post_module_visibility(handler, _parsed(), payload, None)


def test_config_cannot_grant_a_module_beyond_the_technical_permission_ceiling(monkeypatch):
    # O comprador não tem fichas:view — mesmo o Administrador Geral tentando
    # liberar "fichas" via esta rota, o efetivo do ator continua fechado.
    # (a rota grava a config; quem aplica o teto é get_effective_module_
    # visibility, consumido pelo /api/bootstrap e por /api/auth/me.)
    _fake_meta_store(monkeypatch)
    _patch_common(monkeypatch, GENERAL_ADMIN)
    monkeypatch.setattr('modules.companies.service.register_company_audit', lambda *a, **k: None)
    handler = _FakeHandler()
    payload = {'actor_user_id': 1, 'role': 'buyer', 'modules': {'fichas': True}}
    routes.handle_post_module_visibility(handler, _parsed(), payload, None)
    assert handler.status == 200

    effective = settings_service.get_effective_module_visibility(
        _FakeConn(), {'company_id': 7, 'id': 4, 'role': 'buyer'},
    )
    assert effective['fichas'] is False
