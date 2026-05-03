"""Serviços de entregas."""

from datetime import datetime


UTC = getattr(__import__('datetime'), 'UTC', None)
if UTC is None:
    from datetime import timezone
    UTC = timezone.utc

MSG_SIGNED_DIGITALLY = 'Assinado digitalmente'


def create_delivery_service(
    connection,
    payload,
    *,
    client_ip='',
    authorize_action,
    resolve_actor_user_id,
    get_employee_by_id,
    get_epi_by_id,
    ensure_resource_company,
    get_employee_current_unit,
    actor_operational_unit_id,
    get_unit_stock,
    upsert_unit_stock,
    ensure_ficha_for_delivery,
):
    actor = authorize_action(connection, resolve_actor_user_id(), 'deliveries:create', int(payload['company_id']))
    employee = get_employee_by_id(connection, int(payload['employee_id']))
    epi = get_epi_by_id(connection, int(payload['epi_id']))
    ensure_resource_company(actor, employee, 'Colaborador')
    ensure_resource_company(actor, epi, 'EPI')
    if str(employee['company_id']) != str(payload['company_id']) or str(epi['company_id']) != str(payload['company_id']):
        raise ValueError('Empresa incompatível para entrega.')
    quantity = int(payload['quantity'])
    if quantity != 1:
        raise ValueError('Entrega por leitura exige quantidade unitária (1).')
    stock_item_id = int(payload.get('stock_item_id') or 0)
    stock_qr_code = str(payload.get('stock_qr_code') or '').strip()
    if not stock_item_id or not stock_qr_code:
        raise ValueError('Leitura do código da unidade é obrigatória.')
    signature_data = str(payload.get('signature_data', '')).strip()
    signature_name = str(payload.get('signature_name') or '').strip()
    signature_comment = str(payload.get('signature_comment') or '').strip()
    signature_at = str(payload.get('signature_at') or '').strip()
    if signature_data:
        signature_name = signature_name or str(employee.get('name') or MSG_SIGNED_DIGITALLY)
        signature_at = signature_at or datetime.now(UTC).isoformat()
    else:
        signature_name = ''
        signature_comment = ''
        signature_at = ''
    if signature_data:
        signature_name = str(payload.get('signature_name') or actor.get('full_name') or 'Assinatura digital').strip() or 'Assinatura digital'
        signature_comment = str(payload.get('signature_comment') or '').strip()
        signature_at = str(payload.get('signature_at') or datetime.now(UTC).isoformat()).strip()
    employee_current_unit_id = get_employee_current_unit(connection, int(employee['id']))
    requested_unit_id = int(payload.get('unit_id') or 0)
    delivery_unit_id = int(requested_unit_id or employee_current_unit_id)
    if int(employee_current_unit_id) != int(delivery_unit_id):
        raise ValueError('Entrega só pode ocorrer na unidade operacional atual do colaborador.')
    actor_scope_unit_id = actor_operational_unit_id(connection, actor)
    if actor.get('role') in ('admin', 'user') and not actor_scope_unit_id:
        raise PermissionError('Seu perfil não possui unidade operacional ativa para registrar entregas.')
    if actor_scope_unit_id and int(delivery_unit_id) != int(actor_scope_unit_id):
        raise PermissionError('Seu perfil só pode registrar entregas na própria unidade operacional.')
    if epi.get('unit_id') and int(epi['unit_id']) != int(delivery_unit_id):
        raise ValueError('EPI vinculado a outra unidade operacional.')
    stock_item = connection.execute(
        (
            'SELECT id, company_id, unit_id, epi_id, status, qr_code_value '
            'FROM epi_stock_items '
            'WHERE id = ?'
        ),
        (stock_item_id,)
    ).fetchone()
    if not stock_item:
        raise ValueError('Unidade etiquetada não encontrada.')
    if str(stock_item['company_id']) != str(payload['company_id']) or int(stock_item['unit_id']) != int(delivery_unit_id):
        raise ValueError('Unidade etiquetada incompatível com empresa/unidade da entrega.')
    if int(stock_item['epi_id']) != int(payload['epi_id']):
        raise ValueError('Código lido não corresponde ao EPI selecionado.')
    if str(stock_item['qr_code_value']).strip().lower() != stock_qr_code.lower():
        raise ValueError('Código lido não confere com a unidade informada.')
    if str(stock_item['status']) != 'in_stock':
        raise ValueError('Entrega bloqueada: item já baixado, entregue, descartado ou inválido.')
    stock_row = get_unit_stock(connection, int(payload['company_id']), delivery_unit_id, int(epi['id']))
    current_stock = int((stock_row or {}).get('quantity') or 0)
    if current_stock < quantity:
        raise ValueError('Estoque insuficiente para realizar a entrega.')
    claim_cursor = connection.execute(
        (
            "UPDATE epi_stock_items "
            "SET status = 'delivering', updated_at = ? "
            "WHERE id = ? AND status = 'in_stock'"
        ),
        (datetime.now(UTC).isoformat(), stock_item_id)
    )
    if int(getattr(claim_cursor, 'rowcount', 0) or 0) != 1:
        raise ValueError('Entrega bloqueada: item já foi processado em outra operação. Atualize e tente novamente.')
    cursor = connection.execute(
        (
            'INSERT INTO deliveries (company_id, employee_id, epi_id, quantity, quantity_label, sector, role_name, '
            'delivery_date, next_replacement_date, notes, signature_name, signature_ip, signature_at, signature_data, signature_comment) '
            'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'
        ),
        (
            payload['company_id'], payload['employee_id'], payload['epi_id'], quantity,
            str(epi.get('unit_measure') or 'unidade'), payload['sector'], payload['role_name'], payload['delivery_date'],
            payload['next_replacement_date'], payload.get('notes', ''), signature_name,
            str(client_ip or ''), signature_at, signature_data, signature_comment
        )
    )
    new_stock = current_stock - quantity
    upsert_unit_stock(connection, int(payload['company_id']), delivery_unit_id, int(epi['id']), new_stock)
    stock_cursor = connection.execute(
        (
            'INSERT INTO stock_movements ('
            'company_id, unit_id, epi_id, movement_type, quantity, previous_stock, new_stock, '
            'source_type, source_id, notes, actor_user_id, actor_name, created_at'
            ') VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'
        ),
        (
            payload['company_id'], delivery_unit_id, epi['id'], 'out', quantity, current_stock, new_stock,
            'delivery', int(cursor.lastrowid), str(payload.get('notes', '')).strip(),
            actor['id'], actor['full_name'], datetime.now(UTC).isoformat()
        )
    )
    connection.execute('UPDATE deliveries SET unit_id = ?, stock_movement_id = ? WHERE id = ?', (delivery_unit_id, int(stock_cursor.lastrowid), int(cursor.lastrowid)))
    connection.execute(
        "UPDATE epi_stock_items SET status = 'delivered', delivery_id = ?, updated_at = ? WHERE id = ?",
        (int(cursor.lastrowid), datetime.now(UTC).isoformat(), stock_item_id)
    )
    ensure_ficha_for_delivery(
        connection,
        {
            'id': int(cursor.lastrowid),
            'company_id': int(payload['company_id']),
            'employee_id': int(payload['employee_id']),
            'unit_id': delivery_unit_id,
            'epi_id': int(payload['epi_id']),
            'quantity': quantity,
            'delivery_date': payload['delivery_date'],
            'schedule_type': employee.get('schedule_type'),
            'signature_name': signature_name,
            'signature_data': signature_data,
            'signature_ip': str(client_ip or ''),
            'signature_at': signature_at,
            'signature_comment': signature_comment
        }
    )
    if str(payload.get('request_id', '')).strip():
        connection.execute(
            "UPDATE epi_requests SET status = 'entregue', delivery_id = ?, last_updated_at = ? WHERE id = ?",
            (int(cursor.lastrowid), datetime.now(UTC).isoformat(), int(payload['request_id']))
        )
    connection.commit()
    return int(cursor.lastrowid)
