"""PR 9 (ADR-0002): regressão de ponta a ponta do Cadastro Simplificado de
Terceirizados e Prestadores.

Os testes de PR1/PR3/PR4/PR5/PR6 cobrem cada peça isoladamente (schema,
validação, snapshot, auditoria, ressarcimento, sugestão de migração). Este
arquivo verifica que as peças funcionam **juntas**, na mesma jornada que um
Administrador Geral realmente percorre: cadastrar a empresa terceirizada em
modo Simplificado, vincular um colaborador, registrar uma entrega (o
snapshot precisa congelar o vínculo do momento), atualizar a responsabilidade
pelo EPI (o snapshot já gravado não pode mudar, mas a auditoria precisa
refletir a mudança), registrar um ressarcimento, receber a sugestão de
migração após o prazo configurado e, por fim, promover ao Cadastro Padrão —
sempre com isolamento multi-tenant intacto.
"""

import sqlite3
from datetime import datetime, timedelta, timezone

import pytest

from core.audit import register_company_audit
from core.schema import (
    ensure_delivery_handover_columns,
    ensure_delivery_outsourced_snapshot_columns,
    ensure_delivery_signature_columns,
    ensure_epi_reimbursements,
    ensure_legal_entities,
    ensure_outsourced_companies,
    ensure_outsourced_company_unit_links,
)
from modules.deliveries.service import create_delivery_service
from modules.outsourced_companies.service import (
    create_outsourced_company,
    create_reimbursement,
    fetch_migration_suggestions,
    fetch_outsourced_companies,
    fetch_reimbursements,
    get_outsourced_company_by_id,
    promote_outsourced_company,
    update_outsourced_company,
    update_reimbursement_status,
)

UTC = timezone.utc


def _dict_factory(cursor, row):
    return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}


def _conn():
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
        CREATE TABLE company_audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL, actor_user_id INTEGER NOT NULL, actor_name TEXT NOT NULL,
            action_type TEXT NOT NULL, summary TEXT NOT NULL, details_json TEXT NOT NULL DEFAULT '[]',
            created_at TEXT NOT NULL
        );
        """
    )
    ensure_delivery_signature_columns(conn)
    ensure_delivery_handover_columns(conn)
    ensure_delivery_outsourced_snapshot_columns(conn)
    ensure_legal_entities(conn)
    ensure_outsourced_companies(conn)
    ensure_outsourced_company_unit_links(conn)
    ensure_epi_reimbursements(conn)
    conn.commit()
    return conn


def _seed_company(conn, name='ACME'):
    cur = conn.execute("INSERT INTO companies (name, legal_name, cnpj) VALUES (?, ?, '')", (name, name))
    conn.commit()
    return int(cur.lastrowid)


def _seed_user(conn, company_id, role='general_admin'):
    cur = conn.execute(
        "INSERT INTO users (username, company_id, role) VALUES ('admin', ?, ?)", (company_id, role),
    )
    conn.commit()
    return int(cur.lastrowid)


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


def test_outsourced_company_full_lifecycle_journey():
    conn = _conn()
    cid = _seed_company(conn)
    actor = {'id': _seed_user(conn, cid), 'full_name': 'Admin Geral'}

    # 1) Cadastro Simplificado: sem CNPJ, nasce como 'simplified'.
    oc_id = create_outsourced_company(
        conn,
        {'legal_name': 'Terceirizada X', 'company_kind': 'outsourced',
         'epi_responsibility': 'Empresa Terceirizada'},
        cid, actor_user_id=actor['id'],
    )
    company = get_outsourced_company_by_id(conn, oc_id)
    assert company['registration_mode'] == 'simplified'
    assert company['cnpj'] == ''

    # 2) Promover sem CNPJ é recusado — o Simplificado existe justamente para
    # o caso emergencial em que o CNPJ ainda não é conhecido.
    with pytest.raises(ValueError, match='CNPJ'):
        promote_outsourced_company(conn, oc_id, cid)

    # 3) Colaborador terceirizado vinculado à empresa; entrega registrada —
    # o snapshot precisa congelar nome/CNPJ/responsabilidade do momento.
    employee = {
        'id': 21, 'company_id': cid, 'name': 'Carlos', 'tipo_vinculo': 'Terceirizado',
        'outsourced_company_id': oc_id, 'service_contract_id': None, 'epi_responsibility_override': '',
    }
    stock_item_id, qr = _stock_item(conn, cid)
    delivery_payload = {
        'company_id': cid, 'employee_id': 21, 'epi_id': 30, 'quantity': 1,
        'sector': 'Operações', 'role_name': 'Técnico', 'delivery_date': '2026-07-29',
        'next_replacement_date': '2027-07-29', 'stock_item_id': stock_item_id, 'stock_qr_code': qr,
    }
    delivery_id = create_delivery_service(conn, delivery_payload, **_delivery_kwargs(employee))
    delivery = conn.execute('SELECT * FROM deliveries WHERE id = ?', (delivery_id,)).fetchone()
    assert delivery['snapshot_outsourced_company_name'] == 'Terceirizada X'
    assert delivery['snapshot_epi_responsibility'] == 'Empresa Terceirizada'

    # 4) Responsabilidade pelo EPI muda depois da entrega — a auditoria (PR5)
    # reflete a mudança viva, mas o snapshot já gravado (PR4) não se altera.
    update_outsourced_company(
        conn, oc_id,
        {'legal_name': 'Terceirizada X', 'epi_responsibility': 'Empresa Contratante'},
        cid,
    )
    register_company_audit(
        conn, cid, actor, 'outsourced_company_updated',
        'Empresa terceirizada atualizada: Terceirizada X.',
        [{'field': 'epi_responsibility', 'before': 'Empresa Terceirizada', 'after': 'Empresa Contratante'}],
    )
    register_company_audit(
        conn, cid, actor, 'epi_responsibility_changed',
        'Responsabilidade pelo fornecimento de EPI de Terceirizada X alterada: '
        'Empresa Terceirizada → Empresa Contratante.',
        [{'field': 'epi_responsibility', 'before': 'Empresa Terceirizada', 'after': 'Empresa Contratante'}],
    )
    audit_types = {
        row['action_type']
        for row in conn.execute('SELECT action_type FROM company_audit_logs WHERE company_id = ?', (cid,)).fetchall()
    }
    assert {'outsourced_company_updated', 'epi_responsibility_changed'} <= audit_types

    delivery_after_update = conn.execute('SELECT * FROM deliveries WHERE id = ?', (delivery_id,)).fetchone()
    assert delivery_after_update['snapshot_epi_responsibility'] == 'Empresa Terceirizada', (
        'histórico da entrega não pode mudar quando o cadastro vivo da empresa muda depois'
    )

    # 5) Ressarcimento (PR6): registro de apoio ligado à entrega real.
    reimb_id = create_reimbursement(
        conn,
        {'delivery_id': delivery_id, 'outsourced_company_id': oc_id, 'unit_cost': 45.5, 'quantity': 2,
         'reason': 'EPI fornecido pela terceirizada, cobrança pendente'},
        cid, actor_user_id=actor['id'],
    )
    reimbursements = fetch_reimbursements(conn, cid)
    assert len(reimbursements) == 1
    assert reimbursements[0]['id'] == reimb_id
    assert reimbursements[0]['status'] == 'Pendente de Análise'
    assert reimbursements[0]['total_value'] == pytest.approx(91.0)
    update_reimbursement_status(conn, reimb_id, cid, 'Ressarcida')
    assert fetch_reimbursements(conn, cid)[0]['status'] == 'Ressarcida'

    # 6) Sugestão de migração (PR6): só aparece depois do limiar configurado
    # (default 30 dias) — simula a empresa "envelhecendo" no Simplificado.
    old_created_at = (datetime.now(UTC) - timedelta(days=45)).isoformat()
    conn.execute('UPDATE outsourced_companies SET created_at = ? WHERE id = ?', (old_created_at, oc_id))
    conn.commit()
    suggestions = fetch_migration_suggestions(conn, cid)
    assert len(suggestions) == 1
    assert suggestions[0]['outsourced_company_id'] == oc_id
    assert suggestions[0]['age_days'] >= 30

    # 7) CNPJ chega, e a promoção ao Cadastro Padrão passa a funcionar — a
    # mesma linha é atualizada, sem duplicar o cadastro nem perder o histórico.
    update_outsourced_company(
        conn, oc_id,
        {'legal_name': 'Terceirizada X', 'cnpj': '11.222.333/0001-81', 'epi_responsibility': 'Empresa Contratante'},
        cid,
    )
    promote_outsourced_company(conn, oc_id, cid)
    promoted = get_outsourced_company_by_id(conn, oc_id)
    assert promoted['id'] == oc_id
    assert promoted['registration_mode'] == 'standard'
    assert promoted['registration_status'] == 'complete'
    assert promoted['promoted_at']

    # Promovida, a empresa some da lista de sugestão de migração.
    assert fetch_migration_suggestions(conn, cid) == []

    # A entrega já registrada continua intocada mesmo após a promoção.
    delivery_after_promotion = conn.execute('SELECT * FROM deliveries WHERE id = ?', (delivery_id,)).fetchone()
    assert delivery_after_promotion['snapshot_epi_responsibility'] == 'Empresa Terceirizada'


def test_outsourced_companies_cnpj_reuse_and_data_isolation_across_tenants():
    """Mesmo CNPJ em tenants diferentes não colide, e nenhum dado de um
    tenant (empresa, ressarcimento) vaza para o outro — checagem final de
    isolamento multi-tenant, condição vinculante do ADR-0002."""
    conn = _conn()
    company_a = _seed_company(conn, 'Tenant A')
    company_b = _seed_company(conn, 'Tenant B')
    shared_cnpj = '11.222.333/0001-81'

    oc_a = create_outsourced_company(
        conn, {'legal_name': 'Fornecedora Compartilhada', 'cnpj': shared_cnpj}, company_a,
    )
    oc_b = create_outsourced_company(
        conn, {'legal_name': 'Fornecedora Compartilhada', 'cnpj': shared_cnpj}, company_b,
    )
    assert oc_a != oc_b

    companies_a = fetch_outsourced_companies(conn, company_a)
    companies_b = fetch_outsourced_companies(conn, company_b)
    assert {c['id'] for c in companies_a['linked']} == {oc_a}
    assert {c['id'] for c in companies_b['linked']} == {oc_b}

    # Ressarcimento de A não aparece na lista de B, mesmo consultando sem
    # nenhum filtro de outsourced_company_id.
    actor_a = {'id': _seed_user(conn, company_a), 'full_name': 'Admin A'}
    employee_a = {
        'id': 1, 'company_id': company_a, 'name': 'Ana', 'tipo_vinculo': 'Terceirizado',
        'outsourced_company_id': oc_a, 'service_contract_id': None, 'epi_responsibility_override': '',
    }
    stock_item_id, qr = _stock_item(conn, company_a)
    delivery_payload = {
        'company_id': company_a, 'employee_id': 1, 'epi_id': 30, 'quantity': 1,
        'sector': 'Operações', 'role_name': 'Técnica', 'delivery_date': '2026-07-29',
        'next_replacement_date': '2027-07-29', 'stock_item_id': stock_item_id, 'stock_qr_code': qr,
    }
    delivery_id = create_delivery_service(conn, delivery_payload, **_delivery_kwargs(employee_a))
    create_reimbursement(
        conn, {'delivery_id': delivery_id, 'outsourced_company_id': oc_a}, company_a,
        actor_user_id=actor_a['id'],
    )
    assert len(fetch_reimbursements(conn, company_a)) == 1
    assert fetch_reimbursements(conn, company_b) == []
