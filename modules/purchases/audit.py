"""Trilha de auditoria de Compras (``purchase_events``).

Módulo folha (só depende do banco): quem precisa gravar evento de Compras o
importa sem criar ciclo com ``modules.purchases.service``. O nome histórico
``service._record_purchase_event`` continua disponível (reexportado).
"""

from datetime import datetime, timezone

UTC = timezone.utc


def record_purchase_event(connection, company_id, entity_type, entity_id, action, status_from, status_to, comment,
                          actor_user_id, actor_name, ip_address='', actor_role='', reason='', destination=''):
    now = datetime.now(UTC).isoformat()
    connection.execute(
        'INSERT INTO purchase_events (company_id, entity_type, entity_id, action, status_from, status_to, comment, '
        'actor_user_id, actor_name, actor_role, reason, destination, ip_address, created_at) '
        'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
        (company_id, entity_type, entity_id, action, status_from, status_to, comment, actor_user_id, actor_name,
         actor_role, reason, destination, ip_address, now)
    )
