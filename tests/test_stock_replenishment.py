"""Necessidade de reposição persistida (plano §4).

O estoque mínimo já era detectado, mas só *calculado na hora*. Sem registro não
havia antiduplicidade (§4.2) nem rastro da origem até a compra (§3.8).
"""

import sqlite3

import pytest

from core.schema import ensure_stock_reservations, ensure_stock_replenishment_needs
from modules.stock.replenishment import (
    CANCELLED,
    FULFILLED,
    IN_PURCHASE,
    OPEN,
    ORIGIN_EMPLOYEE_REQUEST,
    ORIGIN_MINIMUM_STOCK,
    close_need,
    evaluate_need,
    fetch_open_needs,
    link_to_purchase_request,
    on_order_quantity,
    open_need_for,
    pending_demand_quantity,
    register_need,
    replenishment_ready,
)
from modules.stock.reservations import create_reservation

MATRIZ, FILIAL, EPI = 1, 2, 99


def _conn(*, stock=4, minimum=10, maximum=30, ready=True):
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        CREATE TABLE companies (id INTEGER PRIMARY KEY, name TEXT, cnpj TEXT);
        CREATE TABLE units (id INTEGER PRIMARY KEY, company_id INTEGER, name TEXT);
        CREATE TABLE epis (id INTEGER PRIMARY KEY, name TEXT, minimum_stock INTEGER DEFAULT 10);
        CREATE TABLE epi_requests (
            id INTEGER PRIMARY KEY, company_id INTEGER, unit_id INTEGER,
            epi_id INTEGER, quantity INTEGER, status TEXT
        );
        CREATE TABLE purchase_requests (id INTEGER PRIMARY KEY, company_id INTEGER, status TEXT);
        CREATE TABLE purchase_request_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT, purchase_request_id INTEGER,
            company_id INTEGER, unit_id INTEGER, epi_id INTEGER,
            quantity_requested INTEGER DEFAULT 0, quantity_approved INTEGER DEFAULT 0,
            status TEXT DEFAULT 'open'
        );
        CREATE TABLE unit_epi_stock (
            id INTEGER PRIMARY KEY AUTOINCREMENT, company_id INTEGER, unit_id INTEGER,
            epi_id INTEGER, quantity INTEGER, updated_at TEXT
        );
        INSERT INTO companies (id, name, cnpj) VALUES (1, 'ACME', '11.222.333/0001-81');
        INSERT INTO units (id, company_id, name) VALUES (1, 1, 'Matriz'), (2, 1, 'Filial');
        """
    )
    conn.execute('INSERT INTO epis (id, name, minimum_stock) VALUES (?, ?, ?)', (EPI, 'Luva', minimum))
    for unit in (MATRIZ, FILIAL):
        conn.execute(
            'INSERT INTO unit_epi_stock (company_id, unit_id, epi_id, quantity, updated_at) '
            "VALUES (1, ?, ?, ?, '2026-01-01')", (unit, EPI, stock),
        )
    conn.commit()
    ensure_stock_reservations(conn)
    if ready:
        ensure_stock_replenishment_needs(conn)
        conn.execute('UPDATE epis SET maximum_stock = ? WHERE id = ?', (maximum, EPI))
    conn.commit()
    return conn


# ── fórmula da quantidade sugerida (§4.3) ────────────────────────────────────

def test_suggested_quantity_follows_the_formula():
    """alvo − livre − em compra + demanda descoberta."""
    conn = _conn(stock=4, minimum=10, maximum=30)
    snapshot = evaluate_need(conn, 1, MATRIZ, EPI)
    assert snapshot['free_stock'] == 4
    assert snapshot['target_stock'] == 30
    assert snapshot['suggested_quantity'] == 26  # 30 - 4 - 0 + 0


def test_suggestion_uses_free_not_physical():
    """O que já está prometido não conta como disponível."""
    conn = _conn(stock=10, minimum=10, maximum=30)
    create_reservation(conn, company_id=1, unit_id=MATRIZ, epi_id=EPI, quantity=6)
    snapshot = evaluate_need(conn, 1, MATRIZ, EPI)
    assert snapshot['physical_stock'] == 10
    assert snapshot['free_stock'] == 4
    assert snapshot['suggested_quantity'] == 26  # sobre o livre, não sobre o físico


def test_suggestion_discounts_what_is_already_on_order():
    """§4.2: não pedir de novo o que já está a caminho."""
    conn = _conn(stock=4, minimum=10, maximum=30)
    conn.execute("INSERT INTO purchase_requests (id, company_id, status) VALUES (1, 1, 'open')")
    conn.execute(
        'INSERT INTO purchase_request_items (purchase_request_id, company_id, unit_id, epi_id, '
        "quantity_requested, status) VALUES (1, 1, ?, ?, 10, 'open')", (MATRIZ, EPI),
    )
    conn.commit()
    assert on_order_quantity(conn, 1, MATRIZ, EPI) == 10
    assert evaluate_need(conn, 1, MATRIZ, EPI)['suggested_quantity'] == 16  # 30 - 4 - 10


def test_settled_purchase_stops_counting_as_on_order():
    """Requisição recebida/cancelada não representa mais material a caminho."""
    conn = _conn(stock=4, minimum=10, maximum=30)
    conn.execute("INSERT INTO purchase_requests (id, company_id, status) VALUES (1, 1, 'received')")
    conn.execute(
        'INSERT INTO purchase_request_items (purchase_request_id, company_id, unit_id, epi_id, '
        "quantity_requested, status) VALUES (1, 1, ?, ?, 10, 'received')", (MATRIZ, EPI),
    )
    conn.commit()
    assert on_order_quantity(conn, 1, MATRIZ, EPI) == 0


def test_approved_quantity_wins_over_requested():
    """Aprovação parcial (§7): o que vem é o aprovado, não o pedido."""
    conn = _conn(stock=4, minimum=10, maximum=30)
    conn.execute("INSERT INTO purchase_requests (id, company_id, status) VALUES (1, 1, 'approved')")
    conn.execute(
        'INSERT INTO purchase_request_items (purchase_request_id, company_id, unit_id, epi_id, '
        "quantity_requested, quantity_approved, status) VALUES (1, 1, ?, ?, 10, 6, 'approved')",
        (MATRIZ, EPI),
    )
    conn.commit()
    assert on_order_quantity(conn, 1, MATRIZ, EPI) == 6


def test_uncovered_employee_demand_increases_the_suggestion():
    conn = _conn(stock=4, minimum=10, maximum=30)
    conn.execute(
        'INSERT INTO epi_requests (id, company_id, unit_id, epi_id, quantity, status) '
        "VALUES (1, 1, ?, ?, 5, 'aguardando estoque')", (MATRIZ, EPI),
    )
    conn.commit()
    assert pending_demand_quantity(conn, 1, MATRIZ, EPI) == 5
    assert evaluate_need(conn, 1, MATRIZ, EPI)['suggested_quantity'] == 31  # 30 - 4 + 5


def test_reserved_request_no_longer_counts_as_uncovered():
    """Solicitação já reservada tem a peça separada do saldo livre."""
    conn = _conn(stock=4, minimum=10, maximum=30)
    conn.execute(
        'INSERT INTO epi_requests (id, company_id, unit_id, epi_id, quantity, status) '
        "VALUES (1, 1, ?, ?, 5, 'reservado')", (MATRIZ, EPI),
    )
    conn.commit()
    assert pending_demand_quantity(conn, 1, MATRIZ, EPI) == 0


def test_suggestion_never_goes_negative():
    """Sobra de estoque não vira "compra de -20"."""
    conn = _conn(stock=50, minimum=10, maximum=30)
    snapshot = evaluate_need(conn, 1, MATRIZ, EPI)
    assert snapshot['suggested_quantity'] == 0
    assert not snapshot['below_threshold']


def test_missing_maximum_falls_back_to_minimum():
    """Base que nunca configurou máximo ainda repõe, mirando o mínimo."""
    conn = _conn(stock=2, minimum=10, maximum=0)
    snapshot = evaluate_need(conn, 1, MATRIZ, EPI)
    assert snapshot['maximum_stock'] == 0
    assert snapshot['target_stock'] == 10
    assert snapshot['suggested_quantity'] == 8


def test_threshold_includes_being_exactly_at_the_minimum():
    """§4.1 usa `<=`, coerente com o card de estoque baixo do dashboard."""
    conn = _conn(stock=10, minimum=10, maximum=30)
    assert evaluate_need(conn, 1, MATRIZ, EPI)['below_threshold']


# ── antiduplicidade (§4.2) ───────────────────────────────────────────────────

def test_second_evaluation_updates_instead_of_duplicating():
    conn = _conn(stock=4, minimum=10, maximum=30)
    first = register_need(conn, company_id=1, unit_id=MATRIZ, epi_id=EPI)
    conn.execute('UPDATE unit_epi_stock SET quantity = 2 WHERE unit_id = ?', (MATRIZ,))
    conn.commit()
    second = register_need(conn, company_id=1, unit_id=MATRIZ, epi_id=EPI)
    assert second['id'] == first['id'], 'não pode criar uma segunda necessidade'
    assert second['suggested_quantity'] == 28  # retrato atualizado
    assert len(fetch_open_needs(conn, 1)) == 1


def test_need_in_purchase_still_blocks_a_duplicate():
    conn = _conn(stock=4, minimum=10, maximum=30)
    need = register_need(conn, company_id=1, unit_id=MATRIZ, epi_id=EPI)
    conn.execute("INSERT INTO purchase_requests (id, company_id, status) VALUES (1, 1, 'open')")
    conn.commit()
    link_to_purchase_request(conn, need['id'], 1)
    again = register_need(conn, company_id=1, unit_id=MATRIZ, epi_id=EPI)
    assert again['id'] == need['id']
    assert again['status'] == IN_PURCHASE


def test_closed_need_does_not_block_a_new_one():
    conn = _conn(stock=4, minimum=10, maximum=30)
    first = register_need(conn, company_id=1, unit_id=MATRIZ, epi_id=EPI)
    close_need(conn, first['id'], status=FULFILLED)
    second = register_need(conn, company_id=1, unit_id=MATRIZ, epi_id=EPI)
    assert second['id'] != first['id']


def test_no_need_is_registered_when_stock_is_healthy():
    conn = _conn(stock=50, minimum=10, maximum=30)
    assert register_need(conn, company_id=1, unit_id=MATRIZ, epi_id=EPI) is None
    assert fetch_open_needs(conn, 1) == []


# ── uma necessidade por unidade (ADR-0001 §15) ───────────────────────────────

def test_each_unit_gets_its_own_need():
    """Consolidar aqui reintroduziria o estoque compartilhado pela porta dos fundos."""
    conn = _conn(stock=4, minimum=10, maximum=30)
    matriz = register_need(conn, company_id=1, unit_id=MATRIZ, epi_id=EPI)
    filial = register_need(conn, company_id=1, unit_id=FILIAL, epi_id=EPI)
    assert matriz['id'] != filial['id']
    assert {n['unit_id'] for n in fetch_open_needs(conn, 1)} == {MATRIZ, FILIAL}
    assert len(fetch_open_needs(conn, 1, unit_id=MATRIZ)) == 1


def test_purchase_on_one_unit_does_not_discount_the_other():
    conn = _conn(stock=4, minimum=10, maximum=30)
    conn.execute("INSERT INTO purchase_requests (id, company_id, status) VALUES (1, 1, 'open')")
    conn.execute(
        'INSERT INTO purchase_request_items (purchase_request_id, company_id, unit_id, epi_id, '
        "quantity_requested, status) VALUES (1, 1, ?, ?, 10, 'open')", (MATRIZ, EPI),
    )
    conn.commit()
    assert on_order_quantity(conn, 1, MATRIZ, EPI) == 10
    assert on_order_quantity(conn, 1, FILIAL, EPI) == 0


# ── origem e rastro (§2, §3.8) ───────────────────────────────────────────────

def test_origins_are_distinct_processes():
    """§2: demanda automática não é uma falsa solicitação de colaborador."""
    conn = _conn(stock=4, minimum=10, maximum=30)
    need = register_need(conn, company_id=1, unit_id=MATRIZ, epi_id=EPI)
    assert need['origin'] == ORIGIN_MINIMUM_STOCK
    assert 'mínimo' in need['trigger_rule']


def test_employee_request_origin_wins_over_minimum_stock():
    """Se o atendimento de alguém passa a depender da compra, a origem muda.

    O comprador precisa ver que há uma pessoa esperando, não só um nível baixo.
    """
    conn = _conn(stock=4, minimum=10, maximum=30)
    conn.execute("INSERT INTO epi_requests (id, company_id, unit_id, epi_id, quantity, status) "
                 "VALUES (7, 1, ?, ?, 2, 'aguardando estoque')", (MATRIZ, EPI))
    conn.commit()
    register_need(conn, company_id=1, unit_id=MATRIZ, epi_id=EPI)
    updated = register_need(
        conn, company_id=1, unit_id=MATRIZ, epi_id=EPI,
        origin=ORIGIN_EMPLOYEE_REQUEST, employee_request_id=7,
    )
    assert updated['origin'] == ORIGIN_EMPLOYEE_REQUEST
    assert updated['employee_request_id'] == 7


def test_employee_request_registers_even_with_healthy_minimum():
    """Falta para atender alguém é necessidade, mesmo acima do mínimo."""
    conn = _conn(stock=10, minimum=2, maximum=12)
    create_reservation(conn, company_id=1, unit_id=MATRIZ, epi_id=EPI, quantity=10)
    need = register_need(
        conn, company_id=1, unit_id=MATRIZ, epi_id=EPI,
        origin=ORIGIN_EMPLOYEE_REQUEST, employee_request_id=None,
    )
    assert need is not None
    assert need['origin'] == ORIGIN_EMPLOYEE_REQUEST
    assert 'colaborador' in need['trigger_rule']


def test_invalid_origin_is_refused():
    conn = _conn()
    with pytest.raises(ValueError, match='Origem inválida'):
        register_need(conn, company_id=1, unit_id=MATRIZ, epi_id=EPI, origin='inventada')


def test_link_and_close_walk_the_chain():
    conn = _conn(stock=4, minimum=10, maximum=30)
    conn.execute("INSERT INTO purchase_requests (id, company_id, status) VALUES (9, 1, 'open')")
    conn.commit()
    need = register_need(conn, company_id=1, unit_id=MATRIZ, epi_id=EPI)
    assert need['status'] == OPEN

    linked = link_to_purchase_request(conn, need['id'], 9)
    assert linked['purchase_request_id'] == 9
    assert linked['status'] == IN_PURCHASE

    closed = close_need(conn, need['id'], status=FULFILLED, notes='recebido')
    assert closed['status'] == FULFILLED
    assert closed['closed_at']
    assert closed['notes'] == 'recebido'
    assert open_need_for(conn, 1, MATRIZ, EPI) is None


def test_invalid_close_status_is_refused():
    conn = _conn(stock=4, minimum=10, maximum=30)
    need = register_need(conn, company_id=1, unit_id=MATRIZ, epi_id=EPI)
    with pytest.raises(ValueError, match='encerramento inválido'):
        close_need(conn, need['id'], status='sei la')
    assert close_need(conn, need['id'], status=CANCELLED)['status'] == CANCELLED


def test_snapshot_is_stored_so_the_number_stays_explainable():
    """Sem o retrato, uma sugestão antiga vira número sem explicação."""
    conn = _conn(stock=4, minimum=10, maximum=30)
    need = register_need(conn, company_id=1, unit_id=MATRIZ, epi_id=EPI)
    assert need['physical_stock'] == 4
    assert need['free_stock'] == 4
    assert need['minimum_stock'] == 10
    assert need['maximum_stock'] == 30
    assert need['on_order_quantity'] == 0
    assert need['pending_demand_quantity'] == 0


# ── degradação graciosa ──────────────────────────────────────────────────────

def test_without_the_table_reads_degrade_and_writes_are_inert():
    conn = _conn(ready=False)
    assert not replenishment_ready(conn)
    assert fetch_open_needs(conn, 1) == []
    assert open_need_for(conn, 1, MATRIZ, EPI) is None
    assert register_need(conn, company_id=1, unit_id=MATRIZ, epi_id=EPI) is None


def test_ensure_is_idempotent():
    conn = _conn(stock=4, minimum=10, maximum=30)
    need = register_need(conn, company_id=1, unit_id=MATRIZ, epi_id=EPI)
    ensure_stock_replenishment_needs(conn)
    assert open_need_for(conn, 1, MATRIZ, EPI)['id'] == need['id']
