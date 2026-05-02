def handle_create_epi_route(handler, connection, payload, *, require_fields, send_json, create_epi):
    require_fields(payload, ['actor_user_id', 'company_id', 'name', 'purchase_code', 'ca', 'sector', 'epi_section', 'model_reference', 'manufacturer', 'supplier_company', 'unit_measure', 'ca_expiry', 'epi_validity_date', 'manufacturer_validity_months'])
    epi_id = create_epi(connection, payload)
    return send_json(handler, 201, {'ok': True, 'id': epi_id})


def handle_update_epi_route(handler, connection, parsed, payload, *, require_fields, send_json, update_epi):
    epi_id = int(parsed.path.rsplit('/', 1)[-1].split('?')[0])
    require_fields(payload, ['actor_user_id', 'company_id', 'name', 'purchase_code', 'ca', 'sector', 'epi_section', 'model_reference', 'manufacturer', 'supplier_company', 'unit_measure', 'ca_expiry', 'epi_validity_date', 'manufacturer_validity_months'])
    update_epi(connection, epi_id, payload)
    return send_json(handler, 200, {'ok': True})
