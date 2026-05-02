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
    def __init__(self, duplicated_constraints=False, col_info='__DEFAULT__', duplicate_groups=None):
        self.executed = []
        self._duplicated_constraints = duplicated_constraints
        self._col_info = ('YES', '1') if col_info == '__DEFAULT__' else col_info
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


class DictRowLike:
    def __init__(self, mapping):
        self._mapping = dict(mapping)

    def keys(self):
        return list(self._mapping.keys())

    def __getitem__(self, key):
        return self._mapping[key]


class RenderDictRow:
    def __init__(self, values, key_map):
        self._values = list(values)
        self._key_map = dict(key_map)

    def __getitem__(self, key):
        if isinstance(key, str):
            if key not in self._key_map:
                raise KeyError(key)
            index = self._key_map[key]
            if index >= len(self._values):
                raise IndexError(index)
            return self._values[index]
        return self._values[key]

    def keys(self):
        return list(self._key_map.keys())

    def __iter__(self):
        return iter(self._values)

    def __len__(self):
        return len(self._values)

    def __repr__(self):
        return repr(self._values)


class BrokenKeysRow:
    def keys(self):
        return ['constraint_name']

    def __getitem__(self, key):
        raise IndexError('simulated broken DictRow access')


def test_migration_pg_tuple_col_info_without_default_uses_safe_access_and_runs():
    conn = FakePgConnection(duplicated_constraints=False, col_info=('YES', ''), duplicate_groups=[])

    _ensure_ficha_periods_sequence_unique(conn)

    assert any('ALTER TABLE epi_ficha_periods ALTER COLUMN ficha_sequence SET DEFAULT 1' in s for s in conn.executed)
    assert any('ALTER TABLE epi_ficha_periods ALTER COLUMN ficha_sequence SET NOT NULL' in s for s in conn.executed)
    assert any('CREATE UNIQUE INDEX IF NOT EXISTS uq_epi_ficha_periods_employee_window_sequence' in s for s in conn.executed)
    assert conn.committed is True


def test_migration_pg_metadata_none_raises_controlled_error(monkeypatch):
    captured = []

    def _capture(level, event, **fields):
        captured.append((level, event, fields))

    monkeypatch.setattr(server_postgres, 'structured_log', _capture)

    conn = FakePgConnection(col_info=None)

    with pytest.raises(SchemaMigrationError) as exc_info:
        _ensure_ficha_periods_sequence_unique(conn)

    assert exc_info.value.kind == 'schema_missing_object'
    raw_events = [entry for entry in captured if entry[1] == 'db.ficha_sequence_metadata_raw']
    assert raw_events


def test_migration_pg_metadata_tuple_len_one_raises_controlled_error(monkeypatch):
    captured = []

    def _capture(level, event, **fields):
        captured.append((level, event, fields))

    monkeypatch.setattr(server_postgres, 'structured_log', _capture)

    conn = FakePgConnection(col_info=('YES',))

    with pytest.raises(SchemaMigrationError) as exc_info:
        _ensure_ficha_periods_sequence_unique(conn)

    assert exc_info.value.kind == 'schema_health_failed'
    assert exc_info.value.context.get('row_len') == 1
    assert exc_info.value.context.get('expected_len') == 2
    raw_events = [entry for entry in captured if entry[1] == 'db.ficha_sequence_metadata_raw']
    assert raw_events


def test_migration_pg_tuple_metadata_logs_and_creates_unique_index(monkeypatch):
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
    assert duplicate_events
    _, _, payload = duplicate_events[0]
    assert payload['count'] == 2
    assert isinstance(payload['sample'], list)
    assert payload['sample'][0]['employee_id'] == 10
    assert payload['sample'][0]['duplicate_count'] == 2


def test_migration_duplicate_rows_tuple_shape_is_handled_without_index_error():
    duplicate_rows = [(10, '2026-01-01', '2026-01-14', 2)]
    conn = FakePgConnection(duplicate_groups=duplicate_rows)

    with pytest.raises(SchemaMigrationError) as exc_info:
        _ensure_ficha_periods_sequence_unique(conn)

    assert exc_info.value.kind == 'duplicate_key_conflict'


def test_migration_constraint_rows_tuple_shape_is_handled():
    conn = FakePgConnection(duplicated_constraints=True, duplicate_groups=[])

    _ensure_ficha_periods_sequence_unique(conn)

    assert any('DROP CONSTRAINT IF EXISTS "uq_old_employee_window"' in s for s in conn.executed)


def test_migration_constraint_rows_dictrow_shape_is_handled():
    class DictConstraintConn(FakePgConnection):
        def execute(self, sql, params=()):
            text = str(sql)
            self.executed.append(text)
            if 'FROM pg_indexes' in text:
                return _Cursor(one=None)
            if 'FROM information_schema.columns' in text:
                return _Cursor(one=DictRowLike({'ficha_sequence_is_nullable': 'NO', 'ficha_sequence_column_default': '1'}))
            if 'GROUP BY employee_id, period_start, period_end' in text:
                return _Cursor(all_rows=[])
            if 'FROM pg_constraint' in text:
                return _Cursor(all_rows=[DictRowLike({'constraint_name': 'uq_old_employee_window'})])
            return _Cursor()

    conn = DictConstraintConn()
    _ensure_ficha_periods_sequence_unique(conn)
    assert any('DROP CONSTRAINT IF EXISTS "uq_old_employee_window"' in s for s in conn.executed)


def test_migration_constraint_alias_conname_is_supported():
    class ConnameConn(FakePgConnection):
        def execute(self, sql, params=()):
            text = str(sql)
            self.executed.append(text)
            if 'FROM pg_indexes' in text:
                return _Cursor(one=None)
            if 'FROM information_schema.columns' in text:
                return _Cursor(one={'ficha_sequence_is_nullable': 'NO', 'ficha_sequence_column_default': '1'})
            if 'GROUP BY employee_id, period_start, period_end' in text:
                return _Cursor(all_rows=[])
            if 'FROM pg_constraint' in text:
                return _Cursor(all_rows=[{'conname': 'uq_old_employee_window'}])
            return _Cursor()

    conn = ConnameConn()
    _ensure_ficha_periods_sequence_unique(conn)
    assert any('DROP CONSTRAINT IF EXISTS "uq_old_employee_window"' in s for s in conn.executed)


def test_migration_dictrow_keys_access_failure_raises_contextual_schema_error():
    class BrokenConstraintConn(FakePgConnection):
        def execute(self, sql, params=()):
            text = str(sql)
            self.executed.append(text)
            if 'FROM pg_indexes' in text:
                return _Cursor(one=None)
            if 'FROM information_schema.columns' in text:
                return _Cursor(one={'ficha_sequence_is_nullable': 'NO', 'ficha_sequence_column_default': '1'})
            if 'GROUP BY employee_id, period_start, period_end' in text:
                return _Cursor(all_rows=[])
            if 'FROM pg_constraint' in text:
                return _Cursor(all_rows=[BrokenKeysRow()])
            return _Cursor()

    with pytest.raises(SchemaMigrationError) as exc_info:
        _ensure_ficha_periods_sequence_unique(BrokenConstraintConn())

    assert exc_info.value.kind == 'driver_unexpected'
    assert 'tuple index out of range' not in str(exc_info.value).lower()
    assert exc_info.value.context.get('step') == 'normalize_legacy_constraint_row'


def test_migration_tuple_short_never_leaks_raw_index_error():
    class ShortTupleConstraintConn(FakePgConnection):
        def execute(self, sql, params=()):
            text = str(sql)
            self.executed.append(text)
            if 'FROM pg_indexes' in text:
                return _Cursor(one=None)
            if 'FROM information_schema.columns' in text:
                return _Cursor(one={'ficha_sequence_is_nullable': 'NO', 'ficha_sequence_column_default': '1'})
            if 'GROUP BY employee_id, period_start, period_end' in text:
                return _Cursor(all_rows=[])
            if 'FROM pg_constraint' in text:
                return _Cursor(all_rows=[tuple()])
            return _Cursor()

    with pytest.raises(SchemaMigrationError) as exc_info:
        _ensure_ficha_periods_sequence_unique(ShortTupleConstraintConn())

    assert exc_info.value.kind == 'schema_health_failed'
    assert exc_info.value.context.get('row_len') == 0
    assert exc_info.value.context.get('expected_len') == 1


def test_migration_render_dictrow_shape_logs_checkpoints_and_completes(monkeypatch):
    captured = []

    def _capture(level, event, **fields):
        captured.append((level, event, fields))

    monkeypatch.setattr(server_postgres, 'structured_log', _capture)

    class RenderShapeConn(FakePgConnection):
        def execute(self, sql, params=()):
            text = str(sql)
            self.executed.append(text)
            if 'FROM pg_indexes' in text:
                return _Cursor(one=None)
            if 'FROM information_schema.columns' in text:
                return _Cursor(
                    one=RenderDictRow(
                        values=['NO', '1'],
                        key_map={'ficha_sequence_is_nullable': 0, 'is_nullable': 0, 'ficha_sequence_column_default': 1, 'column_default': 1},
                    )
                )
            if 'GROUP BY employee_id, period_start, period_end' in text:
                return _Cursor(all_rows=[])
            if 'FROM pg_constraint' in text:
                return _Cursor(
                    all_rows=[
                        RenderDictRow(values=['uq_old_employee_window'], key_map={'constraint_name': 0, 'conname': 0})
                    ]
                )
            return _Cursor()

    conn = RenderShapeConn()
    _ensure_ficha_periods_sequence_unique(conn)

    events = [e for _, e, _ in captured]
    assert 'db.ficha_sequence_before_load_legacy_constraints' in events
    assert 'db.ficha_sequence_after_load_legacy_constraints' in events
    assert 'db.ficha_sequence_before_drop_legacy_constraint' in events
    assert 'db.ficha_sequence_after_drop_legacy_constraint' in events
    assert 'db.ficha_sequence_before_create_unique_index' in events
    assert 'db.ficha_sequence_after_create_unique_index' in events
    assert not any('tuple index out of range' in str(fields.get('error', '')) for _, event, fields in captured if event == 'db.ficha_periods_unique_migration_failed')


def test_migration_returns_early_when_unique_index_already_exists():
    class IndexExistsConn(FakePgConnection):
        def execute(self, sql, params=()):
            text = str(sql)
            self.executed.append(text)
            if 'FROM pg_indexes' in text:
                return _Cursor(one=DictRowLike({'exists_flag': 1}))
            return _Cursor()

    conn = IndexExistsConn()
    _ensure_ficha_periods_sequence_unique(conn)
    assert not any('CREATE UNIQUE INDEX IF NOT EXISTS uq_epi_ficha_periods_employee_window_sequence' in s for s in conn.executed)
