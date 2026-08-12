"""Migration 024: vínculo local do colaborador terceirizado com a Unidade
(ADR-0002 §13, PR B da issue #180).

Cria ``employee_unit_links`` — estrutura paralela e independente de
``employees.unit_id``, que permite reutilizar a mesma pessoa em mais de uma
Unidade sem duplicar o cadastro — com RLS habilitada e backfill idempotente
do vínculo inicial para os terceirizados já cadastrados.

Toda a DDL é idempotente (IF NOT EXISTS / NOT EXISTS), então reexecutar é
seguro mesmo depois de ``ensure_employee_unit_links`` /
``ensure_employee_unit_links_backfill`` já terem provisionado o schema no
bootstrap.
"""

from __future__ import annotations

import pathlib

MIGRATION_ID = '024_employee_unit_links'

_SQL_FILE = (
    pathlib.Path(__file__).parent.parent.parent
    / 'supabase' / 'migrations' / '20260812000000_employee_unit_links.sql'
)


def run(connection) -> dict[str, str]:
    connection.execute(_SQL_FILE.read_text(encoding='utf-8'))
    connection.commit()
    return {'migration_id': MIGRATION_ID, 'status': 'applied'}
