"""Migration 011: RLS na tabela purchase_quote_files (Fase F2). Idempotente."""
from __future__ import annotations

import pathlib

MIGRATION_ID = '011_rls_purchase_quote_files'
_SQL_FILE = pathlib.Path(__file__).parent.parent.parent / 'supabase' / 'migrations' / '20260709000000_rls_purchase_quote_files.sql'


def run(connection) -> dict[str, str]:
    connection.execute(_SQL_FILE.read_text(encoding='utf-8'))
    connection.commit()
    return {'migration_id': MIGRATION_ID, 'status': 'applied'}
