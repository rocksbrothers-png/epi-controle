from pathlib import Path

import server_postgres as sp

ROOT = Path(__file__).resolve().parents[1]


def test_general_admin_does_not_have_commercial_permission():
    assert sp.PERM_COMMERCIAL_VIEW not in sp.PERMISSIONS['general_admin']
    assert sp.PERM_COMMERCIAL_VIEW in sp.PERMISSIONS['master_admin']


def test_bootstrap_hides_commercial_settings_for_non_master(monkeypatch):
    import modules.units.service as units_svc
    import modules.employees.service as employees_svc
    import modules.epis.service as epis_svc
    import modules.settings.service as settings_svc
    import modules.commercial.service as commercial_svc
    import modules.companies.service as companies_svc
    import modules.ficha.service as ficha_svc
    import modules.auth.service as auth_svc
    import modules.deliveries.service as deliveries_svc
    import modules.feedback.service as feedbacks_svc
    import modules.alerts.service as alerts_svc

    monkeypatch.setattr(units_svc, 'fetch_units', lambda *_args, **_kwargs: [])
    monkeypatch.setattr(employees_svc, 'fetch_employees', lambda *_args, **_kwargs: [])
    monkeypatch.setattr(employees_svc, 'fetch_employee_movements', lambda *_args, **_kwargs: [])
    monkeypatch.setattr(epis_svc, 'fetch_epis', lambda *_args, **_kwargs: [])
    monkeypatch.setattr(settings_svc, 'canary_evaluate_visibility_dataset', lambda *_args, **_kwargs: [])
    monkeypatch.setattr(commercial_svc, 'get_platform_brand', lambda *_args, **_kwargs: {})
    monkeypatch.setattr(companies_svc, 'fetch_companies', lambda *_args, **_kwargs: [])
    monkeypatch.setattr(companies_svc, 'fetch_company_audit_logs', lambda *_args, **_kwargs: [])
    monkeypatch.setattr(ficha_svc, 'fetch_ficha_epi_audit_logs', lambda *_args, **_kwargs: [])
    monkeypatch.setattr(auth_svc, 'fetch_users', lambda *_args, **_kwargs: [])
    monkeypatch.setattr(deliveries_svc, 'fetch_deliveries', lambda *_args, **_kwargs: [])
    monkeypatch.setattr(feedbacks_svc, 'fetch_feedbacks', lambda *_args, **_kwargs: [])
    monkeypatch.setattr(alerts_svc, 'compute_alerts', lambda *_args, **_kwargs: [])

    calls = {'commercial_settings': 0}

    def _commercial_settings(*_args, **_kwargs):
        calls['commercial_settings'] += 1
        return {'unit_price': 42}

    monkeypatch.setattr(commercial_svc, 'get_commercial_settings', _commercial_settings)

    non_master_payload = sp.build_bootstrap(None, {'role': 'general_admin', 'company_id': 1})
    assert non_master_payload['commercial_settings'] is None
    assert calls['commercial_settings'] == 0

    master_payload = sp.build_bootstrap(None, {'role': 'master_admin', 'company_id': None})
    assert master_payload['commercial_settings'] == {'unit_price': 42}
    assert calls['commercial_settings'] == 1


def test_frontend_general_admin_menu_does_not_include_commercial_permission():
    app_js = (ROOT / 'static' / 'app.js').read_text(encoding='utf-8')
    marker = "general_admin: ["
    start = app_js.find(marker)
    assert start >= 0
    end = app_js.find('],', start)
    assert end > start
    general_permissions_block = app_js[start:end]
    assert "'commercial:view'" not in general_permissions_block
