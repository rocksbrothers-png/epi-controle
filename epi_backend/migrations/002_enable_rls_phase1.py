"""RLS hardening phase 1: users + employee_portal_links. Idempotente."""
from __future__ import annotations

import pathlib

MIGRATION_ID = '002_enable_rls_phase1'
_SQL_FILE = pathlib.Path(__file__).parent.parent.parent / 'supabase' / 'migrations' / '20260501000000_rls_hardening_phase1.sql'


def run(connection) -> dict[str, str]:
    connection.execute(_SQL_FILE.read_text(encoding='utf-8'))
    connection.commit()
    return {'migration_id': MIGRATION_ID, 'status': 'applied'}
