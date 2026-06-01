"""Serviço de autenticação sem DI."""

import os
import traceback as _traceback
from urllib.parse import parse_qs
from core.repository import enforce_company_block_rules
from modules.employees.service import actor_operational_unit_id
from core.auth import ensure_permission, ensure_company_access
from core.roles import normalize_role_name
from core.security import (
    JWT_EXP_SECONDS,
    create_jwt_token,
    hash_password,
    is_bcrypt_hash,
    verify_password,
)
from core.meta import set_meta
from core.permissions import PERMISSIONS, PERMISSIONS as _PERMISSIONS
from epi_backend.db import row_to_dict
from epi_backend.http_utils import structured_log

INITIAL_MASTER_ADMIN_USERNAME = os.environ.get('INITIAL_MASTER_USERNAME', 'admin')
INITIAL_MASTER_ADMIN_PASSWORD = os.environ.get('INITIAL_MASTER_PASSWORD', 'admin123')
if not INITIAL_MASTER_ADMIN_PASSWORD:
    raise ValueError('INITIAL_MASTER_PASSWORD não definido. Configure a variável de ambiente.')
INITIAL_MASTER_ADMIN = {
    'username': INITIAL_MASTER_ADMIN_USERNAME,
    'password': INITIAL_MASTER_ADMIN_PASSWORD,
    'full_name': 'Administrador Master',
}

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
        'users.active, users.linked_employee_id, '
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


def _bootstrap_error_summary(exc):
    stack_lines = _traceback.format_exception(type(exc), exc, exc.__traceback__, limit=4)
    return ''.join(stack_lines).strip()


def _safe_bootstrap_section(section_name, loader, fallback, warnings, actor, path='/api/bootstrap'):
    try:
        return loader()
    except Exception as exc:
        warning = {
            'section': section_name,
            'message': str(exc),
            'type': type(exc).__name__,
        }
        warnings.append(warning)
        from epi_backend.http_utils import structured_log
        structured_log(
            'error',
            'bootstrap.section_failed',
            actor_user_id=actor.get('id'),
            user_role=actor.get('role'),
            company_id=actor.get('company_id'),
            path=path,
            section=section_name,
            error=str(exc),
            error_type=type(exc).__name__,
            stack=_bootstrap_error_summary(exc),
        )
        return fallback() if callable(fallback) else fallback


def build_bootstrap(connection, actor):
    from modules.settings.service import canary_evaluate_visibility_dataset
    from modules.units.service import fetch_units
    from modules.employees.service import fetch_employees, fetch_employee_movements
    from modules.epis.service import fetch_epis
    from modules.deliveries.service import fetch_deliveries
    from modules.feedback.service import fetch_feedbacks
    from modules.commercial.service import get_platform_brand, get_commercial_settings
    from modules.companies.service import fetch_companies, fetch_company_audit_logs
    from modules.ficha.service import fetch_ficha_epi_audit_logs
    from modules.alerts.service import compute_alerts as _compute_alerts_impl
    from modules.employees.service import actor_operational_unit_id as _actor_op_unit_id
    from modules.stock.service import fetch_low_stock_items as _fetch_low_stock
    from epi_backend.epi_scope import is_epi_visible_for_unit as _is_epi_visible
    from core.repository import get_unit_active_jv_name as _get_unit_jv_name

    def compute_alerts(connection, actor):
        return _compute_alerts_impl(
            connection,
            actor,
            fetch_low_stock_items=lambda conn, act: _fetch_low_stock(
                conn, act,
                actor_operational_unit_id=_actor_op_unit_id,
                get_unit_active_jv_name=_get_unit_jv_name,
                is_epi_visible_for_unit=_is_epi_visible,
            ),
            actor_operational_unit_id=_actor_op_unit_id,
            fetch_epis=fetch_epis,
        )

    warnings = []
    permissions = sorted(_PERMISSIONS.get(actor['role'], set()))

    units = _safe_bootstrap_section('units', lambda: fetch_units(connection, actor), [], warnings, actor)
    employees = _safe_bootstrap_section('employees', lambda: fetch_employees(connection, actor), [], warnings, actor)
    epis = _safe_bootstrap_section('epis', lambda: fetch_epis(connection, actor), [], warnings, actor)

    units = _safe_bootstrap_section(
        'units_visibility_canary',
        lambda: canary_evaluate_visibility_dataset(connection, actor, endpoint_name='/api/bootstrap', dataset_name='units', legacy_items=units),
        units, warnings, actor,
    )
    employees = _safe_bootstrap_section(
        'employees_visibility_canary',
        lambda: canary_evaluate_visibility_dataset(connection, actor, endpoint_name='/api/bootstrap', dataset_name='employees', legacy_items=employees),
        employees, warnings, actor,
    )
    epis = _safe_bootstrap_section(
        'epis_visibility_canary',
        lambda: canary_evaluate_visibility_dataset(connection, actor, endpoint_name='/api/bootstrap', dataset_name='epis', legacy_items=epis),
        epis, warnings, actor,
    )

    payload = {
        'ok': True,
        'user': {
            'id': actor.get('id'),
            'username': actor.get('username'),
            'full_name': actor.get('full_name'),
            'role': actor.get('role'),
            'company_id': actor.get('company_id'),
            'company_name': actor.get('company_name'),
            'company_cnpj': actor.get('company_cnpj'),
            'operational_unit_id': actor.get('operational_unit_id'),
        },
        'company': {
            'id': actor.get('company_id'),
            'name': actor.get('company_name'),
            'cnpj': actor.get('company_cnpj'),
        } if actor.get('company_id') else None,
        'permissions': permissions,
        'platform_brand': _safe_bootstrap_section('platform_brand', lambda: get_platform_brand(connection), {}, warnings, actor),
        'commercial_settings': _safe_bootstrap_section(
            'commercial_settings',
            lambda: get_commercial_settings(connection) if actor['role'] == 'master_admin' else None,
            None, warnings, actor,
        ),
        'companies': _safe_bootstrap_section('companies', lambda: fetch_companies(connection, None if actor['role'] == 'master_admin' else actor['company_id']), [], warnings, actor),
        'company_audit_logs': _safe_bootstrap_section('company_audit_logs', lambda: fetch_company_audit_logs(connection, actor), [], warnings, actor),
        'ficha_audit_logs': _safe_bootstrap_section('ficha_audit_logs', lambda: fetch_ficha_epi_audit_logs(connection, actor, {}), [], warnings, actor),
        'users': _safe_bootstrap_section('users', lambda: fetch_users(connection, actor), [], warnings, actor),
        'units': units,
        'employees': employees,
        'employee_movements': _safe_bootstrap_section('employee_movements', lambda: fetch_employee_movements(connection, actor), [], warnings, actor),
        'epis': epis,
        'deliveries': _safe_bootstrap_section('deliveries', lambda: fetch_deliveries(connection, actor), [], warnings, actor),
        'feedbacks': _safe_bootstrap_section('feedbacks', lambda: fetch_feedbacks(connection, actor), [], warnings, actor),
        'alerts': _safe_bootstrap_section('alerts', lambda: compute_alerts(connection, actor), [], warnings, actor),
        'bootstrap_warnings': warnings,
        'degraded': bool(warnings),
    }
    return payload


def auth_diagnostics():
    from epi_backend.config import (
        DATABASE_URL as _DB_URL,
        DB_CONNECTOR_AVAILABLE as _DB_AVAIL,
        BCRYPT_AVAILABLE as _BCRYPT,
        JWT_EXP_SECONDS as _JWT_EXP,
        JWT_SECRET as _JWT_SECRET,
        PASSWORD_RECOVERY_KEY as _PWD_KEY,
    )
    from core.schema import _get_migration_runtime_state
    from urllib.parse import urlparse
    parsed_db = urlparse(_DB_URL) if _DB_URL else None
    host = parsed_db.hostname if parsed_db else ''
    migration_state = _get_migration_runtime_state()
    migration_state_public = {
        'status': migration_state.get('status', 'not_started'),
        'failed_migration': migration_state.get('failed_migration', ''),
        'applied_count': len(migration_state.get('applied') or []),
    }
    return {
        'database_configured': bool(_DB_URL),
        'database_host': host,
        'database_provider': 'supabase' if 'supabase' in str(host).lower() else 'custom_postgres',
        'db_connector_available': _DB_AVAIL,
        'bcrypt_available': _BCRYPT,
        'jwt_exp_seconds': _JWT_EXP,
        'jwt_secret_default': _JWT_SECRET == 'change-this-jwt-secret',
        'password_recovery_key_configured': bool(_PWD_KEY),
        'migration_runner': migration_state_public,
    }


def static_asset_diagnostics():
    from pathlib import Path
    import hashlib as _hashlib
    base_dir = Path(__file__).resolve().parent.parent / 'static'
    index_path = base_dir / 'index.html'
    app_path = base_dir / 'app.js'

    def digest(path):
        if not path.exists():
            return ''
        return _hashlib.sha256(path.read_bytes()).hexdigest()

    def line_count(path):
        if not path.exists():
            return 0
        return path.read_text(encoding='utf-8', errors='ignore').count('\n') + 1

    return {
        'index_html_sha256': digest(index_path),
        'index_html_bytes': index_path.stat().st_size if index_path.exists() else 0,
        'app_js_sha256': digest(app_path),
        'app_js_bytes': app_path.stat().st_size if app_path.exists() else 0,
        'app_js_lines': line_count(app_path),
    }


def ensure_initial_master_admin(connection):
    admin_user = None
    try:
        admin_user = connection.execute(
            'SELECT id, username, full_name, password FROM users WHERE username = ? LIMIT 1',
            (INITIAL_MASTER_ADMIN['username'],),
        ).fetchone()
    except Exception as _e:
        structured_log('warning', 'db.col_skip', error=str(_e))
    if admin_user:
        password_to_store = admin_user['password']
        if not is_bcrypt_hash(password_to_store):
            password_to_store = hash_password(password_to_store)
        try:
            connection.execute(
                "UPDATE users SET password = ?, full_name = ?, role = 'master_admin', company_id = NULL, active = 1 WHERE id = ?",
                (password_to_store, INITIAL_MASTER_ADMIN['full_name'], admin_user['id']),
            )
        except Exception as _e:
            structured_log('warning', 'db.col_skip', error=str(_e))
        set_meta(connection, 'initial_master_admin_bootstrapped', str(admin_user['id']))
        return {'id': admin_user['id'], **INITIAL_MASTER_ADMIN}

    cursor = None
    try:
        cursor = connection.execute(
            'INSERT INTO users (username, password, full_name, role, company_id, active) VALUES (?, ?, ?, ?, ?, ?)',
            (
                INITIAL_MASTER_ADMIN['username'],
                hash_password(INITIAL_MASTER_ADMIN['password']),
                INITIAL_MASTER_ADMIN['full_name'],
                'master_admin',
                None,
                1,
            ),
        )
    except Exception as _e:
        structured_log('warning', 'db.col_skip', error=str(_e))
    set_meta(connection, 'initial_master_admin_bootstrapped', str(cursor.lastrowid))
    return {'id': cursor.lastrowid, **INITIAL_MASTER_ADMIN}


# ── Route-level SQL extractions ───────────────────────────────────────────────

def get_user_by_username(connection, username):
    row = connection.execute(
        'SELECT id FROM users WHERE LOWER(username) = LOWER(?) LIMIT 1',
        (username,)
    ).fetchone()
    return dict(row) if row else None


def update_user_password(connection, user_id, hashed_password):
    connection.execute(
        'UPDATE users SET password = ? WHERE id = ?',
        (hashed_password, int(user_id))
    )
