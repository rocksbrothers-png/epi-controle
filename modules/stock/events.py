"""Escrita append-only de eventos físicos, sem dependência do serviço agregado."""

def append_stock_event(connection, *, company_id, epi_id, stock_item_id, event_type, reason_code,
                        justification, actor_user_id, actor_name, actor_role, now,
                        before_values, after_values, quantity=1, origin_unit_id=None):
    """Grava uma linha no histórico append-only ``epi_stock_events`` (imutável por
    trigger em PostgreSQL; somente-inserção no código). Nunca atualiza/apaga."""
    import json as _json
    connection.execute(
        'INSERT INTO epi_stock_events (company_id, epi_id, stock_item_id, lot_id, quantity, '
        'event_type, origin_unit_id, destination_unit_id, reason_code, justification, '
        'actor_user_id, actor_name_snapshot, actor_role_snapshot, created_at, '
        'before_values, after_values) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
        (int(company_id), int(epi_id), int(stock_item_id), None, int(quantity),
         str(event_type), (int(origin_unit_id) if origin_unit_id else None), None,
         str(reason_code), str(justification), int(actor_user_id),
         str(actor_name or ''), str(actor_role or ''), str(now),
         _json.dumps(before_values, ensure_ascii=False, sort_keys=True),
         _json.dumps(after_values, ensure_ascii=False, sort_keys=True)),
    )
