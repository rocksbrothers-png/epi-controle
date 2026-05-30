"""Rotas de autenticação."""
import traceback
from contextlib import closing

from core.database import get_connection
from epi_backend.http_utils import require_fields, send_json, structured_log
from modules.auth.service import authenticate_login


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


def register_routes(router):
    router.register('POST', '/api/login', handle_post_login)
