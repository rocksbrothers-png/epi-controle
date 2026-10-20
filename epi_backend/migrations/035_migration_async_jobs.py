"""035 — fila durável de migração assíncrona (MIG-DATA-FIX-V1 Fase 3).

Cria somente a tabela de controle ``migration_async_jobs`` (nenhuma entidade
de negócio, fila externa ou serviço novo). O processamento assíncrono fica
DESLIGADO por padrão: só roda com ``MIGRATION_ASYNC_ENABLED`` ligado e um worker
dedicado. A DDL é idempotente e compartilhada com ``async_jobs.install_schema``.
"""
from modules.data_migration import async_jobs

MIGRATION_ID = '035_migration_async_jobs'


def run(connection):
    async_jobs.install_schema(connection)
    connection.commit()
    return {'migration_id': MIGRATION_ID, 'status': 'applied'}
