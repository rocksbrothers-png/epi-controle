"""Migration 026: faixa de atenção e habilitação de alerta por Unidade (#271).

Cria ``company_stock_attention_config`` (padrão de 20% por empresa),
``unit_epi_attention_percentage`` e ``unit_epi_stock_alert_settings`` (ambas
chaveadas por ``company_id + unit_id + epi_id``), mais
``unit_epi_stock_config_audit_logs``. Todas com RLS.

**Sem backfill**, pelo mesmo motivo da migration 025: a existência da linha é a
configuração local, e criá-las em massa marcaria como ``unit_configured`` quem
nunca configurou nada. Ver o cabeçalho do ``.sql`` para o raciocínio completo,
inclusive a assimetria deliberada entre ``company_default`` (mínimo,
percentual) e ``system_default`` (alerta).
"""

from __future__ import annotations

import pathlib

MIGRATION_ID = '026_stock_classification_config'

_SQL_FILE = (
    pathlib.Path(__file__).parent.parent.parent
    / 'supabase' / 'migrations' / '20260821000000_stock_classification_config.sql'
)


def run(connection) -> dict[str, str]:
    connection.execute(_SQL_FILE.read_text(encoding='utf-8'))
    connection.commit()
    return {'migration_id': MIGRATION_ID, 'status': 'applied'}
