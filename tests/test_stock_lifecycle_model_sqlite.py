"""EST-V3 substrate — modelo físico da EST-V2 provisionado em SQLite.

Em produção (PostgreSQL) o modelo vem das migrations 030/031; o runner de
migrations é pulado no SQLite (core/schema.run_pending_migrations). Para que o
código operacional da EST-V3+ seja exercitável na suíte unitária (SQLite),
``ensure_stock_lifecycle_model`` provisiona a mesma ESTRUTURA (tabelas/colunas)
em SQLite — NO-OP em PostgreSQL. Estes testes cobrem só a estrutura/idempotência.
"""

import sqlite3

from core.schema import ensure_stock_lifecycle_model

NEW_TABLES = {'epi_stock_lots', 'epi_stock_events', 'epi_stock_decisions', 'company_stock_validity_config'}
NEW_ITEM_COLS = {
    'lot_id', 'physical_manufacture_date', 'physical_expiry_date', 'expiry_source',
    'expiry_evidence', 'unit_cost', 'row_version', 'blocking_reason_code',
    'blocking_justification', 'blocked_by_user_id', 'blocked_at',
}


def _conn():
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        CREATE TABLE epi_stock_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT, company_id INTEGER, unit_id INTEGER, epi_id INTEGER,
            qr_code_value TEXT DEFAULT '', status TEXT DEFAULT 'in_stock',
            lot_code TEXT DEFAULT '', manufacture_date TEXT DEFAULT '',
            created_at TEXT DEFAULT '', updated_at TEXT DEFAULT ''
        );
        """
    )
    conn.commit()
    return conn


def test_provisions_tables_and_columns():
    conn = _conn()
    ensure_stock_lifecycle_model(conn)
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert NEW_TABLES <= tables, NEW_TABLES - tables
    cols = {r[1] for r in conn.execute('PRAGMA table_info(epi_stock_items)')}
    assert NEW_ITEM_COLS <= cols, NEW_ITEM_COLS - cols


def test_is_idempotent():
    conn = _conn()
    ensure_stock_lifecycle_model(conn)
    ensure_stock_lifecycle_model(conn)  # segunda passada não pode falhar nem duplicar
    cols = [r[1] for r in conn.execute('PRAGMA table_info(epi_stock_items)')]
    assert cols.count('physical_expiry_date') == 1


def test_round_trip_lot_item_event():
    conn = _conn()
    ensure_stock_lifecycle_model(conn)
    lot_id = conn.execute(
        'INSERT INTO epi_stock_lots (company_id, epi_id, receipt_unit_id, receipt_key, received_quantity, '
        'received_by_user_id, physical_expiry_date, expiry_source, expiry_evidence, unit_cost) '
        "VALUES (1, 7, 2, 'rk-1', 1, 3, '2027-01-01', 'label', 'nota fiscal', 12.5)"
    ).lastrowid
    item_id = conn.execute(
        'INSERT INTO epi_stock_items (company_id, unit_id, epi_id, qr_code_value, status, lot_id, '
        'physical_expiry_date, expiry_source) '
        "VALUES (1, 2, 7, 'QR-1', 'in_stock', ?, '2027-01-01', 'label')",
        (lot_id,),
    ).lastrowid
    conn.execute(
        'INSERT INTO epi_stock_events (company_id, epi_id, stock_item_id, lot_id, quantity, event_type, '
        'destination_unit_id, reason_code, justification, actor_user_id) '
        "VALUES (1, 7, ?, ?, 1, 'receipt', 2, 'receipt', 'recebimento por lote', 3)",
        (item_id, lot_id),
    )
    conn.commit()
    row = conn.execute('SELECT physical_expiry_date, lot_id, unit_cost FROM epi_stock_items WHERE id=?', (item_id,)).fetchone()
    assert row['physical_expiry_date'] == '2027-01-01' and row['lot_id'] == lot_id
    assert conn.execute('SELECT count(*) FROM epi_stock_events WHERE stock_item_id=?', (item_id,)).fetchone()[0] == 1
    assert conn.execute('SELECT unit_cost FROM epi_stock_lots WHERE id=?', (lot_id,)).fetchone()[0] == 12.5


def test_receipt_key_unique_per_company():
    conn = _conn()
    ensure_stock_lifecycle_model(conn)
    conn.execute(
        'INSERT INTO epi_stock_lots (company_id, epi_id, receipt_unit_id, receipt_key, received_quantity, received_by_user_id) '
        "VALUES (1, 7, 2, 'dup', 1, 3)"
    )
    import pytest
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            'INSERT INTO epi_stock_lots (company_id, epi_id, receipt_unit_id, receipt_key, received_quantity, received_by_user_id) '
            "VALUES (1, 7, 2, 'dup', 1, 3)"
        )
    # outra empresa pode reusar o mesmo receipt_key
    conn.execute(
        'INSERT INTO epi_stock_lots (company_id, epi_id, receipt_unit_id, receipt_key, received_quantity, received_by_user_id) '
        "VALUES (2, 7, 2, 'dup', 1, 3)"
    )
