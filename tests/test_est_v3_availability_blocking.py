"""EST-V3 / G01 — bloquear reduz o DISPONÍVEL (não o físico); bloqueio estruturado.

O agregado unit_epi_stock.quantity é o FÍSICO (inclui bloqueado). O disponível
real (unit_balance.free) passa a excluir as peças bloqueadas (derivado do status
real em epi_stock_items), de modo que não se reserva nem se promete peça
bloqueada. set_stock_item_status grava motivo/responsável/horário estruturados
na peça (colunas EST-V2) ao bloquear, e os limpa ao desbloquear.
"""

import sqlite3

from core.schema import ensure_stock_lifecycle_model
from modules.stock.reservations import unit_balance
from modules.stock.service import blocked_physical_quantity, set_stock_item_status


def _conn(quantity=10):
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        CREATE TABLE epis (id INTEGER PRIMARY KEY, name TEXT, epi_validity_date TEXT DEFAULT '');
        CREATE TABLE unit_epi_stock (
            id INTEGER PRIMARY KEY AUTOINCREMENT, company_id INTEGER, unit_id INTEGER,
            epi_id INTEGER, quantity INTEGER, updated_at TEXT
        );
        CREATE TABLE epi_stock_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT, company_id INTEGER, unit_id INTEGER, epi_id INTEGER,
            glove_size TEXT DEFAULT 'N/A', size TEXT DEFAULT 'N/A', uniform_size TEXT DEFAULT 'N/A',
            qr_code_value TEXT DEFAULT '', status TEXT DEFAULT 'in_stock',
            manufacture_date TEXT DEFAULT '', created_at TEXT DEFAULT '', updated_at TEXT DEFAULT ''
        );
        CREATE TABLE stock_movements (
            id INTEGER PRIMARY KEY AUTOINCREMENT, company_id INTEGER, unit_id INTEGER, epi_id INTEGER,
            movement_type TEXT, quantity INTEGER, previous_stock INTEGER, new_stock INTEGER,
            source_type TEXT, source_id INTEGER, notes TEXT, actor_user_id INTEGER, actor_name TEXT,
            created_at TEXT, glove_size TEXT, size TEXT, uniform_size TEXT
        );
        INSERT INTO epis (id, name) VALUES (7, 'Capacete');
        """
    )
    conn.execute(
        "INSERT INTO unit_epi_stock (company_id, unit_id, epi_id, quantity, updated_at) VALUES (1, 2, 7, ?, '')",
        (quantity,),
    )
    ensure_stock_lifecycle_model(conn)
    conn.commit()
    return conn


def _add_item(conn, iid, status='in_stock'):
    conn.execute(
        "INSERT INTO epi_stock_items (id, company_id, unit_id, epi_id, qr_code_value, status) "
        "VALUES (?, 1, 2, 7, ?, ?)",
        (iid, f'QR-{iid}', status),
    )
    conn.commit()
    return conn.execute('SELECT * FROM epi_stock_items WHERE id = ?', (iid,)).fetchone()


def test_block_reduces_free_not_physical():
    conn = _conn(quantity=10)
    for iid in (1, 2, 3):
        _add_item(conn, iid, 'in_stock')
    before = unit_balance(conn, 1, 2, 7)
    assert before['physical'] == 10 and before['free'] == 10 and before['reserved'] == 0

    set_stock_item_status(conn, _add_item(conn, 4, 'in_stock'), 'blocked_expired', 'vencido', 3, 'Admin', 'now')
    set_stock_item_status(conn, conn.execute('SELECT * FROM epi_stock_items WHERE id=1').fetchone(),
                          'blocked_discard', 'avaria', 3, 'Admin', 'now')
    after = unit_balance(conn, 1, 2, 7)
    assert after['physical'] == 10, 'físico preservado'
    assert blocked_physical_quantity(conn, 1, 2, 7) == 2
    assert after['free'] == 8, 'disponível desconta as 2 peças bloqueadas'


def test_free_floors_at_zero_when_blocked_exceeds_physical():
    conn = _conn(quantity=2)
    for iid in range(1, 6):  # 5 peças bloqueadas, físico agregado só 2
        _add_item(conn, iid, 'blocked_expired')
    bal = unit_balance(conn, 1, 2, 7)
    assert bal['physical'] == 2 and bal['free'] == 0


def test_unit_balance_dict_shape_preserved():
    # contrato de unit_balance: mesmas 5 chaves (sem 'blocked')
    conn = _conn(quantity=4)
    assert set(unit_balance(conn, 1, 2, 7).keys()) == {'company_id', 'unit_id', 'epi_id', 'physical', 'reserved', 'free'}


def test_block_records_structured_reason_and_actor():
    conn = _conn()
    set_stock_item_status(conn, _add_item(conn, 1, 'in_stock'), 'blocked_expired', 'lote vencido', 9, 'HSE', 'now')
    row = conn.execute(
        'SELECT status, blocking_reason_code, blocking_justification, blocked_by_user_id, blocked_at '
        'FROM epi_stock_items WHERE id = 1'
    ).fetchone()
    assert row['status'] == 'blocked_expired'
    assert row['blocking_reason_code'] == 'expired'
    assert row['blocking_justification'] == 'lote vencido'
    assert row['blocked_by_user_id'] == 9
    assert row['blocked_at'] == 'now'


def test_unblock_clears_structured_reason():
    conn = _conn()
    item = _add_item(conn, 1, 'in_stock')
    set_stock_item_status(conn, item, 'blocked_rejected', 'reprovado', 9, 'HSE', 'now')
    blocked = conn.execute('SELECT * FROM epi_stock_items WHERE id = 1').fetchone()
    set_stock_item_status(conn, blocked, 'in_stock', 'reinspecionado', 9, 'HSE', 'later')
    row = conn.execute(
        'SELECT status, blocking_reason_code, blocking_justification, blocked_by_user_id, blocked_at '
        'FROM epi_stock_items WHERE id = 1'
    ).fetchone()
    assert row['status'] == 'in_stock'
    assert row['blocking_reason_code'] is None and row['blocking_justification'] is None
    assert row['blocked_by_user_id'] is None and row['blocked_at'] is None
