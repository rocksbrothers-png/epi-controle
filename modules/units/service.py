"""Serviços de unidades operacionais."""

from epi_backend.db import row_to_dict


def normalize_unit_type(value):
    raw = str(value or '').strip().lower()
    aliases = {
        'navio': 'embarcacao',
        'embarcação': 'embarcacao',
        'embarcacao': 'embarcacao',
        'base': 'base',
        'plataforma': 'plataforma',
    }
    return aliases.get(raw, raw or 'base')


def fetch_units(connection, actor=None):
    sql = (
        'SELECT units.id, units.company_id, units.name, units.unit_type, units.city, units.notes, '
        'companies.name AS company_name, companies.cnpj AS company_cnpj, companies.logo_type '
        'FROM units JOIN companies ON companies.id = units.company_id'
    )
    if actor and actor['role'] != 'master_admin':
        rows = connection.execute(
            sql + ' WHERE units.company_id = ? ORDER BY companies.name, units.name',
            (actor['company_id'],),
        ).fetchall()
    else:
        rows = connection.execute(sql + ' ORDER BY companies.name, units.name').fetchall()
    return [row_to_dict(row) for row in rows]


def get_unit_by_id(connection, unit_id):
    row = connection.execute(
        'SELECT id, company_id, name, unit_type, city, notes FROM units WHERE id = ?',
        (unit_id,),
    ).fetchone()
    return row_to_dict(row) if row else None


def get_unit_active_jv_name(connection, unit_id):
    if not unit_id:
        return ''
    row = connection.execute(
        'SELECT joint_venture_name FROM unit_joint_venture_periods '
        'WHERE unit_id = ? AND ended_at IS NULL '
        'ORDER BY started_at DESC LIMIT 1',
        (int(unit_id),),
    ).fetchone()
    if not row:
        return ''
    return str(dict(row).get('joint_venture_name') or '').strip()


def delete_epi_dependencies(connection, epi_id):
    epi_id = int(epi_id)
    connection.execute(
        'DELETE FROM epi_stock_item_reprints WHERE stock_item_id IN (SELECT id FROM epi_stock_items WHERE epi_id = ?)',
        (epi_id,)
    )
    connection.execute('DELETE FROM epi_stock_items WHERE epi_id = ?', (epi_id,))
    connection.execute('DELETE FROM stock_movements WHERE epi_id = ?', (epi_id,))
    connection.execute('DELETE FROM unit_epi_stock WHERE epi_id = ?', (epi_id,))
    connection.execute('DELETE FROM epi_ficha_items WHERE epi_id = ?', (epi_id,))
    connection.execute('DELETE FROM deliveries WHERE epi_id = ?', (epi_id,))
    request_ids = [
        int(row['id'])
        for row in connection.execute('SELECT id FROM epi_requests WHERE epi_id = ?', (epi_id,)).fetchall()
    ]
    if request_ids:
        connection.execute(
            f"DELETE FROM epi_request_history WHERE request_id IN ({','.join(['?'] * len(request_ids))})",
            tuple(request_ids)
        )
    connection.execute('DELETE FROM epi_requests WHERE epi_id = ?', (epi_id,))
    feedback_ids = [
        int(row['id'])
        for row in connection.execute('SELECT id FROM epi_feedbacks WHERE epi_id = ?', (epi_id,)).fetchall()
    ]
    if feedback_ids:
        connection.execute(
            f"DELETE FROM epi_feedback_history WHERE feedback_id IN ({','.join(['?'] * len(feedback_ids))})",
            tuple(feedback_ids)
        )
    connection.execute('DELETE FROM epi_feedbacks WHERE epi_id = ?', (epi_id,))
    connection.execute('DELETE FROM epis WHERE id = ?', (epi_id,))


def delete_unit_dependencies(connection, unit_id):
    unit_id = int(unit_id)
    scoped_epi_ids = [
        int(row['id'])
        for row in connection.execute('SELECT id FROM epis WHERE unit_id = ?', (unit_id,)).fetchall()
    ]
    for epi_id in scoped_epi_ids:
        delete_epi_dependencies(connection, epi_id)
    connection.execute(
        'DELETE FROM epi_stock_item_reprints WHERE stock_item_id IN (SELECT id FROM epi_stock_items WHERE unit_id = ?)',
        (unit_id,)
    )
    connection.execute('DELETE FROM epi_stock_items WHERE unit_id = ?', (unit_id,))
    connection.execute('DELETE FROM stock_movements WHERE unit_id = ?', (unit_id,))
    connection.execute('DELETE FROM unit_epi_stock WHERE unit_id = ?', (unit_id,))
    request_ids = [
        int(row['id'])
        for row in connection.execute('SELECT id FROM epi_requests WHERE unit_id = ?', (unit_id,)).fetchall()
    ]
    if request_ids:
        connection.execute(
            f"DELETE FROM epi_request_history WHERE request_id IN ({','.join(['?'] * len(request_ids))})",
            tuple(request_ids)
        )
    connection.execute('DELETE FROM epi_requests WHERE unit_id = ?', (unit_id,))
    ficha_item_ids = [
        int(row['id'])
        for row in connection.execute('SELECT id FROM epi_ficha_items WHERE unit_id = ?', (unit_id,)).fetchall()
    ]
    if ficha_item_ids:
        connection.execute('DELETE FROM epi_ficha_items WHERE unit_id = ?', (unit_id,))
    connection.execute('DELETE FROM epi_ficha_periods WHERE unit_id = ?', (unit_id,))
    feedback_ids = [
        int(row['id'])
        for row in connection.execute('SELECT id FROM epi_feedbacks WHERE unit_id = ?', (unit_id,)).fetchall()
    ]
    if feedback_ids:
        connection.execute(
            f"DELETE FROM epi_feedback_history WHERE feedback_id IN ({','.join(['?'] * len(feedback_ids))})",
            tuple(feedback_ids)
        )
    connection.execute('DELETE FROM epi_feedbacks WHERE unit_id = ?', (unit_id,))
    connection.execute('DELETE FROM deliveries WHERE unit_id = ?', (unit_id,))
    connection.execute(
        'DELETE FROM employee_unit_movements WHERE source_unit_id = ? OR target_unit_id = ?',
        (unit_id, unit_id)
    )
    employee_ids = [
        int(row['id'])
        for row in connection.execute('SELECT id FROM employees WHERE unit_id = ?', (unit_id,)).fetchall()
    ]
    if employee_ids:
        connection.execute(
            f"DELETE FROM employee_portal_audit WHERE employee_id IN ({','.join(['?'] * len(employee_ids))})",
            tuple(employee_ids)
        )
        connection.execute(
            f"DELETE FROM employee_portal_links WHERE employee_id IN ({','.join(['?'] * len(employee_ids))})",
            tuple(employee_ids)
        )
        connection.execute(
            f"DELETE FROM users WHERE linked_employee_id IN ({','.join(['?'] * len(employee_ids))})",
            tuple(employee_ids)
        )
        connection.execute(
            f"DELETE FROM employees WHERE id IN ({','.join(['?'] * len(employee_ids))})",
            tuple(employee_ids)
        )


# ── Route-level SQL extractions ───────────────────────────────────────────────

def create_unit(connection, company_id, name, unit_type, city, notes):
    cursor = connection.execute(
        'INSERT INTO units (company_id, name, unit_type, city, notes) VALUES (?, ?, ?, ?, ?)',
        (company_id, name, unit_type, city, notes)
    )
    return cursor.lastrowid


def update_unit(connection, unit_id, company_id, name, unit_type, city, notes):
    connection.execute(
        'UPDATE units SET company_id = ?, name = ?, unit_type = ?, city = ?, notes = ? WHERE id = ?',
        (company_id, name, unit_type, city, notes, int(unit_id))
    )


def delete_unit(connection, unit_id):
    connection.execute('DELETE FROM units WHERE id = ?', (int(unit_id),))


def start_unit_jv(connection, company_id, unit_id, jv_name, started_at, actor_id):
    connection.execute(
        'INSERT INTO unit_joint_venture_periods (company_id, unit_id, joint_venture_name, started_at, created_by) '
        'VALUES (?, ?, ?, ?, ?)',
        (int(company_id), int(unit_id), jv_name, started_at, str(actor_id))
    )


def end_unit_jv(connection, unit_id, ended_at):
    connection.execute(
        'UPDATE unit_joint_venture_periods SET ended_at = ? WHERE unit_id = ? AND ended_at IS NULL',
        (ended_at, int(unit_id))
    )
