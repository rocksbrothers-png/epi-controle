"""Destinação física pela unidade: inclui doação terminal e evento imutável."""
from pathlib import Path

MIGRATION_ID = '033_stock_unit_disposition'
SQL_FILE = Path(__file__).resolve().parents[2] / 'supabase/migrations/20261022175115_stock_unit_disposition.sql'


def run(connection):
    connection.execute(SQL_FILE.read_text(encoding='utf-8'))
    connection.commit()
    return {'migration_id': MIGRATION_ID, 'status': 'applied'}
