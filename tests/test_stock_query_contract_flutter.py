"""Consulta de estoque atravessando Python↔Dart (#246 Lote 1, fatia 1.1).

`/api/stock/available-items` e `/api/stock/blocked-items` existiam no backend e
eram usadas pelo Web Legado, sem nenhum consumidor Flutter. Estes testes travam
o contrato entre as duas pontas — o tipo de defeito que nenhum dos dois lados
enxerga sozinho:

- rota chamada pelo Dart que não está registrada responde 404 e o app mostra
  erro genérico, sem nada acusar em CI;
- chave de status renderizada a partir do rótulo do backend deixa o app em
  português nos outros quatro idiomas;
- `company_id` enviado pela UI moveria autorização para o cliente, que é
  exatamente o que o backend recusa fazer.
"""

import pathlib
import re

RAIZ = pathlib.Path(__file__).resolve().parent.parent
ROUTES = RAIZ / 'modules/stock/routes.py'
SERVICE = RAIZ / 'modules/stock/service.py'
STOCK_API = RAIZ / 'flutter/packages/epi_api/lib/endpoints/stock_api.dart'
STOCK_MODEL = RAIZ / 'flutter/packages/epi_api/lib/models/stock_item.dart'
STOCK_SCREEN = RAIZ / 'flutter/apps/epi_admin/lib/features/stock/stock_screen.dart'
STOCK_CUBIT = RAIZ / 'flutter/apps/epi_admin/lib/core/bloc/stock_cubit.dart'
REPOSITORY = RAIZ / 'flutter/apps/epi_admin/lib/features/stock/domain/repositories/stock_repository.dart'

FATIA = ('/api/stock/available-items', '/api/stock/blocked-items')


def _sem_comentarios(fonte: str) -> str:
    """Remove linhas de comentário Dart.

    Sem isto, os testes abaixo tropeçariam na própria documentação: um comentário
    que EXPLICA por que `company_id` não é enviado seria lido como se o enviasse.
    Comentário é prosa; o que interessa é o código executado.
    """
    return '\n'.join(
        linha for linha in fonte.split('\n')
        if not linha.lstrip().startswith(('///', '//'))
    )


def _rotas_registradas():
    texto = ROUTES.read_text(encoding='utf-8')
    return set(re.findall(r"router\.register\(\s*'[A-Z]+'\s*,\s*'([^']+)'", texto))


def _rotas_chamadas_pelo_dart():
    texto = STOCK_API.read_text(encoding='utf-8')
    return set(re.findall(r"'(/api/stock/[a-z0-9/_-]+)'", texto))


# ── o contrato existe dos dois lados ─────────────────────────────────────────

def test_as_rotas_da_fatia_estao_registradas_no_backend():
    registradas = _rotas_registradas()
    for rota in FATIA:
        assert rota in registradas, f'{rota} não está registrada em modules/stock/routes.py'


def test_toda_rota_de_estoque_chamada_pelo_dart_existe_no_backend():
    # O ponto do teste: uma rota renomeada no backend não quebra compilação
    # nenhuma do lado Dart — só falha em runtime, no cliente.
    faltando = _rotas_chamadas_pelo_dart() - _rotas_registradas()
    assert not faltando, f'o Dart chama rotas inexistentes: {sorted(faltando)}'


def test_a_fatia_tem_consumidor_dart_de_verdade():
    api = STOCK_API.read_text(encoding='utf-8')
    for rota in FATIA:
        assert f"'{rota}'" in api, f'{rota} sem chamada no stock_api.dart'
    # Cliente sem uso não conta (ADR-0004): o repositório precisa expor, e o
    # cubit precisa chamar.
    repo = REPOSITORY.read_text(encoding='utf-8')
    cubit = STOCK_CUBIT.read_text(encoding='utf-8')
    for metodo in ('fetchAvailableItems', 'fetchBlockedItems'):
        assert metodo in repo, f'{metodo} fora do contrato do repositório'
        assert metodo in cubit, f'{metodo} não é chamado pelo cubit'


# ── escopo é autorização, e mora no servidor ─────────────────────────────────

def test_o_cliente_nao_envia_company_id_nessas_rotas():
    # O backend só aceita `company_id` de master_admin e ignora o dos demais
    # perfis. Mandar da UI não mudaria o resultado, mas passaria a ideia de que
    # o cliente escolhe o tenant — e a próxima pessoa a mexer confiaria nisso.
    api = _sem_comentarios(STOCK_API.read_text(encoding='utf-8'))
    inicio = api.index('fetchAvailableItems')
    fim = api.index('recordMovement')
    trecho = api[inicio:fim]
    assert 'company_id' not in trecho, 'company_id não pode sair da UI nas rotas de consulta'
    assert 'unit_id' not in trecho, 'unit_id é derivado do ator no servidor'


def test_o_backend_exige_unidade_operacional_para_perfis_de_campo():
    # Guarda de regressão: se alguém remover esta trava, `admin`/`user` sem
    # unidade passariam a enxergar o estoque da empresa inteira.
    texto = ROUTES.read_text(encoding='utf-8')
    for handler in ('handle_get_stock_available_items', 'handle_get_stock_blocked_items'):
        inicio = texto.index(f'def {handler}')
        corpo = texto[inicio:inicio + 2000]
        assert "actor.get('role') in ('admin', 'user')" in corpo, \
            f'{handler} não restringe perfis com unidade fixa'
        assert 'PermissionError' in corpo, f'{handler} não recusa perfil sem unidade'


def test_o_escopo_de_empresa_vem_do_ator_e_nao_do_cliente():
    texto = ROUTES.read_text(encoding='utf-8')
    for handler in ('handle_get_stock_available_items', 'handle_get_stock_blocked_items'):
        inicio = texto.index(f'def {handler}')
        corpo = texto[inicio:inicio + 2000]
        assert "actor['company_id'] if actor['role'] != 'master_admin'" in corpo, \
            f'{handler} deixaria o cliente escolher a empresa'


# ── i18n: chave é contrato, rótulo é tradução ────────────────────────────────

def test_o_dart_traduz_as_chaves_de_status_em_vez_de_exibir_o_rotulo_do_backend():
    servico = SERVICE.read_text(encoding='utf-8')
    inicio = servico.index('BLOCKED_STOCK_STATUSES = {')
    bloco = servico[inicio:servico.index('}', inicio)]
    chaves_backend = set(re.findall(r"'(blocked_[a-z]+)'", bloco))
    assert chaves_backend, 'nenhuma chave de status lida do backend'

    tela = STOCK_SCREEN.read_text(encoding='utf-8')
    inicio = tela.index('String stockStatusLabel')
    switch = tela[inicio:tela.index('};', inicio)]
    chaves_dart = set(re.findall(r"'(blocked_[a-z]+)'", switch))

    assert chaves_backend == chaves_dart, (
        'as chaves de status do backend e do Dart divergiram — '
        f'só no backend: {sorted(chaves_backend - chaves_dart)}; '
        f'só no Dart: {sorted(chaves_dart - chaves_backend)}'
    )


def test_os_rotulos_em_portugues_do_backend_nao_aparecem_no_dart():
    # O backend manda 'Vencido', 'Em análise' etc. no mapa `statuses`. Renderizar
    # essas strings deixaria o app em português nos outros quatro idiomas.
    servico = SERVICE.read_text(encoding='utf-8')
    inicio = servico.index('BLOCKED_STOCK_STATUSES = {')
    bloco = servico[inicio:servico.index('}', inicio)]
    rotulos = re.findall(r":\s*'([^']+)'", bloco)
    assert rotulos, 'nenhum rótulo lido do backend'

    fontes = _sem_comentarios(
        STOCK_SCREEN.read_text(encoding='utf-8')
        + STOCK_API.read_text(encoding='utf-8')
        + STOCK_MODEL.read_text(encoding='utf-8')
    )
    vazando = [r for r in rotulos if r in fontes]
    assert not vazando, f'rótulos do backend hardcoded no Dart: {vazando}'


def test_o_cliente_guarda_as_chaves_de_status_nao_os_rotulos():
    api = STOCK_API.read_text(encoding='utf-8')
    assert 'statusKeys' in api, 'BlockedStockItems precisa expor as chaves'
    assert 'statuses.keys.toList()' in api, \
        'as chaves têm de vir de `statuses.keys` — guardar os valores traria o rótulo pt-BR'


# ── um modelo só para as duas rotas ──────────────────────────────────────────

def test_um_unico_modelo_cobre_as_duas_rotas():
    # Dois DTOs quase iguais divergem no primeiro campo que o backend mudar de
    # um lado só. As colunas extras de blocked-items são anuláveis no mesmo
    # modelo, em vez de virarem uma segunda classe.
    modelo = STOCK_MODEL.read_text(encoding='utf-8')
    comuns = ('id', 'epi_id', 'epi_name', 'status', 'qr_code_value',
              'glove_size', 'size', 'uniform_size', 'manufacture_date',
              'epi_validity_date')
    extras = ('lot_code', 'unit_measure', 'unit_name', 'unit_id', 'updated_at')
    for campo in comuns + extras:
        assert f"'{campo}'" in modelo, f'StockItem não lê {campo}'

    api = STOCK_API.read_text(encoding='utf-8')
    assert api.count('StockItem.fromJson') == 2, \
        'as duas rotas devem desserializar pelo mesmo StockItem'


def test_o_modelo_cobre_as_colunas_que_o_sql_realmente_seleciona():
    # Contrato contra a fonte, não contra a documentação: se alguém acrescentar
    # coluna no SELECT e esquecer o modelo, o campo chega e é descartado em
    # silêncio.
    servico = SERVICE.read_text(encoding='utf-8')
    inicio = servico.index('def fetch_blocked_stock_items')
    corpo = servico[inicio:servico.index('return connection.execute', inicio) + 400]
    # Só a lista de colunas do SELECT. `esi.company_id` aparece no WHERE — é
    # filtro de escopo aplicado no servidor, e NÃO deve virar campo no cliente:
    # o app não escolhe tenant.
    sql = corpo[corpo.index("'SELECT"):corpo.index("'FROM")]
    colunas = set(re.findall(r'esi\.([a-z_]+)', sql)) | set(re.findall(r'AS ([a-z_]+)', sql))
    colunas -= {'id'}  # 'esi.id' já coberto; evita ruído de alias

    modelo = STOCK_MODEL.read_text(encoding='utf-8')
    ausentes = [c for c in sorted(colunas) if f"'{c}'" not in modelo]
    assert not ausentes, f'colunas do SELECT sem campo no StockItem: {ausentes}'


# ── estados da UI ────────────────────────────────────────────────────────────

def test_a_ui_distingue_sem_permissao_de_erro():
    cubit = STOCK_CUBIT.read_text(encoding='utf-8')
    assert 'StockListStatus' in cubit
    for estado in ('idle', 'loading', 'ready', 'error', 'forbidden'):
        assert estado in cubit, f'estado {estado} ausente'
    # 403 é contexto ausente (perfil sem unidade), não falha — e não pode cair
    # no mesmo ramo de erro, senão a tela oferece "tentar de novo" para algo
    # que tentar de novo não resolve.
    assert 'statusCode == 403' in cubit, 'o cubit não distingue 403'

    tela = STOCK_SCREEN.read_text(encoding='utf-8')
    assert 'stockNoOperationalUnit' in tela, 'sem mensagem própria para 403'
    assert 'StockListStatus.forbidden' in tela


def test_a_lista_vazia_nao_se_confunde_com_consulta_nao_feita():
    tela = STOCK_SCREEN.read_text(encoding='utf-8')
    assert 'idleMessage' in tela, \
        'sem estado idle, a tela diria "nenhum item" antes de existir consulta'
    assert 'stockAvailableEmpty' in tela
    assert 'stockBlockedEmpty' in tela


def test_a_tela_nao_faz_chamada_http_direta():
    tela = STOCK_SCREEN.read_text(encoding='utf-8')
    for proibido in ('Dio(', 'ApiClient.stock', 'http.get', "'/api/"):
        assert proibido not in tela, f'{proibido} não pode aparecer no widget'
