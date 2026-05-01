"""RLS hardening Fase 2: 27 tabelas restantes. Idempotente. Backend nao afetado."""
from __future__ import annotations
import pathlib

MIGRATION_ID = '003_enable_rls_phase2'
_SQL_FILE = pathlib.Path(__file__).parent.parent.parent / 'supabase' / 'migrations' / '20260501000001_rls_hardening_phase2.sql'

def run(connection) -> dict[str, str]:
    connection.execute(_SQL_FILE.read_text(encoding='utf-8'))
    connection.commit()
    return {'migration_id': MIGRATION_ID, 'status': 'applied'}
