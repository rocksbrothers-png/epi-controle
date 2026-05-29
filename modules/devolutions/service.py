"""Serviços de devoluções de EPIs."""

from epi_backend.db import row_to_dict

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
