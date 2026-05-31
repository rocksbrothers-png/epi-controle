"""Tests for Phase 17: handler migration from server_postgres to modules."""

import importlib
import types


MIGRATED_ROUTES = [
    # (module_path, method, path)
    ('modules.epis.routes',      'GET',    r'/api/epi-replacement-days/(\d+)'),
    ('modules.units.routes',     'GET',    '/api/unit-jv/active'),
    ('modules.purchases.routes', 'GET',    '/api/authorized-suppliers'),
    ('modules.purchases.routes', 'GET',    r'^/api/authorized-suppliers/(\d+)/purchase-orders$'),
    ('modules.purchases.routes', 'GET',    '/api/company-purchase-config'),
    ('modules.purchases.routes', 'GET',    '/api/user-unit-links'),
]


def test_migrated_handlers_registered_in_modules():
    from core.router import Router
    for module_path, method, path in MIGRATED_ROUTES:
        mod = importlib.import_module(module_path)
        r = Router()
        mod.register_routes(r)
        paths = [(m, p) for m, p, _, _ in r._routes]
        assert (method, path) in paths, f"{module_path} missing ({method}, {path!r})"


def test_migrated_handlers_not_defined_in_server_postgres():
    """Handler functions must NOT be defined directly in server_postgres."""
    import server_postgres as sp
    absent = [
        '_handle_get_epi_replacement_days',
        '_handle_get_unit_jv_active',
        '_handle_get_authorized_suppliers',
        '_handle_get_supplier_pos',
        '_handle_get_company_purchase_config',
        '_handle_get_user_unit_links',
    ]
    for name in absent:
        assert not hasattr(sp, name), f"server_postgres still defines {name}"


def test_test_imports_use_modules_not_server_postgres():
    """Key functions must be importable from modules, not server_postgres."""
    from modules.stock.service import fetch_low_stock_items, backfill_unit_stock_from_epis, sync_epi_scope_stock_unit
    from modules.devolutions.service import fetch_open_deliveries_for_devolution, register_epi_devolution
    from modules.feedback.service import apply_feedback_triage, fetch_feedback_detail, fetch_feedbacks_for_manager
    from core.schema import ensure_devolution_columns
    from core.permissions import PERM_EPI_FEEDBACK_VIEW, PERMISSIONS

    for fn in (fetch_low_stock_items, backfill_unit_stock_from_epis, sync_epi_scope_stock_unit,
               fetch_open_deliveries_for_devolution, register_epi_devolution,
               apply_feedback_triage, fetch_feedback_detail, fetch_feedbacks_for_manager,
               ensure_devolution_columns):
        assert callable(fn), f"{fn} is not callable"
    assert isinstance(PERMISSIONS, dict)
