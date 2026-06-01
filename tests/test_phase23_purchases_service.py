"""Tests for Phase 23: SQL extraction from purchases/routes.py into service layer."""

import sqlite3


# ── fixtures ──────────────────────────────────────────────────────────────────

def _conn():
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        CREATE TABLE companies (id INTEGER PRIMARY KEY, name TEXT, active INTEGER DEFAULT 1);
        CREATE TABLE units (id INTEGER PRIMARY KEY, company_id INTEGER, name TEXT);
        CREATE TABLE employees (
            id INTEGER PRIMARY KEY, company_id INTEGER, unit_id INTEGER,
            name TEXT, employee_id_code TEXT, sector TEXT, role_name TEXT, active INTEGER DEFAULT 1
        );
        CREATE TABLE epis (
            id INTEGER PRIMARY KEY, company_id INTEGER, unit_id INTEGER,
            name TEXT, ca TEXT, unit_measure TEXT, manufacturer TEXT, supplier_company TEXT,
            minimum_stock INTEGER DEFAULT 0, active INTEGER DEFAULT 1, active_joinventure TEXT
        );
        CREATE TABLE epi_requests (
            id INTEGER PRIMARY KEY, company_id INTEGER, unit_id INTEGER,
            employee_id INTEGER, epi_id INTEGER, quantity INTEGER DEFAULT 1,
            glove_size TEXT DEFAULT 'N/A', size TEXT DEFAULT 'N/A', uniform_size TEXT DEFAULT 'N/A',
            status TEXT DEFAULT 'solicitado', requested_at TEXT, last_updated_at TEXT,
            approver_user_id INTEGER, approver_name TEXT, approved_at TEXT,
            rejection_reason TEXT, postponed_until TEXT
        );
        CREATE TABLE epi_request_history (
            id INTEGER PRIMARY KEY, request_id INTEGER, company_id INTEGER,
            status TEXT, notes TEXT, actor_user_id INTEGER, actor_name TEXT, created_at TEXT
        );
        CREATE TABLE epi_feedbacks (
            id INTEGER PRIMARY KEY, company_id INTEGER, status TEXT DEFAULT 'pendente',
            reviewer_user_id INTEGER, reviewer_name TEXT, reviewed_at TEXT, updated_at TEXT
        );
        CREATE TABLE epi_feedback_history (
            id INTEGER PRIMARY KEY, feedback_id INTEGER, company_id INTEGER,
            status TEXT, notes TEXT, actor_user_id INTEGER, actor_name TEXT, created_at TEXT
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
            epi_id INTEGER, epi_name TEXT, ca TEXT, unit_measure TEXT,
            manufacturer TEXT DEFAULT '', supplier TEXT DEFAULT '',
            glove_size TEXT DEFAULT 'N/A', size TEXT DEFAULT 'N/A', uniform_size TEXT DEFAULT 'N/A',
            quantity_requested INTEGER DEFAULT 1, origin TEXT DEFAULT 'stock_minimum',
            employee_id INTEGER, employee_name TEXT DEFAULT '', employee_sector TEXT DEFAULT '',
            employee_role TEXT DEFAULT '', epi_request_id INTEGER,
            status TEXT DEFAULT 'included_in_request', notes TEXT DEFAULT '',
            approval_decided_by_user_id INTEGER, approval_decided_by_name TEXT,
            approval_decided_at TEXT, quantity_approved INTEGER,
            rejection_reason TEXT DEFAULT '', rejection_comment TEXT DEFAULT '',
            created_at TEXT, updated_at TEXT
        );
        CREATE TABLE purchase_orders (
            id INTEGER PRIMARY KEY, company_id INTEGER, unit_id INTEGER,
            status TEXT DEFAULT 'open', po_number TEXT, supplier TEXT, supplier_cnpj TEXT,
            created_at TEXT, updated_at TEXT
        );
        CREATE TABLE purchase_order_items (
            id INTEGER PRIMARY KEY, purchase_order_id INTEGER, purchase_request_item_id INTEGER,
            quantity_received INTEGER DEFAULT 0
        );
        CREATE TABLE purchase_order_files (
            id INTEGER PRIMARY KEY, purchase_order_id INTEGER,
            file_name TEXT, file_type TEXT, uploaded_by_name TEXT, created_at TEXT
        );
        CREATE TABLE purchase_events (
            id INTEGER PRIMARY KEY, company_id INTEGER, entity_type TEXT, entity_id INTEGER,
            action TEXT, status_from TEXT, status_to TEXT, comment TEXT,
            actor_user_id INTEGER, actor_name TEXT, actor_role TEXT DEFAULT '',
            reason TEXT DEFAULT '', destination TEXT DEFAULT '', ip_address TEXT DEFAULT '',
            created_at TEXT
        );
        CREATE TABLE purchase_role_unit_links (
            id INTEGER PRIMARY KEY, company_id INTEGER, unit_id INTEGER,
            employee_id INTEGER, role_type TEXT
        );
        CREATE TABLE user_unit_links (
            id INTEGER PRIMARY KEY, company_id INTEGER, unit_id INTEGER, user_id INTEGER
        );
        CREATE TABLE authorized_suppliers (
            id INTEGER PRIMARY KEY, company_id INTEGER, name TEXT, cnpj TEXT DEFAULT '',
            category TEXT DEFAULT '', contact_email TEXT DEFAULT '', notes TEXT DEFAULT '',
            updated_at TEXT
        );
        CREATE TABLE app_meta (key TEXT PRIMARY KEY, value TEXT);
        CREATE TABLE unit_epi_stock (
            id INTEGER PRIMARY KEY, company_id INTEGER, unit_id INTEGER, epi_id INTEGER, quantity INTEGER DEFAULT 0
        );
        CREATE TABLE stock_movements (id INTEGER PRIMARY KEY);
        CREATE TABLE epi_stock_items (id INTEGER PRIMARY KEY);
        CREATE TABLE users (
            id INTEGER PRIMARY KEY, company_id INTEGER, username TEXT, role TEXT,
            full_name TEXT, active INTEGER DEFAULT 1, linked_employee_id INTEGER
        );
    """)
    conn.execute("INSERT INTO companies VALUES (1, 'Empresa Teste', 1)")
    conn.execute("INSERT INTO units VALUES (1, 1, 'Unidade Alpha')")
    conn.execute("INSERT INTO units VALUES (2, 1, 'Unidade Beta')")
    conn.execute("INSERT INTO employees VALUES (10, 1, 1, 'João Silva', 'EMP001', 'TI', 'Técnico', 1)")
    conn.execute("INSERT INTO epis VALUES (100, 1, 1, 'Capacete', 'CA-999', 'unidade', 'FabX', 'FornY', 5, 1, '')")
    conn.commit()
    return conn


def _actor(role='admin', company_id=1, unit_id=None, employee_id=None):
    return {
        'id': 1, 'full_name': 'Admin Teste', 'role': role,
        'company_id': company_id, 'unit_id': unit_id,
        'linked_employee_id': employee_id,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# fetch_epi_requests
# ═══════════════════════════════════════════════════════════════════════════════

def test_fetch_epi_requests_returns_empty_without_data():
    from modules.purchases.service import fetch_epi_requests
    conn = _conn()
    result = fetch_epi_requests(conn, 1, None, None)
    assert result == []


def test_fetch_epi_requests_filters_by_company():
    from modules.purchases.service import fetch_epi_requests
    conn = _conn()
    conn.execute("INSERT INTO epi_requests VALUES (1,1,1,10,100,1,'N/A','N/A','N/A','solicitado','2024-01-01',NULL,NULL,NULL,NULL,NULL,NULL)")
    conn.execute("INSERT INTO epi_requests VALUES (2,2,1,10,100,1,'N/A','N/A','N/A','solicitado','2024-01-01',NULL,NULL,NULL,NULL,NULL,NULL)")
    conn.execute("INSERT INTO companies VALUES (2,'Outra',1)")
    conn.commit()
    result = fetch_epi_requests(conn, 1, None, None)
    ids = [r['id'] for r in result]
    assert 1 in ids
    assert 2 not in ids


def test_fetch_epi_requests_filters_by_scope_unit():
    from modules.purchases.service import fetch_epi_requests
    conn = _conn()
    conn.execute("INSERT INTO epi_requests VALUES (1,1,1,10,100,1,'N/A','N/A','N/A','solicitado','2024-01-01',NULL,NULL,NULL,NULL,NULL,NULL)")
    conn.execute("INSERT INTO epi_requests VALUES (2,1,2,10,100,1,'N/A','N/A','N/A','solicitado','2024-01-01',NULL,NULL,NULL,NULL,NULL,NULL)")
    conn.commit()
    result = fetch_epi_requests(conn, 1, 1, None)
    ids = [r['id'] for r in result]
    assert 1 in ids
    assert 2 not in ids


def test_fetch_epi_requests_no_filter_returns_all():
    from modules.purchases.service import fetch_epi_requests
    conn = _conn()
    conn.execute("INSERT INTO epi_requests VALUES (1,1,1,10,100,1,'N/A','N/A','N/A','solicitado','2024-01-01',NULL,NULL,NULL,NULL,NULL,NULL)")
    conn.execute("INSERT INTO epi_requests VALUES (2,1,2,10,100,1,'N/A','N/A','N/A','solicitado','2024-01-01',NULL,NULL,NULL,NULL,NULL,NULL)")
    conn.commit()
    result = fetch_epi_requests(conn, None, None, None)
    assert len(result) == 2


# ═══════════════════════════════════════════════════════════════════════════════
# fetch_purchase_requests
# ═══════════════════════════════════════════════════════════════════════════════

def test_fetch_purchase_requests_returns_empty():
    from modules.purchases.service import fetch_purchase_requests
    conn = _conn()
    result = fetch_purchase_requests(conn, 1, None, None)
    assert result == []


def test_fetch_purchase_requests_status_filter():
    from modules.purchases.service import fetch_purchase_requests
    conn = _conn()
    conn.execute("INSERT INTO purchase_requests VALUES (1,1,1,'open','R1','',1,'Admin',NULL,NULL,NULL,'2024-01-01','2024-01-01')")
    conn.execute("INSERT INTO purchase_requests VALUES (2,1,1,'closed','R2','',1,'Admin',NULL,'2024-01-02',NULL,'2024-01-01','2024-01-02')")
    conn.commit()
    result = fetch_purchase_requests(conn, 1, None, None, status_filter='open')
    ids = [r['id'] for r in result]
    assert 1 in ids
    assert 2 not in ids


def test_fetch_purchase_requests_unit_scope():
    from modules.purchases.service import fetch_purchase_requests
    conn = _conn()
    conn.execute("INSERT INTO purchase_requests VALUES (1,1,1,'open','R1','',1,'Admin',NULL,NULL,NULL,'2024-01-01','2024-01-01')")
    conn.execute("INSERT INTO purchase_requests VALUES (2,1,2,'open','R2','',1,'Admin',NULL,NULL,NULL,'2024-01-01','2024-01-01')")
    conn.commit()
    result = fetch_purchase_requests(conn, 1, 1, None)
    ids = [r['id'] for r in result]
    assert 1 in ids
    assert 2 not in ids


def test_fetch_purchase_requests_purchase_scope_units():
    from modules.purchases.service import fetch_purchase_requests
    conn = _conn()
    conn.execute("INSERT INTO purchase_requests VALUES (1,1,1,'open','R1','',1,'Admin',NULL,NULL,NULL,'2024-01-01','2024-01-01')")
    conn.execute("INSERT INTO purchase_requests VALUES (2,1,2,'open','R2','',1,'Admin',NULL,NULL,NULL,'2024-01-01','2024-01-01')")
    conn.execute("INSERT INTO purchase_requests VALUES (3,1,1,'open','R3','',1,'Admin',NULL,NULL,NULL,'2024-01-01','2024-01-01')")
    conn.commit()
    result = fetch_purchase_requests(conn, 1, None, [1])
    ids = [r['id'] for r in result]
    assert 1 in ids
    assert 3 in ids
    assert 2 not in ids


# ═══════════════════════════════════════════════════════════════════════════════
# get_purchase_request_detail
# ═══════════════════════════════════════════════════════════════════════════════

def test_get_purchase_request_detail_not_found():
    from modules.purchases.service import get_purchase_request_detail
    conn = _conn()
    pr, items, events = get_purchase_request_detail(conn, 999)
    assert pr is None
    assert items == []
    assert events == []


def test_get_purchase_request_detail_found():
    from modules.purchases.service import get_purchase_request_detail
    conn = _conn()
    conn.execute("INSERT INTO purchase_requests VALUES (1,1,1,'open','Req Teste','',1,'Admin',NULL,NULL,NULL,'2024-01-01','2024-01-01')")
    conn.execute("INSERT INTO purchase_request_items VALUES (1,1,1,1,100,'Capacete','CA-999','unidade','','','N/A','N/A','N/A',2,'stock_minimum',NULL,'','','',NULL,'included_in_request','',NULL,NULL,NULL,NULL,'','','2024-01-01','2024-01-01')")
    conn.execute("INSERT INTO purchase_events VALUES (1,1,'purchase_request',1,'created','','open','',1,'Admin','','','','','2024-01-01')")
    conn.commit()
    pr, items, events = get_purchase_request_detail(conn, 1)
    assert pr is not None
    assert pr['title'] == 'Req Teste'
    assert len(items) == 1
    assert len(events) == 1


# ═══════════════════════════════════════════════════════════════════════════════
# fetch_purchase_orders
# ═══════════════════════════════════════════════════════════════════════════════

def test_fetch_purchase_orders_returns_empty():
    from modules.purchases.service import fetch_purchase_orders
    conn = _conn()
    result = fetch_purchase_orders(conn, 1, None, None)
    assert result == []


def test_fetch_purchase_orders_status_filter():
    from modules.purchases.service import fetch_purchase_orders
    conn = _conn()
    conn.execute("INSERT INTO purchase_orders VALUES (1,1,1,'open','PO-001','FornA','','2024-01-01','2024-01-01')")
    conn.execute("INSERT INTO purchase_orders VALUES (2,1,1,'closed','PO-002','FornB','','2024-01-01','2024-01-01')")
    conn.commit()
    result = fetch_purchase_orders(conn, 1, None, None, status_filter='open')
    assert len(result) == 1
    assert result[0]['po_number'] == 'PO-001'


# ═══════════════════════════════════════════════════════════════════════════════
# get_purchase_order_detail
# ═══════════════════════════════════════════════════════════════════════════════

def test_get_purchase_order_detail_not_found():
    from modules.purchases.service import get_purchase_order_detail
    conn = _conn()
    po, items, files, events = get_purchase_order_detail(conn, 999)
    assert po is None
    assert items == [] and files == [] and events == []


def test_get_purchase_order_detail_found():
    from modules.purchases.service import get_purchase_order_detail
    conn = _conn()
    conn.execute("INSERT INTO purchase_orders VALUES (1,1,1,'open','PO-001','FornA','12345','2024-01-01','2024-01-01')")
    conn.execute("INSERT INTO purchase_order_items VALUES (1,1,NULL,5)")
    conn.execute("INSERT INTO purchase_order_files VALUES (1,1,'nota.pdf','application/pdf','Admin','2024-01-01')")
    conn.execute("INSERT INTO purchase_events VALUES (1,1,'purchase_order',1,'created','','open','',1,'Admin','','','','','2024-01-01')")
    conn.commit()
    po, items, files, events = get_purchase_order_detail(conn, 1)
    assert po['po_number'] == 'PO-001'
    assert len(items) == 1
    assert len(files) == 1
    assert len(events) == 1


# ═══════════════════════════════════════════════════════════════════════════════
# fetch_purchase_events
# ═══════════════════════════════════════════════════════════════════════════════

def test_fetch_purchase_events_by_company():
    from modules.purchases.service import fetch_purchase_events
    conn = _conn()
    conn.execute("INSERT INTO purchase_events VALUES (1,1,'purchase_request',1,'created','','open','',1,'A','','','','','2024-01-01')")
    conn.execute("INSERT INTO purchase_events VALUES (2,2,'purchase_request',2,'created','','open','',1,'A','','','','','2024-01-01')")
    conn.execute("INSERT INTO companies VALUES (2,'C2',1)")
    conn.commit()
    result = fetch_purchase_events(conn, 1)
    ids = [r['id'] for r in result]
    assert 1 in ids
    assert 2 not in ids


def test_fetch_purchase_events_entity_filter():
    from modules.purchases.service import fetch_purchase_events
    conn = _conn()
    conn.execute("INSERT INTO purchase_events VALUES (1,1,'purchase_request',10,'created','','open','',1,'A','','','','','2024-01-01')")
    conn.execute("INSERT INTO purchase_events VALUES (2,1,'purchase_request',20,'created','','open','',1,'A','','','','','2024-01-01')")
    conn.commit()
    result = fetch_purchase_events(conn, 1, entity_type='purchase_request', entity_id='10')
    assert len(result) == 1
    assert result[0]['entity_id'] == 10


# ═══════════════════════════════════════════════════════════════════════════════
# create_purchase_request
# ═══════════════════════════════════════════════════════════════════════════════

def _fake_get_epi(conn, epi_id):
    row = conn.execute('SELECT * FROM epis WHERE id = ?', (epi_id,)).fetchone()
    return dict(row) if row else None


def test_create_purchase_request_success():
    from modules.purchases.service import create_purchase_request
    conn = _conn()
    actor = _actor()
    items = [{'epi_id': 100, 'quantity_requested': 2}]
    result = create_purchase_request(conn, actor, 1, items, 'Nova Req', '', '1.2.3.4', get_epi_by_id_fn=_fake_get_epi)
    assert result['ok'] is True
    assert result['id'] > 0
    assert not result.get('duplicate')
    pr = conn.execute('SELECT * FROM purchase_requests WHERE id = ?', (result['id'],)).fetchone()
    assert pr['title'] == 'Nova Req'
    assert pr['status'] == 'open'
    items_in_db = conn.execute('SELECT * FROM purchase_request_items WHERE purchase_request_id = ?', (result['id'],)).fetchall()
    assert len(items_in_db) == 1


def test_create_purchase_request_records_event():
    from modules.purchases.service import create_purchase_request
    conn = _conn()
    actor = _actor()
    items = [{'epi_id': 100, 'quantity_requested': 1}]
    result = create_purchase_request(conn, actor, 1, items, 'Req Event Test', '', '', get_epi_by_id_fn=_fake_get_epi)
    events = conn.execute('SELECT * FROM purchase_events WHERE entity_type = ? AND entity_id = ?', ('purchase_request', result['id'])).fetchall()
    assert len(events) == 1
    assert events[0]['action'] == 'created'


def test_create_purchase_request_locks_epi_requests():
    from modules.purchases.service import create_purchase_request
    conn = _conn()
    conn.execute("INSERT INTO epi_requests VALUES (5,1,1,10,100,1,'N/A','N/A','N/A','solicitado','2024-01-01',NULL,NULL,NULL,NULL,NULL,NULL)")
    conn.commit()
    actor = _actor()
    items = [{'epi_id': 100, 'quantity_requested': 1, 'epi_request_id': 5}]
    create_purchase_request(conn, actor, 1, items, 'Req Lock', '', '', get_epi_by_id_fn=_fake_get_epi)
    locked = conn.execute('SELECT status FROM epi_requests WHERE id = 5').fetchone()
    assert locked['status'] == 'em análise'


def test_create_purchase_request_raises_on_missing_epi():
    from modules.purchases.service import create_purchase_request
    conn = _conn()
    actor = _actor()
    items = [{'epi_id': 9999, 'quantity_requested': 1}]
    try:
        create_purchase_request(conn, actor, 1, items, 'Req Bad EPI', '', '', get_epi_by_id_fn=_fake_get_epi)
        assert False, 'should have raised'
    except ValueError as e:
        assert '9999' in str(e)


# ═══════════════════════════════════════════════════════════════════════════════
# update_purchase_request_status
# ═══════════════════════════════════════════════════════════════════════════════

def test_update_pr_status_invalid_raises():
    from modules.purchases.service import update_purchase_request_status
    conn = _conn()
    conn.execute("INSERT INTO purchase_requests VALUES (1,1,1,'open','R','',1,'A',NULL,NULL,NULL,'2024-01-01','2024-01-01')")
    conn.commit()
    pr = {'id': 1, 'company_id': 1, 'status': 'open'}
    actor = _actor()
    try:
        update_purchase_request_status(conn, actor, pr, 'invalid_status', '', '', [], '')
        assert False, 'should raise'
    except ValueError:
        pass


def test_update_pr_status_to_closed_closes_items():
    from modules.purchases.service import update_purchase_request_status
    conn = _conn()
    conn.execute("INSERT INTO purchase_requests VALUES (1,1,1,'open','R','',1,'A',NULL,NULL,NULL,'2024-01-01','2024-01-01')")
    conn.execute("INSERT INTO purchase_request_items VALUES (1,1,1,1,100,'Cap','CA-999','unid','','','N/A','N/A','N/A',1,'stock_minimum',NULL,'','','',NULL,'included_in_request','',NULL,NULL,NULL,NULL,'','','2024-01-01','2024-01-01')")
    conn.commit()
    pr = {'id': 1, 'company_id': 1, 'status': 'open'}
    actor = _actor()
    update_purchase_request_status(conn, actor, pr, 'closed', '', '', [], '')
    item = conn.execute('SELECT status FROM purchase_request_items WHERE id = 1').fetchone()
    assert item['status'] == 'closed'


def test_update_pr_status_to_received_updates_items():
    from modules.purchases.service import update_purchase_request_status
    conn = _conn()
    conn.execute("INSERT INTO purchase_requests VALUES (1,1,1,'open','R','',1,'A',NULL,NULL,NULL,'2024-01-01','2024-01-01')")
    conn.execute("INSERT INTO purchase_request_items VALUES (1,1,1,1,100,'Cap','CA-999','unid','','','N/A','N/A','N/A',1,'stock_minimum',NULL,'','','',NULL,'included_in_request','',NULL,NULL,NULL,NULL,'','','2024-01-01','2024-01-01')")
    conn.commit()
    pr = {'id': 1, 'company_id': 1, 'status': 'open'}
    actor = _actor()
    update_purchase_request_status(conn, actor, pr, 'received', '', '', [], '')
    item = conn.execute('SELECT status FROM purchase_request_items WHERE id = 1').fetchone()
    assert item['status'] == 'received'


def test_update_pr_status_records_event():
    from modules.purchases.service import update_purchase_request_status
    conn = _conn()
    conn.execute("INSERT INTO purchase_requests VALUES (1,1,1,'open','R','',1,'A',NULL,NULL,NULL,'2024-01-01','2024-01-01')")
    conn.commit()
    pr = {'id': 1, 'company_id': 1, 'status': 'open'}
    actor = _actor()
    update_purchase_request_status(conn, actor, pr, 'sent_to_buyer', 'enviado', '', [], '1.2.3.4')
    events = conn.execute('SELECT * FROM purchase_events WHERE entity_id = 1').fetchall()
    assert len(events) == 1
    assert events[0]['action'] == 'status_changed'
    assert events[0]['status_to'] == 'sent_to_buyer'
    assert events[0]['comment'] == 'enviado'


# ═══════════════════════════════════════════════════════════════════════════════
# update_epi_request_status
# ═══════════════════════════════════════════════════════════════════════════════

def test_update_epi_request_status_invalid_raises():
    from modules.purchases.service import update_epi_request_status
    conn = _conn()
    req = {'id': 1, 'company_id': 1}
    actor = _actor()
    try:
        update_epi_request_status(conn, actor, req, 'invalid', '', '', '')
        assert False
    except ValueError:
        pass


def test_update_epi_request_status_prorrogado_requires_date():
    from modules.purchases.service import update_epi_request_status
    conn = _conn()
    req = {'id': 1, 'company_id': 1}
    actor = _actor()
    try:
        update_epi_request_status(conn, actor, req, 'prorrogado', '', '', '')
        assert False
    except ValueError as e:
        assert 'prorrogação' in str(e)


def test_update_epi_request_status_updates_and_inserts_history():
    from modules.purchases.service import update_epi_request_status
    conn = _conn()
    conn.execute("INSERT INTO epi_requests VALUES (1,1,1,10,100,1,'N/A','N/A','N/A','solicitado','2024-01-01',NULL,NULL,NULL,NULL,NULL,NULL)")
    conn.commit()
    req = {'id': 1, 'company_id': 1}
    actor = _actor()
    update_epi_request_status(conn, actor, req, 'aprovado', '', '', 'ok')
    row = conn.execute('SELECT status FROM epi_requests WHERE id = 1').fetchone()
    assert row['status'] == 'aprovado'
    hist = conn.execute('SELECT * FROM epi_request_history WHERE request_id = 1').fetchall()
    assert len(hist) == 1
    assert hist[0]['status'] == 'aprovado'
    assert hist[0]['notes'] == 'ok'


# ═══════════════════════════════════════════════════════════════════════════════
# bulk_update_epi_request_statuses
# ═══════════════════════════════════════════════════════════════════════════════

def test_bulk_update_skips_missing_requests():
    from modules.purchases.service import bulk_update_epi_request_statuses
    conn = _conn()
    actor = _actor()
    updates = [{'request_id': 999, 'status': 'aprovado'}]
    bulk_update_epi_request_statuses(conn, actor, updates)
    hist = conn.execute('SELECT * FROM epi_request_history').fetchall()
    assert len(hist) == 0


def test_bulk_update_skips_invalid_status():
    from modules.purchases.service import bulk_update_epi_request_statuses
    conn = _conn()
    conn.execute("INSERT INTO epi_requests VALUES (1,1,1,10,100,1,'N/A','N/A','N/A','solicitado','2024-01-01',NULL,NULL,NULL,NULL,NULL,NULL)")
    conn.commit()
    actor = _actor()
    updates = [{'request_id': 1, 'status': 'status_invalido'}]
    bulk_update_epi_request_statuses(conn, actor, updates)
    row = conn.execute('SELECT status FROM epi_requests WHERE id = 1').fetchone()
    assert row['status'] == 'solicitado'


def test_bulk_update_processes_valid_entries():
    from modules.purchases.service import bulk_update_epi_request_statuses
    conn = _conn()
    conn.execute("INSERT INTO epi_requests VALUES (1,1,1,10,100,1,'N/A','N/A','N/A','solicitado','2024-01-01',NULL,NULL,NULL,NULL,NULL,NULL)")
    conn.execute("INSERT INTO epi_requests VALUES (2,1,1,10,100,1,'N/A','N/A','N/A','solicitado','2024-01-01',NULL,NULL,NULL,NULL,NULL,NULL)")
    conn.commit()
    actor = _actor()
    updates = [
        {'request_id': 1, 'status': 'aprovado', 'notes': 'ok'},
        {'request_id': 2, 'status': 'rejeitado', 'rejection_reason': 'sem estoque'},
    ]
    bulk_update_epi_request_statuses(conn, actor, updates)
    r1 = conn.execute('SELECT status FROM epi_requests WHERE id = 1').fetchone()
    r2 = conn.execute('SELECT status FROM epi_requests WHERE id = 2').fetchone()
    assert r1['status'] == 'aprovado'
    assert r2['status'] == 'rejeitado'
    hist = conn.execute('SELECT * FROM epi_request_history ORDER BY id').fetchall()
    assert len(hist) == 2


# ═══════════════════════════════════════════════════════════════════════════════
# update_feedback_status
# ═══════════════════════════════════════════════════════════════════════════════

def test_update_feedback_status_invalid_raises():
    from modules.purchases.service import update_feedback_status
    conn = _conn()
    feedback = {'id': 1, 'company_id': 1}
    actor = _actor()
    try:
        update_feedback_status(conn, actor, feedback, 'invalido', '')
        assert False
    except ValueError:
        pass


def test_update_feedback_status_updates_and_inserts_history():
    from modules.purchases.service import update_feedback_status
    conn = _conn()
    conn.execute("INSERT INTO epi_feedbacks VALUES (1,1,'pendente',NULL,NULL,NULL,NULL)")
    conn.commit()
    feedback = {'id': 1, 'company_id': 1}
    actor = _actor()
    update_feedback_status(conn, actor, feedback, 'aprovada', 'looks good')
    row = conn.execute('SELECT status FROM epi_feedbacks WHERE id = 1').fetchone()
    assert row['status'] == 'aprovada'
    hist = conn.execute('SELECT * FROM epi_feedback_history WHERE feedback_id = 1').fetchall()
    assert len(hist) == 1
    assert hist[0]['notes'] == 'looks good'


# ═══════════════════════════════════════════════════════════════════════════════
# upsert_authorized_supplier
# ═══════════════════════════════════════════════════════════════════════════════

def test_upsert_authorized_supplier_not_found_returns_false():
    from modules.purchases.service import upsert_authorized_supplier
    conn = _conn()
    result = upsert_authorized_supplier(conn, 1, 999, 'Test', '', '', '', '')
    assert result is False


def test_upsert_authorized_supplier_updates_fields():
    from modules.purchases.service import upsert_authorized_supplier
    conn = _conn()
    conn.execute("INSERT INTO authorized_suppliers VALUES (1,1,'Old Name','','','','',NULL)")
    conn.commit()
    result = upsert_authorized_supplier(conn, 1, 1, 'New Name', '12345', 'EPI', 'test@x.com', 'obs')
    assert result is True
    row = conn.execute('SELECT * FROM authorized_suppliers WHERE id = 1').fetchone()
    assert row['name'] == 'New Name'
    assert row['cnpj'] == '12345'
    assert row['contact_email'] == 'test@x.com'


# ═══════════════════════════════════════════════════════════════════════════════
# delete_purchase_function_link
# ═══════════════════════════════════════════════════════════════════════════════

def test_delete_purchase_function_link_not_found_raises():
    from modules.purchases.service import delete_purchase_function_link
    conn = _conn()
    try:
        delete_purchase_function_link(conn, 1, 999)
        assert False
    except ValueError:
        pass


def test_delete_purchase_function_link_wrong_company_raises():
    from modules.purchases.service import delete_purchase_function_link
    conn = _conn()
    conn.execute("INSERT INTO purchase_role_unit_links VALUES (1,2,1,10,'buyer')")
    conn.commit()
    try:
        delete_purchase_function_link(conn, 1, 1)
        assert False
    except PermissionError:
        pass


def test_delete_purchase_function_link_success():
    from modules.purchases.service import delete_purchase_function_link
    conn = _conn()
    conn.execute("INSERT INTO purchase_role_unit_links VALUES (1,1,1,10,'buyer')")
    conn.commit()
    delete_purchase_function_link(conn, 1, 1)
    row = conn.execute('SELECT * FROM purchase_role_unit_links WHERE id = 1').fetchone()
    assert row is None


# ═══════════════════════════════════════════════════════════════════════════════
# delete_user_unit_link
# ═══════════════════════════════════════════════════════════════════════════════

def test_delete_user_unit_link_not_found_raises():
    from modules.purchases.service import delete_user_unit_link
    conn = _conn()
    try:
        delete_user_unit_link(conn, 1, 999)
        assert False
    except ValueError:
        pass


def test_delete_user_unit_link_success():
    from modules.purchases.service import delete_user_unit_link
    conn = _conn()
    conn.execute("INSERT INTO user_unit_links VALUES (1,1,1,5)")
    conn.commit()
    delete_user_unit_link(conn, 1, 1)
    row = conn.execute('SELECT * FROM user_unit_links WHERE id = 1').fetchone()
    assert row is None


# ═══════════════════════════════════════════════════════════════════════════════
# fetch_authorized_suppliers
# ═══════════════════════════════════════════════════════════════════════════════

def test_fetch_authorized_suppliers_returns_sorted():
    from modules.purchases.service import fetch_authorized_suppliers
    conn = _conn()
    conn.execute("INSERT INTO authorized_suppliers VALUES (1,1,'Zebra','','','','',NULL)")
    conn.execute("INSERT INTO authorized_suppliers VALUES (2,1,'Alpha','','','','',NULL)")
    conn.commit()
    result = fetch_authorized_suppliers(conn, 1)
    names = [r['name'] for r in result]
    assert names == ['Alpha', 'Zebra']


def test_fetch_authorized_suppliers_filters_by_company():
    from modules.purchases.service import fetch_authorized_suppliers
    conn = _conn()
    conn.execute("INSERT INTO authorized_suppliers VALUES (1,1,'FornA','','','','',NULL)")
    conn.execute("INSERT INTO authorized_suppliers VALUES (2,2,'FornB','','','','',NULL)")
    conn.execute("INSERT INTO companies VALUES (2,'C2',1)")
    conn.commit()
    result = fetch_authorized_suppliers(conn, 1)
    names = [r['name'] for r in result]
    assert 'FornA' in names
    assert 'FornB' not in names


# ═══════════════════════════════════════════════════════════════════════════════
# fetch_supplier_purchase_orders
# ═══════════════════════════════════════════════════════════════════════════════

def test_fetch_supplier_pos_not_found():
    from modules.purchases.service import fetch_supplier_purchase_orders
    conn = _conn()
    sup, items = fetch_supplier_purchase_orders(conn, 1, 999)
    assert sup is None
    assert items is None


def test_fetch_supplier_pos_found():
    from modules.purchases.service import fetch_supplier_purchase_orders
    conn = _conn()
    conn.execute("INSERT INTO authorized_suppliers VALUES (1,1,'FornA','','','','',NULL)")
    conn.execute("INSERT INTO purchase_orders VALUES (1,1,1,'open','PO-001','FornA','','2024-01-01','2024-01-01')")
    conn.commit()
    sup, items = fetch_supplier_purchase_orders(conn, 1, 1)
    assert sup['name'] == 'FornA'
    assert len(items) == 1


# ═══════════════════════════════════════════════════════════════════════════════
# get_company_purchase_config
# ═══════════════════════════════════════════════════════════════════════════════

def test_get_company_purchase_config_missing_returns_empty():
    from modules.purchases.service import get_company_purchase_config
    conn = _conn()
    result = get_company_purchase_config(conn, 1)
    assert result == {}


def test_get_company_purchase_config_returns_parsed_json():
    import json
    from modules.purchases.service import get_company_purchase_config
    conn = _conn()
    config_data = {'max_po_value': 10000, 'require_two_approvers': True}
    conn.execute("INSERT INTO app_meta VALUES ('purchase_config_1', ?)", (json.dumps(config_data),))
    conn.commit()
    result = get_company_purchase_config(conn, 1)
    assert result['max_po_value'] == 10000
    assert result['require_two_approvers'] is True


# ═══════════════════════════════════════════════════════════════════════════════
# fetch_user_unit_links
# ═══════════════════════════════════════════════════════════════════════════════

def test_fetch_user_unit_links_self_merges_prl():
    from modules.purchases.service import fetch_user_unit_links
    conn = _conn()
    conn.execute("INSERT INTO user_unit_links VALUES (1,1,1,5)")
    conn.execute("INSERT INTO purchase_role_unit_links VALUES (1,1,2,10,'buyer')")
    conn.commit()
    result = fetch_user_unit_links(conn, 1, 5, linked_employee_id=10, is_self=True)
    unit_ids = {r['unit_id'] for r in result}
    assert 1 in unit_ids
    assert 2 in unit_ids


def test_fetch_user_unit_links_self_no_duplicate_units():
    from modules.purchases.service import fetch_user_unit_links
    conn = _conn()
    conn.execute("INSERT INTO user_unit_links VALUES (1,1,1,5)")
    conn.execute("INSERT INTO purchase_role_unit_links VALUES (1,1,1,10,'buyer')")
    conn.commit()
    result = fetch_user_unit_links(conn, 1, 5, linked_employee_id=10, is_self=True)
    unit_ids = [r['unit_id'] for r in result]
    assert unit_ids.count(1) == 1


def test_fetch_user_unit_links_admin_by_target_user():
    from modules.purchases.service import fetch_user_unit_links
    conn = _conn()
    conn.execute("INSERT INTO user_unit_links VALUES (1,1,1,5)")
    conn.execute("INSERT INTO user_unit_links VALUES (2,1,2,6)")
    conn.commit()
    result = fetch_user_unit_links(conn, 1, 5)
    unit_ids = [r['unit_id'] for r in result]
    assert 1 in unit_ids
    assert 2 not in unit_ids


def test_fetch_user_unit_links_admin_all_users():
    from modules.purchases.service import fetch_user_unit_links
    conn = _conn()
    conn.execute("INSERT INTO users VALUES (5,1,'u1','buyer','User A',1,NULL)")
    conn.execute("INSERT INTO users VALUES (6,1,'u2','buyer','User B',1,NULL)")
    conn.execute("INSERT INTO user_unit_links VALUES (1,1,1,5)")
    conn.execute("INSERT INTO user_unit_links VALUES (2,1,2,6)")
    conn.commit()
    result = fetch_user_unit_links(conn, 1, None)
    assert len(result) == 2


# ═══════════════════════════════════════════════════════════════════════════════
# review_purchase_request_items
# ═══════════════════════════════════════════════════════════════════════════════

def test_review_pr_items_update_quantity():
    from modules.purchases.service import review_purchase_request_items
    conn = _conn()
    conn.execute("INSERT INTO purchase_requests VALUES (1,1,1,'waiting_requester_correction','R','',1,'A',NULL,NULL,NULL,'2024-01-01','2024-01-01')")
    conn.execute("INSERT INTO purchase_request_items VALUES (1,1,1,1,100,'Cap','CA-999','unid','','','N/A','N/A','N/A',1,'stock_minimum',NULL,'','','',NULL,'included_in_request','',NULL,NULL,NULL,NULL,'','','2024-01-01','2024-01-01')")
    conn.commit()
    pr = {'id': 1, 'company_id': 1, 'unit_id': 1, 'status': 'waiting_requester_correction'}
    actor = _actor()
    affected = review_purchase_request_items(conn, actor, pr, [{'id': 1, 'quantity_requested': 5}], [], [], '', '', '', get_epi_by_id_fn=_fake_get_epi)
    assert 1 in affected
    qty = conn.execute('SELECT quantity_requested FROM purchase_request_items WHERE id = 1').fetchone()
    assert qty['quantity_requested'] == 5


def test_review_pr_items_delete_item():
    from modules.purchases.service import review_purchase_request_items
    conn = _conn()
    conn.execute("INSERT INTO purchase_requests VALUES (1,1,1,'waiting_requester_correction','R','',1,'A',NULL,NULL,NULL,'2024-01-01','2024-01-01')")
    conn.execute("INSERT INTO purchase_request_items VALUES (1,1,1,1,100,'Cap','CA-999','unid','','','N/A','N/A','N/A',1,'stock_minimum',NULL,'','','',NULL,'included_in_request','',NULL,NULL,NULL,NULL,'','','2024-01-01','2024-01-01')")
    conn.commit()
    pr = {'id': 1, 'company_id': 1, 'unit_id': 1, 'status': 'waiting_requester_correction'}
    actor = _actor()
    review_purchase_request_items(conn, actor, pr, [], [1], [], '', '', '', get_epi_by_id_fn=_fake_get_epi)
    row = conn.execute('SELECT * FROM purchase_request_items WHERE id = 1').fetchone()
    assert row is None


def test_review_pr_items_add_new_item():
    from modules.purchases.service import review_purchase_request_items
    conn = _conn()
    conn.execute("INSERT INTO purchase_requests VALUES (1,1,1,'waiting_requester_correction','R','',1,'A',NULL,NULL,NULL,'2024-01-01','2024-01-01')")
    conn.commit()
    pr = {'id': 1, 'company_id': 1, 'unit_id': 1, 'status': 'waiting_requester_correction'}
    actor = _actor()
    affected = review_purchase_request_items(conn, actor, pr, [], [], [{'epi_id': 100, 'quantity_requested': 3}], '', '', '', get_epi_by_id_fn=_fake_get_epi)
    assert len(affected) == 1
    items = conn.execute('SELECT * FROM purchase_request_items WHERE purchase_request_id = 1').fetchall()
    assert len(items) == 1
    assert items[0]['quantity_requested'] == 3
