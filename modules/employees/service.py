"""Serviços de gestão de colaboradores."""

from epi_backend.http_utils import structured_log
from epi_backend.db import row_to_dict
from core.auth import ensure_resource_company

_SQL_UPDATE_EMPLOYEE = (
    "UPDATE employees SET company_id = ?, unit_id = ?, employee_id_code = ?, cpf = ?, name = ?, "
    "email = ?, whatsapp = ?, preferred_contact_channel = ?, "
    "sector = ?, role_name = ?, admission_date = ?, schedule_type = ?, tipo_vinculo = ?, empresa_origem = ? "
    "WHERE id = ?"
)


def normalize_cpf(value):
    digits = ''.join(ch for ch in str(value or '') if ch.isdigit())
    if len(digits) != 11:
        raise ValueError('CPF do colaborador deve conter 11 dígitos.')
    return digits


def normalize_preferred_contact_channel(value):
    normalized = str(value or '').strip().lower()
    return normalized if normalized in ('whatsapp', 'email') else 'whatsapp'


def ensure_employee_identity_unique(connection, company_id, employee_id_code, cpf, exclude_id=None):
    try:
        code_row = connection.execute(
            f"SELECT id FROM employees WHERE company_id = ? AND employee_id_code = ? {'AND id <> ?' if exclude_id else ''} LIMIT 1",
            (int(company_id), str(employee_id_code).strip(), int(exclude_id)) if exclude_id else (int(company_id), str(employee_id_code).strip())
        ).fetchone()
    except Exception as _e:
        structured_log('warning', 'db.col_skip', error=str(_e))
        code_row = None
    if code_row:
        raise ValueError('ID do colaborador já cadastrado nesta empresa.')
    try:
        cpf_row = connection.execute(
            f"SELECT id FROM employees WHERE company_id = ? AND cpf = ? {'AND id <> ?' if exclude_id else ''} LIMIT 1",
            (int(company_id), normalize_cpf(cpf), int(exclude_id)) if exclude_id else (int(company_id), normalize_cpf(cpf))
        ).fetchone()
    except Exception as _e:
        structured_log('warning', 'db.col_skip', error=str(_e))
        cpf_row = None
    if cpf_row:
        raise ValueError('CPF do colaborador já cadastrado nesta empresa.')


def create_employee(connection, payload, *, actor):
    from core.auth import ensure_resource_company
    from core.repository import get_unit_by_id

    if str(payload.get('unit_id', '')).strip():
        unit = get_unit_by_id(connection, int(payload['unit_id']))
    else:
        unit = connection.execute(
            'SELECT id, company_id, name, unit_type, city, notes FROM units WHERE company_id = ? ORDER BY id LIMIT 1',
            (int(payload['company_id']),)
        ).fetchone()
        if not unit:
            default_unit_name = f"Unidade Padrão {int(payload['company_id'])}"
            unit_cursor = connection.execute(
                'INSERT INTO units (company_id, name, unit_type, city, notes) VALUES (?, ?, ?, ?, ?)',
                (int(payload['company_id']), default_unit_name, 'base', 'Não informado', 'Unidade criada automaticamente no cadastro do colaborador.')
            )
            unit = connection.execute(
                'SELECT id, company_id, name, unit_type, city, notes FROM units WHERE id = ?',
                (int(unit_cursor.lastrowid),)
            ).fetchone()
    ensure_resource_company(actor, unit, 'Unidade')
    from modules.units.service import ensure_unit_operational
    ensure_unit_operational(connection, unit['id'], 'novos colaboradores')
    if str(unit['company_id']) != str(payload['company_id']):
        raise ValueError('Unidade e empresa do colaborador precisam ser compatíveis.')
    cpf_digits = normalize_cpf(payload.get('cpf'))
    ensure_employee_identity_unique(connection, int(payload['company_id']), payload['employee_id_code'], cpf_digits)
    preferred_channel = normalize_preferred_contact_channel(payload.get('preferred_contact_channel'))
    tipo_vinculo = str(payload.get('tipo_vinculo') or 'CLT').strip() or 'CLT'
    empresa_origem = str(payload.get('empresa_origem') or '').strip() if tipo_vinculo != 'CLT' else ''
    cursor = connection.execute(
        'INSERT INTO employees (company_id, unit_id, employee_id_code, cpf, name, email, whatsapp, '
        'preferred_contact_channel, sector, role_name, admission_date, schedule_type, tipo_vinculo, empresa_origem) '
        'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
        (
            payload['company_id'],
            unit['id'],
            payload['employee_id_code'],
            cpf_digits,
            payload['name'],
            str(payload.get('email') or '').strip().lower(),
            ''.join(ch for ch in str(payload.get('whatsapp') or '') if ch.isdigit()),
            preferred_channel,
            payload['sector'],
            payload['role_name'],
            payload['admission_date'],
            payload['schedule_type'],
            tipo_vinculo,
            empresa_origem,
        )
    )
    connection.commit()
    return int(cursor.lastrowid)


def update_employee(connection, employee_id, payload, *, actor):
    from core.auth import ensure_resource_company
    from core.repository import get_employee_by_id, get_unit_by_id

    current = get_employee_by_id(connection, employee_id)
    ensure_resource_company(actor, current, 'Colaborador')
    unit = get_unit_by_id(connection, int(payload['unit_id']))
    ensure_resource_company(actor, unit, 'Unidade')
    if int(unit['id']) != int(current.get('unit_id') or 0):
        # Só bloqueia transferência PARA unidade arquivada; editar cadastro de
        # colaborador que já está em unidade arquivada continua permitido.
        from modules.units.service import ensure_unit_operational
        ensure_unit_operational(connection, unit['id'], 'transferência de colaboradores')
    if str(unit['company_id']) != str(payload['company_id']):
        raise ValueError('Unidade e empresa do colaborador precisam ser compatíveis.')
    cpf_digits = normalize_cpf(payload.get('cpf'))
    ensure_employee_identity_unique(connection, int(payload['company_id']), payload['employee_id_code'], cpf_digits, exclude_id=employee_id)
    preferred_channel = normalize_preferred_contact_channel(payload.get('preferred_contact_channel'))
    tipo_vinculo = str(payload.get('tipo_vinculo') or 'CLT').strip() or 'CLT'
    empresa_origem = str(payload.get('empresa_origem') or '').strip() if tipo_vinculo != 'CLT' else ''
    connection.execute(
        _SQL_UPDATE_EMPLOYEE,
        (
            payload['company_id'],
            payload['unit_id'],
            payload['employee_id_code'],
            cpf_digits,
            payload['name'],
            str(payload.get('email') or '').strip().lower(),
            ''.join(ch for ch in str(payload.get('whatsapp') or '') if ch.isdigit()),
            preferred_channel,
            payload['sector'],
            payload['role_name'],
            payload['admission_date'],
            payload['schedule_type'],
            tipo_vinculo,
            empresa_origem,
            employee_id,
        )
    )
    connection.commit()


def get_employee_by_id(connection, employee_id):
    row = connection.execute(
        'SELECT id, company_id, unit_id, employee_id_code, cpf, name, email, whatsapp, '
        'preferred_contact_channel, sector, role_name, admission_date, schedule_type, '
        'tipo_vinculo, empresa_origem FROM employees WHERE id = ?',
        (employee_id,),
    ).fetchone()
    return row_to_dict(row) if row else None


def get_employee_current_unit(connection, employee_id):
    from datetime import date
    employee = get_employee_by_id(connection, int(employee_id))
    if not employee:
        return None
    today_iso = date.today().isoformat()
    movement = connection.execute(
        '''
        SELECT target_unit_id
        FROM employee_unit_movements
        WHERE employee_id = ?
          AND movement_type = 'temporary'
          AND start_date <= ?
          AND COALESCE(NULLIF(end_date, ''), '9999-12-31') >= ?
        ORDER BY start_date DESC, id DESC
        LIMIT 1
        ''',
        (int(employee_id), today_iso, today_iso),
    ).fetchone()
    return int(movement['target_unit_id']) if movement else int(employee['unit_id'])


def actor_operational_unit_id(connection, actor):
    if not actor or actor.get('role') not in ('admin', 'user'):
        return None
    linked_employee_id = actor.get('linked_employee_id')
    if not linked_employee_id:
        return None
    return get_employee_current_unit(connection, int(linked_employee_id))


def ensure_actor_employee_scope(connection, actor, employee):
    ensure_resource_company(actor, employee, 'Colaborador')
    scope_unit_id = actor_operational_unit_id(connection, actor)
    if actor.get('role') in ('admin', 'user') and not scope_unit_id:
        raise PermissionError('Seu perfil não possui unidade operacional ativa.')
    if scope_unit_id:
        employee_unit_id = get_employee_current_unit(connection, int(employee['id']))
        if int(employee_unit_id) != int(scope_unit_id):
            raise PermissionError('Operação permitida somente para colaboradores da sua unidade operacional.')


def active_temporary_unit_allocations(connection, today_iso=None):
    """Mapa {employee_id: {'unit_id', 'unit_name'}} das movimentações temporárias
    ativas hoje, numa única query (evita N+1 ao enriquecer listas)."""
    from datetime import date
    today_iso = today_iso or date.today().isoformat()
    rows = connection.execute(
        'SELECT m.employee_id, m.target_unit_id, u.name AS target_unit_name '
        'FROM employee_unit_movements m JOIN units u ON u.id = m.target_unit_id '
        "WHERE m.movement_type = 'temporary' AND m.start_date <= ? "
        "AND COALESCE(NULLIF(m.end_date, ''), '9999-12-31') >= ? "
        'ORDER BY m.start_date DESC, m.id DESC',
        (today_iso, today_iso),
    ).fetchall()
    allocations = {}
    for row in rows:
        item = row_to_dict(row)
        eid = int(item['employee_id'])
        if eid not in allocations:  # ordenado DESC -> primeiro é o mais recente
            allocations[eid] = {
                'unit_id': int(item['target_unit_id']),
                'unit_name': item.get('target_unit_name'),
            }
    return allocations


def apply_current_unit_allocation(connection, employees):
    """Acrescenta current_unit_id / current_unit_name / unit_allocation_type
    a cada colaborador, refletindo movimentações temporárias ativas.

    Corrige a tabela de colaboradores, que lia esses campos mas nunca os recebia
    do bootstrap — exibindo a unidade-base mesmo durante transferências."""
    allocations = active_temporary_unit_allocations(connection)
    for emp in employees or []:
        alloc = allocations.get(int(emp['id']))
        if alloc:
            emp['current_unit_id'] = alloc['unit_id']
            emp['current_unit_name'] = alloc['unit_name']
            emp['unit_allocation_type'] = 'temporary'
        else:
            emp['current_unit_id'] = int(emp['unit_id']) if emp.get('unit_id') is not None else None
            emp['current_unit_name'] = emp.get('unit_name')
            emp['unit_allocation_type'] = 'definitive'
    return employees


def fetch_employees(connection, actor=None):
    sql = (
        'SELECT employees.id, employees.company_id, employees.unit_id, '
        'employees.employee_id_code, employees.cpf, employees.name, employees.email, '
        'employees.whatsapp, employees.preferred_contact_channel, employees.sector, '
        'employees.role_name, employees.admission_date, employees.schedule_type, '
        'employees.tipo_vinculo, employees.empresa_origem, '
        'companies.name AS company_name, companies.cnpj AS company_cnpj, '
        'companies.logo_type, units.name AS unit_name, units.unit_type, '
        'units.city AS unit_city '
        'FROM employees '
        'JOIN companies ON companies.id = employees.company_id '
        'JOIN units ON units.id = employees.unit_id'
    )
    if actor and actor['role'] != 'master_admin':
        rows = connection.execute(
            sql + ' WHERE employees.company_id = ? ORDER BY employees.name',
            (actor['company_id'],),
        ).fetchall()
    else:
        rows = connection.execute(sql + ' ORDER BY employees.name').fetchall()
    employees = [row_to_dict(row) for row in rows]
    return apply_current_unit_allocation(connection, employees)


def fetch_employee_movements(connection, actor=None):
    sql = (
        'SELECT employee_unit_movements.*, '
        'employees.name AS employee_name, employees.employee_id_code, '
        'units.name AS unit_name, companies.name AS company_name '
        'FROM employee_unit_movements '
        'JOIN employees ON employees.id = employee_unit_movements.employee_id '
        'JOIN units ON units.id = employee_unit_movements.target_unit_id '
        'JOIN companies ON companies.id = employees.company_id'
    )
    if actor and actor['role'] != 'master_admin':
        rows = connection.execute(
            sql + ' WHERE employees.company_id = ? ORDER BY employee_unit_movements.start_date DESC',
            (actor['company_id'],),
        ).fetchall()
    else:
        rows = connection.execute(
            sql + ' ORDER BY employee_unit_movements.start_date DESC'
        ).fetchall()
    return [row_to_dict(row) for row in rows]


# ── Route-level SQL extractions ───────────────────────────────────────────────

def delete_employee(connection, employee_id):
    connection.execute('DELETE FROM employees WHERE id = ?', (int(employee_id),))


def close_temporary_unit_movements(connection, employee_id, start_date):
    connection.execute(
        "UPDATE employee_unit_movements SET end_date = ? WHERE employee_id = ? AND movement_type = 'temporary' AND COALESCE(NULLIF(end_date, ''), '9999-12-31') >= ?",
        (start_date, employee_id, start_date)
    )


def create_employee_unit_movement(connection, employee_id, company_id, source_unit_id, target_unit_id,
                                   movement_type, start_date, end_date, notes, actor_user_id, actor_name, created_at):
    connection.execute(
        (
            'INSERT INTO employee_unit_movements ('
            'employee_id, company_id, source_unit_id, target_unit_id, '
            'movement_type, start_date, end_date, notes, '
            'actor_user_id, actor_name, created_at'
            ') VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'
        ),
        (employee_id, company_id, source_unit_id, target_unit_id,
         movement_type, start_date, end_date, notes, actor_user_id, actor_name, created_at)
    )


def update_employee_unit(connection, employee_id, unit_id):
    connection.execute(
        'UPDATE employees SET unit_id = ? WHERE id = ?',
        (int(unit_id), int(employee_id))
    )
