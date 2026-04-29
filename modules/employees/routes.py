def handle_create_employee_route(handler, connection, payload, *, require_fields, send_json, create_employee):
    require_fields(payload, ['actor_user_id', 'company_id', 'employee_id_code', 'cpf', 'name', 'sector', 'role_name', 'admission_date', 'schedule_type'])
    employee_id = create_employee(connection, payload)
    return send_json(handler, 201, {'ok': True, 'id': employee_id})


def handle_update_employee_route(handler, connection, parsed, payload, *, require_fields, send_json, update_employee):
    employee_id = int(parsed.path.rsplit('/', 1)[-1].split('?')[0])
    require_fields(payload, ['actor_user_id', 'company_id', 'unit_id', 'employee_id_code', 'cpf', 'name', 'sector', 'role_name', 'admission_date', 'schedule_type'])
    update_employee(connection, employee_id, payload)
    return send_json(handler, 200, {'ok': True})
