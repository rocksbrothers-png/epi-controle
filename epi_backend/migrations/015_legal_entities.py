"""Migration 015: Arquitetura Multi-CNPJ / Joint Venture (LegalEntity).

Cria a tabela ``legal_entities`` e as colunas de vínculo/config associadas
(companies.org_structure_type, companies.stock_control_scope,
employees.legal_entity_id, units.legal_entity_id), com backfill idempotente da
matriz padrão de cada empresa. Toda a DDL é idempotente (IF NOT EXISTS / NOT
EXISTS), então reexecutar é seguro mesmo após ``ensure_legal_entities`` já ter
provisionado o schema no bootstrap.
"""

from __future__ import annotations

import pathlib

MIGRATION_ID = '015_legal_entities'

_SQL_FILE = pathlib.Path(__file__).parent.parent.parent / 'supabase' / 'migrations' / '20260725000000_legal_entities.sql'


def run(connection) -> dict[str, str]:
    connection.execute(_SQL_FILE.read_text(encoding='utf-8'))
    connection.commit()
    return {'migration_id': MIGRATION_ID, 'status': 'applied'}
