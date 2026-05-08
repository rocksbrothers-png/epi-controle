def handle_create_company_route(handler, connection, payload, *, require_fields, send_json, create_company):
    require_fields(payload, ['actor_user_id', 'name', 'legal_name', 'cnpj', 'plan_name', 'user_limit', 'license_status', 'active'])
    company_id = create_company(connection, payload)
    return send_json(handler, 201, {'ok': True, 'id': company_id})

def handle_update_company_route(handler, connection, parsed, payload, *, require_fields, send_json, update_company):
    company_id = int(parsed.path.rsplit('/', 1)[-1])
    require_fields(payload, ['actor_user_id', 'name', 'legal_name', 'cnpj', 'plan_name', 'user_limit', 'license_status', 'active'])
    update_company(connection, company_id, payload)
    return send_json(handler, 200, {'ok': True})

def handle_company_block_status_route(handler, connection, parsed, payload, *, send_json, handle_block_status):
    status = handle_block_status(connection, parsed, payload)
    return send_json(handler, 200, status)
