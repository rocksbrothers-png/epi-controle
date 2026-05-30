"""Rotas de gestão de estoque de EPIs."""

from contextlib import closing
from urllib.parse import parse_qs

from core.database import get_connection
from core.repository import actor_operational_unit_id, authorize_action, get_unit_by_id, get_unit_active_jv_name
from core.security import resolve_actor_user_id
from epi_backend.db import row_to_dict
from epi_backend.epi_scope import is_epi_visible_for_unit
from epi_backend.http_utils import send_json
from modules.purchases.service import get_actor_purchase_unit_scope
from modules.stock.service import build_low_stock, parse_int_flexible, parse_stock_qr_lookup_value


# ── GET ───────────────────────────────────────────────────────────────────────

def handle_get_stock_low(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed), 'stock:view')
        result = build_low_stock(
            connection,
            actor,
            actor_operational_unit_id=actor_operational_unit_id,
            get_unit_active_jv_name=get_unit_active_jv_name,
            is_epi_visible_for_unit=is_epi_visible_for_unit,
        )
        return send_json(handler, 200, result)


def handle_get_stock_lookup_qr(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed), 'stock:view')
        query = parse_qs(parsed.query)
        qr_code = str(query.get('qr_code', [''])[0]).strip()
        if not qr_code:
            raise ValueError('QR informado é obrigatório.')
        parsed_qr = parse_stock_qr_lookup_value(qr_code)
        query_stock_item_id = parse_int_flexible(query.get('stock_item_id', [''])[0], 0) or parsed_qr.get('stock_item_id') or 0
        company_filter = actor['company_id'] if actor['role'] != 'master_admin' else query.get('company_id', [''])[0]
        scope_unit_id = actor_operational_unit_id(connection, actor)
        if actor.get('role') in ('admin', 'user') and not scope_unit_id:
            raise PermissionError('Perfil sem unidade operacional ativa para consultar estoque.')
        unit_filter = scope_unit_id or query.get('unit_id', [''])[0]
        if not unit_filter:
            raise ValueError('Unidade é obrigatória para validar o QR.')
        company_scope_id = int(company_filter or 0)
        if not company_scope_id:
            unit_row = get_unit_by_id(connection, int(unit_filter))
            company_scope_id = int(unit_row['company_id']) if unit_row else 0
        requested_qr_code = str(parsed_qr.get('qr_code_value') or '').strip()
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
        query_params = [int(company_scope_id), int(unit_filter)]
        if requested_qr_code:
            query_sql += ' AND esi.qr_code_value = ?'
            query_params.append(requested_qr_code)
        if int(query_stock_item_id) > 0:
            query_sql += ' AND esi.id = ?'
            query_params.append(int(query_stock_item_id))
        query_sql += ' ORDER BY esi.id DESC LIMIT 1'
        stock_item = connection.execute(query_sql, tuple(query_params)).fetchone()
        if not stock_item:
            raise ValueError('QR não encontrado com correspondência exata no estoque da unidade.')
        return send_json(handler, 200, {'stock_item': row_to_dict(stock_item)})


def handle_get_stock_available_items(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed), 'stock:view')
        query = parse_qs(parsed.query)
        epi_id = parse_int_flexible(query.get('epi_id', [''])[0], 0)
        if epi_id <= 0:
            raise ValueError('EPI é obrigatório para listar QRs disponíveis.')
        company_filter = actor['company_id'] if actor['role'] != 'master_admin' else query.get('company_id', [''])[0]
        scope_unit_id = actor_operational_unit_id(connection, actor)
        if actor.get('role') in ('admin', 'user') and not scope_unit_id:
            raise PermissionError('Perfil sem unidade operacional ativa para consultar estoque.')
        unit_filter = scope_unit_id or query.get('unit_id', [''])[0]
        if not unit_filter:
            raise ValueError('Unidade é obrigatória para listar QRs disponíveis.')
        company_scope_id = int(company_filter or 0)
        if not company_scope_id:
            unit_row = get_unit_by_id(connection, int(unit_filter))
            company_scope_id = int(unit_row['company_id']) if unit_row else 0
        items = connection.execute(
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
            (int(company_scope_id), int(unit_filter), int(epi_id))
        ).fetchall()
        return send_json(handler, 200, {'items': [row_to_dict(item) for item in items]})


def handle_get_stock_movements_report(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed), 'stock:view')
        query = parse_qs(parsed.query)
        company_filter = actor['company_id'] if actor['role'] != 'master_admin' else query.get('company_id', [''])[0]
        scope_unit_id = actor_operational_unit_id(connection, actor)
        purchase_scope = get_actor_purchase_unit_scope(connection, actor)
        clauses, params = [], []
        if company_filter:
            clauses.append('sm.company_id = ?')
            params.append(int(company_filter))
        if scope_unit_id:
            clauses.append('sm.unit_id = ?')
            params.append(int(scope_unit_id))
        elif purchase_scope:
            ph = ','.join(['?'] * len(purchase_scope))
            clauses.append(f'sm.unit_id IN ({ph})')
            params.extend(purchase_scope)
        year_filter = query.get('year', [''])[0].strip()
        month_filter = query.get('month', [''])[0].strip()
        epi_filter = query.get('epi_id', [''])[0].strip()
        movement_type_filter = query.get('movement_type', [''])[0].strip()
        source_type_filter = query.get('source_type', [''])[0].strip()
        unit_filter_q = query.get('unit_id', [''])[0].strip()
        if year_filter:
            clauses.append("substr(sm.created_at, 1, 4) = ?")
            params.append(year_filter)
        if month_filter:
            clauses.append("substr(sm.created_at, 6, 2) = ?")
            params.append(month_filter.zfill(2))
        if epi_filter:
            clauses.append('sm.epi_id = ?')
            params.append(int(epi_filter))
        if movement_type_filter:
            clauses.append('sm.movement_type = ?')
            params.append(movement_type_filter)
        if source_type_filter:
            clauses.append('sm.source_type = ?')
            params.append(source_type_filter)
        if unit_filter_q and not scope_unit_id:
            clauses.append('sm.unit_id = ?')
            params.append(int(unit_filter_q))
        final_where = f"WHERE {' AND '.join(clauses)}" if clauses else ''
        rows = connection.execute(
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
        return send_json(handler, 200, {'items': [row_to_dict(r) for r in rows]})


# ── Registro ──────────────────────────────────────────────────────────────────

def register_routes(router):
    router.register('GET', '/api/stock/low',              handle_get_stock_low)
    router.register('GET', '/api/stock/lookup-qr',        handle_get_stock_lookup_qr)
    router.register('GET', '/api/stock/available-items',  handle_get_stock_available_items)
    router.register('GET', '/api/stock/movements/report', handle_get_stock_movements_report)
