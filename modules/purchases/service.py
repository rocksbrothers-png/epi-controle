"""Serviços do domínio de compras e requisições de EPI."""

from datetime import datetime, timedelta, timezone

from core.auth import ensure_permission, ensure_resource_company
from core.permissions import PERM_PO_APPROVE, PERM_PURCHASE_REQUESTS_UPDATE
from core.roles import normalize_role_name
from epi_backend.db import row_to_dict
from epi_backend.http_utils import structured_log
from epi_backend.purchase_workflow import (
    PURCHASE_STATUS_LABELS as PURCHASE_WORKFLOW_STATUS_LABELS,
    latest_requester_review_origin,
    normalize_purchase_item_approval_decisions,
    resolve_purchase_transition,
    serialize_purchase_event_comment,
    validate_purchase_transition_payload,
)
from modules.stock.service import (
    fetch_epi_size_balance,
    get_unit_stock,
    upsert_unit_stock,
    next_company_qr_sequence,
    build_stock_item_qr,
)

UTC = timezone.utc

PURCHASE_FUNCTION_TYPES = {'buyer', 'approver'}
PURCHASE_FUNCTION_LABELS = {'buyer': 'Comprador', 'approver': 'Aprovador'}


def normalize_purchase_function_type(value):
    normalized = normalize_role_name(value)
    if normalized not in PURCHASE_FUNCTION_TYPES:
        raise ValueError('Função de compras deve ser comprador ou aprovador.')
    return normalized


def get_actor_purchase_unit_scope(connection, actor):
    """Retorna unit_ids para vínculos de Compras via purchase_role_unit_links."""
    if not actor:
        return None
    actor_role = actor.get('role')
    linked_employee_id = actor.get('linked_employee_id')
    if not linked_employee_id or actor_role not in ('buyer', 'approver', 'admin', 'registry_admin', 'general_admin'):
        return None
    function_rows = connection.execute(
        'SELECT unit_id FROM purchase_role_unit_links WHERE employee_id = ? AND role_type = ?',
        (int(linked_employee_id), actor_role if actor_role in PURCHASE_FUNCTION_TYPES else 'buyer')
    ).fetchall()
    unit_ids = [int(r['unit_id']) for r in function_rows]
    return sorted(set(unit_ids)) if unit_ids else None


def actor_company_id_or_query(connection, actor, query):
    if actor.get('role') != 'master_admin':
        return int(actor['company_id'])
    requested = str(query.get('company_id', [''])[0] or '').strip()
    if requested:
        return int(requested)
    first_company = connection.execute('SELECT id FROM companies ORDER BY id ASC LIMIT 1').fetchone()
    if not first_company:
        raise ValueError('Nenhuma empresa cadastrada para consulta.')
    return int(first_company['id'])


def require_purchase_function_admin(actor):
    if actor.get('role') not in ('general_admin', 'registry_admin'):
        raise PermissionError('Somente Administrador Geral ou Administrador de Registro pode gerenciar funções de compras.')


def fetch_purchase_function_links(connection, company_id):
    """Retorna vínculos de função de compra (comprador/aprovador) por unidade.

    Inclui flag has_system_user indicando se o colaborador possui conta de usuário
    ativa com o perfil correspondente.
    """
    rows = connection.execute(
        'SELECT prul.*, employees.name AS employee_name, employees.employee_id_code, '
        'employees.sector AS employee_sector, employees.role_name AS employee_role, '
        'units.name AS unit_name '
        'FROM purchase_role_unit_links prul '
        'JOIN employees ON employees.id = prul.employee_id '
        'JOIN units ON units.id = prul.unit_id '
        'WHERE prul.company_id = ? '
        'ORDER BY employees.name, prul.role_type, units.name',
        (int(company_id),)
    ).fetchall()
    items = []
    for row in rows:
        item = row_to_dict(row)
        item['role_label'] = PURCHASE_FUNCTION_LABELS.get(item.get('role_type'), item.get('role_type'))
        user_check = connection.execute(
            'SELECT id, username FROM users WHERE linked_employee_id = ? AND role = ? AND active = 1 LIMIT 1',
            (item['employee_id'], item.get('role_type'))
        ).fetchone()
        item['has_system_user'] = bool(user_check)
        item['system_user_login'] = str(user_check['username']) if user_check else ''
        items.append(item)
    return items


def fetch_purchase_demands(connection, company_id, scope_unit_id=None):
    """Retorna demandas pendentes: solicitações de colaboradores + EPIs abaixo do estoque mínimo."""
    demands = []
    req_clauses = ["r.status IN ('solicitado', 'aprovado')"]
    req_params = []
    if company_id is not None:
        req_clauses.insert(0, 'r.company_id = ?')
        req_params.append(company_id)
    if scope_unit_id:
        req_clauses.append('r.unit_id = ?')
        req_params.append(int(scope_unit_id))
    req_rows = connection.execute(
        f'SELECT r.id, r.company_id, r.unit_id, r.employee_id, r.epi_id, r.quantity, '
        f'r.glove_size, r.size, r.uniform_size, r.requested_at, r.status, '
        f'emp.name AS employee_name, emp.sector AS employee_sector, emp.role_name AS employee_role, '
        f'ep.name AS epi_name, ep.ca, ep.unit_measure, ep.manufacturer, ep.supplier_company AS supplier, '
        f'u.name AS unit_name, c.name AS company_name '
        f'FROM epi_requests r '
        f'JOIN employees emp ON emp.id = r.employee_id '
        f'JOIN epis ep ON ep.id = r.epi_id '
        f'JOIN units u ON u.id = r.unit_id '
        f'JOIN companies c ON c.id = r.company_id '
        f"WHERE {' AND '.join(req_clauses)} "
        f'ORDER BY r.status DESC, r.requested_at ASC',
        tuple(req_params)
    ).fetchall()
    for row in req_rows:
        d = dict(row)
        d['demand_type'] = 'employee_request'
        demands.append(d)
    stock_clauses = ['ep.active = 1', 'ues.quantity < ep.minimum_stock']
    stock_params = []
    if company_id is not None:
        stock_clauses.insert(0, 'ues.company_id = ?')
        stock_params.append(company_id)
    if scope_unit_id:
        stock_clauses.append('ues.unit_id = ?')
        stock_params.append(int(scope_unit_id))
    stock_rows = connection.execute(
        f'SELECT ues.company_id, ues.unit_id, ues.epi_id, ues.quantity AS current_stock, ep.minimum_stock, '
        f'ep.name AS epi_name, ep.ca, ep.unit_measure, ep.manufacturer, ep.supplier_company AS supplier, '
        f'ep.sector AS employee_sector, ep.glove_size, ep.size, ep.uniform_size, '
        f'u.name AS unit_name, c.name AS company_name '
        f'FROM unit_epi_stock ues '
        f'JOIN epis ep ON ep.id = ues.epi_id '
        f'JOIN units u ON u.id = ues.unit_id '
        f'JOIN companies c ON c.id = ues.company_id '
        f"WHERE {' AND '.join(stock_clauses)} "
        f'ORDER BY (ep.minimum_stock - ues.quantity) DESC',
        tuple(stock_params)
    ).fetchall()
    for row in stock_rows:
        d = dict(row)
        d['demand_type'] = 'low_stock'
        d['quantity_requested'] = max(1, int(row['minimum_stock']) - int(row['current_stock']))
        d['employee_name'] = ''
        d['employee_role'] = ''
        d['employee_sector'] = d.get('employee_sector') or 'Estoque baixo'
        d['sector'] = d['employee_sector']
        d['glove_size'] = d.get('glove_size') or 'N/A'
        d['size'] = d.get('size') or 'N/A'
        d['uniform_size'] = d.get('uniform_size') or 'N/A'
        d['status'] = 'low_stock'
        d['size_balances'] = fetch_epi_size_balance(connection, int(d['company_id']), int(d['unit_id']), int(d['epi_id']))
        demands.append(d)
    return demands


def _record_purchase_event(connection, company_id, entity_type, entity_id, action, status_from, status_to, comment, actor_user_id, actor_name, ip_address='', actor_role='', reason='', destination=''):
    now = datetime.now(UTC).isoformat()
    connection.execute(
        'INSERT INTO purchase_events (company_id, entity_type, entity_id, action, status_from, status_to, comment, actor_user_id, actor_name, actor_role, reason, destination, ip_address, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
        (company_id, entity_type, entity_id, action, status_from, status_to, comment, actor_user_id, actor_name, actor_role, reason, destination, ip_address, now)
    )


def ensure_purchase_request_action_scope(connection, actor, purchase_request, *, actor_operational_unit_id=None):
    ensure_resource_company(actor, purchase_request, 'Requisição')
    if actor.get('role') == 'master_admin':
        return
    scope_unit_id = actor_operational_unit_id(connection, actor) if actor_operational_unit_id is not None else None
    if scope_unit_id and int(purchase_request['unit_id']) != int(scope_unit_id):
        raise PermissionError('Requisição fora da unidade operacional do usuário.')
    purchase_scope_units = get_actor_purchase_unit_scope(connection, actor)
    if actor.get('role') in ('buyer', 'approver'):
        if not purchase_scope_units:
            raise PermissionError('Usuário sem unidade de compras vinculada.')
        if int(purchase_request['unit_id']) not in set(int(uid) for uid in purchase_scope_units):
            raise PermissionError('Requisição fora das unidades de compras vinculadas ao usuário.')


def ensure_purchase_workflow_permission(actor, permission_group):
    if permission_group == 'approve':
        ensure_permission(actor, PERM_PO_APPROVE)
        return
    ensure_permission(actor, PERM_PURCHASE_REQUESTS_UPDATE)


def _format_purchase_item_decision_comment(item, decision, totals=None):
    quantity = int(item.get('quantity_requested') or item.get('quantity') or 1)
    unit_price = float(item.get('unit_price') or 0)
    total_price = float(item.get('total_price') or (unit_price * quantity))
    parts = [
        f"Item #{item.get('id')}",
        f"EPI: {item.get('epi_name') or item.get('epi_display_name') or ''}",
        f"CA: {item.get('ca') or item.get('epi_ca') or ''}",
        f"Qtd: {quantity}",
        f"Valor unitário: {unit_price:.2f}",
        f"Total item: {total_price:.2f}",
        f"Decisão: {'Aprovado' if decision.get('approved') else 'Reprovado'}",
    ]
    if not decision.get('approved'):
        parts.append(f"Motivo: {decision.get('reason') or ''}")
        if decision.get('comment'):
            parts.append(f"Observação: {decision.get('comment')}")
    if totals:
        parts.extend([
            f"Total aprovado: {float(totals.get('approved_total') or 0):.2f}",
            f"Total reprovado: {float(totals.get('rejected_total') or 0):.2f}",
            f"Total geral: {float(totals.get('grand_total') or 0):.2f}",
        ])
    return ' | '.join(parts)


def apply_purchase_request_item_approval(connection, actor, pr_id, payload, ip_address='', transition=None, *, actor_operational_unit_id=None):
    purchase_request = connection.execute('SELECT * FROM purchase_requests WHERE id = ?', (int(pr_id),)).fetchone()
    if not purchase_request:
        raise ValueError('Requisição não encontrada.')
    pr = row_to_dict(purchase_request)
    ensure_purchase_request_action_scope(connection, actor, pr, actor_operational_unit_id=actor_operational_unit_id)
    if transition is None:
        transition = resolve_purchase_transition(pr.get('status'), 'approve')
    ensure_purchase_workflow_permission(actor, transition.get('permission'))
    item_rows = connection.execute(
        'SELECT pri.*, e.name AS epi_display_name, e.ca AS epi_ca, u.name AS unit_name '
        'FROM purchase_request_items pri '
        'JOIN epis e ON e.id = pri.epi_id '
        'JOIN units u ON u.id = pri.unit_id '
        'WHERE pri.purchase_request_id = ? ORDER BY pri.id',
        (int(pr_id),)
    ).fetchall()
    items = [row_to_dict(row) for row in item_rows]
    decisions, status_to, totals = normalize_purchase_item_approval_decisions(items, payload)
    now = datetime.now(UTC).isoformat()
    summary_parts = []
    for decision in decisions:
        item = decision['item']
        item_id = int(decision['item_id'])
        previous_status = str(item.get('status') or '')
        new_status = 'approved' if decision.get('approved') else 'rejected'
        comment = _format_purchase_item_decision_comment(item, decision)
        if decision.get('approved'):
            connection.execute(
                """
                UPDATE purchase_request_items
                SET status = 'approved', quantity_approved = quantity_requested,
                    rejection_reason = '', rejection_comment = '',
                    approval_decided_by_user_id = ?, approval_decided_by_name = ?, approval_decided_at = ?,
                    updated_at = ?
                WHERE purchase_request_id = ? AND id = ?
                """,
                (int(actor['id']), actor['full_name'], now, now, int(pr_id), item_id),
            )
        else:
            note_suffix = f"Reprovado: {decision.get('reason') or ''}"
            if decision.get('comment'):
                note_suffix += f" — {decision.get('comment')}"
            connection.execute(
                """
                UPDATE purchase_request_items
                SET status = 'rejected', quantity_approved = 0,
                    rejection_reason = ?, rejection_comment = ?,
                    approval_decided_by_user_id = ?, approval_decided_by_name = ?, approval_decided_at = ?,
                    notes = trim(COALESCE(NULLIF(notes, ''), '') || CASE WHEN COALESCE(NULLIF(notes, ''), '') = '' THEN '' ELSE ' | ' END || ?),
                    updated_at = ?
                WHERE purchase_request_id = ? AND id = ?
                """,
                (decision.get('reason') or '', decision.get('comment') or '', int(actor['id']), actor['full_name'], now, note_suffix, now, int(pr_id), item_id),
            )
        _record_purchase_event(
            connection,
            int(pr['company_id']),
            'purchase_request_item',
            item_id,
            'item_approval_decision',
            previous_status,
            new_status,
            comment,
            int(actor['id']),
            actor['full_name'],
            ip_address,
            actor.get('role') or '',
            decision.get('reason') or '',
            'closed' if decision.get('approved') else 'rejected',
        )
        summary_parts.append(_format_purchase_item_decision_comment(item, decision))
    connection.execute(
        'UPDATE purchase_requests SET status = ?, updated_at = ? WHERE id = ?',
        (status_to, now, int(pr_id))
    )
    request_comment = 'Decisão por item | Resumo da aprovação por item: ' + ' || '.join(summary_parts)
    request_comment += (
        f" || Totais: aprovado {totals['approved_total']:.2f} ({totals['approved_quantity']} un.), "
        f"reprovado {totals['rejected_total']:.2f} ({totals['rejected_quantity']} un.), "
        f"geral {totals['grand_total']:.2f}"
    )
    _record_purchase_event(
        connection,
        int(pr['company_id']),
        'purchase_request',
        int(pr_id),
        'approve',
        transition['status_from'],
        status_to,
        request_comment,
        int(actor['id']),
        actor['full_name'],
        ip_address,
        actor.get('role') or '',
        '',
        'closed',
    )
    structured_log(
        'info',
        'purchase.workflow.item_approval_completed',
        purchase_request_id=int(pr_id),
        status_from=transition['status_from'],
        status_to=status_to,
        actor_user_id=int(actor['id']),
        actor_role=actor.get('role'),
        approved_count=totals['approved_count'],
        rejected_count=totals['rejected_count'],
        approved_total=totals['approved_total'],
        rejected_total=totals['rejected_total'],
    )
    return {
        'ok': True,
        'id': int(pr_id),
        'status': status_to,
        'status_label': PURCHASE_WORKFLOW_STATUS_LABELS.get(status_to, status_to),
        'action': 'approve',
        'totals': totals,
        'decisions': [
            {
                'item_id': int(decision['item_id']),
                'status': 'approved' if decision.get('approved') else 'rejected',
                'reason': decision.get('reason') or '',
                'comment': decision.get('comment') or '',
            }
            for decision in decisions
        ],
    }


def apply_purchase_request_workflow_action(connection, actor, pr_id, payload, ip_address='', *, actor_operational_unit_id=None):
    purchase_request = connection.execute('SELECT * FROM purchase_requests WHERE id = ?', (int(pr_id),)).fetchone()
    if not purchase_request:
        raise ValueError('Requisição não encontrada.')
    pr = row_to_dict(purchase_request)
    ensure_purchase_request_action_scope(connection, actor, pr, actor_operational_unit_id=actor_operational_unit_id)
    events = [row_to_dict(row) for row in connection.execute(
        'SELECT * FROM purchase_events WHERE entity_type = ? AND entity_id = ? ORDER BY created_at DESC, id DESC',
        ('purchase_request', int(pr_id))
    ).fetchall()]
    transition = resolve_purchase_transition(
        pr.get('status'),
        payload.get('action'),
        requester_review_origin=latest_requester_review_origin(events),
    )
    ensure_purchase_workflow_permission(actor, transition.get('permission'))
    reason, comment = validate_purchase_transition_payload(
        transition,
        reason=payload.get('reason'),
        comment=payload.get('comment'),
    )
    requested_changes = payload.get('requested_changes') or []
    if isinstance(requested_changes, str):
        requested_changes = [requested_changes]
    affected_item_ids = [int(item_id) for item_id in (payload.get('item_ids') or []) if str(item_id).isdigit()]
    if affected_item_ids:
        requested_changes.append('Itens afetados: ' + ', '.join(str(item_id) for item_id in affected_item_ids))
    event_comment = serialize_purchase_event_comment(reason, comment, requested_changes)
    now = datetime.now(UTC).isoformat()
    status_to = transition['status_to']
    if transition['action'] == 'approve':
        return apply_purchase_request_item_approval(
            connection, actor, pr_id, payload, ip_address, transition,
            actor_operational_unit_id=actor_operational_unit_id,
        )
    connection.execute(
        'UPDATE purchase_requests SET status = ?, updated_at = ? WHERE id = ?',
        (status_to, now, int(pr_id))
    )
    _record_purchase_event(
        connection,
        int(pr['company_id']),
        'purchase_request',
        int(pr_id),
        transition['action'],
        transition['status_from'],
        status_to,
        event_comment,
        int(actor['id']),
        actor['full_name'],
        ip_address,
        actor.get('role') or '',
        reason,
        transition.get('destination') or '',
    )
    structured_log(
        'info',
        'purchase.workflow.transition',
        purchase_request_id=int(pr_id),
        action=transition['action'],
        status_from=transition['status_from'],
        status_to=transition['status_to'],
        actor_user_id=int(actor['id']),
        actor_role=actor.get('role'),
        destination=transition.get('destination') or '',
    )
    if transition.get('destination') == 'buyer':
        structured_log('info', 'purchase.workflow.notify_buyer', purchase_request_id=int(pr_id), reason=reason)
    elif transition.get('destination') == 'requester':
        structured_log('info', 'purchase.workflow.notify_requester', purchase_request_id=int(pr_id), reason=reason)
    elif transition.get('destination') == 'approver':
        structured_log('info', 'purchase.workflow.notify_approver', purchase_request_id=int(pr_id))
    return {
        'ok': True,
        'id': int(pr_id),
        'status': status_to,
        'status_label': PURCHASE_WORKFLOW_STATUS_LABELS.get(status_to, status_to),
        'action': transition['action'],
    }


def approved_purchase_request_items_for_po(connection, pr_id, items):
    approved_rows = connection.execute(
        "SELECT * FROM purchase_request_items WHERE purchase_request_id = ? AND status = 'approved'",
        (int(pr_id),),
    ).fetchall()
    approved_items = {int(row['id']): row_to_dict(row) for row in approved_rows}
    if not approved_items:
        raise ValueError('Requisição sem itens aprovados para gerar PO.')
    for item in items or []:
        pr_item_id = int(item['purchase_request_item_id']) if item.get('purchase_request_item_id') else 0
        if not pr_item_id:
            raise ValueError('PO vinculada a requisição aprovada deve informar o item aprovado da requisição.')
        if pr_item_id not in approved_items:
            raise ValueError('Somente itens aprovados podem ser incluídos na PO.')
    return approved_items


def _purchase_request_items_signature(items):
    normalized = []
    for item in items or []:
        normalized.append((
            int(item.get('epi_id') or 0),
            int(item.get('quantity_requested') or item.get('quantity') or 1),
            int(item.get('employee_id') or 0),
            str(item.get('origin') or 'stock_minimum'),
            str(item.get('glove_size') or 'N/A'),
            str(item.get('size') or 'N/A'),
            str(item.get('uniform_size') or 'N/A'),
        ))
    return sorted(normalized)


def find_recent_duplicate_purchase_request(connection, actor, unit_id, title, items, now):
    cutoff = (datetime.fromisoformat(now) - timedelta(seconds=60)).isoformat()
    expected_signature = _purchase_request_items_signature(items)
    candidates = connection.execute(
        "SELECT * FROM purchase_requests WHERE company_id = ? AND unit_id = ? AND created_by_user_id = ? AND title = ? AND created_at >= ? ORDER BY id DESC LIMIT 5",
        (int(actor['company_id']), int(unit_id), int(actor['id']), title, cutoff),
    ).fetchall()
    for candidate in candidates:
        rows = connection.execute(
            'SELECT epi_id, quantity_requested, employee_id, origin, glove_size, size, uniform_size '
            'FROM purchase_request_items WHERE purchase_request_id = ?',
            (int(candidate['id']),)
        ).fetchall()
        existing = [row_to_dict(row) for row in rows]
        if _purchase_request_items_signature(existing) == expected_signature:
            return int(candidate['id'])
    return None


def generate_po_number(connection, company_id):
    year = datetime.now(UTC).year
    prefix = f'PO-{year}-'
    row = connection.execute(
        "SELECT MAX(CAST(SUBSTR(po_number, ?) AS INTEGER)) AS last_seq FROM purchase_orders WHERE company_id = ? AND po_number LIKE ?",
        (len(prefix) + 1, company_id, f'{prefix}%')
    ).fetchone()
    last_seq = int(row['last_seq'] or 0) if row else 0
    return f'{prefix}{last_seq + 1:04d}'


def _auto_add_received_items_to_stock(connection, pr_id, received_item_flags, actor_id, actor_name, now):
    """Adds received EPI items to stock automatically after conferência."""
    from modules.deliveries.service import ensure_stock_movement_size_columns
    if received_item_flags:
        received_ids = {int(f['id']) for f in received_item_flags if f.get('received')}
    else:
        rows = connection.execute(
            "SELECT id FROM purchase_request_items WHERE purchase_request_id = ? AND status = 'received'",
            (pr_id,)
        ).fetchall()
        received_ids = {int(r['id']) for r in rows}
    if not received_ids:
        return 0
    placeholders = ','.join('?' for _ in received_ids)
    pr_items = [row_to_dict(r) for r in connection.execute(
        f'SELECT * FROM purchase_request_items WHERE purchase_request_id = ? AND id IN ({placeholders})',
        (pr_id, *received_ids)
    ).fetchall()]
    total_units = 0
    ensure_stock_movement_size_columns(connection)
    for item in pr_items:
        epi_id = int(item['epi_id'])
        unit_id = int(item['unit_id'])
        company_id = int(item['company_id'])
        pri_id = int(item['id'])
        po_item = connection.execute(
            'SELECT * FROM purchase_order_items WHERE purchase_request_item_id = ? ORDER BY id DESC LIMIT 1',
            (pri_id,)
        ).fetchone()
        if po_item:
            quantity = int(po_item.get('quantity_received') or 0)
        else:
            quantity = int(item.get('quantity_requested') or 0)
        if quantity <= 0:
            continue
        glove_size = str(item.get('glove_size') or 'N/A')
        size = str(item.get('size') or 'N/A')
        uniform_size = str(item.get('uniform_size') or 'N/A')
        stock_row = get_unit_stock(connection, company_id, unit_id, epi_id)
        previous_stock = int((stock_row or {}).get('quantity') or 0)
        new_stock = previous_stock + quantity
        movement_cursor = connection.execute(
            'INSERT INTO stock_movements ('
            'company_id, unit_id, epi_id, movement_type, quantity, previous_stock, new_stock, '
            'source_type, source_id, notes, actor_user_id, actor_name, created_at, glove_size, size, uniform_size'
            ') VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (
                company_id, unit_id, epi_id, 'in', quantity, previous_stock, new_stock,
                'purchase_request', pri_id,
                f'Entrada automática — Conferência Requisição #{pr_id}',
                actor_id, actor_name, now, glove_size, size, uniform_size
            )
        )
        movement_id = int(movement_cursor.lastrowid)
        upsert_unit_stock(connection, company_id, unit_id, epi_id, new_stock)
        for _ in range(quantity):
            seq_value = next_company_qr_sequence(connection, company_id)
            qr_value = build_stock_item_qr(company_id, unit_id, seq_value)
            connection.execute(
                'INSERT INTO epi_stock_items ('
                'company_id, unit_id, epi_id, glove_size, size, uniform_size, qr_sequence, qr_code_value, status, '
                'stock_movement_id, lot_code, manufacture_date, label_measure, label_printer_name, label_print_format, '
                'generated_by_user_id, created_at, updated_at'
                ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'in_stock', ?, '', '', 'unidade', '', '', ?, ?, ?)",
                (
                    company_id, unit_id, epi_id, glove_size, size, uniform_size,
                    seq_value, qr_value, movement_id,
                    actor_id, now, now
                )
            )
        total_units += quantity
        epi_req_id = item.get('epi_request_id')
        if epi_req_id:
            connection.execute(
                "UPDATE epi_requests SET status = 'separado', last_updated_at = ? "
                "WHERE id = ? AND status NOT IN ('entregue', 'cancelado', 'rejeitado')",
                (now, int(epi_req_id))
            )
    return total_units


# ── Query / fetch functions ────────────────────────────────────────────────────

def fetch_epi_requests(connection, company_filter, scope_unit_id, purchase_scope):
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
        'SELECT r.*, employees.name AS employee_name, employees.employee_id_code, '
        'employees.sector AS employee_sector, employees.role_name AS employee_role, '
        'units.name AS unit_name, '
        'epis.name AS epi_name, epis.ca, epis.unit_measure '
        'FROM epi_requests r '
        'JOIN employees ON employees.id = r.employee_id '
        'JOIN units ON units.id = r.unit_id '
        'JOIN epis ON epis.id = r.epi_id '
        f'{final_where} '
        'ORDER BY r.requested_at DESC, r.id DESC',
        tuple(params),
    ).fetchall()
    return [row_to_dict(r) for r in rows]


def fetch_purchase_requests(connection, company_id, scope_unit_id, purchase_scope_units, status_filter=None):
    clauses, params = ['pr.company_id = ?'], [company_id]
    if scope_unit_id:
        clauses.append('pr.unit_id = ?')
        params.append(int(scope_unit_id))
    elif purchase_scope_units:
        placeholders = ','.join(['?'] * len(purchase_scope_units))
        clauses.append(f'pr.unit_id IN ({placeholders})')
        params.extend(purchase_scope_units)
    if status_filter:
        clauses.append('pr.status = ?')
        params.append(status_filter)
    where_sql = f"WHERE {' AND '.join(clauses)}"
    rows = connection.execute(
        f'SELECT pr.*, u.name AS unit_name, '
        f'(SELECT COUNT(*) FROM purchase_request_items pri WHERE pri.purchase_request_id = pr.id) AS items_count '
        f'FROM purchase_requests pr JOIN units u ON u.id = pr.unit_id {where_sql} ORDER BY pr.created_at DESC',
        tuple(params),
    ).fetchall()
    return [row_to_dict(r) for r in rows]


def get_purchase_request_detail(connection, pr_id):
    """Returns (pr_dict, items, events) or (None, [], []) if not found."""
    pr = connection.execute(
        'SELECT pr.*, u.name AS unit_name FROM purchase_requests pr '
        'JOIN units u ON u.id = pr.unit_id WHERE pr.id = ?',
        (pr_id,),
    ).fetchone()
    if not pr:
        return None, [], []
    items = connection.execute(
        'SELECT pri.*, e.name AS epi_display_name, e.ca AS epi_ca, u.name AS unit_name '
        'FROM purchase_request_items pri '
        'JOIN epis e ON e.id = pri.epi_id '
        'JOIN units u ON u.id = pri.unit_id '
        'WHERE pri.purchase_request_id = ? ORDER BY pri.id',
        (pr_id,),
    ).fetchall()
    events = connection.execute(
        'SELECT * FROM purchase_events WHERE entity_type = ? AND entity_id = ? ORDER BY created_at DESC, id DESC',
        ('purchase_request', pr_id),
    ).fetchall()
    return row_to_dict(pr), [row_to_dict(i) for i in items], [row_to_dict(e) for e in events]


def fetch_purchase_orders(connection, company_id, scope_unit_id, purchase_scope_units, status_filter=None):
    clauses, params = ['po.company_id = ?'], [company_id]
    if scope_unit_id:
        clauses.append('po.unit_id = ?')
        params.append(int(scope_unit_id))
    elif purchase_scope_units:
        placeholders = ','.join(['?'] * len(purchase_scope_units))
        clauses.append(f'po.unit_id IN ({placeholders})')
        params.extend(purchase_scope_units)
    if status_filter:
        clauses.append('po.status = ?')
        params.append(status_filter)
    where_sql = f"WHERE {' AND '.join(clauses)}"
    rows = connection.execute(
        f'SELECT po.*, u.name AS unit_name, '
        f'(SELECT COUNT(*) FROM purchase_order_items poi WHERE poi.purchase_order_id = po.id) AS items_count '
        f'FROM purchase_orders po JOIN units u ON u.id = po.unit_id {where_sql} ORDER BY po.created_at DESC',
        tuple(params),
    ).fetchall()
    return [row_to_dict(r) for r in rows]


def get_purchase_order_detail(connection, po_id):
    """Returns (po_dict, items, files, events) or (None, [], [], []) if not found."""
    po = connection.execute(
        'SELECT po.*, u.name AS unit_name FROM purchase_orders po '
        'JOIN units u ON u.id = po.unit_id WHERE po.id = ?',
        (po_id,),
    ).fetchone()
    if not po:
        return None, [], [], []
    items = connection.execute(
        'SELECT poi.* FROM purchase_order_items poi WHERE poi.purchase_order_id = ?', (po_id,)
    ).fetchall()
    files = connection.execute(
        'SELECT id, file_name, file_type, uploaded_by_name, created_at '
        'FROM purchase_order_files WHERE purchase_order_id = ?',
        (po_id,),
    ).fetchall()
    events = connection.execute(
        'SELECT * FROM purchase_events WHERE entity_type = ? AND entity_id = ? ORDER BY created_at DESC',
        ('purchase_order', po_id),
    ).fetchall()
    return row_to_dict(po), [row_to_dict(i) for i in items], [row_to_dict(f) for f in files], [row_to_dict(e) for e in events]


def fetch_purchase_events(connection, company_id, entity_type=None, entity_id=None):
    clauses, params = ['company_id = ?'], [company_id]
    if entity_type:
        clauses.append('entity_type = ?')
        params.append(entity_type)
    if entity_id:
        clauses.append('entity_id = ?')
        params.append(int(entity_id))
    where_sql = f"WHERE {' AND '.join(clauses)}"
    rows = connection.execute(
        f'SELECT * FROM purchase_events {where_sql} ORDER BY created_at DESC LIMIT 200',
        tuple(params),
    ).fetchall()
    return [row_to_dict(r) for r in rows]


def fetch_authorized_suppliers(connection, company_id):
    rows = connection.execute(
        'SELECT * FROM authorized_suppliers WHERE company_id = ? ORDER BY name ASC',
        (int(company_id),),
    ).fetchall()
    return [row_to_dict(r) for r in rows]


def fetch_supplier_purchase_orders(connection, company_id, supplier_id):
    """Returns (supplier_dict, po_list) or (None, None) if supplier not found."""
    supplier = connection.execute(
        'SELECT * FROM authorized_suppliers WHERE id = ? AND company_id = ?',
        (supplier_id, company_id),
    ).fetchone()
    if not supplier:
        return None, None
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
    return sup, [row_to_dict(r) for r in rows]


def get_company_purchase_config(connection, company_id):
    import json as _json
    row = connection.execute(
        'SELECT value FROM app_meta WHERE key = ?',
        (f'purchase_config_{int(company_id)}',),
    ).fetchone()
    return _json.loads(row['value']) if row else {}


def fetch_user_unit_links(connection, company_id, target_user_id, linked_employee_id=None, is_self=False):
    """Returns unit links for a buyer/approver from purchase_role_unit_links.

    Admin path (is_self=False) returns empty — user_unit_links was dropped in Phase 26.
    """
    if is_self and linked_employee_id:
        rows = connection.execute(
            'SELECT prul.unit_id, u.name AS unit_name FROM purchase_role_unit_links prul '
            'JOIN units u ON u.id = prul.unit_id '
            'WHERE prul.employee_id = ? AND prul.company_id = ? ORDER BY u.name',
            (int(linked_employee_id), company_id),
        ).fetchall()
        return [
            {'unit_id': r['unit_id'], 'unit_name': r['unit_name'],
             'user_id': target_user_id, 'company_id': company_id}
            for r in rows
        ]
    return []


# ── Mutation functions ─────────────────────────────────────────────────────────

def create_purchase_request(connection, actor, unit_id, items, title, notes, ip_address, *, get_epi_by_id_fn):
    """Inserts a new purchase request with items. Returns {ok, id} or {ok, id, duplicate: True}."""
    company_id = int(actor['company_id'])
    now = datetime.now(UTC).isoformat()
    duplicate_id = find_recent_duplicate_purchase_request(connection, actor, unit_id, title, items, now)
    if duplicate_id:
        structured_log('info', 'purchase.request.duplicate_recent_reused', purchase_request_id=duplicate_id, actor_user_id=int(actor['id']))
        return {'ok': True, 'id': duplicate_id, 'duplicate': True}
    cursor = connection.execute(
        "INSERT INTO purchase_requests (company_id, unit_id, status, title, notes, created_by_user_id, created_by_name, created_at, updated_at) VALUES (?, ?, 'open', ?, ?, ?, ?, ?, ?)",
        (company_id, unit_id, title, notes, int(actor['id']), actor['full_name'], now, now)
    )
    pr_id = cursor.lastrowid
    epi_request_ids_to_lock = []
    for item in items:
        epi = get_epi_by_id_fn(connection, int(item['epi_id']))
        if not epi:
            raise ValueError(f"EPI {item['epi_id']} não encontrado.")
        connection.execute(
            'INSERT INTO purchase_request_items '
            '(purchase_request_id, company_id, unit_id, epi_id, epi_name, ca, unit_measure, '
            'manufacturer, supplier, glove_size, size, uniform_size, quantity_requested, origin, '
            'employee_id, employee_name, employee_sector, employee_role, epi_request_id, status, notes, created_at, updated_at) '
            'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (
                pr_id, company_id, unit_id, int(item['epi_id']), epi['name'], epi['ca'], epi['unit_measure'],
                str(item.get('manufacturer') or epi.get('manufacturer') or ''),
                str(item.get('supplier') or epi.get('supplier_company') or ''),
                str(item.get('glove_size') or 'N/A'), str(item.get('size') or 'N/A'), str(item.get('uniform_size') or 'N/A'),
                int(item.get('quantity_requested') or 1), str(item.get('origin') or 'stock_minimum'),
                int(item['employee_id']) if item.get('employee_id') else None,
                str(item.get('employee_name') or ''), str(item.get('employee_sector') or ''), str(item.get('employee_role') or ''),
                int(item['epi_request_id']) if item.get('epi_request_id') else None,
                'included_in_request', str(item.get('notes') or ''), now, now,
            )
        )
        if item.get('epi_request_id'):
            epi_request_ids_to_lock.append(int(item['epi_request_id']))
    for epi_req_id in epi_request_ids_to_lock:
        connection.execute("UPDATE epi_requests SET status = 'em análise', last_updated_at = ? WHERE id = ?", (now, epi_req_id))
    _record_purchase_event(connection, company_id, 'purchase_request', pr_id, 'created', '', 'open', '', int(actor['id']), actor['full_name'], ip_address)
    return {'ok': True, 'id': pr_id}


def review_purchase_request_items(connection, actor, pr, updates, remove_ids, add_items, notes, reason, ip_address, *, get_epi_by_id_fn):
    """Applies requester corrections to PR items. Returns list of affected item ids."""
    pr_id = int(pr['id'])
    now = datetime.now(UTC).isoformat()
    affected = []
    for item in updates or []:
        item_id = int(item.get('id') or 0)
        qty = int(item.get('quantity_requested') or 1)
        if item_id <= 0 or qty <= 0:
            continue
        connection.execute(
            "UPDATE purchase_request_items SET quantity_requested = ?, notes = ?, updated_at = ? "
            "WHERE id = ? AND purchase_request_id = ? AND status NOT IN ('approved', 'ordered', 'received', 'closed')",
            (qty, str(item.get('notes') or '').strip(), now, item_id, pr_id)
        )
        affected.append(item_id)
    if remove_ids:
        placeholders = ','.join('?' for _ in remove_ids)
        connection.execute(
            f"DELETE FROM purchase_request_items WHERE purchase_request_id = ? AND id IN ({placeholders}) "
            f"AND status NOT IN ('approved', 'ordered', 'received', 'closed')",
            (pr_id, *remove_ids)
        )
        affected.extend(remove_ids)
    for item in add_items or []:
        epi = get_epi_by_id_fn(connection, int(item.get('epi_id') or 0))
        if not epi:
            raise ValueError(f"EPI {item.get('epi_id')} não encontrado.")
        qty = int(item.get('quantity_requested') or 1)
        if qty <= 0:
            raise ValueError('Quantidade inválida.')
        cursor = connection.execute(
            'INSERT INTO purchase_request_items '
            '(purchase_request_id, company_id, unit_id, epi_id, epi_name, ca, unit_measure, '
            'manufacturer, supplier, glove_size, size, uniform_size, quantity_requested, origin, '
            'employee_id, employee_name, employee_sector, employee_role, epi_request_id, status, notes, created_at, updated_at) '
            'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (
                pr_id, int(pr['company_id']), int(pr['unit_id']), int(epi['id']), epi['name'], epi['ca'], epi['unit_measure'],
                str(item.get('manufacturer') or epi.get('manufacturer') or ''),
                str(item.get('supplier') or epi.get('supplier_company') or ''),
                str(item.get('glove_size') or 'N/A'), str(item.get('size') or 'N/A'), str(item.get('uniform_size') or 'N/A'),
                qty, str(item.get('origin') or 'manual'),
                int(item['employee_id']) if item.get('employee_id') else None,
                str(item.get('employee_name') or ''), str(item.get('employee_sector') or ''), str(item.get('employee_role') or ''),
                int(item['epi_request_id']) if item.get('epi_request_id') else None,
                'included_in_request', str(item.get('notes') or ''), now, now,
            )
        )
        affected.append(int(cursor.lastrowid))
    connection.execute(
        "UPDATE purchase_requests SET notes = COALESCE(NULLIF(?, ''), notes), updated_at = ? WHERE id = ?",
        (notes, now, pr_id)
    )
    _record_purchase_event(
        connection, int(pr['company_id']), 'purchase_request', pr_id, 'requester_review_saved',
        str(pr['status']), str(pr['status']),
        'Itens afetados: ' + ', '.join(str(iid) for iid in affected),
        int(actor['id']), actor['full_name'], ip_address,
        actor.get('role') or '', reason, 'requester',
    )
    return affected


_PURCHASE_REQUEST_VALID_STATUSES = {
    'draft', 'open', 'sent_to_buyer', 'quoted', 'pending_approval', 'partially_approved',
    'approved', 'rejected', 'returned_to_buyer', 'waiting_buyer_correction', 'buyer_resubmitted',
    'waiting_requester_correction', 'requester_resubmitted', 'postponed', 'po_generated',
    'received', 'checked', 'closed', 'cancelled',
}


def update_purchase_request_status(connection, actor, pr, new_status, comment, postponed_until, received_items_payload, ip_address):
    """Updates PR status with optional item-level logic. Returns count of auto stock entries."""
    if new_status not in _PURCHASE_REQUEST_VALID_STATUSES:
        raise ValueError('Status inválido para requisição de compra.')
    pr_id = int(pr['id'])
    old_status = str(pr['status'])
    now = datetime.now(UTC).isoformat()
    extra = {}
    if new_status == 'sent_to_buyer':
        extra['sent_to_buyer_at'] = now
    elif new_status in ('closed', 'cancelled'):
        extra['closed_at'] = now
    elif new_status == 'postponed' and postponed_until:
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
                "UPDATE purchase_request_items SET status = 'checked', updated_at = ? "
                "WHERE purchase_request_id = ? AND status NOT IN ('not_received', 'closed')",
                (now, pr_id)
            )
        if old_status == 'received':
            stock_entries = _auto_add_received_items_to_stock(
                connection, pr_id, received_items_payload, int(actor['id']), actor['full_name'], now
            )
    elif new_status == 'received':
        connection.execute(
            "UPDATE purchase_request_items SET status = 'received', updated_at = ? "
            "WHERE purchase_request_id = ? AND status = 'included_in_request'",
            (now, pr_id)
        )
    _record_purchase_event(
        connection, int(pr['company_id']), 'purchase_request', pr_id, 'status_changed',
        old_status, new_status, comment, int(actor['id']), actor['full_name'], ip_address
    )
    return stock_entries


_EPI_REQUEST_VALID_STATUSES = {'solicitado', 'em análise', 'aprovado', 'rejeitado', 'prorrogado', 'separado', 'entregue', 'assinado'}


def update_epi_request_status(connection, actor, req, new_status, postponed_until, rejection_reason, notes):
    """Updates a single epi_request status and inserts a history record."""
    if new_status not in _EPI_REQUEST_VALID_STATUSES:
        raise ValueError('Status inválido.')
    if new_status == 'prorrogado' and not postponed_until:
        raise ValueError('Data de prorrogação obrigatória.')
    now = datetime.now(UTC).isoformat()
    connection.execute(
        "UPDATE epi_requests "
        "SET status = ?, approver_user_id = ?, approver_name = ?, "
        "approved_at = CASE WHEN ? IN ('aprovado','rejeitado','prorrogado') THEN ? ELSE approved_at END, "
        "rejection_reason = CASE WHEN ? = 'rejeitado' THEN ? ELSE rejection_reason END, "
        "postponed_until = CASE WHEN ? = 'prorrogado' THEN ? ELSE postponed_until END, "
        "last_updated_at = ? WHERE id = ?",
        (
            new_status, int(actor['id']), actor['full_name'],
            new_status, now,
            new_status, rejection_reason,
            new_status, postponed_until,
            now, int(req['id']),
        )
    )
    connection.execute(
        'INSERT INTO epi_request_history (request_id, company_id, status, notes, actor_user_id, actor_name, created_at) '
        'VALUES (?, ?, ?, ?, ?, ?, ?)',
        (int(req['id']), int(req['company_id']), new_status, notes, int(actor['id']), actor['full_name'], now)
    )


def bulk_update_epi_request_statuses(connection, actor, updates):
    """Bulk-updates epi_request statuses, skipping missing or invalid records."""
    now = datetime.now(UTC).isoformat()
    for upd in updates or []:
        _req = connection.execute('SELECT * FROM epi_requests WHERE id = ?', (int(upd['request_id']),)).fetchone()
        if not _req:
            continue
        req = row_to_dict(_req)
        ensure_resource_company(actor, req, 'Solicitação')
        new_status = str(upd.get('status', '')).strip().lower()
        if new_status not in _EPI_REQUEST_VALID_STATUSES:
            continue
        postponed_until = str(upd.get('postponed_until') or '').strip()
        rejection_reason = str(upd.get('rejection_reason') or '').strip()
        connection.execute(
            "UPDATE epi_requests "
            "SET status = ?, approver_user_id = ?, approver_name = ?, "
            "approved_at = CASE WHEN ? IN ('aprovado','rejeitado','prorrogado') THEN ? ELSE approved_at END, "
            "rejection_reason = CASE WHEN ? = 'rejeitado' THEN ? ELSE rejection_reason END, "
            "postponed_until = CASE WHEN ? = 'prorrogado' THEN ? ELSE postponed_until END, "
            "last_updated_at = ? WHERE id = ?",
            (
                new_status, int(actor['id']), actor['full_name'],
                new_status, now,
                new_status, rejection_reason,
                new_status, postponed_until,
                now, int(req['id']),
            )
        )
        connection.execute(
            'INSERT INTO epi_request_history (request_id, company_id, status, notes, actor_user_id, actor_name, created_at) '
            'VALUES (?, ?, ?, ?, ?, ?, ?)',
            (int(req['id']), int(req['company_id']), new_status, str(upd.get('notes') or '').strip(), int(actor['id']), actor['full_name'], now)
        )


def update_feedback_status(connection, actor, feedback, status, notes):
    """Updates epi_feedback status and inserts a history record."""
    valid_status = {'pendente', 'em análise', 'aprovada', 'rejeitada', 'arquivada'}
    if status not in valid_status:
        raise ValueError('Status inválido para avaliação.')
    now = datetime.now(UTC).isoformat()
    connection.execute(
        'UPDATE epi_feedbacks '
        'SET status = ?, reviewer_user_id = ?, reviewer_name = ?, reviewed_at = ?, updated_at = ? '
        'WHERE id = ?',
        (status, int(actor['id']), actor['full_name'], now, now, int(feedback['id']))
    )
    connection.execute(
        'INSERT INTO epi_feedback_history (feedback_id, company_id, status, notes, actor_user_id, actor_name, created_at) '
        'VALUES (?, ?, ?, ?, ?, ?, ?)',
        (int(feedback['id']), int(feedback['company_id']), status, notes, int(actor['id']), actor['full_name'], now)
    )


def upsert_authorized_supplier(connection, company_id, supplier_id, name, cnpj, category, contact_email, notes):
    """Updates authorized supplier fields. Returns False if not found, True on success."""
    existing = connection.execute(
        'SELECT id FROM authorized_suppliers WHERE id = ? AND company_id = ?',
        (supplier_id, company_id)
    ).fetchone()
    if not existing:
        return False
    now = datetime.now(UTC).isoformat()
    connection.execute(
        'UPDATE authorized_suppliers SET name = ?, cnpj = ?, category = ?, contact_email = ?, notes = ?, updated_at = ? WHERE id = ?',
        (name, cnpj, category, contact_email, notes, now, supplier_id)
    )
    return True


def delete_purchase_function_link(connection, company_id, link_id):
    """Deletes a purchase_role_unit_link. Raises ValueError/PermissionError on failure."""
    link = connection.execute('SELECT * FROM purchase_role_unit_links WHERE id = ?', (link_id,)).fetchone()
    if not link:
        raise ValueError('Vínculo de compras não encontrado.')
    if int(link['company_id']) != company_id:
        raise PermissionError('Vínculo pertence a outra empresa.')
    connection.execute('DELETE FROM purchase_role_unit_links WHERE id = ?', (link_id,))


def delete_user_unit_link(connection, company_id, link_id):
    """Deprecated: user_unit_links was removed in Phase 26. Raises ValueError."""
    raise ValueError('user_unit_links foi removida. Use purchase_role_unit_links.')


# ── Route-level SQL extractions ───────────────────────────────────────────────

def get_purchase_request_by_id(connection, pr_id):
    row = connection.execute('SELECT * FROM purchase_requests WHERE id = ?', (int(pr_id),)).fetchone()
    return dict(row) if row else None


def get_epi_request_by_id(connection, request_id):
    row = connection.execute('SELECT * FROM epi_requests WHERE id = ?', (int(request_id),)).fetchone()
    return dict(row) if row else None


def get_epi_feedback_by_id(connection, feedback_id):
    row = connection.execute('SELECT * FROM epi_feedbacks WHERE id = ?', (int(feedback_id),)).fetchone()
    return dict(row) if row else None
