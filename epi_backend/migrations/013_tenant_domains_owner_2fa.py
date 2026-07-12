"""Migration 013: tenant_domains + 2FA (TOTP) do Owner.

Cria a tabela de domínios por tenant (com verificação CNAME/SSL), faz o
backfill dos campos legados companies.subdomain/custom_domain e adiciona as
colunas totp_secret/totp_enabled em users. Idempotente.
"""

from __future__ import annotations

import pathlib

MIGRATION_ID = '013_tenant_domains_owner_2fa'

_SQL_FILE = pathlib.Path(__file__).parent.parent.parent / 'supabase' / 'migrations' / '20260712120000_tenant_domains_owner_2fa.sql'


def run(connection) -> dict[str, str]:
    connection.execute(_SQL_FILE.read_text(encoding='utf-8'))
    connection.commit()
    return {'migration_id': MIGRATION_ID, 'status': 'applied'}
