"""Máquina de estados (pura) das Ordens de Compra (PO).

Funções sem efeitos colaterais: validam transições e regras de aprovação
multi-nível. A camada de serviço (modules/purchases/service.py) aplica os
efeitos em banco. Mantido isolado para facilitar testes unitários.

Ciclo de vida (alinhado ao frontend em app.js openPoDetail):

    criada → waiting_admin_review
        admin /review:
            review_approved          → pending_approval
            returned_with_suggestions → quoted (+ buyer_suggestions)
    quoted → comprador /resubmit → waiting_admin_review
    pending_approval | postponed → aprovador /approve:
            approved | partially_approved → approved   (1+ níveis)
            rejected                       → rejected   (terminal)
            postponed                      → postponed
    approved | received_partial → /receive:
            received | received_partial    → received[_partial] (+ estoque)
    received | received_partial → /receive checked  → checked
    checked → /receive closed → closed
"""

# Reaproveita os motivos de reprovação por item já usados nas requisições.
from epi_backend.purchase_workflow import PURCHASE_APPROVAL_REJECTION_REASONS

PO_STATUS_LABELS = {
    'draft': 'Rascunho',
    'waiting_admin_review': 'Aguardando Revisão do Admin',
    'quoted': 'Em Revisão do Comprador',
    'pending_approval': 'Aguardando Aprovação',
    'approved': 'Aprovada',
    'partially_approved': 'Aprovada Parcialmente',
    'rejected': 'Reprovada',
    'postponed': 'Prorrogada',
    'received_partial': 'Recebida Parcialmente',
    'received': 'Recebida',
    'checked': 'Conferida',
    'closed': 'Fechada',
    'cancelled': 'Cancelada',
}

PO_REVIEW_DECISIONS = {'review_approved', 'returned_with_suggestions'}
PO_APPROVAL_DECISIONS = {'approved', 'partially_approved', 'rejected', 'postponed'}
PO_RECEIVE_ACTIONS = {'received', 'received_partial', 'checked', 'closed'}

# from-status permitido por ação
_REVIEW_FROM = {'waiting_admin_review'}
_RESUBMIT_FROM = {'quoted'}
_APPROVE_FROM = {'pending_approval', 'postponed'}
_RECEIVE_FROM = {
    'received': {'approved', 'received_partial', 'received'},
    'received_partial': {'approved', 'received_partial'},
    'checked': {'received', 'received_partial'},
    'closed': {'checked'},
}


def po_status_label(status):
    key = str(status or '').strip().lower()
    return PO_STATUS_LABELS.get(key, key)


def _norm(status):
    return str(status or '').strip().lower()


def assert_review_allowed(current_status, decision):
    if _norm(current_status) not in _REVIEW_FROM:
        raise ValueError(
            f'Revisão indisponível: PO em "{po_status_label(current_status)}".'
        )
    if str(decision or '').strip() not in PO_REVIEW_DECISIONS:
        raise ValueError('Decisão de revisão inválida.')
    return 'pending_approval' if decision == 'review_approved' else 'quoted'


def assert_resubmit_allowed(current_status):
    if _norm(current_status) not in _RESUBMIT_FROM:
        raise ValueError(
            f'Reenvio indisponível: PO em "{po_status_label(current_status)}".'
        )
    return 'waiting_admin_review'


def assert_approval_allowed(current_status, decision):
    if _norm(current_status) not in _APPROVE_FROM:
        raise ValueError(
            f'Aprovação indisponível: PO em "{po_status_label(current_status)}".'
        )
    if str(decision or '').strip() not in PO_APPROVAL_DECISIONS:
        raise ValueError('Decisão de aprovação inválida.')


def assert_receive_allowed(current_status, action):
    act = str(action or '').strip()
    if act not in PO_RECEIVE_ACTIONS:
        raise ValueError('Ação de recebimento inválida.')
    if _norm(current_status) not in _RECEIVE_FROM[act]:
        raise ValueError(
            f'Ação "{act}" indisponível: PO em "{po_status_label(current_status)}".'
        )
    return act


def required_approval_levels(total_value, threshold):
    """Quantos níveis de aprovação a PO exige.

    Acima (ou igual) ao limite configurado pela empresa, exige um segundo nível
    (financeiro/diretor). Limite ausente ou <= 0 desativa o multi-nível.
    """
    try:
        total = float(total_value or 0)
    except (TypeError, ValueError):
        total = 0.0
    try:
        limit = float(threshold or 0)
    except (TypeError, ValueError):
        limit = 0.0
    if limit > 0 and total >= limit:
        return 2
    return 1


def resolve_approval_outcome(decision, *, prior_approvals, total_value, threshold):
    """Resolve o status final da PO após uma decisão de aprovação.

    prior_approvals = nº de aprovações de nível já registradas ANTES desta.
    Retorna (next_status, finalizes) onde finalizes indica se a decisão
    encerrou o fluxo de aprovação (para registro/итем).
    """
    decision = str(decision or '').strip()
    if decision == 'rejected':
        return 'rejected', True
    if decision == 'postponed':
        return 'postponed', False
    # approved | partially_approved
    needed = required_approval_levels(total_value, threshold)
    approvals_after = int(prior_approvals or 0) + 1
    if approvals_after >= needed:
        return ('partially_approved' if decision == 'partially_approved' else 'approved'), True
    # ainda faltam níveis de aprovação
    return 'pending_approval', False


__all__ = [
    'PO_STATUS_LABELS',
    'PO_REVIEW_DECISIONS',
    'PO_APPROVAL_DECISIONS',
    'PO_RECEIVE_ACTIONS',
    'PURCHASE_APPROVAL_REJECTION_REASONS',
    'po_status_label',
    'assert_review_allowed',
    'assert_resubmit_allowed',
    'assert_approval_allowed',
    'assert_receive_allowed',
    'required_approval_levels',
    'resolve_approval_outcome',
]
