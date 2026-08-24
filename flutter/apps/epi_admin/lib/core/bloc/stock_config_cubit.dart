import 'package:epi_api/epi_api.dart';
import 'package:equatable/equatable.dart';
import 'package:flutter_bloc/flutter_bloc.dart';

/// Configuração de estoque por `Unidade + EPI` (#271-B2-a).
///
/// A lógica mora aqui, e não na tela, pelo mesmo motivo da B2-b: não há
/// toolchain Dart no ambiente de desenvolvimento, então o que estiver num
/// `StatefulWidget` só é exercitado no CI — e o que esta fatia protege é
/// comportamento, não pintura.
///
/// Quatro invariantes que os testes travam:
///
/// 1. **O alerta não persiste sozinho.** O toggle mexe só no rascunho local;
///    `POST` acontece em [saveAlert]. Silenciar o alerta de um EPI é decisão
///    operacional, e um toggle que grava ao toque a torna reversível só por
///    acidente.
/// 2. **Nenhuma classificação é recalculada.** `attentionLimit`,
///    `stockStatus` e `underlyingStatus` são LIDOS de `/api/stock/epis` e
///    exibidos como vieram. O gate `tests/stock_rule_scan.py` reprova o build
///    se alguém comparar saldo com mínimo aqui.
/// 3. **Escopo é fail-closed.** Sem Unidade não há leitura nem escrita; sem
///    EPI validado contra a lista daquela Unidade, idem.
/// 4. **Resposta de par errado é descartada.** Toda gravação carrega o par que
///    a originou e é conferida na volta.

/// Qual dos três parâmetros uma ação toca. Eles são independentes no backend
/// (rotas separadas) e por isso o erro e o aviso de conclusão também são por
/// bloco: uma gravação de mínimo que falha não pode invalidar o bloco da faixa
/// de atenção.
enum StockConfigBlock { minimum, attention, alert }

/// Salvar e restaurar podem terminar com o MESMO valor e significam coisas
/// opostas. Duas mensagens, nunca um "pronto" genérico.
enum StockConfigOutcome { saved, restored }

enum StockConfigStatus { initial, loading, ready, saving, error }

class StockConfigState extends Equatable {
  const StockConfigState({
    this.status = StockConfigStatus.initial,
    this.unitId,
    this.epiId,
    this.epis = const <Epi>[],
    this.query = '',
    this.selected,
    this.minimum,
    this.attention,
    this.alert,
    this.alertDraft = true,
    this.busyBlock,
    this.errorBlock,
    this.error,
    this.outcome,
    this.outcomeBlock,
  });

  final StockConfigStatus status;

  /// Escopo corrente. **Sempre vem do `EpiUnitSelector`**, nunca de
  /// `bootstrap`, nunca do `unitScopeId` derivado da listagem de estoque
  /// (`stock_cubit` faz isso para LEITURA e aquilo é retrato, não autoridade).
  final int? unitId;

  final int? epiId;

  /// EPIs visíveis naquela Unidade, como o servidor os recortou. A tela não
  /// reavalia visibilidade GLOBAL/JV — quem faz isso é `/api/stock/epis`.
  final List<Epi> epis;

  final String query;

  /// Linha do par corrente. Fonte ÚNICA dos derivados exibidos
  /// (`attentionLimit`, `stockStatus`, `underlyingStatus`, saldo).
  final Epi? selected;

  /// Valor e ORIGEM de cada parâmetro, sempre como o servidor devolveu.
  final UnitEpiMinimum? minimum;
  final UnitEpiAttention? attention;
  final UnitEpiAlert? alert;

  /// Rascunho local do toggle de alerta. Diverge de `alert.enabled` enquanto
  /// houver alteração pendente — ver [alertDirty].
  final bool alertDraft;

  /// Qual bloco está gravando. `null` quando nenhum está.
  final StockConfigBlock? busyBlock;

  final StockConfigBlock? errorBlock;
  final String? error;

  final StockConfigOutcome? outcome;
  final StockConfigBlock? outcomeBlock;

  /// Qualquer operação de rede em voo. Enquanto for `true` a tela desabilita
  /// **tudo** que muda estado — inclusive os dois seletores. Trocar de par com
  /// uma requisição em voo faria a resposta chegar e ser pintada sobre o par
  /// errado; [_parCorrente] é a rede, isto é a prevenção.
  bool get isBusy =>
      status == StockConfigStatus.loading || status == StockConfigStatus.saving;

  /// Há Unidade E EPI resolvidos? Abaixo disto a tela não lê nem grava.
  bool get hasScope => unitId != null && epiId != null;

  /// O toggle foi mexido e ainda não foi gravado.
  bool get alertDirty => alert != null && alertDraft != alert!.enabled;

  /// A gravação pendente DESLIGA o alerta — a tela precisa confirmar antes do
  /// `POST`. Ligar não pede confirmação: só o silenciamento é a decisão que
  /// merece uma pergunta.
  bool get alertRequiresConfirmation => alertDirty && !alertDraft;

  /// Restaurar só faz sentido quando existe decisão local para apagar. O
  /// backend trata o caso herdado como no-op silencioso, mas oferecer um botão
  /// que não faz nada é pior do que desabilitá-lo.
  bool get canRestoreMinimum => minimum?.isUnitConfigured ?? false;
  bool get canRestoreAttention => attention?.isUnitConfigured ?? false;
  bool get canRestoreAlert => alert?.isUnitConfigured ?? false;

  /// Lista filtrada do seletor de EPI. Filtro é LOCAL sobre o que o servidor
  /// já recortou: a busca é conveniência de navegação, não um segundo recorte
  /// de visibilidade.
  List<Epi> get filtered {
    final termo = query.trim().toLowerCase();
    if (termo.isEmpty) return epis;
    return epis.where((e) => e.name.toLowerCase().contains(termo)).toList();
  }

  StockConfigState _copyWith({
    StockConfigStatus? status,
    int? unitId,
    int? epiId,
    List<Epi>? epis,
    String? query,
    Epi? selected,
    UnitEpiMinimum? minimum,
    UnitEpiAttention? attention,
    UnitEpiAlert? alert,
    bool? alertDraft,
    StockConfigBlock? busyBlock,
    StockConfigBlock? errorBlock,
    String? error,
    StockConfigOutcome? outcome,
    StockConfigBlock? outcomeBlock,
    bool clearUnit = false,
    bool clearEpi = false,
    bool clearBusy = false,
    bool clearError = false,
    bool clearOutcome = false,
    bool clearParams = false,
    bool clearSelected = false,
  }) =>
      StockConfigState(
        status: status ?? this.status,
        unitId: clearUnit ? null : (unitId ?? this.unitId),
        epiId: clearEpi || clearUnit ? null : (epiId ?? this.epiId),
        epis: epis ?? this.epis,
        query: query ?? this.query,
        selected: clearSelected || clearParams || clearEpi || clearUnit
            ? null
            : (selected ?? this.selected),
        minimum: clearParams || clearEpi || clearUnit
            ? null
            : (minimum ?? this.minimum),
        attention: clearParams || clearEpi || clearUnit
            ? null
            : (attention ?? this.attention),
        alert:
            clearParams || clearEpi || clearUnit ? null : (alert ?? this.alert),
        alertDraft: alertDraft ?? this.alertDraft,
        busyBlock: clearBusy ? null : (busyBlock ?? this.busyBlock),
        errorBlock: clearError ? null : (errorBlock ?? this.errorBlock),
        error: clearError ? null : (error ?? this.error),
        outcome: clearOutcome ? null : (outcome ?? this.outcome),
        outcomeBlock: clearOutcome ? null : (outcomeBlock ?? this.outcomeBlock),
      );

  @override
  List<Object?> get props => [
        status, unitId, epiId, epis, query, selected,
        minimum, attention, alert, alertDraft,
        busyBlock, errorBlock, error, outcome, outcomeBlock,
      ];
}

class StockConfigCubit extends Cubit<StockConfigState> {
  StockConfigCubit({
    required this.actorUserId,
    required this.stockApi,
  }) : super(const StockConfigState());

  final int actorUserId;
  final StockApi stockApi;

  /// EPI pedido por deep link, ainda NÃO validado. Guardado até a lista
  /// daquela Unidade chegar; aplicado só se constar dela, descartado em
  /// silêncio caso contrário.
  int? _epiPedidoPorDeepLink;

  /// Registra o `?epi_id=` da URL. Não seleciona nada por si: entrada de URL
  /// não é autorização e não pode virar escopo antes de o servidor confirmar
  /// que aquele EPI é visível na Unidade escolhida.
  void deepLinkEpi(int? epiId) => _epiPedidoPorDeepLink = epiId;

  /// A Unidade mudou (ou foi resolvida pela primeira vez) pelo seletor
  /// compartilhado — que já a validou contra `GET /api/units/selectable`.
  ///
  /// Zera EPI, parâmetros e lista ANTES de buscar. Manter o que estava na tela
  /// durante a carga exibiria os números da Unidade A sob o rótulo da B; e um
  /// EPI visível em A pode não ser visível em B.
  Future<void> setUnit(int? unitId) async {
    if (unitId == null) {
      emit(state._copyWith(
        status: StockConfigStatus.initial,
        clearUnit: true,
        epis: const <Epi>[],
        clearError: true,
        clearOutcome: true,
      ));
      return;
    }
    emit(state._copyWith(
      status: StockConfigStatus.loading,
      unitId: unitId,
      clearEpi: true,
      clearParams: true,
      epis: const <Epi>[],
      clearError: true,
      clearOutcome: true,
    ));
    await _carregarEpis(unitId);
  }

  Future<void> _carregarEpis(int unitId) async {
    try {
      final epis = await stockApi.fetchUnitStockEpis(
        actorUserId: actorUserId,
        unitId: unitId,
      );
      // A Unidade mudou enquanto a lista vinha: esta resposta é de um escopo
      // que já não está na tela.
      if (state.unitId != unitId) return;
      emit(state._copyWith(status: StockConfigStatus.ready, epis: epis));

      // Deep link só agora, com a lista na mão. `firstWhere` com `orElse` em
      // vez de `any` + índice para não percorrer a lista duas vezes.
      final pedido = _epiPedidoPorDeepLink;
      if (pedido != null) {
        _epiPedidoPorDeepLink = null;
        if (epis.any((e) => e.id == pedido)) selectEpi(pedido);
      }
    } on Object catch (e) {
      if (state.unitId != unitId) return;
      emit(state._copyWith(
        status: StockConfigStatus.error,
        error: e.toString(),
        clearBusy: true,
      ));
    }
  }

  /// Escolhe o EPI. Só aceita um que esteja na lista daquela Unidade — a mesma
  /// guarda que `UnitSelectorCubit.select` aplica às Unidades, pelo mesmo
  /// motivo: aceitar aqui exibiria um par que o servidor recusaria.
  void selectEpi(int epiId) {
    final unitId = state.unitId;
    if (unitId == null) return;
    final linha = state.epis.where((e) => e.id == epiId).toList();
    if (linha.isEmpty) return;
    _aplicarLinha(linha.first);
  }

  /// Traduz a linha de `/api/stock/epis` nos três parâmetros + derivados.
  ///
  /// Os valores e as origens saem TODOS do servidor. Nenhum é deduzido, e o
  /// rascunho do alerta nasce igual ao que está gravado — sem alteração
  /// pendente até o usuário mexer.
  void _aplicarLinha(Epi linha) {
    final unitId = linha.unitScopeId ?? state.unitId!;
    final alerta = UnitEpiAlert(
      unitId: unitId,
      enabled: linha.stockAlertEnabled ?? true,
      source: linha.alertSource ?? '',
    );
    emit(state._copyWith(
      status: StockConfigStatus.ready,
      epiId: linha.id,
      selected: linha,
      minimum: UnitEpiMinimum(
        unitId: unitId,
        minimumStock: linha.unitMinimumStock ?? 0,
        source: linha.minimumStockSource ?? '',
      ),
      attention: UnitEpiAttention(
        unitId: unitId,
        attentionPercentage: linha.effectiveAttentionPercentage ?? 0,
        source: linha.attentionPercentageSource ?? '',
      ),
      alert: alerta,
      alertDraft: alerta.enabled,
      clearError: true,
      clearOutcome: true,
      clearBusy: true,
    ));
  }

  void search(String termo) => emit(state._copyWith(query: termo));

  /// Mexe apenas no rascunho local (#271-B2-a, ajuste 1). **Não grava.**
  void toggleAlertDraft(bool habilitado) {
    if (state.alert == null || state.isBusy) return;
    emit(state._copyWith(alertDraft: habilitado, clearOutcome: true));
  }

  // ── Gravações ────────────────────────────────────────────────────────────

  Future<void> saveMinimum(int valor) async {
    // Negativo é o único formato que o backend normaliza em silêncio
    // (`max(0, ...)`). Recusar aqui evita gravar 0 quando o usuário quis outra
    // coisa. **Não há teto**: o backend não define nenhum, e inventar um no
    // cliente criaria uma régua que o servidor desconhece.
    if (valor < 0) {
      _erroLocal(StockConfigBlock.minimum, 'negative');
      return;
    }
    await _executar(
      StockConfigBlock.minimum,
      StockConfigOutcome.saved,
      (unitId, epiId) => stockApi.setUnitEpiMinimum(
        actorUserId: actorUserId,
        unitId: unitId,
        epiId: epiId,
        minimumStock: valor,
      ),
    );
  }

  Future<void> restoreMinimum() => _executar(
        StockConfigBlock.minimum,
        StockConfigOutcome.restored,
        (unitId, epiId) => stockApi.restoreUnitEpiMinimum(
          actorUserId: actorUserId,
          unitId: unitId,
          epiId: epiId,
        ),
      );

  Future<void> saveAttention(int percentual) async {
    // 0–100 é contrato PUBLICADO do backend (`MAX_ATTENTION_PERCENTAGE`), não
    // um limite inventado aqui — por isso esta validação é legítima e a do
    // mínimo, que não tem teto publicado, para na negatividade.
    if (percentual < 0 || percentual > 100) {
      _erroLocal(StockConfigBlock.attention, 'range');
      return;
    }
    await _executar(
      StockConfigBlock.attention,
      StockConfigOutcome.saved,
      (unitId, epiId) => stockApi.setUnitEpiAttentionPercentage(
        actorUserId: actorUserId,
        unitId: unitId,
        epiId: epiId,
        attentionPercentage: percentual,
      ),
    );
  }

  Future<void> restoreAttention() => _executar(
        StockConfigBlock.attention,
        StockConfigOutcome.restored,
        (unitId, epiId) => stockApi.restoreUnitEpiAttentionPercentage(
          actorUserId: actorUserId,
          unitId: unitId,
          epiId: epiId,
        ),
      );

  /// Persiste o rascunho do toggle. A tela é responsável por confirmar antes
  /// de chamar quando [StockConfigState.alertRequiresConfirmation] — a
  /// confirmação é diálogo, mas a CONDIÇÃO dela mora aqui, para ser testável.
  Future<void> saveAlert() async {
    if (!state.alertDirty) return;
    final desejado = state.alertDraft;
    await _executar(
      StockConfigBlock.alert,
      StockConfigOutcome.saved,
      (unitId, epiId) => stockApi.setUnitEpiAlertEnabled(
        actorUserId: actorUserId,
        unitId: unitId,
        epiId: epiId,
        alertEnabled: desejado,
      ),
    );
  }

  /// Apaga a decisão local de alerta. Operação DISTINTA de [saveAlert] com
  /// `true`: aquela deixa o par `unit_configured`, esta o devolve à herança.
  Future<void> restoreAlert() => _executar(
        StockConfigBlock.alert,
        StockConfigOutcome.restored,
        (unitId, epiId) => stockApi.restoreUnitEpiAlertEnabled(
          actorUserId: actorUserId,
          unitId: unitId,
          epiId: epiId,
        ),
      );

  void _erroLocal(StockConfigBlock bloco, String chave) => emit(state._copyWith(
        status: StockConfigStatus.ready,
        errorBlock: bloco,
        error: chave,
        clearOutcome: true,
        clearBusy: true,
      ));

  /// Tronco comum das seis gravações.
  ///
  /// O par é capturado ANTES da chamada e conferido depois. Duas conferências,
  /// porque elas cobrem coisas diferentes: `unitId` volta na resposta e prova
  /// qual Unidade o SERVIDOR usou (que para perfil travado pode não ser a que
  /// o cliente mandou); `epiId` não volta, e é conferido contra o capturado.
  Future<void> _executar(
    StockConfigBlock bloco,
    StockConfigOutcome desfecho,
    Future<Object> Function(int unitId, int epiId) acao,
  ) async {
    final unitId = state.unitId;
    final epiId = state.epiId;
    if (unitId == null || epiId == null || state.isBusy) return;

    emit(state._copyWith(
      status: StockConfigStatus.saving,
      busyBlock: bloco,
      clearError: true,
      clearOutcome: true,
    ));

    try {
      final resposta = await acao(unitId, epiId);
      if (!_parCorrente(unitId, epiId)) return;

      // Aplica valor e origem VINDOS DO SERVIDOR. Nunca deduzidos do botão
      // clicado: salvar 20 e restaurar para 20 chegam aqui com o mesmo número
      // e origens opostas, e é a origem que a tela mostra.
      var proximo = state._copyWith(
        status: StockConfigStatus.ready,
        outcome: desfecho,
        outcomeBlock: bloco,
        clearBusy: true,
      );
      if (resposta is UnitEpiMinimum) {
        proximo = proximo._copyWith(minimum: resposta);
      } else if (resposta is UnitEpiAttention) {
        proximo = proximo._copyWith(attention: resposta);
      } else if (resposta is UnitEpiAlert) {
        proximo = proximo._copyWith(
          alert: resposta,
          alertDraft: resposta.enabled,
        );
      }
      emit(proximo);

      // Os derivados (`attention_limit`, `stock_status`, `underlying_status`)
      // NÃO voltam nas respostas de escrita, e não existe `GET` de par único.
      // Relê a listagem daquela Unidade para trazê-los recalculados PELO
      // SERVIDOR. A alternativa seria calculá-los aqui — que é exatamente o
      // que o gate da 1.1D-C4 proíbe.
      await _recarregarDerivados(unitId, epiId);
    } on Object catch (e) {
      if (!_parCorrente(unitId, epiId)) return;
      emit(state._copyWith(
        status: StockConfigStatus.ready,
        errorBlock: bloco,
        error: e.toString(),
        clearBusy: true,
      ));
    }
  }

  /// O par que originou a requisição ainda é o que está na tela?
  ///
  /// Sem isto, uma resposta lenta da Unidade A chegaria depois de o usuário
  /// trocar para a B e seria pintada como se fosse dela.
  bool _parCorrente(int unitId, int epiId) =>
      state.unitId == unitId && state.epiId == epiId;

  Future<void> _recarregarDerivados(int unitId, int epiId) async {
    try {
      final epis = await stockApi.fetchUnitStockEpis(
        actorUserId: actorUserId,
        unitId: unitId,
      );
      if (!_parCorrente(unitId, epiId)) return;
      final linha = epis.where((e) => e.id == epiId).toList();
      emit(state._copyWith(
        epis: epis,
        selected: linha.isEmpty ? null : linha.first,
        clearSelected: linha.isEmpty,
      ));
    } on Object catch (_) {
      // A gravação DEU CERTO — o valor e a origem já estão aplicados e são os
      // do servidor. Só os derivados ficaram velhos. Transformar isso em erro
      // diria ao usuário que a gravação falhou, o que seria mentira; a tela
      // mostra os derivados como indisponíveis em vez disso.
      if (!_parCorrente(unitId, epiId)) return;
      emit(state._copyWith(clearSelected: true));
    }
  }
}
