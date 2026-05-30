"""Serviço de autenticação sem DI."""

from urllib.parse import parse_qs
from core.repository import actor_operational_unit_id, enforce_company_block_rules
from core.auth import ensure_permission, ensure_company_access
from core.roles import normalize_role_name
from core.security import (
    JWT_EXP_SECONDS,
    create_jwt_token,
    hash_password,
    is_bcrypt_hash,
    verify_password,
)
from core.permissions import PERMISSIONS
from epi_backend.db import row_to_dict
from epi_backend.http_utils import structured_log

MSG_LOGIN_FAILED = 'auth.login_failed'
MSG_USER_NOT_FOUND = 'Usuário não encontrado.'


def authenticate_login(connection, username, password):
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
        structured_log('warning', MSG_LOGIN_FAILED, username=normalized_username, reason='user_not_found')
        return None, 401, {'error': MSG_USER_NOT_FOUND, 'code': 'USER_NOT_FOUND'}

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
        'permissions': sorted(PERMISSIONS.get(resolved_role, set())),
        'token': create_jwt_token(user_data),
        'token_expires_in': JWT_EXP_SECONDS
    }, 200, None


def get_user_by_id(connection, user_id):
    row = connection.execute(
        'SELECT users.id, users.username, users.password, users.full_name, users.role, '
        'users.company_id, users.active, users.linked_employee_id, '
        'users.employee_access_token, users.employee_access_expires_at, '
        'companies.name AS company_name, companies.cnpj AS company_cnpj, companies.logo_type '
        'FROM users LEFT JOIN companies ON companies.id = users.company_id '
        'WHERE users.id = ?',
        (user_id,),
    ).fetchone()
    if not row:
        return None
    item = row_to_dict(row)
    item['role'] = normalize_role_name(item.get('role'))
    from modules.employees.service import actor_operational_unit_id as _emp_op_unit_id
    operational_unit_id = _emp_op_unit_id(connection, item)
    if operational_unit_id:
        item['operational_unit_id'] = operational_unit_id
    return item


def fetch_users(connection, actor=None):
    sql = (
        'SELECT users.id, users.username, users.full_name, users.role, users.company_id, '
        'users.active, users.linked_employee_id, users.employee_access_token, '
        'users.employee_access_expires_at, '
        'companies.name AS company_name, companies.cnpj AS company_cnpj '
        'FROM users LEFT JOIN companies ON companies.id = users.company_id'
    )
    if actor and actor['role'] != 'master_admin':
        rows = connection.execute(
            sql + ' WHERE users.company_id = ? ORDER BY users.full_name',
            (actor['company_id'],),
        ).fetchall()
    else:
        rows = connection.execute(sql + ' ORDER BY users.full_name').fetchall()
    return [row_to_dict(row) for row in rows]


def require_actor(connection, actor_user_id):
    actor = get_user_by_id(connection, int(actor_user_id))
    if not actor or not int(actor['active']):
        raise PermissionError('Usuário executor inválido.')
    actor['role'] = normalize_role_name(actor.get('role'))
    if actor.get('role') != 'master_admin' and actor.get('company_id'):
        from modules.companies.service import enforce_company_block_rules as _enforce_block
        _enforce_block(connection, int(actor['company_id']))
    return actor


def authorize_action(connection, actor_user_id, action, company_id=None):
    actor = require_actor(connection, actor_user_id)
    ensure_permission(actor, action)
    if company_id is not None:
        ensure_company_access(actor, company_id)
    return actor


def parse_actor_user_id_from_query(parsed):
    return int(parse_qs(parsed.query).get('actor_user_id', ['0'])[0])
