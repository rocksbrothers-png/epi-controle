"""Item 4 — QR híbrido de entrega (handover_token) + fechamento do portal.

O QR da entrega carrega um token OPACO. A conferência resolve uma projeção
SEGURA (nome+sobrenome, matrícula, EPI, tamanho, lote, solicitação) sem expor
CPF. A confirmação é idempotente, fecha a solicitação como 'entregue' e não
duplica entrega/movimentação. Multi-tenant respeitado.
"""

import sqlite3

import pytest

from modules.deliveries.service import (
    confirm_delivery_handover,
    generate_handover_token,
    lookup_delivery_by_handover_token,
)


def _conn():
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        CREATE TABLE employees (id INTEGER PRIMARY KEY, company_id INTEGER, unit_id INTEGER,
            name TEXT, employee_id_code TEXT DEFAULT '', sector TEXT DEFAULT '', role_name TEXT DEFAULT '');
        CREATE TABLE epis (id INTEGER PRIMARY KEY, name TEXT, purchase_code TEXT DEFAULT '', ca TEXT DEFAULT '');
        CREATE TABLE units (id INTEGER PRIMARY KEY, name TEXT);
        CREATE TABLE epi_stock_items (id INTEGER PRIMARY KEY AUTOINCREMENT, company_id INTEGER,
            unit_id INTEGER, epi_id INTEGER, lot_code TEXT DEFAULT '', qr_code_value TEXT DEFAULT '',
            status TEXT DEFAULT 'in_stock', delivery_id INTEGER);
        CREATE TABLE epi_requests (id INTEGER PRIMARY KEY AUTOINCREMENT, employee_id INTEGER, epi_id INTEGER,
            quantity INTEGER DEFAULT 1, status TEXT DEFAULT 'aprovado', delivery_id INTEGER,
            last_updated_at TEXT DEFAULT '');
        CREATE TABLE deliveries (id INTEGER PRIMARY KEY AUTOINCREMENT, company_id INTEGER, unit_id INTEGER,
            employee_id INTEGER, epi_id INTEGER, quantity INTEGER DEFAULT 1, quantity_label TEXT DEFAULT 'unidade',
            delivery_date TEXT DEFAULT '2026-07-18', glove_size TEXT DEFAULT 'N/A', size TEXT DEFAULT 'M',
            uniform_size TEXT DEFAULT 'N/A', signature_name TEXT DEFAULT '', signature_data TEXT DEFAULT '',
            signature_ip TEXT DEFAULT '', signature_at TEXT DEFAULT '', signature_comment TEXT DEFAULT '',
            handover_token TEXT DEFAULT '', handover_confirmed_at TEXT DEFAULT '',
            handover_confirmed_by INTEGER, handover_confirmed_name TEXT DEFAULT '');
        INSERT INTO units (id, name) VALUES (2, 'Base Norte');
        INSERT INTO employees (id, company_id, unit_id, name, employee_id_code, sector, role_name)
            VALUES (5, 1, 2, 'Maria da Silva Souza', 'MAT-007', 'Operações', 'Técnica');
        INSERT INTO epis (id, name, purchase_code, ca) VALUES (9, 'Luva Nitrílica', 'P-9', 'CA-1');
        INSERT INTO deliveries (id, company_id, unit_id, employee_id, epi_id, handover_token)
            VALUES (100, 1, 2, 5, 9, 'ENTREGA-tok-abc');
        INSERT INTO epi_stock_items (company_id, unit_id, epi_id, lot_code, qr_code_value, status, delivery_id)
            VALUES (1, 2, 9, 'LOTE-42', 'EPI-ITEM-0001-0002-00000003', 'delivered', 100);
        INSERT INTO epi_requests (employee_id, epi_id, quantity, status, delivery_id)
            VALUES (5, 9, 1, 'aprovado', 100);
        """
    )
    conn.commit()
    return conn


ACTOR = {'id': 1, 'role': 'admin', 'company_id': 1, 'full_name': 'Almoxarife'}
MASTER = {'id': 2, 'role': 'master_admin', 'company_id': 99, 'full_name': 'Master'}
OTHER_CO = {'id': 3, 'role': 'admin', 'company_id': 2, 'full_name': 'Outro'}


def test_token_is_opaque_and_prefixed():
    a, b = generate_handover_token(), generate_handover_token()
    assert a.startswith('ENTREGA-') and b.startswith('ENTREGA-')
    assert a != b  # entropia por entrega
    assert len(a) > 20


def test_lookup_returns_safe_projection_without_personal_data():
    conn = _conn()
    data = lookup_delivery_by_handover_token(conn, 'ENTREGA-tok-abc', ACTOR)
    assert data['employee_first_name'] == 'Maria'
    assert data['employee_last_name'] == 'da Silva Souza'
    assert data['employee_registration'] == 'MAT-007'  # matrícula
    assert data['epi_name'] == 'Luva Nitrílica'
    assert data['size'] == 'M'
    assert data['lot_code'] == 'LOTE-42'
    assert data['request_id'] == 1
    # Nenhum dado pessoal direto (CPF) na projeção.
    assert not any('cpf' in k.lower() for k in data)


def test_lookup_unknown_token_raises():
    conn = _conn()
    with pytest.raises(ValueError):
        lookup_delivery_by_handover_token(conn, 'ENTREGA-nao-existe', ACTOR)


def test_lookup_blocks_other_company():
    conn = _conn()
    with pytest.raises(PermissionError):
        lookup_delivery_by_handover_token(conn, 'ENTREGA-tok-abc', OTHER_CO)


def test_master_can_lookup_any_company():
    conn = _conn()
    data = lookup_delivery_by_handover_token(conn, 'ENTREGA-tok-abc', MASTER)
    assert data['delivery_id'] == 100


def test_confirm_closes_request_and_is_idempotent():
    conn = _conn()
    r1 = confirm_delivery_handover(conn, 'ENTREGA-tok-abc', ACTOR,
                                   signature_name='Maria', signature_data='data:img')
    assert r1['confirmed'] is True and r1['already_confirmed'] is False
    # Solicitação vinculada foi fechada.
    status = conn.execute('SELECT status FROM epi_requests WHERE delivery_id = 100').fetchone()[0]
    assert status == 'entregue'
    # Assinatura aplicada.
    sig = conn.execute('SELECT signature_at, handover_confirmed_at FROM deliveries WHERE id = 100').fetchone()
    assert sig[0] and sig[1]
    # Segunda confirmação é idempotente (não duplica).
    r2 = confirm_delivery_handover(conn, 'ENTREGA-tok-abc', ACTOR)
    assert r2['already_confirmed'] is True
    assert r2['confirmed_at'] == r1['confirmed_at']
    # Continua exatamente uma entrega e uma solicitação entregue.
    assert conn.execute('SELECT COUNT(*) FROM deliveries').fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM epi_requests WHERE status='entregue'").fetchone()[0] == 1


def test_confirm_blocks_other_company():
    conn = _conn()
    with pytest.raises(PermissionError):
        confirm_delivery_handover(conn, 'ENTREGA-tok-abc', OTHER_CO)


def test_lookup_reflects_confirmed_state():
    conn = _conn()
    confirm_delivery_handover(conn, 'ENTREGA-tok-abc', ACTOR)
    data = lookup_delivery_by_handover_token(conn, 'ENTREGA-tok-abc', ACTOR)
    assert data['already_confirmed'] is True
