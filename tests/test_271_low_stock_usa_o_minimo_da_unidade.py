"""`/api/stock/low` decide pelo mínimo DA UNIDADE — regressão funcional (#271).

Esta suíte existe por causa de um buraco que a auditoria de 26/08 encontrou:
`fetch_low_stock_items` foi migrado para `classify_unit_epi_stock`, mas
**nenhum teste reprovava a reversão**. Trocar

    minimum = classificacao.effective_minimum_stock

por `minimum = int(row['minimum_stock'] or 0)` — o mínimo da EMPRESA — passava
a suíte inteira. O consumidor mais consequente da frente ficou sem rede: é ele
que alimenta o card "Estoque crítico" do Web Legado, os alertas e o KPI do
Dashboard.

Os testes abaixo são **funcionais**, não estruturais: montam saldo e
configuração num SQLite em memória e olham o que a função devolve. Um teste que
lesse o texto do arquivo cairia na mesma armadilha dos gates anteriores, que
passaram a ser satisfeitos por comentários.

## O contrato de dois caminhos

`/api/stock/low` significa **abaixo do mínimo** para os seus consumidores, e o
Web Legado conta `state.lowStock.length` no card **"Estoque crítico"**. Incluir
a faixa de atenção ali inflaria um KPI cujo rótulo diz outra coisa. Por isso:

    include_near_minimum=False  (padrão)  → só `critical`
    include_near_minimum=True   (alertas) → `critical` + `near_minimum`

`disabled` fica de fora dos dois: monitoramento desligado pela Unidade não
gera alerta, não entra em KPI e não dispara reposição.
"""

import sqlite3

import pytest

from epi_backend.epi_scope import is_epi_visible_for_unit
from modules.employees.service import actor_operational_unit_id
from modules.stock.service import (
    MINIMUM_SOURCE_COMPANY,
    MINIMUM_SOURCE_UNIT,
    STATUS_CRITICAL,
    STATUS_NEAR_MINIMUM,
    fetch_low_stock_items,
)
from modules.units.service import get_unit_active_jv_name

EMPRESA = 1
UNIDADE = 10
EPI = 101

#: Mínimo corporativo do EPI. Deliberadamente **divergente** do mínimo da
#: Unidade em quase todos os cenários: se ele voltar a decidir, o resultado
#: muda e o teste reprova.
MINIMO_CORPORATIVO = 100


class Conexao:
    """Traduz `%s` para `?`, como o wrapper de Postgres faz em produção."""

    def __init__(self, conn):
        self._conn = conn

    def execute(self, sql, params=()):
        return self._conn.execute(str(sql).replace('%s', '?'), params)

    def __getattr__(self, name):
        return getattr(self._conn, name)


def _banco():
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.executescript(
        '''
        CREATE TABLE companies (id INTEGER PRIMARY KEY, name TEXT);
        CREATE TABLE units (id INTEGER PRIMARY KEY, company_id INTEGER, name TEXT);
        CREATE TABLE epis (
            id INTEGER PRIMARY KEY, company_id INTEGER NOT NULL, unit_id INTEGER,
            name TEXT, minimum_stock INTEGER, unit_measure TEXT,
            active INTEGER DEFAULT 1, active_joinventure TEXT
        );
        CREATE TABLE unit_epi_stock (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL, unit_id INTEGER NOT NULL, epi_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 0, updated_at TEXT
        );
        CREATE TABLE unit_epi_minimum_stock (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL, unit_id INTEGER NOT NULL, epi_id INTEGER NOT NULL,
            minimum_stock INTEGER NOT NULL DEFAULT 0,
            created_by_user_id INTEGER, updated_by_user_id INTEGER,
            created_at TEXT NOT NULL DEFAULT '', updated_at TEXT NOT NULL DEFAULT '',
            UNIQUE (company_id, unit_id, epi_id)
        );
        CREATE TABLE company_stock_attention_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL UNIQUE,
            attention_percentage INTEGER NOT NULL DEFAULT 20,
            updated_by_user_id INTEGER,
            created_at TEXT NOT NULL DEFAULT '', updated_at TEXT NOT NULL DEFAULT ''
        );
        CREATE TABLE unit_epi_attention_percentage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL, unit_id INTEGER NOT NULL, epi_id INTEGER NOT NULL,
            attention_percentage INTEGER NOT NULL DEFAULT 0,
            created_by_user_id INTEGER, updated_by_user_id INTEGER,
            created_at TEXT NOT NULL DEFAULT '', updated_at TEXT NOT NULL DEFAULT '',
            UNIQUE (company_id, unit_id, epi_id)
        );
        CREATE TABLE unit_epi_stock_alert_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL, unit_id INTEGER NOT NULL, epi_id INTEGER NOT NULL,
            alert_enabled INTEGER NOT NULL DEFAULT 1,
            created_by_user_id INTEGER, updated_by_user_id INTEGER,
            created_at TEXT NOT NULL DEFAULT '', updated_at TEXT NOT NULL DEFAULT '',
            UNIQUE (company_id, unit_id, epi_id)
        );
        CREATE TABLE unit_joint_venture_periods (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            unit_id INTEGER NOT NULL, joint_venture_name TEXT,
            started_at TEXT, ended_at TEXT
        );
        '''
    )
    conn.execute("INSERT INTO companies (id, name) VALUES (?, 'Empresa')", (EMPRESA,))
    conn.execute("INSERT INTO units (id, company_id, name) VALUES (?, ?, 'Unidade A')",
                 (UNIDADE, EMPRESA))
    conn.execute(
        'INSERT INTO epis (id, company_id, unit_id, name, minimum_stock, unit_measure, active) '
        "VALUES (?, ?, NULL, 'Capacete', ?, 'unidade', 1)",
        (EPI, EMPRESA, MINIMO_CORPORATIVO),
    )
    conn.commit()
    return conn


def _cenario(saldo, *, minimo_da_unidade=None, percentual=None, alerta=None):
    """Monta o estado e devolve a conexão pronta.

    `None` significa **ausência de linha**, que é como a herança do padrão da
    empresa é representada — não há valor-sentinela.
    """
    conn = _banco()
    conn.execute(
        'INSERT INTO unit_epi_stock (company_id, unit_id, epi_id, quantity) VALUES (?, ?, ?, ?)',
        (EMPRESA, UNIDADE, EPI, saldo),
    )
    if minimo_da_unidade is not None:
        conn.execute(
            'INSERT INTO unit_epi_minimum_stock (company_id, unit_id, epi_id, minimum_stock) '
            'VALUES (?, ?, ?, ?)',
            (EMPRESA, UNIDADE, EPI, minimo_da_unidade),
        )
    if percentual is not None:
        conn.execute(
            'INSERT INTO unit_epi_attention_percentage '
            '(company_id, unit_id, epi_id, attention_percentage) VALUES (?, ?, ?, ?)',
            (EMPRESA, UNIDADE, EPI, percentual),
        )
    if alerta is not None:
        conn.execute(
            'INSERT INTO unit_epi_stock_alert_settings '
            '(company_id, unit_id, epi_id, alert_enabled) VALUES (?, ?, ?, ?)',
            (EMPRESA, UNIDADE, EPI, 1 if alerta else 0),
        )
    conn.commit()
    return conn


def _baixos(conn, *, incluir_atencao=False):
    return fetch_low_stock_items(
        Conexao(conn),
        None,
        actor_operational_unit_id=actor_operational_unit_id,
        get_unit_active_jv_name=get_unit_active_jv_name,
        is_epi_visible_for_unit=is_epi_visible_for_unit,
        include_near_minimum=incluir_atencao,
    )


# ═══════════════════════════════════════════════════════════════════════════
# O mínimo que decide é o da Unidade
# ═══════════════════════════════════════════════════════════════════════════

def test_o_saldo_da_unidade_e_comparado_ao_minimo_efetivo_da_unidade():
    """Saldo 30, mínimo da Unidade 20, mínimo da empresa 100.

    Pelo mínimo da Unidade o EPI está saudável. Pelo corporativo estaria
    crítico — e era assim que uma empresa com estoque distribuído gerava
    alerta falso em toda Unidade.
    """
    itens = _baixos(_cenario(30, minimo_da_unidade=20))
    assert itens == [], \
        'o mínimo corporativo voltou a decidir: 30 > 20 na Unidade, e mesmo ' \
        'assim o EPI apareceu como abaixo do mínimo'


def test_o_minimo_corporativo_divergente_nao_entra_na_decisao():
    """O caminho inverso: crítico na Unidade, saudável na empresa.

    Sem este par, um teste passaria trocando as duas fontes — bastaria que a
    comparação fosse feita, não importa contra o quê.
    """
    conn = _cenario(5, minimo_da_unidade=50)
    conn.execute('UPDATE epis SET minimum_stock = 1 WHERE id = ?', (EPI,))
    conn.commit()

    itens = _baixos(conn)
    assert len(itens) == 1, \
        'saldo 5 contra mínimo 50 da Unidade é crítico; o mínimo 1 da empresa ' \
        'não pode absolver'
    assert itens[0]['minimum_stock'] == 50
    assert itens[0]['stock_status'] == STATUS_CRITICAL


def test_o_minimo_devolvido_e_o_da_unidade_e_nao_o_da_empresa():
    """O campo `minimum_stock` da resposta é o mínimo EFETIVO.

    É o que o Web Legado exibe ao lado do saldo. Devolver o corporativo aqui
    mostraria ao operador um número que não governa nada.
    """
    item = _baixos(_cenario(5, minimo_da_unidade=50))[0]
    assert item['minimum_stock'] == 50, \
        f"devolveu {item['minimum_stock']}; o mínimo da Unidade é 50 e o da " \
        f'empresa é {MINIMO_CORPORATIVO}'
    assert item['minimum_stock_source'] == MINIMUM_SOURCE_UNIT


# ═══════════════════════════════════════════════════════════════════════════
# Herança: `unit_configured` sobrepõe `company_default`
# ═══════════════════════════════════════════════════════════════════════════

def test_sem_linha_da_unidade_a_origem_e_o_padrao_da_empresa():
    item = _baixos(_cenario(5))[0]
    assert item['minimum_stock'] == MINIMO_CORPORATIVO
    assert item['minimum_stock_source'] == MINIMUM_SOURCE_COMPANY


def test_configurar_a_unidade_sobrepoe_o_padrao_da_empresa():
    """Mesma empresa, mesmo EPI, mesmo saldo — só a linha da Unidade muda."""
    sem = _baixos(_cenario(5))[0]
    com = _baixos(_cenario(5, minimo_da_unidade=3))

    assert sem['minimum_stock_source'] == MINIMUM_SOURCE_COMPANY
    assert com == [], \
        'com mínimo 3 na Unidade, saldo 5 está acima; a configuração local ' \
        'não sobrepôs o padrão da empresa'


def test_zero_configurado_na_unidade_e_valor_e_nao_ausencia():
    """`0` é decisão: "não monitorar por mínimo nesta Unidade".

    Se `0` fosse lido como ausência de configuração, a herança devolveria o
    mínimo 100 da empresa e o saldo 5 viraria crítico. O teste falha
    exatamente nesse caso.
    """
    itens = _baixos(_cenario(5, minimo_da_unidade=0))
    assert itens == [], \
        'mínimo 0 da Unidade foi tratado como ausência e caiu na herança'


# ═══════════════════════════════════════════════════════════════════════════
# Os dois caminhos: `/api/stock/low` × alertas
# ═══════════════════════════════════════════════════════════════════════════

def test_critico_aparece_nos_dois_caminhos():
    conn_padrao = _cenario(2, minimo_da_unidade=10)
    conn_alertas = _cenario(2, minimo_da_unidade=10)

    assert [i['stock_status'] for i in _baixos(conn_padrao)] == [STATUS_CRITICAL]
    assert [i['stock_status'] for i in _baixos(conn_alertas, incluir_atencao=True)] \
        == [STATUS_CRITICAL]


def test_near_minimum_fica_de_fora_do_padrao():
    """Saldo 11, mínimo 10, faixa de atenção 20% → limite 12. Está na faixa.

    O card "Estoque crítico" do Web Legado conta `state.lowStock.length`.
    Incluir a faixa laranja ali infla um KPI cujo rótulo diz outra coisa —
    por isso o padrão é `critical` apenas.
    """
    conn = _cenario(11, minimo_da_unidade=10, percentual=20)
    assert _baixos(conn) == [], \
        'a faixa de atenção entrou em /api/stock/low e vai inflar o card ' \
        '"Estoque crítico"'


def test_near_minimum_entra_quando_os_alertas_pedem():
    """Mesmo cenário, `include_near_minimum=True`: o alerta laranja existe."""
    conn = _cenario(11, minimo_da_unidade=10, percentual=20)
    itens = _baixos(conn, incluir_atencao=True)
    assert [i['stock_status'] for i in itens] == [STATUS_NEAR_MINIMUM], \
        'a faixa de atenção sumiu do caminho dos alertas — que é a razão de ' \
        'ela existir'


@pytest.mark.parametrize('incluir_atencao', [False, True])
def test_disabled_nunca_e_critico(incluir_atencao):
    """Monitoramento desligado pela Unidade sai dos DOIS caminhos.

    Saldo 0 contra mínimo 10 seria crítico. Com o alerta desligado o EPI não
    gera alerta, não entra em KPI e não dispara reposição — e, sobretudo, não
    vira `normal`: continua visível no Controle de Estoque como desligado.
    """
    conn = _cenario(0, minimo_da_unidade=10, alerta=False)
    assert _baixos(conn, incluir_atencao=incluir_atencao) == [], \
        'EPI com monitoramento desligado apareceu como abaixo do mínimo'


def test_desligar_e_religar_muda_o_desfecho():
    """Controle do teste acima: sem o `alerta=False`, o mesmo saldo reprova.

    Sem este par, `test_disabled_nunca_e_critico` passaria mesmo que a função
    devolvesse lista vazia por qualquer outro motivo.
    """
    itens = _baixos(_cenario(0, minimo_da_unidade=10, alerta=True))
    assert [i['stock_status'] for i in itens] == [STATUS_CRITICAL]
