"""EST-V3.5-F (G02): validade do fabricante do lote no item da PO.

Adiciona ``purchase_order_items.manufacturer_validity_date`` em PostgreSQL de
forma numerada, versionada e auditável (registrada em ``app_migrations``), no
lugar de uma escrita por catálogo. Em SQLite a coluna vem de
``ensure_epi_operational_tables`` (migrations numeradas são puladas no SQLite),
de modo que cada engine tem uma única fonte — sem duplicidade de aplicação.
Idempotente: o SQL usa ``ADD COLUMN IF NOT EXISTS``.
"""

from pathlib import Path

MIGRATION_ID = '032_po_item_manufacturer_validity'
SQL_FILE = (
    Path(__file__).resolve().parents[2]
    / 'supabase/migrations/20261012000200_po_item_manufacturer_validity.sql'
)


def run(connection):
    connection.execute(SQL_FILE.read_text(encoding='utf-8'))
    connection.commit()
    return {'migration_id': MIGRATION_ID, 'status': 'applied'}
