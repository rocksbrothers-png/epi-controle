from dotenv import load_dotenv
load_dotenv()

import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import threading
import time
import textwrap
from contextlib import closing
from datetime import date, datetime, timezone, timedelta
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

try:
    import bcrypt
    BCRYPT_AVAILABLE = True
except ModuleNotFoundError:
    bcrypt = None
    BCRYPT_AVAILABLE = False

try:
    import psycopg2
    from psycopg2 import pool as psycopg2_pool
    from psycopg2.extras import DictCursor
    DB_CONNECTOR_AVAILABLE = True
    DBIntegrityError = psycopg2.IntegrityError
except ModuleNotFoundError:
    psycopg2 = None
    psycopg2_pool = None
    DictCursor = None
    DB_CONNECTOR_AVAILABLE = False
    DBIntegrityError = Exception

BASE_DIR = Path(__file__).resolve().parent / "static"
UTC = timezone.utc
DATABASE_URL = os.environ.get('DATABASE_URL', '').strip()
DB_POOL_MINCONN = int(os.environ.get('DB_POOL_MINCONN', '1'))
DB_POOL_MAXCONN = int(os.environ.get('DB_POOL_MAXCONN', '10'))
PASSWORD_RECOVERY_KEY = os.environ.get('PASSWORD_RECOVERY_KEY', '').strip()
JWT_SECRET = os.environ.get('JWT_SECRET', '').strip() or PASSWORD_RECOVERY_KEY or 'change-this-jwt-secret'
JWT_EXP_SECONDS = int(os.environ.get('JWT_EXP_SECONDS', '28800'))
ROLE_WEIGHT = {'employee': 0, 'user': 1, 'admin': 2, 'registry_admin': 3, 'general_admin': 4, 'master_admin': 5}
BILLABLE_ROLES = ('general_admin', 'registry_admin', 'admin', 'user', 'employee')
PERM_DASHBOARD_VIEW = 'dashboard:view'
PERM_USERS_VIEW = 'users:view'
PERM_USERS_CREATE = 'users:create'
PERM_USERS_UPDATE = 'users:update'
PERM_USERS_DELETE = 'users:delete'
PERM_UNITS_VIEW = 'units:view'
PERM_UNITS_CREATE = 'units:create'
PERM_UNITS_UPDATE = 'units:update'
PERM_UNITS_DELETE = 'units:delete'
PERM_EMPLOYEES_VIEW = 'employees:view'
PERM_EMPLOYEES_CREATE = 'employees:create'
PERM_EMPLOYEES_UPDATE = 'employees:update'
PERM_EMPLOYEES_DELETE = 'employees:delete'
PERM_EPIS_VIEW = 'epis:view'
PERM_EPIS_CREATE = 'epis:create'
PERM_EPIS_UPDATE = 'epis:update'
PERM_EPIS_DELETE = 'epis:delete'
PERM_DELIVERIES_VIEW = 'deliveries:view'
PERM_DELIVERIES_CREATE = 'deliveries:create'
PERM_FICHAS_VIEW = 'fichas:view'
PERM_REPORTS_VIEW = 'reports:view'
PERM_ALERTS_VIEW = 'alerts:view'
PERM_COMPANIES_VIEW = 'companies:view'
PERM_COMPANIES_CREATE = 'companies:create'
PERM_COMPANIES_UPDATE = 'companies:update'
PERM_COMPANIES_LICENSE = 'companies:license'
PERM_COMMERCIAL_VIEW = 'commercial:view'
PERM_USAGE_VIEW = 'usage:view'
PERM_STOCK_VIEW = 'stock:view'
PERM_STOCK_ADJUST = 'stock:adjust'
PERM_EPI_VIEW_SELF = 'epi:view_self'
PERM_EPI_SIGN = 'epi:sign'

# Error/Status Message Constants
MSG_TOKEN_INVALID = 'Token inválido.'
MSG_TOKEN_ABSENT = 'Token ausente.'
MSG_TOKEN_EXPIRED_ACCESS = 'Token de acesso inválido ou expirado.'
MSG_EMPLOYEE_NOT_FOUND = 'Colaborador não encontrado.'
MSG_COMPANY_NOT_FOUND = 'Empresa não encontrada.'
MSG_UNIT_DUPLICATE = 'Já existe uma unidade com este nome nesta empresa.'
MSG_EPI_DUPLICATE = 'Já existe um EPI com este código de compra nesta empresa.'
MSG_EPI_INVALID = 'EPI inválido para avaliação.'
MSG_JOINVENTURE_INVALID = 'JoinVenture inválida.'
MSG_SIGNED_DIGITALLY = 'Assinado digitalmente'
MSG_LOGIN_FAILED = 'auth.login_failed'
MSG_USER_NOT_FOUND = 'Usuário não encontrado.'
MSG_REQUEST_PATH = '/api/requests'
MSG_PORTAL_LINK_REVOKE = '/api/employee-portal-link/revoke'
MSG_SELECT_EPIS_QUERY = '''
                        SELECT id, name, purchase_code, ca, unit_measure
                        FROM epis
                        WHERE company_id = ? AND active = 1
                        ORDER BY name ASC
                        '''
MSG_INSERT_UNITS = 'INSERT INTO units (company_id, name, unit_type, city, notes) VALUES (?, ?, ?, ?, ?)'
SQL_UPDATE_COMPANY = (
    "UPDATE companies SET "
    "name = ?, legal_name = ?, cnpj = ?, logo_type = ?, "
    "plan_name = ?, user_limit = ?, license_status = ?, active = ?, "
    "commercial_notes = ?, contract_start = ?, contract_end = ?, "
    "monthly_value = ?, addendum_enabled = ? "
    "WHERE id = ?"
)
SQL_UPDATE_USER = (
    "UPDATE users SET "
    "username = ?, password = ?, full_name = ?, role = ?, company_id = ?, active = ?, "
    "linked_employee_id = ?, employee_access_token = ?, employee_access_expires_at = ? "
    "WHERE id = ?"
)
SQL_UPDATE_EMPLOYEE = (
    "UPDATE employees SET company_id = ?, unit_id = ?, employee_id_code = ?, name = ?, "
    "sector = ?, role_name = ?, admission_date = ?, schedule_type = ? WHERE id = ?"
)

# Log Event Constants
LOG_HTTP_PERMISSION_ERROR = 'http.permission_error'
LOG_HTTP_VALUE_ERROR = 'http.value_error'
LOG_HTTP_UNHANDLED_ERROR = 'http.unhandled_error'
LOG_REDUNDANT_EXCEPTION = 'Remove this redundant Exception class'

# Company Names
COMPANY_DOF_BRASIL = 'DOF Brasil'
COMPANY_NORSKAN_OFFSHORE = 'Norskan Offshore'

ADMIN_BASE_PERMISSIONS = {
    PERM_DASHBOARD_VIEW, PERM_USERS_VIEW, PERM_USERS_CREATE, PERM_USERS_UPDATE, PERM_USERS_DELETE,
    PERM_UNITS_VIEW, PERM_UNITS_CREATE, PERM_UNITS_UPDATE, PERM_UNITS_DELETE,
    PERM_EMPLOYEES_VIEW, PERM_EMPLOYEES_CREATE, PERM_EMPLOYEES_UPDATE, PERM_EMPLOYEES_DELETE,
    PERM_EPIS_VIEW, PERM_EPIS_CREATE, PERM_EPIS_UPDATE, PERM_EPIS_DELETE,
    PERM_DELIVERIES_VIEW, PERM_FICHAS_VIEW, PERM_REPORTS_VIEW, PERM_ALERTS_VIEW, PERM_STOCK_VIEW
}
DELIVERY_WRITE_PERMISSIONS = {PERM_DELIVERIES_CREATE}
COMPANY_CORE_PERMISSIONS = {PERM_COMPANIES_VIEW}
COMPANY_MANAGEMENT_PERMISSIONS = {PERM_COMPANIES_CREATE, PERM_COMPANIES_UPDATE, PERM_COMPANIES_LICENSE}
COMMERCIAL_PERMISSIONS = {PERM_COMMERCIAL_VIEW, PERM_USAGE_VIEW}
STOCK_MANAGEMENT_PERMISSIONS = {PERM_STOCK_ADJUST}
PERMISSIONS = {
    'master_admin': ADMIN_BASE_PERMISSIONS | DELIVERY_WRITE_PERMISSIONS | COMPANY_CORE_PERMISSIONS | COMPANY_MANAGEMENT_PERMISSIONS | COMMERCIAL_PERMISSIONS | STOCK_MANAGEMENT_PERMISSIONS,
    'general_admin': ADMIN_BASE_PERMISSIONS | DELIVERY_WRITE_PERMISSIONS | COMPANY_CORE_PERMISSIONS | STOCK_MANAGEMENT_PERMISSIONS,
    'registry_admin': ADMIN_BASE_PERMISSIONS,
    'admin': {PERM_DASHBOARD_VIEW, PERM_USERS_VIEW, PERM_UNITS_VIEW, PERM_EMPLOYEES_VIEW, PERM_EMPLOYEES_UPDATE, PERM_EPIS_VIEW, PERM_DELIVERIES_VIEW, PERM_FICHAS_VIEW, PERM_REPORTS_VIEW, PERM_ALERTS_VIEW, PERM_STOCK_VIEW} | DELIVERY_WRITE_PERMISSIONS | STOCK_MANAGEMENT_PERMISSIONS,
    'user': {PERM_DASHBOARD_VIEW, PERM_DELIVERIES_VIEW, PERM_FICHAS_VIEW, PERM_ALERTS_VIEW, PERM_UNITS_VIEW, PERM_EMPLOYEES_VIEW, PERM_EPIS_VIEW, PERM_STOCK_VIEW} | DELIVERY_WRITE_PERMISSIONS | STOCK_MANAGEMENT_PERMISSIONS,
    'employee': {PERM_EPI_VIEW_SELF, PERM_EPI_SIGN}
}

_CONNECTION_POOL = None
_CONNECTION_POOL_LOCK = threading.Lock()


class PostgresCursorWrapper:
    def __init__(self, cursor, inserted_id=None):
        self._cursor = cursor
        self.lastrowid = inserted_id

    def fetchone(self):
        return self._cursor.fetchone()

    def fetchall(self):
        return self._cursor.fetchall()

    def __getattr__(self, name):
        return getattr(self._cursor, name)


class PostgresConnectionWrapper:
    def __init__(self, connection, release_hook=None):
        self._connection = connection
        self._release_hook = release_hook
        self._released = False

    def _normalize_sql(self, query):
        normalized = str(query)
        normalized = normalized.replace('INTEGER PRIMARY KEY AUTOINCREMENT', 'INTEGER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY')
        normalized = normalized.replace('?', '%s')
        return normalized

    def execute(self, query, params=None):
        sql = self._normalize_sql(query)
        cursor = self._connection.cursor(cursor_factory=DictCursor)
        inserted_id = None
        if sql.lstrip().upper().startswith('INSERT INTO ') and ' RETURNING ' not in sql.upper():
            returning_sql = sql.rstrip().rstrip(';') + ' RETURNING id'
            try:
                cursor.execute('SAVEPOINT sp_insert_returning_id')
                cursor.execute(returning_sql, params or ())
                row = cursor.fetchone()
                inserted_id = row[0] if row else None
                cursor.execute('RELEASE SAVEPOINT sp_insert_returning_id')
            except Exception as exc:
                message = str(exc).lower()
                if 'column "id" does not exist' not in message and 'undefinedcolumn' not in message:
                    raise
                cursor.execute('ROLLBACK TO SAVEPOINT sp_insert_returning_id')
                cursor.execute('RELEASE SAVEPOINT sp_insert_returning_id')
                cursor.execute(sql, params or ())
        else:
            cursor.execute(sql, params or ())
        return PostgresCursorWrapper(cursor, inserted_id)

    def executemany(self, query, seq_of_params):
        sql = self._normalize_sql(query)
        with self._connection.cursor() as cursor:
            cursor.executemany(sql, seq_of_params)

    def executescript(self, script):
        statements = [item.strip() for item in str(script).split(';') if item.strip()]
        with self._connection.cursor() as cursor:
            for statement in statements:
                cursor.execute(self._normalize_sql(statement))

    def cursor(self):
        return self._connection.cursor(cursor_factory=DictCursor)

    def commit(self):
        self._connection.commit()

    def rollback(self):
        self._connection.rollback()

    def close(self):
        if self._released:
            return
        self._released = True
        if self._release_hook:
            self._release_hook(self._connection)
            return
        self._connection.close()

    def __getattr__(self, name):
        return getattr(self._connection, name)


def get_connection_pool():
    global _CONNECTION_POOL
    if _CONNECTION_POOL:
        return _CONNECTION_POOL
    with _CONNECTION_POOL_LOCK:
        if _CONNECTION_POOL:
            return _CONNECTION_POOL
        if not DB_CONNECTOR_AVAILABLE:
            raise RuntimeError('Instale psycopg2-binary para usar o servidor Postgres/Supabase.')
        if not DATABASE_URL:
            raise RuntimeError('DATABASE_URL nao configurada.')
        _CONNECTION_POOL = psycopg2_pool.SimpleConnectionPool(DB_POOL_MINCONN, DB_POOL_MAXCONN, DATABASE_URL)
        structured_log('info', 'db.pool_initialized', minconn=DB_POOL_MINCONN, maxconn=DB_POOL_MAXCONN)
        return _CONNECTION_POOL


def release_connection(raw_connection):
    pool = get_connection_pool()
    pool.putconn(raw_connection)


def db_pool_status():
    pool = _CONNECTION_POOL
    if not pool:
        return {
            'enabled': DB_CONNECTOR_AVAILABLE and bool(DATABASE_URL),
            'initialized': False,
            'minconn': DB_POOL_MINCONN,
            'maxconn': DB_POOL_MAXCONN,
            'available': 0,
            'in_use': 0
        }
    available = len(getattr(pool, '_pool', []) or [])
    in_use = len(getattr(pool, '_used', {}) or {})
    return {
        'enabled': True,
        'initialized': True,
        'minconn': DB_POOL_MINCONN,
        'maxconn': DB_POOL_MAXCONN,
        'available': int(available),
        'in_use': int(in_use)
    }


def get_connection():
    if not DB_CONNECTOR_AVAILABLE:
        raise RuntimeError('Instale psycopg2-binary para usar o servidor Postgres/Supabase.')
    if not DATABASE_URL:
        raise RuntimeError('DATABASE_URL nao configurada.')
    pool = get_connection_pool()
    raw_connection = pool.getconn()
    return PostgresConnectionWrapper(raw_connection, release_hook=release_connection)


def row_to_dict(row):
    return {key: row[key] for key in row.keys()}


def _json_safe(value):
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    return str(value)


def structured_log(level, event, **fields):
    payload = {
        'ts': datetime.now(UTC).isoformat().replace('+00:00', 'Z'),
        'level': str(level).lower(),
        'event': event,
        **{key: _json_safe(value) for key, value in fields.items()}
    }
    print(json.dumps(payload, ensure_ascii=False), flush=True)


def send_json(handler, status, payload):
    body = json.dumps(payload, ensure_ascii=False).encode('utf-8')
    handler.send_response(status)
    handler.send_header('Content-Type', 'application/json; charset=utf-8')
    handler.send_header('Content-Length', str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)
    if str(handler.path).startswith('/api/') or str(handler.path).startswith('/health'):
        structured_log(
            'info' if status < 400 else 'error',
            'http.response',
            method=getattr(handler, 'command', ''),
            path=getattr(handler, 'path', ''),
            status=status
        )


def send_bytes(handler, status, content_type, body, filename=None):
    handler.send_response(status)
    handler.send_header('Content-Type', content_type)
    handler.send_header('Content-Length', str(len(body)))
    if filename:
        handler.send_header('Content-Disposition', f'attachment; filename="{filename}"')
    handler.end_headers()
    handler.wfile.write(body)


def parse_json(handler):
    length = int(handler.headers.get('Content-Length', '0'))
    raw = handler.rfile.read(length) if length else b'{}'
    return json.loads(raw.decode('utf-8'))


def require_fields(payload, fields):
    for field in fields:
        if payload.get(field) in (None, ''):
            raise ValueError(f'Campo obrigatório: {field}')

def validate_password_strength(password):
    raw = str(password or '').strip()
    if len(raw) < 6:
        raise ValueError('A senha deve ter pelo menos 6 caracteres.')
    return raw


def jwt_b64encode(data_bytes):
    return base64.urlsafe_b64encode(data_bytes).decode('utf-8').rstrip('=')


def jwt_b64decode(data):
    raw = str(data or '')
    padding = '=' * (-len(raw) % 4)
    return base64.urlsafe_b64decode((raw + padding).encode('utf-8'))


def create_jwt_token(user_row):
    now_ts = int(datetime.now(UTC).timestamp())
    payload = {
        'sub': int(user_row['id']),
        'role': user_row['role'],
        'company_id': user_row['company_id'],
        'iat': now_ts,
        'exp': now_ts + JWT_EXP_SECONDS
    }
    header_segment = jwt_b64encode(json.dumps({'alg': 'HS256', 'typ': 'JWT'}, separators=(',', ':')).encode('utf-8'))
    payload_segment = jwt_b64encode(json.dumps(payload, separators=(',', ':')).encode('utf-8'))
    signing_input = f'{header_segment}.{payload_segment}'.encode('utf-8')
    signature = hmac.new(JWT_SECRET.encode('utf-8'), signing_input, hashlib.sha256).digest()
    signature_segment = jwt_b64encode(signature)
    return f'{header_segment}.{payload_segment}.{signature_segment}'


def parse_bearer_token(handler):
    auth_header = str(handler.headers.get('Authorization', '')).strip()
    if not auth_header:
        return ''
    if not auth_header.lower().startswith('bearer '):
        raise PermissionError('Formato de Authorization inválido.')
    return auth_header.split(' ', 1)[1].strip()


def decode_jwt_token(token):
    raw = str(token or '').strip()
    if not raw:
        raise PermissionError(MSG_TOKEN_ABSENT)
    parts = raw.split('.')
    if len(parts) != 3:
        raise PermissionError(MSG_TOKEN_INVALID)
    header_segment, payload_segment, signature_segment = parts
    signing_input = f'{header_segment}.{payload_segment}'.encode('utf-8')
    expected_signature = hmac.new(JWT_SECRET.encode('utf-8'), signing_input, hashlib.sha256).digest()
    provided_signature = jwt_b64decode(signature_segment)
    if not hmac.compare_digest(expected_signature, provided_signature):
        raise PermissionError(MSG_TOKEN_INVALID)
    try:
        payload = json.loads(jwt_b64decode(payload_segment).decode('utf-8'))
    except json.JSONDecodeError:
        raise PermissionError(MSG_TOKEN_INVALID)
    if int(payload.get('exp', 0)) < int(datetime.now(UTC).timestamp()):
        raise PermissionError('Sessão expirada. Faça login novamente.')
    return payload


def resolve_actor_user_id(handler, parsed, payload=None):
    payload = payload or {}
    query_actor = parse_qs(parsed.query).get('actor_user_id', [''])[0]
    body_actor = str(payload.get('actor_user_id', '')).strip()
    token = parse_bearer_token(handler)
    token_actor = ''
    if token:
        claims = decode_jwt_token(token)
        token_actor = str(claims.get('sub', '')).strip()
    actor_candidates = [item for item in (body_actor, query_actor, token_actor) if str(item).strip()]
    if not actor_candidates:
        raise PermissionError('Sessão inválida: usuário não informado.')
    actor_user_id = actor_candidates[0]
    for candidate in actor_candidates[1:]:
        if str(candidate) != str(actor_user_id):
            raise PermissionError('Dados de autenticação inconsistentes.')
    return int(actor_user_id)


def is_bcrypt_hash(value):
    raw = str(value or '')
    return raw.startswith('$2a$') or raw.startswith('$2b$') or raw.startswith('$2y$')


def hash_password(password):
    raw = validate_password_strength(password)
    if not BCRYPT_AVAILABLE:
        return raw
    return bcrypt.hashpw(raw.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def verify_password(stored_password, provided_password):
    stored = str(stored_password or '')
    provided = str(provided_password or '')
    if is_bcrypt_hash(stored):
        if not BCRYPT_AVAILABLE:
            return False
        return bcrypt.checkpw(provided.encode('utf-8'), stored.encode('utf-8'))
    return stored == provided



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

    if row.get('role') == 'employee':
        structured_log('warning', 'auth.login_blocked', username=normalized_username, user_id=row['id'], reason='employee_external_only')
        return None, 403, {'error': 'Funcionário não pode acessar o sistema interno.', 'code': 'EMPLOYEE_EXTERNAL_ONLY'}

    if not is_bcrypt_hash(row['password']):
        connection.execute('UPDATE users SET password = ? WHERE id = ?', (hash_password(provided_password), row['id']))
        connection.commit()

    if row.get('role') != 'master_admin' and row.get('company_id'):
        enforce_company_block_rules(connection, int(row['company_id']))

    user_data = row_to_dict(row)
    user_data.pop('password', None)
    operational_unit_id = actor_operational_unit_id(connection, user_data)
    if operational_unit_id:
        user_data['operational_unit_id'] = operational_unit_id
    structured_log('info', 'auth.login_success', username=row['username'], user_id=row['id'], role=row['role'])
    return {
        'user': user_data,
        'permissions': sorted(PERMISSIONS.get(row['role'], set())),
        'token': create_jwt_token(row),
        'token_expires_in': JWT_EXP_SECONDS
    }, 200, None


def only_digits(value):
    return ''.join(ch for ch in str(value or '') if ch.isdigit())


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


def format_cnpj(value):
    digits = only_digits(value)
    if len(digits) != 14:
        return str(value or '').strip()
    return f"{digits[:2]}.{digits[2:5]}.{digits[5:8]}/{digits[8:12]}-{digits[12:]}"


def is_valid_cnpj(value):
    digits = only_digits(value)
    if len(digits) != 14 or len(set(digits)) == 1:
        return False

    numbers = [int(item) for item in digits]
    weights_one = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    total = sum(number * weight for number, weight in zip(numbers[:12], weights_one))
    remainder = total % 11
    digit_one = 0 if remainder < 2 else 11 - remainder

    weights_two = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    total = sum(number * weight for number, weight in zip(numbers[:12] + [digit_one], weights_two))
    remainder = total % 11
    digit_two = 0 if remainder < 2 else 11 - remainder
    return numbers[12] == digit_one and numbers[13] == digit_two


def validate_cnpj(value):
    if not is_valid_cnpj(value):
        raise ValueError('CNPJ inválido.')
    return format_cnpj(value)


def ensure_unique_company_cnpj(connection, cnpj, exclude_company_id=None):
    normalized = only_digits(cnpj)
    rows = connection.execute('SELECT id, cnpj FROM companies').fetchall()
    for row in rows:
        if exclude_company_id and int(row['id']) == int(exclude_company_id):
            continue
        if only_digits(row['cnpj']) == normalized:
            raise ValueError('Já existe uma empresa cadastrada com este CNPJ.')


def validate_logo_payload(value):
    logo = str(value or '').strip()
    if not logo:
        return ''
    if logo.startswith('data:image/'):
        allowed = ('data:image/png', 'data:image/jpeg', 'data:image/jpg', 'data:image/svg+xml')
        if not logo.startswith(allowed):
            raise ValueError('Logotipo inválido. Envie PNG, JPG ou SVG.')
    return logo


def validate_company_payload(connection, payload, company_id=None):
    settings = get_commercial_settings(connection)
    payload['name'] = str(payload.get('name', '')).strip()
    payload['legal_name'] = str(payload.get('legal_name', '')).strip()
    payload['cnpj'] = validate_cnpj(payload.get('cnpj', ''))
    ensure_unique_company_cnpj(connection, payload['cnpj'], company_id)
    payload['logo_type'] = validate_logo_payload(payload.get('logo_type', ''))
    payload['plan_name'] = normalize_plan_key(payload.get('plan_name') or 'start')
    if payload['plan_name'] not in settings['plans']:
        raise ValueError('Plano comercial invalido.')
    payload['commercial_notes'] = str(payload.get('commercial_notes', '')).strip()
    payload['user_limit'] = int(payload.get('user_limit', 0))
    if payload['user_limit'] < 1:
        raise ValueError('O limite de usuarios deve ser maior que zero.')
    payload['addendum_enabled'] = 1 if str(payload.get('addendum_enabled', '0')).lower() in ('1', 'true', 'on', 'yes') else 0
    plan = settings['plans'][payload['plan_name']]
    if payload['user_limit'] < plan['min_users']:
        raise ValueError(f"O plano {plan['label']} exige no minimo {plan['min_users']} usuario(s).")
    if plan['max_users'] is not None and payload['user_limit'] > plan['max_users'] and not payload['addendum_enabled']:
        raise ValueError(f"O plano {plan['label']} permite ate {plan['max_users']} usuarios sem aditivo contratual.")
    active_users = count_company_users(connection, company_id) if company_id else 0
    if active_users > payload['user_limit']:
        raise ValueError('O limite contratado nao pode ficar abaixo da quantidade atual de usuarios ativos.')
    payload['monthly_value'] = round(active_users * float(settings['unit_price']), 2)
    payload['contract_start'] = str(payload.get('contract_start', '')).strip()
    payload['contract_end'] = str(payload.get('contract_end', '')).strip()
    if payload['contract_start']:
        datetime.strptime(payload['contract_start'], '%Y-%m-%d')
    if payload['contract_end']:
        datetime.strptime(payload['contract_end'], '%Y-%m-%d')
    if payload['contract_start'] and payload['contract_end'] and payload['contract_end'] < payload['contract_start']:
        raise ValueError('A data final do contrato deve ser maior ou igual a data inicial.')
    payload['license_status'] = str(payload.get('license_status', 'active')).strip() or 'active'
    payload['unit_price'] = float(settings['unit_price'])
    payload['projected_monthly_value'] = round(payload['user_limit'] * payload['unit_price'], 2)
    return payload


def bad_request(handler, message):
    send_json(handler, 400, {'error': message})


def forbidden(handler, message):
    send_json(handler, 403, {'error': message})


def not_found(handler):
    send_json(handler, 404, {'error': 'Rota não encontrada.'})


def humanize_integrity_error(exc):
    message = str(exc or '')
    lowered = message.lower()
    if 'employees_employee_id_code_key' in lowered:
        return 'ID do colaborador já cadastrado para esta empresa.'
    if 'unique constraint failed: employees.employee_id_code' in lowered:
        return 'ID do colaborador já cadastrado. Use outro identificador para este colaborador.'
    if 'units_company_id_name_key' in lowered:
        return 'Já existe uma unidade com este nome nesta empresa.'
    if 'unique constraint failed: units.company_id, units.name' in lowered:
        return 'Já existe uma unidade com este nome nesta empresa.'
    if 'epis_company_id_purchase_code_key' in lowered:
        return 'Já existe um EPI com este código de compra nesta empresa.'
    if 'unique constraint failed: epis.company_id, epis.purchase_code' in lowered:
        return 'Já existe um EPI com este código de compra nesta empresa.'
    if 'unique constraint failed: epis.company_id, epis.ca' in lowered:
        return 'Já existe um EPI com este CA nesta empresa.'
    if 'units_company_id_name_key' in lowered:
        return 'Já existe uma unidade com este nome nesta empresa.'
    if 'epis_company_id_purchase_code_key' in lowered:
        return 'Já existe um EPI com este código de compra nesta empresa.'
    if 'epi_stock_items_company_id_qr_sequence_key' in lowered:
        return 'Conflito de sequência de QR no estoque. Tente novamente.'
    if 'epi_stock_items_company_id_qr_code_value_key' in lowered:
        return 'QR Code de item já existente no estoque.'
    if 'unique constraint failed: employee_portal_links.employee_id' in lowered:
        return 'Este colaborador já possui um link externo ativo.'
    if 'unique constraint failed: employee_portal_links.token' in lowered:
        return 'Falha ao gerar token de acesso externo. Tente novamente.'
    if 'unique constraint failed: employee_portal_links.qr_code_value' in lowered:
        return 'Falha ao gerar link externo único. Tente novamente.'

    if 'unique constraint' in lowered or 'duplicate key value' in lowered:
        return 'Registro duplicado: já existe um item com os mesmos identificadores.'
    return f'Erro de integridade: {message}'


def request_base_url(handler):
    forwarded_proto = str(handler.headers.get('X-Forwarded-Proto', '')).strip()
    scheme = forwarded_proto or ('https' if 'onrender.com' in str(handler.headers.get('Host', '')).lower() else 'http')
    host = str(handler.headers.get('Host', '')).strip()
    configured = str(os.environ.get('PUBLIC_BASE_URL', '')).strip()
    if configured:
        return configured.rstrip('/')
    return f'{scheme}://{host}'.rstrip('/')


INITIAL_MASTER_ADMIN_USERNAME = os.environ.get('INITIAL_MASTER_USERNAME', 'admin')
INITIAL_MASTER_ADMIN_PASSWORD = os.environ.get('INITIAL_MASTER_PASSWORD', 'admin123')
if not INITIAL_MASTER_ADMIN_PASSWORD:
    raise ValueError('INITIAL_MASTER_PASSWORD não definido. Configure a variável de ambiente.')
INITIAL_MASTER_ADMIN = {
    'username': INITIAL_MASTER_ADMIN_USERNAME,
    'password': INITIAL_MASTER_ADMIN_PASSWORD,
    'full_name': 'Administrador Master'
}
DEFAULT_PLATFORM_BRAND = {'display_name': 'Sua Empresa', 'legal_name': '', 'cnpj': '', 'logo_type': ''}
DEFAULT_COMMERCIAL_SETTINGS = {
    'unit_price': 42.0,
    'plans': {
        'individual': {'label': 'Individual', 'min_users': 1, 'max_users': 1},
        'start': {'label': 'Start', 'min_users': 1, 'max_users': 10},
        'business': {'label': 'Business', 'min_users': 11, 'max_users': 25},
        'corporate': {'label': 'Corporate', 'min_users': 26, 'max_users': 100},
        'enterprise': {'label': 'Enterprise', 'min_users': 101, 'max_users': None},
    },
}


def default_commercial_settings():
    return json.loads(json.dumps(DEFAULT_COMMERCIAL_SETTINGS))


def normalize_plan_key(value):
    normalized = str(value or '').strip().lower()
    aliases = {
        'individual': 'individual',
        'indivudual': 'individual',
        'start': 'start',
        'business': 'business',
        'corporate': 'corporate',
        'enterprise': 'enterprise',
    }
    return aliases.get(normalized, normalized)


def ensure_commercial_settings(connection):
    if not get_meta(connection, 'commercial_settings'):
        set_meta(connection, 'commercial_settings', json.dumps(default_commercial_settings(), ensure_ascii=False))


def get_commercial_settings(connection):
    settings = default_commercial_settings()
    raw = get_meta(connection, 'commercial_settings')
    if not raw:
        return settings
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return settings
    settings['unit_price'] = float(parsed.get('unit_price', settings['unit_price']) or settings['unit_price'])
    for key, plan in settings['plans'].items():
        source = (parsed.get('plans') or {}).get(key, {})
        plan['label'] = str(source.get('label', plan['label'])).strip() or plan['label']
        plan['min_users'] = max(1, int(source.get('min_users', plan['min_users']) or plan['min_users']))
        raw_max = source.get('max_users', plan['max_users'])
        plan['max_users'] = None if raw_max in (None, '', 'null') else max(plan['min_users'], int(raw_max))
    return settings


def save_commercial_settings(connection, payload):
    actor = require_master_actor(connection, int(payload.get('actor_user_id') or 0))
    current = get_commercial_settings(connection)
    unit_price = float(str(payload.get('unit_price', current['unit_price'])).replace(',', '.'))
    if unit_price <= 0:
        raise ValueError('O valor unitario precisa ser maior que zero.')
    plans_payload = payload.get('plans') or {}
    settings = default_commercial_settings()
    settings['unit_price'] = unit_price
    details = [{'field': 'Valor unitario', 'before': str(current['unit_price']), 'after': str(unit_price)}]
    for key, default_plan in settings['plans'].items():
        current_plan = current['plans'][key]
        source = plans_payload.get(key) or current_plan
        label = str(source.get('label', default_plan['label'])).strip() or default_plan['label']
        min_users = max(1, int(source.get('min_users', default_plan['min_users']) or default_plan['min_users']))
        raw_max = source.get('max_users', default_plan['max_users'])
        max_users = None if raw_max in (None, '', 'null') else max(min_users, int(raw_max))
        settings['plans'][key] = {'label': label, 'min_users': min_users, 'max_users': max_users}
        details.append({
            'field': f'Plano {label}',
            'before': f"min {current_plan['min_users']} / max {current_plan['max_users'] if current_plan['max_users'] is not None else 'livre'}",
            'after': f"min {min_users} / max {max_users if max_users is not None else 'livre'}"
        })
    if settings['plans']['individual']['max_users'] < 1:
        raise ValueError('O plano Individual precisa permitir pelo menos 1 usuario.')
    if settings['plans']['start']['max_users'] < settings['plans']['individual']['max_users']:
        raise ValueError('O limite do plano Start nao pode ser menor que o Individual.')
    if settings['plans']['business']['min_users'] > settings['plans']['business']['max_users']:
        raise ValueError('O plano Business esta com faixa invalida.')
    if settings['plans']['corporate']['min_users'] > settings['plans']['corporate']['max_users']:
        raise ValueError('O plano Corporate esta com faixa invalida.')
    if settings['plans']['enterprise']['min_users'] <= settings['plans']['corporate']['max_users']:
        raise ValueError('O plano Enterprise precisa comecar acima do limite do Corporate.')
    set_meta(connection, 'commercial_settings', json.dumps(settings, ensure_ascii=False))
    return actor, settings, details


def commercial_plan_for_company(company, settings):
    return settings['plans'].get(normalize_plan_key(company.get('plan_name')))


def compute_company_contract_metrics(company, settings):
    active_users = int(company.get('user_count') or 0)
    user_limit = int(company.get('user_limit') or 0)
    unit_price = float(settings['unit_price'])
    addendum_enabled = int(company.get('addendum_enabled') or 0)
    plan = commercial_plan_for_company(company, settings)
    min_users = plan['min_users'] if plan else 1
    max_users = plan['max_users'] if plan else None
    return {
        'unit_price': unit_price,
        'calculated_monthly_value': round(active_users * unit_price, 2),
        'projected_monthly_value': round(user_limit * unit_price, 2),
        'plan_min_users': min_users,
        'plan_max_users': max_users,
        'requires_addendum': bool(plan and max_users is not None and user_limit > max_users),
        'within_plan_limit': bool(plan and user_limit >= min_users and (max_users is None or user_limit <= max_users)),
        'addendum_enabled': addendum_enabled,
    }



def get_platform_brand(connection):
    raw = get_meta(connection, 'platform_brand')
    if not raw:
        return dict(DEFAULT_PLATFORM_BRAND)
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return dict(DEFAULT_PLATFORM_BRAND)
    return {**DEFAULT_PLATFORM_BRAND, **parsed}


def validate_platform_brand_payload(payload):
    brand = {
        'display_name': str(payload.get('display_name', '')).strip() or DEFAULT_PLATFORM_BRAND['display_name'],
        'legal_name': str(payload.get('legal_name', '')).strip(),
        'cnpj': str(payload.get('cnpj', '')).strip(),
        'logo_type': validate_logo_payload(payload.get('logo_type', ''))
    }
    if brand['cnpj']:
        brand['cnpj'] = validate_cnpj(brand['cnpj'])
    return brand


def save_platform_brand(connection, payload):
    brand = validate_platform_brand_payload(payload)
    set_meta(connection, 'platform_brand', json.dumps(brand, ensure_ascii=False))
    return brand


def require_master_actor(connection, actor_user_id):
    actor = authorize_action(connection, actor_user_id, 'commercial:view')
    if actor['role'] != 'master_admin':
        raise PermissionError('Apenas o Administrador Master pode alterar a marca do sistema.')
    return actor


def get_meta(connection, key):
    with connection.cursor() as cursor:
        cursor.execute(
            'SELECT value FROM app_meta WHERE key = %s',
            (key,)
        )
        row = cursor.fetchone()
        return row['value'] if row else None


def set_meta(connection, key, value):
    with connection.cursor() as cursor:
        cursor.execute(
            '''
            INSERT INTO app_meta (key, value)
            VALUES (%s, %s)
            ON CONFLICT (key)
            DO UPDATE SET value = EXCLUDED.value
            ''',
            (key, value)
        )


def migrate_role_hierarchy(connection):
    connection.execute("UPDATE users SET role = 'master_admin', company_id = NULL WHERE role = 'general_admin' AND company_id IS NULL")


def ensure_user_columns(connection):
    connection.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS linked_employee_id INTEGER")
    connection.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS employee_access_token TEXT")
    connection.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS employee_access_expires_at TEXT")


def ensure_delivery_signature_columns(connection):
    connection.execute("ALTER TABLE deliveries ADD COLUMN IF NOT EXISTS signature_ip TEXT NOT NULL DEFAULT ''")
    connection.execute("ALTER TABLE deliveries ADD COLUMN IF NOT EXISTS signature_at TEXT NOT NULL DEFAULT ''")
    connection.execute("ALTER TABLE deliveries ADD COLUMN IF NOT EXISTS signature_data TEXT NOT NULL DEFAULT ''")
    connection.execute("ALTER TABLE deliveries ADD COLUMN IF NOT EXISTS unit_id INTEGER")
    connection.execute("ALTER TABLE deliveries ADD COLUMN IF NOT EXISTS stock_movement_id INTEGER")


def ensure_stock_columns(connection):
    connection.execute("ALTER TABLE epis ADD COLUMN IF NOT EXISTS minimum_stock INTEGER NOT NULL DEFAULT 10")
    connection.execute(
        '''
        CREATE TABLE IF NOT EXISTS stock_movements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL,
            unit_id INTEGER NOT NULL,
            epi_id INTEGER NOT NULL,
            movement_type TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            previous_stock INTEGER NOT NULL,
            new_stock INTEGER NOT NULL,
            source_type TEXT NOT NULL DEFAULT '',
            source_id INTEGER,
            notes TEXT NOT NULL DEFAULT '',
            actor_user_id INTEGER NOT NULL,
            actor_name TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
            FOREIGN KEY (unit_id) REFERENCES units(id) ON DELETE RESTRICT,
            FOREIGN KEY (epi_id) REFERENCES epis(id) ON DELETE RESTRICT,
            FOREIGN KEY (actor_user_id) REFERENCES users(id) ON DELETE RESTRICT
        )
        '''
    )


def ensure_epi_operational_tables(connection):
    connection.execute(
        '''
        CREATE TABLE IF NOT EXISTS epi_qr_sequences (
            company_id INTEGER PRIMARY KEY,
            last_value INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE
        )
        '''
    )
    connection.execute(
        '''
        CREATE TABLE IF NOT EXISTS unit_epi_stock (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL,
            unit_id INTEGER NOT NULL,
            epi_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 0,
            updated_at TEXT NOT NULL,
            UNIQUE(company_id, unit_id, epi_id),
            FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
            FOREIGN KEY (unit_id) REFERENCES units(id) ON DELETE RESTRICT,
            FOREIGN KEY (epi_id) REFERENCES epis(id) ON DELETE RESTRICT
        )
        '''
    )
    connection.execute(
        '''
        CREATE TABLE IF NOT EXISTS epi_stock_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL,
            unit_id INTEGER NOT NULL,
            epi_id INTEGER NOT NULL,
            glove_size TEXT NOT NULL DEFAULT 'N/A',
            size TEXT NOT NULL DEFAULT 'N/A',
            uniform_size TEXT NOT NULL DEFAULT 'N/A',
            qr_sequence INTEGER NOT NULL,
            qr_code_value TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'in_stock',
            stock_movement_id INTEGER,
            delivery_id INTEGER,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(company_id, qr_sequence),
            UNIQUE(company_id, qr_code_value),
            FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
            FOREIGN KEY (unit_id) REFERENCES units(id) ON DELETE RESTRICT,
            FOREIGN KEY (epi_id) REFERENCES epis(id) ON DELETE RESTRICT,
            FOREIGN KEY (stock_movement_id) REFERENCES stock_movements(id) ON DELETE SET NULL,
            FOREIGN KEY (delivery_id) REFERENCES deliveries(id) ON DELETE SET NULL
        )
        '''
    )
    connection.execute("ALTER TABLE epi_stock_items ADD COLUMN IF NOT EXISTS glove_size TEXT NOT NULL DEFAULT 'N/A'")
    connection.execute("ALTER TABLE epi_stock_items ADD COLUMN IF NOT EXISTS size TEXT NOT NULL DEFAULT 'N/A'")
    connection.execute("ALTER TABLE epi_stock_items ADD COLUMN IF NOT EXISTS uniform_size TEXT NOT NULL DEFAULT 'N/A'")
    connection.execute(
        '''
        CREATE TABLE IF NOT EXISTS epi_ficha_periods (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL,
            employee_id INTEGER NOT NULL,
            unit_id INTEGER NOT NULL,
            schedule_type TEXT NOT NULL,
            period_start TEXT NOT NULL,
            period_end TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'open',
            batch_signature_name TEXT NOT NULL DEFAULT '',
            batch_signature_data TEXT NOT NULL DEFAULT '',
            batch_signature_ip TEXT NOT NULL DEFAULT '',
            batch_signature_at TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(employee_id, period_start, period_end),
            FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
            FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE,
            FOREIGN KEY (unit_id) REFERENCES units(id) ON DELETE RESTRICT
        )
        '''
    )
    connection.execute(
        '''
        CREATE TABLE IF NOT EXISTS epi_ficha_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ficha_period_id INTEGER NOT NULL,
            delivery_id INTEGER NOT NULL UNIQUE,
            company_id INTEGER NOT NULL,
            employee_id INTEGER NOT NULL,
            unit_id INTEGER NOT NULL,
            epi_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            item_signature_name TEXT NOT NULL DEFAULT '',
            item_signature_data TEXT NOT NULL DEFAULT '',
            item_signature_ip TEXT NOT NULL DEFAULT '',
            item_signature_at TEXT NOT NULL DEFAULT '',
            signed_mode TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (ficha_period_id) REFERENCES epi_ficha_periods(id) ON DELETE CASCADE,
            FOREIGN KEY (delivery_id) REFERENCES deliveries(id) ON DELETE CASCADE,
            FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
            FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE,
            FOREIGN KEY (unit_id) REFERENCES units(id) ON DELETE RESTRICT,
            FOREIGN KEY (epi_id) REFERENCES epis(id) ON DELETE RESTRICT
        )
        '''
    )
    connection.execute(
        '''
        CREATE TABLE IF NOT EXISTS employee_portal_links (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL,
            employee_id INTEGER NOT NULL UNIQUE,
            token TEXT NOT NULL UNIQUE,
            qr_code_value TEXT NOT NULL UNIQUE,
            active INTEGER NOT NULL DEFAULT 1,
            expires_at TEXT NOT NULL DEFAULT '',
            created_by_user_id INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
            FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE,
            FOREIGN KEY (created_by_user_id) REFERENCES users(id) ON DELETE RESTRICT
        )
        '''
    )
    connection.execute(
        '''
        CREATE TABLE IF NOT EXISTS epi_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL,
            unit_id INTEGER NOT NULL,
            employee_id INTEGER NOT NULL,
            epi_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 1,
            request_token TEXT NOT NULL,
            status TEXT NOT NULL,
            justification TEXT NOT NULL DEFAULT '',
            requested_at TEXT NOT NULL,
            requested_by TEXT NOT NULL DEFAULT 'employee',
            approver_user_id INTEGER,
            approver_name TEXT NOT NULL DEFAULT '',
            approved_at TEXT NOT NULL DEFAULT '',
            rejection_reason TEXT NOT NULL DEFAULT '',
            separated_by_user_id INTEGER,
            separated_at TEXT NOT NULL DEFAULT '',
            delivery_id INTEGER,
            last_updated_at TEXT NOT NULL,
            FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
            FOREIGN KEY (unit_id) REFERENCES units(id) ON DELETE RESTRICT,
            FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE,
            FOREIGN KEY (epi_id) REFERENCES epis(id) ON DELETE RESTRICT,
            FOREIGN KEY (approver_user_id) REFERENCES users(id) ON DELETE SET NULL,
            FOREIGN KEY (separated_by_user_id) REFERENCES users(id) ON DELETE SET NULL,
            FOREIGN KEY (delivery_id) REFERENCES deliveries(id) ON DELETE SET NULL
        )
        '''
    )
    connection.execute(
        '''
        CREATE TABLE IF NOT EXISTS epi_request_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            request_id INTEGER NOT NULL,
            company_id INTEGER NOT NULL,
            status TEXT NOT NULL,
            notes TEXT NOT NULL DEFAULT '',
            actor_user_id INTEGER,
            actor_name TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            FOREIGN KEY (request_id) REFERENCES epi_requests(id) ON DELETE CASCADE,
            FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
            FOREIGN KEY (actor_user_id) REFERENCES users(id) ON DELETE SET NULL
        )
        '''
    )
    connection.execute(
        '''
        CREATE TABLE IF NOT EXISTS epi_feedbacks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL,
            unit_id INTEGER NOT NULL,
            employee_id INTEGER NOT NULL,
            epi_id INTEGER,
            comfort_rating INTEGER NOT NULL DEFAULT 0,
            quality_rating INTEGER NOT NULL DEFAULT 0,
            adequacy_rating INTEGER NOT NULL DEFAULT 0,
            performance_rating INTEGER NOT NULL DEFAULT 0,
            comments TEXT NOT NULL DEFAULT '',
            improvement_suggestion TEXT NOT NULL DEFAULT '',
            suggested_new_epi_name TEXT NOT NULL DEFAULT '',
            suggested_new_epi_notes TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'pendente',
            request_token TEXT NOT NULL DEFAULT '',
            reviewer_user_id INTEGER,
            reviewer_name TEXT NOT NULL DEFAULT '',
            reviewed_at TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
            FOREIGN KEY (unit_id) REFERENCES units(id) ON DELETE RESTRICT,
            FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE,
            FOREIGN KEY (epi_id) REFERENCES epis(id) ON DELETE SET NULL,
            FOREIGN KEY (reviewer_user_id) REFERENCES users(id) ON DELETE SET NULL
        )
        '''
    )
    connection.execute(
        '''
        CREATE TABLE IF NOT EXISTS epi_feedback_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            feedback_id INTEGER NOT NULL,
            company_id INTEGER NOT NULL,
            status TEXT NOT NULL,
            notes TEXT NOT NULL DEFAULT '',
            actor_user_id INTEGER,
            actor_name TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            FOREIGN KEY (feedback_id) REFERENCES epi_feedbacks(id) ON DELETE CASCADE,
            FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
            FOREIGN KEY (actor_user_id) REFERENCES users(id) ON DELETE SET NULL
        )
        '''
    )
    connection.execute(
        '''
        CREATE TABLE IF NOT EXISTS employee_portal_audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL,
            employee_id INTEGER NOT NULL,
            portal_link_id INTEGER,
            token_hash TEXT NOT NULL,
            action TEXT NOT NULL,
            ip_address TEXT NOT NULL DEFAULT '',
            user_agent TEXT NOT NULL DEFAULT '',
            payload TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
            FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE,
            FOREIGN KEY (portal_link_id) REFERENCES employee_portal_links(id) ON DELETE SET NULL
        )
        '''
    )

    
def period_days_from_schedule(schedule_type):
    raw = str(schedule_type or '').strip().lower()
    if '14x14' in raw:
        return 14
    if '28x28' in raw:
        return 28
    if '30' in raw:
        return 30
    if '31' in raw:
        return 31
    return 30


def today_iso():
    return date.today().isoformat()


def ensure_company_columns(connection):
    migrations = [
        "ALTER TABLE companies ADD COLUMN IF NOT EXISTS legal_name TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE companies ADD COLUMN IF NOT EXISTS plan_name TEXT NOT NULL DEFAULT 'Plano padrao'",
        "ALTER TABLE companies ADD COLUMN IF NOT EXISTS user_limit INTEGER NOT NULL DEFAULT 25",
        "ALTER TABLE companies ADD COLUMN IF NOT EXISTS license_status TEXT NOT NULL DEFAULT 'active'",
        "ALTER TABLE companies ADD COLUMN IF NOT EXISTS active INTEGER NOT NULL DEFAULT 1",
        "ALTER TABLE companies ADD COLUMN IF NOT EXISTS commercial_notes TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE companies ADD COLUMN IF NOT EXISTS contract_start TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE companies ADD COLUMN IF NOT EXISTS contract_end TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE companies ADD COLUMN IF NOT EXISTS monthly_value REAL NOT NULL DEFAULT 0",
        "ALTER TABLE companies ADD COLUMN IF NOT EXISTS addendum_enabled INTEGER NOT NULL DEFAULT 0",
    ]
    for sql in migrations:
        connection.execute(sql)



def company_license_label(status):
    return {
        'active': 'Ativo',
        'trial': 'Trial',
        'suspended': 'Suspenso',
        'expired': 'Expirado',
    }.get(status, status)


def count_company_users(connection, company_id):
    placeholders = ','.join(['?'] * len(BILLABLE_ROLES))
    return connection.execute(
        f"SELECT COUNT(*) FROM users WHERE company_id = ? AND active = 1 AND role IN ({placeholders})",
        (company_id, *BILLABLE_ROLES)
    ).fetchone()[0]


def ensure_company_user_limit(connection, company_id, ignore_user_id=None):
    company = connection.execute('SELECT id, name, user_limit, active, license_status FROM companies WHERE id = ?', (company_id,)).fetchone()
    if not company:
        raise ValueError('Empresa não encontrada.')
    if not int(company['active']) or company['license_status'] in ('suspended', 'expired'):
        raise ValueError('Empresa sem licença ativa para novos usuários.')
    contract_end = connection.execute('SELECT contract_end FROM companies WHERE id = ?', (company_id,)).fetchone()['contract_end']
    if contract_end and contract_end < date.today().isoformat():
        raise ValueError('Contrato expirado para novos usuários.')
    placeholders = ','.join(['?'] * len(BILLABLE_ROLES))
    query = f'SELECT COUNT(*) FROM users WHERE company_id = ? AND active = 1 AND role IN ({placeholders})'
    params = [company_id, *BILLABLE_ROLES]
    if ignore_user_id:
        query += ' AND id != ?'
        params.append(ignore_user_id)
    active_users = connection.execute(query, tuple(params)).fetchone()[0]
    if active_users >= int(company['user_limit']):
        raise ValueError('Limite de usuários contratado atingido para esta empresa.')


def get_company_by_id(connection, company_id):
    row = connection.execute(
        'SELECT id, name, user_limit, license_status, active, contract_end, addendum_enabled FROM companies WHERE id = ?',
        (company_id,)
    ).fetchone()
    return row_to_dict(row) if row else None


def enforce_company_block_rules(connection, company_id):
    status = evaluate_company_block_status(connection, company_id, persist_expiration=True)
    if not status['blocked']:
        return
    reason_priority = status['reasons'][0]
    if reason_priority == 'company_inactive':
        raise PermissionError('Acesso bloqueado: empresa inativa.')
    if reason_priority in ('license_suspended', 'license_expired_by_contract'):
        raise PermissionError('Acesso bloqueado: licença suspensa ou expirada.')
    if reason_priority == 'usage_exceeds_contract':
        raise PermissionError('Acesso bloqueado: uso acima do limite contratado.')
    raise PermissionError('Acesso bloqueado por política comercial.')


def evaluate_company_block_status(connection, company_id, persist_expiration=True):
    company = get_company_by_id(connection, company_id)
    if not company:
        raise ValueError('Empresa vinculada não encontrada.')

    reasons = []
    today_iso = date.today().isoformat()
    contract_end = str(company.get('contract_end') or '').strip()
    license_status = str(company.get('license_status') or 'active').strip() or 'active'
    if contract_end and contract_end < today_iso:
        reasons.append('license_expired_by_contract')
        if persist_expiration and license_status != 'expired':
            connection.execute('UPDATE companies SET license_status = ? WHERE id = ?', ('expired', company_id))
            connection.commit()
            license_status = 'expired'
    if int(company.get('active') or 0) != 1:
        reasons.append('company_inactive')
    if license_status == 'suspended':
        reasons.append('license_suspended')
    if license_status == 'expired':
        reasons.append('license_expired_by_contract')
    active_users = count_company_users(connection, company_id)
    user_limit = int(company.get('user_limit') or 0)
    addendum_enabled = int(company.get('addendum_enabled') or 0) == 1
    if user_limit > 0 and active_users > user_limit and not addendum_enabled:
        reasons.append('usage_exceeds_contract')

    dedup_reasons = []
    for reason in reasons:
        if reason not in dedup_reasons:
            dedup_reasons.append(reason)
    return {
        'company_id': int(company_id),
        'blocked': bool(dedup_reasons),
        'reasons': dedup_reasons,
        'license_status': license_status,
        'active_users': active_users,
        'user_limit': user_limit,
        'addendum_enabled': addendum_enabled,
        'contract_end': contract_end,
    }

def ensure_initial_master_admin(connection):
    admin_user = connection.execute("SELECT id, username, full_name, password FROM users WHERE username = ? LIMIT 1", (INITIAL_MASTER_ADMIN['username'],)).fetchone()
    if admin_user:
        password_to_store = admin_user['password']
        if not is_bcrypt_hash(password_to_store):
            password_to_store = hash_password(password_to_store)
        connection.execute(
            "UPDATE users SET password = ?, full_name = ?, role = 'master_admin', company_id = NULL, active = 1 WHERE id = ?",
            (password_to_store, INITIAL_MASTER_ADMIN['full_name'], admin_user['id'])
        )
        set_meta(connection, 'initial_master_admin_bootstrapped', str(admin_user['id']))
        return {'id': admin_user['id'], **INITIAL_MASTER_ADMIN}

    cursor = connection.execute(
        'INSERT INTO users (username, password, full_name, role, company_id, active) VALUES (?, ?, ?, ?, ?, ?)',
        (INITIAL_MASTER_ADMIN['username'], hash_password(INITIAL_MASTER_ADMIN['password']), INITIAL_MASTER_ADMIN['full_name'], 'master_admin', None, 1)
    )
    set_meta(connection, 'initial_master_admin_bootstrapped', str(cursor.lastrowid))
    return {'id': cursor.lastrowid, **INITIAL_MASTER_ADMIN}


def init_db():
    retries = int(os.environ.get('DB_INIT_RETRIES', '8'))
    retry_delay = float(os.environ.get('DB_INIT_RETRY_DELAY_SECONDS', '2'))
    last_error = None
    connection = None
    for attempt in range(1, retries + 1):
        try:
            connection = get_connection()
            break
        except Exception as exc:
            last_error = exc
            structured_log('warning', 'db.connect_retry', attempt=attempt, retries=retries, error=str(exc))
            if attempt < retries:
                time.sleep(retry_delay)
    if not connection:
        raise RuntimeError(f'Falha ao conectar no banco após {retries} tentativas: {last_error}')

    with closing(connection) as connection:
        if isinstance(connection, PostgresConnectionWrapper):
            # Serializa migrações de startup entre múltiplos processos para evitar deadlock em ALTER TABLE.
            connection.execute('SELECT pg_advisory_lock(?)', (83492117,))
        connection.executescript(
            '''
            CREATE TABLE IF NOT EXISTS companies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                legal_name TEXT NOT NULL DEFAULT '',
                cnpj TEXT NOT NULL UNIQUE,
                logo_type TEXT NOT NULL,
                plan_name TEXT NOT NULL DEFAULT 'Plano padrão',
                user_limit INTEGER NOT NULL DEFAULT 25,
                license_status TEXT NOT NULL DEFAULT 'active',
                active INTEGER NOT NULL DEFAULT 1,
                commercial_notes TEXT NOT NULL DEFAULT '',
                contract_start TEXT NOT NULL DEFAULT '',
                contract_end TEXT NOT NULL DEFAULT '',
                monthly_value REAL NOT NULL DEFAULT 0,
                addendum_enabled INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS app_meta (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL,
                full_name TEXT NOT NULL,
                role TEXT NOT NULL,
                company_id INTEGER,
                active INTEGER NOT NULL DEFAULT 1,
                FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE SET NULL
            );
            CREATE TABLE IF NOT EXISTS company_audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                actor_user_id INTEGER NOT NULL,
                actor_name TEXT NOT NULL,
                action_type TEXT NOT NULL,
                summary TEXT NOT NULL,
                details_json TEXT NOT NULL DEFAULT '[]',
                created_at TEXT NOT NULL,
                FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
                FOREIGN KEY (actor_user_id) REFERENCES users(id) ON DELETE RESTRICT
            );
            CREATE TABLE IF NOT EXISTS units (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                unit_type TEXT NOT NULL,
                city TEXT NOT NULL,
                notes TEXT DEFAULT '',
                UNIQUE(company_id, name),
                FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE RESTRICT
            );
            CREATE TABLE IF NOT EXISTS employees (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                unit_id INTEGER NOT NULL,
                employee_id_code TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                sector TEXT NOT NULL,
                role_name TEXT NOT NULL,
                admission_date TEXT NOT NULL,
                schedule_type TEXT NOT NULL,
                FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE RESTRICT,
                FOREIGN KEY (unit_id) REFERENCES units(id) ON DELETE RESTRICT
            );
            CREATE TABLE IF NOT EXISTS epis (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                unit_id INTEGER,
                name TEXT NOT NULL,
                purchase_code TEXT NOT NULL,
                ca TEXT NOT NULL,
                sector TEXT NOT NULL,
                epi_section TEXT NOT NULL DEFAULT '',
                stock INTEGER NOT NULL DEFAULT 0,
                unit_measure TEXT NOT NULL,
                ca_expiry TEXT NOT NULL,
                epi_validity_date TEXT NOT NULL,
                manufacture_date TEXT NOT NULL,
                validity_days INTEGER NOT NULL,
                validity_years INTEGER NOT NULL DEFAULT 0,
                validity_months INTEGER NOT NULL DEFAULT 0,
                manufacturer_validity_months INTEGER NOT NULL DEFAULT 0,
                manufacturer TEXT NOT NULL DEFAULT '',
                model_reference TEXT NOT NULL DEFAULT '',
                supplier_company TEXT NOT NULL DEFAULT '',
                manufacturer_recommendations TEXT NOT NULL DEFAULT '',
                epi_photo_data TEXT,
                glove_size TEXT,
                size TEXT,
                uniform_size TEXT,
                manufacturer TEXT NOT NULL DEFAULT '',
                supplier_company TEXT NOT NULL DEFAULT '',
                joinventures_json TEXT NOT NULL DEFAULT '[]',
                active_joinventure TEXT,
                qr_code_value TEXT,
                UNIQUE(company_id, purchase_code),
                UNIQUE(company_id, ca),
                UNIQUE(company_id, qr_code_value),
                FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE RESTRICT,
                FOREIGN KEY (unit_id) REFERENCES units(id) ON DELETE RESTRICT
            );
            CREATE TABLE IF NOT EXISTS deliveries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                employee_id INTEGER NOT NULL,
                epi_id INTEGER NOT NULL,
                quantity INTEGER NOT NULL,
                quantity_label TEXT NOT NULL,
                sector TEXT NOT NULL,
                role_name TEXT NOT NULL,
                delivery_date TEXT NOT NULL,
                next_replacement_date TEXT NOT NULL,
                notes TEXT DEFAULT '',
                signature_name TEXT NOT NULL,
                FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE RESTRICT,
                FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE RESTRICT,
                FOREIGN KEY (epi_id) REFERENCES epis(id) ON DELETE RESTRICT
            );
            CREATE TABLE IF NOT EXISTS employee_unit_movements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id INTEGER NOT NULL,
                company_id INTEGER NOT NULL,
                source_unit_id INTEGER NOT NULL,
                target_unit_id INTEGER NOT NULL,
                movement_type TEXT NOT NULL,
                start_date TEXT NOT NULL,
                end_date TEXT NOT NULL DEFAULT '',
                notes TEXT NOT NULL DEFAULT '',
                actor_user_id INTEGER NOT NULL,
                actor_name TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE,
                FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
                FOREIGN KEY (source_unit_id) REFERENCES units(id) ON DELETE RESTRICT,
                FOREIGN KEY (target_unit_id) REFERENCES units(id) ON DELETE RESTRICT,
                FOREIGN KEY (actor_user_id) REFERENCES users(id) ON DELETE RESTRICT
            );
            '''
        )
        ensure_company_columns(connection)
        ensure_company_audit_columns(connection)
        ensure_epi_columns(connection)
        ensure_stock_columns(connection)
        ensure_epi_operational_tables(connection)
        ensure_commercial_settings(connection)
        ensure_user_columns(connection)
        ensure_delivery_signature_columns(connection)
        if connection.execute('SELECT COUNT(*) FROM companies').fetchone()[0] == 0:
            connection.executemany('INSERT INTO companies (name, legal_name, cnpj, logo_type, plan_name, user_limit, license_status, active, commercial_notes, contract_start, contract_end, monthly_value, addendum_enabled) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', [('DOF Brasil', 'DOF Subsea Brasil Servicos Ltda', '11.222.333/0001-81', '', 'enterprise', 120, 'active', 1, 'Contrato corporativo ativo.', '2026-01-01', '2026-12-31', 0.0, 0), ('Norskan Offshore', 'Norskan Offshore Ltda', '44.555.666/0001-81', '', 'corporate', 80, 'active', 1, 'Operacao offshore ativa.', '2026-01-01', '2026-12-31', 0.0, 0)])
        companies = {row['name']: row['id'] for row in connection.execute('SELECT id, name FROM companies').fetchall()}
        connection.execute("UPDATE companies SET cnpj = '11.222.333/0001-81', contract_start = COALESCE(NULLIF(contract_start, ''), '2026-01-01'), contract_end = COALESCE(NULLIF(contract_end, ''), '2026-12-31'), plan_name = CASE WHEN plan_name IN ('Plano padrao', 'Plano padrão', 'Enterprise Offshore') THEN 'enterprise' ELSE plan_name END, logo_type = COALESCE(logo_type, ''), addendum_enabled = COALESCE(addendum_enabled, 0) WHERE name = 'DOF Brasil'")
        connection.execute("UPDATE companies SET cnpj = '44.555.666/0001-81', contract_start = COALESCE(NULLIF(contract_start, ''), '2026-01-01'), contract_end = COALESCE(NULLIF(contract_end, ''), '2026-12-31'), plan_name = CASE WHEN plan_name IN ('Plano padrao', 'Plano padrão', 'Fleet Base') THEN 'corporate' ELSE plan_name END, logo_type = COALESCE(logo_type, ''), addendum_enabled = COALESCE(addendum_enabled, 0) WHERE name = 'Norskan Offshore'")
        connection.execute("UPDATE units SET unit_type = 'embarcacao' WHERE unit_type IN ('navio', 'embarcação')")
        migrate_role_hierarchy(connection)
        existing_usernames = {row['username'] for row in connection.execute('SELECT username FROM users').fetchall()}
        users_to_insert = []
        if 'dof.general' not in existing_usernames:
            users_to_insert.append(('dof.general', hash_password('dofgeneral123'), 'Administrador Geral DOF Brasil', 'general_admin', companies['DOF Brasil']))
        if 'dof.admin' not in existing_usernames:
            users_to_insert.append(('dof.admin', hash_password('dofadmin123'), 'Administrador DOF Brasil', 'admin', companies['DOF Brasil']))
        if 'dof.user' not in existing_usernames:
            users_to_insert.append(('dof.user', hash_password('dof123'), 'Usuário DOF Brasil', 'user', companies['DOF Brasil']))
        if 'norskan.general' not in existing_usernames:
            users_to_insert.append(('norskan.general', hash_password('norskangeneral123'), 'Administrador Geral Norskan', 'general_admin', companies['Norskan Offshore']))
        if 'norskan.admin' not in existing_usernames:
            users_to_insert.append(('norskan.admin', hash_password('norskanadmin123'), 'Administrador Norskan', 'admin', companies['Norskan Offshore']))
        if 'norskan.user' not in existing_usernames:
            users_to_insert.append(('norskan.user', hash_password('norskan123'), 'Usuário Norskan Offshore', 'user', companies['Norskan Offshore']))
        if users_to_insert:
            connection.executemany('INSERT INTO users (username, password, full_name, role, company_id) VALUES (?, ?, ?, ?, ?)', users_to_insert)
        bootstrap_admin = ensure_initial_master_admin(connection)
        if connection.execute('SELECT COUNT(*) FROM units').fetchone()[0] == 0:
            connection.executemany('INSERT INTO units (company_id, name, unit_type, city, notes) VALUES (?, ?, ?, ?, ?)', [(companies['DOF Brasil'], 'Base Macae', 'base', 'Macae', 'Base onshore'), (companies['DOF Brasil'], 'Navio Skandi', 'navio', 'Bacia de Campos', 'Navio offshore'), (companies['Norskan Offshore'], 'Base Rio Capital', 'base', 'Rio de Janeiro', 'Base onshore'), (companies['Norskan Offshore'], 'Navio Norskan Alpha', 'navio', 'Bacia de Santos', 'Navio offshore')])
        if connection.execute('SELECT COUNT(*) FROM employees').fetchone()[0] == 0:
            dof_base = connection.execute("SELECT id FROM units WHERE name = 'Base Macae'").fetchone()['id']
            norskan_ship = connection.execute("SELECT id FROM units WHERE name = 'Navio Norskan Alpha'").fetchone()['id']
            connection.executemany('INSERT INTO employees (company_id, unit_id, employee_id_code, name, sector, role_name, admission_date, schedule_type) VALUES (?, ?, ?, ?, ?, ?, ?, ?)', [(companies['DOF Brasil'], dof_base, '1001', 'Carlos Souza', 'Producao', 'Operador', '2025-01-10', '14x14'), (companies['Norskan Offshore'], norskan_ship, '2001', 'Fernanda Lima', 'SSMA', 'Tecnica de Seguranca', '2024-11-20', '28x28')])
        if connection.execute('SELECT COUNT(*) FROM epis').fetchone()[0] == 0:
            dof_base = connection.execute("SELECT id FROM units WHERE name = 'Base Macae'").fetchone()['id']
            norskan_ship = connection.execute("SELECT id FROM units WHERE name = 'Navio Norskan Alpha'").fetchone()['id']
            connection.executemany('INSERT INTO epis (company_id, unit_id, name, purchase_code, ca, sector, stock, unit_measure, ca_expiry, epi_validity_date, manufacture_date, validity_days, qr_code_value) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', [(companies['DOF Brasil'], dof_base, 'Capacete Classe B', 'COD-001', '12345', 'Producao', 18, 'unidade', '2026-04-25', '2026-10-25', '2025-10-25', 180, f"EPI-{companies['DOF Brasil']}-{dof_base}-COD-001"), (companies['DOF Brasil'], dof_base, 'Bota de Seguranca', 'COD-002', '12346', 'Producao', 12, 'par', '2026-08-01', '2027-02-01', '2025-08-01', 180, f"EPI-{companies['DOF Brasil']}-{dof_base}-COD-002"), (companies['Norskan Offshore'], norskan_ship, 'Luva Nitrilica', 'COD-101', '67890', 'SSMA', 7, 'par', '2026-03-28', '2026-09-28', '2025-09-28', 60, f"EPI-{companies['Norskan Offshore']}-{norskan_ship}-COD-101")])
        connection.execute("UPDATE epis SET unit_id = COALESCE(unit_id, (SELECT id FROM units WHERE units.company_id = epis.company_id ORDER BY id LIMIT 1)) WHERE unit_id IS NULL")
        connection.execute("UPDATE epis SET qr_code_value = COALESCE(NULLIF(qr_code_value, ''), 'EPI-' || company_id || '-' || COALESCE(unit_id, 0) || '-' || UPPER(REPLACE(purchase_code, ' ', '-')))")
        seq_rows = connection.execute('SELECT id, company_id FROM epis WHERE epi_master_sequence IS NULL ORDER BY id').fetchall()
        for row in seq_rows:
            seq_value = next_company_qr_sequence(connection, int(row['company_id']))
            connection.execute(
                'UPDATE epis SET epi_master_sequence = ?, qr_code_value = COALESCE(NULLIF(qr_code_value, \'\'), ?) WHERE id = ?',
                (seq_value, build_master_epi_qr(int(row['company_id']), seq_value), int(row['id']))
            )
        connection.execute(
            '''
            INSERT INTO unit_epi_stock (company_id, unit_id, epi_id, quantity, updated_at)
            SELECT epis.company_id, epis.unit_id, epis.id, epis.stock, ?
            FROM epis
            WHERE NOT EXISTS (
                SELECT 1 FROM unit_epi_stock s
                WHERE s.company_id = epis.company_id AND s.unit_id = epis.unit_id AND s.epi_id = epis.id
            )
            ''',
            (datetime.now(UTC).isoformat(),)
        )
        connection.commit()
        return bootstrap_admin


def ensure_company_audit_columns(connection):
    connection.execute("ALTER TABLE company_audit_logs ADD COLUMN IF NOT EXISTS details_json TEXT NOT NULL DEFAULT '[]'")


def ensure_epi_columns(connection):
    connection.execute("ALTER TABLE epis ADD COLUMN IF NOT EXISTS unit_id INTEGER")
    connection.execute("ALTER TABLE epis ADD COLUMN IF NOT EXISTS qr_code_value TEXT")
    connection.execute("ALTER TABLE epis ADD COLUMN IF NOT EXISTS epi_master_sequence INTEGER")
    connection.execute("ALTER TABLE epis ADD COLUMN IF NOT EXISTS manufacturer TEXT NOT NULL DEFAULT ''")
    connection.execute("ALTER TABLE epis ADD COLUMN IF NOT EXISTS supplier_company TEXT NOT NULL DEFAULT ''")
    connection.execute("ALTER TABLE epis ADD COLUMN IF NOT EXISTS validity_years INTEGER NOT NULL DEFAULT 0")
    connection.execute("ALTER TABLE epis ADD COLUMN IF NOT EXISTS validity_months INTEGER NOT NULL DEFAULT 0")
    connection.execute("ALTER TABLE epis ADD COLUMN IF NOT EXISTS manufacturer_validity_months INTEGER NOT NULL DEFAULT 0")
    connection.execute("ALTER TABLE epis ADD COLUMN IF NOT EXISTS joinventures_json TEXT NOT NULL DEFAULT '[]'")
    connection.execute("ALTER TABLE epis ADD COLUMN IF NOT EXISTS active_joinventure TEXT")
    connection.execute("ALTER TABLE epis ADD COLUMN IF NOT EXISTS model_reference TEXT NOT NULL DEFAULT ''")
    connection.execute("ALTER TABLE epis ADD COLUMN IF NOT EXISTS manufacturer_recommendations TEXT NOT NULL DEFAULT ''")
    connection.execute("ALTER TABLE epis ADD COLUMN IF NOT EXISTS epi_photo_data TEXT")
    connection.execute("ALTER TABLE epis ADD COLUMN IF NOT EXISTS epi_section TEXT NOT NULL DEFAULT ''")
    connection.execute("ALTER TABLE epis ADD COLUMN IF NOT EXISTS glove_size TEXT")
    connection.execute("ALTER TABLE epis ADD COLUMN IF NOT EXISTS size TEXT")
    connection.execute("ALTER TABLE epis ADD COLUMN IF NOT EXISTS uniform_size TEXT")
    connection.execute("ALTER TABLE epis ADD COLUMN IF NOT EXISTS joinventures_json TEXT NOT NULL DEFAULT '[]'")
    connection.execute("ALTER TABLE epis ADD COLUMN IF NOT EXISTS active_joinventure TEXT")


def generate_epi_qr_code(payload):
    purchase_code = str(payload.get('purchase_code', '')).strip().upper().replace(' ', '-')
    return f"EPI-{payload.get('company_id')}-{payload.get('unit_id')}-{purchase_code}"


def next_company_qr_sequence(connection, company_id):
    # Em Postgres, faz incremento atômico para evitar colisões em cenários concorrentes.
    if isinstance(connection, PostgresConnectionWrapper):
        row = connection.execute(
            '''
            INSERT INTO epi_qr_sequences (company_id, last_value)
            VALUES (?, 1)
            ON CONFLICT (company_id)
            DO UPDATE SET last_value = epi_qr_sequences.last_value + 1
            RETURNING last_value
            ''',
            (company_id,)
        ).fetchone()
        return int(row['last_value'])

    # Fallback compatível para SQLite/local.
    current = connection.execute('SELECT last_value FROM epi_qr_sequences WHERE company_id = ?', (company_id,)).fetchone()
    if not current:
        connection.execute('INSERT INTO epi_qr_sequences (company_id, last_value) VALUES (?, ?)', (company_id, 1))
        return 1
    next_value = int(current['last_value']) + 1
    connection.execute('UPDATE epi_qr_sequences SET last_value = ? WHERE company_id = ?', (next_value, company_id))
    return next_value


def build_master_epi_qr(company_id, sequence_value):
    return f"EPI-MASTER-{int(company_id):04d}-{int(sequence_value):08d}"


def build_stock_item_qr(company_id, unit_id, sequence_value):
    return f"EPI-ITEM-{int(company_id):04d}-{int(unit_id):04d}-{int(sequence_value):08d}"


def get_unit_stock(connection, company_id, unit_id, epi_id):
    row = connection.execute(
        'SELECT id, quantity FROM unit_epi_stock WHERE company_id = ? AND unit_id = ? AND epi_id = ?',
        (company_id, unit_id, epi_id)
    ).fetchone()
    return row_to_dict(row) if row else None


def upsert_unit_stock(connection, company_id, unit_id, epi_id, new_quantity):
    now = datetime.now(UTC).isoformat()
    existing = get_unit_stock(connection, company_id, unit_id, epi_id)
    if existing:
        connection.execute(
            'UPDATE unit_epi_stock SET quantity = ?, updated_at = ? WHERE id = ?',
            (int(new_quantity), now, int(existing['id']))
        )
    else:
        connection.execute(
            'INSERT INTO unit_epi_stock (company_id, unit_id, epi_id, quantity, updated_at) VALUES (?, ?, ?, ?, ?)',
            (company_id, unit_id, epi_id, int(new_quantity), now)
        )


def resolve_delivery_period(delivery_date, schedule_type):
    start = datetime.strptime(str(delivery_date), '%Y-%m-%d').date()
    days = period_days_from_schedule(schedule_type)
    end = start + timedelta(days=days - 1)
    return start.isoformat(), end.isoformat()


def ensure_ficha_for_delivery(connection, delivery_row):
    period_start, period_end = resolve_delivery_period(delivery_row['delivery_date'], delivery_row.get('schedule_type'))
    now = datetime.now(UTC).isoformat()
    ficha = connection.execute(
        '''
        SELECT id FROM epi_ficha_periods
        WHERE employee_id = ? AND period_start = ? AND period_end = ?
        ''',
        (delivery_row['employee_id'], period_start, period_end)
    ).fetchone()
    if ficha:
        ficha_id = int(ficha['id'])
    else:
        cursor = connection.execute(
            '''
            INSERT INTO epi_ficha_periods (
                company_id, employee_id, unit_id, schedule_type, period_start, period_end,
                status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, 'open', ?, ?)
            ''',
            (
                delivery_row['company_id'],
                delivery_row['employee_id'],
                delivery_row['unit_id'],
                delivery_row.get('schedule_type') or '',
                period_start,
                period_end,
                now,
                now
            )
        )
        ficha_id = int(cursor.lastrowid)
    connection.execute(
        '''
        INSERT INTO epi_ficha_items (
            ficha_period_id, delivery_id, company_id, employee_id, unit_id, epi_id, quantity,
            created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT (delivery_id) DO NOTHING
        ''',
        (
            ficha_id,
            delivery_row['id'],
            delivery_row['company_id'],
            delivery_row['employee_id'],
            delivery_row['unit_id'],
            delivery_row['epi_id'],
            delivery_row['quantity'],
            now,
            now
        )
    )
    return ficha_id


def company_action_label(action_type):
    return {
        'create': 'Criação',
        'update': 'Atualização',
        'suspend': 'Suspensão',
        'reactivate': 'Reativação',
    }.get(action_type, action_type)


def summarize_company_changes(previous, payload):
    tracked_fields = {
        'plan_name': 'Plano',
        'user_limit': 'Limite de usuários',
        'license_status': 'Status da licença',
        'active': 'Status da empresa',
        'contract_start': 'Início do contrato',
        'contract_end': 'Fim do contrato',
        'monthly_value': 'Valor mensal atual',
        'addendum_enabled': 'Aditivo contratual',
        'commercial_notes': 'Observações',
    }
    if not previous:
        details = [{
            'field': tracked_fields[field],
            'before': '',
            'after': str(payload.get(field, ''))
        } for field in tracked_fields]
        return f"Empresa criada com plano {payload['plan_name']} e limite de {payload['user_limit']} usuários.", details
    changes = []
    details = []
    for field, label in tracked_fields.items():
        previous_value = str(previous.get(field, ''))
        current_value = str(payload.get(field, ''))
        if previous_value != current_value:
            changes.append(label.lower())
            details.append({'field': label, 'before': previous_value, 'after': current_value})
    summary = 'Alteração em ' + ', '.join(changes) + '.' if changes else 'Dados comerciais revisados sem mudança crítica.'
    return summary, details


def register_company_audit(connection, company_id, actor, action_type, summary, details=None):
    connection.execute(
        'INSERT INTO company_audit_logs (company_id, actor_user_id, actor_name, action_type, summary, details_json, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)',
        (company_id, actor['id'], actor['full_name'], action_type, summary, json.dumps(details or [], ensure_ascii=False), datetime.now().isoformat(timespec='seconds')),
    )


def fetch_company_audit_logs(connection, actor=None):
    sql = """SELECT company_audit_logs.id, company_audit_logs.company_id, company_audit_logs.actor_user_id, company_audit_logs.actor_name,
                    company_audit_logs.action_type, company_audit_logs.summary, company_audit_logs.details_json, company_audit_logs.created_at,
                    companies.name AS company_name
             FROM company_audit_logs
             JOIN companies ON companies.id = company_audit_logs.company_id"""
    if actor and actor['role'] != 'master_admin':
        rows = connection.execute(sql + ' WHERE company_audit_logs.company_id = ? ORDER BY company_audit_logs.created_at DESC, company_audit_logs.id DESC', (actor['company_id'],)).fetchall()
    else:
        rows = connection.execute(sql + ' ORDER BY company_audit_logs.created_at DESC, company_audit_logs.id DESC').fetchall()
    logs = []
    for row in rows:
        item = row_to_dict(row)
        item['action_label'] = company_action_label(item['action_type'])
        item['details'] = json.loads(item.get('details_json') or '[]')
        logs.append(item)
    return logs


def pdf_safe_text(value):
    text = str(value or '')
    text = text.encode('cp1252', 'replace').decode('cp1252')
    return text.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')


def extract_jpeg_dimensions(image_bytes):
    if not image_bytes.startswith(b'\xff\xd8'):
        raise ValueError('JPEG inválido.')
    offset = 2
    sof_markers = {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}
    standalone_markers = {0x01, 0xD0, 0xD1, 0xD2, 0xD3, 0xD4, 0xD5, 0xD6, 0xD7, 0xD8, 0xD9}

    while offset < len(image_bytes):
        while offset < len(image_bytes) and image_bytes[offset] != 0xFF:
            offset += 1
        while offset < len(image_bytes) and image_bytes[offset] == 0xFF:
            offset += 1
        if offset >= len(image_bytes):
            break

        marker_byte = image_bytes[offset]
        offset += 1

        if marker_byte in standalone_markers:
            continue
        if offset + 2 > len(image_bytes):
            break

        segment_length = int.from_bytes(image_bytes[offset:offset + 2], 'big')
        if segment_length < 2 or offset + segment_length > len(image_bytes):
            break

        if marker_byte in sof_markers:
            segment_start = offset + 2
            if segment_start + 5 > len(image_bytes):
                break
            height = int.from_bytes(image_bytes[segment_start + 1:segment_start + 3], 'big')
            width = int.from_bytes(image_bytes[segment_start + 3:segment_start + 5], 'big')
            if width > 0 and height > 0:
                return width, height

        offset += segment_length

    return 1, 1


def extract_pdf_logo_image(data_uri):
    value = str(data_uri or '')
    if not value.startswith('data:image/jpeg;base64,') and not value.startswith('data:image/jpg;base64,'):
        return None
    image_bytes = base64.b64decode(value.split(',', 1)[1])
    width, height = extract_jpeg_dimensions(image_bytes)
    return {'bytes': image_bytes, 'width': width, 'height': height}


def build_pdf_document(page_lines, header_image=None):
    objects = []

    def add_object(content):
        objects.append(content)
        return len(objects)

    catalog_id = add_object('')
    pages_id = add_object('')
    font_regular_id = add_object('<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>')
    font_bold_id = add_object('<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>')
    image_object_id = None
    if header_image:
        image_stream = header_image['bytes']
        image_object_id = add_object(
            f"<< /Type /XObject /Subtype /Image /Width {header_image['width']} /Height {header_image['height']} /ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /DCTDecode /Length {len(image_stream)} >>\nstream\n".encode('latin-1')
            + image_stream
            + b"\nendstream"
        )
    page_ids = []
    for lines in page_lines:
        commands = ['q 0.96 0.85 0.78 rg 40 770 515 44 re f Q']
        if image_object_id:
            commands.append('q 72 0 0 36 452 774 cm /Im1 Do Q')
        for line in lines:
            font = '/F2' if line.get('bold') else '/F1'
            size = line.get('size', 12)
            x = line.get('x', 50)
            y = line.get('y', 760)
            commands.append(f"BT {font} {size} Tf 1 0 0 1 {x} {y} Tm ({pdf_safe_text(line.get('text', ''))}) Tj ET")
        content_stream = '\n'.join(commands).encode('cp1252', 'replace')
        content_id = add_object(f"<< /Length {len(content_stream)} >>\nstream\n".encode('latin-1') + content_stream + b"\nendstream")
        image_resource = f" /XObject << /Im1 {image_object_id} 0 R >>" if image_object_id else ''
        page_id = add_object(f"<< /Type /Page /Parent {pages_id} 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 {font_regular_id} 0 R /F2 {font_bold_id} 0 R >>{image_resource} >> /Contents {content_id} 0 R >>")
        page_ids.append(page_id)
    kids = ' '.join(f'{page_id} 0 R' for page_id in page_ids)
    objects[pages_id - 1] = f"<< /Type /Pages /Count {len(page_ids)} /Kids [{kids}] >>"
    objects[catalog_id - 1] = f"<< /Type /Catalog /Pages {pages_id} 0 R >>"

    output = bytearray(b'%PDF-1.4\n%\xe2\xe3\xcf\xd3\n')
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(output))
        if isinstance(obj, bytes):
            output.extend(f"{index} 0 obj\n".encode('latin-1'))
            output.extend(obj)
            output.extend(b"\nendobj\n")
        else:
            output.extend(f"{index} 0 obj\n{obj}\nendobj\n".encode('latin-1'))
    xref_pos = len(output)
    output.extend(f"xref\n0 {len(objects) + 1}\n".encode('latin-1'))
    output.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n \n".encode('latin-1'))
    output.extend(f"trailer\n<< /Size {len(objects) + 1} /Root {catalog_id} 0 R >>\nstartxref\n{xref_pos}\n%%EOF".encode('latin-1'))
    return bytes(output)


def build_commercial_contract_pdf(connection, actor, company_id):
    ensure_company_access(actor, company_id)
    company = connection.execute('SELECT * FROM companies WHERE id = ?', (company_id,)).fetchone()
    if not company:
        raise ValueError('Empresa nao encontrada.')
    company = row_to_dict(company)
    company['user_count'] = count_company_users(connection, company_id)
    settings = get_commercial_settings(connection)
    metrics = compute_company_contract_metrics(company, settings)
    brand = get_platform_brand(connection)
    logo_image = extract_pdf_logo_image(brand.get('logo_type'))
    today = datetime.now()
    monthly_value = f"R$ {float(metrics['calculated_monthly_value'] or 0):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    projected_value = f"R$ {float(metrics['projected_monthly_value'] or 0):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    unit_price = f"R$ {float(metrics['unit_price'] or 0):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    pages = []
    page_lines = []
    y = 792

    def add_line(text_value, size=12, bold=False, x=52, gap=18):
        nonlocal y, page_lines
        if y < 70:
            pages.append(page_lines)
            page_lines = []
            y = 792
        page_lines.append({'text': text_value, 'size': size, 'bold': bold, 'x': x, 'y': y})
        y -= gap

    add_line(brand.get('display_name') or 'Sua Empresa', size=22, bold=True, x=52, gap=28)
    if brand.get('legal_name'):
        add_line(brand['legal_name'], size=11, x=52, gap=16)
    if brand.get('cnpj'):
        add_line(f"CNPJ: {brand['cnpj']}", size=11, x=52, gap=20)
    add_line('Contrato Comercial de Licenca do Sistema', size=18, bold=True, x=52, gap=24)
    add_line(f"Gerado em {today.strftime('%d/%m/%Y %H:%M')}", size=10, x=52, gap=22)
    add_line('Empresa contratante', size=14, bold=True, x=52, gap=20)
    add_line(company['name'], size=12, bold=True, x=52, gap=18)
    add_line(f"Razao social: {company.get('legal_name') or '-'}")
    add_line(f"CNPJ: {company.get('cnpj') or '-'}")
    add_line(f"Plano contratado: {company.get('plan_name') or '-'}")
    add_line(f"Usuarios ativos: {company.get('user_count') or 0}")
    add_line(f"Limite de usuarios ativos: {company.get('user_limit') or 0}")
    add_line(f"Valor unitario: {unit_price}")
    add_line(f"Valor mensal atual: {monthly_value}")
    add_line(f"Valor projetado pelo limite contratado: {projected_value}")
    add_line(f"Status da licenca: {company_license_label(company.get('license_status'))}")
    add_line(f"Status da empresa: {'Ativa' if int(company.get('active') or 0) == 1 else 'Inativa'}")
    add_line(f"Aditivo contratual: {'Sim' if int(company.get('addendum_enabled') or 0) == 1 else 'Nao'}")
    add_line(f"Inicio do contrato: {company.get('contract_start') or '-'}")
    add_line(f"Fim do contrato: {company.get('contract_end') or '-'}")
    add_line('Observacoes comerciais', size=14, bold=True, x=52, gap=20)
    notes = company.get('commercial_notes') or 'Sem observacoes comerciais registradas.'
    for wrapped in textwrap.wrap(notes, width=82):
        add_line(wrapped, size=11, x=52, gap=16)
    add_line('Clausulas operacionais', size=14, bold=True, x=52, gap=20)
    clauses = [
        '1. O valor mensal atual e calculado automaticamente pela quantidade de usuarios ativos.',
        '2. O valor unitario e definido pelo Administrador Master no modulo comercial.',
        '3. Ao atingir o limite contratado, novos usuarios ativos serao bloqueados.',
        '4. Exceder o plano padrao exige aditivo contratual ativo.',
    ]
    for clause in clauses:
        for wrapped in textwrap.wrap(clause, width=82):
            add_line(wrapped, size=11, x=52, gap=16)
    add_line('Assinaturas', size=14, bold=True, x=52, gap=22)
    add_line(f"Contratada: {brand.get('display_name') or 'Sua Empresa'}", size=11, x=52, gap=40)
    add_line(f"Contratante: {company['name']}", size=11, x=52, gap=40)
    pages.append(page_lines)
    return build_pdf_document(pages, logo_image)


def get_employee_user_by_token(connection, token):
    if not token:
        return None
    row = connection.execute(
        '''
        SELECT users.id, users.full_name, users.username, users.role, users.company_id, users.active, users.linked_employee_id,
               users.employee_access_token, users.employee_access_expires_at,
               companies.name AS company_name, companies.cnpj AS company_cnpj,
               employees.name AS employee_name, employees.employee_id_code, employees.role_name, employees.sector, employees.schedule_type
        FROM users
        JOIN employees ON employees.id = users.linked_employee_id
        LEFT JOIN companies ON companies.id = users.company_id
        WHERE users.employee_access_token = ? AND users.role = 'employee'
        LIMIT 1
        ''',
        (token,)
    ).fetchone()
    if not row:
        return None
    item = row_to_dict(row)
    expires_at = str(item.get('employee_access_expires_at') or '').strip()
    if expires_at and expires_at < datetime.now(UTC).isoformat():
        return None
    if int(item.get('active') or 0) != 1:
        return None
    return item


def hash_portal_token(token):
    return hashlib.sha256(str(token or '').encode('utf-8')).hexdigest()


def parse_int_flexible(value, default=0):
    raw = str(value or '').strip()
    if not raw:
        return int(default)
    digits = ''.join(ch for ch in raw if ch.isdigit() or ch == '-')
    if not digits:
        return int(default)
    try:
        return int(digits)
    except ValueError:
        return int(default)


def register_employee_portal_audit(connection, portal_context, action, ip_address='', user_agent='', payload=None):
    if not portal_context:
        return
    now = datetime.now(UTC).isoformat()
    connection.execute(
        '''
        INSERT INTO employee_portal_audit_logs (
            company_id, employee_id, portal_link_id, token_hash, action, ip_address, user_agent, payload, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''',
        (
            int(portal_context['company_id']),
            int(portal_context['employee_id']),
            int(portal_context['portal_link_id']) if portal_context.get('portal_link_id') else None,
            hash_portal_token(portal_context.get('token')),
            str(action or '').strip() or 'unknown',
            str(ip_address or '').strip(),
            str(user_agent or '').strip(),
            json.dumps(payload or {}, ensure_ascii=False),
            now
        )
    )


def get_employee_portal_context_by_token(connection, token):
    if not token:
        return None
    row = connection.execute(
        '''
        SELECT employee_portal_links.id AS portal_link_id, employee_portal_links.company_id, employee_portal_links.employee_id,
               employee_portal_links.token, employee_portal_links.active, employee_portal_links.expires_at,
               employees.name AS employee_name, employees.employee_id_code, employees.role_name, employees.sector,
               employees.schedule_type, employees.unit_id, units.name AS unit_name, companies.name AS company_name
        FROM employee_portal_links
        JOIN employees ON employees.id = employee_portal_links.employee_id
        JOIN units ON units.id = employees.unit_id
        JOIN companies ON companies.id = employee_portal_links.company_id
        WHERE employee_portal_links.token = ?
        LIMIT 1
        ''',
        (token,)
    ).fetchone()
    if not row:
        return None
    item = row_to_dict(row)
    if int(item.get('active') or 0) != 1:
        return None
    expires_at = str(item.get('expires_at') or '').strip()
    if expires_at and expires_at < datetime.now(UTC).isoformat():
        return None
    return item


def resolve_external_employee_context(connection, token):
    employee_user = get_employee_user_by_token(connection, token)
    if employee_user:
        return {
            'company_id': int(employee_user['company_id']),
            'employee_id': int(employee_user['linked_employee_id']),
            'employee_name': employee_user.get('employee_name') or employee_user.get('full_name'),
            'employee_id_code': employee_user.get('employee_id_code'),
            'role_name': employee_user.get('role_name', ''),
            'sector': employee_user.get('sector', ''),
            'schedule_type': employee_user.get('schedule_type', ''),
            'company_name': employee_user.get('company_name', ''),
            'unit_id': None,
            'unit_name': '',
            'portal_link_id': None,
            'token': token
        }
    return get_employee_portal_context_by_token(connection, token)


def build_employee_ficha_pdf(connection, employee_user):
    employee_id = int(employee_user['linked_employee_id'])
    deliveries = connection.execute(
        '''
        SELECT deliveries.delivery_date, deliveries.quantity, deliveries.quantity_label, deliveries.signature_name,
               deliveries.signature_at, epis.name AS epi_name, epis.purchase_code
        FROM deliveries
        JOIN epis ON epis.id = deliveries.epi_id
        WHERE deliveries.employee_id = ?
        ORDER BY deliveries.delivery_date DESC, deliveries.id DESC
        ''',
        (employee_id,)
    ).fetchall()

    lines = []
    lines.append(f"Ficha EPI - {employee_user.get('employee_name')}")
    lines.append(f"Empresa: {employee_user.get('company_name') or '-'}")
    lines.append(f"Matricula: {employee_user.get('employee_id_code') or '-'}")
    lines.append(f"Setor: {employee_user.get('sector') or '-'}")
    lines.append(f"Funcao: {employee_user.get('role_name') or '-'}")
    lines.append('')
    if deliveries:
        for item in deliveries:
            lines.append(
                f"{item['delivery_date']} | {item['epi_name']} ({item['purchase_code']}) | {item['quantity']} {item['quantity_label']} | assinatura: {item['signature_name']} {item['signature_at'] or ''}"
            )
    else:
        lines.append('Nenhuma entrega encontrada.')
    return build_pdf_document([lines], None)


def fetch_companies(connection, company_id=None):
    settings = get_commercial_settings(connection)
    placeholders = ','.join(['?'] * len(BILLABLE_ROLES))
    sql = f'''SELECT companies.id, companies.name, companies.legal_name, companies.cnpj, companies.logo_type, companies.plan_name, companies.user_limit, companies.license_status, companies.active, companies.commercial_notes, companies.contract_start, companies.contract_end, companies.monthly_value, companies.addendum_enabled, COUNT(users.id) AS user_count FROM companies LEFT JOIN users ON users.company_id = companies.id AND users.active = 1 AND users.role IN ({placeholders})'''
    params = list(BILLABLE_ROLES)
    if company_id:
        rows = connection.execute(sql + ' WHERE companies.id = ? GROUP BY companies.id ORDER BY companies.name', tuple(params + [company_id])).fetchall()
    else:
        rows = connection.execute(sql + ' GROUP BY companies.id ORDER BY companies.name', tuple(params)).fetchall()
    companies = []
    for row in rows:
        item = row_to_dict(row)
        metrics = compute_company_contract_metrics(item, settings)
        item.update(metrics)
        item['monthly_value'] = metrics['calculated_monthly_value']
        item['license_status_label'] = company_license_label(item['license_status'])
        item['limit_reached'] = int(item['user_count']) >= int(item['user_limit'])
        item['available_slots'] = max(int(item['user_limit']) - int(item['user_count']), 0)
        item['near_limit'] = int(item['user_limit']) > 0 and (int(item['user_count']) / int(item['user_limit'])) >= 0.8
        companies.append(item)
    return companies


def fetch_users(connection, actor=None):
    if actor and actor['role'] == 'user':
        return []
    sql = '''SELECT users.id, users.username, users.full_name, users.role, users.company_id, users.active,
             users.linked_employee_id, users.employee_access_token, users.employee_access_expires_at,
             companies.name AS company_name, companies.cnpj AS company_cnpj, companies.logo_type,
             employees.employee_id_code AS linked_employee_code, employees.name AS linked_employee_name
             FROM users
             LEFT JOIN companies ON companies.id = users.company_id
             LEFT JOIN employees ON employees.id = users.linked_employee_id'''
    order_by = " ORDER BY CASE users.role WHEN 'master_admin' THEN 4 WHEN 'general_admin' THEN 3 WHEN 'admin' THEN 2 WHEN 'user' THEN 1 ELSE 0 END DESC, users.full_name"
    if actor and actor['role'] in ('general_admin', 'registry_admin', 'admin'):
        rows = connection.execute(sql + " WHERE users.company_id = ? OR users.id = ?" + order_by, (actor['company_id'], actor['id'])).fetchall()
    else:
        rows = connection.execute(sql + order_by).fetchall()
    return [row_to_dict(row) for row in rows]

def fetch_units(connection, actor=None):
    sql = '''SELECT units.id, units.company_id, units.name, units.unit_type, units.city, units.notes, companies.name AS company_name, companies.cnpj AS company_cnpj, companies.logo_type FROM units JOIN companies ON companies.id = units.company_id'''
    if actor and actor['role'] != 'master_admin':
        rows = connection.execute(sql + ' WHERE units.company_id = ? ORDER BY companies.name, units.name', (actor['company_id'],)).fetchall()
    else:
        rows = connection.execute(sql + ' ORDER BY companies.name, units.name').fetchall()
    return [row_to_dict(row) for row in rows]


def fetch_employees(connection, actor=None):
    sql = '''SELECT employees.id, employees.company_id, employees.unit_id, employees.employee_id_code, employees.name, employees.sector, employees.role_name, employees.admission_date, employees.schedule_type, companies.name AS company_name, companies.cnpj AS company_cnpj, companies.logo_type, units.name AS unit_name, units.unit_type, units.city AS unit_city FROM employees JOIN companies ON companies.id = employees.company_id JOIN units ON units.id = employees.unit_id'''
    if actor and actor['role'] != 'master_admin':
        rows = connection.execute(sql + ' WHERE employees.company_id = ? ORDER BY employees.name', (actor['company_id'],)).fetchall()
    else:
        rows = connection.execute(sql + ' ORDER BY employees.name').fetchall()
    employees = [row_to_dict(row) for row in rows]
    today_iso = date.today().isoformat()
    for employee in employees:
        movement = connection.execute(
            '''
            SELECT employee_unit_movements.target_unit_id, units.name AS target_unit_name, units.unit_type AS target_unit_type
            FROM employee_unit_movements
            JOIN units ON units.id = employee_unit_movements.target_unit_id
            WHERE employee_unit_movements.employee_id = ?
              AND employee_unit_movements.movement_type = 'temporary'
              AND employee_unit_movements.start_date <= ?
              AND COALESCE(NULLIF(employee_unit_movements.end_date, ''), '9999-12-31') >= ?
            ORDER BY employee_unit_movements.start_date DESC, employee_unit_movements.id DESC
            LIMIT 1
            ''',
            (employee['id'], today_iso, today_iso)
        ).fetchone()
        if movement:
            employee['current_unit_id'] = movement['target_unit_id']
            employee['current_unit_name'] = movement['target_unit_name']
            employee['current_unit_type'] = movement['target_unit_type']
            employee['unit_allocation_type'] = 'temporary'
        else:
            employee['current_unit_id'] = employee['unit_id']
            employee['current_unit_name'] = employee['unit_name']
            employee['current_unit_type'] = employee['unit_type']
            employee['unit_allocation_type'] = 'primary'
    return employees


def fetch_employee_movements(connection, actor=None):
    sql = '''
    SELECT employee_unit_movements.id, employee_unit_movements.employee_id, employee_unit_movements.company_id,
           employee_unit_movements.source_unit_id, employee_unit_movements.target_unit_id, employee_unit_movements.movement_type,
           employee_unit_movements.start_date, employee_unit_movements.end_date, employee_unit_movements.notes,
           employee_unit_movements.actor_user_id, employee_unit_movements.actor_name, employee_unit_movements.created_at,
           employees.name AS employee_name, employees.employee_id_code,
           source_units.name AS source_unit_name, target_units.name AS target_unit_name
    FROM employee_unit_movements
    JOIN employees ON employees.id = employee_unit_movements.employee_id
    JOIN units AS source_units ON source_units.id = employee_unit_movements.source_unit_id
    JOIN units AS target_units ON target_units.id = employee_unit_movements.target_unit_id
    '''
    if actor and actor['role'] != 'master_admin':
        rows = connection.execute(sql + ' WHERE employee_unit_movements.company_id = ? ORDER BY employee_unit_movements.created_at DESC, employee_unit_movements.id DESC', (actor['company_id'],)).fetchall()
    else:
        rows = connection.execute(sql + ' ORDER BY employee_unit_movements.created_at DESC, employee_unit_movements.id DESC').fetchall()
    return [row_to_dict(row) for row in rows]


def get_employee_current_unit(connection, employee_id):
    employee = get_employee_by_id(connection, int(employee_id))
    if not employee:
        return None
    today_iso = date.today().isoformat()
    movement = connection.execute(
        '''
        SELECT employee_unit_movements.target_unit_id
        FROM employee_unit_movements
        WHERE employee_unit_movements.employee_id = ?
          AND employee_unit_movements.movement_type = 'temporary'
          AND employee_unit_movements.start_date <= ?
          AND COALESCE(NULLIF(employee_unit_movements.end_date, ''), '9999-12-31') >= ?
        ORDER BY employee_unit_movements.start_date DESC, employee_unit_movements.id DESC
        LIMIT 1
        ''',
        (int(employee_id), today_iso, today_iso)
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


def fetch_epis(connection, actor=None, unit_id=None):
    sql = '''SELECT epis.id, epis.company_id, epis.unit_id, epis.name, epis.purchase_code, epis.ca, epis.sector, epis.epi_section,
                    COALESCE((
                        SELECT SUM(unit_epi_stock.quantity) FROM unit_epi_stock
                        WHERE unit_epi_stock.company_id = epis.company_id AND unit_epi_stock.epi_id = epis.id
                    ), epis.stock, 0) AS stock,
                    epis.minimum_stock, epis.unit_measure, epis.ca_expiry, epis.epi_validity_date,
                    epis.manufacture_date, epis.validity_days, epis.validity_years, epis.validity_months, epis.manufacturer_validity_months,
                    epis.manufacturer, epis.model_reference, epis.supplier_company, epis.manufacturer_recommendations, epis.epi_photo_data,
                    epis.glove_size, epis.size, epis.uniform_size,
                    epis.joinventures_json, epis.active_joinventure,
                    epis.manufacture_date, epis.validity_days, epis.validity_years, epis.validity_months,
                    epis.manufacturer, epis.supplier_company, epis.joinventures_json, epis.active_joinventure,
                    epis.qr_code_value, epis.epi_master_sequence,
                    companies.name AS company_name, companies.cnpj AS company_cnpj, companies.logo_type, units.name AS unit_name, units.unit_type
             FROM epis JOIN companies ON companies.id = epis.company_id LEFT JOIN units ON units.id = epis.unit_id'''
    clauses = []
    params = []
    if actor and actor['role'] != 'master_admin':
        clauses.append('epis.company_id = ?')
        params.append(actor['company_id'])
    if unit_id:
        clauses.append('(epis.unit_id = ? OR epis.unit_id IS NULL)')
        params.append(int(unit_id))
    where_sql = f" WHERE {' AND '.join(clauses)}" if clauses else ''
    rows = connection.execute(sql + where_sql + ' ORDER BY companies.name, epis.name', tuple(params)).fetchall()
    return [row_to_dict(row) for row in rows]


def fetch_epis_from_unit_stock(connection, actor, company_id, unit_id):
    params = [int(company_id), int(unit_id)]
    where_sql = 'WHERE s.company_id = ? AND s.unit_id = ?'
    rows = connection.execute(
        f'''
        SELECT epis.id, epis.company_id, s.unit_id AS unit_id, epis.name, epis.purchase_code, epis.ca, epis.sector, epis.epi_section,
               s.quantity AS stock, epis.minimum_stock, epis.unit_measure, epis.ca_expiry, epis.epi_validity_date,
               epis.manufacture_date, epis.validity_days, epis.validity_years, epis.validity_months, epis.manufacturer_validity_months,
               epis.manufacturer, epis.model_reference, epis.supplier_company, epis.manufacturer_recommendations, epis.epi_photo_data,
               epis.glove_size, epis.size, epis.uniform_size, epis.joinventures_json, epis.active_joinventure,
               epis.qr_code_value, epis.epi_master_sequence,
               companies.name AS company_name, companies.cnpj AS company_cnpj, companies.logo_type,
               units.name AS unit_name, units.unit_type
        FROM unit_epi_stock s
        JOIN epis ON epis.id = s.epi_id
        JOIN companies ON companies.id = s.company_id
        JOIN units ON units.id = s.unit_id
        {where_sql}
        ORDER BY epis.name ASC
        ''',
        tuple(params)
    ).fetchall()
    return [row_to_dict(row) for row in rows]


def fetch_epi_size_balance(connection, company_id, unit_id, epi_id):
    rows = connection.execute(
        '''
        SELECT glove_size, size, uniform_size, COUNT(*) AS quantity
        FROM epi_stock_items
        WHERE company_id = ? AND unit_id = ? AND epi_id = ? AND status = 'in_stock'
        GROUP BY glove_size, size, uniform_size
        ORDER BY quantity DESC, glove_size ASC, size ASC, uniform_size ASC
        ''',
        (int(company_id), int(unit_id), int(epi_id))
    ).fetchall()
    items = []
    for row in rows:
        parsed = row_to_dict(row)
        items.append(
            {
                'glove_size': parsed.get('glove_size') or 'N/A',
                'size': parsed.get('size') or 'N/A',
                'uniform_size': parsed.get('uniform_size') or 'N/A',
                'quantity': int(parsed.get('quantity') or 0)
            }
        )
    return items


def fetch_deliveries(connection, actor=None, where_clause='', params=()):
    clauses = []
    query_params = list(params)
    if actor and actor['role'] != 'master_admin':
        clauses.append('deliveries.company_id = ?')
        query_params.append(actor['company_id'])
    if where_clause:
        clean = where_clause.strip()
        clauses.append(clean[6:] if clean.upper().startswith('WHERE ') else clean)
    final_where = f"WHERE {' AND '.join(clauses)}" if clauses else ''
    rows = connection.execute(f'''SELECT deliveries.id, deliveries.company_id, deliveries.employee_id, deliveries.epi_id, deliveries.quantity, deliveries.quantity_label, deliveries.sector, deliveries.role_name, deliveries.delivery_date, deliveries.next_replacement_date, deliveries.notes, deliveries.signature_name, deliveries.signature_data, deliveries.signature_at, deliveries.unit_id, deliveries.stock_movement_id,
                                  companies.name AS company_name, companies.cnpj AS company_cnpj, companies.logo_type,
                                  employees.employee_id_code, employees.name AS employee_name, employees.schedule_type,
                                  units.name AS unit_name, units.unit_type, epis.name AS epi_name, epis.purchase_code, epis.ca, epis.unit_measure, epis.epi_validity_date, epis.manufacture_date, epis.qr_code_value
                           FROM deliveries
                           JOIN companies ON companies.id = deliveries.company_id
                           JOIN employees ON employees.id = deliveries.employee_id
                           LEFT JOIN units ON units.id = deliveries.unit_id
                           JOIN epis ON epis.id = deliveries.epi_id
                           {final_where}
                           ORDER BY deliveries.delivery_date DESC, deliveries.id DESC''', tuple(query_params)).fetchall()
    return [row_to_dict(row) for row in rows]


def fetch_feedbacks(connection, actor=None):
    clauses = []
    params = []
    if actor and actor['role'] != 'master_admin':
        clauses.append('f.company_id = ?')
        params.append(actor['company_id'])
    final_where = f"WHERE {' AND '.join(clauses)}" if clauses else ''
    rows = connection.execute(
        f'''
        SELECT f.id, f.company_id, f.unit_id, f.employee_id, f.epi_id, f.comfort_rating, f.quality_rating, f.adequacy_rating,
               f.performance_rating, f.comments, f.improvement_suggestion, f.suggested_new_epi_name, f.suggested_new_epi_notes,
               f.status, f.reviewer_user_id, f.reviewer_name, f.reviewed_at, f.created_at, f.updated_at,
               companies.name AS company_name, units.name AS unit_name, employees.name AS employee_name,
               epis.name AS epi_name, epis.purchase_code
        FROM epi_feedbacks f
        JOIN companies ON companies.id = f.company_id
        JOIN units ON units.id = f.unit_id
        JOIN employees ON employees.id = f.employee_id
        LEFT JOIN epis ON epis.id = f.epi_id
        {final_where}
        ORDER BY f.created_at DESC, f.id DESC
        ''',
        tuple(params)
    ).fetchall()
    return [row_to_dict(row) for row in rows]


def compute_alerts(connection, actor=None):
    alerts = []
    today = date.today()
    scope_unit_id = actor_operational_unit_id(connection, actor)
    for epi in fetch_epis(connection, actor, scope_unit_id):
        days = (datetime.strptime(epi['ca_expiry'], '%Y-%m-%d').date() - today).days
        stock = int(epi['stock'])
        min_stock = int(epi.get('minimum_stock') or 10)
        if stock <= min_stock:
            alerts.append({'type': 'danger' if stock <= max(1, min_stock // 2) else 'warning', 'title': f"Estoque baixo: {epi['name']}", 'description': f"{epi['company_name']} / {epi.get('unit_name') or '-'} - saldo atual de {stock} {epi['unit_measure']}(s), mínimo {min_stock}."})
        if days <= 30:
            alerts.append({'type': 'danger' if days <= 7 else 'warning', 'title': f"CA próximo do vencimento: {epi['name']}", 'description': f"{epi['company_name']} - vence em {epi['ca_expiry']}."})
    return alerts


def get_user_by_id(connection, user_id):
    row = connection.execute('SELECT users.id, users.username, users.password, users.full_name, users.role, users.company_id, users.active, users.linked_employee_id, users.employee_access_token, users.employee_access_expires_at, companies.name AS company_name, companies.cnpj AS company_cnpj, companies.logo_type FROM users LEFT JOIN companies ON companies.id = users.company_id WHERE users.id = ?', (user_id,)).fetchone()
    if not row:
        return None
    item = row_to_dict(row)
    operational_unit_id = actor_operational_unit_id(connection, item)
    if operational_unit_id:
        item['operational_unit_id'] = operational_unit_id
    return item


def get_unit_by_id(connection, unit_id):
    row = connection.execute('SELECT id, company_id, name, unit_type, city, notes FROM units WHERE id = ?', (unit_id,)).fetchone()
    return row_to_dict(row) if row else None


def parse_epi_joinventures(raw_value):
    try:
        parsed = json.loads(str(raw_value or '[]'))
    except Exception:
        raise ValueError(MSG_JOINVENTURE_INVALID)
    if not isinstance(parsed, list):
        raise ValueError(MSG_JOINVENTURE_INVALID)
    normalized = []
    for entry in parsed:
        if isinstance(entry, str):
            name = entry.strip()
            unit_id = None
            if '@@' in name:
                name_part, unit_part = name.split('@@', 1)
                name = str(name_part or '').strip()
                unit_id = int(unit_part) if str(unit_part or '').strip().isdigit() else None
            if not name:
                continue
            normalized.append({'name': name, 'unit_id': unit_id})
            continue
        if not isinstance(entry, dict):
            raise ValueError('JoinVenture inválida.')
        name = str(entry.get('name', '')).strip()
        if not name:
            continue
        raw_unit_id = entry.get('unit_id')
        unit_id = None if raw_unit_id in (None, '') else int(raw_unit_id)
        normalized.append({'name': name, 'unit_id': unit_id})
    return normalized


def normalize_active_joinventure_name(value):
    raw = str(value or '').strip()
    if '@@' in raw:
        raw = raw.split('@@', 1)[0]
    return raw.strip()


def resolve_epi_scope_unit(connection, actor, payload, joinventures_values, active_joinventure):
    requested_company_id = int(payload['company_id'])
    raw_unit = str(payload.get('unit_id', '')).strip()
    requested_unit_id = None if raw_unit in ('', '__ALL_UNITS__') else int(raw_unit)
    if requested_unit_id:
        unit = get_unit_by_id(connection, requested_unit_id)
        ensure_resource_company(actor, unit, 'Unidade')
        if int(unit['company_id']) != requested_company_id:
            raise ValueError('Unidade e empresa do EPI precisam ser compatíveis.')
    normalized_active = normalize_active_joinventure_name(active_joinventure)
    if normalized_active:
        matching = [entry for entry in joinventures_values if str(entry['name']).strip().lower() == normalized_active.lower()]
        if not matching:
            raise ValueError('JoinVenture ativa precisa existir na lista de JoinVentures.')
        unit_ids = sorted({entry.get('unit_id') for entry in matching if entry.get('unit_id')})
        if not unit_ids:
            if requested_unit_id:
                unit_ids = [requested_unit_id]
            else:
                raise ValueError('JoinVenture ativa precisa possuir unidade vinculada.')
        if len(unit_ids) > 1:
            raise ValueError('JoinVenture ativa está vinculada a múltiplas unidades. Ajuste o cadastro.')
        required_unit_id = int(unit_ids[0])
        required_unit = get_unit_by_id(connection, required_unit_id)
        ensure_resource_company(actor, required_unit, 'Unidade')
        if int(required_unit['company_id']) != requested_company_id:
            raise ValueError('JoinVenture e empresa do EPI precisam ser compatíveis.')
        if requested_unit_id and requested_unit_id != required_unit_id:
            raise ValueError('Unidade incompatível com a JoinVenture ativa.')
        return required_unit_id
    return requested_unit_id


def epi_context_signature(unit_id, active_joinventure):
    normalized_unit = int(unit_id) if unit_id else 0
    normalized_jv = str(active_joinventure or '').strip().lower()
    if not normalized_unit and not normalized_jv:
        return 'global'
    return f'unit:{normalized_unit}|jv:{normalized_jv}'


def validate_epi_uniqueness(connection, company_id, unit_id, active_joinventure, name, purchase_code, exclude_id=None):
    normalized_name = str(name or '').strip()
    normalized_code = str(purchase_code or '').strip()
    if not normalized_name:
        raise ValueError('Nome completo do EPI é obrigatório.')
    if not normalized_code:
        raise ValueError('Código do EPI é obrigatório.')

    params = [int(company_id), normalized_name.lower()]
    sql = 'SELECT id, unit_id, active_joinventure FROM epis WHERE company_id = ? AND LOWER(TRIM(name)) = ?'
    if exclude_id:
        sql += ' AND id <> ?'
        params.append(int(exclude_id))
    name_matches = connection.execute(sql, tuple(params)).fetchall()
    incoming_scope = epi_context_signature(unit_id, active_joinventure)
    for row in name_matches:
        if epi_context_signature(row['unit_id'], row['active_joinventure']) == incoming_scope:
            raise ValueError('Já existe EPI com o mesmo Nome completo neste contexto (empresa/unidade/Joint Venture).')

    code_params = [int(company_id), normalized_code.lower()]
    code_sql = 'SELECT id FROM epis WHERE company_id = ? AND LOWER(TRIM(purchase_code)) = ?'
    if exclude_id:
        code_sql += ' AND id <> ?'
        code_params.append(int(exclude_id))
    code_match = connection.execute(code_sql + ' LIMIT 1', tuple(code_params)).fetchone()
    if code_match:
        raise ValueError('Código do EPI já cadastrado nesta empresa.')


def get_employee_by_id(connection, employee_id):
    row = connection.execute('SELECT id, company_id, unit_id, employee_id_code, name, sector, role_name, admission_date, schedule_type FROM employees WHERE id = ?', (employee_id,)).fetchone()
    return row_to_dict(row) if row else None


def get_epi_by_id(connection, epi_id):
    row = connection.execute('SELECT id, company_id, unit_id, name, purchase_code, ca, sector, epi_section, stock, minimum_stock, unit_measure, ca_expiry, epi_validity_date, manufacture_date, validity_days, validity_years, validity_months, manufacturer_validity_months, manufacturer, model_reference, supplier_company, manufacturer_recommendations, epi_photo_data, glove_size, size, uniform_size, joinventures_json, active_joinventure, qr_code_value FROM epis WHERE id = ?', (epi_id,)).fetchone()
    return row_to_dict(row) if row else None


def require_actor(connection, actor_user_id):
    actor = get_user_by_id(connection, int(actor_user_id))
    if not actor or not int(actor['active']):
        raise PermissionError('Usuário executor inválido.')
    if actor.get('role') != 'master_admin' and actor.get('company_id'):
        enforce_company_block_rules(connection, int(actor['company_id']))
    return actor


def ensure_permission(actor, action):
    if action not in PERMISSIONS.get(actor['role'], set()):
        raise PermissionError('Perfil sem permissão para esta ação.')


def ensure_company_access(actor, company_id):
    if actor['role'] == 'master_admin':
        return
    if str(actor.get('company_id') or '') != str(company_id or ''):
        raise PermissionError('Acesso permitido apenas para registros da própria empresa.')


def ensure_resource_company(actor, resource, label='Registro'):
    if not resource:
        raise ValueError(f'{label} não encontrado.')
    ensure_company_access(actor, resource.get('company_id'))


def authorize_action(connection, actor_user_id, action, company_id=None):
    actor = require_actor(connection, actor_user_id)
    ensure_permission(actor, action)
    if company_id is not None:
        ensure_company_access(actor, company_id)
    return actor


def authorize_user_management(connection, actor_user_id, operation='create', target_role=None, target_user_id=None, target_company_id=None):
    action = {'create': 'users:create', 'update': 'users:update', 'delete': 'users:delete'}[operation]
    actor = authorize_action(connection, actor_user_id, action)
    target = get_user_by_id(connection, target_user_id) if target_user_id else None

    if target_user_id and not target:
        raise ValueError('Usuário alvo não encontrado.')

    if actor['role'] == 'master_admin':
        if target_role == 'master_admin' and target_user_id is None:
            raise ValueError('Não é permitido criar outro Administrador Master por esta tela.')
        if target and target['role'] == 'master_admin':
            if target['id'] == actor['id']:
                if operation == 'delete':
                    raise ValueError('Não é permitido excluir o próprio usuário logado.')
                if target_role and ROLE_WEIGHT.get(target_role, 0) < ROLE_WEIGHT['master_admin']:
                    raise ValueError('Administrador Master não pode remover a própria administração.')
            else:
                raise ValueError('Administrador Master só pode ser gerenciado pelo bootstrap inicial do sistema.')
        return actor

    if actor['role'] in ('general_admin', 'registry_admin'):
        if target_role and target_role not in ('registry_admin', 'admin', 'user', 'employee'):
            raise ValueError('Perfil pode gerenciar apenas Administrador de Registro, Administrador Local, Gestor de EPI e Funcionário da própria empresa.')
        if target:
            if target['role'] not in ('registry_admin', 'admin', 'user', 'employee'):
                raise ValueError('Perfil pode alterar apenas Administrador de Registro, Administrador Local, Gestor de EPI e Funcionário.')
            ensure_company_access(actor, target.get('company_id'))
        if target_company_id:
            ensure_company_access(actor, target_company_id)
        return actor

    if actor['role'] == 'admin':
        raise PermissionError('Administrador Local não pode cadastrar/editar usuários da base principal.')

    raise PermissionError('Somente perfis administrativos podem gerenciar usuários.')

def resolve_target_company_id(actor, payload_company_id, payload_role, linked_employee_id=None):
    role = str(payload_role or '').strip()
    company_id = payload_company_id
    if actor['role'] in ('general_admin', 'registry_admin', 'admin') and not company_id:
        company_id = actor.get('company_id')
    has_linked_employee = linked_employee_id not in (None, '', 'null')
    if role in ('general_admin', 'registry_admin', 'admin', 'user', 'employee') and not company_id and not has_linked_employee:
        raise ValueError('Perfil com empresa exige uma empresa vinculada.')
    return int(company_id) if company_id not in (None, '', 'null') else None


def ensure_operational_role_link(connection, role, linked_employee_id, company_id):
    if role not in ('admin', 'user'):
        return
    if linked_employee_id in (None, '', 'null'):
        raise ValueError('Administrador Local e Gestor de EPI devem estar vinculados a um colaborador com unidade.')
    employee = get_employee_by_id(connection, int(linked_employee_id))
    if not employee:
        raise ValueError('Colaborador vinculado não encontrado para o perfil operacional.')
    if company_id and str(employee.get('company_id')) != str(company_id):
        raise ValueError('Colaborador vinculado precisa pertencer à mesma empresa do usuário.')
    if not employee.get('unit_id'):
        raise ValueError('Colaborador vinculado precisa possuir unidade principal definida.')


def build_employee_access_token():
    return secrets.token_urlsafe(32)


def resolve_user_employee_link(connection, actor, payload, company_id, allow_manual_create=False):
    linked_employee_id = payload.get('linked_employee_id')
    if linked_employee_id not in (None, '', 'null'):
        employee = get_employee_by_id(connection, int(linked_employee_id))
        if not employee:
            raise ValueError('Colaborador vinculado não encontrado.')
        ensure_company_access(actor, employee['company_id'])
        return int(employee['id']), int(employee['company_id'])

    if not allow_manual_create:
        raise ValueError('Selecione um colaborador em "Vincular colaborador".')

    employee_id_code = str(payload.get('employee_id_code', '')).strip()
    employee_role_name = str(payload.get('employee_role_name', '')).strip()
    employee_sector = str(payload.get('employee_sector', '')).strip()
    employee_schedule_type = str(payload.get('employee_schedule_type', '')).strip()
    employee_admission_date = str(payload.get('employee_admission_date', '')).strip()
    employee_unit_id = str(payload.get('employee_unit_id', '')).strip()
    employee_name = str(payload.get('employee_name') or payload.get('full_name') or '').strip()

    require_fields(
        {
            'employee_id_code': employee_id_code,
            'employee_role_name': employee_role_name,
            'employee_sector': employee_sector,
            'employee_schedule_type': employee_schedule_type,
            'employee_admission_date': employee_admission_date,
            'employee_name': employee_name
        },
        ['employee_id_code', 'employee_role_name', 'employee_sector', 'employee_schedule_type', 'employee_admission_date', 'employee_name']
    )

    datetime.strptime(employee_admission_date, '%Y-%m-%d')
    if not company_id:
        raise ValueError('Empresa obrigatória para criar colaborador sem vínculo.')

    ensure_company_access(actor, company_id)
    if employee_unit_id:
        unit = get_unit_by_id(connection, int(employee_unit_id))
        ensure_resource_company(actor, unit, 'Unidade')
        if int(unit['company_id']) != int(company_id):
            raise ValueError('A unidade selecionada precisa pertencer à empresa do usuário.')
        unit_id = int(unit['id'])
    else:
        default_unit = connection.execute('SELECT id FROM units WHERE company_id = ? ORDER BY id LIMIT 1', (company_id,)).fetchone()
        if not default_unit:
            raise ValueError('Empresa sem unidade cadastrada para criar colaborador.')
        unit_id = int(default_unit['id'])

    existing_code = connection.execute('SELECT id FROM employees WHERE employee_id_code = ?', (employee_id_code,)).fetchone()
    if existing_code:
        raise ValueError('ID do colaborador já cadastrado.')

    cursor = connection.execute(
        '''
        INSERT INTO employees (company_id, unit_id, employee_id_code, name, sector, role_name, admission_date, schedule_type)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''',
        (
            int(company_id),
            unit_id,
            employee_id_code,
            employee_name,
            employee_sector,
            employee_role_name,
            employee_admission_date,
            employee_schedule_type
        )
    )
    return int(cursor.lastrowid), int(company_id)

  
def parse_actor_user_id_from_query(parsed):
    return int(parse_qs(parsed.query).get('actor_user_id', ['0'])[0])


def build_reports(connection, actor, filters):
    clauses, params = [], []
    if filters.get('company_id'):
        ensure_company_access(actor, int(filters['company_id']))
        clauses.append('deliveries.company_id = ?')
        params.append(filters['company_id'])
    if filters.get('unit_id'):
        unit = get_unit_by_id(connection, int(filters['unit_id']))
        ensure_resource_company(actor, unit, 'Unidade')
        clauses.append('employees.unit_id = ?')
        params.append(filters['unit_id'])
    if filters.get('sector'):
        clauses.append('deliveries.sector = ?')
        params.append(filters['sector'])
    if filters.get('epi_id'):
        epi = get_epi_by_id(connection, int(filters['epi_id']))
        ensure_resource_company(actor, epi, 'EPI')
        clauses.append('deliveries.epi_id = ?')
        params.append(filters['epi_id'])
    if filters.get('start_date'):
        clauses.append('deliveries.delivery_date >= ?')
        params.append(filters['start_date'])
    if filters.get('end_date'):
        clauses.append('deliveries.delivery_date <= ?')
        params.append(filters['end_date'])
    where_clause = f"WHERE {' AND '.join(clauses)}" if clauses else ''
    deliveries = fetch_deliveries(connection, actor, where_clause, tuple(params))
    by_unit, by_sector, by_epi = {}, {}, {}
    for item in deliveries:
        by_unit[item['unit_name']] = by_unit.get(item['unit_name'], 0) + int(item['quantity'])
        by_sector[item['sector']] = by_sector.get(item['sector'], 0) + int(item['quantity'])
        by_epi[item['epi_name']] = by_epi.get(item['epi_name'], 0) + int(item['quantity'])
    return {'deliveries': deliveries, 'by_unit': by_unit, 'by_sector': by_sector, 'by_epi': by_epi, 'total_quantity': sum(int(item['quantity']) for item in deliveries)}


def build_bootstrap(connection, actor):
    return {'platform_brand': get_platform_brand(connection), 'commercial_settings': get_commercial_settings(connection), 'companies': fetch_companies(connection, None if actor['role'] == 'master_admin' else actor['company_id']), 'company_audit_logs': fetch_company_audit_logs(connection, actor), 'users': fetch_users(connection, actor), 'units': fetch_units(connection, actor), 'employees': fetch_employees(connection, actor), 'employee_movements': fetch_employee_movements(connection, actor), 'epis': fetch_epis(connection, actor), 'deliveries': fetch_deliveries(connection, actor), 'feedbacks': fetch_feedbacks(connection, actor), 'alerts': compute_alerts(connection, actor), 'permissions': sorted(PERMISSIONS.get(actor['role'], set()))}


def build_low_stock(connection, actor):
    items = []
    clauses = []
    params = []
    if actor and actor['role'] != 'master_admin':
        clauses.append('s.company_id = ?')
        params.append(actor['company_id'])
    scope_unit_id = actor_operational_unit_id(connection, actor)
    if scope_unit_id:
        clauses.append('s.unit_id = ?')
        params.append(scope_unit_id)
    scope_clause = f"WHERE {' AND '.join(clauses)}" if clauses else ''
    rows = connection.execute(
        f'''
        SELECT s.company_id, s.unit_id, s.epi_id, s.quantity AS stock, units.name AS unit_name,
               companies.name AS company_name, epis.name AS epi_name, epis.minimum_stock, epis.unit_measure
        FROM unit_epi_stock s
        JOIN units ON units.id = s.unit_id
        JOIN companies ON companies.id = s.company_id
        JOIN epis ON epis.id = s.epi_id
        {scope_clause}
        ''',
        tuple(params)
    ).fetchall()
    for row in rows:
        stock = int(row['stock'] or 0)
        minimum = int(row['minimum_stock'] or 10)
        if stock <= minimum:
            items.append({
                'epi_id': row['epi_id'],
                'epi_name': row['epi_name'],
                'company_id': row['company_id'],
                'company_name': row['company_name'],
                'unit_id': row['unit_id'],
                'unit_name': row.get('unit_name') or '-',
                'stock': stock,
                'minimum_stock': minimum,
                'unit_measure': row.get('unit_measure') or 'unidade'
            })
    items.sort(key=lambda row: (row['company_name'], row['unit_name'], row['epi_name']))
    return {'items': items}


def auth_diagnostics():
    parsed_db = urlparse(DATABASE_URL) if DATABASE_URL else None
    host = parsed_db.hostname if parsed_db else ''
    return {
        'database_configured': bool(DATABASE_URL),
        'database_host': host,
        'database_provider': 'supabase' if 'supabase' in str(host).lower() else 'custom_postgres',
        'db_connector_available': DB_CONNECTOR_AVAILABLE,
        'bcrypt_available': BCRYPT_AVAILABLE,
        'jwt_exp_seconds': JWT_EXP_SECONDS,
        'jwt_secret_default': JWT_SECRET == 'change-this-jwt-secret',
        'password_recovery_key_configured': bool(PASSWORD_RECOVERY_KEY)
    }

class EpiHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(BASE_DIR), **kwargs)

    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == '/health':
            return send_json(self, 200, {'status': 'ok'})

        if parsed.path == '/':
            self.path = '/index.html'
            return super().do_GET()

        try:
            if parsed.path == '/api/auth-diagnostics':
                return send_json(self, 200, auth_diagnostics())

            if parsed.path == '/api/db-pool/status':
                with closing(get_connection()) as connection:
                    actor = authorize_action(
                        connection,
                        resolve_actor_user_id(self, parsed),
                        'dashboard:view'
                    )
                    if actor.get('role') != 'master_admin':
                        raise PermissionError('Somente Administrador Master pode consultar o status do pool.')
                    return send_json(self, 200, {'pool': db_pool_status()})

            if parsed.path == '/api/bootstrap':
                with closing(get_connection()) as connection:
                    actor = authorize_action(
                        connection,
                        resolve_actor_user_id(self, parsed),
                        'dashboard:view'
                    )
                    return send_json(self, 200, build_bootstrap(connection, actor))

            if parsed.path == '/api/reports':
                with closing(get_connection()) as connection:
                    actor = authorize_action(
                        connection,
                        resolve_actor_user_id(self, parsed),
                        'reports:view'
                    )
                    filters = {
                        key: values[0]
                        for key, values in parse_qs(parsed.query).items()
                        if key != 'actor_user_id'
                    }
                    return send_json(self, 200, build_reports(connection, actor, filters))

            if parsed.path == '/api/stock/low':
                with closing(get_connection()) as connection:
                    actor = authorize_action(
                        connection,
                        resolve_actor_user_id(self, parsed),
                        'stock:view'
                    )
                    return send_json(self, 200, build_low_stock(connection, actor))

            if parsed.path == '/api/stock/epis':
                with closing(get_connection()) as connection:
                    actor = authorize_action(
                        connection,
                        resolve_actor_user_id(self, parsed),
                        'stock:view'
                    )
                    query = parse_qs(parsed.query)
                    company_filter = actor['company_id'] if actor['role'] != 'master_admin' else query.get('company_id', [''])[0]
                    scope_unit_id = actor_operational_unit_id(connection, actor)
                    if actor.get('role') in ('admin', 'user') and not scope_unit_id:
                        raise PermissionError('Perfil sem unidade operacional ativa para consultar estoque.')
                    unit_filter = scope_unit_id or query.get('unit_id', [''])[0]
                    company_scope_id = int(company_filter or 0)
                    if unit_filter and not company_scope_id:
                        unit_row = get_unit_by_id(connection, int(unit_filter))
                        company_scope_id = int(unit_row['company_id']) if unit_row else 0
                    protection = str(query.get('protection', [''])[0]).strip().lower()
                    name = str(query.get('name', [''])[0]).strip().lower()
                    section = str(query.get('section', [''])[0]).strip().lower()
                    manufacturer = str(query.get('manufacturer', [''])[0]).strip().lower()
                    ca = str(query.get('ca', [''])[0]).strip().lower()
                    if unit_filter:
                        epis = fetch_epis_from_unit_stock(
                            connection,
                            actor if actor['role'] != 'master_admin' else None,
                            int(company_scope_id),
                            int(unit_filter)
                        )
                    else:
                        epis = fetch_epis(connection, actor if actor['role'] != 'master_admin' else None, unit_filter)
                    items = []
                    for epi in epis:
                        if company_filter and str(epi.get('company_id')) != str(company_filter):
                            continue
                        if protection and protection not in str(epi.get('sector') or '').lower():
                            continue
                        if name and name not in str(epi.get('name') or '').lower():
                            continue
                        if section and section not in str(epi.get('epi_section') or '').lower():
                            continue
                        if manufacturer and manufacturer not in str(epi.get('manufacturer') or '').lower():
                            continue
                        if ca and ca not in str(epi.get('ca') or '').lower():
                            continue
                        stock_unit_id = int(unit_filter or 0)
                        stock_row = get_unit_stock(connection, int(epi['company_id']), stock_unit_id, int(epi['id'])) if stock_unit_id else None
                        item = dict(epi)
                        item['stock'] = int((stock_row or {}).get('quantity') or (item.get('stock') or 0))
                        size_rows = fetch_epi_size_balance(connection, int(epi['company_id']), stock_unit_id, int(epi['id'])) if stock_unit_id else []
                        item['size_balances'] = size_rows
                        items.append(item)
                    return send_json(self, 200, {'items': items})

            if parsed.path == '/api/requests':
                with closing(get_connection()) as connection:
                    actor = authorize_action(
                        connection,
                        resolve_actor_user_id(self, parsed),
                        'deliveries:view'
                    )
                    query = parse_qs(parsed.query)
                    company_filter = actor['company_id'] if actor['role'] != 'master_admin' else query.get('company_id', [''])[0]
                    scope_unit_id = actor_operational_unit_id(connection, actor)
                    clauses, params = [], []
                    if company_filter:
                        clauses.append('r.company_id = ?')
                        params.append(int(company_filter))
                    if scope_unit_id:
                        clauses.append('r.unit_id = ?')
                        params.append(int(scope_unit_id))
                    final_where = f"WHERE {' AND '.join(clauses)}" if clauses else ''
                    rows = connection.execute(
                        f'''
                        SELECT r.*, employees.name AS employee_name, employees.employee_id_code, units.name AS unit_name,
                               epis.name AS epi_name
                        FROM epi_requests r
                        JOIN employees ON employees.id = r.employee_id
                        JOIN units ON units.id = r.unit_id
                        JOIN epis ON epis.id = r.epi_id
                        {final_where}
                        ORDER BY r.requested_at DESC, r.id DESC
                        ''',
                        tuple(params)
                    ).fetchall()
                    return send_json(self, 200, {'items': [row_to_dict(item) for item in rows]})

            if parsed.path == '/api/fichas':
                with closing(get_connection()) as connection:
                    actor = authorize_action(
                        connection,
                        resolve_actor_user_id(self, parsed),
                        'fichas:view'
                    )
                    clauses = []
                    params = []
                    if actor['role'] != 'master_admin':
                        clauses.append('fp.company_id = ?')
                        params.append(actor['company_id'])
                    employee_id = parse_qs(parsed.query).get('employee_id', [''])[0]
                    if employee_id:
                        clauses.append('fp.employee_id = ?')
                        params.append(int(employee_id))
                    final_where = f"WHERE {' AND '.join(clauses)}" if clauses else ''
                    periods = connection.execute(
                        f'''
                        SELECT fp.*, employees.name AS employee_name, employees.employee_id_code, units.name AS unit_name
                        FROM epi_ficha_periods fp
                        JOIN employees ON employees.id = fp.employee_id
                        JOIN units ON units.id = fp.unit_id
                        {final_where}
                        ORDER BY fp.period_start DESC, fp.id DESC
                        ''',
                        tuple(params)
                    ).fetchall()
                    return send_json(self, 200, {'items': [row_to_dict(item) for item in periods]})

            if parsed.path == '/api/employee-access':
                token = parse_qs(parsed.query).get('token', [''])[0].strip()
                with closing(get_connection()) as connection:
                    employee_user = resolve_external_employee_context(connection, token)
                    if not employee_user:
                        portal = connection.execute(
                            '''
                            SELECT employee_portal_links.*, employees.name AS employee_name, employees.employee_id_code,
                                   employees.schedule_type, companies.name AS company_name
                            FROM employee_portal_links
                            JOIN employees ON employees.id = employee_portal_links.employee_id
                            JOIN companies ON companies.id = employee_portal_links.company_id
                            WHERE employee_portal_links.token = ? AND employee_portal_links.active = 1
                            ''',
                            (token,)
                        ).fetchone()
                        if not portal:
                            raise PermissionError(MSG_TOKEN_EXPIRED_ACCESS)
                        employee_user = {
                            'employee_id': int(portal['employee_id']),
                            'linked_employee_id': int(portal['employee_id']),
                            'employee_name': portal['employee_name'],
                            'employee_id_code': portal['employee_id_code'],
                            'schedule_type': portal['schedule_type'],
                            'company_name': portal['company_name']
                        }
                    employee_id = int(employee_user['employee_id'])
                    deliveries = connection.execute(
                        '''
                        SELECT deliveries.id, deliveries.delivery_date, deliveries.next_replacement_date, deliveries.quantity, deliveries.quantity_label,
                               deliveries.signature_name, deliveries.signature_at, deliveries.signature_ip,
                               epis.name AS epi_name, epis.purchase_code, epis.ca, epis.epi_validity_date
                        FROM deliveries
                        JOIN epis ON epis.id = deliveries.epi_id
                        WHERE deliveries.employee_id = ?
                        ORDER BY deliveries.delivery_date DESC, deliveries.id DESC
                        ''',
                        (employee_id,)
                    ).fetchall()
                    fichas = connection.execute(
                        '''
                        SELECT fp.id, fp.period_start, fp.period_end, fp.status, fp.batch_signature_name, fp.batch_signature_at
                        FROM epi_ficha_periods fp
                        WHERE fp.employee_id = ?
                        ORDER BY fp.period_start DESC
                        ''',
                        (employee_id,)
                    ).fetchall()
                    requests = connection.execute(
                        '''
                        SELECT r.id, r.epi_id, r.quantity, r.status, r.justification, r.requested_at, r.last_updated_at,
                               epis.name AS epi_name, epis.purchase_code
                        FROM epi_requests r
                        JOIN epis ON epis.id = r.epi_id
                        WHERE r.employee_id = ?
                        ORDER BY r.requested_at DESC, r.id DESC
                        ''',
                        (employee_id,)
                    ).fetchall()
                    feedbacks = connection.execute(
                        '''
                        SELECT f.id, f.epi_id, f.comfort_rating, f.quality_rating, f.adequacy_rating, f.performance_rating,
                               f.comments, f.improvement_suggestion, f.suggested_new_epi_name, f.suggested_new_epi_notes,
                               f.status, f.created_at, f.updated_at, epis.name AS epi_name, epis.purchase_code
                        FROM epi_feedbacks f
                        LEFT JOIN epis ON epis.id = f.epi_id
                        WHERE f.employee_id = ?
                        ORDER BY f.created_at DESC, f.id DESC
                        ''',
                        (employee_id,)
                    ).fetchall()

                   
                    available_epis = connection.execute(
                        '''
                        SELECT id, name, purchase_code, ca, unit_measure
                        FROM epis
                        WHERE company_id = ? AND active = 1
                        ORDER BY name ASC
                        ''',
                        (int(employee_user['company_id']),)
                    ).fetchall()

                    available_epis = connection.execute(
                        '''
                        SELECT id, name, purchase_code, ca, unit_measure
                        FROM epis
                        WHERE company_id = ? AND active = 1
                        ORDER BY name ASC
                        ''',
                        (int(employee_user['company_id']),)
                    ).fetchall()

                    fichas = connection.execute(
                        '''
                        SELECT fp.id, fp.period_start, fp.period_end, fp.status, fp.batch_signature_name, fp.batch_signature_at
                        FROM epi_ficha_periods fp
                        WHERE fp.employee_id = ?
                        ORDER BY fp.period_start DESC
                        ''',
                        (employee_user['linked_employee_id'],)
                    ).fetchall()
                
                    available_epis = connection.execute(
                        '''
                        SELECT id, name, purchase_code, ca, unit_measure
                        FROM epis
                        WHERE company_id = ? AND active = 1
                        ORDER BY name ASC
                        ''',
                        (int(employee_user['company_id']),)
                    ).fetchall()
                    register_employee_portal_audit(
                        connection,
                        employee_user,
                        'portal_access',
                        ip_address=str(getattr(self, 'client_address', ('',))[0] or ''),
                        user_agent=self.headers.get('User-Agent', ''),
                        payload={'path': parsed.path}
                    )
                    connection.commit()
                    return send_json(
                        self,
                        200,
                        {
                            'employee': employee_user,
                            'deliveries': [row_to_dict(item) for item in deliveries],
                            'fichas': [row_to_dict(item) for item in fichas],
                            'requests': [row_to_dict(item) for item in requests],
                            'feedbacks': [row_to_dict(item) for item in feedbacks],
                            'available_epis': [row_to_dict(item) for item in available_epis]
                        }
                    )
                    register_employee_portal_audit(
                        connection,
                        employee_user,
                        'portal_access',
                        ip_address=str(getattr(self, 'client_address', ('',))[0] or ''),
                        user_agent=self.headers.get('User-Agent', ''),
                        payload={'path': parsed.path}
                    )
                    connection.commit()
                    return send_json(
                        self,
                        200,
                        {
                            'employee': employee_user,
                            'deliveries': [row_to_dict(item) for item in deliveries],
                            'fichas': [row_to_dict(item) for item in fichas],
                            'requests': [row_to_dict(item) for item in requests],
                            'feedbacks': [row_to_dict(item) for item in feedbacks],
                            'available_epis': [row_to_dict(item) for item in available_epis]
                        }
                    )

            if parsed.path == '/api/employee-access/pdf':
                token = parse_qs(parsed.query).get('token', [''])[0].strip()
                with closing(get_connection()) as connection:
                    employee_user = resolve_external_employee_context(connection, token)
                    if not employee_user:
                        raise PermissionError('Token de acesso inválido ou expirado.')
                    if not employee_user.get('linked_employee_id'):
                        employee_user['linked_employee_id'] = employee_user.get('employee_id')
                    pdf_bytes = build_employee_ficha_pdf(connection, employee_user)
                    return send_bytes(self, 200, 'application/pdf', pdf_bytes, f"ficha-epi-{employee_user['employee_id_code']}.pdf")

            return super().do_GET()

        except PermissionError as exc:
            structured_log('warning', 'http.permission_error', method='GET', path=parsed.path, error=str(exc))
            return forbidden(self, str(exc))
        except ValueError as exc:
            structured_log('warning', 'http.value_error', method='GET', path=parsed.path, error=str(exc))
            return bad_request(self, str(exc))
        except Exception as exc:
            structured_log('error', 'http.unhandled_error', method='GET', path=parsed.path, error=str(exc))
            return send_json(self, 500, {'error': str(exc)})

    def do_POST(self):
        parsed = urlparse(self.path)

        try:
            payload = parse_json(self)
        except json.JSONDecodeError:
            return bad_request(self, 'JSON inválido.')

        try:
            with closing(get_connection()) as connection:
                company_block_match = re.match(r'^/api/companies/(\d+)/block-status$', parsed.path or '')
                if company_block_match:
                    actor_user_id = resolve_actor_user_id(self, parsed, payload)
                    actor = authorize_action(connection, actor_user_id, 'companies:license')
                    company_id = int(company_block_match.group(1))
                    company = get_company_by_id(connection, company_id)
                    if not company:
                        raise ValueError(MSG_COMPANY_NOT_FOUND)

                    mark_payment_overdue = str(payload.get('mark_payment_overdue', '')).lower() in ('1', 'true', 'yes', 'on')
                    if mark_payment_overdue and company.get('license_status') != 'suspended':
                        connection.execute(
                            "UPDATE companies SET license_status = 'suspended' WHERE id = ?",
                            (company_id,)
                        )
                        register_company_audit(
                            connection,
                            company_id,
                            actor,
                            'suspend',
                            'Licença suspensa automaticamente por atraso de pagamento.',
                            [{
                                'field': 'Status da licença',
                                'before': str(company.get('license_status') or 'active'),
                                'after': 'suspended'
                            }]
                        )
                        connection.commit()

                    status = evaluate_company_block_status(connection, company_id, persist_expiration=True)
                    return send_json(self, 200, status)

                elif parsed.path == '/api/employee-unit-movements':
                    require_fields(payload, ['actor_user_id', 'employee_id', 'target_unit_id', 'movement_type', 'start_date'])

                    actor_user_id = resolve_actor_user_id(self, parsed, payload)
                    actor = authorize_action(connection, actor_user_id, 'employees:update')
                    employee = get_employee_by_id(connection, int(payload['employee_id']))
                    if not employee:
                        raise ValueError(MSG_EMPLOYEE_NOT_FOUND)

                    ensure_resource_company(actor, employee, 'Colaborador')

                    target_unit = get_unit_by_id(connection, int(payload['target_unit_id']))
                    if not target_unit:
                        raise ValueError('Unidade de destino não encontrada.')

                    ensure_resource_company(actor, target_unit, 'Unidade de destino')

                    if int(target_unit['id']) == int(employee['unit_id']):
                        raise ValueError('A unidade de destino deve ser diferente da unidade atual do colaborador.')

                    movement_type = str(payload.get('movement_type', '')).strip().lower()
                    if movement_type not in ('temporary', 'definitive'):
                        raise ValueError("Tipo de movimentação inválido. Use 'temporary' ou 'definitive'.")

                    start_date = str(payload.get('start_date', '')).strip()
                    end_date = str(payload.get('end_date', '')).strip()

                    datetime.strptime(start_date, '%Y-%m-%d')
                    if end_date:
                        datetime.strptime(end_date, '%Y-%m-%d')
                        if end_date < start_date:
                            raise ValueError('Data final não pode ser menor que a data inicial.')

                    if movement_type == 'temporary':
                        connection.execute(
                            "UPDATE employee_unit_movements SET end_date = ? WHERE employee_id = ? AND movement_type = 'temporary' AND COALESCE(NULLIF(end_date, ''), '9999-12-31') >= ?",
                            (start_date, employee['id'], start_date)
                        )

                    if movement_type == 'definitive' and not end_date:
                        end_date = start_date

                    source_unit_id = int(employee['unit_id'])
                    connection.execute(
                        '''
                        INSERT INTO employee_unit_movements (
                            employee_id, company_id, source_unit_id, target_unit_id,
                            movement_type, start_date, end_date, notes,
                            actor_user_id, actor_name, created_at
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''',
                        (
                            employee['id'],
                            employee['company_id'],
                            source_unit_id,
                            int(target_unit['id']),
                            movement_type,
                            start_date,
                            end_date,
                            str(payload.get('notes', '')).strip(),
                            actor['id'],
                            actor['full_name'],
                            datetime.now().isoformat(timespec='seconds')
                        )
                    )

                    if movement_type == 'definitive':
                        connection.execute(
                            'UPDATE employees SET unit_id = ? WHERE id = ?',
                            (int(target_unit['id']), employee['id'])
                        )
                        connection.execute(
                            "UPDATE employee_unit_movements SET end_date = ? WHERE employee_id = ? AND movement_type = 'temporary' AND COALESCE(NULLIF(end_date, ''), '9999-12-31') >= ?",
                            (start_date, employee['id'], start_date)
                        )

                    connection.commit()
                    return send_json(self, 200, {'ok': True})

                elif parsed.path == '/api/users':
                    require_fields(payload, ['actor_user_id', 'username', 'full_name', 'role', 'password'])

                    actor_user_id = resolve_actor_user_id(self, parsed, payload)
                    actor = authorize_user_management(
                        connection,
                        actor_user_id,
                        'create',
                        payload['role'],
                        None,
                        payload.get('company_id')
                    )


                    role = str(payload.get('role', '')).strip()
                    if role not in ROLE_WEIGHT:
                        raise ValueError('Perfil de usuário inválido.')
                    if role == 'employee' and actor['role'] not in ('master_admin', 'general_admin', 'registry_admin'):
                        raise PermissionError('Somente Master, Geral e Registro podem criar perfil Funcionário.')

                    password = hash_password(payload.get('password'))
                    company_id = resolve_target_company_id(actor, payload.get('company_id'), role, payload.get('linked_employee_id'))
                    allow_manual_link = actor['role'] in ('master_admin', 'general_admin')
                    linked_employee_id, company_id = resolve_user_employee_link(
                        connection,
                        actor,
                        payload,
                        company_id,
                        allow_manual_create=allow_manual_link and str(payload.get('linked_employee_id', '')).strip() == ''
                    )
                    ensure_operational_role_link(connection, role, linked_employee_id, company_id)
                    if company_id and int(payload.get('active', 1)) == 1:
                        ensure_company_user_limit(connection, company_id)

                    employee_access_token = build_employee_access_token() if role == 'employee' else ''
                    connection.execute(
                        '''
                        INSERT INTO users (username, password, full_name, role, company_id, active, linked_employee_id, employee_access_token, employee_access_expires_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''',
                        (
                            str(payload.get('username', '')).strip(),
                            password,
                            str(payload.get('full_name', '')).strip(),
                            role,
                            company_id,
                            int(payload.get('active', 1) or 1),
                            linked_employee_id,
                            employee_access_token,
                            ''
                        )
                    )

                    connection.commit()
                    return send_json(self, 201, {'ok': True, 'message': 'Usuário criado com sucesso.'})

                elif parsed.path == '/api/employee-sign':
                    require_fields(payload, ['token', 'delivery_id'])
                    token = str(payload.get('token', '')).strip()
                    with_name = str(payload.get('signature_name', '')).strip()
                    with_data = str(payload.get('signature_data', '')).strip()
                    if not with_name and not with_data:
                        raise ValueError('Informe o nome da assinatura ou desenhe no canvas.')

                    employee_user = resolve_external_employee_context(connection, token)
                    if not employee_user:
                        raise PermissionError('Token de acesso inválido ou expirado.')

                    delivery = connection.execute(
                        'SELECT id, employee_id FROM deliveries WHERE id = ?',
                        (int(payload.get('delivery_id')),)
                    ).fetchone()
                    if not delivery:
                        raise ValueError('Entrega não encontrada.')
                    if int(delivery['employee_id']) != int(employee_user['employee_id']):
                        raise PermissionError('Entrega não pertence ao funcionário informado.')

                    connection.execute(
                        '''
                        UPDATE deliveries
                        SET signature_name = ?, signature_data = ?, signature_at = ?, signature_ip = ?
                        WHERE id = ?
                        ''',
                        (
                            with_name or employee_user.get('employee_name') or MSG_SIGNED_DIGITALLY,
                            with_data,
                            datetime.now(UTC).isoformat(),
                            str(getattr(self, 'client_address', ('',))[0] or ''),
                            int(payload.get('delivery_id'))
                        )
                    )
                    register_employee_portal_audit(
                        connection,
                        employee_user,
                        'sign_delivery_item',
                        ip_address=str(getattr(self, 'client_address', ('',))[0] or ''),
                        user_agent=self.headers.get('User-Agent', ''),
                        payload={'delivery_id': int(payload.get('delivery_id'))}
                    )
                    
                    connection.commit()
                    return send_json(self, 200, {'ok': True})

                elif parsed.path == '/api/employee-sign-batch':
                    require_fields(payload, ['token', 'ficha_period_id'])
                    token = str(payload.get('token', '')).strip()
                    signature_name = str(payload.get('signature_name', '')).strip()
                    signature_data = str(payload.get('signature_data', '')).strip()
                    if not signature_name and not signature_data:
                        raise ValueError('Assinatura obrigatória.')
                    employee_user = resolve_external_employee_context(connection, token)
                    if not employee_user:
                        raise PermissionError('Token de acesso inválido ou expirado.')
                    employee_id = int(employee_user['employee_id'])
                    ficha = connection.execute('SELECT id, employee_id FROM epi_ficha_periods WHERE id = ?', (int(payload['ficha_period_id']),)).fetchone()
                    if not ficha or int(ficha['employee_id']) != employee_id:
                        raise PermissionError('Ficha não pertence ao funcionário.')
                    now = datetime.now(UTC).isoformat()
                    client_ip = str(getattr(self, 'client_address', ('',))[0] or '')
                    connection.execute(
                        '''
                        UPDATE epi_ficha_periods
                        SET status = 'signed', batch_signature_name = ?, batch_signature_data = ?, batch_signature_ip = ?, batch_signature_at = ?, updated_at = ?
                        WHERE id = ?
                        ''',
                        (signature_name or 'Assinado digitalmente', signature_data, client_ip, now, now, int(ficha['id']))
                    )
                    connection.execute(
                        '''
                        UPDATE epi_ficha_items
                        SET item_signature_name = ?, item_signature_data = ?, item_signature_ip = ?, item_signature_at = ?, signed_mode = 'batch', updated_at = ?
                        WHERE ficha_period_id = ? AND COALESCE(item_signature_at, '') = ''
                        ''',
                        (signature_name or 'Assinado digitalmente', signature_data, client_ip, now, now, int(ficha['id']))
                    )
                    register_employee_portal_audit(
                        connection,
                        employee_user,
                        'sign_batch_period',
                        ip_address=client_ip,
                        user_agent=self.headers.get('User-Agent', ''),
                        payload={'ficha_period_id': int(ficha['id'])}
                    )
                    connection.commit()
                    return send_json(self, 200, {'ok': True})

                elif parsed.path == '/api/employee-lookup':
                    require_fields(payload, ['actor_user_id', 'employee_qr_code'])
                    actor = authorize_action(connection, resolve_actor_user_id(self, parsed, payload), 'deliveries:create')
                    qr_value = str(payload.get('employee_qr_code', '')).strip()
                    lookup_token = ''
                    if qr_value.startswith('http://') or qr_value.startswith('https://'):
                        parsed_link = urlparse(qr_value)
                        query_values = parse_qs(parsed_link.query or '')
                        lookup_token = str((query_values.get('employee_token') or query_values.get('token') or [''])[0]).strip()
                    elif len(qr_value) > 20 and '-' in qr_value:
                        lookup_token = qr_value
                    params = [qr_value]
                    token_clause = ''
                    if lookup_token:
                        params.append(lookup_token)
                        token_clause = ' OR employee_portal_links.token = ?'
                    row = connection.execute(
                        f'''
                        SELECT employees.id, employees.company_id, employees.unit_id, employees.employee_id_code, employees.name,
                               employees.sector, employees.role_name, employees.schedule_type,
                               employee_portal_links.qr_code_value, employee_portal_links.token
                        FROM employee_portal_links
                        JOIN employees ON employees.id = employee_portal_links.employee_id
                        WHERE employee_portal_links.active = 1
                          AND (employee_portal_links.qr_code_value = ?{token_clause})
                        ''',
                        tuple(params)
                    ).fetchone()
                    if not row:
                        raise ValueError('Link do funcionário não encontrado.')
                        raise ValueError('QR/link do funcionário não encontrado.')
                    ensure_resource_company(actor, row, 'Colaborador')
                    return send_json(self, 200, {'employee': row_to_dict(row)})

                elif parsed.path == '/api/employee-portal-link':
                    require_fields(payload, ['actor_user_id', 'employee_id'])
                    actor = authorize_action(connection, resolve_actor_user_id(self, parsed, payload), 'deliveries:create')
                    employee = get_employee_by_id(connection, int(payload['employee_id']))
                    if not employee:
                        raise ValueError('Colaborador não encontrado.')
                    ensure_actor_employee_scope(connection, actor, employee)
                    token = secrets.token_urlsafe(24)
                    access_link = f"{request_base_url(self)}/?employee_token={token}"
                    qr_code_value = access_link
                    now = datetime.now(UTC).isoformat()
                    expires_at = (datetime.now(UTC) + timedelta(days=180)).isoformat()
                    existing = connection.execute('SELECT id FROM employee_portal_links WHERE employee_id = ?', (int(employee['id']),)).fetchone()
                    if existing:
                        connection.execute(
                            '''
                            UPDATE employee_portal_links
                            SET token = ?, qr_code_value = ?, active = 1, expires_at = ?, updated_at = ?
                            WHERE employee_id = ?
                            ''',
                            (token, qr_code_value, expires_at, now, int(employee['id']))
                        )
                    else:
                        connection.execute(
                            '''
                            INSERT INTO employee_portal_links (
                                company_id, employee_id, token, qr_code_value, active, expires_at,
                                created_by_user_id, created_at, updated_at
                            ) VALUES (?, ?, ?, ?, 1, ?, ?, ?, ?)
                            ''',
                            (int(employee['company_id']), int(employee['id']), token, qr_code_value, expires_at, int(actor['id']), now, now)
                        )
                    connection.commit()
                    return send_json(self, 200, {'ok': True, 'token': token, 'qr_code_value': qr_code_value, 'access_link': access_link, 'expires_at': expires_at})

                elif parsed.path == '/api/employee-portal-link/revoke':
                    require_fields(payload, ['actor_user_id', 'employee_id'])
                    actor = authorize_action(connection, resolve_actor_user_id(self, parsed, payload), 'deliveries:create')
                    employee = get_employee_by_id(connection, int(payload['employee_id']))
                    if not employee:
                        raise ValueError('Colaborador não encontrado.')
                    ensure_actor_employee_scope(connection, actor, employee)
                    connection.execute(
                        "UPDATE employee_portal_links SET active = 0, updated_at = ? WHERE employee_id = ?",
                        (datetime.now(UTC).isoformat(), int(employee['id']))
                    )
                    connection.commit()
                    return send_json(self, 200, {'ok': True})

                    return send_json(self, 200, {'ok': True, 'token': token, 'qr_code_value': qr_code_value, 'expires_at': expires_at})

                elif parsed.path == '/api/employee-portal-link/revoke':
                    require_fields(payload, ['actor_user_id', 'employee_id'])
                    actor = authorize_action(connection, resolve_actor_user_id(self, parsed, payload), 'deliveries:create')
                    employee = get_employee_by_id(connection, int(payload['employee_id']))
                    if not employee:
                        raise ValueError('Colaborador não encontrado.')
                    ensure_actor_employee_scope(connection, actor, employee)
                    connection.execute(
                        "UPDATE employee_portal_links SET active = 0, updated_at = ? WHERE employee_id = ?",
                        (datetime.now(UTC).isoformat(), int(employee['id']))
                    )
                    
                    connection.commit()
                    return send_json(self, 200, {'ok': True})

                elif parsed.path == '/api/employee-sign-batch':
                    require_fields(payload, ['token', 'ficha_period_id'])
                    token = str(payload.get('token', '')).strip()
                    signature_name = str(payload.get('signature_name', '')).strip()
                    signature_data = str(payload.get('signature_data', '')).strip()
                    if not signature_name and not signature_data:
                        raise ValueError('Assinatura obrigatória.')
                    employee_user = resolve_external_employee_context(connection, token)
                    if not employee_user:
                        raise PermissionError('Token de acesso inválido ou expirado.')
                    employee_id = int(employee_user['employee_id'])
                    ficha = connection.execute('SELECT id, employee_id FROM epi_ficha_periods WHERE id = ?', (int(payload['ficha_period_id']),)).fetchone()
                    if not ficha or int(ficha['employee_id']) != employee_id:
                        raise PermissionError('Ficha não pertence ao funcionário.')
                    now = datetime.now(UTC).isoformat()
                    client_ip = str(getattr(self, 'client_address', ('',))[0] or '')
                    connection.execute(
                        '''
                        UPDATE epi_ficha_periods
                        SET status = 'signed', batch_signature_name = ?, batch_signature_data = ?, batch_signature_ip = ?, batch_signature_at = ?, updated_at = ?
                        WHERE id = ?
                        ''',
                        (signature_name or 'Assinado digitalmente', signature_data, client_ip, now, now, int(ficha['id']))
                    )
                    connection.execute(
                        '''
                        UPDATE epi_ficha_items
                        SET item_signature_name = ?, item_signature_data = ?, item_signature_ip = ?, item_signature_at = ?, signed_mode = 'batch', updated_at = ?
                        WHERE ficha_period_id = ? AND COALESCE(item_signature_at, '') = ''
                        ''',
                        (signature_name or 'Assinado digitalmente', signature_data, client_ip, now, now, int(ficha['id']))
                    )
                    register_employee_portal_audit(
                        connection,
                        employee_user,
                        'sign_batch_period',
                        ip_address=client_ip,
                        user_agent=self.headers.get('User-Agent', ''),
                        payload={'ficha_period_id': int(ficha['id'])}
                    )
                    connection.commit()
                    return send_json(self, 200, {'ok': True})

                elif parsed.path == '/api/employee-lookup':
                    require_fields(payload, ['actor_user_id', 'employee_qr_code'])
                    actor = authorize_action(connection, resolve_actor_user_id(self, parsed, payload), 'deliveries:create')
                    qr_value = str(payload.get('employee_qr_code', '')).strip()
                    lookup_token = ''
                    if qr_value.startswith('http://') or qr_value.startswith('https://'):
                        parsed_link = urlparse(qr_value)
                        query_values = parse_qs(parsed_link.query or '')
                        lookup_token = str((query_values.get('employee_token') or query_values.get('token') or [''])[0]).strip()
                    elif len(qr_value) > 20 and '-' in qr_value:
                        lookup_token = qr_value
                    params = [qr_value]
                    token_clause = ''
                    if lookup_token:
                        params.append(lookup_token)
                        token_clause = ' OR employee_portal_links.token = ?'
                    row = connection.execute(
                        f'''
                        SELECT employees.id, employees.company_id, employees.unit_id, employees.employee_id_code, employees.name,
                               employees.sector, employees.role_name, employees.schedule_type,
                               employee_portal_links.qr_code_value, employee_portal_links.token
                        FROM employee_portal_links
                        JOIN employees ON employees.id = employee_portal_links.employee_id
                        WHERE employee_portal_links.active = 1
                          AND (employee_portal_links.qr_code_value = ?{token_clause})
                        ''',
                        tuple(params)
                    ).fetchone()
                    if not row:
                        raise ValueError('Link do funcionário não encontrado.')
                    ensure_resource_company(actor, row, 'Colaborador')
                    return send_json(self, 200, {'employee': row_to_dict(row)})

                elif parsed.path == '/api/employee-portal-link':
                    require_fields(payload, ['actor_user_id', 'employee_id'])
                    actor = authorize_action(connection, resolve_actor_user_id(self, parsed, payload), 'deliveries:create')
                    employee = get_employee_by_id(connection, int(payload['employee_id']))
                    if not employee:
                        raise ValueError('Colaborador não encontrado.')
                    ensure_actor_employee_scope(connection, actor, employee)
                    token = secrets.token_urlsafe(24)
                    access_link = f"{request_base_url(self)}/?employee_token={token}"
                    qr_code_value = access_link
                    now = datetime.now(UTC).isoformat()
                    expires_at = (datetime.now(UTC) + timedelta(days=180)).isoformat()
                    existing = connection.execute('SELECT id FROM employee_portal_links WHERE employee_id = ?', (int(employee['id']),)).fetchone()
                    if existing:
                        connection.execute(
                            '''
                            UPDATE employee_portal_links
                            SET token = ?, qr_code_value = ?, active = 1, expires_at = ?, updated_at = ?
                            WHERE employee_id = ?
                            ''',
                            (token, qr_code_value, expires_at, now, int(employee['id']))
                        )
                    else:
                        connection.execute(
                            '''
                            INSERT INTO employee_portal_links (
                                company_id, employee_id, token, qr_code_value, active, expires_at,
                                created_by_user_id, created_at, updated_at
                            ) VALUES (?, ?, ?, ?, 1, ?, ?, ?, ?)
                            ''',
                            (int(employee['company_id']), int(employee['id']), token, qr_code_value, expires_at, int(actor['id']), now, now)
                        )
                    connection.commit()
                    return send_json(self, 200, {'ok': True, 'token': token, 'qr_code_value': qr_code_value, 'access_link': access_link, 'expires_at': expires_at})

                elif parsed.path == '/api/employee-portal-link/revoke':
                    require_fields(payload, ['actor_user_id', 'employee_id'])
                    actor = authorize_action(connection, resolve_actor_user_id(self, parsed, payload), 'deliveries:create')
                    employee = get_employee_by_id(connection, int(payload['employee_id']))
                    if not employee:
                        raise ValueError('Colaborador não encontrado.')
                    ensure_actor_employee_scope(connection, actor, employee)
                    connection.execute(
                        "UPDATE employee_portal_links SET active = 0, updated_at = ? WHERE employee_id = ?",
                        (datetime.now(UTC).isoformat(), int(employee['id']))
                    )
                    connection.commit()
                    return send_json(self, 200, {'ok': True})

                elif parsed.path == '/api/requests':
                    require_fields(payload, ['token', 'epi_id', 'quantity'])
                    portal = resolve_external_employee_context(connection, str(payload.get('token', '')).strip())
                    if not portal:
                        raise PermissionError('Link de solicitação inválido.')
                    if int(portal['employee_id']) != int(payload['employee_id']):
                        raise PermissionError('Solicitação incompatível com o colaborador.')

                elif parsed.path == '/api/requests':
                    require_fields(payload, ['token', 'epi_id', 'quantity'])
                    portal = resolve_external_employee_context(connection, str(payload.get('token', '')).strip())
                    if not portal:
                        raise PermissionError('Link de solicitação inválido.')
                    employee = get_employee_by_id(connection, int(portal['employee_id']))
                    if not employee:
                        raise ValueError('Colaborador não encontrado.')
                    target_epi = get_epi_by_id(connection, int(payload['epi_id']))
                    if not target_epi:
                        raise ValueError('EPI não encontrado.')
                    if int(target_epi['company_id']) != int(portal['company_id']):
                        raise PermissionError('EPI fora do escopo da empresa do colaborador.')
                    now = datetime.now(UTC).isoformat()
                    cursor = connection.execute(
                        '''
                        INSERT INTO epi_requests (
                            company_id, unit_id, employee_id, epi_id, quantity, request_token, status,
                            justification, requested_at, requested_by, last_updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, 'solicitado', ?, ?, 'employee', ?)
                        ''',
                        (
                            int(portal['company_id']),
                            int(payload['unit_id']),
                            int(payload['employee_id']),
                            int(employee['unit_id']),
                            int(portal['employee_id']),
                            int(payload['epi_id']),
                            int(payload.get('quantity') or 1),
                            str(payload.get('token', '')).strip(),
                            str(payload.get('justification', '')).strip(),
                            now,
                            now
                        )
                    )
                    connection.execute(
                        'INSERT INTO epi_request_history (request_id, company_id, status, notes, actor_name, created_at) VALUES (?, ?, ?, ?, ?, ?)',
                        (int(cursor.lastrowid), int(portal['company_id']), 'solicitado', str(payload.get('justification', '')).strip(), 'Funcionário', now)
                    )
                    register_employee_portal_audit(
                        connection,
                        portal,
                        'create_epi_request',
                        ip_address=str(getattr(self, 'client_address', ('',))[0] or ''),
                        user_agent=self.headers.get('User-Agent', ''),
                        payload={'request_id': int(cursor.lastrowid), 'epi_id': int(payload['epi_id'])}
                    )
                    connection.commit()
                    return send_json(self, 201, {'ok': True, 'id': cursor.lastrowid})

                elif parsed.path == '/api/employee-feedback':
                    require_fields(payload, ['token'])
                    portal = resolve_external_employee_context(connection, str(payload.get('token', '')).strip())
                    if not portal:
                        raise PermissionError('Link de avaliação inválido.')
                    epi_id = payload.get('epi_id')
                    if epi_id:
                        target_epi = get_epi_by_id(connection, int(epi_id))
                        if not target_epi or int(target_epi['company_id']) != int(portal['company_id']):
                            raise PermissionError('EPI inválido para avaliação.')
                    ratings = {}
                    for field in ('comfort_rating', 'quality_rating', 'adequacy_rating', 'performance_rating'):
                        raw = int(payload.get(field) or 0)
                        ratings[field] = min(5, max(0, raw))
                    now = datetime.now(UTC).isoformat()
                    cursor = connection.execute(
                        '''
                        INSERT INTO epi_feedbacks (
                            company_id, unit_id, employee_id, epi_id, comfort_rating, quality_rating, adequacy_rating, performance_rating,
                            comments, improvement_suggestion, suggested_new_epi_name, suggested_new_epi_notes,
                            status, request_token, created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pendente', ?, ?, ?)
                        ''',
                        (
                            int(portal['company_id']),
                            int(get_employee_by_id(connection, int(portal['employee_id']))['unit_id']),
                            int(portal['employee_id']),
                            int(epi_id) if epi_id else None,
                            ratings['comfort_rating'],
                            ratings['quality_rating'],
                            ratings['adequacy_rating'],
                            ratings['performance_rating'],
                            str(payload.get('comments', '')).strip(),
                            str(payload.get('improvement_suggestion', '')).strip(),
                            str(payload.get('suggested_new_epi_name', '')).strip(),
                            str(payload.get('suggested_new_epi_notes', '')).strip(),
                            str(payload.get('token', '')).strip(),
                            now,
                            now
                        )
                    )
                    connection.execute(
                        '''
                        INSERT INTO epi_feedback_history (feedback_id, company_id, status, notes, actor_name, created_at)
                        VALUES (?, ?, 'pendente', ?, 'Funcionário', ?)
                        ''',
                        (int(cursor.lastrowid), int(portal['company_id']), str(payload.get('comments', '')).strip(), now)
                    )
                    register_employee_portal_audit(
                        connection,
                        portal,
                        'create_epi_feedback',
                        ip_address=str(getattr(self, 'client_address', ('',))[0] or ''),
                        user_agent=self.headers.get('User-Agent', ''),
                        payload={'feedback_id': int(cursor.lastrowid)}
                    )

                    connection.commit()
                    return send_json(self, 201, {'ok': True, 'id': cursor.lastrowid})

                elif parsed.path == '/api/employee-feedback':
                    require_fields(payload, ['token'])
                    portal = resolve_external_employee_context(connection, str(payload.get('token', '')).strip())
                    if not portal:
                        raise PermissionError('Link de avaliação inválido.')
                    epi_id = payload.get('epi_id')
                    if epi_id:
                        target_epi = get_epi_by_id(connection, int(epi_id))
                        if not target_epi or int(target_epi['company_id']) != int(portal['company_id']):
                            raise PermissionError('EPI inválido para avaliação.')
                    ratings = {}
                    for field in ('comfort_rating', 'quality_rating', 'adequacy_rating', 'performance_rating'):
                        raw = int(payload.get(field) or 0)
                        ratings[field] = min(5, max(0, raw))
                    now = datetime.now(UTC).isoformat()
                    cursor = connection.execute(
                        '''
                        INSERT INTO epi_feedbacks (
                            company_id, unit_id, employee_id, epi_id, comfort_rating, quality_rating, adequacy_rating, performance_rating,
                            comments, improvement_suggestion, suggested_new_epi_name, suggested_new_epi_notes,
                            status, request_token, created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pendente', ?, ?, ?)
                        ''',
                        (
                            int(portal['company_id']),
                            int(get_employee_by_id(connection, int(portal['employee_id']))['unit_id']),
                            int(portal['employee_id']),
                            int(epi_id) if epi_id else None,
                            ratings['comfort_rating'],
                            ratings['quality_rating'],
                            ratings['adequacy_rating'],
                            ratings['performance_rating'],
                            str(payload.get('comments', '')).strip(),
                            str(payload.get('improvement_suggestion', '')).strip(),
                            str(payload.get('suggested_new_epi_name', '')).strip(),
                            str(payload.get('suggested_new_epi_notes', '')).strip(),
                            str(payload.get('token', '')).strip(),
                            now,
                            now
                        )
                    )
                    connection.execute(
                        '''
                        INSERT INTO epi_feedback_history (feedback_id, company_id, status, notes, actor_name, created_at)
                        VALUES (?, ?, 'pendente', ?, 'Funcionário', ?)
                        ''',
                        (int(cursor.lastrowid), int(portal['company_id']), str(payload.get('comments', '')).strip(), now)
                    )
                    register_employee_portal_audit(
                        connection,
                        portal,
                        'create_epi_feedback',
                        ip_address=str(getattr(self, 'client_address', ('',))[0] or ''),
                        user_agent=self.headers.get('User-Agent', ''),
                        payload={'feedback_id': int(cursor.lastrowid)}
                    )
                    connection.commit()
                    return send_json(self, 201, {'ok': True, 'id': cursor.lastrowid})
                    register_employee_portal_audit(
                        connection,
                        portal,
                        'create_epi_request',
                        ip_address=str(getattr(self, 'client_address', ('',))[0] or ''),
                        user_agent=self.headers.get('User-Agent', ''),
                        payload={'request_id': int(cursor.lastrowid), 'epi_id': int(payload['epi_id'])}
                    )
                    connection.commit()
                    return send_json(self, 201, {'ok': True, 'id': cursor.lastrowid})

                elif parsed.path == '/api/employee-feedback':
                    require_fields(payload, ['token'])
                    portal = resolve_external_employee_context(connection, str(payload.get('token', '')).strip())
                    if not portal:
                        raise PermissionError('Link de avaliação inválido.')
                    epi_id = payload.get('epi_id')
                    if epi_id:
                        target_epi = get_epi_by_id(connection, int(epi_id))
                        if not target_epi or int(target_epi['company_id']) != int(portal['company_id']):
                            raise PermissionError('EPI inválido para avaliação.')
                    ratings = {}
                    for field in ('comfort_rating', 'quality_rating', 'adequacy_rating', 'performance_rating'):
                        raw = int(payload.get(field) or 0)
                        ratings[field] = min(5, max(0, raw))
                    now = datetime.now(UTC).isoformat()
                    cursor = connection.execute(
                        '''
                        INSERT INTO epi_feedbacks (
                            company_id, unit_id, employee_id, epi_id, comfort_rating, quality_rating, adequacy_rating, performance_rating,
                            comments, improvement_suggestion, suggested_new_epi_name, suggested_new_epi_notes,
                            status, request_token, created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pendente', ?, ?, ?)
                        ''',
                        (
                            int(portal['company_id']),
                            int(get_employee_by_id(connection, int(portal['employee_id']))['unit_id']),
                            int(portal['employee_id']),
                            int(epi_id) if epi_id else None,
                            ratings['comfort_rating'],
                            ratings['quality_rating'],
                            ratings['adequacy_rating'],
                            ratings['performance_rating'],
                            str(payload.get('comments', '')).strip(),
                            str(payload.get('improvement_suggestion', '')).strip(),
                            str(payload.get('suggested_new_epi_name', '')).strip(),
                            str(payload.get('suggested_new_epi_notes', '')).strip(),
                            str(payload.get('token', '')).strip(),
                            now,
                            now
                        )
                    )
                    connection.execute(
                        '''
                        INSERT INTO epi_feedback_history (feedback_id, company_id, status, notes, actor_name, created_at)
                        VALUES (?, ?, 'pendente', ?, 'Funcionário', ?)
                        ''',
                        (int(cursor.lastrowid), int(portal['company_id']), str(payload.get('comments', '')).strip(), now)
                    )
                    register_employee_portal_audit(
                        connection,
                        portal,
                        'create_epi_feedback',
                        ip_address=str(getattr(self, 'client_address', ('',))[0] or ''),
                        user_agent=self.headers.get('User-Agent', ''),
                        payload={'feedback_id': int(cursor.lastrowid)}
                    )
                    connection.commit()
                    return send_json(self, 201, {'ok': True, 'id': cursor.lastrowid})
                  
                elif parsed.path == '/api/requests/status':
                    require_fields(payload, ['actor_user_id', 'request_id', 'status'])
                    actor = authorize_action(connection, resolve_actor_user_id(self, parsed, payload), 'deliveries:create')
                    req = connection.execute('SELECT * FROM epi_requests WHERE id = ?', (int(payload['request_id']),)).fetchone()
                    if not req:
                        raise ValueError('Solicitação não encontrada.')
                    ensure_resource_company(actor, req, 'Solicitação')
                    new_status = str(payload.get('status', '')).strip().lower()
                    valid = {'solicitado', 'em análise', 'aprovado', 'rejeitado', 'separado', 'entregue', 'assinado'}
                    if new_status not in valid:
                        raise ValueError('Status inválido.')
                    now = datetime.now(UTC).isoformat()
                    connection.execute(
                        '''
                        UPDATE epi_requests
                        SET status = ?, approver_user_id = ?, approver_name = ?, approved_at = CASE WHEN ? IN ('aprovado','rejeitado') THEN ? ELSE approved_at END,
                            rejection_reason = CASE WHEN ? = 'rejeitado' THEN ? ELSE rejection_reason END, last_updated_at = ?
                        WHERE id = ?
                        ''',
                        (
                            new_status,
                            int(actor['id']),
                            actor['full_name'],
                            new_status,
                            now,
                            new_status,
                            str(payload.get('rejection_reason', '')).strip(),
                            now,
                            int(req['id'])
                        )
                    )
                    connection.execute(
                        'INSERT INTO epi_request_history (request_id, company_id, status, notes, actor_user_id, actor_name, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)',
                        (int(req['id']), int(req['company_id']), new_status, str(payload.get('notes', '')).strip(), int(actor['id']), actor['full_name'], now)
                    )
                    connection.commit()
                    return send_json(self, 200, {'ok': True})

                elif parsed.path == '/api/feedbacks/status':
                    require_fields(payload, ['actor_user_id', 'feedback_id', 'status'])
                    actor = authorize_action(connection, resolve_actor_user_id(self, parsed, payload), 'deliveries:view')
                    feedback = connection.execute('SELECT * FROM epi_feedbacks WHERE id = ?', (int(payload['feedback_id']),)).fetchone()
                    if not feedback:
                        raise ValueError('Avaliação não encontrada.')
                    ensure_resource_company(actor, feedback, 'Avaliação')
                    status = str(payload.get('status', '')).strip().lower()
                    valid_status = {'pendente', 'em análise', 'aprovada', 'rejeitada', 'arquivada'}
                    if status not in valid_status:
                        raise ValueError('Status inválido para avaliação.')
                    now = datetime.now(UTC).isoformat()
                    connection.execute(
                        '''
                        UPDATE epi_feedbacks
                        SET status = ?, reviewer_user_id = ?, reviewer_name = ?, reviewed_at = ?, updated_at = ?
                        WHERE id = ?
                        ''',
                        (status, int(actor['id']), actor['full_name'], now, now, int(payload['feedback_id']))
                    )
                    connection.execute(
                        '''
                        INSERT INTO epi_feedback_history (feedback_id, company_id, status, notes, actor_user_id, actor_name, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        ''',
                        (int(payload['feedback_id']), int(feedback['company_id']), status, str(payload.get('notes', '')).strip(), int(actor['id']), actor['full_name'], now)
                    )
                    connection.commit()
                    return send_json(self, 200, {'ok': True})

                elif parsed.path == '/api/companies':
                    require_fields(payload, ['actor_user_id', 'name', 'legal_name', 'cnpj', 'plan_name', 'user_limit', 'license_status', 'active'])
                    actor = authorize_action(connection, resolve_actor_user_id(self, parsed, payload), 'companies:create')
                    payload = validate_company_payload(connection, payload, None)
                    cursor = connection.execute(
                        '''INSERT INTO companies (
                            name, legal_name, cnpj, logo_type, plan_name, user_limit, license_status, active,
                            commercial_notes, contract_start, contract_end, monthly_value, addendum_enabled
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                        (
                            payload['name'], payload['legal_name'], payload['cnpj'], payload.get('logo_type', ''),
                            payload['plan_name'], payload['user_limit'], payload['license_status'], int(payload['active']),
                            payload.get('commercial_notes', ''), payload.get('contract_start', ''), payload.get('contract_end', ''),
                            payload.get('monthly_value', 0), payload.get('addendum_enabled', 0)
                        )
                    )
                    summary, details = summarize_company_changes({}, payload)
                    register_company_audit(connection, int(cursor.lastrowid), actor, 'create', summary, details)
                    connection.commit()
                    return send_json(self, 201, {'ok': True, 'id': cursor.lastrowid})
                 
                elif parsed.path == '/api/units':
                    require_fields(payload, ['actor_user_id', 'company_id', 'name', 'unit_type', 'city'])
                    authorize_action(connection, resolve_actor_user_id(self, parsed, payload), 'units:create', int(payload['company_id']))
                    unit_type = normalize_unit_type(payload.get('unit_type'))
                    cursor = connection.execute(
                        'INSERT INTO units (company_id, name, unit_type, city, notes) VALUES (?, ?, ?, ?, ?)',
                        (payload['company_id'], payload['name'], unit_type, payload['city'], payload.get('notes', ''))
                    )
                    connection.commit()
                    return send_json(self, 201, {'ok': True, 'id': cursor.lastrowid})
                  
                elif parsed.path == '/api/employees':
                    require_fields(payload, ['actor_user_id', 'company_id', 'employee_id_code', 'name', 'sector', 'role_name', 'admission_date', 'schedule_type'])
                    actor = authorize_action(connection, resolve_actor_user_id(self, parsed, payload), 'employees:create', int(payload['company_id']))
                    if str(payload.get('unit_id', '')).strip():
                        unit = get_unit_by_id(connection, int(payload['unit_id']))
                    else:
                        unit = connection.execute('SELECT id, company_id, name, unit_type, city, notes FROM units WHERE company_id = ? ORDER BY id LIMIT 1', (int(payload['company_id']),)).fetchone()
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
                        payload['unit_id'] = unit['id']
                    ensure_resource_company(actor, unit, 'Unidade')
                    if str(unit['company_id']) != str(payload['company_id']):
                        raise ValueError('Unidade e empresa do colaborador precisam ser compatíveis.')
                    datetime.strptime(str(payload.get('admission_date', '')).strip(), '%Y-%m-%d')
                    cursor = connection.execute(
                        '''INSERT INTO employees (company_id, unit_id, employee_id_code, name, sector, role_name, admission_date, schedule_type)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                        (
                            payload['company_id'], payload['unit_id'], payload['employee_id_code'], payload['name'],
                            payload['sector'], payload['role_name'], payload['admission_date'], payload['schedule_type']
                        )
                    )
                    new_employee_id = int(cursor.lastrowid)
                    now = datetime.now(UTC).isoformat()
                    expires_at = (datetime.now(UTC) + timedelta(days=180)).isoformat()
                    token = secrets.token_urlsafe(24)
                    access_link = f"{request_base_url(self)}/?employee_token={token}"
                    qr_code_value = access_link
                    qr_code_value = f"EMP-{int(payload['company_id']):04d}-{new_employee_id:08d}"
                    connection.execute(
                        '''
                        INSERT INTO employee_portal_links (
                            company_id, employee_id, token, qr_code_value, active, expires_at,
                            created_by_user_id, created_at, updated_at
                        ) VALUES (?, ?, ?, ?, 1, ?, ?, ?, ?)
                        ''',
                        (int(payload['company_id']), new_employee_id, token, qr_code_value, expires_at, int(actor['id']), now, now)
                    )
                    connection.commit()
                    return send_json(self, 201, {'ok': True, 'id': new_employee_id, 'employee_portal_token': token, 'employee_qr_code': qr_code_value, 'employee_access_link': access_link, 'expires_at': expires_at})

                    return send_json(self, 201, {'ok': True, 'id': new_employee_id, 'employee_portal_token': token, 'employee_qr_code': qr_code_value, 'expires_at': expires_at})

                elif parsed.path == '/api/epis':
                    require_fields(payload, ['actor_user_id', 'company_id', 'name', 'purchase_code', 'ca', 'sector', 'epi_section', 'model_reference', 'manufacturer', 'supplier_company', 'unit_measure', 'ca_expiry', 'epi_validity_date', 'manufacture_date', 'manufacturer_validity_months'])
                    actor = authorize_action(connection, resolve_actor_user_id(self, parsed, payload), 'epis:create', int(payload['company_id']))
                    master_sequence = next_company_qr_sequence(connection, int(payload['company_id']))
                    qr_code_value = str(payload.get('qr_code_value') or build_master_epi_qr(int(payload['company_id']), master_sequence)).strip()
                    initial_stock = int(payload.get('stock') or 0)
                    joinventures_values = parse_epi_joinventures(payload.get('joinventures_json'))
                    active_joinventure = normalize_active_joinventure_name(payload.get('active_joinventure'))
                    resolved_unit_id = resolve_epi_scope_unit(connection, actor, payload, joinventures_values, active_joinventure)
                    validate_epi_uniqueness(
                        connection,
                        payload['company_id'],
                        resolved_unit_id,
                        active_joinventure,
                        payload.get('name'),
                        payload.get('purchase_code')
                    )
                    cursor = connection.execute(
                        '''INSERT INTO epis (company_id, unit_id, name, purchase_code, ca, sector, epi_section, stock, unit_measure, ca_expiry, epi_validity_date, manufacture_date, validity_days, validity_years, validity_months, manufacturer_validity_months, manufacturer, model_reference, supplier_company, manufacturer_recommendations, epi_photo_data, glove_size, size, uniform_size, joinventures_json, active_joinventure, qr_code_value, epi_master_sequence)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                        (
                            payload['company_id'], resolved_unit_id, payload['name'], payload['purchase_code'], payload['ca'],
                            payload['sector'], str(payload.get('epi_section', '')).strip(), initial_stock, payload['unit_measure'], payload['ca_expiry'],
                            payload['epi_validity_date'], payload['manufacture_date'], parse_int_flexible(payload.get('validity_days'), 0),
                            parse_int_flexible(payload.get('validity_years'), 0), parse_int_flexible(payload.get('validity_months'), 0),
                            parse_int_flexible(payload.get('manufacturer_validity_months'), 0),
                            str(payload.get('manufacturer', '')).strip(), str(payload.get('model_reference', '')).strip(), str(payload.get('supplier_company', '')).strip(),
                            str(payload.get('manufacturer_recommendations', '')).strip(), str(payload.get('epi_photo_data') or '').strip() or None,
                            str(payload.get('glove_size') or 'N/A').strip() or 'N/A',
                            str(payload.get('size') or 'N/A').strip() or 'N/A',
                            str(payload.get('uniform_size') or 'N/A').strip() or 'N/A',
                            json.dumps(joinventures_values, ensure_ascii=False),
                            active_joinventure or None,
                            qr_code_value, master_sequence
                        )
                    )
                    if resolved_unit_id:
                        upsert_unit_stock(connection, int(payload['company_id']), int(resolved_unit_id), int(cursor.lastrowid), initial_stock)
                    connection.commit()
                    return send_json(self, 201, {'ok': True, 'id': cursor.lastrowid})

                elif parsed.path == '/api/deliveries':
                    require_fields(payload, ['actor_user_id', 'company_id', 'employee_id', 'epi_id', 'quantity', 'quantity_label', 'sector', 'role_name', 'delivery_date', 'next_replacement_date'])
                    actor = authorize_action(connection, resolve_actor_user_id(self, parsed, payload), 'deliveries:create', int(payload['company_id']))
                    employee = get_employee_by_id(connection, int(payload['employee_id']))
                    epi = get_epi_by_id(connection, int(payload['epi_id']))
                    ensure_resource_company(actor, employee, 'Colaborador')
                    ensure_resource_company(actor, epi, 'EPI')
                    if str(employee['company_id']) != str(payload['company_id']) or str(epi['company_id']) != str(payload['company_id']):
                       
                       raise ValueError('Empresa incompatível para entrega.')
                    quantity = int(payload['quantity'])
                    if quantity <= 0:
                        raise ValueError('Quantidade inválida para entrega.')
                    signature_data = str(payload.get('signature_data', '')).strip()
                    if not signature_data:
                        raise ValueError('Assinatura digital obrigatória para registrar entrega.')
                    employee_current_unit_id = get_employee_current_unit(connection, int(employee['id']))
                    requested_unit_id = int(payload.get('unit_id') or 0)
                    delivery_unit_id = int(requested_unit_id or employee_current_unit_id)
                    if int(employee_current_unit_id) != int(delivery_unit_id):
                        raise ValueError('Entrega só pode ocorrer na unidade operacional atual do colaborador.')
                    actor_scope_unit_id = actor_operational_unit_id(connection, actor)
                    if actor.get('role') in ('admin', 'user') and not actor_scope_unit_id:
                        raise PermissionError('Seu perfil não possui unidade operacional ativa para registrar entregas.')
                    if actor_scope_unit_id and int(delivery_unit_id) != int(actor_scope_unit_id):
                        raise PermissionError('Seu perfil só pode registrar entregas na própria unidade operacional.')
                    if epi.get('unit_id') and int(epi['unit_id']) != int(delivery_unit_id):
                        raise ValueError('EPI vinculado a outra unidade operacional.')
                    stock_row = get_unit_stock(connection, int(payload['company_id']), delivery_unit_id, int(epi['id']))
                    current_stock = int((stock_row or {}).get('quantity') or 0)
                    if current_stock < quantity:
                        raise ValueError('Estoque insuficiente para realizar a entrega.')
                    existing = connection.execute(
                        '''
                        SELECT id FROM deliveries
                        WHERE company_id = ? AND employee_id = ? AND epi_id = ? AND delivery_date = ? AND quantity = ?
                        ORDER BY id DESC LIMIT 1
                        ''',
                        (payload['company_id'], payload['employee_id'], payload['epi_id'], payload['delivery_date'], quantity)
                    ).fetchone()
                    if existing:
                        raise ValueError('Entrega duplicada detectada para os mesmos dados.')
                    cursor = connection.execute(
                        '''INSERT INTO deliveries (company_id, employee_id, epi_id, quantity, quantity_label, sector, role_name, delivery_date, next_replacement_date, notes, signature_name, signature_ip, signature_at, signature_data)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                        (
                            
                            payload['company_id'], payload['employee_id'], payload['epi_id'], quantity,
                            payload['quantity_label'], payload['sector'], payload['role_name'], payload['delivery_date'],
                            payload['next_replacement_date'], payload.get('notes', ''), str(payload.get('signature_name') or 'Assinatura digital'),
                            str(getattr(self, 'client_address', ('',))[0] or ''), datetime.now(UTC).isoformat(), signature_data
                        )
                    )
                    new_stock = current_stock - quantity
                    upsert_unit_stock(connection, int(payload['company_id']), delivery_unit_id, int(epi['id']), new_stock)
                    stock_cursor = connection.execute(
                        '''
                        INSERT INTO stock_movements (
                            company_id, unit_id, epi_id, movement_type, quantity, previous_stock, new_stock,
                            source_type, source_id, notes, actor_user_id, actor_name, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''',
                        (
                            payload['company_id'], delivery_unit_id, epi['id'], 'out', quantity, current_stock, new_stock,
                            'delivery', int(cursor.lastrowid), str(payload.get('notes', '')).strip(),
                            actor['id'], actor['full_name'], datetime.now(UTC).isoformat()
                        )
                    )
                    connection.execute('UPDATE deliveries SET unit_id = ?, stock_movement_id = ? WHERE id = ?', (delivery_unit_id, int(stock_cursor.lastrowid), int(cursor.lastrowid)))
                    connection.execute(
                        '''
                        UPDATE epi_stock_items
                        SET status = 'delivered', delivery_id = ?, updated_at = ?
                        WHERE id IN (
                            SELECT id FROM epi_stock_items
                            WHERE company_id = ? AND unit_id = ? AND epi_id = ? AND status = 'in_stock'
                            ORDER BY id
                            LIMIT ?
                        )
                        ''',
                        (
                            int(cursor.lastrowid),
                            datetime.now(UTC).isoformat(),
                            int(payload['company_id']),
                            delivery_unit_id,
                            int(epi['id']),
                            quantity
                        )
                    )
                    ensure_ficha_for_delivery(
                        connection,
                        {
                            'id': int(cursor.lastrowid),
                            'company_id': int(payload['company_id']),
                            'employee_id': int(payload['employee_id']),
                            'unit_id': delivery_unit_id,
                            'epi_id': int(payload['epi_id']),
                            'quantity': quantity,
                            'delivery_date': payload['delivery_date'],
                            'schedule_type': employee.get('schedule_type')
                        }
                    )
                    if str(payload.get('request_id', '')).strip():
                        connection.execute(
                            "UPDATE epi_requests SET status = 'entregue', delivery_id = ?, last_updated_at = ? WHERE id = ?",
                            (int(cursor.lastrowid), datetime.now(UTC).isoformat(), int(payload['request_id']))
                        )
                    connection.commit()
                    return send_json(self, 201, {'ok': True, 'id': cursor.lastrowid})
                    
                elif parsed.path == '/api/platform-brand':
                    require_fields(payload, ['actor_user_id'])
                    actor = require_master_actor(connection, resolve_actor_user_id(self, parsed, payload))
                    brand = save_platform_brand(connection, payload)
                    connection.commit()
                    structured_log('info', 'platform_brand.updated', actor_user_id=actor['id'])
                    return send_json(self, 200, {'ok': True, 'brand': brand})
                elif parsed.path == '/api/stock/minimum':
                    require_fields(payload, ['actor_user_id', 'epi_id', 'minimum_stock'])
                    actor = authorize_action(connection, resolve_actor_user_id(self, parsed, payload), 'stock:adjust')
                    if actor.get('role') not in ('admin', 'user'):
                        raise PermissionError('Apenas Administrador Local e Gestor de EPI podem definir estoque mínimo.')
                    epi = get_epi_by_id(connection, int(payload['epi_id']))
                    ensure_resource_company(actor, epi, 'EPI')
                    scope_unit_id = actor_operational_unit_id(connection, actor)
                    if not scope_unit_id:
                        raise PermissionError('Perfil sem unidade operacional ativa para editar estoque mínimo.')
                    if scope_unit_id and int(epi.get('unit_id') or 0) != int(scope_unit_id):
                        raise PermissionError('Perfil só pode editar estoque mínimo da unidade operacional ativa.')
                    minimum_stock = max(0, int(payload.get('minimum_stock') or 0))
                    connection.execute('UPDATE epis SET minimum_stock = ? WHERE id = ?', (minimum_stock, int(payload['epi_id'])))
                    connection.commit()
                    return send_json(self, 200, {'ok': True, 'minimum_stock': minimum_stock})
                elif parsed.path == '/api/stock/movements':
                    require_fields(payload, ['actor_user_id', 'company_id', 'unit_id', 'epi_id', 'movement_type', 'quantity'])
                    actor = authorize_action(connection, resolve_actor_user_id(self, parsed, payload), 'stock:adjust', int(payload['company_id']))
                    scope_unit_id = actor_operational_unit_id(connection, actor)
                    if actor.get('role') in ('admin', 'user') and not scope_unit_id:
                        raise PermissionError('Perfil sem unidade operacional ativa para movimentar estoque.')
                    if scope_unit_id and int(payload.get('unit_id') or 0) != int(scope_unit_id):
                        raise PermissionError('Perfil só pode movimentar estoque da unidade operacional ativa.')
                    movement_type = str(payload.get('movement_type', '')).strip()
                    if movement_type not in ('in', 'out'):
                        raise ValueError('Tipo de movimentação inválido.')
                    if movement_type == 'out':
                        raise ValueError('Saída manual bloqueada: utilize o fluxo de Entrega de EPI para manter rastreabilidade.')
                    epi = get_epi_by_id(connection, int(payload['epi_id']))
                    unit = get_unit_by_id(connection, int(payload['unit_id']))
                    ensure_resource_company(actor, epi, 'EPI')
                    ensure_resource_company(actor, unit, 'Unidade')
                    quantity = int(payload.get('quantity') or 0)
                    if quantity <= 0:
                        raise ValueError('Quantidade deve ser maior que zero.')
                    glove_size = str(payload.get('glove_size') or 'N/A').strip() or 'N/A'
                    size = str(payload.get('size') or 'N/A').strip() or 'N/A'
                    uniform_size = str(payload.get('uniform_size') or 'N/A').strip() or 'N/A'
                    stock_row = get_unit_stock(connection, int(payload['company_id']), int(payload['unit_id']), int(payload['epi_id']))
                    if not stock_row:
                        raise ValueError('EPI sem estoque na unidade.')
                    previous_stock = int((stock_row or {}).get('quantity') or 0)
                    delta = quantity if movement_type == 'in' else -quantity
                    new_stock = previous_stock + delta
                    if new_stock < 0:
                        raise ValueError('Saída deixa estoque negativo.')
                    movement_cursor = connection.execute(
                        '''
                        INSERT INTO stock_movements (
                            company_id, unit_id, epi_id, movement_type, quantity, previous_stock, new_stock,
                            source_type, source_id, notes, actor_user_id, actor_name, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''',
                        (
                            int(payload['company_id']),
                            int(payload['unit_id']),
                            int(payload['epi_id']),
                            movement_type,
                            quantity,
                            previous_stock,
                            new_stock,
                            'manual',
                            None,
                            str(payload.get('notes', '')).strip(),
                            actor['id'],
                            actor['full_name'],
                            datetime.now(UTC).isoformat()
                        )
                    )
                    upsert_unit_stock(connection, int(payload['company_id']), int(payload['unit_id']), int(payload['epi_id']), new_stock)
                    qr_labels = []
                    if movement_type == 'in':
                        now = datetime.now(UTC).isoformat()
                        for _ in range(quantity):
                            seq_value = next_company_qr_sequence(connection, int(payload['company_id']))
                            qr_value = build_stock_item_qr(int(payload['company_id']), int(payload['unit_id']), seq_value)
                            stock_item_cursor = connection.execute(
                                '''
                                INSERT INTO epi_stock_items (
                                    company_id, unit_id, epi_id, glove_size, size, uniform_size, qr_sequence, qr_code_value, status,
                                    stock_movement_id, created_at, updated_at
                                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'in_stock', ?, ?, ?)
                                ''',
                                (
                                    int(payload['company_id']),
                                    int(payload['unit_id']),
                                    int(payload['epi_id']),
                                    glove_size,
                                    size,
                                    uniform_size,
                                    seq_value,
                                    qr_value,
                                    int(movement_cursor.lastrowid),
                                    now,
                                    now
                                )
                            )
                            qr_labels.append({
                                'qr_code_value': qr_value,
                                'epi_name': epi['name'],
                                'glove_size': glove_size,
                                'size': size,
                                'uniform_size': uniform_size,
                                'size': epi.get('size') or 'N/A',
                                'stock_item_id': stock_item_cursor.lastrowid,
                                'unit_name': unit['name']
                            })
                            
                    connection.commit()
                    return send_json(self, 201, {'ok': True, 'movement_id': movement_cursor.lastrowid, 'new_stock': new_stock, 'qr_labels': qr_labels})
                elif parsed.path == '/api/commercial-settings':
                    require_fields(payload, ['actor_user_id', 'unit_price', 'plans'])
                    actor_user_id = resolve_actor_user_id(self, parsed, payload)
                    actor, settings, details = save_commercial_settings(connection, payload)
                    if actor['role'] != 'master_admin' or int(actor['id']) != int(actor_user_id):
                        raise PermissionError('Apenas o Administrador Master pode alterar parâmetros comerciais.')
                    connection.commit()
                    structured_log(
                        'info',
                        'commercial_settings.updated',
                        actor_user_id=actor['id'],
                        details=details
                    )
                    return send_json(self, 200, {'ok': True, 'commercial_settings': settings})
                elif parsed.path == '/api/recover-password':
                    require_fields(payload, ['username', 'new_password', 'recovery_key'])
                    username = str(payload.get('username', '')).strip()
                    new_password = validate_password_strength(payload.get('new_password', ''))
                    provided_key = str(payload.get('recovery_key', '')).strip()

                    if not PASSWORD_RECOVERY_KEY:
                        raise PermissionError('Recuperação de senha indisponível no ambiente.')
                    if not hmac.compare_digest(provided_key, PASSWORD_RECOVERY_KEY):
                        raise PermissionError('Chave de recuperação inválida.')
                    row = connection.execute(
                        'SELECT id FROM users WHERE LOWER(username) = LOWER(?) LIMIT 1',
                        (username,)
                    ).fetchone()

                    if not row:
                        raise ValueError('Usuário não encontrado.')

                    connection.execute(
                        'UPDATE users SET password = ? WHERE id = ?',
                        (hash_password(new_password), row['id'])
                    )
                    connection.commit()
                    structured_log('info', 'auth.password_recovered', username=username, user_id=row['id'])
                    return send_json(self, 200, {'ok': True})

                elif parsed.path == '/api/login':
                    require_fields(payload, ['username', 'password'])
                    response_payload, status_code, error_payload = authenticate_login(
                        connection,
                        payload.get('username', ''),
                        payload.get('password', '')
                    )
                    if error_payload:
                        return send_json(self, status_code, error_payload)
                    return send_json(self, status_code, response_payload)

                else:
                    return not_found(self)

        except PermissionError as exc:
            structured_log('warning', 'http.permission_error', method='POST', path=parsed.path, error=str(exc))
            return forbidden(self, str(exc))
        except ValueError as exc:
            structured_log('warning', 'http.value_error', method='POST', path=parsed.path, error=str(exc))
            return bad_request(self, str(exc))
        except DBIntegrityError as exc:
            structured_log('warning', 'http.integrity_error', method='POST', path=parsed.path, error=str(exc))
            return bad_request(self, humanize_integrity_error(exc))
        except Exception as exc:
            structured_log('error', 'http.unhandled_error', method='POST', path=parsed.path, error=str(exc))
            return send_json(self, 500, {'error': str(exc)})

    def do_PUT(self):
        parsed = urlparse(self.path)

        try:
            payload = parse_json(self)
        except json.JSONDecodeError:
            return bad_request(self, 'JSON inválido.')

        try:
            with closing(get_connection()) as connection:
                if parsed.path.startswith('/api/companies/'):
                    company_id = int(parsed.path.rsplit('/', 1)[-1])
                    require_fields(payload, ['actor_user_id', 'name', 'legal_name', 'cnpj', 'plan_name', 'user_limit', 'license_status', 'active'])
                    actor = authorize_action(connection, resolve_actor_user_id(self, parsed, payload), 'companies:update')
                    current = connection.execute('SELECT * FROM companies WHERE id = ?', (company_id,)).fetchone()
                    if not current:
                        raise ValueError('Empresa não encontrada.')
                    previous = row_to_dict(current)
                    payload = validate_company_payload(connection, payload, company_id)
                    connection.execute(
                        SQL_UPDATE_COMPANY,
                        (
                            payload['name'], payload['legal_name'], payload['cnpj'], payload.get('logo_type', ''),
                            payload['plan_name'], payload['user_limit'], payload['license_status'], int(payload['active']),
                            payload.get('commercial_notes', ''), payload.get('contract_start', ''), payload.get('contract_end', ''),
                            payload.get('monthly_value', 0), payload.get('addendum_enabled', 0), company_id
                        )
                    )
                    action_type = 'update'
                    if previous.get('license_status') != 'suspended' and payload.get('license_status') == 'suspended':
                        action_type = 'suspend'
                    elif (
                        (previous.get('license_status') in ('suspended', 'expired') or int(previous.get('active', 1)) == 0)
                        and payload.get('license_status') == 'active'
                        and int(payload.get('active', 1)) == 1
                    ):
                        action_type = 'reactivate'
                    summary, details = summarize_company_changes(previous, payload)
                    register_company_audit(connection, company_id, actor, action_type, summary, details)
                    connection.commit()
                    return send_json(self, 200, {'ok': True})

                if parsed.path.startswith('/api/users/'):
                    user_id = int(parsed.path.rsplit('/', 1)[-1].split('?')[0])
                    require_fields(payload, ['actor_user_id', 'username', 'full_name', 'role'])

                    actor = authorize_user_management(
                        connection,
                        resolve_actor_user_id(self, parsed, payload),
                        'update',
                        payload['role'],
                        user_id,
                        payload.get('company_id')
                    )

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

                    role = str(payload.get('role', '')).strip()
                    if role not in ROLE_WEIGHT:
                        raise ValueError('Perfil de usuário inválido.')
                    if role == 'employee' and actor['role'] not in ('master_admin', 'general_admin', 'registry_admin'):
                        raise PermissionError('Somente Master, Geral e Registro podem criar perfil Funcionário.')

                    allow_manual_link = actor['role'] in ('master_admin', 'general_admin')
                    linked_value = payload.get('linked_employee_id', current.get('linked_employee_id'))
                    company_id = resolve_target_company_id(actor, payload.get('company_id'), role, linked_value)
                    payload_for_link = {**payload, 'linked_employee_id': linked_value}
                    linked_employee_id, company_id = resolve_user_employee_link(
                        connection,
                        actor,
                        payload_for_link,
                        company_id,
                        allow_manual_create=allow_manual_link and str(linked_value or '').strip() == ''
                    )
                    ensure_operational_role_link(connection, role, linked_employee_id, company_id)

                    if company_id and int(payload.get('active', 1)) == 1:
                        ensure_company_user_limit(connection, int(company_id), ignore_user_id=user_id)

                    employee_access_token = str(current.get('employee_access_token') or '')
                    if role == 'employee' and not employee_access_token:
                        employee_access_token = build_employee_access_token()
                    if role != 'employee':
                        employee_access_token = ''
                    employee_access_expires_at = str(current.get('employee_access_expires_at') or '') if role == 'employee' else ''

                    connection.execute(
                        SQL_UPDATE_USER,
                        (
                            str(payload.get('username', '')).strip(),
                            password,
                            str(payload.get('full_name', '')).strip(),
                            role,
                            company_id,
                            int(payload.get('active', 1)),
                            linked_employee_id,
                            employee_access_token,
                            employee_access_expires_at,
                            user_id
                        )
                    )

                    connection.commit()
                    return send_json(self, 200, {'ok': True, 'message': 'Usuário atualizado com sucesso.'})

                if parsed.path.startswith('/api/units/'):
                    unit_id = int(parsed.path.rsplit('/', 1)[-1].split('?')[0])
                    require_fields(payload, ['actor_user_id', 'company_id', 'name', 'unit_type', 'city'])
                    actor = authorize_action(connection, resolve_actor_user_id(self, parsed, payload), 'units:update', int(payload['company_id']))
                    current = get_unit_by_id(connection, unit_id)
                    ensure_resource_company(actor, current, 'Unidade')
                    unit_type = normalize_unit_type(payload.get('unit_type'))
                    connection.execute(
                        'UPDATE units SET company_id = ?, name = ?, unit_type = ?, city = ?, notes = ? WHERE id = ?',
                        (payload['company_id'], payload['name'], unit_type, payload['city'], payload.get('notes', ''), unit_id)
                    )
                    connection.commit()
                    return send_json(self, 200, {'ok': True})

                if parsed.path.startswith('/api/employees/'):
                    employee_id = int(parsed.path.rsplit('/', 1)[-1].split('?')[0])
                    require_fields(payload, ['actor_user_id', 'company_id', 'unit_id', 'employee_id_code', 'name', 'sector', 'role_name', 'admission_date', 'schedule_type'])
                    actor = authorize_action(connection, resolve_actor_user_id(self, parsed, payload), 'employees:update', int(payload['company_id']))
                    current = get_employee_by_id(connection, employee_id)
                    ensure_resource_company(actor, current, 'Colaborador')
                    unit = get_unit_by_id(connection, int(payload['unit_id']))
                    ensure_resource_company(actor, unit, 'Unidade')
                    if str(unit['company_id']) != str(payload['company_id']):
                        raise ValueError('Unidade e empresa do colaborador precisam ser compatíveis.')
                    connection.execute(
                        SQL_UPDATE_EMPLOYEE,
                        (
                            payload['company_id'], payload['unit_id'], payload['employee_id_code'], payload['name'],
                            payload['sector'], payload['role_name'], payload['admission_date'], payload['schedule_type'], employee_id
                        )
                    )
                    connection.commit()
                    return send_json(self, 200, {'ok': True})

                if parsed.path.startswith('/api/epis/'):
                    epi_id = int(parsed.path.rsplit('/', 1)[-1].split('?')[0])
                    require_fields(payload, ['actor_user_id', 'company_id', 'name', 'purchase_code', 'ca', 'sector', 'epi_section', 'model_reference', 'manufacturer', 'supplier_company', 'unit_measure', 'ca_expiry', 'epi_validity_date', 'manufacture_date', 'manufacturer_validity_months'])
                    actor = authorize_action(connection, resolve_actor_user_id(self, parsed, payload), 'epis:update', int(payload['company_id']))
                    current = get_epi_by_id(connection, epi_id)
                    ensure_resource_company(actor, current, 'EPI')
                    qr_code_value = str(payload.get('qr_code_value') or generate_epi_qr_code(payload)).strip()
                    joinventures_values = parse_epi_joinventures(payload.get('joinventures_json'))
                    active_joinventure = normalize_active_joinventure_name(payload.get('active_joinventure'))
                    resolved_unit_id = resolve_epi_scope_unit(connection, actor, payload, joinventures_values, active_joinventure)
                    validate_epi_uniqueness(
                        connection,
                        payload['company_id'],
                        resolved_unit_id,
                        active_joinventure,
                        payload.get('name'),
                        payload.get('purchase_code'),
                        exclude_id=epi_id
                    )
                    connection.execute(
                        (
                            'UPDATE epis SET company_id = ?, unit_id = ?, name = ?, purchase_code = ?, ca = ?, sector = ?, epi_section = ?, stock = ?, '
                            'unit_measure = ?, ca_expiry = ?, epi_validity_date = ?, manufacture_date = ?, validity_days = ?, validity_years = ?, validity_months = ?, manufacturer_validity_months = ?, '
                            'manufacturer = ?, model_reference = ?, supplier_company = ?, manufacturer_recommendations = ?, epi_photo_data = ?, glove_size = ?, size = ?, uniform_size = ?, joinventures_json = ?, active_joinventure = ?, qr_code_value = ? '
                            'WHERE id = ?'
                        ),
                        (
                            payload['company_id'], resolved_unit_id, payload['name'], payload['purchase_code'], payload['ca'],
                            payload['sector'], str(payload.get('epi_section', '')).strip(), int(payload.get('stock') or 0), payload['unit_measure'], payload['ca_expiry'],
                            payload['epi_validity_date'], payload['manufacture_date'], parse_int_flexible(payload.get('validity_days'), 0),
                            parse_int_flexible(payload.get('validity_years'), 0), parse_int_flexible(payload.get('validity_months'), 0), parse_int_flexible(payload.get('manufacturer_validity_months'), 0),
                            str(payload.get('manufacturer', '')).strip(), str(payload.get('model_reference', '')).strip(), str(payload.get('supplier_company', '')).strip(),
                            str(payload.get('manufacturer_recommendations', '')).strip(),
                            (
                                str(payload.get('epi_photo_data', current.get('epi_photo_data') or '')).strip() or None
                                if 'epi_photo_data' in payload
                                else current.get('epi_photo_data')
                            ),
                            str(payload.get('glove_size') or current.get('glove_size') or 'N/A').strip() or 'N/A',
                            str(payload.get('size') or current.get('size') or 'N/A').strip() or 'N/A',
                            str(payload.get('uniform_size') or current.get('uniform_size') or 'N/A').strip() or 'N/A',
                            json.dumps(joinventures_values, ensure_ascii=False),
                            active_joinventure or None,
                            qr_code_value, epi_id
                        )
                    )
                    connection.commit()
                    return send_json(self, 200, {'ok': True})
            return not_found(self)
        except PermissionError as exc:
            structured_log('warning', 'http.permission_error', method='PUT', path=parsed.path, error=str(exc))
            return forbidden(self, str(exc))
        except ValueError as exc:
            structured_log('warning', 'http.value_error', method='PUT', path=parsed.path, error=str(exc))
            return bad_request(self, str(exc))
        except DBIntegrityError as exc:
            structured_log('warning', 'http.integrity_error', method='PUT', path=parsed.path, error=str(exc))
            return bad_request(self, humanize_integrity_error(exc))
        except Exception as exc:
            structured_log('error', 'http.unhandled_error', method='PUT', path=parsed.path, error=str(exc))
            return send_json(self, 500, {'error': str(exc)})

    def do_DELETE(self):
        parsed = urlparse(self.path)
        try:
            with closing(get_connection()) as connection:
                if parsed.path.startswith('/api/users/'):
                    user_id = int(parsed.path.rsplit('/', 1)[-1].split('?')[0])
                    actor_user_id = resolve_actor_user_id(self, parsed)
                    authorize_user_management(connection, actor_user_id, 'delete', None, user_id, None)
                    if actor_user_id == user_id:
                        raise ValueError('Não é permitido excluir o próprio usuário logado.')
                    connection.execute('DELETE FROM users WHERE id = ?', (user_id,))
                    connection.commit()
                    return send_json(self, 200, {'ok': True})
                if parsed.path.startswith('/api/units/'):
                    unit_id = int(parsed.path.rsplit('/', 1)[-1].split('?')[0])
                    actor = authorize_action(connection, resolve_actor_user_id(self, parsed), 'units:delete')
                    unit = get_unit_by_id(connection, unit_id)
                    if not unit:
                        raise ValueError('Unidade não encontrada.')
                    ensure_resource_company(actor, unit, 'Unidade')
                    connection.execute('DELETE FROM units WHERE id = ?', (unit_id,))
                    connection.commit()
                    return send_json(self, 200, {'ok': True})
                if parsed.path.startswith('/api/employees/'):
                    employee_id = int(parsed.path.rsplit('/', 1)[-1].split('?')[0])
                    actor = authorize_action(connection, resolve_actor_user_id(self, parsed), 'employees:delete')
                    employee = get_employee_by_id(connection, employee_id)
                    if not employee:
                        raise ValueError('Colaborador não encontrado.')
                    ensure_resource_company(actor, employee, 'Colaborador')
                    connection.execute('DELETE FROM employees WHERE id = ?', (employee_id,))
                    connection.commit()
                    return send_json(self, 200, {'ok': True})
                if parsed.path.startswith('/api/epis/'):
                    epi_id = int(parsed.path.rsplit('/', 1)[-1].split('?')[0])
                    actor = authorize_action(connection, resolve_actor_user_id(self, parsed), 'epis:delete')
                    epi = get_epi_by_id(connection, epi_id)
                    if not epi:
                        raise ValueError('EPI não encontrado.')
                    ensure_resource_company(actor, epi, 'EPI')
                    connection.execute('DELETE FROM epis WHERE id = ?', (epi_id,))
                    connection.commit()
                    return send_json(self, 200, {'ok': True})
            return not_found(self)
        except PermissionError as exc:
            structured_log('warning', 'http.permission_error', method='DELETE', path=parsed.path, error=str(exc))
            return forbidden(self, str(exc))
        except ValueError as exc:
            structured_log('warning', 'http.value_error', method='DELETE', path=parsed.path, error=str(exc))
            return bad_request(self, str(exc))
        except DBIntegrityError as exc:
            structured_log('warning', 'http.integrity_error', method='DELETE', path=parsed.path, error=str(exc))
            return bad_request(self, humanize_integrity_error(exc))
        except Exception as exc:
            structured_log('error', 'http.unhandled_error', method='DELETE', path=parsed.path, error=str(exc))
            return send_json(self, 500, {'error': str(exc)})


if __name__ == '__main__':
    try:
        bootstrap_admin = init_db()
        port = int(os.environ.get('EPI_PORT', os.environ.get('PORT', '8000')))
        server = ThreadingHTTPServer(('0.0.0.0', port), EpiHandler)
        structured_log(
            'info',
            'auth.config',
            bcrypt_available=BCRYPT_AVAILABLE,
            jwt_exp_seconds=JWT_EXP_SECONDS,
            jwt_secret_default=JWT_SECRET == 'change-this-jwt-secret',
            password_recovery_key_configured=bool(PASSWORD_RECOVERY_KEY)
        )
        if bootstrap_admin:
            structured_log('info', 'bootstrap.completed', user_id=bootstrap_admin.get('id'), username=bootstrap_admin.get('username'))
        structured_log('info', 'server.started', port=port)
        server.serve_forever()
    except Exception as exc:
        structured_log('error', 'server.startup_failed', error=str(exc))
        raise
