"""Fase 4 (HSE) — política FEFO (First Expire, First Out) no estoque disponível.

fetch_available_stock_items passa a ordenar os itens disponíveis pela validade
mais próxima (data de fabricação mais antiga primeiro), para que o lote que vence
antes seja sugerido/entregue primeiro. Itens sem data de fabricação vão ao final.
Itens bloqueados (status fora de in_stock/available) não aparecem — o que garante
que estoque bloqueado nunca é oferecido na entrega.
"""

import sqlite3

from modules.stock.service import fetch_available_stock_items


def _conn():
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        CREATE TABLE epis (id INTEGER PRIMARY KEY, name TEXT, epi_validity_date TEXT DEFAULT '');
        CREATE TABLE epi_stock_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT, company_id INTEGER, unit_id INTEGER, epi_id INTEGER,
            glove_size TEXT DEFAULT 'N/A', size TEXT DEFAULT 'N/A', uniform_size TEXT DEFAULT 'N/A',
            qr_code_value TEXT DEFAULT '', status TEXT DEFAULT 'in_stock', manufacture_date TEXT DEFAULT ''
        );
        INSERT INTO epis (id, name) VALUES (7, 'Capacete');
        """
    )
    def add(iid, mfg, status='in_stock', qr=None):
        conn.execute(
            "INSERT INTO epi_stock_items (id, company_id, unit_id, epi_id, qr_code_value, status, manufacture_date) "
            "VALUES (?, 1, 2, 7, ?, ?, ?)",
            (iid, qr or f'QR-{iid}', status, mfg),
        )
    # Ordem de inserção propositalmente fora de ordem de validade.
    add(10, '2026-03-01')          # vence antes (fabricado antes)
    add(11, '2026-01-01')          # vence PRIMEIRO
    add(12, '')                    # sem data → vai ao final
    add(13, '2026-02-01')          # meio
    add(99, '2025-01-01', status='blocked_expired')  # bloqueado → não aparece
    conn.commit()
    return conn


def test_fefo_orders_by_earliest_manufacture_first():
    conn = _conn()
    rows = fetch_available_stock_items(conn, 1, 2, 7)
    ids = [r['id'] for r in rows]
    # 11 (jan) < 13 (fev) < 10 (mar) < 12 (sem data, por último)
    assert ids == [11, 13, 10, 12], ids


def test_blocked_items_are_never_offered():
    conn = _conn()
    ids = [r['id'] for r in fetch_available_stock_items(conn, 1, 2, 7)]
    assert 99 not in ids, 'item bloqueado não pode ser oferecido na entrega'


def test_only_scoped_company_unit_epi():
    conn = _conn()
    # outro escopo não deve retornar nada
    assert fetch_available_stock_items(conn, 1, 999, 7) == []
    assert fetch_available_stock_items(conn, 999, 2, 7) == []
