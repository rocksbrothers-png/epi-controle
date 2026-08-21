"""P3-B — as listagens de Compras passam a aceitar `unit_id`.

A P3-A entregou o contrato; esta fatia liga as consultas nele. Antes, cada
rota montava à mão o par `scope_unit_id` + `purchase_scope_units` e duas
guardas de fail-closed — seis cópias da mesma decisão, que é exatamente como
as três variantes de escopo apareceram no backend.

O que muda para quem consome:

- Administrador Geral pode enviar `unit_id` e receber só aquela Unidade.
  Sem `unit_id`, continua recebendo a empresa (visão consolidada).
- Comprador/Aprovador escolhem dentro da carteira. Sem `unit_id`, recebem a
  carteira consolidada — "Todas as minhas Unidades" —, nunca a empresa.
- Perfil travado: `unit_id` descartado, própria Unidade.

`purchase_listing_scope` devolve `None` só nas duas situações que não são
erro (perfil travado sem unidade; carteira vazia). Unidade fora da carteira
continua 403 e identificador inválido continua 400 — engolir os dois em
lista vazia esconderia de quem pediu a diferença entre "não há nada" e
"você não pode".
"""

import sqlite3

import pytest

from modules.purchases.service import purchase_listing_scope

A, B, C = 10, 11, 12

GERAL = {'id': 2, 'role': 'general_admin', 'company_id': 1, 'linked_employee_id': None}
LOCAL = {'id': 4, 'role': 'admin', 'company_id': 1, 'linked_employee_id': 70}
COMPRADOR_AB = {'id': 5, 'role': 'buyer', 'company_id': 1, 'linked_employee_id': 50}
COMPRADOR_SO_A = {'id': 6, 'role': 'buyer', 'company_id': 1, 'linked_employee_id': 51}
SEM_CARTEIRA = {'id': 8, 'role': 'buyer', 'company_id': 1, 'linked_employee_id': 53}


@pytest.fixture()
def conn():
    c = sqlite3.connect(':memory:')
    c.row_factory = sqlite3.Row
    c.execute('CREATE TABLE units (id INTEGER PRIMARY KEY, company_id INTEGER, name TEXT)')
    c.executemany('INSERT INTO units VALUES (?, ?, ?)',
                  [(A, 1, 'A'), (B, 1, 'B'), (C, 1, 'C'), (90, 2, 'Outro tenant')])
    return c


def _escopo(conn, actor, pedido=None, *, unidade_do_ator=None, carteira=None):
    """As duas dependências são injetadas, como nas rotas."""
    return purchase_listing_scope(
        conn, actor, pedido,
        actor_operational_unit_id=lambda *_a: unidade_do_ator,
        purchase_units_loader=lambda *_a: carteira,
    )


# ── Administrador Geral: consolidado ou uma Unidade ──────────────────────────

def test_administrador_geral_sem_unit_id_ve_a_empresa():
    """Visão consolidada: sem recorte de Unidade."""
    escopo = _escopo(None, GERAL)
    assert escopo.unit_id is None
    assert escopo.allowed_unit_ids is None


def test_administrador_geral_com_unit_id_recorta_naquela_unidade(conn):
    escopo = _escopo(conn, GERAL, B)
    assert escopo.unit_id == B
    assert escopo.source == 'selected'


# ── Comprador/Aprovador: a carteira, nunca a empresa ─────────────────────────

def test_comprador_sem_unit_id_recebe_a_carteira_e_nao_a_empresa():
    escopo = _escopo(None, COMPRADOR_AB, carteira=[A, B])
    assert escopo.unit_id is None
    assert escopo.allowed_unit_ids == (A, B), \
        'o recorte precisa ir para o SQL como IN (A, B), não sumir'
    assert escopo.source == 'purchase_scope'


def test_comprador_escolhe_dentro_da_carteira(conn):
    assert _escopo(conn, COMPRADOR_AB, A, carteira=[A, B]).unit_id == A
    assert _escopo(conn, COMPRADOR_AB, B, carteira=[A, B]).unit_id == B


def test_comprador_de_uma_unidade_ja_vem_recortado():
    assert _escopo(None, COMPRADOR_SO_A, carteira=[A]).unit_id == A


def test_unidade_fora_da_carteira_e_403_e_nao_lista_vazia(conn):
    """Esconder isto em `{'items': []}` faria "não pode" parecer "não há"."""
    with pytest.raises(PermissionError):
        _escopo(conn, COMPRADOR_AB, C, carteira=[A, B])


def test_identificador_invalido_e_400_e_nao_lista_vazia(conn):
    with pytest.raises(ValueError):
        _escopo(conn, GERAL, 'abc')


def test_unidade_de_outro_tenant_e_400(conn):
    with pytest.raises(ValueError):
        _escopo(conn, GERAL, 90)


# ── as duas situações que devolvem lista vazia ───────────────────────────────

def test_carteira_vazia_devolve_none_para_lista_vazia():
    assert _escopo(None, SEM_CARTEIRA, carteira=[]) is None
    assert _escopo(None, SEM_CARTEIRA, carteira=None) is None


def test_perfil_travado_sem_unidade_devolve_none_para_lista_vazia():
    assert _escopo(None, LOCAL, unidade_do_ator=None) is None


def test_carteira_vazia_nunca_vira_empresa_inteira():
    """O antipadrão: `()` é falsy e viraria "sem restrição" num `if`."""
    assert _escopo(None, SEM_CARTEIRA, carteira=[]) is None, \
        'carteira vazia caiu na visão corporativa'


# ── perfil travado ───────────────────────────────────────────────────────────

def test_perfil_travado_ignora_a_unidade_pedida(conn):
    assert _escopo(conn, LOCAL, C, unidade_do_ator=A).unit_id == A


def test_perfil_travado_fica_na_propria_unidade():
    escopo = _escopo(None, LOCAL, unidade_do_ator=A)
    assert (escopo.unit_id, escopo.locked) == (A, True)


# ── injeção obrigatória ──────────────────────────────────────────────────────

def test_esquecer_uma_dependencia_e_erro_e_nao_escopo_mais_amplo():
    """Fail-open silencioso é o modo de falha que este desenho proíbe."""
    with pytest.raises(TypeError):
        purchase_listing_scope(None, GERAL, None)


# ── as rotas usam o helper, e nenhuma reconstrói o escopo ────────────────────

def test_as_listagens_de_compras_usam_o_helper():
    from pathlib import Path
    raiz = Path(__file__).resolve().parents[1]
    rotas = (raiz / 'modules' / 'purchases' / 'routes.py').read_text(encoding='utf-8')
    assert rotas.count('purchase_listing_scope(') == 5, \
        'demandas, requisições, POs, pendências e aprovações — as cinco de Compras'
    relatorios = (raiz / 'modules' / 'reports' / 'routes.py').read_text(encoding='utf-8')
    assert relatorios.count('purchase_listing_scope(') == 1


def test_nenhuma_listagem_remonta_o_par_de_escopo_a_mao():
    """O idioma antigo não pode voltar a conviver com o novo."""
    from pathlib import Path
    raiz = Path(__file__).resolve().parents[1]
    for caminho in ('modules/purchases/routes.py', 'modules/reports/routes.py'):
        fonte = (raiz / caminho).read_text(encoding='utf-8')
        sem_comentarios = '\n'.join(
            l for l in fonte.splitlines() if not l.lstrip().startswith('#'))
        assert 'actor_has_no_purchase_unit_scope(' not in sem_comentarios, caminho


def test_todas_as_listagens_aceitam_unit_id():
    from pathlib import Path
    rotas = (Path(__file__).resolve().parents[1] / 'modules' / 'purchases' / 'routes.py').read_text(encoding='utf-8')
    # 5 listagens + `GET /api/purchase-scope`, que confirma a seleção.
    assert rotas.count("query.get('unit_id', [''])[0],") == 6
