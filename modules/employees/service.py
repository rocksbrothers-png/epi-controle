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
    from core.archival import NON_OPERATIONAL_STATUSES, lifecycle_enabled
    lifecycle = lifecycle_enabled(connection, 'employees')
    status_field = ', employees.status' if lifecycle else ''
    sql = (
        'SELECT employees.id, employees.company_id, employees.unit_id, '
        'employees.employee_id_code, employees.cpf, employees.name, employees.email, '
        'employees.whatsapp, employees.preferred_contact_channel, employees.sector, '
        'employees.role_name, employees.admission_date, employees.schedule_type, '
        f'employees.tipo_vinculo, employees.empresa_origem{status_field}, '
        'companies.name AS company_name, companies.cnpj AS company_cnpj, '
        'companies.logo_type, units.name AS unit_name, units.unit_type, '
        'units.city AS unit_city '
        'FROM employees '
        'JOIN companies ON companies.id = employees.company_id '
        'JOIN units ON units.id = employees.unit_id'
    )
    where = []
    params = []
    if lifecycle:
        placeholders = ', '.join(['?'] * len(NON_OPERATIONAL_STATUSES))
        where.append(f'employees.status NOT IN ({placeholders})')
        params.extend(NON_OPERATIONAL_STATUSES)
    if actor and actor['role'] != 'master_admin':
        where.append('employees.company_id = ?')
        params.append(actor['company_id'])
    if where:
        sql += ' WHERE ' + ' AND '.join(where)
    rows = connection.execute(sql + ' ORDER BY employees.name', tuple(params)).fetchall()
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


# ── Arquivamento (Soft Delete) com retenção — mesma política das Unidades ────

def get_employee_lifecycle(connection, employee_id):
    """Colaborador com os campos de ciclo de vida (para fluxos de arquivo)."""
    from core.archival import LIFECYCLE_FIELD_NAMES, lifecycle_enabled
    extra = (', ' + ', '.join(LIFECYCLE_FIELD_NAMES)) if lifecycle_enabled(connection, 'employees') else ''
    row = connection.execute(
        f'SELECT id, company_id, unit_id, employee_id_code, cpf, name{extra} '
        'FROM employees WHERE id = ?',
        (int(employee_id),),
    ).fetchone()
    return row_to_dict(row) if row else None


def ensure_employee_operational(connection, employee_id, operation='esta operação'):
    from core.archival import ensure_record_operational
    ensure_record_operational(connection, 'employees', employee_id, 'Colaborador', operation)


def fetch_archived_employees(connection, actor):
    """Colaboradores arquivados do tenant, com dados de retenção para a UI."""
    from core.archival import STATUS_ARCHIVED, STATUS_PENDING_DELETION, retention_days_remaining
    sql = (
        'SELECT employees.id, employees.company_id, employees.unit_id, '
        'employees.employee_id_code, employees.name, employees.sector, employees.role_name, '
        'employees.status, employees.archived_at, employees.archived_by, '
        'employees.archive_reason, employees.retention_until, employees.legal_hold, '
        'companies.name AS company_name, units.name AS unit_name, '
        'users.full_name AS archived_by_name '
        'FROM employees '
        'JOIN companies ON companies.id = employees.company_id '
        'LEFT JOIN units ON units.id = employees.unit_id '
        'LEFT JOIN users ON users.id = employees.archived_by '
        'WHERE employees.status IN (?, ?)'
    )
    params = [STATUS_ARCHIVED, STATUS_PENDING_DELETION]
    if actor and actor['role'] != 'master_admin':
        sql += ' AND employees.company_id = ?'
        params.append(actor['company_id'])
    rows = connection.execute(sql + ' ORDER BY employees.archived_at DESC', tuple(params)).fetchall()
    result = []
    for row in rows:
        item = row_to_dict(row)
        item['retention_days_remaining'] = retention_days_remaining(item.get('retention_until'))
        result.append(item)
    return result


def summarize_employee_history(connection, employee_id):
    """Resumo do que será removido na exclusão definitiva do colaborador."""
    from core.archival import count_where
    employee_id = int(employee_id)
    return {
        'deliveries': count_where(connection, 'deliveries', 'employee_id = ?', (employee_id,)),
        'devolutions': count_where(connection, 'epi_devolutions', 'employee_id = ?', (employee_id,)),
        'epi_requests': count_where(connection, 'epi_requests', 'employee_id = ?', (employee_id,)),
        'feedbacks': count_where(connection, 'epi_feedbacks', 'employee_id = ?', (employee_id,)),
        'ficha_periods': count_where(connection, 'epi_ficha_periods', 'employee_id = ?', (employee_id,)),
        'ficha_items': count_where(connection, 'epi_ficha_items', 'employee_id = ?', (employee_id,)),
        'unit_movements': count_where(connection, 'employee_unit_movements', 'employee_id = ?', (employee_id,)),
        'portal_links': count_where(connection, 'employee_portal_links', 'employee_id = ?', (employee_id,)),
        'portal_audit_logs': count_where(connection, 'employee_portal_audit_logs', 'employee_id = ?', (employee_id,)),
    }


def purge_employee_history(connection, employee_id):
    """Expurga os dados operacionais do colaborador (tombstone permanece).

    Chamado apenas pela etapa 2 da exclusão definitiva, após a retenção.
    """
    from core.archival import delete_where
    employee_id = int(employee_id)
    request_ids = [
        int(row['id'])
        for row in connection.execute(
            'SELECT id FROM epi_requests WHERE employee_id = ?', (employee_id,)
        ).fetchall()
    ]
    if request_ids:
        placeholders = ','.join(['?'] * len(request_ids))
        delete_where(connection, 'epi_request_history', f'request_id IN ({placeholders})', tuple(request_ids))
    feedback_ids = [
        int(row['id'])
        for row in connection.execute(
            'SELECT id FROM epi_feedbacks WHERE employee_id = ?', (employee_id,)
        ).fetchall()
    ]
    if feedback_ids:
        placeholders = ','.join(['?'] * len(feedback_ids))
        delete_where(connection, 'epi_feedback_history', f'feedback_id IN ({placeholders})', tuple(feedback_ids))
    for table in (
        'epi_requests', 'epi_feedbacks', 'epi_devolutions', 'deliveries',
        'epi_ficha_items', 'epi_ficha_periods', 'ficha_epi_snapshots',
        'ficha_epi_audit_log', 'employee_unit_movements',
        'employee_portal_audit_logs', 'employee_portal_links',
        'purchase_role_unit_links',
    ):
        delete_where(connection, table, 'employee_id = ?', (employee_id,))
    delete_where(connection, 'users', 'linked_employee_id = ?', (employee_id,))
