"""Migration 023: procedência da entrega — Lote 2 do Centro de Migração.

Acrescenta a `deliveries` as colunas que distinguem uma entrega **migrada** de
uma entrega **criada pelo sistema** (`origin`, `source_system`,
`migration_job_id`) e o marcador de rollback lógico
(`migration_reverted_at`); acrescenta a `migration_jobs` o estado de
homologação (`homologated_at`, `homologated_by`), que é a fronteira entre
reversão física e reversão lógica.

Toda a DDL é idempotente, então reexecutar é seguro mesmo depois de
`ensure_delivery_migration_origin_columns` já ter provisionado o schema no
bootstrap.

Ver issue #211 e ADR-0003 §9 (Lote 2).
"""

from __future__ import annotations

import pathlib

MIGRATION_ID = '023_delivery_migration_origin'

_SQL_FILE = (
    pathlib.Path(__file__).parent.parent.parent
    / 'supabase' / 'migrations' / '20260811120000_delivery_migration_origin.sql'
)


def run(connection) -> dict[str, str]:
    connection.execute(_SQL_FILE.read_text(encoding='utf-8'))
    connection.commit()
    return {'migration_id': MIGRATION_ID, 'status': 'applied'}
