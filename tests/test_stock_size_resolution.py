import sqlite3

import server_postgres


def test_resolve_item_size_accepts_glove_only():
    resolved = server_postgres.resolve_item_size('G (9)', 'N/A', 'N/A')
    assert resolved['selected_size'] == 'G (9)'
    assert resolved['size'] == 'G (9)'


def test_resolve_item_size_accepts_size_only():
    resolved = server_postgres.resolve_item_size('N/A', 'M', 'N/A')
    assert resolved['selected_size'] == 'M'
    assert resolved['size'] == 'M'


def test_resolve_item_size_accepts_uniform_only():
    resolved = server_postgres.resolve_item_size('N/A', '', 'GG')
    assert resolved['selected_size'] == 'GG'
    assert resolved['size'] == 'GG'


def test_resolve_item_size_rejects_all_empty_equivalents():
    resolved = server_postgres.resolve_item_size('N/A', 'Selecione', 'undefined')
    assert resolved['selected_size'] == ''
    assert resolved['size'] == 'N/A'


def test_resolve_item_size_accepts_when_one_field_valid():
    resolved = server_postgres.resolve_item_size('N/A', 'N/A', '42')
    assert resolved['selected_size'] == '42'
    assert resolved['size'] == '42'



def test_effective_size_uses_stock_item_fallback_when_delivery_has_default_values():
    delivery = {'glove_size': 'N/A', 'size': 'N/A', 'uniform_size': 'N/A'}
    stock_item = {'stock_item_glove_size': 'G (9)', 'stock_item_size': 'G (9)', 'stock_item_uniform_size': 'N/A'}

    resolved = server_postgres.resolve_effective_size_fields(delivery, stock_item, fallback_prefix='stock_item_')

    assert resolved['selected_size'] == 'G (9)'
    assert resolved['glove_size'] == 'G (9)'
    assert resolved['size'] == 'G (9)'
    assert resolved['uniform_size'] == 'N/A'


def test_fetch_deliveries_returns_stock_item_size_when_delivery_size_is_default():
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        CREATE TABLE companies (id INTEGER PRIMARY KEY, name TEXT, cnpj TEXT, logo_type TEXT);
        CREATE TABLE employees (id INTEGER PRIMARY KEY, company_id INTEGER, employee_id_code TEXT, name TEXT, schedule_type TEXT, tipo_vinculo TEXT);
        CREATE TABLE units (id INTEGER PRIMARY KEY, name TEXT, unit_type TEXT);
        CREATE TABLE epis (id INTEGER PRIMARY KEY, name TEXT, purchase_code TEXT, ca TEXT, unit_measure TEXT, epi_validity_date TEXT, manufacture_date TEXT, qr_code_value TEXT);
        CREATE TABLE deliveries (
            id INTEGER PRIMARY KEY,
            company_id INTEGER,
            employee_id INTEGER,
            epi_id INTEGER,
            quantity INTEGER,
            quantity_label TEXT,
            sector TEXT,
            role_name TEXT,
            delivery_date TEXT,
            next_replacement_date TEXT,
            notes TEXT,
            signature_name TEXT,
            signature_data TEXT,
            signature_at TEXT,
            signature_comment TEXT,
            unit_id INTEGER,
            stock_movement_id INTEGER,
            glove_size TEXT NOT NULL DEFAULT 'N/A',
            size TEXT NOT NULL DEFAULT 'N/A',
            uniform_size TEXT NOT NULL DEFAULT 'N/A',
            returned_date TEXT NOT NULL DEFAULT '',
            returned_condition TEXT NOT NULL DEFAULT '',
            returned_notes TEXT NOT NULL DEFAULT '',
            return_movement_id INTEGER
        );
        CREATE TABLE epi_stock_items (
            id INTEGER PRIMARY KEY,
            delivery_id INTEGER,
            glove_size TEXT NOT NULL DEFAULT 'N/A',
            size TEXT NOT NULL DEFAULT 'N/A',
            uniform_size TEXT NOT NULL DEFAULT 'N/A'
        );
        CREATE TABLE epi_ficha_items (id INTEGER PRIMARY KEY, delivery_id INTEGER, ficha_period_id INTEGER);
        CREATE TABLE epi_ficha_periods (id INTEGER PRIMARY KEY, employee_id INTEGER, period_start TEXT, period_end TEXT, status TEXT);
        INSERT INTO companies (id, name, cnpj, logo_type) VALUES (1, 'ACME', '00', '');
        INSERT INTO employees (id, company_id, employee_id_code, name, schedule_type, tipo_vinculo) VALUES (2, 1, 'E-2', 'Joana', '', 'CLT');
        INSERT INTO units (id, name, unit_type) VALUES (3, 'Unidade A', 'operational');
        INSERT INTO epis (id, name, purchase_code, ca, unit_measure, epi_validity_date, manufacture_date, qr_code_value) VALUES (4, 'Luva', 'P-1', 'CA-1', 'unidade', '', '', '');
        INSERT INTO deliveries (id, company_id, employee_id, epi_id, quantity, quantity_label, sector, role_name, delivery_date, next_replacement_date, notes, signature_name, signature_data, signature_at, signature_comment, unit_id, stock_movement_id)
        VALUES (5, 1, 2, 4, 1, 'unidade', 'Operação', 'Técnica', '2026-05-01', '2026-06-01', '', '', '', '', '', 3, NULL);
        INSERT INTO epi_stock_items (id, delivery_id, glove_size, size, uniform_size) VALUES (6, 5, 'M (8)', 'M (8)', 'N/A');
        """
    )

    items = server_postgres.fetch_deliveries(conn)

    assert len(items) == 1
    assert items[0]['glove_size'] == 'M (8)'
    assert items[0]['size'] == 'M (8)'
    assert items[0]['uniform_size'] == 'N/A'
