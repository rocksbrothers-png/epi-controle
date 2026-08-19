"""Serviço de autenticação sem DI."""

import os
import traceback as _traceback
from urllib.parse import parse_qs
# `get_user_password_policy` mora em core.repository (ver nota lá): reexportada
# aqui para os importadores existentes deste módulo continuarem funcionando.
from core.repository import (
    enforce_company_block_rules,
    get_user_password_policy,
    require_actor as _require_actor,
)
from modules.employees.service import actor_operational_unit_id
from core.auth import ensure_permission, ensure_company_access
from core.roles import normalize_role_name
from core.security import (
    JWT_EXP_SECONDS,
    JWT_REFRESH_EXP_SECONDS,
    create_jwt_token,
    create_refresh_token,
    decode_token_of_type,
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


def authenticate_login(connection, username, password, totp_code=None):
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

    # Autenticação em duas etapas (TOTP): quando habilitada, a senha correta
    # não basta — o código do app autenticador é exigido na mesma requisição.
    totp = get_user_totp_state(connection, row['id'])
    if totp['enabled']:
        from core.totp import verify_totp
        provided_code = str(totp_code or '').strip()
        if not provided_code:
            structured_log('info', 'auth.totp_challenge', user_id=row['id'])
            return None, 401, {
                'error': 'Informe o código de autenticação em duas etapas.',
                'code': 'TOTP_REQUIRED',
            }
        if not verify_totp(totp['secret'], provided_code):
            structured_log('warning', 'auth.totp_failed', user_id=row['id'])
            return None, 401, {
                'error': 'Código de autenticação em duas etapas inválido.',
                'code': 'TOTP_INVALID',
            }

    # Política de senha temporária (provisionada por admin): se expirou e a
    # troca ainda é obrigatória, bloqueia o login e orienta a recuperação.
    # Não afeta usuários existentes (must_change_password default 0). Avaliado
    # após o TOTP para não interferir no desafio de duas etapas.
    password_policy = get_user_password_policy(connection, row['id'])
    if password_policy['must_change'] and password_policy['expired']:
        structured_log('warning', 'auth.temp_password_expired', user_id=row['id'])
        return None, 403, {
            'error': 'Sua senha temporária expirou. Use "Esqueci minha senha" para definir uma nova.',
            'code': 'TEMP_PASSWORD_EXPIRED',
        }

    if resolved_role != 'master_admin' and row.get('company_id'):
        enforce_company_block_rules(connection, int(row['company_id']))

    user_data = row_to_dict(row)
    user_data['role'] = resolved_role
    user_data.pop('password', None)
    operational_unit_id = actor_operational_unit_id(connection, user_data)
    if operational_unit_id:
        user_data['operational_unit_id'] = operational_unit_id
    # Sinaliza ao cliente que o 1º acesso exige troca de senha (credencial
    # temporária provisionada por admin). O cliente força a tela de troca.
    user_data['must_change_password'] = bool(password_policy['must_change'])
    structured_log('info', 'auth.login_success', username=row['username'], user_id=row['id'], role=resolved_role)
    from modules.settings.service import get_effective_module_visibility
    return {
        'user': user_data,
        'permissions': sorted(PERMISSIONS.get(resolved_role, set())),
        # Visibilidade estrutural por módulo (menu/rotas/deep links) — mesma
        # combinação (config x permissão técnica) usada no /api/bootstrap.
        # Vem também no login para o NavigationPolicy do Flutter decidir a
        # navegação desde a primeira tela, sem esperar o bootstrap completo.
        'module_visibility': get_effective_module_visibility(connection, user_data, unit_id=operational_unit_id),
        'token': create_jwt_token(user_data),
        'token_expires_in': JWT_EXP_SECONDS,
        'refresh_token': create_refresh_token(user_data),
        'refresh_expires_in': JWT_REFRESH_EXP_SECONDS,
        # Duas chaves com o MESMO valor: o Flutter lê `must_change_password`; o
        # web legado já consome `require_password_change` (fluxo dormante até
        # aqui). Manter ambas evita divergência entre os frontends.
        'must_change_password': bool(password_policy['must_change']),
        'require_password_change': bool(password_policy['must_change']),
    }, 200, None


def refresh_access_token(connection, refresh_token):
    """Reemite um access token (e rotaciona o refresh) a partir de um refresh válido.

    Retorna (response_payload, status, error_payload) no mesmo formato de
    authenticate_login. Stateless: a revogação/detecção de reuso de refresh exige
    um denylist server-side (evolução futura).
    """
    claims = decode_token_of_type(refresh_token, 'refresh')
    user_id = int(claims.get('sub') or 0)
    if not user_id:
        return None, 401, {'error': 'Token de atualização inválido.', 'code': 'INVALID_REFRESH_TOKEN'}
    row = get_user_by_id(connection, user_id)
    if not row or not int(row.get('active') or 0):
        return None, 401, {'error': 'Usuário inválido ou inativo.', 'code': 'INVALID_REFRESH_TOKEN'}
    resolved_role = normalize_role_name(row.get('role'))
    if resolved_role != 'master_admin' and row.get('company_id'):
        enforce_company_block_rules(connection, int(row['company_id']))
    user_data = row_to_dict(row) if not isinstance(row, dict) else dict(row)
    user_data['role'] = resolved_role
    user_data.pop('password', None)
    return {
        'token': create_jwt_token(user_data),
        'token_expires_in': JWT_EXP_SECONDS,
        'refresh_token': create_refresh_token(user_data),
        'refresh_expires_in': JWT_REFRESH_EXP_SECONDS,
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
    _base = (
        'SELECT users.id, users.username, users.full_name, users.role, users.company_id, '
        'users.active, users.linked_employee_id, {email_col}'
        'companies.name AS company_name, companies.cnpj AS company_cnpj '
        'FROM users LEFT JOIN companies ON companies.id = users.company_id'
    )
    for email_col in ('users.email, ', ''):
        sql = _base.format(email_col=email_col)
        try:
            if actor and actor['role'] != 'master_admin':
                rows = connection.execute(
                    sql + ' WHERE users.company_id = ? ORDER BY users.full_name',
                    (actor['company_id'],),
                ).fetchall()
            else:
                rows = connection.execute(sql + ' ORDER BY users.full_name').fetchall()
            return [row_to_dict(row) for row in rows]
        except Exception:
            # On PostgreSQL a failed statement aborts the whole transaction
            # ("current transaction is aborted"). Roll back before retrying,
            # otherwise the fallback query — and every later bootstrap section
            # sharing this connection — fails too.
            try:
                connection.rollback()
            except Exception:
                pass
            if not email_col:
                raise
            # email column not yet migrated — retry without it


def require_actor(connection, actor_user_id, *, allow_password_change_pending=False):
    """Delega para `core.repository.require_actor` — implementação ÚNICA.

    Isto aqui era uma segunda cópia, quase idêntica à de `core.repository`
    (só divergia no nome de uma variável local dentro de
    `enforce_company_block_rules`). Duas cópias da mesma regra divergem no
    primeiro ajuste feito num lado só, e foi exatamente o que aconteceu: o
    bloqueio de senha temporária entrou em `core.repository` e esta cópia
    ficou sem ele — deixando `/api/users/{id}/email` e as rotas de 2FA
    passarem por cima da proteção, em silêncio.

    Mantida como função (e não substituída por um import direto) porque
    `modules/auth/routes.py` e `modules/users/routes.py` a importam deste
    módulo, e o `authorize_action` logo abaixo também a usa.
    """
    return _require_actor(
        connection,
        actor_user_id,
        allow_password_change_pending=allow_password_change_pending,
    )


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


def _safe_bootstrap_section(section_name, loader, fallback, warnings, actor, path='/api/bootstrap', connection=None):
    try:
        return loader()
    except Exception as exc:
        # On PostgreSQL a failed statement aborts the entire transaction, so
        # every later section sharing this connection would fail with
        # "current transaction is aborted". Roll back to clear the abort and
        # keep the remaining sections (and graceful degradation) working.
        if connection is not None:
            try:
                connection.rollback()
            except Exception:
                pass
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


def _with_company_stock_fields(epis):
    """Nomeia o saldo corporativo do catálogo, sem mudar o conjunto de EPIs.

    Aditivo e retrocompatível: `stock` permanece intacto, com o mesmo valor de
    sempre, porque consumidores antigos do bootstrap ainda o leem. O que muda é
    passar a existir um campo cujo nome diz de que escopo o número é.

    A criticidade vem da MESMA função de `/api/stock/low` e `/api/stock/epis`.
    Duas cópias da comparação divergem no primeiro ajuste feito num lado só, e
    o operador passaria a ver alertas diferentes conforme a tela que abrisse.

    Import tardio pelo mesmo motivo dos demais neste arquivo: `modules.stock`
    alcança o auth por caminhos indiretos, e o ciclo já custou um achado de
    CodeQL neste repositório.
    """
    from modules.stock.service import is_stock_critical, resolve_minimum_stock

    for item in epis:
        company_stock = int(item.get('stock') or 0)
        minimum_stock = resolve_minimum_stock(item.get('minimum_stock'))
        item['minimum_stock'] = minimum_stock
        item['company_stock_quantity'] = company_stock
        item['is_company_stock_critical'] = is_stock_critical(company_stock, minimum_stock)
    return epis


def build_bootstrap(connection, actor):
    from modules.settings.service import canary_evaluate_visibility_dataset, get_effective_module_visibility
    from modules.units.service import fetch_units
    from modules.legal_entities.service import fetch_legal_entities
    from modules.employees.service import fetch_employees, fetch_employee_movements
    from modules.epis.service import fetch_epis
    from modules.deliveries.service import fetch_deliveries
    from modules.feedback.service import fetch_feedbacks
    from modules.purchases.service import (
        actor_has_no_purchase_unit_scope as _has_no_purchase_scope,
        count_pending_purchase_requests as _count_pending_purchases,
        get_actor_purchase_unit_scope as _get_purchase_scope,
    )
    from modules.commercial.service import get_platform_brand, get_commercial_settings
    from modules.companies.service import fetch_companies, fetch_company_audit_logs
    from modules.ficha.service import fetch_ficha_epi_audit_logs
    from modules.alerts.service import compute_alerts as _compute_alerts_impl
    from modules.employees.service import actor_has_no_operational_unit as _has_no_operational_unit
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

    def count_pending_purchases():
        # KPI do dashboard: requisições de compra pendentes (não terminais) no
        # escopo do ator. 0 quando o ator não enxerga compras ou não tem empresa.
        if 'purchase_requests:view' not in permissions:
            return 0
        company_id = actor.get('company_id')
        if not company_id:
            return 0
        scope_unit_id = _actor_op_unit_id(connection, actor)
        purchase_scope_units = _get_purchase_scope(connection, actor)
        if _has_no_purchase_scope(actor, scope_unit_id, purchase_scope_units) or _has_no_operational_unit(actor, scope_unit_id):
            return 0
        return _count_pending_purchases(connection, company_id, scope_unit_id, purchase_scope_units)

    warnings = []
    permissions = sorted(_PERMISSIONS.get(actor['role'], set()))

    units = _safe_bootstrap_section('units', lambda: fetch_units(connection, actor), [], warnings, actor, connection=connection)
    employees = _safe_bootstrap_section('employees', lambda: fetch_employees(connection, actor), [], warnings, actor, connection=connection)
    # Escopo de EPI por unidade: perfis operacionais (Administrador Local /
    # Gestor de EPI) só enxergam os EPIs cadastrados na sua unidade + os de
    # nível empresa (unit_id NULL). Administradores de empresa (sem unidade
    # operacional) seguem vendo todos os EPIs. fetch_epis(unit_id) aplica o
    # filtro `epis.unit_id = ? OR epis.unit_id IS NULL`.
    _epis_scope_unit = _actor_op_unit_id(connection, actor)
    if actor.get('role') in ('admin', 'user') and not _epis_scope_unit:
        epis = []
    else:
        epis = _safe_bootstrap_section('epis', lambda: fetch_epis(connection, actor, _epis_scope_unit), [], warnings, actor, connection=connection)

    units = _safe_bootstrap_section(
        'units_visibility_canary',
        lambda: canary_evaluate_visibility_dataset(connection, actor, endpoint_name='/api/bootstrap', dataset_name='units', legacy_items=units),
        units, warnings, actor, connection=connection,
    )
    employees = _safe_bootstrap_section(
        'employees_visibility_canary',
        lambda: canary_evaluate_visibility_dataset(connection, actor, endpoint_name='/api/bootstrap', dataset_name='employees', legacy_items=employees),
        employees, warnings, actor, connection=connection,
    )
    epis = _safe_bootstrap_section(
        'epis_visibility_canary',
        lambda: canary_evaluate_visibility_dataset(connection, actor, endpoint_name='/api/bootstrap', dataset_name='epis', legacy_items=epis),
        epis, warnings, actor, connection=connection,
    )
    # Saldo CORPORATIVO em campo próprio (#258, fatia 1.1C).
    #
    # `bootstrap.epis` sempre trouxe o total da empresa no campo `stock` — mas
    # `stock` é o nome ambíguo que a 1.1B aposentou, e o cliente vinha
    # recalculando a criticidade por conta própria (`stockQuantity <=
    # minimumStock`), duplicando uma regra que já existe no servidor.
    #
    # Aqui só se NOMEIA o que já vinha: mesma consulta, mesmo conjunto de EPIs,
    # mesmo escopo. Nada de `unit_stock_quantity`/`unit_scope_id` — o bootstrap
    # não tem semântica de unidade, e inventar zero afirmaria "esta unidade não
    # tem estoque" sobre uma unidade que nem foi resolvida. Os dois ficam
    # ausentes, e o cliente os lê como `null`, que é o par coerente.
    epis = _with_company_stock_fields(epis)

    users_list = _safe_bootstrap_section('users', lambda: fetch_users(connection, actor), [], warnings, actor, connection=connection)
    users_list = _safe_bootstrap_section(
        'users_visibility_canary',
        lambda: canary_evaluate_visibility_dataset(connection, actor, endpoint_name='/api/bootstrap', dataset_name='users', legacy_items=users_list),
        users_list, warnings, actor, connection=connection,
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
        # Visibilidade estrutural por módulo (menu/rotas/deep links), já
        # combinando a regra padrão + a configuração do Administrador Geral
        # (por tenant) com a permissão técnica do ator. Orienta navegação no
        # Flutter (NavigationPolicy) e no web legado (canAccessView); a
        # autorização de dados continua exclusivamente nas rotas de API.
        'module_visibility': _safe_bootstrap_section(
            'module_visibility',
            lambda: get_effective_module_visibility(connection, actor, unit_id=_epis_scope_unit),
            {}, warnings, actor, connection=connection,
        ),
        'platform_brand': _safe_bootstrap_section('platform_brand', lambda: get_platform_brand(connection), {}, warnings, actor, connection=connection),
        'commercial_settings': _safe_bootstrap_section(
            'commercial_settings',
            lambda: get_commercial_settings(connection) if actor['role'] == 'master_admin' else None,
            None, warnings, actor, connection=connection,
        ),
        'companies': _safe_bootstrap_section('companies', lambda: fetch_companies(connection, None if actor['role'] == 'master_admin' else actor['company_id']), [], warnings, actor, connection=connection),
        'company_audit_logs': _safe_bootstrap_section('company_audit_logs', lambda: fetch_company_audit_logs(connection, actor), [], warnings, actor, connection=connection),
        'ficha_audit_logs': _safe_bootstrap_section('ficha_audit_logs', lambda: fetch_ficha_epi_audit_logs(connection, actor, {}), [], warnings, actor, connection=connection),
        'users': users_list,
        # CNPJs (LegalEntity) visíveis ao ator — alimentam o filtro em cascata do
        # dashboard (Empresa → CNPJ → Unidade → Setor) e o seletor de CNPJ no
        # cadastro de colaborador. Já vem escopado por papel.
        'legal_entities': _safe_bootstrap_section(
            'legal_entities',
            lambda: fetch_legal_entities(connection, actor),
            [], warnings, actor, connection=connection,
        ),
        'units': units,
        'employees': employees,
        'employee_movements': _safe_bootstrap_section('employee_movements', lambda: fetch_employee_movements(connection, actor), [], warnings, actor, connection=connection),
        'epis': epis,
        'deliveries': _safe_bootstrap_section('deliveries', lambda: fetch_deliveries(connection, actor), [], warnings, actor, connection=connection),
        'feedbacks': _safe_bootstrap_section('feedbacks', lambda: fetch_feedbacks(connection, actor), [], warnings, actor, connection=connection),
        'pending_purchases': _safe_bootstrap_section('pending_purchases', count_pending_purchases, 0, warnings, actor, connection=connection),
        'alerts': _safe_bootstrap_section('alerts', lambda: compute_alerts(connection, actor), [], warnings, actor, connection=connection),
        'bootstrap_warnings': warnings,
        'degraded': bool(warnings),
    }
    return payload


def auth_diagnostics(public=False):
    from epi_backend.config import (
        DATABASE_URL as _DB_URL,
        DB_CONNECTOR_AVAILABLE as _DB_AVAIL,
        BCRYPT_AVAILABLE as _BCRYPT,
        JWT_EXP_SECONDS as _JWT_EXP,
        JWT_SECRET_IS_FALLBACK as _JWT_SECRET_IS_FALLBACK,
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
    payload = {
        'database_configured': bool(_DB_URL),
        'database_provider': 'supabase' if 'supabase' in str(host).lower() else 'custom_postgres',
        'db_connector_available': _DB_AVAIL,
        'bcrypt_available': _BCRYPT,
        'jwt_exp_seconds': _JWT_EXP,
        'jwt_secret_default': bool(_JWT_SECRET_IS_FALLBACK),
        'password_recovery_key_configured': bool(_PWD_KEY),
        'migration_runner': migration_state_public,
    }
    if not public:
        payload['database_host'] = host
    return payload


def static_asset_diagnostics():
    import hashlib as _hashlib
    from epi_backend.config import BASE_DIR as base_dir
    index_path = base_dir / 'index.html'
    app_path = base_dir / 'app.js'
    app_index_path = base_dir / 'app' / 'index.html'
    app_bootstrap_path = base_dir / 'app' / 'flutter_bootstrap.js'
    app_manifest_path = base_dir / 'app' / 'manifest.json'

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
        'app_web_index_present': app_index_path.exists(),
        'app_web_index_sha256': digest(app_index_path),
        'app_web_index_bytes': app_index_path.stat().st_size if app_index_path.exists() else 0,
        'app_web_bootstrap_present': app_bootstrap_path.exists(),
        'app_web_bootstrap_sha256': digest(app_bootstrap_path),
        'app_web_bootstrap_bytes': app_bootstrap_path.stat().st_size if app_bootstrap_path.exists() else 0,
        'app_web_manifest_present': app_manifest_path.exists(),
        'app_web_manifest_sha256': digest(app_manifest_path),
        'app_web_manifest_bytes': app_manifest_path.stat().st_size if app_manifest_path.exists() else 0,
        # Backward-compatible diagnostic aliases while /flutter_web/* redirects to /app/*.
        'flutter_web_index_present': app_index_path.exists(),
        'flutter_web_index_sha256': digest(app_index_path),
        'flutter_web_index_bytes': app_index_path.stat().st_size if app_index_path.exists() else 0,
        'flutter_web_bootstrap_present': app_bootstrap_path.exists(),
        'flutter_web_bootstrap_sha256': digest(app_bootstrap_path),
        'flutter_web_bootstrap_bytes': app_bootstrap_path.stat().st_size if app_bootstrap_path.exists() else 0,
        'flutter_web_manifest_present': app_manifest_path.exists(),
        'flutter_web_manifest_sha256': digest(app_manifest_path),
        'flutter_web_manifest_bytes': app_manifest_path.stat().st_size if app_manifest_path.exists() else 0,
        'flutter_web_legacy_redirect_target': '/app/',
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
    # Troca/recuperação define a senha ESCOLHIDA pelo próprio usuário: encerra a
    # política de senha temporária (não exige nova troca nem carrega expiração).
    clear_user_password_policy(connection, user_id)


def clear_user_password_policy(connection, user_id):
    """Zera a exigência de troca e a expiração da senha. Tolerante a bases
    pré-migração (colunas ausentes)."""
    try:
        connection.execute(
            "UPDATE users SET must_change_password = 0, password_expires_at = '' WHERE id = ?",
            (int(user_id),),
        )
    except Exception:
        try:
            connection.rollback()
        except Exception:
            # Rollback que falha significa conexão já inutilizável: não há o que
            # desfazer, e levantar aqui esconderia a falha original (coluna
            # ausente em base pré-migração) atrás de uma secundária. A troca de
            # senha em si já foi gravada e não pode ser perdida por causa disto.
            pass


def get_user_totp_state(connection, user_id):
    """Estado de 2FA do usuário. Tolerante a bases sem as colunas (pré-migração)."""
    try:
        row = connection.execute(
            'SELECT totp_secret, totp_enabled FROM users WHERE id = ?', (int(user_id),)
        ).fetchone()
    except Exception:
        try:
            connection.rollback()
        except Exception:
            pass
        return {'secret': '', 'enabled': False}
    if not row:
        return {'secret': '', 'enabled': False}
    data = row_to_dict(row)
    return {
        'secret': str(data.get('totp_secret') or ''),
        'enabled': int(data.get('totp_enabled') or 0) == 1,
    }


def setup_user_totp(connection, user_id, account_label):
    """Gera (ou regenera) o segredo TOTP — ainda desabilitado até confirmação."""
    from core.totp import generate_totp_secret, otpauth_uri
    state = get_user_totp_state(connection, user_id)
    if state['enabled']:
        raise ValueError('A autenticação em duas etapas já está ativa. Desative antes de gerar um novo segredo.')
    secret = generate_totp_secret()
    connection.execute(
        'UPDATE users SET totp_secret = ?, totp_enabled = 0 WHERE id = ?',
        (secret, int(user_id)),
    )
    return {'secret': secret, 'otpauth_uri': otpauth_uri(secret, account_label)}


def enable_user_totp(connection, user_id, code):
    """Confirma o código do autenticador e liga o 2FA."""
    from core.totp import verify_totp
    state = get_user_totp_state(connection, user_id)
    if not state['secret']:
        raise ValueError('Gere o segredo de autenticação (setup) antes de ativar o 2FA.')
    if not verify_totp(state['secret'], code):
        raise ValueError('Código de autenticação inválido. Confira o app autenticador e tente novamente.')
    connection.execute('UPDATE users SET totp_enabled = 1 WHERE id = ?', (int(user_id),))
    structured_log('info', 'auth.totp_enabled', user_id=int(user_id))


def disable_user_totp(connection, user_id, code):
    """Desativa o 2FA mediante um código válido do autenticador."""
    from core.totp import verify_totp
    state = get_user_totp_state(connection, user_id)
    if not state['enabled']:
        raise ValueError('A autenticação em duas etapas não está ativa.')
    if not verify_totp(state['secret'], code):
        raise ValueError('Código de autenticação inválido.')
    connection.execute(
        'UPDATE users SET totp_enabled = 0, totp_secret = NULL WHERE id = ?', (int(user_id),)
    )
    structured_log('info', 'auth.totp_disabled', user_id=int(user_id))


def generate_user_recovery_token(connection, user_id):
    """Generates a one-time recovery token, stores bcrypt hash + 24h expiry, returns plain token."""
    import secrets
    from datetime import datetime, timedelta
    from epi_backend.config import UTC
    token = secrets.token_urlsafe(32)
    token_hash = hash_password(token)
    expires_at = (datetime.now(UTC) + timedelta(hours=24)).isoformat()
    connection.execute(
        'UPDATE users SET recovery_token_hash = ?, recovery_token_expires_at = ? WHERE id = ?',
        (token_hash, expires_at, int(user_id))
    )
    return token


def validate_and_clear_recovery_token(connection, username, provided_token):
    """Validates per-user token, clears it from DB, returns user row. Raises on any failure."""
    from datetime import datetime
    from epi_backend.config import UTC
    user = get_user_by_username(connection, username)
    if not user:
        raise ValueError('Usuário não encontrado.')
    row = connection.execute(
        'SELECT id, username, password, full_name, role, recovery_token_hash, recovery_token_expires_at FROM users WHERE id = ?',
        (user['id'],)
    ).fetchone()
    if not row:
        raise ValueError('Usuário não encontrado.')
    token_hash = row['recovery_token_hash'] if hasattr(row, '__getitem__') else None
    try:
        token_hash = row['recovery_token_hash']
    except Exception:
        token_hash = None
    if not token_hash:
        raise ValueError('Nenhuma chave de recuperação ativa para este usuário. Solicite ao administrador.')
    expires_str = None
    try:
        expires_str = row['recovery_token_expires_at']
    except Exception:
        pass
    if expires_str:
        try:
            exp = datetime.fromisoformat(expires_str)
            if exp.tzinfo is None:
                exp = exp.replace(tzinfo=UTC)
            if datetime.now(UTC) > exp:
                connection.execute(
                    'UPDATE users SET recovery_token_hash = NULL, recovery_token_expires_at = NULL WHERE id = ?',
                    (row['id'],)
                )
                raise ValueError('Chave de recuperação expirada. Solicite uma nova ao administrador.')
        except ValueError:
            raise
        except Exception:
            pass
    if not verify_password(token_hash, provided_token):
        raise ValueError('Chave de recuperação inválida.')
    connection.execute(
        'UPDATE users SET recovery_token_hash = NULL, recovery_token_expires_at = NULL WHERE id = ?',
        (row['id'],)
    )
    return dict(row)


def send_recovery_email_smtp(to_email, username, token):
    """Sends recovery token via SMTP (delega para epi_backend.mailer)."""
    from epi_backend.mailer import send_email
    body = (
        f'Olá,\n\n'
        f'Você solicitou a recuperação de senha para o usuário "{username}".\n\n'
        f'Sua chave de recuperação (válida por 24 horas):\n\n'
        f'  {token}\n\n'
        f'Para redefinir, acesse a tela de login → "Esqueci minha senha".\n'
        f'Informe seu usuário, a nova senha e esta chave.\n\n'
        f'Se você não solicitou, ignore este e-mail.\n\n'
        f'Atenciosamente,\nEPI Controle'
    )
    send_email(to_email, 'Recuperação de Senha — EPI Controle', body)
