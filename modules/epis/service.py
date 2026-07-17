import json
from epi_backend.db import row_to_dict
from modules.units.service import get_unit_by_id, get_unit_active_jv_name
from core.auth import ensure_resource_company

MSG_JOINVENTURE_INVALID = 'JoinVenture inválida.'
EPI_ALL_UNITS_VALUE = 'ALL'


def create_epi(connection, payload, *, authorize_action, resolve_actor_user_id, require_structural_admin, next_company_qr_sequence, build_master_epi_qr, parse_epi_joinventures, normalize_active_joinventure_name, resolve_epi_scope_unit, resolve_epi_scope_metadata, validate_epi_uniqueness, parse_int_flexible, upsert_unit_stock):
    actor = authorize_action(connection, resolve_actor_user_id(), 'epis:create', int(payload['company_id']))
    require_structural_admin(actor)
    master_sequence = next_company_qr_sequence(connection, int(payload['company_id']))
    qr_code_value = str(payload.get('qr_code_value') or build_master_epi_qr(int(payload['company_id']), master_sequence)).strip()
    initial_stock = int(payload.get('stock') or 0)
    joinventures_values = parse_epi_joinventures(payload.get('joinventures_json'))
    active_joinventure = normalize_active_joinventure_name(payload.get('active_joinventure'))
    resolved_unit_id = resolve_epi_scope_unit(connection, actor, payload, joinventures_values, active_joinventure)
    if resolved_unit_id:
        from modules.units.service import ensure_unit_operational
        ensure_unit_operational(connection, resolved_unit_id, 'novos EPIs')
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


def parse_epi_joinventures(raw_value):
    try:
        parsed = json.loads(str(raw_value or '[]'))
    except Exception:
        raise ValueError(MSG_JOINVENTURE_INVALID)
    if not isinstance(parsed, list):
        raise ValueError(MSG_JOINVENTURE_INVALID)
    normalized = []
    for entry in parsed:
        if isinstance(entry, str):
            name = entry.strip()
            unit_id = None
            if '@@' in name:
                name_part, unit_part = name.split('@@', 1)
                name = str(name_part or '').strip()
                unit_id = int(unit_part) if str(unit_part or '').strip().isdigit() else None
            if not name:
                continue
            normalized.append({'name': name, 'unit_id': unit_id})
            continue
        if not isinstance(entry, dict):
            raise ValueError('JoinVenture inválida.')
        name = str(entry.get('name', '')).strip()
        if not name:
            continue
        raw_unit_id = entry.get('unit_id')
        unit_id = None if raw_unit_id in (None, '') else int(raw_unit_id)
        normalized.append({'name': name, 'unit_id': unit_id})
    return normalized


def normalize_active_joinventure_name(value):
    raw = str(value or '').strip()
    if '@@' in raw:
        raw = raw.split('@@', 1)[0]
    return raw.strip()


def parse_epi_scope_unit_id(raw_unit_value):
    raw_unit = str(raw_unit_value or '').strip()
    if raw_unit in ('', EPI_ALL_UNITS_VALUE):
        return None
    return int(raw_unit)


def resolve_epi_scope_metadata(unit_id, active_joinventure):
    normalized_jv = normalize_active_joinventure_name(active_joinventure)
    if normalized_jv:
        return 'JOINT_VENTURE', 1
    if unit_id:
        return 'UNIT', 0
    return 'GLOBAL', 0


def epi_context_signature(unit_id, active_joinventure):
    normalized_unit = int(unit_id) if unit_id else 0
    normalized_jv = str(active_joinventure or '').strip().lower()
    if not normalized_unit and not normalized_jv:
        return 'global'
    return f'unit:{normalized_unit}|jv:{normalized_jv}'


def resolve_epi_scope_unit(connection, actor, payload, joinventures_values, active_joinventure):
    requested_company_id = int(payload['company_id'])
    requested_unit_id = parse_epi_scope_unit_id(payload.get('unit_id'))
    if requested_unit_id:
        unit = get_unit_by_id(connection, requested_unit_id)
        ensure_resource_company(actor, unit, 'Unidade')
        if int(unit['company_id']) != requested_company_id:
            raise ValueError('Unidade e empresa do EPI precisam ser compatíveis.')
    normalized_active = normalize_active_joinventure_name(active_joinventure)
    if normalized_active:
        matching = [entry for entry in joinventures_values if str(entry['name']).strip().lower() == normalized_active.lower()]
        if not matching:
            raise ValueError('JoinVenture Ativa ou Unidade Única Ativa precisa existir na lista de JoinVentures.')
        unit_ids = sorted({entry.get('unit_id') for entry in matching if entry.get('unit_id')})
        if not unit_ids:
            if requested_unit_id:
                unit_ids = [requested_unit_id]
            else:
                raise ValueError('JoinVenture Ativa ou Unidade Única Ativa precisa possuir unidade vinculada.')
        if len(unit_ids) > 1:
            raise ValueError('JoinVenture Ativa ou Unidade Única Ativa está vinculada a múltiplas unidades. Ajuste o cadastro.')
        required_unit_id = int(unit_ids[0])
        required_unit = get_unit_by_id(connection, required_unit_id)
        ensure_resource_company(actor, required_unit, 'Unidade')
        if int(required_unit['company_id']) != requested_company_id:
            raise ValueError('JoinVenture e empresa do EPI precisam ser compatíveis.')
        if requested_unit_id and requested_unit_id != required_unit_id:
            raise ValueError('Unidade incompatível com a JoinVenture Ativa ou Unidade Única Ativa.')
        return required_unit_id
    return requested_unit_id


def validate_epi_uniqueness(connection, company_id, unit_id, active_joinventure, name, purchase_code, exclude_id=None):
    normalized_name = str(name or '').strip()
    normalized_code = str(purchase_code or '').strip()
    if not normalized_name:
        raise ValueError('Nome completo do EPI é obrigatório.')
    if not normalized_code:
        raise ValueError('Código do EPI é obrigatório.')

    params = [int(company_id), normalized_name.lower()]
    sql = 'SELECT id, unit_id, active_joinventure FROM epis WHERE company_id = ? AND LOWER(TRIM(name)) = ?'
    if exclude_id:
        sql += ' AND id <> ?'
        params.append(int(exclude_id))
    name_matches = connection.execute(sql, tuple(params)).fetchall()
    incoming_scope = epi_context_signature(unit_id, active_joinventure)
    for row in name_matches:
        if epi_context_signature(row['unit_id'], row['active_joinventure']) == incoming_scope:
            raise ValueError('Já existe EPI com o mesmo Nome completo neste contexto (empresa/unidade/Joint Venture).')

    code_params = [int(company_id), normalized_code.lower()]
    code_sql = 'SELECT id FROM epis WHERE company_id = ? AND LOWER(TRIM(purchase_code)) = ?'
    if exclude_id:
        code_sql += ' AND id <> ?'
        code_params.append(int(exclude_id))
    code_match = connection.execute(code_sql + ' LIMIT 1', tuple(code_params)).fetchone()
    if code_match:
        raise ValueError('Código do EPI já cadastrado nesta empresa.')


def get_epi_by_id(connection, epi_id):
    row = connection.execute(
        'SELECT id, company_id, unit_id, name, purchase_code, ca, sector, epi_section, '
        'stock, minimum_stock, unit_measure, ca_expiry, epi_validity_date, '
        'manufacture_date, validity_days, validity_years, validity_months, '
        'manufacturer_validity_months, default_replacement_days, '
        'manufacturer, model_reference, supplier_company, manufacturer_recommendations, '
        'epi_photo_data, glove_size, size, uniform_size, joinventures_json, '
        'active_joinventure, scope_type, is_joint_venture, qr_code_value '
        'FROM epis WHERE id = ?',
        (epi_id,),
    ).fetchone()
    return row_to_dict(row) if row else None


def fetch_epis(connection, actor=None, unit_id=None, *, name=None, section=None, manufacturer=None, ca=None, protection=None):
    sql = (
        'SELECT epis.id, epis.company_id, epis.unit_id, epis.name, epis.purchase_code, epis.ca, epis.sector, epis.epi_section, '
        'epis.active, '
        'COALESCE(('
        'SELECT SUM(unit_epi_stock.quantity) FROM unit_epi_stock '
        'WHERE unit_epi_stock.company_id = epis.company_id AND unit_epi_stock.epi_id = epis.id'
        '), epis.stock, 0) AS stock, '
        'epis.minimum_stock, epis.unit_measure, epis.ca_expiry, epis.epi_validity_date, '
        'epis.manufacture_date, epis.validity_days, epis.validity_years, epis.validity_months, epis.manufacturer_validity_months, epis.default_replacement_days, '
        'epis.manufacturer, epis.model_reference, epis.supplier_company, epis.manufacturer_recommendations, epis.epi_photo_data, '
        'epis.glove_size, epis.size, epis.uniform_size, '
        'epis.joinventures_json, epis.active_joinventure, '
        'epis.scope_type, epis.is_joint_venture, '
        'epis.qr_code_value, epis.epi_master_sequence, '
        'companies.name AS company_name, companies.cnpj AS company_cnpj, companies.logo_type, units.name AS unit_name, units.unit_type '
        'FROM epis JOIN companies ON companies.id = epis.company_id LEFT JOIN units ON units.id = epis.unit_id'
    )
    clauses = []
    params = []
    from core.archival import NON_OPERATIONAL_STATUSES, lifecycle_enabled
    if lifecycle_enabled(connection, 'epis'):
        placeholders = ', '.join(['?'] * len(NON_OPERATIONAL_STATUSES))
        clauses.append(f'epis.status NOT IN ({placeholders})')
        params.extend(NON_OPERATIONAL_STATUSES)
    if actor and actor['role'] != 'master_admin':
        clauses.append('epis.company_id = ?')
        params.append(actor['company_id'])
    if unit_id:
        clauses.append('(epis.unit_id = ? OR epis.unit_id IS NULL)')
        params.append(int(unit_id))
    if name:
        clauses.append('LOWER(epis.name) LIKE ?')
        params.append(f'%{name.lower()}%')
    if section:
        clauses.append('LOWER(COALESCE(epis.epi_section, \'\')) LIKE ?')
        params.append(f'%{section.lower()}%')
    if manufacturer:
        clauses.append('LOWER(COALESCE(epis.manufacturer, \'\')) LIKE ?')
        params.append(f'%{manufacturer.lower()}%')
    if ca:
        clauses.append('LOWER(COALESCE(epis.ca, \'\')) LIKE ?')
        params.append(f'%{ca.lower()}%')
    if protection:
        clauses.append('LOWER(COALESCE(epis.sector, \'\')) LIKE ?')
        params.append(f'%{protection.lower()}%')
    where_sql = f" WHERE {' AND '.join(clauses)}" if clauses else ''
    rows = connection.execute(sql + where_sql + ' ORDER BY companies.name, epis.name', tuple(params)).fetchall()
    items = []
    for row in rows:
        item = row_to_dict(row)
        scope_type = str(item.get('scope_type') or '').strip().upper()
        if scope_type not in {'GLOBAL', 'UNIT', 'JOINT_VENTURE'}:
            scope_type, is_jv = resolve_epi_scope_metadata(item.get('unit_id'), item.get('active_joinventure'))
            item['scope_type'] = scope_type
            item['is_joint_venture'] = is_jv
        if not item.get('unit_name') and str(item.get('scope_type') or '').upper() == 'GLOBAL':
            item['unit_name'] = 'Todas as Unidades'
        item['scope_label'] = (
            'Todas as Unidades'
            if str(item.get('scope_type') or '').upper() == 'GLOBAL'
            else f"{item.get('unit_name') or '-'}{' (Joint Venture)' if int(item.get('is_joint_venture') or 0) == 1 else ''}"
        )
        items.append(item)
    return items


# ── Route-level SQL extractions ───────────────────────────────────────────────

def get_epi_replacement_days(connection, epi_id):
    row = connection.execute(
        'SELECT default_replacement_days, manufacturer_validity_months FROM epis WHERE id = ?',
        (int(epi_id),),
    ).fetchone()
    return dict(row) if row else None


# ── Arquivamento (Soft Delete) com retenção — mesma política das Unidades ────

def get_epi_lifecycle(connection, epi_id):
    """EPI com os campos de ciclo de vida (para fluxos de arquivo)."""
    from core.archival import LIFECYCLE_FIELD_NAMES, lifecycle_enabled
    extra = (', ' + ', '.join(LIFECYCLE_FIELD_NAMES)) if lifecycle_enabled(connection, 'epis') else ''
    row = connection.execute(
        f'SELECT id, company_id, unit_id, name, purchase_code, ca{extra} FROM epis WHERE id = ?',
        (int(epi_id),),
    ).fetchone()
    return row_to_dict(row) if row else None


def ensure_epi_operational(connection, epi_id, operation='esta operação'):
    from core.archival import ensure_record_operational
    ensure_record_operational(connection, 'epis', epi_id, 'EPI', operation)


def fetch_archived_epis(connection, actor):
    """EPIs arquivados do tenant, com dados de retenção para a UI."""
    from core.archival import STATUS_ARCHIVED, STATUS_PENDING_DELETION, retention_days_remaining
    sql = (
        'SELECT epis.id, epis.company_id, epis.unit_id, epis.name, epis.purchase_code, '
        'epis.ca, epis.sector, epis.status, epis.archived_at, epis.archived_by, '
        'epis.archive_reason, epis.retention_until, epis.legal_hold, '
        'companies.name AS company_name, units.name AS unit_name, '
        'users.full_name AS archived_by_name '
        'FROM epis '
        'JOIN companies ON companies.id = epis.company_id '
        'LEFT JOIN units ON units.id = epis.unit_id '
        'LEFT JOIN users ON users.id = epis.archived_by '
        'WHERE epis.status IN (?, ?)'
    )
    params = [STATUS_ARCHIVED, STATUS_PENDING_DELETION]
    if actor and actor['role'] != 'master_admin':
        sql += ' AND epis.company_id = ?'
        params.append(actor['company_id'])
    rows = connection.execute(sql + ' ORDER BY epis.archived_at DESC', tuple(params)).fetchall()
    result = []
    for row in rows:
        item = row_to_dict(row)
        item['retention_days_remaining'] = retention_days_remaining(item.get('retention_until'))
        result.append(item)
    return result


def summarize_epi_history(connection, epi_id):
    """Resumo do que será removido na exclusão definitiva do EPI."""
    from core.archival import count_where
    epi_id = int(epi_id)
    return {
        'deliveries': count_where(connection, 'deliveries', 'epi_id = ?', (epi_id,)),
        'devolutions': count_where(connection, 'epi_devolutions', 'epi_id = ?', (epi_id,)),
        'stock_items': count_where(connection, 'epi_stock_items', 'epi_id = ?', (epi_id,)),
        'stock_movements': count_where(connection, 'stock_movements', 'epi_id = ?', (epi_id,)),
        'epi_requests': count_where(connection, 'epi_requests', 'epi_id = ?', (epi_id,)),
        'feedbacks': count_where(connection, 'epi_feedbacks', 'epi_id = ?', (epi_id,)),
        'ficha_items': count_where(connection, 'epi_ficha_items', 'epi_id = ?', (epi_id,)),
        'purchase_request_items': count_where(connection, 'purchase_request_items', 'epi_id = ?', (epi_id,)),
        'purchase_order_items': count_where(connection, 'purchase_order_items', 'epi_id = ?', (epi_id,)),
    }


def purge_epi_history(connection, epi_id):
    """Expurga os dados operacionais do EPI (tombstone permanece).

    Mesma cascata da exclusão legada (delete_epi_dependencies), porém sem
    remover a linha de epis — o registro vira tombstone com status='deleted'.
    """
    from core.archival import delete_where
    epi_id = int(epi_id)
    delete_where(
        connection, 'epi_stock_item_reprints',
        'stock_item_id IN (SELECT id FROM epi_stock_items WHERE epi_id = ?)', (epi_id,)
    )
    request_ids = [
        int(row['id'])
        for row in connection.execute('SELECT id FROM epi_requests WHERE epi_id = ?', (epi_id,)).fetchall()
    ]
    if request_ids:
        placeholders = ','.join(['?'] * len(request_ids))
        delete_where(connection, 'epi_request_history', f'request_id IN ({placeholders})', tuple(request_ids))
    feedback_ids = [
        int(row['id'])
        for row in connection.execute('SELECT id FROM epi_feedbacks WHERE epi_id = ?', (epi_id,)).fetchall()
    ]
    if feedback_ids:
        placeholders = ','.join(['?'] * len(feedback_ids))
        delete_where(connection, 'epi_feedback_history', f'feedback_id IN ({placeholders})', tuple(feedback_ids))
    for table in (
        'epi_stock_items', 'stock_movements', 'unit_epi_stock', 'epi_ficha_items',
        'deliveries', 'epi_devolutions', 'epi_requests', 'epi_feedbacks',
    ):
        delete_where(connection, table, 'epi_id = ?', (epi_id,))
