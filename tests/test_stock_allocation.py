"""Alocação de estoque recebido às solicitações pendentes (plano §10).

Sem isto, o recebimento alimentava o saldo e as pessoas continuavam esperando
até alguém reparar manualmente.
"""

import sqlite3

from core.schema import ensure_stock_reservations
from modules.epis.request_states import RESERVED, WAITING_STOCK
from modules.stock.allocation import (
    allocate_incoming_stock,
    pending_requests_for,
)
from modules.stock.reservations import reserved_quantity, unit_balance

MATRIZ, FILIAL, EPI = 1, 2, 99


def _conn(stock=0):
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        CREATE TABLE companies (id INTEGER PRIMARY KEY, name TEXT);
        CREATE TABLE units (id INTEGER PRIMARY KEY, company_id INTEGER, name TEXT);
        CREATE TABLE epis (id INTEGER PRIMARY KEY, name TEXT, minimum_stock INTEGER DEFAULT 0);
        CREATE TABLE epi_requests (
            id INTEGER PRIMARY KEY, company_id INTEGER, unit_id INTEGER, epi_id INTEGER,
            quantity INTEGER, status TEXT, urgency TEXT DEFAULT 'normal',
            approved_at TEXT DEFAULT '', requested_at TEXT DEFAULT '',
            glove_size TEXT DEFAULT 'N/A', size TEXT DEFAULT 'N/A',
            uniform_size TEXT DEFAULT 'N/A', last_updated_at TEXT DEFAULT ''
        );
        CREATE TABLE epi_request_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT, request_id INTEGER, company_id INTEGER,
            status TEXT, notes TEXT, actor_name TEXT, created_at TEXT
        );
        CREATE TABLE unit_epi_stock (
            id INTEGER PRIMARY KEY AUTOINCREMENT, company_id INTEGER, unit_id INTEGER,
            epi_id INTEGER, quantity INTEGER, updated_at TEXT
        );
        INSERT INTO companies (id, name) VALUES (1, 'ACME');
        INSERT INTO units (id, company_id, name) VALUES (1, 1, 'Matriz'), (2, 1, 'Filial');
        INSERT INTO epis (id, name) VALUES (99, 'Luva');
        """
    )
    for unit in (MATRIZ, FILIAL):
        conn.execute(
            'INSERT INTO unit_epi_stock (company_id, unit_id, epi_id, quantity, updated_at) '
            "VALUES (1, ?, ?, ?, '2026-01-01')", (unit, EPI, stock),
        )
    conn.commit()
    ensure_stock_reservations(conn)
    conn.commit()
    return conn


def _request(conn, request_id, *, quantity=1, unit_id=MATRIZ, urgency='normal',
             approved_at='', requested_at='2026-01-01', status=WAITING_STOCK):
    conn.execute(
        'INSERT INTO epi_requests (id, company_id, unit_id, epi_id, quantity, status, '
        'urgency, approved_at, requested_at) VALUES (?, 1, ?, ?, ?, ?, ?, ?, ?)',
        (request_id, unit_id, EPI, quantity, status, urgency, approved_at, requested_at),
    )
    conn.commit()


def _status(conn, request_id):
    return conn.execute('SELECT status FROM epi_requests WHERE id = ?', (request_id,)).fetchone()['status']


# ── ordem de atendimento (§10) ───────────────────────────────────────────────

def test_urgency_comes_before_dates():
    conn = _conn()
    _request(conn, 1, urgency='normal', requested_at='2026-01-01')
    _request(conn, 2, urgency='alta', requested_at='2026-06-01')
    _request(conn, 3, urgency='critica', requested_at='2026-09-01')
    assert [r['id'] for r in pending_requests_for(conn, 1, MATRIZ, EPI)] == [3, 2, 1]


def test_approval_date_breaks_ties_within_the_same_urgency():
    conn = _conn()
    _request(conn, 1, approved_at='2026-05-01', requested_at='2026-01-01')
    _request(conn, 2, approved_at='2026-02-01', requested_at='2026-04-01')
    assert [r['id'] for r in pending_requests_for(conn, 1, MATRIZ, EPI)] == [2, 1]


def test_request_date_breaks_ties_when_approval_matches():
    conn = _conn()
    _request(conn, 1, approved_at='2026-05-01', requested_at='2026-03-01')
    _request(conn, 2, approved_at='2026-05-01', requested_at='2026-01-01')
    assert [r['id'] for r in pending_requests_for(conn, 1, MATRIZ, EPI)] == [2, 1]


def test_id_is_the_final_tiebreaker():
    """Sem ele, duas do mesmo instante alternariam de posição entre execuções."""
    conn = _conn()
    _request(conn, 7, approved_at='2026-05-01', requested_at='2026-01-01')
    _request(conn, 3, approved_at='2026-05-01', requested_at='2026-01-01')
    assert [r['id'] for r in pending_requests_for(conn, 1, MATRIZ, EPI)] == [3, 7]


def test_unknown_urgency_falls_back_to_normal():
    """Dado inesperado não pula na frente nem afunda a fila."""
    conn = _conn()
    _request(conn, 1, urgency='urgentíssimo!!', requested_at='2026-05-01')
    _request(conn, 2, urgency='alta', requested_at='2026-09-01')
    _request(conn, 3, urgency='baixa', requested_at='2026-01-01')
    assert [r['id'] for r in pending_requests_for(conn, 1, MATRIZ, EPI)] == [2, 1, 3]


def test_only_waiting_stock_requests_enter_the_queue():
    conn = _conn()
    _request(conn, 1, status=WAITING_STOCK)
    _request(conn, 2, status='reservado')
    _request(conn, 3, status='entregue')
    assert [r['id'] for r in pending_requests_for(conn, 1, MATRIZ, EPI)] == [1]


# ── isolamento entre unidades (ADR-0001 §15) ─────────────────────────────────

def test_queue_never_includes_another_unit():
    conn = _conn()
    _request(conn, 1, unit_id=MATRIZ)
    _request(conn, 2, unit_id=FILIAL)
    assert [r['id'] for r in pending_requests_for(conn, 1, MATRIZ, EPI)] == [1]


def test_incoming_stock_never_serves_another_unit():
    """Material entrou na matriz; a filial continua esperando."""
    conn = _conn(stock=0)
    _request(conn, 1, unit_id=FILIAL, quantity=5)
    conn.execute('UPDATE unit_epi_stock SET quantity = 10 WHERE unit_id = ?', (MATRIZ,))
    conn.commit()

    assert allocate_incoming_stock(conn, 1, MATRIZ, EPI) == []
    assert _status(conn, 1) == WAITING_STOCK
    assert reserved_quantity(conn, 1, FILIAL, EPI) == 0


# ── alocação ─────────────────────────────────────────────────────────────────

def test_incoming_stock_reserves_for_whoever_was_waiting():
    conn = _conn(stock=0)
    _request(conn, 1, quantity=3)
    conn.execute('UPDATE unit_epi_stock SET quantity = 5 WHERE unit_id = ?', (MATRIZ,))
    conn.commit()

    allocated = allocate_incoming_stock(conn, 1, MATRIZ, EPI)
    assert len(allocated) == 1
    assert allocated[0]['request_id'] == 1
    assert _status(conn, 1) == RESERVED
    assert reserved_quantity(conn, 1, MATRIZ, EPI) == 3


def test_allocation_reserves_but_never_writes_off():
    """Reserva promete a peça; a baixa continua sendo da entrega."""
    conn = _conn(stock=0)
    _request(conn, 1, quantity=4)
    conn.execute('UPDATE unit_epi_stock SET quantity = 4 WHERE unit_id = ?', (MATRIZ,))
    conn.commit()

    allocate_incoming_stock(conn, 1, MATRIZ, EPI)
    balance = unit_balance(conn, 1, MATRIZ, EPI)
    assert balance['physical'] == 4, 'entrada não pode ser baixada na alocação'
    assert balance['reserved'] == 4
    assert balance['free'] == 0


def test_allocation_serves_the_queue_in_order_until_stock_runs_out():
    conn = _conn(stock=0)
    _request(conn, 1, quantity=2, urgency='normal', requested_at='2026-01-01')
    _request(conn, 2, quantity=2, urgency='alta', requested_at='2026-06-01')
    conn.execute('UPDATE unit_epi_stock SET quantity = 2 WHERE unit_id = ?', (MATRIZ,))
    conn.commit()

    allocated = allocate_incoming_stock(conn, 1, MATRIZ, EPI)
    assert [a['request_id'] for a in allocated] == [2], 'a urgente leva'
    assert _status(conn, 2) == RESERVED
    assert _status(conn, 1) == WAITING_STOCK


def test_allocation_stops_instead_of_skipping_to_a_smaller_request():
    """Atender fora de ordem quebraria a prioridade recém-estabelecida.

    Há saldo para a segunda (menor), mas a primeira da fila não cabe: para.
    """
    conn = _conn(stock=0)
    _request(conn, 1, quantity=10, requested_at='2026-01-01')
    _request(conn, 2, quantity=1, requested_at='2026-02-01')
    conn.execute('UPDATE unit_epi_stock SET quantity = 5 WHERE unit_id = ?', (MATRIZ,))
    conn.commit()

    assert allocate_incoming_stock(conn, 1, MATRIZ, EPI) == []
    assert _status(conn, 1) == WAITING_STOCK
    assert _status(conn, 2) == WAITING_STOCK


def test_partial_fulfilment_is_never_automatic():
    """§3.8: atendimento parcial exige decisão do Gestor de EPI."""
    conn = _conn(stock=0)
    _request(conn, 1, quantity=10)
    conn.execute('UPDATE unit_epi_stock SET quantity = 6 WHERE unit_id = ?', (MATRIZ,))
    conn.commit()

    assert allocate_incoming_stock(conn, 1, MATRIZ, EPI) == []
    assert reserved_quantity(conn, 1, MATRIZ, EPI) == 0, 'nada de reserva parcial'


def test_existing_reservations_reduce_what_is_allocatable():
    conn = _conn(stock=0)
    _request(conn, 1, quantity=3)
    conn.execute('UPDATE unit_epi_stock SET quantity = 5 WHERE unit_id = ?', (MATRIZ,))
    conn.commit()
    from modules.stock.reservations import create_reservation
    create_reservation(conn, company_id=1, unit_id=MATRIZ, epi_id=EPI, quantity=4)

    assert allocate_incoming_stock(conn, 1, MATRIZ, EPI) == []


def test_allocation_is_recorded_in_the_request_history():
    """A alocação automática também presta contas."""
    conn = _conn(stock=0)
    _request(conn, 1, quantity=1)
    conn.execute('UPDATE unit_epi_stock SET quantity = 1 WHERE unit_id = ?', (MATRIZ,))
    conn.commit()

    allocate_incoming_stock(conn, 1, MATRIZ, EPI)
    row = conn.execute('SELECT * FROM epi_request_history WHERE request_id = 1').fetchone()
    assert row['status'] == RESERVED
    assert 'automaticamente' in row['notes']
    assert row['actor_name'] == 'Sistema'


def test_running_twice_does_not_double_reserve():
    conn = _conn(stock=0)
    _request(conn, 1, quantity=2)
    conn.execute('UPDATE unit_epi_stock SET quantity = 10 WHERE unit_id = ?', (MATRIZ,))
    conn.commit()

    allocate_incoming_stock(conn, 1, MATRIZ, EPI)
    # A solicitação saiu de "aguardando estoque"; a segunda passada não a vê.
    assert allocate_incoming_stock(conn, 1, MATRIZ, EPI) == []
    assert reserved_quantity(conn, 1, MATRIZ, EPI) == 2


def test_zero_quantity_request_is_skipped_without_breaking_the_queue():
    conn = _conn(stock=0)
    _request(conn, 1, quantity=0, requested_at='2026-01-01')
    _request(conn, 2, quantity=1, requested_at='2026-02-01')
    conn.execute('UPDATE unit_epi_stock SET quantity = 5 WHERE unit_id = ?', (MATRIZ,))
    conn.commit()

    allocated = allocate_incoming_stock(conn, 1, MATRIZ, EPI)
    assert [a['request_id'] for a in allocated] == [2]


def test_nothing_waiting_means_nothing_allocated():
    conn = _conn(stock=10)
    assert allocate_incoming_stock(conn, 1, MATRIZ, EPI) == []
