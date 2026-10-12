"""EST-V2: valida a empresa do responsável pelo bloqueio da peça."""

from pathlib import Path

MIGRATION_ID = '031_stock_item_actor_scope'
SQL_FILE = Path(__file__).resolve().parents[2] / 'supabase/migrations/20261012000100_stock_item_actor_scope.sql'


def run(connection):
    connection.execute(SQL_FILE.read_text(encoding='utf-8'))
    connection.commit()
    return {'migration_id': MIGRATION_ID, 'status': 'applied'}
