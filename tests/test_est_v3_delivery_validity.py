"""EST-V3 — validade física por lote na entrega/FEFO e no desbloqueio.

G02: a entrega passa a reprovar a peça pela validade FÍSICA do lote
(epi_stock_items.physical_expiry_date), não só pela validade do catálogo —
um lote vencido é barrado mesmo com o catálogo do EPI em dia; peça sem
validade física cai no catálogo (compatibilidade).
G03: FEFO ordena pela validade física quando conhecida.
G04: desbloquear uma peça fisicamente vencida é recusado.
"""

import sqlite3
from tests.stock_physical_fixtures import ensure_test_physical_schema
from datetime import date, timedelta

import pytest

from core.schema import ensure_stock_lifecycle_model
from modules.stock.service import (
    effective_delivery_expiry,
    fetch_available_stock_items,
    item_physical_expiry,
    set_stock_item_status,
)

PAST = (date.today() - timedelta(days=10)).isoformat()
SOON = (date.today() + timedelta(days=5)).isoformat()
FUTURE = (date.today() + timedelta(days=365)).isoformat()


def _conn():
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        CREATE TABLE epis (id INTEGER PRIMARY KEY, name TEXT, epi_validity_date TEXT DEFAULT '', unit_measure TEXT DEFAULT 'un');
        CREATE TABLE epi_stock_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT, company_id INTEGER, unit_id INTEGER, epi_id INTEGER,
            glove_size TEXT DEFAULT 'N/A', size TEXT DEFAULT 'N/A', uniform_size TEXT DEFAULT 'N/A',
            qr_code_value TEXT DEFAULT '', status TEXT DEFAULT 'in_stock', lot_code TEXT DEFAULT '',
            manufacture_date TEXT DEFAULT '', created_at TEXT DEFAULT '', updated_at TEXT DEFAULT ''
        );
        CREATE TABLE stock_movements (
            id INTEGER PRIMARY KEY AUTOINCREMENT, company_id INTEGER, unit_id INTEGER, epi_id INTEGER,
            movement_type TEXT, quantity INTEGER, previous_stock INTEGER, new_stock INTEGER,
            source_type TEXT, source_id INTEGER, notes TEXT, actor_user_id INTEGER, actor_name TEXT,
            created_at TEXT, glove_size TEXT, size TEXT, uniform_size TEXT
        );
        INSERT INTO epis (id, name, epi_validity_date) VALUES (7, 'Capacete', '');
        """
    )
    ensure_stock_lifecycle_model(conn)
    conn.commit()
    ensure_test_physical_schema(conn)
    conn.execute('CREATE TABLE IF NOT EXISTS unit_epi_stock(id INTEGER PRIMARY KEY, company_id INTEGER, unit_id INTEGER, epi_id INTEGER, quantity INTEGER, updated_at TEXT)')
    conn.execute('INSERT INTO unit_epi_stock(company_id,unit_id,epi_id,quantity) VALUES(1,2,7,20)')
    conn.commit()
    return conn


def _add_item(conn, iid, status='in_stock', physical_expiry='', mfg='', qr=None, epi_validity=None, epi_id=7):
    if epi_validity is not None:
        conn.execute('UPDATE epis SET epi_validity_date = ? WHERE id = ?', (epi_validity, epi_id))
    conn.execute(
        'INSERT INTO epi_stock_items (id, company_id, unit_id, epi_id, qr_code_value, status, '
        'manufacture_date, physical_expiry_date) VALUES (?, 1, 2, ?, ?, ?, ?, ?)',
        (iid, epi_id, qr or f'QR-{iid}', status, mfg, physical_expiry),
    )
    conn.commit()
    return conn.execute('SELECT * FROM epi_stock_items WHERE id = ?', (iid,)).fetchone()


# ── helpers de validade efetiva (G02) ────────────────────────────────────────

def test_effective_expiry_prefers_physical_lot_over_catalog():
    conn = _conn()
    _add_item(conn, 10, physical_expiry=PAST, epi_validity=FUTURE)
    # catálogo em dia, mas o LOTE está vencido → efetiva = validade física (vencida)
    assert effective_delivery_expiry(conn, 10, FUTURE) == PAST
    assert item_physical_expiry(conn, 10) == PAST


def test_effective_expiry_never_falls_back_to_catalog_when_physical_unknown():
    conn = _conn()
    _add_item(conn, 11, physical_expiry='', epi_validity=FUTURE)
    assert item_physical_expiry(conn, 11) == ''
    assert effective_delivery_expiry(conn, 11, FUTURE) == ''


def test_item_physical_expiry_degrades_without_column():
    # schema antigo (sem a coluna) → '' e o chamador usa o catálogo
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.executescript(
        "CREATE TABLE epi_stock_items (id INTEGER PRIMARY KEY, company_id INTEGER, status TEXT DEFAULT 'in_stock');"
        "INSERT INTO epi_stock_items (id, company_id) VALUES (99, 1);"
    )
    assert item_physical_expiry(conn, 99) == ''
    assert effective_delivery_expiry(conn, 99, FUTURE) == ''


# ── FEFO por validade física (G03) ────────────────────────────────────────────

def test_fefo_orders_by_physical_expiry_first():
    conn = _conn()
    # inseridos fora de ordem de validade física
    _add_item(conn, 10, physical_expiry=FUTURE, mfg='2020-01-01')   # vence por último
    _add_item(conn, 11, physical_expiry=PAST, mfg='2026-01-01')     # vence PRIMEIRO
    _add_item(conn, 12, physical_expiry=SOON, mfg='2019-01-01')     # meio
    _add_item(conn, 13, physical_expiry='', mfg='2018-01-01')       # sem validade física → fallback (fim)
    ids = [r['id'] for r in fetch_available_stock_items(conn, 1, 2, 7)]
    # PAST < SOON < FUTURE ; item sem validade física vai ao final
    assert ids == [12, 10], ids


# ── desbloqueio recusa vencido (G04) ──────────────────────────────────────────

def _item(conn, iid):
    return conn.execute('SELECT * FROM epi_stock_items WHERE id = ?', (iid,)).fetchone()


def test_unblock_refused_when_lot_physically_expired():
    conn = _conn()
    _add_item(conn, 10, status='blocked_analysis', physical_expiry=PAST, epi_validity=FUTURE)
    with pytest.raises(ValueError, match='vencido'):
        set_stock_item_status(conn, _item(conn, 10), 'in_stock', 'liberar', 3, 'Admin', 'now')
    # o item permanece bloqueado (o desbloqueio foi recusado antes do UPDATE)
    assert _item(conn, 10)['status'] == 'blocked_analysis'


def test_unblock_unknown_remains_operationally_ineligible():
    conn = _conn()
    _add_item(conn, 11, status='blocked_discard', physical_expiry='', epi_validity=PAST)
    set_stock_item_status(conn, _item(conn, 11), 'in_stock', 'reinspeção administrativa', 3, 'Admin', 'now')
    assert fetch_available_stock_items(conn, 1, 2, 7) == []


def test_unblock_allowed_for_administrative_block_not_expired():
    conn = _conn()
    _add_item(conn, 12, status='blocked_rejected', physical_expiry=FUTURE, epi_validity=FUTURE)
    out = set_stock_item_status(conn, _item(conn, 12), 'in_stock', 'reinspecionado', 3, 'Admin', 'now')
    assert out == 'in_stock'
    assert _item(conn, 12)['status'] == 'in_stock'


def test_unblock_allowed_when_validity_unknown():
    conn = _conn()
    _add_item(conn, 13, status='blocked_analysis', physical_expiry='', epi_validity='')
    out = set_stock_item_status(conn, _item(conn, 13), 'in_stock', '', 3, 'Admin', 'now')
    assert out == 'in_stock'


def test_blocking_still_works_and_is_not_gated_by_validity():
    # bloquear (não desbloquear) um item vencido deve continuar funcionando
    conn = _conn()
    _add_item(conn, 14, status='in_stock', physical_expiry=PAST)
    out = set_stock_item_status(conn, _item(conn, 14), 'blocked_expired', 'vencido', 3, 'Admin', 'now')
    assert out == 'blocked_expired'
