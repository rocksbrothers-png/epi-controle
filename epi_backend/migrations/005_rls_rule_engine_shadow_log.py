"""RLS na tabela rule_engine_shadow_log. Idempotente."""
from __future__ import annotations

import pathlib

MIGRATION_ID = '005_rls_rule_engine_shadow_log'
_SQL_FILE = pathlib.Path(__file__).parent.parent.parent / 'supabase' / 'migrations' / '20260601000000_rls_rule_engine_shadow_log.sql'


def run(connection) -> dict[str, str]:
    connection.execute(_SQL_FILE.read_text(encoding='utf-8'))
    connection.commit()
    return {'migration_id': MIGRATION_ID, 'status': 'applied'}
