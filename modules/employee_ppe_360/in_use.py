"""F2.1 read projection: tenant + person authorization never replaces row scope."""
import re
from datetime import UTC, date, datetime

from core.auth import ensure_permission
from core.permissions import PERM_DELIVERIES_VIEW, PERM_EMPLOYEES_VIEW
from core.repository import resolve_unit_scope
from modules.deliveries.visibility import active_delivery_sql
from modules.employee_ppe_360.contract import (
    BLOCKED_ROLES,
    ContractError,
    encode_cursor,
    parse_page_params,
)

SENTINEL = '0000-00-00'
MAX_ID = 9223372036854775807


class InUseError(Exception):
    def __init__(self, code, status=400):
        self.code, self.status = code, status
        super().__init__(code)


def require_permissions(actor):
    if actor.get('role') in BLOCKED_ROLES:
        raise ContractError('FORBIDDEN')
    try:
        ensure_permission(actor, PERM_EMPLOYEES_VIEW)
        ensure_permission(actor, PERM_DELIVERIES_VIEW)
    except PermissionError:
        raise ContractError('FORBIDDEN') from None
    if not actor.get('company_id'):
        raise ContractError('FORBIDDEN')


def valid_date(raw):
    text = str(raw or '').strip(' \t\n\r\f\v')
    if not re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}', text):
        return None
    try:
        date.fromisoformat(text)
    except ValueError:
        return None
    return text


def parse_query(query):
    if set(query) - {'limit', 'cursor', 'actor_user_id'} or len(query.get('actor_user_id', [])) > 1:
        raise InUseError('INVALID_QUERY_PARAM')
    limits = query.get('limit', [])
    if limits and limits[0].strip() and (not re.fullmatch(r'[0-9]{1,10}', limits[0].strip())):
        raise ContractError('INVALID_PAGINATION')
    page = parse_page_params(query)
    if page['cursor']:
        sort, row_id = page['cursor']
        if (sort != SENTINEL and valid_date(sort) != sort) or row_id > MAX_ID:
            raise ContractError('INVALID_PAGINATION')
    return page


def resolve_scope(connection, actor):
    try:
        scope = resolve_unit_scope(connection, actor)
    except (PermissionError, ValueError, TypeError):
        raise ContractError('FORBIDDEN') from None
    if scope.locked:
        row = connection.execute('SELECT id FROM units WHERE id = ? AND company_id = ?',
                                 (scope.unit_id, actor['company_id'])).fetchone()
        if not row:
            raise ContractError('FORBIDDEN')
    return {
        'company_id': int(actor['company_id']),
        'mode': 'operational_unit' if scope.locked else 'company',
        'authorized_unit_ids': [scope.unit_id] if scope.locked else None,
        'partial_by_unit': scope.locked,
    }


# CASE guards all casts: malformed legacy text cannot abort a PostgreSQL transaction.
# Gregorian validation avoids version-specific pg_input_is_valid and unsafe date casts.
_DATE_TEXT = "btrim(COALESCE(d.delivery_date, ''), chr(32)||chr(9)||chr(10)||chr(13)||chr(12)||chr(11))"
_YEAR = f"substring({_DATE_TEXT},1,4)::int"
_MONTH = f"substring({_DATE_TEXT},6,2)::int"
_DAY = f"substring({_DATE_TEXT},9,2)::int"
SORT_DATE_SQL = f"""CASE WHEN {_DATE_TEXT} ~ '^[0-9]{{4}}-[0-9]{{2}}-[0-9]{{2}}$'
THEN CASE WHEN {_YEAR} BETWEEN 1 AND 9999 AND {_MONTH} BETWEEN 1 AND 12
 AND {_DAY} BETWEEN 1 AND CASE {_MONTH}
 WHEN 2 THEN CASE WHEN mod({_YEAR},400) = 0 OR (mod({_YEAR},4) = 0 AND mod({_YEAR},100) <> 0)
 THEN 29 ELSE 28 END
 WHEN 4 THEN 30 WHEN 6 THEN 30 WHEN 9 THEN 30 WHEN 11 THEN 30 ELSE 31 END
 THEN {_DATE_TEXT} ELSE '0000-00-00' END ELSE '0000-00-00' END"""



def item_query(connection, actor, employee, scope, page):
    where = ('d.company_id = ? AND d.employee_id = ? '
             "AND COALESCE(d.returned_date, '') = ''" + active_delivery_sql(connection, 'd'))
    params = [int(actor['company_id']), int(employee['id'])]
    if scope['partial_by_unit']:
        where += ' AND d.unit_id = ?'
        params.append(scope['authorized_unit_ids'][0])
    after = ''
    if page['cursor']:
        after = 'WHERE (n.sort_date, n.id) < (?, ?)'
    sql = f"""WITH normalized AS (
 SELECT d.id, d.epi_id, d.unit_id, d.quantity, d.delivery_date, d.next_replacement_date,
 {SORT_DATE_SQL} AS sort_date FROM deliveries d WHERE {where}),
 windowed AS (SELECT n.* FROM normalized n {after}
 ORDER BY n.sort_date DESC, n.id DESC LIMIT ?)
 SELECT n.id, n.quantity, n.delivery_date, n.next_replacement_date, n.sort_date,
 e.id AS product_id, e.name AS product_name, e.epi_section AS product_category,
 u.id AS unit_id, u.name AS unit_name
 FROM windowed n
 LEFT JOIN epis e ON e.id = n.epi_id AND e.company_id = ?
 LEFT JOIN units u ON u.id = n.unit_id AND u.company_id = ?
 ORDER BY n.sort_date DESC, n.id DESC"""
    if page['cursor']:
        params.extend(page['cursor'])
    params.extend([page['limit'] + 1, actor['company_id'], actor['company_id']])
    return sql, tuple(params)


def _text(raw):
    if raw is None:
        return None
    return str(raw).strip() or None


def fetch_in_use(connection, actor, employee, scope, page):
    sql, params = item_query(connection, actor, employee, scope, page)
    rows = connection.execute(sql, params).fetchall()
    more = len(rows) > page['limit']
    rows = rows[:page['limit']]
    items = []
    for row in rows:
        items.append({
            'delivery_id': int(row['id']),
            'product': {'id': int(row['product_id']), 'name': _text(row['product_name']),
                        'category': _text(row['product_category'])} if row['product_id'] else None,
            'quantity': int(row['quantity']) if row['quantity'] is not None else 1,
            'delivery_date': valid_date(row['delivery_date']),
            'next_replacement_date': valid_date(row['next_replacement_date']),
            'unit': {'id': int(row['unit_id']), 'name': _text(row['unit_name'])} if row['unit_id'] else None,
        })
    cursor = encode_cursor(rows[-1]['sort_date'], int(rows[-1]['id'])) if more else None
    return {'employee_id': int(employee['id']), 'scope': scope, 'items': items,
            'generated_at': datetime.now(UTC).isoformat()}, cursor
