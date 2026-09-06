"""Regra de Demandas Pendentes vs. card "Estoque baixo" do dashboard.

Causa raiz investigada: a LUVA CONTRA IMPACTO (estoque 10 / mínimo 10) aparecia
no card "Estoque baixo da unidade" (que usa `stock <= minimum`) mas NÃO em
Demandas Pendentes, porque `fetch_purchase_demands` usava `quantity < minimum`
(estrito). Agora ambos usam `<=` (ponto de reposição = no mínimo ou abaixo).
"""

import sqlite3


from modules.purchases.service import fetch_purchase_demands


def _conn():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        CREATE TABLE companies (id INTEGER PRIMARY KEY, name TEXT);
        CREATE TABLE units (id INTEGER PRIMARY KEY, name TEXT);
        CREATE TABLE employees (id INTEGER PRIMARY KEY, name TEXT, sector TEXT, role_name TEXT);
        CREATE TABLE epis (
            id INTEGER PRIMARY KEY, name TEXT, ca TEXT, unit_measure TEXT, manufacturer TEXT,
            supplier_company TEXT, sector TEXT, glove_size TEXT, size TEXT, uniform_size TEXT,
            active INTEGER, minimum_stock INTEGER);
        CREATE TABLE unit_epi_stock (
            company_id INTEGER, unit_id INTEGER, epi_id INTEGER, quantity INTEGER);
        -- #271: parâmetros de classificação. Sem linhas — a ausência É a
        -- herança (mínimo e percentual da empresa, alerta habilitado).
        CREATE TABLE unit_epi_minimum_stock (
            id INTEGER PRIMARY KEY AUTOINCREMENT, company_id INTEGER NOT NULL,
            unit_id INTEGER NOT NULL, epi_id INTEGER NOT NULL,
            minimum_stock INTEGER NOT NULL DEFAULT 0,
            created_by_user_id INTEGER, updated_by_user_id INTEGER,
            created_at TEXT NOT NULL DEFAULT '', updated_at TEXT NOT NULL DEFAULT '',
            UNIQUE (company_id, unit_id, epi_id));
        CREATE TABLE company_stock_attention_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT, company_id INTEGER NOT NULL UNIQUE,
            attention_percentage INTEGER NOT NULL DEFAULT 20, updated_by_user_id INTEGER,
            created_at TEXT NOT NULL DEFAULT '', updated_at TEXT NOT NULL DEFAULT '');
        CREATE TABLE unit_epi_attention_percentage (
            id INTEGER PRIMARY KEY AUTOINCREMENT, company_id INTEGER NOT NULL,
            unit_id INTEGER NOT NULL, epi_id INTEGER NOT NULL,
            attention_percentage INTEGER NOT NULL DEFAULT 0,
            created_by_user_id INTEGER, updated_by_user_id INTEGER,
            created_at TEXT NOT NULL DEFAULT '', updated_at TEXT NOT NULL DEFAULT '',
            UNIQUE (company_id, unit_id, epi_id));
        CREATE TABLE unit_epi_stock_alert_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT, company_id INTEGER NOT NULL,
            unit_id INTEGER NOT NULL, epi_id INTEGER NOT NULL,
            alert_enabled INTEGER NOT NULL DEFAULT 1,
            created_by_user_id INTEGER, updated_by_user_id INTEGER,
            created_at TEXT NOT NULL DEFAULT '', updated_at TEXT NOT NULL DEFAULT '',
            UNIQUE (company_id, unit_id, epi_id));
        CREATE TABLE unit_epi_stock_config_audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT, company_id INTEGER NOT NULL,
            unit_id INTEGER NOT NULL, epi_id INTEGER NOT NULL, parameter TEXT NOT NULL,
            previous_value TEXT, new_value TEXT NOT NULL,
            previous_source TEXT NOT NULL DEFAULT '', actor_user_id INTEGER,
            actor_name TEXT NOT NULL DEFAULT '', actor_role TEXT NOT NULL DEFAULT '',
            ip_address TEXT NOT NULL DEFAULT '', user_agent TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL);
        CREATE TABLE epi_requests (
            id INTEGER PRIMARY KEY, company_id INTEGER, unit_id INTEGER, employee_id INTEGER,
            epi_id INTEGER, quantity INTEGER, glove_size TEXT, size TEXT, uniform_size TEXT,
            requested_at TEXT, status TEXT);
        CREATE TABLE epi_stock_items (
            company_id INTEGER, unit_id INTEGER, epi_id INTEGER,
            glove_size TEXT, size TEXT, uniform_size TEXT, status TEXT);
        INSERT INTO companies VALUES (2, 'Norskan Offshore');
        INSERT INTO units VALUES (4, 'Skandi Paraty');
        """
    )
    return conn


def _add_epi(conn, epi_id, minimum, quantity, active=1, name=None):
    conn.execute(
        "INSERT INTO epis (id, name, ca, unit_measure, manufacturer, supplier_company, sector, "
        "glove_size, size, uniform_size, active, minimum_stock) "
        "VALUES (?, ?, 'CA1', 'par', 'Fab', 'Forn', 'Operação', 'N/A', 'N/A', 'N/A', ?, ?)",
        (epi_id, name or f"EPI {epi_id}", active, minimum),
    )
    conn.execute(
        "INSERT INTO unit_epi_stock (company_id, unit_id, epi_id, quantity) VALUES (2, 4, ?, ?)",
        (epi_id, quantity),
    )
    conn.commit()


def _demand_epi_ids(conn):
    demands = fetch_purchase_demands(conn, company_id=2, scope_unit_id=4)
    return {int(d["epi_id"]) for d in demands if d.get("demand_type") == "low_stock"}


def test_item_at_exactly_minimum_is_a_pending_demand():
    conn = _conn()
    _add_epi(conn, 26, minimum=10, quantity=10, name="LUVA CONTRA IMPACTO")
    assert 26 in _demand_epi_ids(conn), "estoque == mínimo (10/10) deve gerar demanda pendente"


def test_item_below_minimum_is_a_pending_demand():
    conn = _conn()
    _add_epi(conn, 27, minimum=10, quantity=5)
    assert 27 in _demand_epi_ids(conn)


def test_item_above_minimum_is_not_a_demand():
    conn = _conn()
    _add_epi(conn, 28, minimum=10, quantity=15)
    assert 28 not in _demand_epi_ids(conn)


def test_inactive_item_at_minimum_is_not_a_demand():
    conn = _conn()
    _add_epi(conn, 29, minimum=10, quantity=10, active=0)
    assert 29 not in _demand_epi_ids(conn)


def test_quantity_requested_is_at_least_one_at_minimum():
    conn = _conn()
    _add_epi(conn, 30, minimum=10, quantity=10)
    demands = fetch_purchase_demands(conn, company_id=2, scope_unit_id=4)
    luva = next(d for d in demands if int(d["epi_id"]) == 30)
    assert int(luva["quantity_requested"]) >= 1


def _add_employee_request(conn, req_id, epi_id, status, employee_id=5):
    conn.execute(
        "INSERT OR IGNORE INTO employees (id, name, sector, role_name) VALUES (?, 'Maria', 'Operação', 'Operadora')",
        (employee_id,),
    )
    # EPI referenciado pela solicitação (JOIN epis na query de solicitações)
    conn.execute(
        "INSERT OR IGNORE INTO epis (id, name, ca, unit_measure, manufacturer, supplier_company, sector, "
        "glove_size, size, uniform_size, active, minimum_stock) "
        "VALUES (?, 'EPI Solic', 'CA9', 'un', 'Fab', 'Forn', 'Operação', 'N/A', 'N/A', 'N/A', 1, 999)",
        (epi_id,),
    )
    conn.execute(
        "INSERT INTO epi_requests (id, company_id, unit_id, employee_id, epi_id, quantity, "
        "glove_size, size, uniform_size, requested_at, status) "
        "VALUES (?, 2, 4, ?, ?, 1, 'N/A', 'N/A', 'N/A', '2026-06-01T00:00:00+00:00', ?)",
        (req_id, employee_id, epi_id, status),
    )
    conn.commit()


def _employee_demand_epi_ids(conn):
    demands = fetch_purchase_demands(conn, company_id=2, scope_unit_id=4)
    return {int(d["epi_id"]) for d in demands if d.get("demand_type") == "employee_request"}


def test_collaborator_request_pending_approval_is_not_a_demand():
    # status 'solicitado' fica na aba Aprovações; não deve aparecer em Demandas.
    conn = _conn()
    _add_employee_request(conn, req_id=1, epi_id=40, status="solicitado")
    assert 40 not in _employee_demand_epi_ids(conn)


def test_collaborator_request_approved_becomes_a_demand():
    # após aprovação do Administrador Local (status 'aprovado'), vira demanda.
    conn = _conn()
    _add_employee_request(conn, req_id=2, epi_id=41, status="aprovado")
    assert 41 in _employee_demand_epi_ids(conn)


# ── #1 — Demandas automáticas por tamanho ──────────────────────────────────────

def _low_stock_demand(conn, epi_id):
    demands = fetch_purchase_demands(conn, company_id=2, scope_unit_id=4)
    return next(d for d in demands if int(d["epi_id"]) == epi_id and d["demand_type"] == "low_stock")


def test_size_demands_present_without_tracking_falls_back_to_single():
    conn = _conn()
    _add_epi(conn, 50, minimum=10, quantity=4)
    demand = _low_stock_demand(conn, 50)
    assert demand["size_demands"], "deve sempre listar ao menos um tamanho"
    assert len(demand["size_demands"]) == 1
    row = demand["size_demands"][0]
    assert row["minimum_stock"] == 10
    assert row["current_stock"] == 4
    assert row["suggested_quantity"] == 6  # mínimo − atual


def test_size_demands_break_down_per_registered_size():
    conn = _conn()
    _add_epi(conn, 51, minimum=10, quantity=3)
    # rastreio por tamanho: 2 luvas P e 1 luva G em estoque
    conn.execute("INSERT INTO epi_stock_items VALUES (2,4,51,'P','N/A','N/A','in_stock')")
    conn.execute("INSERT INTO epi_stock_items VALUES (2,4,51,'P','N/A','N/A','in_stock')")
    conn.execute("INSERT INTO epi_stock_items VALUES (2,4,51,'G','N/A','N/A','in_stock')")
    conn.commit()
    demand = _low_stock_demand(conn, 51)
    by_glove = {r["glove_size"]: r for r in demand["size_demands"]}
    assert by_glove["P"]["current_stock"] == 2
    assert by_glove["P"]["suggested_quantity"] == 8  # 10 − 2
    assert by_glove["G"]["current_stock"] == 1
    assert by_glove["G"]["suggested_quantity"] == 9  # 10 − 1


def test_size_demands_suggested_never_negative():
    conn = _conn()
    _add_epi(conn, 52, minimum=10, quantity=10)
    # um tamanho já com saldo acima do mínimo não deve sugerir quantidade negativa
    for _ in range(12):
        conn.execute("INSERT INTO epi_stock_items VALUES (2,4,52,'M','N/A','N/A','in_stock')")
    conn.commit()
    demand = _low_stock_demand(conn, 52)
    m_row = next(r for r in demand["size_demands"] if r["glove_size"] == "M")
    assert m_row["suggested_quantity"] == 0
