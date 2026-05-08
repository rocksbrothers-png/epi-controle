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
