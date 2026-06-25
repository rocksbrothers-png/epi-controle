"""Serviços de entregas."""

from datetime import datetime

from epi_backend.db import row_to_dict
from modules.epis.validity import is_expired
from modules.stock.service import apply_effective_size_fields


UTC = getattr(__import__('datetime'), 'UTC', None)
if UTC is None:
    from datetime import timezone
    UTC = timezone.utc

MSG_SIGNED_DIGITALLY = 'Assinado digitalmente'

def ensure_stock_movement_size_columns(connection):
    # Delega para a versão canônica e agnóstica de banco (SQLite + PostgreSQL).
    # A implementação anterior usava `PRAGMA table_info(stock_movements)` — sintaxe
    # exclusiva do SQLite — que no PostgreSQL/Supabase quebrava a conferência de
    # recebimento de PO com 'syntax error at or near "PRAGMA"' (HTTP 500 em
    # POST /api/purchase-requests/{id}/status). A versão de core.schema usa
    # introspecção via information_schema no Postgres e só adiciona colunas
    # ausentes (no-op quando já existem).
    from core.schema import ensure_stock_movement_size_columns as _ensure_canonical
    _ensure_canonical(connection)


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
    # Regra NT 146/2015: após a aquisição (com CA válido), o uso/entrega do EPI
    # não fica proibido pelo vencimento do CA — passa a valer a validade do
    # produto informada pelo fabricante. Portanto, bloqueia-se a entrega quando a
    # validade do fabricante está vencida; o CA vencido NÃO bloqueia a entrega.
    if is_expired(epi.get('epi_validity_date')):
        raise ValueError(
            'Entrega bloqueada: validade do fabricante do EPI vencida em '
            f"{epi.get('epi_validity_date')}. Retire o item do estoque (NT 146/2015)."
        )
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
            'SELECT id, company_id, unit_id, epi_id, status, qr_code_value, glove_size, size, uniform_size '
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
            'delivery_date, next_replacement_date, notes, signature_name, signature_ip, signature_at, signature_data, signature_comment, '
            'glove_size, size, uniform_size) '
            'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'
        ),
        (
            payload['company_id'], payload['employee_id'], payload['epi_id'], quantity,
            str(epi.get('unit_measure') or 'unidade'), payload['sector'], payload['role_name'], payload['delivery_date'],
            payload['next_replacement_date'], payload.get('notes', ''), signature_name,
            str(client_ip or ''), signature_at, signature_data, signature_comment,
            str(stock_item.get('glove_size') or 'N/A'), str(stock_item.get('size') or 'N/A'), str(stock_item.get('uniform_size') or 'N/A')
        )
    )
    new_stock = current_stock - quantity
    upsert_unit_stock(connection, int(payload['company_id']), delivery_unit_id, int(epi['id']), new_stock)
    ensure_stock_movement_size_columns(connection)
    stock_cursor = connection.execute(
        (
            'INSERT INTO stock_movements ('
            'company_id, unit_id, epi_id, movement_type, quantity, previous_stock, new_stock, '
            'source_type, source_id, notes, actor_user_id, actor_name, created_at, glove_size, size, uniform_size'
            ') VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'
        ),
        (
            payload['company_id'], delivery_unit_id, epi['id'], 'out', quantity, current_stock, new_stock,
            'delivery', int(cursor.lastrowid), str(payload.get('notes', '')).strip(),
            actor['id'], actor['full_name'], datetime.now(UTC).isoformat(),
            str(stock_item.get('glove_size') or 'N/A'), str(stock_item.get('size') or 'N/A'), str(stock_item.get('uniform_size') or 'N/A')
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


def fetch_deliveries(connection, actor=None, where_clause='', params=()):
    clauses = []
    query_params = list(params)
    if actor and actor['role'] != 'master_admin':
        clauses.append('deliveries.company_id = ?')
        query_params.append(actor['company_id'])
    if where_clause:
        clean = where_clause.strip()
        clauses.append(clean[6:] if clean.upper().startswith('WHERE ') else clean)
    final_where = f"WHERE {' AND '.join(clauses)}" if clauses else ''
    rows = connection.execute(
        f'''SELECT deliveries.id, deliveries.company_id, deliveries.employee_id, deliveries.epi_id, deliveries.quantity, deliveries.quantity_label, deliveries.sector, deliveries.role_name, deliveries.delivery_date, deliveries.next_replacement_date, deliveries.notes, deliveries.signature_name, deliveries.signature_data, deliveries.signature_at, deliveries.signature_comment, deliveries.unit_id, deliveries.stock_movement_id, deliveries.glove_size, deliveries.size, deliveries.uniform_size, deliveries.returned_date, deliveries.returned_condition, deliveries.returned_notes, deliveries.return_movement_id,
                          companies.name AS company_name, companies.cnpj AS company_cnpj, companies.logo_type,
                          employees.employee_id_code, employees.name AS employee_name, employees.schedule_type, employees.tipo_vinculo,
                          units.name AS unit_name, units.unit_type, epis.name AS epi_name, epis.purchase_code, epis.ca, epis.unit_measure, epis.epi_validity_date, epis.manufacture_date, epis.qr_code_value,
                          esi.glove_size AS stock_item_glove_size, esi.size AS stock_item_size, esi.uniform_size AS stock_item_uniform_size,
                          CASE WHEN COALESCE(deliveries.returned_date, '') != '' THEN 0
                               WHEN EXISTS (
                                   SELECT 1 FROM epi_ficha_items fi
                                   JOIN epi_ficha_periods fp ON fp.id = fi.ficha_period_id
                                   WHERE fi.delivery_id = deliveries.id
                                     AND fp.status = 'closed'
                               ) THEN 0
                               WHEN NOT EXISTS (
                                   SELECT 1 FROM epi_ficha_items fi WHERE fi.delivery_id = deliveries.id
                               ) AND EXISTS (
                                   SELECT 1 FROM epi_ficha_periods fp
                                   WHERE fp.employee_id = deliveries.employee_id
                                     AND fp.period_start <= deliveries.delivery_date
                                     AND fp.period_end   >= deliveries.delivery_date
                                     AND fp.status = 'closed'
                               ) THEN 0
                               ELSE 1 END AS devolution_available
                   FROM deliveries
                   JOIN companies ON companies.id = deliveries.company_id
                   JOIN employees ON employees.id = deliveries.employee_id
                   LEFT JOIN units ON units.id = deliveries.unit_id
                   JOIN epis ON epis.id = deliveries.epi_id
                   LEFT JOIN epi_stock_items esi ON esi.delivery_id = deliveries.id AND esi.id = (SELECT MAX(esi_latest.id) FROM epi_stock_items esi_latest WHERE esi_latest.delivery_id = deliveries.id)
                   {final_where}
                   ORDER BY deliveries.delivery_date DESC, deliveries.id DESC''',
        tuple(query_params),
    ).fetchall()
    items = []
    for row in rows:
        item = row_to_dict(row)
        apply_effective_size_fields(item, item, item, fallback_prefix='stock_item_')
        items.append(item)
    return items
