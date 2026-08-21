"""P3-A — escopo de Unidade em Compras: fonte única, com a lista do seletor.

A auditoria achou que NENHUMA rota de listagem de Compras aceitava `unit_id`:
o escopo saía inteiro do ator. O Administrador Geral recebia a empresa toda
sem como filtrar, e Comprador/Aprovador com carteira múltipla recebiam as
Unidades FUNDIDAS numa lista só, sem como alternar.

Esta fatia entrega o contrato — `scope` + `available_units` + `allows_all_units`
— e corrige três defeitos que a auditoria numerou:

- **L4**: o KPI `pending_purchases` do Dashboard ignorava a Unidade
  selecionada; era o único número do painel surdo ao seletor que já existia.
- **L5**: `filters.units` não respeitava a carteira — um Comprador de A via
  B e C entre as opções.
- **L7**: `get_actor_purchase_unit_scope` aceitava `general_admin` e
  consultava com `role_type='buyer'`, restringindo silenciosamente quem
  deveria enxergar a empresa inteira.

A regra travada aqui: **o vínculo é a carteira de atuação e pode ser
múltiplo; a transação não.** "Todas as minhas Unidades" consolida a carteira
e nunca a empresa.
"""

import sqlite3

import pytest

from core.repository import UnitSelection, resolve_purchase_unit_scope
from modules.purchases.service import (
    build_purchase_scope_payload,
    get_actor_purchase_unit_scope,
)

A, B, C, ALHEIA = 10, 11, 12, 90

MASTER = {'id': 1, 'role': 'master_admin', 'company_id': None}
GERAL = {'id': 2, 'role': 'general_admin', 'company_id': 1, 'linked_employee_id': 60}
REGISTRO = {'id': 3, 'role': 'registry_admin', 'company_id': 1}
LOCAL = {'id': 4, 'role': 'admin', 'company_id': 1, 'linked_employee_id': 70}
COMPRADOR_ABC = {'id': 5, 'role': 'buyer', 'company_id': 1, 'linked_employee_id': 50}
COMPRADOR_SO_A = {'id': 6, 'role': 'buyer', 'company_id': 1, 'linked_employee_id': 51}
APROVADOR_AB = {'id': 7, 'role': 'approver', 'company_id': 1, 'linked_employee_id': 52}
SEM_CARTEIRA = {'id': 8, 'role': 'buyer', 'company_id': 1, 'linked_employee_id': 53}


@pytest.fixture()
def conn():
    c = sqlite3.connect(':memory:')
    c.row_factory = sqlite3.Row
    c.executescript(
        """
        CREATE TABLE companies (id INTEGER PRIMARY KEY, name TEXT);
        CREATE TABLE units (id INTEGER PRIMARY KEY, company_id INTEGER, name TEXT,
                            legal_entity_id INTEGER);
        CREATE TABLE employees (id INTEGER PRIMARY KEY, company_id INTEGER, unit_id INTEGER, name TEXT);
        CREATE TABLE purchase_role_unit_links (
            id INTEGER PRIMARY KEY AUTOINCREMENT, company_id INTEGER, employee_id INTEGER,
            role_type TEXT, unit_id INTEGER);
        -- `actor_operational_unit_id` honra movimentação temporária vigente.
        -- Sem linhas: o perfil travado fica na unidade de cadastro.
        CREATE TABLE employee_unit_movements (
            id INTEGER PRIMARY KEY AUTOINCREMENT, employee_id INTEGER,
            target_unit_id INTEGER, movement_type TEXT,
            start_date TEXT, end_date TEXT);
        """
    )
    c.execute("INSERT INTO companies VALUES (1, 'Norskan'), (2, 'Outra')")
    c.executemany(
        'INSERT INTO units (id, company_id, name, legal_entity_id) VALUES (?, ?, ?, ?)',
        [(A, 1, 'Unidade A', 3), (B, 1, 'Unidade B', 3), (C, 1, 'Unidade C', 4),
         (ALHEIA, 2, 'Unidade de Outro Tenant', 9)],
    )
    c.execute('INSERT INTO employees (id, company_id, unit_id, name) VALUES (70, 1, ?, ?)', (A, 'Local'))
    c.executemany(
        'INSERT INTO purchase_role_unit_links (company_id, employee_id, role_type, unit_id) VALUES (?, ?, ?, ?)',
        [(1, 50, 'buyer', A), (1, 50, 'buyer', B), (1, 50, 'buyer', C),
         (1, 51, 'buyer', A),
         (1, 52, 'approver', A), (1, 52, 'approver', B)],
    )
    return c


def _escopo(conn, actor, pedido=None):
    return resolve_purchase_unit_scope(
        conn, actor, pedido, purchase_units_loader=get_actor_purchase_unit_scope,
    )


def _fetch_units(conn, actor):
    return [dict(r) for r in conn.execute('SELECT * FROM units ORDER BY id').fetchall()]


def _opcoes(conn, actor, pedido=None):
    payload = build_purchase_scope_payload(
        conn, actor, _escopo(conn, actor, pedido), fetch_units_fn=_fetch_units)
    return [u['id'] for u in payload['available_units']]


# ── carteira múltipla: alternar entre as Unidades autorizadas ────────────────

def test_comprador_com_tres_unidades_ve_as_tres_no_seletor(conn):
    assert _opcoes(conn, COMPRADOR_ABC) == [A, B, C]


def test_comprador_sem_selecao_cai_em_purchase_scope_e_nao_em_none(conn):
    """`none` significa empresa inteira. Comprador nunca pode chegar lá."""
    escopo = _escopo(conn, COMPRADOR_ABC)
    assert escopo.source == 'purchase_scope'
    assert escopo.unit_id is None
    assert escopo.allowed_unit_ids == (A, B, C)


def test_todas_as_minhas_unidades_e_oferecida_a_partir_de_duas(conn):
    assert _escopo(conn, COMPRADOR_ABC).allows_all_units is True
    assert _escopo(conn, APROVADOR_AB).allows_all_units is True


@pytest.mark.parametrize('unidade', [A, B, C])
def test_comprador_alterna_entre_as_unidades_da_carteira(conn, unidade):
    escopo = _escopo(conn, COMPRADOR_ABC, unidade)
    assert (escopo.unit_id, escopo.source) == (unidade, 'selected')


def test_aprovador_so_alterna_dentro_da_propria_carteira(conn):
    assert _opcoes(conn, APROVADOR_AB) == [A, B]
    assert _escopo(conn, APROVADOR_AB, B).unit_id == B


# ── carteira de uma Unidade: pré-selecionada, sem "Todas" ────────────────────

def test_comprador_de_uma_unidade_ja_vem_pre_selecionado(conn):
    escopo = _escopo(conn, COMPRADOR_SO_A)
    assert (escopo.unit_id, escopo.source) == (A, 'selected')
    assert escopo.allows_all_units is False, 'não há o que consolidar com uma Unidade só'
    assert _opcoes(conn, COMPRADOR_SO_A) == [A]


# ── fail-closed ──────────────────────────────────────────────────────────────

def test_carteira_vazia_nao_enxerga_nada_e_nunca_a_empresa(conn):
    escopo = _escopo(conn, SEM_CARTEIRA)
    assert escopo.allowed_unit_ids == ()
    assert escopo.blocks_everything is True
    assert escopo.allows_all_units is False
    assert _opcoes(conn, SEM_CARTEIRA) == []


def test_carteira_vazia_e_sem_restricao_nao_se_confundem(conn):
    """`()` e `None` são opostos; distingui-los por truthiness inverteria tudo."""
    vazia = _escopo(conn, SEM_CARTEIRA)
    livre = _escopo(conn, GERAL)
    assert vazia.allowed_unit_ids == () and livre.allowed_unit_ids is None
    assert not vazia.allowed_unit_ids and not livre.allowed_unit_ids, \
        'ambos são falsy — é exatamente por isso que a checagem precisa ser `is None`'
    assert vazia.blocks_everything is True
    assert livre.blocks_everything is False
    assert vazia.permits(A) is False
    assert livre.permits(A) is True


def test_unidade_fora_da_carteira_e_403(conn):
    with pytest.raises(PermissionError):
        _escopo(conn, APROVADOR_AB, C)


def test_unidade_de_outro_tenant_e_400(conn):
    """Erro diferente de propósito: identificador inválido, não direito negado."""
    with pytest.raises(ValueError):
        _escopo(conn, COMPRADOR_ABC, ALHEIA)


def test_unidade_inexistente_e_400(conn):
    with pytest.raises(ValueError):
        _escopo(conn, GERAL, 9999)


@pytest.mark.parametrize('lixo', ['abc', '0', '-5'])
def test_identificador_invalido_e_400(conn, lixo):
    with pytest.raises(ValueError):
        _escopo(conn, GERAL, lixo)


# ── perfis administrativos ───────────────────────────────────────────────────

def test_administrador_geral_ve_todas_as_unidades_da_empresa(conn):
    escopo = _escopo(conn, GERAL)
    assert (escopo.unit_id, escopo.source) == (None, 'none')
    assert escopo.allows_all_units is True
    assert escopo.allowed_unit_ids is None
    assert _opcoes(conn, GERAL) == [A, B, C], 'a Unidade de outro tenant não pode entrar'


def test_administrador_geral_com_vinculo_de_comprador_nao_e_restringido(conn):
    """L7: o vínculo acidental restringia silenciosamente quem não tem carteira."""
    conn.execute(
        'INSERT INTO purchase_role_unit_links (company_id, employee_id, role_type, unit_id) '
        "VALUES (1, 60, 'buyer', ?)", (A,))
    assert get_actor_purchase_unit_scope(conn, GERAL) is None
    assert _opcoes(conn, GERAL) == [A, B, C]


def test_administrador_de_registro_tambem_escolhe_livremente(conn):
    assert _escopo(conn, REGISTRO).allows_all_units is True


def test_master_admin_nao_e_barrado_pela_empresa(conn):
    escopo = _escopo(conn, MASTER, ALHEIA)
    assert (escopo.unit_id, escopo.source) == (ALHEIA, 'selected')


# ── perfil travado ───────────────────────────────────────────────────────────

def test_perfil_travado_fica_na_propria_unidade_sem_opcao_todas(conn):
    escopo = _escopo(conn, LOCAL)
    assert (escopo.unit_id, escopo.source, escopo.locked) == (A, 'actor', True)
    assert escopo.allows_all_units is False
    assert _opcoes(conn, LOCAL) == [A]


def test_perfil_travado_ignora_a_unidade_pedida_em_vez_de_recusar(conn):
    """Cliente desatualizado não vira erro; a autorização segue no servidor."""
    assert _escopo(conn, LOCAL, B).unit_id == A


def test_perfil_travado_sem_unidade_e_fail_closed(conn):
    orfao = {'id': 9, 'role': 'admin', 'company_id': 1, 'linked_employee_id': 999}
    with pytest.raises(PermissionError):
        _escopo(conn, orfao)


# ── o contrato publicado ─────────────────────────────────────────────────────

def test_o_payload_tem_a_forma_do_contrato(conn):
    payload = build_purchase_scope_payload(
        conn, COMPRADOR_ABC, _escopo(conn, COMPRADOR_ABC, B), fetch_units_fn=_fetch_units)
    assert payload['scope'] == {
        'company_id': 1, 'unit_id': B, 'unit_scope_source': 'selected', 'locked': False,
    }
    assert payload['allows_all_units'] is True
    assert payload['available_units'][0] == {'id': A, 'name': 'Unidade A', 'legal_entity_id': 3}


def test_as_quatro_origens_existem_e_sao_distintas(conn):
    origens = {
        _escopo(conn, LOCAL).source,
        _escopo(conn, COMPRADOR_ABC, A).source,
        _escopo(conn, COMPRADOR_ABC).source,
        _escopo(conn, GERAL).source,
    }
    assert origens == {'actor', 'selected', 'purchase_scope', 'none'}


def test_unit_selection_e_um_tipo_proprio(conn):
    assert isinstance(_escopo(conn, GERAL), UnitSelection)
