"""RLS hardening phase 3: tabelas de compras e links. Idempotente."""
from __future__ import annotations

import pathlib

MIGRATION_ID = '004_enable_rls_phase3'
_SQL_FILE = pathlib.Path(__file__).parent.parent.parent / 'supabase' / 'migrations' / '20260501000002_rls_hardening_phase3.sql'


def run(connection) -> dict[str, str]:
    connection.execute(_SQL_FILE.read_text(encoding='utf-8'))
    connection.commit()
    return {'migration_id': MIGRATION_ID, 'status': 'applied'}
