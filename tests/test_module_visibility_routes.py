"""Rotas GET/POST /api/module-visibility (Configuração → Regras →
Visualização, personalização pelo Administrador Geral).

Cobre a autoridade do endpoint (require_configuration_admin — o mesmo gate
de /api/configuration-rules, NÃO o gate master_admin-only do framework de
hardening) e a auditoria de toda mudança de visibilidade
(register_company_audit, evento "visibility_config_updated").

PR19 estende a rota POST para aceitar `unit_id` (override por Unidade,
válido só para papéis em _UNIT_SCOPED_ROLES — admin/user) e a auditoria
para registrar a unidade afetada. A validação de negócio (papel não
escopável, unidade fora do tenant) já é feita por
modules.settings.service.save_module_visibility, que levanta ValueError —
o dispatcher genérico de app.py converte isso em HTTP 400
(ver `except ValueError as exc: ... bad_request(self, str(exc))` nos
handlers GET/POST/PUT/DELETE), então testamos aqui apenas que a exceção
se propaga a partir da rota.
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


class _FakeUnitsConn(_FakeConn):
    """Conexão fake que responde à query de unidades do tenant, usada por
    _configuration_scope_unit_ids (validação de pertencimento quando a rota
    recebe unit_id)."""

    def __init__(self, unit_ids):
        self._unit_ids = set(unit_ids)

    def execute(self, _sql, _params=()):
        return _FakeUnitsRows([{'id': unit_id} for unit_id in self._unit_ids])


class _FakeUnitsRows:
    def __init__(self, rows):
        self._rows = rows

    def fetchall(self):
        return self._rows


def _fake_meta_store(monkeypatch):
    store = {}
    monkeypatch.setattr(settings_service, 'get_meta', lambda _conn, key: store.get(key))
    monkeypatch.setattr(settings_service, 'set_meta', lambda _conn, key, value: store.__setitem__(key, value))
    return store


def _patch_common(monkeypatch, actor, connection_factory=_FakeConn):
    monkeypatch.setattr(routes, 'get_connection', connection_factory)
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
    assert body['module_visibility']['buyer']['*']['estoque'] is False


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


# ── POST com unit_id: override por Unidade (PR19) ───────────────────────────

def test_general_admin_saves_module_visibility_with_unit_id_and_it_is_audited(monkeypatch):
    _fake_meta_store(monkeypatch)
    _patch_common(monkeypatch, GENERAL_ADMIN, connection_factory=lambda: _FakeUnitsConn({9, 10}))
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
    payload = {'actor_user_id': 1, 'role': 'admin', 'modules': {'estoque': False}, 'unit_id': 9}
    routes.handle_post_module_visibility(handler, _parsed(), payload, None)

    assert handler.status == 200
    body = handler.json()
    assert body['ok'] is True
    assert body['unit_id'] == 9
    assert body['before'] == {'estoque': True}  # admin tem estoque=True por padrão na base "*"
    assert body['after'] == {'estoque': False}

    assert len(audits) == 1
    entry = audits[0]
    assert entry['details']['unit_id'] == 9
    assert '9' in entry['summary'] or 'unidade' in entry['summary'].lower()


def test_post_module_visibility_without_unit_id_audits_unit_id_none(monkeypatch):
    _fake_meta_store(monkeypatch)
    _patch_common(monkeypatch, GENERAL_ADMIN)
    audits = []
    monkeypatch.setattr(
        'modules.companies.service.register_company_audit',
        lambda connection, company_id, actor, action_type, summary, details=None, **kwargs:
            audits.append({'details': details}),
    )
    handler = _FakeHandler()
    payload = {'actor_user_id': 1, 'role': 'buyer', 'modules': {'estoque': True}}
    routes.handle_post_module_visibility(handler, _parsed(), payload, None)
    assert handler.json()['unit_id'] is None
    assert audits[0]['details']['unit_id'] is None


def test_post_module_visibility_rejects_unit_id_for_role_not_unit_scoped(monkeypatch):
    # general_admin não está em _UNIT_SCOPED_ROLES — só admin/user (vínculo de
    # unidade única) fazem sentido com override por Unidade.
    _fake_meta_store(monkeypatch)
    _patch_common(monkeypatch, GENERAL_ADMIN, connection_factory=lambda: _FakeUnitsConn({9}))
    monkeypatch.setattr('modules.companies.service.register_company_audit', lambda *a, **k: None)
    handler = _FakeHandler()
    payload = {'actor_user_id': 1, 'role': 'general_admin', 'modules': {'estoque': True}, 'unit_id': 9}
    with pytest.raises(ValueError):
        routes.handle_post_module_visibility(handler, _parsed(), payload, None)


def test_post_module_visibility_rejects_unit_id_outside_tenant(monkeypatch):
    _fake_meta_store(monkeypatch)
    _patch_common(monkeypatch, GENERAL_ADMIN, connection_factory=lambda: _FakeUnitsConn({9, 10}))
    monkeypatch.setattr('modules.companies.service.register_company_audit', lambda *a, **k: None)
    handler = _FakeHandler()
    payload = {'actor_user_id': 1, 'role': 'admin', 'modules': {'estoque': True}, 'unit_id': 99}
    with pytest.raises(ValueError):
        routes.handle_post_module_visibility(handler, _parsed(), payload, None)


@pytest.mark.parametrize('actor', [LOCAL_ADMIN, BUYER])
def test_non_configuration_roles_cannot_save_module_visibility_with_unit_id(monkeypatch, actor):
    _fake_meta_store(monkeypatch)
    _patch_common(monkeypatch, actor, connection_factory=lambda: _FakeUnitsConn({9}))
    handler = _FakeHandler()
    payload = {'actor_user_id': actor['id'], 'role': 'admin', 'modules': {'estoque': True}, 'unit_id': 9}
    with pytest.raises(PermissionError):
        routes.handle_post_module_visibility(handler, _parsed(), payload, None)


def test_get_module_visibility_round_trips_per_unit_bucket(monkeypatch):
    _fake_meta_store(monkeypatch)
    _patch_common(monkeypatch, GENERAL_ADMIN, connection_factory=lambda: _FakeUnitsConn({9, 10}))
    monkeypatch.setattr('modules.companies.service.register_company_audit', lambda *a, **k: None)
    handler = _FakeHandler()
    routes.handle_post_module_visibility(
        handler, _parsed(),
        {'actor_user_id': 1, 'role': 'admin', 'modules': {'estoque': True}}, None,
    )
    routes.handle_post_module_visibility(
        handler, _parsed(),
        {'actor_user_id': 1, 'role': 'admin', 'modules': {'estoque': False}, 'unit_id': 9}, None,
    )

    get_handler = _FakeHandler()
    routes.handle_get_module_visibility(get_handler, _parsed(), {}, None)
    body = get_handler.json()
    assert body['module_visibility']['admin']['*']['estoque'] is True
    assert body['module_visibility']['admin']['9']['estoque'] is False
