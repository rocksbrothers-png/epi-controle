"""Regra de criticidade de estoque — semântica de `minimum_stock` (#258, 1.1B).

Antes de `is_company_stock_critical` virar API autoritativa, a semântica de
`minimum_stock = 0` e `NULL` precisa estar fixada em teste. A dúvida é real: se
a regra é `saldo <= mínimo`, então mínimo 0 com saldo 0 dá crítico — o que está
certo se 0 significa "mínimo configurado em zero", e errado se 0 for usado como
"ainda não configurado".

**A resposta vem do schema, não de escolha nova:** `epis.minimum_stock` é
`INTEGER NOT NULL DEFAULT 10` (`core/schema.py`). Logo:

- `NULL` não é estado alcançável por linha normal — o fallback existe para
  linhas anteriores à criação da coluna, e vale **10**, não 0;
- `0` é valor **configurado**: a tela administrativa grava o que o usuário
  digitar. Tratar 0 como "não configurado" silenciaria o alerta de quem
  deliberadamente pediu para ser avisado ao zerar o estoque.

Estes testes travam essa leitura, e travam também que a regra é UMA só —
`/api/stock/low` e `/api/stock/epis` compartilham a mesma função, para não
divergirem no primeiro ajuste feito num lado só.
"""

import pathlib
import re

import pytest

from modules.stock.service import (
    DEFAULT_MINIMUM_STOCK,
    is_stock_critical,
    resolve_minimum_stock,
)

RAIZ = pathlib.Path(__file__).resolve().parent.parent


# ── mínimo efetivo ───────────────────────────────────────────────────────────

def test_minimo_nulo_cai_no_default_da_coluna_e_nao_em_zero():
    # Se caísse em 0, um EPI sem mínimo configurado só alertaria com estoque
    # zerado — perderia o aviso justamente na faixa em que ainda dá tempo de
    # repor.
    assert resolve_minimum_stock(None) == DEFAULT_MINIMUM_STOCK == 10


def test_o_default_do_fallback_e_o_mesmo_da_coluna():
    # Guarda contra divergência silenciosa: se alguém alterar o DEFAULT da
    # coluna sem mexer no fallback, linhas antigas e novas passariam a ter
    # mínimos diferentes.
    schema = (RAIZ / 'core/schema.py').read_text(encoding='utf-8')
    match = re.search(
        r"_safe_add_column\(connection, 'epis', 'minimum_stock', '([^']+)'\)", schema
    )
    assert match, 'declaração da coluna minimum_stock não encontrada'
    declaracao = match.group(1)
    assert f'DEFAULT {DEFAULT_MINIMUM_STOCK}' in declaracao, (
        f'a coluna declara "{declaracao}" mas o fallback do serviço usa '
        f'{DEFAULT_MINIMUM_STOCK}'
    )


def test_zero_e_valor_configurado_nao_ausencia():
    assert resolve_minimum_stock(0) == 0


@pytest.mark.parametrize('valor', [1, 10, 100, 9999])
def test_valor_positivo_passa_intacto(valor):
    assert resolve_minimum_stock(valor) == valor


# ── criticidade ──────────────────────────────────────────────────────────────

def test_cenario_quatro_unidades_com_cinquenta_cada():
    # Caso A do enunciado: mínimo 100, quatro unidades com 50 cada.
    # O total da empresa (200) supera o mínimo — nada de crítico. É o cenário
    # que quebraria se a comparação usasse o saldo de UMA unidade (50 <= 100).
    company_stock = 50 * 4
    assert company_stock == 200
    assert is_stock_critical(company_stock, 100) is False
    # E a comparação errada, para deixar explícito o que NÃO se deve fazer:
    assert is_stock_critical(50, 100) is True


def test_cenario_empresa_abaixo_do_minimo():
    # Caso B do enunciado.
    assert is_stock_critical(80, 100) is True


def test_saldo_igual_ao_minimo_e_critico():
    # A comparação é `<=`, não `<`: atingir o mínimo já é sinal de reposição.
    assert is_stock_critical(100, 100) is True


def test_minimo_zero_so_dispara_com_estoque_zerado():
    assert is_stock_critical(0, 0) is True
    assert is_stock_critical(1, 0) is False
    assert is_stock_critical(5, 0) is False


def test_minimo_nao_configurado_usa_dez():
    assert is_stock_critical(10, None) is True
    assert is_stock_critical(11, None) is False


def test_saldo_nulo_conta_como_zero():
    # `COALESCE(SUM(...), epis.stock, 0)` pode não existir para EPI sem
    # nenhuma linha em unit_epi_stock; None ali não pode explodir.
    assert is_stock_critical(None, 10) is True


# ── uma regra só ─────────────────────────────────────────────────────────────

def test_low_stock_usa_a_regra_compartilhada():
    # O ponto do teste: duas cópias da mesma comparação divergem no primeiro
    # ajuste feito num lado só, e o operador passaria a ver alertas diferentes
    # conforme a tela que abrisse.
    servico = (RAIZ / 'modules/stock/service.py').read_text(encoding='utf-8')
    inicio = servico.index('def fetch_low_stock_items(')
    corpo = servico[inicio:servico.index('def build_low_stock(', inicio)]
    assert 'is_stock_critical(' in corpo, \
        'fetch_low_stock_items voltou a comparar por conta própria'
    assert 'resolve_minimum_stock(' in corpo
    assert 'else 10' not in corpo, \
        'o fallback do mínimo foi reintroduzido inline em vez de usar o helper'
