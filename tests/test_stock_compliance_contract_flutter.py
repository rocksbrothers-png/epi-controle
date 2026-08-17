"""Contrato de conformidade de estoque atravessando a fronteira Python↔Dart.

`compute_stock_compliance` é a FONTE ÚNICA da conformidade (item 2 da
auditoria): o card do Dashboard tem de mostrar o mesmo total da tela "Validade
e Bloqueios", e o clique tem de abrir exatamente aqueles itens.

O risco aqui não é a regra — ela é do backend e já tem testes próprios. O risco
é a **fronteira**: o Dashboard em Dart lê as categorias por string
(`compliance['ca_expired']`). Renomear uma categoria no backend não quebra
compilação nenhuma; o card simplesmente passa a exibir zero, em silêncio, e o
usuário conclui que está tudo conforme.

Este repositório é a prova viva do risco: a rota `/api/stock/compliance` e as
9 chaves de i18n já existiam aqui, mas nenhum código Flutter as consumia — a
replicação anterior levou backend e tradução e deixou o cliente para trás.
"""

import pathlib
import re

from modules.stock.service import compute_stock_compliance

RAIZ = pathlib.Path(__file__).resolve().parent.parent
DASHBOARD = RAIZ / 'flutter/apps/epi_admin/lib/features/dashboard/dashboard_screen.dart'
CUBIT = RAIZ / 'flutter/apps/epi_admin/lib/core/bloc/dashboard_cubit.dart'
STOCK_API = RAIZ / 'flutter/packages/epi_api/lib/endpoints/stock_api.dart'

CATEGORIAS = (
    'ca_expired', 'ca_expiring',
    'product_expired', 'product_expiring',
    'missing_manufacture', 'missing_lot',
    'admin_blocked',
)


def _fonte_do_backend():
    """Categorias que o backend realmente emite, lidas do próprio código."""
    src = (RAIZ / 'modules/stock/service.py').read_text(encoding='utf-8')
    i = src.index('def compute_stock_compliance')
    bloco = src[i:i + 4000]
    return set(re.findall(r"categories\['(\w+)'\]", bloco)) | \
        set(re.findall(r"'(\w+)': \[\]", bloco))


def test_o_backend_emite_exatamente_as_categorias_do_contrato():
    assert _fonte_do_backend() == set(CATEGORIAS)


def test_o_dashboard_dart_le_exatamente_as_categorias_do_backend():
    # O teste que pega o drift silencioso: se o backend renomear uma categoria
    # e o Dart não acompanhar (ou vice-versa), o card zera sem ninguém notar.
    dart = DASHBOARD.read_text(encoding='utf-8')
    corpo = dart[dart.index('class _ComplianceSection'):]
    lidas = set(re.findall(r"c\('(\w+)'\)", corpo))
    assert lidas == set(CATEGORIAS), (
        f'Dart lê {sorted(lidas)}, backend emite {sorted(CATEGORIAS)}'
    )


def test_o_cliente_flutter_consome_a_rota_registrada():
    api = STOCK_API.read_text(encoding='utf-8')
    assert '/api/stock/compliance' in api, \
        'StockApi não expõe a fonte única — foi o estado deste repositório até o Lote 3'
    assert 'getStockCompliance' in api

    rotas = (RAIZ / 'modules/stock/routes.py').read_text(encoding='utf-8')
    assert "'/api/stock/compliance'" in rotas


def test_o_dashboard_le_o_summary_e_nao_recalcula_no_cliente():
    # A REGRA é do backend. O cubit consome `summary` e nada mais — se um dia
    # alguém recontar `categories` no cliente, os dois números divergem.
    cubit = CUBIT.read_text(encoding='utf-8')
    assert "res['summary']" in cubit
    assert 'getStockCompliance' in cubit


def test_o_dashboard_degrada_sem_derrubar_a_tela():
    # Backends antigos não têm a rota. O dashboard inteiro não pode cair por
    # causa de uma seção — o modo de falha aceitável é a seção sumir.
    cubit = CUBIT.read_text(encoding='utf-8')
    trecho = cubit[cubit.index('_loadComplianceSafe'):]
    assert 'on Exception' in trecho
    assert 'return const {};' in trecho


def test_summary_e_contagem_e_categories_traz_os_registros():
    # Trava a forma da resposta que o Dart desserializa: `summary` é int por
    # categoria e `categories` é lista — inverter os dois quebraria o card.
    import sqlite3
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.execute(
        'CREATE TABLE epi_stock_items (id INTEGER PRIMARY KEY, epi_id INTEGER, '
        'unit_id INTEGER, company_id INTEGER, lot_code TEXT, manufacture_date TEXT, '
        'status TEXT, qr_code_value TEXT)'
    )
    conn.execute(
        'CREATE TABLE epis (id INTEGER PRIMARY KEY, company_id INTEGER, name TEXT, '
        'ca TEXT, ca_expiry TEXT, epi_validity_date TEXT, unit_id INTEGER)'
    )
    conn.execute('CREATE TABLE units (id INTEGER PRIMARY KEY, company_id INTEGER, name TEXT)')
    resultado = compute_stock_compliance(conn, 1)

    assert set(resultado['summary']) == set(CATEGORIAS)
    assert set(resultado['categories']) == set(CATEGORIAS)
    assert all(isinstance(v, int) for v in resultado['summary'].values())
    assert all(isinstance(v, list) for v in resultado['categories'].values())
