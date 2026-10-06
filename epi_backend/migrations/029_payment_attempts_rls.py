"""Migration 029: payment_attempts — idempotência do checkout (versionada).

Versiona o índice UNIQUE(company_id, idempotency_key) e a RLS RESTRICTIVE da
tabela `payment_attempts` (criada em bootstrap por
`core/checkout_idempotency.ensure_payment_attempt_tables`). Contexto completo e
raciocínio no cabeçalho do `.sql`. Mesmo molde de 028 (bloco único `DO $$`,
idempotente, no-op se a tabela ainda não existe no boot).
"""

from __future__ import annotations

import pathlib

MIGRATION_ID = '029_payment_attempts_rls'

_SQL_FILE = (
    pathlib.Path(__file__).parent.parent.parent
    / 'supabase' / 'migrations' / '20260829000000_payment_attempts_rls.sql'
)


def run(connection) -> dict[str, str]:
    connection.execute(_SQL_FILE.read_text(encoding='utf-8'))
    connection.commit()
    return {'migration_id': MIGRATION_ID, 'status': 'applied'}
