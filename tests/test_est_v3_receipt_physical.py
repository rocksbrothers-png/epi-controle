"""EST-V3 / G02-G15 — recebimento grava validade física na peça (unidade).

record_received_item_physical descola a validade do catálogo (G02) gravando-a
na peça e, se o lote chega vencido, bloqueia a peça no recebimento (G15).
"""

import sqlite3
from datetime import date, timedelta

from core.schema import ensure_stock_lifecycle_model
from modules.stock.service import record_received_item_physical

PAST = (date.today() - timedelta(days=10)).isoformat()
FUTURE = (date.today() + timedelta(days=365)).isoformat()


def _conn():
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.executescript(
        "CREATE TABLE epi_stock_items (id INTEGER PRIMARY KEY AUTOINCREMENT, company_id INTEGER, "
        "unit_id INTEGER, epi_id INTEGER, status TEXT DEFAULT 'in_stock', qr_code_value TEXT DEFAULT '');"
    )
    ensure_stock_lifecycle_model(conn)
    conn.commit()
    return conn


def _item(conn):
    iid = conn.execute("INSERT INTO epi_stock_items (company_id, unit_id, epi_id, status) VALUES (1,2,7,'in_stock')").lastrowid
    conn.commit()
    return iid


def test_sets_physical_validity_and_source_future():
    conn = _conn()
    iid = _item(conn)
    record_received_item_physical(conn, iid, FUTURE, 3, 'now', evidence='Conferência X')
    r = conn.execute('SELECT physical_expiry_date, expiry_source, expiry_evidence, status FROM epi_stock_items WHERE id=?', (iid,)).fetchone()
    assert r['physical_expiry_date'] == FUTURE
    assert r['expiry_source'] == 'manufacturer_document'
    assert r['expiry_evidence'] == 'Conferência X'
    assert r['status'] == 'in_stock'


def test_expired_lot_enters_blocked_with_structured_reason():
    conn = _conn()
    iid = _item(conn)
    record_received_item_physical(conn, iid, PAST, 3, 'now')
    r = conn.execute('SELECT physical_expiry_date, status, blocking_reason_code, blocked_by_user_id FROM epi_stock_items WHERE id=?', (iid,)).fetchone()
    assert r['physical_expiry_date'] == PAST
    assert r['status'] == 'blocked_expired'
    assert r['blocking_reason_code'] == 'expired'
    assert r['blocked_by_user_id'] == 3


def test_unknown_validity_is_noop():
    conn = _conn()
    iid = _item(conn)
    record_received_item_physical(conn, iid, '', 3, 'now')
    r = conn.execute('SELECT physical_expiry_date, status FROM epi_stock_items WHERE id=?', (iid,)).fetchone()
    assert (r['physical_expiry_date'] in (None, '')) and r['status'] == 'in_stock'


def test_degrades_without_physical_column():
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.execute("CREATE TABLE epi_stock_items (id INTEGER PRIMARY KEY, status TEXT DEFAULT 'in_stock')")
    conn.execute("INSERT INTO epi_stock_items (id, status) VALUES (5, 'in_stock')")
    conn.commit()
    record_received_item_physical(conn, 5, FUTURE, 3, 'now')  # sem a coluna → no-op, sem erro
    assert conn.execute('SELECT status FROM epi_stock_items WHERE id=5').fetchone()['status'] == 'in_stock'
