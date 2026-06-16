"""Entry point da aplicação EPI Controle.

Este módulo contém a classe EpiHandler (servidor HTTP), o registro de rotas,
constantes e helpers de resposta. A inicialização do banco (init_db) e a
configuração do admin master (ensure_initial_master_admin) vivem em seus
módulos canônicos (core/schema.py e modules/auth/service.py).
"""

import base64
import binascii
import hashlib
import hmac
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
from pathlib import Path
from urllib.parse import parse_qs, quote, urlparse

from epi_backend.config import (
    APP_ENV,
    BASE_DIR,
    BCRYPT_AVAILABLE,
    DATABASE_URL,
    DB_CONNECTOR_AVAILABLE,
    DBIntegrityError,
    JWT_EXP_SECONDS,
    JWT_SECRET,
    JWT_SECRET_IS_FALLBACK,
    PASSWORD_RECOVERY_KEY,
    UTC,
)
from core.database import PostgresConnectionWrapper, db_pool_status, get_connection
from core.http_cache import is_no_store, resolve_cache_control
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
    ensure_drop_legacy_token_columns,
    ensure_rule_engine_enforced_all_companies,
    ensure_rule_engine_shadow_activated,
    ensure_rule_engine_shadow_log,
    ensure_stock_columns,
    ensure_stock_movement_size_columns,
    ensure_user_columns,
    init_db,
    migrate_role_hierarchy,
    _operational_error_code,
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
from modules.auth.service import (
    authenticate_login as authenticate_login_service,
    auth_diagnostics,
    build_bootstrap,
    get_user_by_id,
    fetch_users,
    require_actor,
    authorize_action,
    parse_actor_user_id_from_query,
    ensure_initial_master_admin,
    INITIAL_MASTER_ADMIN,
)
from modules.employees.service import (
    normalize_cpf,
    normalize_preferred_contact_channel,
    ensure_employee_identity_unique,
    get_employee_by_id,
    get_employee_current_unit,
    actor_operational_unit_id,
    ensure_actor_employee_scope,
    fetch_employees,
    fetch_employee_movements,
)
from modules.deliveries.service import create_delivery_service, fetch_deliveries
from modules.units.routes import register_routes as _reg_units
from modules.units.service import (
    normalize_unit_type,
    delete_epi_dependencies,
    delete_unit_dependencies,
    fetch_units,
    get_unit_by_id,
    get_unit_active_jv_name,
)
from modules.companies.service import (
    ensure_unique_company_cnpj,
    evaluate_company_block_status,
    enforce_company_block_rules,
    ensure_company_user_limit,
    fetch_companies,
    get_company_by_id,
    company_action_label,
    summarize_company_changes,
    register_company_audit,
    fetch_company_audit_logs,
    validate_company_payload,
)
from modules.epis.service import (
    parse_epi_joinventures,
    normalize_active_joinventure_name,
    parse_epi_scope_unit_id,
    resolve_epi_scope_metadata,
    epi_context_signature,
    resolve_epi_scope_unit,
    validate_epi_uniqueness,
    fetch_epis,
    get_epi_by_id,
)
from modules.stock.service import (
    build_master_epi_qr,
    build_stock_item_qr,
    generate_epi_qr_code,
    get_unit_stock,
    next_company_qr_sequence,
    upsert_unit_stock,
    backfill_unit_stock_from_epis,
    normalize_item_size_value,
    resolve_item_size,
    resolve_effective_size_fields,
    apply_effective_size_fields,
    sync_epi_scope_stock_unit,
    parse_stock_qr_lookup_value,
    fetch_epi_size_balance,
)
from modules.reports.service import build_reports
from modules.users.routes import register_routes as _reg_users
from modules.users.service import (
    authorize_user_management,
    resolve_target_company_id,
    ensure_operational_role_link,
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
    canary_evaluate_visibility_dataset,
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
from modules.alerts.service import compute_alerts_wired as compute_alerts
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
    _auto_add_received_items_to_stock,
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
    generate_po_number,
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
    build_ficha_epi_html,
    build_ficha_epi_html_by_period,
    period_days_from_schedule,
    resolve_delivery_period,
    register_ficha_epi_audit,
    build_ficha_archive_filters,
    fetch_ficha_archive_snapshots,
    get_ficha_archive_snapshot_by_id,
    _snapshot_status,
    build_ficha_snapshot_payload,
    ensure_ficha_snapshot_for_period,
    refresh_ficha_snapshot_for_period_if_exists,
    apply_snapshot_retention,
    assert_ficha_period_can_close,
    compute_ficha_period_signature_state,
    fetch_ficha_epi_audit_logs,
    get_ficha_period_close_requirements,
    is_valid_ficha_period_state,
    resolve_ficha_period_effective_status,
)
from modules.devolutions.service import register_epi_devolution
from modules.portal.service import (
    EMPLOYEE_PORTAL_LINK_HOURS,
    EMPLOYEE_PORTAL_SECRET_KEY,
    EmployeePortalAccessDenied,
    MSG_TOKEN_ABSENT,
    MSG_TOKEN_EXPIRED_ACCESS,
    build_employee_ficha_pdf,
    build_portal_link_from_cpf,
    get_employee_portal_context_by_token,
    hash_portal_token,
    parse_int_flexible,
    parse_iso_datetime_utc,
    register_employee_portal_audit,
    resolve_external_employee_context,
    validate_portal_cpf_with_attempts,
)
from modules.auth.service import static_asset_diagnostics
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
    only_digits,
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
from core.router import router
from core.rate_limit import get_client_ip, login_limiter, recovery_limiter
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
from modules.tenant.routes import register_routes as _reg_tenant
from modules.i18n.routes import register_routes as _reg_i18n

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
_reg_tenant(router)
_reg_i18n(router)

from epi_backend.bootstrap import (
    DB_BOOTSTRAP_STATE,
    DB_BOOTSTRAP_STATE_LOCK,
    BOOTSTRAP_READY_EXEMPT_PATHS,
    _set_bootstrap_state,
    _get_bootstrap_state,
    current_runtime_health,
    runtime_probe_response,
)

# ── Message / SQL constants ──────────────────────────────────────────────────

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
SQL_UPDATE_EMPLOYEE = (
    "UPDATE employees SET company_id = ?, unit_id = ?, employee_id_code = ?, cpf = ?, name = ?, "
    "email = ?, whatsapp = ?, preferred_contact_channel = ?, "
    "sector = ?, role_name = ?, admission_date = ?, schedule_type = ?, tipo_vinculo = ?, empresa_origem = ? "
    "WHERE id = ?"
)

LOG_HTTP_PERMISSION_ERROR = 'http.permission_error'
LOG_HTTP_VALUE_ERROR = 'http.value_error'
LOG_HTTP_UNHANDLED_ERROR = 'http.unhandled_error'

# CSP report-only policy for the legacy website + Flutter Web gateway.
# Keep this in report-only mode while the legacy static HTML still contains
# inline event handlers/styles; move to blocking mode only after modularization.
CSP_LEGACY_SCRIPT_SOURCES = ("'self'", "'unsafe-inline'", 'https://unpkg.com')
CSP_LEGACY_STYLE_SOURCES = ("'self'", "'unsafe-inline'", 'https://fonts.googleapis.com')
CSP_REPORT_ONLY_DIRECTIVES = (
    ("default-src", ("'self'",)),
    ("script-src", CSP_LEGACY_SCRIPT_SOURCES),
    ("style-src", CSP_LEGACY_STYLE_SOURCES),
    ("img-src", ("'self'", 'data:', 'blob:', 'https://api.qrserver.com')),
    ("font-src", ("'self'", 'data:', 'https://fonts.gstatic.com')),
    ("connect-src", ("'self'",)),
    ("frame-ancestors", ("'self'",)),
    ("base-uri", ("'self'",)),
)

COMPANY_DOF_BRASIL = 'DOF Brasil'
COMPANY_NORSKAN_OFFSHORE = 'Norskan Offshore'
EPI_ALL_UNITS_VALUE = '__ALL_UNITS__'


# ── Helper functions ─────────────────────────────────────────────────────────

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


# ── HTTP Request Handler ─────────────────────────────────────────────────────

class EpiHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(BASE_DIR), **kwargs)

    def _apply_default_response_headers(self):
        parsed = urlparse(self.path)
        path = parsed.path or ''
        request_origin = str(self.headers.get('Origin', '')).strip()
        configured_origins = [
            item.strip()
            for item in os.environ.get('CORS_ALLOW_ORIGIN', '*').split(',')
            if item.strip()
        ] or ['*']
        is_production = APP_ENV in ('prod', 'production')
        if '*' in configured_origins and not is_production:
            response_origin = '*'
        elif request_origin and request_origin in configured_origins:
            response_origin = request_origin
        elif not is_production and configured_origins:
            response_origin = configured_origins[0]
        else:
            response_origin = ''

        if response_origin:
            self.send_header('Access-Control-Allow-Origin', response_origin)
        self.send_header('Vary', 'Origin')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, PATCH, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Authorization, Content-Type, Accept, X-Requested-With, X-Tenant-Slug')
        if response_origin and response_origin != '*':
            self.send_header('Access-Control-Allow-Credentials', 'true')

        # Security headers
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('X-Frame-Options', 'SAMEORIGIN')
        self.send_header('X-XSS-Protection', '1; mode=block')
        self.send_header('Referrer-Policy', 'strict-origin-when-cross-origin')
        self.send_header('Permissions-Policy', 'camera=(self), microphone=(), geolocation=()')
        csp_report_only = '; '.join(
            f"{name} {' '.join(values)}"
            for name, values in CSP_REPORT_ONLY_DIRECTIVES
        )
        csp_report_uri = os.environ.get('CSP_REPORT_URI', '').strip()
        csp_report_uri_safe = (
            csp_report_uri
            and '\r' not in csp_report_uri
            and '\n' not in csp_report_uri
            and (
                csp_report_uri.startswith('/')
                or csp_report_uri.startswith('https://')
                or (APP_ENV not in ('prod', 'production') and csp_report_uri.startswith('http://'))
            )
        )
        if csp_report_uri_safe:
            csp_report_only = f"{csp_report_only}; report-uri {csp_report_uri}"
        self.send_header('Content-Security-Policy-Report-Only', csp_report_only)
        if APP_ENV in ('prod', 'production'):
            self.send_header('Strict-Transport-Security', 'max-age=31536000; includeSubDomains')

        cache_control = resolve_cache_control(path)
        if cache_control:
            self.send_header('Cache-Control', cache_control)
            if is_no_store(cache_control):
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

    def _handle_csp_report(self):
        try:
            length = int(self.headers.get('Content-Length', '0') or '0')
        except (TypeError, ValueError):
            length = 0
        raw = self.rfile.read(min(max(length, 0), 65536)) if length else b'{}'
        try:
            payload = json.loads(raw.decode('utf-8') or '{}')
        except (UnicodeDecodeError, json.JSONDecodeError):
            payload = {}
        report = payload.get('csp-report') if isinstance(payload, dict) else {}
        if not isinstance(report, dict):
            report = payload if isinstance(payload, dict) else {}

        def _compact(value, limit=240):
            text = str(value or '').replace('\r', ' ').replace('\n', ' ').strip()
            return text[:limit]

        structured_log(
            'warning',
            'security.csp_report',
            document_uri=_compact(report.get('document-uri')),
            violated_directive=_compact(report.get('violated-directive') or report.get('effective-directive')),
            blocked_uri=_compact(report.get('blocked-uri')),
            source_file=_compact(report.get('source-file')),
            line_number=_compact(report.get('line-number'), 32),
        )
        self.send_response(204)
        self.send_header('Content-Length', '0')
        return self.end_headers()

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
        if request_path == '/app' or request_path.startswith('/app/'):
            return True
        if request_path == '/flutter_web' or request_path.startswith('/flutter_web/'):
            return True
        return False

    def _legacy_flutter_web_redirect(self, parsed):
        path = str(parsed.path or '')
        if path == '/flutter_web' or path == '/flutter_web/':
            target = '/app/'
        elif path.startswith('/flutter_web/'):
            target = '/app/' + path[len('/flutter_web/'):].lstrip('/')
        else:
            return ''
        if parsed.query:
            target = f"{target}?{parsed.query}"
        return target

    def _redirect_legacy_flutter_web(self, parsed):
        target = self._legacy_flutter_web_redirect(parsed)
        if not target:
            return False
        self.send_response(308)
        self.send_header('Location', target)
        self.send_header('Content-Length', '0')
        self.end_headers()
        return True

    def _resolve_static_fallback_path(self, request_path):
        path = str(request_path or '')
        if path == '/':
            return '/index.html'
        if path == '/app' or path == '/app/':
            return '/app/index.html'
        if path.startswith('/app/'):
            requested = BASE_DIR / path.lstrip('/')
            if not requested.exists():
                return '/app/index.html'
        return ''

    def _require_bootstrap_ready(self, path):
        gate_path = self.path if path is None else str(path)
        parsed = urlparse(gate_path)
        normalized_path = str(parsed.path or '').rstrip('/') or '/'
        if not normalized_path.startswith('/api/'):
            return True
        state = _get_bootstrap_state()
        _BOOTSTRAP_EXEMPT_PREFIXES = ('/api/i18n/', '/api/tenant/')
        allowed = (
            normalized_path in BOOTSTRAP_READY_EXEMPT_PATHS
            or any(normalized_path.startswith(p) for p in _BOOTSTRAP_EXEMPT_PREFIXES)
        )
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
            if self._redirect_legacy_flutter_web(parsed):
                return
            fallback_path = self._resolve_static_fallback_path(parsed.path)
            if fallback_path:
                self.path = fallback_path
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

        try:
            result = router.dispatch('GET', parsed.path, self, parsed)
            if result is not None:
                return result
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
            if self._redirect_legacy_flutter_web(parsed):
                return
            fallback_path = self._resolve_static_fallback_path(parsed.path)
            if fallback_path:
                self.path = fallback_path
            return super().do_HEAD()
        if parsed.path.startswith('/api/') and not self._require_bootstrap_ready(parsed.path):
            return
        return super().do_HEAD()

    def do_POST(self):
        parsed = urlparse(self.path)
        structured_log('info', 'http.post.entry', path=parsed.path, raw_path=self.path)
        if parsed.path == '/api/csp-report':
            return self._handle_csp_report()
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


# ── Server startup ───────────────────────────────────────────────────────────

def main():
    import threading as _threading

    port = int(os.environ.get('EPI_PORT', os.environ.get('PORT', '8000')))

    # O Render precisa detectar a porta em < 60s: servidor sobe ANTES de init_db.
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
        jwt_secret_default=JWT_SECRET_IS_FALLBACK,
        password_recovery_key_configured=bool(PASSWORD_RECOVERY_KEY)
    )

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
            # Servidor continua no ar para /api/login e health — evita loop de restart
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

    _init_thread = _threading.Thread(target=_run_init_db, daemon=True, name='init_db')
    _init_thread.start()

    structured_log('info', 'server.started', port=port)
    try:
        server.serve_forever()
    except Exception as exc:
        structured_log('error', 'server.startup_failed', error=str(exc))
        raise


if __name__ == '__main__':
    main()
