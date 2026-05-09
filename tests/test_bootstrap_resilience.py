from types import SimpleNamespace
from urllib.parse import urlparse

import pytest

import server_postgres as sp
from core.security import create_jwt_token, resolve_actor_user_id


BASE_ACTOR = {
    'id': 17,
    'username': 'daniel.lima',
    'full_name': 'Daniel Lima',
    'role': 'admin',
    'company_id': 2,
    'company_name': 'Norskan Offshore',
    'company_cnpj': '44.555.666/0001-81',
    'operational_unit_id': 4,
}


def _patch_successful_bootstrap_sections(monkeypatch):
    monkeypatch.setattr(sp, 'get_platform_brand', lambda connection: {'name': 'EPI Controle'})
    monkeypatch.setattr(sp, 'get_commercial_settings', lambda connection: {'plans': []})
    monkeypatch.setattr(sp, 'fetch_companies', lambda connection, company_id=None: [{'id': company_id or 1}])
    monkeypatch.setattr(sp, 'fetch_company_audit_logs', lambda connection, actor: [])
    monkeypatch.setattr(sp, 'fetch_ficha_epi_audit_logs', lambda connection, actor, filters: [])
    monkeypatch.setattr(sp, 'fetch_users', lambda connection, actor: [{'id': actor['id']}])
    monkeypatch.setattr(sp, 'fetch_units', lambda connection, actor: [{'id': 4, 'company_id': actor['company_id']}])
    monkeypatch.setattr(sp, 'fetch_employees', lambda connection, actor: [{'id': 21, 'unit_id': 4}])
    monkeypatch.setattr(sp, 'fetch_employee_movements', lambda connection, actor: [])
    monkeypatch.setattr(sp, 'fetch_epis', lambda connection, actor: [{'id': 9, 'unit_id': 4}])
    monkeypatch.setattr(sp, 'fetch_deliveries', lambda connection, actor: [{'id': 33}])
    monkeypatch.setattr(sp, 'fetch_feedbacks', lambda connection, actor: [])
    monkeypatch.setattr(sp, 'compute_alerts', lambda connection, actor: [])
    monkeypatch.setattr(sp, 'canary_evaluate_visibility_dataset', lambda connection, actor, endpoint_name, dataset_name, legacy_items: legacy_items)


@pytest.mark.parametrize(
    ('role', 'expected_permissions'),
    [
        ('admin', {'deliveries:view', 'deliveries:create', 'purchase_requests:view', 'purchase_orders:review', 'purchase_orders:receive', 'stock:view'}),
        ('buyer', {'purchase_requests:view', 'purchase_requests:update', 'purchase_orders:create', 'purchase_orders:upload', 'stock:view'}),
        ('approver', {'purchase_requests:view', 'purchase_orders:approve', 'stock:view'}),
    ],
)
def test_bootstrap_returns_minimum_payload_for_purchase_roles(monkeypatch, role, expected_permissions):
    _patch_successful_bootstrap_sections(monkeypatch)
    actor = {**BASE_ACTOR, 'role': role}

    payload = sp.build_bootstrap(object(), actor)

    assert payload['ok'] is True
    assert payload['degraded'] is False
    assert payload['user']['id'] == actor['id']
    assert payload['company']['id'] == actor['company_id']
    assert payload['units']
    assert payload['employees']
    assert payload['epis']
    assert expected_permissions.issubset(set(payload['permissions']))


def test_bootstrap_partial_optional_failure_does_not_raise_or_drop_core_sections(monkeypatch):
    _patch_successful_bootstrap_sections(monkeypatch)

    def fail_purchase_adjacent_history(connection, actor, filters):
        raise RuntimeError('relation purchase_events does not exist')

    monkeypatch.setattr(sp, 'fetch_ficha_epi_audit_logs', fail_purchase_adjacent_history)

    payload = sp.build_bootstrap(object(), BASE_ACTOR)

    assert payload['ok'] is True
    assert payload['degraded'] is True
    assert payload['ficha_audit_logs'] == []
    assert payload['units'] == [{'id': 4, 'company_id': BASE_ACTOR['company_id']}]
    assert payload['deliveries'] == [{'id': 33}]
    assert payload['bootstrap_warnings'][0]['section'] == 'ficha_audit_logs'


def test_bootstrap_purchase_permissions_are_safe_for_local_admin(monkeypatch):
    _patch_successful_bootstrap_sections(monkeypatch)

    payload = sp.build_bootstrap(object(), BASE_ACTOR)

    permissions = set(payload['permissions'])
    assert 'purchase_requests:view' in permissions
    assert 'purchase_requests:create' in permissions
    assert 'purchase_requests:update' in permissions
    assert 'purchase_orders:review' in permissions
    assert 'purchase_orders:receive' in permissions
    assert 'purchase_orders:approve' not in permissions


def test_actor_user_id_divergent_from_token_is_controlled_permission_error():
    token = create_jwt_token({'id': 17, 'role': 'admin', 'company_id': 2})
    handler = SimpleNamespace(headers={'Authorization': f'Bearer {token}'})
    parsed = urlparse('/api/bootstrap?actor_user_id=18')

    with pytest.raises(PermissionError, match='Dados de autenticação inconsistentes'):
        resolve_actor_user_id(handler, parsed)


def test_delivery_view_is_not_blocked_by_bootstrap_degraded_panel():
    source = open('static/app.js', encoding='utf-8').read()

    required_views_line = next(line for line in source.splitlines() if 'BOOTSTRAP_REQUIRED_VIEWS' in line)
    assert "'entregas'" not in required_views_line
    assert "loadOptionalBootstrapSection('purchases'" in source
    assert "loadOptionalBootstrapSection('stock'" in source
