"""Item 2 da auditoria — fonte ÚNICA de conformidade de estoque.

O Dashboard e a tela "Validade e Bloqueios" devem ler daqui: o total do card é
o mesmo total da tela e cada categoria traz os registros calculados (deep-link).
Base única: itens de estoque (não o catálogo de EPIs), com CA vencido, validade
física, fabricação, lote e bloqueio administrativo separados.
"""

import sqlite3

from modules.stock.service import compute_stock_compliance

TODAY = __import__('datetime').date(2026, 7, 18)


def _conn():
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        CREATE TABLE epis (id INTEGER PRIMARY KEY, name TEXT, ca TEXT DEFAULT '',
            ca_expiry TEXT DEFAULT '', epi_validity_date TEXT DEFAULT '');
        CREATE TABLE units (id INTEGER PRIMARY KEY, name TEXT);
        CREATE TABLE epi_stock_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT, company_id INTEGER, unit_id INTEGER, epi_id INTEGER,
            lot_code TEXT DEFAULT '', manufacture_date TEXT DEFAULT '', status TEXT DEFAULT 'in_stock',
            qr_code_value TEXT DEFAULT ''
        );
        INSERT INTO units (id, name) VALUES (2, 'Base');
        -- EPI com CA vencido e validade física vencida
        INSERT INTO epis (id, name, ca, ca_expiry, epi_validity_date) VALUES (7, 'Capacete', '111', '2026-01-01', '2026-02-01');
        -- EPI conforme
        INSERT INTO epis (id, name, ca, ca_expiry, epi_validity_date) VALUES (8, 'Luva', '222', '2027-01-01', '2027-01-01');
        """
    )
    conn.commit()
    return conn


def test_ca_expired_counts_available_stock_items_not_catalog():
    conn = _conn()
    # 2 itens disponíveis do EPI com CA vencido + 1 item entregue (não conta)
    conn.executemany(
        "INSERT INTO epi_stock_items (company_id, unit_id, epi_id, lot_code, manufacture_date, status, qr_code_value) VALUES (1,2,7,'L1','2025-01-01',?,?)",
        [('in_stock', 'Q1'), ('available', 'Q2'), ('delivered', 'Q3')],
    )
    conn.commit()
    result = compute_stock_compliance(conn, 1, today=TODAY)
    # card = mesmo total que a tela: 2 itens disponíveis com CA vencido (o entregue não conta)
    assert result['summary']['ca_expired'] == 2
    assert result['summary']['product_expired'] == 2
    # deep-link: os registros exatos
    ids = sorted(r['stock_item_id'] for r in result['categories']['ca_expired'])
    assert len(ids) == 2
    assert all(r['epi_id'] == 7 for r in result['categories']['ca_expired'])


def test_admin_blocked_is_separate_and_excludes_from_validity():
    conn = _conn()
    conn.execute("INSERT INTO epi_stock_items (company_id, unit_id, epi_id, status, qr_code_value) VALUES (1,2,7,'blocked_archived','QB')")
    conn.commit()
    result = compute_stock_compliance(conn, 1, today=TODAY)
    assert result['summary']['admin_blocked'] == 1
    # item bloqueado não entra em CA/validade (já fora de uso)
    assert result['summary']['ca_expired'] == 0
    assert result['summary']['product_expired'] == 0


def test_missing_manufacture_and_lot_flagged():
    conn = _conn()
    conn.execute("INSERT INTO epi_stock_items (company_id, unit_id, epi_id, lot_code, manufacture_date, status, qr_code_value) VALUES (1,2,8,'','','in_stock','QX')")
    conn.commit()
    result = compute_stock_compliance(conn, 1, today=TODAY)
    assert result['summary']['missing_manufacture'] == 1
    assert result['summary']['missing_lot'] == 1
    # EPI 8 é conforme em validade
    assert result['summary']['ca_expired'] == 0


def test_multitenant_isolation_and_unit_filter():
    conn = _conn()
    conn.execute("INSERT INTO epi_stock_items (company_id, unit_id, epi_id, status, qr_code_value) VALUES (1,2,7,'in_stock','QA')")
    conn.execute("INSERT INTO epi_stock_items (company_id, unit_id, epi_id, status, qr_code_value) VALUES (2,9,7,'in_stock','QB')")
    conn.commit()
    # empresa 1 não enxerga item da empresa 2
    r1 = compute_stock_compliance(conn, 1, today=TODAY)
    assert r1['summary']['ca_expired'] == 1
    # filtro por unidade
    r_unit = compute_stock_compliance(conn, 1, unit_id=99, today=TODAY)
    assert r_unit['summary']['ca_expired'] == 0
