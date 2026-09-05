"""Gates 3-5 da #313 — isolamento de tenant da identidade de certificação.

A propriedade sob teste é a que decide se `certification_readonly` pode existir:
**ele enxerga as Unidades da própria empresa e nunca as de outra.** Isso não se
prova lendo o código — `selectable_units` compõe três funções, e o recorte por
tenant nasce em `fetch_units`. Prova-se consultando.

Por que escopo ENUMERADO e não `allowed_unit_ids = None`: sem o ramo explícito
de `resolve_purchase_unit_scope` o papel cairia no `else` dos perfis livres, que
devolve "sem restrição", e o isolamento passaria a ser efeito colateral do
`WHERE units.company_id = ?` de `fetch_units`. O gate `test_o_escopo_e_enumerado`
existe para que remover o ramo seja uma falha, e não uma equivalência silenciosa.
"""

import os
import sys
from contextlib import closing

import pytest

# Mesma linha de `test_migration_contract_postgres.py`, e pelo mesmo motivo: o
# CI roda o console script `pytest`, que — ao contrário de `python -m pytest` —
# NÃO põe o diretório atual no `sys.path`. Este arquivo é o primeiro de
# `tests_postgres/` na ordem alfabética, então é importado antes de qualquer
# outro que já faça esse ajuste (foi assim que a #315 ficou verde local e
# vermelha no CI).
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import get_connection
from core.repository import resolve_purchase_unit_scope, selectable_units
from core.roles import CERTIFICATION_READONLY_ROLE
from modules.units.service import fetch_units

pytestmark = pytest.mark.skipif(
    not os.environ.get('DATABASE_URL', '').startswith('postgres'),
    reason='Exige DATABASE_URL apontando para PostgreSQL real.',
)

EMPRESA_A = 'T313 Empresa A'
EMPRESA_B = 'T313 Empresa B'


def _sem_carteira(connection, actor):
    """`purchase_units_loader` que reprova se for chamado.

    A identidade de certificação não tem carteira e não pode adquirir uma por
    engano: se o ramo explícito sumir e o papel cair no caminho de
    Comprador/Aprovador, isto falha em vez de devolver silêncio.
    """
    raise AssertionError('a identidade de certificação não deve consultar carteira')


@pytest.fixture
def dois_tenants():
    """Duas empresas com Unidades próprias. Limpa o que criou, e só isso."""
    from core.bootstrap import init_db
    init_db()

    criados = {'empresas': [], 'unidades': []}
    with closing(get_connection()) as conexao:
        for nome in (EMPRESA_A, EMPRESA_B):
            conexao.execute('DELETE FROM units WHERE company_id IN '
                            '(SELECT id FROM companies WHERE name = ?)', (nome,))
            conexao.execute('DELETE FROM companies WHERE name = ?', (nome,))
        conexao.commit()

        for indice, nome in enumerate((EMPRESA_A, EMPRESA_B)):
            # `cnpj` e `logo_type` são NOT NULL sem default; o CNPJ é
            # reservado ao cenário e removido no teardown.
            conexao.execute(
                'INSERT INTO companies (name, cnpj, logo_type) VALUES (?, ?, ?)',
                (nome, f'0000000000313{indice}', 'none'))
            conexao.commit()
            empresa = conexao.execute(
                'SELECT id FROM companies WHERE name = ?', (nome,)).fetchone()[0]
            criados['empresas'].append(int(empresa))
            for sufixo in ('I', 'II'):
                conexao.execute(
                    'INSERT INTO units (company_id, name, unit_type, city) '
                    'VALUES (?, ?, ?, ?)',
                    (empresa, f'{nome} · Unidade {sufixo}', 'filial', 'T313'))
            conexao.commit()
        for empresa in criados['empresas']:
            for linha in conexao.execute(
                    'SELECT id FROM units WHERE company_id = ?', (empresa,)).fetchall():
                criados['unidades'].append(int(linha[0]))

    yield criados

    with closing(get_connection()) as conexao:
        for empresa in criados['empresas']:
            conexao.execute('DELETE FROM units WHERE company_id = ?', (empresa,))
            conexao.execute('DELETE FROM companies WHERE id = ?', (empresa,))
        conexao.commit()


def _ator(company_id):
    return {'id': -1, 'role': CERTIFICATION_READONLY_ROLE, 'company_id': company_id}


def _selecionaveis(conexao, actor):
    selecao = resolve_purchase_unit_scope(
        conexao, actor, purchase_units_loader=_sem_carteira)
    return selecao, [int(u['id']) for u in selectable_units(fetch_units(conexao, actor), selecao)]


# ── Gate 3 ───────────────────────────────────────────────────────────────────

def test_ve_exatamente_as_unidades_da_propria_empresa(dois_tenants):
    a, b = dois_tenants['empresas']
    with closing(get_connection()) as conexao:
        _, vistas_a = _selecionaveis(conexao, _ator(a))
        _, vistas_b = _selecionaveis(conexao, _ator(b))

        esperadas_a = [int(r[0]) for r in conexao.execute(
            'SELECT id FROM units WHERE company_id = ? ORDER BY id', (a,)).fetchall()]
        esperadas_b = [int(r[0]) for r in conexao.execute(
            'SELECT id FROM units WHERE company_id = ? ORDER BY id', (b,)).fetchall()]

    assert esperadas_a and esperadas_b, 'cenário vazio não prova isolamento'
    assert sorted(vistas_a) == sorted(esperadas_a)
    assert sorted(vistas_b) == sorted(esperadas_b)
    # A asserção que importa: nenhuma unidade do vizinho, em nenhuma direção.
    assert not set(vistas_a) & set(esperadas_b)
    assert not set(vistas_b) & set(esperadas_a)


def test_o_escopo_e_enumerado_e_nao_sem_restricao(dois_tenants):
    """`None` significaria "sem restrição" e é o que o ramo explícito evita.

    Um papel que caísse no `else` devolveria `allowed_unit_ids = None` e
    passaria neste arquivo em todos os outros testes — o isolamento seria real,
    mas por conta de `fetch_units`, não por decisão deste papel.
    """
    a = dois_tenants['empresas'][0]
    with closing(get_connection()) as conexao:
        selecao, _ = _selecionaveis(conexao, _ator(a))
        esperadas = {int(r[0]) for r in conexao.execute(
            'SELECT id FROM units WHERE company_id = ?', (a,)).fetchall()}

    assert selecao.allowed_unit_ids is not None, \
        'escopo veio como "sem restrição": o ramo explícito da #313 não agiu'
    assert set(selecao.allowed_unit_ids) == esperadas
    assert selecao.allows_all_units is False
    assert selecao.locked is False
    assert selecao.source == 'certification'


# ── Gate 4 ───────────────────────────────────────────────────────────────────

def test_sem_empresa_bloqueia_tudo_em_vez_de_liberar_tudo(dois_tenants):
    """A distinção entre `()` e `None` é a diferença entre "nada" e "tudo".

    Conta técnica sem tenant é erro de provisionamento; o comportamento certo é
    reprovar a certificação, nunca alcançar unidade órfã de terceiro.
    """
    with closing(get_connection()) as conexao:
        selecao, vistas = _selecionaveis(conexao, _ator(None))

    assert selecao.allowed_unit_ids == ()
    assert selecao.blocks_everything is True
    assert vistas == []


# ── Gate 5 ───────────────────────────────────────────────────────────────────

def test_unidade_de_outro_tenant_e_recusada(dois_tenants):
    """O caminho de `GET /api/stock/epis?unit_id=<da empresa B>` com ator de A."""
    from core.repository import resolve_unit_scope

    a, b = dois_tenants['empresas']
    with closing(get_connection()) as conexao:
        alheia = int(conexao.execute(
            'SELECT id FROM units WHERE company_id = ? ORDER BY id', (b,)).fetchone()[0])
        propria = int(conexao.execute(
            'SELECT id FROM units WHERE company_id = ? ORDER BY id', (a,)).fetchone()[0])

        with pytest.raises(ValueError, match='não pertence à empresa'):
            resolve_unit_scope(conexao, _ator(a), alheia)

        escopo = resolve_unit_scope(conexao, _ator(a), propria)
        assert escopo.unit_id == propria


def test_sem_empresa_nenhuma_unidade_e_alcancavel(dois_tenants):
    """Empresa ausente em QUALQUER lado nega — "desconhecido" nunca é "igual"."""
    from core.repository import resolve_unit_scope

    alguma = dois_tenants['unidades'][0]
    with closing(get_connection()) as conexao, \
            pytest.raises(ValueError, match='não pertence à empresa'):
        resolve_unit_scope(conexao, _ator(None), alguma)


# ── Defesa em profundidade ───────────────────────────────────────────────────

def test_o_escopo_resiste_a_fetch_units_sem_recorte(dois_tenants):
    """Por que remover o `WHERE company_id` de `fetch_units` NÃO muda nada aqui.

    Esse é o resultado que a campanha de sabotagem encontrou e que precisa ser
    documentado como propriedade, não como buraco de gate: com o escopo
    ENUMERADO, `selectable_units` já limita a lista às Unidades da empresa do
    ator, então afrouxar o recorte de tenant a montante não amplia este papel.

    A simulação não mexe no código: `fetch_units(conexao, None)` devolve TODAS
    as Unidades de TODAS as empresas — exatamente o que a sabotagem produziria.
    Se o dia em que alguém trocar o escopo enumerado por `None` chegar, este
    teste passa a ver as Unidades do vizinho e reprova.
    """
    a, b = dois_tenants['empresas']
    with closing(get_connection()) as conexao:
        selecao = resolve_purchase_unit_scope(
            conexao, _ator(a), purchase_units_loader=_sem_carteira)
        todas = fetch_units(conexao, None)
        vistas = {int(u['id']) for u in selectable_units(todas, selecao)}
        alheias = {int(r[0]) for r in conexao.execute(
            'SELECT id FROM units WHERE company_id = ?', (b,)).fetchall()}
        proprias = {int(r[0]) for r in conexao.execute(
            'SELECT id FROM units WHERE company_id = ?', (a,)).fetchall()}

    assert len(todas) > len(proprias), \
        'a simulação não trouxe unidades de outros tenants — cenário inválido'
    assert vistas == proprias
    assert not vistas & alheias
