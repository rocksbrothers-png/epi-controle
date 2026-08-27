"""Migration 028: a RLS das cinco tabelas de billing passa a ser versionada (#309).

`payments`, `payment_plans`, `subscriptions`, `invoices` e
`subscription_audit_logs` recebiam RLS de ``modules/payments/service.py``, via
``_enable_rls``. As duas funções que o chamavam estão em ``_ensure_fns``, então
a proteção rodava em todo boot e existe em produção — o defeito era de
rastreabilidade, não de ausência. Ver o cabeçalho do ``.sql`` para o raciocínio
completo, inclusive por que o bloco único ``DO $$`` torna inalcançável o estado
"RLS ligada sem policy".
"""

from __future__ import annotations

import pathlib

MIGRATION_ID = '028_billing_rls'

_SQL_FILE = (
    pathlib.Path(__file__).parent.parent.parent
    / 'supabase' / 'migrations' / '20260827000000_billing_rls.sql'
)


def run(connection) -> dict[str, str]:
    connection.execute(_SQL_FILE.read_text(encoding='utf-8'))
    connection.commit()
    return {'migration_id': MIGRATION_ID, 'status': 'applied'}
