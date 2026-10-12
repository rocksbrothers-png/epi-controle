"""EST-V2: lote físico, proveniência, decisões e histórico preservado.

Aditiva: não infere vencimento/custo a partir do catálogo, não reconcilia
saldos nem ativa os comandos operacionais das fases EST-V3–V6.
"""

from pathlib import Path

MIGRATION_ID = '030_stock_lifecycle_model'
SQL_FILE = Path(__file__).resolve().parents[2] / 'supabase/migrations/20261012000000_stock_lifecycle_model.sql'


def run(connection):
    connection.execute(SQL_FILE.read_text(encoding='utf-8'))
    connection.commit()
    return {'migration_id': MIGRATION_ID, 'status': 'applied'}
