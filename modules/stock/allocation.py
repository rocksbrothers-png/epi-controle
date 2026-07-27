"""Alocação de estoque recém-recebido às solicitações pendentes (plano §10).

Quando material entra no estoque de uma unidade, as solicitações que estavam
esperando por ele **daquela mesma unidade** passam a ser atendíveis. Sem isto,
o recebimento alimentava o saldo e as pessoas continuavam esperando até alguém
reparar manualmente.

Duas regras que o plano é explícito em exigir:

1. **Nunca atender solicitação de outra unidade.** O material entrou no estoque
   de uma unidade específica; alocá-lo para outra seria consumo cruzado, que o
   ADR-0001 §15 proíbe.
2. **A ordem é determinística e auditável.** Urgência aprovada → data de
   aprovação → data de solicitação → id como desempate final. Sem o desempate
   por id, duas solicitações do mesmo instante alternariam de posição entre
   execuções, e ninguém conseguiria explicar por que uma foi atendida antes.
3. **Data ausente não vira prioridade máxima.** Ela é primeiro *reconstruída*
   pelo histórico da solicitação; quando isso não é possível, a solicitação é
   **sinalizada para saneamento** e ordenada no fim da sua faixa de urgência.
   Ordenar dado ruim na frente premiaria o registro incompleto.

Nada é baixado aqui. A entrada de material e a reserva apenas *prometem* a
peça; a baixa continua sendo da entrega.

Atendimento fora de ordem existe, mas nunca é automático: exige o
:func:`allocate_to_request` com justificativa, que fica auditada.
"""

from epi_backend.db import row_to_dict, table_columns, table_exists

#: Ordem de prioridade da urgência. Valor desconhecido cai em `normal`, para
#: que um dado inesperado não pule na frente nem afunde a fila.
URGENCY_RANK = {
    'critica': 0,
    'crítica': 0,
    'alta': 1,
    'normal': 2,
    'baixa': 3,
}
DEFAULT_URGENCY_RANK = URGENCY_RANK['normal']


def _urgency_rank(value) -> int:
    return URGENCY_RANK.get(str(value or '').strip().lower(), DEFAULT_URGENCY_RANK)


#: Ordena depois de qualquer data ISO real. Usado para a solicitação cuja data
#: não pôde ser reconstruída: ela espera, e é sinalizada — em vez de furar a
#: fila por ausência de dado.
_UNRESOLVED_DATE_SENTINEL = '9999-12-31T23:59:59'


def _sort_key(request) -> tuple:
    """Chave da ordem do §10.

    A data efetiva já vem reconstruída por :func:`_resolve_dates`. O que não foi
    possível reconstruir recebe o sentinela do fim — nunca o começo.
    """
    return (
        _urgency_rank(request.get('urgency')),
        str(request.get('effective_approved_at') or _UNRESOLVED_DATE_SENTINEL),
        str(request.get('effective_requested_at') or _UNRESOLVED_DATE_SENTINEL),
        int(request.get('id') or 0),
    )


def _history_timestamp(connection, request_id, statuses) -> str:
    """Primeiro carimbo do histórico em que a solicitação entrou num dos estados.

    É a fonte confiável para reconstruir uma data perdida: o histórico registra
    quando cada transição aconteceu, mesmo que a coluna da solicitação tenha
    ficado vazia.
    """
    if not table_exists(connection, 'epi_request_history'):
        return ''
    placeholders = ', '.join(['?'] * len(statuses))
    row = connection.execute(
        'SELECT created_at FROM epi_request_history WHERE request_id = ? '
        f'AND LOWER(COALESCE(status, \'\')) IN ({placeholders}) '  # noqa: S608
        'ORDER BY created_at, id LIMIT 1',
        (int(request_id), *statuses),
    ).fetchone()
    if not row:
        return ''
    return str((row['created_at'] if hasattr(row, 'keys') else row[0]) or '')


def _resolve_dates(connection, request) -> dict:
    """Preenche as datas efetivas e sinaliza o que não deu para reconstruir.

    Ordem das fontes, da mais para a menos confiável:

    1. a própria coluna da solicitação;
    2. o histórico da transição correspondente;
    3. nada — e aí a solicitação é marcada com ``needs_date_review``.

    A marcação é o ponto: um registro incompleto precisa aparecer para
    saneamento, não sumir dentro de uma ordenação silenciosa.
    """
    from modules.epis.request_states import APPROVED, RESERVED, SUBMITTED

    pending_review = []

    approved = str(request.get('approved_at') or '').strip()
    if not approved:
        approved = _history_timestamp(connection, request['id'], (APPROVED, RESERVED))
        if not approved:
            pending_review.append('approved_at')
    request['effective_approved_at'] = approved

    requested = str(request.get('requested_at') or '').strip()
    if not requested:
        requested = _history_timestamp(connection, request['id'], (SUBMITTED,))
        if not requested:
            pending_review.append('requested_at')
    request['effective_requested_at'] = requested

    request['needs_date_review'] = bool(pending_review)
    request['unresolved_date_fields'] = pending_review
    return request


def pending_requests_for(connection, company_id, unit_id, epi_id) -> list:
    """Solicitações aguardando estoque, **da unidade que recebeu**, já ordenadas."""
    if not table_exists(connection, 'epi_requests'):
        return []
    from modules.epis.request_states import WAITING_STOCK

    columns = table_columns(connection, 'epi_requests')
    rows = connection.execute(
        'SELECT * FROM epi_requests WHERE company_id = ? AND unit_id = ? AND epi_id = ? '
        'AND LOWER(COALESCE(status, \'\')) = ?',
        (int(company_id), int(unit_id), int(epi_id), WAITING_STOCK),
    ).fetchall()
    requests = [row_to_dict(row) for row in rows]
    for request in requests:
        if 'urgency' not in columns:
            # Base ainda sem a coluna: todos entram como `normal`, e a ordem
            # cai para os critérios cronológicos. A fila segue determinística.
            request.setdefault('urgency', 'normal')
        _resolve_dates(connection, request)
    return sorted(requests, key=_sort_key)


def requests_needing_date_review(connection, company_id, unit_id=None) -> list:
    """Solicitações cuja data não pôde ser reconstruída.

    Existe para o saneamento: sem uma lista, a inconsistência ficaria só na
    ordenação, invisível para quem poderia corrigi-la.
    """
    if not table_exists(connection, 'epi_requests'):
        return []
    from modules.epis.request_states import TERMINAL_STATUSES

    clauses = ['company_id = ?']
    params = [int(company_id)]
    if unit_id:
        clauses.append('unit_id = ?')
        params.append(int(unit_id))
    placeholders = ', '.join(['?'] * len(TERMINAL_STATUSES))
    rows = connection.execute(
        f'SELECT * FROM epi_requests WHERE {" AND ".join(clauses)} '  # noqa: S608
        f'AND LOWER(COALESCE(status, \'\')) NOT IN ({placeholders}) ORDER BY id',
        (*params, *sorted(TERMINAL_STATUSES)),
    ).fetchall()
    flagged = []
    for row in rows:
        request = _resolve_dates(connection, row_to_dict(row))
        if request['needs_date_review']:
            flagged.append(request)
    return flagged


def allocate_incoming_stock(
    connection,
    company_id,
    unit_id,
    epi_id,
    *,
    actor_user_id=None,
) -> list:
    """Reserva o saldo que acabou de entrar para quem está esperando.

    Percorre a fila em ordem e reserva a quantidade **integral** de cada
    solicitação enquanto houver saldo livre. Quem não couber permanece
    aguardando: o §3.8 é explícito em que atendimento parcial exige decisão do
    Gestor de EPI, então parar aqui é deliberado — não é limitação.

    Devolve a lista do que foi alocado, para auditoria e notificação.
    """
    from modules.epis.request_states import RESERVED, assert_transition
    from modules.stock.reservations import (
        InsufficientFreeStock,
        create_reservation,
        reservations_ready,
        unit_balance,
    )

    if not reservations_ready(connection):
        return []

    allocated = []
    for request in pending_requests_for(connection, company_id, unit_id, epi_id):
        quantity = int(request.get('quantity') or 0)
        if quantity <= 0:
            continue
        if unit_balance(connection, company_id, unit_id, epi_id)['free'] < quantity:
            # Fila ordenada: quem vem depois pode ser menor e caber, mas
            # atender fora de ordem quebraria a prioridade que acabamos de
            # estabelecer. Para aqui.
            break
        try:
            reservation = create_reservation(
                connection,
                company_id=company_id,
                unit_id=unit_id,
                epi_id=epi_id,
                quantity=quantity,
                request_id=int(request['id']),
                actor_user_id=actor_user_id,
                glove_size=request.get('glove_size') or 'N/A',
                size=request.get('size') or 'N/A',
                uniform_size=request.get('uniform_size') or 'N/A',
                notes='reserva automática após entrada de estoque',
            )
        except InsufficientFreeStock:
            break

        new_status = assert_transition(request.get('status'), RESERVED)
        connection.execute(
            'UPDATE epi_requests SET status = ?, last_updated_at = ? WHERE id = ?',
            (new_status, reservation['created_at'], int(request['id'])),
        )
        _record_history(connection, request, new_status, reservation)
        allocated.append({
            'request_id': int(request['id']),
            'reservation_id': int(reservation['id']),
            'quantity': quantity,
            'unit_id': int(unit_id),
            'epi_id': int(epi_id),
        })
    return allocated


def allocate_to_request(
    connection,
    request_id,
    *,
    reason,
    actor_user_id=None,
    actor_name='',
) -> dict:
    """Atendimento **fora de ordem**, autorizado pelo Gestor de EPI.

    A rotina automática nunca pula a fila. Este é o único caminho para atender
    alguém antes de quem estava na frente, e ele **exige justificativa**: a
    razão vai para o histórico da solicitação, que é onde a decisão fica
    auditável.

    Não é atalho para as demais regras: a unidade continua sendo a da própria
    solicitação, a quantidade continua sendo integral e o saldo livre continua
    tendo de existir.
    """
    from modules.epis.request_states import RESERVED, assert_transition
    from modules.stock.reservations import create_reservation

    justification = str(reason or '').strip()
    if not justification:
        raise ValueError('Atendimento fora de ordem exige justificativa.')

    row = connection.execute(
        'SELECT * FROM epi_requests WHERE id = ?', (int(request_id),)
    ).fetchone()
    if not row:
        raise ValueError('Solicitação não encontrada.')
    request = row_to_dict(row)

    reservation = create_reservation(
        connection,
        company_id=request['company_id'],
        unit_id=request['unit_id'],
        epi_id=request['epi_id'],
        quantity=int(request.get('quantity') or 0),
        request_id=int(request['id']),
        actor_user_id=actor_user_id,
        glove_size=request.get('glove_size') or 'N/A',
        size=request.get('size') or 'N/A',
        uniform_size=request.get('uniform_size') or 'N/A',
        notes=f'atendimento fora de ordem: {justification}',
    )
    new_status = assert_transition(request.get('status'), RESERVED)
    connection.execute(
        'UPDATE epi_requests SET status = ?, last_updated_at = ? WHERE id = ?',
        (new_status, reservation['created_at'], int(request['id'])),
    )
    if table_exists(connection, 'epi_request_history'):
        connection.execute(
            'INSERT INTO epi_request_history (request_id, company_id, status, notes, '
            'actor_user_id, actor_name, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)',
            (
                int(request['id']), int(request['company_id']), new_status,
                f'atendimento fora de ordem autorizado — justificativa: {justification}',
                int(actor_user_id) if actor_user_id else None,
                str(actor_name or ''), reservation['created_at'],
            ),
        )
    return {
        'request_id': int(request['id']),
        'reservation_id': int(reservation['id']),
        'quantity': int(reservation['quantity']),
        'unit_id': int(request['unit_id']),
        'epi_id': int(request['epi_id']),
        'out_of_order': True,
        'reason': justification,
    }


def _record_history(connection, request, status, reservation) -> None:
    """Histórico da solicitação — a alocação automática também presta contas."""
    if not table_exists(connection, 'epi_request_history'):
        return
    connection.execute(
        'INSERT INTO epi_request_history (request_id, company_id, status, notes, actor_name, created_at) '
        'VALUES (?, ?, ?, ?, ?, ?)',
        (
            int(request['id']), int(request['company_id']), status,
            f'reserva #{reservation["id"]} criada automaticamente após entrada de estoque',
            'Sistema', reservation['created_at'],
        ),
    )
