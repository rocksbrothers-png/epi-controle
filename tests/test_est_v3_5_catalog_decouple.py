"""EST-V3.5 (G02) — conformidade/validade por LOTE físico, não por catálogo.

O recebimento deixa de escrever a validade no catálogo (``epis.epi_validity_date``
vira só default de cadastro). Alertas, painel e relatórios passam a usar a
validade FÍSICA da peça (``epi_stock_items.physical_expiry_date``), com o
catálogo apenas como fallback para peças sem validade própria. Aqui provamos a
fonte por lote nas funções de relatório/painel e no mapa agregado por EPI.
"""

import sqlite3
from datetime import date

from core.schema import ensure_stock_lifecycle_model
from modules.stock.service import (
    compute_stock_compliance,
    epi_physical_validity_map,
    fetch_validity_overview,
)

TODAY = date(2026, 7, 18)
PAST = '2026-01-01'    # vencido relativo a TODAY
FUTURE = '2027-01-01'  # válido


def _conn():
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        CREATE TABLE companies (id INTEGER PRIMARY KEY, name TEXT);
        CREATE TABLE epis (id INTEGER PRIMARY KEY, name TEXT, ca TEXT DEFAULT '',
            manufacturer TEXT DEFAULT '', ca_expiry TEXT DEFAULT '',
            epi_validity_date TEXT DEFAULT '', unit_measure TEXT DEFAULT 'un');
        CREATE TABLE units (id INTEGER PRIMARY KEY, name TEXT);
        CREATE TABLE epi_stock_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT, company_id INTEGER, unit_id INTEGER, epi_id INTEGER,
            lot_code TEXT DEFAULT '', manufacture_date TEXT DEFAULT '', status TEXT DEFAULT 'in_stock',
            qr_code_value TEXT DEFAULT ''
        );
        INSERT INTO companies (id, name) VALUES (1, 'Acme');
        INSERT INTO units (id, name) VALUES (2, 'Base');
        -- EPI 7: catálogo EM DIA (FUTURE)
        INSERT INTO epis (id, name, ca_expiry, epi_validity_date) VALUES (7, 'Capacete', '2027-01-01', '2027-01-01');
        -- EPI 8: catálogo VENCIDO (PAST)
        INSERT INTO epis (id, name, ca_expiry, epi_validity_date) VALUES (8, 'Luva', '2027-01-01', '2026-01-01');
        """
    )
    ensure_stock_lifecycle_model(conn)  # adiciona physical_expiry_date etc. (EST-V2)
    conn.commit()
    return conn


def _add(conn, epi_id, physical, status='in_stock', qr=None):
    iid = conn.execute(
        'INSERT INTO epi_stock_items (company_id, unit_id, epi_id, status, qr_code_value, physical_expiry_date) '
        'VALUES (1,2,?,?,?,?)',
        (epi_id, status, qr or f'Q{epi_id}-{physical or "none"}-{status}', physical),
    ).lastrowid
    conn.commit()
    return iid


# ── mapa agregado por EPI (para alertas/dashboard por EPI) ────────────────────

def test_map_returns_min_in_stock_physical_excluding_blocked_and_unknown():
    conn = _conn()
    _add(conn, 7, FUTURE)                               # válido
    _add(conn, 7, PAST)                                 # vencido in_stock → é o MENOR
    _add(conn, 7, '2025-01-01', status='blocked_expired')  # bloqueado → ignorado (mais antigo)
    _add(conn, 7, '')                                   # sem validade física → ignorado
    m = epi_physical_validity_map(conn, 1, 2)
    assert m.get(7) == PAST  # menor entre as peças in_stock COM validade física


def test_map_empty_without_physical_column():
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.execute("CREATE TABLE epi_stock_items (id INTEGER PRIMARY KEY, company_id INTEGER, epi_id INTEGER, status TEXT DEFAULT 'in_stock')")
    conn.execute("INSERT INTO epi_stock_items (id, company_id, epi_id) VALUES (1, 1, 7)")
    conn.commit()
    assert epi_physical_validity_map(conn, 1) == {}


# ── compute_stock_compliance (dashboard + "Validade e Bloqueios") ─────────────

def test_compliance_flags_expired_lot_even_with_catalog_valid():
    """G02: catálogo em dia (EPI 7 = FUTURE), peça física vencida → product_expired."""
    conn = _conn()
    _add(conn, 7, PAST)
    r = compute_stock_compliance(conn, 1, today=TODAY)
    assert r['summary']['product_expired'] == 1
    rec = r['categories']['product_expired'][0]
    assert rec['product_validity'] == PAST       # efetiva (física) usada na classificação
    assert rec['epi_validity_date'] == FUTURE     # catálogo preservado como referência


def test_compliance_valid_lot_under_expired_catalog_not_flagged():
    """Reverso: catálogo vencido (EPI 8 = PAST), peça física válida → NÃO conta."""
    conn = _conn()
    _add(conn, 8, FUTURE)
    r = compute_stock_compliance(conn, 1, today=TODAY)
    assert r['summary']['product_expired'] == 0


def test_compliance_falls_back_to_catalog_when_physical_unknown():
    """Peça sem validade física + catálogo vencido (EPI 8) → fallback → product_expired."""
    conn = _conn()
    _add(conn, 8, '')
    r = compute_stock_compliance(conn, 1, today=TODAY)
    assert r['summary']['product_expired'] == 1


def test_compliance_blocked_lot_excluded_from_validity():
    conn = _conn()
    _add(conn, 7, PAST, status='blocked_expired')
    r = compute_stock_compliance(conn, 1, today=TODAY)
    assert r['summary']['product_expired'] == 0
    assert r['summary']['admin_blocked'] == 1


# ── fetch_validity_overview (painel Gestão de Validade) ───────────────────────

def test_overview_counts_expired_lot_with_catalog_valid():
    conn = _conn()
    _add(conn, 7, PAST)     # catálogo FUTURE, lote vencido
    _add(conn, 7, FUTURE)   # lote válido
    ov = fetch_validity_overview(conn, 1, today=TODAY)
    assert ov['summary']['product_expired'] == 1   # só a peça física vencida


def test_overview_valid_lot_under_expired_catalog_not_at_risk():
    conn = _conn()
    _add(conn, 8, FUTURE)   # catálogo PAST, lote válido
    ov = fetch_validity_overview(conn, 1, today=TODAY)
    assert ov['summary']['product_expired'] == 0
