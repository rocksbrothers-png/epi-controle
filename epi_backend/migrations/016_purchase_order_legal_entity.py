"""Migration 016: pedido de compra emitido para um CNPJ específico.

Adiciona ``purchase_orders.legal_entity_id`` (nullable). NULL mantém o
comportamento histórico: pedido da empresa, sem CNPJ específico. Idempotente
via ADD COLUMN IF NOT EXISTS.
"""

from __future__ import annotations

import pathlib

MIGRATION_ID = '016_purchase_order_legal_entity'

_SQL_FILE = pathlib.Path(__file__).parent.parent.parent / 'supabase' / 'migrations' / '20260726000000_purchase_order_legal_entity.sql'


def run(connection) -> dict[str, str]:
    connection.execute(_SQL_FILE.read_text(encoding='utf-8'))
    connection.commit()
    return {'migration_id': MIGRATION_ID, 'status': 'applied'}
