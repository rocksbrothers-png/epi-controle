import sqlite3

from server_postgres import fetch_low_stock_items


def make_connection():
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.execute(
        '''
        CREATE TABLE companies (
            id INTEGER PRIMARY KEY,
            name TEXT
        )
        '''
    )
    conn.execute(
        '''
        CREATE TABLE units (
            id INTEGER PRIMARY KEY,
            company_id INTEGER,
            name TEXT
        )
        '''
    )
    conn.execute(
        '''
        CREATE TABLE epis (
            id INTEGER PRIMARY KEY,
            company_id INTEGER NOT NULL,
            unit_id INTEGER,
            name TEXT,
            minimum_stock INTEGER,
            unit_measure TEXT,
            active INTEGER DEFAULT 1,
            active_joinventure TEXT
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
            updated_at TEXT
        )
        '''
    )
    conn.execute(
        '''
        CREATE TABLE unit_joint_venture_periods (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            unit_id INTEGER NOT NULL,
            joint_venture_name TEXT,
            started_at TEXT,
            ended_at TEXT
        )
        '''
    )
    return conn


def test_low_stock_does_not_mix_unit_scoped_epi_between_units():
    conn = make_connection()
    conn.execute("INSERT INTO companies (id, name) VALUES (1, 'Norskan Offshore')")
    conn.execute("INSERT INTO units (id, company_id, name) VALUES (10, 1, 'Navio Norskan Alpha')")
    conn.execute("INSERT INTO units (id, company_id, name) VALUES (20, 1, 'Skandi Paraty')")

    conn.execute(
        "INSERT INTO epis (id, company_id, unit_id, name, minimum_stock, unit_measure, active) VALUES (101, 1, 10, 'Capacete', 10, 'unidade', 1)"
    )
    conn.execute(
        "INSERT INTO epis (id, company_id, unit_id, name, minimum_stock, unit_measure, active) VALUES (202, 1, 20, 'Luva', 10, 'par', 1)"
    )

    conn.execute("INSERT INTO unit_epi_stock (company_id, unit_id, epi_id, quantity) VALUES (1, 10, 101, 0)")
    # linha residual incorreta: EPI da unidade 20 aparecendo no estoque da unidade 10
    conn.execute("INSERT INTO unit_epi_stock (company_id, unit_id, epi_id, quantity) VALUES (1, 10, 202, 0)")

    items = fetch_low_stock_items(conn)

    assert len(items) == 1
    assert int(items[0]['unit_id']) == 10
    assert int(items[0]['epi_id']) == 101


def test_low_stock_keeps_only_epis_actually_linked_to_each_unit():
    conn = make_connection()
    conn.execute("INSERT INTO companies (id, name) VALUES (1, 'Norskan Offshore')")
    conn.execute("INSERT INTO units (id, company_id, name) VALUES (10, 1, 'Navio Norskan Alpha')")
    conn.execute("INSERT INTO units (id, company_id, name) VALUES (20, 1, 'Skandi Paraty')")

    conn.execute(
        "INSERT INTO epis (id, company_id, unit_id, name, minimum_stock, unit_measure, active) VALUES (101, 1, 10, 'Capacete', 10, 'unidade', 1)"
    )
    conn.execute(
        "INSERT INTO epis (id, company_id, unit_id, name, minimum_stock, unit_measure, active) VALUES (202, 1, 20, 'Luva', 10, 'par', 1)"
    )
    conn.execute(
        "INSERT INTO epis (id, company_id, unit_id, name, minimum_stock, unit_measure, active) VALUES (303, 1, 20, 'Óculos', 5, 'unidade', 1)"
    )

    conn.execute("INSERT INTO unit_epi_stock (company_id, unit_id, epi_id, quantity) VALUES (1, 10, 101, 8)")
    conn.execute("INSERT INTO unit_epi_stock (company_id, unit_id, epi_id, quantity) VALUES (1, 20, 202, 6)")
    conn.execute("INSERT INTO unit_epi_stock (company_id, unit_id, epi_id, quantity) VALUES (1, 20, 303, 5)")

    items = fetch_low_stock_items(conn)

    assert {(int(item['unit_id']), int(item['epi_id'])) for item in items} == {(10, 101), (20, 202), (20, 303)}
    assert {int(item['epi_id']): int(item['minimum_stock']) for item in items} == {101: 10, 202: 10, 303: 5}
    assert {int(item['epi_id']): int(item['stock']) for item in items} == {101: 8, 202: 6, 303: 5}
