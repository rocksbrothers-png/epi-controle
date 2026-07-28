"""Reserva de estoque por unidade.

O elo que faltava entre aprovar e entregar. Antes disto o sistema só conhecia o
saldo **físico**, então duas solicitações podiam ser aprovadas sobre a mesma
peça e a segunda descobria o problema só na entrega.

    saldo livre = saldo físico − saldo reservado (ativo)

Três invariantes que este módulo existe para sustentar:

1. **A reserva não baixa estoque.** Ela só reduz o que está disponível para
   novas promessas. A baixa acontece no consumo, junto com a entrega.
2. **A reserva é sempre de uma unidade.** Não existe reserva que atravesse
   unidades nem reserva "da empresa" — o estoque pertence exclusivamente a uma
   unidade (ADR-0001 §15), e o escopo de consolidação não tem voz aqui.
3. **Saldo livre nunca fica negativo.** Sob concorrência, quem chegar segundo
   perde: o claim é feito por ``UPDATE ... WHERE`` com verificação de
   ``rowcount``, o mesmo padrão já usado na entrega.
"""

from datetime import datetime, timezone

from epi_backend.db import row_to_dict

UTC = timezone.utc

ACTIVE = 'active'
CONSUMED = 'consumed'
RELEASED = 'released'

RESERVATION_STATUSES = (ACTIVE, CONSUMED, RELEASED)


class InsufficientFreeStock(ValueError):
    """Saldo livre insuficiente para a reserva pedida."""


class ReservationNotActive(ValueError):
    """Reserva já consumida ou liberada — não pode ser usada de novo."""


def reservations_ready(connection) -> bool:
    """A tabela existe? Permite degradação graciosa na janela de migração."""
    from epi_backend.db import table_exists

    return table_exists(connection, 'stock_reservations')


def reserved_quantity(connection, company_id, unit_id, epi_id) -> int:
    """Quantidade ainda **prometida** do EPI naquela unidade.

    É o que falta entregar, não o que foi reservado: ``quantity -
    consumed_quantity``. A parte já entregue saiu do estoque físico, então
    continuar contando-a como reserva subtrairia a mesma peça duas vezes do
    saldo livre.
    """
    if not reservations_ready(connection):
        return 0
    row = connection.execute(
        'SELECT COALESCE(SUM(quantity - COALESCE(consumed_quantity, 0)), 0) AS total '
        'FROM stock_reservations '
        'WHERE company_id = ? AND unit_id = ? AND epi_id = ? AND status = ?',
        (int(company_id), int(unit_id), int(epi_id), ACTIVE),
    ).fetchone()
    if not row:
        return 0
    total = row['total'] if hasattr(row, 'keys') else row[0]
    return int(total or 0)


def unit_balance(connection, company_id, unit_id, epi_id) -> dict:
    """Saldo físico, reservado e livre do EPI **naquela unidade**.

    É a fonte para decidir se a solicitação pode ser atendida (§3.5). Note que
    não há parâmetro de escopo: a decisão de atender olha uma unidade só.
    """
    from modules.stock.service import get_unit_stock

    stock = get_unit_stock(connection, int(company_id), int(unit_id), int(epi_id))
    physical = int((stock or {}).get('quantity') or 0)
    reserved = reserved_quantity(connection, company_id, unit_id, epi_id)
    return {
        'company_id': int(company_id),
        'unit_id': int(unit_id),
        'epi_id': int(epi_id),
        'physical': physical,
        'reserved': reserved,
        # Reserva órfã (maior que o físico, por ajuste manual do saldo) não
        # pode virar saldo livre negativo e liberar entrega.
        'free': max(0, physical - reserved),
    }


def create_reservation(
    connection,
    *,
    company_id,
    unit_id,
    epi_id,
    quantity,
    request_id=None,
    actor_user_id=None,
    glove_size='N/A',
    size='N/A',
    uniform_size='N/A',
    notes='',
) -> dict:
    """Reserva ``quantity`` do EPI na unidade, se houver saldo livre.

    Levanta :class:`InsufficientFreeStock` quando não houver — **sem** olhar
    outras unidades. Faltar aqui significa comprar ou transferir, nunca
    consumir o saldo alheio.
    """
    quantity = int(quantity or 0)
    if quantity <= 0:
        raise ValueError('Quantidade da reserva deve ser positiva.')
    if not reservations_ready(connection):
        raise RuntimeError('Reservas de estoque ainda não provisionadas.')

    balance = unit_balance(connection, company_id, unit_id, epi_id)
    if balance['free'] < quantity:
        raise InsufficientFreeStock(
            f'Saldo livre insuficiente na unidade: {balance["free"]} disponível(is), '
            f'{quantity} solicitada(s).'
        )

    now = datetime.now(UTC).isoformat()
    cursor = connection.execute(
        'INSERT INTO stock_reservations ('
        'company_id, unit_id, epi_id, request_id, quantity, status, '
        'glove_size, size, uniform_size, notes, created_by_user_id, created_at, updated_at'
        ') VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
        (
            int(company_id), int(unit_id), int(epi_id),
            int(request_id) if request_id else None,
            quantity, ACTIVE,
            str(glove_size or 'N/A'), str(size or 'N/A'), str(uniform_size or 'N/A'),
            str(notes or ''),
            int(actor_user_id) if actor_user_id else None,
            now, now,
        ),
    )
    reservation_id = int(cursor.lastrowid)

    # Releitura sob a mesma transação: se outra reserva entrou entre o cálculo
    # e a inserção, o saldo livre ficaria negativo. Quem chegou segundo perde.
    if unit_balance(connection, company_id, unit_id, epi_id)['physical'] < reserved_quantity(
        connection, company_id, unit_id, epi_id
    ):
        connection.execute('DELETE FROM stock_reservations WHERE id = ?', (reservation_id,))
        raise InsufficientFreeStock(
            'Saldo livre esgotado por outra operação simultânea. Atualize e tente novamente.'
        )
    return get_reservation(connection, reservation_id)


def get_reservation(connection, reservation_id) -> dict | None:
    row = connection.execute(
        'SELECT * FROM stock_reservations WHERE id = ?', (int(reservation_id),)
    ).fetchone()
    return row_to_dict(row) if row else None


def _claim(connection, reservation_id, new_status, timestamp_column) -> dict:
    """Transição de reserva com claim otimista.

    ``UPDATE ... WHERE status = 'active'`` + ``rowcount`` é o mesmo padrão da
    entrega: garante que só uma operação consuma (ou libere) a reserva, mesmo
    com duas requisições simultâneas.
    """
    now = datetime.now(UTC).isoformat()
    cursor = connection.execute(
        f'UPDATE stock_reservations SET status = ?, {timestamp_column} = ?, '  # noqa: S608
        'updated_at = ? WHERE id = ? AND status = ?',
        (new_status, now, now, int(reservation_id), ACTIVE),
    )
    if int(getattr(cursor, 'rowcount', 0) or 0) != 1:
        current = get_reservation(connection, reservation_id)
        if current is None:
            raise ReservationNotActive('Reserva inexistente.')
        raise ReservationNotActive(
            f'Reserva já {current.get("status")}. Atualize e tente novamente.'
        )
    return get_reservation(connection, reservation_id)


def remaining_quantity(reservation) -> int:
    """Quanto da reserva ainda não foi entregue."""
    if not reservation:
        return 0
    return max(
        0,
        int(reservation.get('quantity') or 0) - int(reservation.get('consumed_quantity') or 0),
    )


def consume_reservation(connection, reservation_id, *, quantity=None, delivery_id=None) -> dict:
    """Abate ``quantity`` da reserva porque a entrega ocorreu.

    **Não baixa o estoque aqui.** A baixa é do fluxo de entrega, que ocorre na
    mesma transação — separar as duas responsabilidades evita que uma reserva
    consumida sem entrega deixe o saldo errado.

    O consumo é **parcial por natureza**: a entrega é sempre de uma unidade
    etiquetada, então uma solicitação de 3 gera 3 entregas contra a mesma
    reserva. A reserva só fecha (``consumed``) quando o último item sai; até
    lá continua ``active`` com o restante ainda prometido a quem solicitou.

    ``quantity=None`` consome o restante — o caso de quem chama sem se
    importar com fracionamento.
    """
    reservation = get_reservation(connection, reservation_id)
    if reservation is None:
        raise ReservationNotActive('Reserva inexistente.')
    if str(reservation.get('status')) != ACTIVE:
        raise ReservationNotActive(
            f'Reserva já {reservation.get("status")}. Atualize e tente novamente.'
        )

    remaining = remaining_quantity(reservation)
    amount = remaining if quantity is None else int(quantity)
    if amount <= 0:
        raise ValueError('Quantidade consumida deve ser positiva.')
    if amount > remaining:
        raise InsufficientFreeStock(
            f'Reserva tem {remaining} unidade(s) pendente(s); {amount} pedida(s).'
        )

    consumed_total = int(reservation.get('consumed_quantity') or 0) + amount
    closes = consumed_total >= int(reservation.get('quantity') or 0)
    now = datetime.now(UTC).isoformat()
    # Claim otimista sobre o que ainda resta: duas entregas simultâneas do
    # último item não podem ambas ter sucesso. A condição de `consumed_quantity`
    # é o que impede a segunda de passar.
    cursor = connection.execute(
        'UPDATE stock_reservations SET consumed_quantity = ?, status = ?, '
        'consumed_at = ?, updated_at = ? '
        'WHERE id = ? AND status = ? AND COALESCE(consumed_quantity, 0) = ?',
        (
            consumed_total,
            CONSUMED if closes else ACTIVE,
            now if closes else str(reservation.get('consumed_at') or ''),
            now,
            int(reservation_id),
            ACTIVE,
            int(reservation.get('consumed_quantity') or 0),
        ),
    )
    if int(getattr(cursor, 'rowcount', 0) or 0) != 1:
        raise ReservationNotActive(
            'Reserva alterada por outra operação simultânea. Atualize e tente novamente.'
        )
    if delivery_id:
        connection.execute(
            'UPDATE stock_reservations SET delivery_id = ? WHERE id = ?',
            (int(delivery_id), int(reservation_id)),
        )
    return get_reservation(connection, reservation_id)


def release_reservation(connection, reservation_id, *, notes='') -> dict:
    """Devolve a quantidade ao saldo livre (cancelamento, recusa, ajuste)."""
    reservation = _claim(connection, reservation_id, RELEASED, 'released_at')
    if notes:
        connection.execute(
            'UPDATE stock_reservations SET notes = ? WHERE id = ?',
            (str(notes), int(reservation_id)),
        )
        reservation = get_reservation(connection, reservation_id)
    return reservation


def fetch_active_reservations(connection, company_id, unit_id=None, epi_id=None) -> list:
    """Reservas ativas, opcionalmente filtradas por unidade e EPI."""
    if not reservations_ready(connection):
        return []
    clauses = ['company_id = ?', 'status = ?']
    params = [int(company_id), ACTIVE]
    if unit_id:
        clauses.append('unit_id = ?')
        params.append(int(unit_id))
    if epi_id:
        clauses.append('epi_id = ?')
        params.append(int(epi_id))
    rows = connection.execute(
        f'SELECT * FROM stock_reservations WHERE {" AND ".join(clauses)} '  # noqa: S608
        'ORDER BY created_at, id',
        tuple(params),
    ).fetchall()
    return [row_to_dict(row) for row in rows]


def reservation_for_request(connection, request_id) -> dict | None:
    """Reserva ativa vinculada a uma solicitação, se houver."""
    if not reservations_ready(connection):
        return None
    row = connection.execute(
        'SELECT * FROM stock_reservations WHERE request_id = ? AND status = ? '
        'ORDER BY id DESC LIMIT 1',
        (int(request_id), ACTIVE),
    ).fetchone()
    return row_to_dict(row) if row else None
