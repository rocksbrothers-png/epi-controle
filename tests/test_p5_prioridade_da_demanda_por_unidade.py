"""P5 — a prioridade da demanda usa o mínimo daquela Unidade.

`fetch_purchase_demands` ordenava por `(ep.minimum_stock - ues.quantity) DESC`:
o tamanho do buraco medido contra o mínimo da EMPRESA. Era o último operando
de mínimo corporativo sobrevivente neste caminho — a #271 tirou o irmão dele
do WHERE e deixou este para trás.

Ele não decidia se a demanda existia (isso é do `classify_unit_epi_stock`),
mas decidia o que o Administrador Local via primeiro. Com mínimo por Unidade
configurado, a lista chegava ordenada por um número que não governa nada — e
em desacordo com a quantidade de reposição exibida na mesma linha.

Regra travada aqui: prioridade = mínimo EFETIVO da Unidade − saldo da
Unidade, a mesma fonte que dimensiona `quantity_requested`.
"""

import sqlite3

from modules.purchases.service import fetch_purchase_demands

EMPRESA, UNIDADE = 2, 4


def _conn():
    conn = sqlite3.connect(':memory:')
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
        INSERT INTO units VALUES (4, 'Skandi Paraty'), (5, 'Skandi Buzios');
        """
    )
    return conn


def _epi(conn, epi_id, *, minimo_empresa, saldo, minimo_da_unidade=None, unidade=UNIDADE, nome=None):
    conn.execute(
        "INSERT INTO epis (id, name, ca, unit_measure, manufacturer, supplier_company, sector, "
        "glove_size, size, uniform_size, active, minimum_stock) "
        "VALUES (?, ?, 'CA1', 'par', 'Fab', 'Forn', 'Operação', 'N/A', 'N/A', 'N/A', 1, ?)",
        (epi_id, nome or f'EPI {epi_id}', minimo_empresa),
    )
    conn.execute(
        'INSERT INTO unit_epi_stock (company_id, unit_id, epi_id, quantity) VALUES (?, ?, ?, ?)',
        (EMPRESA, unidade, epi_id, saldo),
    )
    if minimo_da_unidade is not None:
        conn.execute(
            'INSERT INTO unit_epi_minimum_stock (company_id, unit_id, epi_id, minimum_stock) '
            'VALUES (?, ?, ?, ?)',
            (EMPRESA, unidade, epi_id, minimo_da_unidade),
        )
    conn.commit()


def _ordem(conn, *, scope_unit_id=UNIDADE):
    demandas = fetch_purchase_demands(conn, company_id=EMPRESA, scope_unit_id=scope_unit_id)
    return [int(d['epi_id']) for d in demandas if d.get('demand_type') == 'low_stock']


def test_a_ordem_segue_o_minimo_da_unidade_e_nao_o_da_empresa():
    """O caso que a ordenação antiga invertia.

    Pelo mínimo da EMPRESA o EPI 1 parecia o buraco maior (100 − 0 = 100)
    e o EPI 2 o menor (10 − 0 = 10). Pelos mínimos DAS UNIDADES é o
    contrário: 5 − 0 = 5 contra 80 − 0 = 80.
    """
    conn = _conn()
    _epi(conn, 1, minimo_empresa=100, saldo=0, minimo_da_unidade=5)
    _epi(conn, 2, minimo_empresa=10, saldo=0, minimo_da_unidade=80)

    assert _ordem(conn) == [2, 1]


def test_a_ordem_concorda_com_a_quantidade_de_reposicao_exibida():
    """Ordem e número na mesma linha vêm da mesma fonte."""
    conn = _conn()
    _epi(conn, 1, minimo_empresa=100, saldo=0, minimo_da_unidade=5)
    _epi(conn, 2, minimo_empresa=10, saldo=0, minimo_da_unidade=80)
    _epi(conn, 3, minimo_empresa=1, saldo=2, minimo_da_unidade=30)

    demandas = [d for d in fetch_purchase_demands(conn, company_id=EMPRESA, scope_unit_id=UNIDADE)
                if d.get('demand_type') == 'low_stock']
    quantidades = [int(d['quantity_requested']) for d in demandas]
    assert quantidades == sorted(quantidades, reverse=True), \
        'a lista não está em ordem decrescente da própria reposição sugerida'
    assert quantidades == [80, 28, 5]


def test_sem_minimo_local_a_heranca_da_empresa_continua_valendo():
    """Ausência de configuração local é herança, não zero."""
    conn = _conn()
    _epi(conn, 1, minimo_empresa=100, saldo=0)
    _epi(conn, 2, minimo_empresa=10, saldo=0)

    assert _ordem(conn) == [1, 2]


def test_minimo_local_de_um_epi_nao_reordena_o_que_herda():
    conn = _conn()
    _epi(conn, 1, minimo_empresa=50, saldo=0)                       # herda 50
    _epi(conn, 2, minimo_empresa=50, saldo=0, minimo_da_unidade=90)  # local 90
    _epi(conn, 3, minimo_empresa=50, saldo=0, minimo_da_unidade=10)  # local 10

    assert _ordem(conn) == [2, 1, 3]


def test_empate_sai_em_ordem_estavel():
    """Duas chamadas iguais não podem devolver ordens diferentes."""
    conn = _conn()
    for epi_id in (7, 3, 9, 1):
        _epi(conn, epi_id, minimo_empresa=20, saldo=0)

    primeira = _ordem(conn)
    assert primeira == [1, 3, 7, 9]
    assert _ordem(conn) == primeira


def test_a_ordem_e_por_unidade_quando_o_escopo_abrange_varias():
    """Sem `scope_unit_id`, cada linha continua sendo de UMA Unidade.

    A prioridade compara buracos locais entre si; ela não soma nem funde as
    Unidades — o par (unidade, EPI) segue intacto em cada demanda.
    """
    conn = _conn()
    _epi(conn, 1, minimo_empresa=10, saldo=0, minimo_da_unidade=5, unidade=UNIDADE)
    _epi(conn, 2, minimo_empresa=10, saldo=0, minimo_da_unidade=50, unidade=5)

    demandas = [d for d in fetch_purchase_demands(conn, company_id=EMPRESA)
                if d.get('demand_type') == 'low_stock']
    assert [(int(d['unit_id']), int(d['epi_id'])) for d in demandas] == [(5, 2), (UNIDADE, 1)]


def test_solicitacoes_de_colaborador_continuam_antes_e_na_ordem_delas():
    """A P5 reordena só a fatia de estoque baixo."""
    conn = _conn()
    conn.execute("INSERT INTO employees VALUES (1, 'Ana', 'Operação', 'Marinheiro')")
    _epi(conn, 1, minimo_empresa=10, saldo=0, minimo_da_unidade=5)
    conn.executemany(
        'INSERT INTO epi_requests (id, company_id, unit_id, employee_id, epi_id, quantity, '
        "glove_size, size, uniform_size, requested_at, status) "
        "VALUES (?, ?, ?, 1, 1, 1, 'N/A', 'N/A', 'N/A', ?, 'aprovado')",
        [(10, EMPRESA, UNIDADE, '2026-01-02'), (11, EMPRESA, UNIDADE, '2026-01-01')],
    )
    conn.commit()

    demandas = fetch_purchase_demands(conn, company_id=EMPRESA, scope_unit_id=UNIDADE)
    tipos = [d.get('demand_type') for d in demandas]
    assert tipos == ['employee_request', 'employee_request', 'low_stock']
    # `ORDER BY r.requested_at ASC` preservado.
    assert [int(d['id']) for d in demandas[:2]] == [11, 10]


def test_o_sql_nao_ordena_mais_pelo_minimo_corporativo():
    """Leitura estrutural: o operando removido não pode voltar ao SQL."""
    from pathlib import Path
    fonte = (Path(__file__).resolve().parents[1] / 'modules' / 'purchases' / 'service.py').read_text(encoding='utf-8')
    corpo = '\n'.join(l for l in fonte.splitlines() if not l.lstrip().startswith('#'))
    assert 'ORDER BY (ep.minimum_stock - ues.quantity) DESC' not in corpo
    assert 'ep.minimum_stock' not in corpo, \
        'o mínimo corporativo voltou ao caminho de demandas'
