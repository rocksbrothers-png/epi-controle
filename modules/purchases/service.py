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
from modules.stock.service import fetch_epi_size_balance

UTC = timezone.utc

PURCHASE_FUNCTION_TYPES = {'buyer', 'approver'}
PURCHASE_FUNCTION_LABELS = {'buyer': 'Comprador', 'approver': 'Aprovador'}


def normalize_purchase_function_type(value):
    normalized = normalize_role_name(value)
    if normalized not in PURCHASE_FUNCTION_TYPES:
        raise ValueError('Função de compras deve ser comprador ou aprovador.')
    return normalized


def get_actor_purchase_unit_scope(connection, actor):
    """Retorna unit_ids para vínculos de Compras.

    Mantém compatibilidade com user_unit_links legado e também consulta a
    estrutura separada por colaborador (purchase_role_unit_links).
    """
    if not actor:
        return None
    actor_role = actor.get('role')
    unit_ids = []
    if actor_role in ('buyer', 'approver'):
        legacy_rows = connection.execute(
            'SELECT unit_id FROM user_unit_links WHERE user_id = ?',
            (int(actor['id']),)
        ).fetchall()
        unit_ids.extend(int(r['unit_id']) for r in legacy_rows)
    linked_employee_id = actor.get('linked_employee_id')
    if linked_employee_id and actor_role in ('buyer', 'approver', 'admin', 'registry_admin', 'general_admin'):
        function_rows = connection.execute(
            'SELECT unit_id FROM purchase_role_unit_links WHERE employee_id = ? AND role_type = ?',
            (int(linked_employee_id), actor_role if actor_role in PURCHASE_FUNCTION_TYPES else 'buyer')
        ).fetchall()
        unit_ids.extend(int(r['unit_id']) for r in function_rows)
    if not unit_ids:
        return None
    return sorted(set(unit_ids))


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
