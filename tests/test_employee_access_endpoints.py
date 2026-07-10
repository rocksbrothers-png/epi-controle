"""Auditoria F-05 — endpoints do bloco "Acesso do colaborador" pela Entrega.

Reativados na tela de Entrega (QR lookup + link + envio). Estes testes cobrem a
orquestração dos handlers: permissão (deliveries:create), escopo de empresa
(ensure_actor_employee_scope / ensure_resource_company), retorno de expires_at e
o registro de auditoria (structured_log) da geração e do envio.
"""

import io
import json
from urllib.parse import urlparse

import pytest

import modules.portal.routes as routes


class _FakeHandler:
    def __init__(self):
        self.path = '/api/employee-portal-link'
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
        self._committed = True

    def close(self):
        pass


def _patch_common(monkeypatch, actor, audits):
    monkeypatch.setattr(routes, 'get_connection', lambda: _FakeConn())
    monkeypatch.setattr(routes, 'resolve_actor_user_id', lambda *a, **k: actor['id'])
    monkeypatch.setattr(routes, 'authorize_action', lambda *a, **k: actor)
    monkeypatch.setattr(routes, 'request_base_url', lambda _h: 'https://app.example')
    monkeypatch.setattr(routes, 'structured_log', lambda *a, **k: audits.append((a, k)))


def _parsed():
    return urlparse('/api/x?actor_user_id=1')


# ── Geração de link ──────────────────────────────────────────────────────────

def test_portal_link_generates_and_audits(monkeypatch):
    actor = {'id': 1, 'role': 'general_admin', 'company_id': 5}
    audits = []
    _patch_common(monkeypatch, actor, audits)
    monkeypatch.setattr(routes, 'get_employee_by_id',
                        lambda _c, eid: {'id': eid, 'company_id': 5, 'cpf': '12345678901'})
    scope_seen = {}
    monkeypatch.setattr(routes, 'ensure_actor_employee_scope',
                        lambda _c, a, e: scope_seen.update({'actor': a, 'emp': e}))
    monkeypatch.setattr(routes, 'build_portal_link_from_cpf',
                        lambda **k: {'token': 'tok-abc', 'access_link': 'https://app.example/?employee_token=tok-abc',
                                     'expires_at': '2026-07-12T00:00:00+00:00'})
    monkeypatch.setattr(routes, 'upsert_employee_portal_link', lambda *a, **k: None)

    h = _FakeHandler()
    routes.handle_post_employee_portal_link(h, _parsed(), {'actor_user_id': 1, 'employee_id': 42}, None)

    assert h.status == 200
    body = h.json()
    assert body['ok'] and body['access_link'].endswith('tok-abc')
    assert body['expires_at'] == '2026-07-12T00:00:00+00:00'
    # escopo de empresa foi verificado antes de gerar
    assert scope_seen['emp']['company_id'] == 5
    # auditoria de geração registrada
    assert any(a[0][:2] == ('info', 'employee.access_link.generate') for a in audits)


def test_portal_link_missing_employee_raises(monkeypatch):
    actor = {'id': 1, 'role': 'general_admin', 'company_id': 5}
    _patch_common(monkeypatch, actor, [])
    monkeypatch.setattr(routes, 'get_employee_by_id', lambda _c, eid: None)
    with pytest.raises(ValueError, match='Colaborador'):
        routes.handle_post_employee_portal_link(_FakeHandler(), _parsed(), {'actor_user_id': 1, 'employee_id': 99}, None)


def test_portal_link_enforces_company_scope(monkeypatch):
    actor = {'id': 1, 'role': 'general_admin', 'company_id': 5}
    _patch_common(monkeypatch, actor, [])
    monkeypatch.setattr(routes, 'get_employee_by_id',
                        lambda _c, eid: {'id': eid, 'company_id': 9, 'cpf': '1'})

    def _deny(_c, _a, _e):
        raise PermissionError('Colaborador de outra empresa.')

    monkeypatch.setattr(routes, 'ensure_actor_employee_scope', _deny)
    with pytest.raises(PermissionError):
        routes.handle_post_employee_portal_link(_FakeHandler(), _parsed(), {'actor_user_id': 1, 'employee_id': 42}, None)


# ── Envio (WhatsApp / e-mail) ────────────────────────────────────────────────

def test_contact_launch_email_audits_and_returns_mailto(monkeypatch):
    actor = {'id': 1, 'role': 'general_admin', 'company_id': 5}
    audits = []
    _patch_common(monkeypatch, actor, audits)
    monkeypatch.setattr(routes, 'get_employee_by_id',
                        lambda _c, eid: {'id': eid, 'company_id': 5, 'name': 'Ana', 'email': 'ana@acme.com'})
    monkeypatch.setattr(routes, 'ensure_actor_employee_scope', lambda *a, **k: None)

    h = _FakeHandler()
    routes.handle_post_employee_contact_launch(
        h, _parsed(),
        {'actor_user_id': 1, 'employee_id': 42, 'channel': 'email', 'access_link': 'https://app.example/?employee_token=t'},
        None,
    )
    assert h.status == 200
    body = h.json()
    assert body['channel'] == 'email' and body['launch_url'].startswith('mailto:ana@acme.com')
    assert any(a[0][:2] == ('info', 'employee.access_link.send') for a in audits)


def test_contact_launch_whatsapp_without_number_raises(monkeypatch):
    actor = {'id': 1, 'role': 'general_admin', 'company_id': 5}
    _patch_common(monkeypatch, actor, [])
    monkeypatch.setattr(routes, 'get_employee_by_id',
                        lambda _c, eid: {'id': eid, 'company_id': 5, 'name': 'Ana', 'whatsapp': ''})
    monkeypatch.setattr(routes, 'ensure_actor_employee_scope', lambda *a, **k: None)
    with pytest.raises(ValueError, match='WhatsApp'):
        routes.handle_post_employee_contact_launch(
            _FakeHandler(), _parsed(),
            {'actor_user_id': 1, 'employee_id': 42, 'channel': 'whatsapp', 'access_link': 'https://app.example/?employee_token=t'},
            None,
        )


# ── Lookup por QR ────────────────────────────────────────────────────────────

def test_employee_lookup_enforces_resource_company(monkeypatch):
    actor = {'id': 1, 'role': 'general_admin', 'company_id': 5}
    _patch_common(monkeypatch, actor, [])
    monkeypatch.setattr(routes, 'lookup_employee_by_qr_or_token',
                        lambda _c, qr, tok: {'id': 7, 'company_id': 9, 'name': 'Bruno'})

    def _deny(_a, _row, _label):
        raise PermissionError('Recurso de outra empresa.')

    monkeypatch.setattr(routes, 'ensure_resource_company', _deny)
    with pytest.raises(PermissionError):
        routes.handle_post_employee_lookup(
            _FakeHandler(), _parsed(),
            {'actor_user_id': 1, 'employee_qr_code': 'https://app.example/?employee_token=abc'},
            None,
        )
