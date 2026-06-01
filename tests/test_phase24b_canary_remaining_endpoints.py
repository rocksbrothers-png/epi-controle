"""Phase 24b — canary_evaluate_visibility_dataset nos endpoints restantes."""

import inspect
import json
import sqlite3


# ── helpers ───────────────────────────────────────────────────────────────────

def _conn(mode='shadow'):
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.executescript('''
        CREATE TABLE companies (id INTEGER PRIMARY KEY, name TEXT, active INTEGER DEFAULT 1);
        CREATE TABLE app_meta (key TEXT PRIMARY KEY, value TEXT);
        CREATE TABLE rule_engine_shadow_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER, user_id INTEGER, role TEXT,
            endpoint TEXT, dataset TEXT, mode TEXT,
            legacy_count INTEGER, new_count INTEGER,
            has_diff INTEGER, legacy_only TEXT, new_only TEXT, created_at TEXT
        );
        INSERT INTO companies VALUES (1, 'Test Corp', 1);
    ''')
    framework = {
        'feature_flags': {
            'execution_mode': mode,
            'enable_new_rules_engine': True,
        }
    }
    conn.execute(
        "INSERT INTO app_meta (key, value) VALUES (?, ?)",
        ('configuration_framework:1', json.dumps(framework)),
    )
    conn.commit()
    return conn


ACTOR = {'id': 1, 'company_id': 1, 'role': 'admin'}


# ── import coverage ───────────────────────────────────────────────────────────

def test_reports_routes_imports_canary():
    import modules.reports.routes as r
    assert 'canary_evaluate_visibility_dataset' in inspect.getsource(r)


# ── dataset_name correctness per handler ─────────────────────────────────────

def test_devolutions_open_deliveries_dataset_name():
    import modules.devolutions.routes as r
    src = inspect.getsource(r.handle_get_devolutions_open_deliveries)
    assert "dataset_name='open_deliveries'" in src


def test_ficha_snapshots_dataset_name():
    import modules.ficha.routes as r
    src = inspect.getsource(r.handle_get_ficha_epi_snapshots)
    assert "dataset_name='ficha_snapshots'" in src


def test_ficha_audit_dataset_name():
    import modules.ficha.routes as r
    src = inspect.getsource(r.handle_get_ficha_epi_audit)
    assert "dataset_name='ficha_audit'" in src


def test_avaliacoes_ranking_dataset_name():
    import modules.feedback.routes as r
    src = inspect.getsource(r.handle_get_avaliacoes_ranking)
    assert "dataset_name='avaliacoes_ranking'" in src


def test_avaliacoes_ranking_sugestoes_dataset_name():
    import modules.feedback.routes as r
    src = inspect.getsource(r.handle_get_avaliacoes_ranking_sugestoes)
    assert "dataset_name='avaliacoes_suggestions'" in src


def test_stock_movements_dataset_name():
    import modules.stock.routes as r
    src = inspect.getsource(r.handle_get_stock_movements_report)
    assert "dataset_name='stock_movements'" in src


def test_purchase_demands_dataset_name():
    import modules.purchases.routes as r
    src = inspect.getsource(r.handle_get_purchase_demands)
    assert "dataset_name='purchase_demands'" in src


def test_purchase_requests_dataset_name():
    import modules.purchases.routes as r
    src = inspect.getsource(r.handle_get_purchase_requests)
    assert "dataset_name='purchase_requests'" in src


def test_purchase_orders_dataset_name():
    import modules.purchases.routes as r
    src = inspect.getsource(r.handle_get_purchase_orders)
    assert "dataset_name='purchase_orders'" in src


def test_purchase_events_dataset_name():
    import modules.purchases.routes as r
    src = inspect.getsource(r.handle_get_purchase_events)
    assert "dataset_name='purchase_events'" in src


def test_authorized_suppliers_dataset_name():
    import modules.purchases.routes as r
    src = inspect.getsource(r.handle_get_authorized_suppliers)
    assert "dataset_name='authorized_suppliers'" in src


def test_supplier_pos_dataset_name():
    import modules.purchases.routes as r
    src = inspect.getsource(r.handle_get_supplier_pos)
    assert "dataset_name='supplier_pos'" in src


def test_user_unit_links_dataset_name():
    import modules.purchases.routes as r
    src = inspect.getsource(r.handle_get_user_unit_links)
    assert "dataset_name='user_unit_links'" in src


def test_report_requests_dataset_name():
    import modules.reports.routes as r
    src = inspect.getsource(r.handle_get_report_requests)
    assert "dataset_name='report_requests'" in src


# ── canary pass-through for non-unit/employee/epi datasets ───────────────────

def test_canary_passthrough_open_deliveries():
    from modules.settings.service import canary_evaluate_visibility_dataset
    conn = _conn('shadow')
    items = [{'id': 1, 'epi_id': 5}, {'id': 2, 'epi_id': 6}]
    result = canary_evaluate_visibility_dataset(
        conn, ACTOR,
        endpoint_name='/api/devolutions/open-deliveries',
        dataset_name='open_deliveries',
        legacy_items=items,
    )
    assert result == items


def test_canary_passthrough_ficha_snapshots():
    from modules.settings.service import canary_evaluate_visibility_dataset
    conn = _conn('shadow')
    items = [{'id': 10, 'employee_id': 1}]
    result = canary_evaluate_visibility_dataset(
        conn, ACTOR,
        endpoint_name='/api/ficha-epi-snapshots',
        dataset_name='ficha_snapshots',
        legacy_items=items,
    )
    assert result == items


def test_canary_passthrough_stock_movements():
    from modules.settings.service import canary_evaluate_visibility_dataset
    conn = _conn('shadow')
    items = [{'id': 100, 'movement_type': 'entry'}, {'id': 101, 'movement_type': 'exit'}]
    result = canary_evaluate_visibility_dataset(
        conn, ACTOR,
        endpoint_name='/api/stock/movements/report',
        dataset_name='stock_movements',
        legacy_items=items,
    )
    assert result == items


def test_canary_passthrough_purchase_requests():
    from modules.settings.service import canary_evaluate_visibility_dataset
    conn = _conn('shadow')
    items = [{'id': 20, 'status': 'open'}, {'id': 21, 'status': 'draft'}]
    result = canary_evaluate_visibility_dataset(
        conn, ACTOR,
        endpoint_name='/api/purchase-requests',
        dataset_name='purchase_requests',
        legacy_items=items,
    )
    assert result == items


def test_canary_passthrough_purchase_orders():
    from modules.settings.service import canary_evaluate_visibility_dataset
    conn = _conn('shadow')
    items = [{'id': 30}]
    result = canary_evaluate_visibility_dataset(
        conn, ACTOR,
        endpoint_name='/api/purchase-orders',
        dataset_name='purchase_orders',
        legacy_items=items,
    )
    assert result == items


def test_canary_passthrough_authorized_suppliers():
    from modules.settings.service import canary_evaluate_visibility_dataset
    conn = _conn('shadow')
    items = [{'id': 5, 'name': 'Fornecedor X'}]
    result = canary_evaluate_visibility_dataset(
        conn, ACTOR,
        endpoint_name='/api/authorized-suppliers',
        dataset_name='authorized_suppliers',
        legacy_items=items,
    )
    assert result == items


def test_canary_passthrough_report_requests():
    from modules.settings.service import canary_evaluate_visibility_dataset
    conn = _conn('shadow')
    items = [{'id': 1, 'status': 'pending'}]
    result = canary_evaluate_visibility_dataset(
        conn, ACTOR,
        endpoint_name='/api/report-requests',
        dataset_name='report_requests',
        legacy_items=items,
    )
    assert result == items


# ── shadow log written for each new endpoint ─────────────────────────────────

def test_shadow_log_written_for_open_deliveries():
    from modules.settings.service import canary_evaluate_visibility_dataset
    conn = _conn('shadow')
    canary_evaluate_visibility_dataset(
        conn, ACTOR,
        endpoint_name='/api/devolutions/open-deliveries',
        dataset_name='open_deliveries',
        legacy_items=[{'id': 1}, {'id': 2}],
    )
    row = conn.execute("SELECT * FROM rule_engine_shadow_log").fetchone()
    assert row is not None
    assert row['endpoint'] == '/api/devolutions/open-deliveries'
    assert row['legacy_count'] == 2


def test_shadow_log_written_for_avaliacoes_ranking():
    from modules.settings.service import canary_evaluate_visibility_dataset
    conn = _conn('shadow')
    canary_evaluate_visibility_dataset(
        conn, ACTOR,
        endpoint_name='/api/avaliacoes/ranking',
        dataset_name='avaliacoes_ranking',
        legacy_items=[{'id': 1}],
    )
    row = conn.execute("SELECT * FROM rule_engine_shadow_log").fetchone()
    assert row['dataset'] == 'avaliacoes_ranking'


def test_shadow_log_written_for_purchase_demands():
    from modules.settings.service import canary_evaluate_visibility_dataset
    conn = _conn('shadow')
    canary_evaluate_visibility_dataset(
        conn, ACTOR,
        endpoint_name='/api/purchase-demands',
        dataset_name='purchase_demands',
        legacy_items=[{'id': 1}, {'id': 2}, {'id': 3}],
    )
    row = conn.execute("SELECT * FROM rule_engine_shadow_log").fetchone()
    assert row['dataset'] == 'purchase_demands'
    assert row['legacy_count'] == 3


def test_shadow_log_written_for_stock_movements():
    from modules.settings.service import canary_evaluate_visibility_dataset
    conn = _conn('shadow')
    canary_evaluate_visibility_dataset(
        conn, ACTOR,
        endpoint_name='/api/stock/movements/report',
        dataset_name='stock_movements',
        legacy_items=[{'id': 1}],
    )
    row = conn.execute("SELECT * FROM rule_engine_shadow_log").fetchone()
    assert row['endpoint'] == '/api/stock/movements/report'
    assert row['dataset'] == 'stock_movements'


def test_shadow_log_written_for_report_requests():
    from modules.settings.service import canary_evaluate_visibility_dataset
    conn = _conn('shadow')
    canary_evaluate_visibility_dataset(
        conn, ACTOR,
        endpoint_name='/api/report-requests',
        dataset_name='report_requests',
        legacy_items=[{'id': 10}],
    )
    row = conn.execute("SELECT * FROM rule_engine_shadow_log").fetchone()
    assert row['endpoint'] == '/api/report-requests'
    assert row['new_count'] == 1


# ── enforced mode still returns all items for non-filtered datasets ───────────

def test_enforced_mode_returns_all_purchase_requests():
    from modules.settings.service import canary_evaluate_visibility_dataset
    conn = _conn('enforced')
    items = [{'id': 1}, {'id': 2}, {'id': 3}]
    result = canary_evaluate_visibility_dataset(
        conn, ACTOR,
        endpoint_name='/api/purchase-requests',
        dataset_name='purchase_requests',
        legacy_items=items,
    )
    assert len(result) == 3


def test_enforced_mode_returns_all_stock_movements():
    from modules.settings.service import canary_evaluate_visibility_dataset
    conn = _conn('enforced')
    items = [{'id': 1}, {'id': 2}]
    result = canary_evaluate_visibility_dataset(
        conn, ACTOR,
        endpoint_name='/api/stock/movements/report',
        dataset_name='stock_movements',
        legacy_items=items,
    )
    assert len(result) == 2


# ── canary positioned after data fetch in each handler ───────────────────────

def test_purchase_demands_canary_after_fetch():
    import modules.purchases.routes as r
    src = inspect.getsource(r.handle_get_purchase_demands)
    fetch_pos = src.find('fetch_purchase_demands(')
    canary_pos = src.find('canary_evaluate_visibility_dataset(')
    assert fetch_pos < canary_pos


def test_purchase_requests_canary_after_fetch():
    import modules.purchases.routes as r
    src = inspect.getsource(r.handle_get_purchase_requests)
    fetch_pos = src.find('fetch_purchase_requests(')
    canary_pos = src.find('canary_evaluate_visibility_dataset(')
    assert fetch_pos < canary_pos


def test_purchase_orders_canary_after_fetch():
    import modules.purchases.routes as r
    src = inspect.getsource(r.handle_get_purchase_orders)
    fetch_pos = src.find('fetch_purchase_orders(')
    canary_pos = src.find('canary_evaluate_visibility_dataset(')
    assert fetch_pos < canary_pos


def test_report_requests_canary_after_fetch():
    import modules.reports.routes as r
    src = inspect.getsource(r.handle_get_report_requests)
    rows_pos = src.find('.fetchall()')
    canary_pos = src.find('canary_evaluate_visibility_dataset(')
    assert rows_pos < canary_pos


def test_total_open_recalculated_after_canary_in_open_deliveries():
    """total_open must reflect canary result, not original fetch result."""
    import modules.devolutions.routes as r
    src = inspect.getsource(r.handle_get_devolutions_open_deliveries)
    canary_pos = src.find('canary_evaluate_visibility_dataset(')
    total_open_pos = src.find('total_open')
    assert canary_pos < total_open_pos, "total_open must be computed after canary"
