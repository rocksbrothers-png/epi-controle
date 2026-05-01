"""RLS hardening consolidado: 29 tabelas. Idempotente. Backend nao afetado."""
from __future__ import annotations
import pathlib

MIGRATION_ID = '002_enable_rls_all'
_SQL_FILE = pathlib.Path(__file__).parent.parent.parent / 'supabase' / 'migrations' / '20260501120000_rls_hardening_all.sql'

def run(connection) -> dict[str, str]:
    connection.execute(_SQL_FILE.read_text(encoding='utf-8'))
    connection.commit()
    return {'migration_id': MIGRATION_ID, 'status': 'applied'}
