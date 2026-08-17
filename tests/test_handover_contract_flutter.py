"""Contrato da conferência de entrega por QR, atravessando Python↔Dart.

Item 4 da auditoria: o QR da entrega carrega um token **opaco**. O backend
projeta a entrega sem expor dado pessoal direto e confirma o recebimento de
forma idempotente. A REGRA é toda dele — multi-tenant, projeção e idempotência.

Este repositório repetiu aqui o padrão do Lote 3: as rotas
`/api/deliveries/handover-lookup` e `/api/deliveries/handover-confirm` já
estavam registradas, os serviços implementados e as 19 chaves de i18n
traduzidas nos 5 idiomas — e nenhuma linha de Flutter consumia nada disso.

O que estes testes travam é a fronteira, não a regra:

- o caminho que o cliente Dart chama tem de ser um caminho REGISTRADO. Um typo
  aqui não quebra compilação: vira 404 em runtime, no meio de uma conferência
  de EPI no campo;
- a chave que o Dart lê (`handover`) tem de ser a que o backend devolve. Ler a
  chave errada devolve mapa vazio **em silêncio** — a tela mostraria uma
  entrega em branco em vez de um erro.
"""

import pathlib
import re

RAIZ = pathlib.Path(__file__).resolve().parent.parent
DELIVERIES_API = RAIZ / 'flutter/packages/epi_api/lib/endpoints/deliveries_api.dart'
ROUTES = RAIZ / 'modules/deliveries/routes.py'
TELA = RAIZ / 'flutter/apps/epi_admin/lib/features/deliveries/handover_conference_screen.dart'


def _rotas_registradas():
    """Caminhos que o backend realmente registra, lidos do próprio router."""
    src = ROUTES.read_text(encoding='utf-8')
    return set(re.findall(r"router\.register\('(?:GET|POST|PUT|DELETE)',\s*'([^']+)'", src))


def _caminhos_chamados_pelo_dart():
    src = DELIVERIES_API.read_text(encoding='utf-8')
    return set(re.findall(r"'(/api/deliveries/[a-z0-9\-/]+)'", src))


def test_todo_caminho_de_handover_do_dart_existe_no_backend():
    registradas = _rotas_registradas()
    chamados = {c for c in _caminhos_chamados_pelo_dart() if 'handover' in c}

    assert chamados, 'o cliente Dart não chama nenhuma rota de handover'
    orfas = chamados - registradas
    assert not orfas, f'Dart chama rotas inexistentes: {sorted(orfas)}'


def test_as_duas_pontas_do_fluxo_estao_ligadas():
    # lookup projeta, confirm fecha o ciclo. Ter só uma das duas no cliente
    # deixaria a conferência pela metade.
    api = DELIVERIES_API.read_text(encoding='utf-8')
    assert 'handoverLookup' in api
    assert 'handoverConfirm' in api
    assert '/api/deliveries/handover-lookup' in api
    assert '/api/deliveries/handover-confirm' in api


def test_o_dart_le_a_chave_que_o_backend_devolve():
    # O backend responde {'ok': True, 'handover': ...}; o Dart lê ['handover'].
    # Divergir aqui devolve `{}` em silêncio, sem erro nenhum.
    backend = ROUTES.read_text(encoding='utf-8')
    assert "'handover': data" in backend

    api = DELIVERIES_API.read_text(encoding='utf-8')
    assert "res.data?['handover']" in api


def test_a_confirmacao_e_idempotente_no_backend_e_o_cliente_respeita():
    # A idempotência é do backend. O cliente só não pode esconder o resultado:
    # precisa devolver o corpo bruto para a tela distinguir uma confirmação
    # nova de uma já existente.
    servico = (RAIZ / 'modules/deliveries/service.py').read_text(encoding='utf-8')
    assert 'already_confirmed' in servico

    api = DELIVERIES_API.read_text(encoding='utf-8')
    trecho = api[api.index('handoverConfirm'):]
    assert 'return res.data ?? {};' in trecho, \
        'handoverConfirm precisa devolver o corpo bruto (confirmed/already_confirmed)'


def test_a_tela_de_conferencia_existe_e_usa_o_cliente():
    assert TELA.exists(), 'handover_conference_screen.dart ausente — era o estado até o Lote 4'
    tela = TELA.read_text(encoding='utf-8')
    assert 'handoverLookup' in tela
    assert 'handoverConfirm' in tela


def test_a_rota_de_handover_esta_no_router_e_com_permissao():
    rotas = (RAIZ / 'flutter/apps/epi_admin/lib/core/router/routes.dart').read_text(encoding='utf-8')
    assert 'handover' in rotas

    permissoes = (RAIZ / 'flutter/apps/epi_admin/lib/core/router/route_permissions.dart') \
        .read_text(encoding='utf-8')
    assert 'deliveries:view' in permissoes, \
        'rota sem permissão declarada abriria a conferência para quem não pode ver entregas'
