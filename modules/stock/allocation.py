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

Nada é baixado aqui. A entrada de material e a reserva apenas *prometem* a
peça; a baixa continua sendo da entrega.
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


def _sort_key(request) -> tuple:
    """Chave da ordem do §10.

    Datas ausentes viram string vazia, que ordena antes de qualquer data real —
    o efeito desejado: uma solicitação aprovada há muito tempo, mas sem carimbo,
    não deve ser empurrada para o fim da fila.
    """
    return (
        _urgency_rank(request.get('urgency')),
        str(request.get('approved_at') or ''),
        str(request.get('requested_at') or ''),
        int(request.get('id') or 0),
    )


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
    if 'urgency' not in columns:
        # Base ainda sem a coluna: todos entram como `normal`, e a ordem cai
        # para os critérios cronológicos. A fila continua determinística.
        for request in requests:
            request.setdefault('urgency', 'normal')
    return sorted(requests, key=_sort_key)


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
