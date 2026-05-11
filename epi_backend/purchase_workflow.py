"""Workflow/status helpers for purchase request review transitions."""

PURCHASE_STATUS_LABELS = {
    'draft': 'Rascunho',
    'open': 'Aguardando Cotação',
    'sent_to_buyer': 'Aguardando Cotação',
    'quoted': 'Em Cotação',
    'pending_approval': 'Cotação Enviada ao Aprovador',
    'waiting_buyer_correction': 'Aguardando Correção do Comprador',
    'buyer_resubmitted': 'Reenviada pelo Comprador',
    'waiting_requester_correction': 'Aguardando Correção do Requisitante',
    'requester_resubmitted': 'Reenviada pelo Requisitante',
    'approved': 'Aprovada',
    'partially_approved': 'Aprovada Parcialmente',
    'rejected': 'Reprovada',
    'postponed': 'Prorrogada',
    'returned_to_buyer': 'Retornado ao Comprador',
    'po_generated': 'PO Gerada',
    'received': 'Recebida',
    'checked': 'Conferida',
    'closed': 'Fechada',
    'cancelled': 'Cancelada',
}

REVIEW_REASON_GROUPS = {
    'buyer': {
        'Valor acima do esperado',
        'Fornecedor incorreto',
        'Item com preço divergente',
        'Cotação incompleta',
        'Necessário novo fornecedor',
        'Quantidade divergente',
        'Outro',
    },
    'requester': {
        'Acrescentar novos itens',
        'Corrigir item existente',
        'Revisar quantidade',
        'Reavaliar item inicialmente reprovado',
        'Justificar necessidade',
        'Anexar informação complementar',
        'Outro',
    },
    'reject': {
        'Valor acima do esperado',
        'Fornecedor incorreto',
        'Item com preço divergente',
        'Cotação incompleta',
        'Quantidade divergente',
        'Outro',
    },
}

PURCHASE_ITEM_STATUS_LABELS = {
    'open': 'Pendente',
    'included_in_request': 'Pendente',
    'sent_to_buyer': 'Aguardando Cotação',
    'waiting_quote': 'Aguardando Cotação',
    'quoted': 'Cotado',
    'pending_approval': 'Aguardando Aprovação',
    'approved': 'Aprovado',
    'partially_approved': 'Aprovado Parcialmente',
    'rejected': 'Reprovado',
    'ordered': 'Em Compra',
    'waiting_admin_review': 'Em Compra',
    'received': 'Recebido',
    'closed': 'Fechado',
}

PURCHASE_APPROVAL_REJECTION_REASONS = {
    'Item não necessário',
    'Valor acima do esperado',
    'Quantidade incorreta',
    'Fornecedor inadequado',
    'EPI incompatível',
    'Fora do escopo da solicitação',
    'Outro',
}


def _coerce_int_set(values):
    result = set()
    for value in values or []:
        text = str(value).strip()
        if text:
            result.add(int(text))
    return result


def normalize_purchase_item_approval_decisions(items, payload):
    """Validate and normalize per-item approval decisions for a purchase request."""
    item_map = {int(item['id']): item for item in (items or [])}
    if not item_map:
        raise ValueError('Requisição sem itens para aprovação.')

    raw_decisions = payload.get('decisions') or payload.get('item_decisions') or []
    normalized = []
    seen = set()
    if raw_decisions:
        if not isinstance(raw_decisions, list):
            raise ValueError('Decisões por item devem ser uma lista.')
        for index, decision in enumerate(raw_decisions, start=1):
            if not isinstance(decision, dict):
                raise ValueError(f'Decisão do item #{index} inválida.')
            item_id = int(decision.get('item_id') or decision.get('id') or 0)
            if item_id not in item_map:
                raise ValueError(f'Item {item_id} não pertence à requisição.')
            if item_id in seen:
                raise ValueError(f'Item {item_id} possui decisão duplicada.')
            seen.add(item_id)
            decision_value = str(decision.get('decision') or '').strip().lower()
            approved = bool(decision.get('approved')) or decision_value in {'approved', 'approve', 'aprovado', 'aprovar'}
            if decision_value in {'rejected', 'reject', 'reprovado', 'reprovar'}:
                approved = False
            reason = str(decision.get('rejection_reason') or decision.get('reason') or '').strip()
            comment = str(decision.get('rejection_comment') or decision.get('comment') or '').strip()
            normalized.append({'item': item_map[item_id], 'item_id': item_id, 'approved': approved, 'reason': reason, 'comment': comment})
    else:
        approved_ids = _coerce_int_set(payload.get('approved_item_ids') or [])
        rejected_ids = _coerce_int_set(payload.get('rejected_item_ids') or [])
        unknown = (approved_ids | rejected_ids) - set(item_map)
        if unknown:
            raise ValueError(f'Item {min(unknown)} não pertence à requisição.')
        if approved_ids & rejected_ids:
            raise ValueError('Um item não pode ser aprovado e reprovado ao mesmo tempo.')
        if approved_ids or rejected_ids:
            missing = set(item_map) - approved_ids - rejected_ids
            if missing:
                raise ValueError('Informe decisão para todos os itens da requisição.')
        else:
            approved_ids = set(item_map)
        for item_id in sorted(item_map):
            approved = item_id in approved_ids
            normalized.append({
                'item': item_map[item_id],
                'item_id': item_id,
                'approved': approved,
                'reason': '' if approved else str(payload.get('reason') or '').strip(),
                'comment': '' if approved else str(payload.get('comment') or '').strip(),
            })

    missing = set(item_map) - seen if raw_decisions else set()
    if missing:
        raise ValueError('Informe decisão para todos os itens da requisição.')

    approved_count = 0
    rejected_count = 0
    approved_quantity = 0
    rejected_quantity = 0
    approved_total = 0.0
    rejected_total = 0.0
    grand_total = 0.0
    for decision in normalized:
        item = decision['item']
        quantity = int(item.get('quantity_requested') or item.get('quantity') or 1)
        total = float(item.get('total_price') or (float(item.get('unit_price') or 0) * quantity))
        grand_total += total
        if decision['approved']:
            approved_count += 1
            approved_quantity += quantity
            approved_total += total
            decision['quantity_approved'] = quantity
            continue
        rejected_count += 1
        rejected_quantity += quantity
        rejected_total += total
        decision['quantity_approved'] = 0
        if not decision['reason']:
            raise ValueError('Selecione o motivo para cada item reprovado.')
        if decision['reason'] not in PURCHASE_APPROVAL_REJECTION_REASONS:
            raise ValueError('Motivo de reprovação do item inválido.')
        if decision['reason'] == 'Outro' and not decision['comment']:
            raise ValueError('Informe a observação quando o motivo for Outro.')

    if approved_count and rejected_count:
        request_status = 'partially_approved'
    elif approved_count:
        request_status = 'approved'
    else:
        request_status = 'rejected'

    totals = {
        'approved_total': round(approved_total, 2),
        'rejected_total': round(rejected_total, 2),
        'grand_total': round(grand_total, 2),
        'approved_quantity': approved_quantity,
        'rejected_quantity': rejected_quantity,
        'approved_count': approved_count,
        'rejected_count': rejected_count,
        'total_count': len(normalized),
    }
    return normalized, request_status, totals

WORKFLOW_ACTIONS = {
    'approve': {
        'from': {'pending_approval', 'postponed'},
        'to': 'approved',
        'permission': 'approve',
        'destination': 'closed',
        'label': 'Aprovar cotação/requisição',
    },
    'reject': {
        'from': {'pending_approval', 'postponed'},
        'to': 'rejected',
        'permission': 'approve',
        'destination': 'closed',
        'requires_reason': True,
        'requires_comment': True,
        'reason_group': 'reject',
        'label': 'Reprovar cotação/requisição',
    },
    'generate_po_partial': {
        'from': {'partially_approved'},
        'to': 'po_generated',
        'permission': 'update',
        'destination': 'buyer',
        'label': 'Gerar PO (itens aprovados)',
    },
    'return_to_buyer': {
        'from': {'pending_approval', 'postponed'},
        'to': 'waiting_buyer_correction',
        'permission': 'approve',
        'destination': 'buyer',
        'requires_reason': True,
        'requires_comment': True,
        'reason_group': 'buyer',
        'label': 'Solicitar revisão da cotação',
    },
    'return_to_requester': {
        'from': {'pending_approval', 'postponed'},
        'to': 'waiting_requester_correction',
        'permission': 'approve',
        'destination': 'requester',
        'requires_reason': True,
        'requires_comment': True,
        'reason_group': 'requester',
        'label': 'Solicitar revisão da requisição',
    },
    'buyer_return_to_requester': {
        'from': {'sent_to_buyer', 'quoted', 'returned_to_buyer', 'waiting_buyer_correction'},
        'to': 'waiting_requester_correction',
        'permission': 'update',
        'destination': 'requester',
        'requires_reason': True,
        'requires_comment': True,
        'reason_group': 'requester',
        'label': 'Retornar ao Requisitante',
    },
    'buyer_resubmit': {
        'from': {'waiting_buyer_correction', 'returned_to_buyer', 'quoted'},
        'to': 'pending_approval',
        'permission': 'update',
        'destination': 'approver',
        'label': 'Reenviar ao Aprovador',
    },
    'requester_resubmit': {
        'from': {'waiting_requester_correction'},
        'to': None,
        'permission': 'update',
        'destination': 'buyer_or_approver',
        'label': 'Reenviar requisição corrigida',
    },
}


def normalize_purchase_status(status):
    return str(status or '').strip().lower()


def latest_requester_review_origin(events):
    for event in events or []:
        action = str(event.get('action') or '')
        destination = str(event.get('destination') or '')
        if action in {'return_to_requester', 'buyer_return_to_requester'} or destination == 'requester':
            return str(event.get('status_from') or '')
    return ''


def _requester_resubmit_target(origin_status):
    if normalize_purchase_status(origin_status) in {'pending_approval', 'postponed'}:
        return 'pending_approval'
    return 'sent_to_buyer'


def resolve_purchase_transition(status, action, *, requester_review_origin=''):
    action_key = str(action or '').strip().lower()
    if action_key not in WORKFLOW_ACTIONS:
        raise ValueError('Ação de compras inválida.')
    current = normalize_purchase_status(status)
    definition = WORKFLOW_ACTIONS[action_key]
    if current not in definition['from']:
        raise ValueError(f'Transição inválida: {PURCHASE_STATUS_LABELS.get(current, current)} não permite {definition["label"]}.')
    next_status = definition['to']
    if action_key == 'requester_resubmit':
        next_status = _requester_resubmit_target(requester_review_origin)
    return {**definition, 'action': action_key, 'status_from': current, 'status_to': next_status}


def validate_purchase_transition_payload(transition, *, reason='', comment=''):
    clean_reason = str(reason or '').strip()
    clean_comment = str(comment or '').strip()
    if transition.get('requires_reason') and not clean_reason:
        raise ValueError('Selecione o motivo da revisão/decisão.')
    if transition.get('requires_comment') and not clean_comment:
        raise ValueError('Informe a observação obrigatória.')
    reason_group = transition.get('reason_group')
    if clean_reason and reason_group and clean_reason not in REVIEW_REASON_GROUPS.get(reason_group, set()):
        raise ValueError('Motivo selecionado inválido para esta ação.')
    return clean_reason, clean_comment


def serialize_purchase_event_comment(reason='', comment='', requested_changes=None):
    parts = []
    if reason:
        parts.append(f'Motivo: {reason}')
    if requested_changes:
        parts.append(f'Necessidades: {", ".join(str(item) for item in requested_changes if str(item).strip())}')
    if comment:
        parts.append(f'Observação: {comment}')
    return ' | '.join(parts)
