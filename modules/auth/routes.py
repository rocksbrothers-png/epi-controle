def handle_login_route(handler, connection, payload, authenticate_login, require_fields, send_json):
    require_fields(payload, ['username', 'password'])
    response_payload, status_code, error_payload = authenticate_login(
        connection,
        payload.get('username', ''),
        payload.get('password', '')
    )
    if error_payload:
        return send_json(handler, status_code, error_payload)
    return send_json(handler, status_code, response_payload)
