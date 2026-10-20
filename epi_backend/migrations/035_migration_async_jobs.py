"""035 — fila durável de migração assíncrona (MIG-DATA-FIX-V1 Fase 3).

Cria a tabela de controle ``migration_async_jobs`` (via ``async_jobs.install_schema``)
e aplica a RLS versionada do `.sql` pareado (ADR-0005), nunca DDL de RLS própria
(#309). Nenhuma entidade de negócio, fila externa ou serviço novo. O processamento
assíncrono fica DESLIGADO por padrão (``MIGRATION_ASYNC_ENABLED``). PostgreSQL-only.
"""
from pathlib import Path

from modules.data_migration import async_jobs

MIGRATION_ID = '035_migration_async_jobs'
SQL_FILE = (Path(__file__).resolve().parents[2]
            / 'supabase' / 'migrations' / '20261016000000_migration_async_jobs.sql')


def run(connection):
    async_jobs.install_schema(connection)                      # tabela + índices
    connection.execute(SQL_FILE.read_text(encoding='utf-8'))   # RLS versionada (.sql)
    connection.commit()
    return {'migration_id': MIGRATION_ID, 'status': 'applied'}
