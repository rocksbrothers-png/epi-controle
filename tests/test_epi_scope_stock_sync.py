import sqlite3

from server_postgres import backfill_unit_stock_from_epis, sync_epi_scope_stock_unit


def make_connection():
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
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
        CREATE TABLE epis (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL,
            unit_id INTEGER,
            stock INTEGER NOT NULL DEFAULT 0
        )
        '''
    )
    return conn


def test_transfer_stock_when_scope_changes_between_units():
    conn = make_connection()
    conn.execute(
        'INSERT INTO unit_epi_stock (company_id, unit_id, epi_id, quantity, updated_at) VALUES (?,?,?,?,?)',
        (1, 10, 99, 7, '2026-01-01T00:00:00+00:00'),
    )

    sync_epi_scope_stock_unit(conn, 1, 99, 10, 20)

    old_row = conn.execute('SELECT * FROM unit_epi_stock WHERE company_id = 1 AND unit_id = 10 AND epi_id = 99').fetchone()
    new_row = conn.execute('SELECT * FROM unit_epi_stock WHERE company_id = 1 AND unit_id = 20 AND epi_id = 99').fetchone()
    assert old_row is None
    assert new_row is not None
    assert int(new_row['quantity']) == 7


def test_no_transfer_when_new_scope_is_global():
    conn = make_connection()
    conn.execute(
        'INSERT INTO unit_epi_stock (company_id, unit_id, epi_id, quantity, updated_at) VALUES (?,?,?,?,?)',
        (1, 10, 99, 7, '2026-01-01T00:00:00+00:00'),
    )

    sync_epi_scope_stock_unit(conn, 1, 99, 10, None)

    row = conn.execute('SELECT * FROM unit_epi_stock WHERE company_id = 1 AND unit_id = 10 AND epi_id = 99').fetchone()
    assert row is not None
    assert int(row['quantity']) == 7


def test_backfill_unit_stock_ignores_global_epi_without_unit():
    conn = make_connection()
    conn.execute('INSERT INTO epis (id, company_id, unit_id, stock) VALUES (25, 2, NULL, 0)')
    conn.execute('INSERT INTO epis (id, company_id, unit_id, stock) VALUES (26, 2, 7, 3)')

    backfill_unit_stock_from_epis(conn, '2026-04-16T00:38:37.640395+00:00')

    global_row = conn.execute('SELECT * FROM unit_epi_stock WHERE epi_id = 25').fetchone()
    scoped_row = conn.execute('SELECT * FROM unit_epi_stock WHERE epi_id = 26').fetchone()
    assert global_row is None
    assert scoped_row is not None
    assert int(scoped_row['unit_id']) == 7
    assert int(scoped_row['quantity']) == 3
