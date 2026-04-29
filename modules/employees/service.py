# extracted employee services

def create_employee(connection, payload, *, authorize_action, resolve_actor_user_id, get_unit_by_id, ensure_resource_company, normalize_cpf, ensure_employee_identity_unique, normalize_preferred_contact_channel):
    actor = authorize_action(connection, resolve_actor_user_id(), 'employees:create', int(payload['company_id']))
    if str(payload.get('unit_id', '')).strip():
        unit = get_unit_by_id(connection, int(payload['unit_id']))
    else:
        unit = connection.execute('SELECT id, company_id, name, unit_type, city, notes FROM units WHERE company_id = ? ORDER BY id LIMIT 1', (int(payload['company_id']),)).fetchone()
        if not unit:
            default_unit_name = f"Unidade Padrão {int(payload['company_id'])}"
            unit_cursor = connection.execute('INSERT INTO units (company_id, name, unit_type, city, notes) VALUES (?, ?, ?, ?, ?)', (int(payload['company_id']), default_unit_name, 'base', 'Não informado', 'Unidade criada automaticamente no cadastro do colaborador.'))
            unit = connection.execute('SELECT id, company_id, name, unit_type, city, notes FROM units WHERE id = ?', (int(unit_cursor.lastrowid),)).fetchone()
    ensure_resource_company(actor, unit, 'Unidade')
    if str(unit['company_id']) != str(payload['company_id']):
        raise ValueError('Unidade e empresa do colaborador precisam ser compatíveis.')
    cpf_digits = normalize_cpf(payload.get('cpf'))
    ensure_employee_identity_unique(connection, int(payload['company_id']), payload['employee_id_code'], cpf_digits)
    preferred_channel = normalize_preferred_contact_channel(payload.get('preferred_contact_channel'))
    cursor = connection.execute('INSERT INTO employees (company_id, unit_id, employee_id_code, cpf, name, email, whatsapp, preferred_contact_channel, sector, role_name, admission_date, schedule_type) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', (payload['company_id'], unit['id'], payload['employee_id_code'], cpf_digits, payload['name'], str(payload.get('email') or '').strip().lower(), ''.join(ch for ch in str(payload.get('whatsapp') or '') if ch.isdigit()), preferred_channel, payload['sector'], payload['role_name'], payload['admission_date'], payload['schedule_type']))
    connection.commit()
    return int(cursor.lastrowid)


def update_employee(connection, employee_id, payload, *, authorize_action, resolve_actor_user_id, get_employee_by_id, get_unit_by_id, ensure_resource_company, normalize_cpf, ensure_employee_identity_unique, normalize_preferred_contact_channel, sql_update_employee):
    actor = authorize_action(connection, resolve_actor_user_id(), 'employees:update', int(payload['company_id']))
    current = get_employee_by_id(connection, employee_id)
    ensure_resource_company(actor, current, 'Colaborador')
    unit = get_unit_by_id(connection, int(payload['unit_id']))
    ensure_resource_company(actor, unit, 'Unidade')
    if str(unit['company_id']) != str(payload['company_id']):
        raise ValueError('Unidade e empresa do colaborador precisam ser compatíveis.')
    cpf_digits = normalize_cpf(payload.get('cpf'))
    ensure_employee_identity_unique(connection, int(payload['company_id']), payload['employee_id_code'], cpf_digits, exclude_id=employee_id)
    preferred_channel = normalize_preferred_contact_channel(payload.get('preferred_contact_channel'))
    connection.execute(sql_update_employee, (payload['company_id'], payload['unit_id'], payload['employee_id_code'], cpf_digits, payload['name'], str(payload.get('email') or '').strip().lower(), ''.join(ch for ch in str(payload.get('whatsapp') or '') if ch.isdigit()), preferred_channel, payload['sector'], payload['role_name'], payload['admission_date'], payload['schedule_type'], employee_id))
    connection.commit()
