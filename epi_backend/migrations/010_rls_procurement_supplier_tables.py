"""Migration 010: RLS nas tabelas F0 do módulo de Compras. Idempotente.

As tabelas são criadas antes pelo bootstrap (ensure_procurement_supplier_tables);
esta migration apenas habilita RLS + policy block_direct_api_access, no mesmo
padrão das fases de RLS hardening (002-004 e purchase_pendencies).
"""
from __future__ import annotations

import pathlib

MIGRATION_ID = '010_rls_procurement_supplier_tables'
_SQL_FILE = pathlib.Path(__file__).parent.parent.parent / 'supabase' / 'migrations' / '20260708000000_rls_procurement_supplier_tables.sql'


def run(connection) -> dict[str, str]:
    connection.execute(_SQL_FILE.read_text(encoding='utf-8'))
    connection.commit()
    return {'migration_id': MIGRATION_ID, 'status': 'applied'}
