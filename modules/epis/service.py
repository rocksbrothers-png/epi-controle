import json

def create_epi(connection, payload, *, authorize_action, resolve_actor_user_id, require_structural_admin, next_company_qr_sequence, build_master_epi_qr, parse_epi_joinventures, normalize_active_joinventure_name, resolve_epi_scope_unit, resolve_epi_scope_metadata, validate_epi_uniqueness, parse_int_flexible, upsert_unit_stock):
    actor = authorize_action(connection, resolve_actor_user_id(), 'epis:create', int(payload['company_id']))
    require_structural_admin(actor)
    master_sequence = next_company_qr_sequence(connection, int(payload['company_id']))
    qr_code_value = str(payload.get('qr_code_value') or build_master_epi_qr(int(payload['company_id']), master_sequence)).strip()
    initial_stock = int(payload.get('stock') or 0)
    joinventures_values = parse_epi_joinventures(payload.get('joinventures_json'))
    active_joinventure = normalize_active_joinventure_name(payload.get('active_joinventure'))
    resolved_unit_id = resolve_epi_scope_unit(connection, actor, payload, joinventures_values, active_joinventure)
    scope_type, is_joint_venture = resolve_epi_scope_metadata(resolved_unit_id, active_joinventure)
    validate_epi_uniqueness(connection, payload['company_id'], resolved_unit_id, active_joinventure, payload.get('name'), payload.get('purchase_code'))
    cursor = connection.execute(('INSERT INTO epis (company_id, unit_id, name, purchase_code, ca, sector, epi_section, stock, unit_measure, ca_expiry, epi_validity_date, manufacture_date, validity_days, validity_years, validity_months, manufacturer_validity_months, default_replacement_days, manufacturer, model_reference, supplier_company, manufacturer_recommendations, epi_photo_data, glove_size, size, uniform_size, joinventures_json, active_joinventure, scope_type, is_joint_venture, qr_code_value, epi_master_sequence) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'), (payload['company_id'], resolved_unit_id, payload['name'], payload['purchase_code'], payload['ca'], payload['sector'], str(payload.get('epi_section', '')).strip(), initial_stock, payload['unit_measure'], payload['ca_expiry'], payload['epi_validity_date'], '', parse_int_flexible(payload.get('validity_days'), 0), parse_int_flexible(payload.get('validity_years'), 0), parse_int_flexible(payload.get('validity_months'), 0), parse_int_flexible(payload.get('manufacturer_validity_months'), 0), parse_int_flexible(payload.get('default_replacement_days'), 0) or None, str(payload.get('manufacturer', '')).strip(), str(payload.get('model_reference', '')).strip(), str(payload.get('supplier_company', '')).strip(), str(payload.get('manufacturer_recommendations', '')).strip(), str(payload.get('epi_photo_data') or '').strip() or None, str(payload.get('glove_size') or 'N/A').strip() or 'N/A', str(payload.get('size') or 'N/A').strip() or 'N/A', str(payload.get('uniform_size') or 'N/A').strip() or 'N/A', json.dumps(joinventures_values, ensure_ascii=False), active_joinventure or None, scope_type, int(is_joint_venture), qr_code_value, master_sequence))
    if resolved_unit_id:
        upsert_unit_stock(connection, int(payload['company_id']), int(resolved_unit_id), int(cursor.lastrowid), initial_stock)
    connection.commit()
    return int(cursor.lastrowid)


def update_epi(connection, epi_id, payload, *, authorize_action, resolve_actor_user_id, require_structural_admin, get_epi_by_id, ensure_resource_company, generate_epi_qr_code, parse_epi_joinventures, normalize_active_joinventure_name, resolve_epi_scope_unit, resolve_epi_scope_metadata, validate_epi_uniqueness, parse_int_flexible, sync_epi_scope_stock_unit):
    actor = authorize_action(connection, resolve_actor_user_id(), 'epis:update', int(payload['company_id']))
    require_structural_admin(actor)
    current = get_epi_by_id(connection, epi_id)
    ensure_resource_company(actor, current, 'EPI')
    qr_code_value = str(payload.get('qr_code_value') or generate_epi_qr_code(payload)).strip()
    joinventures_values = parse_epi_joinventures(payload.get('joinventures_json'))
    active_joinventure = normalize_active_joinventure_name(payload.get('active_joinventure'))
    resolved_unit_id = resolve_epi_scope_unit(connection, actor, payload, joinventures_values, active_joinventure)
    scope_type, is_joint_venture = resolve_epi_scope_metadata(resolved_unit_id, active_joinventure)
    validate_epi_uniqueness(connection, payload['company_id'], resolved_unit_id, active_joinventure, payload.get('name'), payload.get('purchase_code'), exclude_id=epi_id)
    connection.execute(('UPDATE epis SET company_id = ?, unit_id = ?, name = ?, purchase_code = ?, ca = ?, sector = ?, epi_section = ?, stock = ?, unit_measure = ?, ca_expiry = ?, epi_validity_date = ?, manufacture_date = ?, validity_days = ?, validity_years = ?, validity_months = ?, manufacturer_validity_months = ?, default_replacement_days = ?, manufacturer = ?, model_reference = ?, supplier_company = ?, manufacturer_recommendations = ?, epi_photo_data = ?, glove_size = ?, size = ?, uniform_size = ?, joinventures_json = ?, active_joinventure = ?, scope_type = ?, is_joint_venture = ?, qr_code_value = ? WHERE id = ?'), (payload['company_id'], resolved_unit_id, payload['name'], payload['purchase_code'], payload['ca'], payload['sector'], str(payload.get('epi_section', '')).strip(), int(payload.get('stock') or 0), payload['unit_measure'], payload['ca_expiry'], payload['epi_validity_date'], current.get('manufacture_date') or '', parse_int_flexible(payload.get('validity_days'), 0), parse_int_flexible(payload.get('validity_years'), 0), parse_int_flexible(payload.get('validity_months'), 0), parse_int_flexible(payload.get('manufacturer_validity_months'), 0), parse_int_flexible(payload.get('default_replacement_days'), current.get('default_replacement_days') or 0) or None, str(payload.get('manufacturer', '')).strip(), str(payload.get('model_reference', '')).strip(), str(payload.get('supplier_company', '')).strip(), str(payload.get('manufacturer_recommendations', '')).strip(), (str(payload.get('epi_photo_data', current.get('epi_photo_data') or '')).strip() or None if 'epi_photo_data' in payload else current.get('epi_photo_data')), str(payload.get('glove_size') or current.get('glove_size') or 'N/A').strip() or 'N/A', str(payload.get('size') or current.get('size') or 'N/A').strip() or 'N/A', str(payload.get('uniform_size') or current.get('uniform_size') or 'N/A').strip() or 'N/A', json.dumps(joinventures_values, ensure_ascii=False), active_joinventure or None, scope_type, int(is_joint_venture), qr_code_value, epi_id))
    sync_epi_scope_stock_unit(connection, int(payload['company_id']), int(epi_id), current.get('unit_id'), resolved_unit_id)
    connection.commit()
