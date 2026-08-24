"""Seletor de Unidade compartilhado — uma regra, um endpoint.

O QUE ESTA FATIA CORRIGE

`GET /api/units` recorta por TENANT e mais nada: um `admin`/`user` travado
recebe dela todas as Unidades da empresa. Cada tela ficava encarregada de
estreitar a lista — ou seja, a interface reconstruindo autorização. No Flutter,
quatro telas consomem `bootstrap.units` e só UMA estreita, no cliente, por
`_ownUnitId`.

E a regra correta já existia em dois lugares: `UnitSelection.permits`, em
`core/repository.py`, e `_unidade_selecionavel`, copiada dentro do Dashboard.
Duas implementações da mesma decisão divergem no primeiro ajuste feito num lado
só — foi o que a 1.1D-C4 desfez entre Dart e JS.

Agora existe `selectable_units`, único, e `GET /api/units/selectable`, que
devolve a lista JÁ recortada mais o contexto que o cliente precisa para desenhar
o seletor sem inferir nada.

A ARMADILHA CENTRAL

    allowed_unit_ids is None  → sem restrição   → todas as Unidades do tenant
    allowed_unit_ids == ()    → carteira vazia  → NENHUMA Unidade

As duas são falsy. `if not allowed_unit_ids` transformaria "não pode ver nada"
em "pode ver tudo" — um Comprador sem vínculo enxergando a empresa inteira.
"""

import sqlite3

import pytest

from core.repository import UnitSelection, selectable_units

A, B, C = 10, 11, 12

UNIDADES = [
    {'id': A, 'name': 'Unidade A', 'legal_entity_id': 1},
    {'id': B, 'name': 'Unidade B', 'legal_entity_id': 1},
    {'id': C, 'name': 'Unidade C', 'legal_entity_id': 2},
]


def _ids(unidades):
    return [u['id'] for u in unidades]


# ── selectable_units: a regra, nos quatro casos ─────────────────────────────

def test_perfil_livre_sem_restricao_ve_todas():
    livre = UnitSelection(None, 'none', False, None, True)
    assert _ids(selectable_units(UNIDADES, livre)) == [A, B, C]


def test_perfil_travado_ve_apenas_a_propria():
    travado = UnitSelection(B, 'actor', True, (B,), False)
    assert _ids(selectable_units(UNIDADES, travado)) == [B]


def test_carteira_preenchida_ve_apenas_a_carteira():
    comprador = UnitSelection(None, 'purchase_scope', False, (A, C), True)
    assert _ids(selectable_units(UNIDADES, comprador)) == [A, C]


def test_carteira_VAZIA_nao_vira_empresa_inteira():
    """O defeito que a distinção `None` × `()` existe para impedir."""
    sem_carteira = UnitSelection(None, 'purchase_scope', False, (), False)
    assert selectable_units(UNIDADES, sem_carteira) == []
    assert sem_carteira.blocks_everything is True


def test_none_e_tupla_vazia_nao_se_confundem():
    """As duas são falsy; o comportamento tem de ser oposto."""
    sem_restricao = UnitSelection(None, 'none', False, None, True)
    sem_carteira = UnitSelection(None, 'purchase_scope', False, (), False)

    assert len(selectable_units(UNIDADES, sem_restricao)) == 3
    assert len(selectable_units(UNIDADES, sem_carteira)) == 0
    assert sem_restricao.blocks_everything is False


def test_unidade_de_outro_tenant_ja_veio_de_fora():
    """A lista de entrada é recortada por tenant; aqui só entra o direito.

    `fetch_units` já filtra `company_id`. Refiltrar aqui duplicaria a regra de
    tenant num segundo lugar — o defeito que a fatia inteira combate.
    """
    livre = UnitSelection(None, 'none', False, None, True)
    assert _ids(selectable_units([{'id': A, 'name': 'A'}], livre)) == [A]


def test_unidade_sem_id_utilizavel_nao_entra():
    livre = UnitSelection(None, 'none', False, None, True)
    lixo = [{'id': None, 'name': 'sem id'}, {'id': 'abc', 'name': 'id inválido'},
            {'id': 0, 'name': 'zero'}, {'id': A, 'name': 'boa'}]
    assert _ids(selectable_units(lixo, livre)) == [A]


def test_a_ordem_da_lista_de_entrada_e_preservada():
    """Ordenação é decisão de `fetch_units` (nome da empresa, nome da Unidade).

    Reordenar aqui criaria uma segunda ordenação, que divergiria da do resto
    do sistema no primeiro ajuste.
    """
    livre = UnitSelection(None, 'none', False, None, True)
    invertida = list(reversed(UNIDADES))
    assert _ids(selectable_units(invertida, livre)) == [C, B, A]


# ── O Dashboard passou a usar a MESMA regra ─────────────────────────────────

def test_o_dashboard_nao_tem_mais_copia_da_regra():
    import pathlib
    fonte = (pathlib.Path(__file__).resolve().parents[1]
             / 'modules' / 'dashboard' / 'service.py').read_text(encoding='utf-8')
    assert 'def _unidade_selecionavel' not in fonte, \
        'a cópia da regra voltou para dentro do Dashboard'
    assert 'selectable_units(' in fonte, \
        'o Dashboard deixou de consumir o ponto único'


def test_a_traducao_do_painel_preserva_os_dois_casos_perigosos():
    """Perfil travado e carteira vazia não podem virar `None`."""
    from modules.dashboard.service import _selecao_do_painel

    class _Escopo:
        def __init__(self, locked, unit_id):
            self.locked, self.unit_id = locked, unit_id

    travado = _selecao_do_painel(_Escopo(True, B), None)
    assert travado.allowed_unit_ids == (B,)
    assert _ids(selectable_units(UNIDADES, travado)) == [B]

    vazia = _selecao_do_painel(_Escopo(False, None), [])
    assert vazia.allowed_unit_ids == ()
    assert selectable_units(UNIDADES, vazia) == []

    livre = _selecao_do_painel(_Escopo(False, None), None)
    assert livre.allowed_unit_ids is None
    assert len(selectable_units(UNIDADES, livre)) == 3


def test_o_painel_so_oferece_todas_a_partir_de_duas_unidades():
    """Carteira de uma Unidade só: "Todas" não faz sentido."""
    from modules.dashboard.service import _selecao_do_painel

    class _Escopo:
        locked = False
        unit_id = None

    assert _selecao_do_painel(_Escopo(), [A]).allows_all_units is False
    assert _selecao_do_painel(_Escopo(), [A, B]).allows_all_units is True
    assert _selecao_do_painel(_Escopo(), None).allows_all_units is True


# ── A rota ──────────────────────────────────────────────────────────────────

@pytest.fixture()
def conn():
    c = sqlite3.connect(':memory:')
    c.row_factory = sqlite3.Row
    c.execute('CREATE TABLE units (id INTEGER PRIMARY KEY, company_id INTEGER, name TEXT)')
    c.executemany('INSERT INTO units VALUES (?, ?, ?)',
                  [(A, 1, 'Unidade A'), (B, 1, 'Unidade B'), (C, 1, 'Unidade C')])
    return c


def test_a_rota_esta_registrada():
    import pathlib
    fonte = (pathlib.Path(__file__).resolve().parents[1]
             / 'modules' / 'units' / 'routes.py').read_text(encoding='utf-8')
    assert "'/api/units/selectable'" in fonte
    assert 'handle_get_selectable_units' in fonte


def test_a_rota_exige_a_mesma_permissao_da_listagem():
    """A lista aqui é SUBCONJUNTO de `/api/units`, nunca superconjunto."""
    import pathlib
    fonte = (pathlib.Path(__file__).resolve().parents[1]
             / 'modules' / 'units' / 'routes.py').read_text(encoding='utf-8')
    corpo = fonte.split('def handle_get_selectable_units')[1].split('\ndef ')[0]
    assert "'units:view'" in corpo


def test_a_rota_injeta_a_carteira_em_vez_de_importar_no_topo():
    """`core.repository` não pode importar `modules.purchases` (issue #148)."""
    import pathlib
    fonte = (pathlib.Path(__file__).resolve().parents[1]
             / 'modules' / 'units' / 'routes.py').read_text(encoding='utf-8')
    corpo = fonte.split('def handle_get_selectable_units')[1].split('\ndef ')[0]
    assert 'purchase_units_loader=get_actor_purchase_unit_scope' in corpo


def test_a_rota_devolve_o_contexto_e_nao_deixa_o_cliente_inferir():
    import pathlib
    fonte = (pathlib.Path(__file__).resolve().parents[1]
             / 'modules' / 'units' / 'routes.py').read_text(encoding='utf-8')
    corpo = fonte.split('def handle_get_selectable_units')[1].split('\ndef ')[0]
    for campo in ("'locked'", "'unit_id'", "'allows_all_units'",
                  "'blocks_everything'", "'source'"):
        assert campo in corpo, f'a rota deixou de devolver {campo}'


def test_a_rota_nao_recalcula_a_regra_por_conta_propria():
    """Ela compõe `resolve_purchase_unit_scope` + `selectable_units`."""
    import pathlib
    import re
    fonte = (pathlib.Path(__file__).resolve().parents[1]
             / 'modules' / 'units' / 'routes.py').read_text(encoding='utf-8')
    corpo = fonte.split('def handle_get_selectable_units')[1].split('\ndef ')[0]
    codigo = '\n'.join(l for l in corpo.split('\n') if not l.strip().startswith('#'))
    assert 'resolve_purchase_unit_scope(' in codigo
    assert 'selectable_units(' in codigo
    # A rota não tem por que LER o perfil: quem decide por perfil é
    # `resolve_purchase_unit_scope`. Qualquer menção a `role` aqui é uma
    # segunda decisão nascendo — inclusive `actor.get('role') in (...)`, que
    # uma regex de `role ==` deixaria passar.
    assert 'role' not in codigo, \
        'a rota passou a decidir por perfil em vez de delegar ao ponto único'
    assert not re.search(r'\bif\b.*\bunit', codigo), \
        'a rota passou a filtrar Unidade por conta própria'
