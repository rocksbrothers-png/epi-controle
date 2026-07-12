"""Migration 012: Minha Empresa (Administrador Geral) + onboarding.

Adds cadastral/preference columns (state_registration, municipal_registration,
address, whatsapp, display_name, timezone) and the first-access wizard flag
(onboarding_completed / onboarding_completed_at) to companies.
Idempotent via ADD COLUMN IF NOT EXISTS.
"""

from __future__ import annotations

import pathlib

MIGRATION_ID = '012_company_settings_onboarding'

_SQL_FILE = pathlib.Path(__file__).parent.parent.parent / 'supabase' / 'migrations' / '20260712000000_company_settings_onboarding.sql'


def run(connection) -> dict[str, str]:
    connection.execute(_SQL_FILE.read_text(encoding='utf-8'))
    connection.commit()
    return {'migration_id': MIGRATION_ID, 'status': 'applied'}
