"""Fail-closed evidence and preflight for migration rollback; no new schema.

PostgreSQL is authoritative. Lock the job before targets, and distinct targets
in ascending id order. All checks precede mutations. SQLite supports functional
fixtures only; its state snapshots do not establish concurrency guarantees.
"""
from __future__ import annotations

import json

from epi_backend import db


class RollbackConflict(ValueError):
    def __init__(self, reason: str, *, row: int = 0, target_id=None):
        super().__init__(f'Reversão recusada: {reason}. Nenhum registro foi revertido.')
        self.reason = reason
        self.row = row
        self.target_id = target_id


def lock_suffix(connection) -> str:
    if db._is_sqlite_connection(connection):
        return ''
    isolation = connection.execute('SHOW transaction_isolation').fetchone()
    if next(iter(db.row_to_dict(isolation).values())) != 'read committed':
        raise ValueError('A operação de migração exige isolamento READ COMMITTED.')
    return ' FOR UPDATE'


def read_row(connection, table: str, company_id: int, target_id: int, *, lock=False):
    """Complete persisted state plus PostgreSQL tuple identity (detects ABA)."""
    suffix = lock_suffix(connection) if lock else ''
    version_columns = '' if db._is_sqlite_connection(connection) else (
        ', t.xmin::text AS __migration_xmin, t.ctid::text AS __migration_ctid'
    )
    row = connection.execute(
        f'SELECT t.*{version_columns} FROM {table} t '  # noqa: S608 - table from EntityDescriptor only
        f'WHERE t.id = %s AND t.company_id = %s{suffix}',
        (int(target_id), int(company_id)),
    ).fetchone()
    if row is None:
        return None
    values = db.row_to_dict(row)
    version = {}
    if version_columns:
        version = {'xmin': values.pop('__migration_xmin'), 'ctid': values.pop('__migration_ctid')}
    # Match the JSON representation stored in existing migration audit columns.
    return {'row': json.loads(json.dumps(values, default=str)), 'version': version}


def evidence(payload: dict, after: dict, before=None) -> dict:
    if after is None:
        raise ValueError('Registro importado não encontrado para conciliação.')
    return {**payload, '__rollback_v1__': {**after, 'before_row': before['row'] if before else None}}


def _decode(value, record, label):
    try:
        data = json.loads(value or '{}')
    except (TypeError, ValueError) as exc:
        raise RollbackConflict(f'{label} inválido', row=record['row_number'],
                               target_id=record['target_id']) from exc
    if not isinstance(data, dict):
        raise RollbackConflict(f'{label} inválido', row=record['row_number'],
                               target_id=record['target_id'])
    return data


def _identifier(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def _has_dependents(connection, references, state: dict) -> bool:
    for ref in references:
        sources, targets = ref['source_columns'], ref['target_columns']
        if not sources or len(sources) != len(targets) or any(name not in state for name in targets):
            raise RollbackConflict('metadados de dependência incompatíveis')
        values = [state[name] for name in targets]
        if any(value is None for value in values):
            continue  # NULL foreign keys do not reference a parent.
        table = _identifier(ref['table'])
        if ref['schema']:
            table = _identifier(ref['schema']) + '.' + table
        clauses = ' AND '.join(f'{_identifier(name)} = %s' for name in sources)
        # Identifiers are quoted database catalogue metadata, not imported input.
        if connection.execute(f'SELECT 1 FROM {table} WHERE {clauses} LIMIT 1', tuple(values)).fetchone():  # noqa: S608
            return True
    return False


def preflight(connection, descriptor, company_id: int, records: list[dict]) -> list[dict]:
    """Return inverse operations after proving entire rollback safe under locks."""
    affected = []
    for record in records:
        if record['action'] in ('skip', 'error', 'rollback_conflict'):
            continue
        if (record['action'] not in ('insert', 'update') or not record['target_id']
                or record['target_table'] != descriptor.target_table):
            raise RollbackConflict('identidade ou ação de auditoria inválida')
        affected.append(record)
    states = {}
    for target_id in sorted({int(r['target_id']) for r in affected}):
        current = read_row(connection, descriptor.target_table, company_id, target_id, lock=True)
        if current is None:
            raise RollbackConflict('registro ausente ou fora da empresa', target_id=target_id)
        states[target_id] = current
    # Locked parents prevent concurrent FK insertions from passing KEY SHARE.
    # Metadata/read failures propagate, aborting the operation rather than allowing deletion.
    references = db.migration_incoming_foreign_keys(connection, descriptor.target_table)
    security = None
    if not db._is_sqlite_connection(connection):
        security = next(iter(db.row_to_dict(connection.execute('SHOW row_security').fetchone()).values()))
        # OFF does not bypass RLS: PostgreSQL refuses a query whose rows would
        # be hidden. A filtered reference query must never authorize CASCADE.
        connection.execute('SET LOCAL row_security = off')
    for target_id, current in states.items():
        if _has_dependents(connection, references, current['row']):
            raise RollbackConflict('registro possui dependências posteriores', target_id=target_id)
    if security is not None:
        connection.execute("SELECT set_config('row_security', %s, true)", (security,))
    seen = set()
    plan = []
    allowed = (set(descriptor.field_names()) | set(descriptor.derived_columns)
               | set(descriptor.computed_columns) | set(getattr(descriptor, 'service_columns', ())))
    for record in affected:  # audit order is descending; simulate earlier states in memory.
        target_id = int(record['target_id'])
        after = _decode(record['after_json'], record, 'snapshot posterior')
        proof = after.get('__rollback_v1__')
        current = states[target_id]
        if (not isinstance(proof, dict) or not isinstance(proof.get('row'), dict)
                or not isinstance(proof.get('version'), dict) or 'before_row' not in proof):
            raise RollbackConflict('job legado ou sem snapshot completo verificável',
                                   row=record['row_number'], target_id=target_id)
        if (current is None or proof['row'] != current['row']
                or proof['row'].get('id') != target_id
                or proof['row'].get('company_id') != int(company_id)
                or (target_id not in seen and proof['version'] != current['version'])):
            raise RollbackConflict('registro foi alterado após a importação',
                                   row=record['row_number'], target_id=target_id)
        seen.add(target_id)
        before = None
        if record['action'] == 'update':
            before = _decode(record['before_json'], record, 'snapshot anterior')
            full_before = proof['before_row']
            if (not before or not isinstance(full_before, dict)
                    or set(full_before) != set(current['row'])
                    or full_before.get('id') != target_id
                    or full_before.get('company_id') != int(company_id)
                    or not set(before).issubset(allowed)
                    or any(full_before.get(name) != value for name, value in before.items())):
                raise RollbackConflict('snapshot anterior incompatível',
                                       row=record['row_number'], target_id=target_id)
            states[target_id] = {'row': full_before, 'version': {}}
        else:
            if proof['before_row'] is not None:
                raise RollbackConflict('snapshot de inserção incompatível', target_id=target_id)
            states[target_id] = None
        plan.append({**record, 'before': before, 'expected_before': proof['before_row'],
                     'expected_after': proof['row']})
    return plan
