"""Testes de integração das mutações de Ordem de Compra (PO).

Exercita create/review/resubmit/approve (nível único e multi-nível) /receive
(incl. conferência com baixa em estoque) / upload de arquivo, contra um schema
SQLite em memória que espelha as colunas reais usadas pelos serviços.
"""

import json
import sqlite3

import pytest

from modules.purchases.service import (
    add_purchase_order_file,
    approve_purchase_order,
    create_purchase_order,
    ensure_purchase_order_action_scope,
    get_purchase_order_by_id,
    receive_purchase_order,
    resubmit_purchase_order,
    review_purchase_order,
)

ADMIN = {'id': 1, 'company_id': 1, 'role': 'general_admin', 'full_name': 'Admin Geral', 'linked_employee_id': None}


def _conn():
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        CREATE TABLE companies (id INTEGER PRIMARY KEY, name TEXT, active INTEGER DEFAULT 1);
        CREATE TABLE units (id INTEGER PRIMARY KEY, company_id INTEGER, name TEXT,
            unit_type TEXT DEFAULT 'base', city TEXT DEFAULT '', notes TEXT DEFAULT '');
        CREATE TABLE app_meta (key TEXT PRIMARY KEY, value TEXT);
        CREATE TABLE purchase_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT, company_id INTEGER, unit_id INTEGER,
            status TEXT DEFAULT 'open', title TEXT DEFAULT '', notes TEXT DEFAULT '',
            linked_po_id INTEGER, linked_po_number TEXT DEFAULT '',
            created_by_user_id INTEGER, created_by_name TEXT DEFAULT '',
            created_at TEXT, updated_at TEXT
        );
        CREATE TABLE purchase_request_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT, purchase_request_id INTEGER,
            company_id INTEGER, unit_id INTEGER, epi_id INTEGER, status TEXT DEFAULT 'open'
        );
        CREATE TABLE purchase_orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT, purchase_request_id INTEGER,
            company_id INTEGER NOT NULL, unit_id INTEGER NOT NULL, status TEXT NOT NULL DEFAULT 'draft',
            po_number TEXT NOT NULL DEFAULT '', supplier TEXT NOT NULL DEFAULT '',
            supplier_cnpj TEXT NOT NULL DEFAULT '', expected_delivery_date TEXT NOT NULL DEFAULT '',
            notes TEXT NOT NULL DEFAULT '', total_value REAL NOT NULL DEFAULT 0,
            created_by_user_id INTEGER NOT NULL, created_by_name TEXT NOT NULL DEFAULT '',
            approved_by_user_id INTEGER, approved_by_name TEXT NOT NULL DEFAULT '',
            approved_at TEXT NOT NULL DEFAULT '', approval_comment TEXT NOT NULL DEFAULT '',
            received_by_user_id INTEGER, received_by_name TEXT NOT NULL DEFAULT '',
            received_at TEXT NOT NULL DEFAULT '', checked_at TEXT NOT NULL DEFAULT '',
            closed_at TEXT NOT NULL DEFAULT '', postponed_until TEXT NOT NULL DEFAULT '',
            buyer_suggestions TEXT NOT NULL DEFAULT '',
            admin_review_by_user_id INTEGER, admin_review_by_name TEXT NOT NULL DEFAULT '',
            admin_review_at TEXT NOT NULL DEFAULT '', admin_review_comment TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL, updated_at TEXT NOT NULL
        );
        CREATE TABLE purchase_order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT, purchase_order_id INTEGER NOT NULL,
            purchase_request_item_id INTEGER, company_id INTEGER, unit_id INTEGER,
            epi_id INTEGER, epi_name TEXT DEFAULT '', ca TEXT DEFAULT '', unit_measure TEXT DEFAULT '',
            manufacturer TEXT DEFAULT '', supplier TEXT DEFAULT '', glove_size TEXT DEFAULT 'N/A',
            size TEXT DEFAULT 'N/A', uniform_size TEXT DEFAULT 'N/A', quantity INTEGER DEFAULT 1,
            quantity_approved INTEGER DEFAULT 0, quantity_received INTEGER DEFAULT 0,
            unit_price REAL DEFAULT 0, total_price REAL DEFAULT 0, origin TEXT DEFAULT 'stock_minimum',
            employee_name TEXT DEFAULT '', employee_sector TEXT DEFAULT '', employee_role TEXT DEFAULT '',
            status TEXT DEFAULT 'open', notes TEXT DEFAULT '', created_at TEXT, updated_at TEXT
        );
        CREATE TABLE purchase_order_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT, purchase_order_id INTEGER, company_id INTEGER,
            file_name TEXT, file_type TEXT, file_data TEXT, uploaded_by_user_id INTEGER,
            uploaded_by_name TEXT, created_at TEXT
        );
        CREATE TABLE purchase_approvals (
            id INTEGER PRIMARY KEY AUTOINCREMENT, purchase_order_id INTEGER, company_id INTEGER,
            decision TEXT, comment TEXT DEFAULT '', actor_user_id INTEGER, actor_name TEXT, created_at TEXT
        );
        CREATE TABLE purchase_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT, company_id INTEGER, entity_type TEXT, entity_id INTEGER,
            action TEXT, status_from TEXT DEFAULT '', status_to TEXT DEFAULT '', comment TEXT DEFAULT '',
            actor_user_id INTEGER, actor_name TEXT DEFAULT '', actor_role TEXT DEFAULT '',
            reason TEXT DEFAULT '', destination TEXT DEFAULT '', ip_address TEXT DEFAULT '', created_at TEXT
        );
        -- estoque (caminho de conferência)
        CREATE TABLE unit_epi_stock (id INTEGER PRIMARY KEY AUTOINCREMENT, company_id INTEGER,
            unit_id INTEGER, epi_id INTEGER, quantity INTEGER DEFAULT 0, updated_at TEXT);
        CREATE TABLE stock_movements (id INTEGER PRIMARY KEY AUTOINCREMENT, company_id INTEGER,
            unit_id INTEGER, epi_id INTEGER, movement_type TEXT, quantity INTEGER, previous_stock INTEGER,
            new_stock INTEGER, source_type TEXT, source_id INTEGER, notes TEXT, actor_user_id INTEGER,
            actor_name TEXT, created_at TEXT);
        CREATE TABLE epi_stock_items (id INTEGER PRIMARY KEY AUTOINCREMENT, company_id INTEGER, unit_id INTEGER,
            epi_id INTEGER, glove_size TEXT, size TEXT, uniform_size TEXT, qr_sequence INTEGER, qr_code_value TEXT,
            status TEXT, stock_movement_id INTEGER, lot_code TEXT, manufacture_date TEXT, label_measure TEXT,
            label_printer_name TEXT, label_print_format TEXT, generated_by_user_id INTEGER,
            created_at TEXT, updated_at TEXT);
        CREATE TABLE epi_qr_sequences (company_id INTEGER PRIMARY KEY, last_value INTEGER);

        INSERT INTO companies (id, name) VALUES (1, 'ACME'), (2, 'Outra');
        INSERT INTO units (id, company_id, name) VALUES (10, 1, 'Base Santos'), (20, 2, 'Base Rio');
    """)
    conn.commit()
    return conn


def _basic_items():
    return [{
        'epi_id': 100, 'epi_name': 'Luva', 'ca': '123', 'manufacturer': 'Fab',
        'quantity': 3, 'unit_price': 10.0, 'origin': 'stock_minimum',
    }]


def _set_threshold(conn, company_id, value):
    conn.execute(
        'INSERT OR REPLACE INTO app_meta (key, value) VALUES (?, ?)',
        (f'purchase_config_{company_id}', json.dumps({'po_approval_threshold': value})),
    )
    conn.commit()


# ── create ────────────────────────────────────────────────────────────────────

def test_create_po_basic():
    conn = _conn()
    res = create_purchase_order(conn, ADMIN, {'unit_id': 10, 'supplier': 'Fornec', 'items': _basic_items()}, '1.2.3.4')
    assert res['status'] == 'waiting_admin_review'
    po = get_purchase_order_by_id(conn, res['id'])
    assert po['total_value'] == 30.0
    assert po['po_number'].startswith('PO-')
    items = conn.execute('SELECT * FROM purchase_order_items WHERE purchase_order_id = ?', (res['id'],)).fetchall()
    assert len(items) == 1 and items[0]['total_price'] == 30.0
    ev = conn.execute("SELECT * FROM purchase_events WHERE entity_type='purchase_order' AND action='created'").fetchone()
    assert ev['status_to'] == 'waiting_admin_review'


def test_create_po_requires_items():
    conn = _conn()
    with pytest.raises(ValueError):
        create_purchase_order(conn, ADMIN, {'unit_id': 10, 'items': []}, '')


def test_create_po_links_purchase_request():
    conn = _conn()
    conn.execute("INSERT INTO purchase_requests (id, company_id, unit_id, status) VALUES (5, 1, 10, 'partially_approved')")
    conn.execute("INSERT INTO purchase_request_items (id, purchase_request_id, company_id, unit_id, epi_id, status) "
                 "VALUES (7, 5, 1, 10, 100, 'approved')")
    conn.commit()
    items = _basic_items()
    items[0]['purchase_request_item_id'] = 7
    res = create_purchase_order(conn, ADMIN, {'unit_id': 10, 'purchase_request_id': 5, 'items': items}, '')
    pr = conn.execute('SELECT * FROM purchase_requests WHERE id = 5').fetchone()
    assert pr['status'] == 'po_generated'
    assert pr['linked_po_id'] == res['id']


# ── review + resubmit ─────────────────────────────────────────────────────────

def test_review_approved_advances_to_pending():
    conn = _conn()
    po_id = create_purchase_order(conn, ADMIN, {'unit_id': 10, 'items': _basic_items()}, '')['id']
    out = review_purchase_order(conn, ADMIN, get_purchase_order_by_id(conn, po_id), 'review_approved', '', '')
    assert out['status'] == 'pending_approval'


def test_review_return_then_resubmit_roundtrip():
    conn = _conn()
    po_id = create_purchase_order(conn, ADMIN, {'unit_id': 10, 'items': _basic_items()}, '')['id']
    review_purchase_order(conn, ADMIN, get_purchase_order_by_id(conn, po_id), 'returned_with_suggestions', 'Trocar fornecedor', '')
    po = get_purchase_order_by_id(conn, po_id)
    assert po['status'] == 'quoted'
    assert po['buyer_suggestions'] == 'Trocar fornecedor'
    out = resubmit_purchase_order(conn, ADMIN, po, 'Fornecedor ajustado', '')
    assert out['status'] == 'waiting_admin_review'


def test_review_requires_comment_on_return():
    conn = _conn()
    po_id = create_purchase_order(conn, ADMIN, {'unit_id': 10, 'items': _basic_items()}, '')['id']
    with pytest.raises(ValueError):
        review_purchase_order(conn, ADMIN, get_purchase_order_by_id(conn, po_id), 'returned_with_suggestions', '', '')


# ── approval (single level) ───────────────────────────────────────────────────

def _to_pending(conn):
    po_id = create_purchase_order(conn, ADMIN, {'unit_id': 10, 'items': _basic_items()}, '')['id']
    review_purchase_order(conn, ADMIN, get_purchase_order_by_id(conn, po_id), 'review_approved', '', '')
    return po_id


def test_approve_single_level_full():
    conn = _conn()
    po_id = _to_pending(conn)
    out = approve_purchase_order(conn, ADMIN, get_purchase_order_by_id(conn, po_id), 'approved', 'ok', [], '', '')
    assert out['status'] == 'approved' and out['pending_next_level'] is False
    po = get_purchase_order_by_id(conn, po_id)
    assert po['approved_by_user_id'] == 1
    item = conn.execute('SELECT * FROM purchase_order_items WHERE purchase_order_id = ?', (po_id,)).fetchone()
    assert item['quantity_approved'] == 3 and item['status'] == 'approved'


def test_approve_rejected_requires_comment():
    conn = _conn()
    po_id = _to_pending(conn)
    with pytest.raises(ValueError):
        approve_purchase_order(conn, ADMIN, get_purchase_order_by_id(conn, po_id), 'rejected', '', [], '', '')


def test_approve_rejected_terminal():
    conn = _conn()
    po_id = _to_pending(conn)
    out = approve_purchase_order(conn, ADMIN, get_purchase_order_by_id(conn, po_id), 'rejected', 'fora do escopo', [], '', '')
    assert out['status'] == 'rejected'


def test_approve_postponed_requires_date():
    conn = _conn()
    po_id = _to_pending(conn)
    with pytest.raises(ValueError):
        approve_purchase_order(conn, ADMIN, get_purchase_order_by_id(conn, po_id), 'postponed', '', [], '', '')


def test_approve_partial_with_item_decisions():
    conn = _conn()
    po_id = _to_pending(conn)
    item = conn.execute('SELECT id FROM purchase_order_items WHERE purchase_order_id = ?', (po_id,)).fetchone()
    decisions = [{'item_id': item['id'], 'approved': False, 'rejection_reason': 'Valor acima do esperado'}]
    out = approve_purchase_order(conn, ADMIN, get_purchase_order_by_id(conn, po_id), 'partially_approved', '', decisions, '', '')
    assert out['status'] == 'partially_approved'
    row = conn.execute('SELECT * FROM purchase_order_items WHERE id = ?', (item['id'],)).fetchone()
    assert row['status'] == 'rejected' and row['quantity_approved'] == 0


# ── approval multi-nível ──────────────────────────────────────────────────────

ADMIN2 = {'id': 3, 'company_id': 1, 'role': 'general_admin', 'full_name': 'Aprovador 2', 'linked_employee_id': None}


def test_approve_multilevel_two_steps():
    conn = _conn()
    _set_threshold(conn, 1, 10)  # total 30 >= 10 -> exige 2 níveis
    po_id = _to_pending(conn)
    first = approve_purchase_order(conn, ADMIN, get_purchase_order_by_id(conn, po_id), 'approved', '', [], '', '')
    assert first['status'] == 'pending_approval' and first['pending_next_level'] is True
    # segundo nível, por aprovador DIFERENTE (segregação de funções)
    second = approve_purchase_order(conn, ADMIN2, get_purchase_order_by_id(conn, po_id), 'approved', 'finance ok', [], '', '')
    assert second['status'] == 'approved' and second['pending_next_level'] is False
    approvals = conn.execute('SELECT COUNT(*) AS n FROM purchase_approvals WHERE purchase_order_id = ?', (po_id,)).fetchone()
    assert approvals['n'] == 2


def test_approve_multilevel_second_step_needs_finance_permission():
    conn = _conn()
    _set_threshold(conn, 1, 10)
    po_id = _to_pending(conn)
    approve_purchase_order(conn, ADMIN, get_purchase_order_by_id(conn, po_id), 'approved', '', [], '', '')
    # role 'user' não possui finance:view
    plain_user = {'id': 4, 'company_id': 1, 'role': 'user', 'full_name': 'Usuário', 'linked_employee_id': None}
    with pytest.raises(PermissionError):
        approve_purchase_order(conn, plain_user, get_purchase_order_by_id(conn, po_id), 'approved', '', [], '', '')


def test_approve_multilevel_blocks_same_approver():
    conn = _conn()
    _set_threshold(conn, 1, 10)
    po_id = _to_pending(conn)
    approve_purchase_order(conn, ADMIN, get_purchase_order_by_id(conn, po_id), 'approved', '', [], '', '')
    # mesmo aprovador tentando finalizar o segundo nível
    with pytest.raises(PermissionError):
        approve_purchase_order(conn, ADMIN, get_purchase_order_by_id(conn, po_id), 'approved', '', [], '', '')


# ── receive + conferência (estoque) + fechamento ──────────────────────────────

def _to_approved(conn):
    po_id = _to_pending(conn)
    approve_purchase_order(conn, ADMIN, get_purchase_order_by_id(conn, po_id), 'approved', 'ok', [], '', '')
    return po_id


def test_receive_then_check_adds_stock_then_close():
    conn = _conn()
    po_id = _to_approved(conn)
    item = conn.execute('SELECT id FROM purchase_order_items WHERE purchase_order_id = ?', (po_id,)).fetchone()
    rec = receive_purchase_order(conn, ADMIN, get_purchase_order_by_id(conn, po_id), 'received',
                                 [{'id': item['id'], 'quantity_received': 3}], '', '')
    assert rec['status'] == 'received'
    chk = receive_purchase_order(conn, ADMIN, get_purchase_order_by_id(conn, po_id), 'checked', [], '', '')
    assert chk['status'] == 'checked' and chk['stock_units'] == 3
    stock = conn.execute('SELECT quantity FROM unit_epi_stock WHERE epi_id = 100 AND unit_id = 10').fetchone()
    assert stock['quantity'] == 3
    item_count = conn.execute("SELECT COUNT(*) AS n FROM epi_stock_items WHERE epi_id = 100").fetchone()
    assert item_count['n'] == 3
    closed = receive_purchase_order(conn, ADMIN, get_purchase_order_by_id(conn, po_id), 'closed', [], '', '')
    assert closed['status'] == 'closed'


def test_receive_partial_keeps_status():
    conn = _conn()
    po_id = _to_approved(conn)
    item = conn.execute('SELECT id FROM purchase_order_items WHERE purchase_order_id = ?', (po_id,)).fetchone()
    out = receive_purchase_order(conn, ADMIN, get_purchase_order_by_id(conn, po_id), 'received_partial',
                                 [{'id': item['id'], 'quantity_received': 1}], 'faltou', '')
    assert out['status'] == 'received_partial'


def test_receive_blocked_before_approval():
    conn = _conn()
    po_id = _to_pending(conn)
    with pytest.raises(ValueError):
        receive_purchase_order(conn, ADMIN, get_purchase_order_by_id(conn, po_id), 'received', [], '', '')


# ── arquivos + escopo ─────────────────────────────────────────────────────────

def test_add_file():
    conn = _conn()
    po_id = create_purchase_order(conn, ADMIN, {'unit_id': 10, 'items': _basic_items()}, '')['id']
    out = add_purchase_order_file(conn, ADMIN, get_purchase_order_by_id(conn, po_id), 'cotacao.pdf', 'application/pdf', 'QUJD', '')
    assert out['ok'] is True
    row = conn.execute('SELECT * FROM purchase_order_files WHERE id = ?', (out['id'],)).fetchone()
    assert row['file_name'] == 'cotacao.pdf' and row['file_data'] == 'QUJD'


def test_scope_rejects_other_company():
    conn = _conn()
    other_po = {'id': 99, 'company_id': 2, 'unit_id': 20}
    with pytest.raises(PermissionError):
        ensure_purchase_order_action_scope(conn, ADMIN, other_po)


def test_scope_master_admin_bypass():
    conn = _conn()
    master = {'id': 1, 'company_id': None, 'role': 'master_admin', 'full_name': 'Master'}
    ensure_purchase_order_action_scope(conn, master, {'id': 99, 'company_id': 2, 'unit_id': 20})  # não levanta
