"""CO-1 — governança de aprovação em Compras: segregação de funções (D-17).

Regra: quem CRIOU uma requisição de compra (PR) ou um pedido (PO) não aprova esse
registro. No PO, também não aprova quem criou QUALQUER requisição de origem —
inclusive quando o PO reúne itens de várias requisições. E, no PO de dois níveis,
a mesma pessoa não faz as duas aprovações (regra preexistente, agora por pessoa).

**Pessoa, não conta.** ``users.linked_employee_id`` não é único: a mesma pessoa
pode ter, por exemplo, uma conta de Administrador Local e outra de Aprovador. A
identidade comparada é o conjunto de contas da empresa ligadas ao mesmo
colaborador (mais a própria conta). Trocar de conta/perfil não contorna a regra.

**Vínculos legados.** Criador ausente (``NULL``/0) não prova conflito nenhum: a
aprovação segue, mas a decisão registra em ``purchase_events`` que a segregação
não pôde ser verificada para aquele vínculo (``segregation_unverifiable``). Não é
uma exceção silenciosa nem uma permissão de contorno: nada libera quem É o
criador comprovado.

**Poucos usuários.** Não há exceção: sem outra pessoa autorizada, o registro
continua pendente de aprovação independente.
"""

from __future__ import annotations


class PurchaseGovernanceError(PermissionError):
    """Recusa de governança com código estável (HTTP 403).

    Subclasse de ``PermissionError`` para que qualquer handler que só capture
    ``PermissionError`` continue respondendo 403.
    """

    status = 403

    def __init__(self, code: str, message: str, *, details=None):
        super().__init__(message)
        self.code = code
        self.details = details or {}


class PurchaseConflictError(ValueError):
    """Estado persistido mudou (concorrência ou reenvio) — HTTP 409."""

    status = 409

    def __init__(self, code: str, message: str, *, details=None):
        super().__init__(message)
        self.code = code
        self.details = details or {}


MSG_SELF_APPROVAL_PR = (
    'Aprovação recusada: quem criou a requisição não pode aprová-la. '
    'A requisição continua pendente de aprovação por outro responsável.'
)
MSG_SELF_APPROVAL_PO = (
    'Aprovação recusada: quem criou o pedido de compra ou a requisição de origem não pode aprová-lo. '
    'O pedido continua pendente de aprovação por outro responsável.'
)
MSG_SECOND_LEVEL_SAME_PERSON = 'O segundo nível de aprovação exige um aprovador diferente do primeiro.'
MSG_APPROVAL_STATUS_ROUTE = (
    'A aprovação de requisição deve ser feita pelo fluxo de aprovação, com registro do aprovador.'
)
MSG_PO_STATE_CHANGED = (
    'O pedido de compra foi alterado por outro usuário e não está mais aguardando esta decisão. '
    'Recarregue para ver o estado atual.'
)

APPROVING_DECISIONS = frozenset({'approved', 'partially_approved'})


def person_user_ids(connection, user_id, company_id) -> frozenset:
    """Contas da mesma pessoa na empresa (inclui ``user_id``)."""
    if not user_id:
        return frozenset()
    ids = {int(user_id)}
    from epi_backend.db import table_columns
    # Esquema mínimo (fixtures) sem users/linked_employee_id: a pessoa é a conta.
    try:
        if 'linked_employee_id' not in set(table_columns(connection, 'users')):
            return frozenset(ids)
    except Exception:  # noqa: BLE001 - tabela ausente em fixture mínima
        return frozenset(ids)
    row = connection.execute('SELECT linked_employee_id FROM users WHERE id = ?', (int(user_id),)).fetchone()
    linked = row['linked_employee_id'] if row else None
    if linked:
        for other in connection.execute(
            'SELECT id FROM users WHERE company_id = ? AND linked_employee_id = ?',
            (int(company_id), int(linked)),
        ).fetchall():
            ids.add(int(other['id']))
    return frozenset(ids)


def _ids(values) -> tuple[set, int]:
    """Separa criadores comprovados (ids > 0) da contagem de vínculos ausentes."""
    known, missing = set(), 0
    for value in values:
        try:
            number = int(value or 0)
        except (TypeError, ValueError):
            number = 0
        if number > 0:
            known.add(number)
        else:
            missing += 1
    return known, missing


def purchase_request_creators(connection, pr_ids) -> tuple[set, int]:
    pr_ids = sorted({int(i) for i in pr_ids if i})
    if not pr_ids:
        return set(), 0
    placeholders = ','.join('?' for _ in pr_ids)
    rows = connection.execute(
        f'SELECT created_by_user_id FROM purchase_requests WHERE id IN ({placeholders})', tuple(pr_ids)
    ).fetchall()
    known, missing = _ids(r['created_by_user_id'] for r in rows)
    return known, missing + (len(pr_ids) - len(rows))


def purchase_order_origin_pr_ids(connection, po) -> set:
    """Requisições de origem do PO: a do cabeçalho e as dos itens."""
    ids = set()
    if po.get('purchase_request_id'):
        ids.add(int(po['purchase_request_id']))
    for row in connection.execute(
        'SELECT DISTINCT pri.purchase_request_id AS pr_id '
        'FROM purchase_order_items poi JOIN purchase_request_items pri ON pri.id = poi.purchase_request_item_id '
        'WHERE poi.purchase_order_id = ?',
        (int(po['id']),),
    ).fetchall():
        if row['pr_id']:
            ids.add(int(row['pr_id']))
    return ids


def _conflict(connection, actor, creator_ids) -> bool:
    actor_person = person_user_ids(connection, actor['id'], actor.get('company_id') or 0)
    for creator in creator_ids:
        if creator in actor_person:
            return True
        if actor_person & person_user_ids(connection, creator, actor.get('company_id') or 0):
            return True
    return False


def ensure_not_self_approving_purchase_request(connection, actor, pr) -> dict:
    known, missing = purchase_request_creators(connection, [pr['id']])
    if _conflict(connection, actor, known):
        raise PurchaseGovernanceError('PURCHASE_SELF_APPROVAL_FORBIDDEN', MSG_SELF_APPROVAL_PR,
                                      details={'entity': 'purchase_request', 'id': int(pr['id'])})
    return {'unverifiable_links': missing}


def ensure_not_self_approving_purchase_order(connection, actor, po) -> dict:
    po_known, po_missing = _ids([po.get('created_by_user_id')])
    origin_ids = purchase_order_origin_pr_ids(connection, po)
    pr_known, pr_missing = purchase_request_creators(connection, origin_ids)
    if _conflict(connection, actor, po_known | pr_known):
        raise PurchaseGovernanceError('PURCHASE_SELF_APPROVAL_FORBIDDEN', MSG_SELF_APPROVAL_PO,
                                      details={'entity': 'purchase_order', 'id': int(po['id'])})
    return {'unverifiable_links': po_missing + pr_missing, 'origin_requests': sorted(origin_ids)}


def ensure_independent_second_level(connection, actor, prior_approver_ids) -> None:
    if _conflict(connection, actor, set(prior_approver_ids)):
        raise PurchaseGovernanceError('PURCHASE_SECOND_LEVEL_SAME_PERSON', MSG_SECOND_LEVEL_SAME_PERSON)
