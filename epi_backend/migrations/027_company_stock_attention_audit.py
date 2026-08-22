"""Migration 027: auditoria do percentual de atenção corporativo (#271-B1b).

Cria ``company_stock_attention_config_audit_logs`` com RLS. A tabela nasceu
apenas em ``core/schema.py`` e, como o ``executescript`` também roda contra
PostgreSQL, passou a existir no schema ``public`` sem RLS — trilha de auditoria
com nome do ator, IP e user agent legível pelo PostgREST com a chave anon. Ver
o cabeçalho do ``.sql`` para o raciocínio completo, inclusive por que a
auditoria corporativa não cabe em ``unit_epi_stock_config_audit_logs``.
"""

from __future__ import annotations

import pathlib

MIGRATION_ID = '027_company_stock_attention_audit'

_SQL_FILE = (
    pathlib.Path(__file__).parent.parent.parent
    / 'supabase' / 'migrations' / '20260822000000_company_stock_attention_audit.sql'
)


def run(connection) -> dict[str, str]:
    connection.execute(_SQL_FILE.read_text(encoding='utf-8'))
    connection.commit()
    return {'migration_id': MIGRATION_ID, 'status': 'applied'}
