#!/usr/bin/env python3
"""Diagnóstico estrutural de duplicidade/consistência para EPIs, estoque e alertas."""

from __future__ import annotations

import json
from contextlib import closing
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from server_postgres import get_connection, PERMISSIONS


def q(connection, sql: str, params=()):
    return [dict(row) for row in connection.execute(sql, params).fetchall()]


def main():
    report = {}
    try:
        connection_ctx = closing(get_connection())
    except Exception as exc:
        report['error'] = str(exc)
        report['low_stock_visibility_by_role'] = {
            role: ('stock:view' in permissions and 'alerts:view' in permissions and 'dashboard:view' in permissions)
            for role, permissions in PERMISSIONS.items()
        }
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return

    with connection_ctx as connection:

        report['potential_epi_duplicates_by_identity'] = q(
            connection,
            '''
            SELECT
                e.company_id,
                LOWER(TRIM(e.name)) AS name_key,
                LOWER(TRIM(COALESCE(e.manufacturer, ''))) AS manufacturer_key,
                LOWER(TRIM(COALESCE(e.ca, ''))) AS ca_key,
                LOWER(TRIM(COALESCE(e.unit_measure, ''))) AS unit_measure_key,
                LOWER(TRIM(COALESCE(e.scope_type, 'GLOBAL'))) AS scope_key,
                COALESCE(e.unit_id, 0) AS unit_key,
                LOWER(TRIM(COALESCE(e.active_joinventure, ''))) AS jv_key,
                COUNT(*) AS total_rows,
                STRING_AGG(CAST(e.id AS TEXT), ', ' ORDER BY e.id) AS epi_ids
            FROM epis e
            GROUP BY
                e.company_id,
                LOWER(TRIM(e.name)),
                LOWER(TRIM(COALESCE(e.manufacturer, ''))),
                LOWER(TRIM(COALESCE(e.ca, ''))),
                LOWER(TRIM(COALESCE(e.unit_measure, ''))),
                LOWER(TRIM(COALESCE(e.scope_type, 'GLOBAL'))),
                COALESCE(e.unit_id, 0),
                LOWER(TRIM(COALESCE(e.active_joinventure, '')))
            HAVING COUNT(*) > 1
            ORDER BY total_rows DESC, e.company_id
            '''
        )

        report['duplicated_unit_stock_rows'] = q(
            connection,
            '''
            SELECT company_id, unit_id, epi_id, COUNT(*) AS total_rows,
                   COALESCE(SUM(quantity), 0) AS total_quantity,
                   STRING_AGG(CAST(id AS TEXT), ', ' ORDER BY id) AS row_ids
            FROM unit_epi_stock
            GROUP BY company_id, unit_id, epi_id
            HAVING COUNT(*) > 1
            ORDER BY total_rows DESC, company_id, unit_id, epi_id
            '''
        )

        report['orphan_unit_stock_rows'] = q(
            connection,
            '''
            SELECT s.id, s.company_id, s.unit_id, s.epi_id, s.quantity
            FROM unit_epi_stock s
            LEFT JOIN companies c ON c.id = s.company_id
            LEFT JOIN units u ON u.id = s.unit_id
            LEFT JOIN epis e ON e.id = s.epi_id
            WHERE c.id IS NULL OR u.id IS NULL OR e.id IS NULL
            ORDER BY s.id
            '''
        )

        report['inactive_epi_with_stock'] = q(
            connection,
            '''
            SELECT e.id AS epi_id, e.company_id, e.name,
                   COALESCE(SUM(s.quantity), 0) AS stock_balance
            FROM epis e
            LEFT JOIN unit_epi_stock s ON s.epi_id = e.id
            WHERE COALESCE(e.active, 1) = 0
            GROUP BY e.id, e.company_id, e.name
            HAVING COALESCE(SUM(s.quantity), 0) > 0
            ORDER BY stock_balance DESC, e.id
            '''
        )

        report['epi_without_stock_and_without_delivery'] = q(
            connection,
            '''
            SELECT e.id AS epi_id, e.company_id, e.name, e.ca, e.manufacturer,
                   COALESCE(SUM(s.quantity), 0) AS stock_balance,
                   COUNT(DISTINCT d.id) AS deliveries
            FROM epis e
            LEFT JOIN unit_epi_stock s ON s.epi_id = e.id
            LEFT JOIN deliveries d ON d.epi_id = e.id
            WHERE COALESCE(e.active, 1) = 1
            GROUP BY e.id, e.company_id, e.name, e.ca, e.manufacturer
            HAVING COALESCE(SUM(s.quantity), 0) = 0 AND COUNT(DISTINCT d.id) = 0
            ORDER BY e.company_id, e.name, e.id
            '''
        )

    report['low_stock_visibility_by_role'] = {
        role: ('stock:view' in permissions and 'alerts:view' in permissions and 'dashboard:view' in permissions)
        for role, permissions in PERMISSIONS.items()
    }

    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
