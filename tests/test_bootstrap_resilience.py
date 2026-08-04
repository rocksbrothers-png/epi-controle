from types import SimpleNamespace
from urllib.parse import urlparse

import pytest

import server_postgres as sp
import modules.auth.service as auth_svc
import modules.units.service as units_svc
import modules.employees.service as employees_svc
import modules.epis.service as epis_svc
import modules.deliveries.service as deliveries_svc
import modules.feedback.service as feedbacks_svc
import modules.commercial.service as commercial_svc
import modules.companies.service as companies_svc
import modules.ficha.service as ficha_svc
import modules.settings.service as settings_svc
import modules.legal_entities.service as legal_entities_svc
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
    monkeypatch.setattr(commercial_svc, 'get_platform_brand', lambda connection: {'name': 'EPI Controle'})
    monkeypatch.setattr(commercial_svc, 'get_commercial_settings', lambda connection: {'plans': []})
    monkeypatch.setattr(companies_svc, 'fetch_companies', lambda connection, company_id=None: [{'id': company_id or 1}])
    monkeypatch.setattr(companies_svc, 'fetch_company_audit_logs', lambda connection, actor: [])
    monkeypatch.setattr(ficha_svc, 'fetch_ficha_epi_audit_logs', lambda connection, actor, filters: [])
    monkeypatch.setattr(auth_svc, 'fetch_users', lambda connection, actor: [{'id': actor['id']}])
    monkeypatch.setattr(units_svc, 'fetch_units', lambda connection, actor: [{'id': 4, 'company_id': actor['company_id']}])
    monkeypatch.setattr(legal_entities_svc, 'fetch_legal_entities', lambda connection, actor=None, company_id=None: [{'id': 2, 'company_id': actor['company_id'] if actor else company_id}])
    monkeypatch.setattr(employees_svc, 'fetch_employees', lambda connection, actor: [{'id': 21, 'unit_id': 4}])
    monkeypatch.setattr(employees_svc, 'fetch_employee_movements', lambda connection, actor: [])
    monkeypatch.setattr(epis_svc, 'fetch_epis', lambda connection, actor, unit_id=None: [{'id': 9, 'unit_id': 4}])
    monkeypatch.setattr(deliveries_svc, 'fetch_deliveries', lambda connection, actor: [{'id': 33}])
    monkeypatch.setattr(feedbacks_svc, 'fetch_feedbacks', lambda connection, actor: [])
    monkeypatch.setattr(settings_svc, 'canary_evaluate_visibility_dataset', lambda connection, actor, endpoint_name, dataset_name, legacy_items: legacy_items)
    monkeypatch.setattr(settings_svc, 'get_effective_module_visibility', lambda connection, actor, **kwargs: {})
    # patch compute_alerts via auth_svc inner function — patch alerts service directly
    import modules.alerts.service as alerts_svc
    monkeypatch.setattr(alerts_svc, 'compute_alerts', lambda connection, actor=None, **kwargs: [])
    # pending_purchases (KPI do dashboard): mockar a contagem e os helpers de escopo.
    import modules.purchases.service as purchases_svc
    monkeypatch.setattr(purchases_svc, 'count_pending_purchase_requests', lambda connection, company_id, scope_unit_id=None, purchase_scope_units=None: 0)
    monkeypatch.setattr(purchases_svc, 'get_actor_purchase_unit_scope', lambda connection, actor: [])
    monkeypatch.setattr(employees_svc, 'actor_operational_unit_id', lambda connection, actor: actor.get('operational_unit_id'))


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

    monkeypatch.setattr(ficha_svc, 'fetch_ficha_epi_audit_logs', fail_purchase_adjacent_history)

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
    assert "loadOptionalBootstrapSection(\n        'purchases'" in source
    assert "loadOptionalBootstrapSection(\n        'stock'" in source
