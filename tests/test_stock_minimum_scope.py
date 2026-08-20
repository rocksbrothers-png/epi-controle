"""PR24-2 (bug reportado em produção): Administrador Local/Gestor de EPI
recebiam "Perfil só pode editar estoque mínimo da unidade operacional
ativa." mesmo estando dentro da própria unidade, ao editar o estoque
mínimo de um EPI de escopo GLOBAL (visível/estocado em várias unidades via
`unit_epi_stock`, sem `epis.unit_id` próprio) ou de Joint Venture.

Causa raiz: `handle_post_stock_minimum` (modules/stock/routes.py) comparava
`epi.unit_id` (coluna estática do catálogo, só preenchida para EPI de
escopo UNIT) diretamente contra a unidade operacional do ator — em vez de
reaproveitar `epi_backend.epi_scope.is_epi_visible_for_unit`, a mesma
função já usada por `GET /api/stock/epis` e por
`fetch_low_stock_items` para decidir se um EPI aparece na tela de estoque
daquela unidade. Um EPI GLOBAL nunca tem `unit_id` preenchido, então a
comparação ingênua falhava sempre, mesmo quando o EPI estava
legitimamente visível e em uso na unidade do ator.
"""

import sqlite3

import pytest

import modules.stock.routes as routes


def _dict_factory(cursor, row):
    return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}


class _PgStyleConn:
    def __init__(self, conn):
        self._conn = conn

    def execute(self, sql, params=()):
        return self._conn.execute(str(sql).replace('%s', '?'), params)

    def commit(self):
        self._conn.commit()

    def __getattr__(self, name):
        return getattr(self._conn, name)


def _conn():
    conn = sqlite3.connect(':memory:')
    conn.row_factory = _dict_factory
    conn.executescript(
        """
        CREATE TABLE companies (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT);
        CREATE TABLE units (id INTEGER PRIMARY KEY AUTOINCREMENT, company_id INTEGER, name TEXT);
        CREATE TABLE employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL, unit_id INTEGER, name TEXT
        );
        CREATE TABLE employee_unit_movements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id INTEGER, movement_type TEXT, start_date TEXT, end_date TEXT DEFAULT '',
            target_unit_id INTEGER
        );
        CREATE TABLE epis (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL, unit_id INTEGER, name TEXT DEFAULT '',
            purchase_code TEXT DEFAULT '', ca TEXT DEFAULT '', active INTEGER NOT NULL DEFAULT 1,
            unit_measure TEXT DEFAULT '', glove_size TEXT DEFAULT '', size TEXT DEFAULT '',
            uniform_size TEXT DEFAULT '', active_joinventure TEXT, scope_type TEXT DEFAULT 'GLOBAL',
            minimum_stock INTEGER NOT NULL DEFAULT 10
        );
        CREATE TABLE unit_epi_stock (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL, unit_id INTEGER NOT NULL, epi_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 0, updated_at TEXT
        );
        CREATE TABLE unit_joint_venture_periods (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            unit_id INTEGER NOT NULL, joint_venture_name TEXT, started_at TEXT, ended_at TEXT
        );
        -- 1.1D-B0: o mínimo passou a ser gravado por Unidade, não em `epis`.
        -- O escopo de VISIBILIDADE testado aqui não muda; só o destino da
        -- escrita, que agora é isolado por (company_id, unit_id, epi_id).
        CREATE TABLE unit_epi_minimum_stock (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL, unit_id INTEGER NOT NULL, epi_id INTEGER NOT NULL,
            minimum_stock INTEGER NOT NULL DEFAULT 0,
            created_by_user_id INTEGER, updated_by_user_id INTEGER,
            created_at TEXT NOT NULL DEFAULT '', updated_at TEXT NOT NULL DEFAULT '',
            UNIQUE (company_id, unit_id, epi_id)
        );
        CREATE TABLE unit_epi_minimum_stock_audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL, unit_id INTEGER NOT NULL, epi_id INTEGER NOT NULL,
            action TEXT NOT NULL DEFAULT 'set',
            previous_minimum_stock INTEGER, new_minimum_stock INTEGER NOT NULL,
            previous_source TEXT NOT NULL DEFAULT '',
            actor_user_id INTEGER, actor_name TEXT NOT NULL DEFAULT '',
            actor_role TEXT NOT NULL DEFAULT '', ip_address TEXT NOT NULL DEFAULT '',
            user_agent TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL
        );
        """
    )
    return conn


def _seed_company(conn, name='Norskan Offshore'):
    cur = conn.execute('INSERT INTO companies (name) VALUES (?)', (name,))
    conn.commit()
    return int(cur.lastrowid)


def _seed_unit(conn, company_id, name='Skandi Paraty'):
    cur = conn.execute('INSERT INTO units (company_id, name) VALUES (?, ?)', (company_id, name))
    conn.commit()
    return int(cur.lastrowid)


def _seed_unit_scoped_actor(conn, company_id, unit_id, role='user'):
    cur = conn.execute(
        'INSERT INTO employees (company_id, unit_id, name) VALUES (?, ?, ?)',
        (company_id, unit_id, 'Gestor de EPI da Unidade'),
    )
    conn.commit()
    return {'id': 1, 'role': role, 'company_id': company_id, 'linked_employee_id': int(cur.lastrowid)}


def _seed_epi(conn, company_id, *, unit_id=None, joinventure=None, scope_type='GLOBAL', minimum=10):
    cur = conn.execute(
        'INSERT INTO epis (company_id, unit_id, name, active, active_joinventure, scope_type, minimum_stock) '
        'VALUES (?, ?, ?, 1, ?, ?, ?)',
        (company_id, unit_id, 'Capacete', joinventure, scope_type, minimum),
    )
    conn.commit()
    return int(cur.lastrowid)


def _stock_epi(conn, company_id, unit_id, epi_id, quantity=5):
    conn.execute(
        'INSERT INTO unit_epi_stock (company_id, unit_id, epi_id, quantity) VALUES (?, ?, ?, ?)',
        (company_id, unit_id, epi_id, quantity),
    )
    conn.commit()


def _post_minimum(conn, actor, epi_id, minimum_stock, monkeypatch):
    monkeypatch.setattr(routes, 'authorize_action', lambda *a, **k: actor)
    monkeypatch.setattr(routes, 'resolve_actor_user_id', lambda *a, **k: actor['id'])

    class _Handler:
        path = '/api/stock/minimum'

        def send_response(self, *_a, **_k):
            pass

        def send_header(self, *_a, **_k):
            pass

        def end_headers(self):
            pass

        wfile = None

    import io
    handler = _Handler()
    handler.wfile = io.BytesIO()
    monkeypatch.setattr(routes, 'get_connection', lambda: conn)
    payload = {'actor_user_id': actor['id'], 'epi_id': epi_id, 'minimum_stock': minimum_stock}
    routes.handle_post_stock_minimum(handler, None, payload, None)
    import json
    return json.loads(handler.wfile.getvalue().decode('utf-8'))


@pytest.fixture(autouse=True)
def _sqlite_detection(monkeypatch):
    import epi_backend.db as db_module
    monkeypatch.setattr(db_module, '_is_sqlite_connection', lambda _conn: True)


def test_admin_can_edit_minimum_stock_of_global_epi_within_own_unit(monkeypatch):
    conn = _PgStyleConn(_conn())
    cid = _seed_company(conn)
    unit_id = _seed_unit(conn, cid)
    actor = _seed_unit_scoped_actor(conn, cid, unit_id, role='user')
    epi_id = _seed_epi(conn, cid, unit_id=None, scope_type='GLOBAL')
    _stock_epi(conn, cid, unit_id, epi_id)

    body = _post_minimum(conn, actor, epi_id, 15, monkeypatch)

    assert body['ok'] is True
    assert body['minimum_stock'] == 15


def test_admin_can_edit_minimum_stock_of_unit_scoped_epi_of_own_unit(monkeypatch):
    conn = _PgStyleConn(_conn())
    cid = _seed_company(conn)
    unit_id = _seed_unit(conn, cid)
    actor = _seed_unit_scoped_actor(conn, cid, unit_id, role='admin')
    epi_id = _seed_epi(conn, cid, unit_id=unit_id, scope_type='UNIT')
    _stock_epi(conn, cid, unit_id, epi_id)

    body = _post_minimum(conn, actor, epi_id, 20, monkeypatch)

    assert body['ok'] is True
    assert body['minimum_stock'] == 20


def test_admin_cannot_edit_minimum_stock_of_unit_scoped_epi_of_another_unit(monkeypatch):
    conn = _PgStyleConn(_conn())
    cid = _seed_company(conn)
    own_unit_id = _seed_unit(conn, cid, name='Skandi Paraty')
    other_unit_id = _seed_unit(conn, cid, name='Norskan Alpha')
    actor = _seed_unit_scoped_actor(conn, cid, own_unit_id, role='user')
    epi_id = _seed_epi(conn, cid, unit_id=other_unit_id, scope_type='UNIT')
    _stock_epi(conn, cid, other_unit_id, epi_id)

    with pytest.raises(PermissionError):
        _post_minimum(conn, actor, epi_id, 20, monkeypatch)


def test_admin_cannot_edit_minimum_stock_of_joint_venture_epi_outside_the_jv(monkeypatch):
    conn = _PgStyleConn(_conn())
    cid = _seed_company(conn)
    unit_id = _seed_unit(conn, cid)
    actor = _seed_unit_scoped_actor(conn, cid, unit_id, role='user')
    epi_id = _seed_epi(conn, cid, unit_id=None, joinventure='Consorcio X', scope_type='JOINT_VENTURE')
    _stock_epi(conn, cid, unit_id, epi_id)

    with pytest.raises(PermissionError):
        _post_minimum(conn, actor, epi_id, 20, monkeypatch)


def test_admin_can_edit_minimum_stock_of_joint_venture_epi_matching_own_units_active_jv(monkeypatch):
    conn = _PgStyleConn(_conn())
    cid = _seed_company(conn)
    unit_id = _seed_unit(conn, cid)
    actor = _seed_unit_scoped_actor(conn, cid, unit_id, role='user')
    conn.execute(
        'INSERT INTO unit_joint_venture_periods (unit_id, joint_venture_name, started_at, ended_at) '
        "VALUES (?, ?, '2026-01-01', NULL)",
        (unit_id, 'Consorcio X'),
    )
    conn.commit()
    epi_id = _seed_epi(conn, cid, unit_id=None, joinventure='Consorcio X', scope_type='JOINT_VENTURE')
    _stock_epi(conn, cid, unit_id, epi_id)

    body = _post_minimum(conn, actor, epi_id, 25, monkeypatch)

    assert body['ok'] is True
    assert body['minimum_stock'] == 25


def test_admin_without_operational_unit_is_blocked_with_clear_message(monkeypatch):
    conn = _PgStyleConn(_conn())
    cid = _seed_company(conn)
    unit_id = _seed_unit(conn, cid)
    epi_id = _seed_epi(conn, cid, unit_id=unit_id, scope_type='UNIT')
    _stock_epi(conn, cid, unit_id, epi_id)
    actor = {'id': 9, 'role': 'user', 'company_id': cid, 'linked_employee_id': None}

    with pytest.raises(PermissionError, match='sem unidade operacional ativa'):
        _post_minimum(conn, actor, epi_id, 20, monkeypatch)


def test_non_operational_role_is_blocked_before_any_unit_check(monkeypatch):
    conn = _PgStyleConn(_conn())
    cid = _seed_company(conn)
    unit_id = _seed_unit(conn, cid)
    epi_id = _seed_epi(conn, cid, unit_id=unit_id, scope_type='UNIT')
    _stock_epi(conn, cid, unit_id, epi_id)
    actor = {'id': 10, 'role': 'buyer', 'company_id': cid}

    with pytest.raises(PermissionError, match='Apenas Administrador Local e Gestor de EPI'):
        _post_minimum(conn, actor, epi_id, 20, monkeypatch)
