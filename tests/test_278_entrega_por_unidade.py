"""#278 — entrega e movimentação são operações DE UNIDADE.

A auditoria da #278 achou duas coisas de tamanhos diferentes.

A menor: a tela de entrega exibia e usava o saldo CORPORATIVO para habilitar a
escolha do EPI. Falsa promessa — o servidor sempre recusou, porque toda a
autorização já lê `unit_epi_stock`.

A maior: o cliente mandava `stock_item_id = epi.id` e
`stock_qr_code = epi.code`. O backend procura esse id em `epi_stock_items` e
compara o código com `qr_code_value`. São identificadores de domínios
diferentes: a entrega pelo app só daria certo por coincidência de dois valores
independentes.

Estes testes travam as duas correções e as garantias de backend em que elas se
apoiam. Sem toolchain Dart aqui, a parte Flutter é estrutural — prova que a
regra não voltou, não que a tela compila (isso é o CI).
"""

from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
FLUTTER = RAIZ / 'flutter'
APP = FLUTTER / 'apps' / 'epi_admin' / 'lib'

CUBIT = APP / 'core' / 'bloc' / 'new_delivery_cubit.dart'
TELA = APP / 'features' / 'deliveries' / 'new_delivery_screen.dart'
LISTA = APP / 'features' / 'deliveries' / 'deliveries_screen.dart'
ESTOQUE = APP / 'features' / 'stock' / 'stock_screen.dart'
STOCK_API = FLUTTER / 'packages' / 'epi_api' / 'lib' / 'endpoints' / 'stock_api.dart'

ENTREGAS = RAIZ / 'modules' / 'deliveries' / 'service.py'
ESTOQUE_ROTAS = RAIZ / 'modules' / 'stock' / 'routes.py'
REPOSITORIO = RAIZ / 'core' / 'repository.py'
EMPLOYEES = RAIZ / 'modules' / 'employees' / 'service.py'


def _sem_comentarios(texto):
    """Comentários explicam a regra removida citando-a. Não podem reprovar."""
    return '\n'.join(
        linha for linha in texto.splitlines()
        if not linha.lstrip().startswith('//')
    )


# ── o item físico REAL ───────────────────────────────────────────────────────

def test_a_entrega_envia_o_item_fisico_e_nao_o_epi():
    corpo = _sem_comentarios(CUBIT.read_text(encoding='utf-8'))
    assert 'final stockItemId = s.selectedItem!.id;' in corpo
    assert "final qrCode      = s.selectedItem!.qrCodeValue ?? '';" in corpo
    # As duas formas antigas, explicitamente proibidas.
    assert "'stock_item_id': s.selectedEpi!.id" not in corpo
    assert 's.selectedEpi!.code' not in corpo, \
        'o código do catálogo voltou a fazer papel de QR de item'


def test_sem_item_fisico_a_entrega_nao_sai():
    corpo = _sem_comentarios(CUBIT.read_text(encoding='utf-8'))
    assert 's.selectedItem == null' in corpo, \
        'submit deixou de exigir a unidade etiquetada'


def test_existe_um_passo_para_o_item():
    corpo = CUBIT.read_text(encoding='utf-8')
    assert 'enum DeliveryStep { employee, epi, item, details, signature }' in corpo
    tela = _sem_comentarios(TELA.read_text(encoding='utf-8'))
    assert 'DeliveryStep.item => const _ItemStep()' in tela


def test_os_dois_caminhos_produzem_um_item_real():
    """QR e seleção manual — o resultado dos dois é um `stock_item_id`."""
    corpo = _sem_comentarios(CUBIT.read_text(encoding='utf-8'))
    assert 'void selectItem(StockItem item)' in corpo
    assert 'Future<void> selectItemByQr(String qrCode)' in corpo
    # O QR é resolvido pelo BACKEND, dentro da Unidade — não por casamento de
    # string no cliente.
    assert '_qrLookup(unidade, qrCode)' in corpo


# ── a Unidade vem do colaborador ─────────────────────────────────────────────

def test_a_unidade_da_entrega_vem_do_colaborador():
    corpo = _sem_comentarios(CUBIT.read_text(encoding='utf-8'))
    assert 'int? get unitId => selectedEmployee?.unitId;' in corpo
    # Sem Unidade não há estoque de onde a entrega sairia.
    assert 'selectedEmployee != null && unitId != null' in corpo


def test_o_current_unit_id_respeita_movimentacao_temporaria():
    """A Unidade que o cliente usa é a que o backend resolveu.

    `Employee.unitId` no Dart lê `current_unit_id`, e quem o produz é
    `apply_current_unit_allocation` — que consulta `employee_unit_movements`.
    """
    modelo = (FLUTTER / 'packages/epi_api/lib/models/employee.dart').read_text(
        encoding='utf-8')
    assert "json['current_unit_id']" in modelo
    servico = EMPLOYEES.read_text(encoding='utf-8')
    trecho = servico[servico.index('def apply_current_unit_allocation'):][:1200]
    assert 'active_temporary_unit_allocations' in trecho
    assert "'temporary'" in servico


def test_a_tela_de_entrega_nao_recebe_mais_o_catalogo_corporativo():
    tela = _sem_comentarios(TELA.read_text(encoding='utf-8'))
    assert 'required this.epis' not in tela, \
        'a tela voltou a receber os EPIs do bootstrap'
    lista = _sem_comentarios(LISTA.read_text(encoding='utf-8'))
    assert 'b.epis' not in lista, 'a lista voltou a carregar EPIs do bootstrap'


# ── nenhum saldo corporativo governando operação local ───────────────────────

def test_o_passo_de_epi_usa_o_saldo_da_unidade():
    tela = _sem_comentarios(TELA.read_text(encoding='utf-8'))
    assert 'epi.unitStockQuantity ?? 0' in tela
    assert 'saldoLocal > 0' in tela
    # A habilitação pelo saldo corporativo, que era o defeito relatado.
    assert 'epi.stockQuantity > 0' not in tela
    # `deliveryStockAvailable` ("Estoque: {qty}") era usado em dois lugares
    # errados: como saldo corporativo na lista de EPIs e como rótulo da
    # quantidade no resumo. Nenhum dos dois sobrevive.
    assert 'deliveryStockAvailable' not in tela, \
        'voltou o rótulo de saldo sem escopo'


def test_a_entrega_e_de_uma_unidade_etiquetada():
    """O backend exige quantidade 1; o campo livre sempre falharia."""
    tela = _sem_comentarios(TELA.read_text(encoding='utf-8'))
    assert '_qtyController' not in tela, 'o campo de quantidade voltou'
    assert 'quantity: 1,' in tela
    entregas = ENTREGAS.read_text(encoding='utf-8')
    assert "raise ValueError('Entrega por leitura exige quantidade unitária (1).')" in entregas


def test_a_movimentacao_exige_unidade_explicita():
    corpo = _sem_comentarios(ESTOQUE.read_text(encoding='utf-8'))
    assert 'unitResolved' in corpo
    assert 'if (!unitResolved) {' in corpo, \
        'a folha de movimentação abre sem Unidade resolvida'
    assert 'state.unitId != 0' in corpo


def _folha_de_movimentacao(corpo):
    """Só a classe `_StockMoveSheetState`, recortada por chave de bloco.

    O arquivo inteiro contém leituras LEGÍTIMAS do saldo corporativo — o card
    mostra os dois saldos com rótulos distintos, e é assim que deve ser. Um
    matcher sobre o arquivo todo reprovaria o card correto junto com a folha
    errada, e alguém acabaria afrouxando o gate para o card passar.
    """
    inicio = corpo.index('class _StockMoveSheetState')
    resto = corpo[inicio:]
    fim = resto.index('\nclass ', 1)
    return resto[:fim]


# ── Ocorrência 2: a folha de movimentação (#278) ─────────────────────────────

def test_a_folha_de_movimentacao_usa_o_saldo_da_unidade():
    """O defeito: entrada/saída DE UMA UNIDADE conferidas contra o saldo da
    empresa inteira, sob rótulo genérico."""
    folha = _folha_de_movimentacao(_sem_comentarios(ESTOQUE.read_text(encoding='utf-8')))
    assert 'widget.epi.unitStockQuantity' in folha, \
        'a folha não lê o saldo da Unidade'
    assert 'widget.epi.stockQuantity' not in folha, \
        'a folha voltou a exibir o saldo CORPORATIVO como saldo operacional'


def test_a_folha_rotula_o_saldo_como_da_unidade():
    """`epiStockLabel` sozinho é "Estoque atual" — não diz de quem."""
    folha = _folha_de_movimentacao(_sem_comentarios(ESTOQUE.read_text(encoding='utf-8')))
    assert 'stockUnitBalanceSuffix' in folha, \
        'o saldo da folha voltou a aparecer sem escopo no rótulo'


def test_a_folha_nao_converte_null_em_zero():
    """`0` afirma "esta Unidade tem zero"; `null` é ausência de contexto.

    Trocar um pelo outro faria a folha afirmar saldo zerado onde não há saldo
    conhecido — e zero é justamente o número que impede a operação.
    """
    folha = _folha_de_movimentacao(_sem_comentarios(ESTOQUE.read_text(encoding='utf-8')))
    assert "unitStockQuantity ?? '—'" in folha, \
        'a folha perdeu o tratamento próprio de saldo desconhecido'
    assert 'unitStockQuantity ?? 0' not in folha, \
        'saldo desconhecido virou zero na folha'


def test_o_saldo_corporativo_do_card_continua_rotulado():
    """Contraprova dos três acima: eles não podem estar passando porque o saldo
    corporativo sumiu da tela. Ele CONTINUA no card, e rotulado."""
    corpo = _sem_comentarios(ESTOQUE.read_text(encoding='utf-8'))
    assert 'stockCompanyBalanceLabel' in corpo, \
        'o saldo corporativo rotulado sumiu do card — a tela perdeu informação'
    assert 'epi.companyStockQuantity ?? epi.stockQuantity' in corpo


def test_as_rotas_por_unidade_mandam_unit_id_e_dizem_por_que():
    """Mandar `unit_id` aqui é transporte, não decisão.

    Na tela de estoque a Unidade é a do ATOR e o servidor a deriva sozinho. Na
    entrega é a do COLABORADOR, que pode ser outra — e `resolve_unit_scope`
    valida contra a empresa do ator antes de usar.
    """
    api = STOCK_API.read_text(encoding='utf-8')
    for metodo in ('fetchUnitStockEpis', 'fetchUnitAvailableItems', 'lookupQr'):
        assert metodo in api, metodo
    # E os métodos antigos continuam SEM mandar unit_id. Os comentários saem
    # da varredura: eles explicam a regra citando o campo.
    codigo = _sem_comentarios(api)
    inicio = codigo.index('Future<List<Epi>> fetchStockEpis')
    fim = codigo.index('Future<List<StockItem>> fetchAvailableItems')
    assert "'unit_id'" not in codigo[inicio:fim]


# ── o que o backend garante, e que o cliente agora acompanha ─────────────────

def test_o_backend_autoriza_pelo_saldo_da_unidade():
    corpo = ENTREGAS.read_text(encoding='utf-8')
    assert 'get_unit_stock(connection, int(payload[\'company_id\']), delivery_unit_id' in corpo
    assert "raise ValueError('Estoque insuficiente para realizar a entrega.')" in corpo


def test_o_backend_exige_o_item_etiquetado_daquela_unidade():
    corpo = ENTREGAS.read_text(encoding='utf-8')
    assert 'FROM epi_stock_items ' in corpo
    assert "raise ValueError('Unidade etiquetada não encontrada.')" in corpo
    assert "int(stock_item['unit_id']) != int(delivery_unit_id)" in corpo
    assert "int(stock_item['epi_id']) != int(payload['epi_id'])" in corpo
    assert "str(stock_item['status']) != 'in_stock'" in corpo


def test_o_backend_reivindica_o_item_atomicamente():
    """Sem o claim, duas entregas simultâneas baixariam o mesmo item."""
    corpo = ENTREGAS.read_text(encoding='utf-8')
    assert "WHERE id = ? AND status = 'in_stock'" in corpo


def test_a_entrega_ocorre_na_unidade_atual_do_colaborador():
    corpo = ENTREGAS.read_text(encoding='utf-8')
    assert 'employee_current_unit_id = get_employee_current_unit(' in corpo
    assert "raise ValueError('Entrega só pode ocorrer na unidade operacional atual do colaborador.')" in corpo


def test_perfil_travado_e_fail_closed_nas_operacoes_fisicas():
    entregas = ENTREGAS.read_text(encoding='utf-8')
    assert "if actor.get('role') in ('admin', 'user') and not actor_scope_unit_id:" in entregas
    assert 'PermissionError' in entregas
    rotas = ESTOQUE_ROTAS.read_text(encoding='utf-8')
    assert "raise PermissionError('Perfil sem unidade operacional ativa para movimentar estoque.')" in rotas


def test_saida_manual_de_estoque_continua_bloqueada():
    """A baixa passa pelo fluxo de entrega, que é o que tem rastreabilidade."""
    rotas = ESTOQUE_ROTAS.read_text(encoding='utf-8')
    assert 'Saída manual bloqueada' in rotas


def test_nenhuma_rota_fisica_le_saldo_corporativo():
    """`company_stock_quantity` informa; `unit_epi_stock` autoriza."""
    entregas = ENTREGAS.read_text(encoding='utf-8')
    assert 'company_stock_quantity' not in entregas
    assert 'is_company_stock_critical' not in entregas
