"""Rotas de autenticação."""
import hmac
import traceback
from contextlib import closing

from core.database import get_connection
from core.repository import authorize_action
from core.security import (
    hash_password,
    is_bcrypt_hash,
    resolve_actor_user_id,
    validate_password_strength,
    verify_password,
)
from epi_backend.config import PASSWORD_RECOVERY_KEY
from epi_backend.http_utils import require_fields, send_json, structured_log
from modules.auth.service import authenticate_login
from core.repository import get_user_by_id


def handle_post_login(handler, parsed, payload, match):
    structured_log('info', 'auth.login.entry', path=parsed.path, raw_path=getattr(handler, 'path', ''))
    _bootstrap_state_fn = None
    try:
        import server_postgres as _sp
        _bootstrap_state_fn = _sp._get_bootstrap_state
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
    require_fields(payload, ['username', 'new_password', 'recovery_key'])
    username = str(payload.get('username', '')).strip()
    new_password = validate_password_strength(payload.get('new_password', ''))
    provided_key = str(payload.get('recovery_key', '')).strip()
    password_recovery_key = PASSWORD_RECOVERY_KEY
    if not password_recovery_key:
        raise PermissionError('Recuperação de senha indisponível no ambiente.')
    if not hmac.compare_digest(provided_key, password_recovery_key):
        raise PermissionError('Chave de recuperação inválida.')
    with closing(get_connection()) as connection:
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
        return send_json(handler, 200, {'ok': True})


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
        connection.execute('UPDATE users SET password = ? WHERE id = ?', (new_hashed, int(actor_user_id)))
        connection.commit()
        structured_log('info', 'auth.password_changed', user_id=actor_user_id)
        return send_json(handler, 200, {'ok': True})


def handle_get_auth_diagnostics(handler, parsed, payload, match):
    from modules.auth.service import auth_diagnostics
    return send_json(handler, 200, auth_diagnostics())


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


def register_routes(router):
    router.register('GET',  '/api/auth-diagnostics',  handle_get_auth_diagnostics)
    router.register('GET',  '/api/db-pool/status',    handle_get_db_pool_status)
    router.register('GET',  '/api/bootstrap',          handle_get_bootstrap)
    router.register('POST', '/api/login',             handle_post_login)
    router.register('POST', '/api/recover-password',  handle_post_recover_password)
    router.register('POST', '/api/change-password',   handle_post_change_password)
