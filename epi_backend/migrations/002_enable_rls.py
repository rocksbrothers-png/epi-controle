"""RLS hardening: habilita Row Level Security e bloqueia anon/authenticated.

Idempotente. Role postgres (superusuário) bypassa RLS — backend não é afetado.
"""
from __future__ import annotations
import pathlib

MIGRATION_ID = '002_enable_rls'

_SQL_FILE = pathlib.Path(__file__).parent.parent.parent / 'supabase' / 'migrations' / '20260430000001_rls_hardening.sql'


def run(connection) -> dict[str, str]:
    sql = _SQL_FILE.read_text(encoding='utf-8')
    connection.execute(sql)
    connection.commit()
    return {'migration_id': MIGRATION_ID, 'status': 'applied'}
