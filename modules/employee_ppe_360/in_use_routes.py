"""F2.1 HTTP boundary, isolated from the F1 handler and global auth rollout."""
from binascii import Error as Base64Error
from contextlib import closing
from urllib.parse import parse_qs

from core.database import get_connection
from core.db_pool import PoolSaturatedError
from core.repository import require_actor
from core.security import (
    AuthenticationError,
    PasswordChangeRequiredError,
    decode_token_of_type,
    parse_bearer_token,
    require_bearer_actor,
)
from epi_backend.http_utils import send_json, structured_log
from modules.employee_ppe_360.audit import record_in_use
from modules.employee_ppe_360.contract import (
    ContractError,
    resolve_authorized_employee,
    success_envelope,
)
from modules.employee_ppe_360.in_use import (
    InUseError,
    fetch_in_use,
    parse_query,
    require_permissions,
    resolve_scope,
)
from modules.employee_ppe_360.summary import is_deleted

IN_USE_PATH = r'^/api/employees/([^/]+)/ppe-360/in-use$'
MESSAGES = {
    'UNAUTHENTICATED': 'Autenticação por token obrigatória.',
    'FORBIDDEN': 'Perfil sem permissão para esta consulta.',
    'PASSWORD_CHANGE_REQUIRED': 'Alteração de senha obrigatória.',
    'EMPLOYEE_NOT_FOUND': 'Colaborador indisponível no seu escopo.',
    'INVALID_EMPLOYEE_ID': 'Identificador de colaborador inválido.',
    'INVALID_PAGINATION': 'Parâmetros de paginação inválidos.',
    'INVALID_QUERY_PARAM': 'Parâmetro de consulta inválido.',
    'AUDIT_UNAVAILABLE': 'Auditoria indisponível.',
    'INTERNAL_ERROR': 'Não foi possível concluir a consulta.',
}


def _error(handler, status, code):
    send_json(handler, status, {'ok': False, 'error': {'code': code, 'message': MESSAGES[code]}})


def _requested_id(raw):
    return int(raw) if raw.isascii() and raw.isdigit() and len(raw) <= 12 else 0


def _authenticate(handler, parsed):
    try:
        user_id = require_bearer_actor(handler, parsed)
        decode_token_of_type(parse_bearer_token(handler), 'access')
        return user_id
    except (ValueError, TypeError, AttributeError, UnicodeError, Base64Error, OverflowError):
        # Legacy decoders may reject malformed claims/base64 with built-in errors.
        # Normalize only authentication, never a database/domain failure.
        raise InUseError('UNAUTHENTICATED', 401) from None


def _rollback(connection):
    try:
        connection.rollback()
    except Exception:  # noqa: BLE001 - a broken connection is discarded by the existing pool
        structured_log('error', 'employee_ppe_360.in_use', result='error', code='ROLLBACK_FAILED')


def handle_get_in_use(handler, parsed, payload, match):
    # Pool errors deliberately escape to the unchanged P0 dispatcher.
    actor = None
    requested_id = _requested_id(match.group(1))
    page, scope = None, None
    try:
        connection = get_connection()
    except PoolSaturatedError:
        raise
    except Exception:  # noqa: BLE001 - keep the new API envelope on connection failure
        structured_log('error', 'employee_ppe_360.in_use', result='error', code='INTERNAL_ERROR')
        _error(handler, 500, 'INTERNAL_ERROR')
        return
    with closing(connection):
        try:
            user_id = _authenticate(handler, parsed)
            actor = require_actor(connection, user_id)
            require_permissions(actor)
            page = parse_query(parse_qs(parsed.query, keep_blank_values=True))
            if not match.group(1).isascii():
                raise ContractError('INVALID_EMPLOYEE_ID')
            employee = resolve_authorized_employee(connection, actor, match.group(1))
            if is_deleted(connection, employee):
                raise ContractError('EMPLOYEE_NOT_FOUND')
            scope = resolve_scope(connection, actor)
            data, cursor = fetch_in_use(connection, actor, employee, scope, page)
        except AuthenticationError:
            status, code = 401, 'UNAUTHENTICATED'
        except PasswordChangeRequiredError:
            status, code = 403, PasswordChangeRequiredError.CODE
        except PermissionError:
            status, code = 403, 'FORBIDDEN'
        except (ContractError, InUseError) as exc:
            status, code = exc.status, exc.code
        except PoolSaturatedError:
            raise
        except Exception:  # noqa: BLE001 - sanitize the HTTP boundary; rollback below
            _rollback(connection)
            structured_log('error', 'employee_ppe_360.in_use', result='error', code='INTERNAL_ERROR')
            _error(handler, 500, 'INTERNAL_ERROR')
            return
        else:
            try:
                record_in_use(connection, actor, requested_id, code='OK', page=page,
                              scope=scope, count=len(data['items']))
            except Exception:  # noqa: BLE001 - sanitize the HTTP boundary; rollback below
                _rollback(connection)
                structured_log('error', 'employee_ppe_360.in_use', result='error', code='AUDIT_UNAVAILABLE')
                _error(handler, 500, 'AUDIT_UNAVAILABLE')
                return
            send_json(handler, 200, success_envelope(data, limit=page['limit'], next_cursor=cursor))
            return
        _rollback(connection)
        try:
            record_in_use(connection, actor, requested_id, code=code, page=page, scope=scope)
        except Exception:  # noqa: BLE001 - sanitize the HTTP boundary; rollback below
            _rollback(connection)
            structured_log('error', 'employee_ppe_360.in_use', result='error', code='AUDIT_UNAVAILABLE')
            _error(handler, 500, 'AUDIT_UNAVAILABLE')
            return
        _error(handler, status, code)
        return
