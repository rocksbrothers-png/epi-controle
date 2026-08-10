"""Migration 022: limpa employees.legal_entity_id gravado indevidamente em
colaborador terceirizado/prestador (ADR-0002 §13.7).

Colaborador terceirizado tem vínculo jurídico com outsourced_company_id
(pessoa jurídica terceira), nunca com um CNPJ do próprio tenant
(legal_entities) — resolve_employee_legal_entity_id não deveria ter sido
chamado nesse fluxo. UPDATE idempotente, sem efeito em colaborador CLT.
"""

from __future__ import annotations

import pathlib

MIGRATION_ID = '022_employee_outsourced_legal_entity_cleanup'

_SQL_FILE = (
    pathlib.Path(__file__).parent.parent.parent
    / 'supabase' / 'migrations' / '20260810000000_employee_outsourced_legal_entity_cleanup.sql'
)


def run(connection) -> dict[str, str]:
    connection.execute(_SQL_FILE.read_text(encoding='utf-8'))
    connection.commit()
    return {'migration_id': MIGRATION_ID, 'status': 'applied'}
