import io
import json

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


def test_normalize_report_filters_rejects_invalid_company_id():
    with pytest.raises(server_postgres.InvalidQueryParamError, match='company_id'):
        server_postgres.normalize_report_filters({'company_id': '2026-04-01'})


def test_normalize_report_filters_rejects_invalid_employee_id():
    with pytest.raises(server_postgres.InvalidQueryParamError, match='employee_id'):
        server_postgres.normalize_report_filters({'employee_id': '2026-04-01'})

        
    with pytest.raises(ValueError, match='company_id'):
        server_postgres.normalize_report_filters({'company_id': '2026-04-01'})


def test_legacy_send_json_wraps_api_errors():
    class DummyHandler:
        def __init__(self):
            self.path = '/api/reports'
            self.command = 'GET'
            self.status = None
            self.headers = {}
            self.wfile = io.BytesIO()

        def send_response(self, status):
            self.status = status

        def send_header(self, key, value):
            self.headers[key] = value

        def end_headers(self):
            return None

    handler = DummyHandler()
    server_postgres.legacy_send_json(handler, 400, {'error': 'Filtro inválido', 'code': 'INVALID_FILTER'})
    body = json.loads(handler.wfile.getvalue().decode('utf-8'))
    assert body['ok'] is False
    assert body['error']['code'] == 'INVALID_FILTER'
    assert body['error']['message'] == 'Filtro inválido'


def test_build_ficha_archive_filters_rejects_invalid_unit():
    with pytest.raises(ValueError, match='unit_id'):
        server_postgres.build_ficha_archive_filters({'unit_id': 'abc'})


def test_default_ficha_retention_policy_is_five_years():
    policy = server_postgres.default_ficha_retention_policy()
    assert policy['retention_years'] == 5
    assert policy['purge_enabled'] is False
