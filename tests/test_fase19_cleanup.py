"""Tests for Fase 19 cleanup: compute_alerts_wired + user_unit_links POST migration."""



# ── compute_alerts_wired ──────────────────────────────────────────────────────

def test_compute_alerts_wired_importable_from_alerts_module():
    from modules.alerts.service import compute_alerts_wired
    assert callable(compute_alerts_wired)


def test_compute_alerts_wrapper_removed_from_server_postgres():
    import server_postgres as sp
    import inspect
    # server_postgres.compute_alerts must now be the module-level function, not a wrapper defined inline
    fn = getattr(sp, 'compute_alerts', None)
    assert fn is not None, 'compute_alerts should still be importable via server_postgres'
    src = inspect.getfile(fn)
    assert 'modules/alerts/service.py' in src.replace('\\', '/'), \
        'compute_alerts in server_postgres must point to modules.alerts.service, not be defined inline'


# ── user_unit_links POST migration ───────────────────────────────────────────

def test_post_user_unit_links_registered_in_purchases():
    from modules.purchases import routes as pr
    from core.router import Router
    r = Router()
    pr.register_routes(r)
    paths = [(m, p) for m, p, _, _ in r._routes]
    assert ('POST', '/api/user-unit-links') in paths


def test_post_user_unit_links_not_registered_in_companies():
    from modules.companies import routes as cr
    from core.router import Router
    r = Router()
    cr.register_routes(r)
    paths = [(m, p) for m, p, _, _ in r._routes]
    assert ('POST', '/api/user-unit-links') not in paths


def test_handle_post_user_unit_links_not_in_companies_module():
    from modules.companies import routes as cr
    assert not hasattr(cr, 'handle_post_user_unit_links')


def test_handle_post_user_unit_links_in_purchases_module():
    from modules.purchases import routes as pr
    assert hasattr(pr, 'handle_post_user_unit_links')
    assert callable(pr.handle_post_user_unit_links)
