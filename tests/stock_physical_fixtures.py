"""Explicit physical backing for legacy unit-test fixtures, never production.

Test expiry 9999-12-31 is a declared input to keep unrelated reservation tests
independent of today's date; no catalog dates or factory dates are inferred.
"""

from epi_backend.db import table_columns, table_exists


def ensure_test_physical_schema(connection):
    if not table_exists(connection, 'companies'):
        connection.execute('CREATE TABLE companies(id INTEGER PRIMARY KEY, timezone TEXT)')
        connection.execute("INSERT INTO companies VALUES(1, 'UTC')")
    if not table_exists(connection, 'units'):
        connection.execute('CREATE TABLE units(id INTEGER PRIMARY KEY, company_id INTEGER)')
        connection.execute('INSERT INTO units VALUES(2,1)')
    elif 'company_id' not in table_columns(connection, 'units'):
        connection.execute('ALTER TABLE units ADD COLUMN company_id INTEGER DEFAULT 1')
    if table_exists(connection, 'epis') and 'company_id' not in table_columns(connection, 'epis'):
        connection.execute('ALTER TABLE epis ADD COLUMN company_id INTEGER DEFAULT 1')
    if not table_exists(connection, 'epi_stock_items'):
        connection.execute('CREATE TABLE epi_stock_items(id INTEGER PRIMARY KEY, company_id INTEGER, '
                           'unit_id INTEGER, epi_id INTEGER, status TEXT, qr_code_value TEXT, physical_expiry_date TEXT)')
    if 'physical_expiry_date' not in table_columns(connection, 'epi_stock_items'):
        connection.execute('ALTER TABLE epi_stock_items ADD COLUMN physical_expiry_date TEXT')


def seed_test_physical_backing(connection):
    ensure_test_physical_schema(connection)
    for company, unit, epi, quantity in connection.execute(
            'SELECT company_id, unit_id, epi_id, quantity FROM unit_epi_stock').fetchall():
        present = connection.execute('SELECT COUNT(*) FROM epi_stock_items WHERE company_id=? AND unit_id=? AND epi_id=?',
                                     (company, unit, epi)).fetchone()[0]
        for index in range(present, max(0, quantity)):
            connection.execute("INSERT INTO epi_stock_items(company_id,unit_id,epi_id,status,qr_code_value,physical_expiry_date) "
                               "VALUES(?,?,?,'in_stock',?,'9999-12-31')", (company, unit, epi, f'TEST-{unit}-{epi}-{index}'))
