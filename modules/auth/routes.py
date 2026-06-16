"""Rotas de autenticação."""
import hmac
import os
import traceback
from contextlib import closing

from core.database import get_connection
from core.rate_limit import get_client_ip, login_limiter, recovery_limiter
from core.repository import authorize_action
from core.security import (
    hash_password,
    is_bcrypt_hash,
    parse_bearer_token,
    resolve_actor_user_id,
    validate_password_strength,
    verify_password,
)
from epi_backend.config import APP_ENV, PASSWORD_RECOVERY_KEY
from epi_backend.http_utils import require_fields, send_api_response, send_json, structured_log
from core.repository import get_user_by_id
from core.permissions import PERMISSIONS
from modules.auth.service import (
    authenticate_login,
    generate_user_recovery_token,
    get_user_by_username,
    refresh_access_token,
    require_actor,
    send_recovery_email_smtp,
    update_user_password,
    validate_and_clear_recovery_token,
)


def handle_post_login(handler, parsed, payload, match):
    structured_log('info', 'auth.login.entry', path=parsed.path, raw_path=getattr(handler, 'path', ''))
    client_ip = get_client_ip(handler)
    if not login_limiter.is_allowed(client_ip):
        structured_log('warning', 'auth.login.rate_limited', ip=client_ip)
        return send_json(handler, 429, {
            'ok': False,
            'error': {
                'code': 'AUTH_RATE_LIMITED',
                'message': 'Muitas tentativas de login. Aguarde 1 minuto e tente novamente.',
            }
        })
    _bootstrap_state_fn = None
    try:
        from epi_backend.bootstrap import _get_bootstrap_state
        _bootstrap_state_fn = _get_bootstrap_state
    except Exception:
        pass

    if _bootstrap_state_fn is not None:
        try:
            _bs = _bootstrap_state_fn()
            structured_log(
                'info',
                'auth.login.bootstrap_state',
                ready=bool(_bs.get('ready')),
                error_code=str(_bs.get('error_code') or ''),
                error_kind=str(_bs.get('error_kind') or ''),
                error_message=str(_bs.get('error_message') or ''),
            )
        except Exception:
            pass

    _login_response = {'status': None, 'code': ''}

    def _login_send_json(h, status, response_payload):
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
        return send_json(h, status, response_payload)

    require_fields(payload, ['username', 'password'])
    try:
        with closing(get_connection()) as connection:
            response_payload, status_code, error_payload = authenticate_login(
                connection,
                payload.get('username', ''),
                payload.get('password', '')
            )
        if error_payload:
            return _login_send_json(handler, status_code, error_payload)
        return _login_send_json(handler, status_code, response_payload)
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
            handler,
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


# ── POST /api/recover-password ────────────────────────────────────────────────

def handle_post_recover_password(handler, parsed, payload, match):
    client_ip = get_client_ip(handler)
    if not recovery_limiter.is_allowed(client_ip):
        structured_log('warning', 'auth.recovery.rate_limited', ip=client_ip)
        return send_json(handler, 429, {
            'ok': False,
            'error': {
                'code': 'RECOVERY_RATE_LIMITED',
                'message': 'Muitas tentativas de recuperação. Aguarde 5 minutos e tente novamente.',
            }
        })
    require_fields(payload, ['username', 'new_password', 'recovery_key'])
    username = str(payload.get('username', '')).strip()
    new_password = validate_password_strength(payload.get('new_password', ''))
    provided_key = str(payload.get('recovery_key', '')).strip()
    with closing(get_connection()) as connection:
        user_ref = get_user_by_username(connection, username)
        if not user_ref:
            raise ValueError('Usuário não encontrado.')
        token_hash_row = connection.execute(
            'SELECT recovery_token_hash FROM users WHERE id = ?', (user_ref['id'],)
        ).fetchone()
        has_per_user_token = bool(token_hash_row and token_hash_row['recovery_token_hash'])
        if has_per_user_token:
            validate_and_clear_recovery_token(connection, username, provided_key)
        else:
            password_recovery_key = PASSWORD_RECOVERY_KEY
            if not password_recovery_key:
                raise PermissionError('Nenhuma chave de recuperação ativa. Solicite ao administrador.')
            if not hmac.compare_digest(provided_key, password_recovery_key):
                raise PermissionError('Chave de recuperação inválida.')
        update_user_password(connection, user_ref['id'], hash_password(new_password))
        connection.commit()
        structured_log('info', 'auth.password_recovered', username=username, user_id=user_ref['id'])
        return send_json(handler, 200, {'ok': True})


# ── POST /api/users/<id>/recovery-token ───────────────────────────────────────

def handle_post_user_recovery_token(handler, parsed, payload, match):
    user_id = int(match.group(1))
    actor_user_id = resolve_actor_user_id(handler, parsed, payload)
    with closing(get_connection()) as connection:
        from core.repository import authorize_action as _auth_action
        from core.auth import ensure_company_access as _ensure_company
        from core.roles import normalize_role_name as _norm_role
        actor = _auth_action(connection, actor_user_id, 'users:update')
        target = get_user_by_id(connection, user_id)
        if not target:
            raise ValueError('Usuário não encontrado.')
        actor_role = actor['role']
        target_role = _norm_role(target.get('role', ''))
        if actor_role == 'master_admin':
            if target_role == 'master_admin' and target['id'] != actor['id']:
                raise PermissionError('Administrador Master não pode gerar chave para outro Administrador Master.')
        elif actor_role == 'general_admin':
            allowed = ('registry_admin', 'admin', 'user', 'buyer', 'approver', 'employee')
            if target_role not in allowed:
                raise PermissionError('Administrador Geral pode gerar chaves apenas para perfis inferiores da própria empresa.')
            _ensure_company(actor, target.get('company_id'))
        else:
            raise PermissionError('Somente Administrador Geral ou Master podem gerar chaves de recuperação.')
        token = generate_user_recovery_token(connection, user_id)
        connection.commit()
        structured_log('info', 'auth.recovery_token_generated', actor_id=actor['id'], target_user_id=user_id)
        return send_json(handler, 200, {'ok': True, 'token': token})


# ── POST /api/auth/request-email-recovery ─────────────────────────────────────

def handle_post_request_email_recovery(handler, parsed, payload, match):
    require_fields(payload, ['username'])
    username = str(payload.get('username', '')).strip()
    _ok_msg = 'Se o usuário existir com e-mail configurado, o token será enviado por e-mail.'
    with closing(get_connection()) as connection:
        user_ref = get_user_by_username(connection, username)
        if not user_ref:
            return send_json(handler, 200, {'ok': True, 'message': _ok_msg})
        row = connection.execute(
            'SELECT id, username, email FROM users WHERE id = ?', (user_ref['id'],)
        ).fetchone()
        if not row or not row['email']:
            return send_json(handler, 200, {'ok': True, 'message': _ok_msg})
        token = generate_user_recovery_token(connection, row['id'])
        connection.commit()
    try:
        send_recovery_email_smtp(row['email'], row['username'], token)
    except Exception as exc:
        structured_log('error', 'auth.recovery_email_failed', username=username, error=str(exc))
        raise ValueError(f'Falha ao enviar e-mail: {exc}')
    structured_log('info', 'auth.recovery_email_sent', user_id=row['id'], username=username)
    return send_json(handler, 200, {'ok': True, 'message': _ok_msg})


# ── POST /api/change-password ─────────────────────────────────────────────────

def handle_post_change_password(handler, parsed, payload, match):
    require_fields(payload, ['actor_user_id', 'current_password', 'new_password'])
    with closing(get_connection()) as connection:
        actor_user_id = resolve_actor_user_id(handler, parsed, payload)
        user = get_user_by_id(connection, actor_user_id)
        if not user:
            raise ValueError('Usuário não encontrado.')
        current_password = str(payload.get('current_password', '')).strip()
        new_password_raw = str(payload.get('new_password', '')).strip()
        if not verify_password(user['password'], current_password):
            raise PermissionError('Senha atual incorreta.')
        new_hashed = hash_password(validate_password_strength(new_password_raw))
        update_user_password(connection, actor_user_id, new_hashed)
        connection.commit()
        structured_log('info', 'auth.password_changed', user_id=actor_user_id)
        return send_json(handler, 200, {'ok': True})


def handle_get_auth_diagnostics(handler, parsed, payload, match):
    from modules.auth.service import auth_diagnostics

    diagnostics_key = os.environ.get('AUTH_DIAGNOSTICS_KEY', '').strip()
    provided_key = str(handler.headers.get('X-Diagnostics-Key', '')).strip()
    has_diagnostics_key = bool(diagnostics_key and hmac.compare_digest(provided_key, diagnostics_key))
    is_production = APP_ENV in ('prod', 'production')
    if has_diagnostics_key or not is_production:
        return send_json(handler, 200, auth_diagnostics(public=False))

    try:
        with closing(get_connection()) as connection:
            authorize_action(connection, resolve_actor_user_id(handler, parsed), 'dashboard:view')
        return send_json(handler, 200, auth_diagnostics(public=False))
    except Exception:
        return send_json(handler, 200, auth_diagnostics(public=True))


def handle_get_db_pool_status(handler, parsed, payload, match):
    from core.database import db_pool_status
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed), 'dashboard:view')
        if actor.get('role') != 'master_admin':
            raise PermissionError('Somente Administrador Master pode consultar o status do pool.')
        return send_json(handler, 200, {'pool': db_pool_status()})


def handle_get_bootstrap(handler, parsed, payload, match):
    from epi_backend.http_utils import structured_log
    from modules.auth.service import build_bootstrap
    actor_user_id = None
    actor = None
    try:
        actor_user_id = resolve_actor_user_id(handler, parsed)
        with closing(get_connection()) as connection:
            actor = authorize_action(connection, actor_user_id, 'dashboard:view')
            structured_log('info', 'bootstrap.started', actor_user_id=actor_user_id, user_role=actor.get('role'), company_id=actor.get('company_id'), path=parsed.path)
            payload_data = build_bootstrap(connection, actor)
            structured_log('info', 'bootstrap.completed', actor_user_id=actor_user_id, user_role=actor.get('role'), company_id=actor.get('company_id'), path=parsed.path, degraded=bool(payload_data.get('degraded')), failed_sections=[item.get('section') for item in payload_data.get('bootstrap_warnings', [])])
            return send_json(handler, 200, {'ok': True, 'data': payload_data})
    except PermissionError as exc:
        from epi_backend.http_utils import structured_log
        structured_log('warning', 'bootstrap.auth_failed', actor_user_id=actor_user_id, user_role=actor.get('role') if actor else '', company_id=actor.get('company_id') if actor else '', path=parsed.path, error=str(exc))
        send_json(handler, 403, {'error': str(exc)})


def handle_post_auth_refresh(handler, parsed, payload, match):
    """Reemite o access token a partir de um refresh token válido (stateless)."""
    client_ip = get_client_ip(handler)
    if not login_limiter.is_allowed(client_ip):
        structured_log('warning', 'auth.refresh.rate_limited', ip=client_ip)
        return send_json(handler, 429, {
            'ok': False,
            'error': {'code': 'AUTH_RATE_LIMITED', 'message': 'Muitas tentativas. Aguarde e tente novamente.'},
        })
    payload = payload or {}
    refresh_token = str(payload.get('refresh_token') or '').strip()
    if not refresh_token:
        try:
            refresh_token = parse_bearer_token(handler)
        except PermissionError:
            refresh_token = ''
    if not refresh_token:
        return send_json(handler, 400, {'error': 'Token de atualização ausente.', 'code': 'MISSING_REFRESH_TOKEN'})
    try:
        with closing(get_connection()) as connection:
            response_payload, status_code, error_payload = refresh_access_token(connection, refresh_token)
        if error_payload:
            return send_json(handler, status_code, error_payload)
        return send_json(handler, status_code, response_payload)
    except PermissionError:
        return send_json(handler, 401, {'error': 'Token de atualização inválido ou expirado.', 'code': 'INVALID_REFRESH_TOKEN'})


def handle_get_auth_me(handler, parsed, payload, match):
    """Identidade enxuta do usuário autenticado (envelope {success,data,message})."""
    with closing(get_connection()) as connection:
        actor = require_actor(connection, resolve_actor_user_id(handler, parsed))
        user = dict(actor)
        user.pop('password', None)
        return send_api_response(handler, 200, data={
            'user': user,
            'permissions': sorted(PERMISSIONS.get(actor['role'], set())),
        })


def register_routes(router):
    router.register('GET',  '/api/auth-diagnostics',  handle_get_auth_diagnostics)
    router.register('GET',  '/api/db-pool/status',    handle_get_db_pool_status)
    router.register('GET',  '/api/bootstrap',          handle_get_bootstrap)
    router.register('GET',  '/api/auth/me',           handle_get_auth_me)
    router.register('POST', '/api/login',             handle_post_login)
    router.register('POST', '/api/auth/login',        handle_post_login)
    router.register('POST', '/api/auth/refresh',      handle_post_auth_refresh)
    router.register('POST', '/api/recover-password',  handle_post_recover_password)
    router.register('POST', '/api/change-password',   handle_post_change_password)
    router.register('POST', r'/api/users/(\d+)/recovery-token$', handle_post_user_recovery_token, regex=True)
    router.register('POST', '/api/auth/request-email-recovery', handle_post_request_email_recovery)
