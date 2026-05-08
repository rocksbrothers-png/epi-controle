def authenticate_login(
    connection,
    username,
    password,
    *,
    structured_log,
    msg_login_failed,
    msg_user_not_found,
    verify_password,
    normalize_role_name,
    is_bcrypt_hash,
    hash_password,
    enforce_company_block_rules,
    row_to_dict,
    actor_operational_unit_id,
    permissions,
    create_jwt_token,
    jwt_exp_seconds,
):
    normalized_username = str(username or '').strip()
    provided_password = str(password or '')
    if not normalized_username or not provided_password.strip():
        raise ValueError('Usuário e senha são obrigatórios.')

    structured_log('info', 'auth.login_attempt', username=normalized_username)

    row = connection.execute(
        '''
        SELECT users.id, users.username, users.password, users.full_name, users.role, users.company_id, users.active, users.linked_employee_id,
               companies.name AS company_name, companies.cnpj AS company_cnpj, companies.logo_type
        FROM users
        LEFT JOIN companies ON companies.id = users.company_id
        WHERE LOWER(users.username) = LOWER(?)
        LIMIT 1
        ''',
        (normalized_username,)
    ).fetchone()

    if not row:
        structured_log('warning', msg_login_failed, username=normalized_username, reason='user_not_found')
        return None, 401, {'error': msg_user_not_found, 'code': 'USER_NOT_FOUND'}

    if int(row['active']) != 1:
        structured_log('warning', 'auth.login_failed', username=normalized_username, user_id=row['id'], reason='user_inactive')
        return None, 403, {'error': 'Usuário inativo.', 'code': 'USER_INACTIVE'}

    if not verify_password(row['password'], provided_password):
        structured_log('warning', 'auth.login_failed', username=normalized_username, user_id=row['id'], reason='invalid_password')
        return None, 401, {'error': 'Senha incorreta.', 'code': 'INVALID_PASSWORD'}

    resolved_role = normalize_role_name(row.get('role'))
    if resolved_role == 'employee':
        structured_log('warning', 'auth.login_blocked', username=normalized_username, user_id=row['id'], reason='employee_external_only')
        return None, 403, {'error': 'Funcionário não pode acessar o sistema interno.', 'code': 'EMPLOYEE_EXTERNAL_ONLY'}

    if not is_bcrypt_hash(row['password']):
        connection.execute('UPDATE users SET password = ? WHERE id = ?', (hash_password(provided_password), row['id']))
        connection.commit()

    if resolved_role != 'master_admin' and row.get('company_id'):
        enforce_company_block_rules(connection, int(row['company_id']))

    user_data = row_to_dict(row)
    user_data['role'] = resolved_role
    user_data.pop('password', None)
    operational_unit_id = actor_operational_unit_id(connection, user_data)
    if operational_unit_id:
        user_data['operational_unit_id'] = operational_unit_id
    structured_log('info', 'auth.login_success', username=row['username'], user_id=row['id'], role=resolved_role)
    return {
        'user': user_data,
        'permissions': sorted(permissions.get(resolved_role, set())),
        'token': create_jwt_token(user_data),
        'token_expires_in': jwt_exp_seconds
    }, 200, None
