"""Rotas de compras: requisições, ordens de compra e fornecedores."""

import re
from contextlib import closing
from urllib.parse import parse_qs

from core.auth import ensure_resource_company
from core.database import get_connection
from core.permissions import (
    PERM_FINANCE_VIEW,
    PERM_PO_VIEW,
    PERM_PURCHASE_REQUESTS_VIEW,
    PERM_PURCHASE_REQUESTS_UPDATE,
    PERM_PURCHASE_REQUESTS_CREATE,
    PERM_SUPPLIERS_MANAGE,
    PERM_UNIT_LINKS_MANAGE,
)
from core.repository import get_epi_by_id, get_unit_by_id, authorize_action
from modules.employees.service import actor_operational_unit_id
from core.security import resolve_actor_user_id
from datetime import datetime, timezone
from epi_backend.db import row_to_dict
from epi_backend.http_utils import require_fields, send_json, structured_log

UTC = timezone.utc


def _get_server():
    import server_postgres as _sp
    return _sp


from modules.purchases.service import (
    _record_purchase_event,
    actor_company_id_or_query,
    apply_purchase_request_workflow_action,
    ensure_purchase_request_action_scope,
    fetch_purchase_demands,
    fetch_purchase_function_links,
    find_recent_duplicate_purchase_request,
    get_actor_purchase_unit_scope,
    require_purchase_function_admin,
)


# ── GET ───────────────────────────────────────────────────────────────────────

def handle_get_epi_requests(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        actor = authorize_action(
            connection,
            resolve_actor_user_id(handler, parsed),
            PERM_PURCHASE_REQUESTS_VIEW
        )
        query = parse_qs(parsed.query)
        company_filter = actor['company_id'] if actor['role'] != 'master_admin' else query.get('company_id', [''])[0]
        scope_unit_id = actor_operational_unit_id(connection, actor)
        purchase_scope = get_actor_purchase_unit_scope(connection, actor)
        clauses, params = [], []
        if company_filter:
            clauses.append('r.company_id = ?')
            params.append(int(company_filter))
        if scope_unit_id:
            clauses.append('r.unit_id = ?')
            params.append(int(scope_unit_id))
        elif purchase_scope:
            placeholders = ','.join(['?'] * len(purchase_scope))
            clauses.append(f'r.unit_id IN ({placeholders})')
            params.extend(purchase_scope)
        final_where = f"WHERE {' AND '.join(clauses)}" if clauses else ''
        rows = connection.execute(
            (
                'SELECT r.*, employees.name AS employee_name, employees.employee_id_code, '
                'employees.sector AS employee_sector, employees.role_name AS employee_role, '
                'units.name AS unit_name, '
                'epis.name AS epi_name, epis.ca, epis.unit_measure '
                'FROM epi_requests r '
                'JOIN employees ON employees.id = r.employee_id '
                'JOIN units ON units.id = r.unit_id '
                'JOIN epis ON epis.id = r.epi_id '
                f'{final_where} '
                'ORDER BY r.requested_at DESC, r.id DESC'
            ),
            tuple(params)
        ).fetchall()
        return send_json(handler, 200, {'items': [row_to_dict(item) for item in rows]})


def handle_get_purchase_demands(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed), PERM_PURCHASE_REQUESTS_VIEW)
        query = parse_qs(parsed.query)
        if actor.get('role') == 'master_admin':
            requested_company = str(query.get('company_id', [''])[0] or '').strip()
            company_id = int(requested_company) if requested_company else None
        else:
            company_id = actor_company_id_or_query(connection, actor, query)
        scope_unit_id = actor_operational_unit_id(connection, actor)
        purchase_scope_units = get_actor_purchase_unit_scope(connection, actor)
        if not scope_unit_id and purchase_scope_units:
            all_demands, seen = [], set()
            for uid in purchase_scope_units:
                for d in fetch_purchase_demands(connection, company_id, uid):
                    key = (d.get('demand_type'), d.get('id') or f"{d.get('unit_id')}/{d.get('epi_id')}")
                    if key not in seen:
                        seen.add(key)
                        all_demands.append(d)
            return send_json(handler, 200, {'items': all_demands})
        demands = fetch_purchase_demands(connection, company_id, scope_unit_id)
        return send_json(handler, 200, {'items': demands})


def handle_get_purchase_requests(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed), PERM_PURCHASE_REQUESTS_VIEW)
        query = parse_qs(parsed.query)
        company_id = actor_company_id_or_query(connection, actor, query)
        scope_unit_id = actor_operational_unit_id(connection, actor)
        purchase_scope_units = get_actor_purchase_unit_scope(connection, actor)
        status_filter = str(query.get('status', [''])[0] or '').strip()
        clauses, params = ['pr.company_id = %s'], [company_id]
        if scope_unit_id:
            clauses.append('pr.unit_id = %s')
            params.append(int(scope_unit_id))
        elif purchase_scope_units:
            placeholders = ','.join(['%s'] * len(purchase_scope_units))
            clauses.append(f'pr.unit_id IN ({placeholders})')
            params.extend(purchase_scope_units)
        if status_filter:
            clauses.append('pr.status = %s')
            params.append(status_filter)
        where_sql = f"WHERE {' AND '.join(clauses)}"
        rows = connection.execute(
            f'SELECT pr.*, u.name AS unit_name, '
            f'(SELECT COUNT(*) FROM purchase_request_items pri WHERE pri.purchase_request_id = pr.id) AS items_count '
            f'FROM purchase_requests pr JOIN units u ON u.id = pr.unit_id {where_sql} ORDER BY pr.created_at DESC',
            tuple(params),
        ).fetchall()
        return send_json(handler, 200, {'items': [row_to_dict(r) for r in rows]})


def handle_get_purchase_request_detail(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed), PERM_PURCHASE_REQUESTS_VIEW)
        pr_id = int(match.group(1))
        pr = connection.execute(
            'SELECT pr.*, u.name AS unit_name FROM purchase_requests pr JOIN units u ON u.id = pr.unit_id WHERE pr.id = %s',
            (pr_id,),
        ).fetchone()
        if not pr:
            return send_json(handler, 404, {'error': 'Requisição não encontrada.'})
        ensure_resource_company(actor, pr, 'Requisição')
        ensure_purchase_request_action_scope(
            connection, actor, row_to_dict(pr), actor_operational_unit_id=actor_operational_unit_id
        )
        items = connection.execute(
            'SELECT pri.*, e.name AS epi_display_name, e.ca AS epi_ca, u.name AS unit_name '
            'FROM purchase_request_items pri '
            'JOIN epis e ON e.id = pri.epi_id '
            'JOIN units u ON u.id = pri.unit_id '
            'WHERE pri.purchase_request_id = %s ORDER BY pri.id',
            (pr_id,),
        ).fetchall()
        events = connection.execute(
            'SELECT * FROM purchase_events WHERE entity_type = %s AND entity_id = %s ORDER BY created_at DESC, id DESC',
            ('purchase_request', pr_id),
        ).fetchall()
        return send_json(handler, 200, {
            'item': row_to_dict(pr),
            'items': [row_to_dict(i) for i in items],
            'events': [row_to_dict(e) for e in events],
        })


def handle_get_purchase_orders(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed), PERM_PO_VIEW)
        query = parse_qs(parsed.query)
        company_id = actor_company_id_or_query(connection, actor, query)
        scope_unit_id = actor_operational_unit_id(connection, actor)
        purchase_scope_units = get_actor_purchase_unit_scope(connection, actor)
        status_filter = str(query.get('status', [''])[0] or '').strip()
        clauses, params = ['po.company_id = %s'], [company_id]
        if scope_unit_id:
            clauses.append('po.unit_id = %s')
            params.append(int(scope_unit_id))
        elif purchase_scope_units:
            placeholders = ','.join(['%s'] * len(purchase_scope_units))
            clauses.append(f'po.unit_id IN ({placeholders})')
            params.extend(purchase_scope_units)
        if status_filter:
            clauses.append('po.status = %s')
            params.append(status_filter)
        where_sql = f"WHERE {' AND '.join(clauses)}"
        rows = connection.execute(
            f'SELECT po.*, u.name AS unit_name, '
            f'(SELECT COUNT(*) FROM purchase_order_items poi WHERE poi.purchase_order_id = po.id) AS items_count '
            f'FROM purchase_orders po JOIN units u ON u.id = po.unit_id {where_sql} ORDER BY po.created_at DESC',
            tuple(params),
        ).fetchall()
        return send_json(handler, 200, {'items': [row_to_dict(r) for r in rows]})


def handle_get_purchase_order_detail(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed), PERM_PO_VIEW)
        po_id = int(match.group(1))
        po = connection.execute(
            'SELECT po.*, u.name AS unit_name FROM purchase_orders po JOIN units u ON u.id = po.unit_id WHERE po.id = %s',
            (po_id,),
        ).fetchone()
        if not po:
            return send_json(handler, 404, {'error': 'PO não encontrada.'})
        ensure_resource_company(actor, po, 'PO')
        items = connection.execute(
            'SELECT poi.* FROM purchase_order_items poi WHERE poi.purchase_order_id = %s', (po_id,)
        ).fetchall()
        files = connection.execute(
            'SELECT id, file_name, file_type, uploaded_by_name, created_at '
            'FROM purchase_order_files WHERE purchase_order_id = %s',
            (po_id,),
        ).fetchall()
        events = connection.execute(
            'SELECT * FROM purchase_events WHERE entity_type = %s AND entity_id = %s ORDER BY created_at DESC',
            ('purchase_order', po_id),
        ).fetchall()
        return send_json(handler, 200, {
            'item': row_to_dict(po),
            'items': [row_to_dict(i) for i in items],
            'files': [row_to_dict(f) for f in files],
            'events': [row_to_dict(e) for e in events],
        })


def handle_get_purchase_events(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed), PERM_FINANCE_VIEW)
        query = parse_qs(parsed.query)
        company_id = actor_company_id_or_query(connection, actor, query)
        entity_type = str(query.get('entity_type', [''])[0] or '').strip()
        entity_id = str(query.get('entity_id', [''])[0] or '').strip()
        clauses, params = ['company_id = %s'], [company_id]
        if entity_type:
            clauses.append('entity_type = %s')
            params.append(entity_type)
        if entity_id:
            clauses.append('entity_id = %s')
            params.append(int(entity_id))
        where_sql = f"WHERE {' AND '.join(clauses)}"
        rows = connection.execute(
            f'SELECT * FROM purchase_events {where_sql} ORDER BY created_at DESC LIMIT 200',
            tuple(params),
        ).fetchall()
        return send_json(handler, 200, {'items': [row_to_dict(r) for r in rows]})


def handle_get_purchase_functions(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        query = parse_qs(parsed.query)
        actor_id = resolve_actor_user_id(handler, parsed)
        try:
            actor = authorize_action(connection, actor_id, PERM_UNIT_LINKS_MANAGE)
        except PermissionError:
            actor = authorize_action(connection, actor_id, PERM_PURCHASE_REQUESTS_VIEW)
        company_id = actor_company_id_or_query(connection, actor, query)
        if actor.get('role') != 'master_admin' and int(actor['company_id']) != company_id:
            raise PermissionError('Empresa fora do escopo do usuário.')
        return send_json(handler, 200, {'items': fetch_purchase_function_links(connection, company_id)})


# ── POST ──────────────────────────────────────────────────────────────────────

def handle_post_purchase_request_workflow(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        require_fields(payload, ['actor_user_id', 'action'])
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed, payload), PERM_PURCHASE_REQUESTS_VIEW)
        pr_id = int(match.group(1))
        ip = str(getattr(handler, 'client_address', ('',))[0] or '')
        result = apply_purchase_request_workflow_action(
            connection, actor, pr_id, payload, ip,
            actor_operational_unit_id=actor_operational_unit_id,
        )
        connection.commit()
        return send_json(handler, 200, result)


def handle_post_purchase_requests(handler, parsed, payload, match):
    require_fields(payload, ['actor_user_id', 'unit_id', 'items'])
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed, payload), PERM_PURCHASE_REQUESTS_CREATE)
        company_id = int(actor['company_id'])
        unit_id = int(payload['unit_id'])
        unit = get_unit_by_id(connection, unit_id)
        if not unit:
            raise ValueError('Unidade não encontrada.')
        from core.auth import ensure_resource_company
        ensure_resource_company(actor, unit, 'Unidade')
        scope_unit_id = actor_operational_unit_id(connection, actor)
        if scope_unit_id and int(unit_id) != int(scope_unit_id):
            return send_json(handler, 403, {'ok': False, 'error': {'code': 'UNIT_SCOPE_VIOLATION', 'message': 'Administrador local pode criar requisições apenas para sua própria unidade operacional.'}})
        items = payload.get('items') or []
        if not items:
            raise ValueError('A requisição precisa ter pelo menos um item.')
        now = datetime.now(UTC).isoformat()
        title = str(payload.get('title') or f'Requisição {now[:10]}').strip()
        duplicate_id = find_recent_duplicate_purchase_request(connection, actor, unit_id, title, items, now)
        if duplicate_id:
            structured_log('info', 'purchase.request.duplicate_recent_reused', purchase_request_id=duplicate_id, actor_user_id=int(actor['id']))
            return send_json(handler, 200, {'ok': True, 'id': duplicate_id, 'duplicate': True})
        cursor = connection.execute(
            "INSERT INTO purchase_requests (company_id, unit_id, status, title, notes, created_by_user_id, created_by_name, created_at, updated_at) VALUES (?, ?, 'open', ?, ?, ?, ?, ?, ?)",
            (company_id, unit_id, title, str(payload.get('notes') or '').strip(), int(actor['id']), actor['full_name'], now, now)
        )
        pr_id = cursor.lastrowid
        epi_request_ids_to_lock = []
        for item in items:
            epi = get_epi_by_id(connection, int(item['epi_id']))
            if not epi:
                raise ValueError(f"EPI {item['epi_id']} não encontrado.")
            connection.execute(
                'INSERT INTO purchase_request_items (purchase_request_id, company_id, unit_id, epi_id, epi_name, ca, unit_measure, manufacturer, supplier, glove_size, size, uniform_size, quantity_requested, origin, employee_id, employee_name, employee_sector, employee_role, epi_request_id, status, notes, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                (pr_id, company_id, unit_id, int(item['epi_id']), epi['name'], epi['ca'], epi['unit_measure'], str(item.get('manufacturer') or epi.get('manufacturer') or ''), str(item.get('supplier') or epi.get('supplier_company') or ''), str(item.get('glove_size') or 'N/A'), str(item.get('size') or 'N/A'), str(item.get('uniform_size') or 'N/A'), int(item.get('quantity_requested') or 1), str(item.get('origin') or 'stock_minimum'), int(item['employee_id']) if item.get('employee_id') else None, str(item.get('employee_name') or ''), str(item.get('employee_sector') or ''), str(item.get('employee_role') or ''), int(item['epi_request_id']) if item.get('epi_request_id') else None, 'included_in_request', str(item.get('notes') or ''), now, now)
            )
            if item.get('epi_request_id'):
                epi_request_ids_to_lock.append(int(item['epi_request_id']))
        for epi_req_id in epi_request_ids_to_lock:
            connection.execute("UPDATE epi_requests SET status = 'em análise', last_updated_at = ? WHERE id = ?", (now, epi_req_id))
        ip = str(getattr(handler, 'client_address', ('',))[0] or '')
        _record_purchase_event(connection, company_id, 'purchase_request', pr_id, 'created', '', 'open', '', int(actor['id']), actor['full_name'], ip)
        connection.commit()
        return send_json(handler, 201, {'ok': True, 'id': pr_id})


def handle_post_purchase_request_review_items(handler, parsed, payload, match):
    require_fields(payload, ['actor_user_id'])
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed, payload), PERM_PURCHASE_REQUESTS_UPDATE)
        pr_id = int(match.group(1))
        pr = connection.execute('SELECT * FROM purchase_requests WHERE id = ?', (pr_id,)).fetchone()
        if not pr:
            raise ValueError('Requisição não encontrada.')
        ensure_purchase_request_action_scope(connection, actor, pr, actor_operational_unit_id=actor_operational_unit_id)
        if str(pr['status']) != 'waiting_requester_correction':
            raise ValueError('Itens só podem ser revisados quando a requisição aguarda correção do requisitante.')
        now = datetime.now(UTC).isoformat()
        affected = []
        for item in payload.get('updates') or []:
            item_id = int(item.get('id') or 0)
            qty = int(item.get('quantity_requested') or 1)
            if item_id <= 0 or qty <= 0:
                continue
            connection.execute(
                "UPDATE purchase_request_items SET quantity_requested = ?, notes = ?, updated_at = ? WHERE id = ? AND purchase_request_id = ? AND status NOT IN ('approved', 'ordered', 'received', 'closed')",
                (qty, str(item.get('notes') or '').strip(), now, item_id, pr_id)
            )
            affected.append(item_id)
        remove_ids = [int(item_id) for item_id in (payload.get('remove_item_ids') or []) if str(item_id).isdigit()]
        if remove_ids:
            placeholders = ','.join('?' for _ in remove_ids)
            connection.execute(
                f"DELETE FROM purchase_request_items WHERE purchase_request_id = ? AND id IN ({placeholders}) AND status NOT IN ('approved', 'ordered', 'received', 'closed')",
                (pr_id, *remove_ids)
            )
            affected.extend(remove_ids)
        for item in payload.get('add_items') or []:
            epi = get_epi_by_id(connection, int(item.get('epi_id') or 0))
            if not epi:
                raise ValueError(f"EPI {item.get('epi_id')} não encontrado.")
            qty = int(item.get('quantity_requested') or 1)
            if qty <= 0:
                raise ValueError('Quantidade inválida.')
            cursor = connection.execute(
                'INSERT INTO purchase_request_items (purchase_request_id, company_id, unit_id, epi_id, epi_name, ca, unit_measure, manufacturer, supplier, glove_size, size, uniform_size, quantity_requested, origin, employee_id, employee_name, employee_sector, employee_role, epi_request_id, status, notes, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                (pr_id, int(pr['company_id']), int(pr['unit_id']), int(epi['id']), epi['name'], epi['ca'], epi['unit_measure'], str(item.get('manufacturer') or epi.get('manufacturer') or ''), str(item.get('supplier') or epi.get('supplier_company') or ''), str(item.get('glove_size') or 'N/A'), str(item.get('size') or 'N/A'), str(item.get('uniform_size') or 'N/A'), qty, str(item.get('origin') or 'manual'), int(item['employee_id']) if item.get('employee_id') else None, str(item.get('employee_name') or ''), str(item.get('employee_sector') or ''), str(item.get('employee_role') or ''), int(item['epi_request_id']) if item.get('epi_request_id') else None, 'included_in_request', str(item.get('notes') or ''), now, now)
            )
            affected.append(int(cursor.lastrowid))
        connection.execute(
            "UPDATE purchase_requests SET notes = COALESCE(NULLIF(?, ''), notes), updated_at = ? WHERE id = ?",
            (str(payload.get('notes') or '').strip(), now, pr_id)
        )
        ip = str(getattr(handler, 'client_address', ('',))[0] or '')
        _record_purchase_event(
            connection, int(pr['company_id']), 'purchase_request', pr_id, 'requester_review_saved',
            str(pr['status']), str(pr['status']),
            'Itens afetados: ' + ', '.join(str(item_id) for item_id in affected),
            int(actor['id']), actor['full_name'], ip,
            actor.get('role') or '', str(payload.get('reason') or ''), 'requester'
        )
        connection.commit()
        return send_json(handler, 200, {'ok': True, 'affected_item_ids': affected})


def handle_post_purchase_request_status(handler, parsed, payload, match):
    require_fields(payload, ['actor_user_id', 'status'])
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed, payload), PERM_PURCHASE_REQUESTS_UPDATE)
        pr_id = int(match.group(1))
        pr = connection.execute('SELECT * FROM purchase_requests WHERE id = ?', (pr_id,)).fetchone()
        if not pr:
            raise ValueError('Requisição não encontrada.')
        ensure_purchase_request_action_scope(connection, actor, pr, actor_operational_unit_id=actor_operational_unit_id)
        valid_statuses = {
            'draft', 'open', 'sent_to_buyer', 'quoted', 'pending_approval', 'partially_approved',
            'approved', 'rejected', 'returned_to_buyer', 'waiting_buyer_correction', 'buyer_resubmitted',
            'waiting_requester_correction', 'requester_resubmitted', 'postponed', 'po_generated',
            'received', 'checked', 'closed', 'cancelled',
        }
        new_status = str(payload.get('status') or '').strip()
        if new_status not in valid_statuses:
            raise ValueError('Status inválido para requisição de compra.')
        old_status = str(pr['status'])
        now = datetime.now(UTC).isoformat()
        extra = {}
        if new_status == 'sent_to_buyer':
            extra['sent_to_buyer_at'] = now
        elif new_status in ('closed', 'cancelled'):
            extra['closed_at'] = now
        elif new_status == 'postponed':
            postponed_until = str(payload.get('postponed_until') or '').strip()
            if postponed_until:
                extra['postponed_until'] = postponed_until
        set_clause = ', '.join([f'{k} = ?' for k in ['status', 'updated_at', *extra.keys()]])
        connection.execute(
            f'UPDATE purchase_requests SET {set_clause} WHERE id = ?',
            [new_status, now, *extra.values(), pr_id]
        )
        stock_entries = 0
        if new_status == 'closed':
            connection.execute(
                "UPDATE purchase_request_items SET status = 'closed', updated_at = ? WHERE purchase_request_id = ?",
                (now, pr_id)
            )
        elif new_status == 'checked':
            received_items_payload = payload.get('received_items') or []
            if received_items_payload:
                for item_data in received_items_payload:
                    item_id = int(str(item_data.get('id') or '').strip() or '0')
                    if not item_id:
                        continue
                    item_status = 'received' if item_data.get('received') else 'not_received'
                    connection.execute(
                        'UPDATE purchase_request_items SET status = ?, updated_at = ? WHERE id = ? AND purchase_request_id = ?',
                        (item_status, now, item_id, pr_id)
                    )
            else:
                connection.execute(
                    "UPDATE purchase_request_items SET status = 'checked', updated_at = ? WHERE purchase_request_id = ? AND status NOT IN ('not_received', 'closed')",
                    (now, pr_id)
                )
            if old_status == 'received':
                sp = _get_server()
                stock_entries = sp._auto_add_received_items_to_stock(
                    connection, pr_id, received_items_payload,
                    int(actor['id']), actor['full_name'], now
                )
        elif new_status == 'received':
            connection.execute(
                "UPDATE purchase_request_items SET status = 'received', updated_at = ? WHERE purchase_request_id = ? AND status = 'included_in_request'",
                (now, pr_id)
            )
        ip = str(getattr(handler, 'client_address', ('',))[0] or '')
        _record_purchase_event(
            connection, int(pr['company_id']), 'purchase_request', pr_id, 'status_changed',
            old_status, new_status, str(payload.get('comment') or ''),
            int(actor['id']), actor['full_name'], ip
        )
        connection.commit()
        return send_json(handler, 200, {'ok': True, 'stock_entries': stock_entries})


def handle_post_requests_status(handler, parsed, payload, match):
    require_fields(payload, ['actor_user_id', 'request_id', 'status'])
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed, payload), 'deliveries:create')
        req = connection.execute('SELECT * FROM epi_requests WHERE id = ?', (int(payload['request_id']),)).fetchone()
        if not req:
            raise ValueError('Solicitação não encontrada.')
        from core.auth import ensure_resource_company
        ensure_resource_company(actor, req, 'Solicitação')
        new_status = str(payload.get('status', '')).strip().lower()
        valid = {'solicitado', 'em análise', 'aprovado', 'rejeitado', 'prorrogado', 'separado', 'entregue', 'assinado'}
        if new_status not in valid:
            raise ValueError('Status inválido.')
        if new_status == 'prorrogado' and not str(payload.get('postponed_until') or '').strip():
            raise ValueError('Data de prorrogação obrigatória.')
        postponed_until = str(payload.get('postponed_until') or '').strip()
        now = datetime.now(UTC).isoformat()
        connection.execute(
            (
                "UPDATE epi_requests "
                "SET status = ?, approver_user_id = ?, approver_name = ?, "
                "approved_at = CASE WHEN ? IN ('aprovado','rejeitado','prorrogado') THEN ? ELSE approved_at END, "
                "rejection_reason = CASE WHEN ? = 'rejeitado' THEN ? ELSE rejection_reason END, "
                "postponed_until = CASE WHEN ? = 'prorrogado' THEN ? ELSE postponed_until END, "
                "last_updated_at = ? "
                "WHERE id = ?"
            ),
            (
                new_status,
                int(actor['id']),
                actor['full_name'],
                new_status, now,
                new_status, str(payload.get('rejection_reason', '')).strip(),
                new_status, postponed_until,
                now,
                int(req['id'])
            )
        )
        connection.execute(
            'INSERT INTO epi_request_history (request_id, company_id, status, notes, actor_user_id, actor_name, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)',
            (int(req['id']), int(req['company_id']), new_status, str(payload.get('notes', '')).strip(), int(actor['id']), actor['full_name'], now)
        )
        connection.commit()
        return send_json(handler, 200, {'ok': True})


def handle_post_requests_bulk_status(handler, parsed, payload, match):
    require_fields(payload, ['actor_user_id', 'updates'])
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed, payload), 'deliveries:create')
        updates = payload.get('updates') or []
        if not updates:
            raise ValueError('Nenhuma atualização enviada.')
        valid = {'solicitado', 'em análise', 'aprovado', 'rejeitado', 'prorrogado', 'separado', 'entregue', 'assinado'}
        now = datetime.now(UTC).isoformat()
        from core.auth import ensure_resource_company
        for upd in updates:
            req = connection.execute('SELECT * FROM epi_requests WHERE id = ?', (int(upd['request_id']),)).fetchone()
            if not req:
                continue
            ensure_resource_company(actor, req, 'Solicitação')
            new_status = str(upd.get('status', '')).strip().lower()
            if new_status not in valid:
                continue
            postponed_until = str(upd.get('postponed_until') or '').strip()
            rejection_reason = str(upd.get('rejection_reason') or '').strip()
            connection.execute(
                (
                    "UPDATE epi_requests "
                    "SET status = ?, approver_user_id = ?, approver_name = ?, "
                    "approved_at = CASE WHEN ? IN ('aprovado','rejeitado','prorrogado') THEN ? ELSE approved_at END, "
                    "rejection_reason = CASE WHEN ? = 'rejeitado' THEN ? ELSE rejection_reason END, "
                    "postponed_until = CASE WHEN ? = 'prorrogado' THEN ? ELSE postponed_until END, "
                    "last_updated_at = ? WHERE id = ?"
                ),
                (
                    new_status, int(actor['id']), actor['full_name'],
                    new_status, now,
                    new_status, rejection_reason,
                    new_status, postponed_until,
                    now, int(req['id'])
                )
            )
            connection.execute(
                'INSERT INTO epi_request_history (request_id, company_id, status, notes, actor_user_id, actor_name, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)',
                (int(req['id']), int(req['company_id']), new_status, str(upd.get('notes') or '').strip(), int(actor['id']), actor['full_name'], now)
            )
        connection.commit()
        return send_json(handler, 200, {'ok': True})


def handle_post_feedbacks_status(handler, parsed, payload, match):
    require_fields(payload, ['actor_user_id', 'feedback_id', 'status'])
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed, payload), 'deliveries:view')
        feedback = connection.execute('SELECT * FROM epi_feedbacks WHERE id = ?', (int(payload['feedback_id']),)).fetchone()
        if not feedback:
            raise ValueError('Avaliação não encontrada.')
        from core.auth import ensure_resource_company
        ensure_resource_company(actor, feedback, 'Avaliação')
        status = str(payload.get('status', '')).strip().lower()
        valid_status = {'pendente', 'em análise', 'aprovada', 'rejeitada', 'arquivada'}
        if status not in valid_status:
            raise ValueError('Status inválido para avaliação.')
        now = datetime.now(UTC).isoformat()
        connection.execute(
            (
                'UPDATE epi_feedbacks '
                'SET status = ?, reviewer_user_id = ?, reviewer_name = ?, reviewed_at = ?, updated_at = ? '
                'WHERE id = ?'
            ),
            (status, int(actor['id']), actor['full_name'], now, now, int(payload['feedback_id']))
        )
        connection.execute(
            (
                'INSERT INTO epi_feedback_history (feedback_id, company_id, status, notes, actor_user_id, actor_name, created_at) '
                'VALUES (?, ?, ?, ?, ?, ?, ?)'
            ),
            (int(payload['feedback_id']), int(feedback['company_id']), status, str(payload.get('notes', '')).strip(), int(actor['id']), actor['full_name'], now)
        )
        connection.commit()
        return send_json(handler, 200, {'ok': True})


def handle_put_authorized_supplier(handler, parsed, payload, match):
    supplier_id = int(match.group(1))
    require_fields(payload, ['actor_user_id', 'name'])
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed, payload), PERM_SUPPLIERS_MANAGE)
        company_id = int(actor['company_id'])
        now = datetime.now(UTC).isoformat()
        name = str(payload['name']).strip()
        cnpj = ''.join(ch for ch in str(payload.get('cnpj') or '') if ch.isdigit())
        category = str(payload.get('category') or '').strip()
        contact_email = str(payload.get('contact_email') or '').strip().lower()
        notes = str(payload.get('notes') or '').strip()
        existing = connection.execute(
            'SELECT id FROM authorized_suppliers WHERE id = ? AND company_id = ?',
            (supplier_id, company_id)
        ).fetchone()
        if not existing:
            return send_json(handler, 404, {'error': 'Fornecedor não encontrado.'})
        connection.execute(
            'UPDATE authorized_suppliers SET name = ?, cnpj = ?, category = ?, contact_email = ?, notes = ?, updated_at = ? WHERE id = ?',
            (name, cnpj, category, contact_email, notes, now, supplier_id)
        )
        connection.commit()
        return send_json(handler, 200, {'ok': True})


def handle_delete_purchase_function(handler, parsed, payload, match):
    link_id = int(match.group(1))
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed), PERM_UNIT_LINKS_MANAGE)
        require_purchase_function_admin(actor)
        company_id = int(actor['company_id'])
        link = connection.execute('SELECT * FROM purchase_role_unit_links WHERE id = ?', (link_id,)).fetchone()
        if not link:
            raise ValueError('Vínculo de compras não encontrado.')
        if int(link['company_id']) != company_id:
            raise PermissionError('Vínculo pertence a outra empresa.')
        connection.execute('DELETE FROM purchase_role_unit_links WHERE id = ?', (link_id,))
        connection.commit()
        return send_json(handler, 200, {'ok': True})


def handle_delete_user_unit_link(handler, parsed, payload, match):
    link_id = int(match.group(1))
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed), PERM_UNIT_LINKS_MANAGE)
        company_id = int(actor['company_id'])
        link = connection.execute('SELECT * FROM user_unit_links WHERE id = ?', (link_id,)).fetchone()
        if not link:
            raise ValueError('Vínculo não encontrado.')
        if int(link['company_id']) != company_id:
            raise PermissionError('Vínculo pertence a outra empresa.')
        connection.execute('DELETE FROM user_unit_links WHERE id = ?', (link_id,))
        connection.commit()
        return send_json(handler, 200, {'ok': True})


# ── GET /api/authorized-suppliers ────────────────────────────────────────────

def handle_get_authorized_suppliers(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed), PERM_PURCHASE_REQUESTS_VIEW)
        rows = connection.execute(
            'SELECT * FROM authorized_suppliers WHERE company_id = ? ORDER BY name ASC',
            (int(actor['company_id']),),
        ).fetchall()
        return send_json(handler, 200, {'items': [row_to_dict(r) for r in rows]})


def handle_get_supplier_pos(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed), PERM_PO_VIEW)
        supplier_id = int(match.group(1))
        company_id = int(actor['company_id'])
        supplier = connection.execute(
            'SELECT * FROM authorized_suppliers WHERE id = ? AND company_id = ?',
            (supplier_id, company_id),
        ).fetchone()
        if not supplier:
            return send_json(handler, 404, {'error': 'Fornecedor não encontrado.'})
        sup = row_to_dict(supplier)
        clauses = ['po.company_id = ?']
        params = [company_id]
        if sup.get('cnpj'):
            clauses.append('(po.supplier_cnpj = ? OR LOWER(TRIM(po.supplier)) = ?)')
            params.extend([sup['cnpj'], sup['name'].lower()])
        else:
            clauses.append('LOWER(TRIM(po.supplier)) = ?')
            params.append(sup['name'].lower())
        where_sql = f"WHERE {' AND '.join(clauses)}"
        rows = connection.execute(
            f'SELECT po.*, u.name AS unit_name, '
            f'(SELECT COUNT(*) FROM purchase_order_items poi WHERE poi.purchase_order_id = po.id) AS items_count '
            f'FROM purchase_orders po JOIN units u ON u.id = po.unit_id {where_sql} ORDER BY po.created_at DESC',
            tuple(params),
        ).fetchall()
        return send_json(handler, 200, {'supplier': sup, 'items': [row_to_dict(r) for r in rows]})


def handle_get_company_purchase_config(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        query = parse_qs(parsed.query)
        actor = authorize_action(connection, resolve_actor_user_id(handler, parsed), PERM_PURCHASE_REQUESTS_VIEW)
        raw_cid = str(query.get('company_id', [''])[0] or '').strip()
        if not raw_cid:
            raw_cid = str(actor.get('company_id') or '').strip()
        if not raw_cid or raw_cid == 'None':
            return send_json(handler, 200, {'config': {}})
        cid = int(raw_cid)
        row = connection.execute(
            'SELECT value FROM app_meta WHERE key = ?',
            (f'purchase_config_{cid}',),
        ).fetchone()
        import json as _json
        config = _json.loads(row['value']) if row else {}
        return send_json(handler, 200, {'config': config})


def handle_get_user_unit_links(handler, parsed, payload, match):
    with closing(get_connection()) as connection:
        query = parse_qs(parsed.query)
        target_user_id_str = str(query.get('user_id', [''])[0] or '').strip()
        actor_id = resolve_actor_user_id(handler, parsed)
        if target_user_id_str and str(actor_id) == target_user_id_str:
            actor = authorize_action(connection, actor_id, PERM_PURCHASE_REQUESTS_VIEW)
            company_id = int(actor['company_id'])
            legacy_rows = connection.execute(
                'SELECT uul.*, u.name AS unit_name FROM user_unit_links uul '
                'JOIN units u ON u.id = uul.unit_id '
                'WHERE uul.user_id = ? AND uul.company_id = ? ORDER BY u.name',
                (int(target_user_id_str), company_id),
            ).fetchall()
            items = [row_to_dict(r) for r in legacy_rows]
            seen_unit_ids = {i['unit_id'] for i in items}
            linked_employee_id = actor.get('linked_employee_id')
            if linked_employee_id:
                prl_rows = connection.execute(
                    'SELECT prul.unit_id, u.name AS unit_name FROM purchase_role_unit_links prul '
                    'JOIN units u ON u.id = prul.unit_id '
                    'WHERE prul.employee_id = ? AND prul.company_id = ? ORDER BY u.name',
                    (int(linked_employee_id), company_id),
                ).fetchall()
                for r in prl_rows:
                    if r['unit_id'] not in seen_unit_ids:
                        items.append({'unit_id': r['unit_id'], 'unit_name': r['unit_name'], 'user_id': int(target_user_id_str), 'company_id': company_id})
                        seen_unit_ids.add(r['unit_id'])
            return send_json(handler, 200, {'items': items})
        else:
            actor = authorize_action(connection, actor_id, PERM_UNIT_LINKS_MANAGE)
            company_id = int(actor['company_id'])
            if target_user_id_str:
                rows = connection.execute(
                    'SELECT uul.*, u.name AS unit_name FROM user_unit_links uul '
                    'JOIN units u ON u.id = uul.unit_id '
                    'WHERE uul.user_id = ? AND uul.company_id = ? ORDER BY u.name',
                    (int(target_user_id_str), company_id),
                ).fetchall()
            else:
                rows = connection.execute(
                    'SELECT uul.*, u.name AS unit_name, us.full_name AS user_name, us.role AS user_role '
                    'FROM user_unit_links uul '
                    'JOIN units u ON u.id = uul.unit_id '
                    'JOIN users us ON us.id = uul.user_id '
                    'WHERE uul.company_id = ? ORDER BY us.full_name, u.name',
                    (company_id,),
                ).fetchall()
            return send_json(handler, 200, {'items': [row_to_dict(r) for r in rows]})


# ── Registro ──────────────────────────────────────────────────────────────────

def register_routes(router):
    # GET
    router.register('GET', '/api/requests',                                  handle_get_epi_requests)
    router.register('GET', '/api/authorized-suppliers',                           handle_get_authorized_suppliers)
    router.register('GET', r'^/api/authorized-suppliers/(\d+)/purchase-orders$',  handle_get_supplier_pos, regex=True)
    router.register('GET', '/api/company-purchase-config',                         handle_get_company_purchase_config)
    router.register('GET', '/api/user-unit-links',                                 handle_get_user_unit_links)
    router.register('GET', '/api/purchase-demands',                          handle_get_purchase_demands)
    router.register('GET', '/api/purchase-requests',                         handle_get_purchase_requests)
    router.register('GET', r'^/api/purchase-requests/(\d+)$',                handle_get_purchase_request_detail, regex=True)
    router.register('GET', '/api/purchase-orders',                           handle_get_purchase_orders)
    router.register('GET', r'^/api/purchase-orders/(\d+)$',                  handle_get_purchase_order_detail, regex=True)
    router.register('GET', '/api/purchase-events',                           handle_get_purchase_events)
    router.register('GET', '/api/purchase-functions',                        handle_get_purchase_functions)
    # POST
    router.register('POST', r'^/api/purchase-requests/(\d+)/workflow$',      handle_post_purchase_request_workflow, regex=True)
    router.register('POST', '/api/purchase-requests',                         handle_post_purchase_requests)
    router.register('POST', r'^/api/purchase-requests/(\d+)/review-items$',  handle_post_purchase_request_review_items, regex=True)
    router.register('POST', r'^/api/purchase-requests/(\d+)/status$',        handle_post_purchase_request_status, regex=True)
    router.register('POST', '/api/requests/status',                           handle_post_requests_status)
    router.register('POST', '/api/requests/bulk-status',                      handle_post_requests_bulk_status)
    router.register('POST', '/api/feedbacks/status',                          handle_post_feedbacks_status)
    # PUT
    router.register('PUT',  r'^/api/authorized-suppliers/(\d+)$',            handle_put_authorized_supplier, regex=True)
    # DELETE
    router.register('DELETE', r'^/api/purchase-functions/(\d+)$',            handle_delete_purchase_function, regex=True)
    router.register('DELETE', r'^/api/user-unit-links/(\d+)$',               handle_delete_user_unit_link, regex=True)
