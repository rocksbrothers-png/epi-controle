"""Regras de validade de EPI / CA — base legal NT 146/2015/CGNOR/DSST/SIT.

Cobre:
- helpers de validade (modules.epis.validity);
- alerta de validade do fabricante próxima/vencida (PEPS) em compute_alerts;
- bloqueio de entrega quando a validade do fabricante está vencida (CA vencido
  NÃO bloqueia a entrega);
- bloqueio de compra quando o CA do EPI está vencido;
- filtros do Relatório de Movimentações de Estoque (CA vencido / validade do
  fabricante próxima / vencida).
"""

import sqlite3
from datetime import date, timedelta

import pytest


TODAY = date.today()
PAST = (TODAY - timedelta(days=10)).isoformat()
SOON = (TODAY + timedelta(days=5)).isoformat()
FUTURE = (TODAY + timedelta(days=365)).isoformat()


# ── helpers de validade ───────────────────────────────────────────────────────

def test_validity_helpers():
    from modules.epis.validity import (
        parse_iso_date, days_until, is_expired, is_expiring_soon,
    )
    assert parse_iso_date('') is None
    assert parse_iso_date('lixo') is None
    assert parse_iso_date('2026-01-15') == date(2026, 1, 15)
    assert parse_iso_date('2026-01-15T10:00:00+00:00') == date(2026, 1, 15)

    assert days_until('') is None
    assert is_expired('') is False          # ausência de data nunca bloqueia
    assert is_expired(PAST) is True
    assert is_expired(FUTURE) is False
    assert is_expiring_soon(SOON) is True
    assert is_expiring_soon(PAST) is False  # já vencida não é "próxima"
    assert is_expiring_soon(FUTURE) is False


# ── alertas de validade do fabricante (PEPS) ──────────────────────────────────

def _compute(epis):
    from modules.alerts.service import compute_alerts
    return compute_alerts(
        None, {'role': 'admin', 'company_id': 1},
        fetch_low_stock_items=lambda conn, act: [],
        actor_operational_unit_id=lambda conn, act: None,
        fetch_epis=lambda conn, act, unit: epis,
    )


def _epi(**over):
    base = {
        'id': 1, 'company_id': 1, 'unit_id': 7, 'active': 1,
        'name': 'Luva Nitrílica', 'company_name': 'Acme', 'stock': 5,
        'unit_measure': 'par', 'ca_expiry': '', 'epi_validity_date': '',
    }
    base.update(over)
    return base


def test_alert_manufacturer_validity_expired():
    alerts = _compute([_epi(epi_validity_date=PAST)])
    manu = [a for a in alerts if 'Validade do fabricante vencida' in a['title']]
    assert len(manu) == 1
    assert manu[0]['type'] == 'danger'
    assert manu[0]['epi_id'] == 1


def test_alert_manufacturer_validity_expiring_soon():
    alerts = _compute([_epi(epi_validity_date=SOON)])
    manu = [a for a in alerts if 'Validade do fabricante próxima' in a['title']]
    assert len(manu) == 1
    assert 'PEPS' in manu[0]['description']


def test_no_manufacturer_alert_when_valid_or_inactive():
    assert _compute([_epi(epi_validity_date=FUTURE)]) == []
    assert _compute([_epi(active=0, epi_validity_date=PAST)]) == []


# ── bloqueio de entrega: validade do fabricante vencida ───────────────────────

def _delivery_kwargs():
    noop = lambda *a, **k: None
    return dict(
        authorize_action=lambda conn, uid, perm, cid: {'id': 1, 'full_name': 'Op', 'role': 'admin', 'company_id': 1},
        resolve_actor_user_id=lambda: 1,
        get_employee_by_id=lambda conn, eid: {'id': eid, 'company_id': 1, 'name': 'Fulano'},
        get_epi_by_id=lambda conn, pid: _epi_full,
        ensure_resource_company=noop,
        get_employee_current_unit=lambda conn, eid: 7,
        actor_operational_unit_id=lambda conn, act: 7,
        get_unit_stock=lambda *a, **k: {'quantity': 5},
        upsert_unit_stock=noop,
        ensure_ficha_for_delivery=noop,
    )


_epi_full = None


def test_delivery_blocked_when_manufacturer_validity_expired():
    global _epi_full
    from modules.deliveries.service import create_delivery_service
    _epi_full = {'id': 30, 'company_id': 1, 'unit_id': 7, 'epi_validity_date': PAST, 'ca_expiry': FUTURE, 'unit_measure': 'UN'}
    payload = {'company_id': 1, 'employee_id': 21, 'epi_id': 30, 'quantity': 1}
    with pytest.raises(ValueError) as exc:
        create_delivery_service(None, payload, **_delivery_kwargs())
    assert 'validade do fabricante' in str(exc.value).lower()


def test_delivery_not_blocked_by_expired_ca_alone():
    """CA vencido + validade do fabricante OK não pode ser barrado pela regra de validade."""
    global _epi_full
    from modules.deliveries.service import create_delivery_service
    _epi_full = {'id': 30, 'company_id': 1, 'unit_id': 7, 'epi_validity_date': FUTURE, 'ca_expiry': PAST, 'unit_measure': 'UN'}
    payload = {'company_id': 1, 'employee_id': 21, 'epi_id': 30, 'quantity': 1}
    with pytest.raises(ValueError) as exc:
        # vai falhar adiante (falta leitura do código), mas NUNCA pela validade do fabricante
        create_delivery_service(None, payload, **_delivery_kwargs())
    assert 'validade do fabricante' not in str(exc.value).lower()


# ── bloqueio de compra: CA vencido ────────────────────────────────────────────

def test_assert_epi_ca_valid_for_purchase():
    from modules.purchases.service import assert_epi_ca_valid_for_purchase
    assert_epi_ca_valid_for_purchase({'name': 'X', 'ca_expiry': FUTURE})   # ok
    assert_epi_ca_valid_for_purchase({'name': 'X', 'ca_expiry': ''})       # sem data: não bloqueia
    with pytest.raises(ValueError) as exc:
        assert_epi_ca_valid_for_purchase({'name': 'Capacete', 'ca_expiry': PAST})
    assert 'CA' in str(exc.value)


def _purchase_conn():
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        CREATE TABLE epis (id INTEGER PRIMARY KEY, name TEXT, ca TEXT, unit_measure TEXT, ca_expiry TEXT);
        CREATE TABLE purchase_requests (
            id INTEGER PRIMARY KEY, company_id INTEGER, unit_id INTEGER, status TEXT,
            title TEXT, notes TEXT, created_by_user_id INTEGER, created_by_name TEXT,
            created_at TEXT, updated_at TEXT
        );
        CREATE TABLE purchase_request_items (
            id INTEGER PRIMARY KEY, purchase_request_id INTEGER, company_id INTEGER, unit_id INTEGER,
            epi_id INTEGER, epi_name TEXT, ca TEXT, unit_measure TEXT, manufacturer TEXT, supplier TEXT,
            glove_size TEXT, size TEXT, uniform_size TEXT, quantity_requested INTEGER, origin TEXT,
            employee_id INTEGER, employee_name TEXT, employee_sector TEXT, employee_role TEXT,
            epi_request_id INTEGER, status TEXT, notes TEXT, created_at TEXT, updated_at TEXT
        );
        CREATE TABLE epi_requests (id INTEGER PRIMARY KEY, status TEXT, last_updated_at TEXT);
        CREATE TABLE purchase_events (
            id INTEGER PRIMARY KEY, company_id INTEGER, entity_type TEXT, entity_id INTEGER,
            action TEXT, status_from TEXT, status_to TEXT, comment TEXT,
            actor_user_id INTEGER, actor_name TEXT, actor_role TEXT, reason TEXT,
            destination TEXT, ip_address TEXT, created_at TEXT
        );
    """)
    conn.execute("INSERT INTO epis (id, name, ca, unit_measure, ca_expiry) VALUES (100, 'Capacete', 'CA-1', 'UN', ?)", (PAST,))
    conn.execute("INSERT INTO epis (id, name, ca, unit_measure, ca_expiry) VALUES (200, 'Luva', 'CA-2', 'PAR', ?)", (FUTURE,))
    conn.commit()
    return conn


def _fake_get_epi(conn, epi_id):
    row = conn.execute('SELECT * FROM epis WHERE id = ?', (epi_id,)).fetchone()
    return dict(row) if row else None


def test_create_purchase_request_blocks_expired_ca():
    from modules.purchases.service import create_purchase_request
    conn = _purchase_conn()
    actor = {'id': 1, 'full_name': 'Comprador', 'company_id': 1, 'role': 'admin'}
    with pytest.raises(ValueError) as exc:
        create_purchase_request(conn, actor, 7, [{'epi_id': 100, 'quantity_requested': 2}], 'Req', '', '', get_epi_by_id_fn=_fake_get_epi)
    assert 'CA' in str(exc.value)


def test_create_purchase_request_allows_valid_ca():
    from modules.purchases.service import create_purchase_request
    conn = _purchase_conn()
    actor = {'id': 1, 'full_name': 'Comprador', 'company_id': 1, 'role': 'admin'}
    res = create_purchase_request(conn, actor, 7, [{'epi_id': 200, 'quantity_requested': 2}], 'Req', '', '', get_epi_by_id_fn=_fake_get_epi)
    assert res['ok'] is True


# ── filtros do Relatório de Movimentações de Estoque ──────────────────────────

def _movements_conn():
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        CREATE TABLE epis (id INTEGER PRIMARY KEY, name TEXT, ca TEXT, unit_measure TEXT, ca_expiry TEXT, epi_validity_date TEXT);
        CREATE TABLE units (id INTEGER PRIMARY KEY, name TEXT);
        CREATE TABLE stock_movements (
            id INTEGER PRIMARY KEY, company_id INTEGER, unit_id INTEGER, epi_id INTEGER,
            movement_type TEXT, quantity INTEGER, previous_stock INTEGER, new_stock INTEGER,
            source_type TEXT, source_id INTEGER, notes TEXT, actor_name TEXT, created_at TEXT,
            glove_size TEXT, size TEXT, uniform_size TEXT
        );
    """)
    conn.execute("INSERT INTO units (id, name) VALUES (7, 'Base A')")
    # 1: CA vencido + fabricante OK ; 2: fabricante vencido ; 3: fabricante próximo ; 4: tudo OK
    conn.execute("INSERT INTO epis VALUES (1,'CA-Venc','C1','UN',?,?)", (PAST, FUTURE))
    conn.execute("INSERT INTO epis VALUES (2,'Fab-Venc','C2','UN',?,?)", (FUTURE, PAST))
    conn.execute("INSERT INTO epis VALUES (3,'Fab-Prox','C3','UN',?,?)", (FUTURE, SOON))
    conn.execute("INSERT INTO epis VALUES (4,'Tudo-OK','C4','UN',?,?)", (FUTURE, FUTURE))
    for epi_id in (1, 2, 3, 4):
        conn.execute(
            "INSERT INTO stock_movements (company_id, unit_id, epi_id, movement_type, quantity, previous_stock, new_stock, source_type, source_id, notes, actor_name, created_at, glove_size, size, uniform_size) "
            "VALUES (1, 7, ?, 'in', 1, 0, 1, 'manual', NULL, '', 'Op', '2026-06-01T00:00:00+00:00', 'N/A', 'N/A', 'N/A')",
            (epi_id,),
        )
    conn.commit()
    return conn


def _ids(rows):
    return sorted(r['epi_id'] for r in rows)


def test_report_filter_ca_expired():
    from modules.stock.service import fetch_stock_movements
    conn = _movements_conn()
    rows = fetch_stock_movements(conn, ["COALESCE(e.ca_expiry, '') <> '' AND e.ca_expiry < ?"], [TODAY.isoformat()])
    assert _ids(rows) == [1]
    # colunas novas disponíveis para exibição
    assert 'ca_expiry' in dict(rows[0]) and 'epi_validity_date' in dict(rows[0])


def test_report_filter_manufacturer_expired():
    from modules.stock.service import fetch_stock_movements
    conn = _movements_conn()
    rows = fetch_stock_movements(conn, ["COALESCE(e.epi_validity_date, '') <> '' AND e.epi_validity_date < ?"], [TODAY.isoformat()])
    assert _ids(rows) == [2]


def test_report_filter_manufacturer_expiring_soon():
    from modules.stock.service import fetch_stock_movements
    conn = _movements_conn()
    threshold = (TODAY + timedelta(days=30)).isoformat()
    rows = fetch_stock_movements(
        conn,
        ["COALESCE(e.epi_validity_date, '') <> '' AND e.epi_validity_date >= ? AND e.epi_validity_date <= ?"],
        [TODAY.isoformat(), threshold],
    )
    assert _ids(rows) == [3]
