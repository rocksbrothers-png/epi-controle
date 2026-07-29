"""Negativo: um colaborador não pode assinar/avaliar recursos de outro
colaborador manipulando `delivery_id`/`epi_id` no portal externo.

O portal (`/api/employee-sign`, `/api/employee-feedback`) não recebe
`employee_id` do cliente — a identidade vem exclusivamente da resolução do
`token` (`resolve_external_employee_context`). O único vetor de manipulação
disponível ao atacante é o ID do recurso-alvo (entrega, EPI); estes testes
travam a verificação de posse que barra esse vetor — nenhum teste cobria
isso antes (gap encontrado nesta auditoria).
"""

import io
import json
from urllib.parse import urlparse

import pytest

import modules.portal.routes as routes


class _FakeHandler:
    def __init__(self):
        self.path = '/api/employee-sign'
        self.command = 'POST'
        self.status = None
        self.wfile = io.BytesIO()
        self.headers = {}

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


PORTAL_EMPLOYEE = {
    'employee_id': 42, 'company_id': 5, 'unit_id': 3,
    'employee_name': 'Ana', 'employee_id_code': 'EMP-042',
}
OTHER_EMPLOYEES_DELIVERY = {'id': 900, 'employee_id': 999}
OWN_DELIVERY = {'id': 901, 'employee_id': 42}


def _parsed():
    return urlparse('/api/employee-sign')


def _patch_portal_common(monkeypatch, *, portal_context=PORTAL_EMPLOYEE):
    monkeypatch.setattr(routes, 'get_connection', _FakeConn)
    monkeypatch.setattr(routes, 'resolve_external_employee_context', lambda *a, **k: portal_context)
    monkeypatch.setattr(routes, 'register_employee_portal_audit', lambda *a, **k: None)


def test_signing_another_employees_delivery_is_denied(monkeypatch):
    _patch_portal_common(monkeypatch)
    monkeypatch.setattr(routes, 'get_delivery_for_employee', lambda _c, delivery_id: OTHER_EMPLOYEES_DELIVERY)
    signed = []
    monkeypatch.setattr(routes, 'sign_delivery', lambda *a, **k: signed.append(a))
    monkeypatch.setattr(routes, 'sign_ficha_items_by_delivery', lambda *a, **k: signed.append(a))

    payload = {
        'token': 'tok-ana', 'delivery_id': OTHER_EMPLOYEES_DELIVERY['id'],
        'signature_name': 'Ana', 'signature_data': '',
    }
    with pytest.raises(PermissionError, match='não pertence ao funcionário'):
        routes.handle_post_employee_sign(_FakeHandler(), _parsed(), payload, None)

    # Nenhuma escrita aconteceu — a negação veio antes de qualquer sign_*.
    assert signed == []


def test_signing_own_delivery_succeeds(monkeypatch):
    _patch_portal_common(monkeypatch)
    monkeypatch.setattr(routes, 'get_delivery_for_employee', lambda _c, delivery_id: OWN_DELIVERY)
    signed = []
    monkeypatch.setattr(routes, 'sign_delivery', lambda *a, **k: signed.append(('delivery', a)))
    monkeypatch.setattr(routes, 'sign_ficha_items_by_delivery', lambda *a, **k: signed.append(('ficha', a)))

    payload = {
        'token': 'tok-ana', 'delivery_id': OWN_DELIVERY['id'],
        'signature_name': 'Ana', 'signature_data': '',
    }
    h = _FakeHandler()
    routes.handle_post_employee_sign(h, _parsed(), payload, None)

    assert h.status == 200
    assert h.json()['ok'] is True
    assert len(signed) == 2


def test_signing_nonexistent_delivery_returns_not_found(monkeypatch):
    _patch_portal_common(monkeypatch)
    monkeypatch.setattr(routes, 'get_delivery_for_employee', lambda _c, delivery_id: None)

    payload = {'token': 'tok-ana', 'delivery_id': 999999, 'signature_name': 'Ana', 'signature_data': ''}
    with pytest.raises(ValueError, match='Entrega não encontrada'):
        routes.handle_post_employee_sign(_FakeHandler(), _parsed(), payload, None)


def test_feedback_for_epi_of_another_company_is_denied(monkeypatch):
    monkeypatch.setattr(routes, 'get_connection', _FakeConn)
    monkeypatch.setattr(routes, 'resolve_external_employee_context', lambda *a, **k: PORTAL_EMPLOYEE)
    monkeypatch.setattr(routes, 'get_epi_by_id', lambda _c, epi_id: {'id': epi_id, 'company_id': 999, 'unit_id': None})

    payload = {'token': 'tok-ana', 'epi_id': 7, 'type': 'avaliacao', 'comfort_rating': 5}
    with pytest.raises(PermissionError, match='EPI inválido'):
        routes.handle_post_employee_feedback(_FakeHandler(), _parsed(), payload, None)
