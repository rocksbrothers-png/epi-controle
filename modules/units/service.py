"""Serviços de unidades operacionais."""

from epi_backend.db import row_to_dict


def fetch_units(connection, actor=None):
    sql = (
        'SELECT units.id, units.company_id, units.name, units.unit_type, units.city, units.notes, '
        'companies.name AS company_name, companies.cnpj AS company_cnpj, companies.logo_type '
        'FROM units JOIN companies ON companies.id = units.company_id'
    )
    if actor and actor['role'] != 'master_admin':
        rows = connection.execute(
            sql + ' WHERE units.company_id = %s ORDER BY companies.name, units.name',
            (actor['company_id'],),
        ).fetchall()
    else:
        rows = connection.execute(sql + ' ORDER BY companies.name, units.name').fetchall()
    return [row_to_dict(row) for row in rows]


def get_unit_by_id(connection, unit_id):
    row = connection.execute(
        'SELECT id, company_id, name, unit_type, city, notes FROM units WHERE id = %s',
        (unit_id,),
    ).fetchone()
    return row_to_dict(row) if row else None


def get_unit_active_jv_name(connection, unit_id):
    if not unit_id:
        return ''
    row = connection.execute(
        'SELECT joint_venture_name FROM unit_joint_venture_periods '
        'WHERE unit_id = %s AND ended_at IS NULL '
        'ORDER BY started_at DESC LIMIT 1',
        (int(unit_id),),
    ).fetchone()
    if not row:
        return ''
    return str(dict(row).get('joint_venture_name') or '').strip()


def actor_operational_unit_id(connection, actor, *, get_employee_current_unit):
    if not actor or actor.get('role') not in ('admin', 'user'):
        return None
    linked_employee_id = actor.get('linked_employee_id')
    if not linked_employee_id:
        return None
    return get_employee_current_unit(connection, int(linked_employee_id))


def delete_unit_dependencies(connection, unit_id, *, delete_epi_dependencies):
    unit_id = int(unit_id)
    scoped_epi_ids = [
        int(row['id'])
        for row in connection.execute(
            'SELECT id FROM epis WHERE unit_id = %s', (unit_id,)
        ).fetchall()
    ]
    for epi_id in scoped_epi_ids:
        delete_epi_dependencies(connection, epi_id)

    connection.execute(
        'DELETE FROM epi_stock_item_reprints WHERE stock_item_id IN '
        '(SELECT id FROM epi_stock_items WHERE unit_id = %s)',
        (unit_id,),
    )
    connection.execute('DELETE FROM epi_stock_items WHERE unit_id = %s', (unit_id,))
    connection.execute('DELETE FROM stock_movements WHERE unit_id = %s', (unit_id,))
    connection.execute('DELETE FROM unit_epi_stock WHERE unit_id = %s', (unit_id,))

    request_ids = [
        int(row['id'])
        for row in connection.execute(
            'SELECT id FROM epi_requests WHERE unit_id = %s', (unit_id,)
        ).fetchall()
    ]
    if request_ids:
        placeholders = ','.join(['%s'] * len(request_ids))
        connection.execute(
            f'DELETE FROM epi_request_history WHERE request_id IN ({placeholders})',
            tuple(request_ids),
        )
    connection.execute('DELETE FROM epi_requests WHERE unit_id = %s', (unit_id,))

    connection.execute('DELETE FROM epi_ficha_items WHERE unit_id = %s', (unit_id,))
    connection.execute('DELETE FROM epi_ficha_periods WHERE unit_id = %s', (unit_id,))

    feedback_ids = [
        int(row['id'])
        for row in connection.execute(
            'SELECT id FROM epi_feedbacks WHERE unit_id = %s', (unit_id,)
        ).fetchall()
    ]
    if feedback_ids:
        placeholders = ','.join(['%s'] * len(feedback_ids))
        connection.execute(
            f'DELETE FROM epi_feedback_history WHERE feedback_id IN ({placeholders})',
            tuple(feedback_ids),
        )
    connection.execute('DELETE FROM epi_feedbacks WHERE unit_id = %s', (unit_id,))
    connection.execute('DELETE FROM deliveries WHERE unit_id = %s', (unit_id,))
    connection.execute(
        'DELETE FROM employee_unit_movements WHERE source_unit_id = %s OR target_unit_id = %s',
        (unit_id, unit_id),
    )

    employee_ids = [
        int(row['id'])
        for row in connection.execute(
            'SELECT id FROM employees WHERE unit_id = %s', (unit_id,)
        ).fetchall()
    ]
    if employee_ids:
        placeholders = ','.join(['%s'] * len(employee_ids))
        connection.execute(
            f'DELETE FROM employee_portal_audit WHERE employee_id IN ({placeholders})',
            tuple(employee_ids),
        )
        connection.execute(
            f'DELETE FROM employee_portal_links WHERE employee_id IN ({placeholders})',
            tuple(employee_ids),
        )
        connection.execute(
            f'DELETE FROM users WHERE linked_employee_id IN ({placeholders})',
            tuple(employee_ids),
        )
        connection.execute(
            f'DELETE FROM employees WHERE id IN ({placeholders})',
            tuple(employee_ids),
        )
