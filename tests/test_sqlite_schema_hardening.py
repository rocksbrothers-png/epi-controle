import sqlite3
from pathlib import Path

import pytest

from server_postgres import (
    SchemaMigrationError,
    _safe_add_column,
    ensure_devolution_columns,
    run_schema_precheck,
    validate_schema_health,
)


class SQLiteSpyConnection:
    def __init__(self, raw_connection):
        self._raw = raw_connection
        self.executed_sql = []

    def execute(self, sql, params=()):
        self.executed_sql.append(str(sql))
        return self._raw.execute(sql, params)

    def commit(self):
        return self._raw.commit()

    def rollback(self):
        return self._raw.rollback()


class _FakeCursor:
    def __init__(self, rows):
        self._rows = list(rows)

    def fetchone(self):
        return self._rows[0] if self._rows else None

    def fetchall(self):
        return self._rows


class BrokenSQLiteConnection:
    """Simula SQLite legado que falha ao alterar schema e não cria coluna."""

    def execute(self, sql, params=()):
        sql_text = str(sql).strip().lower()
        if 'sqlite_master' in sql_text:
            return _FakeCursor([(1,)])
        if sql_text.startswith('pragma table_info'):
            return _FakeCursor([])
        if sql_text.startswith('alter table'):
            raise sqlite3.OperationalError('legacy sqlite syntax error')
        return _FakeCursor([])

    def commit(self):
        return None

    def rollback(self):
        return None


def test_safe_add_column_works_on_legacy_style_without_if_not_exists():
    raw = sqlite3.connect(':memory:')
    raw.row_factory = sqlite3.Row
    raw.execute('CREATE TABLE deliveries (id INTEGER PRIMARY KEY)')
    conn = SQLiteSpyConnection(raw)

    _safe_add_column(conn, 'deliveries', 'returned_date', "TEXT NOT NULL DEFAULT ''")

    cols = {row['name'] for row in raw.execute('PRAGMA table_info(deliveries)').fetchall()}
    assert 'returned_date' in cols
    alter_sql = [item for item in conn.executed_sql if item.strip().upper().startswith('ALTER TABLE')]
    assert alter_sql, 'ALTER TABLE não executado'
    assert all('IF NOT EXISTS' not in item.upper() for item in alter_sql)


def test_safe_add_column_is_idempotent_when_column_already_exists():
    raw = sqlite3.connect(':memory:')
    raw.row_factory = sqlite3.Row
    raw.execute("CREATE TABLE deliveries (id INTEGER PRIMARY KEY, returned_date TEXT NOT NULL DEFAULT '')")
    conn = SQLiteSpyConnection(raw)

    _safe_add_column(conn, 'deliveries', 'returned_date', "TEXT NOT NULL DEFAULT ''")

    alter_sql = [item for item in conn.executed_sql if item.strip().upper().startswith('ALTER TABLE')]
    assert not alter_sql


def test_safe_add_column_raises_when_column_still_missing_after_failure():
    with pytest.raises(SchemaMigrationError):
        _safe_add_column(BrokenSQLiteConnection(), 'deliveries', 'returned_date', "TEXT NOT NULL DEFAULT ''")


def test_ensure_devolution_columns_upgrades_old_sqlite_schema():
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = OFF')
    conn.execute('CREATE TABLE companies (id INTEGER PRIMARY KEY)')
    conn.execute('CREATE TABLE users (id INTEGER PRIMARY KEY)')
    conn.execute('CREATE TABLE units (id INTEGER PRIMARY KEY)')
    conn.execute('CREATE TABLE employees (id INTEGER PRIMARY KEY)')
    conn.execute('CREATE TABLE epis (id INTEGER PRIMARY KEY)')
    conn.execute('CREATE TABLE stock_movements (id INTEGER PRIMARY KEY)')
    conn.execute('CREATE TABLE epi_stock_items (id INTEGER PRIMARY KEY)')
    conn.execute('CREATE TABLE epi_ficha_periods (id INTEGER PRIMARY KEY)')
    conn.execute('CREATE TABLE deliveries (id INTEGER PRIMARY KEY)')

    ensure_devolution_columns(conn)

    delivery_cols = {row['name'] for row in conn.execute('PRAGMA table_info(deliveries)').fetchall()}
    devolution_cols = {row['name'] for row in conn.execute('PRAGMA table_info(epi_devolutions)').fetchall()}
    assert {'returned_date', 'returned_condition', 'returned_notes', 'return_movement_id'}.issubset(delivery_cols)
    assert {'ficha_period_id', 'stock_item_id', 'stock_movement_id', 'signature_name', 'signature_at'}.issubset(devolution_cols)


def test_schema_precheck_detects_readonly_sqlite(tmp_path):
    db_file = tmp_path / 'readonly.db'
    writer = sqlite3.connect(db_file)
    writer.execute('CREATE TABLE sample (id INTEGER PRIMARY KEY)')
    writer.commit()
    writer.close()

    readonly = sqlite3.connect(f'file:{db_file}?mode=ro', uri=True)
    try:
        with pytest.raises(SchemaMigrationError) as exc:
            run_schema_precheck(readonly)
        assert exc.value.kind in {'readonly_database', 'permission_denied'}
    finally:
        readonly.close()


def test_schema_precheck_detects_corrupted_sqlite_file(tmp_path):
    db_file = tmp_path / 'corrupted.db'
    Path(db_file).write_bytes(b'not-a-valid-sqlite-db')
    conn = sqlite3.connect(db_file)
    try:
        with pytest.raises(SchemaMigrationError) as exc:
            run_schema_precheck(conn)
        assert exc.value.kind in {'corrupted_database', 'driver_unexpected'}
    finally:
        conn.close()


def test_schema_health_fails_when_required_table_or_column_missing():
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.execute('CREATE TABLE deliveries (id INTEGER PRIMARY KEY)')
    with pytest.raises(SchemaMigrationError) as exc:
        validate_schema_health(conn)
    assert exc.value.kind == 'schema_health_failed'


def test_schema_health_passes_with_minimum_expected_structure():
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.execute(
        '''
        CREATE TABLE deliveries (
            id INTEGER PRIMARY KEY,
            company_id INTEGER,
            employee_id INTEGER,
            epi_id INTEGER,
            delivery_date TEXT,
            returned_date TEXT,
            returned_condition TEXT,
            return_movement_id INTEGER
        )
        '''
    )
    conn.execute(
        '''
        CREATE TABLE epi_devolutions (
            id INTEGER PRIMARY KEY,
            delivery_id INTEGER,
            returned_date TEXT,
            ficha_period_id INTEGER,
            stock_movement_id INTEGER,
            signature_name TEXT,
            signature_at TEXT
        )
        '''
    )
    conn.execute(
        '''
        CREATE TABLE stock_movements (
            id INTEGER PRIMARY KEY,
            company_id INTEGER,
            unit_id INTEGER,
            epi_id INTEGER,
            movement_type TEXT,
            source_type TEXT
        )
        '''
    )
    conn.execute('CREATE TABLE epi_stock_items (id INTEGER PRIMARY KEY, delivery_id INTEGER, status TEXT)')
    conn.execute('CREATE TABLE epi_ficha_periods (id INTEGER PRIMARY KEY, employee_id INTEGER, period_start TEXT, period_end TEXT, status TEXT)')
    conn.execute('CREATE TABLE epi_ficha_items (id INTEGER PRIMARY KEY, ficha_period_id INTEGER, delivery_id INTEGER)')
    validate_schema_health(conn)
