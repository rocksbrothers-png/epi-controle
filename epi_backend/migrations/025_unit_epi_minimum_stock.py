"""Migration 025: estoque mínimo individual por Unidade (fatia 1.1D-B0).

Cria ``unit_epi_minimum_stock`` (chave ``company_id + unit_id + epi_id``) e
``unit_epi_minimum_stock_audit_logs``, ambas com RLS habilitada.

``epis.minimum_stock`` permanece intacta e passa a ser o **padrão da empresa**:
o mínimo efetivo de um par (Unidade, EPI) sem configuração própria cai nela,
com ``source = 'company_default'``.

**Sem backfill, deliberadamente.** A existência da linha É a configuração da
Unidade; criá-las em massa marcaria como ``unit_configured`` toda Unidade que
nunca configurou nada. E não é preciso para preservar comportamento: o fallback
já devolve o mesmo número de hoje. Ver o cabeçalho do ``.sql`` para o
raciocínio completo.

Toda a DDL é idempotente (``IF NOT EXISTS`` / ``NOT EXISTS``), então reexecutar
é seguro mesmo depois de ``ensure_unit_epi_minimum_stock`` já ter provisionado
o schema no bootstrap.
"""

from __future__ import annotations

import pathlib

MIGRATION_ID = '025_unit_epi_minimum_stock'

_SQL_FILE = (
    pathlib.Path(__file__).parent.parent.parent
    / 'supabase' / 'migrations' / '20260820000000_unit_epi_minimum_stock.sql'
)


def run(connection) -> dict[str, str]:
    connection.execute(_SQL_FILE.read_text(encoding='utf-8'))
    connection.commit()
    return {'migration_id': MIGRATION_ID, 'status': 'applied'}
