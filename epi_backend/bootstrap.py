"""Bootstrap state: tracks DB init lifecycle for the HTTP health gate."""
from __future__ import annotations

import threading

DB_BOOTSTRAP_STATE: dict = {
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
    '/api/recover-password',
    '/api/auth/request-email-recovery',
    # tenant resolution & i18n são públicos e não dependem do bootstrap
    '/api/tenant/resolve',
    '/api/tenant/branding',
    '/api/tenant/slugs',
    '/api/i18n',
})


def _set_bootstrap_state(**values) -> None:
    with DB_BOOTSTRAP_STATE_LOCK:
        DB_BOOTSTRAP_STATE.update(values)


def _get_bootstrap_state() -> dict:
    with DB_BOOTSTRAP_STATE_LOCK:
        return dict(DB_BOOTSTRAP_STATE)


# Texto público da falha de bootstrap. O erro bruto (host, usuário, SQL, DSN)
# continua em DB_BOOTSTRAP_STATE['error_message'] e nos logs internos, mas nunca
# vai para o cliente: o 503 e /health são respondidos antes da autenticação.
PUBLIC_BOOTSTRAP_PENDING = 'A migração/validação de schema ainda não concluiu.'
PUBLIC_BOOTSTRAP_FAILED = (
    'Falha na inicialização ou migração do banco de dados. '
    'Os detalhes técnicos ficam registrados nos logs do servidor.'
)


def public_bootstrap_detail(state: dict) -> str:
    if state.get('ready'):
        return ''
    if state.get('error_code') or state.get('error_message'):
        return PUBLIC_BOOTSTRAP_FAILED
    return PUBLIC_BOOTSTRAP_PENDING


def current_runtime_health() -> dict:
    state = _get_bootstrap_state()
    ready = bool(state.get('ready'))
    has_failure = bool(state.get('error_code'))
    phase = 'ready' if ready else ('failed' if has_failure else 'starting')
    return {
        'status': 'ok',
        'phase': phase,
        'ready': ready,
        'error_code': state.get('error_code') or '',
        'error_kind': state.get('error_kind') or '',
        'error_message': public_bootstrap_detail(state) if has_failure else '',
        'started_at': state.get('started_at') or '',
        'completed_at': state.get('completed_at') or '',
    }


def runtime_probe_response(probe: str = 'ready') -> tuple[int, dict]:
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
