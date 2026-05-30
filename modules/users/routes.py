"""Rotas de gestão de usuários."""
import re
from contextlib import closing

from core.database import get_connection
from core.security import resolve_actor_user_id
from epi_backend.http_utils import require_fields, send_json
from modules.users.service import create_user, delete_user, update_user

_USER_ID_RE = re.compile(r'^/api/users/(\d+)$')


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


def register_routes(router):
    router.register('POST',   '/api/users',          handle_post_users)
    router.register('PUT',    r'/api/users/(\d+)',   handle_put_user,    regex=True)
    router.register('DELETE', r'/api/users/(\d+)',   handle_delete_user, regex=True)
