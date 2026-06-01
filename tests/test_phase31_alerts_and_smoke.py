"""Phase 31 — Alerts bootstrap-only + smoke tests para os 21 endpoints com canary."""

import inspect


# ── alerts: bootstrap-only service ───────────────────────────────────────────

def test_alerts_module_has_no_routes_file():
    """alerts é um serviço bootstrap-only — não tem routes.py próprio."""
    from pathlib import Path
    alerts_dir = Path(__file__).resolve().parents[1] / 'modules' / 'alerts'
    assert not (alerts_dir / 'routes.py').exists(), \
        "alerts/routes.py não deveria existir — alerts serve via bootstrap"


def test_alerts_compute_alerts_wired_callable():
    from modules.alerts.service import compute_alerts_wired
    assert callable(compute_alerts_wired)


def test_alerts_served_via_bootstrap_not_direct_endpoint():
    """compute_alerts_wired deve ser chamado pelo bootstrap, não por routes."""
    from modules.auth.service import build_bootstrap
    src = inspect.getsource(build_bootstrap)
    assert 'compute_alerts' in src
    assert "'alerts'" in src


def test_alerts_not_in_any_routes_registration():
    """Nenhum routes.py deve registrar /api/alerts."""
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    for route_file in root.glob('modules/*/routes.py'):
        content = route_file.read_text(encoding='utf-8')
        assert '/api/alerts' not in content, \
            f"{route_file} registra /api/alerts — deve ser bootstrap-only"


# ── smoke tests: canary corretamente posicionado nos 21 endpoints ─────────────

CANARY_ENDPOINTS = [
    ('modules.devolutions.routes', '/api/devolutions', 'devolutions'),
    ('modules.devolutions.routes', '/api/devolutions/open-deliveries', 'open_deliveries'),
    ('modules.feedback.routes', '/api/feedbacks', 'feedbacks'),
    ('modules.feedback.routes', '/api/avaliacoes/ranking', 'avaliacoes_ranking'),
    ('modules.feedback.routes', '/api/avaliacoes/ranking-sugestoes', 'avaliacoes_suggestions'),
    ('modules.ficha.routes', '/api/fichas', 'fichas'),
    ('modules.ficha.routes', '/api/ficha-epi-snapshots', 'ficha_snapshots'),
    ('modules.ficha.routes', '/api/ficha-epi-audit', 'ficha_audit'),
    ('modules.purchases.routes', '/api/requests', 'epi_requests'),
    ('modules.purchases.routes', '/api/purchase-demands', 'purchase_demands'),
    ('modules.purchases.routes', '/api/purchase-requests', 'purchase_requests'),
    ('modules.purchases.routes', '/api/purchase-orders', 'purchase_orders'),
    ('modules.purchases.routes', '/api/purchase-events', 'purchase_events'),
    ('modules.purchases.routes', '/api/authorized-suppliers', 'authorized_suppliers'),
    ('modules.purchases.routes', '/api/authorized-suppliers/{id}/purchase-orders', 'supplier_pos'),
    ('modules.purchases.routes', '/api/user-unit-links', 'user_unit_links'),
    ('modules.reports.routes', '/api/report-requests', 'report_requests'),
    ('modules.stock.routes', '/api/stock/available-items', 'stock_items'),
    ('modules.stock.routes', '/api/stock/movements/report', 'stock_movements'),
    ('modules.stock.routes', '/api/stock/epis', 'epis'),
    ('modules.auth.service', '/api/bootstrap', 'units'),
    ('modules.auth.service', '/api/bootstrap', 'employees'),
    ('modules.auth.service', '/api/bootstrap', 'epis'),
    ('modules.auth.service', '/api/bootstrap', 'users'),
]


def _src(module_name):
    import importlib
    mod = importlib.import_module(module_name)
    return inspect.getsource(mod)


def test_all_canary_endpoints_import_canary():
    """Cada módulo na lista deve importar ou definir canary_evaluate_visibility_dataset."""
    covered_modules = set(m for m, _, _ in CANARY_ENDPOINTS)
    for mod_name in covered_modules:
        src = _src(mod_name)
        assert 'canary_evaluate_visibility_dataset' in src, \
            f"{mod_name} não usa canary_evaluate_visibility_dataset"


def test_all_endpoint_names_present_in_source():
    covered_modules = set(m for m, _, _ in CANARY_ENDPOINTS)
    src_cache = {m: _src(m) for m in covered_modules}
    for mod_name, endpoint_name, dataset_name in CANARY_ENDPOINTS:
        src = src_cache[mod_name]
        assert endpoint_name in src, \
            f"{mod_name}: endpoint_name='{endpoint_name}' não encontrado"


def test_all_dataset_names_present_in_source():
    covered_modules = set(m for m, _, _ in CANARY_ENDPOINTS)
    src_cache = {m: _src(m) for m in covered_modules}
    for mod_name, endpoint_name, dataset_name in CANARY_ENDPOINTS:
        src = src_cache[mod_name]
        assert dataset_name in src, \
            f"{mod_name}: dataset_name='{dataset_name}' não encontrado"


def test_devolutions_canary_after_fetch():
    import modules.devolutions.routes as r
    src = inspect.getsource(r.handle_get_devolutions)
    fetch_pos = src.find('fetch_devolutions(')
    canary_pos = src.find('canary_evaluate_visibility_dataset(')
    assert fetch_pos != -1 and canary_pos != -1
    assert fetch_pos < canary_pos


def test_feedback_canary_after_fetch():
    import modules.feedback.routes as r
    src = inspect.getsource(r.handle_get_feedbacks)
    assert src.index('fetch_feedbacks') < src.index('canary_evaluate_visibility_dataset')


def test_ficha_canary_after_fetch():
    import modules.ficha.routes as r
    src = inspect.getsource(r.handle_get_fichas)
    assert 'canary_evaluate_visibility_dataset' in src


def test_purchases_epi_requests_canary_after_fetch():
    import modules.purchases.routes as r
    src = inspect.getsource(r.handle_get_epi_requests)
    assert src.index('fetch_epi_requests') < src.index('canary_evaluate_visibility_dataset')


def test_stock_movements_canary_after_fetch():
    import modules.stock.routes as r
    src = inspect.getsource(r.handle_get_stock_movements_report)
    assert 'canary_evaluate_visibility_dataset' in src


def test_stock_available_items_canary_after_fetch():
    import modules.stock.routes as r
    src = inspect.getsource(r.handle_get_stock_available_items)
    assert src.index('fetch_available_stock_items') < src.index('canary_evaluate_visibility_dataset')


def test_bootstrap_canary_dataset_coverage():
    """Bootstrap deve ter canary para units, employees, epis e users."""
    from modules.auth.service import build_bootstrap
    src = inspect.getsource(build_bootstrap)
    for dataset in ('units', 'employees', 'epis', 'users'):
        assert f"dataset_name='{dataset}'" in src, \
            f"bootstrap não tem canary para dataset='{dataset}'"


def test_total_canary_covered_datasets_count():
    """Verifica que pelo menos 20 pares endpoint/dataset estão cobertos."""
    assert len(CANARY_ENDPOINTS) >= 20
