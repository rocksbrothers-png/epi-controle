"""Migration 021: cadastro corporativo compartilhado por tenant + trava
pós-promoção de Empresa Terceirizada/Prestadora (ADR-0002 §11).

Cria ``outsourced_company_unit_links`` (vínculo operacional por Unidade,
independente do arquivamento corporativo) e ``outsourced_company_update_
requests`` ("Solicitar atualização cadastral"), com backfill idempotente do
vínculo inicial para empresas já cadastradas com Unidade de origem. Toda a
DDL é idempotente (IF NOT EXISTS / NOT EXISTS), então reexecutar é seguro
mesmo após ``ensure_outsourced_company_unit_links``/``ensure_outsourced_
company_update_requests`` já terem provisionado o schema no bootstrap.
"""

from __future__ import annotations

import pathlib

MIGRATION_ID = '021_outsourced_company_unit_links'

_SQL_FILE = (
    pathlib.Path(__file__).parent.parent.parent
    / 'supabase' / 'migrations' / '20260806000000_outsourced_company_unit_links.sql'
)


def run(connection) -> dict[str, str]:
    connection.execute(_SQL_FILE.read_text(encoding='utf-8'))
    connection.commit()
    return {'migration_id': MIGRATION_ID, 'status': 'applied'}
