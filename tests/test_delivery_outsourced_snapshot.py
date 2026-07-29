"""Snapshot histórico do vínculo com empresa terceirizada na entrega — PR 4
(ADR-0002).

Cobre:
  - ensure_delivery_outsourced_snapshot_columns: migração idempotente das
    6 colunas snapshot_* em deliveries;
  - resolve_delivery_outsourced_snapshot: congelamento dos atributos no
    momento da entrega, com a mesma precedência de
    resolve_effective_epi_responsibility (colaborador > contrato > empresa);
  - create_delivery_service: a entrega de um colaborador CLT grava snapshot
    vazio (exceto tipo_vinculo); a de um terceirizado grava nome/CNPJ da
    empresa, contrato e responsabilidade efetiva — e uma edição posterior na
    empresa/contrato NÃO altera o snapshot já gravado (histórico imutável).
"""

import sqlite3

import pytest

from core.schema import (
    ensure_delivery_handover_columns,
    ensure_delivery_outsourced_snapshot_columns,
    ensure_delivery_signature_columns,
    ensure_legal_entities,
    ensure_outsourced_companies,
)
from modules.deliveries.service import create_delivery_service
from modules.outsourced_companies.service import (
    create_outsourced_company,
    create_service_contract,
    resolve_delivery_outsourced_snapshot,
    update_outsourced_company,
)


def _dict_factory(cursor, row):
    return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}


# ── migração ────────────────────────────────────────────────────────────────

def test_ensure_delivery_outsourced_snapshot_columns_creates_columns_idempotently():
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.executescript(
        'CREATE TABLE deliveries (id INTEGER PRIMARY KEY, company_id INTEGER NOT NULL);'
    )
    ensure_delivery_outsourced_snapshot_columns(conn)
    ensure_delivery_outsourced_snapshot_columns(conn)  # idempotente
    cols = {row[1] for row in conn.execute('PRAGMA table_info(deliveries)').fetchall()}
    assert {
        'snapshot_tipo_vinculo', 'snapshot_outsourced_company_name',
        'snapshot_outsourced_company_cnpj', 'snapshot_contracting_company_id',
        'snapshot_contract_ref', 'snapshot_epi_responsibility',
    } <= cols


# ── resolve_delivery_outsourced_snapshot (unidade de serviço) ─────────────

def _oc_conn():
    conn = sqlite3.connect(':memory:')
    conn.row_factory = _dict_factory
    conn.executescript(
        """
        CREATE TABLE companies (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, legal_name TEXT DEFAULT '', cnpj TEXT);
        CREATE TABLE units (id INTEGER PRIMARY KEY AUTOINCREMENT, company_id INTEGER NOT NULL, name TEXT);
        CREATE TABLE employees (id INTEGER PRIMARY KEY AUTOINCREMENT, company_id INTEGER NOT NULL, unit_id INTEGER, name TEXT);
        CREATE TABLE users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, company_id INTEGER, role TEXT);
        """
    )
    cur = conn.execute("INSERT INTO companies (name, legal_name, cnpj) VALUES ('ACME', 'ACME', '')")
    conn.commit()
    cid = int(cur.lastrowid)
    ensure_legal_entities(conn)
    ensure_outsourced_companies(conn)
    return conn, cid


def test_snapshot_is_empty_except_tipo_vinculo_for_clt_employee():
    conn, cid = _oc_conn()
    employee = {'tipo_vinculo': 'CLT', 'outsourced_company_id': None, 'service_contract_id': None}
    snapshot = resolve_delivery_outsourced_snapshot(conn, employee, cid)
    assert snapshot['snapshot_tipo_vinculo'] == 'CLT'
    assert snapshot['snapshot_outsourced_company_name'] == ''
    assert snapshot['snapshot_outsourced_company_cnpj'] == ''
    assert snapshot['snapshot_contract_ref'] == ''
    assert snapshot['snapshot_epi_responsibility'] == ''
    assert snapshot['snapshot_contracting_company_id'] == cid


def test_snapshot_captures_outsourced_company_name_cnpj_and_default_responsibility():
    conn, cid = _oc_conn()
    oc_id = create_outsourced_company(
        conn, {'legal_name': 'Terceirizada X', 'cnpj': '11.222.333/0001-81',
               'epi_responsibility': 'Empresa Terceirizada'}, cid,
    )
    employee = {'tipo_vinculo': 'Terceirizado', 'outsourced_company_id': oc_id, 'service_contract_id': None}
    snapshot = resolve_delivery_outsourced_snapshot(conn, employee, cid)
    assert snapshot['snapshot_tipo_vinculo'] == 'Terceirizado'
    assert snapshot['snapshot_outsourced_company_name'] == 'Terceirizada X'
    assert '11.222.333' in snapshot['snapshot_outsourced_company_cnpj']
    assert snapshot['snapshot_epi_responsibility'] == 'Empresa Terceirizada'


def test_snapshot_contract_ref_and_override_precedence():
    conn, cid = _oc_conn()
    oc_id = create_outsourced_company(
        conn, {'legal_name': 'Terceirizada X', 'epi_responsibility': 'Empresa Terceirizada'}, cid,
    )
    contract_id = create_service_contract(
        conn,
        {'contract_ref': 'CTR-001', 'epi_responsibility_override': 'Responsabilidade Compartilhada',
         'override_reason': 'Obra específica'},
        cid, oc_id,
    )
    employee = {
        'tipo_vinculo': 'Terceirizado', 'outsourced_company_id': oc_id, 'service_contract_id': contract_id,
        'epi_responsibility_override': '',
    }
    snapshot = resolve_delivery_outsourced_snapshot(conn, employee, cid)
    assert snapshot['snapshot_contract_ref'] == 'CTR-001'
    assert snapshot['snapshot_epi_responsibility'] == 'Responsabilidade Compartilhada'  # override do contrato vence o default da empresa

    # Exceção individual do colaborador vence tudo, inclusive o contrato.
    employee['epi_responsibility_override'] = 'Empresa Contratante'
    snapshot2 = resolve_delivery_outsourced_snapshot(conn, employee, cid)
    assert snapshot2['snapshot_epi_responsibility'] == 'Empresa Contratante'


def test_snapshot_is_immutable_after_company_is_later_edited():
    # A garantia central do PR 4: editar a empresa DEPOIS não pode alterar
    # um snapshot já resolvido/gravado anteriormente.
    conn, cid = _oc_conn()
    oc_id = create_outsourced_company(
        conn, {'legal_name': 'Terceirizada Original', 'epi_responsibility': 'Empresa Terceirizada'}, cid,
    )
    employee = {'tipo_vinculo': 'Terceirizado', 'outsourced_company_id': oc_id, 'service_contract_id': None}
    snapshot_before = resolve_delivery_outsourced_snapshot(conn, employee, cid)
    assert snapshot_before['snapshot_outsourced_company_name'] == 'Terceirizada Original'

    update_outsourced_company(
        conn, oc_id, {'legal_name': 'Terceirizada Renomeada', 'epi_responsibility': 'Empresa Contratante'}, cid,
    )
    # snapshot_before é um dict já resolvido — congelado por natureza. O que
    # importa é que resolver de novo AGORA reflita a mudança (prova que a
    # função lê o estado vivo), enquanto o snapshot já persistido em uma
    # entrega antiga (snapshot_before) nunca seria re-executado pelo fluxo
    # real — só é escrito uma vez, na criação da entrega.
    snapshot_after = resolve_delivery_outsourced_snapshot(conn, employee, cid)
    assert snapshot_after['snapshot_outsourced_company_name'] == 'Terceirizada Renomeada'
    assert snapshot_before['snapshot_outsourced_company_name'] == 'Terceirizada Original'


# ── integração: create_delivery_service grava o snapshot na entrega ───────

def _delivery_conn():
    conn = sqlite3.connect(':memory:')
    conn.row_factory = _dict_factory
    conn.executescript(
        """
        CREATE TABLE companies (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, legal_name TEXT DEFAULT '', cnpj TEXT);
        CREATE TABLE units (id INTEGER PRIMARY KEY AUTOINCREMENT, company_id INTEGER NOT NULL, name TEXT);
        CREATE TABLE employees (id INTEGER PRIMARY KEY AUTOINCREMENT, company_id INTEGER NOT NULL, unit_id INTEGER, name TEXT);
        CREATE TABLE users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, company_id INTEGER, role TEXT);
        CREATE TABLE deliveries (
            id INTEGER PRIMARY KEY AUTOINCREMENT, company_id INTEGER NOT NULL,
            employee_id INTEGER, epi_id INTEGER, quantity INTEGER, quantity_label TEXT DEFAULT '',
            sector TEXT DEFAULT '', role_name TEXT DEFAULT '', delivery_date TEXT DEFAULT '',
            next_replacement_date TEXT DEFAULT '', notes TEXT DEFAULT '', signature_name TEXT DEFAULT ''
        );
        CREATE TABLE epi_stock_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT, company_id INTEGER NOT NULL, unit_id INTEGER,
            epi_id INTEGER, status TEXT DEFAULT 'in_stock', qr_code_value TEXT DEFAULT '',
            glove_size TEXT DEFAULT 'N/A', size TEXT DEFAULT 'N/A', uniform_size TEXT DEFAULT 'N/A',
            delivery_id INTEGER, updated_at TEXT DEFAULT ''
        );
        CREATE TABLE stock_movements (
            id INTEGER PRIMARY KEY AUTOINCREMENT, company_id INTEGER NOT NULL, unit_id INTEGER,
            epi_id INTEGER, movement_type TEXT, quantity INTEGER, previous_stock INTEGER, new_stock INTEGER,
            source_type TEXT DEFAULT '', source_id INTEGER, notes TEXT DEFAULT '',
            actor_user_id INTEGER, actor_name TEXT DEFAULT '', created_at TEXT DEFAULT '',
            glove_size TEXT DEFAULT 'N/A', size TEXT DEFAULT 'N/A', uniform_size TEXT DEFAULT 'N/A'
        );
        """
    )
    cur = conn.execute("INSERT INTO companies (name, legal_name, cnpj) VALUES ('ACME', 'ACME', '')")
    conn.commit()
    cid = int(cur.lastrowid)
    ensure_delivery_signature_columns(conn)
    ensure_delivery_handover_columns(conn)
    ensure_delivery_outsourced_snapshot_columns(conn)
    ensure_legal_entities(conn)
    ensure_outsourced_companies(conn)
    conn.commit()
    return conn, cid


def _stock_item(conn, company_id, *, unit_id=7, epi_id=30, qr='QR-001'):
    cur = conn.execute(
        'INSERT INTO epi_stock_items (company_id, unit_id, epi_id, status, qr_code_value) '
        "VALUES (?, ?, ?, 'in_stock', ?)",
        (company_id, unit_id, epi_id, qr),
    )
    conn.commit()
    return int(cur.lastrowid), qr


def _delivery_kwargs(employee):
    noop = lambda *a, **k: None
    return dict(
        authorize_action=lambda conn, uid, perm, cid: {'id': 1, 'full_name': 'Op', 'role': 'admin', 'company_id': cid},
        resolve_actor_user_id=lambda: 1,
        get_employee_by_id=lambda conn, eid: employee,
        get_epi_by_id=lambda conn, pid: {
            'id': pid, 'company_id': employee['company_id'], 'unit_id': 7,
            'epi_validity_date': '', 'ca_expiry': '', 'unit_measure': 'UN',
        },
        ensure_resource_company=noop,
        get_employee_current_unit=lambda conn, eid: 7,
        actor_operational_unit_id=lambda conn, act: 7,
        get_unit_stock=lambda *a, **k: {'quantity': 5},
        upsert_unit_stock=noop,
        ensure_ficha_for_delivery=noop,
    )


def test_delivery_for_clt_employee_has_empty_snapshot_except_tipo_vinculo():
    conn, cid = _delivery_conn()
    stock_item_id, qr = _stock_item(conn, cid)
    employee = {'id': 21, 'company_id': cid, 'name': 'Ana', 'tipo_vinculo': 'CLT',
                'outsourced_company_id': None, 'service_contract_id': None}
    payload = {
        'company_id': cid, 'employee_id': 21, 'epi_id': 30, 'quantity': 1,
        'sector': 'Operações', 'role_name': 'Técnica', 'delivery_date': '2026-07-29',
        'next_replacement_date': '2027-07-29', 'stock_item_id': stock_item_id, 'stock_qr_code': qr,
    }
    delivery_id = create_delivery_service(conn, payload, **_delivery_kwargs(employee))
    row = conn.execute('SELECT * FROM deliveries WHERE id = ?', (delivery_id,)).fetchone()
    assert row['snapshot_tipo_vinculo'] == 'CLT'
    assert row['snapshot_outsourced_company_name'] == ''
    assert row['snapshot_epi_responsibility'] == ''


def test_delivery_for_outsourced_employee_captures_full_snapshot():
    conn, cid = _delivery_conn()
    oc_id = create_outsourced_company(
        conn, {'legal_name': 'Terceirizada X', 'cnpj': '11.222.333/0001-81',
               'epi_responsibility': 'Empresa Terceirizada'}, cid,
    )
    stock_item_id, qr = _stock_item(conn, cid)
    employee = {
        'id': 21, 'company_id': cid, 'name': 'Carlos', 'tipo_vinculo': 'Terceirizado',
        'outsourced_company_id': oc_id, 'service_contract_id': None, 'epi_responsibility_override': '',
    }
    payload = {
        'company_id': cid, 'employee_id': 21, 'epi_id': 30, 'quantity': 1,
        'sector': 'Operações', 'role_name': 'Técnico', 'delivery_date': '2026-07-29',
        'next_replacement_date': '2027-07-29', 'stock_item_id': stock_item_id, 'stock_qr_code': qr,
    }
    delivery_id = create_delivery_service(conn, payload, **_delivery_kwargs(employee))
    row = conn.execute('SELECT * FROM deliveries WHERE id = ?', (delivery_id,)).fetchone()
    assert row['snapshot_tipo_vinculo'] == 'Terceirizado'
    assert row['snapshot_outsourced_company_name'] == 'Terceirizada X'
    assert '11.222.333' in row['snapshot_outsourced_company_cnpj']
    assert row['snapshot_epi_responsibility'] == 'Empresa Terceirizada'
    assert int(row['snapshot_contracting_company_id']) == cid


def test_delivery_snapshot_survives_later_company_edit():
    # A prova final: editar a empresa terceirizada DEPOIS da entrega não
    # reescreve o histórico já gravado.
    conn, cid = _delivery_conn()
    oc_id = create_outsourced_company(
        conn, {'legal_name': 'Terceirizada Original', 'epi_responsibility': 'Empresa Terceirizada'}, cid,
    )
    stock_item_id, qr = _stock_item(conn, cid)
    employee = {
        'id': 21, 'company_id': cid, 'name': 'Carlos', 'tipo_vinculo': 'Terceirizado',
        'outsourced_company_id': oc_id, 'service_contract_id': None, 'epi_responsibility_override': '',
    }
    payload = {
        'company_id': cid, 'employee_id': 21, 'epi_id': 30, 'quantity': 1,
        'sector': 'Operações', 'role_name': 'Técnico', 'delivery_date': '2026-07-29',
        'next_replacement_date': '2027-07-29', 'stock_item_id': stock_item_id, 'stock_qr_code': qr,
    }
    delivery_id = create_delivery_service(conn, payload, **_delivery_kwargs(employee))

    update_outsourced_company(
        conn, oc_id, {'legal_name': 'Terceirizada Renomeada', 'epi_responsibility': 'Empresa Contratante'}, cid,
    )

    row = conn.execute('SELECT * FROM deliveries WHERE id = ?', (delivery_id,)).fetchone()
    assert row['snapshot_outsourced_company_name'] == 'Terceirizada Original'
    assert row['snapshot_epi_responsibility'] == 'Empresa Terceirizada'
