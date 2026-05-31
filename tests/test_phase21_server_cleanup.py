"""Tests for Phase 21: server_postgres.py cleanup — business logic moved to modules."""

import inspect
import sqlite3

import server_postgres as sp


# ── Line count ────────────────────────────────────────────────────────────────

def test_server_postgres_under_1450_lines():
    src = inspect.getfile(sp)
    with open(src, encoding='utf-8') as fh:
        count = sum(1 for _ in fh)
    assert count < 1450, f"server_postgres.py has {count} lines (limit: 1450)"


# ── Functions importable from destination modules ─────────────────────────────

def test_generate_epi_qr_code_importable_from_stock_service():
    from modules.stock.service import generate_epi_qr_code
    assert callable(generate_epi_qr_code)


def test_next_company_qr_sequence_importable_from_stock_service():
    from modules.stock.service import next_company_qr_sequence
    assert callable(next_company_qr_sequence)


def test_build_master_epi_qr_importable_from_stock_service():
    from modules.stock.service import build_master_epi_qr
    assert callable(build_master_epi_qr)


def test_build_stock_item_qr_importable_from_stock_service():
    from modules.stock.service import build_stock_item_qr
    assert callable(build_stock_item_qr)


def test_auto_add_received_items_importable_from_purchases_service():
    from modules.purchases.service import _auto_add_received_items_to_stock
    assert callable(_auto_add_received_items_to_stock)


def test_generate_po_number_importable_from_purchases_service():
    from modules.purchases.service import generate_po_number
    assert callable(generate_po_number)


def test_validate_company_payload_importable_from_companies_service():
    from modules.companies.service import validate_company_payload
    assert callable(validate_company_payload)


def test_ensure_unique_company_cnpj_importable_from_companies_service():
    from modules.companies.service import ensure_unique_company_cnpj
    assert callable(ensure_unique_company_cnpj)


def test_build_portal_link_from_cpf_importable_from_portal_service():
    from modules.portal.service import build_portal_link_from_cpf
    assert callable(build_portal_link_from_cpf)


def test_migrate_role_hierarchy_importable_from_core_schema():
    from core.schema import migrate_role_hierarchy
    assert callable(migrate_role_hierarchy)


def test_static_asset_diagnostics_importable_from_auth_service():
    from modules.auth.service import static_asset_diagnostics
    assert callable(static_asset_diagnostics)


def test_build_ficha_epi_html_importable_from_ficha_service():
    from modules.ficha.service import build_ficha_epi_html
    assert callable(build_ficha_epi_html)


def test_build_ficha_epi_html_by_period_importable_from_ficha_service():
    from modules.ficha.service import build_ficha_epi_html_by_period
    assert callable(build_ficha_epi_html_by_period)


# ── Functions NOT defined inline in server_postgres.py ───────────────────────

def _server_defined_fns():
    src = inspect.getfile(sp)
    defined = set()
    with open(src, encoding='utf-8') as fh:
        for line in fh:
            stripped = line.strip()
            if stripped.startswith('def '):
                name = stripped[4:].split('(')[0].strip()
                defined.add(name)
    return defined


def test_generate_epi_qr_code_not_defined_inline():
    assert 'generate_epi_qr_code' not in _server_defined_fns()


def test_next_company_qr_sequence_not_defined_inline():
    assert 'next_company_qr_sequence' not in _server_defined_fns()


def test_build_master_epi_qr_not_defined_inline():
    assert 'build_master_epi_qr' not in _server_defined_fns()


def test_build_stock_item_qr_not_defined_inline():
    assert 'build_stock_item_qr' not in _server_defined_fns()


def test_auto_add_received_items_not_defined_inline():
    assert '_auto_add_received_items_to_stock' not in _server_defined_fns()


def test_generate_po_number_not_defined_inline():
    assert 'generate_po_number' not in _server_defined_fns()


def test_validate_company_payload_not_defined_inline():
    assert 'validate_company_payload' not in _server_defined_fns()


def test_ensure_unique_company_cnpj_not_defined_inline():
    assert 'ensure_unique_company_cnpj' not in _server_defined_fns()


def test_build_portal_link_from_cpf_not_defined_inline():
    assert 'build_portal_link_from_cpf' not in _server_defined_fns()


def test_migrate_role_hierarchy_not_defined_inline():
    assert 'migrate_role_hierarchy' not in _server_defined_fns()


def test_static_asset_diagnostics_not_defined_inline():
    assert 'static_asset_diagnostics' not in _server_defined_fns()


def test_build_ficha_epi_html_not_defined_inline():
    assert 'build_ficha_epi_html' not in _server_defined_fns()


def test_build_ficha_epi_html_by_period_not_defined_inline():
    assert 'build_ficha_epi_html_by_period' not in _server_defined_fns()


# ── Functional correctness ────────────────────────────────────────────────────

def test_generate_epi_qr_code_returns_expected_format():
    from modules.stock.service import generate_epi_qr_code
    result = generate_epi_qr_code({'company_id': 1, 'unit_id': 2, 'purchase_code': 'abc 123'})
    assert result == 'EPI-1-2-ABC-123'


def test_build_master_epi_qr_format():
    from modules.stock.service import build_master_epi_qr
    result = build_master_epi_qr(5, 42)
    assert result == 'EPI-MASTER-0005-00000042'


def test_build_stock_item_qr_format():
    from modules.stock.service import build_stock_item_qr
    result = build_stock_item_qr(3, 7, 99)
    assert result == 'EPI-ITEM-0003-0007-00000099'


def test_generate_po_number_format():
    import sqlite3
    from datetime import datetime, timezone
    from modules.purchases.service import generate_po_number
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.execute('CREATE TABLE purchase_orders (id INTEGER PRIMARY KEY, company_id INTEGER, po_number TEXT)')
    year = datetime.now(timezone.utc).year
    result = generate_po_number(conn, 1)
    assert result == f'PO-{year}-0001'


def test_build_portal_link_from_cpf_returns_token_and_link():
    from modules.portal.service import build_portal_link_from_cpf
    result = build_portal_link_from_cpf('https://example.com', '12345678909', 'secret-key')
    assert 'token' in result
    assert 'access_link' in result
    assert 'expires_at' in result
    assert result['access_link'].startswith('https://example.com/?employee_token=')


def test_migrate_role_hierarchy_updates_users():
    from core.schema import migrate_role_hierarchy
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.execute('CREATE TABLE users (id INTEGER PRIMARY KEY, role TEXT, company_id INTEGER)')
    conn.execute("INSERT INTO users VALUES (1, 'general_admin', NULL)")
    conn.execute("INSERT INTO users VALUES (2, 'general_admin', 5)")
    conn.execute("INSERT INTO users VALUES (3, 'admin', 3)")
    migrate_role_hierarchy(conn)
    rows = {row['id']: dict(row) for row in conn.execute('SELECT * FROM users').fetchall()}
    assert rows[1]['role'] == 'master_admin'
    assert rows[1]['company_id'] is None
    assert rows[2]['role'] == 'general_admin'
    assert rows[3]['role'] == 'admin'


# ── stock/epis handler: text filters delegated to fetch_epis ─────────────────

def test_fetch_epis_accepts_text_filters():
    from modules.epis.service import fetch_epis
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.executescript('''
        CREATE TABLE companies (id INTEGER PRIMARY KEY, name TEXT, cnpj TEXT, logo_type TEXT DEFAULT '');
        CREATE TABLE units (id INTEGER PRIMARY KEY, company_id INTEGER, name TEXT, unit_type TEXT DEFAULT 'base');
        CREATE TABLE unit_epi_stock (id INTEGER PRIMARY KEY, company_id INTEGER, unit_id INTEGER, epi_id INTEGER, quantity INTEGER, updated_at TEXT);
        CREATE TABLE epis (
            id INTEGER PRIMARY KEY, company_id INTEGER, unit_id INTEGER,
            name TEXT, purchase_code TEXT, ca TEXT, sector TEXT, epi_section TEXT,
            active INTEGER DEFAULT 1, stock INTEGER DEFAULT 0, minimum_stock INTEGER DEFAULT 0,
            unit_measure TEXT DEFAULT 'unidade', ca_expiry TEXT DEFAULT '',
            epi_validity_date TEXT DEFAULT '', manufacture_date TEXT DEFAULT '',
            validity_days INTEGER DEFAULT 0, validity_years INTEGER DEFAULT 0,
            validity_months INTEGER DEFAULT 0, manufacturer_validity_months INTEGER DEFAULT 0,
            default_replacement_days INTEGER, manufacturer TEXT DEFAULT '',
            model_reference TEXT DEFAULT '', supplier_company TEXT DEFAULT '',
            manufacturer_recommendations TEXT DEFAULT '', epi_photo_data TEXT,
            glove_size TEXT DEFAULT 'N/A', size TEXT DEFAULT 'N/A', uniform_size TEXT DEFAULT 'N/A',
            joinventures_json TEXT DEFAULT '[]', active_joinventure TEXT,
            scope_type TEXT DEFAULT 'GLOBAL', is_joint_venture INTEGER DEFAULT 0,
            qr_code_value TEXT DEFAULT '', epi_master_sequence INTEGER DEFAULT 0
        );
        INSERT INTO companies VALUES (1, 'Empresa A', '00000000000000', '');
        INSERT INTO epis (id, company_id, name, purchase_code, ca, sector, manufacturer) VALUES
            (1, 1, 'Luva Nitrílica', 'LN-001', 'CA-123', 'Mãos', 'Forn A'),
            (2, 1, 'Capacete ABS', 'CAP-002', 'CA-456', 'Cabeça', 'Forn B'),
            (3, 1, 'Óculos Proteção', 'OC-003', 'CA-789', 'Visão', 'Forn A');
    ''')
    all_epis = fetch_epis(conn)
    assert len(all_epis) == 3

    by_name = fetch_epis(conn, name='luva')
    assert len(by_name) == 1
    assert by_name[0]['name'] == 'Luva Nitrílica'

    by_ca = fetch_epis(conn, ca='CA-45')
    assert len(by_ca) == 1
    assert by_ca[0]['ca'] == 'CA-456'

    by_manufacturer = fetch_epis(conn, manufacturer='forn a')
    assert len(by_manufacturer) == 2

    by_protection = fetch_epis(conn, protection='cabeça')
    assert len(by_protection) == 1
    assert by_protection[0]['name'] == 'Capacete ABS'


# ── canary_evaluate_visibility_dataset mode=enforced ─────────────────────────

def _conn_with_framework(mode='shadow'):
    import json
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.executescript('''
        CREATE TABLE companies (id INTEGER PRIMARY KEY, name TEXT, active INTEGER DEFAULT 1);
        CREATE TABLE app_meta (key TEXT PRIMARY KEY, value TEXT);
        INSERT INTO companies VALUES (1, 'Empresa A', 1);
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


def test_canary_evaluate_returns_legacy_items_in_shadow_mode():
    from modules.settings.service import canary_evaluate_visibility_dataset
    conn = _conn_with_framework('shadow')
    actor = {'id': 1, 'company_id': 1, 'role': 'admin'}
    legacy = [{'id': 1, 'name': 'EPI A'}, {'id': 2, 'name': 'EPI B'}]
    result = canary_evaluate_visibility_dataset(
        conn, actor,
        endpoint_name='/api/stock/epis',
        dataset_name='epis',
        legacy_items=legacy,
    )
    assert result == legacy


def test_canary_evaluate_returns_candidate_items_in_enforced_mode():
    from modules.settings.service import canary_evaluate_visibility_dataset
    conn = _conn_with_framework('enforced')
    actor = {'id': 1, 'company_id': 1, 'role': 'admin'}
    legacy = [{'id': 1, 'name': 'EPI A'}, {'id': 2, 'name': 'EPI B'}]
    result = canary_evaluate_visibility_dataset(
        conn, actor,
        endpoint_name='/api/stock/epis',
        dataset_name='epis',
        legacy_items=legacy,
    )
    assert isinstance(result, list)
