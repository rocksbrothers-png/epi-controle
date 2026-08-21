"""P3-A — L4 e L5: o Dashboard passa a respeitar o próprio seletor.

O Dashboard já tinha seletor de Unidade e já publicava `scope` +
`filters.units`. Dois furos, achados na auditoria:

**L4** — `count_pending_purchases()` era chamado sem argumento nenhum e
re-derivava o escopo a partir do ator. Selecionar uma Unidade mudava todos os
KPIs do painel, menos o de Compras. O número ficava certo para o ator e
errado para a pergunta que ele acabara de fazer.

**L5** — `filters.units` era recortado só por `escopo.locked`. Um Comprador
vinculado à Unidade A recebia B e C entre as opções — Unidades onde ele não
pode agir e cuja seleção o servidor recusaria.

Estes testes exercitam `build_dashboard_summary` de verdade, com dublês
injetados, do mesmo jeito que o resto de `test_dashboard_summary.py`.
"""

from contextlib import contextmanager
import sqlite3

import pytest

from modules.dashboard.service import build_dashboard_summary
from modules.purchases.service import narrow_purchase_unit_to_selection

A, B, C = 10, 11, 12

GERAL = {'id': 2, 'role': 'general_admin', 'company_id': 1, 'linked_employee_id': None}
GESTOR_A = {'id': 5, 'role': 'user', 'company_id': 1, 'linked_employee_id': 50}
COMPRADOR_A = {'id': 7, 'role': 'buyer', 'company_id': 1, 'linked_employee_id': 51}

UNIDADES = [
    {'id': A, 'company_id': 1, 'legal_entity_id': 4, 'name': 'Skandi Paraty'},
    {'id': B, 'company_id': 1, 'legal_entity_id': 4, 'name': 'Skandi Amazonas'},
    {'id': C, 'company_id': 1, 'legal_entity_id': 5, 'name': 'Norskan Alpha'},
]


class _PgStyleConn:
    """Traduz `%s` para `?`, como o wrapper de Postgres em produção.

    Mesmo molde de `test_dashboard_summary.py`: várias consultas do projeto
    têm `%s` fixo no texto e quebram contra sqlite direto.
    """

    def __init__(self, conn):
        self._conn = conn

    def execute(self, sql, params=()):
        return self._conn.execute(str(sql).replace('%s', '?'), params)

    def __getattr__(self, name):
        return getattr(self._conn, name)


@contextmanager
def _conexao():
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        CREATE TABLE employees (id INTEGER PRIMARY KEY, company_id INTEGER, unit_id INTEGER);
        CREATE TABLE employee_unit_movements (
            id INTEGER PRIMARY KEY AUTOINCREMENT, employee_id INTEGER,
            target_unit_id INTEGER, movement_type TEXT, start_date TEXT, end_date TEXT);
        CREATE TABLE units (id INTEGER PRIMARY KEY, company_id INTEGER,
                            legal_entity_id INTEGER, name TEXT);
        CREATE TABLE unit_joint_venture_periods (
            id INTEGER PRIMARY KEY AUTOINCREMENT, company_id INTEGER, unit_id INTEGER,
            joint_venture_name TEXT, started_at TEXT, ended_at TEXT DEFAULT '',
            created_by INTEGER);
        """
    )
    conn.execute('INSERT INTO employees (id, company_id, unit_id) VALUES (50, 1, ?)', (A,))
    # `resolve_unit_scope` valida a Unidade pedida contra a TABELA, não contra
    # a lista devolvida por `fetch_units` — as duas precisam concordar.
    conn.executemany(
        'INSERT INTO units (id, company_id, legal_entity_id, name) VALUES (?, ?, ?, ?)',
        [(u['id'], u['company_id'], u['legal_entity_id'], u['name']) for u in UNIDADES],
    )
    try:
        yield _PgStyleConn(conn)
    finally:
        conn.close()


def _resumo(conn, actor, *, unit_id=None, carteira=None, kpi=None):
    """`kpi` recebe a Unidade resolvida e devolve o que quiser — assim dá para
    observar COM QUE argumento o KPI foi chamado, que é o cerne da L4."""
    return build_dashboard_summary(
        conn, actor,
        requested_unit_id=unit_id,
        purchase_scope_units=carteira,
        fetch_units=lambda c, a: list(UNIDADES),
        fetch_employees=lambda c, a: [],
        fetch_epis=lambda c, a, u: [],
        fetch_deliveries=lambda c, a: [],
        fetch_legal_entities=lambda c, a: [],
        compute_alerts=lambda c, a: [],
        compute_stock_compliance=lambda c, cid, uid: {'summary': {}},
        count_pending_purchases=kpi or (lambda unidade=None: 0),
    )


# ── L4: o KPI de Compras segue o seletor ─────────────────────────────────────

def test_o_kpi_de_compras_recebe_a_unidade_selecionada():
    visto = []
    with _conexao() as conn:
        _resumo(conn, GERAL, unit_id=str(B),
                kpi=lambda unidade=None: visto.append(unidade) or 0)
    assert visto == [B], 'o KPI continuou surdo à Unidade escolhida'


def test_sem_selecao_o_kpi_recebe_none_e_mantem_a_visao_do_ator():
    visto = []
    with _conexao() as conn:
        _resumo(conn, GERAL, kpi=lambda unidade=None: visto.append(unidade) or 0)
    assert visto == [None]


def test_para_perfil_travado_o_kpi_recebe_a_unidade_do_ator():
    """Travado não escolhe, mas o KPI também não pode ficar sem escopo."""
    visto = []
    with _conexao() as conn:
        _resumo(conn, GESTOR_A, unit_id=str(C),
                kpi=lambda unidade=None: visto.append(unidade) or 0)
    assert visto == [A], 'a Unidade pedida deveria ter sido descartada em favor da do ator'


def test_o_kpi_e_o_scope_falam_da_mesma_unidade():
    visto = []
    with _conexao() as conn:
        resumo = _resumo(conn, GERAL, unit_id=str(C),
                         kpi=lambda unidade=None: visto.append(unidade) or 0)
    assert visto == [resumo['scope']['unit_id']]


# ── L4: a seleção só prevalece se estiver na carteira ────────────────────────
#
# A regra vive em `narrow_purchase_unit_to_selection` porque, dentro da
# closure da rota, ela não era exercitável: uma sabotagem que apagasse a linha
# deixava os testes acima todos verdes. Eles cobrem o SERVIÇO passando a
# Unidade adiante; estes cobrem o que a rota faz com ela.

def test_sem_selecao_prevalece_o_escopo_do_ator():
    assert narrow_purchase_unit_to_selection(A, None, None) == A
    assert narrow_purchase_unit_to_selection(None, None, [A, B]) is None


def test_sem_carteira_a_selecao_prevalece():
    assert narrow_purchase_unit_to_selection(None, B, None) == B


def test_selecao_dentro_da_carteira_prevalece():
    assert narrow_purchase_unit_to_selection(None, B, [A, B]) == B


def test_selecao_fora_da_carteira_e_descartada():
    """O seletor esconde C; a API precisa recusá-la mesmo assim."""
    assert narrow_purchase_unit_to_selection(None, C, [A, B]) is None
    assert narrow_purchase_unit_to_selection(A, C, [A, B]) == A


def test_carteira_vazia_descarta_qualquer_selecao():
    assert narrow_purchase_unit_to_selection(None, A, []) is None


@pytest.mark.parametrize('vazio', [None, '', 0])
def test_selecao_ausente_em_qualquer_forma_nao_altera_o_escopo(vazio):
    assert narrow_purchase_unit_to_selection(A, vazio, [A, B]) == A


def test_a_unidade_selecionada_pode_vir_como_texto():
    """A query string entrega string; a comparação com a carteira é numérica."""
    assert narrow_purchase_unit_to_selection(None, str(B), [A, B]) == B
    assert narrow_purchase_unit_to_selection(None, str(C), [A, B]) is None


# ── L5: as opções do filtro respeitam a carteira ─────────────────────────────

def _opcoes(resumo):
    return [u['id'] for u in resumo['filters']['units']]


def test_comprador_so_ve_as_unidades_da_carteira_no_filtro():
    with _conexao() as conn:
        resumo = _resumo(conn, COMPRADOR_A, carteira=[A])
    assert _opcoes(resumo) == [A], 'o Comprador voltou a ver Unidades onde não pode agir'


def test_carteira_com_duas_unidades_mostra_as_duas():
    with _conexao() as conn:
        resumo = _resumo(conn, COMPRADOR_A, carteira=[A, C])
    assert _opcoes(resumo) == [A, C]


def test_carteira_vazia_nao_abre_para_a_empresa():
    """`()` é "não enxerga nenhuma", não "sem restrição"."""
    with _conexao() as conn:
        resumo = _resumo(conn, COMPRADOR_A, carteira=[])
    assert _opcoes(resumo) == []


def test_sem_carteira_o_administrador_ve_todas():
    with _conexao() as conn:
        resumo = _resumo(conn, GERAL, carteira=None)
    assert _opcoes(resumo) == [A, B, C]


def test_perfil_travado_continua_vendo_so_a_propria():
    with _conexao() as conn:
        resumo = _resumo(conn, GESTOR_A)
    assert _opcoes(resumo) == [A]


def test_travamento_manda_mais_que_carteira():
    """Perfil travado com carteira (configuração incoerente) não ganha opções."""
    with _conexao() as conn:
        resumo = _resumo(conn, GESTOR_A, carteira=[A, B, C])
    assert _opcoes(resumo) == [A]
