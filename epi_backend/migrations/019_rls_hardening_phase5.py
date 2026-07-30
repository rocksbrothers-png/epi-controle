"""Migration 019: RLS hardening phase 5. Idempotente.

Supabase Security Advisor sinalizou 17 tabelas criadas após a fase 4 (Multi-
CNPJ/ADR-0001, Cadastro Simplificado de Terceirizados/ADR-0002, módulo PPE
Test, estoque F0) sem a policy `block_direct_api_access` — algumas com RLS já
habilitado e sem policy (INFO), outras com RLS nunca habilitado (ERROR/
CRITICAL, projeto corporativo). O mesmo `ALTER ... ENABLE ROW LEVEL SECURITY`
idempotente cobre os dois casos; mesmo padrão das fases 002-004/010/011.
"""
from __future__ import annotations

import pathlib

MIGRATION_ID = '019_rls_hardening_phase5'
_SQL_FILE = pathlib.Path(__file__).parent.parent.parent / 'supabase' / 'migrations' / '20260730000000_rls_hardening_phase5.sql'


def run(connection) -> dict[str, str]:
    connection.execute(_SQL_FILE.read_text(encoding='utf-8'))
    connection.commit()
    return {'migration_id': MIGRATION_ID, 'status': 'applied'}
