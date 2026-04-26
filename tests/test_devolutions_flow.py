import sqlite3

import pytest

from server_postgres import (
    ensure_devolution_columns,
    fetch_open_deliveries_for_devolution,
    register_epi_devolution,
)


def make_connection():
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = OFF')
    conn.execute('CREATE TABLE companies (id INTEGER PRIMARY KEY, name TEXT)')
    conn.execute('CREATE TABLE users (id INTEGER PRIMARY KEY, full_name TEXT, role TEXT, company_id INTEGER, active INTEGER)')
    conn.execute('CREATE TABLE units (id INTEGER PRIMARY KEY, company_id INTEGER, name TEXT)')
    conn.execute(
        '''
        CREATE TABLE employees (
            id INTEGER PRIMARY KEY,
            company_id INTEGER NOT NULL,
            unit_id INTEGER NOT NULL,
            employee_id_code TEXT NOT NULL,
            cpf TEXT NOT NULL DEFAULT '',
            name TEXT NOT NULL,
            email TEXT NOT NULL DEFAULT '',
            whatsapp TEXT NOT NULL DEFAULT '',
            preferred_contact_channel TEXT NOT NULL DEFAULT 'whatsapp',
            sector TEXT NOT NULL,
            role_name TEXT NOT NULL,
            admission_date TEXT NOT NULL DEFAULT '',
            schedule_type TEXT NOT NULL DEFAULT ''
        )
        '''
    )
    conn.execute(
        '''
        CREATE TABLE epis (
            id INTEGER PRIMARY KEY,
            company_id INTEGER NOT NULL,
            unit_id INTEGER,
            name TEXT NOT NULL,
            unit_measure TEXT NOT NULL DEFAULT 'unidade',
            ca TEXT NOT NULL DEFAULT ''
        )
        '''
    )
    conn.execute(
        '''
        CREATE TABLE deliveries (
            id INTEGER PRIMARY KEY,
            company_id INTEGER NOT NULL,
            employee_id INTEGER NOT NULL,
            epi_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            quantity_label TEXT NOT NULL,
            sector TEXT NOT NULL,
            role_name TEXT NOT NULL,
            delivery_date TEXT NOT NULL,
            next_replacement_date TEXT NOT NULL,
            notes TEXT NOT NULL DEFAULT '',
            signature_name TEXT NOT NULL DEFAULT '',
            signature_data TEXT NOT NULL DEFAULT '',
            signature_at TEXT NOT NULL DEFAULT '',
            signature_comment TEXT NOT NULL DEFAULT '',
            unit_id INTEGER,
            returned_date TEXT NOT NULL DEFAULT '',
            returned_condition TEXT NOT NULL DEFAULT '',
            returned_notes TEXT NOT NULL DEFAULT '',
            return_movement_id INTEGER
        )
        '''
    )
    conn.execute(
        '''
        CREATE TABLE unit_epi_stock (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL,
            unit_id INTEGER NOT NULL,
            epi_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 0,
            updated_at TEXT NOT NULL
        )
        '''
    )
    conn.execute(
        '''
        CREATE TABLE stock_movements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL,
            unit_id INTEGER NOT NULL,
            epi_id INTEGER NOT NULL,
            movement_type TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            previous_stock INTEGER NOT NULL,
            new_stock INTEGER NOT NULL,
            source_type TEXT NOT NULL DEFAULT '',
            source_id INTEGER,
            notes TEXT NOT NULL DEFAULT '',
            actor_user_id INTEGER NOT NULL,
            actor_name TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        '''
    )
    conn.execute(
        '''
        CREATE TABLE epi_stock_items (
            id INTEGER PRIMARY KEY,
            company_id INTEGER NOT NULL,
            unit_id INTEGER NOT NULL,
            epi_id INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'delivered',
            delivery_id INTEGER,
            updated_at TEXT NOT NULL DEFAULT ''
        )
        '''
    )
    conn.execute(
        '''
        CREATE TABLE epi_ficha_periods (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL,
            employee_id INTEGER NOT NULL,
            unit_id INTEGER NOT NULL,
            schedule_type TEXT NOT NULL,
            period_start TEXT NOT NULL,
            period_end TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'open',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        '''
    )
    ensure_devolution_columns(conn)
    conn.execute("INSERT INTO companies (id, name) VALUES (1, 'Acme')")
    conn.execute("INSERT INTO users (id, full_name, role, company_id, active) VALUES (10, 'Admin Operacional', 'admin', 1, 1)")
    conn.execute("INSERT INTO units (id, company_id, name) VALUES (7, 1, 'Base A')")
    conn.execute("INSERT INTO units (id, company_id, name) VALUES (8, 1, 'Base B')")
    conn.execute(
        "INSERT INTO employees (id, company_id, unit_id, employee_id_code, name, sector, role_name, schedule_type) VALUES (21, 1, 7, 'C-001', 'Fulano', 'Operação', 'Técnico', '30x30')"
    )
    conn.execute("INSERT INTO epis (id, company_id, unit_id, name, unit_measure, ca) VALUES (30, 1, 7, 'Capacete', 'UN', 'CA-1')")
    conn.execute(
        "INSERT INTO deliveries (id, company_id, employee_id, epi_id, quantity, quantity_label, sector, role_name, delivery_date, next_replacement_date, signature_name, unit_id) VALUES (100, 1, 21, 30, 1, 'UN', 'Operação', 'Técnico', '2026-04-01', '2026-05-01', 'Fulano', 7)"
    )
    conn.execute(
        "INSERT INTO unit_epi_stock (company_id, unit_id, epi_id, quantity, updated_at) VALUES (1, 7, 30, 0, '2026-04-01T00:00:00+00:00')"
    )
    conn.execute(
        "INSERT INTO epi_stock_items (id, company_id, unit_id, epi_id, status, delivery_id, updated_at) VALUES (500, 1, 7, 30, 'delivered', 100, '2026-04-01T00:00:00+00:00')"
    )
    return conn


def test_register_devolution_creates_movement_updates_stock_and_links_ficha_period():
    conn = make_connection()
    actor = {'id': 10, 'full_name': 'Admin Operacional', 'role': 'admin', 'company_id': 1}
    payload = {
        'actor_user_id': 10,
        'delivery_id': 100,
        'returned_date': '2026-04-18',
        'condition': 'usable',
        'destination': 'stock',
        'reason': 'Troca por desgaste',
        'notes': 'Item devolvido em bom estado',
    }

    devolution_id = register_epi_devolution(conn, payload, actor)

    assert devolution_id > 0
    delivery = conn.execute('SELECT returned_date, returned_condition FROM deliveries WHERE id = 100').fetchone()
    assert delivery['returned_date'] == '2026-04-18'
    assert delivery['returned_condition'] == 'usable'
    stock = conn.execute('SELECT quantity FROM unit_epi_stock WHERE company_id = 1 AND unit_id = 7 AND epi_id = 30').fetchone()
    assert int(stock['quantity']) == 1
    movement = conn.execute("SELECT movement_type, source_type, source_id FROM stock_movements WHERE source_type = 'devolution'").fetchone()
    assert movement is not None
    assert movement['movement_type'] == 'return'
    devolution = conn.execute('SELECT ficha_period_id, stock_movement_id, stock_item_id FROM epi_devolutions WHERE id = ?', (devolution_id,)).fetchone()
    assert int(devolution['ficha_period_id']) > 0
    assert int(devolution['stock_movement_id']) > 0
    assert int(devolution['stock_item_id']) == 500


def test_register_devolution_accepts_optional_immediate_signature():
    conn = make_connection()
    actor = {'id': 10, 'full_name': 'Admin Operacional', 'role': 'admin', 'company_id': 1}
    payload = {
        'actor_user_id': 10,
        'delivery_id': 100,
        'returned_date': '2026-04-20',
        'condition': 'maintenance',
        'destination': 'maintenance',
        'signature_name': 'Fulano',
        'signature_data': 'data:image/png;base64,abc',
        'signature_at': '2026-04-20T10:00:00+00:00',
        'signature_comment': 'Conferido no recebimento',
    }

    devolution_id = register_epi_devolution(conn, payload, actor)
    devolution = conn.execute(
        'SELECT signature_name, signature_data, signature_at, signature_comment FROM epi_devolutions WHERE id = ?',
        (devolution_id,),
    ).fetchone()
    assert devolution['signature_name'] == 'Fulano'
    assert devolution['signature_data'].startswith('data:image/png;base64,')
    assert devolution['signature_at'] == '2026-04-20T10:00:00+00:00'
    assert devolution['signature_comment'] == 'Conferido no recebimento'


def test_fetch_open_deliveries_for_devolution_returns_only_non_returned_records():
    conn = make_connection()
    conn.execute(
        "INSERT INTO deliveries (id, company_id, employee_id, epi_id, quantity, quantity_label, sector, role_name, delivery_date, next_replacement_date, signature_name, unit_id) "
        "VALUES (101, 1, 21, 30, 1, 'UN', 'Operação', 'Técnico', '2026-04-02', '2026-05-02', 'Fulano', 7)"
    )
    conn.execute(
        "INSERT INTO deliveries (id, company_id, employee_id, epi_id, quantity, quantity_label, sector, role_name, delivery_date, next_replacement_date, signature_name, unit_id, returned_date) "
        "VALUES (102, 1, 21, 30, 1, 'UN', 'Operação', 'Técnico', '2026-04-03', '2026-05-03', 'Fulano', 7, '2026-04-10')"
    )
    actor = {'id': 10, 'full_name': 'Admin Operacional', 'role': 'admin', 'company_id': 1}

    items = fetch_open_deliveries_for_devolution(conn, actor, employee_id=21, epi_id=30)

    ids = [item['id'] for item in items]
    assert 102 not in ids
    assert ids == [101, 100]


def test_fetch_open_deliveries_for_devolution_respects_unit_scope_and_multiple_employees():
    conn = make_connection()
    conn.execute(
        "INSERT INTO employees (id, company_id, unit_id, employee_id_code, name, sector, role_name, schedule_type) VALUES (22, 1, 8, 'C-002', 'Beltrano', 'Operação', 'Técnico', '30x30')"
    )
    conn.execute(
        "INSERT INTO deliveries (id, company_id, employee_id, epi_id, quantity, quantity_label, sector, role_name, delivery_date, next_replacement_date, signature_name, unit_id) "
        "VALUES (103, 1, 21, 30, 1, 'UN', 'Operação', 'Técnico', '2026-04-04', '2026-05-04', 'Fulano', 8)"
    )
    conn.execute(
        "INSERT INTO deliveries (id, company_id, employee_id, epi_id, quantity, quantity_label, sector, role_name, delivery_date, next_replacement_date, signature_name, unit_id) "
        "VALUES (104, 1, 22, 30, 1, 'UN', 'Operação', 'Técnico', '2026-04-05', '2026-05-05', 'Beltrano', 8)"
    )
    actor = {'id': 10, 'full_name': 'Admin Operacional', 'role': 'admin', 'company_id': 1}

    unit_8_items = fetch_open_deliveries_for_devolution(conn, actor, employee_id=21, epi_id=30, unit_id=8)
    all_items_emp_21 = fetch_open_deliveries_for_devolution(conn, actor, employee_id=21, epi_id=30)

    assert [item['id'] for item in unit_8_items] == [103]
    assert 104 not in [item['id'] for item in all_items_emp_21]


def test_register_devolution_blocks_mismatched_expected_origin_context():
    conn = make_connection()
    actor = {'id': 10, 'full_name': 'Admin Operacional', 'role': 'admin', 'company_id': 1}
    payload = {
        'actor_user_id': 10,
        'delivery_id': 100,
        'returned_date': '2026-04-21',
        'condition': 'usable',
        'destination': 'stock',
        'expected_employee_id': 999,
    }

    with pytest.raises(ValueError, match='colaborador'):
        register_epi_devolution(conn, payload, actor)
