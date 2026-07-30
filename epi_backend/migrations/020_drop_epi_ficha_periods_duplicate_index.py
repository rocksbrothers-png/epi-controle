"""Migration 020: drop do índice UNIQUE duplicado em epi_ficha_periods.

Supabase Performance Advisor sinalizou dois índices idênticos cobrindo
(employee_id, period_start, period_end, ficha_sequence): o legado, com nome
auto-gerado pelo Postgres, e uq_epi_ficha_periods_employee_window_sequence,
o atual. `core.schema._ensure_ficha_periods_sequence_unique` tem uma guarda
de idempotência que retorna assim que o índice atual existe, então nunca
limpou a legada em bancos onde ela sobreviveu. Idempotente.
"""
from __future__ import annotations

import pathlib

MIGRATION_ID = '020_drop_epi_ficha_periods_duplicate_index'
_SQL_FILE = pathlib.Path(__file__).parent.parent.parent / 'supabase' / 'migrations' / '20260730000001_drop_epi_ficha_periods_duplicate_index.sql'


def run(connection) -> dict[str, str]:
    connection.execute(_SQL_FILE.read_text(encoding='utf-8'))
    connection.commit()
    return {'migration_id': MIGRATION_ID, 'status': 'applied'}
