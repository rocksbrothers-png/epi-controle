"""Rotas de gestão de usuários."""
import re
from contextlib import closing

from core.auth import ensure_resource_company
from core.database import get_connection
from core.repository import authorize_action
from core.security import resolve_actor_user_id
from epi_backend.http_utils import require_fields, send_json
from modules.auth.service import fetch_users, get_user_by_id
from modules.users.service import create_user, delete_user, update_user

_USER_ID_RE = re.compile(r'^/api/users/(\d+)$')
_EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')


def _sanitize_user(user):
    """Remove campos sensíveis (senha) antes de devolver o usuário ao cliente."""
    if not user:
        return user
    safe = dict(user)
    safe.pop('password', None)
    return safe


def handle_get_users(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed), 'users:view')
        users = fetch_users(connection, actor)
        return send_json(handler, 200, {'users': users})


def handle_get_user(handler, parsed, payload, match):
    user_id = int(match.group(1))
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed), 'users:view')
        user = get_user_by_id(connection, user_id)
        ensure_resource_company(actor, user, 'Usuário')
        return send_json(handler, 200, {'user': _sanitize_user(user)})


def handle_post_users(handler, parsed, payload, match):
    require_fields(payload, ['actor_user_id', 'username', 'full_name', 'role'])
    with closing(get_connection()) as connection:
        create_user(connection, payload)
        return send_json(handler, 201, {'ok': True, 'message': 'Usuário criado com sucesso.'})


def handle_put_user(handler, parsed, payload, match):
    user_id = int(match.group(1))
    require_fields(payload, ['actor_user_id', 'username', 'full_name', 'role'])
    with closing(get_connection()) as connection:
        update_user(connection, user_id, payload)
        return send_json(handler, 200, {'ok': True, 'message': 'Usuário atualizado com sucesso.'})


def handle_delete_user(handler, parsed, payload, match):
    user_id = int(match.group(1))
    actor_user_id = resolve_actor_user_id(handler, parsed)
    with closing(get_connection()) as connection:
        delete_user(connection, user_id, actor_user_id)
        return send_json(handler, 200, {'ok': True})


def handle_put_user_email(handler, parsed, payload, match):
    user_id = int(match.group(1))
    actor_user_id = resolve_actor_user_id(handler, parsed, payload)
    email = str(payload.get('email', '') or '').strip()
    if email and not _EMAIL_RE.match(email):
        raise ValueError('Endereço de e-mail inválido.')
    with closing(get_connection()) as connection:
        from modules.auth.service import require_actor as _req_actor
        actor = _req_actor(connection, actor_user_id)
        if actor['id'] != user_id and actor['role'] != 'master_admin':
            raise PermissionError('Somente o próprio usuário ou Administrador Master pode alterar o e-mail.')
        connection.execute(
            'UPDATE users SET email = ? WHERE id = ?',
            (email if email else None, user_id)
        )
        connection.commit()
        return send_json(handler, 200, {'ok': True})


def register_routes(router):
    router.register('GET',    '/api/users',                handle_get_users)
    router.register('GET',    r'/api/users/(\d+)$',        handle_get_user,       regex=True)
    router.register('POST',   '/api/users',                handle_post_users)
    # Specific routes BEFORE generic (\d+) to avoid re.match prefix collision
    router.register('PUT',    r'/api/users/(\d+)/email$',  handle_put_user_email, regex=True)
    router.register('PUT',    r'/api/users/(\d+)$',        handle_put_user,       regex=True)
    router.register('DELETE', r'/api/users/(\d+)$',        handle_delete_user,    regex=True)
