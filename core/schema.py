"""Schema migrations e infraestrutura de banco de dados.

Contém: SchemaMigrationError, helpers de detecção de esquema,
runner de migrations, e todas as funções ensure_* de tabelas/colunas.
"""

import importlib.util
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from types import ModuleType

from epi_backend.http_utils import structured_log

UTC = timezone.utc

# ── Estado em memória do runner de migrations ────────────────────────────────

MIGRATION_RUNTIME_STATE: dict = {
    'status': 'not_started',
    'last_error': '',
    'applied': [],
    'failed_migration': '',
}
MIGRATION_RUNTIME_STATE_LOCK = threading.Lock()


def _set_migration_runtime_state(**values) -> None:
    with MIGRATION_RUNTIME_STATE_LOCK:
        MIGRATION_RUNTIME_STATE.update(values)


def _get_migration_runtime_state() -> dict:
    with MIGRATION_RUNTIME_STATE_LOCK:
        return dict(MIGRATION_RUNTIME_STATE)


def _discover_migration_modules() -> list:
    migrations_dir = Path(__file__).resolve().parent.parent / 'epi_backend' / 'migrations'
    modules = []
    for path in sorted(migrations_dir.glob('[0-9][0-9][0-9]_*.py')):
        if path.name == '__init__.py':
            continue
        module_name = f"epi_backend.migrations.{path.stem}"
        modules.append((path, module_name))
    return modules


def _load_migration_module(path: Path, module_name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(module_name, str(path))
    if spec is None or spec.loader is None:
        raise RuntimeError(f'Não foi possível carregar migration module: {path.name}')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_pending_migrations(connection) -> dict:
    if _is_sqlite_connection(connection):
        _set_migration_runtime_state(
            status='skipped_sqlite',
            last_error='',
            failed_migration='',
            applied=[],
        )
        structured_log('info', 'db.migration_runner_skipped', reason='sqlite_connection')
        return {
            'status': 'skipped_sqlite',
            'applied': [],
            'failed_migration': '',
            'error': '',
        }

    connection.execute(
        '''
        CREATE TABLE IF NOT EXISTS app_migrations (
            migration_id TEXT PRIMARY KEY,
            status TEXT NOT NULL,
            applied_at TEXT NOT NULL
        )
        '''
    )
    connection.commit()
    applied_rows = connection.execute(
        "SELECT migration_id FROM app_migrations WHERE status = 'applied'"
    ).fetchall()
    applied_ids = {str((row['migration_id'] if hasattr(row, 'keys') else row[0])) for row in applied_rows}

    discovered = _discover_migration_modules()
    for path, module_name in discovered:
        module = _load_migration_module(path, module_name)
        migration_id = str(getattr(module, 'MIGRATION_ID', '') or '').strip()
        run_fn = getattr(module, 'run', None)
        if not migration_id or not callable(run_fn):
            raise RuntimeError(f'Migration inválida: {path.name} (MIGRATION_ID/run ausente)')
        if migration_id in applied_ids:
            continue
        try:
            result = run_fn(connection)
            connection.execute(
                'INSERT INTO app_migrations (migration_id, status, applied_at) VALUES (?, ?, ?)',
                (migration_id, 'applied', datetime.now(UTC).isoformat())
            )
            connection.commit()
            applied_ids.add(migration_id)
            structured_log(
                'info',
                'db.migration_applied',
                migration_id=migration_id,
                module=path.name,
                result=str(result or ''),
            )
        except Exception as exc:
            try:
                connection.rollback()
            except Exception:
                pass
            structured_log(
                'error',
                'db.migration_failed',
                migration_id=migration_id,
                module=path.name,
                error=str(exc),
                action='server_continuing_in_degraded_mode',
            )
            _set_migration_runtime_state(
                status='degraded',
                last_error=str(exc),
                failed_migration=migration_id,
            )
            return {
                'status': 'degraded',
                'applied': sorted(applied_ids),
                'failed_migration': migration_id,
                'error': str(exc),
            }
    _set_migration_runtime_state(
        status='ok',
        last_error='',
        failed_migration='',
        applied=sorted(applied_ids),
    )
    return {
        'status': 'ok',
        'applied': sorted(applied_ids),
        'failed_migration': '',
        'error': '',
    }


# ── Classe de erro e helpers de schema ───────────────────────────────────────

class SchemaMigrationError(RuntimeError):
    """Erro fatal de migração estrutural do banco."""

    def __init__(self, message, *, kind='unexpected', context=None):
        super().__init__(message)
        self.kind = str(kind or 'unexpected')
        self.context = context or {}


def _is_sqlite_connection(connection) -> bool:
    module_name = str(getattr(type(connection), '__module__', '')).lower()
    class_name = str(getattr(type(connection), '__name__', '')).lower()
    return 'sqlite' in module_name or 'sqlite' in class_name


def _classify_db_error(error) -> str:
    message = str(error or '').lower()
    if isinstance(error, (PermissionError,)):
        return 'permission_denied'
    if isinstance(error, OSError):
        return 'io_error'
    if 'readonly' in message or 'read-only' in message or 'attempt to write a readonly database' in message:
        return 'readonly_database'
    if 'permission denied' in message or 'not authorized' in message:
        return 'permission_denied'
    if 'malformed' in message or 'corrupt' in message or 'not a database' in message:
        return 'corrupted_database'
    if 'i/o error' in message or 'input/output error' in message or 'disk i/o' in message:
        return 'io_error'
    if 'syntax error' in message or 'unsupported' in message:
        return 'ddl_incompatible'
    if 'no such table' in message or 'no such column' in message:
        return 'schema_missing_object'
    return 'driver_unexpected'


def _table_exists(connection, table) -> bool:
    table_name = str(table or '').strip()
    if not table_name:
        return False
    try:
        if _is_sqlite_connection(connection):
            row = connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ? LIMIT 1",
                (table_name,),
            ).fetchone()
            return row is not None
        row = connection.execute(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_name = ? LIMIT 1",
            (table_name,),
        ).fetchone()
        return row is not None
    except Exception:
        return False


def _table_columns(connection, table) -> set:
    table_name = str(table or '').strip()
    if not table_name:
        return set()
    try:
        if _is_sqlite_connection(connection):
            rows = connection.execute(f"PRAGMA table_info({table_name})").fetchall()
            return {str(row['name'] if isinstance(row, dict) else row[1]) for row in rows}
        rows = connection.execute(
            "SELECT column_name FROM information_schema.columns WHERE table_name = ?",
            (table_name,),
        ).fetchall()
        result = set()
        for row in rows:
            if isinstance(row, dict):
                result.add(str(row.get('column_name') or ''))
            elif hasattr(row, 'keys'):
                result.add(str(row['column_name']))
            else:
                result.add(str(row[0]))
        return {item for item in result if item}
    except Exception:
        return set()


def _col_exists(connection, table, column) -> bool:
    return str(column or '').strip() in _table_columns(connection, table)


def _safe_add_column(connection, table, column, definition, log_event='db.col_skip') -> None:
    """Adiciona coluna apenas se ela não existir e valida pós-migração."""
    table_name = str(table or '').strip()
    column_name = str(column or '').strip()
    if not table_name or not column_name:
        raise SchemaMigrationError(
            f'Parâmetros inválidos de migração: table={table_name!r}, column={column_name!r}.',
            kind='migration_invalid_arguments',
            context={'table': table_name, 'column': column_name, 'phase': 'migration'},
        )
    if not _table_exists(connection, table_name):
        raise SchemaMigrationError(
            f'Tabela ausente para migração de coluna: {table_name}.',
            kind='schema_missing_table',
            context={'table': table_name, 'column': column_name, 'phase': 'migration'},
        )
    if _col_exists(connection, table_name, column_name):
        return  # coluna ja existe — nao toca na tabela
    try:
        connection.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}")
        connection.commit()
        if not _col_exists(connection, table_name, column_name):
            raise SchemaMigrationError(
                f'Coluna {table_name}.{column_name} não encontrada após ALTER TABLE.',
                kind='column_missing_after_migration',
                context={'table': table_name, 'column': column_name, 'phase': 'post_migration_validation'},
            )
        structured_log('info', 'db.col_added', table=table_name, column=column_name)
    except Exception as _e:
        try:
            connection.rollback()
        except Exception:
            pass
        if _col_exists(connection, table_name, column_name):
            structured_log('info', 'db.col_already_present_after_error', table=table_name, column=column_name, error=str(_e))
            return
        kind = _classify_db_error(_e)
        structured_log('error', log_event, table=table_name, column=column_name, error=str(_e), kind=kind, phase='migration')
        raise SchemaMigrationError(
            f'Falha ao adicionar coluna {table_name}.{column_name}: {_e}',
            kind=kind,
            context={'table': table_name, 'column': column_name, 'phase': 'migration'},
        ) from _e


def run_schema_precheck(connection) -> None:
    """Pré-check bloqueante do ambiente de banco antes de migrar schema."""
    phase = 'precheck'
    structured_log('info', 'db.schema_precheck_started', sqlite=bool(_is_sqlite_connection(connection)))
    try:
        connection.execute('SELECT 1').fetchone()
        if _is_sqlite_connection(connection):
            db_row = connection.execute('PRAGMA database_list').fetchone()
            db_path = ''
            if db_row:
                try:
                    db_path = str(db_row['file'])
                except Exception:
                    db_path = str(db_row[2] if len(db_row) > 2 else '')
            query_only_row = connection.execute('PRAGMA query_only').fetchone()
            query_only = int(query_only_row[0] if query_only_row else 0)
            if query_only == 1:
                raise SchemaMigrationError('Banco SQLite está em modo somente leitura (PRAGMA query_only=1).', kind='readonly_database', context={'phase': phase, 'database_path': db_path})
            integrity_row = connection.execute('PRAGMA quick_check').fetchone()
            integrity_result = str(integrity_row[0] if integrity_row else '').strip().lower()
            if integrity_result not in {'ok', 'ok\n'}:
                raise SchemaMigrationError(f'Integridade SQLite inválida: {integrity_result or "desconhecido"}.', kind='corrupted_database', context={'phase': phase, 'database_path': db_path})
            connection.execute('DROP TABLE IF EXISTS __schema_precheck_write__')
            connection.execute('CREATE TABLE __schema_precheck_write__ (id INTEGER)')
            connection.execute('DROP TABLE __schema_precheck_write__')
            connection.commit()
            structured_log('info', 'db.schema_precheck_ok', phase=phase, database_path=db_path or ':memory:')
            return
        # PostgreSQL/Outros via wrapper
        try:
            ro_row = connection.execute('SHOW transaction_read_only').fetchone()
            read_only = str(ro_row[0] if ro_row else '').strip().lower()
            if read_only in {'on', 'true', '1'}:
                raise SchemaMigrationError('Sessão do banco em modo somente leitura.', kind='readonly_database', context={'phase': phase})
        except SchemaMigrationError:
            raise
        except Exception as read_only_error:
            structured_log('warning', 'db.schema_precheck_readonly_probe_failed', phase=phase, error=str(read_only_error))
        structured_log('info', 'db.schema_precheck_ok', phase=phase, database_path='remote')
    except SchemaMigrationError:
        raise
    except Exception as exc:
        try:
            connection.rollback()
        except Exception:
            pass
        kind = _classify_db_error(exc)
        structured_log('error', 'db.schema_precheck_failed', phase=phase, error=str(exc), kind=kind)
        raise SchemaMigrationError(f'Pré-check de schema falhou: {exc}', kind=kind, context={'phase': phase}) from exc


def validate_schema_health(connection) -> None:
    """Validação bloqueante do schema mínimo esperado para subir a aplicação."""
    required_schema = {
        'deliveries': {'id', 'company_id', 'employee_id', 'epi_id', 'delivery_date', 'returned_date', 'returned_condition', 'return_movement_id'},
        'epi_devolutions': {'id', 'delivery_id', 'returned_date', 'ficha_period_id', 'stock_movement_id', 'signature_name', 'signature_at'},
        'stock_movements': {'id', 'company_id', 'unit_id', 'epi_id', 'movement_type', 'source_type'},
        'epi_stock_items': {'id', 'delivery_id', 'status'},
        'epi_ficha_periods': {'id', 'employee_id', 'period_start', 'period_end', 'status'},
        'epi_ficha_items': {'id', 'ficha_period_id', 'delivery_id'},
    }
    missing = []
    for table, columns in required_schema.items():
        if not _table_exists(connection, table):
            missing.append(f'table:{table}')
            continue
        current_cols = _table_columns(connection, table)
        for column in sorted(columns):
            if column not in current_cols:
                missing.append(f'column:{table}.{column}')
    if missing:
        structured_log('error', 'db.schema_health_failed', missing=missing, total_missing=len(missing))
        raise SchemaMigrationError(
            f'Schema mínimo inconsistente. Itens ausentes: {", ".join(missing[:12])}',
            kind='schema_health_failed',
            context={'missing': missing},
        )
    structured_log('info', 'db.schema_health_ok', tables=len(required_schema))


def _ensure_ficha_periods_sequence_unique(connection) -> None:
    def _normalize_ficha_sequence_row(row, keys=None, *, phase='ficha_sequence_unique_migration', query='', step='row_normalization'):
        key_list = tuple(keys or ())
        context_base = {
            'phase': phase,
            'query': query,
            'step': step,
            'row_type': type(row).__name__ if row is not None else 'NoneType',
            'row_repr': repr(row),
            'expected_keys': list(key_list),
        }
        if row is None:
            raise SchemaMigrationError(
                'row_none',
                kind='schema_health_failed',
                context={**context_base, 'found_keys': []},
            )

        mapping = None
        if isinstance(row, dict):
            mapping = dict(row)
        elif hasattr(row, '_mapping'):
            try:
                mapping = dict(row._mapping)
            except (TypeError, ValueError) as exc:
                raise SchemaMigrationError(
                    'row_mapping_invalid',
                    kind='driver_unexpected',
                    context={**context_base, 'found_keys': []},
                ) from exc
        elif hasattr(row, 'keys'):
            try:
                row_keys = list(row.keys())
                mapping = {key: row[key] for key in row_keys}
            except (KeyError, TypeError, IndexError, AttributeError) as exc:
                raise SchemaMigrationError(
                    'row_keys_access_failed',
                    kind='driver_unexpected',
                    context={**context_base, 'found_keys': []},
                ) from exc

        if mapping is not None:
            if not key_list:
                return dict(mapping)
            normalized = {}
            missing = []
            for key in key_list:
                aliases = (key, 'conname') if key == 'constraint_name' else (key,)
                found = False
                for alias in aliases:
                    if alias in mapping:
                        normalized[key] = mapping[alias]
                        found = True
                        break
                if not found:
                    missing.append(key)
            if missing:
                raise SchemaMigrationError(
                    'row_missing_expected_keys',
                    kind='schema_health_failed',
                    context={**context_base, 'found_keys': sorted(str(k) for k in mapping.keys())},
                )
            return normalized

        if isinstance(row, (tuple, list)):
            row_values = tuple(row)
            if not key_list:
                raise SchemaMigrationError(
                    'missing_keys_for_tuple',
                    kind='schema_health_failed',
                    context={**context_base, 'found_keys': [], 'row_len': len(row_values), 'expected_len': 0},
                )
            if len(row_values) < len(key_list):
                raise SchemaMigrationError(
                    'tuple_len_invalid',
                    kind='schema_health_failed',
                    context={**context_base, 'found_keys': [], 'row_len': len(row_values), 'expected_len': len(key_list)},
                )
            return dict(zip(key_list, row_values))

        raise SchemaMigrationError(
            'unsupported_row_type',
            kind='driver_unexpected',
            context={**context_base, 'found_keys': []},
        )

    try:
        structured_log(
            'info',
            'db.ficha_sequence_safe_row_version',
            supports_step=True,
            normalizer='_normalize_ficha_sequence_row',
            table='epi_ficha_periods',
            phase='ficha_sequence_unique_migration',
        )
        if _is_sqlite_connection(connection):
            table_sql_row = connection.execute(
                "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'epi_ficha_periods'"
            ).fetchone()
            table_sql = str(_normalize_ficha_sequence_row(table_sql_row, keys=('sql',), query='sqlite_master.sql', step='sqlite_load_table_sql').get('sql') or '')
            legacy_unique = 'UNIQUE(employee_id, period_start, period_end)' in table_sql
            has_sequence_unique = 'UNIQUE(employee_id, period_start, period_end, ficha_sequence)' in table_sql
            if not legacy_unique or has_sequence_unique:
                return
            connection.execute('ALTER TABLE epi_ficha_periods RENAME TO epi_ficha_periods_legacy')
            connection.execute(
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
                    batch_signature_name TEXT NOT NULL DEFAULT '',
                    batch_signature_data TEXT NOT NULL DEFAULT '',
                    batch_signature_ip TEXT NOT NULL DEFAULT '',
                    batch_signature_at TEXT NOT NULL DEFAULT '',
                    batch_signature_comment TEXT NOT NULL DEFAULT '',
                    ficha_sequence INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(employee_id, period_start, period_end, ficha_sequence),
                    FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
                    FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE,
                    FOREIGN KEY (unit_id) REFERENCES units(id) ON DELETE RESTRICT
                )
                '''
            )
            connection.execute(
                '''
                INSERT INTO epi_ficha_periods (
                    id, company_id, employee_id, unit_id, schedule_type, period_start, period_end,
                    status, batch_signature_name, batch_signature_data, batch_signature_ip, batch_signature_at,
                    batch_signature_comment, ficha_sequence, created_at, updated_at
                )
                SELECT
                    id, company_id, employee_id, unit_id, schedule_type, period_start, period_end,
                    status, batch_signature_name, batch_signature_data, batch_signature_ip, batch_signature_at,
                    batch_signature_comment, COALESCE(ficha_sequence, 1), created_at, updated_at
                FROM epi_ficha_periods_legacy
                '''
            )
            connection.execute('DROP TABLE epi_ficha_periods_legacy')
            connection.commit()
            return

        # Postgres path (sem sqlite_master/rebuild SQLite)

        # Idempotency check: skip entirely if the unique index already exists.
        # Prevents re-applying an already-completed migration on every cold start.
        _idx_exists = connection.execute(
            """
            SELECT 1 FROM pg_indexes
            WHERE schemaname = current_schema()
              AND tablename = 'epi_ficha_periods'
              AND indexname = 'uq_epi_ficha_periods_employee_window_sequence'
            """
        ).fetchone()
        if _idx_exists:
            return

        # Check current nullability so we only ALTER when actually needed.
        _col_info = connection.execute(
            """
            SELECT
                is_nullable AS ficha_sequence_is_nullable,
                column_default AS ficha_sequence_column_default
            FROM information_schema.columns
            WHERE table_schema = current_schema()
              AND table_name = 'epi_ficha_periods'
              AND column_name = 'ficha_sequence'
            """
        ).fetchone()
        structured_log(
            'info',
            'db.ficha_sequence_metadata_raw',
            raw_type=type(_col_info).__name__,
            raw_repr=repr(_col_info),
            table='epi_ficha_periods',
            phase='ficha_sequence_unique_migration',
        )
        if _col_info is None:
            raise SchemaMigrationError(
                'Metadata da coluna ficha_sequence não encontrada.',
                kind='schema_missing_object',
                context={'table': 'epi_ficha_periods', 'column': 'ficha_sequence', 'phase': 'ficha_sequence_unique_migration'},
            )
        _col_data = _normalize_ficha_sequence_row(
            _col_info,
            keys=('ficha_sequence_is_nullable', 'ficha_sequence_column_default'),
            query='information_schema.columns.ficha_sequence',
            step='load_column_metadata',
        )
        is_nullable = _col_data.get('ficha_sequence_is_nullable')
        column_default = _col_data.get('ficha_sequence_column_default')
        structured_log(
            'info',
            'db.ficha_sequence_metadata_loaded',
            is_nullable=str(is_nullable),
            column_default='' if column_default is None else str(column_default),
            table='epi_ficha_periods',
            phase='ficha_sequence_unique_migration',
        )
        if not column_default or '1' not in str(column_default):
            connection.execute('ALTER TABLE epi_ficha_periods ALTER COLUMN ficha_sequence SET DEFAULT 1')
        connection.execute('UPDATE epi_ficha_periods SET ficha_sequence = 1 WHERE ficha_sequence IS NULL')
        if str(is_nullable).upper() == 'YES':
            connection.execute('ALTER TABLE epi_ficha_periods ALTER COLUMN ficha_sequence SET NOT NULL')

        duplicate_rows = connection.execute(
            '''
            SELECT employee_id, period_start, period_end, ficha_sequence, COUNT(*) AS duplicate_count
            FROM epi_ficha_periods
            GROUP BY employee_id, period_start, period_end, ficha_sequence
            HAVING COUNT(*) > 1
            '''
        ).fetchall()
        structured_log(
            'info',
            'db.ficha_sequence_duplicates_checked',
            duplicate_count=len(duplicate_rows or []),
            table='epi_ficha_periods',
            phase='ficha_sequence_unique_migration',
        )
        if duplicate_rows:
            duplicate_sample = []
            for row in duplicate_rows[:5]:

                _duplicate_data = _normalize_ficha_sequence_row(
                    row,
                    keys=('employee_id', 'period_start', 'period_end', 'ficha_sequence', 'duplicate_count'),
                    query='duplicates_query',
                    step='build_duplicate_sample',
                )
                employee_id = _duplicate_data.get('employee_id')
                period_start = _duplicate_data.get('period_start')
                period_end = _duplicate_data.get('period_end')
                ficha_sequence = _duplicate_data.get('ficha_sequence')
                duplicate_count = _duplicate_data.get('duplicate_count', 0)
                duplicate_sample.append(
                    {
                        'employee_id': employee_id,
                        'period_start': period_start,
                        'period_end': period_end,
                        'ficha_sequence': ficha_sequence,
                        'duplicate_count': int(duplicate_count or 0),
                    }
                )
            structured_log(
                'critical',
                'db.ficha_periods_duplicate_detected',
                count=len(duplicate_rows),
                sample=duplicate_sample,
                table='epi_ficha_periods',
                phase='ficha_sequence_unique_migration',
            )
            raise SchemaMigrationError(
                'Dados duplicados em epi_ficha_periods impedem criação de índice único.',
                kind='duplicate_key_conflict',
                context={'table': 'epi_ficha_periods', 'phase': 'ficha_sequence_unique_migration'},
            )

        structured_log('info', 'db.step_started', step='load_legacy_constraints', table='epi_ficha_periods', phase='ficha_sequence_unique_migration')
        structured_log('info', 'db.ficha_sequence_before_load_legacy_constraints', table='epi_ficha_periods', phase='ficha_sequence_unique_migration')
        try:
            constraints_cursor = connection.execute(
                """
                SELECT c.conname AS constraint_name
                FROM pg_constraint c
                JOIN pg_class t ON t.oid = c.conrelid
                JOIN pg_namespace n ON n.oid = t.relnamespace
                WHERE t.relname = 'epi_ficha_periods'
                  AND n.nspname = current_schema()
                  AND c.contype = 'u'
                  AND pg_get_constraintdef(c.oid) ILIKE ?
                """,
                ('UNIQUE (employee_id, period_start, period_end)%',),
            )
            description = getattr(constraints_cursor, 'description', None)
            if description is None or not isinstance(description, (list, tuple)) or len(description) < 1:
                raise SchemaMigrationError(
                    'Cursor de constraints legadas sem metadata válida.',
                    kind='driver_unexpected',
                    context={
                        'step': 'load_legacy_constraints',
                        'query_name': 'pg_constraint_legacy_unique',
                        'description_repr': repr(description),
                        'description_type': type(description).__name__,
                    },
                )
            structured_log(
                'info',
                'db.ficha_sequence_legacy_constraints_cursor_validated',
                row_count=0,
                table='epi_ficha_periods',
                phase='ficha_sequence_unique_migration',
            )
            old_constraints = constraints_cursor.fetchall()
            if old_constraints is None:
                raise SchemaMigrationError(
                    'fetchall() de constraints legadas retornou None.',
                    kind='driver_unexpected',
                    context={'step': 'load_legacy_constraints', 'query_name': 'pg_constraint_legacy_unique', 'rows_type': 'NoneType'},
                )
            if isinstance(old_constraints, (str, bytes)):
                raise SchemaMigrationError(
                    'fetchall() de constraints legadas retornou tipo inválido.',
                    kind='driver_unexpected',
                    context={'step': 'load_legacy_constraints', 'query_name': 'pg_constraint_legacy_unique', 'rows_type': type(old_constraints).__name__},
                )
            if not isinstance(old_constraints, (list, tuple)):
                try:
                    old_constraints = list(old_constraints)
                except Exception as exc:
                    raise SchemaMigrationError(
                        'Resultado de constraints legadas não é iterável seguro.',
                        kind='driver_unexpected',
                        context={'step': 'load_legacy_constraints', 'query_name': 'pg_constraint_legacy_unique', 'rows_type': type(old_constraints).__name__, 'error': str(exc), 'error_type': type(exc).__name__},
                    ) from exc
            structured_log(
                'info',
                'db.ficha_sequence_legacy_constraints_rows_loaded',
                row_count=len(old_constraints),
                table='epi_ficha_periods',
                phase='ficha_sequence_unique_migration',
            )
        except SchemaMigrationError:
            raise
        except Exception as exc:
            structured_log(
                'critical',
                'db.step_failed',
                step='load_legacy_constraints',
                error=str(exc),
                error_type=type(exc).__name__,
                table='epi_ficha_periods',
                phase='ficha_sequence_unique_migration',
            )
            raise SchemaMigrationError(
                'Falha ao carregar constraints legadas da migração de ficha_sequence.',
                kind='driver_unexpected',
                context={'step': 'load_legacy_constraints', 'query_name': 'pg_constraint_legacy_unique', 'row_type': None, 'row_repr': None, 'error': str(exc), 'error_type': type(exc).__name__},
            ) from exc
        structured_log('info', 'db.ficha_sequence_after_load_legacy_constraints', table='epi_ficha_periods', phase='ficha_sequence_unique_migration', constraint_count=len(old_constraints or []))
        structured_log('info', 'db.step_completed', step='load_legacy_constraints', table='epi_ficha_periods', phase='ficha_sequence_unique_migration')
        structured_log(
            'info',
            'db.ficha_sequence_legacy_constraints_loaded',
            constraint_count=len(old_constraints or []),
            table='epi_ficha_periods',
            phase='ficha_sequence_unique_migration',
        )
        for row in old_constraints:
            try:
                normalized = _normalize_ficha_sequence_row(
                    row,
                    keys=('constraint_name',),
                    query='pg_constraint_legacy_unique',
                    step='load_legacy_constraints',
                )
                constraint_name = normalized['constraint_name']
            except SchemaMigrationError:
                raise
            except Exception as exc:
                raise SchemaMigrationError(
                    'Falha ao normalizar linha de constraint legada.',
                    kind='driver_unexpected',
                    context={
                        'step': 'load_legacy_constraints',
                        'query_name': 'pg_constraint_legacy_unique',
                        'row_type': type(row).__name__,
                        'row_repr': repr(row),
                        'error': str(exc),
                        'error_type': type(exc).__name__,
                    },
                ) from exc
            name = str(constraint_name or '').strip()
            if name:
                structured_log('info', 'db.ficha_sequence_before_drop_legacy_constraint', table='epi_ficha_periods', phase='ficha_sequence_unique_migration', constraint_name=name)
                try:
                    structured_log('info', 'db.step_started', step='drop_legacy_constraint', table='epi_ficha_periods', phase='ficha_sequence_unique_migration', constraint_name=name)
                    connection.execute(f'ALTER TABLE epi_ficha_periods DROP CONSTRAINT IF EXISTS "{name}"')
                    structured_log('info', 'db.step_completed', step='drop_legacy_constraint', table='epi_ficha_periods', phase='ficha_sequence_unique_migration', constraint_name=name)
                except Exception as exc:
                    structured_log(
                        'critical',
                        'db.step_failed',
                        step='drop_legacy_constraint',
                        error=str(exc),
                        error_type=type(exc).__name__,
                        table='epi_ficha_periods',
                        phase='ficha_sequence_unique_migration',
                        constraint_name=name,
                    )
                    raise SchemaMigrationError(
                        'Falha ao remover constraint legada da migração de ficha_sequence.',
                        kind='driver_unexpected',
                        context={'step': 'drop_legacy_constraint', 'query_name': 'alter_table.drop_constraint', 'row_type': type(row).__name__, 'row_repr': repr(row), 'constraint_name': name},
                    ) from exc
                structured_log('info', 'db.ficha_sequence_after_drop_legacy_constraint', table='epi_ficha_periods', phase='ficha_sequence_unique_migration', constraint_name=name)

        structured_log('info', 'db.ficha_sequence_before_create_unique_index', table='epi_ficha_periods', phase='ficha_sequence_unique_migration')
        structured_log('info', 'db.step_started', step='create_unique_index', table='epi_ficha_periods', phase='ficha_sequence_unique_migration')
        try:
            connection.execute(
                'CREATE UNIQUE INDEX IF NOT EXISTS uq_epi_ficha_periods_employee_window_sequence '
                'ON epi_ficha_periods (employee_id, period_start, period_end, ficha_sequence)'
            )
        except SchemaMigrationError:
            raise
        except Exception as exc:
            structured_log(
                'critical',
                'db.step_failed',
                step='create_unique_index',
                error=str(exc),
                error_type=type(exc).__name__,
                table='epi_ficha_periods',
                phase='ficha_sequence_unique_migration',
            )
            raise SchemaMigrationError(
                'Falha ao criar índice único da migração de ficha_sequence.',
                kind='driver_unexpected',
                context={'step': 'create_unique_index', 'query_name': 'create_unique_index', 'row_type': None, 'row_repr': None, 'error': str(exc), 'error_type': type(exc).__name__},
            ) from exc
        structured_log('info', 'db.step_completed', step='create_unique_index', table='epi_ficha_periods', phase='ficha_sequence_unique_migration')
        structured_log('info', 'db.ficha_sequence_after_create_unique_index', table='epi_ficha_periods', phase='ficha_sequence_unique_migration')
        structured_log('info', 'db.ficha_sequence_index_creation_started', table='epi_ficha_periods', phase='ficha_sequence_unique_migration')
        structured_log('info', 'db.step_started', step='create_secondary_index', query_name='create_secondary_index', table='epi_ficha_periods', phase='ficha_sequence_unique_migration')
        try:
            connection.execute(
                'CREATE INDEX IF NOT EXISTS idx_epi_ficha_items_period_sequence '
                'ON epi_ficha_periods (employee_id, period_start, period_end, ficha_sequence DESC)'
            )
        except SchemaMigrationError:
            raise
        except Exception as exc:
            structured_log(
                'critical',
                'db.step_failed',
                step='create_secondary_index',
                query_name='create_secondary_index',
                error=str(exc),
                error_type=type(exc).__name__,
                table='epi_ficha_periods',
                phase='ficha_sequence_unique_migration',
            )
            raise SchemaMigrationError(
                'Falha ao criar índice secundário da migração de ficha_sequence.',
                kind='driver_unexpected',
                context={
                    'step': 'create_secondary_index',
                    'query_name': 'create_secondary_index',
                    'error': str(exc),
                    'error_type': type(exc).__name__,
                    'phase': 'ficha_sequence_unique_migration',
                },
            ) from exc
        structured_log('info', 'db.step_completed', step='create_secondary_index', query_name='create_secondary_index', table='epi_ficha_periods', phase='ficha_sequence_unique_migration')
        structured_log('info', 'db.ficha_sequence_index_created', table='epi_ficha_periods', phase='ficha_sequence_unique_migration')
        connection.commit()
    except Exception as exc:
        if isinstance(exc, SchemaMigrationError):
            raise
        try:
            connection.rollback()
        except Exception:
            pass
        structured_log(
            'critical',
            'db.ficha_periods_unique_migration_failed',
            error=str(exc),
            table='epi_ficha_periods',
            phase='ficha_sequence_unique_migration',
            action='migration_aborted',
        )
        raise SchemaMigrationError(
            f'Falha crítica na migração de unicidade de sequência da ficha: {exc}',
            kind=_classify_db_error(exc),
            context={'table': 'epi_ficha_periods', 'phase': 'ficha_sequence_unique_migration'},
        ) from exc


# ── Funções ensure_* de colunas/tabelas ──────────────────────────────────────

def ensure_user_columns(connection) -> None:
    """Adiciona colunas da tabela users apenas se nao existirem."""
    _safe_add_column(connection, 'users', 'linked_employee_id', 'INTEGER')


def ensure_drop_legacy_token_columns(connection) -> None:
    """Remove colunas legadas de token do portal de users."""
    try:
        connection.execute('ALTER TABLE users DROP COLUMN IF EXISTS employee_access_token')
    except Exception as _e:
        structured_log('warning', 'db.drop_col_skip', column='employee_access_token', error=str(_e))
    try:
        connection.execute('ALTER TABLE users DROP COLUMN IF EXISTS employee_access_expires_at')
    except Exception as _e:
        structured_log('warning', 'db.drop_col_skip', column='employee_access_expires_at', error=str(_e))


def ensure_delivery_signature_columns(connection) -> None:
    """Adiciona colunas de assinatura na tabela deliveries apenas se nao existirem."""
    _safe_add_column(connection, 'deliveries', 'signature_ip', "TEXT NOT NULL DEFAULT ''")
    _safe_add_column(connection, 'deliveries', 'signature_at', "TEXT NOT NULL DEFAULT ''")
    _safe_add_column(connection, 'deliveries', 'signature_data', "TEXT NOT NULL DEFAULT ''")
    _safe_add_column(connection, 'deliveries', 'signature_comment', "TEXT NOT NULL DEFAULT ''")
    _safe_add_column(connection, 'deliveries', 'unit_id', 'INTEGER')
    _safe_add_column(connection, 'deliveries', 'stock_movement_id', 'INTEGER')
    _safe_add_column(connection, 'deliveries', 'glove_size', "TEXT NOT NULL DEFAULT 'N/A'")
    _safe_add_column(connection, 'deliveries', 'size', "TEXT NOT NULL DEFAULT 'N/A'")
    _safe_add_column(connection, 'deliveries', 'uniform_size', "TEXT NOT NULL DEFAULT 'N/A'")


def ensure_devolution_columns(connection) -> None:
    """Garante estrutura de devoluções de EPI e colunas correlatas."""
    _safe_add_column(connection, 'deliveries', 'returned_date', "TEXT NOT NULL DEFAULT ''")
    _safe_add_column(connection, 'deliveries', 'returned_condition', "TEXT NOT NULL DEFAULT ''")
    _safe_add_column(connection, 'deliveries', 'returned_notes', "TEXT NOT NULL DEFAULT ''")
    _safe_add_column(connection, 'deliveries', 'return_movement_id', 'INTEGER')
    connection.execute(
        '''
        CREATE TABLE IF NOT EXISTS epi_devolutions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL,
            unit_id INTEGER NOT NULL,
            employee_id INTEGER NOT NULL,
            epi_id INTEGER NOT NULL,
            delivery_id INTEGER NOT NULL UNIQUE,
            ficha_period_id INTEGER,
            stock_item_id INTEGER,
            stock_movement_id INTEGER,
            returned_date TEXT NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 1,
            condition TEXT NOT NULL,
            destination TEXT NOT NULL,
            notes TEXT NOT NULL DEFAULT '',
            reason TEXT NOT NULL DEFAULT '',
            received_by_user_id INTEGER NOT NULL,
            received_by_name TEXT NOT NULL DEFAULT '',
            signature_name TEXT NOT NULL DEFAULT '',
            signature_data TEXT NOT NULL DEFAULT '',
            signature_ip TEXT NOT NULL DEFAULT '',
            signature_at TEXT NOT NULL DEFAULT '',
            signature_comment TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
            FOREIGN KEY (unit_id) REFERENCES units(id) ON DELETE RESTRICT,
            FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE,
            FOREIGN KEY (epi_id) REFERENCES epis(id) ON DELETE RESTRICT,
            FOREIGN KEY (delivery_id) REFERENCES deliveries(id) ON DELETE CASCADE,
            FOREIGN KEY (ficha_period_id) REFERENCES epi_ficha_periods(id) ON DELETE SET NULL,
            FOREIGN KEY (stock_item_id) REFERENCES epi_stock_items(id) ON DELETE SET NULL,
            FOREIGN KEY (stock_movement_id) REFERENCES stock_movements(id) ON DELETE SET NULL,
            FOREIGN KEY (received_by_user_id) REFERENCES users(id) ON DELETE RESTRICT
        )
        '''
    )
    _safe_add_column(connection, 'epi_devolutions', 'ficha_period_id', 'INTEGER')
    _safe_add_column(connection, 'epi_devolutions', 'stock_item_id', 'INTEGER')
    _safe_add_column(connection, 'epi_devolutions', 'stock_movement_id', 'INTEGER')
    _safe_add_column(connection, 'epi_devolutions', 'signature_name', "TEXT NOT NULL DEFAULT ''")
    _safe_add_column(connection, 'epi_devolutions', 'signature_data', "TEXT NOT NULL DEFAULT ''")
    _safe_add_column(connection, 'epi_devolutions', 'signature_ip', "TEXT NOT NULL DEFAULT ''")
    _safe_add_column(connection, 'epi_devolutions', 'signature_at', "TEXT NOT NULL DEFAULT ''")
    _safe_add_column(connection, 'epi_devolutions', 'signature_comment', "TEXT NOT NULL DEFAULT ''")


def ensure_stock_movement_size_columns(connection) -> None:
    _safe_add_column(connection, 'stock_movements', 'glove_size', "TEXT NOT NULL DEFAULT 'N/A'")
    _safe_add_column(connection, 'stock_movements', 'size', "TEXT NOT NULL DEFAULT 'N/A'")
    _safe_add_column(connection, 'stock_movements', 'uniform_size', "TEXT NOT NULL DEFAULT 'N/A'")


def ensure_stock_columns(connection) -> None:
    _safe_add_column(connection, 'epis', 'minimum_stock', 'INTEGER NOT NULL DEFAULT 10')
    try:
        connection.execute(
            '''
            CREATE TABLE IF NOT EXISTS stock_movements (
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
                created_at TEXT NOT NULL,
                FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
                FOREIGN KEY (unit_id) REFERENCES units(id) ON DELETE RESTRICT,
                FOREIGN KEY (epi_id) REFERENCES epis(id) ON DELETE RESTRICT,
                FOREIGN KEY (actor_user_id) REFERENCES users(id) ON DELETE RESTRICT
            )
            '''
        )
    except Exception as _e:
        structured_log('warning', 'db.col_skip', error=str(_e))
    ensure_stock_movement_size_columns(connection)


def ensure_epi_operational_tables(connection) -> None:
    try:
        connection.execute(
            '''
            CREATE TABLE IF NOT EXISTS epi_qr_sequences (
                company_id INTEGER PRIMARY KEY,
                last_value INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE
            )
            '''
        )
    except Exception as _e:
        structured_log('warning', 'db.col_skip', error=str(_e))
    try:
        connection.execute(
            '''
            CREATE TABLE IF NOT EXISTS unit_epi_stock (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                unit_id INTEGER NOT NULL,
                epi_id INTEGER NOT NULL,
                quantity INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL,
                UNIQUE(company_id, unit_id, epi_id),
                FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
                FOREIGN KEY (unit_id) REFERENCES units(id) ON DELETE RESTRICT,
                FOREIGN KEY (epi_id) REFERENCES epis(id) ON DELETE RESTRICT
            )
            '''
        )
    except Exception as _e:
        structured_log('warning', 'db.col_skip', error=str(_e))
    try:
        connection.execute(
            '''
            CREATE TABLE IF NOT EXISTS epi_stock_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                unit_id INTEGER NOT NULL,
                epi_id INTEGER NOT NULL,
                glove_size TEXT NOT NULL DEFAULT 'N/A',
                size TEXT NOT NULL DEFAULT 'N/A',
                uniform_size TEXT NOT NULL DEFAULT 'N/A',
                qr_sequence INTEGER NOT NULL,
                qr_code_value TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'in_stock',
                stock_movement_id INTEGER,
                delivery_id INTEGER,
                manufacture_date TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(company_id, qr_sequence),
                UNIQUE(company_id, qr_code_value),
                FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
                FOREIGN KEY (unit_id) REFERENCES units(id) ON DELETE RESTRICT,
                FOREIGN KEY (epi_id) REFERENCES epis(id) ON DELETE RESTRICT,
                FOREIGN KEY (stock_movement_id) REFERENCES stock_movements(id) ON DELETE SET NULL,
                FOREIGN KEY (delivery_id) REFERENCES deliveries(id) ON DELETE SET NULL
            )
            '''
        )
    except Exception as _e:
        structured_log('warning', 'db.col_skip', error=str(_e))
    _safe_add_column(connection, 'epi_stock_items', 'glove_size', "TEXT NOT NULL DEFAULT 'N/A'")
    _safe_add_column(connection, 'epi_stock_items', 'size', "TEXT NOT NULL DEFAULT 'N/A'")
    _safe_add_column(connection, 'epi_stock_items', 'uniform_size', "TEXT NOT NULL DEFAULT 'N/A'")
    _safe_add_column(connection, 'epi_stock_items', 'lot_code', "TEXT NOT NULL DEFAULT ''")
    _safe_add_column(connection, 'epi_stock_items', 'manufacture_date', "TEXT NOT NULL DEFAULT ''")
    _safe_add_column(connection, 'epi_stock_items', 'label_measure', "TEXT NOT NULL DEFAULT 'unidade'")
    _safe_add_column(connection, 'epi_stock_items', 'label_printer_name', "TEXT NOT NULL DEFAULT ''")
    _safe_add_column(connection, 'epi_stock_items', 'label_print_format', "TEXT NOT NULL DEFAULT ''")
    _safe_add_column(connection, 'epi_stock_items', 'reprint_count', 'INTEGER NOT NULL DEFAULT 0')
    _safe_add_column(connection, 'epi_stock_items', 'generated_by_user_id', 'INTEGER')
    try:
        connection.execute(
            """
            UPDATE epi_stock_items
            SET manufacture_date = COALESCE(NULLIF(manufacture_date, ''), (
                SELECT COALESCE(epis.manufacture_date, '') FROM epis WHERE epis.id = epi_stock_items.epi_id
            ), '')
            WHERE COALESCE(NULLIF(manufacture_date, ''), '') = ''
            """
        )
    except Exception as _e:
        structured_log('warning', 'db.col_skip', error=str(_e))
    try:
        connection.execute(
            '''
            CREATE TABLE IF NOT EXISTS epi_stock_item_reprints (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                stock_item_id INTEGER NOT NULL,
                company_id INTEGER NOT NULL,
                reason_code TEXT NOT NULL,
                reason_note TEXT NOT NULL DEFAULT '',
                actor_user_id INTEGER NOT NULL,
                actor_name TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                FOREIGN KEY (stock_item_id) REFERENCES epi_stock_items(id) ON DELETE CASCADE,
                FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
                FOREIGN KEY (actor_user_id) REFERENCES users(id) ON DELETE RESTRICT
            )
            '''
        )
    except Exception as _e:
        structured_log('warning', 'db.col_skip', error=str(_e))
    try:
        connection.execute(
            '''
            CREATE TABLE IF NOT EXISTS epi_ficha_periods (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                employee_id INTEGER NOT NULL,
                unit_id INTEGER NOT NULL,
                schedule_type TEXT NOT NULL,
                period_start TEXT NOT NULL,
                period_end TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'open',
                batch_signature_name TEXT NOT NULL DEFAULT '',
                batch_signature_data TEXT NOT NULL DEFAULT '',
                batch_signature_ip TEXT NOT NULL DEFAULT '',
                batch_signature_at TEXT NOT NULL DEFAULT '',
                batch_signature_comment TEXT NOT NULL DEFAULT '',
                ficha_sequence INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(employee_id, period_start, period_end, ficha_sequence),
                FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
                FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE,
                FOREIGN KEY (unit_id) REFERENCES units(id) ON DELETE RESTRICT
            )
            '''
        )
    except Exception as _e:
        structured_log('warning', 'db.col_skip', error=str(_e))
    try:
        connection.execute(
            '''
            CREATE TABLE IF NOT EXISTS epi_ficha_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ficha_period_id INTEGER NOT NULL,
                delivery_id INTEGER NOT NULL UNIQUE,
                company_id INTEGER NOT NULL,
                employee_id INTEGER NOT NULL,
                unit_id INTEGER NOT NULL,
                epi_id INTEGER NOT NULL,
                quantity INTEGER NOT NULL,
                item_signature_name TEXT NOT NULL DEFAULT '',
                item_signature_data TEXT NOT NULL DEFAULT '',
                item_signature_ip TEXT NOT NULL DEFAULT '',
                item_signature_at TEXT NOT NULL DEFAULT '',
                item_signature_comment TEXT NOT NULL DEFAULT '',
                signed_mode TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (ficha_period_id) REFERENCES epi_ficha_periods(id) ON DELETE CASCADE,
                FOREIGN KEY (delivery_id) REFERENCES deliveries(id) ON DELETE CASCADE,
                FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
                FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE,
                FOREIGN KEY (unit_id) REFERENCES units(id) ON DELETE RESTRICT,
                FOREIGN KEY (epi_id) REFERENCES epis(id) ON DELETE RESTRICT
            )
            '''
        )
    except Exception as _e:
        structured_log('warning', 'db.col_skip', error=str(_e))
    _safe_add_column(connection, 'epi_ficha_periods', 'batch_signature_comment', "TEXT NOT NULL DEFAULT ''")
    _safe_add_column(connection, 'epi_ficha_periods', 'ficha_sequence', 'INTEGER NOT NULL DEFAULT 1')
    _ensure_ficha_periods_sequence_unique(connection)
    _safe_add_column(connection, 'epi_ficha_items', 'item_signature_comment', "TEXT NOT NULL DEFAULT ''")
    connection.execute('CREATE INDEX IF NOT EXISTS idx_epi_ficha_items_ficha_period_id ON epi_ficha_items (ficha_period_id)')
    connection.execute('CREATE INDEX IF NOT EXISTS idx_epi_ficha_items_period_sequence ON epi_ficha_periods (employee_id, period_start, period_end, ficha_sequence DESC)')
    try:
        connection.execute(
            '''
            CREATE TABLE IF NOT EXISTS ficha_epi_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ficha_period_id INTEGER NOT NULL UNIQUE,
                company_id INTEGER NOT NULL,
                unit_id INTEGER NOT NULL,
                employee_id INTEGER NOT NULL,
                html_content TEXT NOT NULL,
                html_sha256 TEXT NOT NULL,
                generated_by_user_id INTEGER NOT NULL,
                generated_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                FOREIGN KEY (ficha_period_id) REFERENCES epi_ficha_periods(id) ON DELETE CASCADE,
                FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
                FOREIGN KEY (unit_id) REFERENCES units(id) ON DELETE RESTRICT,
                FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE,
                FOREIGN KEY (generated_by_user_id) REFERENCES users(id) ON DELETE RESTRICT
            )
            '''
        )
        connection.execute('CREATE INDEX IF NOT EXISTS idx_snapshots_employee ON ficha_epi_snapshots (employee_id, generated_at DESC)')
        connection.execute('CREATE INDEX IF NOT EXISTS idx_snapshots_company ON ficha_epi_snapshots (company_id, generated_at DESC)')
        connection.execute('CREATE INDEX IF NOT EXISTS idx_snapshots_expires ON ficha_epi_snapshots (expires_at)')
        _safe_add_column(connection, 'ficha_epi_snapshots', 'snapshot_payload', "TEXT NOT NULL DEFAULT '{}'")
        _safe_add_column(connection, 'ficha_epi_snapshots', 'payload_sha256', "TEXT NOT NULL DEFAULT ''")
        _safe_add_column(connection, 'ficha_epi_snapshots', 'status', "TEXT NOT NULL DEFAULT 'archived'")
        _safe_add_column(connection, 'ficha_epi_snapshots', 'retention_years', "INTEGER NOT NULL DEFAULT 5")
        _safe_add_column(connection, 'ficha_epi_snapshots', 'expired_at', "TEXT NOT NULL DEFAULT ''")
        _safe_add_column(connection, 'ficha_epi_snapshots', 'purged_at', "TEXT NOT NULL DEFAULT ''")
    except Exception as _e:
        structured_log('warning', 'db.col_skip', error=str(_e))
    try:
        connection.execute(
            '''
            CREATE TABLE IF NOT EXISTS ficha_epi_audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                actor_user_id INTEGER NOT NULL,
                actor_name TEXT NOT NULL DEFAULT '',
                actor_role TEXT NOT NULL DEFAULT '',
                employee_id INTEGER NOT NULL,
                employee_name TEXT NOT NULL DEFAULT '',
                unit_id INTEGER NOT NULL,
                company_id INTEGER NOT NULL,
                action TEXT NOT NULL,
                ip_address TEXT NOT NULL DEFAULT '',
                user_agent TEXT NOT NULL DEFAULT '',
                accessed_at TEXT NOT NULL,
                FOREIGN KEY (actor_user_id) REFERENCES users(id) ON DELETE RESTRICT,
                FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE,
                FOREIGN KEY (unit_id) REFERENCES units(id) ON DELETE RESTRICT,
                FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE
            )
            '''
        )
        connection.execute('CREATE INDEX IF NOT EXISTS idx_ficha_audit_actor ON ficha_epi_audit_log (actor_user_id, accessed_at DESC)')
        connection.execute('CREATE INDEX IF NOT EXISTS idx_ficha_audit_employee ON ficha_epi_audit_log (employee_id, accessed_at DESC)')
        connection.execute('CREATE INDEX IF NOT EXISTS idx_ficha_audit_company ON ficha_epi_audit_log (company_id, accessed_at DESC)')
    except Exception as _e:
        structured_log('warning', 'db.col_skip', error=str(_e))
    try:
        connection.execute(
            '''
            CREATE TABLE IF NOT EXISTS employee_portal_links (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                employee_id INTEGER NOT NULL UNIQUE,
                token TEXT NOT NULL UNIQUE,
                qr_code_value TEXT NOT NULL UNIQUE,
                active INTEGER NOT NULL DEFAULT 1,
                expires_at TEXT NOT NULL DEFAULT '',
                created_by_user_id INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
                FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE,
                FOREIGN KEY (created_by_user_id) REFERENCES users(id) ON DELETE RESTRICT
            )
            '''
        )
    except Exception as _e:
        structured_log('warning', 'db.col_skip', error=str(_e))
    _safe_add_column(connection, 'employee_portal_links', 'cpf_attempts', 'INTEGER NOT NULL DEFAULT 0')
    _safe_add_column(connection, 'employee_portal_links', 'last_cpf_attempt_at', "TEXT NOT NULL DEFAULT ''")
    _safe_add_column(connection, 'employee_portal_links', 'blocked_at', "TEXT NOT NULL DEFAULT ''")
    try:
        connection.execute(
            '''
            CREATE TABLE IF NOT EXISTS epi_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                unit_id INTEGER NOT NULL,
                employee_id INTEGER NOT NULL,
                epi_id INTEGER NOT NULL,
                quantity INTEGER NOT NULL DEFAULT 1,
                glove_size TEXT NOT NULL DEFAULT 'N/A',
                size TEXT NOT NULL DEFAULT 'N/A',
                uniform_size TEXT NOT NULL DEFAULT 'N/A',
                request_token TEXT NOT NULL,
                status TEXT NOT NULL,
                justification TEXT NOT NULL DEFAULT '',
                requested_at TEXT NOT NULL,
                requested_by TEXT NOT NULL DEFAULT 'employee',
                approver_user_id INTEGER,
                approver_name TEXT NOT NULL DEFAULT '',
                approved_at TEXT NOT NULL DEFAULT '',
                rejection_reason TEXT NOT NULL DEFAULT '',
                separated_by_user_id INTEGER,
                separated_at TEXT NOT NULL DEFAULT '',
                delivery_id INTEGER,
                last_updated_at TEXT NOT NULL,
                FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
                FOREIGN KEY (unit_id) REFERENCES units(id) ON DELETE RESTRICT,
                FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE,
                FOREIGN KEY (epi_id) REFERENCES epis(id) ON DELETE RESTRICT,
                FOREIGN KEY (approver_user_id) REFERENCES users(id) ON DELETE SET NULL,
                FOREIGN KEY (separated_by_user_id) REFERENCES users(id) ON DELETE SET NULL,
                FOREIGN KEY (delivery_id) REFERENCES deliveries(id) ON DELETE SET NULL
            )
            '''
        )
    except Exception as _e:
        structured_log('warning', 'db.col_skip', error=str(_e))
    _safe_add_column(connection, 'epi_requests', 'glove_size', "TEXT NOT NULL DEFAULT 'N/A'")
    _safe_add_column(connection, 'epi_requests', 'size', "TEXT NOT NULL DEFAULT 'N/A'")
    _safe_add_column(connection, 'epi_requests', 'uniform_size', "TEXT NOT NULL DEFAULT 'N/A'")
    try:
        connection.execute(
            '''
            CREATE TABLE IF NOT EXISTS epi_request_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                request_id INTEGER NOT NULL,
                company_id INTEGER NOT NULL,
                status TEXT NOT NULL,
                notes TEXT NOT NULL DEFAULT '',
                actor_user_id INTEGER,
                actor_name TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                FOREIGN KEY (request_id) REFERENCES epi_requests(id) ON DELETE CASCADE,
                FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
                FOREIGN KEY (actor_user_id) REFERENCES users(id) ON DELETE SET NULL
            )
            '''
        )
    except Exception as _e:
        structured_log('warning', 'db.col_skip', error=str(_e))
    # ── Fase 2 — Módulo de Compras ────────────────────────────────────────
    try:
        connection.execute(
            '''
            CREATE TABLE IF NOT EXISTS purchase_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                unit_id INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'draft',
                title TEXT NOT NULL DEFAULT '',
                notes TEXT NOT NULL DEFAULT '',
                created_by_user_id INTEGER NOT NULL,
                created_by_name TEXT NOT NULL DEFAULT '',
                sent_to_buyer_at TEXT NOT NULL DEFAULT '',
                closed_at TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
                FOREIGN KEY (unit_id) REFERENCES units(id) ON DELETE RESTRICT,
                FOREIGN KEY (created_by_user_id) REFERENCES users(id) ON DELETE RESTRICT
            )
            '''
        )
    except Exception as _e:
        structured_log('warning', 'db.col_skip', error=str(_e))
    try:
        connection.execute(
            '''
            CREATE TABLE IF NOT EXISTS purchase_request_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                purchase_request_id INTEGER NOT NULL,
                company_id INTEGER NOT NULL,
                unit_id INTEGER NOT NULL,
                epi_id INTEGER NOT NULL,
                epi_name TEXT NOT NULL DEFAULT '',
                ca TEXT NOT NULL DEFAULT '',
                unit_measure TEXT NOT NULL DEFAULT '',
                manufacturer TEXT NOT NULL DEFAULT '',
                supplier TEXT NOT NULL DEFAULT '',
                glove_size TEXT NOT NULL DEFAULT 'N/A',
                size TEXT NOT NULL DEFAULT 'N/A',
                uniform_size TEXT NOT NULL DEFAULT 'N/A',
                quantity_requested INTEGER NOT NULL DEFAULT 1,
                quantity_approved INTEGER NOT NULL DEFAULT 0,
                origin TEXT NOT NULL DEFAULT 'stock_minimum',
                employee_id INTEGER,
                employee_name TEXT NOT NULL DEFAULT '',
                employee_sector TEXT NOT NULL DEFAULT '',
                employee_role TEXT NOT NULL DEFAULT '',
                epi_request_id INTEGER,
                status TEXT NOT NULL DEFAULT 'open',
                unit_price REAL NOT NULL DEFAULT 0,
                total_price REAL NOT NULL DEFAULT 0,
                notes TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (purchase_request_id) REFERENCES purchase_requests(id) ON DELETE CASCADE,
                FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
                FOREIGN KEY (unit_id) REFERENCES units(id) ON DELETE RESTRICT,
                FOREIGN KEY (epi_id) REFERENCES epis(id) ON DELETE RESTRICT,
                FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE SET NULL,
                FOREIGN KEY (epi_request_id) REFERENCES epi_requests(id) ON DELETE SET NULL
            )
            '''
        )
    except Exception as _e:
        structured_log('warning', 'db.col_skip', error=str(_e))
    try:
        connection.execute(
            '''
            CREATE TABLE IF NOT EXISTS purchase_orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                purchase_request_id INTEGER,
                company_id INTEGER NOT NULL,
                unit_id INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'draft',
                po_number TEXT NOT NULL DEFAULT '',
                supplier TEXT NOT NULL DEFAULT '',
                supplier_cnpj TEXT NOT NULL DEFAULT '',
                expected_delivery_date TEXT NOT NULL DEFAULT '',
                notes TEXT NOT NULL DEFAULT '',
                total_value REAL NOT NULL DEFAULT 0,
                created_by_user_id INTEGER NOT NULL,
                created_by_name TEXT NOT NULL DEFAULT '',
                approved_by_user_id INTEGER,
                approved_by_name TEXT NOT NULL DEFAULT '',
                approved_at TEXT NOT NULL DEFAULT '',
                approval_comment TEXT NOT NULL DEFAULT '',
                received_by_user_id INTEGER,
                received_by_name TEXT NOT NULL DEFAULT '',
                received_at TEXT NOT NULL DEFAULT '',
                checked_at TEXT NOT NULL DEFAULT '',
                closed_at TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (purchase_request_id) REFERENCES purchase_requests(id) ON DELETE SET NULL,
                FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
                FOREIGN KEY (unit_id) REFERENCES units(id) ON DELETE RESTRICT,
                FOREIGN KEY (created_by_user_id) REFERENCES users(id) ON DELETE RESTRICT,
                FOREIGN KEY (approved_by_user_id) REFERENCES users(id) ON DELETE SET NULL,
                FOREIGN KEY (received_by_user_id) REFERENCES users(id) ON DELETE SET NULL
            )
            '''
        )
    except Exception as _e:
        structured_log('warning', 'db.col_skip', error=str(_e))
    try:
        connection.execute(
            '''
            CREATE TABLE IF NOT EXISTS purchase_order_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                purchase_order_id INTEGER NOT NULL,
                purchase_request_item_id INTEGER,
                company_id INTEGER NOT NULL,
                unit_id INTEGER NOT NULL,
                epi_id INTEGER NOT NULL,
                epi_name TEXT NOT NULL DEFAULT '',
                ca TEXT NOT NULL DEFAULT '',
                unit_measure TEXT NOT NULL DEFAULT '',
                manufacturer TEXT NOT NULL DEFAULT '',
                supplier TEXT NOT NULL DEFAULT '',
                glove_size TEXT NOT NULL DEFAULT 'N/A',
                size TEXT NOT NULL DEFAULT 'N/A',
                uniform_size TEXT NOT NULL DEFAULT 'N/A',
                quantity INTEGER NOT NULL DEFAULT 1,
                quantity_approved INTEGER NOT NULL DEFAULT 0,
                quantity_received INTEGER NOT NULL DEFAULT 0,
                unit_price REAL NOT NULL DEFAULT 0,
                total_price REAL NOT NULL DEFAULT 0,
                origin TEXT NOT NULL DEFAULT 'stock_minimum',
                employee_name TEXT NOT NULL DEFAULT '',
                employee_sector TEXT NOT NULL DEFAULT '',
                employee_role TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'open',
                notes TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (purchase_order_id) REFERENCES purchase_orders(id) ON DELETE CASCADE,
                FOREIGN KEY (purchase_request_item_id) REFERENCES purchase_request_items(id) ON DELETE SET NULL,
                FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
                FOREIGN KEY (unit_id) REFERENCES units(id) ON DELETE RESTRICT,
                FOREIGN KEY (epi_id) REFERENCES epis(id) ON DELETE RESTRICT
            )
            '''
        )
    except Exception as _e:
        structured_log('warning', 'db.col_skip', error=str(_e))
    try:
        connection.execute(
            '''
            CREATE TABLE IF NOT EXISTS purchase_order_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                purchase_order_id INTEGER NOT NULL,
                company_id INTEGER NOT NULL,
                file_name TEXT NOT NULL DEFAULT '',
                file_type TEXT NOT NULL DEFAULT '',
                file_data TEXT NOT NULL DEFAULT '',
                uploaded_by_user_id INTEGER NOT NULL,
                uploaded_by_name TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                FOREIGN KEY (purchase_order_id) REFERENCES purchase_orders(id) ON DELETE CASCADE,
                FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
                FOREIGN KEY (uploaded_by_user_id) REFERENCES users(id) ON DELETE RESTRICT
            )
            '''
        )
    except Exception as _e:
        structured_log('warning', 'db.col_skip', error=str(_e))
    try:
        connection.execute(
            '''
            CREATE TABLE IF NOT EXISTS purchase_approvals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                purchase_order_id INTEGER NOT NULL,
                company_id INTEGER NOT NULL,
                decision TEXT NOT NULL,
                comment TEXT NOT NULL DEFAULT '',
                actor_user_id INTEGER NOT NULL,
                actor_name TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                FOREIGN KEY (purchase_order_id) REFERENCES purchase_orders(id) ON DELETE CASCADE,
                FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
                FOREIGN KEY (actor_user_id) REFERENCES users(id) ON DELETE RESTRICT
            )
            '''
        )
    except Exception as _e:
        structured_log('warning', 'db.col_skip', error=str(_e))
    try:
        connection.execute(
            '''
            CREATE TABLE IF NOT EXISTS purchase_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                entity_type TEXT NOT NULL,
                entity_id INTEGER NOT NULL,
                action TEXT NOT NULL,
                status_from TEXT NOT NULL DEFAULT '',
                status_to TEXT NOT NULL DEFAULT '',
                comment TEXT NOT NULL DEFAULT '',
                actor_user_id INTEGER,
                actor_name TEXT NOT NULL DEFAULT '',
                actor_role TEXT NOT NULL DEFAULT '',
                reason TEXT NOT NULL DEFAULT '',
                destination TEXT NOT NULL DEFAULT '',
                ip_address TEXT NOT NULL DEFAULT '',
                session_ref TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE
            )
            '''
        )
    except Exception as _e:
        structured_log('warning', 'db.col_skip', error=str(_e))
    connection.execute('CREATE INDEX IF NOT EXISTS idx_purchase_requests_company ON purchase_requests (company_id, status)')
    connection.execute('CREATE INDEX IF NOT EXISTS idx_purchase_request_items_request ON purchase_request_items (purchase_request_id)')
    connection.execute('CREATE INDEX IF NOT EXISTS idx_purchase_orders_company ON purchase_orders (company_id, status)')
    connection.execute('CREATE INDEX IF NOT EXISTS idx_purchase_events_entity ON purchase_events (entity_type, entity_id)')
    _safe_add_column(connection, 'purchase_events', 'actor_role', "TEXT NOT NULL DEFAULT ''")
    _safe_add_column(connection, 'purchase_events', 'reason', "TEXT NOT NULL DEFAULT ''")
    _safe_add_column(connection, 'purchase_events', 'destination', "TEXT NOT NULL DEFAULT ''")
    _safe_add_column(connection, 'purchase_orders', 'postponed_until', "TEXT NOT NULL DEFAULT ''")
    _safe_add_column(connection, 'purchase_requests', 'postponed_until', "TEXT NOT NULL DEFAULT ''")
    _safe_add_column(connection, 'epi_requests', 'postponed_until', "TEXT NOT NULL DEFAULT ''")
    _safe_add_column(connection, 'purchase_requests', 'linked_po_number', "TEXT NOT NULL DEFAULT ''")
    _safe_add_column(connection, 'purchase_requests', 'linked_po_id', "INTEGER")
    _safe_add_column(connection, 'purchase_request_items', 'rejection_reason', "TEXT NOT NULL DEFAULT ''")
    _safe_add_column(connection, 'purchase_request_items', 'rejection_comment', "TEXT NOT NULL DEFAULT ''")
    _safe_add_column(connection, 'purchase_request_items', 'approval_decided_by_user_id', "INTEGER")
    _safe_add_column(connection, 'purchase_request_items', 'approval_decided_by_name', "TEXT NOT NULL DEFAULT ''")
    _safe_add_column(connection, 'purchase_request_items', 'approval_decided_at', "TEXT NOT NULL DEFAULT ''")
    # Colunas para revisão operacional do Admin e sugestões ao Comprador
    _safe_add_column(connection, 'purchase_orders', 'admin_review_by_user_id', "INTEGER")
    _safe_add_column(connection, 'purchase_orders', 'admin_review_by_name', "TEXT NOT NULL DEFAULT ''")
    _safe_add_column(connection, 'purchase_orders', 'admin_review_at', "TEXT NOT NULL DEFAULT ''")
    _safe_add_column(connection, 'purchase_orders', 'admin_review_comment', "TEXT NOT NULL DEFAULT ''")
    _safe_add_column(connection, 'purchase_orders', 'buyer_suggestions', "TEXT NOT NULL DEFAULT ''")
    try:
        connection.execute(
            '''
            CREATE TABLE IF NOT EXISTS authorized_suppliers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                cnpj TEXT NOT NULL DEFAULT '',
                category TEXT NOT NULL DEFAULT '',
                contact_email TEXT NOT NULL DEFAULT '',
                notes TEXT NOT NULL DEFAULT '',
                active INTEGER NOT NULL DEFAULT 1,
                source TEXT NOT NULL DEFAULT 'manual',
                created_by_user_id INTEGER,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(company_id, cnpj),
                FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
                FOREIGN KEY (created_by_user_id) REFERENCES users(id) ON DELETE SET NULL
            )
            '''
        )
    except Exception as _e:
        structured_log('warning', 'db.col_skip', error=str(_e))
    connection.execute('CREATE INDEX IF NOT EXISTS idx_authorized_suppliers_company ON authorized_suppliers (company_id, active)')
    try:
        connection.execute(
            '''
            CREATE TABLE IF NOT EXISTS user_unit_links (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                unit_id INTEGER NOT NULL,
                created_by_user_id INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(user_id, unit_id),
                FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (unit_id) REFERENCES units(id) ON DELETE CASCADE
            )
            '''
        )
        connection.execute('CREATE INDEX IF NOT EXISTS idx_user_unit_links_user ON user_unit_links (user_id)')
        connection.execute('CREATE INDEX IF NOT EXISTS idx_user_unit_links_company ON user_unit_links (company_id)')
    except Exception as _e:
        structured_log('warning', 'db.col_skip', error=str(_e))
    try:
        connection.execute(
            '''
            CREATE TABLE IF NOT EXISTS purchase_role_unit_links (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                employee_id INTEGER NOT NULL,
                role_type TEXT NOT NULL,
                unit_id INTEGER NOT NULL,
                created_by_user_id INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(employee_id, role_type, unit_id),
                FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
                FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE,
                FOREIGN KEY (unit_id) REFERENCES units(id) ON DELETE CASCADE,
                FOREIGN KEY (created_by_user_id) REFERENCES users(id) ON DELETE RESTRICT
            )
            '''
        )
        connection.execute('CREATE INDEX IF NOT EXISTS idx_purchase_role_links_employee ON purchase_role_unit_links (employee_id, role_type)')
        connection.execute('CREATE INDEX IF NOT EXISTS idx_purchase_role_links_company ON purchase_role_unit_links (company_id, role_type)')
    except Exception as _e:
        structured_log('warning', 'db.col_skip', error=str(_e))
    # ── Fim Fase 2 ────────────────────────────────────────────────────────
    try:
        connection.execute(
            '''
            CREATE TABLE IF NOT EXISTS epi_feedbacks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                unit_id INTEGER NOT NULL,
                employee_id INTEGER NOT NULL,
                epi_id INTEGER,
                comfort_rating INTEGER NOT NULL DEFAULT 0,
                quality_rating INTEGER NOT NULL DEFAULT 0,
                adequacy_rating INTEGER NOT NULL DEFAULT 0,
                performance_rating INTEGER NOT NULL DEFAULT 0,
                comments TEXT NOT NULL DEFAULT '',
                improvement_suggestion TEXT NOT NULL DEFAULT '',
                suggested_new_epi_name TEXT NOT NULL DEFAULT '',
                suggested_new_epi_notes TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'pendente',
                request_token TEXT NOT NULL DEFAULT '',
                reviewer_user_id INTEGER,
                reviewer_name TEXT NOT NULL DEFAULT '',
                reviewed_at TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
                FOREIGN KEY (unit_id) REFERENCES units(id) ON DELETE RESTRICT,
                FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE,
                FOREIGN KEY (epi_id) REFERENCES epis(id) ON DELETE SET NULL,
                FOREIGN KEY (reviewer_user_id) REFERENCES users(id) ON DELETE SET NULL
            )
            '''
        )
    except Exception as _e:
        structured_log('warning', 'db.col_skip', error=str(_e))
    try:
        connection.execute(
            '''
            CREATE TABLE IF NOT EXISTS epi_feedback_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                feedback_id INTEGER NOT NULL,
                company_id INTEGER NOT NULL,
                status TEXT NOT NULL,
                notes TEXT NOT NULL DEFAULT '',
                actor_user_id INTEGER,
                actor_name TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                FOREIGN KEY (feedback_id) REFERENCES epi_feedbacks(id) ON DELETE CASCADE,
                FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
                FOREIGN KEY (actor_user_id) REFERENCES users(id) ON DELETE SET NULL
            )
            '''
        )
    except Exception as _e:
        structured_log('warning', 'db.col_skip', error=str(_e))
    # Colunas adicionais para fluxo completo de EPI feedback
    _safe_add_column(connection, 'epi_feedbacks', 'type', "TEXT NOT NULL DEFAULT 'avaliacao'")
    _safe_add_column(connection, 'epi_feedbacks', 'category', "TEXT NOT NULL DEFAULT ''")
    _safe_add_column(connection, 'epi_feedbacks', 'description', "TEXT NOT NULL DEFAULT ''")
    _safe_add_column(connection, 'epi_feedbacks', 'priority', "TEXT NOT NULL DEFAULT 'normal'")
    _safe_add_column(connection, 'epi_feedbacks', 'created_by_user_id', "INTEGER")
    _safe_add_column(connection, 'epi_feedbacks', 'assigned_epi_manager_id', "INTEGER")
    _safe_add_column(connection, 'epi_feedbacks', 'hseq_required', "INTEGER NOT NULL DEFAULT 0")
    _safe_add_column(connection, 'epi_feedbacks', 'hseq_user_id', "INTEGER")
    _safe_add_column(connection, 'epi_feedbacks', 'hseq_opinion', "TEXT NOT NULL DEFAULT ''")
    _safe_add_column(connection, 'epi_feedbacks', 'hseq_analyzed_at', "TEXT NOT NULL DEFAULT ''")
    _safe_add_column(connection, 'epi_feedbacks', 'admin_decision', "TEXT NOT NULL DEFAULT ''")
    _safe_add_column(connection, 'epi_feedbacks', 'admin_decision_by_user_id', "INTEGER")
    _safe_add_column(connection, 'epi_feedbacks', 'admin_decision_by_name', "TEXT NOT NULL DEFAULT ''")
    _safe_add_column(connection, 'epi_feedbacks', 'suggested_new_epi_link', "TEXT NOT NULL DEFAULT ''")
    _safe_add_column(connection, 'epi_feedbacks', 'admin_decision_at', "TEXT NOT NULL DEFAULT ''")
    _safe_add_column(connection, 'epi_feedbacks', 'final_justification', "TEXT NOT NULL DEFAULT ''")
    _safe_add_column(connection, 'epi_feedback_history', 'actor_role', "TEXT NOT NULL DEFAULT ''")
    _safe_add_column(connection, 'epi_feedback_history', 'action', "TEXT NOT NULL DEFAULT ''")
    _safe_add_column(connection, 'epi_feedback_history', 'previous_status', "TEXT NOT NULL DEFAULT ''")
    _safe_add_column(connection, 'epi_feedback_history', 'reason', "TEXT NOT NULL DEFAULT ''")
    # Avaliação e Sugestão de EPI — novos campos
    _safe_add_column(connection, 'epi_feedbacks', 'feedback_subtype', "TEXT NOT NULL DEFAULT ''")
    _safe_add_column(connection, 'epi_feedbacks', 'risk_level', "TEXT NOT NULL DEFAULT 'nenhum'")
    _safe_add_column(connection, 'epi_feedbacks', 'rejection_reason', "TEXT NOT NULL DEFAULT ''")
    _safe_add_column(connection, 'epi_feedbacks', 'supplier_eval_requested', "INTEGER NOT NULL DEFAULT 0")
    _safe_add_column(connection, 'epi_feedbacks', 'reassessment_period', "TEXT NOT NULL DEFAULT ''")
    _safe_add_column(connection, 'epi_feedbacks', 'manager_eval_status', "TEXT NOT NULL DEFAULT 'pendente'")
    _safe_add_column(connection, 'epi_feedbacks', 'manager_eval_notes', "TEXT NOT NULL DEFAULT ''")
    _safe_add_column(connection, 'epi_feedbacks', 'manager_eval_at', "TEXT NOT NULL DEFAULT ''")
    _safe_add_column(connection, 'epi_feedbacks', 'employee_portal_status', "TEXT NOT NULL DEFAULT ''")
    _safe_add_column(connection, 'epi_feedbacks', 'employee_portal_message', "TEXT NOT NULL DEFAULT ''")
    _safe_add_column(connection, 'epi_feedbacks', 'epi_rank', "TEXT NOT NULL DEFAULT ''")
    _safe_add_column(connection, 'epi_feedbacks', 'admin_tech_decision', "TEXT NOT NULL DEFAULT ''")
    _safe_add_column(connection, 'epi_feedbacks', 'atende_nr', "TEXT NOT NULL DEFAULT ''")
    _safe_add_column(connection, 'epi_feedbacks', 'reduz_risco', "TEXT NOT NULL DEFAULT ''")
    _safe_add_column(connection, 'epi_feedbacks', 'problemas_observados', "TEXT NOT NULL DEFAULT '[]'")
    _safe_add_column(connection, 'epi_feedbacks', 'custo_estimado', "TEXT NOT NULL DEFAULT ''")
    _safe_add_column(connection, 'epi_feedbacks', 'durabilidade_esperada', "TEXT NOT NULL DEFAULT ''")
    _safe_add_column(connection, 'epi_feedbacks', 'disponibilidade_mercado', "TEXT NOT NULL DEFAULT ''")
    _safe_add_column(connection, 'epi_feedbacks', 'admin_tech_notes', "TEXT NOT NULL DEFAULT ''")
    _safe_add_column(connection, 'epi_feedbacks', 'marca_modelo_sugerido', "TEXT NOT NULL DEFAULT ''")
    _safe_add_column(connection, 'epi_feedbacks', 'admin_tech_eval_at', "TEXT NOT NULL DEFAULT ''")
    for _rc in ('excelente', 'otimo', 'muito_bom', 'ruim', 'muito_ruim', 'pessimo',
                'excelente_sug', 'otima_sug', 'muito_boa_sug', 'pessima_sug', 'muito_ruim_sug', 'ruim_sug'):
        _safe_add_column(connection, 'epi_evaluation_summary', f'rank_{_rc}', 'INTEGER NOT NULL DEFAULT 0')
    try:
        connection.execute(
            '''
            CREATE TABLE IF NOT EXISTS epi_evaluation_summary (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                epi_id INTEGER NOT NULL,
                epi_name TEXT NOT NULL DEFAULT '',
                total_avaliacoes INTEGER NOT NULL DEFAULT 0,
                total_reclamacoes INTEGER NOT NULL DEFAULT 0,
                total_elogios INTEGER NOT NULL DEFAULT 0,
                total_sugestoes INTEGER NOT NULL DEFAULT 0,
                avg_comfort REAL NOT NULL DEFAULT 0,
                avg_quality REAL NOT NULL DEFAULT 0,
                avg_adequacy REAL NOT NULL DEFAULT 0,
                avg_performance REAL NOT NULL DEFAULT 0,
                score REAL NOT NULL DEFAULT 0,
                evaluation_status TEXT NOT NULL DEFAULT 'normal',
                last_computed_at TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
                FOREIGN KEY (epi_id) REFERENCES epis(id) ON DELETE CASCADE,
                UNIQUE (company_id, epi_id)
            )
            '''
        )
    except Exception as _e:
        structured_log('warning', 'db.col_skip', error=str(_e))
    try:
        connection.execute(
            '''
            CREATE TABLE IF NOT EXISTS employee_portal_audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                employee_id INTEGER NOT NULL,
                portal_link_id INTEGER,
                token_hash TEXT NOT NULL,
                action TEXT NOT NULL,
                ip_address TEXT NOT NULL DEFAULT '',
                user_agent TEXT NOT NULL DEFAULT '',
                payload TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
                FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE,
                FOREIGN KEY (portal_link_id) REFERENCES employee_portal_links(id) ON DELETE SET NULL
            )
            '''
        )
    except Exception as _e:
        structured_log('warning', 'db.col_skip', error=str(_e))
    try:
        connection.execute(
            '''
            CREATE TABLE IF NOT EXISTS report_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                unit_id INTEGER,
                requester_user_id INTEGER NOT NULL,
                requester_name TEXT NOT NULL DEFAULT '',
                period_year INTEGER,
                period_month INTEGER,
                notes TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'pending',
                handled_by_user_id INTEGER,
                handled_by_name TEXT NOT NULL DEFAULT '',
                handled_at TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL
            )
            '''
        )
    except Exception as _e:
        structured_log('warning', 'db.col_skip', error=str(_e))


def ensure_company_columns(connection) -> None:
    """Adiciona colunas da tabela companies apenas se nao existirem."""
    migrations = [
        ('legal_name', "TEXT NOT NULL DEFAULT ''"),
        ('plan_name', "TEXT NOT NULL DEFAULT 'Plano padrao'"),
        ('user_limit', 'INTEGER NOT NULL DEFAULT 25'),
        ('license_status', "TEXT NOT NULL DEFAULT 'active'"),
        ('active', 'INTEGER NOT NULL DEFAULT 1'),
        ('commercial_notes', "TEXT NOT NULL DEFAULT ''"),
        ('contract_start', "TEXT NOT NULL DEFAULT ''"),
        ('contract_end', "TEXT NOT NULL DEFAULT ''"),
        ('monthly_value', 'REAL NOT NULL DEFAULT 0'),
        ('addendum_enabled', 'INTEGER NOT NULL DEFAULT 0'),
    ]
    for col, defn in migrations:
        _safe_add_column(connection, 'companies', col, defn)


def ensure_company_audit_columns(connection) -> None:
    """Adiciona colunas de auditoria apenas se nao existirem."""
    _safe_add_column(connection, 'company_audit_logs', 'details_json', "TEXT NOT NULL DEFAULT '[]'")


def ensure_epi_columns(connection) -> None:
    """Adiciona colunas da tabela epis apenas se nao existirem.
    Verifica o catalogo do PostgreSQL antes de qualquer ALTER TABLE,
    eliminando timeouts em producao onde as colunas ja existem.
    """
    _safe_add_column(connection, 'epis', 'unit_id', 'INTEGER')
    _safe_add_column(connection, 'epis', 'qr_code_value', 'TEXT')
    _safe_add_column(connection, 'epis', 'epi_master_sequence', 'INTEGER')
    _safe_add_column(connection, 'epis', 'manufacturer', "TEXT NOT NULL DEFAULT ''")
    _safe_add_column(connection, 'epis', 'supplier_company', "TEXT NOT NULL DEFAULT ''")
    _safe_add_column(connection, 'epis', 'validity_years', 'INTEGER NOT NULL DEFAULT 0')
    _safe_add_column(connection, 'epis', 'validity_months', 'INTEGER NOT NULL DEFAULT 0')
    _safe_add_column(connection, 'epis', 'manufacturer_validity_months', 'INTEGER NOT NULL DEFAULT 0')
    _safe_add_column(connection, 'epis', 'joinventures_json', "TEXT NOT NULL DEFAULT '[]'")
    _safe_add_column(connection, 'epis', 'active_joinventure', 'TEXT')
    _safe_add_column(connection, 'epis', 'model_reference', "TEXT NOT NULL DEFAULT ''")
    _safe_add_column(connection, 'epis', 'manufacturer_recommendations', "TEXT NOT NULL DEFAULT ''")
    _safe_add_column(connection, 'epis', 'epi_photo_data', 'TEXT')
    _safe_add_column(connection, 'epis', 'active', 'INTEGER NOT NULL DEFAULT 1')
    _safe_add_column(connection, 'epis', 'epi_section', "TEXT NOT NULL DEFAULT ''")
    _safe_add_column(connection, 'epis', 'glove_size', 'TEXT')
    _safe_add_column(connection, 'epis', 'size', 'TEXT')
    _safe_add_column(connection, 'epis', 'uniform_size', 'TEXT')
    _safe_add_column(connection, 'epis', 'scope_type', "TEXT NOT NULL DEFAULT 'GLOBAL'")
    _safe_add_column(connection, 'epis', 'is_joint_venture', 'INTEGER NOT NULL DEFAULT 0')
    _safe_add_column(connection, 'epis', 'default_replacement_days', 'INTEGER')
    _safe_add_column(connection, 'epis', 'evaluation_status', "TEXT NOT NULL DEFAULT 'normal'")
    try:
        connection.execute(
            """
            UPDATE epis
            SET
                scope_type = CASE
                    WHEN COALESCE(TRIM(active_joinventure), '') <> '' THEN 'JOINT_VENTURE'
                    WHEN unit_id IS NULL THEN 'GLOBAL'
                    ELSE 'UNIT'
                END,
                is_joint_venture = CASE
                    WHEN COALESCE(TRIM(active_joinventure), '') <> '' THEN 1
                    ELSE 0
                END
            WHERE scope_type = 'GLOBAL' AND unit_id IS NOT NULL
            """
        )
    except Exception as _e:
        structured_log('warning', 'db.ensure_epi_update_skip', error=str(_e))
        try:
            connection.rollback()
        except Exception:
            pass


def ensure_employee_columns(connection) -> None:
    """Adiciona colunas da tabela employees apenas se nao existirem."""
    _safe_add_column(connection, 'employees', 'cpf', "TEXT NOT NULL DEFAULT ''")
    _safe_add_column(connection, 'employees', 'email', "TEXT NOT NULL DEFAULT ''")
    _safe_add_column(connection, 'employees', 'whatsapp', "TEXT NOT NULL DEFAULT ''")
    _safe_add_column(connection, 'employees', 'preferred_contact_channel', "TEXT NOT NULL DEFAULT 'whatsapp'")
    _safe_add_column(connection, 'employees', 'tipo_vinculo', "TEXT NOT NULL DEFAULT 'CLT'")
    _safe_add_column(connection, 'employees', 'empresa_origem', "TEXT NOT NULL DEFAULT ''")


def ensure_rule_engine_shadow_activated(connection) -> None:
    """Ativa execution_mode=shadow para todas as empresas com modo=off.

    Idempotente: empresas já em shadow/canary/enforced não são alteradas.
    Executa na inicialização para garantir que o motor de regras entre em
    shadow mode automaticamente em todos os ambientes.
    """
    import json as _json
    MODES_KEEP = ('shadow', 'canary', 'enforced')
    try:
        rows = connection.execute('SELECT id FROM companies').fetchall()
        for row in rows:
            company_id = int(row['id'] if hasattr(row, 'keys') else row[0])
            scope_key = str(company_id)
            meta_key = f'configuration_framework:{scope_key}'
            meta_row = connection.execute('SELECT value FROM app_meta WHERE key = ?', (meta_key,)).fetchone()
            raw = (meta_row['value'] if hasattr(meta_row, 'keys') else meta_row[0]) if meta_row else None
            framework = {}
            if raw:
                try:
                    framework = _json.loads(raw)
                except Exception:
                    pass
            flags = framework.get('feature_flags', {})
            current_mode = str(flags.get('execution_mode', 'off')).lower()
            if current_mode in MODES_KEEP:
                continue
            if 'feature_flags' not in framework:
                framework['feature_flags'] = {}
            framework['feature_flags']['execution_mode'] = 'shadow'
            framework['feature_flags']['enable_new_rules_engine'] = True
            framework['feature_flags'].setdefault('rollout_percentage', 100)
            connection.execute(
                'INSERT INTO app_meta (key, value) VALUES (?, ?) '
                'ON CONFLICT (key) DO UPDATE SET value = excluded.value',
                (meta_key, _json.dumps(framework, ensure_ascii=False)),
            )
    except Exception as _e:
        structured_log('warning', 'db.rule_engine_shadow_skip', error=str(_e))


def ensure_rule_engine_shadow_log(connection) -> None:
    """Tabela de log de divergências do shadow mode do motor de regras."""
    try:
        connection.execute(
            '''
            CREATE TABLE IF NOT EXISTS rule_engine_shadow_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                role TEXT NOT NULL DEFAULT '',
                endpoint TEXT NOT NULL DEFAULT '',
                dataset TEXT NOT NULL DEFAULT '',
                mode TEXT NOT NULL DEFAULT 'shadow',
                legacy_count INTEGER NOT NULL DEFAULT 0,
                new_count INTEGER NOT NULL DEFAULT 0,
                has_diff INTEGER NOT NULL DEFAULT 0,
                legacy_only TEXT NOT NULL DEFAULT '[]',
                new_only TEXT NOT NULL DEFAULT '[]',
                created_at TEXT NOT NULL
            )
            '''
        )
    except Exception as _e:
        structured_log('warning', 'db.rule_engine_shadow_log_skip', error=str(_e))


def ensure_migrate_legacy_portal_tokens(connection) -> None:
    """Migra tokens legados de users.employee_access_token para employee_portal_links."""
    ph = '?' if _is_sqlite_connection(connection) else '%s'
    now = datetime.now(UTC).isoformat()
    try:
        rows = connection.execute(
            f'''
            SELECT id, company_id, linked_employee_id, employee_access_token, active
            FROM users
            WHERE role = {ph}
              AND employee_access_token IS NOT NULL
              AND employee_access_token != {ph}
              AND linked_employee_id IS NOT NULL
            ''',
            ('employee', '')
        ).fetchall()
    except Exception as _e:
        structured_log('warning', 'db.migrate_legacy_tokens_skip', error=str(_e))
        return
    if not rows:
        return
    conflict_clause = 'OR IGNORE' if _is_sqlite_connection(connection) else ''
    on_conflict = 'ON CONFLICT DO NOTHING' if not _is_sqlite_connection(connection) else ''
    for row in rows:
        user_id, company_id, employee_id, token, active = row[0], row[1], row[2], row[3], row[4]
        try:
            if _is_sqlite_connection(connection):
                connection.execute(
                    'INSERT OR IGNORE INTO employee_portal_links '
                    '(company_id, employee_id, token, qr_code_value, active, expires_at, created_by_user_id, created_at, updated_at) '
                    'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
                    (int(company_id), int(employee_id), str(token), str(token), int(active or 1), '', int(user_id), now, now)
                )
            else:
                connection.execute(
                    'INSERT INTO employee_portal_links '
                    '(company_id, employee_id, token, qr_code_value, active, expires_at, created_by_user_id, created_at, updated_at) '
                    'VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING',
                    (int(company_id), int(employee_id), str(token), str(token), int(active or 1), '', int(user_id), now, now)
                )
        except Exception as _e:
            structured_log('warning', 'db.migrate_legacy_token_row_skip', error=str(_e), user_id=user_id)



def migrate_role_hierarchy(connection):
    connection.execute("UPDATE users SET role = 'master_admin', company_id = NULL WHERE role = 'general_admin' AND company_id IS NULL")
