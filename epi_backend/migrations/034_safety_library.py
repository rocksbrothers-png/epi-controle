"""PORTAL-DOCS-V1: private originals, immutable versions and authorized previews."""
from pathlib import Path

MIGRATION_ID = '034_safety_library'
SQL_FILE = Path(__file__).resolve().parents[2] / 'supabase/migrations/20261013000100_safety_library.sql'


def run(connection):
    connection.execute(SQL_FILE.read_text(encoding='utf-8'))
    connection.commit()
    return {'migration_id': MIGRATION_ID, 'status': 'applied'}
