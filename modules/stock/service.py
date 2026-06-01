"""Serviços de gestão de estoque de EPIs."""

import json
import re
import unicodedata
from datetime import datetime, timezone

from epi_backend.config import DATABASE_URL, DB_CONNECTOR_AVAILABLE
from epi_backend.db import row_to_dict

UTC = timezone.utc


def generate_epi_qr_code(payload):
    purchase_code = str(payload.get('purchase_code', '')).strip().upper().replace(' ', '-')
    return f"EPI-{payload.get('company_id')}-{payload.get('unit_id')}-{purchase_code}"


def next_company_qr_sequence(connection, company_id):
    if DB_CONNECTOR_AVAILABLE and DATABASE_URL:
        row = connection.execute(
            '''
            INSERT INTO epi_qr_sequences (company_id, last_value)
            VALUES (?, 1)
            ON CONFLICT (company_id)
            DO UPDATE SET last_value = epi_qr_sequences.last_value + 1
            RETURNING last_value
            ''',
            (company_id,)
        ).fetchone()
        return int(row['last_value'])
    current = connection.execute('SELECT last_value FROM epi_qr_sequences WHERE company_id = ?', (company_id,)).fetchone()
    if not current:
        connection.execute('INSERT INTO epi_qr_sequences (company_id, last_value) VALUES (?, ?)', (company_id, 1))
        return 1
    next_value = int(current['last_value']) + 1
    connection.execute('UPDATE epi_qr_sequences SET last_value = ? WHERE company_id = ?', (next_value, company_id))
    return next_value


def build_master_epi_qr(company_id, sequence_value):
    return f"EPI-MASTER-{int(company_id):04d}-{int(sequence_value):08d}"


def build_stock_item_qr(company_id, unit_id, sequence_value):
    return f"EPI-ITEM-{int(company_id):04d}-{int(unit_id):04d}-{int(sequence_value):08d}"


def parse_int_flexible(value, default=0):
    raw = str(value or '').strip()
    if not raw:
        return int(default)
    digits = ''.join(ch for ch in raw if ch.isdigit() or ch == '-')
    if not digits:
        return int(default)
    try:
        return int(digits)
    except ValueError:
        return int(default)


def parse_stock_qr_lookup_value(raw_value):
    text = str(raw_value or '').strip()
    if not text:
        return {'raw': '', 'stock_item_id': None, 'qr_code_value': None, 'format': 'empty'}
    normalized = unicodedata.normalize('NFKC', text)
    if normalized.startswith('{') and normalized.endswith('}'):
        try:
            payload = json.loads(normalized)
        except (TypeError, ValueError):
            payload = None
        payload_type = str((payload or {}).get('type') or '').strip().lower()
        if payload_type in ('stock_item', 'epi_stock_item', 'stockitem'):
            parsed_id = parse_int_flexible((payload or {}).get('id'), 0) or 0
            parsed_code = str((payload or {}).get('code') or (payload or {}).get('qr_code_value') or '').strip()
            return {
                'raw': text,
                'stock_item_id': int(parsed_id) if int(parsed_id) > 0 else None,
                'qr_code_value': parsed_code if parsed_code else None,
                'format': 'json'
            }
    simple_match = re.match(r'^EPIITEM\s*:\s*(\d+)$', normalized, flags=re.IGNORECASE)
    if simple_match:
        return {
            'raw': text,
            'stock_item_id': int(simple_match.group(1)),
            'qr_code_value': None,
            'format': 'simple'
        }
    stock_label_match = re.match(r'^EPI-ITEM-(\d{4})-(\d{4})-(\d{8})$', normalized, flags=re.IGNORECASE)
    if stock_label_match:
        return {
            'raw': text,
            'stock_item_id': None,
            'qr_code_value': normalized,
            'format': 'stock-label'
        }
    return {
        'raw': text,
        'stock_item_id': None,
        'qr_code_value': normalized,
        'format': 'raw'
    }


def get_unit_stock(connection, company_id, unit_id, epi_id):
    row = connection.execute(
        'SELECT id, quantity FROM unit_epi_stock WHERE company_id = ? AND unit_id = ? AND epi_id = ?',
        (company_id, unit_id, epi_id),
    ).fetchone()
    return row_to_dict(row) if row else None


def upsert_unit_stock(connection, company_id, unit_id, epi_id, new_quantity):
    now = datetime.now(UTC).isoformat()
    existing = get_unit_stock(connection, company_id, unit_id, epi_id)
    if existing:
        connection.execute(
            'UPDATE unit_epi_stock SET quantity = ?, updated_at = ? WHERE id = ?',
            (int(new_quantity), now, int(existing['id'])),
        )
    else:
        connection.execute(
            'INSERT INTO unit_epi_stock (company_id, unit_id, epi_id, quantity, updated_at) '
            'VALUES (?, ?, ?, ?, ?)',
            (company_id, unit_id, epi_id, int(new_quantity), now),
        )


def fetch_epi_size_balance(connection, company_id, unit_id, epi_id):
    try:
        rows = connection.execute(
            '''
            SELECT glove_size, size, uniform_size, COUNT(*) AS quantity
            FROM epi_stock_items
            WHERE company_id = ? AND unit_id = ? AND epi_id = ? AND status = 'in_stock'
            GROUP BY glove_size, size, uniform_size
            ORDER BY quantity DESC, glove_size ASC, size ASC, uniform_size ASC
            ''',
            (int(company_id), int(unit_id), int(epi_id)),
        ).fetchall()
    except Exception:
        return []
    return [
        {
            'glove_size': row_to_dict(row).get('glove_size') or 'N/A',
            'size': row_to_dict(row).get('size') or 'N/A',
            'uniform_size': row_to_dict(row).get('uniform_size') or 'N/A',
            'quantity': int(row_to_dict(row).get('quantity') or 0),
        }
        for row in rows
    ]


def backfill_unit_stock_from_epis(connection, timestamp_iso):
    connection.execute(
        '''
        INSERT INTO unit_epi_stock (company_id, unit_id, epi_id, quantity, updated_at)
        SELECT epis.company_id, epis.unit_id, epis.id, epis.stock, ?
        FROM epis
        WHERE epis.unit_id IS NOT NULL
          AND NOT EXISTS (
              SELECT 1 FROM unit_epi_stock s
              WHERE s.company_id = epis.company_id AND s.unit_id = epis.unit_id AND s.epi_id = epis.id
          )
        ''',
        (timestamp_iso,),
    )


def fetch_low_stock_items(
    connection,
    actor=None,
    *,
    actor_operational_unit_id,
    get_unit_active_jv_name,
    is_epi_visible_for_unit,
):
    items = []
    clauses = ['COALESCE(epis.active, 1) = 1']
    params = []
    if actor and actor['role'] != 'master_admin':
        clauses.append('s.company_id = %s')
        params.append(actor['company_id'])
    scope_unit_id = actor_operational_unit_id(connection, actor)
    if scope_unit_id:
        clauses.append('s.unit_id = %s')
        params.append(scope_unit_id)
    scope_clause = f"WHERE {' AND '.join(clauses)}" if clauses else ''
    rows = connection.execute(
        f'''
        SELECT
               s.company_id, s.unit_id, s.epi_id,
               COALESCE(SUM(s.quantity), 0) AS stock,
               MAX(units.name) AS unit_name,
               MAX(companies.name) AS company_name,
               MAX(epis.name) AS epi_name,
               MAX(epis.minimum_stock) AS minimum_stock,
               MAX(epis.unit_measure) AS unit_measure,
               MAX(epis.unit_id) AS epi_unit_id,
               MAX(epis.active_joinventure) AS epi_active_joinventure
        FROM unit_epi_stock s
        JOIN units ON units.id = s.unit_id
        JOIN companies ON companies.id = s.company_id
        JOIN epis ON epis.id = s.epi_id
        {scope_clause}
        GROUP BY s.company_id, s.unit_id, s.epi_id
        ''',
        tuple(params),
    ).fetchall()
    unit_jv_cache: dict = {}
    for row in rows:
        row = row_to_dict(row)
        target_unit_id = int(row['unit_id'] or 0)
        if target_unit_id not in unit_jv_cache:
            unit_jv_cache[target_unit_id] = get_unit_active_jv_name(connection, target_unit_id)
        if not is_epi_visible_for_unit(
            epi_unit_id=row['epi_unit_id'],
            epi_joint_venture_name=row['epi_active_joinventure'],
            target_unit_id=target_unit_id,
            target_unit_joint_venture_name=unit_jv_cache[target_unit_id],
        ):
            continue
        stock = int(row['stock'] or 0)
        minimum = int(row['minimum_stock']) if row['minimum_stock'] is not None else 10
        if stock <= minimum:
            size_balances = fetch_epi_size_balance(
                connection, int(row['company_id']), int(row['unit_id']), int(row['epi_id'])
            )
            severity = 'critical' if stock <= 0 else ('danger' if stock < minimum else 'warning')
            items.append({
                'epi_id': row['epi_id'],
                'epi_name': row['epi_name'],
                'company_id': row['company_id'],
                'company_name': row['company_name'],
                'unit_id': row['unit_id'],
                'unit_name': row.get('unit_name') or '-',
                'stock': stock,
                'minimum_stock': minimum,
                'unit_measure': row.get('unit_measure') or 'unidade',
                'severity': severity,
                'size_balances': size_balances,
            })
    items.sort(key=lambda r: (r['company_name'], r['unit_name'], r['epi_name']))
    return items


def build_low_stock(
    connection,
    actor,
    *,
    actor_operational_unit_id,
    get_unit_active_jv_name,
    is_epi_visible_for_unit,
):
    items = fetch_low_stock_items(
        connection,
        actor,
        actor_operational_unit_id=actor_operational_unit_id,
        get_unit_active_jv_name=get_unit_active_jv_name,
        is_epi_visible_for_unit=is_epi_visible_for_unit,
    )
    return {'items': items}


def normalize_item_size_value(value):
    normalized = str(value or '').strip()
    if not normalized:
        return ''
    lowered = normalized.lower()
    if lowered in {'n/a', 'na', 'selecione', 'selecione o tamanho', 'null', 'undefined'}:
        return ''
    return normalized


def resolve_item_size(glove_size, size, uniform_size):
    normalized_glove = normalize_item_size_value(glove_size)
    normalized_size = normalize_item_size_value(size)
    normalized_uniform = normalize_item_size_value(uniform_size)
    selected_size = normalized_glove or normalized_size or normalized_uniform or ''
    return {
        'selected_size': selected_size,
        'glove_size': normalized_glove or 'N/A',
        'size': selected_size or 'N/A',
        'uniform_size': normalized_uniform or 'N/A',
    }


def resolve_effective_size_fields(primary, fallback=None, *, fallback_prefix=''):
    primary = primary or {}
    fallback = fallback or {}
    primary_glove = normalize_item_size_value(primary.get('glove_size'))
    primary_size = normalize_item_size_value(primary.get('size'))
    primary_uniform = normalize_item_size_value(primary.get('uniform_size'))
    fallback_glove = normalize_item_size_value(fallback.get(f'{fallback_prefix}glove_size'))
    fallback_size = normalize_item_size_value(fallback.get(f'{fallback_prefix}size'))
    fallback_uniform = normalize_item_size_value(fallback.get(f'{fallback_prefix}uniform_size'))
    selected_size = (
        primary_glove or primary_size or primary_uniform
        or fallback_glove or fallback_size or fallback_uniform or ''
    )
    return {
        'selected_size': selected_size,
        'glove_size': primary_glove or fallback_glove or 'N/A',
        'size': primary_size or fallback_size or selected_size or 'N/A',
        'uniform_size': primary_uniform or fallback_uniform or 'N/A',
    }


def apply_effective_size_fields(target, primary, fallback=None, *, fallback_prefix=''):
    effective_size = resolve_effective_size_fields(primary, fallback, fallback_prefix=fallback_prefix)
    target['glove_size'] = effective_size['glove_size']
    target['size'] = effective_size['size']
    target['uniform_size'] = effective_size['uniform_size']
    return target


def sync_epi_scope_stock_unit(connection, company_id, epi_id, previous_unit_id, new_unit_id):
    old_unit = int(previous_unit_id) if previous_unit_id else 0
    next_unit = int(new_unit_id) if new_unit_id else 0
    if old_unit == next_unit:
        return
    if not old_unit or not next_unit:
        return
    previous_stock = get_unit_stock(connection, int(company_id), old_unit, int(epi_id))
    if not previous_stock:
        return
    quantity = int(previous_stock.get('quantity') or 0)
    connection.execute('DELETE FROM unit_epi_stock WHERE id = ?', (int(previous_stock['id']),))
    target_stock = get_unit_stock(connection, int(company_id), next_unit, int(epi_id))
    if target_stock:
        upsert_unit_stock(
            connection, int(company_id), next_unit, int(epi_id),
            int(target_stock.get('quantity') or 0) + quantity
        )
    else:
        upsert_unit_stock(connection, int(company_id), next_unit, int(epi_id), quantity)


# ── Route-level SQL extractions ───────────────────────────────────────────────

def lookup_stock_item_by_qr(connection, company_id, unit_id, qr_code='', stock_item_id=0):
    query_sql = (
        'SELECT esi.id, esi.company_id, esi.unit_id, esi.epi_id, esi.glove_size, esi.size, esi.uniform_size, '
        'esi.lot_code, esi.qr_code_value, esi.status, esi.reprint_count, esi.label_measure, '
        'esi.label_printer_name, esi.label_print_format, epis.name AS epi_name, epis.purchase_code, '
        'epis.unit_measure, units.name AS unit_name '
        'FROM epi_stock_items esi '
        'JOIN epis ON epis.id = esi.epi_id '
        'JOIN units ON units.id = esi.unit_id '
        'WHERE esi.company_id = ? AND esi.unit_id = ?'
    )
    query_params = [int(company_id), int(unit_id)]
    if qr_code:
        query_sql += ' AND esi.qr_code_value = ?'
        query_params.append(qr_code)
    if int(stock_item_id) > 0:
        query_sql += ' AND esi.id = ?'
        query_params.append(int(stock_item_id))
    query_sql += ' ORDER BY esi.id DESC LIMIT 1'
    return connection.execute(query_sql, tuple(query_params)).fetchone()


def fetch_available_stock_items(connection, company_id, unit_id, epi_id):
    return connection.execute(
        (
            'SELECT esi.id, esi.qr_code_value, esi.epi_id, epis.name AS epi_name, esi.status, '
            'esi.glove_size, esi.size, esi.uniform_size '
            'FROM epi_stock_items esi '
            'JOIN epis ON epis.id = esi.epi_id '
            'WHERE esi.company_id = ? AND esi.unit_id = ? AND esi.epi_id = ? '
            "AND COALESCE(LOWER(esi.status), 'in_stock') IN ('in_stock', 'available') "
            "AND COALESCE(esi.qr_code_value, '') != '' "
            'ORDER BY esi.id ASC'
        ),
        (int(company_id), int(unit_id), int(epi_id))
    ).fetchall()


def fetch_stock_movements(connection, clauses, params):
    final_where = f"WHERE {' AND '.join(clauses)}" if clauses else ''
    return connection.execute(
        (
            'SELECT sm.id, sm.company_id, sm.unit_id, sm.epi_id, sm.movement_type, '
            'sm.quantity, sm.previous_stock, sm.new_stock, sm.source_type, sm.source_id, '
            'sm.notes, sm.actor_name, sm.created_at, '
            'sm.glove_size, sm.size, sm.uniform_size, '
            'e.name AS epi_name, e.ca, e.unit_measure, u.name AS unit_name '
            'FROM stock_movements sm '
            'JOIN epis e ON e.id = sm.epi_id '
            'JOIN units u ON u.id = sm.unit_id '
            f'{final_where} '
            'ORDER BY sm.created_at DESC, sm.id DESC '
            'LIMIT 500'
        ),
        tuple(params)
    ).fetchall()


def set_epi_minimum_stock(connection, epi_id, minimum_stock):
    connection.execute('UPDATE epis SET minimum_stock = ? WHERE id = ?', (minimum_stock, int(epi_id)))


def create_stock_movement(connection, company_id, unit_id, epi_id, movement_type, quantity,
                          previous_stock, new_stock, source_type, source_id, notes,
                          actor_user_id, actor_name, created_at, glove_size, size, uniform_size):
    cursor = connection.execute(
        (
            'INSERT INTO stock_movements ('
            'company_id, unit_id, epi_id, movement_type, quantity, previous_stock, new_stock, '
            'source_type, source_id, notes, actor_user_id, actor_name, created_at, glove_size, size, uniform_size'
            ') VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'
        ),
        (
            company_id, unit_id, epi_id, movement_type, quantity,
            previous_stock, new_stock, source_type, source_id, notes,
            actor_user_id, actor_name, created_at, glove_size, size, uniform_size,
        )
    )
    return int(cursor.lastrowid)


def create_stock_item(connection, company_id, unit_id, epi_id, glove_size, size, uniform_size,
                      seq_value, qr_value, movement_id, lot_code, manufacture_date,
                      label_measure, label_printer_name, label_print_format,
                      generated_by_user_id, now):
    cursor = connection.execute(
        (
            'INSERT INTO epi_stock_items ('
            'company_id, unit_id, epi_id, glove_size, size, uniform_size, qr_sequence, qr_code_value, status, '
            'stock_movement_id, lot_code, manufacture_date, label_measure, label_printer_name, label_print_format, generated_by_user_id, created_at, updated_at'
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'in_stock', ?, ?, ?, ?, ?, ?, ?, ?, ?)"
        ),
        (
            company_id, unit_id, epi_id, glove_size, size, uniform_size,
            seq_value, qr_value, movement_id, lot_code, manufacture_date,
            label_measure, label_printer_name, label_print_format,
            generated_by_user_id, now, now,
        )
    )
    return int(cursor.lastrowid)


def get_stock_item_for_reprint(connection, stock_item_id):
    return connection.execute(
        (
            'SELECT esi.id, esi.company_id, esi.unit_id, esi.epi_id, esi.qr_code_value, esi.status, esi.glove_size, esi.size, '
            'esi.uniform_size, esi.label_measure, esi.label_printer_name, esi.label_print_format, esi.reprint_count, '
            'units.name AS unit_name, epis.name AS epi_name '
            'FROM epi_stock_items esi '
            'JOIN units ON units.id = esi.unit_id '
            'JOIN epis ON epis.id = esi.epi_id '
            'WHERE esi.id = ?'
        ),
        (int(stock_item_id),)
    ).fetchone()


def create_stock_item_reprint(connection, stock_item_id, company_id, reason_code, reason_note,
                               actor_user_id, actor_name, now):
    connection.execute(
        (
            'INSERT INTO epi_stock_item_reprints (stock_item_id, company_id, reason_code, reason_note, actor_user_id, actor_name, created_at) '
            'VALUES (?, ?, ?, ?, ?, ?, ?)'
        ),
        (int(stock_item_id), int(company_id), reason_code, reason_note, int(actor_user_id), str(actor_name or ''), now)
    )
    connection.execute(
        'UPDATE epi_stock_items SET reprint_count = COALESCE(reprint_count, 0) + 1, updated_at = ? WHERE id = ?',
        (now, int(stock_item_id))
    )
    updated = connection.execute(
        'SELECT reprint_count FROM epi_stock_items WHERE id = ?',
        (int(stock_item_id),)
    ).fetchone()
    return int(updated['reprint_count']) if updated else 0
