def handle_create_user_route(handler, connection, payload, *, require_fields, send_json, create_user):
    require_fields(payload, ['actor_user_id', 'username', 'full_name', 'role', 'password'])
    create_user(connection, payload)
    return send_json(handler, 201, {'ok': True, 'message': 'Usuário criado com sucesso.'})


def handle_update_user_route(handler, connection, parsed, payload, *, require_fields, send_json, update_user):
    user_id = int(parsed.path.rsplit('/', 1)[-1].split('?')[0])
    require_fields(payload, ['actor_user_id', 'username', 'full_name', 'role'])
    update_user(connection, user_id, payload)
    return send_json(handler, 200, {'ok': True, 'message': 'Usuário atualizado com sucesso.'})


def handle_delete_user_route(handler, connection, parsed, *, send_json, delete_user):
    user_id = int(parsed.path.rsplit('/', 1)[-1].split('?')[0])
    delete_user(connection, user_id)
    return send_json(handler, 200, {'ok': True})
