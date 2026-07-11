"""Fase 4b (HSE) — Estoque Bloqueado.

Itens com status bloqueado (Vencido / Aguardando descarte / Devolução ao
fornecedor / Em análise / Reprovado) saem do estoque disponível e passam a
constar na aba de Estoque Bloqueado. set_stock_item_status muda o status e
registra auditoria (stock_movement). Desbloquear volta o item a in_stock.
"""

import sqlite3

import pytest

from modules.stock.service import (
    BLOCKED_STOCK_STATUSES,
    fetch_available_stock_items,
    fetch_blocked_stock_items,
    set_stock_item_status,
)


def _conn():
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        CREATE TABLE epis (id INTEGER PRIMARY KEY, name TEXT, epi_validity_date TEXT DEFAULT '', unit_measure TEXT DEFAULT 'un');
        CREATE TABLE units (id INTEGER PRIMARY KEY, name TEXT);
        CREATE TABLE epi_stock_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT, company_id INTEGER, unit_id INTEGER, epi_id INTEGER,
            glove_size TEXT DEFAULT 'N/A', size TEXT DEFAULT 'N/A', uniform_size TEXT DEFAULT 'N/A',
            qr_code_value TEXT DEFAULT '', status TEXT DEFAULT 'in_stock', lot_code TEXT DEFAULT '',
            manufacture_date TEXT DEFAULT '', updated_at TEXT DEFAULT ''
        );
        CREATE TABLE stock_movements (
            id INTEGER PRIMARY KEY AUTOINCREMENT, company_id INTEGER, unit_id INTEGER, epi_id INTEGER,
            movement_type TEXT, quantity INTEGER, previous_stock INTEGER, new_stock INTEGER,
            source_type TEXT, source_id INTEGER, notes TEXT, actor_user_id INTEGER, actor_name TEXT,
            created_at TEXT, glove_size TEXT, size TEXT, uniform_size TEXT
        );
        INSERT INTO epis (id, name) VALUES (7, 'Capacete');
        INSERT INTO units (id, name) VALUES (2, 'Base');
        INSERT INTO epi_stock_items (id, company_id, unit_id, epi_id, qr_code_value, status)
            VALUES (10, 1, 2, 7, 'QR-10', 'in_stock');
        """
    )
    conn.commit()
    return conn


def _item(conn, item_id=10):
    return conn.execute('SELECT * FROM epi_stock_items WHERE id = ?', (item_id,)).fetchone()


def test_block_item_removes_from_available_and_appears_in_blocked():
    conn = _conn()
    assert [r['id'] for r in fetch_available_stock_items(conn, 1, 2, 7)] == [10]
    set_stock_item_status(conn, _item(conn), 'blocked_discard', 'danificado', 3, 'Admin', 'now')
    # não é mais ofertado na entrega
    assert fetch_available_stock_items(conn, 1, 2, 7) == []
    # aparece no estoque bloqueado
    blocked = fetch_blocked_stock_items(conn, 1)
    assert [r['id'] for r in blocked] == [10]
    assert blocked[0]['status'] == 'blocked_discard'


def test_block_records_audit_movement():
    conn = _conn()
    set_stock_item_status(conn, _item(conn), 'blocked_return', 'devolver', 3, 'Admin', 'now')
    mv = conn.execute("SELECT * FROM stock_movements WHERE source_type = 'stock_block'").fetchall()
    assert len(mv) == 1 and mv[0]['movement_type'] == 'block'
    assert 'blocked_return' in mv[0]['notes'] and 'devolver' in mv[0]['notes']


def test_unblock_returns_to_stock():
    conn = _conn()
    set_stock_item_status(conn, _item(conn), 'blocked_analysis', '', 3, 'Admin', 'now')
    set_stock_item_status(conn, _item(conn), 'in_stock', 'liberado', 3, 'Admin', 'now')
    assert [r['id'] for r in fetch_available_stock_items(conn, 1, 2, 7)] == [10]
    assert fetch_blocked_stock_items(conn, 1) == []


def test_invalid_status_raises():
    conn = _conn()
    with pytest.raises(ValueError, match='inválido'):
        set_stock_item_status(conn, _item(conn), 'whatever', '', 3, 'Admin', 'now')


def test_status_labels_cover_requested_dispositions():
    labels = set(BLOCKED_STOCK_STATUSES.values())
    assert {'Vencido', 'Aguardando descarte', 'Aguardando devolução ao fornecedor', 'Em análise', 'Reprovado'} <= labels
