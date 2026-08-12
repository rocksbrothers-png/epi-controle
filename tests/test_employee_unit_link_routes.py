"""Rotas de vínculo local do colaborador com a Unidade (ADR-0002 §13, PR B).

Estes testes existem por um motivo concreto: a primeira versão das rotas usava
`PERM_EMPLOYEES_UPDATE` e `actor_operational_unit_id` sem que o módulo os
importasse. A suíte de serviço passava — ela nunca chama os handlers — e só o
`ruff` (F821) apontou. Um teste que executa o handler transforma esse erro em
falha de teste, que é onde ele deveria aparecer.

O foco é a AUTORIZAÇÃO: para perfis escopados por Unidade o backend deriva a
Unidade do ator e ignora o `unit_id` do payload. Se essa regra afrouxar, o
escopo por Unidade vira sugestão.
"""

import io
import json
from urllib.parse import urlparse

import pytest

from modules.employees import routes


class _FakeHandler:
    def __init__(self, path='/api/employees/100/link'):
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


class _FakeConn:
    def commit(self):
        pass

    def close(self):
        pass


class _Match:
    def __init__(self, value='100'):
        self._value = value

    def group(self, _n):
        return self._value


OUTSOURCED = {
    'id': 100, 'company_id': 7, 'unit_id': 10,
    'name': 'Terceirizado', 'tipo_vinculo': 'Terceirizado',
}
OWN = {
    'id': 101, 'company_id': 7, 'unit_id': 10,
    'name': 'Próprio', 'tipo_vinculo': 'CLT',
}


_DEFAULT_UNIT = object()


def _patch(monkeypatch, *, actor, employee=OUTSOURCED, unit=_DEFAULT_UNIT,
           operational_unit=None, created=None):
    # Sentinela em vez de `None`: `unit=None` explícito significa "Unidade
    # não encontrada", e com o default `None` o helper substituía esse caso
    # pela Unidade válida — o teste do 404 nunca exercitava o 404.
    unit = {'id': 11, 'company_id': 7, 'name': 'A2'} if unit is _DEFAULT_UNIT else unit
    monkeypatch.setattr(routes, 'get_connection', _FakeConn)
    monkeypatch.setattr(routes, 'resolve_actor_user_id', lambda *a, **k: actor['id'])
    monkeypatch.setattr(routes, 'authorize_action_any', lambda *a, **k: actor)
    monkeypatch.setattr(routes, 'get_employee_by_id', lambda *a, **k: employee)
    monkeypatch.setattr(routes, 'get_unit_by_id', lambda *a, **k: unit)
    monkeypatch.setattr(routes, 'ensure_resource_company', lambda *a, **k: None)
    monkeypatch.setattr(routes, 'ensure_module_enabled_for_unit', lambda *a, **k: None)
    monkeypatch.setattr(routes, 'actor_operational_unit_id', lambda *a, **k: operational_unit)
    monkeypatch.setattr(routes, '_audit_employee_unit_link', lambda *a, **k: None)
    monkeypatch.setattr(
        routes, 'create_employee_unit_link',
        lambda _c, employee_id, company_id, unit_id, actor_id: (
            created.append({'employee_id': employee_id, 'unit_id': unit_id}) or 501
        ),
    )


def _post_link(handler, payload):
    return routes.handle_post_employee_unit_link(
        handler, urlparse(handler.path), payload, _Match(),
    )


# ── o handler executa (pega NameError de import faltando) ───────────────────

def test_linking_succeeds_for_a_non_scoped_actor_informing_the_unit(monkeypatch):
    created = []
    _patch(monkeypatch, actor={'id': 1, 'role': 'general_admin', 'company_id': 7}, created=created)
    h = _FakeHandler()
    _post_link(h, {'unit_id': 11})
    assert h.status == 201
    assert created == [{'employee_id': 100, 'unit_id': 11}]


# ── autorização: quem é escopado não escolhe a Unidade ──────────────────────

@pytest.mark.parametrize('role', ['admin', 'user'])
def test_scoped_actor_gets_the_unit_derived_and_the_payload_ignored(monkeypatch, role):
    """O ator escopado manda unit_id=999 no payload e é ignorado: vale a
    Unidade operacional dele. Sem isto, o escopo por Unidade seria
    contornável por quem monta o request."""
    created = []
    _patch(
        monkeypatch,
        actor={'id': 2, 'role': role, 'company_id': 7},
        operational_unit=11,
        created=created,
    )
    h = _FakeHandler()
    _post_link(h, {'unit_id': 999})
    assert h.status == 201
    assert created == [{'employee_id': 100, 'unit_id': 11}]


@pytest.mark.parametrize('role', ['admin', 'user'])
def test_scoped_actor_without_operational_unit_is_refused(monkeypatch, role):
    _patch(
        monkeypatch,
        actor={'id': 2, 'role': role, 'company_id': 7},
        operational_unit=None,
        created=[],
    )
    h = _FakeHandler()
    _post_link(h, {})
    assert h.status == 403


def test_non_scoped_actor_must_inform_the_unit(monkeypatch):
    _patch(monkeypatch, actor={'id': 1, 'role': 'general_admin', 'company_id': 7}, created=[])
    h = _FakeHandler()
    _post_link(h, {})
    assert h.status == 400


# ── regras de domínio ───────────────────────────────────────────────────────

def test_own_workforce_is_refused_with_400(monkeypatch):
    """Mesma regra do backfill: vínculo local é para mão de obra contratada."""
    _patch(monkeypatch, actor={'id': 1, 'role': 'general_admin', 'company_id': 7},
           employee=OWN, created=[])
    h = _FakeHandler()
    _post_link(h, {'unit_id': 11})
    assert h.status == 400
    assert 'mão de obra própria' in h.json()['error']


def test_unit_from_another_tenant_is_refused(monkeypatch):
    """O ator não escopado informa a Unidade; sem esta checagem ele poderia
    apontar para a Unidade de outro tenant e criar vínculo atravessando a
    fronteira."""
    _patch(
        monkeypatch,
        actor={'id': 1, 'role': 'general_admin', 'company_id': 7},
        unit={'id': 11, 'company_id': 99, 'name': 'De outro tenant'},
        created=[],
    )
    h = _FakeHandler()
    _post_link(h, {'unit_id': 11})
    assert h.status == 400


def test_missing_employee_returns_404(monkeypatch):
    _patch(monkeypatch, actor={'id': 1, 'role': 'general_admin', 'company_id': 7},
           employee=None, created=[])
    h = _FakeHandler()
    _post_link(h, {'unit_id': 11})
    assert h.status == 404


def test_missing_unit_returns_404(monkeypatch):
    _patch(monkeypatch, actor={'id': 1, 'role': 'general_admin', 'company_id': 7},
           unit=None, created=[])
    h = _FakeHandler()
    _post_link(h, {'unit_id': 11})
    assert h.status == 404
