"""Auditoria F-02 — endpoint/serviço save-prices da requisição de compra.

Cobre o caminho feliz (salva preço/quantidade e move para 'quoted'), a
preservação da regra R1 (item aprovado não é alterado) e as guardas de
status (requisição já avançada não aceita novos preços).
"""

import sqlite3

import pytest

from modules.purchases.service import save_purchase_request_prices

ACTOR = {'id': 7, 'full_name': 'Comprador', 'role': 'buyer', 'company_id': 1}


def _conn():
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        CREATE TABLE purchase_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT, company_id INTEGER, entity_type TEXT, entity_id INTEGER,
            action TEXT, status_from TEXT DEFAULT '', status_to TEXT DEFAULT '', comment TEXT DEFAULT '',
            actor_user_id INTEGER, actor_name TEXT DEFAULT '', actor_role TEXT DEFAULT '',
            reason TEXT DEFAULT '', destination TEXT DEFAULT '', ip_address TEXT DEFAULT '',
            session_ref TEXT DEFAULT '', created_at TEXT
        );
        CREATE TABLE purchase_requests (
            id INTEGER PRIMARY KEY, company_id INTEGER, unit_id INTEGER,
            status TEXT DEFAULT 'sent_to_buyer', updated_at TEXT DEFAULT ''
        );
        CREATE TABLE purchase_request_items (
            id INTEGER PRIMARY KEY, purchase_request_id INTEGER, company_id INTEGER, unit_id INTEGER,
            epi_id INTEGER, epi_name TEXT DEFAULT '', quantity_requested INTEGER DEFAULT 1,
            unit_price REAL DEFAULT 0, total_price REAL DEFAULT 0, status TEXT DEFAULT 'included_in_request',
            updated_at TEXT DEFAULT ''
        );
        """
    )
    conn.execute("INSERT INTO purchase_requests (id, company_id, unit_id, status) VALUES (100, 1, 1, 'sent_to_buyer')")
    conn.executescript(
        """
        INSERT INTO purchase_request_items (id, purchase_request_id, company_id, unit_id, epi_id, epi_name, quantity_requested, status)
        VALUES (1000, 100, 1, 1, 5, 'Luva', 10, 'included_in_request'),
               (1001, 100, 1, 1, 6, 'Capacete', 4, 'approved');
        """
    )
    return conn


def _pr(conn):
    row = conn.execute('SELECT * FROM purchase_requests WHERE id = 100').fetchone()
    return dict(row)


def test_save_prices_updates_item_and_moves_to_quoted():
    conn = _conn()
    affected, status = save_purchase_request_prices(
        conn, ACTOR, _pr(conn), [{'item_id': 1000, 'unit_price': 12.5, 'quantity': 8}], ip_address='1.2.3.4'
    )
    assert affected == [1000]
    assert status == 'quoted'
    item = conn.execute('SELECT unit_price, total_price, quantity_requested FROM purchase_request_items WHERE id = 1000').fetchone()
    assert float(item['unit_price']) == 12.5
    assert float(item['total_price']) == 100.0  # 12.5 * 8
    assert int(item['quantity_requested']) == 8
    assert conn.execute('SELECT status FROM purchase_requests WHERE id = 100').fetchone()['status'] == 'quoted'
    ev = conn.execute("SELECT action, status_to FROM purchase_events WHERE action = 'prices_saved'").fetchone()
    assert ev['status_to'] == 'quoted'


def test_save_prices_preserves_approved_item():
    conn = _conn()
    # tenta atualizar um item aprovado junto com um válido
    affected, _ = save_purchase_request_prices(
        conn, ACTOR, _pr(conn),
        [{'item_id': 1000, 'unit_price': 9.0}, {'item_id': 1001, 'unit_price': 99.0}],
        ip_address=''
    )
    assert affected == [1000]  # item aprovado (1001) ignorado — R1
    approved = conn.execute('SELECT unit_price FROM purchase_request_items WHERE id = 1001').fetchone()
    assert float(approved['unit_price']) == 0  # inalterado


def test_save_prices_defaults_quantity_from_item():
    conn = _conn()
    save_purchase_request_prices(conn, ACTOR, _pr(conn), [{'item_id': 1000, 'unit_price': 5.0}], ip_address='')
    item = conn.execute('SELECT total_price, quantity_requested FROM purchase_request_items WHERE id = 1000').fetchone()
    assert int(item['quantity_requested']) == 10  # mantém a quantidade original
    assert float(item['total_price']) == 50.0


def test_save_prices_rejects_when_request_already_advanced():
    conn = _conn()
    conn.execute("UPDATE purchase_requests SET status = 'approved' WHERE id = 100")
    with pytest.raises(ValueError, match='avançou'):
        save_purchase_request_prices(conn, ACTOR, _pr(conn), [{'item_id': 1000, 'unit_price': 5.0}], ip_address='')


def test_save_prices_requires_eligible_item():
    conn = _conn()
    with pytest.raises(ValueError, match='Nenhum item'):
        save_purchase_request_prices(conn, ACTOR, _pr(conn), [{'item_id': 1001, 'unit_price': 5.0}], ip_address='')


def test_save_prices_rejects_invalid_values():
    conn = _conn()
    with pytest.raises(ValueError, match='Preço'):
        save_purchase_request_prices(conn, ACTOR, _pr(conn), [{'item_id': 1000, 'unit_price': -1}], ip_address='')
    with pytest.raises(ValueError, match='Quantidade'):
        save_purchase_request_prices(conn, ACTOR, _pr(conn), [{'item_id': 1000, 'unit_price': 5.0, 'quantity': 0}], ip_address='')
