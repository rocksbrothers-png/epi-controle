"""Migration 020: RLS hardening phase 6. Idempotente.

Fecha as seis tabelas que um banco criado do zero deixava sem RLS.

Três são do Centro de Migração (ADR-0003) — `migration_jobs`,
`migration_job_records` e `migration_field_mappings`. Nasceram em
`core/schema.py` depois da fase 5 e nunca entraram numa fase de hardening; o
Supabase Security Advisor as reporta como ERROR no projeto corporativo.
`migration_job_records` guarda o payload importado, com dados pessoais.

As outras três — `epi_evaluation_summary`, `purchase_pendencies` e
`report_requests` — já estão protegidas nos dois projetos de produção, mas
não em banco novo: as fases que as cobriam rodaram antes de a tabela existir
e o `CONTINUE WHEN NOT EXISTS` as pulou em silêncio. Reaplicar é inofensivo
onde já está feito e necessário em ambiente novo.

Mesmo padrão das fases 002-004/005/010/011/019.
"""
from __future__ import annotations

import pathlib

MIGRATION_ID = '020_rls_hardening_phase6'
_SQL_FILE = pathlib.Path(__file__).parent.parent.parent / 'supabase' / 'migrations' / '20260811000000_rls_hardening_phase6.sql'


def run(connection) -> dict[str, str]:
    connection.execute(_SQL_FILE.read_text(encoding='utf-8'))
    connection.commit()
    return {'migration_id': MIGRATION_ID, 'status': 'applied'}
