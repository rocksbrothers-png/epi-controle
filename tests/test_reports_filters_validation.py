import pytest

import server_postgres


def test_normalize_report_filters_parses_expected_types():
    filters = server_postgres.normalize_report_filters({
        'company_id': '2',
        'unit_id': '5',
        'employee_id': '10',
        'epi_id': '7',
        'start_date': '2026-04-01',
        'end_date': '2026-04-30',
        'sector': 'Operação',
    })
    assert filters['company_id'] == 2
    assert filters['unit_id'] == 5
    assert filters['employee_id'] == 10
    assert filters['epi_id'] == 7
    assert filters['start_date'] == '2026-04-01'
    assert filters['end_date'] == '2026-04-30'
    assert filters['sector'] == 'Operação'
    assert filters['archive_status'] == ''


def test_normalize_report_filters_accepts_archive_status_alias():
    filters = server_postgres.normalize_report_filters({
        'status': 'archived',
    })
    assert filters['archive_status'] == 'archived'


def test_normalize_report_filters_rejects_invalid_company_id():
    with pytest.raises(server_postgres.InvalidQueryParamError, match='company_id'):
        server_postgres.normalize_report_filters({'company_id': '2026-04-01'})


def test_normalize_report_filters_rejects_invalid_employee_id():
    with pytest.raises(server_postgres.InvalidQueryParamError, match='employee_id'):
        server_postgres.normalize_report_filters({'employee_id': '2026-04-01'})



def test_build_ficha_archive_filters_rejects_invalid_unit():
    with pytest.raises(ValueError, match='unit_id'):
        server_postgres.build_ficha_archive_filters({'unit_id': 'abc'})


def test_default_ficha_retention_policy_is_five_years():
    policy = server_postgres.default_ficha_retention_policy()
    assert policy['retention_years'] == 5
    assert policy['purge_enabled'] is False


def test_build_reports_keeps_filter_binding_order_without_actor_duplication(monkeypatch):
    import modules.reports.service as reports_svc
    import modules.deliveries.service as deliveries_svc
    captured = {}

    def fake_fetch_deliveries(connection, actor, where_clause='', params=()):
        captured['actor'] = actor
        captured['where_clause'] = where_clause
        captured['params'] = params
        return []

    monkeypatch.setattr(deliveries_svc, 'fetch_deliveries', fake_fetch_deliveries)
    monkeypatch.setattr(reports_svc, 'actor_operational_unit_id', lambda connection, actor: None)
    monkeypatch.setattr(reports_svc, 'ensure_company_access', lambda actor, company_id: None)
    monkeypatch.setattr(reports_svc, 'get_unit_by_id', lambda connection, unit_id: {'id': unit_id, 'company_id': 2})
    monkeypatch.setattr(reports_svc, 'ensure_resource_company', lambda actor, resource, label: None)

    actor = {'id': 9, 'role': 'general_admin', 'company_id': 2}
    filters = {
        'company_id': '2',
        'unit_id': '5',
        'start_date': '2026-04-01',
        'end_date': '2026-04-23',
    }
    payload = server_postgres.build_reports(connection=None, actor=actor, filters=filters)

    assert payload['deliveries'] == []
    assert captured['actor'] is None
    assert captured['params'] == (2, 5, '2026-04-01', '2026-04-23')
    assert 'deliveries.company_id = ?' in captured['where_clause']
    assert 'deliveries.unit_id = ?' in captured['where_clause']
    assert 'deliveries.delivery_date >= ?' in captured['where_clause']
    assert 'deliveries.delivery_date <= ?' in captured['where_clause']
