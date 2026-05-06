import sqlite3

import server_postgres


def _purchase_demands_connection():
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        CREATE TABLE employees (
            id INTEGER PRIMARY KEY,
            company_id INTEGER,
            unit_id INTEGER,
            name TEXT,
            sector TEXT,
            role_name TEXT
        );
        CREATE TABLE units (id INTEGER PRIMARY KEY, company_id INTEGER, name TEXT);
        CREATE TABLE epis (
            id INTEGER PRIMARY KEY,
            company_id INTEGER,
            name TEXT,
            ca TEXT,
            unit_measure TEXT,
            manufacturer TEXT,
            supplier_company TEXT,
            sector TEXT,
            glove_size TEXT,
            size TEXT,
            uniform_size TEXT,
            minimum_stock INTEGER,
            active INTEGER
        );
        CREATE TABLE epi_requests (
            id INTEGER PRIMARY KEY,
            company_id INTEGER,
            unit_id INTEGER,
            employee_id INTEGER,
            epi_id INTEGER,
            quantity INTEGER,
            glove_size TEXT,
            size TEXT,
            uniform_size TEXT,
            status TEXT,
            requested_at TEXT
        );
        CREATE TABLE purchase_request_items (
            id INTEGER PRIMARY KEY,
            epi_request_id INTEGER
        );
        CREATE TABLE unit_epi_stock (
            id INTEGER PRIMARY KEY,
            company_id INTEGER,
            unit_id INTEGER,
            epi_id INTEGER,
            quantity INTEGER
        );
        INSERT INTO units (id, company_id, name) VALUES (10, 1, 'Base A');
        INSERT INTO employees (id, company_id, unit_id, name, sector, role_name) VALUES (20, 1, 10, 'Ana Silva', 'Operação', 'Marinheira');
        INSERT INTO epis (id, company_id, name, ca, unit_measure, manufacturer, supplier_company, sector, glove_size, size, uniform_size, minimum_stock, active)
        VALUES (30, 1, 'Luva Nitrílica', 'CA-30', 'par', 'Fabricante', 'Fornecedor', 'Mãos', 'M (8)', 'N/A', 'N/A', 10, 1);
        INSERT INTO epi_requests (id, company_id, unit_id, employee_id, epi_id, quantity, glove_size, size, uniform_size, status, requested_at)
        VALUES (40, 1, 10, 20, 30, 2, 'M (8)', 'N/A', 'N/A', 'solicitado', '2026-05-06T10:00:00+00:00');
        INSERT INTO epi_requests (id, company_id, unit_id, employee_id, epi_id, quantity, glove_size, size, uniform_size, status, requested_at)
        VALUES (41, 1, 10, 20, 30, 1, 'M (8)', 'N/A', 'N/A', 'aprovado', '2026-05-06T11:00:00+00:00');
        INSERT INTO purchase_request_items (id, epi_request_id) VALUES (50, 41);
        INSERT INTO unit_epi_stock (id, company_id, unit_id, epi_id, quantity) VALUES (60, 1, 10, 30, 4);
        """
    )
    return conn


def test_fetch_purchase_demands_includes_employee_solicitation_with_full_context():
    conn = _purchase_demands_connection()

    demands = server_postgres.fetch_purchase_demands(conn, 1, 10)
    employee_demands = [item for item in demands if item.get('demand_type') == 'employee_request']

    assert len(employee_demands) == 1
    demand = employee_demands[0]
    assert demand['id'] == 40
    assert demand['employee_id'] == 20
    assert demand['unit_id'] == 10
    assert demand['epi_id'] == 30
    assert demand['employee_name'] == 'Ana Silva'
    assert demand['employee_sector'] == 'Operação'
    assert demand['employee_role'] == 'Marinheira'
    assert demand['status'] == 'solicitado'
    assert demand['quantity'] == 2


def test_fetch_purchase_demands_keeps_low_stock_size_status_and_unit_fields():
    conn = _purchase_demands_connection()

    demands = server_postgres.fetch_purchase_demands(conn, 1, 10)
    low_stock = [item for item in demands if item.get('demand_type') == 'low_stock']

    assert len(low_stock) == 1
    demand = low_stock[0]
    assert demand['unit_id'] == 10
    assert demand['epi_id'] == 30
    assert demand['quantity_requested'] == 6
    assert demand['status'] == 'low_stock'
    assert demand['sector'] == 'Mãos'
    assert demand['glove_size'] == 'M (8)'
