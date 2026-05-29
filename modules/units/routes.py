"""Handlers de rotas de unidades operacionais."""


def handle_create_unit_route(handler, connection, payload, *, authorize_action, send_json, require_fields):
    require_fields(payload, ['company_id', 'name'])
    actor = authorize_action(connection, None, 'units:create', int(payload['company_id']))
    name = str(payload.get('name', '')).strip()
    unit_type = str(payload.get('unit_type', '')).strip()
    city = str(payload.get('city', '')).strip()
    notes = str(payload.get('notes', '')).strip()
    cursor = connection.execute(
        'INSERT INTO units (company_id, name, unit_type, city, notes) VALUES (%s, %s, %s, %s, %s)',
        (int(actor['company_id'] if actor['role'] != 'master_admin' else payload['company_id']),
         name, unit_type, city, notes),
    )
    connection.commit()
    return send_json(handler, 201, {'id': int(cursor.lastrowid), 'ok': True})


def handle_update_unit_route(handler, connection, unit_id, payload, *, authorize_action, get_unit_by_id,
                              ensure_resource_company, send_json):
    actor = authorize_action(connection, None, 'units:update')
    unit = get_unit_by_id(connection, int(unit_id))
    if not unit:
        return send_json(handler, 404, {'error': 'Unidade não encontrada.'})
    ensure_resource_company(actor, unit, 'Unidade')
    name = str(payload.get('name', unit['name'])).strip()
    unit_type = str(payload.get('unit_type', unit.get('unit_type', ''))).strip()
    city = str(payload.get('city', unit.get('city', ''))).strip()
    notes = str(payload.get('notes', unit.get('notes', ''))).strip()
    connection.execute(
        'UPDATE units SET name = %s, unit_type = %s, city = %s, notes = %s WHERE id = %s',
        (name, unit_type, city, notes, int(unit_id)),
    )
    connection.commit()
    return send_json(handler, 200, {'ok': True})


def handle_delete_unit_route(handler, connection, unit_id, *, authorize_action, get_unit_by_id,
                               ensure_resource_company, delete_unit_dependencies, send_json):
    actor = authorize_action(connection, None, 'units:delete')
    unit = get_unit_by_id(connection, int(unit_id))
    if not unit:
        return send_json(handler, 404, {'error': 'Unidade não encontrada.'})
    ensure_resource_company(actor, unit, 'Unidade')
    delete_unit_dependencies(connection, int(unit_id))
    connection.execute('DELETE FROM units WHERE id = %s', (int(unit_id),))
    connection.commit()
    return send_json(handler, 200, {'ok': True})
