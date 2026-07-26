"""Trilha de auditoria da empresa.

Vive em ``core`` — camada que não importa ``modules`` — para que qualquer módulo
possa registrar auditoria sem criar ciclo de importação. ``modules.companies.service``
reexporta ``register_company_audit`` por compatibilidade com os chamadores já
existentes.
"""

from __future__ import annotations

import json
from datetime import datetime

from epi_backend.db import table_columns


def register_company_audit(connection, company_id, actor, action_type, summary, details=None,
                           *, legal_entity_id=None):
    """Registra uma ação auditável no histórico da empresa.

    ``legal_entity_id`` identifica o CNPJ (LegalEntity) afetado pela ação, que
    tem efeito fiscal/trabalhista. Só entra no INSERT quando a coluna existe,
    preservando compatibilidade durante a janela de migração.
    """
    columns = ['company_id', 'actor_user_id', 'actor_name', 'action_type', 'summary',
               'details_json', 'created_at']
    values = [
        company_id,
        actor['id'],
        actor['full_name'],
        action_type,
        summary,
        json.dumps(details or [], ensure_ascii=False),
        datetime.now().isoformat(timespec='seconds'),
    ]
    if legal_entity_id not in (None, '', 0, '0') and 'legal_entity_id' in table_columns(connection, 'company_audit_logs'):
        columns.append('legal_entity_id')
        values.append(int(legal_entity_id))
    placeholders = ', '.join(['?'] * len(values))
    connection.execute(
        f"INSERT INTO company_audit_logs ({', '.join(columns)}) VALUES ({placeholders})",  # noqa: S608
        tuple(values),
    )
