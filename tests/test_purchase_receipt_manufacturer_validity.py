"""Conferência de recebimento (Compras): captura da validade do fabricante.

NT 146/2015 — ao dar entrada dos EPIs no estoque, o administrador local informa a
validade do fabricante antes de enviar ao estoque, para que nenhum item fique
"aberto" sem data comprovada. Cada linha/lote precisa de sua própria
comprovação; a identidade do EPI não comprova um lote físico compartilhado.
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
            name TEXT, ca TEXT, unit_measure TEXT, minimum_stock INTEGER DEFAULT 0,
            epi_validity_date TEXT DEFAULT ''
        );
        CREATE TABLE epi_requests (id INTEGER PRIMARY KEY, status TEXT, last_updated_at TEXT);
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
    conn.execute("INSERT INTO epis VALUES (100, 1, 1, 'Capacete', 'CA-999', 'unidade', 5, '')")
    conn.commit()
    return conn


def _actor():
    return {'id': 1, 'full_name': 'Admin Teste', 'role': 'admin', 'company_id': 1}


def test_manufacturer_validity_saved_on_piece_not_catalog():
    # EST-V3.5 (G02): a conferência grava a validade do fabricante NA PEÇA
    # (física, por lote), NÃO no catálogo (epis.epi_validity_date, que vira só
    # default de cadastro). As etiquetas seguem carregando a data para exibição.
    from core.schema import ensure_stock_lifecycle_model
    from modules.purchases.service import update_purchase_request_status
    conn = _conn()
    ensure_stock_lifecycle_model(conn)
    conn.execute(
        "INSERT INTO purchase_requests (id, company_id, unit_id, status, title, created_at, updated_at) "
        "VALUES (1, 1, 1, 'received', 'Req', '2024-01-01', '2024-01-01')"
    )
    conn.execute(
        "INSERT INTO purchase_request_items (id, purchase_request_id, company_id, unit_id, epi_id, epi_name, "
        "quantity_requested, status, created_at, updated_at) "
        "VALUES (1, 1, 1, 1, 100, 'Capacete', 2, 'received', '2024-01-01', '2024-01-01')"
    )
    conn.commit()
    pr = {'id': 1, 'company_id': 1, 'status': 'received'}
    result = update_purchase_request_status(
        conn, _actor(), pr, 'checked', '', '',
        [{'id': 1, 'received': True, 'manufacturer_validity_date': '2027-09-30',
          'evidence': 'Etiqueta do fabricante'}], '1.2.3.4'
    )
    assert result['stock_entries'] == 2
    # catálogo NÃO é mais escrito no recebimento
    epi = conn.execute('SELECT epi_validity_date FROM epis WHERE id = 100').fetchone()
    assert epi['epi_validity_date'] == ''
    # a validade vive na PEÇA (física do lote)
    rows = conn.execute('SELECT physical_expiry_date FROM epi_stock_items WHERE epi_id = 100').fetchall()
    assert len(rows) == 2 and all(r['physical_expiry_date'] == '2027-09-30' for r in rows)
    # etiquetas carregam a validade para exibição/impressão
    assert all(l['manufacturer_validity_date'] == '2027-09-30' for l in result['qr_labels'])


def test_same_epi_does_not_share_physical_expiry_between_lines():
    """Somente a linha com data e evidência comprovadas ganha validade física."""
    from core.schema import ensure_stock_lifecycle_model
    from modules.purchases.service import update_purchase_request_status
    conn = _conn()
    ensure_stock_lifecycle_model(conn)
    conn.execute(
        "INSERT INTO purchase_requests (id, company_id, unit_id, status, title, created_at, updated_at) "
        "VALUES (1, 1, 1, 'received', 'Req', '2024-01-01', '2024-01-01')"
    )
    # Dois itens do MESMO EPI (tamanhos diferentes); data só no primeiro.
    conn.execute(
        "INSERT INTO purchase_request_items (id, purchase_request_id, company_id, unit_id, epi_id, epi_name, "
        "quantity_requested, glove_size, status, created_at, updated_at) "
        "VALUES (1, 1, 1, 1, 100, 'Capacete', 1, 'M', 'received', '2024-01-01', '2024-01-01')"
    )
    conn.execute(
        "INSERT INTO purchase_request_items (id, purchase_request_id, company_id, unit_id, epi_id, epi_name, "
        "quantity_requested, glove_size, status, created_at, updated_at) "
        "VALUES (2, 1, 1, 1, 100, 'Capacete', 1, 'G', 'received', '2024-01-01', '2024-01-01')"
    )
    conn.commit()
    pr = {'id': 1, 'company_id': 1, 'status': 'received'}
    result = update_purchase_request_status(
        conn, _actor(), pr, 'checked', '', '',
        [
            {'id': 1, 'received': True, 'manufacturer_validity_date': '2028-01-15',
             'evidence': 'Etiqueta da primeira linha'},
            {'id': 2, 'received': True},
        ], ''
    )
    assert result['stock_entries'] == 2
    # Catálogo intacto; a segunda linha permanece desconhecida.
    epi = conn.execute('SELECT epi_validity_date FROM epis WHERE id = 100').fetchone()
    assert epi['epi_validity_date'] == ''
    rows = conn.execute('SELECT physical_expiry_date FROM epi_stock_items WHERE epi_id = 100 ORDER BY id').fetchall()
    assert [r['physical_expiry_date'] for r in rows] == ['2028-01-15', None]
    assert [label['manufacturer_validity_date'] for label in result['qr_labels']] == ['2028-01-15', '']


# ── caminho da PO (recebimento) ───────────────────────────────────────────────

def _po_conn():
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        CREATE TABLE epis (id INTEGER PRIMARY KEY, name TEXT, epi_validity_date TEXT DEFAULT '');
        CREATE TABLE purchase_orders (
            id INTEGER PRIMARY KEY, company_id INTEGER, unit_id INTEGER, status TEXT,
            po_number TEXT DEFAULT '', received_by_user_id INTEGER, received_by_name TEXT DEFAULT '',
            received_at TEXT DEFAULT '', checked_at TEXT DEFAULT '', closed_at TEXT DEFAULT '',
            updated_at TEXT
        );
        CREATE TABLE purchase_order_items (
            id INTEGER PRIMARY KEY, purchase_order_id INTEGER, company_id INTEGER, unit_id INTEGER,
            epi_id INTEGER, quantity INTEGER DEFAULT 1, quantity_received INTEGER DEFAULT 0,
            manufacturer_validity_date TEXT DEFAULT '',
            status TEXT DEFAULT 'open', updated_at TEXT
        );
        CREATE TABLE purchase_events (
            id INTEGER PRIMARY KEY, company_id INTEGER, entity_type TEXT, entity_id INTEGER,
            action TEXT, status_from TEXT, status_to TEXT, comment TEXT,
            actor_user_id INTEGER, actor_name TEXT, actor_role TEXT DEFAULT '',
            reason TEXT DEFAULT '', destination TEXT DEFAULT '', ip_address TEXT DEFAULT '', created_at TEXT
        );
    """)
    conn.execute("INSERT INTO epis VALUES (100, 'Capacete', '')")
    conn.execute("INSERT INTO purchase_orders (id, company_id, unit_id, status) VALUES (1, 1, 10, 'approved')")
    conn.execute("INSERT INTO purchase_order_items (id, purchase_order_id, company_id, unit_id, epi_id, quantity, status) VALUES (1, 1, 1, 10, 100, 3, 'open')")
    conn.execute("INSERT INTO purchase_order_items (id, purchase_order_id, company_id, unit_id, epi_id, quantity, status) VALUES (2, 1, 1, 10, 100, 2, 'open')")
    conn.commit()
    return conn


def test_po_receive_keeps_validity_on_its_own_line():
    from modules.purchases.service import receive_purchase_order
    conn = _po_conn()
    po = {'id': 1, 'company_id': 1, 'status': 'approved'}
    # O mesmo EPI pode ter outro lote: item 2 permanece sem validade comprovada.
    result = receive_purchase_order(
        conn, _actor(), po, 'received',
        [
            {'id': 1, 'quantity_received': 3, 'manufacturer_validity_date': '2029-04-30'},
            {'id': 2, 'quantity_received': 2},
        ], '', ''
    )
    assert result['status'] == 'received'
    # EST-V3.5 (G02): validade do lote guardada NO ITEM DA PO (não no catálogo);
    # o item 2 herda por lote. A conferência ('checked') materializa na peça.
    epi = conn.execute('SELECT epi_validity_date FROM epis WHERE id = 100').fetchone()
    assert epi['epi_validity_date'] == ''
    items = conn.execute('SELECT manufacturer_validity_date FROM purchase_order_items ORDER BY id').fetchall()
    assert [i['manufacturer_validity_date'] for i in items] == ['2029-04-30', '']


# ── EST-V3 (G02/G15): validade física POR PEÇA no recebimento ─────────────────

def test_est_v3_received_items_carry_physical_expiry():
    """Com o modelo físico provisionado, a conferência grava a validade física
    na peça (não só no catálogo): a validade passa a viver no lote/peça (G02)."""
    from core.schema import ensure_stock_lifecycle_model
    from modules.purchases.service import update_purchase_request_status
    conn = _conn()
    ensure_stock_lifecycle_model(conn)
    conn.execute(
        "INSERT INTO purchase_requests (id, company_id, unit_id, status, title, created_at, updated_at) "
        "VALUES (1, 1, 1, 'received', 'Req', '2024-01-01', '2024-01-01')"
    )
    conn.execute(
        "INSERT INTO purchase_request_items (id, purchase_request_id, company_id, unit_id, epi_id, epi_name, "
        "quantity_requested, status, created_at, updated_at) "
        "VALUES (1, 1, 1, 1, 100, 'Capacete', 2, 'received', '2024-01-01', '2024-01-01')"
    )
    conn.commit()
    pr = {'id': 1, 'company_id': 1, 'status': 'received'}
    update_purchase_request_status(
        conn, _actor(), pr, 'checked', '', '',
        [{'id': 1, 'received': True, 'manufacturer_validity_date': '2027-09-30',
          'evidence': 'Etiqueta do fabricante'}], ''
    )
    rows = conn.execute(
        "SELECT physical_expiry_date, expiry_source, status FROM epi_stock_items WHERE epi_id = 100"
    ).fetchall()
    assert len(rows) == 2
    assert all(r['physical_expiry_date'] == '2027-09-30' for r in rows)
    assert all(r['expiry_source'] == 'manufacturer_document' for r in rows)
    assert all(r['status'] == 'in_stock' for r in rows)


def test_est_v3_expired_lot_at_receipt_enters_blocked_not_available():
    """G15: um lote que chega JÁ VENCIDO não entra como disponível — a peça
    recebida vai para blocked_expired (física, porém fora do disponível)."""
    from datetime import date, timedelta
    from core.schema import ensure_stock_lifecycle_model
    from modules.purchases.service import update_purchase_request_status
    from modules.stock.service import blocked_physical_quantity
    past = (date.today() - timedelta(days=5)).isoformat()
    conn = _conn()
    ensure_stock_lifecycle_model(conn)
    conn.execute(
        "INSERT INTO purchase_requests (id, company_id, unit_id, status, title, created_at, updated_at) "
        "VALUES (1, 1, 1, 'received', 'Req', '2024-01-01', '2024-01-01')"
    )
    conn.execute(
        "INSERT INTO purchase_request_items (id, purchase_request_id, company_id, unit_id, epi_id, epi_name, "
        "quantity_requested, status, created_at, updated_at) "
        "VALUES (1, 1, 1, 1, 100, 'Capacete', 1, 'received', '2024-01-01', '2024-01-01')"
    )
    conn.commit()
    pr = {'id': 1, 'company_id': 1, 'status': 'received'}
    update_purchase_request_status(
        conn, _actor(), pr, 'checked', '', '',
        [{'id': 1, 'received': True, 'manufacturer_validity_date': past,
          'evidence': 'Etiqueta vencida do fabricante'}], ''
    )
    r = conn.execute(
        "SELECT status, physical_expiry_date, blocking_reason_code FROM epi_stock_items WHERE epi_id = 100"
    ).fetchone()
    assert r['status'] == 'blocked_expired'
    assert r['physical_expiry_date'] == past
    assert r['blocking_reason_code'] == 'expired'
    # fisicamente presente, porém fora do disponível
    assert blocked_physical_quantity(conn, 1, 1, 100) == 1
