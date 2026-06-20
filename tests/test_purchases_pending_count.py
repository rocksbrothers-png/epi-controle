"""Contagem de requisições de compra pendentes (KPI do dashboard via bootstrap).

Trava: estados terminais não contam; escopo por empresa/unidade respeitado.
Pattern de teste: sqlite in-memory isolado (sem tocar no banco real).
"""
import sqlite3

from modules.purchases.service import count_pending_purchase_requests


def _dict_factory(cursor, row):
    return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}


def _conn():
    conn = sqlite3.connect(':memory:')
    conn.row_factory = _dict_factory
    conn.executescript(
        """
        CREATE TABLE purchase_requests (
            id INTEGER PRIMARY KEY,
            company_id INTEGER,
            unit_id INTEGER,
            status TEXT,
            created_at TEXT DEFAULT ''
        );
        """
    )
    conn.commit()
    return conn


def _seed(conn, rows):
    conn.executemany(
        'INSERT INTO purchase_requests (company_id, unit_id, status) VALUES (?, ?, ?)',
        rows,
    )
    conn.commit()


def test_counts_only_non_terminal_in_company():
    conn = _conn()
    _seed(conn, [
        (1, 10, 'open'),                # pendente
        (1, 10, 'pending_approval'),    # pendente
        (1, 11, 'po_generated'),        # pendente (ainda em andamento)
        (1, 11, 'rejected'),            # terminal
        (1, 11, 'closed'),              # terminal
        (1, 11, 'cancelled'),           # terminal
        (1, 11, 'received'),            # terminal
        (1, 11, 'checked'),             # terminal
        (2, 99, 'open'),                # outra empresa — não conta
    ])
    assert count_pending_purchase_requests(conn, company_id=1) == 3


def test_scopes_by_single_unit():
    conn = _conn()
    _seed(conn, [
        (1, 10, 'open'),
        (1, 10, 'draft'),
        (1, 11, 'open'),
    ])
    assert count_pending_purchase_requests(conn, company_id=1, scope_unit_id=10) == 2


def test_scopes_by_purchase_scope_units():
    conn = _conn()
    _seed(conn, [
        (1, 10, 'open'),
        (1, 11, 'open'),
        (1, 12, 'open'),
    ])
    # scope_unit_id None → usa a lista de unidades de escopo de compras.
    assert count_pending_purchase_requests(
        conn, company_id=1, purchase_scope_units=[10, 12]
    ) == 2


def test_zero_when_all_terminal():
    conn = _conn()
    _seed(conn, [(1, 10, 'closed'), (1, 10, 'rejected')])
    assert count_pending_purchase_requests(conn, company_id=1) == 0
