"""#7 — Geração e listagem de etiquetas QR na conferência da PO.

Ao confirmar o recebimento (received -> checked), os itens recebidos entram em
estoque e cada unidade gera um epi_stock_item com QR. A tela de conferência
precisa receber essas etiquetas para imprimir/reimprimir, e poder recuperá-las
depois via fetch_purchase_request_stock_labels.
"""

import sqlite3


def _conn():
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        CREATE TABLE companies (id INTEGER PRIMARY KEY, name TEXT, active INTEGER DEFAULT 1);
        CREATE TABLE units (id INTEGER PRIMARY KEY, company_id INTEGER, name TEXT);
        CREATE TABLE epis (
            id INTEGER PRIMARY KEY, company_id INTEGER, unit_id INTEGER,
            name TEXT, ca TEXT, unit_measure TEXT, minimum_stock INTEGER DEFAULT 0
        );
        CREATE TABLE epi_requests (
            id INTEGER PRIMARY KEY, status TEXT, last_updated_at TEXT
        );
        CREATE TABLE purchase_requests (
            id INTEGER PRIMARY KEY, company_id INTEGER, unit_id INTEGER,
            status TEXT DEFAULT 'open', title TEXT, notes TEXT,
            created_by_user_id INTEGER, created_by_name TEXT,
            sent_to_buyer_at TEXT, closed_at TEXT, postponed_until TEXT,
            created_at TEXT, updated_at TEXT
        );
        CREATE TABLE purchase_request_items (
            id INTEGER PRIMARY KEY, purchase_request_id INTEGER, company_id INTEGER, unit_id INTEGER,
            epi_id INTEGER, epi_name TEXT, quantity_requested INTEGER DEFAULT 1,
            glove_size TEXT DEFAULT 'N/A', size TEXT DEFAULT 'N/A', uniform_size TEXT DEFAULT 'N/A',
            epi_request_id INTEGER, status TEXT DEFAULT 'included_in_request',
            created_at TEXT, updated_at TEXT
        );
        CREATE TABLE purchase_order_items (
            id INTEGER PRIMARY KEY, purchase_order_id INTEGER, purchase_request_item_id INTEGER,
            quantity_received INTEGER DEFAULT 0
        );
        CREATE TABLE purchase_events (
            id INTEGER PRIMARY KEY, company_id INTEGER, entity_type TEXT, entity_id INTEGER,
            action TEXT, status_from TEXT, status_to TEXT, comment TEXT,
            actor_user_id INTEGER, actor_name TEXT, actor_role TEXT DEFAULT '',
            reason TEXT DEFAULT '', destination TEXT DEFAULT '', ip_address TEXT DEFAULT '',
            created_at TEXT
        );
        CREATE TABLE unit_epi_stock (
            id INTEGER PRIMARY KEY AUTOINCREMENT, company_id INTEGER, unit_id INTEGER,
            epi_id INTEGER, quantity INTEGER DEFAULT 0, updated_at TEXT
        );
        CREATE TABLE epi_qr_sequences (company_id INTEGER PRIMARY KEY, last_value INTEGER);
        CREATE TABLE stock_movements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER, unit_id INTEGER, epi_id INTEGER,
            movement_type TEXT, quantity INTEGER, previous_stock INTEGER, new_stock INTEGER,
            source_type TEXT DEFAULT '', source_id INTEGER, notes TEXT DEFAULT '',
            actor_user_id INTEGER, actor_name TEXT, created_at TEXT,
            glove_size TEXT DEFAULT 'N/A', size TEXT DEFAULT 'N/A', uniform_size TEXT DEFAULT 'N/A'
        );
        CREATE TABLE epi_stock_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER, unit_id INTEGER, epi_id INTEGER,
            glove_size TEXT, size TEXT, uniform_size TEXT, qr_sequence INTEGER,
            qr_code_value TEXT, status TEXT, stock_movement_id INTEGER,
            lot_code TEXT DEFAULT '', manufacture_date TEXT DEFAULT '',
            label_measure TEXT DEFAULT 'unidade', label_printer_name TEXT DEFAULT '',
            label_print_format TEXT DEFAULT '', reprint_count INTEGER DEFAULT 0,
            generated_by_user_id INTEGER, created_at TEXT, updated_at TEXT
        );
        CREATE TABLE purchase_pendencies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER, unit_id INTEGER, purchase_request_id INTEGER,
            purchase_request_item_id INTEGER, epi_id INTEGER, epi_name TEXT,
            glove_size TEXT, size TEXT, uniform_size TEXT,
            quantity_ordered INTEGER, quantity_received INTEGER, quantity_short INTEGER,
            reason TEXT, status TEXT, created_by_user_id INTEGER, created_by_name TEXT,
            resolved_by_user_id INTEGER, resolved_by_name TEXT, resolved_at TEXT,
            created_at TEXT, updated_at TEXT
        );
    """)
    conn.execute("INSERT INTO companies VALUES (1, 'Empresa Teste', 1)")
    conn.execute("INSERT INTO units VALUES (1, 1, 'Unidade Alpha')")
    conn.execute("INSERT INTO epis VALUES (100, 1, 1, 'Capacete', 'CA-999', 'unidade', 5)")
    conn.commit()
    return conn


def _actor():
    return {'id': 1, 'full_name': 'Admin Teste', 'role': 'admin', 'company_id': 1}


def _seed_received_pr(conn, quantity=3):
    conn.execute(
        "INSERT INTO purchase_requests (id, company_id, unit_id, status, title, created_at, updated_at) "
        "VALUES (1, 1, 1, 'received', 'Req', '2024-01-01', '2024-01-01')"
    )
    conn.execute(
        "INSERT INTO purchase_request_items (id, purchase_request_id, company_id, unit_id, epi_id, epi_name, "
        "quantity_requested, glove_size, size, uniform_size, status, created_at, updated_at) "
        "VALUES (1, 1, 1, 1, 100, 'Capacete', ?, 'M', 'N/A', 'N/A', 'received', '2024-01-01', '2024-01-01')",
        (quantity,)
    )
    conn.commit()


def test_conference_returns_qr_labels_and_feeds_stock():
    from modules.purchases.service import update_purchase_request_status
    conn = _conn()
    _seed_received_pr(conn, quantity=3)
    pr = {'id': 1, 'company_id': 1, 'status': 'received'}
    result = update_purchase_request_status(
        conn, _actor(), pr, 'checked', '', '', [{'id': 1, 'received': True}], '1.2.3.4'
    )
    assert result['stock_entries'] == 3
    assert len(result['qr_labels']) == 3
    label = result['qr_labels'][0]
    assert label['epi_name'] == 'Capacete'
    assert label['unit_name'] == 'Unidade Alpha'
    assert label['glove_size'] == 'M'
    assert label['stock_item_id'] > 0
    assert label['qr_code_value'].startswith('EPI-ITEM-')
    # estoque alimentado
    stock = conn.execute('SELECT quantity FROM unit_epi_stock WHERE epi_id = 100').fetchone()
    assert int(stock['quantity']) == 3
    # 3 epi_stock_items criados
    count = conn.execute('SELECT COUNT(*) AS c FROM epi_stock_items').fetchone()
    assert int(count['c']) == 3


def test_no_stock_path_returns_empty_qr_labels():
    from modules.purchases.service import update_purchase_request_status
    conn = _conn()
    conn.execute(
        "INSERT INTO purchase_requests (id, company_id, unit_id, status, title, created_at, updated_at) "
        "VALUES (1, 1, 1, 'open', 'Req', '2024-01-01', '2024-01-01')"
    )
    conn.commit()
    pr = {'id': 1, 'company_id': 1, 'status': 'open'}
    result = update_purchase_request_status(conn, _actor(), pr, 'sent_to_buyer', '', '', [], '')
    assert result['stock_entries'] == 0
    assert result['qr_labels'] == []


def test_partial_receipt_opens_pendency_and_alerts_buyer():
    from modules.purchases.service import update_purchase_request_status, fetch_purchase_pendencies
    conn = _conn()
    # PR com dois itens; um recebido, outro não (recebimento parcial)
    conn.execute(
        "INSERT INTO purchase_requests (id, company_id, unit_id, status, title, created_at, updated_at) "
        "VALUES (1, 1, 1, 'received', 'Req', '2024-01-01', '2024-01-01')"
    )
    conn.execute(
        "INSERT INTO purchase_request_items (id, purchase_request_id, company_id, unit_id, epi_id, epi_name, "
        "quantity_requested, glove_size, size, uniform_size, status, created_at, updated_at) "
        "VALUES (1, 1, 1, 1, 100, 'Capacete', 5, 'M', 'N/A', 'N/A', 'received', '2024-01-01', '2024-01-01')"
    )
    conn.execute(
        "INSERT INTO purchase_request_items (id, purchase_request_id, company_id, unit_id, epi_id, epi_name, "
        "quantity_requested, glove_size, size, uniform_size, status, created_at, updated_at) "
        "VALUES (2, 1, 1, 1, 100, 'Capacete', 3, 'G', 'N/A', 'N/A', 'received', '2024-01-01', '2024-01-01')"
    )
    conn.commit()
    pr = {'id': 1, 'company_id': 1, 'status': 'received'}
    result = update_purchase_request_status(
        conn, _actor(), pr, 'checked', '',
        '', [{'id': 1, 'received': True}, {'id': 2, 'received': False}], '1.2.3.4'
    )
    assert len(result['pendencies']) == 1
    assert result['pendencies'][0]['quantity_short'] == 3
    # pendência persistida
    pend = fetch_purchase_pendencies(conn, company_id=1)
    assert len(pend) == 1
    assert pend[0]['status'] == 'open'
    assert pend[0]['quantity_short'] == 3
    # alerta ao comprador (purchase_event destination='buyer')
    ev = conn.execute(
        "SELECT * FROM purchase_events WHERE action = 'partial_receipt_pendency'"
    ).fetchall()
    assert len(ev) == 1
    assert ev[0]['destination'] == 'buyer'


def test_full_receipt_opens_no_pendency():
    from modules.purchases.service import update_purchase_request_status, fetch_purchase_pendencies
    conn = _conn()
    _seed_received_pr(conn, quantity=3)
    pr = {'id': 1, 'company_id': 1, 'status': 'received'}
    result = update_purchase_request_status(
        conn, _actor(), pr, 'checked', '', '', [{'id': 1, 'received': True}], ''
    )
    assert result['pendencies'] == []
    assert fetch_purchase_pendencies(conn, company_id=1) == []


def test_resolve_purchase_pendency_marks_resolved():
    from modules.purchases.service import (
        update_purchase_request_status, fetch_purchase_pendencies, resolve_purchase_pendency,
    )
    conn = _conn()
    conn.execute(
        "INSERT INTO purchase_requests (id, company_id, unit_id, status, title, created_at, updated_at) "
        "VALUES (1, 1, 1, 'received', 'Req', '2024-01-01', '2024-01-01')"
    )
    conn.execute(
        "INSERT INTO purchase_request_items (id, purchase_request_id, company_id, unit_id, epi_id, epi_name, "
        "quantity_requested, glove_size, size, uniform_size, status, created_at, updated_at) "
        "VALUES (1, 1, 1, 1, 100, 'Capacete', 4, 'M', 'N/A', 'N/A', 'received', '2024-01-01', '2024-01-01')"
    )
    conn.commit()
    pr = {'id': 1, 'company_id': 1, 'status': 'received'}
    update_purchase_request_status(conn, _actor(), pr, 'checked', '', '', [{'id': 1, 'received': False}], '')
    pend = fetch_purchase_pendencies(conn, company_id=1)
    assert len(pend) == 1
    resolve_purchase_pendency(conn, _actor(), pend[0]['id'])
    assert fetch_purchase_pendencies(conn, company_id=1, status='open') == []
    resolved = fetch_purchase_pendencies(conn, company_id=1, status='resolved')
    assert len(resolved) == 1
    assert resolved[0]['resolved_by_name'] == 'Admin Teste'


def test_fetch_purchase_request_stock_labels_after_conference():
    from modules.purchases.service import (
        update_purchase_request_status,
        fetch_purchase_request_stock_labels,
    )
    conn = _conn()
    _seed_received_pr(conn, quantity=2)
    # vincula movimento ao item via source_id já é feito pelo auto-add
    pr = {'id': 1, 'company_id': 1, 'status': 'received'}
    update_purchase_request_status(conn, _actor(), pr, 'checked', '', '', [{'id': 1, 'received': True}], '')
    labels = fetch_purchase_request_stock_labels(conn, 1)
    assert len(labels) == 2
    assert all(l['epi_name'] == 'Capacete' for l in labels)
    assert all(l['unit_name'] == 'Unidade Alpha' for l in labels)
    assert all(l['reprint_count'] == 0 for l in labels)
    assert all(l['stock_item_id'] > 0 for l in labels)
