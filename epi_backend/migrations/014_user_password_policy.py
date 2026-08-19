"""Migration 014: política de senha temporária (troca obrigatória + expiração).

Adiciona à tabela users:
  • must_change_password (INTEGER, default 0) — força a troca no 1º acesso.
  • password_expires_at (TEXT, default '') — expiração da senha temporária.

Idempotente via ADD COLUMN IF NOT EXISTS. Não afeta usuários existentes
(default 0 / '' mantém quem já usa o sistema fora da exigência).
"""

from __future__ import annotations

import pathlib

MIGRATION_ID = '014_user_password_policy'

_SQL_FILE = (
    pathlib.Path(__file__).parent.parent.parent
    / 'supabase' / 'migrations' / '20260715000000_user_password_policy.sql'
)


def run(connection) -> dict[str, str]:
    connection.execute(_SQL_FILE.read_text(encoding='utf-8'))
    connection.commit()
    return {'migration_id': MIGRATION_ID, 'status': 'applied'}
