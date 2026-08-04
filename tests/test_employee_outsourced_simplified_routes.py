"""Rotas POST /api/employees/outsourced-simplified e PUT .../outsourced-simplified/<id>
(Cadastro de Colaboradores — ADR-0002 §10.2/§10.3).

Cobre a autoridade do endpoint: permissão técnica
(employees:create_simplified/update_simplified) E autorização por módulo/
Unidade no BACKEND (ensure_module_enabled_for_unit) — a condição vinculante
da correção do usuário nesta sessão: "o backend deve validar o escopo por
Unidade em todas as operações, mesmo quando o menu estiver oculto no
frontend". Também cobre a auditoria (register_company_audit) de toda
criação/edição.

Não repete a validação de campos/isolamento multi-tenant da camada de
serviço — isso já é coberto em tests/test_employee_outsourced_simplified.py.
"""

import io
import json
from urllib.parse import urlparse

import pytest

import modules.employees.routes as routes


class _FakeHandler:
    def __init__(self):
        self.path = '/api/employees/outsourced-simplified'
        self.command = 'POST'
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


def _parsed(path='/api/employees/outsourced-simplified', query='actor_user_id=1'):
    return urlparse(f'{path}?{query}')


GENERAL_ADMIN = {'id': 1, 'role': 'general_admin', 'company_id': 7, 'full_name': 'Ana Geral'}
LOCAL_ADMIN = {'id': 3, 'role': 'admin', 'company_id': 7, 'full_name': 'Caio Local'}

EMPLOYEE_RECORD = {
    'id': 42, 'company_id': 7, 'unit_id': 5, 'name': 'Trabalhador Terceirizado',
    'tipo_vinculo': 'Terceirizado', 'outsourced_company_id': 9,
}

CREATE_PAYLOAD = {
    'actor_user_id': 1, 'company_id': 7, 'unit_id': 5, 'outsourced_company_id': 9,
    'name': 'Trabalhador Terceirizado', 'cpf': '111.444.777-35',
    'role_name': 'Auxiliar', 'tipo_vinculo': 'Terceirizado', 'admission_date': '2026-01-01',
}


def _patch_common(monkeypatch, actor, *, module_authorized=True):
    monkeypatch.setattr(routes, 'get_connection', _FakeConn)
    monkeypatch.setattr(routes, 'resolve_actor_user_id', lambda *a, **k: actor['id'])
    monkeypatch.setattr(routes, 'authorize_action', lambda *a, **k: actor)
    if module_authorized:
        monkeypatch.setattr(routes, 'ensure_module_enabled_for_unit', lambda *a, **k: None)
    else:
        def _deny(*_a, **_k):
            raise PermissionError('Módulo não autorizado para o seu perfil/unidade.')
        monkeypatch.setattr(routes, 'ensure_module_enabled_for_unit', _deny)


def _patch_audit(monkeypatch):
    audits = []
    monkeypatch.setattr(
        'modules.companies.service.register_company_audit',
        lambda connection, company_id, actor, action_type, summary, details=None, **kwargs:
            audits.append({
                'company_id': company_id, 'actor': actor, 'action_type': action_type,
                'summary': summary, 'details': details,
            }),
    )
    return audits


# ── POST: criação ────────────────────────────────────────────────────────────

def test_general_admin_creates_simplified_employee_and_it_is_audited(monkeypatch):
    _patch_common(monkeypatch, GENERAL_ADMIN)
    audits = _patch_audit(monkeypatch)
    monkeypatch.setattr(routes, 'create_employee_outsourced_simplified', lambda connection, payload, actor: 42)
    monkeypatch.setattr(routes, 'get_employee_by_id', lambda connection, employee_id: EMPLOYEE_RECORD)

    handler = _FakeHandler()
    routes.handle_post_employee_outsourced_simplified(handler, _parsed(), dict(CREATE_PAYLOAD), None)

    assert handler.status == 201
    body = handler.json()
    assert body['ok'] is True
    assert body['id'] == 42

    assert len(audits) == 1
    entry = audits[0]
    assert entry['action_type'] == 'employee_outsourced_simplified_created'
    assert entry['company_id'] == 7
    assert entry['details']['employee_id'] == 42
    assert entry['details']['outsourced_company_id'] == 9


def test_create_blocked_without_technical_permission(monkeypatch):
    def _deny_permission(*_a, **_k):
        raise PermissionError('Permissão negada.')
    monkeypatch.setattr(routes, 'get_connection', _FakeConn)
    monkeypatch.setattr(routes, 'resolve_actor_user_id', lambda *a, **k: LOCAL_ADMIN['id'])
    monkeypatch.setattr(routes, 'authorize_action', _deny_permission)

    handler = _FakeHandler()
    with pytest.raises(PermissionError):
        routes.handle_post_employee_outsourced_simplified(handler, _parsed(), dict(CREATE_PAYLOAD), None)


def test_create_blocked_when_module_not_authorized_for_unit_even_with_permission(monkeypatch):
    # Condição vinculante: mesmo com employees:create_simplified concedida,
    # o backend não pode confiar no menu do cliente — a autorização por
    # módulo/Unidade é obrigatória e independente.
    _patch_common(monkeypatch, LOCAL_ADMIN, module_authorized=False)
    called = {'create': False}
    monkeypatch.setattr(
        routes, 'create_employee_outsourced_simplified',
        lambda connection, payload, actor: called.__setitem__('create', True) or 42,
    )

    handler = _FakeHandler()
    with pytest.raises(PermissionError):
        routes.handle_post_employee_outsourced_simplified(handler, _parsed(), dict(CREATE_PAYLOAD), None)
    assert called['create'] is False


def test_create_requires_all_fields(monkeypatch):
    _patch_common(monkeypatch, GENERAL_ADMIN)
    handler = _FakeHandler()
    incomplete = dict(CREATE_PAYLOAD)
    incomplete.pop('outsourced_company_id')
    with pytest.raises(Exception):
        routes.handle_post_employee_outsourced_simplified(handler, _parsed(), incomplete, None)


# ── PUT: edição ──────────────────────────────────────────────────────────────

def test_general_admin_updates_simplified_employee_and_it_is_audited(monkeypatch):
    _patch_common(monkeypatch, GENERAL_ADMIN)
    audits = _patch_audit(monkeypatch)
    monkeypatch.setattr(routes, 'get_employee_by_id', lambda connection, employee_id: EMPLOYEE_RECORD)
    monkeypatch.setattr(routes, 'update_employee_outsourced_simplified', lambda *a, **k: None)

    handler = _FakeHandler()
    update_payload = {
        'actor_user_id': 1, 'company_id': 7, 'unit_id': 5, 'outsourced_company_id': 9,
        'name': 'Trabalhador Terceirizado', 'cpf': '111.444.777-35',
        'role_name': 'Auxiliar', 'tipo_vinculo': 'Terceirizado', 'admission_date': '2026-01-01',
    }
    match = type('M', (), {'group': lambda self, i: '42'})()
    routes.handle_put_employee_outsourced_simplified(handler, _parsed(), update_payload, match)

    assert handler.status == 200
    body = handler.json()
    assert body['ok'] is True
    assert len(audits) == 1
    assert audits[0]['action_type'] == 'employee_outsourced_simplified_updated'


def test_update_returns_404_when_employee_not_found(monkeypatch):
    monkeypatch.setattr(routes, 'get_connection', _FakeConn)
    monkeypatch.setattr(routes, 'get_employee_by_id', lambda connection, employee_id: None)

    handler = _FakeHandler()
    update_payload = {
        'actor_user_id': 1, 'unit_id': 5, 'outsourced_company_id': 9,
        'name': 'X', 'cpf': '111.444.777-35', 'role_name': 'Auxiliar',
        'tipo_vinculo': 'Terceirizado', 'admission_date': '2026-01-01',
    }
    match = type('M', (), {'group': lambda self, i: '999'})()
    result = routes.handle_put_employee_outsourced_simplified(handler, _parsed(), update_payload, match)
    assert handler.status == 404


def test_update_blocked_when_module_not_authorized_for_unit(monkeypatch):
    monkeypatch.setattr(routes, 'get_connection', _FakeConn)
    monkeypatch.setattr(routes, 'get_employee_by_id', lambda connection, employee_id: EMPLOYEE_RECORD)
    _patch_common(monkeypatch, LOCAL_ADMIN, module_authorized=False)
    called = {'update': False}
    monkeypatch.setattr(
        routes, 'update_employee_outsourced_simplified',
        lambda *a, **k: called.__setitem__('update', True),
    )

    handler = _FakeHandler()
    update_payload = {
        'actor_user_id': 3, 'unit_id': 5, 'outsourced_company_id': 9,
        'name': 'X', 'cpf': '111.444.777-35', 'role_name': 'Auxiliar',
        'tipo_vinculo': 'Terceirizado', 'admission_date': '2026-01-01',
    }
    match = type('M', (), {'group': lambda self, i: '42'})()
    with pytest.raises(PermissionError):
        routes.handle_put_employee_outsourced_simplified(handler, _parsed(), update_payload, match)
    assert called['update'] is False
