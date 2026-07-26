"""Migration 017: escopo de CNPJ por usuário + CNPJ na auditoria.

Cria ``user_legal_entities`` (autorização de CNPJ para o Administrador Local) e
adiciona ``company_audit_logs.legal_entity_id``. Idempotente.
"""

from __future__ import annotations

import pathlib

MIGRATION_ID = '017_user_legal_entities_and_audit'

_SQL_FILE = pathlib.Path(__file__).parent.parent.parent / 'supabase' / 'migrations' / '20260727000000_user_legal_entities_and_audit.sql'


def run(connection) -> dict[str, str]:
    connection.execute(_SQL_FILE.read_text(encoding='utf-8'))
    connection.commit()
    return {'migration_id': MIGRATION_ID, 'status': 'applied'}
