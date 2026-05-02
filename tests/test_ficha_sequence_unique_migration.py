import sqlite3

import pytest

import server_postgres
from server_postgres import SchemaMigrationError, _ensure_ficha_periods_sequence_unique


class _Cursor:
    def __init__(self, one=None, all_rows=None):
        self._one = one
        self._all = all_rows or []

    def fetchone(self):
        return self._one

    def fetchall(self):
        return self._all


class FakePgConnection:
    def __init__(self, duplicated_constraints=False, col_info=None, duplicate_groups=None):
        self.executed = []
        self._duplicated_constraints = duplicated_constraints
        self._col_info = col_info if col_info is not None else ('YES', '1')
        self._duplicate_groups = duplicate_groups or []
        self.committed = False

    def execute(self, sql, params=()):
        text = str(sql)
        self.executed.append(text)
        if 'FROM pg_indexes' in text:
            return _Cursor(one=None)
        if 'FROM information_schema.columns' in text:
            return _Cursor(one=self._col_info)
        if 'GROUP BY employee_id, period_start, period_end' in text:
            return _Cursor(all_rows=self._duplicate_groups)
        if 'FROM pg_constraint' in text:
            rows = [('uq_old_employee_window',)] if self._duplicated_constraints else []
            return _Cursor(all_rows=rows)
        return _Cursor()

    def commit(self):
        self.committed = True

    def rollback(self):
        pass


def test_migration_pg_tuple_col_info_without_default_uses_safe_access_and_runs():
    conn = FakePgConnection(duplicated_constraints=False, col_info=('YES', ''), duplicate_groups=[])

    _ensure_ficha_periods_sequence_unique(conn)

    assert any('ALTER TABLE epi_ficha_periods ALTER COLUMN ficha_sequence SET DEFAULT 1' in s for s in conn.executed)
    assert any('ALTER TABLE epi_ficha_periods ALTER COLUMN ficha_sequence SET NOT NULL' in s for s in conn.executed)
    assert any('CREATE UNIQUE INDEX IF NOT EXISTS uq_epi_ficha_periods_employee_window_sequence' in s for s in conn.executed)
    assert conn.committed is True


def test_migration_pg_tuple_metadata_no_default_error_and_emits_metadata_log(monkeypatch):
    captured = []

    def _capture(level, event, **fields):
        captured.append((level, event, fields))

    monkeypatch.setattr(server_postgres, 'structured_log', _capture)

    conn = FakePgConnection(duplicated_constraints=False, col_info=('NO', '1'), duplicate_groups=[])

    _ensure_ficha_periods_sequence_unique(conn)

    metadata_events = [entry for entry in captured if entry[1] == 'db.ficha_sequence_metadata_loaded']
    assert metadata_events
    _, _, payload = metadata_events[0]
    assert payload['is_nullable'] == 'NO'
    assert payload['column_default'] == '1'
    assert any('CREATE UNIQUE INDEX IF NOT EXISTS uq_epi_ficha_periods_employee_window_sequence' in s for s in conn.executed)


def test_migration_pg_drops_legacy_unique_constraint_and_creates_new_unique_index():
    conn = FakePgConnection(
        duplicated_constraints=True,
        col_info={'ficha_sequence_is_nullable': 'NO', 'ficha_sequence_column_default': '1'},
        duplicate_groups=[],
    )

    _ensure_ficha_periods_sequence_unique(conn)

    assert any('DROP CONSTRAINT IF EXISTS "uq_old_employee_window"' in s for s in conn.executed)
    assert any('CREATE UNIQUE INDEX IF NOT EXISTS uq_epi_ficha_periods_employee_window_sequence' in s for s in conn.executed)


def test_migration_sqlite_empty_table_is_noop():
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE epi_ficha_periods (
            id INTEGER PRIMARY KEY,
            employee_id INTEGER,
            period_start TEXT,
            period_end TEXT,
            ficha_sequence INTEGER NOT NULL DEFAULT 1,
            UNIQUE(employee_id, period_start, period_end, ficha_sequence)
        )
        """
    )

    _ensure_ficha_periods_sequence_unique(conn)

    idx_rows = conn.execute("PRAGMA index_list('epi_ficha_periods')").fetchall()
    assert idx_rows


def test_migration_raises_blocking_error_on_real_failure():
    class BrokenConn(FakePgConnection):
        def execute(self, sql, params=()):
            text = str(sql)
            if 'CREATE UNIQUE INDEX IF NOT EXISTS uq_epi_ficha_periods_employee_window_sequence' in text:
                raise RuntimeError('forced failure')
            return super().execute(sql, params)

    with pytest.raises(SchemaMigrationError):
        _ensure_ficha_periods_sequence_unique(BrokenConn())


def test_migration_duplicate_groups_emit_log_and_raise(monkeypatch):
    captured = []

    def _capture(level, event, **fields):
        captured.append((level, event, fields))

    monkeypatch.setattr(server_postgres, 'structured_log', _capture)

    duplicate_rows = [
        {'employee_id': 10, 'period_start': '2026-01-01', 'period_end': '2026-01-14', 'duplicate_count': 2},
        {'employee_id': 20, 'period_start': '2026-02-01', 'period_end': '2026-02-14', 'duplicate_count': 3},
    ]
    conn = FakePgConnection(duplicate_groups=duplicate_rows)

    with pytest.raises(SchemaMigrationError):
        _ensure_ficha_periods_sequence_unique(conn)

    duplicate_events = [entry for entry in captured if entry[1] == 'db.ficha_periods_duplicate_detected']
    assert duplicate_events, 'evento de duplicidade não foi emitido'
    _, _, payload = duplicate_events[0]
    assert payload['count'] == 2
    assert isinstance(payload['sample'], list)
    assert payload['sample'][0]['employee_id'] == 10
    assert payload['sample'][0]['duplicate_count'] == 2
