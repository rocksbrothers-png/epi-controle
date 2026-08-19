"""Catálogo corporativo: saldo com nome de escopo no bootstrap (#258, fatia 1.1C).

A 1.1B separou saldo da unidade e saldo corporativo em `/api/stock/epis`. O
catálogo de EPIs continuou em `bootstrap.epis`, que sempre trouxe o total da
EMPRESA — mas no campo `stock`, o nome ambíguo que a 1.1B aposentou, e sem a
criticidade calculada. O cliente recalculava (`stockQuantity <= minimumStock`),
duplicando uma regra que o servidor já aplica.

Esta fatia só **nomeia** o que já vinha. Ela deliberadamente NÃO muda:

- o conjunto de EPIs do catálogo (o filtro de cadastro `unit_id = ? OR
  unit_id IS NULL` continua igual);
- o escopo multi-tenant;
- o campo `stock`, que segue intacto para os consumidores antigos.

E deliberadamente não acrescenta `unit_stock_quantity`/`unit_scope_id`: o
bootstrap não tem semântica de unidade, e inventar zero ali afirmaria "esta
unidade não tem estoque" sobre uma unidade que nem foi resolvida.
"""

import pathlib
import re

import pytest

from modules.auth.service import _with_company_stock_fields
from modules.stock.service import DEFAULT_MINIMUM_STOCK

RAIZ = pathlib.Path(__file__).resolve().parent.parent
AUTH_SERVICE = RAIZ / 'modules/auth/service.py'
EPIS_CUBIT = RAIZ / 'flutter/apps/epi_admin/lib/core/bloc/epis_cubit.dart'
EPIS_SCREEN = RAIZ / 'flutter/apps/epi_admin/lib/features/epis/epis_screen.dart'
EPI_DETAIL = RAIZ / 'flutter/apps/epi_admin/lib/features/epis/epi_detail_screen.dart'
EPI_MODEL = RAIZ / 'flutter/packages/epi_api/lib/models/epi.dart'


def _sem_comentarios_dart(fonte: str) -> str:
    return '\n'.join(
        linha for linha in fonte.split('\n')
        if not linha.lstrip().startswith(('///', '//'))
    )


# ── o número corporativo, com nome ───────────────────────────────────────────

def test_corporativo_zero_permanece_zero():
    # Zero é saldo, não ausência. Se virasse `None` ou sumisse, o catálogo
    # deixaria de mostrar justamente o EPI que acabou.
    epis = _with_company_stock_fields([{'id': 1, 'stock': 0, 'minimum_stock': 5}])
    assert epis[0]['company_stock_quantity'] == 0
    assert epis[0]['stock'] == 0


def test_corporativo_positivo_passa_intacto():
    epis = _with_company_stock_fields([{'id': 1, 'stock': 250, 'minimum_stock': 10}])
    assert epis[0]['company_stock_quantity'] == 250


def test_o_campo_legado_e_o_novo_carregam_o_mesmo_valor():
    # Um significado só. Se divergissem, `stock` voltaria a ser ambíguo — o
    # defeito inteiro da 1.1B.
    for saldo in (0, 1, 7, 250):
        epi = _with_company_stock_fields([{'id': 1, 'stock': saldo}])[0]
        assert epi['stock'] == epi['company_stock_quantity'] == saldo


def test_saldo_ausente_conta_como_zero_e_nao_explode():
    epi = _with_company_stock_fields([{'id': 1}])[0]
    assert epi['company_stock_quantity'] == 0


# ── mínimo resolvido ─────────────────────────────────────────────────────────

def test_minimo_nulo_vira_o_default_da_coluna():
    # `epis.minimum_stock` é INTEGER NOT NULL DEFAULT 10. NULL só existe em
    # linhas anteriores à criação da coluna, e vale 10 — não 0, que faria o
    # alerta só disparar com o estoque já zerado.
    epi = _with_company_stock_fields([{'id': 1, 'stock': 3, 'minimum_stock': None}])[0]
    assert epi['minimum_stock'] == DEFAULT_MINIMUM_STOCK == 10


def test_minimo_zero_e_valor_configurado():
    epi = _with_company_stock_fields([{'id': 1, 'stock': 3, 'minimum_stock': 0}])[0]
    assert epi['minimum_stock'] == 0


def test_o_cliente_recebe_o_minimo_ja_resolvido():
    # Sem isto o Flutter leria o NULL cru e cairia no próprio `?? 0`,
    # divergindo do backend em quem é crítico.
    epi = _with_company_stock_fields([{'id': 1, 'stock': 3}])[0]
    assert epi['minimum_stock'] == 10


# ── criticidade: uma regra só, do servidor ───────────────────────────────────

@pytest.mark.parametrize('stock,minimo,esperado', [
    (0, 5, True),      # zerado
    (5, 5, True),      # atingir o mínimo já é crítico (`<=`)
    (6, 5, False),
    (250, 10, False),
    (0, 0, True),      # mínimo configurado em zero
    (1, 0, False),
])
def test_criticidade_corporativa_consistente(stock, minimo, esperado):
    epi = _with_company_stock_fields(
        [{'id': 1, 'stock': stock, 'minimum_stock': minimo}]
    )[0]
    assert epi['is_company_stock_critical'] is esperado


def test_a_criticidade_usa_a_mesma_funcao_das_outras_telas():
    # Duas cópias da comparação divergem no primeiro ajuste feito num lado só,
    # e o operador veria alertas diferentes conforme a tela que abrisse.
    fonte = AUTH_SERVICE.read_text(encoding='utf-8')
    inicio = fonte.index('def _with_company_stock_fields')
    corpo = fonte[inicio:fonte.index('\ndef ', inicio + 1)]
    assert 'from modules.stock.service import is_stock_critical, resolve_minimum_stock' in corpo
    assert 'is_stock_critical(company_stock, minimum_stock)' in corpo
    assert '<=' not in corpo, 'a comparação foi reintroduzida inline'
    assert 'else 10' not in corpo, 'o fallback do mínimo foi reescrito à mão'


# ── nada de semântica de unidade no bootstrap ────────────────────────────────

def test_o_bootstrap_nao_inventa_saldo_de_unidade():
    # O par (saldo, escopo) fica AUSENTE, e o cliente lê os dois como null —
    # que é a combinação coerente. Um zero aqui afirmaria "esta unidade não tem
    # estoque" sobre uma unidade que ninguém resolveu.
    epi = _with_company_stock_fields([{'id': 1, 'stock': 250}])[0]
    assert 'unit_stock_quantity' not in epi
    assert 'unit_scope_id' not in epi


def test_a_criticidade_nunca_olha_saldo_de_unidade():
    # Mesmo que um payload traga o campo por engano, ele não pode influenciar:
    # `minimum_stock` é da empresa, e compará-lo com o saldo de uma unidade
    # marcaria como crítico todo EPI cujo estoque esteja distribuído.
    com_unidade = _with_company_stock_fields(
        [{'id': 1, 'stock': 250, 'minimum_stock': 100, 'unit_stock_quantity': 5}]
    )[0]
    sem_unidade = _with_company_stock_fields(
        [{'id': 1, 'stock': 250, 'minimum_stock': 100}]
    )[0]
    assert com_unidade['is_company_stock_critical'] is False
    assert com_unidade['is_company_stock_critical'] == sem_unidade['is_company_stock_critical']
    assert com_unidade['company_stock_quantity'] == 250


def test_corporativo_zero_com_unidade_positiva_segue_critico():
    # Caso 4 do enunciado. O corporativo manda no catálogo: se a empresa está
    # zerada, o catálogo alerta, mesmo que alguma unidade ainda tenha peças.
    epi = _with_company_stock_fields(
        [{'id': 1, 'stock': 0, 'minimum_stock': 10, 'unit_stock_quantity': 40}]
    )[0]
    assert epi['company_stock_quantity'] == 0
    assert epi['is_company_stock_critical'] is True


def test_corporativo_positivo_com_unidade_zerada_nao_e_critico():
    # Caso 3 do enunciado, o espelho do anterior: unidade sem peças não torna
    # a EMPRESA crítica. Quem cuida do saldo local é a tela de Estoque.
    epi = _with_company_stock_fields(
        [{'id': 1, 'stock': 250, 'minimum_stock': 10, 'unit_stock_quantity': 0}]
    )[0]
    assert epi['is_company_stock_critical'] is False


def test_o_enriquecimento_nao_muda_o_conjunto_de_epis():
    # A fatia é de nomenclatura, não de visibilidade. Perder ou acrescentar um
    # EPI aqui seria mudança de escopo multi-tenant disfarçada.
    entrada = [{'id': i, 'stock': i * 10} for i in range(1, 6)]
    saida = _with_company_stock_fields(entrada)
    assert [e['id'] for e in saida] == [1, 2, 3, 4, 5]


def test_o_enriquecimento_e_aplicado_depois_do_canary():
    # O canary compara o dataset legado com o do motor novo. Enriquecer antes
    # mudaria o que ele compara, e um alarme dele passaria a significar outra
    # coisa.
    fonte = AUTH_SERVICE.read_text(encoding='utf-8')
    canary = fonte.index("'epis_visibility_canary'")
    # Ancorar na CHAMADA, não no `def`: a definição contém a mesma sequência de
    # caracteres e mora antes de `build_bootstrap`, então um `index()` ingênuo
    # mediria a distância errada e o teste passaria/falharia por acidente.
    chamada = re.search(r'^\s+epis = _with_company_stock_fields\(epis\)$', fonte, re.M)
    assert chamada, 'a chamada do enriquecimento sumiu do build_bootstrap'
    assert canary < chamada.start()


# ── compatibilidade com quem já consumia o bootstrap ─────────────────────────

def test_nenhum_campo_pre_existente_e_removido_ou_alterado():
    original = {
        'id': 1, 'name': 'Capacete', 'ca': '12345', 'stock': 250,
        'minimum_stock': 10, 'sector': 'Cabeça', 'manufacturer': 'ACME',
        'unit_id': None, 'scope_type': 'GLOBAL',
    }
    resultado = _with_company_stock_fields([dict(original)])[0]
    for chave, valor in original.items():
        assert resultado[chave] == valor, f'{chave} mudou de valor'


def test_a_mudanca_e_puramente_aditiva():
    original = {'id': 1, 'name': 'Capacete', 'stock': 250, 'minimum_stock': 10}
    resultado = _with_company_stock_fields([dict(original)])[0]
    novos = set(resultado) - set(original)
    assert novos == {'company_stock_quantity', 'is_company_stock_critical'}


# ── o Flutter consome, e não recalcula ───────────────────────────────────────

def test_o_epis_cubit_usa_a_criticidade_do_backend():
    corpo = _sem_comentarios_dart(EPIS_CUBIT.read_text(encoding='utf-8'))
    assert 'isCompanyStockCritical == true' in corpo
    assert 'isCriticalStock' not in corpo, \
        'o catálogo voltou a comparar saldo com mínimo no cliente'


def test_o_epis_cubit_nao_infere_saldo():
    corpo = _sem_comentarios_dart(EPIS_CUBIT.read_text(encoding='utf-8'))
    for proibido in ('stockQuantity <=', 'stockQuantity <', 'minimumStock'):
        assert proibido not in corpo, f'{proibido} no cubit indica recálculo'


@pytest.mark.parametrize('tela', [EPIS_SCREEN, EPI_DETAIL])
def test_o_catalogo_exibe_o_saldo_corporativo_nomeado(tela):
    corpo = _sem_comentarios_dart(tela.read_text(encoding='utf-8'))
    assert 'companyStock' in corpo, f'{tela.name} não usa o saldo corporativo'
    assert 'unitStockQuantity' not in corpo, \
        f'{tela.name} é catálogo corporativo e não deve ler saldo de unidade'


def test_o_acessor_corporativo_nao_cruza_escopos():
    # `companyStock` é `companyStockQuantity ?? stockQuantity`. Os DOIS são
    # corporativos pelo contrato da 1.1B — não é fallback entre escopos, e o
    # dia em que alguém puser `unitStockQuantity` nessa expressão, o defeito da
    # 1.1B volta inteiro.
    modelo = EPI_MODEL.read_text(encoding='utf-8')
    inicio = modelo.index('int get companyStock')
    expressao = modelo[inicio:modelo.index(';', inicio)]
    assert 'unitStockQuantity' not in expressao
    assert 'companyStockQuantity ?? stockQuantity' in expressao
    # `??` cobre só null. `||`/truthiness trataria 0 como ausente e o saldo
    # zerado da empresa cairia noutro número.
    assert '||' not in expressao


def test_o_catalogo_nao_usa_a_rota_de_estoque_por_unidade():
    # Decisão explícita da 1.1C: o catálogo continua no bootstrap. Apontá-lo
    # para `/api/stock/epis` trocaria a regra de pertencimento (cadastro →
    # GLOBAL/JV) e faria admin/user sem unidade tomar 403 em vez de lista
    # vazia — mudança de escopo multi-tenant, que é outra fatia.
    corpo = _sem_comentarios_dart(EPIS_CUBIT.read_text(encoding='utf-8'))
    assert '/api/stock/epis' not in corpo
    assert 'fetchStockEpis' not in corpo


def test_o_bootstrap_segue_sendo_a_fonte_do_catalogo():
    # Guarda da sequência: `bootstrap.epis` só sai na 1.1E, depois de 1.1D.
    corpo = _sem_comentarios_dart(EPIS_CUBIT.read_text(encoding='utf-8'))
    assert 'bootstrap.epis' in corpo or 'bootstrap' in corpo


# ── Web Legado ───────────────────────────────────────────────────────────────

def test_o_catalogo_do_web_legado_nao_exibe_saldo():
    # Documenta por que não há mudança equivalente no Web: a tabela de EPIs
    # aprovados não tem coluna de estoque. Se um dia ganhar uma, este teste
    # falha e obriga a decidir de qual escopo o número é — em vez de alguém
    # escolher `stock` por ser o campo mais à mão.
    view = (RAIZ / 'static/js/views/epis.js').read_text(encoding='utf-8')
    inicio = view.index('function renderApprovedEpis')
    corpo = view[inicio:view.index('function renderEpis', inicio)]
    assert not re.search(r'item\.stock\b|company_stock_quantity|unit_stock_quantity', corpo), \
        'o catálogo do Web passou a exibir saldo — defina o escopo explicitamente'
