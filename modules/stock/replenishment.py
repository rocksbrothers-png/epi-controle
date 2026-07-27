"""Necessidade de reposição de estoque, por unidade (plano §4).

O estoque mínimo já era detectado, mas apenas *calculado na hora*. Sem registro
persistido não havia como cumprir duas exigências do plano:

- **§4.2 — não duplicar.** Cada avaliação recriava a mesma demanda, sem saber
  que já havia requisição, cotação ou pedido em andamento.
- **§3.8 — rastrear a origem.** A corrente ``solicitação do colaborador →
  necessidade → requisição de compra`` não tinha onde ser gravada.

A necessidade é **sempre de uma unidade**. Duas unidades abaixo do mínimo geram
duas necessidades, nunca uma agregada: consolidar aqui reintroduziria pela
porta dos fundos o estoque compartilhado que o ADR-0001 §15 rejeita.
"""

from datetime import datetime, timezone

from epi_backend.db import row_to_dict, table_columns, table_exists

UTC = timezone.utc

# Origens (§2): são processos diferentes, não o mesmo com rótulos distintos.
ORIGIN_MINIMUM_STOCK = 'minimum_stock'
ORIGIN_EMPLOYEE_REQUEST = 'employee_request'
ORIGINS = (ORIGIN_MINIMUM_STOCK, ORIGIN_EMPLOYEE_REQUEST)

OPEN = 'open'
IN_PURCHASE = 'in_purchase'
FULFILLED = 'fulfilled'
CANCELLED = 'cancelled'

#: Estados em que a necessidade ainda conta para a antiduplicidade.
LIVE_STATUSES = (OPEN, IN_PURCHASE)

#: Requisição de compra cujo item já não representa material a caminho.
#: Espelha `_PURCHASE_REQUEST_TERMINAL_STATUSES` de modules/purchases.
PURCHASE_SETTLED_STATUSES = ('rejected', 'cancelled', 'closed', 'checked', 'received')


def replenishment_ready(connection) -> bool:
    return table_exists(connection, 'stock_replenishment_needs')


def _epi_levels(connection, epi_id) -> dict:
    """Mínimo e máximo configurados do EPI.

    Máximo zero significa **não configurado**: o alvo cai para o mínimo. Sem
    esse fallback, uma base que nunca configurou máximo sugeriria compra
    negativa e a reposição simplesmente não aconteceria.
    """
    columns = table_columns(connection, 'epis')
    selected = ['minimum_stock'] + (['maximum_stock'] if 'maximum_stock' in columns else [])
    row = connection.execute(
        f'SELECT {", ".join(selected)} FROM epis WHERE id = ?',  # noqa: S608
        (int(epi_id),),
    ).fetchone()
    if not row:
        return {'minimum': 0, 'maximum': 0, 'target': 0}
    data = row_to_dict(row)
    minimum = int(data.get('minimum_stock') or 0)
    maximum = int(data.get('maximum_stock') or 0)
    return {'minimum': minimum, 'maximum': maximum, 'target': maximum or minimum}


def on_order_quantity(connection, company_id, unit_id, epi_id) -> int:
    """Quantidade já em processo de aquisição e ainda não recebida.

    Conta itens de requisição de compra **daquela unidade** cujo processo não
    chegou a um estado terminal. Ignorar isto faria a segunda avaliação pedir
    de novo o que já está a caminho — a duplicidade que o §4.2 proíbe.
    """
    if not table_exists(connection, 'purchase_request_items'):
        return 0
    placeholders = ', '.join(['?'] * len(PURCHASE_SETTLED_STATUSES))
    row = connection.execute(
        'SELECT COALESCE(SUM(CASE WHEN pri.quantity_approved > 0 '
        'THEN pri.quantity_approved ELSE pri.quantity_requested END), 0) AS total '
        'FROM purchase_request_items pri '
        'JOIN purchase_requests pr ON pr.id = pri.purchase_request_id '
        'WHERE pri.company_id = ? AND pri.unit_id = ? AND pri.epi_id = ? '
        f'AND LOWER(COALESCE(pr.status, \'\')) NOT IN ({placeholders}) '  # noqa: S608
        f'AND LOWER(COALESCE(pri.status, \'\')) NOT IN ({placeholders})',  # noqa: S608
        (
            int(company_id), int(unit_id), int(epi_id),
            *PURCHASE_SETTLED_STATUSES, *PURCHASE_SETTLED_STATUSES,
        ),
    ).fetchone()
    total = (row['total'] if hasattr(row, 'keys') else row[0]) if row else 0
    return int(total or 0)


def pending_demand_quantity(connection, company_id, unit_id, epi_id) -> int:
    """Demanda de colaboradores ainda descoberta, naquela unidade.

    São as solicitações vivas que ainda não viraram reserva: exatamente o que o
    §4.3 chama de "demandas confirmadas ainda não cobertas". Solicitação já
    reservada não entra — a peça dela já está separada do saldo livre.
    """
    if not table_exists(connection, 'epi_requests'):
        return 0
    from modules.epis.request_states import (
        APPROVED,
        SUBMITTED,
        UNDER_REVIEW,
        WAITING_STOCK,
    )

    uncovered = (SUBMITTED, UNDER_REVIEW, APPROVED, WAITING_STOCK)
    placeholders = ', '.join(['?'] * len(uncovered))
    row = connection.execute(
        'SELECT COALESCE(SUM(quantity), 0) AS total FROM epi_requests '
        'WHERE company_id = ? AND unit_id = ? AND epi_id = ? '
        f'AND LOWER(COALESCE(status, \'\')) IN ({placeholders})',  # noqa: S608
        (int(company_id), int(unit_id), int(epi_id), *uncovered),
    ).fetchone()
    total = (row['total'] if hasattr(row, 'keys') else row[0]) if row else 0
    return int(total or 0)


def evaluate_need(connection, company_id, unit_id, epi_id) -> dict:
    """Retrato da situação e quantidade sugerida (§4.3).

    Fórmula, com piso zero::

        sugerida = alvo − saldo livre − em compra não recebida + demanda descoberta

    Usa **saldo livre**, não físico: o que já está prometido a alguém não pode
    contar como disponível para decidir se falta comprar.
    """
    from modules.stock.reservations import unit_balance

    balance = unit_balance(connection, company_id, unit_id, epi_id)
    levels = _epi_levels(connection, epi_id)
    on_order = on_order_quantity(connection, company_id, unit_id, epi_id)
    pending = pending_demand_quantity(connection, company_id, unit_id, epi_id)
    suggested = levels['target'] - balance['free'] - on_order + pending
    return {
        'company_id': int(company_id),
        'unit_id': int(unit_id),
        'epi_id': int(epi_id),
        'physical_stock': balance['physical'],
        'reserved_stock': balance['reserved'],
        'free_stock': balance['free'],
        'minimum_stock': levels['minimum'],
        'maximum_stock': levels['maximum'],
        'target_stock': levels['target'],
        'on_order_quantity': on_order,
        'pending_demand_quantity': pending,
        # Nunca negativa: sobra de estoque não vira "compra de -3".
        'suggested_quantity': max(0, suggested),
        # Gatilho do §4.1: no mínimo OU abaixo, coerente com o card do
        # dashboard, que usa `<=`.
        'below_threshold': balance['free'] <= levels['minimum'],
    }


def open_need_for(connection, company_id, unit_id, epi_id) -> dict | None:
    """Necessidade viva para o mesmo EPI/unidade, se houver (§4.2)."""
    if not replenishment_ready(connection):
        return None
    placeholders = ', '.join(['?'] * len(LIVE_STATUSES))
    row = connection.execute(
        'SELECT * FROM stock_replenishment_needs '
        'WHERE company_id = ? AND unit_id = ? AND epi_id = ? '
        f'AND status IN ({placeholders}) ORDER BY id DESC LIMIT 1',  # noqa: S608
        (int(company_id), int(unit_id), int(epi_id), *LIVE_STATUSES),
    ).fetchone()
    return row_to_dict(row) if row else None


def register_need(
    connection,
    *,
    company_id,
    unit_id,
    epi_id,
    origin=ORIGIN_MINIMUM_STOCK,
    employee_request_id=None,
    trigger_rule='',
    notes='',
) -> dict | None:
    """Registra a necessidade, **sem duplicar** (§4.2).

    Já existindo necessidade viva para o mesmo EPI/unidade, ela é *atualizada*
    com o retrato novo em vez de gerar outra. Devolve ``None`` quando não há o
    que repor — o chamador pode varrer o catálogo inteiro sem filtrar antes.
    """
    if not replenishment_ready(connection):
        return None
    if origin not in ORIGINS:
        raise ValueError(f'Origem inválida: {origin!r}.')

    snapshot = evaluate_need(connection, company_id, unit_id, epi_id)
    triggered = snapshot['below_threshold'] or origin == ORIGIN_EMPLOYEE_REQUEST
    if not triggered or snapshot['suggested_quantity'] <= 0:
        return None

    now = datetime.now(UTC).isoformat()
    existing = open_need_for(connection, company_id, unit_id, epi_id)
    if existing:
        connection.execute(
            'UPDATE stock_replenishment_needs SET physical_stock = ?, reserved_stock = ?, '
            'free_stock = ?, minimum_stock = ?, maximum_stock = ?, on_order_quantity = ?, '
            'pending_demand_quantity = ?, suggested_quantity = ?, updated_at = ?, '
            # Uma necessidade nascida do mínimo que passa a ter solicitação de
            # colaborador vinculada muda de origem: o atendimento de uma pessoa
            # passa a depender dela, e isso muda a prioridade do comprador.
            'origin = CASE WHEN ? = ? THEN ? ELSE origin END, '
            'employee_request_id = COALESCE(?, employee_request_id) '
            'WHERE id = ?',
            (
                snapshot['physical_stock'], snapshot['reserved_stock'], snapshot['free_stock'],
                snapshot['minimum_stock'], snapshot['maximum_stock'],
                snapshot['on_order_quantity'], snapshot['pending_demand_quantity'],
                snapshot['suggested_quantity'], now,
                origin, ORIGIN_EMPLOYEE_REQUEST, ORIGIN_EMPLOYEE_REQUEST,
                int(employee_request_id) if employee_request_id else None,
                int(existing['id']),
            ),
        )
        return get_need(connection, existing['id'])

    cursor = connection.execute(
        'INSERT INTO stock_replenishment_needs ('
        'company_id, unit_id, epi_id, origin, status, physical_stock, reserved_stock, '
        'free_stock, minimum_stock, maximum_stock, on_order_quantity, '
        'pending_demand_quantity, suggested_quantity, employee_request_id, '
        'trigger_rule, notes, created_at, updated_at'
        ') VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
        (
            int(company_id), int(unit_id), int(epi_id), origin, OPEN,
            snapshot['physical_stock'], snapshot['reserved_stock'], snapshot['free_stock'],
            snapshot['minimum_stock'], snapshot['maximum_stock'],
            snapshot['on_order_quantity'], snapshot['pending_demand_quantity'],
            snapshot['suggested_quantity'],
            int(employee_request_id) if employee_request_id else None,
            str(trigger_rule or _default_rule(origin, snapshot)), str(notes or ''),
            now, now,
        ),
    )
    return get_need(connection, int(cursor.lastrowid))


def _default_rule(origin, snapshot) -> str:
    """Explica o gatilho em texto — §4.2 exige registrar a regra."""
    if origin == ORIGIN_EMPLOYEE_REQUEST:
        return 'solicitação de colaborador sem saldo livre na unidade'
    return (
        f'saldo livre {snapshot["free_stock"]} <= mínimo {snapshot["minimum_stock"]} '
        f'(alvo {snapshot["target_stock"]})'
    )


def get_need(connection, need_id) -> dict | None:
    row = connection.execute(
        'SELECT * FROM stock_replenishment_needs WHERE id = ?', (int(need_id),)
    ).fetchone()
    return row_to_dict(row) if row else None


def link_to_purchase_request(connection, need_id, purchase_request_id) -> dict:
    """Fecha a corrente ``necessidade → requisição de compra`` (§3.8)."""
    now = datetime.now(UTC).isoformat()
    connection.execute(
        'UPDATE stock_replenishment_needs SET purchase_request_id = ?, status = ?, '
        'updated_at = ? WHERE id = ?',
        (int(purchase_request_id), IN_PURCHASE, now, int(need_id)),
    )
    return get_need(connection, need_id)


def close_need(connection, need_id, *, status=FULFILLED, notes='') -> dict:
    """Encerra a necessidade (material recebido, ou cancelada)."""
    if status not in (FULFILLED, CANCELLED):
        raise ValueError(f'Status de encerramento inválido: {status!r}.')
    now = datetime.now(UTC).isoformat()
    connection.execute(
        'UPDATE stock_replenishment_needs SET status = ?, closed_at = ?, updated_at = ?, '
        'notes = CASE WHEN ? <> \'\' THEN ? ELSE notes END WHERE id = ?',
        (status, now, now, str(notes or ''), str(notes or ''), int(need_id)),
    )
    return get_need(connection, need_id)


def fetch_open_needs(connection, company_id, unit_id=None) -> list:
    """Necessidades vivas, para a fila do comprador."""
    if not replenishment_ready(connection):
        return []
    clauses = ['company_id = ?']
    params = [int(company_id)]
    if unit_id:
        clauses.append('unit_id = ?')
        params.append(int(unit_id))
    placeholders = ', '.join(['?'] * len(LIVE_STATUSES))
    rows = connection.execute(
        f'SELECT * FROM stock_replenishment_needs WHERE {" AND ".join(clauses)} '  # noqa: S608
        f'AND status IN ({placeholders}) ORDER BY unit_id, epi_id, id',
        (*params, *LIVE_STATUSES),
    ).fetchall()
    return [row_to_dict(row) for row in rows]
