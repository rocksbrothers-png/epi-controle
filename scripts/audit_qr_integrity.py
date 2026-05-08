#!/usr/bin/env python3
"""Audita e corrige integridade de QR em epi_stock_items.

Uso:
  python scripts/audit_qr_integrity.py --database-url "$DATABASE_URL" --apply-fixes
  python scripts/audit_qr_integrity.py --sqlite-file ./local.sqlite --apply-fixes
"""

from __future__ import annotations

import argparse
import os
import sqlite3
from dataclasses import dataclass
from typing import Any


@dataclass
class AuditResult:
    duplicated: list[dict[str, Any]]
    empty_qr: list[dict[str, Any]]
    inconsistent_status: list[dict[str, Any]]
    in_stock_without_qr: list[dict[str, Any]]
    invalid_links: list[dict[str, Any]]


def rows_to_dicts(cursor, rows):
    cols = [desc[0] for desc in cursor.description]
    return [dict(zip(cols, row)) for row in rows]


def _connect(args):
    if args.sqlite_file:
        conn = sqlite3.connect(args.sqlite_file)
        conn.row_factory = sqlite3.Row
        return conn, 'sqlite'
    database_url = args.database_url or os.environ.get('DATABASE_URL', '').strip()
    if not database_url:
        raise SystemExit('Informe --database-url ou --sqlite-file (ou defina DATABASE_URL).')
    import psycopg2
    from psycopg2.extras import RealDictCursor

    conn = psycopg2.connect(database_url)
    conn.cursor_factory = RealDictCursor
    return conn, 'postgres'


def fetch_all(conn, sql, params=()):
    cur = conn.cursor()
    try:
        cur.execute(sql, params)
        rows = cur.fetchall()
        if rows and isinstance(rows[0], dict):
            return rows
        return rows_to_dicts(cur, rows)
    finally:
        cur.close()


def execute(conn, sql, params=()):
    cur = conn.cursor()
    try:
        cur.execute(sql, params)
    finally:
        cur.close()


def audit(conn) -> AuditResult:
    duplicated = fetch_all(
        conn,
        """
        SELECT qr_code_value, COUNT(*) AS count_items
        FROM epi_stock_items
        WHERE qr_code_value IS NOT NULL AND qr_code_value <> ''
        GROUP BY qr_code_value
        HAVING COUNT(*) > 1
        ORDER BY COUNT(*) DESC, qr_code_value ASC
        """,
    )
    empty_qr = fetch_all(
        conn,
        """
        SELECT id, company_id, unit_id, epi_id, status, delivery_id, qr_code_value
        FROM epi_stock_items
        WHERE qr_code_value IS NULL OR qr_code_value = ''
        ORDER BY id ASC
        """,
    )
    inconsistent_status = fetch_all(
        conn,
        """
        SELECT id, company_id, unit_id, epi_id, status, delivery_id, qr_code_value
        FROM epi_stock_items
        WHERE delivery_id IS NOT NULL
          AND LOWER(COALESCE(status, '')) IN ('in_stock','available')
        ORDER BY id ASC
        """,
    )
    in_stock_without_qr = fetch_all(
        conn,
        """
        SELECT id, company_id, unit_id, epi_id, status, delivery_id, qr_code_value
        FROM epi_stock_items
        WHERE LOWER(COALESCE(status, '')) IN ('in_stock','available')
          AND (qr_code_value IS NULL OR qr_code_value = '')
        ORDER BY id ASC
        """,
    )
    invalid_links = fetch_all(
        conn,
        """
        SELECT esi.id, esi.company_id, esi.unit_id, esi.epi_id, esi.qr_code_value
        FROM epi_stock_items esi
        LEFT JOIN epis e ON e.id = esi.epi_id
        LEFT JOIN units u ON u.id = esi.unit_id
        LEFT JOIN companies c ON c.id = esi.company_id
        WHERE e.id IS NULL OR u.id IS NULL OR c.id IS NULL
        ORDER BY esi.id ASC
        """,
    )
    return AuditResult(duplicated, empty_qr, inconsistent_status, in_stock_without_qr, invalid_links)


def build_recovered_qr(company_id: int, unit_id: int, item_id: int) -> str:
    return f"EPI-ITEM-{int(company_id):04d}-{int(unit_id):04d}-{int(item_id):08d}"


def apply_fixes(conn, remove_invalid_links: bool = False):
    # 1) status inconsistente de item já entregue
    execute(
        conn,
        """
        UPDATE epi_stock_items
        SET status = 'delivered', updated_at = CURRENT_TIMESTAMP
        WHERE delivery_id IS NOT NULL
          AND LOWER(COALESCE(status, '')) IN ('in_stock','available')
        """,
    )

    # 2) qr vazio em item in_stock/available: gerar QR recuperado
    rows = fetch_all(
        conn,
        """
        SELECT id, company_id, unit_id
        FROM epi_stock_items
        WHERE LOWER(COALESCE(status, '')) IN ('in_stock','available')
          AND (qr_code_value IS NULL OR qr_code_value = '')
        ORDER BY id ASC
        """,
    )
    for row in rows:
        new_qr = build_recovered_qr(row['company_id'], row['unit_id'], row['id'])
        execute(
            conn,
            """
            UPDATE epi_stock_items
            SET qr_code_value = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """ if isinstance(conn, sqlite3.Connection) else
            """
            UPDATE epi_stock_items
            SET qr_code_value = %s, updated_at = NOW()
            WHERE id = %s
            """,
            (new_qr, row['id']),
        )

    # 3) QR duplicado: mantém o item de menor id e regenera os demais
    duplicates = fetch_all(
        conn,
        """
        SELECT qr_code_value
        FROM epi_stock_items
        WHERE qr_code_value IS NOT NULL AND qr_code_value <> ''
        GROUP BY qr_code_value
        HAVING COUNT(*) > 1
        """,
    )
    for dup in duplicates:
        items = fetch_all(
            conn,
            """
            SELECT id, company_id, unit_id
            FROM epi_stock_items
            WHERE qr_code_value = ?
            ORDER BY id ASC
            """ if isinstance(conn, sqlite3.Connection) else
            """
            SELECT id, company_id, unit_id
            FROM epi_stock_items
            WHERE qr_code_value = %s
            ORDER BY id ASC
            """,
            (dup['qr_code_value'],),
        )
        for item in items[1:]:
            new_qr = build_recovered_qr(item['company_id'], item['unit_id'], item['id'])
            execute(
                conn,
                """
                UPDATE epi_stock_items
                SET qr_code_value = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """ if isinstance(conn, sqlite3.Connection) else
                """
                UPDATE epi_stock_items
                SET qr_code_value = %s, updated_at = NOW()
                WHERE id = %s
                """,
                (new_qr, item['id']),
            )

    # 4) Integridade de vínculo: opcionalmente remove itens órfãos
    if remove_invalid_links:
        execute(
            conn,
            """
            DELETE FROM epi_stock_items
            WHERE id IN (
              SELECT esi.id
              FROM epi_stock_items esi
              LEFT JOIN epis e ON e.id = esi.epi_id
              LEFT JOIN units u ON u.id = esi.unit_id
              LEFT JOIN companies c ON c.id = esi.company_id
              WHERE e.id IS NULL OR u.id IS NULL OR c.id IS NULL
            )
            """,
        )


def main():
    parser = argparse.ArgumentParser(description='Auditoria de integridade de QR no estoque')
    parser.add_argument('--database-url', default='')
    parser.add_argument('--sqlite-file', default='')
    parser.add_argument('--apply-fixes', action='store_true')
    parser.add_argument('--remove-invalid-links', action='store_true')
    args = parser.parse_args()

    conn, backend = _connect(args)
    try:
        if args.apply_fixes:
            apply_fixes(conn, remove_invalid_links=args.remove_invalid_links)
            conn.commit()
        result = audit(conn)
    finally:
        conn.close()

    print(f'backend={backend}')
    print('duplicated_qr_count=', len(result.duplicated))
    print('empty_qr_count=', len(result.empty_qr))
    print('inconsistent_status_count=', len(result.inconsistent_status))
    print('in_stock_without_qr_count=', len(result.in_stock_without_qr))
    print('invalid_links_count=', len(result.invalid_links))

    def dump(name, rows):
        if not rows:
            print(f'[{name}] ok')
            return
        print(f'[{name}] {len(rows)} item(ns)')
        for row in rows[:20]:
            print(' ', row)

    dump('duplicated', result.duplicated)
    dump('empty_qr', result.empty_qr)
    dump('inconsistent_status', result.inconsistent_status)
    dump('in_stock_without_qr', result.in_stock_without_qr)
    dump('invalid_links', result.invalid_links)


if __name__ == '__main__':
    main()
