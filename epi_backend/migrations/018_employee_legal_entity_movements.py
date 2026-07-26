"""Migration 018: histórico de vínculo jurídico do colaborador.

Cria ``employee_legal_entity_movements``, que registra toda mudança de CNPJ do
colaborador feita pelo processo administrativo auditado. Idempotente.
"""

from __future__ import annotations

import pathlib

MIGRATION_ID = '018_employee_legal_entity_movements'

_SQL_FILE = pathlib.Path(__file__).parent.parent.parent / 'supabase' / 'migrations' / '20260728000000_employee_legal_entity_movements.sql'


def run(connection) -> dict[str, str]:
    connection.execute(_SQL_FILE.read_text(encoding='utf-8'))
    connection.commit()
    return {'migration_id': MIGRATION_ID, 'status': 'applied'}
