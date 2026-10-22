"""Physical stock eligibility and the tenant's authoritative calendar.

Catalog and CA dates never authorize physical use. Reservations and deliveries
serialize on the same EPI row; locks last until the caller commits/rolls back.
"""

from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from epi_backend.db import _is_sqlite_connection, row_to_dict, table_columns, table_exists
from modules.stock.lifecycle import physical_date, physical_validity

AVAILABLE_STATUSES = frozenset({'in_stock', 'available'})
ON_HAND_STATUSES = AVAILABLE_STATUSES | frozenset({
    'reserved', 'blocked', 'blocked_expired', 'blocked_discard', 'blocked_return',
    'blocked_analysis', 'blocked_rejected', 'blocked_archived', 'quarantine',
    'returned_base', 'maintenance', 'hygiene', 'discard_pending',
})


def validity_policy(connection, company_id, *, now=None):
    row = connection.execute('SELECT * FROM companies WHERE id = ?', (int(company_id),)).fetchone()
    if row is None:
        raise ValueError('Empresa não encontrada para a política de validade.')
    company = row_to_dict(row)
    name = str(company.get('timezone') or 'America/Sao_Paulo')
    try:
        zone = ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise ValueError('Fuso da empresa inválido; regularize antes de operar estoque.') from exc
    instant = now or datetime.now(timezone.utc)
    if instant.tzinfo is None:
        raise ValueError('Instante de referência precisa de fuso horário.')
    days = 30
    if table_exists(connection, 'company_stock_validity_config'):
        config = connection.execute(
            'SELECT warning_days FROM company_stock_validity_config WHERE company_id = ?',
            (int(company_id),),
        ).fetchone()
        if config is not None:
            days = int(config['warning_days'])
    if days < 0:
        raise ValueError('Janela de alerta da empresa inválida.')
    return {'as_of_date': instant.astimezone(zone).date().isoformat(),
            'timezone': name, 'warning_days': days, 'expiry_day_inclusive': True}


def classify_physical(expiry, policy):
    try:
        return physical_validity(expiry, today=policy['as_of_date'], alert_days=policy['warning_days'])
    except ValueError:
        return {'status': 'unknown', 'days_remaining': None, 'eligible_by_validity': False}


def lock_stock_scope(connection, company_id, unit_id, epi_id):
    """A real DB lock shared by reserve, deliver and reservation transitions."""
    if _is_sqlite_connection(connection) and not connection.in_transaction:
        connection.execute('BEGIN IMMEDIATE')
    suffix = '' if _is_sqlite_connection(connection) else ' FOR UPDATE'
    epi = connection.execute(
        'SELECT id FROM epis WHERE id = ? AND company_id = ?' + suffix,
        (int(epi_id), int(company_id)),
    ).fetchone()
    unit = connection.execute('SELECT id FROM units WHERE id = ? AND company_id = ?',
                              (int(unit_id), int(company_id))).fetchone()
    if epi is None or unit is None:
        raise ValueError('Estoque não pertence à empresa/unidade informada.')
    if not _is_sqlite_connection(connection) and table_exists(connection, 'unit_epi_stock'):
        connection.execute('SELECT id FROM unit_epi_stock WHERE company_id=? AND unit_id=? AND epi_id=? FOR UPDATE',
                           (int(company_id), int(unit_id), int(epi_id))).fetchone()


def stock_rows(connection, company_id=None, unit_id=None, epi_id=None):
    if connection is None or not table_exists(connection, 'epi_stock_items'):
        return []
    columns = table_columns(connection, 'epi_stock_items')
    if not {'id', 'company_id', 'unit_id', 'epi_id', 'status', 'qr_code_value'}.issubset(columns):
        return []
    has_expiry = 'physical_expiry_date' in columns
    expiry = 'physical_expiry_date' if has_expiry else 'NULL AS physical_expiry_date'
    sql = 'SELECT id, company_id, unit_id, epi_id, status, qr_code_value, ' + expiry + ' FROM epi_stock_items'
    clauses, params = [], []
    for name, value in [('company_id', company_id), ('unit_id', unit_id), ('epi_id', epi_id)]:
        if value is not None:
            clauses.append(name + ' = ?')
            params.append(int(value))
    if clauses:
        sql += ' WHERE ' + ' AND '.join(clauses)
    rows = [row_to_dict(row) for row in connection.execute(sql, tuple(params)).fetchall()]
    scopes = {}
    for row in rows:
        key = (row['company_id'], row['unit_id'], row['epi_id'])
        if key not in scopes:
            scopes[key] = scope_operational(connection, *key)
        row['scope_operational'] = scopes[key]
    return rows


def scope_operational(connection, company_id, unit_id, epi_id):
    for table, record_id in [('companies', company_id), ('units', unit_id), ('epis', epi_id)]:
        row = connection.execute('SELECT * FROM ' + table + ' WHERE id=?', (int(record_id),)).fetchone()
        if row is None:
            return False
        data = row_to_dict(row)
        if table != 'companies' and int(data.get('company_id', company_id)) != int(company_id):
            return False
        if 'active' in data and data['active'] not in (1, True, '1'):
            return False
        if data.get('archived_at') or data.get('is_archived') in (1, True, '1'):
            return False
    from modules.units.service import ensure_unit_operational
    try:
        ensure_unit_operational(connection, unit_id, 'reservas e entregas')
    except ValueError:
        return False
    return True


def eligible_piece(row, policy):
    return (row.get('scope_operational', True)
            and str(row.get('status') or '').lower() in AVAILABLE_STATUSES
            and bool(str(row.get('qr_code_value') or '').strip())
            and classify_physical(row.get('physical_expiry_date'), policy)['eligible_by_validity'])


def eligible_quantity(connection, company_id, unit_id, epi_id, *, policy=None):
    policy = policy or validity_policy(connection, company_id)
    return sum(eligible_piece(row, policy) for row in stock_rows(connection, company_id, unit_id, epi_id))


def physical_summary_map(connection, company_id=None, unit_id=None):
    policies, result = {}, {}
    for row in stock_rows(connection, company_id, unit_id):
        status = str(row.get('status') or '').lower()
        if status not in ON_HAND_STATUSES:
            continue
        cid, eid = int(row['company_id']), int(row['epi_id'])
        if cid not in policies:
            policies[cid] = validity_policy(connection, cid)
        policy = policies[cid]
        summary = result.setdefault(eid, empty_summary(policy))
        validity = classify_physical(row.get('physical_expiry_date'), policy)
        summary['physical_pieces'] += 1
        summary[validity['status']] += 1
        if status not in AVAILABLE_STATUSES or validity['status'] == 'expired':
            summary['blocked_pieces'] += 1
        if eligible_piece(row, policy):
            summary['eligible_pieces'] += 1
        # A date summary is information, never individual eligibility.
        if validity['status'] != 'unknown' and status in AVAILABLE_STATUSES:
            day = physical_date(row['physical_expiry_date']).isoformat()
            previous = summary['nearest_known_expiry']
            summary['nearest_known_expiry'] = min(day, previous) if previous else day
        kinds = [key for key in ('valid', 'expiring', 'expired', 'unknown') if summary[key]]
        summary['status'] = 'mixed' if len(kinds) > 1 else kinds[0]
    return result


def empty_summary(policy):
    return dict(policy, count_unit='physical_pieces', status='empty', physical_pieces=0,
                eligible_pieces=0, blocked_pieces=0, valid=0, expiring=0, expired=0,
                unknown=0, nearest_known_expiry=None)
