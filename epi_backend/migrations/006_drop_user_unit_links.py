"""Phase 26: drop user_unit_links (substituída por purchase_role_unit_links). Idempotente."""
from __future__ import annotations

import pathlib

MIGRATION_ID = '006_drop_user_unit_links'
_SQL_FILE = pathlib.Path(__file__).parent.parent.parent / 'supabase' / 'migrations' / '20260601000001_drop_user_unit_links.sql'


def run(connection) -> dict[str, str]:
    connection.execute(_SQL_FILE.read_text(encoding='utf-8'))
    connection.commit()
    return {'migration_id': MIGRATION_ID, 'status': 'applied'}
