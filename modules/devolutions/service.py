"""Serviços de devoluções de EPIs."""

from datetime import datetime, timezone

from epi_backend.db import row_to_dict
from epi_backend.http_utils import require_fields, structured_log
from core.auth import ensure_resource_company
from modules.employees.service import get_employee_by_id
from modules.stock.service import get_unit_stock, upsert_unit_stock, resolve_effective_size_fields

UTC = timezone.utc

DEVOLUTION_CONDITION_LABELS = {
    'usable':      'Reutilizável',
    'damaged':     'Danificado',
    'discarded':   'Descartado',
    'maintenance': 'Em manutenção',
    'quarantine':  'Em quarentena',
    'hygiene':     'Para higienização',
}

DEVOLUTION_DESTINATION_LABELS = {
    'stock':       'Retornou ao estoque',
    'discard':     'Descartado',
    'maintenance': 'Encaminhado para manutenção',
    'hygiene':     'Encaminhado para higienização',
    'quarantine':  'Em quarentena',
}

STOCK_ITEM_STATUS_BY_DESTINATION = {
    'stock':       'in_stock',
    'discard':     'discarded',
    'maintenance': 'maintenance',
    'hygiene':     'hygiene',
    'quarantine':  'quarantine',
}


def fetch_open_deliveries_for_devolution(connection, actor, employee_id, epi_id, unit_id=None):
    employee_id = int(employee_id)
    epi_id = int(epi_id)
    clauses = [
        'd.employee_id = ?',
        'd.epi_id = ?',
        "COALESCE(d.returned_date, '') = ''",
        """(
            NOT EXISTS (
                SELECT 1 FROM epi_ficha_items fi
                JOIN epi_ficha_periods fp ON fp.id = fi.ficha_period_id
                WHERE fi.delivery_id = d.id AND fp.status = 'closed'
            )
            AND (
                EXISTS (SELECT 1 FROM epi_ficha_items fi WHERE fi.delivery_id = d.id)
                OR NOT EXISTS (
                    SELECT 1 FROM epi_ficha_periods fp
                    WHERE fp.employee_id = d.employee_id
                      AND fp.period_start <= d.delivery_date
                      AND fp.period_end   >= d.delivery_date
                      AND fp.status = 'closed'
                )
            )
        )""",
    ]
    params = [employee_id, epi_id]
    if actor and actor.get('role') != 'master_admin':
        clauses.append('d.company_id = ?')
        params.append(int(actor.get('company_id') or 0))
    if str(unit_id or '').strip():
        clauses.append('d.unit_id = ?')
        params.append(int(unit_id))
    where_sql = f"WHERE {' AND '.join(clauses)}"
    rows = connection.execute(
        f'''
        SELECT d.id, d.employee_id, d.epi_id, d.unit_id, d.delivery_date, d.quantity, d.quantity_label,
               d.signature_at, d.signature_name,
               COALESCE(u.name, '') AS unit_name, COALESCE(c.name, '') AS company_name
        FROM deliveries d
        JOIN companies c ON c.id = d.company_id
        LEFT JOIN units u ON u.id = d.unit_id
        {where_sql}
        ORDER BY d.delivery_date DESC, d.id DESC
        ''',
        tuple(params),
    ).fetchall()
    items = []
    for row in rows:
        parsed = row_to_dict(row)
        items.append({
            'id': int(parsed['id']),
            'employee_id': int(parsed['employee_id']),
            'epi_id': int(parsed['epi_id']),
            'delivery_date': str(parsed.get('delivery_date') or ''),
            'quantity': int(parsed.get('quantity') or 1),
            'quantity_label': str(parsed.get('quantity_label') or ''),
            'unit_id': int(parsed.get('unit_id') or 0),
            'unit_name': str(parsed.get('unit_name') or ''),
            'company_name': str(parsed.get('company_name') or ''),
            'signature_at': str(parsed.get('signature_at') or ''),
            'signature_name': str(parsed.get('signature_name') or ''),
        })
    return items


def fetch_devolutions(connection, actor, filters=None):
    filters = filters or {}
    clauses, params = [], []
    if actor['role'] != 'master_admin':
        clauses.append('d.company_id = ?')
        params.append(int(actor['company_id']))
    for key in ('employee_id', 'epi_id', 'delivery_id'):
        if filters.get(key):
            clauses.append(f'd.{key} = ?')
            params.append(int(filters[key]))
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ''
    rows = connection.execute(
        f"""SELECT d.*, emp.name AS employee_name, emp.employee_id_code,
                   e.name AS epi_name, e.ca, e.unit_measure, u.name AS unit_name
            FROM epi_devolutions d
            JOIN employees emp ON emp.id = d.employee_id
            JOIN epis      e   ON e.id   = d.epi_id
            JOIN units     u   ON u.id   = d.unit_id
            {where}
            ORDER BY d.returned_date DESC, d.id DESC""",
        tuple(params),
    ).fetchall()
    result = []
    for row in rows:
        item = row_to_dict(row)
        item['condition_label'] = DEVOLUTION_CONDITION_LABELS.get(item.get('condition', ''), item.get('condition', ''))
        item['destination_label'] = DEVOLUTION_DESTINATION_LABELS.get(item.get('destination', ''), item.get('destination', ''))
        result.append(item)
    return result


def register_epi_devolution(connection, payload, actor):
    from modules.deliveries.service import ensure_stock_movement_size_columns
    from modules.ficha.service import ensure_ficha_for_devolution
    require_fields(payload, ['actor_user_id', 'delivery_id', 'returned_date', 'condition', 'destination'])
    delivery_id   = int(payload['delivery_id'])
    returned_date = str(payload['returned_date']).strip()
    condition     = str(payload.get('condition', 'usable')).strip()
    destination   = str(payload.get('destination', 'stock')).strip()
    notes         = str(payload.get('notes', '')).strip()
    reason        = str(payload.get('reason', '')).strip()
    signature_data = str(payload.get('signature_data') or '').strip()
    signature_name = str(payload.get('signature_name') or '').strip()
    signature_comment = str(payload.get('signature_comment') or '').strip()
    signature_at = str(payload.get('signature_at') or '').strip()
    expected_employee_id = str(payload.get('expected_employee_id') or '').strip()
    expected_epi_id = str(payload.get('expected_epi_id') or '').strip()
    expected_unit_id = str(payload.get('expected_unit_id') or '').strip()

    if condition not in DEVOLUTION_CONDITION_LABELS:
        raise ValueError('Condição inválida.')
    if destination not in DEVOLUTION_DESTINATION_LABELS:
        raise ValueError('Destino inválido.')

    delivery = connection.execute(
        'SELECT d.*, e.name AS epi_name FROM deliveries d JOIN epis e ON e.id = d.epi_id WHERE d.id = ?',
        (delivery_id,)
    ).fetchone()
    if not delivery:
        raise ValueError('Entrega não encontrada.')
    delivery = row_to_dict(delivery)
    ensure_resource_company(actor, delivery, 'Entrega')
    if expected_employee_id and int(expected_employee_id) != int(delivery.get('employee_id') or 0):
        raise ValueError('Entrega selecionada não pertence ao colaborador informado.')
    if expected_epi_id and int(expected_epi_id) != int(delivery.get('epi_id') or 0):
        raise ValueError('Entrega selecionada não pertence ao EPI informado.')
    if expected_unit_id and int(expected_unit_id) != int(delivery.get('unit_id') or 0):
        raise ValueError('Entrega selecionada não pertence à unidade informada.')

    employee = get_employee_by_id(connection, int(delivery['employee_id']))
    if str(delivery.get('returned_date') or '').strip():
        raise ValueError('Este EPI já foi registrado como devolvido.')
    _has_ficha_item = connection.execute(
        'SELECT 1 FROM epi_ficha_items fi WHERE fi.delivery_id = ? LIMIT 1', (delivery_id,)
    ).fetchone()
    if _has_ficha_item:
        _closed_period = connection.execute(
            """SELECT fp.id FROM epi_ficha_items fi
               JOIN epi_ficha_periods fp ON fp.id = fi.ficha_period_id
               WHERE fi.delivery_id = ? AND fp.status = 'closed'
               LIMIT 1""",
            (delivery_id,),
        ).fetchone()
    else:
        _delivery_date = str(delivery.get('delivery_date') or '').strip()
        _closed_period = connection.execute(
            """SELECT id FROM epi_ficha_periods
               WHERE employee_id = ? AND period_start <= ? AND period_end >= ? AND status = 'closed'
               LIMIT 1""",
            (int(delivery['employee_id']), _delivery_date, _delivery_date),
        ).fetchone() if _delivery_date else None
    if _closed_period:
        raise ValueError('Período da ficha de EPI encerrado. Devolução não é permitida após o fechamento do período.')
    if signature_data:
        signature_name = signature_name or str(employee.get('name') or actor.get('full_name') or 'Assinatura digital').strip()
        signature_at = signature_at or datetime.now(UTC).isoformat()
    else:
        signature_name = ''
        signature_at = ''
        signature_comment = ''

    now = datetime.now(UTC).isoformat()
    quantity = int(delivery.get('quantity') or 1)

    dev_cursor = connection.execute(
        """INSERT INTO epi_devolutions
           (company_id, unit_id, employee_id, epi_id, delivery_id,
            returned_date, quantity, condition, destination,
            notes, reason, received_by_user_id, received_by_name,
            signature_name, signature_data, signature_ip, signature_at, signature_comment, created_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            int(delivery['company_id']),
            int(delivery.get('unit_id') or 0),
            int(delivery['employee_id']),
            int(delivery['epi_id']),
            delivery_id,
            returned_date, quantity, condition, destination,
            notes, reason,
            int(actor['id']),
            str(actor.get('full_name') or ''),
            signature_name,
            signature_data,
            str(payload.get('signature_ip') or ''),
            signature_at,
            signature_comment,
            now,
        )
    )
    devolution_id = int(dev_cursor.lastrowid)
    ensure_ficha_for_devolution(
        connection,
        {
            'id': devolution_id,
            'company_id': int(delivery['company_id']),
            'employee_id': int(delivery['employee_id']),
            'unit_id': int(delivery.get('unit_id') or 0),
            'returned_date': returned_date,
            'schedule_type': str(employee.get('schedule_type') or ''),
        }
    )

    connection.execute(
        'UPDATE deliveries SET returned_date=?, returned_condition=?, returned_notes=? WHERE id=?',
        (returned_date, condition, notes, delivery_id)
    )

    stock_item_status = STOCK_ITEM_STATUS_BY_DESTINATION.get(destination, 'in_stock')
    try:
        stock_item = connection.execute(
            'SELECT id, glove_size, size, uniform_size FROM epi_stock_items WHERE delivery_id=? ORDER BY id DESC LIMIT 1',
            (delivery_id,)
        ).fetchone()
    except Exception as exc:
        structured_log('warning', 'devolution.stock_item_size_columns_unavailable', delivery_id=delivery_id, error=str(exc))
        stock_item = connection.execute(
            'SELECT id FROM epi_stock_items WHERE delivery_id=? ORDER BY id DESC LIMIT 1',
            (delivery_id,)
        ).fetchone()
    stock_item_data = row_to_dict(stock_item) if stock_item else {}
    effective_delivery_size = resolve_effective_size_fields(delivery, stock_item_data)
    if stock_item:
        connection.execute(
            'UPDATE epi_stock_items SET status=?, updated_at=? WHERE id=?',
            (stock_item_status, now, int(stock_item['id']))
        )
        connection.execute(
            'UPDATE epi_devolutions SET stock_item_id=? WHERE id=?',
            (int(stock_item['id']), devolution_id)
        )

    movement_id = None
    if destination == 'stock':
        unit_id    = int(delivery.get('unit_id') or 0)
        epi_id     = int(delivery['epi_id'])
        company_id = int(delivery['company_id'])
        stock_row  = get_unit_stock(connection, company_id, unit_id, epi_id)
        prev_stock = int((stock_row or {}).get('quantity') or 0)
        new_stock  = prev_stock + quantity
        ensure_stock_movement_size_columns(connection)
        mov = connection.execute(
            """INSERT INTO stock_movements
               (company_id, unit_id, epi_id, movement_type, quantity,
                previous_stock, new_stock, source_type, source_id,
                notes, actor_user_id, actor_name, created_at, glove_size, size, uniform_size)
               VALUES (?,?,?,'return',?,?,?,'devolution',?,?,?,?,?,?,?,?)""",
            (company_id, unit_id, epi_id, quantity, prev_stock, new_stock,
             devolution_id,
             'Devolucao — ' + str(delivery.get('epi_name') or ''),
             int(actor['id']), str(actor.get('full_name') or ''), now,
             effective_delivery_size['glove_size'],
             effective_delivery_size['size'],
             effective_delivery_size['uniform_size'])
        )
        movement_id = int(mov.lastrowid)
        upsert_unit_stock(connection, company_id, unit_id, epi_id, new_stock)
        connection.execute(
            'UPDATE epi_devolutions SET stock_movement_id=? WHERE id=?',
            (movement_id, devolution_id)
        )
        connection.execute(
            'UPDATE deliveries SET return_movement_id=? WHERE id=?',
            (movement_id, delivery_id)
        )

    connection.commit()
    structured_log('info', 'devolution.registered',
                   devolution_id=devolution_id, delivery_id=delivery_id,
                   condition=condition, destination=destination)
    return devolution_id
