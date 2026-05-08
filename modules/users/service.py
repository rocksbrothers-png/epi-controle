import secrets as _secrets

def create_user(connection, payload, *,
    resolve_actor_user_id, authorize_user_management, normalize_role_name, role_weight,
    hash_password, resolve_target_company_id, resolve_user_employee_link,
    ensure_operational_role_link, ensure_company_user_limit, build_employee_access_token):
    actor_user_id = resolve_actor_user_id()
    actor = authorize_user_management(connection, actor_user_id, 'create', payload['role'], None, payload.get('company_id'))

    role = normalize_role_name(payload.get('role', ''))
    if role not in role_weight:
        raise ValueError('Perfil de usuário inválido.')
    if role == 'employee' and actor['role'] not in ('master_admin', 'general_admin', 'registry_admin'):
        raise PermissionError('Somente Master, Geral e Registro podem criar perfil Funcionário.')

    raw_password = str(payload.get('password') or '').strip()
    password = hash_password(raw_password if raw_password else _secrets.token_urlsafe(16))
    company_id = resolve_target_company_id(actor, payload.get('company_id'), role, payload.get('linked_employee_id'))
    allow_manual_link = actor['role'] in ('master_admin', 'general_admin')
    linked_employee_id, company_id = resolve_user_employee_link(
        connection, actor, payload, company_id,
        allow_manual_create=allow_manual_link and str(payload.get('linked_employee_id', '')).strip() == ''
    )
    ensure_operational_role_link(connection, role, linked_employee_id, company_id)
    if company_id and int(payload.get('active', 1)) == 1:
        ensure_company_user_limit(connection, company_id)

    employee_access_token = build_employee_access_token() if role == 'employee' else ''
    connection.execute(
        'INSERT INTO users (username, password, full_name, role, company_id, active, linked_employee_id, employee_access_token, employee_access_expires_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
        (str(payload.get('username', '')).strip(), password, str(payload.get('full_name', '')).strip(), role, company_id, int(payload.get('active', 1) or 1), linked_employee_id, employee_access_token, '')
    )
    connection.commit()


def update_user(connection, user_id, payload, *, resolve_actor_user_id, authorize_user_management, get_user_by_id,
    hash_password, is_bcrypt_hash, normalize_role_name, role_weight, resolve_target_company_id, resolve_user_employee_link,
    ensure_operational_role_link, ensure_company_user_limit, build_employee_access_token, sql_update_user):
    actor = authorize_user_management(connection, resolve_actor_user_id(), 'update', payload['role'], user_id, payload.get('company_id'))
    current = get_user_by_id(connection, user_id)
    if not current:
        raise ValueError('Usuário não encontrado.')
    incoming_password = str(payload.get('password') or '').strip()
    if incoming_password:
        password = hash_password(incoming_password)
    elif is_bcrypt_hash(current['password']):
        password = current['password']
    else:
        password = hash_password(current['password'])
    role = normalize_role_name(payload.get('role', ''))
    if role not in role_weight:
        raise ValueError('Perfil de usuário inválido.')
    if role == 'employee' and actor['role'] not in ('master_admin', 'general_admin', 'registry_admin'):
        raise PermissionError('Somente Master, Geral e Registro podem criar perfil Funcionário.')
    allow_manual_link = actor['role'] in ('master_admin', 'general_admin')
    linked_value = payload.get('linked_employee_id', current.get('linked_employee_id'))
    company_id = resolve_target_company_id(actor, payload.get('company_id'), role, linked_value)
    payload_for_link = {**payload, 'linked_employee_id': linked_value}
    linked_employee_id, company_id = resolve_user_employee_link(connection, actor, payload_for_link, company_id,
        allow_manual_create=allow_manual_link and str(linked_value or '').strip() == '')
    ensure_operational_role_link(connection, role, linked_employee_id, company_id)
    if company_id and int(payload.get('active', 1)) == 1:
        ensure_company_user_limit(connection, int(company_id), ignore_user_id=user_id)
    employee_access_token = str(current.get('employee_access_token') or '')
    if role == 'employee' and not employee_access_token:
        employee_access_token = build_employee_access_token()
    if role != 'employee':
        employee_access_token = ''
    employee_access_expires_at = str(current.get('employee_access_expires_at') or '') if role == 'employee' else ''
    connection.execute(sql_update_user, (str(payload.get('username', '')).strip(), password, str(payload.get('full_name', '')).strip(), role, company_id, int(payload.get('active', 1)), linked_employee_id, employee_access_token, employee_access_expires_at, user_id))
    connection.commit()


def delete_user(connection, user_id, *, resolve_actor_user_id, authorize_user_management):
    actor_user_id = resolve_actor_user_id()
    authorize_user_management(connection, actor_user_id, 'delete', None, user_id, None)
    if actor_user_id == user_id:
        raise ValueError('Não é permitido excluir o próprio usuário logado.')
    connection.execute('DELETE FROM users WHERE id = ?', (user_id,))
    connection.commit()
