"""Migration 009: covering indexes for unindexed foreign keys.

Cria índices nas colunas de foreign key que não possuíam índice de cobertura
(advisor de performance do Supabase: unindexed_foreign_keys). Idempotente via
`CREATE INDEX IF NOT EXISTS`. Beneficia JOINs multi-tenant (company_id, unit_id,
employee_id), buscas por FK e deleções em cascata.
"""

from __future__ import annotations

import pathlib

MIGRATION_ID = '009_index_unindexed_fks'

_SQL_FILE = (
    pathlib.Path(__file__).parent.parent.parent
    / 'supabase' / 'migrations' / '20260619000000_index_unindexed_fks.sql'
)


def run(connection) -> dict[str, str | int]:
    raw = _SQL_FILE.read_text(encoding='utf-8')
    # Remove comment lines first so they don't glue onto the first statement.
    code = '\n'.join(line for line in raw.splitlines() if not line.lstrip().startswith('--'))
    statements = [s.strip() for s in code.split(';') if s.strip()]
    applied = 0
    for statement in statements:
        connection.execute(statement)
        applied += 1
    connection.commit()
    return {'migration_id': MIGRATION_ID, 'status': 'applied', 'indexes': applied}
