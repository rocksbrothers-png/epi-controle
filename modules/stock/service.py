"""Serviços de gestão de estoque de EPIs."""

from datetime import datetime, timezone

from epi_backend.db import row_to_dict

UTC = timezone.utc


def get_unit_stock(connection, company_id, unit_id, epi_id):
    row = connection.execute(
        'SELECT id, quantity FROM unit_epi_stock WHERE company_id = %s AND unit_id = %s AND epi_id = %s',
        (company_id, unit_id, epi_id),
    ).fetchone()
    return row_to_dict(row) if row else None


def upsert_unit_stock(connection, company_id, unit_id, epi_id, new_quantity):
    now = datetime.now(UTC).isoformat()
    existing = get_unit_stock(connection, company_id, unit_id, epi_id)
    if existing:
        connection.execute(
            'UPDATE unit_epi_stock SET quantity = %s, updated_at = %s WHERE id = %s',
            (int(new_quantity), now, int(existing['id'])),
        )
    else:
        connection.execute(
            'INSERT INTO unit_epi_stock (company_id, unit_id, epi_id, quantity, updated_at) '
            'VALUES (%s, %s, %s, %s, %s)',
            (company_id, unit_id, epi_id, int(new_quantity), now),
        )


def fetch_epi_size_balance(connection, company_id, unit_id, epi_id):
    try:
        rows = connection.execute(
            '''
            SELECT glove_size, size, uniform_size, COUNT(*) AS quantity
            FROM epi_stock_items
            WHERE company_id = %s AND unit_id = %s AND epi_id = %s AND status = 'in_stock'
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
        SELECT epis.company_id, epis.unit_id, epis.id, epis.stock, %s
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
