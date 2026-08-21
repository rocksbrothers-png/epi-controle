"""P1 — Comprador/Aprovador só cria PR/PO nas Unidades da própria carteira.

`ensure_purchase_request_action_scope` e `ensure_purchase_order_action_scope`
já validavam a Unidade de um registro EXISTENTE. A criação não passava por
nenhuma das duas: as rotas só checavam a Unidade para os perfis travados
(`admin`/`user`), e o serviço fazia apenas `ensure_resource_company`.

Resultado: um Comprador vinculado à Unidade A criava PR/PO para a Unidade B.
Ele era barrado na ação seguinte — mas o registro já existia na Unidade
errada, e um recebimento creditaria o estoque de B.

Regra travada aqui: o vínculo em `purchase_role_unit_links` é a CARTEIRA de
atuação e pode ser múltiplo; a transação não. Vínculo em A, B e C deixa a
pessoa agir nas três, e não soma nada entre as três.
"""

import sqlite3

import pytest

from modules.purchases.service import purchase_creation_unit_scope_violation

MASTER = {'id': 1, 'role': 'master_admin', 'company_id': 1}
GERAL = {'id': 2, 'role': 'general_admin', 'company_id': 1}
LOCAL = {'id': 3, 'role': 'admin', 'company_id': 1, 'linked_employee_id': 60}
GESTOR = {'id': 4, 'role': 'user', 'company_id': 1, 'linked_employee_id': 61}
COMPRADOR = {'id': 5, 'role': 'buyer', 'company_id': 1, 'linked_employee_id': 50}
APROVADOR = {'id': 6, 'role': 'approver', 'company_id': 1, 'linked_employee_id': 51}
SEM_VINCULO = {'id': 7, 'role': 'buyer', 'company_id': 1, 'linked_employee_id': 52}

TRAVADO = 'Mensagem do perfil travado.'

UNIDADE_A, UNIDADE_B, UNIDADE_C = 1, 2, 3


@pytest.fixture()
def conn():
    connection = sqlite3.connect(':memory:')
    connection.row_factory = sqlite3.Row
    connection.executescript(
        """
        CREATE TABLE purchase_role_unit_links (
            id INTEGER PRIMARY KEY AUTOINCREMENT, company_id INTEGER, employee_id INTEGER,
            role_type TEXT, unit_id INTEGER, created_by_user_id INTEGER, created_at TEXT
        );
        """
    )
    # Carteira MÚLTIPLA: o comprador atua em A, B e C; o aprovador só em A.
    connection.executemany(
        'INSERT INTO purchase_role_unit_links (company_id, employee_id, role_type, unit_id) VALUES (?, ?, ?, ?)',
        [
            (1, 50, 'buyer', UNIDADE_A),
            (1, 50, 'buyer', UNIDADE_B),
            (1, 50, 'buyer', UNIDADE_C),
            (1, 51, 'approver', UNIDADE_A),
        ],
    )
    return connection


def _unidade_operacional(esperada):
    """Stub de `actor_operational_unit_id` para os perfis travados."""
    return lambda connection, actor: esperada


def _violacao(conn, actor, unit_id, *, unidade_operacional=None):
    return purchase_creation_unit_scope_violation(
        conn, actor, unit_id,
        actor_operational_unit_id=_unidade_operacional(unidade_operacional),
        locked_profile_message=TRAVADO,
    )


# ── carteira múltipla: pode nas vinculadas ───────────────────────────────────

@pytest.mark.parametrize('unidade', [UNIDADE_A, UNIDADE_B, UNIDADE_C])
def test_comprador_cria_em_qualquer_unidade_da_carteira(conn, unidade):
    assert _violacao(conn, COMPRADOR, unidade) == ''


def test_comprador_nao_cria_fora_da_carteira(conn):
    assert _violacao(conn, COMPRADOR, 99) == \
        'Unidade fora das unidades de compras vinculadas ao usuário.'


def test_aprovador_com_carteira_de_uma_unidade_so_cria_nela(conn):
    assert _violacao(conn, APROVADOR, UNIDADE_A) == ''
    assert _violacao(conn, APROVADOR, UNIDADE_B) != ''


def test_o_vinculo_de_comprador_nao_serve_de_vinculo_de_aprovador(conn):
    """`role_type` faz parte da chave: papéis não se emprestam carteira."""
    outro_aprovador = {'id': 8, 'role': 'approver', 'company_id': 1, 'linked_employee_id': 50}
    assert _violacao(conn, outro_aprovador, UNIDADE_A) == 'Usuário sem unidade de compras vinculada.'


# ── fail-closed ──────────────────────────────────────────────────────────────

def test_comprador_sem_nenhum_vinculo_nao_cria_em_lugar_nenhum(conn):
    for unidade in (UNIDADE_A, UNIDADE_B, UNIDADE_C, 99):
        assert _violacao(conn, SEM_VINCULO, unidade) == 'Usuário sem unidade de compras vinculada.'


def test_sem_vinculo_nunca_significa_empresa_inteira(conn):
    """O antipadrão que a auditoria procurava: ausência virando permissão."""
    conn.execute('DELETE FROM purchase_role_unit_links')
    assert _violacao(conn, COMPRADOR, UNIDADE_A) != ''


# ── perfis travados: comportamento preservado ────────────────────────────────

@pytest.mark.parametrize('actor', [LOCAL, GESTOR])
def test_perfil_travado_cria_apenas_na_propria_unidade(conn, actor):
    assert _violacao(conn, actor, UNIDADE_A, unidade_operacional=UNIDADE_A) == ''
    assert _violacao(conn, actor, UNIDADE_B, unidade_operacional=UNIDADE_A) == TRAVADO


@pytest.mark.parametrize('actor', [LOCAL, GESTOR])
def test_perfil_travado_sem_unidade_e_fail_closed(conn, actor):
    assert _violacao(conn, actor, UNIDADE_A, unidade_operacional=None) == TRAVADO


def test_a_mensagem_do_perfil_travado_vem_de_quem_chama(conn):
    """PR e PO têm textos diferentes; o helper não escolhe por conta própria."""
    assert purchase_creation_unit_scope_violation(
        conn, LOCAL, UNIDADE_B,
        actor_operational_unit_id=_unidade_operacional(UNIDADE_A),
        locked_profile_message='texto-da-PO',
    ) == 'texto-da-PO'


# ── quem não é do universo de Compras ────────────────────────────────────────

def test_master_admin_passa(conn):
    assert _violacao(conn, MASTER, 99) == ''


def test_administrador_geral_nao_e_restringido_por_carteira(conn):
    """A empresa dele já é validada por `ensure_resource_company` na rota."""
    for unidade in (UNIDADE_A, UNIDADE_B, 99):
        assert _violacao(conn, GERAL, unidade) == ''


# ── as rotas de criação usam o helper ────────────────────────────────────────

def test_as_duas_rotas_de_criacao_chamam_a_checagem():
    """Leitura estrutural: o helper não pode ficar sem chamador.

    A checagem antiga era inline e cobria só `admin`/`user`. Se ela voltar,
    este teste reprova.
    """
    from pathlib import Path
    rotas = Path(__file__).resolve().parents[1] / 'modules' / 'purchases' / 'routes.py'
    corpo = rotas.read_text(encoding='utf-8')
    assert '    purchase_creation_unit_scope_violation,\n' in corpo, 'o helper não é importado'
    assert corpo.count('purchase_creation_unit_scope_violation(') == 2, \
        'esperado: 1 chamada em PR + 1 chamada em PO'
    # As duas mensagens de criação só podem aparecer como argumento do helper.
    # Se voltarem coladas num `if` inline, a cobertura de Comprador/Aprovador
    # se perde de novo. (Outras rotas usam o mesmo idioma legitimamente — por
    # isso a varredura é pelas mensagens, não pelo formato do `if`.)
    for mensagem in (
        'Administrador local pode criar requisições apenas para sua própria unidade operacional.',
        'Usuário pode criar PO apenas para sua unidade operacional.',
    ):
        assert f"locked_profile_message='{mensagem}'" in corpo, mensagem


def test_a_po_valida_escopo_antes_de_validar_epis():
    """Quem não pode criar na Unidade não descobre os EPIs dela por tabela."""
    from pathlib import Path
    rotas = (Path(__file__).resolve().parents[1] / 'modules' / 'purchases' / 'routes.py').read_text(encoding='utf-8')
    trecho = rotas[rotas.index('def handle_post_purchase_orders'):]
    trecho = trecho[:trecho.index('def ', 10)]
    assert trecho.index('purchase_creation_unit_scope_violation(') < trecho.index('ensure_epi_operational(')
