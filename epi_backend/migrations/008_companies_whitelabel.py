"""Migration 008: companies white-label & multi-tenant fields.

Adds slug, subdomain, custom_domain, branding colours, default_language
and related columns to the companies table. Idempotent via _safe_add_column.
"""

from __future__ import annotations

import pathlib

MIGRATION_ID = '008_companies_whitelabel'

_SQL_FILE = pathlib.Path(__file__).parent.parent.parent / 'supabase' / 'migrations' / '20260604000000_companies_whitelabel.sql'


def run(connection) -> dict[str, str]:
    connection.execute(_SQL_FILE.read_text(encoding='utf-8'))
    connection.commit()
    return {'migration_id': MIGRATION_ID, 'status': 'applied'}
