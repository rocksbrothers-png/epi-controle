"""Phase 26: safety-net drop de epi_ficha_periods_legacy. Idempotente."""
from __future__ import annotations

import pathlib

MIGRATION_ID = '007_drop_epi_ficha_periods_legacy'
_SQL_FILE = pathlib.Path(__file__).parent.parent.parent / 'supabase' / 'migrations' / '20260601000002_drop_epi_ficha_periods_legacy.sql'


def run(connection) -> dict[str, str]:
    connection.execute(_SQL_FILE.read_text(encoding='utf-8'))
    connection.commit()
    return {'migration_id': MIGRATION_ID, 'status': 'applied'}
