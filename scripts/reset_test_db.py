#!/usr/bin/env python3
"""Reset completo do banco de teste (PostgreSQL) e recriação do schema base.

Uso:
  DATABASE_URL=postgres://... python scripts/reset_test_db.py
"""

from __future__ import annotations

import os
import sys

from server_postgres import init_db


def _connect_postgres(database_url: str):
    try:
        import psycopg2
    except ModuleNotFoundError as exc:  # pragma: no cover - ambiente sem driver
        raise RuntimeError('psycopg2 não está instalado no ambiente atual.') from exc
    return psycopg2.connect(database_url)


def reset_postgres_schema(database_url: str) -> None:
    connection = _connect_postgres(database_url)
    connection.autocommit = True
    try:
        with connection.cursor() as cursor:
            cursor.execute('DROP SCHEMA IF EXISTS public CASCADE;')
            cursor.execute('CREATE SCHEMA public;')
            cursor.execute('GRANT ALL ON SCHEMA public TO public;')
    finally:
        connection.close()


def main() -> int:
    database_url = str(os.environ.get('DATABASE_URL', '')).strip()
    if not database_url:
        print('DATABASE_URL não configurada. Abortando reset.', file=sys.stderr)
        return 2

    print('[reset-test-db] Iniciando limpeza completa do schema public...')
    reset_postgres_schema(database_url)
    print('[reset-test-db] Schema removido e recriado. Reaplicando bootstrap/migrations...')
    bootstrap_admin = init_db()
    if bootstrap_admin:
        print(f"[reset-test-db] Admin bootstrap ativo: id={bootstrap_admin.get('id')} username={bootstrap_admin.get('username')}")
    print('[reset-test-db] Reset concluído com sucesso.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
