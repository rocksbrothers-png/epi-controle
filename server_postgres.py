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
from core.schema import (
    SchemaMigrationError,
    _classify_db_error,
    _col_exists,
    _ensure_ficha_periods_sequence_unique,
    _get_migration_runtime_state,
    _is_sqlite_connection,
    _safe_add_column,
    _set_migration_runtime_state,
    _table_columns,
    _table_exists,
    ensure_company_audit_columns,
    ensure_company_columns,
    ensure_delivery_signature_columns,
    ensure_devolution_columns,
    ensure_employee_columns,
    ensure_epi_columns,
    ensure_epi_operational_tables,
    ensure_stock_columns,
    ensure_stock_movement_size_columns,
    ensure_user_columns,
    run_pending_migrations,
    run_schema_precheck,
    validate_schema_health,
    MIGRATION_RUNTIME_STATE,
    MIGRATION_RUNTIME_STATE_LOCK,
)
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
from modules.auth.routes import register_routes as _reg_auth
from modules.auth.service import authenticate_login as authenticate_login_service
from modules.employees.service import (
    normalize_cpf,
    normalize_preferred_contact_channel,
    ensure_employee_identity_unique,
)
from modules.deliveries.service import create_delivery_service
from modules.units.routes import register_routes as _reg_units
from modules.units.service import normalize_unit_type, delete_epi_dependencies, delete_unit_dependencies
from modules.users.routes import register_routes as _reg_users
from modules.users.service import (
    authorize_user_management,
    resolve_target_company_id,
    ensure_operational_role_link,
    build_employee_access_token,
    resolve_user_employee_link,
    create_user as create_user_service,
    delete_user as delete_user_service,
    update_user as update_user_service,
)
from core.permissions import (
    ADMIN_BASE_PERMISSIONS,
    COMMERCIAL_PERMISSIONS,
    COMPANY_CORE_PERMISSIONS,
    COMPANY_MANAGEMENT_PERMISSIONS,
    DELIVERY_WRITE_PERMISSIONS,
    EPI_FEEDBACK_ADMIN_PERMISSIONS,
    EPI_FEEDBACK_MANAGER_PERMISSIONS,
    PERMISSIONS,
    PERM_ALERTS_VIEW,
    PERM_COMMERCIAL_VIEW,
    PERM_COMPANIES_CREATE,
    PERM_COMPANIES_LICENSE,
    PERM_COMPANIES_UPDATE,
    PERM_COMPANIES_VIEW,
    PERM_DASHBOARD_VIEW,
    PERM_DELIVERIES_CREATE,
    PERM_DELIVERIES_VIEW,
    PERM_EMPLOYEES_CREATE,
    PERM_EMPLOYEES_DELETE,
    PERM_EMPLOYEES_UPDATE,
    PERM_EMPLOYEES_VIEW,
    PERM_EPI_EVALUATION_DECIDE,
    PERM_EPI_EVALUATION_VIEW,
    PERM_EPI_FEEDBACK_ADMIN_APPROVE,
    PERM_EPI_FEEDBACK_CLOSE,
    PERM_EPI_FEEDBACK_CREATE,
    PERM_EPI_FEEDBACK_HSEQ_REVIEW,
    PERM_EPI_FEEDBACK_MANAGER_EVAL,
    PERM_EPI_FEEDBACK_TRIAGE,
    PERM_EPI_FEEDBACK_VIEW,
    PERM_EPI_SIGN,
    PERM_EPI_SUGGESTION_ACCEPT,
    PERM_EPI_VIEW_SELF,
    PERM_EPIS_CREATE,
    PERM_EPIS_DELETE,
    PERM_EPIS_UPDATE,
    PERM_EPIS_VIEW,
    PERM_FICHAS_VIEW,
    PERM_FINANCE_VIEW,
    PERM_PO_APPROVE,
    PERM_PO_CREATE,
    PERM_PO_RECEIVE,
    PERM_PO_REVIEW,
    PERM_PO_UPLOAD,
    PERM_PO_VIEW,
    PERM_PURCHASE_REQUESTS_CREATE,
    PERM_PURCHASE_REQUESTS_UPDATE,
    PERM_PURCHASE_REQUESTS_VIEW,
    PERM_REPORTS_VIEW,
    PERM_SETTINGS_UPDATE,
    PERM_SETTINGS_VIEW,
    PERM_STOCK_ADJUST,
    PERM_STOCK_VIEW,
    PERM_SUPPLIERS_MANAGE,
    PERM_UNIT_LINKS_MANAGE,
    PERM_UNITS_CREATE,
    PERM_UNITS_DELETE,
    PERM_UNITS_UPDATE,
    PERM_UNITS_VIEW,
    PERM_USAGE_VIEW,
    PERM_USERS_CREATE,
    PERM_USERS_DELETE,
    PERM_USERS_UPDATE,
    PERM_USERS_VIEW,
    PURCHASE_ADMIN_PERMISSIONS,
    PURCHASE_APPROVER_PERMISSIONS,
    PURCHASE_BUYER_PERMISSIONS,
    PURCHASE_VIEW_PERMISSIONS,
    STOCK_MANAGEMENT_PERMISSIONS,
)
from core.roles import BILLABLE_ROLES, ROLE_ALIASES, ROLE_WEIGHT, normalize_role_name
from core.meta import get_meta, set_meta
from modules.settings.service import (
    DEFAULT_FICHA_DECLARACAO,
    DEFAULT_FICHA_OBSERVACOES,
    DEFAULT_FICHA_RASTREABILIDADE,
    DEFAULT_FICHA_TITULO,
    _configuration_scope_key,
    _configuration_scope_unit_ids,
    default_ficha_retention_policy,
    get_configuration_framework,
    get_configuration_rules,
    get_ficha_config,
    get_ficha_retention_policy,
    save_configuration_framework,
    save_configuration_rules,
    save_ficha_config,
    save_ficha_retention_policy,
)
from modules.devolutions.service import (
    DEVOLUTION_CONDITION_LABELS,
    DEVOLUTION_DESTINATION_LABELS,
    STOCK_ITEM_STATUS_BY_DESTINATION,
    fetch_devolutions,
    fetch_open_deliveries_for_devolution,
)
from modules.reports.service import (
    InvalidQueryParamError,
    normalize_report_filters,
)
from modules.alerts.service import compute_alerts as _compute_alerts_impl
from core.auth import (
    ensure_company_access,
    ensure_permission,
    ensure_resource_company,
    require_configuration_admin,
    require_master_admin,
    require_structural_admin,
)
from modules.feedback.service import (
    EPI_FEEDBACK_ADMIN_ACTIONS_AVALIACAO,
    EPI_FEEDBACK_ADMIN_ACTIONS_SUGGESTION,
    EPI_FEEDBACK_PRIORITIES,
    EPI_FEEDBACK_STATUSES,
    EPI_FEEDBACK_TYPES,
    EPI_RANK_LABELS,
    EMPLOYEE_PORTAL_STATUS_LABELS,
    REJECTION_REASON_LABELS,
    RISK_LEVEL_LABELS,
    _record_feedback_history,
    apply_accept_suggestion_as_epi,
    apply_admin_pre_evaluate,
    apply_admin_technical_evaluate,
    apply_feedback_admin_decision,
    apply_feedback_close,
    apply_feedback_forward_admin,
    apply_feedback_hseq_review,
    apply_feedback_manager_reject,
    apply_feedback_manager_validate,
    apply_feedback_triage,
    apply_set_reassessment,
    compute_epi_evaluation_status,
    fetch_avaliacoes_ranking,
    fetch_avaliacoes_summary,
    fetch_feedback_detail,
    fetch_feedbacks,
    fetch_feedbacks_for_manager,
    fetch_suggestion_ranking,
)
from modules.purchases.service import (
    PURCHASE_FUNCTION_LABELS,
    PURCHASE_FUNCTION_TYPES,
    _format_purchase_item_decision_comment,
    _purchase_request_items_signature,
    _record_purchase_event,
    actor_company_id_or_query,
    apply_purchase_request_item_approval,
    apply_purchase_request_workflow_action,
    approved_purchase_request_items_for_po,
    ensure_purchase_request_action_scope,
    ensure_purchase_workflow_permission,
    fetch_purchase_demands,
    fetch_purchase_function_links,
    find_recent_duplicate_purchase_request,
    get_actor_purchase_unit_scope,
    normalize_purchase_function_type,
    require_purchase_function_admin,
)
from core.pdf import (
    build_pdf_document,
    extract_pdf_logo_image,
    pdf_safe_text,
)
from modules.ficha.service import (
    ensure_ficha_for_delivery,
    ensure_ficha_for_devolution,
    render_ficha_epi_html_document,
    build_ficha_epi_html as _build_ficha_epi_html_impl,
    build_ficha_epi_html_by_period as _build_ficha_epi_html_by_period_impl,
)
from modules.portal.service import (
    EmployeePortalAccessDenied,
    MSG_TOKEN_ABSENT,
    MSG_TOKEN_EXPIRED_ACCESS,
    build_employee_ficha_pdf,
    get_employee_portal_context_by_token,
    hash_portal_token,
    parse_int_flexible,
    register_employee_portal_audit,
    resolve_external_employee_context,
    validate_portal_cpf_with_attempts,
)
from modules.commercial.service import (
    COMMERCIAL_CONTRACT_STATUS,
    DEFAULT_COMMERCIAL_SETTINGS,
    DEFAULT_PLATFORM_BRAND,
    DEFAULT_SAAS_CONTRACT_CLAUSES,
    build_commercial_contract_pdf,
    commercial_plan_for_company,
    company_license_label,
    compute_company_contract_metrics,
    count_company_users,
    default_commercial_settings,
    ensure_commercial_contract_tables,
    ensure_commercial_settings,
    generate_commercial_contract_pdf,
    get_commercial_settings,
    get_or_create_commercial_contract,
    get_platform_brand,
    normalize_plan_key,
    register_commercial_contract_event,
    save_commercial_contract,
    save_commercial_settings as _save_commercial_settings_impl,
    save_platform_brand,
    send_commercial_contract_email,
    sign_commercial_contract,
    upload_signed_contract_file,
    validate_cnpj,
    validate_login_logo_payload,
    validate_logo_payload,
    validate_platform_brand_payload,
)
from pathlib import Path
from urllib.parse import parse_qs, quote, urlparse
from core.router import router
from modules.settings.routes import register_routes as _reg_settings
from modules.devolutions.routes import register_routes as _reg_devolutions
from modules.reports.routes import register_routes as _reg_reports
from modules.feedback.routes import register_routes as _reg_feedback
from modules.commercial.routes import register_routes as _reg_commercial
from modules.purchases.routes import register_routes as _reg_purchases
from modules.portal.routes import register_routes as _reg_portal
from modules.ficha.routes import register_routes as _reg_ficha
from modules.stock.routes import register_routes as _reg_stock
from modules.employees.routes import register_routes as _reg_employees
from modules.companies.routes import register_routes as _reg_companies
from modules.epis.routes import register_routes as _reg_epis
from modules.deliveries.routes import register_routes as _reg_deliveries

try:
    import bcrypt
    BCRYPT_AVAILABLE = True
except ModuleNotFoundError:
    bcrypt = None
    BCRYPT_AVAILABLE = False

_reg_settings(router)
_reg_devolutions(router)
_reg_reports(router)
_reg_feedback(router)
_reg_commercial(router)
_reg_purchases(router)
_reg_portal(router)
_reg_ficha(router)
_reg_stock(router)
_reg_employees(router)
_reg_companies(router)
_reg_epis(router)
_reg_deliveries(router)
_reg_units(router)
_reg_users(router)
_reg_auth(router)

BASE_DIR = Path(__file__).resolve().parent / "static"
UTC = timezone.utc
DATABASE_URL = os.environ.get('DATABASE_URL', '').strip()
DB_POOL_MINCONN = int(os.environ.get('DB_POOL_MINCONN', '1'))
DB_POOL_MAXCONN = int(os.environ.get('DB_POOL_MAXCONN', '10'))
PASSWORD_RECOVERY_KEY = os.environ.get('PASSWORD_RECOVERY_KEY', '').strip()
JWT_SECRET = os.environ.get('JWT_SECRET', '').strip() or PASSWORD_RECOVERY_KEY or 'change-this-jwt-secret'
JWT_EXP_SECONDS = int(os.environ.get('JWT_EXP_SECONDS', '28800'))
DB_BOOTSTRAP_STATE = {
    'started_at': '',
    'completed_at': '',
    'ready': False,
    'error_code': '',
    'error_kind': '',
    'error_message': '',
}
DB_BOOTSTRAP_STATE_LOCK = threading.Lock()
BOOTSTRAP_READY_EXEMPT_PATHS = frozenset({
    '/api/login',
})



# Error/Status Message Constants
MSG_TOKEN_INVALID = 'Token inválido.'
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


# Company Names
COMPANY_DOF_BRASIL = 'DOF Brasil'
COMPANY_NORSKAN_OFFSHORE = 'Norskan Offshore'
EPI_ALL_UNITS_VALUE = '__ALL_UNITS__'

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

def require_master_actor(connection, actor_user_id):
    actor = authorize_action(connection, actor_user_id, 'commercial:view')
    if actor['role'] != 'master_admin':
        raise PermissionError('Apenas o Administrador Master pode alterar a marca do sistema.')
    return actor


def migrate_role_hierarchy(connection):
    connection.execute("UPDATE users SET role = 'master_admin', company_id = NULL WHERE role = 'general_admin' AND company_id IS NULL")



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


def compute_alerts(connection, actor=None):
    return _compute_alerts_impl(
        connection,
        actor,
        fetch_low_stock_items=fetch_low_stock_items,
        actor_operational_unit_id=actor_operational_unit_id,
        fetch_epis=fetch_epis,
    )


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


def authorize_action(connection, actor_user_id, action, company_id=None):
    actor = require_actor(connection, actor_user_id)
    ensure_permission(actor, action)
    if company_id is not None:
        ensure_company_access(actor, company_id)
    return actor


def parse_actor_user_id_from_query(parsed):
    return int(parse_qs(parsed.query).get('actor_user_id', ['0'])[0])


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


def build_ficha_epi_html(connection, employee_id, actor):
    return _build_ficha_epi_html_impl(
        connection, employee_id, actor,
        get_employee_fn=get_employee_by_id,
        ensure_actor_scope_fn=ensure_actor_employee_scope,
    )


def build_ficha_epi_html_by_period(connection, ficha_period_id, actor):
    return _build_ficha_epi_html_by_period_impl(
        connection, ficha_period_id, actor,
        get_employee_fn=get_employee_by_id,
        actor_unit_id_fn=actor_operational_unit_id,
    )


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


from modules.ficha.service import (  # noqa: E402
    apply_snapshot_retention,
    assert_ficha_period_can_close,
    compute_ficha_period_signature_state,
    fetch_ficha_epi_audit_logs,
    get_ficha_period_close_requirements,
    is_valid_ficha_period_state,
    resolve_ficha_period_effective_status,
)


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
            result = router.dispatch('GET', parsed.path, self, parsed)
            if result is not None:
                return result

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
            result = router.dispatch('POST', parsed.path, self, parsed, payload)
            if result is not None:
                return result

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
            result = router.dispatch('PUT', parsed.path, self, parsed, payload)
            if result is not None:
                return result
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
            result = router.dispatch('DELETE', parsed.path, self, parsed)
            if result is not None:
                return result
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
