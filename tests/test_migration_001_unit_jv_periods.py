import importlib
import sqlite3


migration = importlib.import_module('epi_backend.migrations.001_unit_jv_periods')


def _conn():
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.execute('CREATE TABLE units (id INTEGER PRIMARY KEY, company_id INTEGER NOT NULL)')
    conn.execute('CREATE TABLE epis (id INTEGER PRIMARY KEY, company_id INTEGER NOT NULL, unit_id INTEGER, active_joinventure TEXT)')
    conn.execute('INSERT INTO units (id, company_id) VALUES (?, ?)', (1, 1))
    conn.execute(
        'INSERT INTO epis (id, company_id, unit_id, active_joinventure) VALUES (?, ?, ?, ?)',
        (1, 1, 1, 'JV-X'),
    )
    return conn


def test_run_is_idempotent_and_imports_active_joinventure():
    conn = _conn()

    first = migration.run(conn)
    second = migration.run(conn)

    assert first['migration_id'] == '001_unit_jv_periods'
    assert first['imported_rows'] == 1
    assert second['imported_rows'] == 0

    rows = conn.execute('SELECT * FROM unit_joint_venture_periods').fetchall()
    assert len(rows) == 1
    assert rows[0]['joint_venture_name'] == 'JV-X'
