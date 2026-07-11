"""Fase 4d (HSE) — Painel de Gestão de Validade.

fetch_validity_overview consolida o estoque DISPONÍVEL por status de validade:
produto (data do fabricante, rege uso/entrega/FEFO) e CA (rege compra). Agrega
contagens por empresa/unidade/fabricante/lote, dias restantes e valor financeiro
do estoque em risco de perda (preço unitário de referência de pedidos de compra).
Somente leitura — não altera saldo nem regra de negócio.
"""

import sqlite3
from datetime import date, timedelta

from modules.stock.service import fetch_validity_overview


def _conn():
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        CREATE TABLE epis (
            id INTEGER PRIMARY KEY, name TEXT, manufacturer TEXT DEFAULT '',
            ca TEXT DEFAULT '', ca_expiry TEXT DEFAULT '', epi_validity_date TEXT DEFAULT '',
            unit_measure TEXT DEFAULT 'un'
        );
        CREATE TABLE units (id INTEGER PRIMARY KEY, name TEXT);
        CREATE TABLE companies (id INTEGER PRIMARY KEY, name TEXT);
        CREATE TABLE epi_stock_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT, company_id INTEGER, unit_id INTEGER, epi_id INTEGER,
            status TEXT DEFAULT 'in_stock', lot_code TEXT DEFAULT '', manufacture_date TEXT DEFAULT ''
        );
        CREATE TABLE purchase_order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT, company_id INTEGER, epi_id INTEGER,
            unit_price REAL DEFAULT 0, created_at TEXT DEFAULT ''
        );
        INSERT INTO companies (id, name) VALUES (1, 'ACME');
        INSERT INTO units (id, name) VALUES (2, 'Base A'), (3, 'Base B');
        """
    )
    conn.commit()
    return conn


def _iso(days_from_today):
    return (date.today() + timedelta(days=days_from_today)).isoformat()


def _seed(conn):
    # EPI 7: produto vencido (validade -5), fabricante Alpha, preço 100
    # EPI 8: produto próximo (validade +10), fabricante Beta, preço 50
    # EPI 9: CA vencido (ca -3, validade folgada), fabricante Alpha, preço 20
    # EPI 10: tudo em dia (não entra em risco)
    conn.executescript(
        f"""
        INSERT INTO epis (id, name, manufacturer, ca, ca_expiry, epi_validity_date) VALUES
          (7, 'Luva', 'Alpha', 'CA7', '{_iso(400)}', '{_iso(-5)}'),
          (8, 'Bota', 'Beta',  'CA8', '{_iso(400)}', '{_iso(10)}'),
          (9, 'Óculos', 'Alpha','CA9', '{_iso(-3)}', '{_iso(400)}'),
          (10, 'Capacete','Beta','CA10','{_iso(400)}', '{_iso(400)}');
        INSERT INTO epi_stock_items (company_id, unit_id, epi_id, status, lot_code, manufacture_date) VALUES
          (1, 2, 7, 'in_stock', 'L1', '{_iso(-370)}'),
          (1, 2, 7, 'in_stock', 'L1', '{_iso(-370)}'),
          (1, 3, 8, 'in_stock', 'L2', '{_iso(-60)}'),
          (1, 2, 9, 'in_stock', 'L3', '{_iso(-30)}'),
          (1, 2, 10, 'in_stock', 'L4', '{_iso(-10)}'),
          (1, 2, 7, 'blocked_discard', 'L1', '{_iso(-370)}');
        INSERT INTO purchase_order_items (company_id, epi_id, unit_price, created_at) VALUES
          (1, 7, 80, '2026-01-01T00:00:00'),
          (1, 7, 100, '2026-06-01T00:00:00'),
          (1, 8, 50, '2026-05-01T00:00:00'),
          (1, 9, 20, '2026-05-01T00:00:00');
        """
    )
    conn.commit()


def test_summary_counts_by_validity_status():
    conn = _conn()
    _seed(conn)
    ov = fetch_validity_overview(conn, 1)
    s = ov['summary']
    assert s['product_expired'] == 2      # 2 itens do EPI 7
    assert s['product_expiring'] == 1     # EPI 8
    assert s['ca_expired'] == 1           # EPI 9
    assert s['at_risk_total'] == 4        # 2 + 1 + 1 (EPI 10 fora, bloqueado fora)


def test_value_at_risk_uses_latest_po_price():
    conn = _conn()
    _seed(conn)
    ov = fetch_validity_overview(conn, 1)
    # 2×100 (EPI 7, último preço) + 50 (EPI 8) + 20 (EPI 9) = 270
    assert ov['summary']['value_at_risk'] == 270.0


def test_blocked_items_excluded():
    conn = _conn()
    _seed(conn)
    ov = fetch_validity_overview(conn, 1)
    # o item bloqueado do EPI 7 não conta
    assert ov['summary']['product_expired'] == 2


def test_breakdowns_by_manufacturer_unit_lot():
    conn = _conn()
    _seed(conn)
    ov = fetch_validity_overview(conn, 1)
    manu = {e['label']: e['count'] for e in ov['by_manufacturer']}
    assert manu['Alpha'] == 3   # 2×EPI7 + 1×EPI9
    assert manu['Beta'] == 1    # EPI8
    units = {e['label']: e['count'] for e in ov['by_unit']}
    assert units['Base A'] == 3
    assert units['Base B'] == 1
    lots = {e['label']: e['count'] for e in ov['by_lot']}
    assert lots['L1'] == 2


def test_soonest_sorted_by_days_remaining():
    conn = _conn()
    _seed(conn)
    ov = fetch_validity_overview(conn, 1)
    days = [it['days_remaining'] for it in ov['soonest']]
    assert days == sorted(days)
    # o mais atrasado (produto vencido -5) vem antes do CA vencido -3
    assert ov['soonest'][0]['days_remaining'] <= ov['soonest'][-1]['days_remaining']


def test_unit_filter_scopes_results():
    conn = _conn()
    _seed(conn)
    ov = fetch_validity_overview(conn, 1, unit_id=3)
    assert ov['summary']['at_risk_total'] == 1   # só EPI 8 na Base B
    assert ov['summary']['product_expiring'] == 1
