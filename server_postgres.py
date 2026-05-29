import base64
import binascii
import hashlib
import hmac
import importlib.util
import json
import os
import re
import secrets
import threading
import time
import traceback
import textwrap
import unicodedata
from contextlib import closing
from datetime import date, datetime, timedelta, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from types import ModuleType
from epi_backend.config import (
    BASE_DIR,
    BCRYPT_AVAILABLE,
    DATABASE_URL,
    DB_CONNECTOR_AVAILABLE,
    DBIntegrityError,
    JWT_EXP_SECONDS,
    JWT_SECRET,
    PASSWORD_RECOVERY_KEY,
    UTC,
)
from core.database import PostgresConnectionWrapper, db_pool_status, get_connection
from epi_backend.db import row_to_dict
from epi_backend.http_utils import parse_json, require_fields, send_bytes, send_json, structured_log
from core.security import (
    create_jwt_token,
    decode_jwt_token,
    hash_password,
    is_bcrypt_hash,
    parse_bearer_token,
    resolve_actor_user_id,
    validate_password_strength,
    verify_password,
)
from epi_backend.unit_jv_lifecycle import (
    ensure_unit_joint_venture_periods_table,
    import_active_joinventures_from_epis,
)
from epi_backend.epi_scope import is_epi_visible_for_unit
from epi_backend.rule_engine import (
    build_context as build_rule_context,
    compute_visibility_diff,
    evaluate_rule_decision,
    normalize_framework_payload,
    resolve_execution_plan,
    resolve_visibility_filters,
    should_enable_new_engine,
)
from epi_backend.manufacture_date_ocr import detect_manufacture_date, get_ocr_runtime_status
from epi_backend.purchase_import import parse_money_decimal, parse_purchase_quote_file
from epi_backend.purchase_workflow import (
    PURCHASE_STATUS_LABELS as PURCHASE_WORKFLOW_STATUS_LABELS,
    latest_requester_review_origin,
    normalize_purchase_item_approval_decisions,
    resolve_purchase_transition,
    serialize_purchase_event_comment,
    validate_purchase_transition_payload,
)
from modules.auth.routes import handle_login_route
from modules.auth.service import authenticate_login as authenticate_login_service
from modules.deliveries.routes import handle_create_delivery_route
from modules.employees.routes import handle_create_employee_route, handle_update_employee_route
from modules.employees.service import create_employee as create_employee_service, update_employee as update_employee_service
from modules.deliveries.service import create_delivery_service
from modules.users.routes import handle_create_user_route, handle_delete_user_route, handle_update_user_route
from modules.users.service import create_user as create_user_service, delete_user as delete_user_service, update_user as update_user_service
from pathlib import Path
from urllib.parse import parse_qs, quote, urlparse

try:
    import bcrypt
    BCRYPT_AVAILABLE = True
except ModuleNotFoundError:
    bcrypt = None
    BCRYPT_AVAILABLE = False

BASE_DIR = Path(__file__).resolve().parent / "static"
UTC = timezone.utc
DATABASE_URL = os.environ.get('DATABASE_URL', '').strip()
DB_POOL_MINCONN = int(os.environ.get('DB_POOL_MINCONN', '1'))
DB_POOL_MAXCONN = int(os.environ.get('DB_POOL_MAXCONN', '10'))
PASSWORD_RECOVERY_KEY = os.environ.get('PASSWORD_RECOVERY_KEY', '').strip()
JWT_SECRET = os.environ.get('JWT_SECRET', '').strip() or PASSWORD_RECOVERY_KEY or 'change-this-jwt-secret'
JWT_EXP_SECONDS = int(os.environ.get('JWT_EXP_SECONDS', '28800'))
ROLE_WEIGHT = {'employee': 0, 'user': 1, 'buyer': 1, 'approver': 2, 'admin': 2, 'registry_admin': 3, 'general_admin': 4, 'master_admin': 5}
ROLE_ALIASES = {
    'master_admin': 'master_admin',
    'masteradmin': 'master_admin',
    'general_admin': 'general_admin',
    'generaladmin': 'general_admin',
    'registry_admin': 'registry_admin',
    'registryadmin': 'registry_admin',
    'local_admin': 'admin',
    'admin_local': 'admin',
    'admin': 'admin',
    'epi_manager': 'user',
    'gestor_epi': 'user',
    'gestor_de_epi': 'user',
    'gestor': 'user',
    'manager': 'user',
    'user': 'user',
    'employee': 'employee',
    'funcionario': 'employee',
    'buyer': 'buyer',
    'comprador': 'buyer',
    'approver': 'approver',
    'aprovador': 'approver',
}
BILLABLE_ROLES = ('general_admin', 'registry_admin', 'admin', 'user', 'buyer', 'approver', 'employee')
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
PERM_SETTINGS_VIEW = 'settings:view'
PERM_SETTINGS_UPDATE = 'settings:update'
PERM_EPI_VIEW_SELF = 'epi:view_self'
PERM_EPI_SIGN = 'epi:sign'
PERM_PURCHASE_REQUESTS_VIEW = 'purchase_requests:view'
PERM_PURCHASE_REQUESTS_CREATE = 'purchase_requests:create'
PERM_PURCHASE_REQUESTS_UPDATE = 'purchase_requests:update'
PERM_PO_VIEW = 'purchase_orders:view'
PERM_PO_CREATE = 'purchase_orders:create'
PERM_PO_UPLOAD = 'purchase_orders:upload'
PERM_PO_APPROVE = 'purchase_orders:approve'
PERM_PO_RECEIVE = 'purchase_orders:receive'
PERM_PO_REVIEW = 'purchase_orders:review'
PERM_FINANCE_VIEW = 'finance:view'
PERM_SUPPLIERS_MANAGE = 'suppliers:manage'
PERM_UNIT_LINKS_MANAGE = 'unit_links:manage'
PERM_EPI_FEEDBACK_VIEW = 'epi_feedback:view'
PERM_EPI_FEEDBACK_CREATE = 'epi_feedback:create'
PERM_EPI_FEEDBACK_TRIAGE = 'epi_feedback:triage'
PERM_EPI_FEEDBACK_HSEQ_REVIEW = 'epi_feedback:hseq_review'
PERM_EPI_FEEDBACK_ADMIN_APPROVE = 'epi_feedback:admin_approve'
PERM_EPI_FEEDBACK_CLOSE = 'epi_feedback:close'
PERM_EPI_FEEDBACK_MANAGER_EVAL = 'epi_feedback:manager_eval'
PERM_EPI_EVALUATION_VIEW = 'epi_evaluation:view'
PERM_EPI_EVALUATION_DECIDE = 'epi_evaluation:decide'
PERM_EPI_SUGGESTION_ACCEPT = 'epi_evaluation:accept_suggestion'
DB_BOOTSTRAP_STATE = {
    'started_at': '',
    'completed_at': '',
    'ready': False,
    'error_code': '',
    'error_kind': '',
    'error_message': '',
}
DB_BOOTSTRAP_STATE_LOCK = threading.Lock()
MIGRATION_RUNTIME_STATE = {
    'status': 'not_started',
    'last_error': '',
    'applied': [],
    'failed_migration': '',
}
MIGRATION_RUNTIME_STATE_LOCK = threading.Lock()
BOOTSTRAP_READY_EXEMPT_PATHS = frozenset({
    '/api/login',
})


def _set_migration_runtime_state(**values):
    with MIGRATION_RUNTIME_STATE_LOCK:
        MIGRATION_RUNTIME_STATE.update(values)


def _get_migration_runtime_state():
    with MIGRATION_RUNTIME_STATE_LOCK:
        return dict(MIGRATION_RUNTIME_STATE)


def _discover_migration_modules():
    migrations_dir = Path(__file__).resolve().parent / 'epi_backend' / 'migrations'
    modules = []
    for path in sorted(migrations_dir.glob('[0-9][0-9][0-9]_*.py')):
        if path.name == '__init__.py':
            continue
        module_name = f"epi_backend.migrations.{path.stem}"
        modules.append((path, module_name))
    return modules


def _load_migration_module(path: Path, module_name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(module_name, str(path))
    if spec is None or spec.loader is None:
        raise RuntimeError(f'Não foi possível carregar migration module: {path.name}')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_pending_migrations(connection):
    if _is_sqlite_connection(connection):
        _set_migration_runtime_state(
            status='skipped_sqlite',
            last_error='',
            failed_migration='',
            applied=[],
        )
        structured_log('info', 'db.migration_runner_skipped', reason='sqlite_connection')
        return {
            'status': 'skipped_sqlite',
            'applied': [],
            'failed_migration': '',
            'error': '',
        }

    connection.execute(
        '''
        CREATE TABLE IF NOT EXISTS app_migrations (
            migration_id TEXT PRIMARY KEY,
            status TEXT NOT NULL,
            applied_at TEXT NOT NULL
        )
        '''
    )
    connection.commit()
    applied_rows = connection.execute(
        "SELECT migration_id FROM app_migrations WHERE status = 'applied'"
    ).fetchall()
    applied_ids = {str((row['migration_id'] if hasattr(row, 'keys') else row[0])) for row in applied_rows}

    discovered = _discover_migration_modules()
    for path, module_name in discovered:
        module = _load_migration_module(path, module_name)
        migration_id = str(getattr(module, 'MIGRATION_ID', '') or '').strip()
        run_fn = getattr(module, 'run', None)
        if not migration_id or not callable(run_fn):
            raise RuntimeError(f'Migration inválida: {path.name} (MIGRATION_ID/run ausente)')
        if migration_id in applied_ids:
            continue
        try:
            result = run_fn(connection)
            connection.execute(
                'INSERT INTO app_migrations (migration_id, status, applied_at) VALUES (?, ?, ?)',
                (migration_id, 'applied', datetime.now(UTC).isoformat())
            )
            connection.commit()
            applied_ids.add(migration_id)
            structured_log(
                'info',
                'db.migration_applied',
                migration_id=migration_id,
                module=path.name,
                result=str(result or ''),
            )
        except Exception as exc:
            try:
                connection.rollback()
            except Exception:
                pass
            structured_log(
                'error',
                'db.migration_failed',
                migration_id=migration_id,
                module=path.name,
                error=str(exc),
                action='server_continuing_in_degraded_mode',
            )
            _set_migration_runtime_state(
                status='degraded',
                last_error=str(exc),
                failed_migration=migration_id,
            )
            return {
                'status': 'degraded',
                'applied': sorted(applied_ids),
                'failed_migration': migration_id,
                'error': str(exc),
            }
    _set_migration_runtime_state(
        status='ok',
        last_error='',
        failed_migration='',
        applied=sorted(applied_ids),
    )
    return {
        'status': 'ok',
        'applied': sorted(applied_ids),
        'failed_migration': '',
        'error': '',
    }

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
    "UPDATE employees SET company_id = ?, unit_id = ?, employee_id_code = ?, cpf = ?, name = ?, "
    "email = ?, whatsapp = ?, preferred_contact_channel = ?, "
    "sector = ?, role_name = ?, admission_date = ?, schedule_type = ?, tipo_vinculo = ?, empresa_origem = ? "
    "WHERE id = ?"
)

# Log Event Constants
LOG_HTTP_PERMISSION_ERROR = 'http.permission_error'
LOG_HTTP_VALUE_ERROR = 'http.value_error'
LOG_HTTP_UNHANDLED_ERROR = 'http.unhandled_error'


class EmployeePortalAccessDenied(PermissionError):
    def __init__(self, code, message, *, portal_context=None):
        super().__init__(message)
        self.code = str(code or 'TOKEN_EXPIRED')
        self.message = str(message or MSG_TOKEN_EXPIRED_ACCESS)
        self.portal_context = portal_context or {}

# Company Names
COMPANY_DOF_BRASIL = 'DOF Brasil'
COMPANY_NORSKAN_OFFSHORE = 'Norskan Offshore'
EPI_ALL_UNITS_VALUE = '__ALL_UNITS__'

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
PURCHASE_VIEW_PERMISSIONS = {PERM_PURCHASE_REQUESTS_VIEW, PERM_PO_VIEW, PERM_FINANCE_VIEW}
PURCHASE_BUYER_PERMISSIONS = {PERM_PURCHASE_REQUESTS_VIEW, PERM_PURCHASE_REQUESTS_UPDATE, PERM_PO_VIEW, PERM_PO_CREATE, PERM_PO_UPLOAD, PERM_FINANCE_VIEW}
PURCHASE_APPROVER_PERMISSIONS = {PERM_PURCHASE_REQUESTS_VIEW, PERM_PO_VIEW, PERM_PO_APPROVE, PERM_FINANCE_VIEW}
PURCHASE_ADMIN_PERMISSIONS = {PERM_PURCHASE_REQUESTS_VIEW, PERM_PURCHASE_REQUESTS_CREATE, PERM_PURCHASE_REQUESTS_UPDATE, PERM_PO_VIEW, PERM_PO_REVIEW, PERM_PO_RECEIVE, PERM_FINANCE_VIEW}
EPI_FEEDBACK_MANAGER_PERMISSIONS = {PERM_EPI_FEEDBACK_VIEW, PERM_EPI_FEEDBACK_TRIAGE}
EPI_FEEDBACK_ADMIN_PERMISSIONS = {PERM_EPI_FEEDBACK_VIEW, PERM_EPI_FEEDBACK_ADMIN_APPROVE, PERM_EPI_FEEDBACK_CLOSE}
PERMISSIONS = {
    'master_admin': ADMIN_BASE_PERMISSIONS | DELIVERY_WRITE_PERMISSIONS | COMPANY_CORE_PERMISSIONS | COMPANY_MANAGEMENT_PERMISSIONS | COMMERCIAL_PERMISSIONS | STOCK_MANAGEMENT_PERMISSIONS | PURCHASE_VIEW_PERMISSIONS | PURCHASE_BUYER_PERMISSIONS | PURCHASE_APPROVER_PERMISSIONS | PURCHASE_ADMIN_PERMISSIONS | EPI_FEEDBACK_MANAGER_PERMISSIONS | EPI_FEEDBACK_ADMIN_PERMISSIONS | {PERM_PURCHASE_REQUESTS_CREATE, PERM_SETTINGS_VIEW, PERM_SETTINGS_UPDATE, PERM_SUPPLIERS_MANAGE, PERM_UNIT_LINKS_MANAGE, PERM_EPI_FEEDBACK_HSEQ_REVIEW, PERM_EPI_FEEDBACK_CREATE},
    'general_admin': ADMIN_BASE_PERMISSIONS | DELIVERY_WRITE_PERMISSIONS | COMPANY_CORE_PERMISSIONS | STOCK_MANAGEMENT_PERMISSIONS | PURCHASE_VIEW_PERMISSIONS | PURCHASE_BUYER_PERMISSIONS | PURCHASE_APPROVER_PERMISSIONS | PURCHASE_ADMIN_PERMISSIONS | EPI_FEEDBACK_MANAGER_PERMISSIONS | EPI_FEEDBACK_ADMIN_PERMISSIONS | {PERM_PURCHASE_REQUESTS_CREATE, PERM_SETTINGS_VIEW, PERM_SETTINGS_UPDATE, PERM_SUPPLIERS_MANAGE, PERM_UNIT_LINKS_MANAGE, PERM_EPI_FEEDBACK_HSEQ_REVIEW, PERM_EPI_FEEDBACK_CREATE, PERM_EPI_FEEDBACK_MANAGER_EVAL, PERM_EPI_EVALUATION_VIEW, PERM_EPI_EVALUATION_DECIDE, PERM_EPI_SUGGESTION_ACCEPT},
    'registry_admin': ADMIN_BASE_PERMISSIONS | PURCHASE_VIEW_PERMISSIONS | PURCHASE_ADMIN_PERMISSIONS | EPI_FEEDBACK_ADMIN_PERMISSIONS | {PERM_PURCHASE_REQUESTS_CREATE, PERM_SETTINGS_VIEW, PERM_SETTINGS_UPDATE, PERM_UNIT_LINKS_MANAGE, PERM_EPI_FEEDBACK_CREATE, PERM_EPI_FEEDBACK_TRIAGE, PERM_EPI_FEEDBACK_MANAGER_EVAL, PERM_EPI_EVALUATION_VIEW, PERM_EPI_EVALUATION_DECIDE},
    'admin': {PERM_DASHBOARD_VIEW, PERM_USERS_VIEW, PERM_UNITS_VIEW, PERM_EMPLOYEES_VIEW, PERM_EMPLOYEES_UPDATE, PERM_EPIS_VIEW, PERM_DELIVERIES_VIEW, PERM_FICHAS_VIEW, PERM_REPORTS_VIEW, PERM_ALERTS_VIEW, PERM_STOCK_VIEW} | DELIVERY_WRITE_PERMISSIONS | STOCK_MANAGEMENT_PERMISSIONS | PURCHASE_ADMIN_PERMISSIONS | {PERM_EPI_FEEDBACK_VIEW, PERM_EPI_FEEDBACK_CREATE, PERM_EPI_EVALUATION_VIEW},
    'buyer': {PERM_DASHBOARD_VIEW, PERM_EPIS_VIEW, PERM_UNITS_VIEW, PERM_STOCK_VIEW, PERM_DELIVERIES_VIEW} | PURCHASE_BUYER_PERMISSIONS,
    'approver': {PERM_DASHBOARD_VIEW, PERM_EPIS_VIEW, PERM_UNITS_VIEW, PERM_STOCK_VIEW, PERM_DELIVERIES_VIEW} | PURCHASE_APPROVER_PERMISSIONS,
    'user': {PERM_DASHBOARD_VIEW, PERM_DELIVERIES_VIEW, PERM_FICHAS_VIEW, PERM_ALERTS_VIEW, PERM_UNITS_VIEW, PERM_EMPLOYEES_VIEW, PERM_EPIS_VIEW, PERM_STOCK_VIEW} | DELIVERY_WRITE_PERMISSIONS | STOCK_MANAGEMENT_PERMISSIONS | {PERM_EPI_FEEDBACK_VIEW, PERM_EPI_FEEDBACK_TRIAGE, PERM_EPI_FEEDBACK_MANAGER_EVAL, PERM_EPI_EVALUATION_VIEW},
    'epi_manager': {PERM_DASHBOARD_VIEW, PERM_DELIVERIES_VIEW, PERM_FICHAS_VIEW, PERM_ALERTS_VIEW, PERM_UNITS_VIEW, PERM_EMPLOYEES_VIEW, PERM_EPIS_VIEW, PERM_STOCK_VIEW} | EPI_FEEDBACK_MANAGER_PERMISSIONS | {PERM_EPI_FEEDBACK_HSEQ_REVIEW, PERM_EPI_FEEDBACK_CREATE},
    'employee': {PERM_EPI_VIEW_SELF, PERM_EPI_SIGN}
}


def normalize_role_name(role):
    normalized = str(role or '').strip().lower().replace('-', '_').replace(' ', '_')
    return ROLE_ALIASES.get(normalized, normalized)
def legacy_row_to_dict(row):
    return {key: row[key] for key in row.keys()}


def legacy_json_safe(value):
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, (list, tuple)):
        return [legacy_json_safe(item) for item in value]
    if isinstance(value, dict):
        return {str(key): legacy_json_safe(item) for key, item in value.items()}
    return str(value)


def legacy_structured_log(level, event, **fields):
    payload = {
        'ts': datetime.now(UTC).isoformat().replace('+00:00', 'Z'),
        'level': str(level).lower(),
        'event': event,
        **{key: legacy_json_safe(value) for key, value in fields.items()}
    }
    print(json.dumps(payload, ensure_ascii=False), flush=True)


def legacy_send_json(handler, status, payload):
    normalized_payload = payload
    path = str(getattr(handler, 'path', '') or '')
    if path.startswith('/api/'):
        if isinstance(payload, dict) and 'ok' in payload and ('data' in payload or 'error' in payload):
            normalized_payload = payload
        elif status < 400:
            normalized_payload = {'ok': True, 'data': payload}
        else:
            raw_error = payload.get('error') if isinstance(payload, dict) else payload
            code = payload.get('code') if isinstance(payload, dict) else ''
            details = payload.get('details') if isinstance(payload, dict) else None
            message = str(raw_error or f'Falha na requisição ({status}).')
            normalized_payload = {
                'ok': False,
                'error': {
                    'code': str(code or f'HTTP_{status}'),
                    'message': message,
                    'details': details,
                }
            }
    body = json.dumps(normalized_payload, ensure_ascii=False).encode('utf-8')
    handler.send_response(status)
    handler.send_header('Content-Type', 'application/json; charset=utf-8')
    handler.send_header('Content-Length', str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)
    if path.startswith('/api/') or path.startswith('/health'):
        legacy_structured_log(
            'info' if status < 400 else 'error',
            'http.response',
            method=getattr(handler, 'command', ''),
            path=getattr(handler, 'path', ''),
            status=status
        )


def legacy_send_bytes(handler, status, content_type, body, filename=None):
    handler.send_response(status)
    handler.send_header('Content-Type', content_type)
    handler.send_header('Content-Length', str(len(body)))
    if filename:
        handler.send_header('Content-Disposition', f'attachment; filename="{filename}"')
    handler.end_headers()
    handler.wfile.write(body)


def legacy_parse_json(handler):
    content_type = str(handler.headers.get('Content-Type', '')).lower()
    length = int(handler.headers.get('Content-Length', '0'))
    raw = handler.rfile.read(length) if length > 0 else b''
    if not raw:
        return {}
    try:
        return json.loads(raw.decode('utf-8'))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        structured_log('warning', 'http.json_parse_error',
            path=getattr(handler, 'path', ''),
            content_type=content_type, length=length, error=str(exc))
        raise


def legacy_require_fields(payload, fields):
    for field in fields:
        if payload.get(field) in (None, ''):
            raise ValueError(f'Campo obrigatório: {field}')

row_to_dict = legacy_row_to_dict
json_safe = legacy_json_safe
structured_log = legacy_structured_log
send_json = legacy_send_json
send_bytes = legacy_send_bytes
parse_json = legacy_parse_json
require_fields = legacy_require_fields


def authenticate_login(connection, username, password):
    return authenticate_login_service(
        connection,
        username,
        password,
        structured_log=structured_log,
        msg_login_failed=MSG_LOGIN_FAILED,
        msg_user_not_found=MSG_USER_NOT_FOUND,
        verify_password=verify_password,
        normalize_role_name=normalize_role_name,
        is_bcrypt_hash=is_bcrypt_hash,
        hash_password=hash_password,
        enforce_company_block_rules=enforce_company_block_rules,
        row_to_dict=row_to_dict,
        actor_operational_unit_id=actor_operational_unit_id,
        permissions=PERMISSIONS,
        create_jwt_token=create_jwt_token,
        jwt_exp_seconds=JWT_EXP_SECONDS,
    )


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
    try:
        rows = connection.execute('SELECT id, cnpj FROM companies').fetchall()
    except Exception as _e:
        structured_log('warning', 'db.col_skip', error=str(_e))
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


def validate_login_logo_payload(value):
    logo = str(value or '').strip()
    if not logo:
        return ''
    if not logo.startswith(('data:image/png', 'data:image/svg+xml')):
        raise ValueError('Logotipo da tela de login inválido. Envie PNG ou SVG.')
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
    if 'uq_epi_ficha_periods_employee_window_sequence' in lowered:
        return 'Conflito de sequência na ficha de EPI. Tente novamente.'
    if 'epi_ficha_periods' in lowered and ('unique' in lowered or 'duplicate key' in lowered):
        return 'Conflito na ficha de EPI: período ou sequência duplicada. Tente novamente.'
    if 'unique constraint failed: users.username' in lowered or ('users' in lowered and 'username' in lowered and 'unique' in lowered):
        return 'Nome de usuário já cadastrado. Para vincular um colaborador ao perfil existente, edite o usuário na lista de usuários.'
    if 'unique constraint failed: users.linked_employee_id' in lowered or ('users' in lowered and 'linked_employee_id' in lowered and 'unique' in lowered):
        return 'Este colaborador já está vinculado a outro perfil de usuário.'

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


EMPLOYEE_PORTAL_SECRET_KEY = str(os.environ.get('EMPLOYEE_PORTAL_SECRET_KEY') or JWT_SECRET or 'employee-portal-secret').strip()
EMPLOYEE_PORTAL_LINK_HOURS = 48


def normalize_cpf(value):
    digits = ''.join(ch for ch in str(value or '') if ch.isdigit())
    if len(digits) != 11:
        raise ValueError('CPF do colaborador deve conter 11 dígitos.')
    return digits


def normalize_preferred_contact_channel(value):
    normalized = str(value or '').strip().lower()
    return normalized if normalized in ('whatsapp', 'email') else 'whatsapp'

def parse_iso_datetime_utc(value):
    raw = str(value or '').strip()
    if not raw:
        return None
    normalized = raw[:-1] + '+00:00' if raw.endswith('Z') else raw
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def build_portal_link_from_cpf(base_url, funcionario_cpf, secret_key):
    cpf_digits = normalize_cpf(funcionario_cpf)
    now = datetime.now(UTC)
    expires_at_dt = now + timedelta(hours=EMPLOYEE_PORTAL_LINK_HOURS)
    exp_unix = int(expires_at_dt.timestamp())
    nonce = secrets.token_hex(8)
    payload = f'{cpf_digits}:{exp_unix}:{nonce}'
    signature = hmac.new(str(secret_key).encode('utf-8'), payload.encode('utf-8'), hashlib.sha256).hexdigest()
    token = f'{exp_unix}.{nonce}.{signature}'
    return {
        'token': token,
        'expires_at': expires_at_dt.isoformat(),
        'access_link': f"{str(base_url).rstrip('/')}/?employee_token={token}"
    }


INITIAL_MASTER_ADMIN_USERNAME = os.environ.get('INITIAL_MASTER_USERNAME', 'admin')
INITIAL_MASTER_ADMIN_PASSWORD = os.environ.get('INITIAL_MASTER_PASSWORD', 'admin123')
if not INITIAL_MASTER_ADMIN_PASSWORD:
    raise ValueError('INITIAL_MASTER_PASSWORD não definido. Configure a variável de ambiente.')
INITIAL_MASTER_ADMIN = {
    'username': INITIAL_MASTER_ADMIN_USERNAME,
    'password': INITIAL_MASTER_ADMIN_PASSWORD,
    'full_name': 'Administrador Master'
}
DEFAULT_PLATFORM_BRAND = {'display_name': 'Sua Empresa', 'legal_name': '', 'cnpj': '', 'logo_type': '', 'login_logo_type': ''}
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


COMMERCIAL_CONTRACT_STATUS = {
    'draft', 'generated', 'sent', 'pending_signature', 'signed', 'active', 'closed', 'archived'
}
DEFAULT_SAAS_CONTRACT_CLAUSES = """1. OBJETO
A CONTRATADA disponibiliza à CONTRATANTE licença de uso do sistema EPI Controle, no modelo SaaS.

2. LICENÇA DE USO, PLANOS E LIMITES
O uso observará o plano contratado, limite de usuários e regras de aditivo comercial configuradas.

3. DISPONIBILIDADE E SUPORTE
A CONTRATADA manterá o serviço e canais de suporte em padrões compatíveis com operação corporativa.

4. OBRIGAÇÕES DA CONTRATANTE
Manter dados cadastrais atualizados, cumprir políticas de uso e preservar credenciais de acesso.

5. OBRIGAÇÕES DA CONTRATADA
Manter a plataforma em funcionamento, promover melhorias contínuas e zelar pela segurança da informação.

6. CONFIDENCIALIDADE E PROTEÇÃO DE DADOS
As partes observam confidencialidade mútua e legislação aplicável de proteção de dados pessoais.

7. PREÇO, PAGAMENTO E REAJUSTE
Os valores vigentes, periodicidade e critérios de reajuste seguem os dados comerciais aprovados no sistema.

8. VIGÊNCIA, RENOVAÇÃO E RESCISÃO
A vigência inicia na data contratual registrada e encerra conforme prazo definido, admitindo renovação/aditivo.

9. ADITIVOS CONTRATUAIS
Alterações de escopo, limite de usuários, preço e condições devem ser formalizadas por aditivo.

10. RESPONSABILIDADE, FORO E DISPOSIÇÕES GERAIS
As partes elegem o foro contratual acordado e reconhecem a validade de assinatura digital."""


def ensure_commercial_contract_tables(connection):
    connection.executescript(
        '''
        CREATE TABLE IF NOT EXISTS commercial_contracts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL UNIQUE,
            contract_number TEXT NOT NULL DEFAULT '',
            issue_date TEXT NOT NULL DEFAULT '',
            start_date TEXT NOT NULL DEFAULT '',
            end_date TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'draft',
            contractor_name TEXT NOT NULL DEFAULT '',
            contractor_legal_name TEXT NOT NULL DEFAULT '',
            contractor_trade_name TEXT NOT NULL DEFAULT '',
            contractor_cnpj TEXT NOT NULL DEFAULT '',
            contractor_address TEXT NOT NULL DEFAULT '',
            contractor_representative TEXT NOT NULL DEFAULT '',
            contractor_representative_role TEXT NOT NULL DEFAULT '',
            contractor_email TEXT NOT NULL DEFAULT '',
            contractor_phone TEXT NOT NULL DEFAULT '',
            contractor_witness_1 TEXT NOT NULL DEFAULT '',
            contractor_witness_2 TEXT NOT NULL DEFAULT '',
            provider_name TEXT NOT NULL DEFAULT '',
            provider_legal_name TEXT NOT NULL DEFAULT '',
            provider_cnpj TEXT NOT NULL DEFAULT '',
            provider_address TEXT NOT NULL DEFAULT '',
            provider_representative TEXT NOT NULL DEFAULT '',
            provider_representative_role TEXT NOT NULL DEFAULT '',
            provider_email TEXT NOT NULL DEFAULT '',
            provider_phone TEXT NOT NULL DEFAULT '',
            provider_witnesses TEXT NOT NULL DEFAULT '',
            clauses_text TEXT NOT NULL DEFAULT '',
            notes TEXT NOT NULL DEFAULT '',
            generated_pdf_base64 TEXT NOT NULL DEFAULT '',
            signed_pdf_base64 TEXT NOT NULL DEFAULT '',
            signed_file_name TEXT NOT NULL DEFAULT '',
            signed_file_mime TEXT NOT NULL DEFAULT '',
            signed_at TEXT NOT NULL DEFAULT '',
            archived_at TEXT NOT NULL DEFAULT '',
            retention_until TEXT NOT NULL DEFAULT '',
            last_email_to TEXT NOT NULL DEFAULT '',
            last_email_subject TEXT NOT NULL DEFAULT '',
            last_email_body TEXT NOT NULL DEFAULT '',
            last_email_sent_at TEXT NOT NULL DEFAULT '',
            signature_name TEXT NOT NULL DEFAULT '',
            signature_data TEXT NOT NULL DEFAULT '',
            signature_at TEXT NOT NULL DEFAULT '',
            addendum_history_json TEXT NOT NULL DEFAULT '[]',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS commercial_contract_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL,
            contract_id INTEGER NOT NULL,
            actor_user_id INTEGER NOT NULL,
            actor_name TEXT NOT NULL,
            event_type TEXT NOT NULL,
            details_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
            FOREIGN KEY (contract_id) REFERENCES commercial_contracts(id) ON DELETE CASCADE
        );
        '''
    )


def _next_retention_date(end_date_value):
    end_date_value = str(end_date_value or '').strip()
    if not end_date_value:
        return ''
    try:
        dt = datetime.strptime(end_date_value, '%Y-%m-%d').date()
    except ValueError:
        return ''
    return dt.replace(year=dt.year + 5).isoformat()


def _default_contract_payload(company, settings, brand):
    metrics = compute_company_contract_metrics(company, settings)
    today_iso = date.today().isoformat()
    return {
        'company_id': int(company['id']),
        'contract_number': f"CTR-{int(company['id']):05d}-{today_iso.replace('-', '')}",
        'issue_date': today_iso,
        'start_date': str(company.get('contract_start') or ''),
        'end_date': str(company.get('contract_end') or ''),
        'status': 'draft',
        'contractor_name': str(company.get('name') or ''),
        'contractor_legal_name': str(company.get('legal_name') or ''),
        'contractor_trade_name': str(company.get('name') or ''),
        'contractor_cnpj': str(company.get('cnpj') or ''),
        'contractor_address': '',
        'contractor_representative': '',
        'contractor_representative_role': '',
        'contractor_email': '',
        'contractor_phone': '',
        'contractor_witness_1': '',
        'contractor_witness_2': '',
        'provider_name': str(brand.get('display_name') or ''),
        'provider_legal_name': str(brand.get('legal_name') or ''),
        'provider_cnpj': str(brand.get('cnpj') or ''),
        'provider_address': '',
        'provider_representative': '',
        'provider_representative_role': '',
        'provider_email': '',
        'provider_phone': '',
        'provider_witnesses': '',
        'clauses_text': DEFAULT_SAAS_CONTRACT_CLAUSES,
        'notes': str(company.get('commercial_notes') or ''),
        'generated_pdf_base64': '',
        'signed_pdf_base64': '',
        'signed_file_name': '',
        'signed_file_mime': '',
        'signed_at': '',
        'archived_at': '',
        'retention_until': _next_retention_date(company.get('contract_end')),
        'last_email_to': '',
        'last_email_subject': '',
        'last_email_body': '',
        'last_email_sent_at': '',
        'signature_name': '',
        'signature_data': '',
        'signature_at': '',
        'addendum_history_json': '[]',
        'metrics': metrics,
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
        'logo_type': validate_logo_payload(payload.get('logo_type', '')),
        'login_logo_type': validate_login_logo_payload(payload.get('login_logo_type', '')),
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
    """Adiciona colunas da tabela users apenas se nao existirem."""
    _safe_add_column(connection, 'users', 'linked_employee_id', 'INTEGER')
    _safe_add_column(connection, 'users', 'employee_access_token', 'TEXT')
    _safe_add_column(connection, 'users', 'employee_access_expires_at', 'TEXT')


def ensure_delivery_signature_columns(connection):
    """Adiciona colunas de assinatura na tabela deliveries apenas se nao existirem."""
    _safe_add_column(connection, 'deliveries', 'signature_ip', "TEXT NOT NULL DEFAULT ''")
    _safe_add_column(connection, 'deliveries', 'signature_at', "TEXT NOT NULL DEFAULT ''")
    _safe_add_column(connection, 'deliveries', 'signature_data', "TEXT NOT NULL DEFAULT ''")
    _safe_add_column(connection, 'deliveries', 'signature_comment', "TEXT NOT NULL DEFAULT ''")
    _safe_add_column(connection, 'deliveries', 'unit_id', 'INTEGER')
    _safe_add_column(connection, 'deliveries', 'stock_movement_id', 'INTEGER')
    _safe_add_column(connection, 'deliveries', 'glove_size', "TEXT NOT NULL DEFAULT 'N/A'")
    _safe_add_column(connection, 'deliveries', 'size', "TEXT NOT NULL DEFAULT 'N/A'")
    _safe_add_column(connection, 'deliveries', 'uniform_size', "TEXT NOT NULL DEFAULT 'N/A'")


def ensure_devolution_columns(connection):
    """Garante estrutura de devoluções de EPI e colunas correlatas."""
    _safe_add_column(connection, 'deliveries', 'returned_date', "TEXT NOT NULL DEFAULT ''")
    _safe_add_column(connection, 'deliveries', 'returned_condition', "TEXT NOT NULL DEFAULT ''")
    _safe_add_column(connection, 'deliveries', 'returned_notes', "TEXT NOT NULL DEFAULT ''")
    _safe_add_column(connection, 'deliveries', 'return_movement_id', 'INTEGER')
    connection.execute(
        '''
        CREATE TABLE IF NOT EXISTS epi_devolutions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL,
            unit_id INTEGER NOT NULL,
            employee_id INTEGER NOT NULL,
            epi_id INTEGER NOT NULL,
            delivery_id INTEGER NOT NULL UNIQUE,
            ficha_period_id INTEGER,
            stock_item_id INTEGER,
            stock_movement_id INTEGER,
            returned_date TEXT NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 1,
            condition TEXT NOT NULL,
            destination TEXT NOT NULL,
            notes TEXT NOT NULL DEFAULT '',
            reason TEXT NOT NULL DEFAULT '',
            received_by_user_id INTEGER NOT NULL,
            received_by_name TEXT NOT NULL DEFAULT '',
            signature_name TEXT NOT NULL DEFAULT '',
            signature_data TEXT NOT NULL DEFAULT '',
            signature_ip TEXT NOT NULL DEFAULT '',
            signature_at TEXT NOT NULL DEFAULT '',
            signature_comment TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
            FOREIGN KEY (unit_id) REFERENCES units(id) ON DELETE RESTRICT,
            FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE,
            FOREIGN KEY (epi_id) REFERENCES epis(id) ON DELETE RESTRICT,
            FOREIGN KEY (delivery_id) REFERENCES deliveries(id) ON DELETE CASCADE,
            FOREIGN KEY (ficha_period_id) REFERENCES epi_ficha_periods(id) ON DELETE SET NULL,
            FOREIGN KEY (stock_item_id) REFERENCES epi_stock_items(id) ON DELETE SET NULL,
            FOREIGN KEY (stock_movement_id) REFERENCES stock_movements(id) ON DELETE SET NULL,
            FOREIGN KEY (received_by_user_id) REFERENCES users(id) ON DELETE RESTRICT
        )
        '''
    )
    _safe_add_column(connection, 'epi_devolutions', 'ficha_period_id', 'INTEGER')
    _safe_add_column(connection, 'epi_devolutions', 'stock_item_id', 'INTEGER')
    _safe_add_column(connection, 'epi_devolutions', 'stock_movement_id', 'INTEGER')
    _safe_add_column(connection, 'epi_devolutions', 'signature_name', "TEXT NOT NULL DEFAULT ''")
    _safe_add_column(connection, 'epi_devolutions', 'signature_data', "TEXT NOT NULL DEFAULT ''")
    _safe_add_column(connection, 'epi_devolutions', 'signature_ip', "TEXT NOT NULL DEFAULT ''")
    _safe_add_column(connection, 'epi_devolutions', 'signature_at', "TEXT NOT NULL DEFAULT ''")
    _safe_add_column(connection, 'epi_devolutions', 'signature_comment', "TEXT NOT NULL DEFAULT ''")


def ensure_stock_columns(connection):
    _safe_add_column(connection, 'epis', 'minimum_stock', 'INTEGER NOT NULL DEFAULT 10')
    try:
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
    except Exception as _e:
        structured_log('warning', 'db.col_skip', error=str(_e))
    ensure_stock_movement_size_columns(connection)


def ensure_stock_movement_size_columns(connection):
    _safe_add_column(connection, 'stock_movements', 'glove_size', "TEXT NOT NULL DEFAULT 'N/A'")
    _safe_add_column(connection, 'stock_movements', 'size', "TEXT NOT NULL DEFAULT 'N/A'")
    _safe_add_column(connection, 'stock_movements', 'uniform_size', "TEXT NOT NULL DEFAULT 'N/A'")


def ensure_epi_operational_tables(connection):
    try:
        connection.execute(
            '''
            CREATE TABLE IF NOT EXISTS epi_qr_sequences (
                company_id INTEGER PRIMARY KEY,
                last_value INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE
            )
            '''
        )
    except Exception as _e:
        structured_log('warning', 'db.col_skip', error=str(_e))
    try:
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
    except Exception as _e:
        structured_log('warning', 'db.col_skip', error=str(_e))
    try:
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
                manufacture_date TEXT NOT NULL DEFAULT '',
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
    except Exception as _e:
        structured_log('warning', 'db.col_skip', error=str(_e))
    _safe_add_column(connection, 'epi_stock_items', 'glove_size', "TEXT NOT NULL DEFAULT 'N/A'")
    _safe_add_column(connection, 'epi_stock_items', 'size', "TEXT NOT NULL DEFAULT 'N/A'")
    _safe_add_column(connection, 'epi_stock_items', 'uniform_size', "TEXT NOT NULL DEFAULT 'N/A'")
    _safe_add_column(connection, 'epi_stock_items', 'lot_code', "TEXT NOT NULL DEFAULT ''")
    _safe_add_column(connection, 'epi_stock_items', 'manufacture_date', "TEXT NOT NULL DEFAULT ''")
    _safe_add_column(connection, 'epi_stock_items', 'label_measure', "TEXT NOT NULL DEFAULT 'unidade'")
    _safe_add_column(connection, 'epi_stock_items', 'label_printer_name', "TEXT NOT NULL DEFAULT ''")
    _safe_add_column(connection, 'epi_stock_items', 'label_print_format', "TEXT NOT NULL DEFAULT ''")
    _safe_add_column(connection, 'epi_stock_items', 'reprint_count', 'INTEGER NOT NULL DEFAULT 0')
    _safe_add_column(connection, 'epi_stock_items', 'generated_by_user_id', 'INTEGER')
    try:
        connection.execute(
            """
            UPDATE epi_stock_items
            SET manufacture_date = COALESCE(NULLIF(manufacture_date, ''), (
                SELECT COALESCE(epis.manufacture_date, '') FROM epis WHERE epis.id = epi_stock_items.epi_id
            ), '')
            WHERE COALESCE(NULLIF(manufacture_date, ''), '') = ''
            """
        )
    except Exception as _e:
        structured_log('warning', 'db.col_skip', error=str(_e))
    try:
        connection.execute(
            '''
            CREATE TABLE IF NOT EXISTS epi_stock_item_reprints (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                stock_item_id INTEGER NOT NULL,
                company_id INTEGER NOT NULL,
                reason_code TEXT NOT NULL,
                reason_note TEXT NOT NULL DEFAULT '',
                actor_user_id INTEGER NOT NULL,
                actor_name TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                FOREIGN KEY (stock_item_id) REFERENCES epi_stock_items(id) ON DELETE CASCADE,
                FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
                FOREIGN KEY (actor_user_id) REFERENCES users(id) ON DELETE RESTRICT
            )
            '''
        )
    except Exception as _e:
        structured_log('warning', 'db.col_skip', error=str(_e))
    try:
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
                batch_signature_comment TEXT NOT NULL DEFAULT '',
                ficha_sequence INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(employee_id, period_start, period_end, ficha_sequence),
                FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
                FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE,
                FOREIGN KEY (unit_id) REFERENCES units(id) ON DELETE RESTRICT
            )
            '''
        )
    except Exception as _e:
        structured_log('warning', 'db.col_skip', error=str(_e))
    try:
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
                item_signature_comment TEXT NOT NULL DEFAULT '',
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
    except Exception as _e:
        structured_log('warning', 'db.col_skip', error=str(_e))
    _safe_add_column(connection, 'epi_ficha_periods', 'batch_signature_comment', "TEXT NOT NULL DEFAULT ''")
    _safe_add_column(connection, 'epi_ficha_periods', 'ficha_sequence', 'INTEGER NOT NULL DEFAULT 1')
    _ensure_ficha_periods_sequence_unique(connection)
    _safe_add_column(connection, 'epi_ficha_items', 'item_signature_comment', "TEXT NOT NULL DEFAULT ''")
    connection.execute('CREATE INDEX IF NOT EXISTS idx_epi_ficha_items_ficha_period_id ON epi_ficha_items (ficha_period_id)')
    connection.execute('CREATE INDEX IF NOT EXISTS idx_epi_ficha_items_period_sequence ON epi_ficha_periods (employee_id, period_start, period_end, ficha_sequence DESC)')
    try:
        connection.execute(
            '''
            CREATE TABLE IF NOT EXISTS ficha_epi_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ficha_period_id INTEGER NOT NULL UNIQUE,
                company_id INTEGER NOT NULL,
                unit_id INTEGER NOT NULL,
                employee_id INTEGER NOT NULL,
                html_content TEXT NOT NULL,
                html_sha256 TEXT NOT NULL,
                generated_by_user_id INTEGER NOT NULL,
                generated_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                FOREIGN KEY (ficha_period_id) REFERENCES epi_ficha_periods(id) ON DELETE CASCADE,
                FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
                FOREIGN KEY (unit_id) REFERENCES units(id) ON DELETE RESTRICT,
                FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE,
                FOREIGN KEY (generated_by_user_id) REFERENCES users(id) ON DELETE RESTRICT
            )
            '''
        )
        connection.execute('CREATE INDEX IF NOT EXISTS idx_snapshots_employee ON ficha_epi_snapshots (employee_id, generated_at DESC)')
        connection.execute('CREATE INDEX IF NOT EXISTS idx_snapshots_company ON ficha_epi_snapshots (company_id, generated_at DESC)')
        connection.execute('CREATE INDEX IF NOT EXISTS idx_snapshots_expires ON ficha_epi_snapshots (expires_at)')
        _safe_add_column(connection, 'ficha_epi_snapshots', 'snapshot_payload', "TEXT NOT NULL DEFAULT '{}'")
        _safe_add_column(connection, 'ficha_epi_snapshots', 'payload_sha256', "TEXT NOT NULL DEFAULT ''")
        _safe_add_column(connection, 'ficha_epi_snapshots', 'status', "TEXT NOT NULL DEFAULT 'archived'")
        _safe_add_column(connection, 'ficha_epi_snapshots', 'retention_years', "INTEGER NOT NULL DEFAULT 5")
        _safe_add_column(connection, 'ficha_epi_snapshots', 'expired_at', "TEXT NOT NULL DEFAULT ''")
        _safe_add_column(connection, 'ficha_epi_snapshots', 'purged_at', "TEXT NOT NULL DEFAULT ''")
    except Exception as _e:
        structured_log('warning', 'db.col_skip', error=str(_e))
    try:
        connection.execute(
            '''
            CREATE TABLE IF NOT EXISTS ficha_epi_audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                actor_user_id INTEGER NOT NULL,
                actor_name TEXT NOT NULL DEFAULT '',
                actor_role TEXT NOT NULL DEFAULT '',
                employee_id INTEGER NOT NULL,
                employee_name TEXT NOT NULL DEFAULT '',
                unit_id INTEGER NOT NULL,
                company_id INTEGER NOT NULL,
                action TEXT NOT NULL,
                ip_address TEXT NOT NULL DEFAULT '',
                user_agent TEXT NOT NULL DEFAULT '',
                accessed_at TEXT NOT NULL,
                FOREIGN KEY (actor_user_id) REFERENCES users(id) ON DELETE RESTRICT,
                FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE,
                FOREIGN KEY (unit_id) REFERENCES units(id) ON DELETE RESTRICT,
                FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE
            )
            '''
        )
        connection.execute('CREATE INDEX IF NOT EXISTS idx_ficha_audit_actor ON ficha_epi_audit_log (actor_user_id, accessed_at DESC)')
        connection.execute('CREATE INDEX IF NOT EXISTS idx_ficha_audit_employee ON ficha_epi_audit_log (employee_id, accessed_at DESC)')
        connection.execute('CREATE INDEX IF NOT EXISTS idx_ficha_audit_company ON ficha_epi_audit_log (company_id, accessed_at DESC)')
    except Exception as _e:
        structured_log('warning', 'db.col_skip', error=str(_e))
    try:
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
    except Exception as _e:
        structured_log('warning', 'db.col_skip', error=str(_e))
    _safe_add_column(connection, 'employee_portal_links', 'cpf_attempts', 'INTEGER NOT NULL DEFAULT 0')
    _safe_add_column(connection, 'employee_portal_links', 'last_cpf_attempt_at', "TEXT NOT NULL DEFAULT ''")
    _safe_add_column(connection, 'employee_portal_links', 'blocked_at', "TEXT NOT NULL DEFAULT ''")
    try:
        connection.execute(
            '''
            CREATE TABLE IF NOT EXISTS epi_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                unit_id INTEGER NOT NULL,
                employee_id INTEGER NOT NULL,
                epi_id INTEGER NOT NULL,
                quantity INTEGER NOT NULL DEFAULT 1,
                glove_size TEXT NOT NULL DEFAULT 'N/A',
                size TEXT NOT NULL DEFAULT 'N/A',
                uniform_size TEXT NOT NULL DEFAULT 'N/A',
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
    except Exception as _e:
        structured_log('warning', 'db.col_skip', error=str(_e))
    _safe_add_column(connection, 'epi_requests', 'glove_size', "TEXT NOT NULL DEFAULT 'N/A'")
    _safe_add_column(connection, 'epi_requests', 'size', "TEXT NOT NULL DEFAULT 'N/A'")
    _safe_add_column(connection, 'epi_requests', 'uniform_size', "TEXT NOT NULL DEFAULT 'N/A'")
    try:
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
    except Exception as _e:
        structured_log('warning', 'db.col_skip', error=str(_e))
    # ── Fase 2 — Módulo de Compras ────────────────────────────────────────
    try:
        connection.execute(
            '''
            CREATE TABLE IF NOT EXISTS purchase_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                unit_id INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'draft',
                title TEXT NOT NULL DEFAULT '',
                notes TEXT NOT NULL DEFAULT '',
                created_by_user_id INTEGER NOT NULL,
                created_by_name TEXT NOT NULL DEFAULT '',
                sent_to_buyer_at TEXT NOT NULL DEFAULT '',
                closed_at TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
                FOREIGN KEY (unit_id) REFERENCES units(id) ON DELETE RESTRICT,
                FOREIGN KEY (created_by_user_id) REFERENCES users(id) ON DELETE RESTRICT
            )
            '''
        )
    except Exception as _e:
        structured_log('warning', 'db.col_skip', error=str(_e))
    try:
        connection.execute(
            '''
            CREATE TABLE IF NOT EXISTS purchase_request_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                purchase_request_id INTEGER NOT NULL,
                company_id INTEGER NOT NULL,
                unit_id INTEGER NOT NULL,
                epi_id INTEGER NOT NULL,
                epi_name TEXT NOT NULL DEFAULT '',
                ca TEXT NOT NULL DEFAULT '',
                unit_measure TEXT NOT NULL DEFAULT '',
                manufacturer TEXT NOT NULL DEFAULT '',
                supplier TEXT NOT NULL DEFAULT '',
                glove_size TEXT NOT NULL DEFAULT 'N/A',
                size TEXT NOT NULL DEFAULT 'N/A',
                uniform_size TEXT NOT NULL DEFAULT 'N/A',
                quantity_requested INTEGER NOT NULL DEFAULT 1,
                quantity_approved INTEGER NOT NULL DEFAULT 0,
                origin TEXT NOT NULL DEFAULT 'stock_minimum',
                employee_id INTEGER,
                employee_name TEXT NOT NULL DEFAULT '',
                employee_sector TEXT NOT NULL DEFAULT '',
                employee_role TEXT NOT NULL DEFAULT '',
                epi_request_id INTEGER,
                status TEXT NOT NULL DEFAULT 'open',
                unit_price REAL NOT NULL DEFAULT 0,
                total_price REAL NOT NULL DEFAULT 0,
                notes TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (purchase_request_id) REFERENCES purchase_requests(id) ON DELETE CASCADE,
                FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
                FOREIGN KEY (unit_id) REFERENCES units(id) ON DELETE RESTRICT,
                FOREIGN KEY (epi_id) REFERENCES epis(id) ON DELETE RESTRICT,
                FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE SET NULL,
                FOREIGN KEY (epi_request_id) REFERENCES epi_requests(id) ON DELETE SET NULL
            )
            '''
        )
    except Exception as _e:
        structured_log('warning', 'db.col_skip', error=str(_e))
    try:
        connection.execute(
            '''
            CREATE TABLE IF NOT EXISTS purchase_orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                purchase_request_id INTEGER,
                company_id INTEGER NOT NULL,
                unit_id INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'draft',
                po_number TEXT NOT NULL DEFAULT '',
                supplier TEXT NOT NULL DEFAULT '',
                supplier_cnpj TEXT NOT NULL DEFAULT '',
                expected_delivery_date TEXT NOT NULL DEFAULT '',
                notes TEXT NOT NULL DEFAULT '',
                total_value REAL NOT NULL DEFAULT 0,
                created_by_user_id INTEGER NOT NULL,
                created_by_name TEXT NOT NULL DEFAULT '',
                approved_by_user_id INTEGER,
                approved_by_name TEXT NOT NULL DEFAULT '',
                approved_at TEXT NOT NULL DEFAULT '',
                approval_comment TEXT NOT NULL DEFAULT '',
                received_by_user_id INTEGER,
                received_by_name TEXT NOT NULL DEFAULT '',
                received_at TEXT NOT NULL DEFAULT '',
                checked_at TEXT NOT NULL DEFAULT '',
                closed_at TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (purchase_request_id) REFERENCES purchase_requests(id) ON DELETE SET NULL,
                FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
                FOREIGN KEY (unit_id) REFERENCES units(id) ON DELETE RESTRICT,
                FOREIGN KEY (created_by_user_id) REFERENCES users(id) ON DELETE RESTRICT,
                FOREIGN KEY (approved_by_user_id) REFERENCES users(id) ON DELETE SET NULL,
                FOREIGN KEY (received_by_user_id) REFERENCES users(id) ON DELETE SET NULL
            )
            '''
        )
    except Exception as _e:
        structured_log('warning', 'db.col_skip', error=str(_e))
    try:
        connection.execute(
            '''
            CREATE TABLE IF NOT EXISTS purchase_order_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                purchase_order_id INTEGER NOT NULL,
                purchase_request_item_id INTEGER,
                company_id INTEGER NOT NULL,
                unit_id INTEGER NOT NULL,
                epi_id INTEGER NOT NULL,
                epi_name TEXT NOT NULL DEFAULT '',
                ca TEXT NOT NULL DEFAULT '',
                unit_measure TEXT NOT NULL DEFAULT '',
                manufacturer TEXT NOT NULL DEFAULT '',
                supplier TEXT NOT NULL DEFAULT '',
                glove_size TEXT NOT NULL DEFAULT 'N/A',
                size TEXT NOT NULL DEFAULT 'N/A',
                uniform_size TEXT NOT NULL DEFAULT 'N/A',
                quantity INTEGER NOT NULL DEFAULT 1,
                quantity_approved INTEGER NOT NULL DEFAULT 0,
                quantity_received INTEGER NOT NULL DEFAULT 0,
                unit_price REAL NOT NULL DEFAULT 0,
                total_price REAL NOT NULL DEFAULT 0,
                origin TEXT NOT NULL DEFAULT 'stock_minimum',
                employee_name TEXT NOT NULL DEFAULT '',
                employee_sector TEXT NOT NULL DEFAULT '',
                employee_role TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'open',
                notes TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (purchase_order_id) REFERENCES purchase_orders(id) ON DELETE CASCADE,
                FOREIGN KEY (purchase_request_item_id) REFERENCES purchase_request_items(id) ON DELETE SET NULL,
                FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
                FOREIGN KEY (unit_id) REFERENCES units(id) ON DELETE RESTRICT,
                FOREIGN KEY (epi_id) REFERENCES epis(id) ON DELETE RESTRICT
            )
            '''
        )
    except Exception as _e:
        structured_log('warning', 'db.col_skip', error=str(_e))
    try:
        connection.execute(
            '''
            CREATE TABLE IF NOT EXISTS purchase_order_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                purchase_order_id INTEGER NOT NULL,
                company_id INTEGER NOT NULL,
                file_name TEXT NOT NULL DEFAULT '',
                file_type TEXT NOT NULL DEFAULT '',
                file_data TEXT NOT NULL DEFAULT '',
                uploaded_by_user_id INTEGER NOT NULL,
                uploaded_by_name TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                FOREIGN KEY (purchase_order_id) REFERENCES purchase_orders(id) ON DELETE CASCADE,
                FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
                FOREIGN KEY (uploaded_by_user_id) REFERENCES users(id) ON DELETE RESTRICT
            )
            '''
        )
    except Exception as _e:
        structured_log('warning', 'db.col_skip', error=str(_e))
    try:
        connection.execute(
            '''
            CREATE TABLE IF NOT EXISTS purchase_approvals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                purchase_order_id INTEGER NOT NULL,
                company_id INTEGER NOT NULL,
                decision TEXT NOT NULL,
                comment TEXT NOT NULL DEFAULT '',
                actor_user_id INTEGER NOT NULL,
                actor_name TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                FOREIGN KEY (purchase_order_id) REFERENCES purchase_orders(id) ON DELETE CASCADE,
                FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
                FOREIGN KEY (actor_user_id) REFERENCES users(id) ON DELETE RESTRICT
            )
            '''
        )
    except Exception as _e:
        structured_log('warning', 'db.col_skip', error=str(_e))
    try:
        connection.execute(
            '''
            CREATE TABLE IF NOT EXISTS purchase_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                entity_type TEXT NOT NULL,
                entity_id INTEGER NOT NULL,
                action TEXT NOT NULL,
                status_from TEXT NOT NULL DEFAULT '',
                status_to TEXT NOT NULL DEFAULT '',
                comment TEXT NOT NULL DEFAULT '',
                actor_user_id INTEGER,
                actor_name TEXT NOT NULL DEFAULT '',
                actor_role TEXT NOT NULL DEFAULT '',
                reason TEXT NOT NULL DEFAULT '',
                destination TEXT NOT NULL DEFAULT '',
                ip_address TEXT NOT NULL DEFAULT '',
                session_ref TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE
            )
            '''
        )
    except Exception as _e:
        structured_log('warning', 'db.col_skip', error=str(_e))
    connection.execute('CREATE INDEX IF NOT EXISTS idx_purchase_requests_company ON purchase_requests (company_id, status)')
    connection.execute('CREATE INDEX IF NOT EXISTS idx_purchase_request_items_request ON purchase_request_items (purchase_request_id)')
    connection.execute('CREATE INDEX IF NOT EXISTS idx_purchase_orders_company ON purchase_orders (company_id, status)')
    connection.execute('CREATE INDEX IF NOT EXISTS idx_purchase_events_entity ON purchase_events (entity_type, entity_id)')
    _safe_add_column(connection, 'purchase_events', 'actor_role', "TEXT NOT NULL DEFAULT ''")
    _safe_add_column(connection, 'purchase_events', 'reason', "TEXT NOT NULL DEFAULT ''")
    _safe_add_column(connection, 'purchase_events', 'destination', "TEXT NOT NULL DEFAULT ''")
    _safe_add_column(connection, 'purchase_orders', 'postponed_until', "TEXT NOT NULL DEFAULT ''")
    _safe_add_column(connection, 'purchase_requests', 'postponed_until', "TEXT NOT NULL DEFAULT ''")
    _safe_add_column(connection, 'epi_requests', 'postponed_until', "TEXT NOT NULL DEFAULT ''")
    _safe_add_column(connection, 'purchase_requests', 'linked_po_number', "TEXT NOT NULL DEFAULT ''")
    _safe_add_column(connection, 'purchase_requests', 'linked_po_id', "INTEGER")
    _safe_add_column(connection, 'purchase_request_items', 'rejection_reason', "TEXT NOT NULL DEFAULT ''")
    _safe_add_column(connection, 'purchase_request_items', 'rejection_comment', "TEXT NOT NULL DEFAULT ''")
    _safe_add_column(connection, 'purchase_request_items', 'approval_decided_by_user_id', "INTEGER")
    _safe_add_column(connection, 'purchase_request_items', 'approval_decided_by_name', "TEXT NOT NULL DEFAULT ''")
    _safe_add_column(connection, 'purchase_request_items', 'approval_decided_at', "TEXT NOT NULL DEFAULT ''")
    # Colunas para revisão operacional do Admin e sugestões ao Comprador
    _safe_add_column(connection, 'purchase_orders', 'admin_review_by_user_id', "INTEGER")
    _safe_add_column(connection, 'purchase_orders', 'admin_review_by_name', "TEXT NOT NULL DEFAULT ''")
    _safe_add_column(connection, 'purchase_orders', 'admin_review_at', "TEXT NOT NULL DEFAULT ''")
    _safe_add_column(connection, 'purchase_orders', 'admin_review_comment', "TEXT NOT NULL DEFAULT ''")
    _safe_add_column(connection, 'purchase_orders', 'buyer_suggestions', "TEXT NOT NULL DEFAULT ''")
    try:
        connection.execute(
            '''
            CREATE TABLE IF NOT EXISTS authorized_suppliers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                cnpj TEXT NOT NULL DEFAULT '',
                category TEXT NOT NULL DEFAULT '',
                contact_email TEXT NOT NULL DEFAULT '',
                notes TEXT NOT NULL DEFAULT '',
                active INTEGER NOT NULL DEFAULT 1,
                source TEXT NOT NULL DEFAULT 'manual',
                created_by_user_id INTEGER,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(company_id, cnpj),
                FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
                FOREIGN KEY (created_by_user_id) REFERENCES users(id) ON DELETE SET NULL
            )
            '''
        )
    except Exception as _e:
        structured_log('warning', 'db.col_skip', error=str(_e))
    connection.execute('CREATE INDEX IF NOT EXISTS idx_authorized_suppliers_company ON authorized_suppliers (company_id, active)')
    try:
        connection.execute(
            '''
            CREATE TABLE IF NOT EXISTS user_unit_links (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                unit_id INTEGER NOT NULL,
                created_by_user_id INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(user_id, unit_id),
                FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (unit_id) REFERENCES units(id) ON DELETE CASCADE
            )
            '''
        )
        connection.execute('CREATE INDEX IF NOT EXISTS idx_user_unit_links_user ON user_unit_links (user_id)')
        connection.execute('CREATE INDEX IF NOT EXISTS idx_user_unit_links_company ON user_unit_links (company_id)')
    except Exception as _e:
        structured_log('warning', 'db.col_skip', error=str(_e))
    try:
        connection.execute(
            '''
            CREATE TABLE IF NOT EXISTS purchase_role_unit_links (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                employee_id INTEGER NOT NULL,
                role_type TEXT NOT NULL,
                unit_id INTEGER NOT NULL,
                created_by_user_id INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(employee_id, role_type, unit_id),
                FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
                FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE,
                FOREIGN KEY (unit_id) REFERENCES units(id) ON DELETE CASCADE,
                FOREIGN KEY (created_by_user_id) REFERENCES users(id) ON DELETE RESTRICT
            )
            '''
        )
        connection.execute('CREATE INDEX IF NOT EXISTS idx_purchase_role_links_employee ON purchase_role_unit_links (employee_id, role_type)')
        connection.execute('CREATE INDEX IF NOT EXISTS idx_purchase_role_links_company ON purchase_role_unit_links (company_id, role_type)')
    except Exception as _e:
        structured_log('warning', 'db.col_skip', error=str(_e))
    # ── Fim Fase 2 ────────────────────────────────────────────────────────
    try:
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
    except Exception as _e:
        structured_log('warning', 'db.col_skip', error=str(_e))
    try:
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
    except Exception as _e:
        structured_log('warning', 'db.col_skip', error=str(_e))
    # Colunas adicionais para fluxo completo de EPI feedback
    _safe_add_column(connection, 'epi_feedbacks', 'type', "TEXT NOT NULL DEFAULT 'avaliacao'")
    _safe_add_column(connection, 'epi_feedbacks', 'category', "TEXT NOT NULL DEFAULT ''")
    _safe_add_column(connection, 'epi_feedbacks', 'description', "TEXT NOT NULL DEFAULT ''")
    _safe_add_column(connection, 'epi_feedbacks', 'priority', "TEXT NOT NULL DEFAULT 'normal'")
    _safe_add_column(connection, 'epi_feedbacks', 'created_by_user_id', "INTEGER")
    _safe_add_column(connection, 'epi_feedbacks', 'assigned_epi_manager_id', "INTEGER")
    _safe_add_column(connection, 'epi_feedbacks', 'hseq_required', "INTEGER NOT NULL DEFAULT 0")
    _safe_add_column(connection, 'epi_feedbacks', 'hseq_user_id', "INTEGER")
    _safe_add_column(connection, 'epi_feedbacks', 'hseq_opinion', "TEXT NOT NULL DEFAULT ''")
    _safe_add_column(connection, 'epi_feedbacks', 'hseq_analyzed_at', "TEXT NOT NULL DEFAULT ''")
    _safe_add_column(connection, 'epi_feedbacks', 'admin_decision', "TEXT NOT NULL DEFAULT ''")
    _safe_add_column(connection, 'epi_feedbacks', 'admin_decision_by_user_id', "INTEGER")
    _safe_add_column(connection, 'epi_feedbacks', 'admin_decision_by_name', "TEXT NOT NULL DEFAULT ''")
    _safe_add_column(connection, 'epi_feedbacks', 'suggested_new_epi_link', "TEXT NOT NULL DEFAULT ''")
    _safe_add_column(connection, 'epi_feedbacks', 'admin_decision_at', "TEXT NOT NULL DEFAULT ''")
    _safe_add_column(connection, 'epi_feedbacks', 'final_justification', "TEXT NOT NULL DEFAULT ''")
    _safe_add_column(connection, 'epi_feedback_history', 'actor_role', "TEXT NOT NULL DEFAULT ''")
    _safe_add_column(connection, 'epi_feedback_history', 'action', "TEXT NOT NULL DEFAULT ''")
    _safe_add_column(connection, 'epi_feedback_history', 'previous_status', "TEXT NOT NULL DEFAULT ''")
    _safe_add_column(connection, 'epi_feedback_history', 'reason', "TEXT NOT NULL DEFAULT ''")
    # Avaliação e Sugestão de EPI — novos campos
    _safe_add_column(connection, 'epi_feedbacks', 'feedback_subtype', "TEXT NOT NULL DEFAULT ''")
    _safe_add_column(connection, 'epi_feedbacks', 'risk_level', "TEXT NOT NULL DEFAULT 'nenhum'")
    _safe_add_column(connection, 'epi_feedbacks', 'rejection_reason', "TEXT NOT NULL DEFAULT ''")
    _safe_add_column(connection, 'epi_feedbacks', 'supplier_eval_requested', "INTEGER NOT NULL DEFAULT 0")
    _safe_add_column(connection, 'epi_feedbacks', 'reassessment_period', "TEXT NOT NULL DEFAULT ''")
    _safe_add_column(connection, 'epi_feedbacks', 'manager_eval_status', "TEXT NOT NULL DEFAULT 'pendente'")
    _safe_add_column(connection, 'epi_feedbacks', 'manager_eval_notes', "TEXT NOT NULL DEFAULT ''")
    _safe_add_column(connection, 'epi_feedbacks', 'manager_eval_at', "TEXT NOT NULL DEFAULT ''")
    _safe_add_column(connection, 'epi_feedbacks', 'employee_portal_status', "TEXT NOT NULL DEFAULT ''")
    _safe_add_column(connection, 'epi_feedbacks', 'employee_portal_message', "TEXT NOT NULL DEFAULT ''")
    _safe_add_column(connection, 'epi_feedbacks', 'epi_rank', "TEXT NOT NULL DEFAULT ''")
    _safe_add_column(connection, 'epi_feedbacks', 'admin_tech_decision', "TEXT NOT NULL DEFAULT ''")
    _safe_add_column(connection, 'epi_feedbacks', 'atende_nr', "TEXT NOT NULL DEFAULT ''")
    _safe_add_column(connection, 'epi_feedbacks', 'reduz_risco', "TEXT NOT NULL DEFAULT ''")
    _safe_add_column(connection, 'epi_feedbacks', 'problemas_observados', "TEXT NOT NULL DEFAULT '[]'")
    _safe_add_column(connection, 'epi_feedbacks', 'custo_estimado', "TEXT NOT NULL DEFAULT ''")
    _safe_add_column(connection, 'epi_feedbacks', 'durabilidade_esperada', "TEXT NOT NULL DEFAULT ''")
    _safe_add_column(connection, 'epi_feedbacks', 'disponibilidade_mercado', "TEXT NOT NULL DEFAULT ''")
    _safe_add_column(connection, 'epi_feedbacks', 'admin_tech_notes', "TEXT NOT NULL DEFAULT ''")
    _safe_add_column(connection, 'epi_feedbacks', 'marca_modelo_sugerido', "TEXT NOT NULL DEFAULT ''")
    _safe_add_column(connection, 'epi_feedbacks', 'admin_tech_eval_at', "TEXT NOT NULL DEFAULT ''")
    for _rc in ('excelente', 'otimo', 'muito_bom', 'ruim', 'muito_ruim', 'pessimo',
                'excelente_sug', 'otima_sug', 'muito_boa_sug', 'pessima_sug', 'muito_ruim_sug', 'ruim_sug'):
        _safe_add_column(connection, 'epi_evaluation_summary', f'rank_{_rc}', 'INTEGER NOT NULL DEFAULT 0')
    try:
        connection.execute(
            '''
            CREATE TABLE IF NOT EXISTS epi_evaluation_summary (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                epi_id INTEGER NOT NULL,
                epi_name TEXT NOT NULL DEFAULT '',
                total_avaliacoes INTEGER NOT NULL DEFAULT 0,
                total_reclamacoes INTEGER NOT NULL DEFAULT 0,
                total_elogios INTEGER NOT NULL DEFAULT 0,
                total_sugestoes INTEGER NOT NULL DEFAULT 0,
                avg_comfort REAL NOT NULL DEFAULT 0,
                avg_quality REAL NOT NULL DEFAULT 0,
                avg_adequacy REAL NOT NULL DEFAULT 0,
                avg_performance REAL NOT NULL DEFAULT 0,
                score REAL NOT NULL DEFAULT 0,
                evaluation_status TEXT NOT NULL DEFAULT 'normal',
                last_computed_at TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
                FOREIGN KEY (epi_id) REFERENCES epis(id) ON DELETE CASCADE,
                UNIQUE (company_id, epi_id)
            )
            '''
        )
    except Exception as _e:
        structured_log('warning', 'db.col_skip', error=str(_e))
    try:
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
    except Exception as _e:
        structured_log('warning', 'db.col_skip', error=str(_e))
    try:
        connection.execute(
            '''
            CREATE TABLE IF NOT EXISTS report_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                unit_id INTEGER,
                requester_user_id INTEGER NOT NULL,
                requester_name TEXT NOT NULL DEFAULT '',
                period_year INTEGER,
                period_month INTEGER,
                notes TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'pending',
                handled_by_user_id INTEGER,
                handled_by_name TEXT NOT NULL DEFAULT '',
                handled_at TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL
            )
            '''
        )
    except Exception as _e:
        structured_log('warning', 'db.col_skip', error=str(_e))


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


def _operational_error_code(kind):
    return {
        'permission_denied': 'DB_PERMISSION_ERROR',
        'readonly_database': 'DB_PERMISSION_ERROR',
        'schema_health_failed': 'DB_SCHEMA_MISMATCH',
        'schema_missing_object': 'DB_SCHEMA_MISMATCH',
        'schema_missing_table': 'DB_SCHEMA_MISMATCH',
        'column_missing_after_migration': 'DB_SCHEMA_MISMATCH',
        'ddl_incompatible': 'DB_DDL_INCOMPATIBLE',
        'corrupted_database': 'DB_CORRUPTION_SUSPECTED',
        'io_error': 'DB_IO_ERROR',
    }.get(str(kind or ''), 'DB_DRIVER_UNEXPECTED')


def _set_bootstrap_state(**values):
    with DB_BOOTSTRAP_STATE_LOCK:
        DB_BOOTSTRAP_STATE.update(values)


def _get_bootstrap_state():
    with DB_BOOTSTRAP_STATE_LOCK:
        return dict(DB_BOOTSTRAP_STATE)


def current_runtime_health():
    state = _get_bootstrap_state()
    ready = bool(state.get('ready'))
    has_failure = bool(state.get('error_code'))
    phase = 'ready' if ready else ('failed' if has_failure else 'starting')
    payload = {
        'status': 'ok',
        'phase': phase,
        'ready': ready,
        'error_code': state.get('error_code') or '',
        'error_kind': state.get('error_kind') or '',
        'error_message': state.get('error_message') or '',
        'started_at': state.get('started_at') or '',
        'completed_at': state.get('completed_at') or '',
    }
    return payload


def runtime_probe_response(probe='ready'):
    probe_name = str(probe or 'ready').strip().lower()
    state = current_runtime_health()
    payload = dict(state)
    payload['probe'] = probe_name

    if probe_name in {'live', 'liveness', 'health'}:
        payload['status'] = 'ok'
        return 200, payload

    if state.get('ready'):
        payload['status'] = 'ok'
        return 200, payload

    payload['status'] = 'starting' if state.get('phase') == 'starting' else 'failed'
    payload['error_code'] = payload.get('error_code') or 'DB_BOOTSTRAP_NOT_READY'
    payload['error_kind'] = payload.get('error_kind') or 'bootstrap_not_ready'
    return 503, payload


class SchemaMigrationError(RuntimeError):
    """Erro fatal de migração estrutural do banco."""

    def __init__(self, message, *, kind='unexpected', context=None):
        super().__init__(message)
        self.kind = str(kind or 'unexpected')
        self.context = context or {}


def _is_sqlite_connection(connection):
    module_name = str(getattr(type(connection), '__module__', '')).lower()
    class_name = str(getattr(type(connection), '__name__', '')).lower()
    return 'sqlite' in module_name or 'sqlite' in class_name


def _classify_db_error(error):
    message = str(error or '').lower()
    if isinstance(error, (PermissionError,)):
        return 'permission_denied'
    if isinstance(error, OSError):
        return 'io_error'
    if 'readonly' in message or 'read-only' in message or 'attempt to write a readonly database' in message:
        return 'readonly_database'
    if 'permission denied' in message or 'not authorized' in message:
        return 'permission_denied'
    if 'malformed' in message or 'corrupt' in message or 'not a database' in message:
        return 'corrupted_database'
    if 'i/o error' in message or 'input/output error' in message or 'disk i/o' in message:
        return 'io_error'
    if 'syntax error' in message or 'unsupported' in message:
        return 'ddl_incompatible'
    if 'no such table' in message or 'no such column' in message:
        return 'schema_missing_object'
    return 'driver_unexpected'


def run_schema_precheck(connection):
    """Pré-check bloqueante do ambiente de banco antes de migrar schema."""
    phase = 'precheck'
    structured_log('info', 'db.schema_precheck_started', sqlite=bool(_is_sqlite_connection(connection)))
    try:
        connection.execute('SELECT 1').fetchone()
        if _is_sqlite_connection(connection):
            db_row = connection.execute('PRAGMA database_list').fetchone()
            db_path = ''
            if db_row:
                try:
                    db_path = str(db_row['file'])
                except Exception:
                    db_path = str(db_row[2] if len(db_row) > 2 else '')
            query_only_row = connection.execute('PRAGMA query_only').fetchone()
            query_only = int(query_only_row[0] if query_only_row else 0)
            if query_only == 1:
                raise SchemaMigrationError('Banco SQLite está em modo somente leitura (PRAGMA query_only=1).', kind='readonly_database', context={'phase': phase, 'database_path': db_path})
            integrity_row = connection.execute('PRAGMA quick_check').fetchone()
            integrity_result = str(integrity_row[0] if integrity_row else '').strip().lower()
            if integrity_result not in {'ok', 'ok\n'}:
                raise SchemaMigrationError(f'Integridade SQLite inválida: {integrity_result or "desconhecido"}.', kind='corrupted_database', context={'phase': phase, 'database_path': db_path})
            connection.execute('DROP TABLE IF EXISTS __schema_precheck_write__')
            connection.execute('CREATE TABLE __schema_precheck_write__ (id INTEGER)')
            connection.execute('DROP TABLE __schema_precheck_write__')
            connection.commit()
            structured_log('info', 'db.schema_precheck_ok', phase=phase, database_path=db_path or ':memory:')
            return
        # PostgreSQL/Outros via wrapper
        try:
            ro_row = connection.execute('SHOW transaction_read_only').fetchone()
            read_only = str(ro_row[0] if ro_row else '').strip().lower()
            if read_only in {'on', 'true', '1'}:
                raise SchemaMigrationError('Sessão do banco em modo somente leitura.', kind='readonly_database', context={'phase': phase})
        except SchemaMigrationError:
            raise
        except Exception as read_only_error:
            structured_log('warning', 'db.schema_precheck_readonly_probe_failed', phase=phase, error=str(read_only_error))
        structured_log('info', 'db.schema_precheck_ok', phase=phase, database_path='remote')
    except SchemaMigrationError:
        raise
    except Exception as exc:
        try:
            connection.rollback()
        except Exception:
            pass
        kind = _classify_db_error(exc)
        structured_log('error', 'db.schema_precheck_failed', phase=phase, error=str(exc), kind=kind)
        raise SchemaMigrationError(f'Pré-check de schema falhou: {exc}', kind=kind, context={'phase': phase}) from exc


def validate_schema_health(connection):
    """Validação bloqueante do schema mínimo esperado para subir a aplicação."""
    required_schema = {
        'deliveries': {'id', 'company_id', 'employee_id', 'epi_id', 'delivery_date', 'returned_date', 'returned_condition', 'return_movement_id'},
        'epi_devolutions': {'id', 'delivery_id', 'returned_date', 'ficha_period_id', 'stock_movement_id', 'signature_name', 'signature_at'},
        'stock_movements': {'id', 'company_id', 'unit_id', 'epi_id', 'movement_type', 'source_type'},
        'epi_stock_items': {'id', 'delivery_id', 'status'},
        'epi_ficha_periods': {'id', 'employee_id', 'period_start', 'period_end', 'status'},
        'epi_ficha_items': {'id', 'ficha_period_id', 'delivery_id'},
    }
    missing = []
    for table, columns in required_schema.items():
        if not _table_exists(connection, table):
            missing.append(f'table:{table}')
            continue
        current_cols = _table_columns(connection, table)
        for column in sorted(columns):
            if column not in current_cols:
                missing.append(f'column:{table}.{column}')
    if missing:
        structured_log('error', 'db.schema_health_failed', missing=missing, total_missing=len(missing))
        raise SchemaMigrationError(
            f'Schema mínimo inconsistente. Itens ausentes: {", ".join(missing[:12])}',
            kind='schema_health_failed',
            context={'missing': missing},
        )
    structured_log('info', 'db.schema_health_ok', tables=len(required_schema))


def _table_exists(connection, table):
    table_name = str(table or '').strip()
    if not table_name:
        return False
    try:
        connection.execute('SELECT 1').fetchone()
        if _is_sqlite_connection(connection):
            db_row = connection.execute('PRAGMA database_list').fetchone()
            db_path = ''
            if db_row:
                try:
                    db_path = str(db_row['file'])
                except Exception:
                    db_path = str(db_row[2] if len(db_row) > 2 else '')
            query_only_row = connection.execute('PRAGMA query_only').fetchone()
            query_only = int(query_only_row[0] if query_only_row else 0)
            if query_only == 1:
                raise SchemaMigrationError('Banco SQLite está em modo somente leitura (PRAGMA query_only=1).', kind='readonly_database', context={'phase': phase, 'database_path': db_path})
            integrity_row = connection.execute('PRAGMA quick_check').fetchone()
            integrity_result = str(integrity_row[0] if integrity_row else '').strip().lower()
            if integrity_result not in {'ok', 'ok\n'}:
                raise SchemaMigrationError(f'Integridade SQLite inválida: {integrity_result or "desconhecido"}.', kind='corrupted_database', context={'phase': phase, 'database_path': db_path})
            connection.execute('DROP TABLE IF EXISTS __schema_precheck_write__')
            connection.execute('CREATE TABLE __schema_precheck_write__ (id INTEGER)')
            connection.execute('DROP TABLE __schema_precheck_write__')
            connection.commit()
            structured_log('info', 'db.schema_precheck_ok', phase=phase, database_path=db_path or ':memory:')
            return
        # PostgreSQL/Outros via wrapper
        try:
            ro_row = connection.execute('SHOW transaction_read_only').fetchone()
            read_only = str(ro_row[0] if ro_row else '').strip().lower()
            if read_only in {'on', 'true', '1'}:
                raise SchemaMigrationError('Sessão do banco em modo somente leitura.', kind='readonly_database', context={'phase': phase})
        except SchemaMigrationError:
            raise
        except Exception as read_only_error:
            structured_log('warning', 'db.schema_precheck_readonly_probe_failed', phase=phase, error=str(read_only_error))
        structured_log('info', 'db.schema_precheck_ok', phase=phase, database_path='remote')
    except SchemaMigrationError:
        raise
    except Exception as exc:
        try:
            connection.rollback()
        except Exception:
            pass
        kind = _classify_db_error(exc)
        structured_log('error', 'db.schema_precheck_failed', phase=phase, error=str(exc), kind=kind)
        raise SchemaMigrationError(f'Pré-check de schema falhou: {exc}', kind=kind, context={'phase': phase}) from exc


def validate_schema_health(connection):
    """Validação bloqueante do schema mínimo esperado para subir a aplicação."""
    required_schema = {
        'deliveries': {'id', 'company_id', 'employee_id', 'epi_id', 'delivery_date', 'returned_date', 'returned_condition', 'return_movement_id'},
        'epi_devolutions': {'id', 'delivery_id', 'returned_date', 'ficha_period_id', 'stock_movement_id', 'signature_name', 'signature_at'},
        'stock_movements': {'id', 'company_id', 'unit_id', 'epi_id', 'movement_type', 'source_type'},
        'epi_stock_items': {'id', 'delivery_id', 'status'},
        'epi_ficha_periods': {'id', 'employee_id', 'period_start', 'period_end', 'status'},
        'epi_ficha_items': {'id', 'ficha_period_id', 'delivery_id'},
    }
    missing = []
    for table, columns in required_schema.items():
        if not _table_exists(connection, table):
            missing.append(f'table:{table}')
            continue
        current_cols = _table_columns(connection, table)
        for column in sorted(columns):
            if column not in current_cols:
                missing.append(f'column:{table}.{column}')
    if missing:
        structured_log('error', 'db.schema_health_failed', missing=missing, total_missing=len(missing))
        raise SchemaMigrationError(
            f'Schema mínimo inconsistente. Itens ausentes: {", ".join(missing[:12])}',
            kind='schema_health_failed',
            context={'missing': missing},
        )
    structured_log('info', 'db.schema_health_ok', tables=len(required_schema))


def _table_exists(connection, table):
    table_name = str(table or '').strip()
    if not table_name:
        return False
    try:
        if _is_sqlite_connection(connection):
            row = connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ? LIMIT 1",
                (table_name,),
            ).fetchone()
            return row is not None
        row = connection.execute(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_name = ? LIMIT 1",
            (table_name,),
        ).fetchone()
        return row is not None
    except Exception:
        return False


def _table_columns(connection, table):
    table_name = str(table or '').strip()
    if not table_name:
        return set()
    try:
        if _is_sqlite_connection(connection):
            rows = connection.execute(f"PRAGMA table_info({table_name})").fetchall()
            return {str(row['name'] if isinstance(row, dict) else row[1]) for row in rows}
        rows = connection.execute(
            "SELECT column_name FROM information_schema.columns WHERE table_name = ?",
            (table_name,),
        ).fetchall()
        result = set()
        for row in rows:
            if isinstance(row, dict):
                result.add(str(row.get('column_name') or ''))
            elif hasattr(row, 'keys'):
                result.add(str(row['column_name']))
            else:
                result.add(str(row[0]))
        return {item for item in result if item}
    except Exception:
        return set()


def _col_exists(connection, table, column):
    return str(column or '').strip() in _table_columns(connection, table)


def _safe_add_column(connection, table, column, definition, log_event='db.col_skip'):
    """Adiciona coluna apenas se ela não existir e valida pós-migração."""
    table_name = str(table or '').strip()
    column_name = str(column or '').strip()
    if not table_name or not column_name:
        raise SchemaMigrationError(
            f'Parâmetros inválidos de migração: table={table_name!r}, column={column_name!r}.',
            kind='migration_invalid_arguments',
            context={'table': table_name, 'column': column_name, 'phase': 'migration'},
        )
    if not _table_exists(connection, table_name):
        raise SchemaMigrationError(
            f'Tabela ausente para migração de coluna: {table_name}.',
            kind='schema_missing_table',
            context={'table': table_name, 'column': column_name, 'phase': 'migration'},
        )
    if _col_exists(connection, table_name, column_name):
        return  # coluna ja existe — nao toca na tabela
    try:
        connection.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}")
        connection.commit()
        if not _col_exists(connection, table_name, column_name):
            raise SchemaMigrationError(
                f'Coluna {table_name}.{column_name} não encontrada após ALTER TABLE.',
                kind='column_missing_after_migration',
                context={'table': table_name, 'column': column_name, 'phase': 'post_migration_validation'},
            )
        structured_log('info', 'db.col_added', table=table_name, column=column_name)
    except Exception as _e:
        try:
            connection.rollback()
        except Exception:
            pass
        if _col_exists(connection, table_name, column_name):
            structured_log('info', 'db.col_already_present_after_error', table=table_name, column=column_name, error=str(_e))
            return
        kind = _classify_db_error(_e)
        structured_log('error', log_event, table=table_name, column=column_name, error=str(_e), kind=kind, phase='migration')
        raise SchemaMigrationError(
            f'Falha ao adicionar coluna {table_name}.{column_name}: {_e}',
            kind=kind,
            context={'table': table_name, 'column': column_name, 'phase': 'migration'},
        ) from _e


def _ensure_ficha_periods_sequence_unique(connection):
    def _normalize_ficha_sequence_row(row, keys=None, *, phase='ficha_sequence_unique_migration', query='', step='row_normalization'):
        key_list = tuple(keys or ())
        context_base = {
            'phase': phase,
            'query': query,
            'step': step,
            'row_type': type(row).__name__ if row is not None else 'NoneType',
            'row_repr': repr(row),
            'expected_keys': list(key_list),
        }
        if row is None:
            raise SchemaMigrationError(
                'row_none',
                kind='schema_health_failed',
                context={**context_base, 'found_keys': []},
            )

        mapping = None
        if isinstance(row, dict):
            mapping = dict(row)
        elif hasattr(row, '_mapping'):
            try:
                mapping = dict(row._mapping)
            except (TypeError, ValueError) as exc:
                raise SchemaMigrationError(
                    'row_mapping_invalid',
                    kind='driver_unexpected',
                    context={**context_base, 'found_keys': []},
                ) from exc
        elif hasattr(row, 'keys'):
            try:
                row_keys = list(row.keys())
                mapping = {key: row[key] for key in row_keys}
            except (KeyError, TypeError, IndexError, AttributeError) as exc:
                raise SchemaMigrationError(
                    'row_keys_access_failed',
                    kind='driver_unexpected',
                    context={**context_base, 'found_keys': []},
                ) from exc

        if mapping is not None:
            if not key_list:
                return dict(mapping)
            normalized = {}
            missing = []
            for key in key_list:
                aliases = (key, 'conname') if key == 'constraint_name' else (key,)
                found = False
                for alias in aliases:
                    if alias in mapping:
                        normalized[key] = mapping[alias]
                        found = True
                        break
                if not found:
                    missing.append(key)
            if missing:
                raise SchemaMigrationError(
                    'row_missing_expected_keys',
                    kind='schema_health_failed',
                    context={**context_base, 'found_keys': sorted(str(k) for k in mapping.keys())},
                )
            return normalized

        if isinstance(row, (tuple, list)):
            row_values = tuple(row)
            if not key_list:
                raise SchemaMigrationError(
                    'missing_keys_for_tuple',
                    kind='schema_health_failed',
                    context={**context_base, 'found_keys': [], 'row_len': len(row_values), 'expected_len': 0},
                )
            if len(row_values) < len(key_list):
                raise SchemaMigrationError(
                    'tuple_len_invalid',
                    kind='schema_health_failed',
                    context={**context_base, 'found_keys': [], 'row_len': len(row_values), 'expected_len': len(key_list)},
                )
            return dict(zip(key_list, row_values))

        raise SchemaMigrationError(
            'unsupported_row_type',
            kind='driver_unexpected',
            context={**context_base, 'found_keys': []},
        )

    try:
        structured_log(
            'info',
            'db.ficha_sequence_safe_row_version',
            supports_step=True,
            normalizer='_normalize_ficha_sequence_row',
            table='epi_ficha_periods',
            phase='ficha_sequence_unique_migration',
        )
        if _is_sqlite_connection(connection):
            table_sql_row = connection.execute(
                "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'epi_ficha_periods'"
            ).fetchone()
            table_sql = str(_normalize_ficha_sequence_row(table_sql_row, keys=('sql',), query='sqlite_master.sql', step='sqlite_load_table_sql').get('sql') or '')
            legacy_unique = 'UNIQUE(employee_id, period_start, period_end)' in table_sql
            has_sequence_unique = 'UNIQUE(employee_id, period_start, period_end, ficha_sequence)' in table_sql
            if not legacy_unique or has_sequence_unique:
                return
            connection.execute('ALTER TABLE epi_ficha_periods RENAME TO epi_ficha_periods_legacy')
            connection.execute(
                '''
                CREATE TABLE epi_ficha_periods (
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
                    batch_signature_comment TEXT NOT NULL DEFAULT '',
                    ficha_sequence INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(employee_id, period_start, period_end, ficha_sequence),
                    FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
                    FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE,
                    FOREIGN KEY (unit_id) REFERENCES units(id) ON DELETE RESTRICT
                )
                '''
            )
            connection.execute(
                '''
                INSERT INTO epi_ficha_periods (
                    id, company_id, employee_id, unit_id, schedule_type, period_start, period_end,
                    status, batch_signature_name, batch_signature_data, batch_signature_ip, batch_signature_at,
                    batch_signature_comment, ficha_sequence, created_at, updated_at
                )
                SELECT
                    id, company_id, employee_id, unit_id, schedule_type, period_start, period_end,
                    status, batch_signature_name, batch_signature_data, batch_signature_ip, batch_signature_at,
                    batch_signature_comment, COALESCE(ficha_sequence, 1), created_at, updated_at
                FROM epi_ficha_periods_legacy
                '''
            )
            connection.execute('DROP TABLE epi_ficha_periods_legacy')
            connection.commit()
            return

        # Postgres path (sem sqlite_master/rebuild SQLite)

        # Idempotency check: skip entirely if the unique index already exists.
        # Prevents re-applying an already-completed migration on every cold start.
        _idx_exists = connection.execute(
            """
            SELECT 1 FROM pg_indexes
            WHERE schemaname = current_schema()
              AND tablename = 'epi_ficha_periods'
              AND indexname = 'uq_epi_ficha_periods_employee_window_sequence'
            """
        ).fetchone()
        if _idx_exists:
            return

        # Check current nullability so we only ALTER when actually needed.
        _col_info = connection.execute(
            """
            SELECT
                is_nullable AS ficha_sequence_is_nullable,
                column_default AS ficha_sequence_column_default
            FROM information_schema.columns
            WHERE table_schema = current_schema()
              AND table_name = 'epi_ficha_periods'
              AND column_name = 'ficha_sequence'
            """
        ).fetchone()
        structured_log(
            'info',
            'db.ficha_sequence_metadata_raw',
            raw_type=type(_col_info).__name__,
            raw_repr=repr(_col_info),
            table='epi_ficha_periods',
            phase='ficha_sequence_unique_migration',
        )
        if _col_info is None:
            raise SchemaMigrationError(
                'Metadata da coluna ficha_sequence não encontrada.',
                kind='schema_missing_object',
                context={'table': 'epi_ficha_periods', 'column': 'ficha_sequence', 'phase': 'ficha_sequence_unique_migration'},
            )
        _col_data = _normalize_ficha_sequence_row(
            _col_info,
            keys=('ficha_sequence_is_nullable', 'ficha_sequence_column_default'),
            query='information_schema.columns.ficha_sequence',
            step='load_column_metadata',
        )
        is_nullable = _col_data.get('ficha_sequence_is_nullable')
        column_default = _col_data.get('ficha_sequence_column_default')
        structured_log(
            'info',
            'db.ficha_sequence_metadata_loaded',
            is_nullable=str(is_nullable),
            column_default='' if column_default is None else str(column_default),
            table='epi_ficha_periods',
            phase='ficha_sequence_unique_migration',
        )
        if not column_default or '1' not in str(column_default):
            connection.execute('ALTER TABLE epi_ficha_periods ALTER COLUMN ficha_sequence SET DEFAULT 1')
        connection.execute('UPDATE epi_ficha_periods SET ficha_sequence = 1 WHERE ficha_sequence IS NULL')
        if str(is_nullable).upper() == 'YES':
            connection.execute('ALTER TABLE epi_ficha_periods ALTER COLUMN ficha_sequence SET NOT NULL')

        duplicate_rows = connection.execute(
            '''
            SELECT employee_id, period_start, period_end, ficha_sequence, COUNT(*) AS duplicate_count
            FROM epi_ficha_periods
            GROUP BY employee_id, period_start, period_end, ficha_sequence
            HAVING COUNT(*) > 1
            '''
        ).fetchall()
        structured_log(
            'info',
            'db.ficha_sequence_duplicates_checked',
            duplicate_count=len(duplicate_rows or []),
            table='epi_ficha_periods',
            phase='ficha_sequence_unique_migration',
        )
        if duplicate_rows:
            duplicate_sample = []
            for row in duplicate_rows[:5]:

                _duplicate_data = _normalize_ficha_sequence_row(
                    row,
                    keys=('employee_id', 'period_start', 'period_end', 'ficha_sequence', 'duplicate_count'),
                    query='duplicates_query',
                    step='build_duplicate_sample',
                )
                employee_id = _duplicate_data.get('employee_id')
                period_start = _duplicate_data.get('period_start')
                period_end = _duplicate_data.get('period_end')
                ficha_sequence = _duplicate_data.get('ficha_sequence')
                duplicate_count = _duplicate_data.get('duplicate_count', 0)
                duplicate_sample.append(
                    {
                        'employee_id': employee_id,
                        'period_start': period_start,
                        'period_end': period_end,
                        'ficha_sequence': ficha_sequence,
                        'duplicate_count': int(duplicate_count or 0),
                    }
                )
            structured_log(
                'critical',
                'db.ficha_periods_duplicate_detected',
                count=len(duplicate_rows),
                sample=duplicate_sample,
                table='epi_ficha_periods',
                phase='ficha_sequence_unique_migration',
            )
            raise SchemaMigrationError(
                'Dados duplicados em epi_ficha_periods impedem criação de índice único.',
                kind='duplicate_key_conflict',
                context={'table': 'epi_ficha_periods', 'phase': 'ficha_sequence_unique_migration'},
            )

        structured_log('info', 'db.step_started', step='load_legacy_constraints', table='epi_ficha_periods', phase='ficha_sequence_unique_migration')
        structured_log('info', 'db.ficha_sequence_before_load_legacy_constraints', table='epi_ficha_periods', phase='ficha_sequence_unique_migration')
        try:
            constraints_cursor = connection.execute(
                """
                SELECT c.conname AS constraint_name
                FROM pg_constraint c
                JOIN pg_class t ON t.oid = c.conrelid
                JOIN pg_namespace n ON n.oid = t.relnamespace
                WHERE t.relname = 'epi_ficha_periods'
                  AND n.nspname = current_schema()
                  AND c.contype = 'u'
                  AND pg_get_constraintdef(c.oid) ILIKE ?
                """,
                ('UNIQUE (employee_id, period_start, period_end)%',),
            )
            description = getattr(constraints_cursor, 'description', None)
            if description is None or not isinstance(description, (list, tuple)) or len(description) < 1:
                raise SchemaMigrationError(
                    'Cursor de constraints legadas sem metadata válida.',
                    kind='driver_unexpected',
                    context={
                        'step': 'load_legacy_constraints',
                        'query_name': 'pg_constraint_legacy_unique',
                        'description_repr': repr(description),
                        'description_type': type(description).__name__,
                    },
                )
            structured_log(
                'info',
                'db.ficha_sequence_legacy_constraints_cursor_validated',
                row_count=0,
                table='epi_ficha_periods',
                phase='ficha_sequence_unique_migration',
            )
            old_constraints = constraints_cursor.fetchall()
            if old_constraints is None:
                raise SchemaMigrationError(
                    'fetchall() de constraints legadas retornou None.',
                    kind='driver_unexpected',
                    context={'step': 'load_legacy_constraints', 'query_name': 'pg_constraint_legacy_unique', 'rows_type': 'NoneType'},
                )
            if isinstance(old_constraints, (str, bytes)):
                raise SchemaMigrationError(
                    'fetchall() de constraints legadas retornou tipo inválido.',
                    kind='driver_unexpected',
                    context={'step': 'load_legacy_constraints', 'query_name': 'pg_constraint_legacy_unique', 'rows_type': type(old_constraints).__name__},
                )
            if not isinstance(old_constraints, (list, tuple)):
                try:
                    old_constraints = list(old_constraints)
                except Exception as exc:
                    raise SchemaMigrationError(
                        'Resultado de constraints legadas não é iterável seguro.',
                        kind='driver_unexpected',
                        context={'step': 'load_legacy_constraints', 'query_name': 'pg_constraint_legacy_unique', 'rows_type': type(old_constraints).__name__, 'error': str(exc), 'error_type': type(exc).__name__},
                    ) from exc
            structured_log(
                'info',
                'db.ficha_sequence_legacy_constraints_rows_loaded',
                row_count=len(old_constraints),
                table='epi_ficha_periods',
                phase='ficha_sequence_unique_migration',
            )
        except SchemaMigrationError:
            raise
        except Exception as exc:
            structured_log(
                'critical',
                'db.step_failed',
                step='load_legacy_constraints',
                error=str(exc),
                error_type=type(exc).__name__,
                table='epi_ficha_periods',
                phase='ficha_sequence_unique_migration',
            )
            raise SchemaMigrationError(
                'Falha ao carregar constraints legadas da migração de ficha_sequence.',
                kind='driver_unexpected',
                context={'step': 'load_legacy_constraints', 'query_name': 'pg_constraint_legacy_unique', 'row_type': None, 'row_repr': None, 'error': str(exc), 'error_type': type(exc).__name__},
            ) from exc
        structured_log('info', 'db.ficha_sequence_after_load_legacy_constraints', table='epi_ficha_periods', phase='ficha_sequence_unique_migration', constraint_count=len(old_constraints or []))
        structured_log('info', 'db.step_completed', step='load_legacy_constraints', table='epi_ficha_periods', phase='ficha_sequence_unique_migration')
        structured_log(
            'info',
            'db.ficha_sequence_legacy_constraints_loaded',
            constraint_count=len(old_constraints or []),
            table='epi_ficha_periods',
            phase='ficha_sequence_unique_migration',
        )
        for row in old_constraints:
            try:
                normalized = _normalize_ficha_sequence_row(
                    row,
                    keys=('constraint_name',),
                    query='pg_constraint_legacy_unique',
                    step='load_legacy_constraints',
                )
                constraint_name = normalized['constraint_name']
            except SchemaMigrationError:
                raise
            except Exception as exc:
                raise SchemaMigrationError(
                    'Falha ao normalizar linha de constraint legada.',
                    kind='driver_unexpected',
                    context={
                        'step': 'load_legacy_constraints',
                        'query_name': 'pg_constraint_legacy_unique',
                        'row_type': type(row).__name__,
                        'row_repr': repr(row),
                        'error': str(exc),
                        'error_type': type(exc).__name__,
                    },
                ) from exc
            name = str(constraint_name or '').strip()
            if name:
                structured_log('info', 'db.ficha_sequence_before_drop_legacy_constraint', table='epi_ficha_periods', phase='ficha_sequence_unique_migration', constraint_name=name)
                try:
                    structured_log('info', 'db.step_started', step='drop_legacy_constraint', table='epi_ficha_periods', phase='ficha_sequence_unique_migration', constraint_name=name)
                    connection.execute(f'ALTER TABLE epi_ficha_periods DROP CONSTRAINT IF EXISTS "{name}"')
                    structured_log('info', 'db.step_completed', step='drop_legacy_constraint', table='epi_ficha_periods', phase='ficha_sequence_unique_migration', constraint_name=name)
                except Exception as exc:
                    structured_log(
                        'critical',
                        'db.step_failed',
                        step='drop_legacy_constraint',
                        error=str(exc),
                        error_type=type(exc).__name__,
                        table='epi_ficha_periods',
                        phase='ficha_sequence_unique_migration',
                        constraint_name=name,
                    )
                    raise SchemaMigrationError(
                        'Falha ao remover constraint legada da migração de ficha_sequence.',
                        kind='driver_unexpected',
                        context={'step': 'drop_legacy_constraint', 'query_name': 'alter_table.drop_constraint', 'row_type': type(row).__name__, 'row_repr': repr(row), 'constraint_name': name},
                    ) from exc
                structured_log('info', 'db.ficha_sequence_after_drop_legacy_constraint', table='epi_ficha_periods', phase='ficha_sequence_unique_migration', constraint_name=name)

        structured_log('info', 'db.ficha_sequence_before_create_unique_index', table='epi_ficha_periods', phase='ficha_sequence_unique_migration')
        structured_log('info', 'db.step_started', step='create_unique_index', table='epi_ficha_periods', phase='ficha_sequence_unique_migration')
        try:
            connection.execute(
                'CREATE UNIQUE INDEX IF NOT EXISTS uq_epi_ficha_periods_employee_window_sequence '
                'ON epi_ficha_periods (employee_id, period_start, period_end, ficha_sequence)'
            )
        except SchemaMigrationError:
            raise
        except Exception as exc:
            structured_log(
                'critical',
                'db.step_failed',
                step='create_unique_index',
                error=str(exc),
                error_type=type(exc).__name__,
                table='epi_ficha_periods',
                phase='ficha_sequence_unique_migration',
            )
            raise SchemaMigrationError(
                'Falha ao criar índice único da migração de ficha_sequence.',
                kind='driver_unexpected',
                context={'step': 'create_unique_index', 'query_name': 'create_unique_index', 'row_type': None, 'row_repr': None, 'error': str(exc), 'error_type': type(exc).__name__},
            ) from exc
        structured_log('info', 'db.step_completed', step='create_unique_index', table='epi_ficha_periods', phase='ficha_sequence_unique_migration')
        structured_log('info', 'db.ficha_sequence_after_create_unique_index', table='epi_ficha_periods', phase='ficha_sequence_unique_migration')
        structured_log('info', 'db.ficha_sequence_index_creation_started', table='epi_ficha_periods', phase='ficha_sequence_unique_migration')
        structured_log('info', 'db.step_started', step='create_secondary_index', query_name='create_secondary_index', table='epi_ficha_periods', phase='ficha_sequence_unique_migration')
        try:
            connection.execute(
                'CREATE INDEX IF NOT EXISTS idx_epi_ficha_items_period_sequence '
                'ON epi_ficha_periods (employee_id, period_start, period_end, ficha_sequence DESC)'
            )
        except SchemaMigrationError:
            raise
        except Exception as exc:
            structured_log(
                'critical',
                'db.step_failed',
                step='create_secondary_index',
                query_name='create_secondary_index',
                error=str(exc),
                error_type=type(exc).__name__,
                table='epi_ficha_periods',
                phase='ficha_sequence_unique_migration',
            )
            raise SchemaMigrationError(
                'Falha ao criar índice secundário da migração de ficha_sequence.',
                kind='driver_unexpected',
                context={
                    'step': 'create_secondary_index',
                    'query_name': 'create_secondary_index',
                    'error': str(exc),
                    'error_type': type(exc).__name__,
                    'phase': 'ficha_sequence_unique_migration',
                },
            ) from exc
        structured_log('info', 'db.step_completed', step='create_secondary_index', query_name='create_secondary_index', table='epi_ficha_periods', phase='ficha_sequence_unique_migration')
        structured_log('info', 'db.ficha_sequence_index_created', table='epi_ficha_periods', phase='ficha_sequence_unique_migration')
        connection.commit()
    except Exception as exc:
        if isinstance(exc, SchemaMigrationError):
            raise
        try:
            connection.rollback()
        except Exception:
            pass
        structured_log(
            'critical',
            'db.ficha_periods_unique_migration_failed',
            error=str(exc),
            table='epi_ficha_periods',
            phase='ficha_sequence_unique_migration',
            action='migration_aborted',
        )
        raise SchemaMigrationError(
            f'Falha crítica na migração de unicidade de sequência da ficha: {exc}',
            kind=_classify_db_error(exc),
            context={'table': 'epi_ficha_periods', 'phase': 'ficha_sequence_unique_migration'},
        ) from exc

def ensure_company_columns(connection):
    """Adiciona colunas da tabela companies apenas se nao existirem."""
    migrations = [
        ('legal_name', "TEXT NOT NULL DEFAULT ''"),
        ('plan_name', "TEXT NOT NULL DEFAULT 'Plano padrao'"),
        ('user_limit', 'INTEGER NOT NULL DEFAULT 25'),
        ('license_status', "TEXT NOT NULL DEFAULT 'active'"),
        ('active', 'INTEGER NOT NULL DEFAULT 1'),
        ('commercial_notes', "TEXT NOT NULL DEFAULT ''"),
        ('contract_start', "TEXT NOT NULL DEFAULT ''"),
        ('contract_end', "TEXT NOT NULL DEFAULT ''"),
        ('monthly_value', 'REAL NOT NULL DEFAULT 0'),
        ('addendum_enabled', 'INTEGER NOT NULL DEFAULT 0'),
    ]
    for col, defn in migrations:
        _safe_add_column(connection, 'companies', col, defn)


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
    try:
        company = connection.execute('SELECT id, name, user_limit, active, license_status FROM companies WHERE id = ?', (company_id,)).fetchone()
    except Exception as _e:
        structured_log('warning', 'db.col_skip', error=str(_e))
    if not company:
        raise ValueError('Empresa não encontrada.')
    if not int(company['active']) or company['license_status'] in ('suspended', 'expired'):
        raise ValueError('Empresa sem licença ativa para novos usuários.')
    try:
        contract_end = connection.execute('SELECT contract_end FROM companies WHERE id = ?', (company_id,)).fetchone()['contract_end']
    except Exception as _e:
        structured_log('warning', 'db.col_skip', error=str(_e))
    if contract_end and contract_end < date.today().isoformat():
        raise ValueError('Contrato expirado para novos usuários.')
    placeholders = ','.join(['?'] * len(BILLABLE_ROLES))
    query = f'SELECT COUNT(*) FROM users WHERE company_id = ? AND active = 1 AND role IN ({placeholders})'
    params = [company_id, *BILLABLE_ROLES]
    if ignore_user_id:
        query += ' AND id != ?'
        params.append(ignore_user_id)
    try:
        active_users = connection.execute(query, tuple(params)).fetchone()[0]
    except Exception as _e:
        structured_log('warning', 'db.col_skip', error=str(_e))
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
    try:
        admin_user = connection.execute("SELECT id, username, full_name, password FROM users WHERE username = ? LIMIT 1", (INITIAL_MASTER_ADMIN['username'],)).fetchone()
    except Exception as _e:
        structured_log('warning', 'db.col_skip', error=str(_e))
    if admin_user:
        password_to_store = admin_user['password']
        if not is_bcrypt_hash(password_to_store):
            password_to_store = hash_password(password_to_store)
        try:
            connection.execute(
                "UPDATE users SET password = ?, full_name = ?, role = 'master_admin', company_id = NULL, active = 1 WHERE id = ?",
                (password_to_store, INITIAL_MASTER_ADMIN['full_name'], admin_user['id'])
            )
        except Exception as _e:
            structured_log('warning', 'db.col_skip', error=str(_e))
        set_meta(connection, 'initial_master_admin_bootstrapped', str(admin_user['id']))
        return {'id': admin_user['id'], **INITIAL_MASTER_ADMIN}

    try:
        cursor = connection.execute(
            'INSERT INTO users (username, password, full_name, role, company_id, active) VALUES (?, ?, ?, ?, ?, ?)',
            (INITIAL_MASTER_ADMIN['username'], hash_password(INITIAL_MASTER_ADMIN['password']), INITIAL_MASTER_ADMIN['full_name'], 'master_admin', None, 1)
        )
    except Exception as _e:
        structured_log('warning', 'db.col_skip', error=str(_e))
    set_meta(connection, 'initial_master_admin_bootstrapped', str(cursor.lastrowid))
    return {'id': cursor.lastrowid, **INITIAL_MASTER_ADMIN}


def init_db():
    retries = int(os.environ.get('DB_INIT_RETRIES', '8'))
    retry_delay = float(os.environ.get('DB_INIT_RETRY_DELAY_SECONDS', '2'))
    lock_retries = int(os.environ.get('DB_INIT_LOCK_RETRIES', '15'))
    lock_retry_delay = float(os.environ.get('DB_INIT_LOCK_RETRY_DELAY_SECONDS', '1'))
    advisory_lock_key = int(os.environ.get('DB_INIT_ADVISORY_LOCK_KEY', '83492117'))
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
        run_schema_precheck(connection)
        advisory_lock_acquired = False
        if DB_CONNECTOR_AVAILABLE and DATABASE_URL:
            # Serializa migrrazão de startup entre múltiplos processos para evitar deadlock em ALTER TABLE.
            # Usa try-lock para não travar startup por statement_timeout do banco.
            for lock_attempt in range(1, lock_retries + 1):
                try:
                    lock_row = connection.execute(
                        'SELECT pg_try_advisory_lock(?) AS acquired',
                        (advisory_lock_key,)
                    ).fetchone()
                    lock_acquired = bool((lock_row or {}).get('acquired'))
                except Exception as exc:
                    lock_acquired = False
                    structured_log(
                        'warning',
                        'db.init_lock_attempt_failed',
                        attempt=lock_attempt,
                        retries=lock_retries,
                        error=str(exc)
                    )
                if lock_acquired:
                    advisory_lock_acquired = True
                    break
                if lock_attempt < lock_retries:
                    time.sleep(lock_retry_delay)
            if not advisory_lock_acquired:
                structured_log(
                    'warning',
                    'db.init_lock_not_acquired',
                    retries=lock_retries,
                    lock_key=advisory_lock_key
                )
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
                cpf TEXT NOT NULL DEFAULT '',
                name TEXT NOT NULL,
                email TEXT NOT NULL DEFAULT '',
                whatsapp TEXT NOT NULL DEFAULT '',
                preferred_contact_channel TEXT NOT NULL DEFAULT 'whatsapp',
                sector TEXT NOT NULL,
                role_name TEXT NOT NULL,
                admission_date TEXT NOT NULL,
                schedule_type TEXT NOT NULL,
                tipo_vinculo TEXT NOT NULL DEFAULT 'CLT',
                empresa_origem TEXT NOT NULL DEFAULT '',
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
                active INTEGER NOT NULL DEFAULT 1,
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
        _ensure_fns = [
            ensure_company_columns,
            ensure_company_audit_columns,
            ensure_epi_columns,
            ensure_employee_columns,
            ensure_stock_columns,
            ensure_epi_operational_tables,
            ensure_commercial_settings,
            ensure_commercial_contract_tables,
            ensure_user_columns,
            ensure_delivery_signature_columns,
            ensure_devolution_columns,
            ensure_unit_joint_venture_periods_table,
        ]
        for _fn in _ensure_fns:
            try:
                structured_log('info', 'db.ensure_fn_started', fn=_fn.__name__)
                _fn(connection)
                connection.commit()
                structured_log('info', 'db.ensure_fn_ok', fn=_fn.__name__)
            except SchemaMigrationError:
                try:
                    connection.rollback()
                except Exception:
                    pass
                raise
            except Exception as _e:
                try:
                    connection.rollback()
                except Exception:
                    pass
                kind = _classify_db_error(_e)
                structured_log('error', 'db.ensure_fn_failed', fn=_fn.__name__, error=str(_e), kind=kind)
                raise SchemaMigrationError(
                    f'Falha em migração { _fn.__name__ }: {_e}',
                    kind=kind,
                    context={'fn': _fn.__name__, 'phase': 'ensure_fn'},
                ) from _e
        validate_schema_health(connection)
        migration_runtime = run_pending_migrations(connection)
        structured_log(
            'info' if migration_runtime.get('status') == 'ok' else 'warning',
            'db.migration_runner_finished',
            status=migration_runtime.get('status'),
            applied_count=len(migration_runtime.get('applied') or []),
            failed_migration=migration_runtime.get('failed_migration') or '',
        )
        # Garantir transacao limpa antes dos SELECTs criticos
        try:
            connection.commit()
        except Exception:
            try:
                connection.rollback()
            except Exception:
                pass
        try:
            _companies_count = connection.execute('SELECT COUNT(*) FROM companies').fetchone()[0]
        except Exception as _e:
            structured_log('warning', 'db.select_companies_retry', error=str(_e))
            try:
                connection.rollback()
                _companies_count = connection.execute('SELECT COUNT(*) FROM companies').fetchone()[0]
            except Exception:
                _companies_count = -1
        if _companies_count == 0:
            connection.executemany('INSERT INTO companies (name, legal_name, cnpj, logo_type, plan_name, user_limit, license_status, active, commercial_notes, contract_start, contract_end, monthly_value, addendum_enabled) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', [('DOF Brasil', 'DOF Subsea Brasil Servicos Ltda', '11.222.333/0001-81', '', 'enterprise', 120, 'active', 1, 'Contrato corporativo ativo.', '2026-01-01', '2026-12-31', 0.0, 0), ('Norskan Offshore', 'Norskan Offshore Ltda', '44.555.666/0001-81', '', 'corporate', 80, 'active', 1, 'Operaçao offshore ativa.', '2026-01-01', '2026-12-31', 0.0, 0)])
        companies = {row['name']: row['id'] for row in connection.execute('SELECT id, name FROM companies').fetchall()}
        connection.execute("UPDATE companies SET cnpj = '11.222.333/0001-81', contract_start = COALESCE(NULLIF(contract_start, ''), '2026-01-01'), contract_end = COALESCE(NULLIF(contract_end, ''), '2026-12-31'), plan_name = CASE WHEN plan_name IN ('Plano padrao', 'Plano padrão', 'Enterprise Offshore') THEN 'enterprise' ELSE plan_name END, logo_type = COALESCE(logo_type, ''), addendum_enabled = COALESCE(addendum_enabled, 0) WHERE name = 'DOF Brasil'")
        connection.execute("UPDATE companies SET cnpj = '44.555.666/0001-81', contract_start = COALESCE(NULLIF(contract_start, ''), '2026-01-01'), contract_end = COALESCE(NULLIF(contract_end, ''), '2026-12-31'), plan_name = CASE WHEN plan_name IN ('Plano padrao', 'Plano padrão', 'Fleet Base') THEN 'corporate' ELSE plan_name END, logo_type = COALESCE(logo_type, ''), addendum_enabled = COALESCE(addendum_enabled, 0) WHERE name = 'Norskan Offshore'")
        connection.execute("UPDATE units SET unit_type = 'embarcacao' WHERE unit_type IN ('navio', 'embarcação')")
        migrate_role_hierarchy(connection)
        # Rollback preventivo para limpar qualquer transacao corrompida pelos ensures
        try:
            connection.rollback()
        except Exception:
            pass
        try:
            existing_usernames = {row['username'] for row in connection.execute('SELECT username FROM users').fetchall()}
        except Exception as _e:
            structured_log('warning', 'db.select_users_retry', error=str(_e))
            try:
                connection.rollback()
            except Exception:
                pass
            try:
                existing_usernames = {row['username'] for row in connection.execute('SELECT username FROM users').fetchall()}
            except Exception:
                existing_usernames = set()
        users_to_insert = []
        if 'dof.general' not in existing_usernames:
            users_to_insert.append(('dof.general', hash_password(os.environ.get('SEED_DOF_GENERAL_PW', '')), 'Administrador Geral DOF Brasil', 'general_admin', companies['DOF Brasil']))
        if 'dof.admin' not in existing_usernames:
            users_to_insert.append(('dof.admin', hash_password(os.environ.get('SEED_DOF_ADMIN_PW', '')), 'Administrador DOF Brasil', 'admin', companies['DOF Brasil']))
        if 'dof.user' not in existing_usernames:
            users_to_insert.append(('dof.user', hash_password(os.environ.get('SEED_DOF_PW', '')), 'Usuário DOF Brasil', 'user', companies['DOF Brasil']))
        if 'norskan.general' not in existing_usernames:
            users_to_insert.append(('norskan.general', hash_password(os.environ.get('SEED_NORSKAN_GENERAL_PW', '')), 'Administrador Geral Norskan', 'general_admin', companies['Norskan Offshore']))
        if 'norskan.admin' not in existing_usernames:
            users_to_insert.append(('norskan.admin', hash_password(os.environ.get('SEED_NORSKAN_ADMIN_PW', '')), 'Administrador Norskan', 'admin', companies['Norskan Offshore']))
        if 'norskan.user' not in existing_usernames:
            users_to_insert.append(('norskan.user', hash_password(os.environ.get('SEED_NORSKAN_PW', '')), 'Usuário Norskan Offshore', 'user', companies['Norskan Offshore']))
        if users_to_insert:
            connection.executemany('INSERT INTO users (username, password, full_name, role, company_id) VALUES (?, ?, ?, ?, ?)', users_to_insert)
        bootstrap_admin = ensure_initial_master_admin(connection)
        if connection.execute('SELECT COUNT(*) FROM units').fetchone()[0] == 0:
            connection.executemany('INSERT INTO units (company_id, name, unit_type, city, notes) VALUES (?, ?, ?, ?, ?)', [(companies['DOF Brasil'], 'Base Macae', 'base', 'Macae', 'Base onshore'), (companies['DOF Brasil'], 'Navio Skandi', 'navio', 'Bacia de Campos', 'Navio offshore'), (companies['Norskan Offshore'], 'Base Rio Capital', 'base', 'Rio de Janeiro', 'Base onshore'), (companies['Norskan Offshore'], 'Navio Norskan Alpha', 'navio', 'Bacia de Santos', 'Navio offshore')])
        if connection.execute('SELECT COUNT(*) FROM employees').fetchone()[0] == 0:
            dof_base = connection.execute("SELECT id FROM units WHERE name = 'Base Macae'").fetchone()['id']
            norskan_ship = connection.execute("SELECT id FROM units WHERE name = 'Navio Norskan Alpha'").fetchone()['id']
            connection.executemany('INSERT INTO employees (company_id, unit_id, employee_id_code, cpf, name, email, whatsapp, preferred_contact_channel, sector, role_name, admission_date, schedule_type) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', [(companies['DOF Brasil'], dof_base, '1001', '12345678901', 'Carlos Souza', 'carlos.souza@example.com', '55999990001', 'whatsapp', 'Producao', 'Operador', '2025-01-10', '14x14'), (companies['Norskan Offshore'], norskan_ship, '2001', '12345678902', 'Fernanda Lima', 'fernanda.lima@example.com', '55999990002', 'whatsapp', 'SSMA', 'Tecnica de Seguranca', '2024-11-20', '28x28')])
        if connection.execute('SELECT COUNT(*) FROM epis').fetchone()[0] == 0:
            dof_base = connection.execute("SELECT id FROM units WHERE name = 'Base Macae'").fetchone()['id']
            norskan_ship = connection.execute("SELECT id FROM units WHERE name = 'Navio Norskan Alpha'").fetchone()['id']
            connection.executemany('INSERT INTO epis (company_id, unit_id, name, purchase_code, ca, sector, stock, unit_measure, ca_expiry, epi_validity_date, manufacture_date, validity_days, qr_code_value) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', [(companies['DOF Brasil'], dof_base, 'Capacete Classe B', 'COD-001', '12345', 'Producao', 18, 'unidade', '2026-04-25', '2026-10-25', '2025-10-25', 180, f"EPI-{companies['DOF Brasil']}-{dof_base}-COD-001"), (companies['DOF Brasil'], dof_base, 'Bota de Seguranca', 'COD-002', '12346', 'Producao', 12, 'par', '2026-08-01', '2027-02-01', '2025-08-01', 180, f"EPI-{companies['DOF Brasil']}-{dof_base}-COD-002"), (companies['Norskan Offshore'], norskan_ship, 'Luva Nitrilica', 'COD-101', '67890', 'SSMA', 7, 'par', '2026-03-28', '2026-09-28', '2025-09-28', 60, f"EPI-{companies['Norskan Offshore']}-{norskan_ship}-COD-101")])
        connection.execute("UPDATE epis SET qr_code_value = COALESCE(NULLIF(qr_code_value, ''), 'EPI-' || company_id || '-' || COALESCE(unit_id, 0) || '-' || UPPER(REPLACE(purchase_code, ' ', '-')))")
        seq_rows = connection.execute('SELECT id, company_id FROM epis WHERE epi_master_sequence IS NULL ORDER BY id').fetchall()
        for row in seq_rows:
            seq_value = next_company_qr_sequence(connection, int(row['company_id']))
            connection.execute(
                'UPDATE epis SET epi_master_sequence = ?, qr_code_value = COALESCE(NULLIF(qr_code_value, \'\'), ?) WHERE id = ?',
                (seq_value, build_master_epi_qr(int(row['company_id']), seq_value), int(row['id']))
            )
        backfill_unit_stock_from_epis(connection, datetime.now(UTC).isoformat())
        import_active_joinventures_from_epis(connection)
        # Corrige solicitações de EPI presas em 'em análise' cujos itens já foram
        # recebidos via PO — atualiza retroativamente para 'separado'.
        try:
            connection.execute(
                """
                UPDATE epi_requests SET status = 'separado', last_updated_at = ?
                WHERE status = 'em análise'
                AND id IN (
                    SELECT DISTINCT epi_request_id
                    FROM purchase_request_items
                    WHERE epi_request_id IS NOT NULL
                    AND status IN ('received', 'received_partial', 'checked', 'closed')
                )
                """,
                (datetime.now(UTC).isoformat(),)
            )
        except Exception as _mig_e:
            structured_log('warning', 'db.retroactive_epi_request_status_fix', error=str(_mig_e))
        if advisory_lock_acquired:
            try:
                connection.execute('SELECT pg_advisory_unlock(?)', (advisory_lock_key,))
            except Exception as exc:
                structured_log('warning', 'db.init_lock_release_failed', lock_key=advisory_lock_key, error=str(exc))
        connection.commit()
        return bootstrap_admin


def ensure_company_audit_columns(connection):
    """Adiciona colunas de auditoria apenas se nao existirem."""
    _safe_add_column(connection, 'company_audit_logs', 'details_json', "TEXT NOT NULL DEFAULT '[]'")


def ensure_epi_columns(connection):
    """Adiciona colunas da tabela epis apenas se nao existirem.
    Verifica o catalogo do PostgreSQL antes de qualquer ALTER TABLE,
    eliminando timeouts em producao onde as colunas ja existem.
    """
    _safe_add_column(connection, 'epis', 'unit_id', 'INTEGER')
    _safe_add_column(connection, 'epis', 'qr_code_value', 'TEXT')
    _safe_add_column(connection, 'epis', 'epi_master_sequence', 'INTEGER')
    _safe_add_column(connection, 'epis', 'manufacturer', "TEXT NOT NULL DEFAULT ''")
    _safe_add_column(connection, 'epis', 'supplier_company', "TEXT NOT NULL DEFAULT ''")
    _safe_add_column(connection, 'epis', 'validity_years', 'INTEGER NOT NULL DEFAULT 0')
    _safe_add_column(connection, 'epis', 'validity_months', 'INTEGER NOT NULL DEFAULT 0')
    _safe_add_column(connection, 'epis', 'manufacturer_validity_months', 'INTEGER NOT NULL DEFAULT 0')
    _safe_add_column(connection, 'epis', 'joinventures_json', "TEXT NOT NULL DEFAULT '[]'")
    _safe_add_column(connection, 'epis', 'active_joinventure', 'TEXT')
    _safe_add_column(connection, 'epis', 'model_reference', "TEXT NOT NULL DEFAULT ''")
    _safe_add_column(connection, 'epis', 'manufacturer_recommendations', "TEXT NOT NULL DEFAULT ''")
    _safe_add_column(connection, 'epis', 'epi_photo_data', 'TEXT')
    _safe_add_column(connection, 'epis', 'active', 'INTEGER NOT NULL DEFAULT 1')
    _safe_add_column(connection, 'epis', 'epi_section', "TEXT NOT NULL DEFAULT ''")
    _safe_add_column(connection, 'epis', 'glove_size', 'TEXT')
    _safe_add_column(connection, 'epis', 'size', 'TEXT')
    _safe_add_column(connection, 'epis', 'uniform_size', 'TEXT')
    _safe_add_column(connection, 'epis', 'scope_type', "TEXT NOT NULL DEFAULT 'GLOBAL'")
    _safe_add_column(connection, 'epis', 'is_joint_venture', 'INTEGER NOT NULL DEFAULT 0')
    _safe_add_column(connection, 'epis', 'default_replacement_days', 'INTEGER')
    _safe_add_column(connection, 'epis', 'evaluation_status', "TEXT NOT NULL DEFAULT 'normal'")
    try:
        connection.execute(
            """
            UPDATE epis
            SET
                scope_type = CASE
                    WHEN COALESCE(TRIM(active_joinventure), '') <> '' THEN 'JOINT_VENTURE'
                    WHEN unit_id IS NULL THEN 'GLOBAL'
                    ELSE 'UNIT'
                END,
                is_joint_venture = CASE
                    WHEN COALESCE(TRIM(active_joinventure), '') <> '' THEN 1
                    ELSE 0
                END
            WHERE scope_type = 'GLOBAL' AND unit_id IS NOT NULL
            """
        )
    except Exception as _e:
        structured_log('warning', 'db.ensure_epi_update_skip', error=str(_e))
        try:
            connection.rollback()
        except Exception:
            pass


def ensure_employee_columns(connection):
    """Adiciona colunas da tabela employees apenas se nao existirem."""
    _safe_add_column(connection, 'employees', 'cpf', "TEXT NOT NULL DEFAULT ''")
    _safe_add_column(connection, 'employees', 'email', "TEXT NOT NULL DEFAULT ''")
    _safe_add_column(connection, 'employees', 'whatsapp', "TEXT NOT NULL DEFAULT ''")
    _safe_add_column(connection, 'employees', 'preferred_contact_channel', "TEXT NOT NULL DEFAULT 'whatsapp'")
    _safe_add_column(connection, 'employees', 'tipo_vinculo', "TEXT NOT NULL DEFAULT 'CLT'")
    _safe_add_column(connection, 'employees', 'empresa_origem', "TEXT NOT NULL DEFAULT ''")


def generate_epi_qr_code(payload):
    purchase_code = str(payload.get('purchase_code', '')).strip().upper().replace(' ', '-')
    return f"EPI-{payload.get('company_id')}-{payload.get('unit_id')}-{purchase_code}"


def next_company_qr_sequence(connection, company_id):
    # Em Postgres, faz incremento atômico para evitar colisões em cenários concorrentes.
    if DB_CONNECTOR_AVAILABLE and DATABASE_URL:
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


def parse_stock_qr_lookup_value(raw_value):
    text = str(raw_value or '').strip()
    if not text:
        return {'raw': '', 'stock_item_id': None, 'qr_code_value': None, 'format': 'empty'}
    normalized = unicodedata.normalize('NFKC', text)
    if normalized.startswith('{') and normalized.endswith('}'):
        try:
            payload = json.loads(normalized)
        except (TypeError, ValueError):
            payload = None
        payload_type = str((payload or {}).get('type') or '').strip().lower()
        if payload_type in ('stock_item', 'epi_stock_item', 'stockitem'):
            parsed_id = parse_int_flexible((payload or {}).get('id'), 0) or 0
            parsed_code = str((payload or {}).get('code') or (payload or {}).get('qr_code_value') or '').strip()
            return {
                'raw': text,
                'stock_item_id': int(parsed_id) if int(parsed_id) > 0 else None,
                'qr_code_value': parsed_code if parsed_code else None,
                'format': 'json'
            }
    simple_match = re.match(r'^EPIITEM\s*:\s*(\d+)$', normalized, flags=re.IGNORECASE)
    if simple_match:
        return {
            'raw': text,
            'stock_item_id': int(simple_match.group(1)),
            'qr_code_value': None,
            'format': 'simple'
        }
    stock_label_match = re.match(r'^EPI-ITEM-(\d{4})-(\d{4})-(\d{8})$', normalized, flags=re.IGNORECASE)
    if stock_label_match:
        return {
            'raw': text,
            'stock_item_id': None,
            'qr_code_value': normalized,
            'format': 'stock-label'
        }
    return {
        'raw': text,
        'stock_item_id': None,
        'qr_code_value': normalized,
        'format': 'raw'
    }


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


def _auto_add_received_items_to_stock(connection, pr_id, received_item_flags, actor_id, actor_name, now):
    """
    Adds received EPI items to stock automatically after conferência.
    received_item_flags: list of {id: int, received: bool} — if empty, uses items with status 'received'.
    Returns count of individual units added to stock.
    """
    if received_item_flags:
        received_ids = {int(f['id']) for f in received_item_flags if f.get('received')}
    else:
        rows = connection.execute(
            "SELECT id FROM purchase_request_items WHERE purchase_request_id = ? AND status = 'received'",
            (pr_id,)
        ).fetchall()
        received_ids = {int(r['id']) for r in rows}
    if not received_ids:
        return 0
    placeholders = ','.join('?' for _ in received_ids)
    pr_items = [row_to_dict(r) for r in connection.execute(
        f'SELECT * FROM purchase_request_items WHERE purchase_request_id = ? AND id IN ({placeholders})',
        (pr_id, *received_ids)
    ).fetchall()]
    total_units = 0
    ensure_stock_movement_size_columns(connection)
    for item in pr_items:
        epi_id = int(item['epi_id'])
        unit_id = int(item['unit_id'])
        company_id = int(item['company_id'])
        pri_id = int(item['id'])
        po_item = connection.execute(
            'SELECT * FROM purchase_order_items WHERE purchase_request_item_id = ? ORDER BY id DESC LIMIT 1',
            (pri_id,)
        ).fetchone()
        if po_item:
            quantity = int(po_item.get('quantity_received') or 0)
        else:
            quantity = int(item.get('quantity_requested') or 0)
        if quantity <= 0:
            continue
        glove_size = str(item.get('glove_size') or 'N/A')
        size = str(item.get('size') or 'N/A')
        uniform_size = str(item.get('uniform_size') or 'N/A')
        stock_row = get_unit_stock(connection, company_id, unit_id, epi_id)
        previous_stock = int((stock_row or {}).get('quantity') or 0)
        new_stock = previous_stock + quantity
        movement_cursor = connection.execute(
            'INSERT INTO stock_movements ('
            'company_id, unit_id, epi_id, movement_type, quantity, previous_stock, new_stock, '
            'source_type, source_id, notes, actor_user_id, actor_name, created_at, glove_size, size, uniform_size'
            ') VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (
                company_id, unit_id, epi_id, 'in', quantity, previous_stock, new_stock,
                'purchase_request', pri_id,
                f'Entrada automática — Conferência Requisição #{pr_id}',
                actor_id, actor_name, now, glove_size, size, uniform_size
            )
        )
        movement_id = int(movement_cursor.lastrowid)
        upsert_unit_stock(connection, company_id, unit_id, epi_id, new_stock)
        for _ in range(quantity):
            seq_value = next_company_qr_sequence(connection, company_id)
            qr_value = build_stock_item_qr(company_id, unit_id, seq_value)
            connection.execute(
                'INSERT INTO epi_stock_items ('
                'company_id, unit_id, epi_id, glove_size, size, uniform_size, qr_sequence, qr_code_value, status, '
                'stock_movement_id, lot_code, manufacture_date, label_measure, label_printer_name, label_print_format, '
                'generated_by_user_id, created_at, updated_at'
                ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'in_stock', ?, '', '', 'unidade', '', '', ?, ?, ?)",
                (
                    company_id, unit_id, epi_id, glove_size, size, uniform_size,
                    seq_value, qr_value, movement_id,
                    actor_id, now, now
                )
            )
        total_units += quantity
        epi_req_id = item.get('epi_request_id')
        if epi_req_id:
            connection.execute(
                "UPDATE epi_requests SET status = 'separado', last_updated_at = ? "
                "WHERE id = ? AND status NOT IN ('entregue', 'cancelado', 'rejeitado')",
                (now, int(epi_req_id))
            )
    return total_units


def backfill_unit_stock_from_epis(connection, timestamp_iso):
    """Cria saldo inicial por unidade apenas para EPIs com unidade física definida."""
    connection.execute(
        '''
        INSERT INTO unit_epi_stock (company_id, unit_id, epi_id, quantity, updated_at)
        SELECT epis.company_id, epis.unit_id, epis.id, epis.stock, ?
        FROM epis
        WHERE epis.unit_id IS NOT NULL
          AND NOT EXISTS (
              SELECT 1 FROM unit_epi_stock s
              WHERE s.company_id = epis.company_id AND s.unit_id = epis.unit_id AND s.epi_id = epis.id
          )
        ''',
        (timestamp_iso,)
    )


def sync_epi_scope_stock_unit(connection, company_id, epi_id, previous_unit_id, new_unit_id):
    """Mantém consistência de estoque por unidade quando o escopo UNIT é alterado.

    Regras:
    - Se o escopo não mudou, não faz nada.
    - Se sair de uma unidade específica para GLOBAL/JV, mantém o estoque físico da unidade atual.
    - Se mudar de uma unidade específica para outra, transfere o saldo agregado para a nova unidade.
    """
    old_unit = int(previous_unit_id) if previous_unit_id else 0
    next_unit = int(new_unit_id) if new_unit_id else 0
    if old_unit == next_unit:
        return
    if not old_unit or not next_unit:
        return
    previous_stock = get_unit_stock(connection, int(company_id), old_unit, int(epi_id))
    if not previous_stock:
        return
    quantity = int(previous_stock.get('quantity') or 0)
    connection.execute('DELETE FROM unit_epi_stock WHERE id = ?', (int(previous_stock['id']),))
    target_stock = get_unit_stock(connection, int(company_id), next_unit, int(epi_id))
    if target_stock:
        upsert_unit_stock(
            connection,
            int(company_id),
            next_unit,
            int(epi_id),
            int(target_stock.get('quantity') or 0) + quantity
        )
    else:
        upsert_unit_stock(connection, int(company_id), next_unit, int(epi_id), quantity)


def resolve_delivery_period(delivery_date, schedule_type):
    start = datetime.strptime(str(delivery_date), '%Y-%m-%d').date()
    days = period_days_from_schedule(schedule_type)
    end = start + timedelta(days=days - 1)
    return start.isoformat(), end.isoformat()


def ensure_ficha_for_delivery(connection, delivery_row):
    delivery_date = str(delivery_row['delivery_date'])
    schedule_type = str(delivery_row.get('schedule_type') or '')
    unit_id = int(delivery_row['unit_id'])
    now = datetime.now(UTC).isoformat()
    ficha = None
    try:
        ficha = connection.execute(
            '''
            SELECT id, period_start, period_end, status
            FROM epi_ficha_periods
            WHERE employee_id = ? AND unit_id = ? AND schedule_type = ? AND status = 'open'
            ORDER BY id DESC
            LIMIT 1
            ''',
            (delivery_row['employee_id'], unit_id, schedule_type)
        ).fetchone()
    except Exception as _e:
        structured_log('warning', 'db.col_skip', error=str(_e))
    if ficha:
        ficha_id = int(ficha['id'])
        current_start = str(ficha.get('period_start') or delivery_date)
        current_end = str(ficha.get('period_end') or delivery_date)
        next_start = min(current_start, delivery_date)
        next_end = max(current_end, delivery_date)
        try:
            connection.execute(
                'UPDATE epi_ficha_periods SET period_start = ?, period_end = ?, status = ?, updated_at = ? WHERE id = ?',
                (next_start, next_end, 'open', now, ficha_id)
            )
        except Exception as _e:
            structured_log('warning', 'db.col_skip', error=str(_e))
    else:
        period_start, period_end = resolve_delivery_period(delivery_date, schedule_type)
        sequence_row = connection.execute(
            'SELECT COALESCE(MAX(ficha_sequence), 0) AS max_sequence FROM epi_ficha_periods WHERE employee_id = ? AND period_start = ? AND period_end = ?',
            (delivery_row['employee_id'], period_start, period_end),
        ).fetchone()
        next_sequence = int((row_to_dict(sequence_row) if sequence_row else {}).get('max_sequence') or 0) + 1
        cursor = None
        try:
            cursor = connection.execute(
                '''
                INSERT INTO epi_ficha_periods (
                    company_id, employee_id, unit_id, schedule_type, period_start, period_end, ficha_sequence,
                    status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 'open', ?, ?)
                ''',
                (
                    delivery_row['company_id'],
                    delivery_row['employee_id'],
                    unit_id,
                    schedule_type,
                    period_start,
                    period_end,
                    next_sequence,
                    now,
                    now
                )
            )
        except Exception as _e:
            structured_log('warning', 'db.col_skip', error=str(_e))
            raise
        if not cursor:
            raise ValueError('Falha ao criar período da ficha para entrega.')
        ficha_id = int(cursor.lastrowid)
    try:
        connection.execute(
            '''
            INSERT INTO epi_ficha_items (
                ficha_period_id, delivery_id, company_id, employee_id, unit_id, epi_id, quantity,
                item_signature_name, item_signature_data, item_signature_ip, item_signature_at, item_signature_comment, signed_mode,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                str(delivery_row.get('signature_name') or ''),
                str(delivery_row.get('signature_data') or ''),
                str(delivery_row.get('signature_ip') or ''),
                str(delivery_row.get('signature_at') or ''),
                str(delivery_row.get('signature_comment') or ''),
                'delivery' if str(delivery_row.get('signature_data') or '').strip() else '',
                now,
                now
            )
        )
    except Exception as _e:
        structured_log('warning', 'db.col_skip', error=str(_e))
    return ficha_id


def ensure_ficha_for_devolution(connection, devolution_row):
    returned_date = str(devolution_row['returned_date'])
    now = datetime.now(UTC).isoformat()
    employee_id = int(devolution_row['employee_id'])
    company_id = int(devolution_row['company_id'])
    unit_id = int(devolution_row['unit_id'])
    schedule_type = str(devolution_row.get('schedule_type') or '')
    exact_period = connection.execute(
        '''
        SELECT id, period_start, period_end, status
        FROM epi_ficha_periods
        WHERE employee_id = ?
          AND period_start <= ?
          AND period_end >= ?
        ORDER BY CASE WHEN status = 'open' THEN 0 ELSE 1 END, id DESC
        LIMIT 1
        ''',
        (employee_id, returned_date, returned_date),
    ).fetchone()
    if exact_period:
        ficha_id = int(exact_period['id'])
    else:
        open_period = connection.execute(
            '''
            SELECT id, period_start, period_end, status
            FROM epi_ficha_periods
            WHERE employee_id = ? AND status <> 'closed'
            ORDER BY id DESC
            LIMIT 1
            ''',
            (employee_id,),
        ).fetchone()
        if open_period:
            ficha_id = int(open_period['id'])
            next_start = min(str(open_period.get('period_start') or returned_date), returned_date)
            next_end = max(str(open_period.get('period_end') or returned_date), returned_date)
            next_status = 'open' if str(open_period.get('status') or '').lower() in {'open', 'signed'} else str(open_period.get('status') or 'open')
            connection.execute(
                'UPDATE epi_ficha_periods SET period_start = ?, period_end = ?, status = ?, updated_at = ? WHERE id = ?',
                (next_start, next_end, next_status, now, ficha_id),
            )
        else:
            _dev_seq_row = connection.execute(
                'SELECT COALESCE(MAX(ficha_sequence), 0) AS max_sequence FROM epi_ficha_periods WHERE employee_id = ? AND period_start = ? AND period_end = ?',
                (employee_id, returned_date, returned_date),
            ).fetchone()
            _dev_next_sequence = int((row_to_dict(_dev_seq_row) if _dev_seq_row else {}).get('max_sequence') or 0) + 1
            cursor = connection.execute(
                '''
                INSERT INTO epi_ficha_periods (
                    company_id, employee_id, unit_id, schedule_type, period_start, period_end, ficha_sequence,
                    status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 'open', ?, ?)
                ''',
                (
                    company_id,
                    employee_id,
                    unit_id,
                    schedule_type,
                    returned_date,
                    returned_date,
                    _dev_next_sequence,
                    now,
                    now,
                ),
            )
            ficha_id = int(cursor.lastrowid)
            delivery_row = connection.execute(
                (
                    'SELECT d.id, d.company_id, d.employee_id, d.unit_id, d.epi_id, d.quantity '
                    'FROM deliveries d '
                    'JOIN epi_devolutions dev ON dev.delivery_id = d.id '
                    'WHERE dev.id = ?'
                ),
                (int(devolution_row['id']),),
            ).fetchone()
            if delivery_row and _table_exists(connection, 'epi_ficha_items'):
                delivery_data = row_to_dict(delivery_row)
                connection.execute(
                    '''
                    INSERT INTO epi_ficha_items (
                        ficha_period_id, delivery_id, company_id, employee_id, unit_id, epi_id, quantity,
                        item_signature_name, item_signature_data, item_signature_ip, item_signature_at, item_signature_comment, signed_mode,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, '', '', '', '', '', '', ?, ?)
                    ON CONFLICT (delivery_id) DO NOTHING
                    ''',
                    (
                        ficha_id,
                        int(delivery_data['id']),
                        int(delivery_data['company_id']),
                        int(delivery_data['employee_id']),
                        int(delivery_data['unit_id']),
                        int(delivery_data['epi_id']),
                        int(delivery_data.get('quantity') or 0),
                        now,
                        now,
                    ),
                )
    connection.execute(
        'UPDATE epi_devolutions SET ficha_period_id = ? WHERE id = ?',
        (ficha_id, int(devolution_row['id'])),
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
        'commercial_notes': 'Observrazão',
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


def register_ficha_epi_audit(connection, *, actor, employee, action, ip_address='', user_agent='', accessed_at=None):
    connection.execute(
        (
            'INSERT INTO ficha_epi_audit_log '
            '(actor_user_id, actor_name, actor_role, employee_id, employee_name, unit_id, company_id, '
            'action, ip_address, user_agent, accessed_at) '
            'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'
        ),
        (
            int(actor.get('id') or 0),
            str(actor.get('full_name') or actor.get('username') or ''),
            str(actor.get('role') or ''),
            int(employee.get('id') or 0),
            str(employee.get('name') or ''),
            int(employee.get('unit_id') or 0),
            int(employee.get('company_id') or 0),
            str(action or '').strip().lower(),
            str(ip_address or ''),
            str(user_agent or ''),
            str(accessed_at or datetime.now(UTC).isoformat()),
        ),
    )


def fetch_ficha_epi_audit_logs(connection, actor, filters=None):
    filters = filters or {}
    clauses = []
    params = []
    if actor.get('role') != 'master_admin':
        clauses.append('l.company_id = ?')
        params.append(int(actor['company_id']))
    scope_unit_id = actor_operational_unit_id(connection, actor)
    if scope_unit_id:
        clauses.append('l.unit_id = ?')
        params.append(int(scope_unit_id))
    if filters.get('employee_id'):
        clauses.append('l.employee_id = ?')
        params.append(int(filters['employee_id']))
    if filters.get('actor_user_id'):
        clauses.append('l.actor_user_id = ?')
        params.append(int(filters['actor_user_id']))
    if filters.get('action'):
        clauses.append('l.action = ?')
        params.append(str(filters['action']).strip().lower())
    if filters.get('date_from'):
        clauses.append('l.accessed_at >= ?')
        params.append(f"{str(filters['date_from']).strip()}T00:00:00")
    if filters.get('date_to'):
        clauses.append('l.accessed_at <= ?')
        params.append(f"{str(filters['date_to']).strip()}T23:59:59")
    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ''
    rows = connection.execute(
        (
            'SELECT l.*, units.name AS unit_name '
            'FROM ficha_epi_audit_log l '
            'LEFT JOIN units ON units.id = l.unit_id '
            f'{where_sql} '
            'ORDER BY l.accessed_at DESC, l.id DESC LIMIT 1000'
        ),
        tuple(params),
    ).fetchall()
    return [row_to_dict(item) for item in rows]


def build_ficha_archive_filters(raw_filters):
    raw_filters = raw_filters or {}

    def parse_optional_int(key):
        value = str(raw_filters.get(key, '') or '').strip()
        if not value:
            return None
        try:
            return int(value)
        except ValueError as exc:
            raise ValueError(f'Filtro inválido: {key} deve ser numérico.') from exc

    def parse_optional_date(key):
        value = str(raw_filters.get(key, '') or '').strip()
        if not value:
            return ''
        try:
            datetime.strptime(value, '%Y-%m-%d')
        except ValueError as exc:
            raise ValueError(f'Filtro inválido: {key} deve estar no formato YYYY-MM-DD.') from exc
        return value

    return {
        'company_id': parse_optional_int('company_id'),
        'unit_id': parse_optional_int('unit_id'),
        'employee_id': parse_optional_int('employee_id'),
        'status': str(raw_filters.get('status', '') or '').strip().lower(),
        'sector': str(raw_filters.get('sector', '') or '').strip(),
        'date_from': parse_optional_date('date_from'),
        'date_to': parse_optional_date('date_to'),
        'page': max(1, int(str(raw_filters.get('page', '1') or '1'))),
        'page_size': min(200, max(1, int(str(raw_filters.get('page_size', '50') or '50')))),
    }


def fetch_ficha_archive_snapshots(connection, actor, raw_filters=None):
    filters = build_ficha_archive_filters(raw_filters)
    policy = get_ficha_retention_policy(connection, actor.get('company_id'))
    apply_snapshot_retention(connection, actor.get('company_id') if actor.get('role') != 'master_admin' else None, policy)
    clauses = []
    params = []

    if actor.get('role') != 'master_admin':
        clauses.append('s.company_id = ?')
        params.append(int(actor['company_id']))

    scope_unit_id = actor_operational_unit_id(connection, actor)
    if scope_unit_id:
        clauses.append('s.unit_id = ?')
        params.append(int(scope_unit_id))

    if filters['company_id']:
        ensure_company_access(actor, filters['company_id'])
        clauses.append('s.company_id = ?')
        params.append(filters['company_id'])
    if filters['unit_id']:
        unit = get_unit_by_id(connection, filters['unit_id'])
        ensure_resource_company(actor, unit, 'Unidade')
        if scope_unit_id and int(filters['unit_id']) != int(scope_unit_id):
            raise PermissionError('Operação permitida somente para sua unidade operacional.')
        clauses.append('s.unit_id = ?')
        params.append(filters['unit_id'])
    if filters['employee_id']:
        employee = get_employee_by_id(connection, filters['employee_id'])
        ensure_resource_company(actor, employee, 'Colaborador')
        if scope_unit_id:
            ensure_actor_employee_scope(connection, actor, employee)
        clauses.append('s.employee_id = ?')
        params.append(filters['employee_id'])
    if filters['sector']:
        clauses.append('employees.sector = ?')
        params.append(filters['sector'])
    if filters['status'] in {'archived', 'expired', 'purged'}:
        clauses.append('s.status = ?')
        params.append(filters['status'])
    if filters['date_from']:
        clauses.append('DATE(s.generated_at) >= DATE(?)')
        params.append(filters['date_from'])
    if filters['date_to']:
        clauses.append('DATE(s.generated_at) <= DATE(?)')
        params.append(filters['date_to'])

    where_clause = f"WHERE {' AND '.join(clauses)}" if clauses else ''
    offset = (filters['page'] - 1) * filters['page_size']
    total_row = connection.execute(
        (
            'SELECT COUNT(*) AS total '
            'FROM ficha_epi_snapshots s '
            'JOIN employees ON employees.id = s.employee_id '
            f'{where_clause}'
        ),
        tuple(params),
    ).fetchone()
    rows = connection.execute(
        (
            'SELECT s.id, s.ficha_period_id, s.company_id, s.unit_id, s.employee_id, s.generated_by_user_id, s.generated_at, s.expires_at, s.status, '
            's.retention_years, s.html_sha256, s.payload_sha256, '
            'employees.name AS employee_name, employees.employee_id_code, employees.sector, employees.role_name, '
            'units.name AS unit_name, companies.name AS company_name '
            'FROM ficha_epi_snapshots s '
            'JOIN employees ON employees.id = s.employee_id '
            'JOIN units ON units.id = s.unit_id '
            'JOIN companies ON companies.id = s.company_id '
            f'{where_clause} '
            'ORDER BY s.generated_at DESC, s.id DESC '
            'LIMIT ? OFFSET ?'
        ),
        tuple([*params, filters['page_size'], offset]),
    ).fetchall()
    items = []
    now_iso = datetime.now(UTC).isoformat()
    for row in rows:
        item = row_to_dict(row)
        item['status'] = _snapshot_status(item, now_iso)
        items.append(item)
    return {
        'items': items,
        'page': filters['page'],
        'page_size': filters['page_size'],
        'total': int(total_row['total'] if total_row else 0),
        'retention_policy': policy,
    }


def get_ficha_archive_snapshot_by_id(connection, actor, snapshot_id):
    row = connection.execute(
        (
            'SELECT s.*, employees.name AS employee_name, employees.employee_id_code, employees.sector, employees.role_name, '
            'units.name AS unit_name, companies.name AS company_name '
            'FROM ficha_epi_snapshots s '
            'JOIN employees ON employees.id = s.employee_id '
            'JOIN units ON units.id = s.unit_id '
            'JOIN companies ON companies.id = s.company_id '
            'WHERE s.id = ?'
        ),
        (int(snapshot_id),),
    ).fetchone()
    if not row:
        raise ValueError('Snapshot arquivado não encontrado.')
    snapshot = row_to_dict(row)
    ensure_company_access(actor, snapshot.get('company_id'))
    scope_unit_id = actor_operational_unit_id(connection, actor)
    if scope_unit_id and int(snapshot.get('unit_id') or 0) != int(scope_unit_id):
        raise PermissionError('Operação permitida somente para sua unidade operacional.')
    snapshot['status'] = _snapshot_status(snapshot, datetime.now(UTC).isoformat())
    return snapshot


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
    contract = get_or_create_commercial_contract(connection, actor, company_id)
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
    add_line(f"Numero do contrato: {contract.get('contract_number') or '-'}", size=11, x=52, gap=16)
    add_line(f"Data de emissao: {contract.get('issue_date') or today.strftime('%Y-%m-%d')}", size=11, x=52, gap=20)
    add_line('Empresa contratante', size=14, bold=True, x=52, gap=20)
    add_line(contract.get('contractor_name') or company['name'], size=12, bold=True, x=52, gap=18)
    add_line(f"Razao social: {contract.get('contractor_legal_name') or company.get('legal_name') or '-'}")
    add_line(f"CNPJ: {contract.get('contractor_cnpj') or company.get('cnpj') or '-'}")
    add_line(f"Endereco: {contract.get('contractor_address') or '-'}")
    add_line(f"Representante: {contract.get('contractor_representative') or '-'}")
    add_line(f"Cargo: {contract.get('contractor_representative_role') or '-'}")
    add_line(f"E-mail: {contract.get('contractor_email') or '-'}")
    add_line(f"Telefone: {contract.get('contractor_phone') or '-'}")
    add_line(f"Testemunha 1: {contract.get('contractor_witness_1') or '-'}")
    add_line(f"Testemunha 2: {contract.get('contractor_witness_2') or '-'}")
    add_line('Empresa contratada', size=14, bold=True, x=52, gap=20)
    add_line(contract.get('provider_name') or brand.get('display_name') or 'Sua Empresa', size=12, bold=True, x=52, gap=18)
    add_line(f"Razao social: {contract.get('provider_legal_name') or brand.get('legal_name') or '-'}")
    add_line(f"CNPJ: {contract.get('provider_cnpj') or brand.get('cnpj') or '-'}")
    add_line(f"Endereco: {contract.get('provider_address') or '-'}")
    add_line(f"Representante: {contract.get('provider_representative') or '-'}")
    add_line(f"Cargo: {contract.get('provider_representative_role') or '-'}")
    add_line(f"E-mail: {contract.get('provider_email') or '-'}")
    add_line(f"Telefone: {contract.get('provider_phone') or '-'}")
    add_line(f"Testemunhas: {contract.get('provider_witnesses') or '-'}")
    add_line('Dados comerciais', size=14, bold=True, x=52, gap=20)
    add_line(f"Plano contratado: {company.get('plan_name') or '-'}")
    add_line(f"Usuarios ativos: {company.get('user_count') or 0}")
    add_line(f"Limite de usuarios ativos: {company.get('user_limit') or 0}")
    add_line(f"Valor unitario: {unit_price}")
    add_line(f"Valor mensal atual: {monthly_value}")
    add_line(f"Valor projetado pelo limite contratado: {projected_value}")
    add_line(f"Status da licenca: {company_license_label(company.get('license_status'))}")
    add_line(f"Status da empresa: {'Ativa' if int(company.get('active') or 0) == 1 else 'Inativa'}")
    add_line(f"Aditivo contratual: {'Sim' if int(company.get('addendum_enabled') or 0) == 1 else 'Nao'}")
    add_line(f"Inicio do contrato: {contract.get('start_date') or company.get('contract_start') or '-'}")
    add_line(f"Fim do contrato: {contract.get('end_date') or company.get('contract_end') or '-'}")
    add_line('Observacoes comerciais', size=14, bold=True, x=52, gap=20)
    notes = contract.get('notes') or company.get('commercial_notes') or 'Sem observacoes comerciais registradas.'
    for wrapped in textwrap.wrap(notes, width=82):
        add_line(wrapped, size=11, x=52, gap=16)
    add_line('Clausulas editaveis do contrato', size=14, bold=True, x=52, gap=20)
    clauses_text = str(contract.get('clauses_text') or '').strip() or DEFAULT_SAAS_CONTRACT_CLAUSES
    clauses = [line.strip() for line in clauses_text.splitlines() if line.strip()]
    for clause in clauses:
        for wrapped in textwrap.wrap(clause, width=82):
            add_line(wrapped, size=11, x=52, gap=16)
    add_line('Assinatura digital', size=14, bold=True, x=52, gap=20)
    add_line(f"Nome: {contract.get('signed_name') or '-'}")
    add_line(f"Hash/codigo: {contract.get('signed_signature') or '-'}")
    add_line(f"Data assinatura: {contract.get('signed_at') or '-'}")
    add_line('Envio por e-mail', size=14, bold=True, x=52, gap=20)
    add_line(f"Destinatario: {contract.get('last_email_to') or '-'}")
    add_line(f"Assunto: {contract.get('last_email_subject') or '-'}")
    email_body = str(contract.get('last_email_body') or '-')
    for wrapped in textwrap.wrap(email_body, width=82):
        add_line(wrapped, size=11, x=52, gap=16)
    add_line('Assinaturas', size=14, bold=True, x=52, gap=22)
    add_line(f"Contratada: {contract.get('provider_name') or brand.get('display_name') or 'Sua Empresa'}", size=11, x=52, gap=40)
    add_line(f"Contratante: {contract.get('contractor_name') or company['name']}", size=11, x=52, gap=40)
    pages.append(page_lines)
    return build_pdf_document(pages, logo_image)


def get_or_create_commercial_contract(connection, actor, company_id):
    ensure_company_access(actor, company_id)
    company_row = connection.execute('SELECT * FROM companies WHERE id = ?', (int(company_id),)).fetchone()
    if not company_row:
        raise ValueError('Empresa nao encontrada.')
    company = row_to_dict(company_row)
    settings = get_commercial_settings(connection)
    brand = get_platform_brand(connection)
    row = connection.execute('SELECT * FROM commercial_contracts WHERE company_id = ?', (int(company_id),)).fetchone()
    now = datetime.now(UTC).isoformat()
    if not row:
        payload = _default_contract_payload(company, settings, brand)
        connection.execute(
            '''
            INSERT INTO commercial_contracts (
                company_id, contract_number, issue_date, start_date, end_date, status,
                contractor_name, contractor_legal_name, contractor_trade_name, contractor_cnpj, contractor_address,
                contractor_representative, contractor_representative_role, contractor_email, contractor_phone,
                contractor_witness_1, contractor_witness_2,
                provider_name, provider_legal_name, provider_cnpj, provider_address, provider_representative,
                provider_representative_role, provider_email, provider_phone, provider_witnesses,
                clauses_text, notes, generated_pdf_base64, signed_pdf_base64, signed_file_name, signed_file_mime,
                signed_at, archived_at, retention_until, last_email_to, last_email_subject, last_email_body,
                last_email_sent_at, signature_name, signature_data, signature_at, addendum_history_json,
                created_at, updated_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            ''',
            (
                payload['company_id'], payload['contract_number'], payload['issue_date'], payload['start_date'], payload['end_date'], payload['status'],
                payload['contractor_name'], payload['contractor_legal_name'], payload['contractor_trade_name'], payload['contractor_cnpj'], payload['contractor_address'],
                payload['contractor_representative'], payload['contractor_representative_role'], payload['contractor_email'], payload['contractor_phone'],
                payload['contractor_witness_1'], payload['contractor_witness_2'],
                payload['provider_name'], payload['provider_legal_name'], payload['provider_cnpj'], payload['provider_address'], payload['provider_representative'],
                payload['provider_representative_role'], payload['provider_email'], payload['provider_phone'], payload['provider_witnesses'],
                payload['clauses_text'], payload['notes'], payload['generated_pdf_base64'], payload['signed_pdf_base64'], payload['signed_file_name'], payload['signed_file_mime'],
                payload['signed_at'], payload['archived_at'], payload['retention_until'], payload['last_email_to'], payload['last_email_subject'], payload['last_email_body'],
                payload['last_email_sent_at'], payload['signature_name'], payload['signature_data'], payload['signature_at'], payload['addendum_history_json'],
                now, now
            )
        )
        row = connection.execute('SELECT * FROM commercial_contracts WHERE company_id = ?', (int(company_id),)).fetchone()
    contract = row_to_dict(row)
    contract['metrics'] = compute_company_contract_metrics(company, settings)
    contract['company'] = company
    contract['provider_brand'] = brand
    events = connection.execute(
        '''
        SELECT id, event_type, details_json, actor_name, created_at
        FROM commercial_contract_events
        WHERE company_id = ?
        ORDER BY id DESC
        LIMIT 20
        ''',
        (int(company_id),)
    ).fetchall()
    contract['events'] = [row_to_dict(item) for item in events]
    return contract


def register_commercial_contract_event(connection, actor, contract, event_type, details=None):
    now = datetime.now(UTC).isoformat()
    connection.execute(
        '''
        INSERT INTO commercial_contract_events (
            company_id, contract_id, actor_user_id, actor_name, event_type, details_json, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        ''',
        (
            int(contract['company_id']),
            int(contract['id']),
            int(actor['id']),
            str(actor.get('full_name') or ''),
            str(event_type or '').strip(),
            json.dumps(details or {}, ensure_ascii=False),
            now
        )
    )


def save_commercial_contract(connection, actor, payload):
    company_id = int(payload.get('company_id') or 0)
    contract = get_or_create_commercial_contract(connection, actor, company_id)
    status = str(payload.get('status') or contract.get('status') or 'draft').strip().lower()
    if status not in COMMERCIAL_CONTRACT_STATUS:
        raise ValueError('Status de contrato inválido.')
    end_date = str(payload.get('end_date') or contract.get('end_date') or '').strip()
    update_data = {
        'contract_number': str(payload.get('contract_number') or contract.get('contract_number') or '').strip(),
        'issue_date': str(payload.get('issue_date') or contract.get('issue_date') or '').strip(),
        'start_date': str(payload.get('start_date') or contract.get('start_date') or '').strip(),
        'end_date': end_date,
        'status': status,
        'contractor_name': str(payload.get('contractor_name') or '').strip(),
        'contractor_legal_name': str(payload.get('contractor_legal_name') or '').strip(),
        'contractor_trade_name': str(payload.get('contractor_trade_name') or '').strip(),
        'contractor_cnpj': str(payload.get('contractor_cnpj') or '').strip(),
        'contractor_address': str(payload.get('contractor_address') or '').strip(),
        'contractor_representative': str(payload.get('contractor_representative') or '').strip(),
        'contractor_representative_role': str(payload.get('contractor_representative_role') or '').strip(),
        'contractor_email': str(payload.get('contractor_email') or '').strip().lower(),
        'contractor_phone': str(payload.get('contractor_phone') or '').strip(),
        'contractor_witness_1': str(payload.get('contractor_witness_1') or '').strip(),
        'contractor_witness_2': str(payload.get('contractor_witness_2') or '').strip(),
        'provider_name': str(payload.get('provider_name') or '').strip(),
        'provider_legal_name': str(payload.get('provider_legal_name') or '').strip(),
        'provider_cnpj': str(payload.get('provider_cnpj') or '').strip(),
        'provider_address': str(payload.get('provider_address') or '').strip(),
        'provider_representative': str(payload.get('provider_representative') or '').strip(),
        'provider_representative_role': str(payload.get('provider_representative_role') or '').strip(),
        'provider_email': str(payload.get('provider_email') or '').strip().lower(),
        'provider_phone': str(payload.get('provider_phone') or '').strip(),
        'provider_witnesses': str(payload.get('provider_witnesses') or '').strip(),
        'clauses_text': str(payload.get('clauses_text') or '').strip() or DEFAULT_SAAS_CONTRACT_CLAUSES,
        'notes': str(payload.get('notes') or '').strip(),
        'retention_until': _next_retention_date(end_date),
    }
    now = datetime.now(UTC).isoformat()
    connection.execute(
        '''
        UPDATE commercial_contracts SET
            contract_number = ?, issue_date = ?, start_date = ?, end_date = ?, status = ?,
            contractor_name = ?, contractor_legal_name = ?, contractor_trade_name = ?, contractor_cnpj = ?, contractor_address = ?,
            contractor_representative = ?, contractor_representative_role = ?, contractor_email = ?, contractor_phone = ?,
            contractor_witness_1 = ?, contractor_witness_2 = ?, provider_name = ?, provider_legal_name = ?, provider_cnpj = ?,
            provider_address = ?, provider_representative = ?, provider_representative_role = ?, provider_email = ?, provider_phone = ?,
            provider_witnesses = ?, clauses_text = ?, notes = ?, retention_until = ?, updated_at = ?
        WHERE id = ?
        ''',
        (
            update_data['contract_number'], update_data['issue_date'], update_data['start_date'], update_data['end_date'], update_data['status'],
            update_data['contractor_name'], update_data['contractor_legal_name'], update_data['contractor_trade_name'], update_data['contractor_cnpj'], update_data['contractor_address'],
            update_data['contractor_representative'], update_data['contractor_representative_role'], update_data['contractor_email'], update_data['contractor_phone'],
            update_data['contractor_witness_1'], update_data['contractor_witness_2'], update_data['provider_name'], update_data['provider_legal_name'], update_data['provider_cnpj'],
            update_data['provider_address'], update_data['provider_representative'], update_data['provider_representative_role'], update_data['provider_email'], update_data['provider_phone'],
            update_data['provider_witnesses'], update_data['clauses_text'], update_data['notes'], update_data['retention_until'], now,
            int(contract['id'])
        )
    )
    updated = get_or_create_commercial_contract(connection, actor, company_id)
    register_commercial_contract_event(connection, actor, updated, 'saved', {'status': updated.get('status')})
    return updated


def generate_commercial_contract_pdf(connection, actor, company_id):
    contract = get_or_create_commercial_contract(connection, actor, company_id)
    pdf_bytes = build_commercial_contract_pdf(connection, actor, company_id)
    now = datetime.now(UTC).isoformat()
    connection.execute(
        'UPDATE commercial_contracts SET generated_pdf_base64 = ?, status = ?, updated_at = ? WHERE id = ?',
        (base64.b64encode(pdf_bytes).decode('ascii'), 'generated', now, int(contract['id']))
    )
    updated = get_or_create_commercial_contract(connection, actor, company_id)
    register_commercial_contract_event(connection, actor, updated, 'generated', {})
    return updated


def sign_commercial_contract(connection, actor, payload):
    company_id = int(payload.get('company_id') or 0)
    signature_name = str(payload.get('signature_name') or '').strip()
    signature_data = str(payload.get('signature_data') or '').strip()
    if not signature_name or not signature_data:
        raise ValueError('Informe nome e assinatura digital.')
    contract = get_or_create_commercial_contract(connection, actor, company_id)
    now = datetime.now(UTC).isoformat()
    connection.execute(
        '''
        UPDATE commercial_contracts
        SET signature_name = ?, signature_data = ?, signature_at = ?, signed_at = ?, status = ?, updated_at = ?
        WHERE id = ?
        ''',
        (signature_name, signature_data, now, now, 'signed', now, int(contract['id']))
    )
    updated = get_or_create_commercial_contract(connection, actor, company_id)
    register_commercial_contract_event(connection, actor, updated, 'signed', {'signature_name': signature_name})
    return updated


def upload_signed_contract_file(connection, actor, payload):
    company_id = int(payload.get('company_id') or 0)
    file_name = str(payload.get('file_name') or '').strip()
    file_mime = str(payload.get('file_mime') or 'application/pdf').strip()
    file_base64 = str(payload.get('file_base64') or '').strip()
    if not file_name or not file_base64:
        raise ValueError('Arquivo assinado inválido.')
    if file_mime not in ('application/pdf', 'application/octet-stream'):
        raise ValueError('Formato inválido. Utilize PDF.')
    raw = base64.b64decode(file_base64.encode('ascii'), validate=True)
    if len(raw) > 10 * 1024 * 1024:
        raise ValueError('Arquivo excede 10MB.')
    contract = get_or_create_commercial_contract(connection, actor, company_id)
    now = datetime.now(UTC).isoformat()
    connection.execute(
        '''
        UPDATE commercial_contracts
        SET signed_pdf_base64 = ?, signed_file_name = ?, signed_file_mime = ?, signed_at = ?, status = ?, updated_at = ?
        WHERE id = ?
        ''',
        (file_base64, file_name, file_mime, now, 'signed', now, int(contract['id']))
    )
    updated = get_or_create_commercial_contract(connection, actor, company_id)
    register_commercial_contract_event(connection, actor, updated, 'uploaded_signed_file', {'file_name': file_name})
    return updated


def send_commercial_contract_email(connection, actor, payload):
    company_id = int(payload.get('company_id') or 0)
    email_to = str(payload.get('email_to') or '').strip().lower()
    subject = str(payload.get('subject') or '').strip() or 'Contrato comercial EPI Controle'
    body = str(payload.get('body') or '').strip() or 'Segue contrato comercial para análise e assinatura.'
    if not email_to:
        raise ValueError('E-mail do destinatário é obrigatório.')
    contract = get_or_create_commercial_contract(connection, actor, company_id)
    now = datetime.now(UTC).isoformat()
    connection.execute(
        '''
        UPDATE commercial_contracts
        SET last_email_to = ?, last_email_subject = ?, last_email_body = ?, last_email_sent_at = ?, status = ?, updated_at = ?
        WHERE id = ?
        ''',
        (email_to, subject, body, now, 'sent', now, int(contract['id']))
    )
    updated = get_or_create_commercial_contract(connection, actor, company_id)
    register_commercial_contract_event(connection, actor, updated, 'email_sent', {'email_to': email_to, 'subject': subject})
    return updated


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
    expires_at_dt = parse_iso_datetime_utc(expires_at)
    if expires_at_dt and expires_at_dt <= datetime.now(UTC):
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
               employee_portal_links.cpf_attempts, employee_portal_links.last_cpf_attempt_at, employee_portal_links.blocked_at,
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
    return item


def ensure_employee_last3_cpf(connection, employee_id, cpf_last3):
    digits = ''.join(ch for ch in str(cpf_last3 or '') if ch.isdigit())
    if len(digits) != 3:
        raise PermissionError('Informe os 3 últimos dígitos do CPF para acessar.')
    employee = get_employee_by_id(connection, int(employee_id))
    if not employee:
        raise PermissionError('Colaborador não encontrado para validação do CPF.')
    cpf_digits = normalize_cpf(employee.get('cpf'))
    if cpf_digits[-3:] != digits:
        raise PermissionError('Os 3 últimos dígitos do CPF não conferem.')


def validate_portal_cpf_with_attempts(connection, portal_context, cpf_last3, *, ip_address='', user_agent=''):
    if not portal_context:
        raise EmployeePortalAccessDenied('TOKEN_NOT_FOUND', MSG_TOKEN_EXPIRED_ACCESS)
    if int(portal_context.get('active') or 0) != 1:
        raise EmployeePortalAccessDenied('TOKEN_REVOKED', MSG_TOKEN_EXPIRED_ACCESS, portal_context=portal_context)
    if str(portal_context.get('blocked_at') or '').strip():
        raise EmployeePortalAccessDenied('LINK_BLOCKED', 'Este link foi bloqueado por tentativas inválidas de CPF. Solicite um novo token.', portal_context=portal_context)

    expires_at = str(portal_context.get('expires_at') or '').strip()
    expires_at_dt = parse_iso_datetime_utc(expires_at)
    if expires_at_dt and expires_at_dt <= datetime.now(UTC):
        raise EmployeePortalAccessDenied('TOKEN_EXPIRED', MSG_TOKEN_EXPIRED_ACCESS, portal_context=portal_context)

    digits = ''.join(ch for ch in str(cpf_last3 or '') if ch.isdigit())
    if len(digits) != 3:
        raise EmployeePortalAccessDenied('CPF_LAST3_INVALID', 'Informe os 3 últimos dígitos do CPF para acessar.', portal_context=portal_context)

    employee = get_employee_by_id(connection, int(portal_context['employee_id']))
    if not employee:
        raise PermissionError('Colaborador não encontrado para validação do CPF.')
    cpf_digits = normalize_cpf(employee.get('cpf'))
    attempts = int(portal_context.get('cpf_attempts') or 0)
    now = datetime.now(UTC).isoformat()

    if cpf_digits[-3:] == digits:
        if attempts > 0:
            connection.execute(
                "UPDATE employee_portal_links SET cpf_attempts = 0, last_cpf_attempt_at = '', updated_at = ? WHERE id = ?",
                (now, int(portal_context['portal_link_id'])),
            )
        register_employee_portal_audit(
            connection,
            portal_context,
            'cpf_validation_success',
            ip_address=ip_address,
            user_agent=user_agent,
            payload={'attempts_before_success': attempts},
        )
        return

    attempts += 1
    remaining = max(0, 3 - attempts)
    if attempts >= 3:
        connection.execute(
            "UPDATE employee_portal_links SET cpf_attempts = ?, last_cpf_attempt_at = ?, blocked_at = ?, active = 0, updated_at = ? WHERE id = ?",
            (attempts, now, now, now, int(portal_context['portal_link_id'])),
        )
        register_employee_portal_audit(
            connection,
            portal_context,
            'cpf_validation_blocked',
            ip_address=ip_address,
            user_agent=user_agent,
            payload={'attempts': attempts},
        )
        raise EmployeePortalAccessDenied('LINK_BLOCKED', 'CPF inválido. Token bloqueado após 3 tentativas. Solicite um novo link.', portal_context=portal_context)

    connection.execute(
        "UPDATE employee_portal_links SET cpf_attempts = ?, last_cpf_attempt_at = ?, updated_at = ? WHERE id = ?",
        (attempts, now, now, int(portal_context['portal_link_id'])),
    )
    register_employee_portal_audit(
        connection,
        portal_context,
        'cpf_validation_failed',
        ip_address=ip_address,
        user_agent=user_agent,
        payload={'attempts': attempts, 'remaining_attempts': remaining},
    )
    raise EmployeePortalAccessDenied('CPF_MISMATCH', f'CPF inválido. Tentativas restantes: {remaining}.', portal_context=portal_context)


def resolve_external_employee_context(connection, token, cpf_last3=None, *, ip_address='', user_agent=''):
    if not str(token or '').strip():
        raise EmployeePortalAccessDenied('TOKEN_MISSING', MSG_TOKEN_ABSENT)
    employee_user = get_employee_user_by_token(connection, token)
    if employee_user:
        # Compatibilidade: tokens legados de users.employee_access_token não dependem de employee_portal_links.
        # Mantemos esse fluxo estável e validamos apenas os 3 últimos dígitos do CPF.
        context = {
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
        if cpf_last3 is not None:
            ensure_employee_last3_cpf(connection, context['employee_id'], cpf_last3)
        return context
    context = get_employee_portal_context_by_token(connection, token)
    if not context:
        raise EmployeePortalAccessDenied('TOKEN_NOT_FOUND', MSG_TOKEN_EXPIRED_ACCESS)
    if context:
        validate_portal_cpf_with_attempts(
            connection,
            context,
            cpf_last3,
            ip_address=ip_address,
            user_agent=user_agent,
        )
    return context


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
    lines.append({'text': f"Ficha EPI - {employee_user.get('employee_name')}", 'bold': True, 'size': 14, 'x': 50, 'y': 760})
    lines.append({'text': f"Empresa: {employee_user.get('company_name') or '-'}", 'x': 50, 'y': 738})
    lines.append({'text': f"Matricula: {employee_user.get('employee_id_code') or '-'}", 'x': 50, 'y': 720})
    lines.append({'text': f"Setor: {employee_user.get('sector') or '-'}", 'x': 50, 'y': 702})
    lines.append({'text': f"Funcao: {employee_user.get('role_name') or '-'}", 'x': 50, 'y': 684})
    lines.append({'text': ' ', 'x': 50, 'y': 666})
    if deliveries:
        y = 648
        for item in deliveries:
            lines.append({
                'text': f"{item['delivery_date']} | {item['epi_name']} ({item['purchase_code']}) | {item['quantity']} {item['quantity_label']} | assinatura: {item['signature_name']} {item['signature_at'] or ''}",
                'x': 50,
                'y': y,
                'size': 10
            })
            y -= 16
            if y < 60:
                break
    else:
        lines.append({'text': 'Nenhuma entrega encontrada.', 'x': 50, 'y': 648})
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
    sql = '''SELECT employees.id, employees.company_id, employees.unit_id, employees.employee_id_code, employees.cpf, employees.name, employees.email, employees.whatsapp, employees.preferred_contact_channel, employees.sector, employees.role_name, employees.admission_date, employees.schedule_type, employees.tipo_vinculo, employees.empresa_origem, companies.name AS company_name, companies.cnpj AS company_cnpj, companies.logo_type, units.name AS unit_name, units.unit_type, units.city AS unit_city FROM employees JOIN companies ON companies.id = employees.company_id JOIN units ON units.id = employees.unit_id'''
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


def get_unit_active_jv_name(connection, unit_id):
    """Retorna o nome da JV ativa de uma unidade, ou '' se não houver."""
    if not unit_id:
        return ''
    row = connection.execute(
        'SELECT joint_venture_name FROM unit_joint_venture_periods '
        'WHERE unit_id = ? AND ended_at IS NULL '
        'ORDER BY started_at DESC LIMIT 1',
        (int(unit_id),)
    ).fetchone()
    if not row:
        return ''
    return str(dict(row).get('joint_venture_name') or '').strip()


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
                    epis.active,
                    COALESCE((
                        SELECT SUM(unit_epi_stock.quantity) FROM unit_epi_stock
                        WHERE unit_epi_stock.company_id = epis.company_id AND unit_epi_stock.epi_id = epis.id
                    ), epis.stock, 0) AS stock,
                    epis.minimum_stock, epis.unit_measure, epis.ca_expiry, epis.epi_validity_date,
                    epis.manufacture_date, epis.validity_days, epis.validity_years, epis.validity_months, epis.manufacturer_validity_months, epis.default_replacement_days,
                    epis.manufacturer, epis.model_reference, epis.supplier_company, epis.manufacturer_recommendations, epis.epi_photo_data,
                    epis.glove_size, epis.size, epis.uniform_size,
                    epis.joinventures_json, epis.active_joinventure,
                    epis.scope_type, epis.is_joint_venture,
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
    items = []
    for row in rows:
        item = row_to_dict(row)
        scope_type = str(item.get('scope_type') or '').strip().upper()
        if scope_type not in {'GLOBAL', 'UNIT', 'JOINT_VENTURE'}:
            scope_type, is_jv = resolve_epi_scope_metadata(item.get('unit_id'), item.get('active_joinventure'))
            item['scope_type'] = scope_type
            item['is_joint_venture'] = is_jv
        if not item.get('unit_name') and str(item.get('scope_type') or '').upper() == 'GLOBAL':
            item['unit_name'] = 'Todas as Unidades'
        item['scope_label'] = (
            'Todas as Unidades'
            if str(item.get('scope_type') or '').upper() == 'GLOBAL'
            else f"{item.get('unit_name') or '-'}{' (Joint Venture)' if int(item.get('is_joint_venture') or 0) == 1 else ''}"
        )
        items.append(item)
    return items


def generate_po_number(connection, company_id):
    year = datetime.now(UTC).year
    prefix = f'PO-{year}-'
    row = connection.execute(
        "SELECT MAX(CAST(SUBSTR(po_number, ?) AS INTEGER)) AS last_seq FROM purchase_orders WHERE company_id = ? AND po_number LIKE ?",
        (len(prefix) + 1, company_id, f'{prefix}%')
    ).fetchone()
    last_seq = int(row['last_seq'] or 0) if row else 0
    return f'{prefix}{last_seq + 1:04d}'


def fetch_epi_size_balance(connection, company_id, unit_id, epi_id):
    try:
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
    except Exception:
        return []
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
    rows = connection.execute(f'''SELECT deliveries.id, deliveries.company_id, deliveries.employee_id, deliveries.epi_id, deliveries.quantity, deliveries.quantity_label, deliveries.sector, deliveries.role_name, deliveries.delivery_date, deliveries.next_replacement_date, deliveries.notes, deliveries.signature_name, deliveries.signature_data, deliveries.signature_at, deliveries.signature_comment, deliveries.unit_id, deliveries.stock_movement_id, deliveries.glove_size, deliveries.size, deliveries.uniform_size, deliveries.returned_date, deliveries.returned_condition, deliveries.returned_notes, deliveries.return_movement_id,
                                  companies.name AS company_name, companies.cnpj AS company_cnpj, companies.logo_type,
                                  employees.employee_id_code, employees.name AS employee_name, employees.schedule_type, employees.tipo_vinculo,
                                  units.name AS unit_name, units.unit_type, epis.name AS epi_name, epis.purchase_code, epis.ca, epis.unit_measure, epis.epi_validity_date, epis.manufacture_date, epis.qr_code_value,
                                  esi.glove_size AS stock_item_glove_size, esi.size AS stock_item_size, esi.uniform_size AS stock_item_uniform_size,
                                  CASE WHEN COALESCE(deliveries.returned_date, '') != '' THEN 0
                                       WHEN EXISTS (
                                           SELECT 1 FROM epi_ficha_items fi
                                           JOIN epi_ficha_periods fp ON fp.id = fi.ficha_period_id
                                           WHERE fi.delivery_id = deliveries.id
                                             AND fp.status = 'closed'
                                       ) THEN 0
                                       WHEN NOT EXISTS (
                                           SELECT 1 FROM epi_ficha_items fi WHERE fi.delivery_id = deliveries.id
                                       ) AND EXISTS (
                                           SELECT 1 FROM epi_ficha_periods fp
                                           WHERE fp.employee_id = deliveries.employee_id
                                             AND fp.period_start <= deliveries.delivery_date
                                             AND fp.period_end   >= deliveries.delivery_date
                                             AND fp.status = 'closed'
                                       ) THEN 0
                                       ELSE 1 END AS devolution_available
                           FROM deliveries
                           JOIN companies ON companies.id = deliveries.company_id
                           JOIN employees ON employees.id = deliveries.employee_id
                           LEFT JOIN units ON units.id = deliveries.unit_id
                           JOIN epis ON epis.id = deliveries.epi_id
                           LEFT JOIN epi_stock_items esi ON esi.delivery_id = deliveries.id AND esi.id = (SELECT MAX(esi_latest.id) FROM epi_stock_items esi_latest WHERE esi_latest.delivery_id = deliveries.id)
                           {final_where}
                           ORDER BY deliveries.delivery_date DESC, deliveries.id DESC''', tuple(query_params)).fetchall()
    items = []
    for row in rows:
        item = row_to_dict(row)
        apply_effective_size_fields(item, item, item, fallback_prefix='stock_item_')
        items.append(item)
    return items


def fetch_open_deliveries_for_devolution(connection, actor, employee_id, epi_id, unit_id=None):
    employee_id = int(employee_id)
    epi_id = int(epi_id)
    clauses = [
        'd.employee_id = ?',
        'd.epi_id = ?',
        "COALESCE(d.returned_date, '') = ''",
        # Bloqueia se o período vinculado à entrega (via ficha_items) está encerrado.
        # Para entregas legadas sem ficha_items, usa fallback por range de datas.
        """(
            NOT EXISTS (
                SELECT 1 FROM epi_ficha_items fi
                JOIN epi_ficha_periods fp ON fp.id = fi.ficha_period_id
                WHERE fi.delivery_id = d.id AND fp.status = 'closed'
            )
            AND (
                EXISTS (SELECT 1 FROM epi_ficha_items fi WHERE fi.delivery_id = d.id)
                OR NOT EXISTS (
                    SELECT 1 FROM epi_ficha_periods fp
                    WHERE fp.employee_id = d.employee_id
                      AND fp.period_start <= d.delivery_date
                      AND fp.period_end   >= d.delivery_date
                      AND fp.status = 'closed'
                )
            )
        )""",
    ]
    params = [employee_id, epi_id]
    if actor and actor.get('role') != 'master_admin':
        clauses.append('d.company_id = ?')
        params.append(int(actor.get('company_id') or 0))
    if str(unit_id or '').strip():
        clauses.append('d.unit_id = ?')
        params.append(int(unit_id))
    where_sql = f"WHERE {' AND '.join(clauses)}"
    rows = connection.execute(
        f'''
        SELECT d.id, d.employee_id, d.epi_id, d.unit_id, d.delivery_date, d.quantity, d.quantity_label,
               d.signature_at, d.signature_name,
               COALESCE(u.name, '') AS unit_name, COALESCE(c.name, '') AS company_name
        FROM deliveries d
        JOIN companies c ON c.id = d.company_id
        LEFT JOIN units u ON u.id = d.unit_id
        {where_sql}
        ORDER BY d.delivery_date DESC, d.id DESC
        ''',
        tuple(params),
    ).fetchall()
    items = []
    for row in rows:
        parsed = row_to_dict(row)
        items.append(
            {
                'id': int(parsed['id']),
                'employee_id': int(parsed['employee_id']),
                'epi_id': int(parsed['epi_id']),
                'delivery_date': str(parsed.get('delivery_date') or ''),
                'quantity': int(parsed.get('quantity') or 1),
                'quantity_label': str(parsed.get('quantity_label') or ''),
                'unit_id': int(parsed.get('unit_id') or 0),
                'unit_name': str(parsed.get('unit_name') or ''),
                'company_name': str(parsed.get('company_name') or ''),
                'signature_at': str(parsed.get('signature_at') or ''),
                'signature_name': str(parsed.get('signature_name') or ''),
            }
        )
    return items


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


EPI_FEEDBACK_STATUSES = {
    'recebido': 'Recebido',
    'em_analise_gestor': 'Em Análise pelo Gestor de EPI',
    'aguardando_hseq': 'Aguardando HSEQ',
    'analise_hseq_concluida': 'Análise HSEQ Concluída',
    'encaminhado_administracao': 'Encaminhado para Administração',
    'aguardando_aprovacao_admin': 'Aguardando Aprovação Administrativa',
    'aprovado': 'Aprovado',
    'reprovado': 'Reprovado',
    'acao_corretiva_aberta': 'Ação Corretiva Aberta',
    'encerrado': 'Encerrado',
    'solicitada_mais_informacao': 'Solicitada Mais Informação',
    # legado
    'pendente': 'Pendente',
    'em análise': 'Em Análise',
    'aprovada': 'Aprovada',
    'rejeitada': 'Reprovada',
    'arquivada': 'Arquivada',
}

EPI_FEEDBACK_TYPES = {'avaliacao', 'sugestao', 'reclamacao', 'elogio'}
EPI_FEEDBACK_PRIORITIES = {'baixa', 'normal', 'alta', 'urgente'}

EPI_FEEDBACK_ADMIN_ACTIONS_SUGGESTION = {
    'aprovar_sugestao', 'reprovar_sugestao', 'solicitar_mais_informacoes',
    'solicitar_analise_hseq', 'transformar_em_cadastro', 'encerrar',
}
EPI_FEEDBACK_ADMIN_ACTIONS_AVALIACAO = {
    'registrar_acao', 'abrir_acao_corretiva', 'encerrar_como_informacao',
    'encaminhar_fornecedor', 'registrar_elogio', 'solicitar_substituicao_epi', 'encerrar',
}


def _record_feedback_history(connection, feedback_id, company_id, action, previous_status, new_status, actor, notes='', reason=''):
    now = datetime.now(UTC).isoformat()
    connection.execute(
        'INSERT INTO epi_feedback_history (feedback_id, company_id, status, notes, actor_user_id, actor_name, actor_role, action, previous_status, reason, created_at) '
        'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
        (
            int(feedback_id),
            int(company_id),
            str(new_status),
            str(notes or ''),
            int(actor['id']) if actor else None,
            str(actor.get('full_name') or '') if actor else '',
            str(actor.get('role') or '') if actor else '',
            str(action),
            str(previous_status),
            str(reason or ''),
            now,
        )
    )


def fetch_feedback_detail(connection, feedback_id, actor):
    row = connection.execute(
        '''
        SELECT f.*, companies.name AS company_name, units.name AS unit_name,
               employees.name AS employee_name, epis.name AS epi_name
        FROM epi_feedbacks f
        JOIN companies ON companies.id = f.company_id
        JOIN units ON units.id = f.unit_id
        JOIN employees ON employees.id = f.employee_id
        LEFT JOIN epis ON epis.id = f.epi_id
        WHERE f.id = ?
        ''',
        (int(feedback_id),)
    ).fetchone()
    if not row:
        raise ValueError('Avaliação/Sugestão não encontrada.')
    feedback = row_to_dict(row)
    ensure_resource_company(actor, feedback, 'Avaliação')
    history = connection.execute(
        'SELECT * FROM epi_feedback_history WHERE feedback_id = ? ORDER BY created_at ASC, id ASC',
        (int(feedback_id),)
    ).fetchall()
    feedback['history'] = [row_to_dict(h) for h in history]
    return feedback


def apply_feedback_triage(connection, actor, feedback_id, payload):
    ensure_permission(actor, PERM_EPI_FEEDBACK_TRIAGE)
    feedback = connection.execute('SELECT * FROM epi_feedbacks WHERE id = ?', (int(feedback_id),)).fetchone()
    if not feedback:
        raise ValueError('Avaliação/Sugestão não encontrada.')
    fb = row_to_dict(feedback)
    ensure_resource_company(actor, fb, 'Avaliação')
    fb_type = str(payload.get('type') or fb.get('type') or 'avaliacao').strip().lower()
    if fb_type not in EPI_FEEDBACK_TYPES:
        raise ValueError('Tipo de feedback inválido.')
    category = str(payload.get('category') or '').strip()
    priority = str(payload.get('priority') or 'normal').strip().lower()
    if priority not in EPI_FEEDBACK_PRIORITIES:
        raise ValueError('Prioridade inválida.')
    hseq_required = bool(payload.get('hseq_required'))
    hseq_user_id = payload.get('hseq_user_id')
    notes = str(payload.get('notes') or '').strip()
    previous_status = str(fb.get('status') or 'pendente')
    new_status = 'aguardando_hseq' if hseq_required else 'em_analise_gestor'
    now = datetime.now(UTC).isoformat()
    connection.execute(
        '''
        UPDATE epi_feedbacks SET type=?, category=?, priority=?, hseq_required=?, hseq_user_id=?,
            assigned_epi_manager_id=?, status=?, reviewer_user_id=?, reviewer_name=?, reviewed_at=?, updated_at=?
        WHERE id=?
        ''',
        (
            fb_type, category, priority, int(hseq_required),
            int(hseq_user_id) if hseq_user_id else None,
            int(actor['id']),
            new_status, int(actor['id']), actor['full_name'], now, now,
            int(feedback_id),
        )
    )
    _record_feedback_history(connection, feedback_id, fb['company_id'], 'triage', previous_status, new_status, actor, notes)
    return {'ok': True, 'status': new_status}


def apply_feedback_hseq_review(connection, actor, feedback_id, payload):
    ensure_permission(actor, PERM_EPI_FEEDBACK_HSEQ_REVIEW)
    feedback = connection.execute('SELECT * FROM epi_feedbacks WHERE id = ?', (int(feedback_id),)).fetchone()
    if not feedback:
        raise ValueError('Avaliação/Sugestão não encontrada.')
    fb = row_to_dict(feedback)
    ensure_resource_company(actor, fb, 'Avaliação')
    hseq_opinion = str(payload.get('hseq_opinion') or '').strip()
    if not hseq_opinion:
        raise ValueError('Parecer HSEQ é obrigatório.')
    notes = str(payload.get('notes') or '').strip()
    previous_status = str(fb.get('status') or '')
    new_status = 'analise_hseq_concluida'
    now = datetime.now(UTC).isoformat()
    connection.execute(
        'UPDATE epi_feedbacks SET hseq_user_id=?, hseq_opinion=?, hseq_analyzed_at=?, status=?, updated_at=? WHERE id=?',
        (int(actor['id']), hseq_opinion, now, new_status, now, int(feedback_id))
    )
    _record_feedback_history(connection, feedback_id, fb['company_id'], 'hseq_review', previous_status, new_status, actor, notes)
    return {'ok': True, 'status': new_status}


def apply_feedback_forward_admin(connection, actor, feedback_id, payload):
    ensure_permission(actor, PERM_EPI_FEEDBACK_TRIAGE)
    feedback = connection.execute('SELECT * FROM epi_feedbacks WHERE id = ?', (int(feedback_id),)).fetchone()
    if not feedback:
        raise ValueError('Avaliação/Sugestão não encontrada.')
    fb = row_to_dict(feedback)
    ensure_resource_company(actor, fb, 'Avaliação')
    notes = str(payload.get('notes') or '').strip()
    previous_status = str(fb.get('status') or '')
    new_status = 'aguardando_aprovacao_admin'
    now = datetime.now(UTC).isoformat()
    connection.execute(
        "UPDATE epi_feedbacks SET status=?, updated_at=? WHERE id=?",
        (new_status, now, int(feedback_id))
    )
    _record_feedback_history(connection, feedback_id, fb['company_id'], 'forward_admin', previous_status, new_status, actor, notes)
    return {'ok': True, 'status': new_status}


def apply_feedback_admin_decision(connection, actor, feedback_id, payload):
    ensure_permission(actor, PERM_EPI_FEEDBACK_ADMIN_APPROVE)
    feedback = connection.execute('SELECT * FROM epi_feedbacks WHERE id = ?', (int(feedback_id),)).fetchone()
    if not feedback:
        raise ValueError('Avaliação/Sugestão não encontrada.')
    fb = row_to_dict(feedback)
    ensure_resource_company(actor, fb, 'Avaliação')
    fb_type = str(fb.get('type') or 'avaliacao').strip()
    decision = str(payload.get('decision') or '').strip()
    if fb_type == 'sugestao':
        valid_decisions = EPI_FEEDBACK_ADMIN_ACTIONS_SUGGESTION
    else:
        valid_decisions = EPI_FEEDBACK_ADMIN_ACTIONS_AVALIACAO
    if not decision:
        raise ValueError('A decisão administrativa é obrigatória.')
    if decision not in valid_decisions:
        raise ValueError('Decisão administrativa inválida para este tipo de feedback.')
    justification = str(payload.get('justification') or '').strip()
    if not justification:
        raise ValueError('Justificativa é obrigatória para decisão administrativa.')
    notes = str(payload.get('notes') or '').strip()
    previous_status = str(fb.get('status') or '')
    status_map = {
        'aprovar_sugestao': 'aprovado',
        'reprovar_sugestao': 'reprovado',
        'abrir_acao_corretiva': 'acao_corretiva_aberta',
        'encerrar': 'encerrado',
        'encerrar_como_informacao': 'encerrado',
        'solicitar_mais_informacoes': 'solicitada_mais_informacao',
        'solicitar_analise_hseq': 'aguardando_hseq',
    }
    new_status = status_map.get(decision, 'encerrado')
    now = datetime.now(UTC).isoformat()
    connection.execute(
        '''
        UPDATE epi_feedbacks SET admin_decision=?, admin_decision_by_user_id=?, admin_decision_by_name=?,
            admin_decision_at=?, final_justification=?, status=?, updated_at=?
        WHERE id=?
        ''',
        (decision, int(actor['id']), actor['full_name'], now, justification, new_status, now, int(feedback_id))
    )
    _record_feedback_history(connection, feedback_id, fb['company_id'], decision, previous_status, new_status, actor, notes, reason=justification)
    return {'ok': True, 'status': new_status, 'decision': decision}


def apply_feedback_close(connection, actor, feedback_id, payload):
    ensure_permission(actor, PERM_EPI_FEEDBACK_CLOSE)
    feedback = connection.execute('SELECT * FROM epi_feedbacks WHERE id = ?', (int(feedback_id),)).fetchone()
    if not feedback:
        raise ValueError('Avaliação/Sugestão não encontrada.')
    fb = row_to_dict(feedback)
    ensure_resource_company(actor, fb, 'Avaliação')
    notes = str(payload.get('notes') or '').strip()
    previous_status = str(fb.get('status') or '')
    now = datetime.now(UTC).isoformat()
    connection.execute(
        "UPDATE epi_feedbacks SET status='encerrado', updated_at=? WHERE id=?",
        (now, int(feedback_id))
    )
    _record_feedback_history(connection, feedback_id, fb['company_id'], 'close', previous_status, 'encerrado', actor, notes)
    return {'ok': True, 'status': 'encerrado'}


def fetch_feedbacks_for_manager(connection, actor):
    """Return feedbacks scoped to actor's role and company."""
    clauses = []
    params = []
    role = str(actor.get('role') or '')
    if role != 'master_admin':
        clauses.append('f.company_id = ?')
        params.append(int(actor['company_id']))
    if role in ('epi_manager', 'user'):
        clauses.append("f.status NOT IN ('encerrado', 'reprovado')")
    where_sql = ('WHERE ' + ' AND '.join(clauses)) if clauses else ''
    rows = connection.execute(
        f'''
        SELECT f.*, companies.name AS company_name, units.name AS unit_name,
               employees.name AS employee_name, epis.name AS epi_name
        FROM epi_feedbacks f
        JOIN companies ON companies.id = f.company_id
        JOIN units ON units.id = f.unit_id
        JOIN employees ON employees.id = f.employee_id
        LEFT JOIN epis ON epis.id = f.epi_id
        {where_sql}
        ORDER BY f.created_at DESC, f.id DESC
        ''',
        tuple(params)
    ).fetchall()
    return [row_to_dict(row) for row in rows]


EMPLOYEE_PORTAL_STATUS_LABELS = {
    '': 'Enviada',
    'enviado_gestor': 'Em Análise',
    'enviado_admin': 'Encaminh. Admin',
    'aceito': 'Aceito',
    'recusado': 'Recusado',
    'bem_avaliado': 'Bem Avaliado',
    'mal_avaliado': 'Mal Avaliado',
    'em_reavaliacao_3m': 'Reavaliação 3m',
    'em_reavaliacao_6m': 'Reavaliação 6m',
}

REJECTION_REASON_LABELS = {
    'sem_ca': 'Sem CA aprovado pelo Brasil',
    'fornecedor_nao_aprovado': 'Fornecedor não aprovado',
    'outro': 'Outro motivo',
}

RISK_LEVEL_LABELS = {
    'nenhum': 'Nenhum',
    'baixo': 'Baixo',
    'medio': 'Médio',
    'alto': 'Alto',
}

EPI_RANK_LABELS = {
    'excelente': 'Excelente',
    'otimo': 'Ótimo',
    'muito_bom': 'Muito Bom',
    'ruim': 'Ruim',
    'muito_ruim': 'Muito Ruim',
    'pessimo': 'Péssimo',
    'excelente_sug': 'Excelente Sugestão',
    'otima_sug': 'Ótima Sugestão',
    'muito_boa_sug': 'Muito Boa Sugestão',
    'pessima_sug': 'Péssima Sugestão',
    'muito_ruim_sug': 'Muito Ruim a Sugestão',
    'ruim_sug': 'Ruim a Sugestão',
}


def apply_feedback_manager_validate(connection, actor, feedback_id, payload):
    ensure_permission(actor, PERM_EPI_FEEDBACK_MANAGER_EVAL)
    feedback = connection.execute('SELECT * FROM epi_feedbacks WHERE id = ?', (int(feedback_id),)).fetchone()
    if not feedback:
        raise ValueError('Avaliação não encontrada.')
    fb = row_to_dict(feedback)
    ensure_resource_company(actor, fb, 'Avaliação')
    notes = str(payload.get('notes') or '').strip()
    feedback_subtype = str(payload.get('feedback_subtype') or fb.get('feedback_subtype') or '').strip()
    risk_level = str(payload.get('risk_level') or 'nenhum').strip()
    epi_rank = str(payload.get('epi_rank') or '').strip()
    if epi_rank and epi_rank not in EPI_RANK_LABELS:
        epi_rank = ''
    previous_status = str(fb.get('status') or 'pendente')
    new_status = 'aguardando_aprovacao_admin'
    portal_status = 'enviado_admin'
    portal_message = 'Sua avaliação foi validada pelo Gestor de EPI e encaminhada ao responsável para análise.'
    now = datetime.now(UTC).isoformat()
    connection.execute(
        '''UPDATE epi_feedbacks SET manager_eval_status=?, manager_eval_notes=?, manager_eval_at=?,
           feedback_subtype=?, risk_level=?, epi_rank=?, employee_portal_status=?, employee_portal_message=?,
           status=?, reviewer_user_id=?, reviewer_name=?, reviewed_at=?, updated_at=?
           WHERE id=?''',
        ('validado', notes, now, feedback_subtype, risk_level, epi_rank, portal_status, portal_message,
         new_status, int(actor['id']), actor['full_name'], now, now, int(feedback_id))
    )
    _record_feedback_history(connection, feedback_id, fb['company_id'], 'manager_validate', previous_status, new_status, actor, notes)
    return {'ok': True, 'status': new_status}


def apply_feedback_manager_reject(connection, actor, feedback_id, payload):
    ensure_permission(actor, PERM_EPI_FEEDBACK_MANAGER_EVAL)
    feedback = connection.execute('SELECT * FROM epi_feedbacks WHERE id = ?', (int(feedback_id),)).fetchone()
    if not feedback:
        raise ValueError('Avaliação não encontrada.')
    fb = row_to_dict(feedback)
    ensure_resource_company(actor, fb, 'Avaliação')
    rejection_reason = str(payload.get('rejection_reason') or 'outro').strip()
    if rejection_reason not in ('sem_ca', 'fornecedor_nao_aprovado', 'outro'):
        rejection_reason = 'outro'
    supplier_eval_requested = bool(payload.get('supplier_eval_requested'))
    notes = str(payload.get('notes') or '').strip()
    previous_status = str(fb.get('status') or 'pendente')
    new_status = 'encerrado'
    reason_label = REJECTION_REASON_LABELS.get(rejection_reason, rejection_reason)
    portal_message = f'Sua avaliação foi analisada pelo Gestor de EPI. Motivo: {reason_label}.'
    if supplier_eval_requested:
        portal_message += ' Uma avaliação de fornecedor foi solicitada.'
    now = datetime.now(UTC).isoformat()
    connection.execute(
        '''UPDATE epi_feedbacks SET manager_eval_status=?, manager_eval_notes=?, manager_eval_at=?,
           rejection_reason=?, supplier_eval_requested=?, employee_portal_status=?, employee_portal_message=?,
           status=?, reviewer_user_id=?, reviewer_name=?, reviewed_at=?, updated_at=?
           WHERE id=?''',
        ('rejeitado_gestor', notes, now, rejection_reason, int(supplier_eval_requested),
         'recusado', portal_message,
         new_status, int(actor['id']), actor['full_name'], now, now, int(feedback_id))
    )
    _record_feedback_history(connection, feedback_id, fb['company_id'], 'manager_reject', previous_status, new_status, actor, notes, reason=rejection_reason)
    return {'ok': True, 'status': new_status}


def apply_set_reassessment(connection, actor, feedback_id, payload):
    ensure_permission(actor, PERM_EPI_EVALUATION_DECIDE)
    feedback = connection.execute('SELECT * FROM epi_feedbacks WHERE id = ?', (int(feedback_id),)).fetchone()
    if not feedback:
        raise ValueError('Avaliação não encontrada.')
    fb = row_to_dict(feedback)
    ensure_resource_company(actor, fb, 'Avaliação')
    period = str(payload.get('period') or '').strip()
    if period not in ('3_meses', '6_meses'):
        raise ValueError('Período de reavaliação inválido. Use 3_meses ou 6_meses.')
    portal_status = 'em_reavaliacao_3m' if period == '3_meses' else 'em_reavaliacao_6m'
    months = '3' if period == '3_meses' else '6'
    portal_message = f'Sua avaliação foi registrada. Uma nova solução de EPI será analisada em {months} meses.'
    notes = str(payload.get('notes') or '').strip()
    previous_status = str(fb.get('status') or '')
    now = datetime.now(UTC).isoformat()
    connection.execute(
        '''UPDATE epi_feedbacks SET reassessment_period=?, employee_portal_status=?, employee_portal_message=?,
           status=?, updated_at=? WHERE id=?''',
        (period, portal_status, portal_message, 'acao_corretiva_aberta', now, int(feedback_id))
    )
    _record_feedback_history(connection, feedback_id, fb['company_id'], 'set_reassessment', previous_status, 'acao_corretiva_aberta', actor, notes, reason=period)
    return {'ok': True, 'period': period, 'portal_status': portal_status}


def apply_accept_suggestion_as_epi(connection, actor, feedback_id, payload):
    ensure_permission(actor, PERM_EPI_SUGGESTION_ACCEPT)
    feedback = connection.execute('SELECT * FROM epi_feedbacks WHERE id = ?', (int(feedback_id),)).fetchone()
    if not feedback:
        raise ValueError('Sugestão não encontrada.')
    fb = row_to_dict(feedback)
    ensure_resource_company(actor, fb, 'Sugestão')
    suggested_name = str(fb.get('suggested_new_epi_name') or '').strip()
    if not suggested_name:
        raise ValueError('Esta avaliação não possui sugestão de novo EPI.')
    notes = str(payload.get('notes') or '').strip()
    now = datetime.now(UTC).isoformat()
    new_epi_id = None
    if payload.get('create_epi'):
        ca = str(payload.get('ca') or '').strip()
        sector = str(payload.get('sector') or fb.get('category') or '').strip()
        unit_id = int(fb.get('unit_id') or 0)
        company_id = int(fb.get('company_id') or actor['company_id'])
        cursor = connection.execute(
            '''INSERT INTO epis (company_id, unit_id, name, ca, sector, stock, unit_measure, evaluation_status, active, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, 0, 'un', 'normal', 1, ?, ?)''',
            (company_id, unit_id, suggested_name, ca, sector, now, now)
        )
        new_epi_id = cursor.lastrowid
    connection.execute(
        '''UPDATE epi_feedbacks SET admin_decision='aprovar_sugestao', admin_decision_by_user_id=?,
           admin_decision_by_name=?, admin_decision_at=?, final_justification=?,
           employee_portal_status=?, employee_portal_message=?, status=?, updated_at=? WHERE id=?''',
        (int(actor['id']), actor['full_name'], now, notes,
         'aceito', 'Parabéns! Sua sugestão de EPI foi aceita e poderá ser incluída no catálogo de EPIs aprovados da empresa.',
         'aprovado', now, int(feedback_id))
    )
    _record_feedback_history(connection, feedback_id, fb['company_id'], 'accept_suggestion', str(fb.get('status') or ''), 'aprovado', actor, notes)
    return {'ok': True, 'new_epi_id': new_epi_id}


def compute_epi_evaluation_status(connection, actor):
    ensure_permission(actor, PERM_EPI_EVALUATION_DECIDE)
    company_id = int(actor['company_id']) if actor.get('role') != 'master_admin' else None
    base_where = 'f.company_id = ? AND' if company_id else ''
    params_base = [company_id] if company_id else []
    rows = connection.execute(
        f'''
        SELECT f.epi_id, e.name as epi_name, e.company_id,
               COUNT(*) as total,
               SUM(CASE WHEN f.feedback_subtype = 'reclamacao' OR f.type = 'reclamacao' THEN 1 ELSE 0 END) as reclamacoes,
               SUM(CASE WHEN f.feedback_subtype = 'elogio' OR f.type = 'elogio' THEN 1 ELSE 0 END) as elogios,
               SUM(CASE WHEN f.feedback_subtype = 'sugestao_nova' OR f.type = 'sugestao' THEN 1 ELSE 0 END) as sugestoes,
               SUM(CASE WHEN f.epi_rank = 'excelente' THEN 1 ELSE 0 END) as rank_excelente,
               SUM(CASE WHEN f.epi_rank = 'otimo' THEN 1 ELSE 0 END) as rank_otimo,
               SUM(CASE WHEN f.epi_rank = 'muito_bom' THEN 1 ELSE 0 END) as rank_muito_bom,
               SUM(CASE WHEN f.epi_rank = 'ruim' THEN 1 ELSE 0 END) as rank_ruim,
               SUM(CASE WHEN f.epi_rank = 'muito_ruim' THEN 1 ELSE 0 END) as rank_muito_ruim,
               SUM(CASE WHEN f.epi_rank = 'pessimo' THEN 1 ELSE 0 END) as rank_pessimo,
               SUM(CASE WHEN f.epi_rank = 'excelente_sug' THEN 1 ELSE 0 END) as rank_excelente_sug,
               SUM(CASE WHEN f.epi_rank = 'otima_sug' THEN 1 ELSE 0 END) as rank_otima_sug,
               SUM(CASE WHEN f.epi_rank = 'muito_boa_sug' THEN 1 ELSE 0 END) as rank_muito_boa_sug,
               SUM(CASE WHEN f.epi_rank = 'pessima_sug' THEN 1 ELSE 0 END) as rank_pessima_sug,
               SUM(CASE WHEN f.epi_rank = 'muito_ruim_sug' THEN 1 ELSE 0 END) as rank_muito_ruim_sug,
               SUM(CASE WHEN f.epi_rank = 'ruim_sug' THEN 1 ELSE 0 END) as rank_ruim_sug,
               AVG(COALESCE(NULLIF(f.comfort_rating, 0), NULL)) as avg_comfort,
               AVG(COALESCE(NULLIF(f.quality_rating, 0), NULL)) as avg_quality,
               AVG(COALESCE(NULLIF(f.adequacy_rating, 0), NULL)) as avg_adequacy,
               AVG(COALESCE(NULLIF(f.performance_rating, 0), NULL)) as avg_performance
        FROM epi_feedbacks f
        JOIN epis e ON e.id = f.epi_id
        WHERE {base_where} f.epi_id IS NOT NULL
          AND f.manager_eval_status = 'validado'
          AND f.status NOT IN ('pendente', 'rejeitado_gestor')
        GROUP BY f.epi_id
        ''',
        tuple(params_base)
    ).fetchall()
    now = datetime.now(UTC).isoformat()
    results = []
    for row in rows:
        data = row_to_dict(row)
        epi_id = data['epi_id']
        epi_company_id = int(data.get('company_id') or (company_id or 0))
        reclamacoes = int(data.get('reclamacoes') or 0)
        elogios = int(data.get('elogios') or 0)
        total = int(data.get('total') or 0)
        score = (elogios - reclamacoes) / max(total, 1) * 100
        if reclamacoes >= 5 or (total > 0 and reclamacoes / total >= 0.6):
            eval_status = 'super_mal_avaliado'
        elif elogios >= 5 or (total > 0 and elogios / total >= 0.6):
            eval_status = 'super_bem_avaliado'
        else:
            eval_status = 'normal'
        connection.execute(
            '''INSERT INTO epi_evaluation_summary
               (company_id, epi_id, epi_name, total_avaliacoes, total_reclamacoes, total_elogios, total_sugestoes,
                avg_comfort, avg_quality, avg_adequacy, avg_performance, score, evaluation_status,
                rank_excelente, rank_otimo, rank_muito_bom, rank_ruim, rank_muito_ruim, rank_pessimo,
                rank_excelente_sug, rank_otima_sug, rank_muito_boa_sug, rank_pessima_sug, rank_muito_ruim_sug, rank_ruim_sug,
                last_computed_at, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(company_id, epi_id) DO UPDATE SET
               epi_name=excluded.epi_name, total_avaliacoes=excluded.total_avaliacoes,
               total_reclamacoes=excluded.total_reclamacoes, total_elogios=excluded.total_elogios,
               total_sugestoes=excluded.total_sugestoes, avg_comfort=excluded.avg_comfort,
               avg_quality=excluded.avg_quality, avg_adequacy=excluded.avg_adequacy,
               avg_performance=excluded.avg_performance, score=excluded.score,
               evaluation_status=excluded.evaluation_status,
               rank_excelente=excluded.rank_excelente, rank_otimo=excluded.rank_otimo,
               rank_muito_bom=excluded.rank_muito_bom, rank_ruim=excluded.rank_ruim,
               rank_muito_ruim=excluded.rank_muito_ruim, rank_pessimo=excluded.rank_pessimo,
               rank_excelente_sug=excluded.rank_excelente_sug, rank_otima_sug=excluded.rank_otima_sug,
               rank_muito_boa_sug=excluded.rank_muito_boa_sug, rank_pessima_sug=excluded.rank_pessima_sug,
               rank_muito_ruim_sug=excluded.rank_muito_ruim_sug, rank_ruim_sug=excluded.rank_ruim_sug,
               last_computed_at=excluded.last_computed_at, updated_at=excluded.updated_at''',
            (epi_company_id, epi_id, data['epi_name'],
             total, reclamacoes, elogios, int(data.get('sugestoes') or 0),
             float(data.get('avg_comfort') or 0), float(data.get('avg_quality') or 0),
             float(data.get('avg_adequacy') or 0), float(data.get('avg_performance') or 0),
             score, eval_status,
             int(data.get('rank_excelente') or 0), int(data.get('rank_otimo') or 0),
             int(data.get('rank_muito_bom') or 0), int(data.get('rank_ruim') or 0),
             int(data.get('rank_muito_ruim') or 0), int(data.get('rank_pessimo') or 0),
             int(data.get('rank_excelente_sug') or 0), int(data.get('rank_otima_sug') or 0),
             int(data.get('rank_muito_boa_sug') or 0), int(data.get('rank_pessima_sug') or 0),
             int(data.get('rank_muito_ruim_sug') or 0), int(data.get('rank_ruim_sug') or 0),
             now, now, now)
        )
        connection.execute(
            "UPDATE epis SET evaluation_status=?, updated_at=? WHERE id=?",
            (eval_status, now, epi_id)
        )
        rank_pos_parts = []
        for k, label in [('rank_excelente', 'Excelente'), ('rank_otimo', 'Ótimo'), ('rank_muito_bom', 'Muito Bom')]:
            v = int(data.get(k) or 0)
            if v > 0:
                rank_pos_parts.append(f'{v}× {label}')
        rank_neg_parts = []
        for k, label in [('rank_pessimo', 'Péssimo'), ('rank_muito_ruim', 'Muito Ruim'), ('rank_ruim', 'Ruim')]:
            v = int(data.get(k) or 0)
            if v > 0:
                rank_neg_parts.append(f'{v}× {label}')
        if eval_status == 'super_bem_avaliado':
            rank_detail = (f' Ranks recebidos: {", ".join(rank_pos_parts)}.' if rank_pos_parts else '')
            bem_msg = f'⭐ EPI Super Bem Avaliado! Score: +{round(score, 1)}.{rank_detail} Obrigado pelo seu feedback — ele ajuda a manter os melhores equipamentos em uso!'
            connection.execute(
                "UPDATE epi_feedbacks SET employee_portal_status='bem_avaliado', employee_portal_message=?"
                " WHERE epi_id=? AND (feedback_subtype='elogio' OR type='elogio')"
                " AND employee_portal_status NOT IN ('aceito', 'recusado')",
                (bem_msg, epi_id)
            )
        elif eval_status == 'super_mal_avaliado':
            rank_detail = (f' Ranks registrados: {", ".join(rank_neg_parts)}.' if rank_neg_parts else '')
            mal_msg = f'⚠ EPI Super Mal Avaliado. Score: {round(score, 1)}.{rank_detail} Suas reclamações foram registradas e o EPI entrará em processo de reavaliação.'
            connection.execute(
                "UPDATE epi_feedbacks SET employee_portal_status='mal_avaliado', employee_portal_message=?"
                " WHERE epi_id=? AND (feedback_subtype='reclamacao' OR type='reclamacao')"
                " AND employee_portal_status NOT IN ('aceito', 'recusado', 'em_reavaliacao_3m', 'em_reavaliacao_6m')",
                (mal_msg, epi_id)
            )
        data['score'] = round(score, 1)
        data['evaluation_status'] = eval_status
        results.append(data)
    return {'ok': True, 'items': results}


def apply_admin_technical_evaluate(connection, actor, feedback_id, payload):
    import json as _json
    ensure_permission(actor, PERM_EPI_EVALUATION_DECIDE)
    feedback = connection.execute('SELECT * FROM epi_feedbacks WHERE id = ?', (int(feedback_id),)).fetchone()
    if not feedback:
        raise ValueError('Avaliação não encontrada.')
    fb = row_to_dict(feedback)
    ensure_resource_company(actor, fb, 'Avaliação')
    tech_decision = str(payload.get('tech_decision') or '').strip()
    if tech_decision not in ('aceito', 'recusado'):
        raise ValueError('Decisão técnica obrigatória: aceito ou recusado.')
    atende_nr = str(payload.get('atende_nr') or '').strip()
    reduz_risco = str(payload.get('reduz_risco') or '').strip()
    problemas = payload.get('problemas_observados') or []
    if not isinstance(problemas, list):
        problemas = []
    problemas_json = _json.dumps(problemas, ensure_ascii=False)
    custo_estimado = str(payload.get('custo_estimado') or '').strip()
    durabilidade_esperada = str(payload.get('durabilidade_esperada') or '').strip()
    disponibilidade_mercado = str(payload.get('disponibilidade_mercado') or '').strip()
    admin_tech_notes = str(payload.get('admin_tech_notes') or '').strip()
    marca_modelo = str(payload.get('marca_modelo_sugerido') or '').strip()
    notes = str(payload.get('notes') or '').strip()
    now = datetime.now(UTC).isoformat()
    portal_status = tech_decision
    justification = admin_tech_notes or notes or ''
    if tech_decision == 'aceito':
        portal_message = 'Avaliação técnica concluída — EPI aprovado e registrado.'
        if justification:
            portal_message += f' Justificativa: {justification}'
    else:
        portal_message = 'Avaliação técnica concluída — EPI não aprovado após critérios técnicos.'
        if justification:
            portal_message += f' Justificativa: {justification}'
    connection.execute(
        '''
        UPDATE epi_feedbacks SET
            admin_tech_decision=?, atende_nr=?, reduz_risco=?, problemas_observados=?,
            custo_estimado=?, durabilidade_esperada=?, disponibilidade_mercado=?,
            admin_tech_notes=?, marca_modelo_sugerido=?,
            status=?, employee_portal_status=?, employee_portal_message=?,
            notes=?, updated_at=?, admin_tech_eval_at=?
        WHERE id=?
        ''',
        (tech_decision, atende_nr, reduz_risco, problemas_json,
         custo_estimado, durabilidade_esperada, disponibilidade_mercado,
         admin_tech_notes, marca_modelo,
         tech_decision, portal_status, portal_message,
         notes, now, now, int(feedback_id))
    )
    _record_feedback_history(connection, feedback_id, fb['company_id'],
                             'admin_technical_evaluate', str(fb.get('status') or ''),
                             tech_decision, actor, notes)
    return {'ok': True}


def fetch_avaliacoes_summary(connection, actor):
    ensure_permission(actor, PERM_EPI_EVALUATION_VIEW)
    company_id = int(actor['company_id']) if actor.get('role') != 'master_admin' else None
    where_clauses = []
    params = []
    if company_id:
        where_clauses.append('f.company_id = ?')
        params.append(company_id)
    where_sql = ('WHERE ' + ' AND '.join(where_clauses)) if where_clauses else ''
    rows = connection.execute(
        f'''
        SELECT f.*, e.name as epi_name, emp.name as employee_name, u.name as unit_name
        FROM epi_feedbacks f
        LEFT JOIN epis e ON e.id = f.epi_id
        JOIN employees emp ON emp.id = f.employee_id
        JOIN units u ON u.id = f.unit_id
        {where_sql}
        ORDER BY f.created_at DESC
        ''',
        tuple(params)
    ).fetchall()
    items = [row_to_dict(r) for r in rows]
    reclamacoes = [i for i in items if i.get('feedback_subtype') == 'reclamacao' or i.get('type') == 'reclamacao']
    elogios = [i for i in items if i.get('feedback_subtype') == 'elogio' or i.get('type') == 'elogio']
    sugestoes = [i for i in items if i.get('feedback_subtype') == 'sugestao_nova' or i.get('type') == 'sugestao']
    risk_counts = {}
    for item in reclamacoes:
        rl = str(item.get('risk_level') or 'nenhum')
        risk_counts[rl] = risk_counts.get(rl, 0) + 1
    epi_complaint_counts = {}
    for item in reclamacoes:
        epi = str(item.get('epi_name') or item.get('epi_id') or 'N/A')
        epi_complaint_counts[epi] = epi_complaint_counts.get(epi, 0) + 1
    epi_elogio_counts = {}
    for item in elogios:
        epi = str(item.get('epi_name') or item.get('epi_id') or 'N/A')
        epi_elogio_counts[epi] = epi_elogio_counts.get(epi, 0) + 1
    top_reclamados = sorted(epi_complaint_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    top_elogiados = sorted(epi_elogio_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    role = str(actor.get('role') or '')
    if role in ('general_admin', 'registry_admin'):
        # Admin vê como "pendentes" os itens que aguardam decisão dele
        pendentes_count = len([i for i in items if str(i.get('employee_portal_status') or '') == 'enviado_admin'])
    else:
        # Gestor vê como "pendentes" os itens ainda não triados
        pendentes_count = len([i for i in items if str(i.get('manager_eval_status') or 'pendente') == 'pendente'])
    return {
        'total': len(items),
        'reclamacoes': len(reclamacoes),
        'elogios': len(elogios),
        'sugestoes': len(sugestoes),
        'pendentes': pendentes_count,
        'actor_role': role,
        'risk_breakdown': risk_counts,
        'epi_complaint_counts': epi_complaint_counts,
        'epi_elogio_counts': epi_elogio_counts,
        'top_reclamados': [{'epi_name': k, 'count': v} for k, v in top_reclamados],
        'top_elogiados': [{'epi_name': k, 'count': v} for k, v in top_elogiados],
        'items': items,
        'reclamacao_items': reclamacoes,
        'elogio_items': elogios,
        'sugestao_items': sugestoes,
    }


def fetch_avaliacoes_ranking(connection, actor):
    ensure_permission(actor, PERM_EPI_EVALUATION_VIEW)
    company_id = int(actor['company_id']) if actor.get('role') != 'master_admin' else None
    where_clauses = ['1=1']
    params = []
    if company_id:
        where_clauses.append('s.company_id = ?')
        params.append(company_id)
    where_sql = 'WHERE ' + ' AND '.join(where_clauses)
    rows = connection.execute(
        f'''SELECT s.*, e.ca, e.manufacturer, e.sector
            FROM epi_evaluation_summary s
            JOIN epis e ON e.id = s.epi_id
            {where_sql}
            ORDER BY s.score DESC, s.total_avaliacoes DESC''',
        tuple(params)
    ).fetchall()
    return [row_to_dict(r) for r in rows]


def fetch_suggestion_ranking(connection, actor):
    ensure_permission(actor, PERM_EPI_EVALUATION_VIEW)
    company_id = int(actor['company_id']) if actor.get('role') != 'master_admin' else None
    where_clauses = ["(f.feedback_subtype = 'sugestao_nova' OR f.type = 'sugestao')",
                     "f.epi_rank != ''", "f.manager_eval_status = 'validado'"]
    params = []
    if company_id:
        where_clauses.append('f.company_id = ?')
        params.append(company_id)
    where_sql = 'WHERE ' + ' AND '.join(where_clauses)
    rank_order = ['excelente_sug', 'otima_sug', 'muito_boa_sug', 'pessima_sug', 'muito_ruim_sug', 'ruim_sug']
    rank_score_sql = ' + '.join(
        f"SUM(CASE WHEN f.epi_rank='{r}' THEN {5 - i} ELSE 0 END)"
        for i, r in enumerate(rank_order)
    )
    rows = connection.execute(
        f'''
        SELECT f.suggested_new_epi_name as sugestao_nome,
               f.epi_name as epi_referencia,
               COUNT(*) as total_avaliacoes,
               {rank_score_sql} as score_sugestao,
               SUM(CASE WHEN f.epi_rank='excelente_sug' THEN 1 ELSE 0 END) as rank_excelente_sug,
               SUM(CASE WHEN f.epi_rank='otima_sug' THEN 1 ELSE 0 END) as rank_otima_sug,
               SUM(CASE WHEN f.epi_rank='muito_boa_sug' THEN 1 ELSE 0 END) as rank_muito_boa_sug,
               SUM(CASE WHEN f.epi_rank='pessima_sug' THEN 1 ELSE 0 END) as rank_pessima_sug,
               SUM(CASE WHEN f.epi_rank='muito_ruim_sug' THEN 1 ELSE 0 END) as rank_muito_ruim_sug,
               SUM(CASE WHEN f.epi_rank='ruim_sug' THEN 1 ELSE 0 END) as rank_ruim_sug,
               MIN(f.created_at) as primeira_sugestao,
               MAX(f.employee_portal_status) as portal_status
        FROM epi_feedbacks f
        {where_sql}
        GROUP BY LOWER(TRIM(f.suggested_new_epi_name))
        ORDER BY score_sugestao DESC, total_avaliacoes DESC
        ''',
        tuple(params)
    ).fetchall()
    return [row_to_dict(r) for r in rows]


def compute_alerts(connection, actor=None):
    alerts = []
    today = date.today()
    low_stock_items = fetch_low_stock_items(connection, actor)
    for item in low_stock_items:
        stock = int(item['stock'])
        minimum = int(item['minimum_stock'])
        if stock < 0:
            type_label = 'danger'
            prefix = 'Saldo negativo'
        elif stock == 0:
            type_label = 'danger'
            prefix = 'Estoque zerado'
        elif stock < minimum:
            type_label = 'danger'
            prefix = 'Estoque abaixo do mínimo'
        else:
            type_label = 'warning'
            prefix = 'Estoque no limite mínimo'
        size_balances = item.get('size_balances') or []
        size_parts = []
        for sb in size_balances:
            parts = []
            if sb.get('glove_size') and sb['glove_size'] != 'N/A':
                parts.append(f"Luva:{sb['glove_size']}")
            if sb.get('size') and sb['size'] != 'N/A':
                parts.append(f"Tam:{sb['size']}")
            if sb.get('uniform_size') and sb['uniform_size'] != 'N/A':
                parts.append(f"Unif:{sb['uniform_size']}")
            label = ' '.join(parts) or 'S/Tam'
            size_parts.append(f"{label}×{sb.get('quantity', 0)}")
        size_info = f" | Tamanhos em estoque: {', '.join(size_parts)}" if size_parts else ''
        alerts.append(
            {
                'type': type_label,
                'title': f"{prefix}: {item['epi_name']}",
                'description': f"{item['company_name']} / {item['unit_name']} - saldo atual de {stock} {item['unit_measure']}(s), mínimo {minimum}.{size_info}",
                'company_id': item.get('company_id'),
                'unit_id': item.get('unit_id'),
                'epi_id': item.get('epi_id'),
                'size_balances': size_balances
            }
        )

    scope_unit_id = actor_operational_unit_id(connection, actor)
    for epi in fetch_epis(connection, actor, scope_unit_id):
        if int(epi.get('active', 1) or 0) != 1:
            continue
        ca_expiry = str(epi.get('ca_expiry') or '').strip()
        if not ca_expiry:
            continue
        days = (datetime.strptime(ca_expiry, '%Y-%m-%d').date() - today).days
        if days <= 30:
            alerts.append({
                'type': 'danger' if days <= 7 else 'warning',
                'title': f"CA próximo do vencimento: {epi['name']}",
                'description': f"{epi['company_name']} - vence em {epi['ca_expiry']}.",
                'company_id': epi.get('company_id'),
                'unit_id': epi.get('unit_id'),
                'epi_id': epi.get('id')
            })
    return alerts


def get_user_by_id(connection, user_id):
    row = connection.execute('SELECT users.id, users.username, users.password, users.full_name, users.role, users.company_id, users.active, users.linked_employee_id, users.employee_access_token, users.employee_access_expires_at, companies.name AS company_name, companies.cnpj AS company_cnpj, companies.logo_type FROM users LEFT JOIN companies ON companies.id = users.company_id WHERE users.id = ?', (user_id,)).fetchone()
    if not row:
        return None
    item = row_to_dict(row)
    item['role'] = normalize_role_name(item.get('role'))
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
    requested_unit_id = parse_epi_scope_unit_id(payload.get('unit_id'))
    if requested_unit_id:
        unit = get_unit_by_id(connection, requested_unit_id)
        ensure_resource_company(actor, unit, 'Unidade')
        if int(unit['company_id']) != requested_company_id:
            raise ValueError('Unidade e empresa do EPI precisam ser compatíveis.')
    normalized_active = normalize_active_joinventure_name(active_joinventure)
    if normalized_active:
        matching = [entry for entry in joinventures_values if str(entry['name']).strip().lower() == normalized_active.lower()]
        if not matching:
            raise ValueError('JoinVenture Ativa ou Unidade Única Ativa precisa existir na lista de JoinVentures.')
        unit_ids = sorted({entry.get('unit_id') for entry in matching if entry.get('unit_id')})
        if not unit_ids:
            if requested_unit_id:
                unit_ids = [requested_unit_id]
            else:
                raise ValueError('JoinVenture Ativa ou Unidade Única Ativa precisa possuir unidade vinculada.')
        if len(unit_ids) > 1:
            raise ValueError('JoinVenture Ativa ou Unidade Única Ativa está vinculada a múltiplas unidades. Ajuste o cadastro.')
        required_unit_id = int(unit_ids[0])
        required_unit = get_unit_by_id(connection, required_unit_id)
        ensure_resource_company(actor, required_unit, 'Unidade')
        if int(required_unit['company_id']) != requested_company_id:
            raise ValueError('JoinVenture e empresa do EPI precisam ser compatíveis.')
        if requested_unit_id and requested_unit_id != required_unit_id:
            raise ValueError('Unidade incompatível com a JoinVenture Ativa ou Unidade Única Ativa.')
        return required_unit_id
    return requested_unit_id


def parse_epi_scope_unit_id(raw_unit_value):
    raw_unit = str(raw_unit_value or '').strip()
    if raw_unit in ('', EPI_ALL_UNITS_VALUE):
        return None
    return int(raw_unit)


def resolve_epi_scope_metadata(unit_id, active_joinventure):
    normalized_jv = normalize_active_joinventure_name(active_joinventure)
    if normalized_jv:
        return 'JOINT_VENTURE', 1
    if unit_id:
        return 'UNIT', 0
    return 'GLOBAL', 0


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
    row = connection.execute('SELECT id, company_id, unit_id, employee_id_code, cpf, name, email, whatsapp, preferred_contact_channel, sector, role_name, admission_date, schedule_type, tipo_vinculo, empresa_origem FROM employees WHERE id = ?', (employee_id,)).fetchone()
    return row_to_dict(row) if row else None


def ensure_employee_identity_unique(connection, company_id, employee_id_code, cpf, exclude_id=None):
    try:
        code_row = connection.execute(
            f"SELECT id FROM employees WHERE company_id = ? AND employee_id_code = ? {'AND id <> ?' if exclude_id else ''} LIMIT 1",
            (int(company_id), str(employee_id_code).strip(), int(exclude_id)) if exclude_id else (int(company_id), str(employee_id_code).strip())
        ).fetchone()
    except Exception as _e:
        structured_log('warning', 'db.col_skip', error=str(_e))
    if code_row:
        raise ValueError('ID do colaborador já cadastrado nesta empresa.')
    try:
        cpf_row = connection.execute(
            f"SELECT id FROM employees WHERE company_id = ? AND cpf = ? {'AND id <> ?' if exclude_id else ''} LIMIT 1",
            (int(company_id), normalize_cpf(cpf), int(exclude_id)) if exclude_id else (int(company_id), normalize_cpf(cpf))
        ).fetchone()
    except Exception as _e:
        structured_log('warning', 'db.col_skip', error=str(_e))
    if cpf_row:
        raise ValueError('CPF do colaborador já cadastrado nesta empresa.')


def get_epi_by_id(connection, epi_id):
    row = connection.execute('SELECT id, company_id, unit_id, name, purchase_code, ca, sector, epi_section, stock, minimum_stock, unit_measure, ca_expiry, epi_validity_date, manufacture_date, validity_days, validity_years, validity_months, manufacturer_validity_months, default_replacement_days, manufacturer, model_reference, supplier_company, manufacturer_recommendations, epi_photo_data, glove_size, size, uniform_size, joinventures_json, active_joinventure, scope_type, is_joint_venture, qr_code_value FROM epis WHERE id = ?', (epi_id,)).fetchone()
    return row_to_dict(row) if row else None


def require_actor(connection, actor_user_id):
    actor = get_user_by_id(connection, int(actor_user_id))
    if not actor or not int(actor['active']):
        raise PermissionError('Usuário executor inválido.')
    actor['role'] = normalize_role_name(actor.get('role'))
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


def require_structural_admin(actor):
    if actor.get('role') not in ('general_admin', 'registry_admin'):
        raise PermissionError('Apenas Administrador Geral e Administrador de Registro podem executar esta ação estrutural.')

def require_configuration_admin(actor):
    if actor.get('role') not in ('master_admin', 'general_admin', 'registry_admin'):
        raise PermissionError('Apenas Administrador Master, Administrador Geral e Administrador de Registro podem acessar Configuração.')


def require_master_admin(actor, message='Apenas Administrador Master pode executar esta ação.'):
    if actor.get('role') != 'master_admin':
        raise PermissionError(message)


def delete_epi_dependencies(connection, epi_id):
    epi_id = int(epi_id)
    connection.execute('DELETE FROM epi_stock_item_reprints WHERE stock_item_id IN (SELECT id FROM epi_stock_items WHERE epi_id = ?)', (epi_id,))
    connection.execute('DELETE FROM epi_stock_items WHERE epi_id = ?', (epi_id,))
    connection.execute('DELETE FROM stock_movements WHERE epi_id = ?', (epi_id,))
    connection.execute('DELETE FROM unit_epi_stock WHERE epi_id = ?', (epi_id,))
    connection.execute('DELETE FROM epi_ficha_items WHERE epi_id = ?', (epi_id,))
    connection.execute('DELETE FROM deliveries WHERE epi_id = ?', (epi_id,))
    request_ids = [int(row['id']) for row in connection.execute('SELECT id FROM epi_requests WHERE epi_id = ?', (epi_id,)).fetchall()]
    if request_ids:
        connection.execute(f"DELETE FROM epi_request_history WHERE request_id IN ({','.join(['?'] * len(request_ids))})", tuple(request_ids))
    connection.execute('DELETE FROM epi_requests WHERE epi_id = ?', (epi_id,))
    feedback_ids = [int(row['id']) for row in connection.execute('SELECT id FROM epi_feedbacks WHERE epi_id = ?', (epi_id,)).fetchall()]
    if feedback_ids:
        connection.execute(f"DELETE FROM epi_feedback_history WHERE feedback_id IN ({','.join(['?'] * len(feedback_ids))})", tuple(feedback_ids))
    connection.execute('DELETE FROM epi_feedbacks WHERE epi_id = ?', (epi_id,))
    connection.execute('DELETE FROM epis WHERE id = ?', (epi_id,))


def delete_unit_dependencies(connection, unit_id):
    unit_id = int(unit_id)
    scoped_epi_ids = [int(row['id']) for row in connection.execute('SELECT id FROM epis WHERE unit_id = ?', (unit_id,)).fetchall()]
    for epi_id in scoped_epi_ids:
        delete_epi_dependencies(connection, epi_id)
    connection.execute('DELETE FROM epi_stock_item_reprints WHERE stock_item_id IN (SELECT id FROM epi_stock_items WHERE unit_id = ?)', (unit_id,))
    connection.execute('DELETE FROM epi_stock_items WHERE unit_id = ?', (unit_id,))
    connection.execute('DELETE FROM stock_movements WHERE unit_id = ?', (unit_id,))
    connection.execute('DELETE FROM unit_epi_stock WHERE unit_id = ?', (unit_id,))
    request_ids = [int(row['id']) for row in connection.execute('SELECT id FROM epi_requests WHERE unit_id = ?', (unit_id,)).fetchall()]
    if request_ids:
        connection.execute(f"DELETE FROM epi_request_history WHERE request_id IN ({','.join(['?'] * len(request_ids))})", tuple(request_ids))
    connection.execute('DELETE FROM epi_requests WHERE unit_id = ?', (unit_id,))
    ficha_item_ids = [int(row['id']) for row in connection.execute('SELECT id FROM epi_ficha_items WHERE unit_id = ?', (unit_id,)).fetchall()]
    if ficha_item_ids:
        connection.execute('DELETE FROM epi_ficha_items WHERE unit_id = ?', (unit_id,))
    connection.execute('DELETE FROM epi_ficha_periods WHERE unit_id = ?', (unit_id,))
    feedback_ids = [int(row['id']) for row in connection.execute('SELECT id FROM epi_feedbacks WHERE unit_id = ?', (unit_id,)).fetchall()]
    if feedback_ids:
        connection.execute(f"DELETE FROM epi_feedback_history WHERE feedback_id IN ({','.join(['?'] * len(feedback_ids))})", tuple(feedback_ids))
    connection.execute('DELETE FROM epi_feedbacks WHERE unit_id = ?', (unit_id,))
    connection.execute('DELETE FROM deliveries WHERE unit_id = ?', (unit_id,))
    connection.execute('DELETE FROM employee_unit_movements WHERE source_unit_id = ? OR target_unit_id = ?', (unit_id, unit_id))
    employee_ids = [int(row['id']) for row in connection.execute('SELECT id FROM employees WHERE unit_id = ?', (unit_id,)).fetchall()]
    if employee_ids:
        connection.execute(f"DELETE FROM employee_portal_audit WHERE employee_id IN ({','.join(['?'] * len(employee_ids))})", tuple(employee_ids))
        connection.execute(f"DELETE FROM employee_portal_links WHERE employee_id IN ({','.join(['?'] * len(employee_ids))})", tuple(employee_ids))
        connection.execute(f"DELETE FROM users WHERE linked_employee_id IN ({','.join(['?'] * len(employee_ids))})", tuple(employee_ids))
        connection.execute(f"DELETE FROM employees WHERE id IN ({','.join(['?'] * len(employee_ids))})", tuple(employee_ids))


def authorize_user_management(connection, actor_user_id, operation='create', target_role=None, target_user_id=None, target_company_id=None):
    action = {'create': 'users:create', 'update': 'users:update', 'delete': 'users:delete'}[operation]
    actor = authorize_action(connection, actor_user_id, action)
    target_role = normalize_role_name(target_role)
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
        if target_role and target_role not in ('registry_admin', 'admin', 'user', 'employee', 'buyer', 'approver'):
            raise ValueError('Perfil pode gerenciar apenas Administrador de Registro, Administrador Local, Comprador, Aprovador, Gestor de EPI e Funcionário da própria empresa.')
        if target:
            if target['role'] not in ('registry_admin', 'admin', 'user', 'employee', 'buyer', 'approver'):
                raise ValueError('Perfil pode alterar apenas Administrador de Registro, Administrador Local, Comprador, Aprovador, Gestor de EPI e Funcionário.')
            ensure_company_access(actor, target.get('company_id'))
        if target_company_id:
            ensure_company_access(actor, target_company_id)
        return actor

    if actor['role'] == 'admin':
        raise PermissionError('Administrador Local não pode cadastrar/editar usuários da base principal.')

    raise PermissionError('Somente perfis administrativos podem gerenciar usuários.')

def resolve_target_company_id(actor, payload_company_id, payload_role, linked_employee_id=None):
    role = normalize_role_name(payload_role)
    company_id = payload_company_id
    if actor['role'] in ('general_admin', 'registry_admin', 'admin') and not company_id:
        company_id = actor.get('company_id')
    has_linked_employee = linked_employee_id not in (None, '', 'null')
    if role in BILLABLE_ROLES and not company_id and not has_linked_employee:
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
        raise ValueError('Empresa obrigatória para criar colaborador Sem vínculo.')

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


class InvalidQueryParamError(ValueError):
    def __init__(self, field_name, message, value):
        super().__init__(message)
        self.field_name = field_name
        self.value = value


def normalize_item_size_value(value):
    normalized = str(value or '').strip()
    if not normalized:
        return ''
    lowered = normalized.lower()
    if lowered in {'n/a', 'na', 'selecione', 'selecione o tamanho', 'null', 'undefined'}:
        return ''
    return normalized


def resolve_item_size(glove_size, size, uniform_size):
    normalized_glove = normalize_item_size_value(glove_size)
    normalized_size = normalize_item_size_value(size)
    normalized_uniform = normalize_item_size_value(uniform_size)
    selected_size = normalized_glove or normalized_size or normalized_uniform or ''
    return {
        'selected_size': selected_size,
        'glove_size': normalized_glove or 'N/A',
        'size': selected_size or 'N/A',
        'uniform_size': normalized_uniform or 'N/A',
    }


def resolve_effective_size_fields(primary, fallback=None, *, fallback_prefix=''):
    primary = primary or {}
    fallback = fallback or {}
    primary_glove = normalize_item_size_value(primary.get('glove_size'))
    primary_size = normalize_item_size_value(primary.get('size'))
    primary_uniform = normalize_item_size_value(primary.get('uniform_size'))
    fallback_glove = normalize_item_size_value(fallback.get(f'{fallback_prefix}glove_size'))
    fallback_size = normalize_item_size_value(fallback.get(f'{fallback_prefix}size'))
    fallback_uniform = normalize_item_size_value(fallback.get(f'{fallback_prefix}uniform_size'))
    selected_size = primary_glove or primary_size or primary_uniform or fallback_glove or fallback_size or fallback_uniform or ''
    return {
        'selected_size': selected_size,
        'glove_size': primary_glove or fallback_glove or 'N/A',
        'size': primary_size or fallback_size or selected_size or 'N/A',
        'uniform_size': primary_uniform or fallback_uniform or 'N/A',
    }


def apply_effective_size_fields(target, primary, fallback=None, *, fallback_prefix=''):
    effective_size = resolve_effective_size_fields(primary, fallback, fallback_prefix=fallback_prefix)
    target['glove_size'] = effective_size['glove_size']
    target['size'] = effective_size['size']
    target['uniform_size'] = effective_size['uniform_size']
    return target


def normalize_report_filters(raw_filters):
    raw_filters = raw_filters or {}

    def parse_optional_int(field_name):
        raw_value = str(raw_filters.get(field_name, '') or '').strip()
        if not raw_value:
            return ''
        try:
            return int(raw_value)
        except ValueError as exc:
            raise InvalidQueryParamError(field_name, f'Filtro inválido: {field_name} deve ser numérico.', raw_value) from exc
            raise ValueError(f'Filtro inválido: {field_name} deve ser numérico.') from exc


    def parse_optional_date(field_name):
        raw_value = str(raw_filters.get(field_name, '') or '').strip()
        if not raw_value:
            return ''
        try:
            datetime.strptime(raw_value, '%Y-%m-%d')
        except ValueError as exc:
            raise InvalidQueryParamError(field_name, f'Filtro inválido: {field_name} deve estar no formato YYYY-MM-DD.', raw_value) from exc
            raise ValueError(f'Filtro inválido: {field_name} deve estar no formato YYYY-MM-DD.') from exc
        return raw_value

    return {
        'company_id': parse_optional_int('company_id'),
        'unit_id': parse_optional_int('unit_id'),
        'employee_id': parse_optional_int('employee_id'),
        'epi_id': parse_optional_int('epi_id'),
        'sector': str(raw_filters.get('sector', '') or '').strip(),
        'start_date': parse_optional_date('start_date'),
        'end_date': parse_optional_date('end_date'),
        'archive_status': str(raw_filters.get('archive_status', raw_filters.get('status', '')) or '').strip().lower(),
    }


def build_reports(connection, actor, filters):
    filters = normalize_report_filters(filters)
    clauses, params = [], []
    scope_unit_id = actor_operational_unit_id(connection, actor)
    if actor.get('role') in ('admin', 'user') and not scope_unit_id:
        raise PermissionError('Perfil sem unidade operacional ativa para consultar relatórios.')
    selected_company_id = filters.get('company_id')
    if selected_company_id:
        ensure_company_access(actor, int(selected_company_id))
        clauses.append('deliveries.company_id = ?')
        params.append(int(selected_company_id))
    elif actor['role'] != 'master_admin':
        clauses.append('deliveries.company_id = ?')
        params.append(actor['company_id'])
    raw_unit_id = str(filters.get('unit_id') or '').strip()
    if scope_unit_id:
        if raw_unit_id and int(raw_unit_id) != int(scope_unit_id):
            raise PermissionError('Operação permitida somente para sua unidade operacional.')
        clauses.append('deliveries.unit_id = ?')
        params.append(scope_unit_id)
    if filters.get('unit_id'):
        if not scope_unit_id:
            unit = get_unit_by_id(connection, int(filters['unit_id']))
            ensure_resource_company(actor, unit, 'Unidade')
            clauses.append('deliveries.unit_id = ?')
            params.append(int(filters['unit_id']))
    employee_id = str(filters.get('employee_id') or '').strip()
    employee = None
    if employee_id:
        employee = get_employee_by_id(connection, int(employee_id))
        ensure_resource_company(actor, employee, 'Colaborador')
        if scope_unit_id:
            ensure_actor_employee_scope(connection, actor, employee)
        clauses.append('deliveries.employee_id = ?')
        params.append(int(employee_id))
    if filters.get('sector'):
        clauses.append('deliveries.sector = ?')
        params.append(filters['sector'])
    if filters.get('tipo_vinculo'):
        clauses.append('employees.tipo_vinculo = ?')
        params.append(filters['tipo_vinculo'])
    if filters.get('epi_id'):
        epi = get_epi_by_id(connection, int(filters['epi_id']))
        ensure_resource_company(actor, epi, 'EPI')
        clauses.append('deliveries.epi_id = ?')
        params.append(int(filters['epi_id']))
    if filters.get('start_date'):
        clauses.append('deliveries.delivery_date >= ?')
        params.append(filters['start_date'])
    if filters.get('end_date'):
        clauses.append('deliveries.delivery_date <= ?')
        params.append(filters['end_date'])
    where_clause = f"WHERE {' AND '.join(clauses)}" if clauses else ''
    # IMPORTANTE: os filtros de relatório já aplicam escopo/empresa/unidade acima.
    # Não reenviar o actor para fetch_deliveries evita duplicar cláusulas de empresa
    # e deslocar a ordem dos parâmetros vinculados no SQL (ex.: data em campo inteiro).
    deliveries = fetch_deliveries(connection, None, where_clause, tuple(params))
    by_unit, by_sector, by_epi, by_tipo_vinculo = {}, {}, {}, {}
    for item in deliveries:
        by_unit[item['unit_name']] = by_unit.get(item['unit_name'], 0) + int(item['quantity'])
        by_sector[item['sector']] = by_sector.get(item['sector'], 0) + int(item['quantity'])
        by_epi[item['epi_name']] = by_epi.get(item['epi_name'], 0) + int(item['quantity'])
        tv = str(item.get('tipo_vinculo') or 'CLT')
        by_tipo_vinculo[tv] = by_tipo_vinculo.get(tv, 0) + int(item['quantity'])
    employee_fichas = []
    if employee:
        ficha_clauses = ['fp.employee_id = ?']
        ficha_params = [int(employee_id)]
        if actor['role'] != 'master_admin':
            ficha_clauses.append('fp.company_id = ?')
            ficha_params.append(actor['company_id'])
        if scope_unit_id:
            ficha_clauses.append('fp.unit_id = ?')
            ficha_params.append(int(scope_unit_id))
        ficha_where = f"WHERE {' AND '.join(ficha_clauses)}"
        ficha_rows = connection.execute(
            (
                'SELECT fp.id, fp.period_start, fp.period_end, fp.status, fp.company_id, fp.unit_id, '
                'employees.name AS employee_name, employees.employee_id_code, units.name AS unit_name '
                'FROM epi_ficha_periods fp '
                'JOIN employees ON employees.id = fp.employee_id '
                'JOIN units ON units.id = fp.unit_id '
                f'{ficha_where} '
                'ORDER BY fp.period_start DESC, fp.id DESC'
            ),
            tuple(ficha_params)
        ).fetchall()
        for row in ficha_rows:
            parsed = row_to_dict(row)
            totals = connection.execute(
                'SELECT COUNT(*) AS total_items, COALESCE(SUM(quantity), 0) AS total_quantity FROM epi_ficha_items WHERE ficha_period_id = ?',
                (int(parsed['id']),)
            ).fetchone()
            totals_data = row_to_dict(totals) if totals else {}
            parsed['total_items'] = int(totals_data.get('total_items') or 0)
            parsed['total_quantity'] = int(totals_data.get('total_quantity') or 0)
            employee_fichas.append(parsed)
    return {
        'deliveries': deliveries,
        'by_unit': by_unit,
        'by_sector': by_sector,
        'by_epi': by_epi,
        'by_tipo_vinculo': by_tipo_vinculo,
        'total_quantity': sum(int(item['quantity']) for item in deliveries),
        'employee_fichas': employee_fichas
    }


def _bootstrap_error_summary(exc):
    stack_lines = traceback.format_exception(type(exc), exc, exc.__traceback__, limit=4)
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
    warnings = []

    permissions = sorted(PERMISSIONS.get(actor['role'], set()))

    units = _safe_bootstrap_section('units', lambda: fetch_units(connection, actor), [], warnings, actor)
    employees = _safe_bootstrap_section('employees', lambda: fetch_employees(connection, actor), [], warnings, actor)
    epis = _safe_bootstrap_section('epis', lambda: fetch_epis(connection, actor), [], warnings, actor)

    # Canary/shadow execution (non-invasive): always return legacy results.
    units = _safe_bootstrap_section(
        'units_visibility_canary',
        lambda: canary_evaluate_visibility_dataset(connection, actor, endpoint_name='/api/bootstrap', dataset_name='units', legacy_items=units),
        units,
        warnings,
        actor,
    )
    employees = _safe_bootstrap_section(
        'employees_visibility_canary',
        lambda: canary_evaluate_visibility_dataset(connection, actor, endpoint_name='/api/bootstrap', dataset_name='employees', legacy_items=employees),
        employees,
        warnings,
        actor,
    )
    epis = _safe_bootstrap_section(
        'epis_visibility_canary',
        lambda: canary_evaluate_visibility_dataset(connection, actor, endpoint_name='/api/bootstrap', dataset_name='epis', legacy_items=epis),
        epis,
        warnings,
        actor,
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
            None,
            warnings,
            actor,
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


def fetch_low_stock_items(connection, actor=None):
    items = []
    clauses = ['COALESCE(epis.active, 1) = 1']
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
        SELECT
               s.company_id, s.unit_id, s.epi_id,
               COALESCE(SUM(s.quantity), 0) AS stock,
               MAX(units.name) AS unit_name,
               MAX(companies.name) AS company_name,
               MAX(epis.name) AS epi_name,
               MAX(epis.minimum_stock) AS minimum_stock,
               MAX(epis.unit_measure) AS unit_measure,
               MAX(epis.unit_id) AS epi_unit_id,
               MAX(epis.active_joinventure) AS epi_active_joinventure
        FROM unit_epi_stock s
        JOIN units ON units.id = s.unit_id
        JOIN companies ON companies.id = s.company_id
        JOIN epis ON epis.id = s.epi_id
        {scope_clause}
        GROUP BY s.company_id, s.unit_id, s.epi_id
        ''',
        tuple(params)
    ).fetchall()
    unit_jv_cache = {}
    for row in rows:
        row = row_to_dict(row)
        target_unit_id = int(row['unit_id'] or 0)
        if target_unit_id not in unit_jv_cache:
            unit_jv_cache[target_unit_id] = get_unit_active_jv_name(connection, target_unit_id)
        if not is_epi_visible_for_unit(
            epi_unit_id=row['epi_unit_id'],
            epi_joint_venture_name=row['epi_active_joinventure'],
            target_unit_id=target_unit_id,
            target_unit_joint_venture_name=unit_jv_cache[target_unit_id],
        ):
            continue
        stock = int(row['stock'] or 0)
        minimum = int(row['minimum_stock']) if row['minimum_stock'] is not None else 10
        if stock <= minimum:
            size_balances = fetch_epi_size_balance(connection, int(row['company_id']), int(row['unit_id']), int(row['epi_id']))
            items.append({
                'epi_id': row['epi_id'],
                'epi_name': row['epi_name'],
                'company_id': row['company_id'],
                'company_name': row['company_name'],
                'unit_id': row['unit_id'],
                'unit_name': row.get('unit_name') or '-',
                'stock': stock,
                'minimum_stock': minimum,
                'unit_measure': row.get('unit_measure') or 'unidade',
                'severity': 'critical' if stock <= 0 else ('danger' if stock < minimum else 'warning'),
                'size_balances': size_balances
            })
    items.sort(key=lambda row: (row['company_name'], row['unit_name'], row['epi_name']))
    return items


def build_low_stock(connection, actor):
    items = fetch_low_stock_items(connection, actor)
    return {'items': items}


def auth_diagnostics():
    parsed_db = urlparse(DATABASE_URL) if DATABASE_URL else None
    host = parsed_db.hostname if parsed_db else ''
    migration_state = _get_migration_runtime_state()
    migration_state_public = {
        'status': migration_state.get('status', 'not_started'),
        'failed_migration': migration_state.get('failed_migration', ''),
        'applied_count': len(migration_state.get('applied') or []),
    }
    return {
        'database_configured': bool(DATABASE_URL),
        'database_host': host,
        'database_provider': 'supabase' if 'supabase' in str(host).lower() else 'custom_postgres',
        'db_connector_available': DB_CONNECTOR_AVAILABLE,
        'bcrypt_available': BCRYPT_AVAILABLE,
        'jwt_exp_seconds': JWT_EXP_SECONDS,
        'jwt_secret_default': JWT_SECRET == 'change-this-jwt-secret',
        'password_recovery_key_configured': bool(PASSWORD_RECOVERY_KEY),
        'migration_runner': migration_state_public,
    }


def static_asset_diagnostics():
    index_path = BASE_DIR / 'index.html'
    app_path = BASE_DIR / 'app.js'

    def digest(path):
        if not path.exists():
            return ''
        return hashlib.sha256(path.read_bytes()).hexdigest()

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


# ═══════════════════════════════════════════════════════
# FICHA DE EPI — configuracao e geracao de PDF
# ═══════════════════════════════════════════════════════

DEFAULT_FICHA_TITULO = 'FICHA INDIVIDUAL DE CONTROLE DE EPI (Equipamento de Proteção Individual) E UNIFORMES'
DEFAULT_FICHA_DECLARACAO = (
    'Declaro que recebi os EPIs e uniformes abaixo discriminados, gratuitamente, para uso individual '
    'durante a jornada de trabalho, pelos quais fico responsável pela guarda e conservação, devendo '
    'devolvê-los quando houver alteração que os torne impróprios para uso ou na rescisão do contrato '
    'de trabalho.\nDeclaro ainda que fui treinado no procedimento de Uso Correto e Cuidados com os EPI.\n'
    'Estou ciente de que estarei sujeito a desconto em folha ou na rescisão se eventualmente vier a '
    'provocar danos, modificar ou extraviar os EPIs e de que a recusa injustificada em usar os EPIs '
    'ora fornecidos pela empresa constitui ato faltoso, podendo sofrer as penalidades previstas na Lei.'
)
DEFAULT_FICHA_OBSERVACOES = (
    'OBS.: Cada EPI tem um prazo de validade que se encontra na embalagem, assim como a vida Útil do '
    'mesmo que pode ser encontrado no próprio EPI ou na embalagem.'
)
DEFAULT_FICHA_RASTREABILIDADE = 'Ficha Individual de Controle de EPI - Ver. 01'


def get_ficha_config(connection, company_id):
    """Retorna configuracao da ficha de EPI da empresa ou defaults."""
    normalized_company_id = None if company_id in (None, '', 'null') else int(company_id)
    if normalized_company_id is None:
        return {
            'titulo': DEFAULT_FICHA_TITULO,
            'declaracao': DEFAULT_FICHA_DECLARACAO,
            'observacoes': DEFAULT_FICHA_OBSERVACOES,
            'rastreabilidade': DEFAULT_FICHA_RASTREABILIDADE,
        }
    try:
        row = connection.execute(
            'SELECT titulo, declaracao, observacoes, rastreabilidade FROM ficha_epi_config WHERE company_id = ?',
            (normalized_company_id,)
        ).fetchone()
        if row:
            return {
                'titulo': row['titulo'] or DEFAULT_FICHA_TITULO,
                'declaracao': row['declaracao'] or DEFAULT_FICHA_DECLARACAO,
                'observacoes': row['observacoes'] or DEFAULT_FICHA_OBSERVACOES,
                'rastreabilidade': row['rastreabilidade'] or DEFAULT_FICHA_RASTREABILIDADE,
            }
    except Exception as _e:
        structured_log('warning', 'ficha.config_load_error', error=str(_e))
    return {
        'titulo': DEFAULT_FICHA_TITULO,
        'declaracao': DEFAULT_FICHA_DECLARACAO,
        'observacoes': DEFAULT_FICHA_OBSERVACOES,
        'rastreabilidade': DEFAULT_FICHA_RASTREABILIDADE,
    }


def save_ficha_config(connection, company_id, payload):
    """Salva ou atualiza configuracao da ficha de EPI da empresa."""
    normalized_company_id = None if company_id in (None, '', 'null') else int(company_id)
    if normalized_company_id is None:
        raise ValueError('Configuração da ficha exige empresa vinculada.')
    now = datetime.now(UTC).isoformat()
    titulo = str(payload.get('titulo') or DEFAULT_FICHA_TITULO).strip()
    declaracao = str(payload.get('declaracao') or DEFAULT_FICHA_DECLARACAO).strip()
    observacoes = str(payload.get('observacoes') or DEFAULT_FICHA_OBSERVACOES).strip()
    rastreabilidade = str(payload.get('rastreabilidade') or DEFAULT_FICHA_RASTREABILIDADE).strip()
    existing = connection.execute(
        'SELECT id FROM ficha_epi_config WHERE company_id = ?',
        (normalized_company_id,)
    ).fetchone()
    if existing:
        connection.execute(
            'UPDATE ficha_epi_config SET titulo=?, declaracao=?, observacoes=?, rastreabilidade=?, updated_at=? WHERE company_id=?',
            (titulo, declaracao, observacoes, rastreabilidade, now, normalized_company_id)
        )
    else:
        connection.execute(
            'INSERT INTO ficha_epi_config (company_id, titulo, declaracao, observacoes, rastreabilidade, created_at, updated_at) VALUES (?,?,?,?,?,?,?)',
            (normalized_company_id, titulo, declaracao, observacoes, rastreabilidade, now, now)
        )
    connection.commit()


def _configuration_scope_key(company_id):
    if company_id in (None, '', 'null'):
        return 'global'
    return str(int(company_id))


def _configuration_scope_unit_ids(connection, company_id):
    if company_id in (None, '', 'null'):
        return set()
    normalized_company_id = int(company_id)
    return {
        int(row['id'])
        for row in connection.execute(
            'SELECT id FROM units WHERE company_id = ?',
            (normalized_company_id,)
        ).fetchall()
    }


def get_configuration_rules(connection, company_id):
    default_rules = []
    scope_key = _configuration_scope_key(company_id)
    raw = get_meta(connection, f'configuration_rules:{scope_key}')
    if not raw:
        return default_rules
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return parsed
    except Exception as _e:
        structured_log('warning', 'configuration.rules_load_error', error=str(_e), scope_key=scope_key)
    return default_rules


def get_configuration_framework(connection, company_id):
    scope_key = _configuration_scope_key(company_id)
    raw = get_meta(connection, f'configuration_framework:{scope_key}')
    payload = {}
    if raw:
        try:
            payload = json.loads(raw)
        except Exception as _e:
            structured_log('warning', 'configuration.framework_load_error', error=str(_e), scope_key=scope_key)
    normalized = normalize_framework_payload(payload)
    if not normalized.get('visibility_rules'):
        normalized['visibility_rules'] = get_configuration_rules(connection, company_id)
    return normalized


def save_configuration_framework(connection, company_id, payload):
    scope_key = _configuration_scope_key(company_id)
    normalized = normalize_framework_payload(payload if isinstance(payload, dict) else {})
    valid_unit_ids = _configuration_scope_unit_ids(connection, company_id)
    valid_roles = {'user', 'employee'}
    cleaned_rules = []
    for rule in normalized.get('visibility_rules', []):
        role = str(rule.get('role') or '').strip()
        unit_id = int(rule.get('unit_id') or 0)
        if role not in valid_roles:
            continue
        if unit_id and unit_id not in valid_unit_ids:
            continue
        cleaned_rules.append(rule)
    normalized['visibility_rules'] = cleaned_rules
    set_meta(connection, f'configuration_framework:{scope_key}', json.dumps(normalized, ensure_ascii=False))
    set_meta(connection, f'configuration_rules:{scope_key}', json.dumps(cleaned_rules, ensure_ascii=False))
    connection.commit()
    return normalized


def save_configuration_rules(connection, company_id, rules):
    sanitized = []
    scope_key = _configuration_scope_key(company_id)
    valid_roles = {'user', 'employee'}
    valid_unit_ids = _configuration_scope_unit_ids(connection, company_id)
    for item in rules or []:
        if not isinstance(item, dict):
            continue
        unit_id = int(item.get('unit_id') or 0)
        if unit_id and unit_id not in valid_unit_ids:
            structured_log(
                'warning',
                'configuration.rules_invalid_unit_fallback',
                scope_key=scope_key,
                unit_id=unit_id,
                rule_id=str(item.get('id') or ''),
            )
            continue
        role = str(item.get('role') or '').strip()
        if role not in valid_roles:
            structured_log(
                'warning',
                'configuration.rules_invalid_role_fallback',
                scope_key=scope_key,
                role=role,
                rule_id=str(item.get('id') or ''),
            )
            continue
        sanitized.append({
            'id': str(item.get('id') or secrets.token_hex(6)),
            'role': role,
            'unit_id': unit_id,
            'unit_context': 'inside_jv' if str(item.get('unit_context') or '') == 'inside_jv' else 'outside_jv',
            'can_view_unit': bool(item.get('can_view_unit')),
            'can_view_epis': bool(item.get('can_view_epis')),
            'can_view_employees': bool(item.get('can_view_employees')),
        })
    set_meta(connection, f'configuration_rules:{scope_key}', json.dumps(sanitized, ensure_ascii=False))
    framework = get_configuration_framework(connection, company_id)
    framework['visibility_rules'] = sanitized
    set_meta(connection, f'configuration_framework:{scope_key}', json.dumps(framework, ensure_ascii=False))
    connection.commit()
    return sanitized


def canary_evaluate_visibility_dataset(connection, actor, *, endpoint_name, dataset_name, legacy_items):
    """Run legacy/new engine in parallel and always return legacy items.

    This function is intentionally non-invasive and keeps legacy as source of truth.
    """
    try:
        framework = get_configuration_framework(connection, actor['company_id'])
        context = build_rule_context(actor, endpoint=endpoint_name)
        plan = resolve_execution_plan(context, framework)
        if not plan.get('evaluate_in_background'):
            return legacy_items

        def item_unit_id(item):
            return int(
                item.get('unit_id')
                or item.get('current_unit_id')
                or 0
            )

        def item_context(item):
            return 'inside_jv' if str(item.get('active_joinventure') or '').strip() else 'outside_jv'

        candidate_items = []
        for item in legacy_items:
            item_ctx = build_rule_context(
                actor,
                endpoint=endpoint_name,
                unit_id=item_unit_id(item) or None,
                jv_context=item_context(item),
            )
            visibility = resolve_visibility_filters(item_ctx, framework)
            if dataset_name == 'units' and visibility.get('allow_unit', True):
                candidate_items.append(item)
            elif dataset_name == 'employees' and visibility.get('allow_employees', True):
                candidate_items.append(item)
            elif dataset_name == 'epis' and visibility.get('allow_epis', True):
                candidate_items.append(item)
            elif dataset_name not in ('units', 'employees', 'epis'):
                candidate_items.append(item)

        legacy_ids = [str(item.get('id') or item.get('employee_id_code') or '') for item in legacy_items]
        candidate_ids = [str(item.get('id') or item.get('employee_id_code') or '') for item in candidate_items]
        diff = compute_visibility_diff(legacy_ids, candidate_ids)

        log_payload = {
            'company_id': int(actor.get('company_id') or 0),
            'user_id': int(actor.get('id') or 0),
            'role': str(actor.get('role') or ''),
            'endpoint': endpoint_name,
            'dataset': dataset_name,
            'mode': plan.get('mode'),
            'legacy_count': len(legacy_items),
            'new_count': len(candidate_items),
            'diff': diff,
        }
        if diff.get('has_diff'):
            structured_log('warning', 'rules_engine.shadow_diff_detected', **log_payload)
        else:
            structured_log('info', 'rules_engine.shadow_diff_none', **log_payload)
    except Exception as exc:
        structured_log(
            'warning',
            'rules_engine.shadow_failed_fallback_legacy',
            company_id=int(actor.get('company_id') or 0),
            user_id=int(actor.get('id') or 0),
            role=str(actor.get('role') or ''),
            endpoint=endpoint_name,
            dataset=dataset_name,
            error=str(exc),
        )
    return legacy_items


def render_ficha_epi_html_document(*, employee, company, unit, deliveries, devolutions, config, period_label=''):
    """Renderiza o HTML da ficha com dados já resolvidos (sem consultas implícitas)."""
    logo_data = str(company.get('logo_type') or '')
    rows_html = ''
    for item in deliveries:
        sig_html = ''
        if item.get('signature_data') and str(item['signature_data']).startswith('data:image'):
            sig_html = f'<img src="{item["signature_data"]}" style="max-height:28px;max-width:80px;">'
        qty = str(item.get('quantity') or 1)
        unid = str(item.get('unit_measure') or 'UNIDADE').upper()
        epi_name = str(item.get('epi_name') or '')
        ca = str(item.get('ca') or '')
        fab = str(item.get('manufacture_date') or '')
        validade = str(item.get('next_replacement_date') or item.get('epi_validity_date') or '')
        recebido = str(item.get('delivery_date') or '')
        devolvido = str(item.get('returned_date') or '')
        rows_html += f"""
        <tr>
          <td style="text-align:center">{qty}</td>
          <td style="text-align:center">{unid}</td>
          <td>{epi_name}</td>
          <td style="text-align:center">{ca}</td>
          <td style="text-align:center">{fab}</td>
          <td style="text-align:center">{validade}</td>
          <td style="text-align:center">{recebido}</td>
          <td style="text-align:center">{devolvido}</td>
          <td style="text-align:center">{sig_html}</td>
        </tr>"""

    for _ in range(max(0, 20 - len(deliveries))):
        rows_html += """
        <tr>
          <td>&nbsp;</td><td></td><td></td><td></td>
          <td></td><td></td><td></td><td></td><td></td>
        </tr>"""

    if logo_data.startswith('data:image'):
        logo_html = f'<img src="{logo_data}" style="max-height:60px;max-width:180px;">'
    else:
        logo_html = f'<div style="font-size:18px;font-weight:bold;">{company.get("name","")}</div>'

    declaracao_html = str(config.get('declaracao', '')).replace('\n', '<br>')
    observacoes_html = str(config.get('observacoes', '')).replace('\n', '<br>')
    unit_name = str(unit.get('name') or '')

    condition_labels = {
        'usable': 'Reutilizável', 'damaged': 'Danificado', 'discarded': 'Descartado',
        'maintenance': 'Em manutenção', 'quarantine': 'Em quarentena', 'hygiene': 'Para higienização'
    }
    destination_labels = {
        'stock': 'Retornou ao estoque', 'discard': 'Descartado',
        'maintenance': 'Manutenção', 'hygiene': 'Higienização', 'quarantine': 'Quarentena'
    }
    devol_rows_html = ''
    for dv in devolutions:
        devol_rows_html += (
            f'<tr>'
            f'<td>{dv.get("epi_name","")}</td>'
            f'<td style="text-align:center">{dv.get("qty_entregue","")}</td>'
            f'<td style="text-align:center">{dv.get("delivery_date","")}</td>'
            f'<td style="text-align:center">{dv.get("returned_date","")}</td>'
            f'<td style="text-align:center">{condition_labels.get(dv.get("condition",""),dv.get("condition",""))}</td>'
            f'<td style="text-align:center">{destination_labels.get(dv.get("destination",""),dv.get("destination",""))}</td>'
            f'<td style="text-align:center">{dv.get("received_by_name","")}</td>'
            f'<td style="text-align:center">{dv.get("signature_name","") or ("Pendente no fechamento" if not dv.get("signature_at","") else "")}</td>'
            f'<td>{dv.get("reason","") or dv.get("notes","")}</td>'
            f'</tr>'
        )

    devol_section_html = ''
    if devolutions:
        devol_section_html = f"""
        <div class="secao" style="margin-top:24px">
          <h3 style="font-size:11pt;font-weight:bold;border-bottom:2px solid #333;padding-bottom:4px;margin-bottom:8px">
            Histórico de Devoluções de EPI
          </h3>
          <table style="width:100%;border-collapse:collapse;font-size:9pt">
            <thead>
              <tr style="background:#f0f0f0">
                <th style="border:1px solid #ccc;padding:4px 6px;text-align:left">EPI</th>
                <th style="border:1px solid #ccc;padding:4px 6px;text-align:center">Qtd</th>
                <th style="border:1px solid #ccc;padding:4px 6px;text-align:center">Data Entrega</th>
                <th style="border:1px solid #ccc;padding:4px 6px;text-align:center">Data Devolução</th>
                <th style="border:1px solid #ccc;padding:4px 6px;text-align:center">Condição</th>
                <th style="border:1px solid #ccc;padding:4px 6px;text-align:center">Destino</th>
                <th style="border:1px solid #ccc;padding:4px 6px;text-align:center">Recebido por</th>
                <th style="border:1px solid #ccc;padding:4px 6px;text-align:center">Assinatura</th>
                <th style="border:1px solid #ccc;padding:4px 6px;text-align:left">Motivo</th>
              </tr>
            </thead>
            <tbody>
              {devol_rows_html}
            </tbody>
          </table>
        </div>
        """

    period_row = ''
    if str(period_label or '').strip():
        period_row = f"""
  <div class="dados-linha">
    <div class="campo"><span class="campo-label">PERÍODO:</span> <span>{period_label}</span></div>
  </div>"""

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<title>Ficha EPI - {employee.get("name","")}</title>
<style>
  @page {{ margin: 12mm 15mm; }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: Arial, Helvetica, sans-serif; font-size: 9pt; color: #111; background: #fff; }}
  .header {{ display: flex; align-items: center; margin-bottom: 10px; padding-bottom: 6px; border-bottom: 1px solid #333; }}
  .logo {{ margin-right: 20px; }}
  .titulo {{ text-align: center; font-size: 10pt; font-weight: bold; margin-bottom: 10px; }}
  .dados-colaborador {{ margin-bottom: 8px; border-bottom: 1px solid #ccc; padding-bottom: 6px; }}
  .dados-linha {{ display: flex; gap: 30px; margin-bottom: 2px; }}
  .campo {{ display: flex; gap: 6px; }}
  .campo-label {{ font-weight: bold; white-space: nowrap; }}
  .declaracao {{ font-size: 8pt; margin-bottom: 8px; text-align: justify; line-height: 1.4; border: 1px solid #ccc; padding: 6px; }}
  table {{ width: 100%; border-collapse: collapse; margin-bottom: 6px; font-size: 8pt; }}
  th {{ background: #f0f0f0; border: 1px solid #333; padding: 4px 3px; text-align: center; font-size: 7.5pt; font-weight: bold; }}
  td {{ border: 1px solid #555; padding: 3px 3px; height: 18px; font-size: 8pt; }}
  .th-quant {{ width: 5%; }} .th-unid {{ width: 7%; }} .th-epi {{ width: 28%; }} .th-ca {{ width: 6%; }}
  .th-fab {{ width: 8%; }} .th-vida {{ width: 8%; }} .th-receb {{ width: 8%; }} .th-devol {{ width: 8%; }} .th-assina {{ width: 12%; }}
  .observacoes {{ font-size: 8pt; margin-top: 4px; font-weight: bold; line-height: 1.4; }}
  .rodape {{ margin-top: 8px; padding-top: 4px; border-top: 1px solid #ccc; text-align: center; font-size: 7pt; color: #555; }}
</style>
</head>
<body>
<div class="header"><div class="logo">{logo_html}</div></div>
<div class="titulo">{config['titulo']}</div>
<div class="dados-colaborador">
  <div class="dados-linha"><div class="campo"><span class="campo-label">NOME:</span> <span>{employee.get('name','')}</span></div></div>
  <div class="dados-linha"><div class="campo"><span class="campo-label">FUNÇÃO:</span> <span>{employee.get('role_name','')}</span></div></div>
  <div class="dados-linha">
    <div class="campo"><span class="campo-label">SETOR:</span> <span>{employee.get('sector','')}</span></div>
    <div class="campo" style="margin-left:auto"><span class="campo-label">UNIDADE:</span> <span>{unit_name}</span></div>
  </div>{period_row}
</div>
<div class="declaracao">{declaracao_html}</div>
<table><thead><tr>
<th class="th-quant">QUANT</th><th class="th-unid">UNID</th><th class="th-epi">EPI</th>
<th class="th-ca">CA</th><th class="th-fab">FABRICAÇÃO</th><th class="th-vida">VIDA ÚTIL</th>
<th class="th-receb">RECEBIDO</th><th class="th-devol">DEVOLVIDO</th><th class="th-assina">ASSINATURA</th>
</tr></thead><tbody>{rows_html}</tbody></table>
<div class="observacoes">{observacoes_html}</div>
{devol_section_html}
<div class="rodape">{config['rastreabilidade']}</div>
</body>
</html>"""


def build_ficha_epi_html(connection, employee_id, actor):
    employee = get_employee_by_id(connection, int(employee_id))
    if not employee:
        raise ValueError('Colaborador não encontrado.')
    ensure_resource_company(actor, employee, 'Colaborador')
    ensure_actor_employee_scope(connection, actor, employee)

    company = connection.execute('SELECT id, name, logo_type FROM companies WHERE id = ?', (int(employee['company_id']),)).fetchone()
    unit = connection.execute('SELECT id, name, unit_type FROM units WHERE id = ?', (int(employee['unit_id']),)).fetchone()
    has_stock_items_table = _table_exists(connection, 'epi_stock_items')
    manufacture_expr = "COALESCE(NULLIF(esi.manufacture_date, ''), e.manufacture_date)" if has_stock_items_table else 'e.manufacture_date'
    join_stock_items = 'LEFT JOIN epi_stock_items esi ON esi.delivery_id = d.id' if has_stock_items_table else ''
    deliveries = connection.execute(
        f"""
        SELECT d.id, d.quantity, d.delivery_date, d.next_replacement_date,
               d.signature_data, d.signature_name, d.returned_date,
               e.name AS epi_name, e.ca, e.unit_measure,
               {manufacture_expr} AS manufacture_date, e.epi_validity_date
        FROM deliveries d
        JOIN epis e ON e.id = d.epi_id
        {join_stock_items}
        WHERE d.employee_id = ?
        ORDER BY d.delivery_date DESC, d.id DESC
        """,
        (int(employee_id),)
    ).fetchall()
    devolutions = connection.execute(
        """
        SELECT dev.returned_date, dev.condition, dev.destination, dev.notes, dev.reason,
               dev.signature_name, dev.signature_at,
               dev.received_by_name, dev.quantity,
               e.name AS epi_name, e.ca, e.unit_measure,
               d.delivery_date, d.quantity AS qty_entregue
          FROM epi_devolutions dev
          JOIN epis e ON e.id = dev.epi_id
          JOIN deliveries d ON d.id = dev.delivery_id
         WHERE dev.employee_id = ?
           AND dev.company_id = ?
         ORDER BY dev.returned_date DESC, dev.id DESC
        """,
        (int(employee_id), int(employee['company_id']))
    ).fetchall()
    return render_ficha_epi_html_document(
        employee=employee,
        company=row_to_dict(company) if company else {},
        unit=row_to_dict(unit) if unit else {},
        deliveries=[row_to_dict(item) for item in deliveries],
        devolutions=[row_to_dict(item) for item in devolutions],
        config=get_ficha_config(connection, int(employee['company_id'])),
    )


def build_ficha_epi_html_by_period(connection, ficha_period_id, actor):
    ficha = connection.execute(
        'SELECT fp.id, fp.company_id, fp.employee_id, fp.unit_id, fp.period_start, fp.period_end FROM epi_ficha_periods fp WHERE fp.id = ?',
        (int(ficha_period_id),),
    ).fetchone()
    if not ficha:
        raise ValueError('Período da ficha não encontrado.')
    ficha = row_to_dict(ficha)
    employee = get_employee_by_id(connection, int(ficha['employee_id']))
    if not employee:
        raise ValueError('Colaborador não encontrado para o período informado.')
    ensure_resource_company(actor, employee, 'Colaborador')
    scope_unit_id = actor_operational_unit_id(connection, actor)
    if scope_unit_id and int(employee['unit_id']) != int(scope_unit_id):
        raise PermissionError('Seu perfil só pode acessar fichas da própria unidade operacional.')

    company = connection.execute('SELECT id, name, logo_type FROM companies WHERE id = ?', (int(employee['company_id']),)).fetchone()
    unit = connection.execute('SELECT id, name, unit_type FROM units WHERE id = ?', (int(employee['unit_id']),)).fetchone()
    has_stock_items_table = _table_exists(connection, 'epi_stock_items')
    manufacture_expr = "COALESCE(NULLIF(esi.manufacture_date, ''), e.manufacture_date)" if has_stock_items_table else 'e.manufacture_date'
    join_stock_items = 'LEFT JOIN epi_stock_items esi ON esi.delivery_id = d.id ' if has_stock_items_table else ''
    deliveries = connection.execute(
        (
            'SELECT d.id, fi.quantity, d.delivery_date, d.next_replacement_date, '
            'fi.item_signature_data AS signature_data, fi.item_signature_name AS signature_name, d.returned_date, '
            f'e.name AS epi_name, e.ca, e.unit_measure, {manufacture_expr} AS manufacture_date, e.epi_validity_date '
            'FROM epi_ficha_items fi '
            'JOIN deliveries d ON d.id = fi.delivery_id '
            'JOIN epis e ON e.id = fi.epi_id '
            f'{join_stock_items}'
            'WHERE fi.ficha_period_id = ? '
            'ORDER BY d.delivery_date DESC, d.id DESC'
        ),
        (int(ficha_period_id),),
    ).fetchall()
    devolutions = connection.execute(
        (
            'SELECT dev.returned_date, dev.condition, dev.destination, dev.notes, dev.reason, '
            'dev.signature_name, dev.signature_at, dev.received_by_name, dev.quantity, '
            'e.name AS epi_name, e.ca, e.unit_measure, d.delivery_date, d.quantity AS qty_entregue '
            'FROM epi_devolutions dev '
            'JOIN epis e ON e.id = dev.epi_id '
            'JOIN deliveries d ON d.id = dev.delivery_id '
            'WHERE dev.ficha_period_id = ? '
            'ORDER BY dev.returned_date DESC, dev.id DESC'
        ),
        (int(ficha_period_id),),
    ).fetchall()
    return render_ficha_epi_html_document(
        employee=employee,
        company=row_to_dict(company) if company else {},
        unit=row_to_dict(unit) if unit else {},
        deliveries=[row_to_dict(item) for item in deliveries],
        devolutions=[row_to_dict(item) for item in devolutions],
        config=get_ficha_config(connection, int(employee['company_id'])),
        period_label=f"{ficha.get('period_start', '')} a {ficha.get('period_end', '')}",
    )


def default_ficha_retention_policy():
    return {
        'retention_years': 5,
        'purge_enabled': False,
        'timeline': [
            {'stage': 'snapshot_generated', 'label': 'Fechamento / snapshot gerado'},
            {'stage': 'years_1_2', 'label': 'Ano 1-2: retenção ativa'},
            {'stage': 'years_3_4', 'label': 'Ano 3-4: auditoria legal'},
            {'stage': 'year_5', 'label': '5 anos: expiração NR-6'},
            {'stage': 'purge', 'label': 'Purge automático (se habilitado)'},
        ],
    }


def get_ficha_retention_policy(connection, company_id):
    policy = default_ficha_retention_policy()
    scope_key = _configuration_scope_key(company_id)
    raw = get_meta(connection, f'ficha_retention_policy:{scope_key}')
    if not raw:
        return policy
    try:
        parsed = json.loads(raw)
    except Exception as exc:
        structured_log('warning', 'ficha.retention_policy_parse_error', error=str(exc), scope_key=scope_key)
        return policy
    retention_years = int(parsed.get('retention_years') or policy['retention_years'])
    purge_enabled = bool(parsed.get('purge_enabled'))
    policy['retention_years'] = max(1, min(retention_years, 15))
    policy['purge_enabled'] = purge_enabled
    return policy


def save_ficha_retention_policy(connection, company_id, payload):
    scope_key = _configuration_scope_key(company_id)
    current = get_ficha_retention_policy(connection, company_id)
    retention_years = int(payload.get('retention_years') or current['retention_years'])
    purge_enabled = bool(payload.get('purge_enabled'))
    normalized = default_ficha_retention_policy()
    normalized['retention_years'] = max(1, min(retention_years, 15))
    normalized['purge_enabled'] = purge_enabled
    set_meta(connection, f'ficha_retention_policy:{scope_key}', json.dumps(normalized, ensure_ascii=False))
    connection.commit()
    return normalized


def _snapshot_status(row, now_iso):
    status = str(row.get('status') or 'archived').strip() or 'archived'
    if status in {'purged', 'expired'}:
        return status
    expires_at = str(row.get('expires_at') or '').strip()
    if expires_at and expires_at <= now_iso:
        return 'expired'
    return 'archived'


def build_ficha_snapshot_payload(connection, ficha_period_id, actor):
    has_finalized_at = _col_exists(connection, 'epi_ficha_periods', 'finalized_at')
    finalized_at_select = 'fp.finalized_at' if has_finalized_at else "'' AS finalized_at"
    ficha = connection.execute(
        (
            f'SELECT fp.id, fp.company_id, fp.unit_id, fp.employee_id, fp.period_start, fp.period_end, fp.status, {finalized_at_select}, '
            'e.name AS employee_name, e.employee_id_code, e.sector, e.role_name, '
            'c.name AS company_name, c.cnpj AS company_cnpj, u.name AS unit_name '
            'FROM epi_ficha_periods fp '
            'JOIN employees e ON e.id = fp.employee_id '
            'JOIN companies c ON c.id = fp.company_id '
            'JOIN units u ON u.id = fp.unit_id '
            'WHERE fp.id = ?'
        ),
        (int(ficha_period_id),),
    ).fetchone()
    if not ficha:
        raise ValueError('Período da ficha não encontrado para snapshot.')
    ficha = row_to_dict(ficha)
    deliveries = connection.execute(
        (
            'SELECT fi.id AS ficha_item_id, fi.delivery_id, fi.epi_id, fi.quantity, d.quantity_label, d.delivery_date, '
            'd.returned_date, fi.item_signature_name, fi.item_signature_data, fi.item_signature_at, fi.item_signature_comment, '
            'd.signature_name AS delivery_signature_name, d.signature_data AS delivery_signature_data, d.signature_at AS delivery_signature_at, '
            'ep.name AS epi_name, ep.purchase_code, ep.ca '
            'FROM epi_ficha_items fi '
            'JOIN deliveries d ON d.id = fi.delivery_id '
            'JOIN epis ep ON ep.id = fi.epi_id '
            'WHERE fi.ficha_period_id = ? '
            'ORDER BY d.delivery_date ASC, fi.id ASC'
        ),
        (int(ficha_period_id),),
    ).fetchall()
    devolutions = connection.execute(
        (
            'SELECT dev.id, dev.delivery_id, dev.epi_id, dev.returned_date, dev.quantity, d.quantity_label, dev.condition AS return_condition, '
            'dev.signature_name, dev.signature_data, dev.signature_at, dev.signature_comment, ep.name AS epi_name, ep.purchase_code, ep.ca '
            'FROM epi_devolutions dev '
            'LEFT JOIN deliveries d ON d.id = dev.delivery_id '
            'JOIN epis ep ON ep.id = dev.epi_id '
            'WHERE dev.ficha_period_id = ? '
            'ORDER BY dev.returned_date ASC, dev.id ASC'
        ),
        (int(ficha_period_id),),
    ).fetchall()
    return {
        'snapshot_version': 1,
        'ficha_period_id': int(ficha['id']),
        'ficha_status': ficha.get('status') or '',
        'employee': {
            'id': int(ficha['employee_id']),
            'name': ficha.get('employee_name') or '',
            'employee_id_code': ficha.get('employee_id_code') or '',
            'sector': ficha.get('sector') or '',
            'role_name': ficha.get('role_name') or '',
        },
        'company': {
            'id': int(ficha['company_id']),
            'name': ficha.get('company_name') or '',
            'cnpj': ficha.get('company_cnpj') or '',
        },
        'unit': {
            'id': int(ficha['unit_id']),
            'name': ficha.get('unit_name') or '',
        },
        'period': {
            'start': ficha.get('period_start') or '',
            'end': ficha.get('period_end') or '',
            'finalized_at': ficha.get('finalized_at') or '',
        },
        'generated_by': {
            'user_id': int(actor['id']),
            'role': actor.get('role') or '',
            'name': actor.get('full_name') or actor.get('username') or '',
        },
        'deliveries': [row_to_dict(item) for item in deliveries],
        'devolutions': [row_to_dict(item) for item in devolutions],
    }


def compute_ficha_period_signature_state(connection, ficha_period_id):
    row = connection.execute(
        (
            "SELECT fp.id, fp.batch_signature_name, fp.batch_signature_data, fp.batch_signature_at, "
            "COUNT(fi.id) AS total_items, "
            "SUM(CASE WHEN fi.id IS NOT NULL AND COALESCE(fi.item_signature_at, '') <> '' THEN 1 ELSE 0 END) AS signed_items, "
            "SUM(CASE WHEN fi.id IS NOT NULL AND COALESCE(fi.item_signature_at, '') = '' THEN 1 ELSE 0 END) AS pending_items "
            "FROM epi_ficha_periods fp "
            "LEFT JOIN epi_ficha_items fi ON fi.ficha_period_id = fp.id "
            "WHERE fp.id = ? "
            "GROUP BY fp.id, fp.batch_signature_name, fp.batch_signature_data, fp.batch_signature_at"
        ),
        (int(ficha_period_id),),
    ).fetchone()
    if not row:
        raise ValueError('Período de ficha não encontrado.')
    data = row_to_dict(row)
    total_items = int(data.get('total_items') or 0)
    signed_items = int(data.get('signed_items') or 0)
    pending_items = int(data.get('pending_items') or 0)
    has_batch_signature = bool(
        str(data.get('batch_signature_name') or '').strip()
        and str(data.get('batch_signature_data') or '').strip()
        and str(data.get('batch_signature_at') or '').strip()
    )
    can_close = total_items > 0 and pending_items == 0 and signed_items == total_items and has_batch_signature
    return {
        'total_items': total_items,
        'signed_items': signed_items,
        'pending_items': pending_items,
        'has_batch_signature': has_batch_signature,
        'can_close': can_close,
    }


def get_ficha_period_close_requirements(state):
    missing = []
    if int(state.get('total_items') or 0) <= 0:
        missing.append('total_items')
    if int(state.get('pending_items') or 0) > 0:
        missing.append('pending_items')
    if int(state.get('signed_items') or 0) != int(state.get('total_items') or 0):
        missing.append('signed_items')
    if not bool(state.get('has_batch_signature')):
        missing.append('batch_signature')
    return missing


def is_valid_ficha_period_state(state):
    return int(state.get('total_items') or 0) > 0


def assert_ficha_period_can_close(connection, ficha_period_id):
    state = compute_ficha_period_signature_state(connection, ficha_period_id)
    if not state['can_close']:
        missing_requirements = get_ficha_period_close_requirements(state)
        if 'pending_items' in missing_requirements or 'signed_items' in missing_requirements:
            raise ValueError('Não é possível fechar o período: existem assinaturas pendentes.')
        if 'batch_signature' in missing_requirements:
            raise ValueError('Não é possível fechar o período: assinatura em lote ausente ou incompleta.')
        if 'total_items' in missing_requirements:
            raise ValueError('Não é possível fechar o período: não há itens no período.')
        raise ValueError('Não é possível fechar o período: requisitos de fechamento não atendidos.')
    return state


def resolve_ficha_period_effective_status(connection, ficha_period):
    period = dict(ficha_period or {})
    state = compute_ficha_period_signature_state(connection, int(period.get('id') or 0))
    effective_status = 'closed' if state['can_close'] else ('pending_signature' if state['pending_items'] > 0 else 'open')
    period['status_effective'] = effective_status
    period['pending_items'] = state['pending_items']
    period['total_items'] = state['total_items']
    period['signed_items'] = state['signed_items']
    period['has_batch_signature'] = state['has_batch_signature']
    if str(period.get('status') or '').strip().lower() == 'closed' and effective_status != 'closed':
        now = datetime.now(UTC).isoformat()
        connection.execute(
            'UPDATE epi_ficha_periods SET status = ?, updated_at = ? WHERE id = ?',
            (effective_status, now, int(period['id']))
        )
        period['status'] = effective_status
    return period


def apply_snapshot_retention(connection, company_id, policy):
    now_iso = datetime.now(UTC).isoformat()
    params = [now_iso]
    where_clause = ''
    if company_id:
        where_clause = ' AND company_id = ?'
        params.append(int(company_id))
    connection.execute(
        f"UPDATE ficha_epi_snapshots SET status = 'expired', expired_at = ? WHERE status = 'archived' AND expires_at <= ?{where_clause}",
        tuple([now_iso, now_iso, *params[1:]]) if company_id else (now_iso, now_iso),
    )
    if policy.get('purge_enabled'):
        if company_id:
            connection.execute(
                "UPDATE ficha_epi_snapshots SET status = 'purged', purged_at = ?, html_content = '', snapshot_payload = '{}' "
                "WHERE status = 'expired' AND company_id = ?",
                (now_iso, int(company_id)),
            )
        else:
            connection.execute(
                "UPDATE ficha_epi_snapshots SET status = 'purged', purged_at = ?, html_content = '', snapshot_payload = '{}' "
                "WHERE status = 'expired'",
                (now_iso,),
            )
    connection.commit()


def ensure_ficha_snapshot_for_period(connection, ficha_period_id, actor):
    ficha_period_id = int(ficha_period_id)
    row = connection.execute(
        'SELECT id, html_content, html_sha256, snapshot_payload, payload_sha256, generated_at, expires_at, status FROM ficha_epi_snapshots WHERE ficha_period_id = ?',
        (ficha_period_id,),
    ).fetchone()
    if row:
        return row_to_dict(row)
    period = connection.execute(
        'SELECT id, company_id, unit_id, employee_id FROM epi_ficha_periods WHERE id = ?',
        (ficha_period_id,),
    ).fetchone()
    if not period:
        raise ValueError('Período da ficha não encontrado para snapshot.')
    period = row_to_dict(period)
    html_content = build_ficha_epi_html_by_period(connection, ficha_period_id, actor)
    html_sha256 = hashlib.sha256(html_content.encode('utf-8')).hexdigest()
    snapshot_payload = build_ficha_snapshot_payload(connection, ficha_period_id, actor)
    snapshot_payload_json = json.dumps(snapshot_payload, ensure_ascii=False, sort_keys=True)
    payload_sha256 = hashlib.sha256(snapshot_payload_json.encode('utf-8')).hexdigest()
    policy = get_ficha_retention_policy(connection, period.get('company_id'))
    retention_years = int(policy.get('retention_years') or 5)
    generated_at = datetime.now(UTC).isoformat()
    expires_at = (datetime.now(UTC) + timedelta(days=365 * retention_years)).isoformat()
    connection.execute(
        (
            'INSERT INTO ficha_epi_snapshots '
            '(ficha_period_id, company_id, unit_id, employee_id, html_content, html_sha256, generated_by_user_id, generated_at, expires_at, snapshot_payload, payload_sha256, status, retention_years) '
            'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'
        ),
        (
            ficha_period_id,
            int(period['company_id']),
            int(period['unit_id']),
            int(period['employee_id']),
            html_content,
            html_sha256,
            int(actor['id']),
            generated_at,
            expires_at,
            snapshot_payload_json,
            payload_sha256,
            'archived',
            retention_years,
        ),
    )
    return {'ficha_period_id': ficha_period_id, 'html_content': html_content, 'html_sha256': html_sha256, 'snapshot_payload': snapshot_payload_json, 'payload_sha256': payload_sha256, 'expires_at': expires_at, 'status': 'archived'}


def refresh_ficha_snapshot_for_period_if_exists(connection, ficha_period_id, actor):
    ficha_period_id = int(ficha_period_id)
    row = connection.execute(
        'SELECT id FROM ficha_epi_snapshots WHERE ficha_period_id = ?',
        (ficha_period_id,),
    ).fetchone()
    if not row:
        return None
    html_content = build_ficha_epi_html_by_period(connection, ficha_period_id, actor)
    html_sha256 = hashlib.sha256(html_content.encode('utf-8')).hexdigest()
    snapshot_payload = build_ficha_snapshot_payload(connection, ficha_period_id, actor)
    snapshot_payload_json = json.dumps(snapshot_payload, ensure_ascii=False, sort_keys=True)
    payload_sha256 = hashlib.sha256(snapshot_payload_json.encode('utf-8')).hexdigest()
    generated_at = datetime.now(UTC).isoformat()
    connection.execute(
        (
            'UPDATE ficha_epi_snapshots '
            'SET html_content = ?, html_sha256 = ?, snapshot_payload = ?, payload_sha256 = ?, generated_at = ?, status = ? '
            'WHERE ficha_period_id = ?'
        ),
        (
            html_content,
            html_sha256,
            snapshot_payload_json,
            payload_sha256,
            generated_at,
            'archived',
            ficha_period_id,
        ),
    )
    return {
        'ficha_period_id': ficha_period_id,
        'html_content': html_content,
        'html_sha256': html_sha256,
        'snapshot_payload': snapshot_payload_json,
        'payload_sha256': payload_sha256,
        'generated_at': generated_at,
        'status': 'archived',
    }


# ═══════════════════════════════════════════════════════
# DEVOLUÇÃO DE EPI
# ═══════════════════════════════════════════════════════

DEVOLUTION_CONDITION_LABELS = {
    'usable':      'Reutilizável',
    'damaged':     'Danificado',
    'discarded':   'Descartado',
    'maintenance': 'Em manutenção',
    'quarantine':  'Em quarentena',
    'hygiene':     'Para higienização',
}

DEVOLUTION_DESTINATION_LABELS = {
    'stock':       'Retornou ao estoque',
    'discard':     'Descartado',
    'maintenance': 'Encaminhado para manutenção',
    'hygiene':     'Encaminhado para higienização',
    'quarantine':  'Em quarentena',
}

STOCK_ITEM_STATUS_BY_DESTINATION = {
    'stock':       'in_stock',
    'discard':     'discarded',
    'maintenance': 'maintenance',
    'hygiene':     'hygiene',
    'quarantine':  'quarantine',
}


def register_epi_devolution(connection, payload, actor):
    require_fields(payload, ['actor_user_id', 'delivery_id', 'returned_date', 'condition', 'destination'])
    delivery_id   = int(payload['delivery_id'])
    returned_date = str(payload['returned_date']).strip()
    condition     = str(payload.get('condition', 'usable')).strip()
    destination   = str(payload.get('destination', 'stock')).strip()
    notes         = str(payload.get('notes', '')).strip()
    reason        = str(payload.get('reason', '')).strip()
    signature_data = str(payload.get('signature_data') or '').strip()
    signature_name = str(payload.get('signature_name') or '').strip()
    signature_comment = str(payload.get('signature_comment') or '').strip()
    signature_at = str(payload.get('signature_at') or '').strip()
    expected_employee_id = str(payload.get('expected_employee_id') or '').strip()
    expected_epi_id = str(payload.get('expected_epi_id') or '').strip()
    expected_unit_id = str(payload.get('expected_unit_id') or '').strip()

    if condition not in DEVOLUTION_CONDITION_LABELS:
        raise ValueError('Condição inválida.')
    if destination not in DEVOLUTION_DESTINATION_LABELS:
        raise ValueError('Destino inválido.')

    delivery = connection.execute(
        'SELECT d.*, e.name AS epi_name FROM deliveries d JOIN epis e ON e.id = d.epi_id WHERE d.id = ?',
        (delivery_id,)
    ).fetchone()
    if not delivery:
        raise ValueError('Entrega não encontrada.')
    delivery = row_to_dict(delivery)
    ensure_resource_company(actor, delivery, 'Entrega')
    if expected_employee_id and int(expected_employee_id) != int(delivery.get('employee_id') or 0):
        raise ValueError('Entrega selecionada não pertence ao colaborador informado.')
    if expected_epi_id and int(expected_epi_id) != int(delivery.get('epi_id') or 0):
        raise ValueError('Entrega selecionada não pertence ao EPI informado.')
    if expected_unit_id and int(expected_unit_id) != int(delivery.get('unit_id') or 0):
        raise ValueError('Entrega selecionada não pertence à unidade informada.')

    employee = get_employee_by_id(connection, int(delivery['employee_id']))
    if str(delivery.get('returned_date') or '').strip():
        raise ValueError('Este EPI já foi registrado como devolvido.')
    # Verifica se o período vinculado à entrega está encerrado.
    # Deliveries com ficha_items: usa o vínculo direto.
    # Deliveries legadas sem ficha_items: fallback por range de datas.
    _has_ficha_item = connection.execute(
        'SELECT 1 FROM epi_ficha_items fi WHERE fi.delivery_id = ? LIMIT 1', (delivery_id,)
    ).fetchone()
    if _has_ficha_item:
        _closed_period = connection.execute(
            """SELECT fp.id FROM epi_ficha_items fi
               JOIN epi_ficha_periods fp ON fp.id = fi.ficha_period_id
               WHERE fi.delivery_id = ? AND fp.status = 'closed'
               LIMIT 1""",
            (delivery_id,),
        ).fetchone()
    else:
        _delivery_date = str(delivery.get('delivery_date') or '').strip()
        _closed_period = connection.execute(
            """SELECT id FROM epi_ficha_periods
               WHERE employee_id = ? AND period_start <= ? AND period_end >= ? AND status = 'closed'
               LIMIT 1""",
            (int(delivery['employee_id']), _delivery_date, _delivery_date),
        ).fetchone() if _delivery_date else None
    if _closed_period:
        raise ValueError('Período da ficha de EPI encerrado. Devolução não é permitida após o fechamento do período.')
    if signature_data:
        signature_name = signature_name or str(employee.get('name') or actor.get('full_name') or 'Assinatura digital').strip()
        signature_at = signature_at or datetime.now(UTC).isoformat()
    else:
        signature_name = ''
        signature_at = ''
        signature_comment = ''

    now = datetime.now(UTC).isoformat()
    quantity = int(delivery.get('quantity') or 1)

    dev_cursor = connection.execute(
        """INSERT INTO epi_devolutions
           (company_id, unit_id, employee_id, epi_id, delivery_id,
            returned_date, quantity, condition, destination,
            notes, reason, received_by_user_id, received_by_name,
            signature_name, signature_data, signature_ip, signature_at, signature_comment, created_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            int(delivery['company_id']),
            int(delivery.get('unit_id') or 0),
            int(delivery['employee_id']),
            int(delivery['epi_id']),
            delivery_id,
            returned_date, quantity, condition, destination,
            notes, reason,
            int(actor['id']),
            str(actor.get('full_name') or ''),
            signature_name,
            signature_data,
            str(payload.get('signature_ip') or ''),
            signature_at,
            signature_comment,
            now,
        )
    )
    devolution_id = int(dev_cursor.lastrowid)
    ensure_ficha_for_devolution(
        connection,
        {
            'id': devolution_id,
            'company_id': int(delivery['company_id']),
            'employee_id': int(delivery['employee_id']),
            'unit_id': int(delivery.get('unit_id') or 0),
            'returned_date': returned_date,
            'schedule_type': str(employee.get('schedule_type') or ''),
        }
    )

    connection.execute(
        'UPDATE deliveries SET returned_date=?, returned_condition=?, returned_notes=? WHERE id=?',
        (returned_date, condition, notes, delivery_id)
    )

    stock_item_status = STOCK_ITEM_STATUS_BY_DESTINATION.get(destination, 'in_stock')
    try:
        stock_item = connection.execute(
            'SELECT id, glove_size, size, uniform_size FROM epi_stock_items WHERE delivery_id=? ORDER BY id DESC LIMIT 1',
            (delivery_id,)
        ).fetchone()
    except Exception as exc:
        structured_log('warning', 'devolution.stock_item_size_columns_unavailable', delivery_id=delivery_id, error=str(exc))
        stock_item = connection.execute(
            'SELECT id FROM epi_stock_items WHERE delivery_id=? ORDER BY id DESC LIMIT 1',
            (delivery_id,)
        ).fetchone()
    stock_item_data = row_to_dict(stock_item) if stock_item else {}
    effective_delivery_size = resolve_effective_size_fields(delivery, stock_item_data)
    if stock_item:
        connection.execute(
            'UPDATE epi_stock_items SET status=?, updated_at=? WHERE id=?',
            (stock_item_status, now, int(stock_item['id']))
        )
        connection.execute(
            'UPDATE epi_devolutions SET stock_item_id=? WHERE id=?',
            (int(stock_item['id']), devolution_id)
        )

    movement_id = None
    if destination == 'stock':
        unit_id    = int(delivery.get('unit_id') or 0)
        epi_id     = int(delivery['epi_id'])
        company_id = int(delivery['company_id'])
        stock_row  = get_unit_stock(connection, company_id, unit_id, epi_id)
        prev_stock = int((stock_row or {}).get('quantity') or 0)
        new_stock  = prev_stock + quantity
        ensure_stock_movement_size_columns(connection)
        mov = connection.execute(
            """INSERT INTO stock_movements
               (company_id, unit_id, epi_id, movement_type, quantity,
                previous_stock, new_stock, source_type, source_id,
                notes, actor_user_id, actor_name, created_at, glove_size, size, uniform_size)
               VALUES (?,?,?,'return',?,?,?,'devolution',?,?,?,?,?,?,?,?)""",
            (company_id, unit_id, epi_id, quantity, prev_stock, new_stock,
             devolution_id,
             'Devolucao — ' + str(delivery.get('epi_name') or ''),
             int(actor['id']), str(actor.get('full_name') or ''), now,
             effective_delivery_size['glove_size'],
             effective_delivery_size['size'],
             effective_delivery_size['uniform_size'])
        )
        movement_id = int(mov.lastrowid)
        upsert_unit_stock(connection, company_id, unit_id, epi_id, new_stock)
        connection.execute(
            'UPDATE epi_devolutions SET stock_movement_id=? WHERE id=?',
            (movement_id, devolution_id)
        )
        connection.execute(
            'UPDATE deliveries SET return_movement_id=? WHERE id=?',
            (movement_id, delivery_id)
        )

    connection.commit()
    structured_log('info', 'devolution.registered',
                   devolution_id=devolution_id, delivery_id=delivery_id,
                   condition=condition, destination=destination)
    return devolution_id


def fetch_devolutions(connection, actor, filters=None):
    filters = filters or {}
    clauses, params = [], []
    if actor['role'] != 'master_admin':
        clauses.append('d.company_id = ?')
        params.append(int(actor['company_id']))
    for key in ('employee_id', 'epi_id', 'delivery_id'):
        if filters.get(key):
            clauses.append(f'd.{key} = ?')
            params.append(int(filters[key]))
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ''
    rows = connection.execute(
        f"""SELECT d.*, emp.name AS employee_name, emp.employee_id_code,
                   e.name AS epi_name, e.ca, e.unit_measure, u.name AS unit_name
            FROM epi_devolutions d
            JOIN employees emp ON emp.id = d.employee_id
            JOIN epis      e   ON e.id   = d.epi_id
            JOIN units     u   ON u.id   = d.unit_id
            {where}
            ORDER BY d.returned_date DESC, d.id DESC""",
        tuple(params)
    ).fetchall()
    result = []
    for row in rows:
        item = row_to_dict(row)
        item['condition_label']   = DEVOLUTION_CONDITION_LABELS.get(item.get('condition',''), item.get('condition',''))
        item['destination_label'] = DEVOLUTION_DESTINATION_LABELS.get(item.get('destination',''), item.get('destination',''))
        result.append(item)
    return result


PURCHASE_FUNCTION_TYPES = {'buyer', 'approver'}
PURCHASE_FUNCTION_LABELS = {'buyer': 'Comprador', 'approver': 'Aprovador'}


def normalize_purchase_function_type(value):
    normalized = normalize_role_name(value)
    if normalized not in PURCHASE_FUNCTION_TYPES:
        raise ValueError('Função de compras deve ser comprador ou aprovador.')
    return normalized


def get_actor_purchase_unit_scope(connection, actor):
    """Retorna unit_ids para vínculos de Compras.
    Mantém compatibilidade com user_unit_links legado e também consulta a
    estrutura separada por colaborador (purchase_role_unit_links)."""
    if not actor:
        return None
    actor_role = actor.get('role')
    unit_ids = []
    if actor_role in ('buyer', 'approver'):
        legacy_rows = connection.execute(
            'SELECT unit_id FROM user_unit_links WHERE user_id = ?',
            (int(actor['id']),)
        ).fetchall()
        unit_ids.extend(int(r['unit_id']) for r in legacy_rows)
    linked_employee_id = actor.get('linked_employee_id')
    if linked_employee_id and actor_role in ('buyer', 'approver', 'admin', 'registry_admin', 'general_admin'):
        function_rows = connection.execute(
            'SELECT unit_id FROM purchase_role_unit_links WHERE employee_id = ? AND role_type = ?',
            (int(linked_employee_id), actor_role if actor_role in PURCHASE_FUNCTION_TYPES else 'buyer')
        ).fetchall()
        unit_ids.extend(int(r['unit_id']) for r in function_rows)
    if not unit_ids:
        return None
    return sorted(set(unit_ids))


def actor_company_id_or_query(connection, actor, query):
    if actor.get('role') != 'master_admin':
        return int(actor['company_id'])
    requested = str(query.get('company_id', [''])[0] or '').strip()
    if requested:
        return int(requested)
    first_company = connection.execute('SELECT id FROM companies ORDER BY id ASC LIMIT 1').fetchone()
    if not first_company:
        raise ValueError('Nenhuma empresa cadastrada para consulta.')
    return int(first_company['id'])


def require_purchase_function_admin(actor):
    if actor.get('role') not in ('general_admin', 'registry_admin'):
        raise PermissionError('Somente Administrador Geral ou Administrador de Registro pode gerenciar funções de compras.')


def fetch_purchase_function_links(connection, company_id):
    """Retorna vínculos de função de compra (comprador/aprovador) por unidade.

    Inclui flag has_system_user indicando se o colaborador possui conta de usuário
    ativa com o perfil correspondente — útil para validação no frontend.
    """
    rows = connection.execute(
        'SELECT prul.*, employees.name AS employee_name, employees.employee_id_code, '
        'employees.sector AS employee_sector, employees.role_name AS employee_role, '
        'units.name AS unit_name '
        'FROM purchase_role_unit_links prul '
        'JOIN employees ON employees.id = prul.employee_id '
        'JOIN units ON units.id = prul.unit_id '
        'WHERE prul.company_id = ? '
        'ORDER BY employees.name, prul.role_type, units.name',
        (int(company_id),)
    ).fetchall()
    items = []
    for row in rows:
        item = row_to_dict(row)
        item['role_label'] = PURCHASE_FUNCTION_LABELS.get(item.get('role_type'), item.get('role_type'))
        user_check = connection.execute(
            'SELECT id, username FROM users WHERE linked_employee_id = ? AND role = ? AND active = 1 LIMIT 1',
            (item['employee_id'], item.get('role_type'))
        ).fetchone()
        item['has_system_user'] = bool(user_check)
        item['system_user_login'] = str(user_check['username']) if user_check else ''
        items.append(item)
    return items


def fetch_purchase_demands(connection, company_id, scope_unit_id=None):
    """Retorna demandas pendentes: solicitações de colaboradores + EPIs abaixo do estoque mínimo.

    Inclui solicitações com status 'solicitado' (aguardando análise) e 'aprovado' (prontas para
    requisição de compra). Filtra por empresa (company_id=None retorna todas) e, quando aplicável,
    por unidade do ator.
    """
    demands = []
    # 1. Solicitações de colaboradores pendentes (solicitado) ou aprovadas (prontas p/ compra)
    req_clauses = ["r.status IN ('solicitado', 'aprovado')"]
    req_params = []
    if company_id is not None:
        req_clauses.insert(0, 'r.company_id = ?')
        req_params.append(company_id)
    if scope_unit_id:
        req_clauses.append('r.unit_id = ?')
        req_params.append(int(scope_unit_id))
    req_rows = connection.execute(
        f'SELECT r.id, r.company_id, r.unit_id, r.employee_id, r.epi_id, r.quantity, '
        f'r.glove_size, r.size, r.uniform_size, r.requested_at, r.status, '
        f'emp.name AS employee_name, emp.sector AS employee_sector, emp.role_name AS employee_role, '
        f'ep.name AS epi_name, ep.ca, ep.unit_measure, ep.manufacturer, ep.supplier_company AS supplier, '
        f'u.name AS unit_name, c.name AS company_name '
        f'FROM epi_requests r '
        f'JOIN employees emp ON emp.id = r.employee_id '
        f'JOIN epis ep ON ep.id = r.epi_id '
        f'JOIN units u ON u.id = r.unit_id '
        f'JOIN companies c ON c.id = r.company_id '
        f"WHERE {' AND '.join(req_clauses)} "
        f'ORDER BY r.status DESC, r.requested_at ASC',
        tuple(req_params)
    ).fetchall()
    for row in req_rows:
        d = dict(row)
        d['demand_type'] = 'employee_request'
        demands.append(d)
    # 2. EPIs abaixo do estoque mínimo
    stock_clauses = ['ep.active = 1', 'ues.quantity < ep.minimum_stock']
    stock_params = []
    if company_id is not None:
        stock_clauses.insert(0, 'ues.company_id = ?')
        stock_params.append(company_id)
    if scope_unit_id:
        stock_clauses.append('ues.unit_id = ?')
        stock_params.append(int(scope_unit_id))
    stock_rows = connection.execute(
        f'SELECT ues.company_id, ues.unit_id, ues.epi_id, ues.quantity AS current_stock, ep.minimum_stock, '
        f'ep.name AS epi_name, ep.ca, ep.unit_measure, ep.manufacturer, ep.supplier_company AS supplier, '
        f'ep.sector AS employee_sector, ep.glove_size, ep.size, ep.uniform_size, '
        f'u.name AS unit_name, c.name AS company_name '
        f'FROM unit_epi_stock ues '
        f'JOIN epis ep ON ep.id = ues.epi_id '
        f'JOIN units u ON u.id = ues.unit_id '
        f'JOIN companies c ON c.id = ues.company_id '
        f"WHERE {' AND '.join(stock_clauses)} "
        f'ORDER BY (ep.minimum_stock - ues.quantity) DESC',
        tuple(stock_params)
    ).fetchall()
    for row in stock_rows:
        d = dict(row)
        d['demand_type'] = 'low_stock'
        d['quantity_requested'] = max(1, int(row['minimum_stock']) - int(row['current_stock']))
        d['employee_name'] = ''
        d['employee_role'] = ''
        d['employee_sector'] = d.get('employee_sector') or 'Estoque baixo'
        d['sector'] = d['employee_sector']
        d['glove_size'] = d.get('glove_size') or 'N/A'
        d['size'] = d.get('size') or 'N/A'
        d['uniform_size'] = d.get('uniform_size') or 'N/A'
        d['status'] = 'low_stock'
        d['size_balances'] = fetch_epi_size_balance(connection, int(d['company_id']), int(d['unit_id']), int(d['epi_id']))
        demands.append(d)
    return demands


def _record_purchase_event(connection, company_id, entity_type, entity_id, action, status_from, status_to, comment, actor_user_id, actor_name, ip_address='', actor_role='', reason='', destination=''):
    now = datetime.now(UTC).isoformat()
    connection.execute(
        'INSERT INTO purchase_events (company_id, entity_type, entity_id, action, status_from, status_to, comment, actor_user_id, actor_name, actor_role, reason, destination, ip_address, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
        (company_id, entity_type, entity_id, action, status_from, status_to, comment, actor_user_id, actor_name, actor_role, reason, destination, ip_address, now)
    )


def ensure_purchase_request_action_scope(connection, actor, purchase_request):
    ensure_resource_company(actor, purchase_request, 'Requisição')
    if actor.get('role') == 'master_admin':
        return
    scope_unit_id = actor_operational_unit_id(connection, actor)
    if scope_unit_id and int(purchase_request['unit_id']) != int(scope_unit_id):
        raise PermissionError('Requisição fora da unidade operacional do usuário.')
    purchase_scope_units = get_actor_purchase_unit_scope(connection, actor)
    if actor.get('role') in ('buyer', 'approver'):
        if not purchase_scope_units:
            raise PermissionError('Usuário sem unidade de compras vinculada.')
        if int(purchase_request['unit_id']) not in set(int(uid) for uid in purchase_scope_units):
            raise PermissionError('Requisição fora das unidades de compras vinculadas ao usuário.')


def ensure_purchase_workflow_permission(actor, permission_group):
    if permission_group == 'approve':
        # Administrador Local atua como Requisitante no fluxo de compras e não
        # pode aprovar/reprovar a própria requisição nem usar ferramentas de aprovador.
        ensure_permission(actor, PERM_PO_APPROVE)
        return
    ensure_permission(actor, PERM_PURCHASE_REQUESTS_UPDATE)



def _format_purchase_item_decision_comment(item, decision, totals=None):
    quantity = int(item.get('quantity_requested') or item.get('quantity') or 1)
    unit_price = float(item.get('unit_price') or 0)
    total_price = float(item.get('total_price') or (unit_price * quantity))
    parts = [
        f"Item #{item.get('id')}",
        f"EPI: {item.get('epi_name') or item.get('epi_display_name') or ''}",
        f"CA: {item.get('ca') or item.get('epi_ca') or ''}",
        f"Qtd: {quantity}",
        f"Valor unitário: {unit_price:.2f}",
        f"Total item: {total_price:.2f}",
        f"Decisão: {'Aprovado' if decision.get('approved') else 'Reprovado'}",
    ]
    if not decision.get('approved'):
        parts.append(f"Motivo: {decision.get('reason') or ''}")
        if decision.get('comment'):
            parts.append(f"Observação: {decision.get('comment')}")
    if totals:
        parts.extend([
            f"Total aprovado: {float(totals.get('approved_total') or 0):.2f}",
            f"Total reprovado: {float(totals.get('rejected_total') or 0):.2f}",
            f"Total geral: {float(totals.get('grand_total') or 0):.2f}",
        ])
    return ' | '.join(parts)


def apply_purchase_request_item_approval(connection, actor, pr_id, payload, ip_address='', transition=None):
    purchase_request = connection.execute('SELECT * FROM purchase_requests WHERE id = ?', (int(pr_id),)).fetchone()
    if not purchase_request:
        raise ValueError('Requisição não encontrada.')
    pr = row_to_dict(purchase_request)
    ensure_purchase_request_action_scope(connection, actor, pr)
    if transition is None:
        transition = resolve_purchase_transition(pr.get('status'), 'approve')
    ensure_purchase_workflow_permission(actor, transition.get('permission'))
    item_rows = connection.execute(
        'SELECT pri.*, e.name AS epi_display_name, e.ca AS epi_ca, u.name AS unit_name '
        'FROM purchase_request_items pri '
        'JOIN epis e ON e.id = pri.epi_id '
        'JOIN units u ON u.id = pri.unit_id '
        'WHERE pri.purchase_request_id = ? ORDER BY pri.id',
        (int(pr_id),)
    ).fetchall()
    items = [row_to_dict(row) for row in item_rows]
    decisions, status_to, totals = normalize_purchase_item_approval_decisions(items, payload)
    now = datetime.now(UTC).isoformat()
    summary_parts = []
    for decision in decisions:
        item = decision['item']
        item_id = int(decision['item_id'])
        previous_status = str(item.get('status') or '')
        new_status = 'approved' if decision.get('approved') else 'rejected'
        comment = _format_purchase_item_decision_comment(item, decision)
        if decision.get('approved'):
            connection.execute(
                """
                UPDATE purchase_request_items
                SET status = 'approved', quantity_approved = quantity_requested,
                    rejection_reason = '', rejection_comment = '',
                    approval_decided_by_user_id = ?, approval_decided_by_name = ?, approval_decided_at = ?,
                    updated_at = ?
                WHERE purchase_request_id = ? AND id = ?
                """,
                (int(actor['id']), actor['full_name'], now, now, int(pr_id), item_id),
            )
        else:
            note_suffix = f"Reprovado: {decision.get('reason') or ''}"
            if decision.get('comment'):
                note_suffix += f" — {decision.get('comment')}"
            connection.execute(
                """
                UPDATE purchase_request_items
                SET status = 'rejected', quantity_approved = 0,
                    rejection_reason = ?, rejection_comment = ?,
                    approval_decided_by_user_id = ?, approval_decided_by_name = ?, approval_decided_at = ?,
                    notes = trim(COALESCE(NULLIF(notes, ''), '') || CASE WHEN COALESCE(NULLIF(notes, ''), '') = '' THEN '' ELSE ' | ' END || ?),
                    updated_at = ?
                WHERE purchase_request_id = ? AND id = ?
                """,
                (decision.get('reason') or '', decision.get('comment') or '', int(actor['id']), actor['full_name'], now, note_suffix, now, int(pr_id), item_id),
            )
        _record_purchase_event(
            connection,
            int(pr['company_id']),
            'purchase_request_item',
            item_id,
            'item_approval_decision',
            previous_status,
            new_status,
            comment,
            int(actor['id']),
            actor['full_name'],
            ip_address,
            actor.get('role') or '',
            decision.get('reason') or '',
            'closed' if decision.get('approved') else 'rejected',
        )
        summary_parts.append(_format_purchase_item_decision_comment(item, decision))
    connection.execute(
        'UPDATE purchase_requests SET status = ?, updated_at = ? WHERE id = ?',
        (status_to, now, int(pr_id))
    )
    request_comment = 'Decisão por item | Resumo da aprovação por item: ' + ' || '.join(summary_parts)
    request_comment += (
        f" || Totais: aprovado {totals['approved_total']:.2f} ({totals['approved_quantity']} un.), "
        f"reprovado {totals['rejected_total']:.2f} ({totals['rejected_quantity']} un.), "
        f"geral {totals['grand_total']:.2f}"
    )
    _record_purchase_event(
        connection,
        int(pr['company_id']),
        'purchase_request',
        int(pr_id),
        'approve',
        transition['status_from'],
        status_to,
        request_comment,
        int(actor['id']),
        actor['full_name'],
        ip_address,
        actor.get('role') or '',
        '',
        'closed',
    )
    structured_log(
        'info',
        'purchase.workflow.item_approval_completed',
        purchase_request_id=int(pr_id),
        status_from=transition['status_from'],
        status_to=status_to,
        actor_user_id=int(actor['id']),
        actor_role=actor.get('role'),
        approved_count=totals['approved_count'],
        rejected_count=totals['rejected_count'],
        approved_total=totals['approved_total'],
        rejected_total=totals['rejected_total'],
    )
    return {
        'ok': True,
        'id': int(pr_id),
        'status': status_to,
        'status_label': PURCHASE_WORKFLOW_STATUS_LABELS.get(status_to, status_to),
        'action': 'approve',
        'totals': totals,
        'decisions': [
            {
                'item_id': int(decision['item_id']),
                'status': 'approved' if decision.get('approved') else 'rejected',
                'reason': decision.get('reason') or '',
                'comment': decision.get('comment') or '',
            }
            for decision in decisions
        ],
    }

def apply_purchase_request_workflow_action(connection, actor, pr_id, payload, ip_address=''):
    purchase_request = connection.execute('SELECT * FROM purchase_requests WHERE id = ?', (int(pr_id),)).fetchone()
    if not purchase_request:
        raise ValueError('Requisição não encontrada.')
    pr = row_to_dict(purchase_request)
    ensure_purchase_request_action_scope(connection, actor, pr)
    events = [row_to_dict(row) for row in connection.execute(
        'SELECT * FROM purchase_events WHERE entity_type = ? AND entity_id = ? ORDER BY created_at DESC, id DESC',
        ('purchase_request', int(pr_id))
    ).fetchall()]
    transition = resolve_purchase_transition(
        pr.get('status'),
        payload.get('action'),
        requester_review_origin=latest_requester_review_origin(events),
    )
    ensure_purchase_workflow_permission(actor, transition.get('permission'))
    reason, comment = validate_purchase_transition_payload(
        transition,
        reason=payload.get('reason'),
        comment=payload.get('comment'),
    )
    requested_changes = payload.get('requested_changes') or []
    if isinstance(requested_changes, str):
        requested_changes = [requested_changes]
    affected_item_ids = [int(item_id) for item_id in (payload.get('item_ids') or []) if str(item_id).isdigit()]
    if affected_item_ids:
        requested_changes.append('Itens afetados: ' + ', '.join(str(item_id) for item_id in affected_item_ids))
    event_comment = serialize_purchase_event_comment(reason, comment, requested_changes)
    now = datetime.now(UTC).isoformat()
    status_to = transition['status_to']
    if transition['action'] == 'approve':
        return apply_purchase_request_item_approval(connection, actor, pr_id, payload, ip_address, transition)
    connection.execute(
        'UPDATE purchase_requests SET status = ?, updated_at = ? WHERE id = ?',
        (status_to, now, int(pr_id))
    )
    _record_purchase_event(
        connection,
        int(pr['company_id']),
        'purchase_request',
        int(pr_id),
        transition['action'],
        transition['status_from'],
        status_to,
        event_comment,
        int(actor['id']),
        actor['full_name'],
        ip_address,
        actor.get('role') or '',
        reason,
        transition.get('destination') or '',
    )
    structured_log(
        'info',
        'purchase.workflow.transition',
        purchase_request_id=int(pr_id),
        action=transition['action'],
        status_from=transition['status_from'],
        status_to=transition['status_to'],
        actor_user_id=int(actor['id']),
        actor_role=actor.get('role'),
        destination=transition.get('destination') or '',
    )
    if transition.get('destination') == 'buyer':
        structured_log('info', 'purchase.workflow.notify_buyer', purchase_request_id=int(pr_id), reason=reason)
    elif transition.get('destination') == 'requester':
        structured_log('info', 'purchase.workflow.notify_requester', purchase_request_id=int(pr_id), reason=reason)
    elif transition.get('destination') == 'approver':
        structured_log('info', 'purchase.workflow.notify_approver', purchase_request_id=int(pr_id))
    return {
        'ok': True,
        'id': int(pr_id),
        'status': status_to,
        'status_label': PURCHASE_WORKFLOW_STATUS_LABELS.get(status_to, status_to),
        'action': transition['action'],
    }



def approved_purchase_request_items_for_po(connection, pr_id, items):
    approved_rows = connection.execute(
        "SELECT * FROM purchase_request_items WHERE purchase_request_id = ? AND status = 'approved'",
        (int(pr_id),),
    ).fetchall()
    approved_items = {int(row['id']): row_to_dict(row) for row in approved_rows}
    if not approved_items:
        raise ValueError('Requisição sem itens aprovados para gerar PO.')
    for item in items or []:
        pr_item_id = int(item['purchase_request_item_id']) if item.get('purchase_request_item_id') else 0
        if not pr_item_id:
            raise ValueError('PO vinculada a requisição aprovada deve informar o item aprovado da requisição.')
        if pr_item_id not in approved_items:
            raise ValueError('Somente itens aprovados podem ser incluídos na PO.')
    return approved_items

def _purchase_request_items_signature(items):
    normalized = []
    for item in items or []:
        normalized.append((
            int(item.get('epi_id') or 0),
            int(item.get('quantity_requested') or item.get('quantity') or 1),
            int(item.get('employee_id') or 0),
            str(item.get('origin') or 'stock_minimum'),
            str(item.get('glove_size') or 'N/A'),
            str(item.get('size') or 'N/A'),
            str(item.get('uniform_size') or 'N/A'),
        ))
    return sorted(normalized)


def find_recent_duplicate_purchase_request(connection, actor, unit_id, title, items, now):
    cutoff = (datetime.fromisoformat(now) - timedelta(seconds=60)).isoformat()
    expected_signature = _purchase_request_items_signature(items)
    candidates = connection.execute(
        "SELECT * FROM purchase_requests WHERE company_id = ? AND unit_id = ? AND created_by_user_id = ? AND title = ? AND created_at >= ? ORDER BY id DESC LIMIT 5",
        (int(actor['company_id']), int(unit_id), int(actor['id']), title, cutoff),
    ).fetchall()
    for candidate in candidates:
        rows = connection.execute('SELECT epi_id, quantity_requested, employee_id, origin, glove_size, size, uniform_size FROM purchase_request_items WHERE purchase_request_id = ?', (int(candidate['id']),)).fetchall()
        existing = [row_to_dict(row) for row in rows]
        if _purchase_request_items_signature(existing) == expected_signature:
            return int(candidate['id'])
    return None


class EpiHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(BASE_DIR), **kwargs)

    def _apply_default_response_headers(self):
        parsed = urlparse(self.path)
        path = parsed.path or ''
        origin = os.environ.get('CORS_ALLOW_ORIGIN', '*').strip() or '*'

        # CORS headers
        self.send_header('Access-Control-Allow-Origin', origin)
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, PATCH, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Authorization, Content-Type, Accept, X-Requested-With')
        if origin != '*':
            self.send_header('Access-Control-Allow-Credentials', 'true')

        # Default cache behavior for API and versioned static entrypoints
        if path.startswith('/api/') or path.startswith('/health') or path.startswith('/ready') or path in ('/', '/index.html') or path.endswith('.js') or path.endswith('.css'):
            self.send_header('Cache-Control', 'no-store, max-age=0, must-revalidate')
            self.send_header('Pragma', 'no-cache')
            self.send_header('Expires', '0')

    def end_headers(self):
        self._apply_default_response_headers()
        return super().end_headers()

    def guess_type(self, path):
        ctype = super().guess_type(path)
        if isinstance(ctype, str) and (ctype.startswith('text/') or 'javascript' in ctype):
            if 'charset' not in ctype:
                ctype += '; charset=utf-8'
        return ctype

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header('Content-Length', '0')
        return self.end_headers()

    def _is_static_request(self, path):
        request_path = str(path or '')
        if request_path in ('/', '/index.html', '/styles.css', '/app.js', '/error-monitor.js'):
            return True
        if request_path.startswith('/assets/') or request_path.startswith('/images/') or request_path.startswith('/fonts/'):
            return True
        if request_path.startswith('/fragments/'):
            return True
        return False

    def _require_bootstrap_ready(self, path):
        gate_path = self.path if path is None else str(path)
        parsed = urlparse(gate_path)
        normalized_path = str(parsed.path or '').rstrip('/') or '/'
        if not normalized_path.startswith('/api/'):
            return True
        state = _get_bootstrap_state()
        allowed = normalized_path in BOOTSTRAP_READY_EXEMPT_PATHS
        structured_log(
            'info',
            'bootstrap.gate.check',
            raw_path=self.path,
            normalized_path=normalized_path,
            method=self.command,
            allowed=allowed,
            ready=bool(state.get('ready')),
        )
        if allowed:
            return True
        if state.get('ready'):
            return True
        return send_json(
            self,
            503,
            {
                'ok': False,
                'error': {
                    'code': state.get('error_code') or 'DB_BOOTSTRAP_NOT_READY',
                    'message': 'Serviço indisponível: bootstrap do banco pendente ou com falha.',
                    'details': {
                        'kind': state.get('error_kind') or 'bootstrap_not_ready',
                        'detail': state.get('error_message') or 'A migração/validação de schema ainda não concluiu.',
                        'ready': False,
                        'started_at': state.get('started_at') or '',
                        'completed_at': state.get('completed_at') or '',
                    },
                }
            },
        )


    def do_GET(self):
        parsed = urlparse(self.path)
        if self._is_static_request(parsed.path):
            if parsed.path == '/':
                self.path = '/index.html'
            return super().do_GET()
        if parsed.path.startswith('/api/') and not self._require_bootstrap_ready(parsed.path):
            return

        if parsed.path in {'/health', '/health/live'}:
            status_code, payload = runtime_probe_response('live')
            payload.update(static_asset_diagnostics())
            return send_json(self, status_code, payload)

        if parsed.path in {'/ready', '/health/ready'}:
            status_code, payload = runtime_probe_response('ready')
            payload.update(static_asset_diagnostics())
            return send_json(self, status_code, payload)

        if parsed.path == '/':
            self.path = '/index.html'

            if parsed.path == '/api/ficha-config':
                with closing(get_connection()) as connection:
                    actor = authorize_action(connection, resolve_actor_user_id(self, parsed), PERM_SETTINGS_VIEW)
                    config = get_ficha_config(connection, actor['company_id'])
                    return send_json(self, 200, config)

            if parsed.path == '/api/configuration-rules':
                with closing(get_connection()) as connection:
                    actor = authorize_action(connection, resolve_actor_user_id(self, parsed), PERM_SETTINGS_VIEW)
                    require_configuration_admin(actor)
                    rules = get_configuration_rules(connection, actor['company_id'])
                    return send_json(self, 200, {'rules': rules})

            if parsed.path == '/api/configuration-framework':
                with closing(get_connection()) as connection:
                    actor = authorize_action(connection, resolve_actor_user_id(self, parsed), PERM_SETTINGS_VIEW)
                    require_master_admin(actor, 'Somente Administrador Master pode acessar o framework de hardening.')
                    framework = get_configuration_framework(connection, actor['company_id'])
                    return send_json(self, 200, {'framework': framework})

            if parsed.path == '/api/rules-engine/diagnostics':
                with closing(get_connection()) as connection:
                    actor = authorize_action(connection, resolve_actor_user_id(self, parsed), PERM_SETTINGS_VIEW)
                    require_master_admin(actor, 'Somente Administrador Master pode consultar diagnósticos do novo motor de regras.')
                    query = parse_qs(parsed.query)
                    endpoint_name = str(query.get('endpoint', [''])[0] or '').strip()
                    report_type = str(query.get('report_type', [''])[0] or '').strip()
                    unit_id = int(query.get('unit_id', ['0'])[0] or 0)
                    jv_context = str(query.get('jv_context', ['outside_jv'])[0] or 'outside_jv')
                    framework = get_configuration_framework(connection, actor['company_id'])
                    context = build_rule_context(actor, endpoint=endpoint_name, unit_id=unit_id or None, jv_context=jv_context)
                    decision = evaluate_rule_decision(context, framework, report_type=report_type)
                    return send_json(self, 200, {'enabled': should_enable_new_engine(context, framework), 'decision': decision})

            if parsed.path.startswith('/api/ficha-epi/') and parsed.path.endswith('.html'):
                # /api/ficha-epi/<employee_id>.html
                try:
                    parts = parsed.path.strip('/').split('/')
                    employee_id = int(parts[2].replace('.html', ''))
                    with closing(get_connection()) as connection:
                        actor = authorize_action(connection, resolve_actor_user_id(self, parsed), 'fichas:view')
                        employee = get_employee_by_id(connection, employee_id)
                        if not employee:
                            raise ValueError('Colaborador não encontrado.')
                        ensure_actor_employee_scope(connection, actor, employee)
                        html_content = build_ficha_epi_html(connection, employee_id, actor)
                        body = html_content.encode('utf-8')
                        self.send_response(200)
                        self.send_header('Content-Type', 'text/html; charset=utf-8')
                        self.send_header('Content-Length', str(len(body)))
                        self.end_headers()
                        self.wfile.write(body)
                        return
                except PermissionError as exc:
                    return send_json(self, 403, {'error': str(exc)})
                except ValueError as exc:
                    return send_json(self, 400, {'error': str(exc)})
                except Exception as exc:
                    return send_json(self, 500, {'error': str(exc)})



            if parsed.path == '/api/devolutions/open-deliveries':
                with closing(get_connection()) as connection:
                    actor = authorize_action(connection, resolve_actor_user_id(self, parsed), 'deliveries:view')
                    query = parse_qs(parsed.query)
                    employee_id = str(query.get('employee_id', [''])[0] or '').strip()
                    epi_id = str(query.get('epi_id', [''])[0] or '').strip()
                    unit_id = str(query.get('unit_id', [''])[0] or '').strip()
                    if not employee_id or not epi_id:
                        raise ValueError('Parâmetros employee_id e epi_id são obrigatórios.')
                    items = fetch_open_deliveries_for_devolution(connection, actor, int(employee_id), int(epi_id), unit_id=unit_id or None)
                    return send_json(self, 200, {'items': items, 'total_open': len(items)})

            if parsed.path == '/api/devolutions':
                with closing(get_connection()) as connection:
                    actor = authorize_action(connection, resolve_actor_user_id(self, parsed), 'stock:view')
                    q = parse_qs(parsed.query)
                    filters = {k: q[k][0] for k in ('employee_id','epi_id','delivery_id') if q.get(k)}
                    return send_json(self, 200, {'items': fetch_devolutions(connection, actor, filters)})


            return super().do_GET()

        elif parsed.path.startswith('/api/epi-replacement-days/'):
            try:
                ep_parts = parsed.path.strip('/').split('/')
                epi_id = int(ep_parts[-1])
                connection = get_connection()
                cursor = connection.cursor()
                cursor.execute(
                    'SELECT default_replacement_days, manufacturer_validity_months FROM epis WHERE id = ?',
                    (epi_id,)
                )
                row = cursor.fetchone()
                cursor.close()
                if not row:
                    return send_json(self, 200, {'days': None})
                days = row[0]
                months = row[1]
                source = None
                if days and int(days) > 0:
                    source = 'epi_rule'
                elif months:
                    try:
                        days = int(float(str(months))) * 30
                        source = 'manufacturer_validity'
                    except Exception:
                        days = None
                return send_json(self, 200, {'days': days, 'source': source})
            except Exception as exc:
                return send_json(self, 500, {'error': str(exc), 'days': None})
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
                actor_user_id = None
                actor = None
                try:
                    actor_user_id = resolve_actor_user_id(self, parsed)
                    with closing(get_connection()) as connection:
                        actor = authorize_action(
                            connection,
                            actor_user_id,
                            'dashboard:view'
                        )
                        structured_log(
                            'info',
                            'bootstrap.started',
                            actor_user_id=actor_user_id,
                            user_role=actor.get('role'),
                            company_id=actor.get('company_id'),
                            path=parsed.path,
                        )
                        payload = build_bootstrap(connection, actor)
                        structured_log(
                            'info',
                            'bootstrap.completed',
                            actor_user_id=actor_user_id,
                            user_role=actor.get('role'),
                            company_id=actor.get('company_id'),
                            path=parsed.path,
                            degraded=bool(payload.get('degraded')),
                            failed_sections=[item.get('section') for item in payload.get('bootstrap_warnings', [])],
                        )
                        return send_json(self, 200, payload)
                except PermissionError as exc:
                    structured_log(
                        'warning',
                        'bootstrap.auth_failed',
                        actor_user_id=actor_user_id,
                        user_role=actor.get('role') if actor else '',
                        company_id=actor.get('company_id') if actor else '',
                        path=parsed.path,
                        error=str(exc),
                    )
                    return forbidden(self, str(exc))

            if parsed.path == '/api/commercial-contract':
                with closing(get_connection()) as connection:
                    actor = authorize_action(connection, resolve_actor_user_id(self, parsed), PERM_COMPANIES_VIEW)
                    actor = authorize_action(connection, resolve_actor_user_id(self, parsed), PERM_COMMERCIAL_VIEW)
                    query = parse_qs(parsed.query)
                    company_id = int(query.get('company_id', ['0'])[0] or 0)
                    if not company_id:
                        raise ValueError('company_id é obrigatório.')
                    contract = get_or_create_commercial_contract(connection, actor, company_id)
                    connection.commit()
                    return send_json(self, 200, {'contract': contract})

            if parsed.path == '/api/commercial-contract.pdf':
                with closing(get_connection()) as connection:
                    actor = authorize_action(connection, resolve_actor_user_id(self, parsed), PERM_COMPANIES_VIEW)
                    actor = authorize_action(connection, resolve_actor_user_id(self, parsed), PERM_COMMERCIAL_VIEW)
                    query = parse_qs(parsed.query)
                    company_id = int(query.get('company_id', ['0'])[0] or 0)
                    if not company_id:
                        raise ValueError('company_id é obrigatório.')
                    contract = get_or_create_commercial_contract(connection, actor, company_id)
                    base64_payload = contract.get('signed_pdf_base64') or contract.get('generated_pdf_base64')
                    pdf_bytes = base64.b64decode(str(base64_payload).encode('ascii')) if base64_payload else build_commercial_contract_pdf(connection, actor, company_id)
                    return send_bytes(self, 200, 'application/pdf', pdf_bytes)

            if parsed.path == '/api/commercial-contract/file':
                with closing(get_connection()) as connection:
                    actor = authorize_action(connection, resolve_actor_user_id(self, parsed), PERM_COMMERCIAL_VIEW)
                    query = parse_qs(parsed.query)
                    company_id = int(query.get('company_id', ['0'])[0] or 0)
                    if not company_id:
                        raise ValueError('company_id é obrigatório.')
                    file_kind = str(query.get('kind', ['generated'])[0] or 'generated').strip().lower()
                    contract = get_or_create_commercial_contract(connection, actor, company_id)
                    base64_payload = contract.get('signed_pdf_base64') if file_kind == 'signed' else contract.get('generated_pdf_base64')
                    if not base64_payload:
                        raise ValueError('Arquivo não disponível para este contrato.')
                    binary = base64.b64decode(str(base64_payload).encode('ascii'))
                    filename = contract.get('signed_file_name') if file_kind == 'signed' else f"contrato-{company_id}-gerado.pdf"
                    content_type = contract.get('signed_file_mime') if file_kind == 'signed' else 'application/pdf'
                    return send_bytes(self, 200, content_type or 'application/pdf', binary, filename or 'contrato.pdf')

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

            if parsed.path == '/api/ocr/runtime-status':
                with closing(get_connection()) as connection:
                    authorize_action(
                        connection,
                        resolve_actor_user_id(self, parsed),
                        'stock:view'
                    )
                    return send_json(self, 200, get_ocr_runtime_status())

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
                    epis = fetch_epis(connection, actor if actor['role'] != 'master_admin' else None, None)
                    target_unit_jv_name = get_unit_active_jv_name(connection, unit_filter) if unit_filter else ''
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
                        # Filtro C1+D1+E3: oculta GLOBAL quando unidade em JV; oculta JV de outras JVs
                        if unit_filter and not is_epi_visible_for_unit(
                            epi_unit_id=epi.get('unit_id'),
                            epi_joint_venture_name=epi.get('active_joinventure'),
                            target_unit_id=unit_filter,
                            target_unit_joint_venture_name=target_unit_jv_name,
                        ):
                            continue
                        stock_unit_id = int(unit_filter or 0)
                        stock_row = get_unit_stock(connection, int(epi['company_id']), stock_unit_id, int(epi['id'])) if stock_unit_id else None
                        item = dict(epi)
                        item['stock'] = int((stock_row or {}).get('quantity') or (item.get('stock') or 0))
                        size_rows = fetch_epi_size_balance(connection, int(epi['company_id']), stock_unit_id, int(epi['id'])) if stock_unit_id else []
                        item['size_balances'] = size_rows
                        items.append(item)
                    items = canary_evaluate_visibility_dataset(
                        connection,
                        actor,
                        endpoint_name='/api/stock/epis',
                        dataset_name='epis',
                        legacy_items=items,
                    )
                    return send_json(self, 200, {'items': items})

            if parsed.path == '/api/stock/lookup-qr':
                with closing(get_connection()) as connection:
                    actor = authorize_action(
                        connection,
                        resolve_actor_user_id(self, parsed),
                        'stock:view'
                    )
                    query = parse_qs(parsed.query)
                    qr_code = str(query.get('qr_code', [''])[0]).strip()
                    if not qr_code:
                        raise ValueError('QR informado é obrigatório.')
                    parsed_qr = parse_stock_qr_lookup_value(qr_code)
                    query_stock_item_id = parse_int_flexible(query.get('stock_item_id', [''])[0], 0) or parsed_qr.get('stock_item_id') or 0
                    company_filter = actor['company_id'] if actor['role'] != 'master_admin' else query.get('company_id', [''])[0]
                    scope_unit_id = actor_operational_unit_id(connection, actor)
                    if actor.get('role') in ('admin', 'user') and not scope_unit_id:
                        raise PermissionError('Perfil sem unidade operacional ativa para consultar estoque.')
                    unit_filter = scope_unit_id or query.get('unit_id', [''])[0]
                    if not unit_filter:
                        raise ValueError('Unidade é obrigatória para validar o QR.')
                    company_scope_id = int(company_filter or 0)
                    if not company_scope_id:
                        unit_row = get_unit_by_id(connection, int(unit_filter))
                        company_scope_id = int(unit_row['company_id']) if unit_row else 0
                    requested_qr_code = str(parsed_qr.get('qr_code_value') or '').strip()
                    query_sql = (
                        'SELECT esi.id, esi.company_id, esi.unit_id, esi.epi_id, esi.glove_size, esi.size, esi.uniform_size, '
                        'esi.lot_code, esi.qr_code_value, esi.status, esi.reprint_count, esi.label_measure, '
                        'esi.label_printer_name, esi.label_print_format, epis.name AS epi_name, epis.purchase_code, '
                        'epis.unit_measure, units.name AS unit_name '
                        'FROM epi_stock_items esi '
                        'JOIN epis ON epis.id = esi.epi_id '
                        'JOIN units ON units.id = esi.unit_id '
                        'WHERE esi.company_id = ? AND esi.unit_id = ?'
                    )
                    query_params = [int(company_scope_id), int(unit_filter)]
                    if requested_qr_code:
                        query_sql += ' AND esi.qr_code_value = ?'
                        query_params.append(requested_qr_code)
                    if int(query_stock_item_id) > 0:
                        query_sql += ' AND esi.id = ?'
                        query_params.append(int(query_stock_item_id))
                    query_sql += ' ORDER BY esi.id DESC LIMIT 1'
                    stock_item = connection.execute(query_sql, tuple(query_params)).fetchone()
                    if not stock_item:
                        raise ValueError('QR não encontrado com correspondência exata no estoque da unidade.')
                    return send_json(self, 200, {'stock_item': row_to_dict(stock_item)})

            if parsed.path == '/api/stock/available-items':
                with closing(get_connection()) as connection:
                    actor = authorize_action(
                        connection,
                        resolve_actor_user_id(self, parsed),
                        'stock:view'
                    )
                    query = parse_qs(parsed.query)
                    epi_id = parse_int_flexible(query.get('epi_id', [''])[0], 0)
                    if epi_id <= 0:
                        raise ValueError('EPI é obrigatório para listar QRs disponíveis.')
                    company_filter = actor['company_id'] if actor['role'] != 'master_admin' else query.get('company_id', [''])[0]
                    scope_unit_id = actor_operational_unit_id(connection, actor)
                    if actor.get('role') in ('admin', 'user') and not scope_unit_id:
                        raise PermissionError('Perfil sem unidade operacional ativa para consultar estoque.')
                    unit_filter = scope_unit_id or query.get('unit_id', [''])[0]
                    if not unit_filter:
                        raise ValueError('Unidade é obrigatória para listar QRs disponíveis.')
                    company_scope_id = int(company_filter or 0)
                    if not company_scope_id:
                        unit_row = get_unit_by_id(connection, int(unit_filter))
                        company_scope_id = int(unit_row['company_id']) if unit_row else 0
                    items = connection.execute(
                        (
                            'SELECT esi.id, esi.qr_code_value, esi.epi_id, epis.name AS epi_name, esi.status, '
                            'esi.glove_size, esi.size, esi.uniform_size '
                            'FROM epi_stock_items esi '
                            'JOIN epis ON epis.id = esi.epi_id '
                            'WHERE esi.company_id = ? AND esi.unit_id = ? AND esi.epi_id = ? '
                            "AND COALESCE(LOWER(esi.status), 'in_stock') IN ('in_stock', 'available') "
                            "AND COALESCE(esi.qr_code_value, '') != '' "
                            'ORDER BY esi.id ASC'
                        ),
                        (
                            int(company_scope_id),
                            int(unit_filter),
                            int(epi_id),
                        )
                    ).fetchall()
                    return send_json(self, 200, {'items': [row_to_dict(item) for item in items]})

            if parsed.path == '/api/stock/available-items':
                with closing(get_connection()) as connection:
                    actor = authorize_action(
                        connection,
                        resolve_actor_user_id(self, parsed),
                        'stock:view'
                    )
                    query = parse_qs(parsed.query)
                    epi_id = parse_int_flexible(query.get('epi_id', [''])[0], 0)
                    if epi_id <= 0:
                        raise ValueError('EPI é obrigatório para listar QRs disponíveis.')
                    company_filter = actor['company_id'] if actor['role'] != 'master_admin' else query.get('company_id', [''])[0]
                    scope_unit_id = actor_operational_unit_id(connection, actor)
                    if actor.get('role') in ('admin', 'user') and not scope_unit_id:
                        raise PermissionError('Perfil sem unidade operacional ativa para consultar estoque.')
                    unit_filter = scope_unit_id or query.get('unit_id', [''])[0]
                    if not unit_filter:
                        raise ValueError('Unidade é obrigatória para listar QRs disponíveis.')
                    company_scope_id = int(company_filter or 0)
                    if not company_scope_id:
                        unit_row = get_unit_by_id(connection, int(unit_filter))
                        company_scope_id = int(unit_row['company_id']) if unit_row else 0
                    items = connection.execute(
                        (
                            'SELECT esi.id, esi.qr_code_value, esi.epi_id, epis.name AS epi_name, esi.status, '
                            'esi.glove_size, esi.size, esi.uniform_size '
                            'FROM epi_stock_items esi '
                            'JOIN epis ON epis.id = esi.epi_id '
                            'WHERE esi.company_id = ? AND esi.unit_id = ? AND esi.epi_id = ? '
                            "AND COALESCE(LOWER(esi.status), 'in_stock') IN ('in_stock', 'available') "
                            "AND COALESCE(esi.qr_code_value, '') != '' "
                            'ORDER BY esi.id ASC'
                        ),
                        (
                            int(company_scope_id),
                            int(unit_filter),
                            int(epi_id),
                        )
                    ).fetchall()
                    return send_json(self, 200, {'items': [row_to_dict(item) for item in items]})

            if parsed.path == '/api/stock/movements/report':
                with closing(get_connection()) as connection:
                    actor = authorize_action(
                        connection,
                        resolve_actor_user_id(self, parsed),
                        'stock:view'
                    )
                    query = parse_qs(parsed.query)
                    company_filter = actor['company_id'] if actor['role'] != 'master_admin' else query.get('company_id', [''])[0]
                    scope_unit_id = actor_operational_unit_id(connection, actor)
                    purchase_scope = get_actor_purchase_unit_scope(connection, actor)
                    clauses, params = [], []
                    if company_filter:
                        clauses.append('sm.company_id = ?')
                        params.append(int(company_filter))
                    if scope_unit_id:
                        clauses.append('sm.unit_id = ?')
                        params.append(int(scope_unit_id))
                    elif purchase_scope:
                        ph = ','.join(['?'] * len(purchase_scope))
                        clauses.append(f'sm.unit_id IN ({ph})')
                        params.extend(purchase_scope)
                    year_filter = query.get('year', [''])[0].strip()
                    month_filter = query.get('month', [''])[0].strip()
                    epi_filter = query.get('epi_id', [''])[0].strip()
                    movement_type_filter = query.get('movement_type', [''])[0].strip()
                    source_type_filter = query.get('source_type', [''])[0].strip()
                    unit_filter_q = query.get('unit_id', [''])[0].strip()
                    if year_filter:
                        clauses.append("substr(sm.created_at, 1, 4) = ?")
                        params.append(year_filter)
                    if month_filter:
                        clauses.append("substr(sm.created_at, 6, 2) = ?")
                        params.append(month_filter.zfill(2))
                    if epi_filter:
                        clauses.append('sm.epi_id = ?')
                        params.append(int(epi_filter))
                    if movement_type_filter:
                        clauses.append('sm.movement_type = ?')
                        params.append(movement_type_filter)
                    if source_type_filter:
                        clauses.append('sm.source_type = ?')
                        params.append(source_type_filter)
                    if unit_filter_q and not scope_unit_id:
                        clauses.append('sm.unit_id = ?')
                        params.append(int(unit_filter_q))
                    final_where = f"WHERE {' AND '.join(clauses)}" if clauses else ''
                    rows = connection.execute(
                        (
                            'SELECT sm.id, sm.company_id, sm.unit_id, sm.epi_id, sm.movement_type, '
                            'sm.quantity, sm.previous_stock, sm.new_stock, sm.source_type, sm.source_id, '
                            'sm.notes, sm.actor_name, sm.created_at, '
                            'sm.glove_size, sm.size, sm.uniform_size, '
                            'e.name AS epi_name, e.ca, e.unit_measure, u.name AS unit_name '
                            'FROM stock_movements sm '
                            'JOIN epis e ON e.id = sm.epi_id '
                            'JOIN units u ON u.id = sm.unit_id '
                            f'{final_where} '
                            'ORDER BY sm.created_at DESC, sm.id DESC '
                            'LIMIT 500'
                        ),
                        tuple(params)
                    ).fetchall()
                    return send_json(self, 200, {'items': [row_to_dict(r) for r in rows]})

            if parsed.path == '/api/report-requests':
                with closing(get_connection()) as connection:
                    actor = authorize_action(connection, resolve_actor_user_id(self, parsed), PERM_STOCK_VIEW)
                    company_id = int(actor['company_id'])
                    scope_unit_id = actor_operational_unit_id(connection, actor)
                    purchase_scope = get_actor_purchase_unit_scope(connection, actor)
                    clauses = ['rr.company_id = ?']
                    params = [company_id]
                    if scope_unit_id:
                        clauses.append('rr.unit_id = ?')
                        params.append(int(scope_unit_id))
                    elif purchase_scope:
                        ph = ','.join(['?'] * len(purchase_scope))
                        clauses.append(f'rr.unit_id IN ({ph})')
                        params.extend(purchase_scope)
                    where = f"WHERE {' AND '.join(clauses)}"
                    rows = connection.execute(
                        f'SELECT rr.*, u.name AS unit_name FROM report_requests rr '
                        f'LEFT JOIN units u ON u.id = rr.unit_id '
                        f'{where} ORDER BY rr.created_at DESC LIMIT 100',
                        tuple(params)
                    ).fetchall()
                    return send_json(self, 200, {'items': [row_to_dict(r) for r in rows]})

            if parsed.path == '/api/requests':
                with closing(get_connection()) as connection:
                    actor = authorize_action(
                        connection,
                        resolve_actor_user_id(self, parsed),
                        PERM_PURCHASE_REQUESTS_VIEW
                    )
                    query = parse_qs(parsed.query)
                    company_filter = actor['company_id'] if actor['role'] != 'master_admin' else query.get('company_id', [''])[0]
                    scope_unit_id = actor_operational_unit_id(connection, actor)
                    purchase_scope = get_actor_purchase_unit_scope(connection, actor)
                    clauses, params = [], []
                    if company_filter:
                        clauses.append('r.company_id = ?')
                        params.append(int(company_filter))
                    if scope_unit_id:
                        clauses.append('r.unit_id = ?')
                        params.append(int(scope_unit_id))
                    elif purchase_scope:
                        placeholders = ','.join(['?'] * len(purchase_scope))
                        clauses.append(f'r.unit_id IN ({placeholders})')
                        params.extend(purchase_scope)
                    final_where = f"WHERE {' AND '.join(clauses)}" if clauses else ''
                    rows = connection.execute(
                        (
                            'SELECT r.*, employees.name AS employee_name, employees.employee_id_code, '
                            'employees.sector AS employee_sector, employees.role_name AS employee_role, '
                            'units.name AS unit_name, '
                            'epis.name AS epi_name, epis.ca, epis.unit_measure '
                            'FROM epi_requests r '
                            'JOIN employees ON employees.id = r.employee_id '
                            'JOIN units ON units.id = r.unit_id '
                            'JOIN epis ON epis.id = r.epi_id '
                            f'{final_where} '
                            'ORDER BY r.requested_at DESC, r.id DESC'
                        ),
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
                    scope_unit_id = actor_operational_unit_id(connection, actor)
                    if scope_unit_id:
                        clauses.append('fp.unit_id = ?')
                        params.append(int(scope_unit_id))
                    employee_id = parse_qs(parsed.query).get('employee_id', [''])[0]
                    if employee_id:
                        clauses.append('fp.employee_id = ?')
                        params.append(int(employee_id))
                    final_where = f"WHERE {' AND '.join(clauses)}" if clauses else ''
                    periods = connection.execute(
                        (
                            'SELECT fp.*, employees.name AS employee_name, employees.employee_id_code, units.name AS unit_name, '
                            '(SELECT COUNT(*) FROM epi_ficha_items fi WHERE fi.ficha_period_id = fp.id) AS total_items, '
                            "(SELECT COUNT(*) FROM epi_ficha_items fi WHERE fi.ficha_period_id = fp.id AND COALESCE(fi.item_signature_at, '') = '') AS pending_items "
                            'FROM epi_ficha_periods fp '
                            'JOIN employees ON employees.id = fp.employee_id '
                            'JOIN units ON units.id = fp.unit_id '
                            f'{final_where} '
                            'ORDER BY fp.period_start DESC, fp.id DESC'
                        ),
                        tuple(params)
                    ).fetchall()
                    period_items = [resolve_ficha_period_effective_status(connection, row_to_dict(item)) for item in periods]
                    period_items = [item for item in period_items if is_valid_ficha_period_state(item)]
                    connection.commit()
                    return send_json(self, 200, {'items': period_items})

            if parsed.path == '/api/employee-access':
                token = parse_qs(parsed.query).get('token', [''])[0].strip()
                cpf_last3 = parse_qs(parsed.query).get('cpf_last3', [''])[0].strip()
                with closing(get_connection()) as connection:
                    try:
                        employee_user = resolve_external_employee_context(
                            connection,
                            token,
                            cpf_last3=cpf_last3,
                            ip_address=str(getattr(self, 'client_address', ('',))[0] or ''),
                            user_agent=self.headers.get('User-Agent', ''),
                        )
                    except EmployeePortalAccessDenied as exc:
                        portal_context = exc.portal_context or {}
                        structured_log(
                            'warning',
                            'employee_portal.access_denied',
                            reason=exc.code,
                            link_id=portal_context.get('portal_link_id'),
                            employee_id=portal_context.get('employee_id'),
                            token_prefix=str(token or '')[:12],
                            cpf_last3_received=''.join(ch for ch in str(cpf_last3 or '') if ch.isdigit())[:3],
                        )
                        return send_json(self, 403, {'ok': False, 'error': {'code': exc.code, 'message': exc.message}})
                    employee_id = int(employee_user['employee_id'])
                    deliveries = connection.execute(
                        (
                            'SELECT deliveries.id, deliveries.delivery_date, deliveries.next_replacement_date, deliveries.quantity, deliveries.quantity_label, '
                            'deliveries.signature_name, deliveries.signature_at, deliveries.signature_ip, deliveries.signature_comment, '
                            'deliveries.returned_date, deliveries.returned_condition, '
                            'fi.ficha_period_id, fi.item_signature_name, fi.item_signature_at, '
                            'epis.name AS epi_name, epis.purchase_code, epis.ca, epis.epi_validity_date '
                            'FROM deliveries '
                            'LEFT JOIN epi_ficha_items fi ON fi.delivery_id = deliveries.id '
                            'JOIN epis ON epis.id = deliveries.epi_id '
                            'WHERE deliveries.employee_id = ? '
                            'ORDER BY deliveries.delivery_date DESC, deliveries.id DESC'
                        ),
                        (employee_id,)
                    ).fetchall()
                    fichas = connection.execute(
                        (
                            'SELECT fp.id, fp.period_start, fp.period_end, fp.status, fp.batch_signature_name, fp.batch_signature_at, '
                            '(SELECT COUNT(*) FROM epi_ficha_items fi WHERE fi.ficha_period_id = fp.id) AS total_items, '
                            "(SELECT COUNT(*) FROM epi_ficha_items fi WHERE fi.ficha_period_id = fp.id AND COALESCE(fi.item_signature_at, '') = '') AS pending_items "
                            'FROM epi_ficha_periods fp '
                            'WHERE fp.employee_id = ? '
                            'ORDER BY fp.period_start DESC'
                        ),
                        (employee_id,)
                    ).fetchall()
                    requests = connection.execute(
                        (
                            'SELECT r.id, r.epi_id, r.quantity, r.glove_size, r.size, r.uniform_size, r.status, r.justification, r.requested_at, r.last_updated_at, '
                            'r.rejection_reason, r.postponed_until, r.approver_name, r.approved_at, '
                            'epis.name AS epi_name, epis.purchase_code '
                            'FROM epi_requests r '
                            'JOIN epis ON epis.id = r.epi_id '
                            'WHERE r.employee_id = ? '
                            'ORDER BY r.requested_at DESC, r.id DESC'
                        ),
                        (employee_id,)
                    ).fetchall()
                    feedbacks = connection.execute(
                        (
                            'SELECT f.id, f.epi_id, f.type, f.comfort_rating, f.quality_rating, f.adequacy_rating, f.performance_rating, '
                            'f.comments, f.improvement_suggestion, f.suggested_new_epi_name, f.suggested_new_epi_notes, '
                            'f.status, f.employee_portal_status, f.employee_portal_message, f.created_at, f.updated_at, '
                            'epis.name AS epi_name, epis.purchase_code '
                            'FROM epi_feedbacks f '
                            'LEFT JOIN epis ON epis.id = f.epi_id '
                            'WHERE f.employee_id = ? '
                            'ORDER BY f.created_at DESC, f.id DESC'
                        ),
                        (employee_id,)
                    ).fetchall()

                    available_epis = connection.execute(
                        (
                            'SELECT id, name, purchase_code, ca, unit_measure, glove_size, size, uniform_size '
                            'FROM epis '
                            'WHERE company_id = ? AND active = 1 '
                            'ORDER BY name ASC'
                        ),
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
                    ficha_items = [resolve_ficha_period_effective_status(connection, row_to_dict(item)) for item in fichas]
                    ficha_items = [item for item in ficha_items if is_valid_ficha_period_state(item)]
                    connection.commit()
                    return send_json(
                        self,
                        200,
                        {
                            'employee': employee_user,
                            'deliveries': [row_to_dict(item) for item in deliveries],
                            'fichas': ficha_items,
                            'requests': [row_to_dict(item) for item in requests],
                            'feedbacks': [row_to_dict(item) for item in feedbacks],
                            'available_epis': [row_to_dict(item) for item in available_epis]
                        }
                    )
                
            if parsed.path == '/api/employee-access/pdf':
                token = parse_qs(parsed.query).get('token', [''])[0].strip()
                cpf_last3 = parse_qs(parsed.query).get('cpf_last3', [''])[0].strip()
                with closing(get_connection()) as connection:
                    employee_user = resolve_external_employee_context(
                        connection,
                        token,
                        cpf_last3=cpf_last3,
                        ip_address=str(getattr(self, 'client_address', ('',))[0] or ''),
                        user_agent=self.headers.get('User-Agent', ''),
                    )
                    if not employee_user:
                        raise PermissionError('Token de acesso inválido ou expirado.')
                    if not employee_user.get('linked_employee_id'):
                        employee_user['linked_employee_id'] = employee_user.get('employee_id')
                    pdf_bytes = build_employee_ficha_pdf(connection, employee_user)
                    return send_bytes(self, 200, 'application/pdf', pdf_bytes, f"ficha-epi-{employee_user['employee_id_code']}.pdf")
                
            if parsed.path == '/api/unit-jv/active':
                with closing(get_connection()) as connection:
                    actor = authorize_action(connection, resolve_actor_user_id(self, parsed), 'units:view')
                    query = parse_qs(parsed.query)
                    unit_id = int(query.get('unit_id', ['0'])[0] or 0)
                    if not unit_id:
                        raise ValueError('unit_id é obrigatório.')
                    unit = get_unit_by_id(connection, unit_id)
                    ensure_resource_company(actor, unit, 'Unidade')
                    name = get_unit_active_jv_name(connection, unit_id)
                    return send_json(self, 200, {'unit_id': unit_id, 'active_jv_name': name, 'in_jv': bool(name)})


            if parsed.path == '/api/ficha-config':
                with closing(get_connection()) as connection:
                    actor = authorize_action(connection, resolve_actor_user_id(self, parsed), PERM_SETTINGS_VIEW)
                    config = get_ficha_config(connection, actor['company_id'])
                    return send_json(self, 200, config)

            if parsed.path == '/api/configuration-rules':
                with closing(get_connection()) as connection:
                    actor = authorize_action(connection, resolve_actor_user_id(self, parsed), PERM_SETTINGS_VIEW)
                    require_configuration_admin(actor)
                    rules = get_configuration_rules(connection, actor['company_id'])
                    return send_json(self, 200, {'rules': rules})

            if parsed.path == '/api/configuration-framework':
                with closing(get_connection()) as connection:
                    actor = authorize_action(connection, resolve_actor_user_id(self, parsed), PERM_SETTINGS_VIEW)
                    require_master_admin(actor, 'Somente Administrador Master pode acessar o framework de hardening.')
                    framework = get_configuration_framework(connection, actor['company_id'])
                    return send_json(self, 200, {'framework': framework})

            if parsed.path == '/api/rules-engine/diagnostics':
                with closing(get_connection()) as connection:
                    actor = authorize_action(connection, resolve_actor_user_id(self, parsed), PERM_SETTINGS_VIEW)
                    require_master_admin(actor, 'Somente Administrador Master pode consultar diagnósticos do novo motor de regras.')
                    query = parse_qs(parsed.query)
                    endpoint_name = str(query.get('endpoint', [''])[0] or '').strip()
                    report_type = str(query.get('report_type', [''])[0] or '').strip()
                    unit_id = int(query.get('unit_id', ['0'])[0] or 0)
                    jv_context = str(query.get('jv_context', ['outside_jv'])[0] or 'outside_jv')
                    framework = get_configuration_framework(connection, actor['company_id'])
                    context = build_rule_context(actor, endpoint=endpoint_name, unit_id=unit_id or None, jv_context=jv_context)
                    decision = evaluate_rule_decision(context, framework, report_type=report_type)
                    return send_json(self, 200, {'enabled': should_enable_new_engine(context, framework), 'decision': decision})

            ficha_html_match = re.match(r'^/api/ficha-epi/(\d+)\.html$', parsed.path or '')
            if ficha_html_match:
                employee_id = int(ficha_html_match.group(1))
                query = parse_qs(parsed.query)
                action = str(query.get('action', ['view'])[0] or 'view').strip().lower()
                action = action if action in {'view', 'print'} else 'view'
                with closing(get_connection()) as connection:
                    actor_user_id = resolve_actor_user_id(self, parsed)
                    actor = authorize_action(connection, actor_user_id, 'fichas:view')
                    employee = get_employee_by_id(connection, employee_id)
                    if not employee:
                        raise ValueError('Colaborador não encontrado.')
                    try:
                        ensure_actor_employee_scope(connection, actor, employee)
                    except PermissionError:
                        register_ficha_epi_audit(
                            connection,
                            actor=actor,
                            employee=employee,
                            action='denied',
                            ip_address=str(getattr(self, 'client_address', ('',))[0] or ''),
                            user_agent=self.headers.get('User-Agent', ''),
                        )
                        connection.commit()
                        raise
                    html_content = build_ficha_epi_html(connection, employee_id, actor)
                    register_ficha_epi_audit(
                        connection,
                        actor=actor,
                        employee=employee,
                        action=action,
                        ip_address=str(getattr(self, 'client_address', ('',))[0] or ''),
                        user_agent=self.headers.get('User-Agent', ''),
                    )
                    connection.commit()
                    body = html_content.encode('utf-8')
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/html; charset=utf-8')
                    self.send_header('Content-Length', str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                    return

            ficha_period_html_match = re.match(r'^/api/ficha-epi-period/(\d+)\.html$', parsed.path or '')
            if ficha_period_html_match:
                ficha_period_id = int(ficha_period_html_match.group(1))
                with closing(get_connection()) as connection:
                    actor = authorize_action(connection, resolve_actor_user_id(self, parsed), 'fichas:view')
                    snapshot = ensure_ficha_snapshot_for_period(connection, ficha_period_id, actor)
                    period = connection.execute('SELECT employee_id FROM epi_ficha_periods WHERE id = ?', (ficha_period_id,)).fetchone()
                    employee = get_employee_by_id(connection, int(period['employee_id'])) if period else None
                    if employee:
                        register_ficha_epi_audit(
                            connection,
                            actor=actor,
                            employee=employee,
                            action='snapshot_view',
                            ip_address=str(getattr(self, 'client_address', ('',))[0] or ''),
                            user_agent=self.headers.get('User-Agent', ''),
                        )
                    connection.commit()
                    body = str(snapshot.get('html_content') or '').encode('utf-8')
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/html; charset=utf-8')
                    self.send_header('Content-Length', str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                    return

            if parsed.path == '/api/ficha-epi-audit':
                with closing(get_connection()) as connection:
                    actor = authorize_action(connection, resolve_actor_user_id(self, parsed), PERM_SETTINGS_VIEW)
                    query = parse_qs(parsed.query)
                    filters = {
                        'employee_id': str(query.get('employee_id', [''])[0] or '').strip(),
                        'actor_user_id': str(query.get('actor_user_id', [''])[0] or '').strip(),
                        'action': str(query.get('action', [''])[0] or '').strip(),
                        'date_from': str(query.get('date_from', [''])[0] or '').strip(),
                        'date_to': str(query.get('date_to', [''])[0] or '').strip(),
                    }
                    filters = {k: v for k, v in filters.items() if v}
                    try:
                        items = fetch_ficha_epi_audit_logs(connection, actor, filters)
                    except Exception as error:
                        structured_log(
                            'warning',
                            'ficha.audit.fetch_failed',
                            actor_user_id=actor.get('id'),
                            error=str(error),
                        )
                        return send_json(
                            self,
                            503,
                            {
                                'error': 'Histórico temporariamente indisponível. Tente novamente.',
                                'code': 'FICHA_AUDIT_UNAVAILABLE',
                            },
                        )
                    return send_json(self, 200, {'items': items})

            if parsed.path == '/api/ficha-epi-snapshots':
                with closing(get_connection()) as connection:
                    actor = authorize_action(connection, resolve_actor_user_id(self, parsed), 'reports:view')
                    query = parse_qs(parsed.query)
                    clauses = []
                    params = []
                    if actor.get('role') != 'master_admin':
                        clauses.append('s.company_id = ?')
                        params.append(int(actor['company_id']))
                    scope_unit_id = actor_operational_unit_id(connection, actor)
                    if scope_unit_id:
                        clauses.append('s.unit_id = ?')
                        params.append(int(scope_unit_id))
                    if query.get('employee_id'):
                        clauses.append('s.employee_id = ?')
                        params.append(int(query['employee_id'][0]))
                    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ''
                    rows = connection.execute(
                        (
                            'SELECT s.id, s.ficha_period_id, s.company_id, s.unit_id, s.employee_id, s.generated_at, s.expires_at, '
                            'employees.name AS employee_name, units.name AS unit_name '
                            'FROM ficha_epi_snapshots s '
                            'JOIN employees ON employees.id = s.employee_id '
                            'JOIN units ON units.id = s.unit_id '
                            f'{where_sql} '
                            'ORDER BY s.generated_at DESC, s.id DESC LIMIT 500'
                        ),
                        tuple(params),
                    ).fetchall()
                    return send_json(self, 200, {'items': [row_to_dict(item) for item in rows]})

            if parsed.path == '/api/ficha-retention-policy':
                with closing(get_connection()) as connection:
                    actor = authorize_action(connection, resolve_actor_user_id(self, parsed), PERM_SETTINGS_VIEW)
                    require_configuration_admin(actor)
                    policy = get_ficha_retention_policy(connection, actor.get('company_id'))
                    return send_json(self, 200, policy)

            if parsed.path == '/api/ficha-archive':
                with closing(get_connection()) as connection:
                    actor = authorize_action(connection, resolve_actor_user_id(self, parsed), 'reports:view')
                    query = parse_qs(parsed.query)
                    filters = {
                        'company_id': str(query.get('company_id', [''])[0] or '').strip(),
                        'unit_id': str(query.get('unit_id', [''])[0] or '').strip(),
                        'employee_id': str(query.get('employee_id', [''])[0] or '').strip(),
                        'status': str(query.get('status', [''])[0] or '').strip(),
                        'sector': str(query.get('sector', [''])[0] or '').strip(),
                        'date_from': str(query.get('date_from', [''])[0] or '').strip(),
                        'date_to': str(query.get('date_to', [''])[0] or '').strip(),
                        'page': str(query.get('page', ['1'])[0] or '1').strip(),
                        'page_size': str(query.get('page_size', ['50'])[0] or '50').strip(),
                    }
                    payload = fetch_ficha_archive_snapshots(connection, actor, filters)
                    return send_json(self, 200, payload)

            ficha_archive_html_match = re.match(r'^/api/ficha-archive/(\d+)\.html$', parsed.path or '')
            if ficha_archive_html_match:
                snapshot_id = int(ficha_archive_html_match.group(1))
                query = parse_qs(parsed.query)
                action = str(query.get('action', ['snapshot_view'])[0] or 'snapshot_view').strip().lower()
                if action not in {'snapshot_view', 'snapshot_print', 'snapshot_export'}:
                    action = 'snapshot_view'
                with closing(get_connection()) as connection:
                    actor = authorize_action(connection, resolve_actor_user_id(self, parsed), 'reports:view')
                    snapshot = get_ficha_archive_snapshot_by_id(connection, actor, snapshot_id)
                    register_ficha_epi_audit(
                        connection,
                        actor=actor,
                        employee={
                            'id': snapshot['employee_id'],
                            'name': snapshot.get('employee_name') or '',
                            'unit_id': snapshot['unit_id'],
                            'company_id': snapshot['company_id'],
                        },
                        action=action,
                        ip_address=str(getattr(self, 'client_address', ('',))[0] or ''),
                        user_agent=self.headers.get('User-Agent', ''),
                    )
                    connection.commit()
                    body = str(snapshot.get('html_content') or '').encode('utf-8')
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/html; charset=utf-8')
                    self.send_header('Content-Length', str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                    return



            if parsed.path == '/api/devolutions/open-deliveries':
                with closing(get_connection()) as connection:
                    actor = authorize_action(connection, resolve_actor_user_id(self, parsed), 'deliveries:view')
                    query = parse_qs(parsed.query)
                    employee_id = str(query.get('employee_id', [''])[0] or '').strip()
                    epi_id = str(query.get('epi_id', [''])[0] or '').strip()
                    unit_id = str(query.get('unit_id', [''])[0] or '').strip()
                    if not employee_id or not epi_id:
                        raise ValueError('Parâmetros employee_id e epi_id são obrigatórios.')
                    items = fetch_open_deliveries_for_devolution(connection, actor, int(employee_id), int(epi_id), unit_id=unit_id or None)
                    return send_json(self, 200, {'items': items, 'total_open': len(items)})

            if parsed.path == '/api/devolutions':
                with closing(get_connection()) as connection:
                    actor = authorize_action(connection, resolve_actor_user_id(self, parsed), 'stock:view')
                    q = parse_qs(parsed.query)
                    filters = {k: q[k][0] for k in ('employee_id','epi_id','delivery_id') if q.get(k)}
                    return send_json(self, 200, {'items': fetch_devolutions(connection, actor, filters)})

            # ── Fase 2 — Compras ─────────────────────────────────────────────
            if parsed.path == '/api/purchase-demands':
                with closing(get_connection()) as connection:
                    actor = authorize_action(connection, resolve_actor_user_id(self, parsed), PERM_PURCHASE_REQUESTS_VIEW)
                    query = parse_qs(parsed.query)
                    # master_admin with no company_id filter → all companies (company_id=None)
                    if actor.get('role') == 'master_admin':
                        requested_company = str(query.get('company_id', [''])[0] or '').strip()
                        company_id = int(requested_company) if requested_company else None
                    else:
                        company_id = actor_company_id_or_query(connection, actor, query)
                    scope_unit_id = actor_operational_unit_id(connection, actor)
                    purchase_scope_units = get_actor_purchase_unit_scope(connection, actor)
                    structured_log('info', 'purchase_demands.fetch', actor_id=actor.get('id'), actor_role=actor.get('role'), company_id=company_id, scope_unit_id=scope_unit_id, purchase_scope_units=purchase_scope_units)
                    if not scope_unit_id and purchase_scope_units:
                        all_demands = []
                        seen_ids = set()
                        for uid in purchase_scope_units:
                            for d in fetch_purchase_demands(connection, company_id, uid):
                                key = (d.get('demand_type'), d.get('id') or f"{d.get('unit_id')}/{d.get('epi_id')}")
                                if key not in seen_ids:
                                    seen_ids.add(key)
                                    all_demands.append(d)
                        structured_log('info', 'purchase_demands.result', count=len(all_demands), scope='multi_unit')
                        return send_json(self, 200, {'items': all_demands})
                    demands = fetch_purchase_demands(connection, company_id, scope_unit_id)
                    structured_log('info', 'purchase_demands.result', count=len(demands), scope='single_unit' if scope_unit_id else 'all_companies' if company_id is None else 'company')
                    return send_json(self, 200, {'items': demands})

            if parsed.path == '/api/feedbacks':
                with closing(get_connection()) as connection:
                    actor = authorize_action(connection, resolve_actor_user_id(self, parsed), PERM_EPI_FEEDBACK_VIEW)
                    query = parse_qs(parsed.query)
                    status_filter = str(query.get('status', [''])[0] or '').strip()
                    type_filter = str(query.get('type', [''])[0] or '').strip()
                    unit_filter = query.get('unit_id', [''])[0] or ''
                    items = fetch_feedbacks_for_manager(connection, actor)
                    if status_filter:
                        items = [f for f in items if str(f.get('status') or '') == status_filter]
                    if type_filter:
                        items = [f for f in items if str(f.get('type') or '') == type_filter]
                    if unit_filter:
                        items = [f for f in items if str(f.get('unit_id') or '') == str(unit_filter)]
                    return send_json(self, 200, {'items': items})

            feedback_detail_match = re.match(r'^/api/feedbacks/(\d+)$', parsed.path or '')
            if feedback_detail_match:
                with closing(get_connection()) as connection:
                    actor = authorize_action(connection, resolve_actor_user_id(self, parsed), PERM_EPI_FEEDBACK_VIEW)
                    fb_id = int(feedback_detail_match.group(1))
                    feedback = fetch_feedback_detail(connection, fb_id, actor)
                    return send_json(self, 200, {'item': feedback})

            if parsed.path == '/api/avaliacoes/summary':
                with closing(get_connection()) as connection:
                    actor = authorize_action(connection, resolve_actor_user_id(self, parsed), PERM_EPI_EVALUATION_VIEW)
                    result = fetch_avaliacoes_summary(connection, actor)
                    return send_json(self, 200, result)

            if parsed.path == '/api/avaliacoes/ranking':
                with closing(get_connection()) as connection:
                    actor = authorize_action(connection, resolve_actor_user_id(self, parsed), PERM_EPI_EVALUATION_VIEW)
                    items = fetch_avaliacoes_ranking(connection, actor)
                    return send_json(self, 200, {'items': items})

            if parsed.path == '/api/avaliacoes/ranking-sugestoes':
                with closing(get_connection()) as connection:
                    actor = authorize_action(connection, resolve_actor_user_id(self, parsed), PERM_EPI_EVALUATION_VIEW)
                    items = fetch_suggestion_ranking(connection, actor)
                    return send_json(self, 200, {'items': items})

            if parsed.path == '/api/purchase-requests':
                with closing(get_connection()) as connection:
                    actor = authorize_action(connection, resolve_actor_user_id(self, parsed), PERM_PURCHASE_REQUESTS_VIEW)
                    query = parse_qs(parsed.query)
                    company_id = actor_company_id_or_query(connection, actor, query)
                    scope_unit_id = actor_operational_unit_id(connection, actor)
                    purchase_scope_units = get_actor_purchase_unit_scope(connection, actor)
                    status_filter = str(query.get('status', [''])[0] or '').strip()
                    clauses, params = ['pr.company_id = ?'], [company_id]
                    if scope_unit_id:
                        clauses.append('pr.unit_id = ?')
                        params.append(int(scope_unit_id))
                    elif purchase_scope_units:
                        placeholders = ','.join(['?'] * len(purchase_scope_units))
                        clauses.append(f'pr.unit_id IN ({placeholders})')
                        params.extend(purchase_scope_units)
                    if status_filter:
                        clauses.append('pr.status = ?')
                        params.append(status_filter)
                    where_sql = f"WHERE {' AND '.join(clauses)}"
                    rows = connection.execute(
                        f'SELECT pr.*, u.name AS unit_name, '
                        f'(SELECT COUNT(*) FROM purchase_request_items pri WHERE pri.purchase_request_id = pr.id) AS items_count '
                        f'FROM purchase_requests pr JOIN units u ON u.id = pr.unit_id {where_sql} ORDER BY pr.created_at DESC',
                        tuple(params)
                    ).fetchall()
                    return send_json(self, 200, {'items': [row_to_dict(r) for r in rows]})

            purchase_request_match = re.match(r'^/api/purchase-requests/(\d+)$', parsed.path or '')
            if purchase_request_match:
                with closing(get_connection()) as connection:
                    actor = authorize_action(connection, resolve_actor_user_id(self, parsed), PERM_PURCHASE_REQUESTS_VIEW)
                    pr_id = int(purchase_request_match.group(1))
                    pr = connection.execute('SELECT pr.*, u.name AS unit_name FROM purchase_requests pr JOIN units u ON u.id = pr.unit_id WHERE pr.id = ?', (pr_id,)).fetchone()
                    if not pr:
                        return send_json(self, 404, {'error': 'Requisição não encontrada.'})
                    ensure_resource_company(actor, pr, 'Requisição')
                    ensure_purchase_request_action_scope(connection, actor, row_to_dict(pr))
                    items = connection.execute(
                        'SELECT pri.*, e.name AS epi_display_name, e.ca AS epi_ca, u.name AS unit_name '
                        'FROM purchase_request_items pri '
                        'JOIN epis e ON e.id = pri.epi_id '
                        'JOIN units u ON u.id = pri.unit_id '
                        'WHERE pri.purchase_request_id = ? ORDER BY pri.id',
                        (pr_id,)
                    ).fetchall()
                    events = connection.execute('SELECT * FROM purchase_events WHERE entity_type = ? AND entity_id = ? ORDER BY created_at DESC, id DESC', ('purchase_request', pr_id)).fetchall()
                    return send_json(self, 200, {'item': row_to_dict(pr), 'items': [row_to_dict(i) for i in items], 'events': [row_to_dict(e) for e in events]})

            if parsed.path == '/api/purchase-orders':
                with closing(get_connection()) as connection:
                    actor = authorize_action(connection, resolve_actor_user_id(self, parsed), PERM_PO_VIEW)
                    query = parse_qs(parsed.query)
                    company_id = actor_company_id_or_query(connection, actor, query)
                    scope_unit_id = actor_operational_unit_id(connection, actor)
                    purchase_scope_units = get_actor_purchase_unit_scope(connection, actor)
                    status_filter = str(query.get('status', [''])[0] or '').strip()
                    clauses, params = ['po.company_id = ?'], [company_id]
                    if scope_unit_id:
                        clauses.append('po.unit_id = ?')
                        params.append(int(scope_unit_id))
                    elif purchase_scope_units:
                        placeholders = ','.join(['?'] * len(purchase_scope_units))
                        clauses.append(f'po.unit_id IN ({placeholders})')
                        params.extend(purchase_scope_units)
                    if status_filter:
                        clauses.append('po.status = ?')
                        params.append(status_filter)
                    where_sql = f"WHERE {' AND '.join(clauses)}"
                    rows = connection.execute(
                        f'SELECT po.*, u.name AS unit_name, '
                        f'(SELECT COUNT(*) FROM purchase_order_items poi WHERE poi.purchase_order_id = po.id) AS items_count '
                        f'FROM purchase_orders po JOIN units u ON u.id = po.unit_id {where_sql} ORDER BY po.created_at DESC',
                        tuple(params)
                    ).fetchall()
                    return send_json(self, 200, {'items': [row_to_dict(r) for r in rows]})

            purchase_order_match = re.match(r'^/api/purchase-orders/(\d+)$', parsed.path or '')
            if purchase_order_match:
                with closing(get_connection()) as connection:
                    actor = authorize_action(connection, resolve_actor_user_id(self, parsed), PERM_PO_VIEW)
                    po_id = int(purchase_order_match.group(1))
                    po = connection.execute('SELECT po.*, u.name AS unit_name FROM purchase_orders po JOIN units u ON u.id = po.unit_id WHERE po.id = ?', (po_id,)).fetchone()
                    if not po:
                        return send_json(self, 404, {'error': 'PO não encontrada.'})
                    ensure_resource_company(actor, po, 'PO')
                    items = connection.execute('SELECT poi.* FROM purchase_order_items poi WHERE poi.purchase_order_id = ?', (po_id,)).fetchall()
                    files = connection.execute('SELECT id, file_name, file_type, uploaded_by_name, created_at FROM purchase_order_files WHERE purchase_order_id = ?', (po_id,)).fetchall()
                    events = connection.execute('SELECT * FROM purchase_events WHERE entity_type = ? AND entity_id = ? ORDER BY created_at DESC', ('purchase_order', po_id)).fetchall()
                    return send_json(self, 200, {'item': row_to_dict(po), 'items': [row_to_dict(i) for i in items], 'files': [row_to_dict(f) for f in files], 'events': [row_to_dict(e) for e in events]})

            if parsed.path == '/api/purchase-events':
                with closing(get_connection()) as connection:
                    actor = authorize_action(connection, resolve_actor_user_id(self, parsed), PERM_FINANCE_VIEW)
                    query = parse_qs(parsed.query)
                    company_id = actor_company_id_or_query(connection, actor, query)
                    entity_type = str(query.get('entity_type', [''])[0] or '').strip()
                    entity_id = str(query.get('entity_id', [''])[0] or '').strip()
                    clauses, params = ['company_id = ?'], [company_id]
                    if entity_type:
                        clauses.append('entity_type = ?')
                        params.append(entity_type)
                    if entity_id:
                        clauses.append('entity_id = ?')
                        params.append(int(entity_id))
                    where_sql = f"WHERE {' AND '.join(clauses)}"
                    rows = connection.execute(f'SELECT * FROM purchase_events {where_sql} ORDER BY created_at DESC LIMIT 200', tuple(params)).fetchall()
                    return send_json(self, 200, {'items': [row_to_dict(r) for r in rows]})
            if parsed.path == '/api/authorized-suppliers':
                with closing(get_connection()) as connection:
                    actor = authorize_action(connection, resolve_actor_user_id(self, parsed), PERM_PURCHASE_REQUESTS_VIEW)
                    company_id = int(actor['company_id'])
                    rows = connection.execute(
                        'SELECT * FROM authorized_suppliers WHERE company_id = ? ORDER BY name ASC',
                        (company_id,)
                    ).fetchall()
                    return send_json(self, 200, {'items': [row_to_dict(r) for r in rows]})

            supplier_pos_match = re.match(r'^/api/authorized-suppliers/(\d+)/purchase-orders$', parsed.path or '')
            if supplier_pos_match:
                with closing(get_connection()) as connection:
                    actor = authorize_action(connection, resolve_actor_user_id(self, parsed), PERM_PO_VIEW)
                    supplier_id = int(supplier_pos_match.group(1))
                    company_id = int(actor['company_id'])
                    supplier = connection.execute('SELECT * FROM authorized_suppliers WHERE id = ? AND company_id = ?', (supplier_id, company_id)).fetchone()
                    if not supplier:
                        return send_json(self, 404, {'error': 'Fornecedor não encontrado.'})
                    sup = row_to_dict(supplier)
                    clauses = ['po.company_id = ?']
                    params = [company_id]
                    if sup.get('cnpj'):
                        clauses.append('(po.supplier_cnpj = ? OR LOWER(TRIM(po.supplier)) = ?)')
                        params.extend([sup['cnpj'], sup['name'].lower()])
                    else:
                        clauses.append('LOWER(TRIM(po.supplier)) = ?')
                        params.append(sup['name'].lower())
                    where_sql = f"WHERE {' AND '.join(clauses)}"
                    rows = connection.execute(
                        f'SELECT po.*, u.name AS unit_name, '
                        f'(SELECT COUNT(*) FROM purchase_order_items poi WHERE poi.purchase_order_id = po.id) AS items_count '
                        f'FROM purchase_orders po JOIN units u ON u.id = po.unit_id {where_sql} ORDER BY po.created_at DESC',
                        tuple(params)
                    ).fetchall()
                    return send_json(self, 200, {'supplier': sup, 'items': [row_to_dict(r) for r in rows]})

            if parsed.path == '/api/purchase-functions':
                with closing(get_connection()) as connection:
                    query = parse_qs(parsed.query)
                    actor_id = resolve_actor_user_id(self, parsed)
                    # Admins veem todos os vínculos; compradores/aprovadores veem somente leitura da empresa
                    try:
                        actor = authorize_action(connection, actor_id, PERM_UNIT_LINKS_MANAGE)
                    except PermissionError:
                        actor = authorize_action(connection, actor_id, PERM_PURCHASE_REQUESTS_VIEW)
                    company_id = actor_company_id_or_query(connection, actor, query)
                    if actor.get('role') != 'master_admin' and int(actor['company_id']) != company_id:
                        raise PermissionError('Empresa fora do escopo do usuário.')
                    return send_json(self, 200, {'items': fetch_purchase_function_links(connection, company_id)})

            if parsed.path == '/api/company-purchase-config':
                with closing(get_connection()) as connection:
                    query = parse_qs(parsed.query)
                    actor = authorize_action(connection, resolve_actor_user_id(self, parsed), PERM_PURCHASE_REQUESTS_VIEW)
                    raw_cid = str(query.get('company_id', [''])[0] or '').strip()
                    if not raw_cid:
                        raw_cid = str(actor.get('company_id') or '').strip()
                    if not raw_cid or raw_cid == 'None':
                        return send_json(self, 200, {'config': {}})
                    cid = int(raw_cid)
                    row = connection.execute('SELECT value FROM app_meta WHERE key = ?', (f'purchase_config_{cid}',)).fetchone()
                    config = json.loads(row['value']) if row else {}
                    return send_json(self, 200, {'config': config})

            if parsed.path == '/api/user-unit-links':
                with closing(get_connection()) as connection:
                    query = parse_qs(parsed.query)
                    target_user_id_str = str(query.get('user_id', [''])[0] or '').strip()
                    actor_id = resolve_actor_user_id(self, parsed)
                    # Buyer/approver podem consultar apenas seus próprios vínculos
                    if target_user_id_str and str(actor_id) == target_user_id_str:
                        actor = authorize_action(connection, actor_id, PERM_PURCHASE_REQUESTS_VIEW)
                        company_id = int(actor['company_id'])
                        # Vínculos legado (user_unit_links)
                        legacy_rows = connection.execute(
                            'SELECT uul.*, u.name AS unit_name FROM user_unit_links uul '
                            'JOIN units u ON u.id = uul.unit_id '
                            'WHERE uul.user_id = ? AND uul.company_id = ? ORDER BY u.name',
                            (int(target_user_id_str), company_id)
                        ).fetchall()
                        items = [row_to_dict(r) for r in legacy_rows]
                        seen_unit_ids = {i['unit_id'] for i in items}
                        # Vínculos via purchase_role_unit_links (sistema atual)
                        linked_employee_id = actor.get('linked_employee_id')
                        if linked_employee_id:
                            prl_rows = connection.execute(
                                'SELECT prul.unit_id, u.name AS unit_name FROM purchase_role_unit_links prul '
                                'JOIN units u ON u.id = prul.unit_id '
                                'WHERE prul.employee_id = ? AND prul.company_id = ? ORDER BY u.name',
                                (int(linked_employee_id), company_id)
                            ).fetchall()
                            for r in prl_rows:
                                if r['unit_id'] not in seen_unit_ids:
                                    items.append({'unit_id': r['unit_id'], 'unit_name': r['unit_name'], 'user_id': int(target_user_id_str), 'company_id': company_id})
                                    seen_unit_ids.add(r['unit_id'])
                        return send_json(self, 200, {'items': items})
                    else:
                        actor = authorize_action(connection, actor_id, PERM_UNIT_LINKS_MANAGE)
                        company_id = int(actor['company_id'])
                        if target_user_id_str:
                            rows = connection.execute(
                                'SELECT uul.*, u.name AS unit_name FROM user_unit_links uul '
                                'JOIN units u ON u.id = uul.unit_id '
                                'WHERE uul.user_id = ? AND uul.company_id = ? ORDER BY u.name',
                                (int(target_user_id_str), company_id)
                            ).fetchall()
                        else:
                            rows = connection.execute(
                                'SELECT uul.*, u.name AS unit_name, us.full_name AS user_name, us.role AS user_role '
                                'FROM user_unit_links uul '
                                'JOIN units u ON u.id = uul.unit_id '
                                'JOIN users us ON us.id = uul.user_id '
                                'WHERE uul.company_id = ? ORDER BY us.full_name, u.name',
                                (company_id,)
                            ).fetchall()
                    return send_json(self, 200, {'items': [row_to_dict(r) for r in rows]})

            # ── Fim Fase 2 GET ───────────────────────────────────────────────

            return super().do_GET()

        except PermissionError as exc:
            structured_log('warning', 'http.permission_error', method='GET', path=parsed.path, error=str(exc))
            return forbidden(self, str(exc))
        except InvalidQueryParamError as exc:
            structured_log('warning', 'http.query_param_error', method='GET', path=parsed.path, field=exc.field_name, value=exc.value, error=str(exc))
            return send_json(self, 400, {
                'ok': False,
                'error': {
                    'code': 'INVALID_QUERY_PARAM',
                    'message': str(exc),
                    'details': {exc.field_name: exc.value}
                }
            })
        except ValueError as exc:
            structured_log('warning', 'http.value_error', method='GET', path=parsed.path, error=str(exc))
            return bad_request(self, str(exc))
        except Exception as exc:
            structured_log('error', 'http.unhandled_error', method='GET', path=parsed.path, error=str(exc))
            return send_json(self, 500, {'error': str(exc)})

    def do_HEAD(self):
        parsed = urlparse(self.path)
        if self._is_static_request(parsed.path):
            if parsed.path == '/':
                self.path = '/index.html'
            return super().do_HEAD()
        if parsed.path.startswith('/api/') and not self._require_bootstrap_ready(parsed.path):
            return
        return super().do_HEAD()

    def do_POST(self):
        parsed = urlparse(self.path)
        structured_log('info', 'http.post.entry', path=parsed.path, raw_path=self.path)
        if parsed.path.startswith('/api/') and not self._require_bootstrap_ready(parsed.path):
            return

        try:
            payload = parse_json(self)
        except (json.JSONDecodeError, UnicodeDecodeError, ValueError):
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
                        (
                            'INSERT INTO employee_unit_movements ('
                            'employee_id, company_id, source_unit_id, target_unit_id, '
                            'movement_type, start_date, end_date, notes, '
                            'actor_user_id, actor_name, created_at'
                            ') VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'
                        ),
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
                    def _create_user(connection_ref, payload_ref):
                        return create_user_service(
                            connection_ref,
                            payload_ref,
                            resolve_actor_user_id=lambda: resolve_actor_user_id(self, parsed, payload_ref),
                            authorize_user_management=authorize_user_management,
                            normalize_role_name=normalize_role_name,
                            role_weight=ROLE_WEIGHT,
                            hash_password=hash_password,
                            resolve_target_company_id=resolve_target_company_id,
                            resolve_user_employee_link=resolve_user_employee_link,
                            ensure_operational_role_link=ensure_operational_role_link,
                            ensure_company_user_limit=ensure_company_user_limit,
                            build_employee_access_token=build_employee_access_token,
                        )
                    return handle_create_user_route(self, connection, payload, require_fields=require_fields, send_json=send_json, create_user=_create_user)

                elif parsed.path == '/api/employee-sign':
                    require_fields(payload, ['token', 'delivery_id'])
                    token = str(payload.get('token', '')).strip()
                    with_name = str(payload.get('signature_name', '')).strip()
                    with_data = str(payload.get('signature_data', '')).strip()
                    with_comment = str(payload.get('signature_comment', '')).strip()
                    if not with_name and not with_data:
                        raise ValueError('Informe o nome da assinatura ou desenhe no canvas.')

                    employee_user = resolve_external_employee_context(
                        connection,
                        token,
                        cpf_last3=payload.get('cpf_last3'),
                        ip_address=str(getattr(self, 'client_address', ('',))[0] or ''),
                        user_agent=self.headers.get('User-Agent', ''),
                    )
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
                        (
                            'UPDATE deliveries '
                            'SET signature_name = ?, signature_data = ?, signature_at = ?, signature_ip = ?, signature_comment = ? '
                            'WHERE id = ?'
                        ),
                        (
                            with_name or employee_user.get('employee_name') or MSG_SIGNED_DIGITALLY,
                            with_data,
                            datetime.now(UTC).isoformat(),
                            str(getattr(self, 'client_address', ('',))[0] or ''),
                            with_comment,
                            int(payload.get('delivery_id'))
                        )
                    )
                    connection.execute(
                        (
                            "UPDATE epi_ficha_items "
                            "SET item_signature_name = ?, item_signature_data = ?, item_signature_ip = ?, item_signature_at = ?, item_signature_comment = ?, signed_mode = 'item', updated_at = ? "
                            "WHERE delivery_id = ?"
                        ),
                        (
                            with_name or employee_user.get('employee_name') or MSG_SIGNED_DIGITALLY,
                            with_data,
                            str(getattr(self, 'client_address', ('',))[0] or ''),
                            datetime.now(UTC).isoformat(),
                            with_comment,
                            datetime.now(UTC).isoformat(),
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
                        (
                            'SELECT employees.id, employees.company_id, employees.unit_id, employees.employee_id_code, employees.name, '
                            'employees.sector, employees.role_name, employees.schedule_type, '
                            'employee_portal_links.qr_code_value, employee_portal_links.token '
                            'FROM employee_portal_links '
                            'JOIN employees ON employees.id = employee_portal_links.employee_id '
                            'WHERE employee_portal_links.active = 1 '
                            f'AND (employee_portal_links.qr_code_value = ?{token_clause})'
                        ),
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
                    link_data = build_portal_link_from_cpf(
                        base_url=request_base_url(self),
                        funcionario_cpf=employee.get('cpf'),
                        secret_key=EMPLOYEE_PORTAL_SECRET_KEY
                    )
                    token = link_data['token']
                    access_link = link_data['access_link']
                    qr_code_value = access_link
                    now = datetime.now(UTC).isoformat()
                    expires_at = link_data['expires_at']
                    existing = connection.execute('SELECT id FROM employee_portal_links WHERE employee_id = ?', (int(employee['id']),)).fetchone()
                    if existing:
                        connection.execute(
                            (
                                'UPDATE employee_portal_links '
                                'SET token = ?, qr_code_value = ?, active = 1, expires_at = ?, updated_at = ? '
                                'WHERE employee_id = ?'
                            ),
                            (token, qr_code_value, expires_at, now, int(employee['id']))
                        )
                    else:
                        connection.execute(
                            (
                                'INSERT INTO employee_portal_links ('
                                'company_id, employee_id, token, qr_code_value, active, expires_at, '
                                'created_by_user_id, created_at, updated_at'
                                ') VALUES (?, ?, ?, ?, 1, ?, ?, ?, ?)'
                            ),
                            (int(employee['company_id']), int(employee['id']), token, qr_code_value, expires_at, int(actor['id']), now, now)
                        )
                    connection.commit()
                    return send_json(self, 200, {'ok': True, 'token': token, 'qr_code_value': qr_code_value, 'access_link': access_link, 'expires_at': expires_at})

                elif parsed.path == '/api/employee-contact-launch':
                    require_fields(payload, ['actor_user_id', 'employee_id', 'channel'])
                    actor = authorize_action(connection, resolve_actor_user_id(self, parsed, payload), 'deliveries:create')
                    employee = get_employee_by_id(connection, int(payload['employee_id']))
                    if not employee:
                        raise ValueError('Colaborador não encontrado.')
                    ensure_actor_employee_scope(connection, actor, employee)
                    channel = normalize_preferred_contact_channel(payload.get('channel'))
                    access_link = str(payload.get('access_link') or '').strip()
                    if not access_link:
                        active_link = connection.execute(
                            (
                                'SELECT token, expires_at '
                                'FROM employee_portal_links '
                                'WHERE employee_id = ? AND active = 1 '
                                'ORDER BY id DESC '
                                'LIMIT 1'
                            ),
                            (int(employee['id']),)
                        ).fetchone()
                        active_link_expires_at = parse_iso_datetime_utc(str((active_link or {}).get('expires_at') or ''))
                        if active_link and active_link_expires_at and active_link_expires_at > datetime.now(UTC):
                            access_link = f"{request_base_url(self)}/?employee_token={active_link['token']}"
                        else:
                            link_data = build_portal_link_from_cpf(request_base_url(self), employee.get('cpf'), EMPLOYEE_PORTAL_SECRET_KEY)
                            access_link = link_data['access_link']
                    employee_name = str(employee.get('name') or 'Colaborador')
                    message = (
                        f"Olá {employee_name}! 👷\n"
                        f"Seu link rápido da Ficha de EPI (48h):\n{access_link}\n"
                        "No portal você consegue: Assinar Ficha, Solicitar EPI e Avaliar EPI."
                    )
                    if channel == 'whatsapp':
                        phone = ''.join(ch for ch in str(employee.get('whatsapp') or '') if ch.isdigit())
                        if not phone:
                            raise ValueError('Colaborador sem WhatsApp cadastrado.')
                        launch_url = f"https://wa.me/{phone}?text={quote(message)}"
                    else:
                        email = str(employee.get('email') or '').strip().lower()
                        if not email:
                            raise ValueError('Colaborador sem e-mail cadastrado.')
                        subject = quote(f'Acesso rápido - Ficha de EPI - {employee_name}')
                        launch_url = f"mailto:{email}?subject={subject}&body={quote(message)}"
                    return send_json(self, 200, {'ok': True, 'channel': channel, 'message': message, 'launch_url': launch_url, 'access_link': access_link})

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
                    signature_comment = str(payload.get('signature_comment', '')).strip()
                    if not signature_name or not signature_data:
                        raise ValueError('Assinatura obrigatória.')
                    employee_user = resolve_external_employee_context(
                        connection,
                        token,
                        cpf_last3=payload.get('cpf_last3'),
                        ip_address=str(getattr(self, 'client_address', ('',))[0] or ''),
                        user_agent=self.headers.get('User-Agent', ''),
                    )
                    if not employee_user:
                        raise PermissionError('Token de acesso inválido ou expirado.')
                    employee_id = int(employee_user['employee_id'])
                    requested_ficha_period_id = int(payload['ficha_period_id'])
                    ficha = connection.execute(
                        'SELECT id, employee_id, period_start, period_end FROM epi_ficha_periods WHERE id = ?',
                        (requested_ficha_period_id,),
                    ).fetchone()
                    if not ficha or int(ficha['employee_id']) != employee_id:
                        raise PermissionError('Ficha não pertence ao funcionário.')
                    total_items = int(
                        (
                            connection.execute(
                                'SELECT COUNT(*) AS total FROM epi_ficha_items WHERE ficha_period_id = ?',
                                (int(ficha['id']),),
                            ).fetchone() or {'total': 0}
                        )['total'] or 0
                    )
                    structured_log(
                        'info',
                        'employee.sign_batch.start',
                        employee_id=employee_id,
                        requested_ficha_period_id=requested_ficha_period_id,
                        resolved_ficha_period_id=int(ficha['id']),
                        selected_period_start=str(ficha['period_start'] or ''),
                        selected_period_end=str(ficha['period_end'] or ''),
                        total_items=total_items,
                    )
                    if total_items <= 0:
                        raise ValueError('Período sem itens vinculados; não é possível assinar.')
                    now = datetime.now(UTC).isoformat()
                    client_ip = str(getattr(self, 'client_address', ('',))[0] or '')
                    if not signature_data:
                        raise ValueError('Assinatura em lote inválida: batch_signature_data não pode estar vazio.')
                    try:
                        period_cursor = connection.execute(
                            (
                                "UPDATE epi_ficha_periods "
                                "SET status = 'pending_signature', batch_signature_name = ?, batch_signature_data = ?, batch_signature_ip = ?, batch_signature_at = ?, batch_signature_comment = ?, updated_at = ? "
                                "WHERE id = ?"
                            ),
                            (signature_name or 'Assinado digitalmente', signature_data, client_ip, now, signature_comment, now, int(ficha['id']))
                        )
                        if int(period_cursor.rowcount or 0) != 1:
                            connection.rollback()
                            raise RuntimeError('Falha ao salvar assinatura em lote no período.')
                        items_cursor = connection.execute(
                            (
                                "UPDATE epi_ficha_items "
                                "SET item_signature_name = ?, item_signature_data = ?, item_signature_ip = ?, item_signature_at = ?, item_signature_comment = ?, signed_mode = 'batch', updated_at = ? "
                                "WHERE ficha_period_id = ?"
                            ),
                            (signature_name or 'Assinado digitalmente', signature_data, client_ip, now, signature_comment, now, int(ficha['id']))
                        )
                        if int(items_cursor.rowcount or 0) <= 0:
                            connection.rollback()
                            raise RuntimeError('Nenhum item da ficha foi assinado.')
                        connection.execute(
                            (
                                "UPDATE deliveries "
                                "SET signature_name = ?, signature_data = ?, signature_ip = ?, signature_at = ?, signature_comment = ? "
                                "WHERE id IN (SELECT delivery_id FROM epi_ficha_items WHERE ficha_period_id = ?) "
                                "AND COALESCE(signature_at, '') = ''"
                            ),
                            (
                                signature_name or 'Assinado digitalmente',
                                signature_data,
                                client_ip,
                                now,
                                signature_comment,
                                int(ficha['id'])
                            )
                        )
                        connection.execute(
                            (
                                "UPDATE epi_devolutions "
                                "SET signature_name = ?, signature_data = ?, signature_ip = ?, signature_at = ?, signature_comment = ? "
                                "WHERE ficha_period_id = ? "
                                "AND COALESCE(signature_at, '') = ''"
                            ),
                            (
                                signature_name or 'Assinado digitalmente',
                                signature_data,
                                client_ip,
                                now,
                                signature_comment,
                                int(ficha['id']),
                            )
                        )
                    except Exception:
                        connection.rollback()
                        raise
                    register_employee_portal_audit(
                        connection,
                        employee_user,
                        'sign_batch_period',
                        ip_address=client_ip,
                        user_agent=self.headers.get('User-Agent', ''),
                        payload={'ficha_period_id': int(ficha['id'])}
                    )
                    refresh_ficha_snapshot_for_period_if_exists(
                        connection,
                        int(ficha['id']),
                        {
                            'id': int(employee_user.get('portal_link_id') or 0),
                            'role': 'general_admin',
                            'company_id': int(employee_user.get('company_id') or 0),
                        },
                    )
                    state = compute_ficha_period_signature_state(connection, int(ficha['id']))
                    structured_log(
                        'info',
                        'employee.sign_batch.done',
                        employee_id=employee_id,
                        ficha_period_id=int(ficha['id']),
                        period_rowcount=int(period_cursor.rowcount or 0),
                        items_rowcount=int(items_cursor.rowcount or 0),
                        items_update_rowcount=int(items_cursor.rowcount or 0),
                        affected_items=int(items_cursor.rowcount or 0),
                        batch_signature_saved=bool(state['has_batch_signature']),
                        total_items=int(state['total_items']),
                        signed_items=int(state['signed_items']),
                        pending_items=int(state['pending_items']),
                        has_batch_signature=bool(state['has_batch_signature']),
                        can_close=bool(state['can_close']),
                    )
                    connection.commit()
                    persisted_signature = connection.execute(
                        'SELECT batch_signature_name, batch_signature_data, batch_signature_at FROM epi_ficha_periods WHERE id = ?',
                        (int(ficha['id']),),
                    ).fetchone()
                    persisted_signature_data = row_to_dict(persisted_signature) if persisted_signature else {}
                    persisted_ok = bool(
                        str(persisted_signature_data.get('batch_signature_name') or '').strip()
                        and str(persisted_signature_data.get('batch_signature_data') or '').strip()
                        and str(persisted_signature_data.get('batch_signature_at') or '').strip()
                    )
                    if not persisted_ok:
                        raise RuntimeError('Erro crítico: assinatura em lote não persistiu no período.')
                    return send_json(
                        self,
                        200,
                        {
                            'ok': True,
                            'period_id': int(ficha['id']),
                            'signature_state': {
                                'total_items': int(state['total_items']),
                                'signed_items': int(state['signed_items']),
                                'pending_items': int(state['pending_items']),
                                'has_batch_signature': bool(state['has_batch_signature']),
                                'can_close': bool(state['can_close']),
                            },
                        },
                    )

                elif parsed.path == '/api/employee-close-period':
                    require_fields(payload, ['token', 'ficha_period_id'])
                    employee_user = resolve_external_employee_context(
                        connection,
                        str(payload.get('token', '')).strip(),
                        cpf_last3=payload.get('cpf_last3'),
                        ip_address=str(getattr(self, 'client_address', ('',))[0] or ''),
                        user_agent=self.headers.get('User-Agent', ''),
                    )
                    if not employee_user:
                        raise PermissionError('Token de acesso inválido ou expirado.')
                    ficha = connection.execute(
                        'SELECT id, employee_id, status FROM epi_ficha_periods WHERE id = ?',
                        (int(payload['ficha_period_id']),)
                    ).fetchone()
                    if not ficha or int(ficha['employee_id']) != int(employee_user['employee_id']):
                        raise PermissionError('Ficha não pertence ao funcionário.')
                    structured_log(
                        'info',
                        'employee.close_period.start',
                        employee_id=int(employee_user['employee_id']),
                        ficha_period_id=int(ficha['id']),
                    )
                    state = compute_ficha_period_signature_state(connection, int(ficha['id']))
                    structured_log(
                        'info',
                        'employee.close_period.state',
                        employee_id=int(employee_user['employee_id']),
                        ficha_period_id=int(ficha['id']),
                        total_items=int(state['total_items']),
                        signed_items=int(state['signed_items']),
                        pending_items=int(state['pending_items']),
                        has_batch_signature=bool(state['has_batch_signature']),
                        can_close=bool(state['can_close']),
                    )
                    if not state['can_close']:
                        missing_requirements = get_ficha_period_close_requirements(state)
                        error_message = 'Não é possível fechar o período: requisitos de fechamento não atendidos.'
                        if 'pending_items' in missing_requirements or 'signed_items' in missing_requirements:
                            error_message = 'Não é possível fechar o período: existem assinaturas pendentes.'
                        elif 'batch_signature' in missing_requirements:
                            error_message = 'Não é possível fechar o período: assinatura em lote ausente ou incompleta.'
                        elif 'total_items' in missing_requirements:
                            error_message = 'Não é possível fechar o período: não há itens no período.'
                        structured_log(
                            'warning',
                            'employee.close_period.denied',
                            employee_id=int(employee_user['employee_id']),
                            ficha_period_id=int(ficha['id']),
                            total_items=int(state['total_items']),
                            signed_items=int(state['signed_items']),
                            pending_items=int(state['pending_items']),
                            has_batch_signature=bool(state['has_batch_signature']),
                            can_close=False,
                            missing_requirements=missing_requirements,
                        )
                        return send_json(
                            self,
                            400,
                            {
                                'ok': False,
                                'error': error_message,
                                'total_items': int(state['total_items']),
                                'signed_items': int(state['signed_items']),
                                'pending_items': int(state['pending_items']),
                                'has_batch_signature': bool(state['has_batch_signature']),
                                'can_close': False,
                                'missing_requirements': missing_requirements,
                            }
                        )
                    assert_ficha_period_can_close(connection, int(ficha['id']))
                    now = datetime.now(UTC).isoformat()
                    connection.execute(
                        "UPDATE epi_ficha_periods SET status = 'closed', updated_at = ? WHERE id = ?",
                        (now, int(ficha['id']))
                    )
                    refresh_ficha_snapshot_for_period_if_exists(
                        connection,
                        int(ficha['id']),
                        {
                            'id': int(employee_user.get('portal_link_id') or 0),
                            'role': 'general_admin',
                            'company_id': int(employee_user.get('company_id') or 0),
                        },
                    )
                    register_employee_portal_audit(
                        connection,
                        employee_user,
                        'close_period',
                        ip_address=str(getattr(self, 'client_address', ('',))[0] or ''),
                        user_agent=self.headers.get('User-Agent', ''),
                        payload={'ficha_period_id': int(ficha['id'])}
                    )
                    structured_log(
                        'info',
                        'employee.close_period.closed',
                        employee_id=int(employee_user['employee_id']),
                        ficha_period_id=int(ficha['id']),
                        total_items=int(state['total_items']),
                        signed_items=int(state['signed_items']),
                        pending_items=int(state['pending_items']),
                        has_batch_signature=bool(state['has_batch_signature']),
                        can_close=True,
                    )
                    connection.commit()
                    return send_json(self, 200, {'ok': True, 'status': 'closed', 'ficha_period_id': int(ficha['id'])})

                elif parsed.path == '/api/requests':
                    require_fields(payload, ['token', 'epi_id', 'quantity'])
                    portal = resolve_external_employee_context(
                        connection,
                        str(payload.get('token', '')).strip(),
                        cpf_last3=payload.get('cpf_last3'),
                        ip_address=str(getattr(self, 'client_address', ('',))[0] or ''),
                        user_agent=self.headers.get('User-Agent', ''),
                    )
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
                    resolved_size = resolve_item_size(
                        payload.get('glove_size'),
                        payload.get('size'),
                        payload.get('uniform_size'),
                    )
                    if not resolved_size['selected_size']:
                        raise ValueError('Tamanho é obrigatório na solicitação de EPI.')
                    glove_size = resolved_size['glove_size']
                    size = resolved_size['size']
                    uniform_size = resolved_size['uniform_size']
                    now = datetime.now(UTC).isoformat()
                    cursor = connection.execute(
                        (
                            'INSERT INTO epi_requests ('
                            'company_id, unit_id, employee_id, epi_id, quantity, glove_size, size, uniform_size, request_token, status, '
                            'justification, requested_at, requested_by, last_updated_at'
                            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'solicitado', ?, ?, 'employee', ?)"
                        ),
                        (
                            int(portal['company_id']),
                            int(employee['unit_id']),
                            int(portal['employee_id']),
                            int(payload['epi_id']),
                            int(payload.get('quantity') or 1),
                            glove_size,
                            size,
                            uniform_size,
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
                    portal = resolve_external_employee_context(
                        connection,
                        str(payload.get('token', '')).strip(),
                        cpf_last3=payload.get('cpf_last3'),
                        ip_address=str(getattr(self, 'client_address', ('',))[0] or ''),
                        user_agent=self.headers.get('User-Agent', ''),
                    )
                    if not portal:
                        raise PermissionError('Link de avaliação inválido.')
                    epi_id = payload.get('epi_id')
                    fb_type = str(payload.get('type') or '').strip()
                    if not fb_type:
                        fb_type = 'sugestao' if str(payload.get('suggested_new_epi_name') or '').strip() else 'avaliacao'
                    if fb_type not in ('avaliacao', 'elogio', 'reclamacao', 'sugestao'):
                        fb_type = 'avaliacao'
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
                        (
                            'INSERT INTO epi_feedbacks ('
                            'company_id, unit_id, employee_id, epi_id, type, comfort_rating, quality_rating, adequacy_rating, performance_rating, '
                            'comments, improvement_suggestion, suggested_new_epi_name, suggested_new_epi_notes, suggested_new_epi_link, '
                            "status, request_token, created_at, updated_at"
                            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pendente', ?, ?, ?)"
                        ),
                        (
                            int(portal['company_id']),
                            int(get_employee_by_id(connection, int(portal['employee_id']))['unit_id']),
                            int(portal['employee_id']),
                            int(epi_id) if epi_id else None,
                            fb_type,
                            ratings['comfort_rating'],
                            ratings['quality_rating'],
                            ratings['adequacy_rating'],
                            ratings['performance_rating'],
                            str(payload.get('comments', '')).strip(),
                            str(payload.get('improvement_suggestion', '')).strip(),
                            str(payload.get('suggested_new_epi_name', '')).strip(),
                            str(payload.get('suggested_new_epi_notes', '')).strip(),
                            str(payload.get('suggested_new_epi_link', '')).strip(),
                            str(payload.get('token', '')).strip(),
                            now,
                            now
                        )
                    )
                    connection.execute(
                        (
                            "INSERT INTO epi_feedback_history (feedback_id, company_id, status, notes, actor_name, created_at) "
                            "VALUES (?, ?, 'pendente', ?, 'Funcionário', ?)"
                        ),
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
                    valid = {'solicitado', 'em análise', 'aprovado', 'rejeitado', 'prorrogado', 'separado', 'entregue', 'assinado'}
                    if new_status not in valid:
                        raise ValueError('Status inválido.')
                    if new_status == 'prorrogado' and not str(payload.get('postponed_until') or '').strip():
                        raise ValueError('Data de prorrogação obrigatória.')
                    postponed_until = str(payload.get('postponed_until') or '').strip()
                    now = datetime.now(UTC).isoformat()
                    connection.execute(
                        (
                            "UPDATE epi_requests "
                            "SET status = ?, approver_user_id = ?, approver_name = ?, "
                            "approved_at = CASE WHEN ? IN ('aprovado','rejeitado','prorrogado') THEN ? ELSE approved_at END, "
                            "rejection_reason = CASE WHEN ? = 'rejeitado' THEN ? ELSE rejection_reason END, "
                            "postponed_until = CASE WHEN ? = 'prorrogado' THEN ? ELSE postponed_until END, "
                            "last_updated_at = ? "
                            "WHERE id = ?"
                        ),
                        (
                            new_status,
                            int(actor['id']),
                            actor['full_name'],
                            new_status, now,
                            new_status, str(payload.get('rejection_reason', '')).strip(),
                            new_status, postponed_until,
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

                elif parsed.path == '/api/requests/bulk-status':
                    require_fields(payload, ['actor_user_id', 'updates'])
                    actor = authorize_action(connection, resolve_actor_user_id(self, parsed, payload), 'deliveries:create')
                    updates = payload.get('updates') or []
                    if not updates:
                        raise ValueError('Nenhuma atualização enviada.')
                    valid = {'solicitado', 'em análise', 'aprovado', 'rejeitado', 'prorrogado', 'separado', 'entregue', 'assinado'}
                    now = datetime.now(UTC).isoformat()
                    for upd in updates:
                        req = connection.execute('SELECT * FROM epi_requests WHERE id = ?', (int(upd['request_id']),)).fetchone()
                        if not req:
                            continue
                        ensure_resource_company(actor, req, 'Solicitação')
                        new_status = str(upd.get('status', '')).strip().lower()
                        if new_status not in valid:
                            continue
                        postponed_until = str(upd.get('postponed_until') or '').strip()
                        rejection_reason = str(upd.get('rejection_reason') or '').strip()
                        connection.execute(
                            (
                                "UPDATE epi_requests "
                                "SET status = ?, approver_user_id = ?, approver_name = ?, "
                                "approved_at = CASE WHEN ? IN ('aprovado','rejeitado','prorrogado') THEN ? ELSE approved_at END, "
                                "rejection_reason = CASE WHEN ? = 'rejeitado' THEN ? ELSE rejection_reason END, "
                                "postponed_until = CASE WHEN ? = 'prorrogado' THEN ? ELSE postponed_until END, "
                                "last_updated_at = ? WHERE id = ?"
                            ),
                            (
                                new_status, int(actor['id']), actor['full_name'],
                                new_status, now,
                                new_status, rejection_reason,
                                new_status, postponed_until,
                                now, int(req['id'])
                            )
                        )
                        connection.execute(
                            'INSERT INTO epi_request_history (request_id, company_id, status, notes, actor_user_id, actor_name, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)',
                            (int(req['id']), int(req['company_id']), new_status, str(upd.get('notes') or '').strip(), int(actor['id']), actor['full_name'], now)
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
                        (
                            'UPDATE epi_feedbacks '
                            'SET status = ?, reviewer_user_id = ?, reviewer_name = ?, reviewed_at = ?, updated_at = ? '
                            'WHERE id = ?'
                        ),
                        (status, int(actor['id']), actor['full_name'], now, now, int(payload['feedback_id']))
                    )
                    connection.execute(
                        (
                            'INSERT INTO epi_feedback_history (feedback_id, company_id, status, notes, actor_user_id, actor_name, created_at) '
                            'VALUES (?, ?, ?, ?, ?, ?, ?)'
                        ),
                        (int(payload['feedback_id']), int(feedback['company_id']), status, str(payload.get('notes', '')).strip(), int(actor['id']), actor['full_name'], now)
                    )
                    connection.commit()
                    return send_json(self, 200, {'ok': True})

                elif parsed.path == '/api/feedbacks/triage':
                    require_fields(payload, ['actor_user_id', 'feedback_id'])
                    actor = authorize_action(connection, resolve_actor_user_id(self, parsed, payload), PERM_EPI_FEEDBACK_TRIAGE)
                    result = apply_feedback_triage(connection, actor, int(payload['feedback_id']), payload)
                    connection.commit()
                    return send_json(self, 200, result)

                elif parsed.path == '/api/feedbacks/hseq-review':
                    require_fields(payload, ['actor_user_id', 'feedback_id', 'hseq_opinion'])
                    actor = authorize_action(connection, resolve_actor_user_id(self, parsed, payload), PERM_EPI_FEEDBACK_HSEQ_REVIEW)
                    result = apply_feedback_hseq_review(connection, actor, int(payload['feedback_id']), payload)
                    connection.commit()
                    return send_json(self, 200, result)

                elif parsed.path == '/api/feedbacks/forward-admin':
                    require_fields(payload, ['actor_user_id', 'feedback_id'])
                    actor = authorize_action(connection, resolve_actor_user_id(self, parsed, payload), PERM_EPI_FEEDBACK_TRIAGE)
                    result = apply_feedback_forward_admin(connection, actor, int(payload['feedback_id']), payload)
                    connection.commit()
                    return send_json(self, 200, result)

                elif parsed.path == '/api/feedbacks/admin-decision':
                    require_fields(payload, ['actor_user_id', 'feedback_id', 'decision', 'justification'])
                    actor = authorize_action(connection, resolve_actor_user_id(self, parsed, payload), PERM_EPI_FEEDBACK_ADMIN_APPROVE)
                    result = apply_feedback_admin_decision(connection, actor, int(payload['feedback_id']), payload)
                    connection.commit()
                    return send_json(self, 200, result)

                elif parsed.path == '/api/feedbacks/close':
                    require_fields(payload, ['actor_user_id', 'feedback_id'])
                    actor = authorize_action(connection, resolve_actor_user_id(self, parsed, payload), PERM_EPI_FEEDBACK_CLOSE)
                    result = apply_feedback_close(connection, actor, int(payload['feedback_id']), payload)
                    connection.commit()
                    return send_json(self, 200, result)

                elif parsed.path == '/api/feedbacks/manager-validate':
                    require_fields(payload, ['actor_user_id', 'feedback_id'])
                    actor = authorize_action(connection, resolve_actor_user_id(self, parsed, payload), PERM_EPI_FEEDBACK_MANAGER_EVAL)
                    result = apply_feedback_manager_validate(connection, actor, int(payload['feedback_id']), payload)
                    connection.commit()
                    return send_json(self, 200, result)

                elif parsed.path == '/api/feedbacks/manager-reject':
                    require_fields(payload, ['actor_user_id', 'feedback_id', 'rejection_reason'])
                    actor = authorize_action(connection, resolve_actor_user_id(self, parsed, payload), PERM_EPI_FEEDBACK_MANAGER_EVAL)
                    result = apply_feedback_manager_reject(connection, actor, int(payload['feedback_id']), payload)
                    connection.commit()
                    return send_json(self, 200, result)

                elif parsed.path == '/api/avaliacoes/set-reassessment':
                    require_fields(payload, ['actor_user_id', 'feedback_id', 'period'])
                    actor = authorize_action(connection, resolve_actor_user_id(self, parsed, payload), PERM_EPI_EVALUATION_DECIDE)
                    result = apply_set_reassessment(connection, actor, int(payload['feedback_id']), payload)
                    connection.commit()
                    return send_json(self, 200, result)

                elif parsed.path == '/api/avaliacoes/compute-status':
                    require_fields(payload, ['actor_user_id'])
                    actor = authorize_action(connection, resolve_actor_user_id(self, parsed, payload), PERM_EPI_EVALUATION_DECIDE)
                    result = compute_epi_evaluation_status(connection, actor)
                    connection.commit()
                    return send_json(self, 200, result)

                elif parsed.path == '/api/avaliacoes/accept-suggestion':
                    require_fields(payload, ['actor_user_id', 'feedback_id'])
                    actor = authorize_action(connection, resolve_actor_user_id(self, parsed, payload), PERM_EPI_SUGGESTION_ACCEPT)
                    result = apply_accept_suggestion_as_epi(connection, actor, int(payload['feedback_id']), payload)
                    connection.commit()
                    return send_json(self, 200, result)

                elif parsed.path == '/api/avaliacoes/admin-evaluate':
                    require_fields(payload, ['actor_user_id', 'feedback_id', 'tech_decision'])
                    actor = authorize_action(connection, resolve_actor_user_id(self, parsed, payload), PERM_EPI_EVALUATION_DECIDE)
                    result = apply_admin_technical_evaluate(connection, actor, int(payload['feedback_id']), payload)
                    connection.commit()
                    return send_json(self, 200, result)

                # ── Fase 2 — Compras POST ──────────────────────────────────────
                elif parsed.path == '/api/purchase-requests':
                    require_fields(payload, ['actor_user_id', 'unit_id', 'items'])
                    actor = authorize_action(connection, resolve_actor_user_id(self, parsed, payload), PERM_PURCHASE_REQUESTS_CREATE)
                    company_id = int(actor['company_id'])
                    unit_id = int(payload['unit_id'])
                    unit = get_unit_by_id(connection, unit_id)
                    if not unit:
                        raise ValueError('Unidade não encontrada.')
                    ensure_resource_company(actor, unit, 'Unidade')
                    # Admin local só pode criar requisições para sua própria unidade operacional
                    scope_unit_id = actor_operational_unit_id(connection, actor)
                    if scope_unit_id and int(unit_id) != int(scope_unit_id):
                        return send_json(self, 403, {'ok': False, 'error': {'code': 'UNIT_SCOPE_VIOLATION', 'message': 'Administrador local pode criar requisições apenas para sua própria unidade operacional.'}})
                    items = payload.get('items') or []
                    if not items:
                        raise ValueError('A requisição precisa ter pelo menos um item.')
                    now = datetime.now(UTC).isoformat()
                    title = str(payload.get('title') or f'Requisição {now[:10]}').strip()
                    duplicate_id = find_recent_duplicate_purchase_request(connection, actor, unit_id, title, items, now)
                    if duplicate_id:
                        structured_log('info', 'purchase.request.duplicate_recent_reused', purchase_request_id=duplicate_id, actor_user_id=int(actor['id']))
                        return send_json(self, 200, {'ok': True, 'id': duplicate_id, 'duplicate': True})
                    cursor = connection.execute(
                        "INSERT INTO purchase_requests (company_id, unit_id, status, title, notes, created_by_user_id, created_by_name, created_at, updated_at) VALUES (?, ?, 'open', ?, ?, ?, ?, ?, ?)",
                        (company_id, unit_id, title, str(payload.get('notes') or '').strip(), int(actor['id']), actor['full_name'], now, now)
                    )
                    pr_id = cursor.lastrowid
                    epi_request_ids_to_lock = []
                    for item in items:
                        epi = get_epi_by_id(connection, int(item['epi_id']))
                        if not epi:
                            raise ValueError(f"EPI {item['epi_id']} não encontrado.")
                        connection.execute(
                            'INSERT INTO purchase_request_items (purchase_request_id, company_id, unit_id, epi_id, epi_name, ca, unit_measure, manufacturer, supplier, glove_size, size, uniform_size, quantity_requested, origin, employee_id, employee_name, employee_sector, employee_role, epi_request_id, status, notes, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                            (pr_id, company_id, unit_id, int(item['epi_id']), epi['name'], epi['ca'], epi['unit_measure'], str(item.get('manufacturer') or epi.get('manufacturer') or ''), str(item.get('supplier') or epi.get('supplier_company') or ''), str(item.get('glove_size') or 'N/A'), str(item.get('size') or 'N/A'), str(item.get('uniform_size') or 'N/A'), int(item.get('quantity_requested') or 1), str(item.get('origin') or 'stock_minimum'), int(item['employee_id']) if item.get('employee_id') else None, str(item.get('employee_name') or ''), str(item.get('employee_sector') or ''), str(item.get('employee_role') or ''), int(item['epi_request_id']) if item.get('epi_request_id') else None, 'included_in_request', str(item.get('notes') or ''), now, now)
                        )
                        if item.get('epi_request_id'):
                            epi_request_ids_to_lock.append(int(item['epi_request_id']))
                    for epi_req_id in epi_request_ids_to_lock:
                        connection.execute("UPDATE epi_requests SET status = 'em análise', last_updated_at = ? WHERE id = ?", (now, epi_req_id))
                    _record_purchase_event(connection, company_id, 'purchase_request', pr_id, 'created', '', 'open', '', int(actor['id']), actor['full_name'], getattr(self, 'client_address', ('',))[0] or '')
                    connection.commit()
                    return send_json(self, 201, {'ok': True, 'id': pr_id})

                elif re.match(r'^/api/purchase-requests/(\d+)/review-items$', parsed.path or ''):
                    review_items_match = re.match(r'^/api/purchase-requests/(\d+)/review-items$', parsed.path)
                    require_fields(payload, ['actor_user_id'])
                    actor = authorize_action(connection, resolve_actor_user_id(self, parsed, payload), PERM_PURCHASE_REQUESTS_UPDATE)
                    pr_id = int(review_items_match.group(1))
                    pr = connection.execute('SELECT * FROM purchase_requests WHERE id = ?', (pr_id,)).fetchone()
                    if not pr:
                        raise ValueError('Requisição não encontrada.')
                    ensure_purchase_request_action_scope(connection, actor, pr)
                    if str(pr['status']) != 'waiting_requester_correction':
                        raise ValueError('Itens só podem ser revisados quando a requisição aguarda correção do requisitante.')
                    now = datetime.now(UTC).isoformat()
                    affected = []
                    for item in payload.get('updates') or []:
                        item_id = int(item.get('id') or 0)
                        qty = int(item.get('quantity_requested') or 1)
                        if item_id <= 0 or qty <= 0:
                            continue
                        connection.execute('UPDATE purchase_request_items SET quantity_requested = ?, notes = ?, updated_at = ? WHERE id = ? AND purchase_request_id = ? AND status NOT IN (\'approved\', \'ordered\', \'received\', \'closed\')', (qty, str(item.get('notes') or '').strip(), now, item_id, pr_id))
                        affected.append(item_id)
                    remove_ids = [int(item_id) for item_id in (payload.get('remove_item_ids') or []) if str(item_id).isdigit()]
                    if remove_ids:
                        placeholders = ','.join('?' for _ in remove_ids)
                        connection.execute(f"DELETE FROM purchase_request_items WHERE purchase_request_id = ? AND id IN ({placeholders}) AND status NOT IN ('approved', 'ordered', 'received', 'closed')", (pr_id, *remove_ids))
                        affected.extend(remove_ids)
                    for item in payload.get('add_items') or []:
                        epi = get_epi_by_id(connection, int(item.get('epi_id') or 0))
                        if not epi:
                            raise ValueError(f"EPI {item.get('epi_id')} não encontrado.")
                        qty = int(item.get('quantity_requested') or 1)
                        if qty <= 0:
                            raise ValueError('Quantidade inválida.')
                        cursor = connection.execute(
                            'INSERT INTO purchase_request_items (purchase_request_id, company_id, unit_id, epi_id, epi_name, ca, unit_measure, manufacturer, supplier, glove_size, size, uniform_size, quantity_requested, origin, employee_id, employee_name, employee_sector, employee_role, epi_request_id, status, notes, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                            (pr_id, int(pr['company_id']), int(pr['unit_id']), int(epi['id']), epi['name'], epi['ca'], epi['unit_measure'], str(item.get('manufacturer') or epi.get('manufacturer') or ''), str(item.get('supplier') or epi.get('supplier_company') or ''), str(item.get('glove_size') or 'N/A'), str(item.get('size') or 'N/A'), str(item.get('uniform_size') or 'N/A'), qty, str(item.get('origin') or 'manual'), int(item['employee_id']) if item.get('employee_id') else None, str(item.get('employee_name') or ''), str(item.get('employee_sector') or ''), str(item.get('employee_role') or ''), int(item['epi_request_id']) if item.get('epi_request_id') else None, 'included_in_request', str(item.get('notes') or ''), now, now)
                        )
                        affected.append(int(cursor.lastrowid))
                    connection.execute('UPDATE purchase_requests SET notes = COALESCE(NULLIF(?, \'\'), notes), updated_at = ? WHERE id = ?', (str(payload.get('notes') or '').strip(), now, pr_id))
                    _record_purchase_event(connection, int(pr['company_id']), 'purchase_request', pr_id, 'requester_review_saved', str(pr['status']), str(pr['status']), 'Itens afetados: ' + ', '.join(str(item_id) for item_id in affected), int(actor['id']), actor['full_name'], getattr(self, 'client_address', ('',))[0] or '', actor.get('role') or '', str(payload.get('reason') or ''), 'requester')
                    connection.commit()
                    return send_json(self, 200, {'ok': True, 'affected_item_ids': affected})

                elif re.match(r'^/api/purchase-requests/(\d+)/workflow$', parsed.path or ''):
                    workflow_match = re.match(r'^/api/purchase-requests/(\d+)/workflow$', parsed.path)
                    require_fields(payload, ['actor_user_id', 'action'])
                    actor = authorize_action(connection, resolve_actor_user_id(self, parsed, payload), PERM_PURCHASE_REQUESTS_VIEW)
                    result = apply_purchase_request_workflow_action(
                        connection,
                        actor,
                        int(workflow_match.group(1)),
                        payload,
                        getattr(self, 'client_address', ('',))[0] or '',
                    )
                    connection.commit()
                    return send_json(self, 200, result)

                elif re.match(r'^/api/purchase-requests/(\d+)/status$', parsed.path or ''):
                    pr_status_match = re.match(r'^/api/purchase-requests/(\d+)/status$', parsed.path)
                    require_fields(payload, ['actor_user_id', 'status'])
                    actor = authorize_action(connection, resolve_actor_user_id(self, parsed, payload), PERM_PURCHASE_REQUESTS_UPDATE)
                    pr_id = int(pr_status_match.group(1))
                    pr = connection.execute('SELECT * FROM purchase_requests WHERE id = ?', (pr_id,)).fetchone()
                    if not pr:
                        raise ValueError('Requisição não encontrada.')
                    ensure_purchase_request_action_scope(connection, actor, pr)
                    valid_statuses = {'draft','open','sent_to_buyer','quoted','pending_approval','partially_approved','approved','rejected','returned_to_buyer','waiting_buyer_correction','buyer_resubmitted','waiting_requester_correction','requester_resubmitted','postponed','po_generated','received','checked','closed','cancelled'}
                    new_status = str(payload.get('status') or '').strip()
                    if new_status not in valid_statuses:
                        raise ValueError('Status inválido para requisição de compra.')
                    old_status = str(pr['status'])
                    now = datetime.now(UTC).isoformat()
                    extra = {}
                    if new_status == 'sent_to_buyer':
                        extra['sent_to_buyer_at'] = now
                    elif new_status in ('closed', 'cancelled'):
                        extra['closed_at'] = now
                    elif new_status == 'postponed':
                        postponed_until = str(payload.get('postponed_until') or '').strip()
                        if postponed_until:
                            extra['postponed_until'] = postponed_until
                    set_clause = ', '.join([f'{k} = ?' for k in ['status', 'updated_at', *extra.keys()]])
                    connection.execute(f'UPDATE purchase_requests SET {set_clause} WHERE id = ?', [new_status, now, *extra.values(), pr_id])
                    stock_entries = 0
                    if new_status == 'closed':
                        connection.execute("UPDATE purchase_request_items SET status = 'closed', updated_at = ? WHERE purchase_request_id = ?", (now, pr_id))
                    elif new_status == 'checked':
                        received_items_payload = payload.get('received_items') or []
                        if received_items_payload:
                            for item_data in received_items_payload:
                                item_id = int(str(item_data.get('id') or '').strip() or '0')
                                if not item_id:
                                    continue
                                item_status = 'received' if item_data.get('received') else 'not_received'
                                connection.execute(
                                    'UPDATE purchase_request_items SET status = ?, updated_at = ? WHERE id = ? AND purchase_request_id = ?',
                                    (item_status, now, item_id, pr_id)
                                )
                        else:
                            connection.execute(
                                "UPDATE purchase_request_items SET status = 'checked', updated_at = ? WHERE purchase_request_id = ? AND status NOT IN ('not_received', 'closed')",
                                (now, pr_id)
                            )
                        if old_status == 'received':
                            stock_entries = _auto_add_received_items_to_stock(
                                connection, pr_id, received_items_payload,
                                int(actor['id']), actor['full_name'], now
                            )
                    elif new_status == 'received':
                        connection.execute(
                            "UPDATE purchase_request_items SET status = 'received', updated_at = ? WHERE purchase_request_id = ? AND status = 'included_in_request'",
                            (now, pr_id)
                        )
                    _record_purchase_event(connection, int(pr['company_id']), 'purchase_request', pr_id, 'status_changed', old_status, new_status, str(payload.get('comment') or ''), int(actor['id']), actor['full_name'], getattr(self, 'client_address', ('',))[0] or '')
                    connection.commit()
                    return send_json(self, 200, {'ok': True, 'stock_entries': stock_entries})

                elif re.match(r'^/api/purchase-requests/(\d+)/save-prices$', parsed.path or ''):
                    pr_sp_match = re.match(r'^/api/purchase-requests/(\d+)/save-prices$', parsed.path)
                    require_fields(payload, ['actor_user_id', 'items'])
                    actor = authorize_action(connection, resolve_actor_user_id(self, parsed, payload), PERM_PURCHASE_REQUESTS_UPDATE)
                    pr_id = int(pr_sp_match.group(1))
                    pr = connection.execute('SELECT * FROM purchase_requests WHERE id = ?', (pr_id,)).fetchone()
                    if not pr:
                        raise ValueError('Requisição não encontrada.')
                    ensure_purchase_request_action_scope(connection, actor, pr)
                    items = payload.get('items') or []
                    now = datetime.now(UTC).isoformat()
                    for row_number, item in enumerate(items, start=1):
                        item_id = item.get('item_id')
                        if not item_id:
                            structured_log('warning', 'import.row_failed', line=row_number, reason='purchase_request_item_id ausente')
                            continue
                        try:
                            unit_price_decimal = parse_money_decimal(item.get('unit_price'))
                            qty = int(item.get('quantity') or 1)
                            if qty <= 0:
                                raise ValueError('Quantidade inválida.')
                        except Exception as exc:
                            structured_log('warning', 'import.row_failed', line=row_number, reason=str(exc), item_id=item_id)
                            continue
                        unit_price = float(unit_price_decimal)
                        total_price = float(unit_price_decimal * qty)
                        cursor = connection.execute(
                            'UPDATE purchase_request_items SET unit_price=?, total_price=?, updated_at=? WHERE id=? AND purchase_request_id=?',
                            (unit_price, total_price, now, int(item_id), pr_id)
                        )
                        if cursor.rowcount:
                            structured_log('info', 'import.row_parsed', line=row_number, item_id=int(item_id), valor_unitario=f'{unit_price_decimal:.2f}', total=f'{(unit_price_decimal * qty):.2f}')
                        else:
                            structured_log('warning', 'import.row_failed', line=row_number, item_id=item_id, reason='Item da requisição não encontrado')
                    quote_edit_statuses = {'sent_to_buyer', 'waiting_buyer_correction', 'returned_to_buyer', 'quoted', 'buyer_resubmitted', 'pending_approval', 'postponed'}
                    old_status = str(pr['status'])
                    new_status = old_status
                    if old_status in {'sent_to_buyer', 'waiting_buyer_correction', 'returned_to_buyer', 'buyer_resubmitted'}:
                        new_status = 'quoted'
                        connection.execute('UPDATE purchase_requests SET status=?, updated_at=? WHERE id=?', (new_status, now, pr_id))
                    elif old_status in quote_edit_statuses:
                        connection.execute('UPDATE purchase_requests SET updated_at=? WHERE id=?', (now, pr_id))
                    if old_status in quote_edit_statuses:
                        _record_purchase_event(connection, int(pr['company_id']), 'purchase_request', pr_id, 'quote_prices_saved', old_status, new_status, 'Preços da cotação salvos', int(actor['id']), actor['full_name'], getattr(self, 'client_address', ('',))[0] or '', actor.get('role') or '', '', 'buyer')
                    connection.commit()
                    return send_json(self, 200, {'ok': True, 'status': new_status})

                elif parsed.path == '/api/purchase-quote-file/parse':
                    require_fields(payload, ['actor_user_id', 'filename', 'content_base64'])
                    authorize_action(connection, resolve_actor_user_id(self, parsed, payload), PERM_PURCHASE_REQUESTS_UPDATE)
                    encoded_content = str(payload.get('content_base64') or '')
                    if ',' in encoded_content and encoded_content.lower().startswith('data:'):
                        encoded_content = encoded_content.split(',', 1)[1]
                    try:
                        file_bytes = base64.b64decode(encoded_content, validate=True)
                    except (binascii.Error, ValueError) as exc:
                        raise ValueError('Arquivo inválido para importação.') from exc
                    rows = parse_purchase_quote_file(file_bytes, str(payload.get('filename') or ''))
                    return send_json(self, 200, {'items': rows})

                elif parsed.path == '/api/purchase-orders':
                    require_fields(payload, ['actor_user_id', 'unit_id', 'supplier', 'items'])
                    actor = authorize_action(connection, resolve_actor_user_id(self, parsed, payload), PERM_PO_CREATE)
                    company_id = int(actor['company_id'])
                    unit_id = int(payload['unit_id'])
                    purchase_scope = get_actor_purchase_unit_scope(connection, actor)
                    if purchase_scope is not None and unit_id not in purchase_scope:
                        raise PermissionError('Comprador não está habilitado para criar POs nesta unidade.')
                    unit = get_unit_by_id(connection, unit_id)
                    if not unit:
                        raise ValueError('Unidade não encontrada.')
                    ensure_resource_company(actor, unit, 'Unidade')
                    items = payload.get('items') or []
                    if not items:
                        raise ValueError('A PO precisa ter pelo menos um item.')
                    now = datetime.now(UTC).isoformat()
                    pr_id = int(payload['purchase_request_id']) if payload.get('purchase_request_id') else None
                    approved_pr_items = {}
                    if pr_id:
                        pr_scope = connection.execute('SELECT * FROM purchase_requests WHERE id = ?', (pr_id,)).fetchone()
                        if not pr_scope:
                            raise ValueError('Requisição vinculada não encontrada.')
                        ensure_purchase_request_action_scope(connection, actor, row_to_dict(pr_scope))
                        if int(pr_scope['unit_id']) != unit_id:
                            raise ValueError('Unidade da PO deve ser a mesma da requisição vinculada.')
                        if str(pr_scope['status']) in {'approved', 'partially_approved'}:
                            approved_pr_items = approved_purchase_request_items_for_po(connection, pr_id, items)
                    total_value = 0.0
                    for total_item in items:
                        total_price_decimal = parse_money_decimal(total_item.get('unit_price'))
                        total_qty = int(total_item.get('quantity') or 1)
                        total_pr_item_id = int(total_item['purchase_request_item_id']) if total_item.get('purchase_request_item_id') else None
                        if approved_pr_items and total_pr_item_id in approved_pr_items:
                            approved_total_item = approved_pr_items[total_pr_item_id]
                            total_qty = int(approved_total_item.get('quantity_approved') or approved_total_item.get('quantity_requested') or total_qty)
                        total_value += float(total_price_decimal * total_qty)
                    po_number = str(payload.get('po_number') or '').strip() or generate_po_number(connection, company_id)
                    cursor = connection.execute(
                        "INSERT INTO purchase_orders (purchase_request_id, company_id, unit_id, status, po_number, supplier, supplier_cnpj, expected_delivery_date, notes, total_value, created_by_user_id, created_by_name, created_at, updated_at) VALUES (?, ?, ?, 'waiting_admin_review', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (pr_id, company_id, unit_id, po_number, str(payload['supplier']).strip(), str(payload.get('supplier_cnpj') or '').strip(), str(payload.get('expected_delivery_date') or '').strip(), str(payload.get('notes') or '').strip(), total_value, int(actor['id']), actor['full_name'], now, now)
                    )
                    po_id = cursor.lastrowid
                    for item in items:
                        epi = get_epi_by_id(connection, int(item['epi_id']))
                        if not epi:
                            raise ValueError(f"EPI {item['epi_id']} não encontrado.")
                        qty = int(item.get('quantity') or 1)
                        unit_price_decimal = parse_money_decimal(item.get('unit_price'))
                        unit_price = float(unit_price_decimal)
                        total_price = float(unit_price_decimal * qty)
                        pr_item_id = int(item['purchase_request_item_id']) if item.get('purchase_request_item_id') else None
                        if pr_id and approved_pr_items:
                            if not pr_item_id:
                                raise ValueError('PO vinculada a requisição aprovada deve informar o item aprovado da requisição.')
                            if pr_item_id not in approved_pr_items:
                                raise ValueError('Somente itens aprovados podem ser incluídos na PO.')
                            approved_pr_item = approved_pr_items[pr_item_id]
                            qty = int(approved_pr_item.get('quantity_approved') or approved_pr_item.get('quantity_requested') or qty)
                            total_price = float(unit_price_decimal * qty)
                        connection.execute(
                            'INSERT INTO purchase_order_items (purchase_order_id, purchase_request_item_id, company_id, unit_id, epi_id, epi_name, ca, unit_measure, manufacturer, supplier, glove_size, size, uniform_size, quantity, unit_price, total_price, origin, employee_name, employee_sector, employee_role, status, notes, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                            (po_id, pr_item_id, company_id, unit_id, int(item['epi_id']), epi['name'], epi['ca'], epi['unit_measure'], str(item.get('manufacturer') or epi.get('manufacturer') or ''), str(item.get('supplier') or payload['supplier']), str(item.get('glove_size') or 'N/A'), str(item.get('size') or 'N/A'), str(item.get('uniform_size') or 'N/A'), qty, unit_price, total_price, str(item.get('origin') or 'stock_minimum'), str(item.get('employee_name') or ''), str(item.get('employee_sector') or ''), str(item.get('employee_role') or ''), 'waiting_admin_review', str(item.get('notes') or ''), now, now)
                        )
                        if pr_item_id and pr_id:
                            connection.execute(
                                'UPDATE purchase_request_items SET unit_price=?, total_price=?, updated_at=? WHERE id=?',
                                (unit_price, total_price, now, pr_item_id)
                            )
                    if pr_id:
                        connection.execute("UPDATE purchase_requests SET status = 'po_generated', updated_at = ? WHERE id = ?", (now, pr_id))
                    _record_purchase_event(connection, company_id, 'purchase_order', po_id, 'created', '', 'waiting_admin_review', '', int(actor['id']), actor['full_name'], getattr(self, 'client_address', ('',))[0] or '')
                    connection.commit()
                    return send_json(self, 201, {'ok': True, 'id': po_id})

                elif re.match(r'^/api/purchase-orders/(\d+)/approve$', parsed.path or ''):
                    po_approve_match = re.match(r'^/api/purchase-orders/(\d+)/approve$', parsed.path)
                    require_fields(payload, ['actor_user_id', 'decision'])
                    actor = authorize_action(connection, resolve_actor_user_id(self, parsed, payload), PERM_PO_APPROVE)
                    po_id = int(po_approve_match.group(1))
                    po = connection.execute('SELECT * FROM purchase_orders WHERE id = ?', (po_id,)).fetchone()
                    if not po:
                        raise ValueError('PO não encontrada.')
                    ensure_resource_company(actor, po, 'PO')
                    decision = str(payload.get('decision') or '').strip().lower()
                    if decision not in ('approved', 'partially_approved', 'rejected', 'postponed'):
                        raise ValueError('Decisão deve ser approved, partially_approved, rejected ou postponed.')
                    comment = str(payload.get('comment') or '').strip()
                    postponed_until = str(payload.get('postponed_until') or '').strip()
                    if decision in ('rejected', 'partially_approved') and not comment:
                        raise ValueError('Comentário obrigatório para rejeição ou aprovação parcial.')
                    if decision == 'postponed' and not postponed_until:
                        raise ValueError('Data de prorrogação obrigatória para prorrogar a aprovação.')
                    now = datetime.now(UTC).isoformat()
                    old_status = str(po['status'])
                    po_number = str(po['po_number'] or f'PO-{po_id}')
                    if decision == 'postponed':
                        connection.execute(
                            'UPDATE purchase_orders SET status = ?, postponed_until = ?, approval_comment = ?, updated_at = ? WHERE id = ?',
                            (decision, postponed_until, comment, now, po_id)
                        )
                    else:
                        connection.execute(
                            'UPDATE purchase_orders SET status = ?, approved_by_user_id = ?, approved_by_name = ?, approved_at = ?, approval_comment = ?, updated_at = ? WHERE id = ?',
                            (decision, int(actor['id']), actor['full_name'], now, comment, now, po_id)
                        )
                    connection.execute(
                        'INSERT INTO purchase_approvals (purchase_order_id, company_id, decision, comment, actor_user_id, actor_name, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)',
                        (po_id, int(po['company_id']), decision, comment, int(actor['id']), actor['full_name'], now)
                    )
                    item_decisions_payload = payload.get('decisions') or payload.get('item_decisions') or []
                    if item_decisions_payload and isinstance(item_decisions_payload, list):
                        for d in item_decisions_payload:
                            item_id = int(d.get('item_id') or d.get('id') or 0)
                            if not item_id:
                                continue
                            item_status = 'approved' if d.get('approved') else 'rejected'
                            connection.execute(
                                'UPDATE purchase_order_items SET status = ?, updated_at = ? WHERE id = ? AND purchase_order_id = ?',
                                (item_status, now, item_id, po_id)
                            )
                    elif decision == 'approved':
                        connection.execute("UPDATE purchase_order_items SET status = 'approved', updated_at = ? WHERE purchase_order_id = ?", (now, po_id))
                    elif decision == 'rejected':
                        connection.execute("UPDATE purchase_order_items SET status = 'rejected', updated_at = ? WHERE purchase_order_id = ?", (now, po_id))
                    # Propaga resultado para a Requisição vinculada.
                    # Admin Local vê status + nº PO para conferência do material.
                    if po['purchase_request_id']:
                        pr_status = decision  # approved/partially_approved/rejected/postponed
                        connection.execute(
                            'UPDATE purchase_requests SET status = ?, postponed_until = ?, linked_po_number = ?, linked_po_id = ?, updated_at = ? WHERE id = ?',
                            (pr_status, postponed_until if decision == 'postponed' else '', po_number, po_id, now, int(po['purchase_request_id']))
                        )
                        _record_purchase_event(connection, int(po['company_id']), 'purchase_request', int(po['purchase_request_id']), 'approval_propagated', 'po_generated', pr_status, comment, int(actor['id']), actor['full_name'], getattr(self, 'client_address', ('',))[0] or '')
                    _record_purchase_event(connection, int(po['company_id']), 'purchase_order', po_id, 'decision', old_status, decision, comment + (f' | Prorrogado até: {postponed_until}' if postponed_until else ''), int(actor['id']), actor['full_name'], getattr(self, 'client_address', ('',))[0] or '')
                    connection.commit()
                    return send_json(self, 200, {'ok': True})

                elif re.match(r'^/api/purchase-orders/(\d+)/receive$', parsed.path or ''):
                    po_receive_match = re.match(r'^/api/purchase-orders/(\d+)/receive$', parsed.path)
                    require_fields(payload, ['actor_user_id', 'action'])
                    actor = authorize_action(connection, resolve_actor_user_id(self, parsed, payload), PERM_PO_RECEIVE)
                    po_id = int(po_receive_match.group(1))
                    po = connection.execute('SELECT * FROM purchase_orders WHERE id = ?', (po_id,)).fetchone()
                    if not po:
                        raise ValueError('PO não encontrada.')
                    ensure_resource_company(actor, po, 'PO')
                    action = str(payload.get('action') or '').strip().lower()
                    if action not in ('received', 'received_partial', 'checked', 'closed'):
                        raise ValueError('Ação deve ser received, received_partial, checked ou closed.')
                    now = datetime.now(UTC).isoformat()
                    old_status = str(po['status'])
                    new_status = action
                    update_fields = {'status': new_status, 'updated_at': now}
                    if action in ('received', 'received_partial'):
                        received_items = payload.get('items') or []
                        notes = str(payload.get('notes') or '').strip()
                        if action == 'received_partial' and not notes:
                            raise ValueError('Observação obrigatória em recebimento parcial.')
                        po_items = [row_to_dict(row) for row in connection.execute('SELECT * FROM purchase_order_items WHERE purchase_order_id = ?', (po_id,)).fetchall()]
                        if not received_items:
                            received_items = [{'id': item['id'], 'quantity_received': item.get('quantity') or 1, 'received': True} for item in po_items]
                        received_by_id = {int(item.get('id') or 0): item for item in received_items}
                        all_received = True
                        for item in po_items:
                            payload_item = received_by_id.get(int(item['id']))
                            qty_ordered = int(item.get('quantity') or 1)
                            qty_received = int(payload_item.get('quantity_received') or 0) if payload_item else 0
                            qty_received = max(0, min(qty_received, qty_ordered))
                            item_status = 'received' if qty_received >= qty_ordered else ('received_partial' if qty_received > 0 else 'not_received')
                            if qty_received < qty_ordered:
                                all_received = False
                            connection.execute('UPDATE purchase_order_items SET quantity_received = ?, status = ?, notes = ?, updated_at = ? WHERE id = ? AND purchase_order_id = ?', (qty_received, item_status, notes, now, int(item['id']), po_id))
                            if item.get('purchase_request_item_id'):
                                connection.execute('UPDATE purchase_request_items SET status = ?, updated_at = ? WHERE id = ?', (item_status, now, int(item['purchase_request_item_id'])))
                        new_status = 'received' if all_received else 'received_partial'
                        update_fields['status'] = new_status
                        update_fields['received_by_user_id'] = int(actor['id'])
                        update_fields['received_by_name'] = actor['full_name']
                        update_fields['received_at'] = now
                        if po.get('purchase_request_id'):
                            connection.execute('UPDATE purchase_requests SET status = ?, updated_at = ? WHERE id = ?', (new_status, now, int(po['purchase_request_id'])))
                    elif action == 'checked':
                        update_fields['checked_at'] = now
                        po_stock_entries = 0
                        if po.get('purchase_request_id'):
                            pr_id_from_po = int(po['purchase_request_id'])
                            connection.execute('UPDATE purchase_requests SET status = ?, updated_at = ? WHERE id = ?', ('checked', now, pr_id_from_po))
                            connection.execute(
                                "UPDATE purchase_request_items SET status = 'checked', updated_at = ? WHERE id IN "
                                "(SELECT purchase_request_item_id FROM purchase_order_items WHERE purchase_order_id = ? AND purchase_request_item_id IS NOT NULL AND status != 'not_received')",
                                (now, po_id)
                            )
                            if old_status in ('received', 'received_partial'):
                                po_stock_entries = _auto_add_received_items_to_stock(
                                    connection, pr_id_from_po, [],
                                    int(actor['id']), actor['full_name'], now
                                )
                    elif action == 'closed':
                        update_fields['closed_at'] = now
                        connection.execute("UPDATE purchase_order_items SET status = 'closed', updated_at = ? WHERE purchase_order_id = ?", (now, po_id))
                        if po.get('purchase_request_id'):
                            connection.execute(
                                "UPDATE purchase_request_items SET status = 'closed', updated_at = ? WHERE id IN "
                                "(SELECT purchase_request_item_id FROM purchase_order_items WHERE purchase_order_id = ? AND purchase_request_item_id IS NOT NULL)",
                                (now, po_id)
                            )
                            connection.execute('UPDATE purchase_requests SET status = ?, updated_at = ? WHERE id = ?', ('closed', now, int(po['purchase_request_id'])))
                    set_clause = ', '.join(f'{k} = ?' for k in update_fields)
                    connection.execute(f'UPDATE purchase_orders SET {set_clause} WHERE id = ?', [*update_fields.values(), po_id])
                    _record_purchase_event(connection, int(po['company_id']), 'purchase_order', po_id, action, old_status, new_status, str(payload.get('notes') or ''), int(actor['id']), actor['full_name'], getattr(self, 'client_address', ('',))[0] or '', actor.get('role') or '', '', 'receiving')
                    connection.commit()
                    return send_json(self, 200, {'ok': True, 'status': new_status})

                elif re.match(r'^/api/purchase-orders/(\d+)/review$', parsed.path or ''):
                    po_review_match = re.match(r'^/api/purchase-orders/(\d+)/review$', parsed.path)
                    require_fields(payload, ['actor_user_id', 'decision'])
                    actor = authorize_action(connection, resolve_actor_user_id(self, parsed, payload), PERM_PO_REVIEW)
                    po_id = int(po_review_match.group(1))
                    po = connection.execute('SELECT * FROM purchase_orders WHERE id = ?', (po_id,)).fetchone()
                    if not po:
                        raise ValueError('PO não encontrada.')
                    ensure_resource_company(actor, po, 'PO')
                    if str(po['status']) != 'waiting_admin_review':
                        raise ValueError('Somente POs aguardando revisão operacional podem ser revisadas pelo Admin.')
                    decision = str(payload.get('decision') or '').strip().lower()
                    if decision not in ('approved_operational', 'returned_with_suggestions'):
                        raise ValueError('Decisão deve ser approved_operational ou returned_with_suggestions.')
                    comment = str(payload.get('comment') or '').strip()
                    suggestions = str(payload.get('suggestions') or '').strip()
                    if decision == 'returned_with_suggestions' and not suggestions:
                        raise ValueError('Sugestões obrigatórias ao devolver cotação ao comprador.')
                    now = datetime.now(UTC).isoformat()
                    old_status = str(po['status'])
                    new_status = 'pending_approval' if decision == 'approved_operational' else 'quoted'
                    connection.execute(
                        'UPDATE purchase_orders SET status = ?, admin_review_by_user_id = ?, admin_review_by_name = ?, admin_review_at = ?, admin_review_comment = ?, buyer_suggestions = ?, updated_at = ? WHERE id = ?',
                        (new_status, int(actor['id']), actor['full_name'], now, comment, suggestions, now, po_id)
                    )
                    if po['purchase_request_id']:
                        pr_new = 'pending_approval' if decision == 'approved_operational' else 'quoted'
                        connection.execute('UPDATE purchase_requests SET status = ?, updated_at = ? WHERE id = ?', (pr_new, now, int(po['purchase_request_id'])))
                    _record_purchase_event(connection, int(po['company_id']), 'purchase_order', po_id, 'admin_review', old_status, new_status, (comment or suggestions), int(actor['id']), actor['full_name'], getattr(self, 'client_address', ('',))[0] or '')
                    connection.commit()
                    return send_json(self, 200, {'ok': True, 'new_status': new_status})

                elif re.match(r'^/api/purchase-orders/(\d+)/resubmit$', parsed.path or ''):
                    resubmit_match = re.match(r'^/api/purchase-orders/(\d+)/resubmit$', parsed.path)
                    require_fields(payload, ['actor_user_id'])
                    actor = authorize_action(connection, resolve_actor_user_id(self, parsed, payload), PERM_PO_CREATE)
                    po_id = int(resubmit_match.group(1))
                    po = connection.execute('SELECT * FROM purchase_orders WHERE id = ?', (po_id,)).fetchone()
                    if not po:
                        raise ValueError('PO não encontrada.')
                    ensure_resource_company(actor, po, 'PO')
                    if str(po['status']) != 'quoted':
                        raise ValueError('Apenas POs devolvidas com sugestões (quoted) podem ser reenviadas.')
                    now = datetime.now(UTC).isoformat()
                    notes = str(payload.get('notes') or '').strip()
                    connection.execute(
                        'UPDATE purchase_orders SET status = ?, buyer_suggestions = ?, updated_at = ? WHERE id = ?',
                        ('waiting_admin_review', '', now, po_id)
                    )
                    if po['purchase_request_id']:
                        connection.execute('UPDATE purchase_requests SET status = ?, updated_at = ? WHERE id = ?', ('waiting_admin_review', now, int(po['purchase_request_id'])))
                    _record_purchase_event(connection, int(po['company_id']), 'purchase_order', po_id, 'resubmit', 'quoted', 'waiting_admin_review', notes, int(actor['id']), actor['full_name'], getattr(self, 'client_address', ('',))[0] or '')
                    connection.commit()
                    return send_json(self, 200, {'ok': True})

                elif parsed.path == '/api/purchase-functions':
                    require_fields(payload, ['actor_user_id', 'employee_id', 'role_type'])
                    actor = authorize_action(connection, resolve_actor_user_id(self, parsed, payload), PERM_UNIT_LINKS_MANAGE)
                    require_purchase_function_admin(actor)
                    company_id = int(actor['company_id'])
                    employee_id = int(payload['employee_id'])
                    role_type = normalize_purchase_function_type(payload.get('role_type'))
                    raw_unit_ids = payload.get('unit_ids')
                    if raw_unit_ids is None:
                        raw_unit_ids = [payload.get('unit_id')]
                    unit_ids = sorted({int(uid) for uid in raw_unit_ids if str(uid or '').strip()})
                    if not unit_ids:
                        raise ValueError('Selecione ao menos uma unidade.')
                    employee = get_employee_by_id(connection, employee_id)
                    if not employee:
                        raise ValueError('Colaborador não encontrado.')
                    if int(employee['company_id']) != company_id:
                        raise PermissionError('Colaborador pertence a outra empresa.')
                    # Validar: colaborador deve ter conta de usuário ativa com perfil buyer ou approver
                    linked_user = connection.execute(
                        'SELECT id, role FROM users WHERE linked_employee_id = ? AND role = ? AND active = 1 LIMIT 1',
                        (employee_id, role_type)
                    ).fetchone()
                    if not linked_user:
                        role_label = PURCHASE_FUNCTION_LABELS.get(role_type, role_type)
                        raise ValueError(
                            f'O colaborador não possui conta de usuário ativa com perfil "{role_label}". '
                            f'Cadastre o usuário com o perfil correto antes de vincular.'
                        )
                    structured_log('info', 'purchase_function.link_validated', employee_id=employee_id, role_type=role_type, user_id=int(linked_user['id']))
                    placeholders = ','.join(['?'] * len(unit_ids))
                    valid_units = connection.execute(
                        f'SELECT id FROM units WHERE company_id = ? AND id IN ({placeholders})',
                        (company_id, *unit_ids)
                    ).fetchall()
                    valid_unit_ids = {int(row['id']) for row in valid_units}
                    if valid_unit_ids != set(unit_ids):
                        raise ValueError('Uma ou mais unidades são inválidas para a empresa.')
                    now = datetime.now(UTC).isoformat()
                    created_ids = []
                    for unit_id in unit_ids:
                        existing = connection.execute(
                            'SELECT id FROM purchase_role_unit_links WHERE employee_id = ? AND role_type = ? AND unit_id = ?',
                            (employee_id, role_type, unit_id)
                        ).fetchone()
                        if existing:
                            created_ids.append(int(existing['id']))
                            continue
                        cur = connection.execute(
                            'INSERT INTO purchase_role_unit_links (company_id, employee_id, role_type, unit_id, created_by_user_id, created_at) VALUES (?, ?, ?, ?, ?, ?)',
                            (company_id, employee_id, role_type, unit_id, int(actor['id']), now)
                        )
                        created_ids.append(int(cur.lastrowid))
                    connection.commit()
                    return send_json(self, 201, {'ok': True, 'ids': created_ids})

                elif parsed.path == '/api/company-purchase-config':
                    require_fields(payload, ['actor_user_id'])
                    actor = authorize_action(connection, resolve_actor_user_id(self, parsed, payload), PERM_PURCHASE_REQUESTS_UPDATE)
                    if actor.get('role') not in ('master_admin', 'general_admin'):
                        raise PermissionError('Apenas o Administrador Geral pode configurar o fluxo de compras.')
                    raw_cid = str(payload.get('company_id') or actor.get('company_id') or '').strip()
                    if not raw_cid or raw_cid == 'None':
                        raise ValueError('Empresa não identificada. Informe company_id.')
                    cid = int(raw_cid)
                    row = connection.execute('SELECT value FROM app_meta WHERE key = ?', (f'purchase_config_{cid}',)).fetchone()
                    config = json.loads(row['value']) if row else {}
                    if 'require_admin_review' in payload:
                        config['require_admin_review'] = bool(payload['require_admin_review'])
                    connection.execute('INSERT INTO app_meta (key, value) VALUES (?, ?) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value', (f'purchase_config_{cid}', json.dumps(config)))
                    connection.commit()
                    return send_json(self, 200, {'ok': True, 'config': config})

                elif parsed.path == '/api/user-unit-links':
                    require_fields(payload, ['actor_user_id', 'target_user_id', 'unit_id'])
                    actor = authorize_action(connection, resolve_actor_user_id(self, parsed, payload), PERM_UNIT_LINKS_MANAGE)
                    company_id = int(actor['company_id'])
                    target_user_id = int(payload['target_user_id'])
                    unit_id = int(payload['unit_id'])
                    target = connection.execute('SELECT id, role, company_id FROM users WHERE id = ?', (target_user_id,)).fetchone()
                    if not target:
                        raise ValueError('Usuário não encontrado.')
                    if int(target['company_id']) != company_id:
                        raise PermissionError('Usuário pertence a outra empresa.')
                    if str(target['role']) not in ('buyer', 'approver'):
                        raise ValueError('Vínculos de unidade só se aplicam a compradores e aprovadores.')
                    unit = connection.execute('SELECT id FROM units WHERE id = ? AND company_id = ?', (unit_id, company_id)).fetchone()
                    if not unit:
                        raise ValueError('Unidade não encontrada ou pertence a outra empresa.')
                    now = datetime.now(UTC).isoformat()
                    try:
                        cur = connection.execute(
                            'INSERT INTO user_unit_links (company_id, user_id, unit_id, created_by_user_id, created_at) VALUES (?, ?, ?, ?, ?)',
                            (company_id, target_user_id, unit_id, int(actor['id']), now)
                        )
                        link_id = int(cur.lastrowid)
                        connection.commit()
                    except Exception:
                        raise ValueError('Este vínculo já existe.')
                    return send_json(self, 201, {'ok': True, 'id': link_id})

                elif parsed.path == '/api/authorized-suppliers':
                    require_fields(payload, ['actor_user_id', 'name'])
                    actor = authorize_action(connection, resolve_actor_user_id(self, parsed, payload), PERM_SUPPLIERS_MANAGE)
                    company_id = int(actor['company_id'])
                    now = datetime.now(UTC).isoformat()
                    name = str(payload['name']).strip()
                    cnpj = ''.join(ch for ch in str(payload.get('cnpj') or '') if ch.isdigit())
                    category = str(payload.get('category') or '').strip()
                    contact_email = str(payload.get('contact_email') or '').strip().lower()
                    notes = str(payload.get('notes') or '').strip()
                    existing = connection.execute('SELECT id FROM authorized_suppliers WHERE company_id = ? AND LOWER(TRIM(name)) = ?', (company_id, name.lower())).fetchone()
                    if existing:
                        connection.execute('UPDATE authorized_suppliers SET cnpj = ?, category = ?, contact_email = ?, notes = ?, active = 1, updated_at = ? WHERE id = ?', (cnpj, category, contact_email, notes, now, int(existing['id'])))
                        sup_id = int(existing['id'])
                    else:
                        cur = connection.execute('INSERT INTO authorized_suppliers (company_id, name, cnpj, category, contact_email, notes, active, source, created_by_user_id, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?)', (company_id, name, cnpj, category, contact_email, notes, 'manual', int(actor['id']), now, now))
                        sup_id = int(cur.lastrowid)
                    connection.commit()
                    return send_json(self, 201, {'ok': True, 'id': sup_id})

                elif parsed.path == '/api/authorized-suppliers/upload':
                    require_fields(payload, ['actor_user_id', 'rows'])
                    actor = authorize_action(connection, resolve_actor_user_id(self, parsed, payload), PERM_SUPPLIERS_MANAGE)
                    company_id = int(actor['company_id'])
                    rows = payload.get('rows') or []
                    if not rows:
                        raise ValueError('Nenhum item para importar.')
                    now = datetime.now(UTC).isoformat()
                    inserted, updated = 0, 0
                    for row in rows:
                        name = str(row.get('name') or row.get('Nome') or row.get('nome') or '').strip()
                        if not name:
                            continue
                        cnpj = ''.join(ch for ch in str(row.get('cnpj') or row.get('CNPJ') or '') if ch.isdigit())
                        category = str(row.get('category') or row.get('categoria') or row.get('Categoria') or '').strip()
                        contact_email = str(row.get('email') or row.get('Email') or '').strip().lower()
                        notes = str(row.get('notes') or row.get('obs') or row.get('Obs') or '').strip()
                        existing = connection.execute("SELECT id FROM authorized_suppliers WHERE company_id = ? AND (LOWER(TRIM(name)) = ? OR (cnpj != '' AND cnpj = ?))", (company_id, name.lower(), cnpj)).fetchone()
                        if existing:
                            connection.execute('UPDATE authorized_suppliers SET name = ?, cnpj = ?, category = ?, contact_email = ?, notes = ?, active = 1, source = ?, updated_at = ? WHERE id = ?', (name, cnpj, category, contact_email, notes, 'upload', now, int(existing['id'])))
                            updated += 1
                        else:
                            connection.execute('INSERT INTO authorized_suppliers (company_id, name, cnpj, category, contact_email, notes, active, source, created_by_user_id, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?)', (company_id, name, cnpj, category, contact_email, notes, 'upload', int(actor['id']), now, now))
                            inserted += 1
                    connection.commit()
                    return send_json(self, 200, {'ok': True, 'inserted': inserted, 'updated': updated, 'total': inserted + updated})

                supplier_toggle_match = re.match(r'^/api/authorized-suppliers/(\d+)/toggle$', parsed.path or '')
                if supplier_toggle_match:
                    supplier_id = int(supplier_toggle_match.group(1))
                    require_fields(payload, ['actor_user_id'])
                    actor = authorize_action(connection, resolve_actor_user_id(self, parsed, payload), PERM_SUPPLIERS_MANAGE)
                    company_id = int(actor['company_id'])
                    now = datetime.now(UTC).isoformat()
                    supplier = connection.execute('SELECT * FROM authorized_suppliers WHERE id = ? AND company_id = ?', (supplier_id, company_id)).fetchone()
                    if not supplier:
                        return send_json(self, 404, {'error': 'Fornecedor não encontrado.'})
                    new_active = 0 if int(supplier['active']) == 1 else 1
                    connection.execute('UPDATE authorized_suppliers SET active = ?, updated_at = ? WHERE id = ?', (new_active, now, supplier_id))
                    connection.commit()
                    action_label = 'reativado' if new_active == 1 else 'suspenso'
                    return send_json(self, 200, {'ok': True, 'active': new_active, 'message': f'Fornecedor {action_label} com sucesso.'})

                # ── Fim Fase 2 POST ───────────────────────────────────────────

                elif parsed.path == '/api/companies':
                    require_fields(payload, ['actor_user_id', 'name', 'legal_name', 'cnpj', 'plan_name', 'user_limit', 'license_status', 'active'])
                    actor = authorize_action(connection, resolve_actor_user_id(self, parsed, payload), 'companies:create')
                    payload = validate_company_payload(connection, payload, None)
                    cursor = connection.execute(
                        (
                            'INSERT INTO companies ('
                            'name, legal_name, cnpj, logo_type, plan_name, user_limit, license_status, active, '
                            'commercial_notes, contract_start, contract_end, monthly_value, addendum_enabled'
                            ') VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'
                        ),
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
                    actor = authorize_action(connection, resolve_actor_user_id(self, parsed, payload), 'units:create', int(payload['company_id']))
                    require_structural_admin(actor)
                    unit_type = normalize_unit_type(payload.get('unit_type'))
                    cursor = connection.execute(
                        'INSERT INTO units (company_id, name, unit_type, city, notes) VALUES (?, ?, ?, ?, ?)',
                        (payload['company_id'], payload['name'], unit_type, payload['city'], payload.get('notes', ''))
                    )
                    connection.commit()
                    return send_json(self, 201, {'ok': True, 'id': cursor.lastrowid})
                  
                elif parsed.path == '/api/employees':
                    def _create_employee(connection_ref, payload_ref):
                        return create_employee_service(
                            connection_ref,
                            payload_ref,
                            authorize_action=authorize_action,
                            resolve_actor_user_id=lambda: resolve_actor_user_id(self, parsed, payload_ref),
                            get_unit_by_id=get_unit_by_id,
                            ensure_resource_company=ensure_resource_company,
                            normalize_cpf=normalize_cpf,
                            ensure_employee_identity_unique=ensure_employee_identity_unique,
                            normalize_preferred_contact_channel=normalize_preferred_contact_channel,
                        )
                    return handle_create_employee_route(self, connection, payload, require_fields=require_fields, send_json=send_json, create_employee=_create_employee)

                elif parsed.path == '/api/epis':
                    def _create_epi(connection_ref, payload_ref):
                        return create_epi_service(
                            connection_ref,
                            payload_ref,
                            authorize_action=authorize_action,
                            resolve_actor_user_id=lambda: resolve_actor_user_id(self, parsed, payload_ref),
                            require_structural_admin=require_structural_admin,
                            next_company_qr_sequence=next_company_qr_sequence,
                            build_master_epi_qr=build_master_epi_qr,
                            parse_epi_joinventures=parse_epi_joinventures,
                            normalize_active_joinventure_name=normalize_active_joinventure_name,
                            resolve_epi_scope_unit=resolve_epi_scope_unit,
                            resolve_epi_scope_metadata=resolve_epi_scope_metadata,
                            validate_epi_uniqueness=validate_epi_uniqueness,
                            parse_int_flexible=parse_int_flexible,
                            upsert_unit_stock=upsert_unit_stock,
                        )
                    return handle_create_epi_route(self, connection, payload, require_fields=require_fields, send_json=send_json, create_epi=_create_epi)

                elif parsed.path == '/api/deliveries':
                    def _create_delivery(connection_ref, payload_ref):
                        return create_delivery_service(
                            connection_ref,
                            payload_ref,
                            client_ip=str(getattr(self, 'client_address', ('',))[0] or ''),
                            authorize_action=authorize_action,
                            resolve_actor_user_id=lambda: resolve_actor_user_id(self, parsed, payload_ref),
                            get_employee_by_id=get_employee_by_id,
                            get_epi_by_id=get_epi_by_id,
                            ensure_resource_company=ensure_resource_company,
                            get_employee_current_unit=get_employee_current_unit,
                            actor_operational_unit_id=actor_operational_unit_id,
                            get_unit_stock=get_unit_stock,
                            upsert_unit_stock=upsert_unit_stock,
                            ensure_ficha_for_delivery=ensure_ficha_for_delivery,
                        )
                    return handle_create_delivery_route(
                        self,
                        connection,
                        payload,
                        require_fields=require_fields,
                        send_json=send_json,
                        create_delivery=_create_delivery,
                    )

                elif parsed.path == '/api/devolutions':
                    require_fields(payload, ['actor_user_id', 'delivery_id', 'returned_date', 'condition', 'destination'])
                    if not str(payload.get('signature_data') or '').strip():
                        raise ValueError('Assinatura digital obrigatória para registrar devolução.')
                    actor = authorize_action(connection, resolve_actor_user_id(self, parsed, payload), 'deliveries:create')
                    payload = dict(payload)
                    payload['signature_ip'] = str(getattr(self, 'client_address', ('',))[0] or '')
                    devolution_id = register_epi_devolution(connection, payload, actor)
                    return send_json(self, 201, {'ok': True, 'id': devolution_id})
                    
                elif parsed.path == '/api/platform-brand':
                    require_fields(payload, ['actor_user_id'])
                    actor = require_master_actor(connection, resolve_actor_user_id(self, parsed, payload))
                    brand = save_platform_brand(connection, payload)
                    connection.commit()
                    structured_log('info', 'platform_brand.updated', actor_user_id=actor['id'])
                    return send_json(self, 200, {'ok': True, 'brand': brand})
                elif parsed.path == '/api/report-requests':
                    require_fields(payload, ['actor_user_id'])
                    actor = authorize_action(connection, resolve_actor_user_id(self, parsed, payload), PERM_STOCK_VIEW)
                    if actor.get('role') not in ('approver', 'general_admin', 'registry_admin', 'master_admin'):
                        raise PermissionError('Apenas Aprovadores e Administradores podem solicitar relatórios.')
                    company_id = int(actor['company_id'])
                    purchase_scope = get_actor_purchase_unit_scope(connection, actor)
                    unit_id = payload.get('unit_id')
                    if unit_id:
                        unit_id = int(unit_id)
                        if purchase_scope and unit_id not in purchase_scope:
                            raise PermissionError('Aprovador só pode solicitar relatório para unidades que administra.')
                    now = datetime.now(UTC).isoformat()
                    connection.execute(
                        'INSERT INTO report_requests (company_id, unit_id, requester_user_id, requester_name, '
                        'period_year, period_month, notes, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
                        (company_id, unit_id, int(actor['id']), actor['full_name'],
                         payload.get('period_year') or None, payload.get('period_month') or None,
                         str(payload.get('notes') or '').strip(), 'pending', now)
                    )
                    connection.commit()
                    return send_json(self, 201, {'ok': True})

                elif re.match(r'^/api/report-requests/(\d+)/mark-done$', parsed.path or ''):
                    rr_match = re.match(r'^/api/report-requests/(\d+)/mark-done$', parsed.path)
                    require_fields(payload, ['actor_user_id'])
                    actor = authorize_action(connection, resolve_actor_user_id(self, parsed, payload), PERM_STOCK_VIEW)
                    if actor.get('role') not in ('admin', 'general_admin', 'registry_admin', 'master_admin'):
                        raise PermissionError('Apenas Administradores podem marcar relatório como enviado.')
                    rr_id = int(rr_match.group(1))
                    now = datetime.now(UTC).isoformat()
                    connection.execute(
                        "UPDATE report_requests SET status = 'done', handled_by_user_id = ?, handled_by_name = ?, handled_at = ? WHERE id = ? AND company_id = ?",
                        (int(actor['id']), actor['full_name'], now, rr_id, int(actor['company_id']))
                    )
                    connection.commit()
                    return send_json(self, 200, {'ok': True})

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
                elif parsed.path == '/api/fichas/finalize':
                    finalize_started_at = time.perf_counter()
                    finalize_payload_period_id = int(payload.get('ficha_period_id') or 0)
                    structured_log('info', 'ficha.finalize.start', ficha_period_id=finalize_payload_period_id)
                    require_fields(payload, ['actor_user_id', 'ficha_period_id'])
                    structured_log('info', 'ficha.finalize.user_validation_done', ficha_period_id=finalize_payload_period_id, elapsed_ms=round((time.perf_counter() - finalize_started_at) * 1000, 2))
                    actor = authorize_action(connection, resolve_actor_user_id(self, parsed, payload), 'fichas:view')
                    structured_log('info', 'ficha.finalize.authorization_done', ficha_period_id=finalize_payload_period_id, actor_user_id=int(actor.get('id') or 0), elapsed_ms=round((time.perf_counter() - finalize_started_at) * 1000, 2))
                    ficha = connection.execute(
                        'SELECT id, company_id, unit_id, employee_id, status, batch_signature_name, batch_signature_data, batch_signature_at FROM epi_ficha_periods WHERE id = ?',
                        (int(payload['ficha_period_id']),)
                    ).fetchone()
                    if not ficha:
                        raise ValueError('Período de ficha não encontrado.')
                    structured_log('info', 'ficha.finalize.period_loaded', ficha_period_id=int(ficha['id']), elapsed_ms=round((time.perf_counter() - finalize_started_at) * 1000, 2))
                    ensure_resource_company(actor, ficha, 'Ficha de EPI')
                    scope_unit_id = actor_operational_unit_id(connection, actor)
                    if scope_unit_id and int(ficha['unit_id']) != int(scope_unit_id):
                        raise PermissionError('Seu perfil só pode finalizar ficha da própria unidade operacional.')
                    preview_only = bool(payload.get('preview_only'))
                    totals_data = compute_ficha_period_signature_state(connection, int(ficha['id']))
                    pending_items = int(totals_data.get('pending_items') or 0)
                    closed_period_with_batch_signature = (
                        str(ficha.get('status') or '').lower() == 'closed'
                        and str(ficha.get('batch_signature_at') or '').strip()
                        and (not preview_only)
                        and pending_items == 0
                    )
                    total_items = int(totals_data.get('total_items') or 0)
                    if total_items <= 0:
                        period = connection.execute(
                            'SELECT period_start, period_end FROM epi_ficha_periods WHERE id = ?',
                            (int(ficha['id']),),
                        ).fetchone()
                        period_data = row_to_dict(period) if period else {}
                        period_start = str(period_data.get('period_start') or '').strip()
                        period_end = str(period_data.get('period_end') or '').strip()
                        if period_start and period_end:
                            now_sync = datetime.now(UTC).isoformat()
                            connection.execute(
                                (
                                    'INSERT INTO epi_ficha_items ('
                                    'ficha_period_id, delivery_id, company_id, employee_id, unit_id, epi_id, quantity, '
                                    'item_signature_name, item_signature_data, item_signature_ip, item_signature_at, item_signature_comment, signed_mode, '
                                    'created_at, updated_at'
                                    ') '
                                    'SELECT ?, d.id, d.company_id, d.employee_id, d.unit_id, d.epi_id, COALESCE(d.quantity, 1), '
                                    "COALESCE(d.signature_name, ''), COALESCE(d.signature_data, ''), COALESCE(d.signature_ip, ''), "
                                    "COALESCE(d.signature_at, ''), COALESCE(d.signature_comment, ''), "
                                    "CASE WHEN COALESCE(d.signature_data, '') <> '' THEN 'delivery' ELSE '' END, ?, ? "
                                    'FROM deliveries d '
                                    'WHERE d.company_id = ? '
                                    'AND d.employee_id = ? '
                                    'AND date(d.delivery_date) >= date(?) '
                                    'AND date(d.delivery_date) <= date(?) '
                                    'ON CONFLICT (delivery_id) DO NOTHING'
                                ),
                                (
                                    int(ficha['id']),
                                    now_sync,
                                    now_sync,
                                    int(ficha['company_id']),
                                    int(ficha['employee_id']),
                                    period_start,
                                    period_end,
                                ),
                            )
                            totals_data = compute_ficha_period_signature_state(connection, int(ficha['id']))
                            total_items = int(totals_data.get('total_items') or 0)
                    if total_items <= 0:
                        raise ValueError('Não é possível finalizar período sem itens de entrega.')
                    employee = get_employee_by_id(connection, int(ficha['employee_id']))
                    if not employee:
                        raise ValueError('Colaborador da ficha não encontrado.')
                    ensure_actor_employee_scope(connection, actor, employee)
                    manager_email = ''
                    linked_employee_id = actor.get('linked_employee_id')
                    if linked_employee_id not in (None, '', 'null'):
                        manager_employee = get_employee_by_id(connection, int(linked_employee_id))
                        manager_email = str((manager_employee or {}).get('email') or '').strip().lower()
                    channel = normalize_preferred_contact_channel(payload.get('channel') or employee.get('preferred_contact_channel') or 'whatsapp')
                    link_data = build_portal_link_from_cpf(
                        request_base_url(self),
                        employee.get('cpf'),
                        EMPLOYEE_PORTAL_SECRET_KEY
                    )
                    token = link_data['token']
                    access_link = link_data['access_link']
                    structured_log('info', 'ficha.finalize.link_generated', ficha_period_id=int(ficha['id']), employee_id=int(employee['id']), channel=channel, elapsed_ms=round((time.perf_counter() - finalize_started_at) * 1000, 2))
                    now = datetime.now(UTC).isoformat()
                    expires_at = link_data['expires_at']
                    existing_link = connection.execute(
                        'SELECT id FROM employee_portal_links WHERE employee_id = ?',
                        (int(employee['id']),)
                    ).fetchone()
                    if existing_link:
                        connection.execute(
                            (
                                'UPDATE employee_portal_links '
                                'SET token = ?, qr_code_value = ?, active = 1, expires_at = ?, updated_at = ? '
                                'WHERE employee_id = ?'
                            ),
                            (token, access_link, expires_at, now, int(employee['id']))
                        )
                    else:
                        connection.execute(
                            (
                                'INSERT INTO employee_portal_links ('
                                'company_id, employee_id, token, qr_code_value, active, expires_at, created_by_user_id, created_at, updated_at'
                                ') VALUES (?, ?, ?, ?, 1, ?, ?, ?, ?)'
                            ),
                            (int(employee['company_id']), int(employee['id']), token, access_link, expires_at, int(actor['id']), now, now)
                        )
                    employee_name = str(employee.get('name') or 'Colaborador')
                    message = (
                        f"Olá {employee_name}! 👷\n"
                        f"Seu link da Ficha de EPI (48h):\n{access_link}\n"
                        "Assine o período, solicite EPIs e registre sua avaliação."
                    )
                    launch_url = ''
                    if channel == 'whatsapp':
                        phone = ''.join(ch for ch in str(employee.get('whatsapp') or '') if ch.isdigit())
                        if not phone:
                            raise ValueError('Colaborador sem WhatsApp cadastrado.')
                        launch_url = f"https://wa.me/{phone}?text={quote(message)}"
                    else:
                        email = str(employee.get('email') or '').strip().lower()
                        if not email:
                            raise ValueError('Colaborador sem e-mail cadastrado.')
                        subject = quote(f'Assinatura da Ficha de EPI - {employee_name}')
                        launch_url = f"mailto:{email}?subject={subject}&body={quote(message)}"
                    if preview_only:
                        connection.commit()
                        structured_log('info', 'ficha.finalize.db_saved', ficha_period_id=int(ficha['id']), status=str(ficha.get('status') or 'open'), preview_only=True, elapsed_ms=round((time.perf_counter() - finalize_started_at) * 1000, 2))
                        structured_log('info', 'ficha.finalize.response_sent', ficha_period_id=int(ficha['id']), status=str(ficha.get('status') or 'open'), elapsed_ms=round((time.perf_counter() - finalize_started_at) * 1000, 2), duration_ms=round((time.perf_counter() - finalize_started_at) * 1000, 2))
                        return send_json(self, 200, {'ok': True, 'status': str(ficha.get('status') or 'open'), 'channel': channel, 'message': message, 'launch_url': launch_url, 'access_link': access_link, 'expires_at': expires_at, 'ficha_period_id': int(ficha['id']), 'period_id': int(ficha['id']), 'employee_id': int(employee['id']), 'token': token, 'manager_email': manager_email})
                        return send_json(self, 200, {'ok': True, 'status': str(ficha.get('status') or 'open'), 'channel': channel, 'message': message, 'launch_url': launch_url, 'access_link': access_link, 'expires_at': expires_at, 'ficha_period_id': int(ficha['id']), 'manager_email': manager_email})
                    if closed_period_with_batch_signature:
                        connection.commit()
                        structured_log('info', 'ficha.finalize.db_saved', ficha_period_id=int(ficha['id']), status='closed', preview_only=False, elapsed_ms=round((time.perf_counter() - finalize_started_at) * 1000, 2))
                        structured_log('info', 'ficha.finalize.response_sent', ficha_period_id=int(ficha['id']), status='closed', elapsed_ms=round((time.perf_counter() - finalize_started_at) * 1000, 2), duration_ms=round((time.perf_counter() - finalize_started_at) * 1000, 2))
                        return send_json(self, 200, {'ok': True, 'status': 'closed', 'channel': channel, 'message': message, 'launch_url': launch_url, 'access_link': access_link, 'expires_at': expires_at, 'ficha_period_id': int(ficha['id']), 'period_id': int(ficha['id']), 'employee_id': int(employee['id']), 'token': token, 'manager_email': manager_email})
                        return send_json(self, 200, {'ok': True, 'status': 'closed', 'channel': channel, 'message': message, 'launch_url': launch_url, 'access_link': access_link, 'expires_at': expires_at, 'ficha_period_id': int(ficha['id']), 'manager_email': manager_email})
                    now = datetime.now(UTC).isoformat()
                    pending_items = int(totals_data.get('pending_items') or 0)
                    connection.execute(
                        "UPDATE epi_ficha_periods SET status = 'pending_signature', updated_at = ? WHERE id = ?",
                        (now, int(ficha['id']))
                    )
                    connection.commit()
                    structured_log('info', 'ficha.finalize.db_saved', ficha_period_id=int(ficha['id']), status='pending_signature', preview_only=False, elapsed_ms=round((time.perf_counter() - finalize_started_at) * 1000, 2))
                    actual_status = 'pending_signature'
                    structured_log('info', 'ficha.finalize.response_sent', ficha_period_id=int(ficha['id']), status=actual_status, elapsed_ms=round((time.perf_counter() - finalize_started_at) * 1000, 2), duration_ms=round((time.perf_counter() - finalize_started_at) * 1000, 2))
                    return send_json(self, 200, {'ok': True, 'status': actual_status, 'channel': channel, 'message': message, 'launch_url': launch_url, 'access_link': access_link, 'expires_at': expires_at, 'ficha_period_id': int(ficha['id']), 'period_id': int(ficha['id']), 'employee_id': int(employee['id']), 'token': token, 'manager_email': manager_email})
                    return send_json(self, 200, {'ok': True, 'status': actual_status, 'channel': channel, 'message': message, 'launch_url': launch_url, 'access_link': access_link, 'expires_at': expires_at, 'ficha_period_id': int(ficha['id']), 'manager_email': manager_email})
                elif parsed.path == '/api/fichas/repair-status':
                    require_fields(payload, ['actor_user_id'])
                    actor = authorize_action(connection, resolve_actor_user_id(self, parsed, payload), 'fichas:view')
                    rows = connection.execute(
                        "SELECT id, status FROM epi_ficha_periods WHERE status = 'closed' ORDER BY id ASC"
                    ).fetchall()
                    repaired_ids = []
                    for row in rows:
                        period = resolve_ficha_period_effective_status(connection, row_to_dict(row))
                        if str(period.get('status') or '') != 'closed':
                            repaired_ids.append(int(period['id']))
                    connection.commit()
                    structured_log('info', 'ficha.repair_status.executed', actor_user_id=int(actor['id']), repaired_count=len(repaired_ids))
                    return send_json(self, 200, {'ok': True, 'repaired_ids': repaired_ids, 'total_checked': len(rows)})
                elif parsed.path == '/api/stock/movements':
                    require_fields(payload, ['actor_user_id', 'company_id', 'unit_id', 'epi_id', 'movement_type', 'quantity', 'label_measure', 'label_printer_name', 'label_print_format', 'manufacture_date'])
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
                    resolved_size = resolve_item_size(
                        payload.get('glove_size'),
                        payload.get('size'),
                        payload.get('uniform_size'),
                    )
                    if not resolved_size['selected_size']:
                        raise ValueError('Tamanho é obrigatório para entrada em estoque. Informe Tamanho-Luvas, Tamanho ou Tamanho Uniforme.')
                    glove_size = resolved_size['glove_size']
                    size = resolved_size['size']
                    uniform_size = resolved_size['uniform_size']
                    label_measure = str(payload.get('label_measure') or '').strip().lower()
                    if not label_measure:
                        raise ValueError('Medida da etiqueta é obrigatória.')
                    label_printer_name = str(payload.get('label_printer_name') or '').strip()
                    if not label_printer_name:
                        raise ValueError('Impressora da etiqueta é obrigatória.')
                    label_print_format = str(payload.get('label_print_format') or '').strip()
                    if not label_print_format:
                        raise ValueError('Formato de impressão da etiqueta é obrigatório.')
                    lot_code = str(payload.get('lot_code') or '').strip()
                    manufacture_date = str(payload.get('manufacture_date') or '').strip()
                    if not manufacture_date:
                        raise ValueError('Data de fabricação é obrigatória para entrada de estoque.')
                    stock_row = get_unit_stock(connection, int(payload['company_id']), int(payload['unit_id']), int(payload['epi_id']))
                    previous_stock = int((stock_row or {}).get('quantity') or 0)
                    delta = quantity if movement_type == 'in' else -quantity
                    new_stock = previous_stock + delta
                    if new_stock < 0:
                        raise ValueError('Saída deixa estoque negativo.')
                    ensure_stock_movement_size_columns(connection)
                    movement_cursor = connection.execute(
                        (
                            'INSERT INTO stock_movements ('
                            'company_id, unit_id, epi_id, movement_type, quantity, previous_stock, new_stock, '
                            'source_type, source_id, notes, actor_user_id, actor_name, created_at, glove_size, size, uniform_size'
                            ') VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'
                        ),
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
                            datetime.now(UTC).isoformat(),
                            glove_size,
                            size,
                            uniform_size
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
                                (
                                    'INSERT INTO epi_stock_items ('
                                    'company_id, unit_id, epi_id, glove_size, size, uniform_size, qr_sequence, qr_code_value, status, '
                                    'stock_movement_id, lot_code, manufacture_date, label_measure, label_printer_name, label_print_format, generated_by_user_id, created_at, updated_at'
                                    ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'in_stock', ?, ?, ?, ?, ?, ?, ?, ?, ?)"
                                ),
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
                                    lot_code,
                                    manufacture_date,
                                    label_measure,
                                    label_printer_name,
                                    label_print_format,
                                    int(actor['id']),
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
                                'stock_item_id': stock_item_cursor.lastrowid,
                                'manufacture_date': manufacture_date,
                                'unit_name': unit['name'],
                                'label_measure': label_measure,
                                'label_printer_name': label_printer_name,
                                'label_print_format': label_print_format,
                                'reprint_count': 0
                            })
                            
                    connection.commit()
                    return send_json(self, 201, {'ok': True, 'movement_id': movement_cursor.lastrowid, 'new_stock': new_stock, 'qr_labels': qr_labels})
                elif parsed.path == '/api/stock/manufacture-date-ocr':
                    require_fields(payload, ['actor_user_id', 'image_data'])
                    actor = authorize_action(connection, resolve_actor_user_id(self, parsed, payload), 'stock:adjust')
                    image_data = str(payload.get('image_data') or '').strip()
                    runtime = get_ocr_runtime_status()
                    if not runtime.get('ready'):
                        status_code = 503 if runtime.get('ocr_required') else 200
                        error_event_level = 'error' if runtime.get('ocr_required') else 'warning'
                        user_message = (
                            'OCR não disponível neste ambiente (somente em produção).'
                            if not runtime.get('ocr_required')
                            else str(runtime.get('error') or 'OCR indisponível no servidor.')
                        )
                        structured_log(
                            error_event_level,
                            'stock.manufacture_date_ocr.runtime_unavailable',
                            actor_user_id=int(actor['id']),
                            detail=runtime.get('error'),
                            message=user_message,
                            tesseract_cmd=runtime.get('tesseract_cmd'),
                        )
                        return send_json(
                            self,
                            status_code,
                            {'error': user_message, 'runtime': runtime, 'manufacture_date': '', 'confidence': 0.0},
                        )
                    result = detect_manufacture_date(image_data)
                    structured_log(
                        'info',
                        'stock.manufacture_date_ocr',
                        actor_user_id=int(actor['id']),
                        has_date=bool(result.get('manufacture_date')),
                        confidence=result.get('confidence'),
                        candidates=len(result.get('candidates') or []),
                    )
                    return send_json(self, 200, result)

                elif parsed.path == '/api/stock/labels/reprint':
                    require_fields(payload, ['actor_user_id', 'company_id', 'stock_item_id', 'reason_code'])
                    actor = authorize_action(connection, resolve_actor_user_id(self, parsed, payload), 'stock:adjust', int(payload['company_id']))
                    reason_code = str(payload.get('reason_code') or '').strip().lower()
                    if reason_code not in {'perdeu', 'rasgou'}:
                        raise ValueError('Justificativa inválida. Opções: Perdeu ou Rasgou.')
                    reason_note = str(payload.get('reason_note') or '').strip()
                    stock_item = connection.execute(
                        (
                            'SELECT esi.id, esi.company_id, esi.unit_id, esi.epi_id, esi.qr_code_value, esi.status, esi.glove_size, esi.size, '
                            'esi.uniform_size, esi.label_measure, esi.label_printer_name, esi.label_print_format, esi.reprint_count, '
                            'units.name AS unit_name, epis.name AS epi_name '
                            'FROM epi_stock_items esi '
                            'JOIN units ON units.id = esi.unit_id '
                            'JOIN epis ON epis.id = esi.epi_id '
                            'WHERE esi.id = ?'
                        ),
                        (int(payload['stock_item_id']),)
                    ).fetchone()
                    if not stock_item:
                        raise ValueError('Etiqueta não encontrada para reimpressão.')
                    ensure_resource_company(actor, stock_item, 'Etiqueta')
                    now = datetime.now(UTC).isoformat()
                    connection.execute(
                        (
                            'INSERT INTO epi_stock_item_reprints (stock_item_id, company_id, reason_code, reason_note, actor_user_id, actor_name, created_at) '
                            'VALUES (?, ?, ?, ?, ?, ?, ?)'
                        ),
                        (
                            int(stock_item['id']),
                            int(stock_item['company_id']),
                            reason_code,
                            reason_note,
                            int(actor['id']),
                            str(actor.get('full_name') or ''),
                            now
                        )
                    )
                    connection.execute(
                        'UPDATE epi_stock_items SET reprint_count = COALESCE(reprint_count, 0) + 1, updated_at = ? WHERE id = ?',
                        (now, int(stock_item['id']))
                    )
                    updated = connection.execute('SELECT reprint_count FROM epi_stock_items WHERE id = ?', (int(stock_item['id']),)).fetchone()
                    connection.commit()
                    label_payload = row_to_dict(stock_item)
                    label_payload['stock_item_id'] = int(stock_item['id'])
                    label_payload['reprint_count'] = int(updated['reprint_count']) if updated else 0
                    return send_json(self, 200, {'ok': True, 'label': label_payload})
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
                elif parsed.path == '/api/commercial-contract/save':
                    require_fields(payload, ['actor_user_id', 'company_id'])
                    actor = authorize_action(connection, resolve_actor_user_id(self, parsed, payload), PERM_COMMERCIAL_VIEW)
                    contract = save_commercial_contract(connection, actor, payload)
                    connection.commit()
                    return send_json(self, 200, {'ok': True, 'contract': contract})
                elif parsed.path == '/api/commercial-contract/generate':
                    require_fields(payload, ['actor_user_id', 'company_id'])
                    actor = authorize_action(connection, resolve_actor_user_id(self, parsed, payload), PERM_COMMERCIAL_VIEW)
                    save_commercial_contract(connection, actor, payload)
                    contract = generate_commercial_contract_pdf(connection, actor, int(payload.get('company_id')))
                    connection.commit()
                    return send_json(self, 200, {'ok': True, 'contract': contract})
                elif parsed.path == '/api/commercial-contract/sign':
                    require_fields(payload, ['actor_user_id', 'company_id', 'signature_name', 'signature_data'])
                    actor = authorize_action(connection, resolve_actor_user_id(self, parsed, payload), PERM_COMMERCIAL_VIEW)
                    contract = sign_commercial_contract(connection, actor, payload)
                    connection.commit()
                    return send_json(self, 200, {'ok': True, 'contract': contract})
                elif parsed.path == '/api/commercial-contract/upload-signed':
                    require_fields(payload, ['actor_user_id', 'company_id', 'file_name', 'file_base64'])
                    actor = authorize_action(connection, resolve_actor_user_id(self, parsed, payload), PERM_COMMERCIAL_VIEW)
                    contract = upload_signed_contract_file(connection, actor, payload)
                    connection.commit()
                    return send_json(self, 200, {'ok': True, 'contract': contract})
                elif parsed.path == '/api/commercial-contract/send-email':
                    require_fields(payload, ['actor_user_id', 'company_id', 'email_to'])
                    actor = authorize_action(connection, resolve_actor_user_id(self, parsed, payload), PERM_COMMERCIAL_VIEW)
                    contract = send_commercial_contract_email(connection, actor, payload)
                    connection.commit()
                    return send_json(self, 200, {'ok': True, 'contract': contract})
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

                elif parsed.path == '/api/change-password':
                    require_fields(payload, ['actor_user_id', 'current_password', 'new_password'])
                    actor_user_id = resolve_actor_user_id(self, parsed, payload)
                    user = get_user_by_id(connection, actor_user_id)
                    if not user:
                        raise ValueError(MSG_USER_NOT_FOUND)
                    current_password = str(payload.get('current_password', '')).strip()
                    new_password_raw = str(payload.get('new_password', '')).strip()
                    if not verify_password(user['password'], current_password):
                        raise PermissionError('Senha atual incorreta.')
                    new_hashed = hash_password(validate_password_strength(new_password_raw))
                    connection.execute('UPDATE users SET password = ? WHERE id = ?', (new_hashed, int(actor_user_id)))
                    connection.commit()
                    structured_log('info', 'auth.password_changed', user_id=actor_user_id)
                    return send_json(self, 200, {'ok': True})

                elif parsed.path == '/api/login':
                    structured_log('info', 'auth.login.entry', path=parsed.path, raw_path=self.path)
                    _bootstrap_state = _get_bootstrap_state()
                    structured_log(
                        'info',
                        'auth.login.bootstrap_state',
                        ready=bool(_bootstrap_state.get('ready')),
                        error_code=str(_bootstrap_state.get('error_code') or ''),
                        error_kind=str(_bootstrap_state.get('error_kind') or ''),
                        error_message=str(_bootstrap_state.get('error_message') or ''),
                    )
                    _login_response = {'status': None, 'code': ''}

                    def _login_send_json(handler, status, response_payload):
                        _login_response['status'] = int(status)
                        parsed_payload = response_payload if isinstance(response_payload, dict) else {}
                        if isinstance(parsed_payload.get('error'), dict):
                            _login_response['code'] = str(parsed_payload.get('error', {}).get('code') or '')
                        else:
                            _login_response['code'] = str(parsed_payload.get('code') or '')
                        structured_log(
                            'info',
                            'auth.login.response',
                            status=_login_response['status'],
                            code=_login_response['code'],
                        )
                        return send_json(handler, status, response_payload)

                    try:
                        return handle_login_route(self, connection, payload, authenticate_login, require_fields, _login_send_json)
                    except Exception as exc:
                        structured_log(
                            'error',
                            'auth.login.exception',
                            error_type=type(exc).__name__,
                            error=str(exc),
                            path=parsed.path,
                            stacktrace=traceback.format_exc(),
                        )
                        structured_log(
                            'info',
                            'auth.login.response',
                            status=500,
                            code='AUTH_LOGIN_RUNTIME_ERROR',
                        )
                        return send_json(
                            self,
                            500,
                            {
                                'ok': False,
                                'error': {
                                    'code': 'AUTH_LOGIN_RUNTIME_ERROR',
                                    'message': 'Falha interna ao processar login.',
                                    'details': {'error_type': type(exc).__name__},
                                },
                            },
                        )

                elif parsed.path == '/api/unit-jv/start':
                    actor = authorize_action(connection, resolve_actor_user_id(self, parsed), 'units:edit')
                    unit_id = int(payload.get('unit_id') or 0)
                    jv_name = str(payload.get('joint_venture_name') or '').strip()
                    if not unit_id or not jv_name:
                        raise ValueError('unit_id e joint_venture_name são obrigatórios.')
                    unit = get_unit_by_id(connection, unit_id)
                    ensure_resource_company(actor, unit, 'Unidade')
                    existing = get_unit_active_jv_name(connection, unit_id)
                    if existing:
                        raise ValueError(f'Unidade já está em JV ativa: "{existing}". Encerre antes de iniciar outra.')
                    connection.execute(
                        'INSERT INTO unit_joint_venture_periods (company_id, unit_id, joint_venture_name, started_at, created_by) '
                        'VALUES (?, ?, ?, ?, ?)',
                        (int(unit['company_id']), unit_id, jv_name, datetime.now(timezone.utc).isoformat(), str(actor.get('id') or ''))
                    )
                    connection.commit()
                    return send_json(self, 201, {'unit_id': unit_id, 'active_jv_name': jv_name, 'started': True})

                elif parsed.path == '/api/unit-jv/end':
                    actor = authorize_action(connection, resolve_actor_user_id(self, parsed), 'units:edit')
                    unit_id = int(payload.get('unit_id') or 0)
                    if not unit_id:
                        raise ValueError('unit_id é obrigatório.')
                    unit = get_unit_by_id(connection, unit_id)
                    ensure_resource_company(actor, unit, 'Unidade')
                    existing = get_unit_active_jv_name(connection, unit_id)
                    if not existing:
                        raise ValueError('Unidade não possui JV ativa para encerrar.')
                    connection.execute(
                        'UPDATE unit_joint_venture_periods SET ended_at = ? '
                        'WHERE unit_id = ? AND ended_at IS NULL',
                        (datetime.now(timezone.utc).isoformat(), unit_id)
                    )
                    connection.commit()
                    return send_json(self, 200, {'unit_id': unit_id, 'ended_jv_name': existing, 'ended': True})
                 

                elif parsed.path == '/api/ficha-config':
                    require_fields(payload, ['actor_user_id'])
                    actor = authorize_action(connection, resolve_actor_user_id(self, parsed, payload), PERM_SETTINGS_UPDATE)
                    save_ficha_config(connection, actor['company_id'], payload)
                    return send_json(self, 200, {'ok': True})

                elif parsed.path == '/api/ficha-retention-policy':
                    require_fields(payload, ['actor_user_id'])
                    actor = authorize_action(connection, resolve_actor_user_id(self, parsed, payload), PERM_SETTINGS_UPDATE)
                    require_configuration_admin(actor)
                    policy = save_ficha_retention_policy(connection, actor.get('company_id'), payload)
                    return send_json(self, 200, policy)

                elif parsed.path == '/api/ficha-archive/purge-expired':
                    require_fields(payload, ['actor_user_id'])
                    actor = authorize_action(connection, resolve_actor_user_id(self, parsed, payload), PERM_SETTINGS_UPDATE)
                    require_configuration_admin(actor)
                    policy = get_ficha_retention_policy(connection, actor.get('company_id'))
                    apply_snapshot_retention(
                        connection,
                        actor.get('company_id') if actor.get('role') != 'master_admin' else None,
                        policy,
                    )
                    return send_json(self, 200, {'ok': True, 'policy': policy})

                elif parsed.path == '/api/configuration-rules':
                    require_fields(payload, ['actor_user_id'])
                    actor = authorize_action(connection, resolve_actor_user_id(self, parsed, payload), PERM_SETTINGS_UPDATE)
                    require_configuration_admin(actor)
                    rules = save_configuration_rules(connection, actor['company_id'], payload.get('rules') or [])
                    return send_json(self, 200, {'ok': True, 'rules': rules})

                elif parsed.path == '/api/configuration-framework':
                    require_fields(payload, ['actor_user_id'])
                    actor = authorize_action(connection, resolve_actor_user_id(self, parsed, payload), PERM_SETTINGS_UPDATE)
                    require_master_admin(actor, 'Somente Administrador Master pode salvar o framework de hardening.')
                    framework = save_configuration_framework(connection, actor['company_id'], payload.get('framework') or {})
                    return send_json(self, 200, {'ok': True, 'framework': framework})

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
        if parsed.path.startswith('/api/') and not self._require_bootstrap_ready(parsed.path):
            return

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
                    def _update_user(connection_ref, user_id_ref, payload_ref):
                        return update_user_service(
                            connection_ref,
                            user_id_ref,
                            payload_ref,
                            resolve_actor_user_id=lambda: resolve_actor_user_id(self, parsed, payload_ref),
                            authorize_user_management=authorize_user_management,
                            get_user_by_id=get_user_by_id,
                            hash_password=hash_password,
                            is_bcrypt_hash=is_bcrypt_hash,
                            normalize_role_name=normalize_role_name,
                            role_weight=ROLE_WEIGHT,
                            resolve_target_company_id=resolve_target_company_id,
                            resolve_user_employee_link=resolve_user_employee_link,
                            ensure_operational_role_link=ensure_operational_role_link,
                            ensure_company_user_limit=ensure_company_user_limit,
                            build_employee_access_token=build_employee_access_token,
                            sql_update_user=SQL_UPDATE_USER,
                        )
                    return handle_update_user_route(self, connection, parsed, payload, require_fields=require_fields, send_json=send_json, update_user=_update_user)

                if parsed.path.startswith('/api/units/'):
                    unit_id = int(parsed.path.rsplit('/', 1)[-1].split('?')[0])
                    require_fields(payload, ['actor_user_id', 'company_id', 'name', 'unit_type', 'city'])
                    actor = authorize_action(connection, resolve_actor_user_id(self, parsed, payload), 'units:update', int(payload['company_id']))
                    require_structural_admin(actor)
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
                    def _update_employee(connection_ref, employee_id_ref, payload_ref):
                        return update_employee_service(
                            connection_ref,
                            employee_id_ref,
                            payload_ref,
                            authorize_action=authorize_action,
                            resolve_actor_user_id=lambda: resolve_actor_user_id(self, parsed, payload_ref),
                            get_employee_by_id=get_employee_by_id,
                            get_unit_by_id=get_unit_by_id,
                            ensure_resource_company=ensure_resource_company,
                            normalize_cpf=normalize_cpf,
                            ensure_employee_identity_unique=ensure_employee_identity_unique,
                            normalize_preferred_contact_channel=normalize_preferred_contact_channel,
                            sql_update_employee=SQL_UPDATE_EMPLOYEE,
                        )
                    return handle_update_employee_route(self, connection, parsed, payload, require_fields=require_fields, send_json=send_json, update_employee=_update_employee)

                if parsed.path.startswith('/api/epis/'):
                    def _update_epi(connection_ref, epi_id_ref, payload_ref):
                        return update_epi_service(
                            connection_ref,
                            epi_id_ref,
                            payload_ref,
                            authorize_action=authorize_action,
                            resolve_actor_user_id=lambda: resolve_actor_user_id(self, parsed, payload_ref),
                            require_structural_admin=require_structural_admin,
                            get_epi_by_id=get_epi_by_id,
                            ensure_resource_company=ensure_resource_company,
                            generate_epi_qr_code=generate_epi_qr_code,
                            parse_epi_joinventures=parse_epi_joinventures,
                            normalize_active_joinventure_name=normalize_active_joinventure_name,
                            resolve_epi_scope_unit=resolve_epi_scope_unit,
                            resolve_epi_scope_metadata=resolve_epi_scope_metadata,
                            validate_epi_uniqueness=validate_epi_uniqueness,
                            parse_int_flexible=parse_int_flexible,
                            sync_epi_scope_stock_unit=sync_epi_scope_stock_unit,
                        )
                    return handle_update_epi_route(self, connection, parsed, payload, require_fields=require_fields, send_json=send_json, update_epi=_update_epi)

                supplier_edit_match = re.match(r'^/api/authorized-suppliers/(\d+)$', parsed.path or '')
                if supplier_edit_match:
                    supplier_id = int(supplier_edit_match.group(1))
                    require_fields(payload, ['actor_user_id', 'name'])
                    actor = authorize_action(connection, resolve_actor_user_id(self, parsed, payload), PERM_SUPPLIERS_MANAGE)
                    company_id = int(actor['company_id'])
                    now = datetime.now(UTC).isoformat()
                    name = str(payload['name']).strip()
                    cnpj = ''.join(ch for ch in str(payload.get('cnpj') or '') if ch.isdigit())
                    category = str(payload.get('category') or '').strip()
                    contact_email = str(payload.get('contact_email') or '').strip().lower()
                    notes = str(payload.get('notes') or '').strip()
                    existing = connection.execute('SELECT id FROM authorized_suppliers WHERE id = ? AND company_id = ?', (supplier_id, company_id)).fetchone()
                    if not existing:
                        return send_json(self, 404, {'error': 'Fornecedor não encontrado.'})
                    connection.execute(
                        'UPDATE authorized_suppliers SET name = ?, cnpj = ?, category = ?, contact_email = ?, notes = ?, updated_at = ? WHERE id = ?',
                        (name, cnpj, category, contact_email, notes, now, supplier_id)
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
        if parsed.path.startswith('/api/') and not self._require_bootstrap_ready(parsed.path):
            return
        try:
            with closing(get_connection()) as connection:
                if parsed.path.startswith('/api/users/'):
                    def _delete_user(connection_ref, user_id_ref):
                        return delete_user_service(
                            connection_ref,
                            user_id_ref,
                            resolve_actor_user_id=lambda: resolve_actor_user_id(self, parsed),
                            authorize_user_management=authorize_user_management,
                        )
                    return handle_delete_user_route(self, connection, parsed, send_json=send_json, delete_user=_delete_user)
                if parsed.path.startswith('/api/units/'):
                    unit_id = int(parsed.path.rsplit('/', 1)[-1].split('?')[0])
                    actor = authorize_action(connection, resolve_actor_user_id(self, parsed), 'units:delete')
                    require_structural_admin(actor)
                    unit = get_unit_by_id(connection, unit_id)
                    if not unit:
                        raise ValueError('Unidade não encontrada.')
                    ensure_resource_company(actor, unit, 'Unidade')
                    delete_unit_dependencies(connection, unit_id)
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
                    require_structural_admin(actor)
                    epi = get_epi_by_id(connection, epi_id)
                    if not epi:
                        raise ValueError('EPI não encontrado.')
                    ensure_resource_company(actor, epi, 'EPI')
                    delete_epi_dependencies(connection, epi_id)
                    connection.commit()
                    return send_json(self, 200, {'ok': True})
                purchase_function_match = re.match(r'^/api/purchase-functions/(\d+)$', parsed.path or '')
                if purchase_function_match:
                    link_id = int(purchase_function_match.group(1))
                    actor = authorize_action(connection, resolve_actor_user_id(self, parsed), PERM_UNIT_LINKS_MANAGE)
                    require_purchase_function_admin(actor)
                    company_id = int(actor['company_id'])
                    link = connection.execute('SELECT * FROM purchase_role_unit_links WHERE id = ?', (link_id,)).fetchone()
                    if not link:
                        raise ValueError('Vínculo de compras não encontrado.')
                    if int(link['company_id']) != company_id:
                        raise PermissionError('Vínculo pertence a outra empresa.')
                    connection.execute('DELETE FROM purchase_role_unit_links WHERE id = ?', (link_id,))
                    connection.commit()
                    return send_json(self, 200, {'ok': True})

                user_unit_link_match = re.match(r'^/api/user-unit-links/(\d+)$', parsed.path or '')
                if user_unit_link_match:
                    link_id = int(user_unit_link_match.group(1))
                    actor = authorize_action(connection, resolve_actor_user_id(self, parsed), PERM_UNIT_LINKS_MANAGE)
                    company_id = int(actor['company_id'])
                    link = connection.execute('SELECT * FROM user_unit_links WHERE id = ?', (link_id,)).fetchone()
                    if not link:
                        raise ValueError('Vínculo não encontrado.')
                    if int(link['company_id']) != company_id:
                        raise PermissionError('Vínculo pertence a outra empresa.')
                    connection.execute('DELETE FROM user_unit_links WHERE id = ?', (link_id,))
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
    import threading as _threading

    port = int(os.environ.get('EPI_PORT', os.environ.get('PORT', '8000')))

    # ── Servidor HTTP sobe PRIMEIRO ──────────────────────────────────────
    # O Render precisa detectar a porta em < 60s.
    # Criamos o servidor antes do init_db() para garantir isso.
    try:
        server = ThreadingHTTPServer(('0.0.0.0', port), EpiHandler)
    except Exception as exc:
        structured_log('error', 'server.bind_failed', port=port, error=str(exc))
        raise

    structured_log('info', 'server.binding', port=port)
    structured_log(
        'info',
        'auth.config',
        bcrypt_available=BCRYPT_AVAILABLE,
        jwt_exp_seconds=JWT_EXP_SECONDS,
        jwt_secret_default=JWT_SECRET == 'change-this-jwt-secret',
        password_recovery_key_configured=bool(PASSWORD_RECOVERY_KEY)
    )

    # ── init_db() em background — nao bloqueia o startup ────────────────
    structured_log('info', 'application.starting', phase='bootstrap_pending')
    structured_log(
        'info',
        'application.version',
        commit=str(os.getenv('RENDER_GIT_COMMIT') or os.getenv('GIT_COMMIT') or 'unknown'),
    )

    def _run_init_db():
        started_at = datetime.now(UTC).isoformat()
        _set_bootstrap_state(
            started_at=started_at,
            completed_at='',
            ready=False,
            error_code='',
            error_kind='',
            error_message='',
        )
        try:
            structured_log('info', 'application.bootstrap_running', started_at=started_at)
            structured_log('info', 'db.init_start')
            bootstrap_admin = init_db()
            if bootstrap_admin:
                structured_log(
                    'info',
                    'bootstrap.completed',
                    user_id=bootstrap_admin.get('id'),
                    username=bootstrap_admin.get('username')
                )
            _set_bootstrap_state(
                completed_at=datetime.now(UTC).isoformat(),
                ready=True,
                error_code='',
                error_kind='',
                error_message='',
            )
            structured_log('info', 'application.ready', phase='ready')
            structured_log('info', 'db.init_done')
        except SchemaMigrationError as exc:
            _set_bootstrap_state(
                completed_at=datetime.now(UTC).isoformat(),
                ready=False,
                error_code=_operational_error_code(exc.kind),
                error_kind=str(exc.kind),
                error_message=str(exc),
            )
            structured_log('error', 'db.init_failed_schema', error=str(exc), kind=exc.kind, context=exc.context)
            structured_log('error', 'application.bootstrap_failed', failure_type='schema', error_kind=exc.kind)
            # Nao encerra o processo: o servidor continua no ar para servir /api/login
            # (isento do bootstrap gate) e endpoints de health. Evita loop infinito de
            # reinicializacoes no Render quando a falha e persistente (ex: bug de migracao).
        except Exception as exc:
            kind = _classify_db_error(exc)
            _set_bootstrap_state(
                completed_at=datetime.now(UTC).isoformat(),
                ready=False,
                error_code=_operational_error_code(kind),
                error_kind=kind,
                error_message=str(exc),
            )
            structured_log('error', 'db.init_failed_gracefully', error=str(exc))
            structured_log('error', 'application.bootstrap_failed', failure_type='unexpected', error_kind=kind)
            # Idem: mantém o servidor rodando para permitir diagnóstico via login.

    _init_thread = _threading.Thread(target=_run_init_db, daemon=True, name='init_db')
    _init_thread.start()

    # ── Porta ja esta aberta — Render detecta aqui ───────────────────────
    structured_log('info', 'server.started', port=port)
    try:
        server.serve_forever()
    except Exception as exc:
        structured_log('error', 'server.startup_failed', error=str(exc))
        raise
