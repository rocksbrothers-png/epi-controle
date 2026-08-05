"""Auditoria de responsabilidade pelo EPI — PR 5 (ADR-0002).

Cobre dois eventos dedicados, além do `outsourced_company_updated`/
`outsourced_company_created` genéricos já implementados no PR 1:

  - `epi_responsibility_changed`: quando o default da empresa terceirizada
    muda (PUT /api/outsourced-companies/{id});
  - `epi_responsibility_override_set`: quando a exceção individual do
    colaborador é criada, alterada ou removida (POST/PUT /api/employees).

Ambos só disparam quando o valor de fato muda — não a cada create/update —
para não poluir a trilha de auditoria com entradas sem informação nova.
"""

import io
import json
from urllib.parse import urlparse

import modules.employees.routes as employees_routes
import modules.outsourced_companies.routes as oc_routes


class _FakeHandler:
    def __init__(self):
        self.path = '/api/x'
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


def _match(value):
    return type('M', (), {'group': lambda self, i: value})()


def _capture_audit(monkeypatch, module):
    calls = []

    def _fake(_conn, company_id, actor, action_type, summary, details=None, **kwargs):
        calls.append({'action_type': action_type, 'company_id': company_id, 'summary': summary, 'details': details})

    monkeypatch.setattr('core.audit.register_company_audit', _fake)
    return calls


# ── colaborador: exceção individual (POST) ─────────────────────────────────

def test_post_employee_audits_override_when_set(monkeypatch):
    actor = {'id': 1, 'full_name': 'Admin', 'role': 'general_admin', 'company_id': 1}
    monkeypatch.setattr(employees_routes, 'get_connection', _DummyConnection)
    monkeypatch.setattr(employees_routes, 'resolve_actor_user_id', lambda *a, **k: 1)
    monkeypatch.setattr(employees_routes, 'authorize_action', lambda *a, **k: actor)
    monkeypatch.setattr(employees_routes, 'create_employee', lambda *a, **k: 42)
    monkeypatch.setattr(employees_routes, 'get_employee_by_id', lambda _c, eid: {
        'id': eid, 'name': 'Carlos', 'epi_responsibility_override': 'Empresa Contratante',
        'epi_responsibility_override_reason': 'Acordo pontual',
    })
    calls = _capture_audit(monkeypatch, employees_routes)

    payload = {
        'actor_user_id': 1, 'company_id': 1, 'employee_id_code': 'E1', 'cpf': '12345678901',
        'name': 'Carlos', 'sector': 'Op', 'role_name': 'Tec', 'admission_date': '2026-01-01',
        'schedule_type': 'integral',
    }
    h = _FakeHandler()
    employees_routes.handle_post_employees(h, _parsed(), payload, None)
    assert h.status == 201
    assert len(calls) == 1
    assert calls[0]['action_type'] == 'epi_responsibility_override_set'
    assert calls[0]['details'][0]['after'] == 'Empresa Contratante'


def test_post_employee_does_not_audit_when_no_override(monkeypatch):
    actor = {'id': 1, 'full_name': 'Admin', 'role': 'general_admin', 'company_id': 1}
    monkeypatch.setattr(employees_routes, 'get_connection', _DummyConnection)
    monkeypatch.setattr(employees_routes, 'resolve_actor_user_id', lambda *a, **k: 1)
    monkeypatch.setattr(employees_routes, 'authorize_action', lambda *a, **k: actor)
    monkeypatch.setattr(employees_routes, 'create_employee', lambda *a, **k: 42)
    monkeypatch.setattr(employees_routes, 'get_employee_by_id', lambda _c, eid: {
        'id': eid, 'name': 'Ana', 'epi_responsibility_override': '', 'epi_responsibility_override_reason': '',
    })
    calls = _capture_audit(monkeypatch, employees_routes)

    payload = {
        'actor_user_id': 1, 'company_id': 1, 'employee_id_code': 'E2', 'cpf': '12345678901',
        'name': 'Ana', 'sector': 'Op', 'role_name': 'Tec', 'admission_date': '2026-01-01',
        'schedule_type': 'integral',
    }
    h = _FakeHandler()
    employees_routes.handle_post_employees(h, _parsed(), payload, None)
    assert h.status == 201
    assert calls == []


# ── colaborador: exceção individual (PUT) ──────────────────────────────────

def test_put_employee_audits_only_when_override_changes(monkeypatch):
    actor = {'id': 1, 'full_name': 'Admin', 'role': 'general_admin', 'company_id': 1}
    monkeypatch.setattr(employees_routes, 'get_connection', _DummyConnection)
    monkeypatch.setattr(employees_routes, 'resolve_actor_user_id', lambda *a, **k: 1)
    monkeypatch.setattr(employees_routes, 'authorize_action', lambda *a, **k: actor)
    monkeypatch.setattr(employees_routes, 'update_employee', lambda *a, **k: None)

    # current (antes do PUT): override vazio. depois: preenchido -> deve auditar.
    responses = iter([
        {'id': 42, 'name': 'Carlos', 'epi_responsibility_override': ''},
        {'id': 42, 'name': 'Carlos', 'epi_responsibility_override': 'Empresa Terceirizada',
         'epi_responsibility_override_reason': 'Mudança de contrato'},
    ])
    monkeypatch.setattr(employees_routes, 'get_employee_by_id', lambda _c, eid: next(responses))
    calls = _capture_audit(monkeypatch, employees_routes)

    payload = {
        'actor_user_id': 1, 'company_id': 1, 'unit_id': 7, 'employee_id_code': 'E1', 'cpf': '12345678901',
        'name': 'Carlos', 'sector': 'Op', 'role_name': 'Tec', 'admission_date': '2026-01-01',
        'schedule_type': 'integral',
    }
    h = _FakeHandler()
    employees_routes.handle_put_employee(h, _parsed(), payload, _match('42'))
    assert h.status == 200
    assert len(calls) == 1
    assert calls[0]['action_type'] == 'epi_responsibility_override_set'
    assert calls[0]['details'][0]['before'] == ''
    assert calls[0]['details'][0]['after'] == 'Empresa Terceirizada'


def test_put_employee_does_not_audit_when_override_unchanged(monkeypatch):
    actor = {'id': 1, 'full_name': 'Admin', 'role': 'general_admin', 'company_id': 1}
    monkeypatch.setattr(employees_routes, 'get_connection', _DummyConnection)
    monkeypatch.setattr(employees_routes, 'resolve_actor_user_id', lambda *a, **k: 1)
    monkeypatch.setattr(employees_routes, 'authorize_action', lambda *a, **k: actor)
    monkeypatch.setattr(employees_routes, 'update_employee', lambda *a, **k: None)
    same = {'id': 42, 'name': 'Carlos', 'epi_responsibility_override': 'Empresa Contratante',
            'epi_responsibility_override_reason': 'Acordo pontual'}
    monkeypatch.setattr(employees_routes, 'get_employee_by_id', lambda _c, eid: same)
    calls = _capture_audit(monkeypatch, employees_routes)

    payload = {
        'actor_user_id': 1, 'company_id': 1, 'unit_id': 7, 'employee_id_code': 'E1', 'cpf': '12345678901',
        'name': 'Carlos', 'sector': 'Op', 'role_name': 'Tec', 'admission_date': '2026-01-01',
        'schedule_type': 'integral',
    }
    h = _FakeHandler()
    employees_routes.handle_put_employee(h, _parsed(), payload, _match('42'))
    assert h.status == 200
    assert calls == []


# ── empresa terceirizada: default de responsabilidade (PUT) ───────────────

def test_put_outsourced_company_audits_responsibility_change_as_dedicated_event(monkeypatch):
    actor = {'id': 1, 'full_name': 'Admin', 'role': 'general_admin', 'company_id': 1}
    monkeypatch.setattr(oc_routes, 'get_connection', _DummyConnection)
    monkeypatch.setattr(oc_routes, 'resolve_actor_user_id', lambda *a, **k: 1)
    monkeypatch.setattr(oc_routes, 'authorize_action_any', lambda *a, **k: actor)
    monkeypatch.setattr(oc_routes, 'ensure_company_access', lambda *a, **k: None)
    monkeypatch.setattr(oc_routes, 'ensure_module_enabled_for_unit', lambda *a, **k: None)
    monkeypatch.setattr(oc_routes, 'update_outsourced_company', lambda *a, **k: None)
    monkeypatch.setattr(oc_routes, 'get_outsourced_company_by_id', lambda _c, eid: {
        'id': eid, 'company_id': 1, 'legal_name': 'Terceirizada X', 'cnpj': '', 'company_kind': 'outsourced',
        'epi_responsibility': 'Conforme Contrato', 'status': 'Ativa',
    })
    calls = _capture_audit(monkeypatch, oc_routes)

    payload = {
        'actor_user_id': 1, 'legal_name': 'Terceirizada X', 'epi_responsibility': 'Empresa Terceirizada',
    }
    h = _FakeHandler()
    oc_routes.handle_put_outsourced_company(h, _parsed(), payload, _match('9'))
    assert h.status == 200
    action_types = [c['action_type'] for c in calls]
    assert action_types == ['outsourced_company_updated', 'epi_responsibility_changed']
    dedicated = calls[1]
    assert dedicated['details'][0]['before'] == 'Conforme Contrato'
    assert dedicated['details'][0]['after'] == 'Empresa Terceirizada'


def test_put_outsourced_company_no_dedicated_event_when_responsibility_unchanged(monkeypatch):
    actor = {'id': 1, 'full_name': 'Admin', 'role': 'general_admin', 'company_id': 1}
    monkeypatch.setattr(oc_routes, 'get_connection', _DummyConnection)
    monkeypatch.setattr(oc_routes, 'resolve_actor_user_id', lambda *a, **k: 1)
    monkeypatch.setattr(oc_routes, 'authorize_action_any', lambda *a, **k: actor)
    monkeypatch.setattr(oc_routes, 'ensure_company_access', lambda *a, **k: None)
    monkeypatch.setattr(oc_routes, 'ensure_module_enabled_for_unit', lambda *a, **k: None)
    monkeypatch.setattr(oc_routes, 'update_outsourced_company', lambda *a, **k: None)
    monkeypatch.setattr(oc_routes, 'get_outsourced_company_by_id', lambda _c, eid: {
        'id': eid, 'company_id': 1, 'legal_name': 'Terceirizada X', 'cnpj': '', 'company_kind': 'outsourced',
        'epi_responsibility': 'Conforme Contrato', 'status': 'Ativa',
    })
    calls = _capture_audit(monkeypatch, oc_routes)

    payload = {
        'actor_user_id': 1, 'legal_name': 'Terceirizada X Renomeada', 'epi_responsibility': 'Conforme Contrato',
    }
    h = _FakeHandler()
    oc_routes.handle_put_outsourced_company(h, _parsed(), payload, _match('9'))
    assert h.status == 200
    action_types = [c['action_type'] for c in calls]
    assert action_types == ['outsourced_company_updated']  # sem epi_responsibility_changed
