"""Reserva de estoque por unidade (plano §3.5, §3.6, §10, §15.1, §18).

O sistema só conhecia o saldo físico. Sem reserva, duas solicitações podiam ser
aprovadas sobre a mesma peça e a segunda descobria o problema na entrega.
"""

import sqlite3

import pytest

from core.schema import ensure_stock_reservations
from modules.stock.reservations import (
    ACTIVE,
    CONSUMED,
    RELEASED,
    InsufficientFreeStock,
    ReservationNotActive,
    consume_reservation,
    create_reservation,
    fetch_active_reservations,
    release_reservation,
    reservation_for_request,
    reservations_ready,
    reserved_quantity,
    unit_balance,
)

MATRIZ = 1
FILIAL = 2
EPI = 99


def _conn(stock_matriz=10, stock_filial=7, with_reservations=True):
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        CREATE TABLE companies (id INTEGER PRIMARY KEY, name TEXT, cnpj TEXT);
        CREATE TABLE units (id INTEGER PRIMARY KEY, company_id INTEGER, name TEXT);
        CREATE TABLE epis (id INTEGER PRIMARY KEY, name TEXT);
        CREATE TABLE epi_requests (id INTEGER PRIMARY KEY, company_id INTEGER, status TEXT);
        CREATE TABLE unit_epi_stock (
            id INTEGER PRIMARY KEY AUTOINCREMENT, company_id INTEGER, unit_id INTEGER,
            epi_id INTEGER, quantity INTEGER, updated_at TEXT
        );
        INSERT INTO companies (id, name, cnpj) VALUES (1, 'ACME', '11.222.333/0001-81');
        INSERT INTO units (id, company_id, name) VALUES (1, 1, 'Matriz SP'), (2, 1, 'Filial RJ');
        INSERT INTO epis (id, name) VALUES (99, 'Luva');
        """
    )
    conn.execute(
        'INSERT INTO unit_epi_stock (company_id, unit_id, epi_id, quantity, updated_at) '
        "VALUES (1, ?, ?, ?, '2026-01-01')", (MATRIZ, EPI, stock_matriz),
    )
    conn.execute(
        'INSERT INTO unit_epi_stock (company_id, unit_id, epi_id, quantity, updated_at) '
        "VALUES (1, ?, ?, ?, '2026-01-01')", (FILIAL, EPI, stock_filial),
    )
    conn.commit()
    if with_reservations:
        ensure_stock_reservations(conn)
        conn.commit()
    return conn


def _reserve(conn, quantity, unit_id=MATRIZ, request_id=None):
    return create_reservation(
        conn, company_id=1, unit_id=unit_id, epi_id=EPI,
        quantity=quantity, request_id=request_id,
    )


# ── saldo livre ──────────────────────────────────────────────────────────────

def test_free_equals_physical_when_nothing_is_reserved():
    conn = _conn()
    balance = unit_balance(conn, 1, MATRIZ, EPI)
    assert balance == {
        'company_id': 1, 'unit_id': MATRIZ, 'epi_id': EPI,
        'physical': 10, 'reserved': 0, 'free': 10,
    }


def test_reservation_reduces_free_but_not_physical():
    """§3.6: a reserva não baixa o estoque, só reduz o disponível."""
    conn = _conn()
    _reserve(conn, 4)
    balance = unit_balance(conn, 1, MATRIZ, EPI)
    assert balance['physical'] == 10, 'reserva não pode baixar o físico'
    assert balance['reserved'] == 4
    assert balance['free'] == 6


def test_consumed_and_released_stop_counting_as_reserved():
    conn = _conn()
    consumed = _reserve(conn, 3)
    released = _reserve(conn, 2)
    assert unit_balance(conn, 1, MATRIZ, EPI)['free'] == 5

    consume_reservation(conn, consumed['id'])
    release_reservation(conn, released['id'])
    assert reserved_quantity(conn, 1, MATRIZ, EPI) == 0
    # Consumir não baixa o físico aqui — a baixa é do fluxo de entrega.
    assert unit_balance(conn, 1, MATRIZ, EPI)['physical'] == 10


def test_orphan_reservation_never_makes_free_negative():
    """Ajuste manual do saldo pode deixar reserva maior que o físico.

    Saldo livre negativo liberaria entrega do que não existe; o piso é zero.
    """
    conn = _conn()
    _reserve(conn, 8)
    conn.execute('UPDATE unit_epi_stock SET quantity = 3 WHERE unit_id = ?', (MATRIZ,))
    conn.commit()
    balance = unit_balance(conn, 1, MATRIZ, EPI)
    assert balance['reserved'] == 8
    assert balance['free'] == 0


# ── isolamento entre unidades (ADR-0001 §15) ─────────────────────────────────

def test_reservation_of_one_unit_does_not_touch_another():
    conn = _conn()
    _reserve(conn, 6, unit_id=MATRIZ)
    assert unit_balance(conn, 1, MATRIZ, EPI)['free'] == 4
    assert unit_balance(conn, 1, FILIAL, EPI)['free'] == 7, 'filial intocada'


def test_shortage_does_not_borrow_from_another_unit():
    """§3.8: faltar aqui significa comprar ou transferir, nunca consumir alheio.

    Há 7 na filial; ainda assim reservar 11 na matriz (que tem 10) falha.
    """
    conn = _conn()
    with pytest.raises(InsufficientFreeStock, match='Saldo livre insuficiente'):
        _reserve(conn, 11, unit_id=MATRIZ)


def test_insufficient_message_reports_the_unit_numbers():
    conn = _conn()
    _reserve(conn, 8)
    with pytest.raises(InsufficientFreeStock) as exc:
        _reserve(conn, 5)
    assert '2 disponível' in str(exc.value)


# ── concorrência (§18) ───────────────────────────────────────────────────────

def test_two_reservations_cannot_oversell_the_last_item():
    """§22 cenário 8: só uma leva o último item; a outra fica sem."""
    conn = _conn(stock_matriz=1)
    first = _reserve(conn, 1)
    assert first['status'] == ACTIVE
    with pytest.raises(InsufficientFreeStock):
        _reserve(conn, 1)
    assert unit_balance(conn, 1, MATRIZ, EPI)['free'] == 0


def test_consuming_twice_is_refused():
    """A mesma reserva não pode virar duas entregas."""
    conn = _conn()
    reservation = _reserve(conn, 2)
    consume_reservation(conn, reservation['id'])
    with pytest.raises(ReservationNotActive, match='já consumed'):
        consume_reservation(conn, reservation['id'])


def test_releasing_a_consumed_reservation_is_refused():
    conn = _conn()
    reservation = _reserve(conn, 2)
    consume_reservation(conn, reservation['id'])
    with pytest.raises(ReservationNotActive):
        release_reservation(conn, reservation['id'])


def test_consuming_a_released_reservation_is_refused():
    conn = _conn()
    reservation = _reserve(conn, 2)
    release_reservation(conn, reservation['id'])
    with pytest.raises(ReservationNotActive):
        consume_reservation(conn, reservation['id'])


def test_missing_reservation_is_reported_not_silently_ignored():
    conn = _conn()
    with pytest.raises(ReservationNotActive, match='inexistente'):
        consume_reservation(conn, 4242)


# ── validações e vínculos ────────────────────────────────────────────────────

def test_non_positive_quantity_is_refused():
    conn = _conn()
    for quantity in (0, -1):
        with pytest.raises(ValueError, match='positiva'):
            _reserve(conn, quantity)


def test_reservation_links_to_the_request():
    conn = _conn()
    conn.execute("INSERT INTO epi_requests (id, company_id, status) VALUES (77, 1, 'reservado')")
    conn.commit()
    created = _reserve(conn, 2, request_id=77)
    assert created['request_id'] == 77
    assert reservation_for_request(conn, 77)['id'] == created['id']


def test_request_lookup_ignores_consumed_reservations():
    conn = _conn()
    conn.execute("INSERT INTO epi_requests (id, company_id, status) VALUES (77, 1, 'reservado')")
    conn.commit()
    created = _reserve(conn, 2, request_id=77)
    consume_reservation(conn, created['id'])
    assert reservation_for_request(conn, 77) is None


def test_consume_records_the_delivery():
    conn = _conn()
    reservation = _reserve(conn, 1)
    consumed = consume_reservation(conn, reservation['id'], delivery_id=555)
    assert consumed['status'] == CONSUMED
    assert consumed['delivery_id'] == 555
    assert consumed['consumed_at']


def test_release_records_the_reason():
    conn = _conn()
    reservation = _reserve(conn, 1)
    released = release_reservation(conn, reservation['id'], notes='colaborador recusou')
    assert released['status'] == RELEASED
    assert released['notes'] == 'colaborador recusou'
    assert released['released_at']


def test_fetch_active_filters_by_unit_and_epi():
    conn = _conn()
    _reserve(conn, 1, unit_id=MATRIZ)
    _reserve(conn, 2, unit_id=FILIAL)
    assert len(fetch_active_reservations(conn, 1)) == 2
    assert len(fetch_active_reservations(conn, 1, unit_id=MATRIZ)) == 1
    assert len(fetch_active_reservations(conn, 1, unit_id=MATRIZ, epi_id=EPI)) == 1
    assert fetch_active_reservations(conn, 1, unit_id=MATRIZ, epi_id=12345) == []


# ── degradação graciosa ──────────────────────────────────────────────────────

def test_without_the_table_reads_degrade_instead_of_crashing():
    """Janela de migração: leitura funciona, escrita recusa explicitamente."""
    conn = _conn(with_reservations=False)
    assert not reservations_ready(conn)
    assert reserved_quantity(conn, 1, MATRIZ, EPI) == 0
    assert unit_balance(conn, 1, MATRIZ, EPI)['free'] == 10
    assert fetch_active_reservations(conn, 1) == []
    assert reservation_for_request(conn, 1) is None
    with pytest.raises(RuntimeError, match='não provisionadas'):
        _reserve(conn, 1)


def test_ensure_is_idempotent():
    conn = _conn()
    _reserve(conn, 3)
    ensure_stock_reservations(conn)  # segunda execução não pode perder dados
    assert reserved_quantity(conn, 1, MATRIZ, EPI) == 3
