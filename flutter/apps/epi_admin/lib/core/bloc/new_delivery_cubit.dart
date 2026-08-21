import 'dart:convert';
import 'dart:math';
import 'package:dio/dio.dart';
import 'package:equatable/equatable.dart';
import 'package:epi_api/epi_api.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import '../api/api_client.dart';
import '../sync/offline_queue.dart';
import '../../features/deliveries/data/datasources/deliveries_remote_datasource.dart';
import '../../features/deliveries/data/repository_impl/deliveries_repository_impl.dart';
import '../../features/deliveries/domain/repositories/deliveries_repository.dart';

/// Passos da entrega. `item` entrou na #278: entre escolher o EPI e preencher
/// os detalhes existe uma decisão física — QUAL unidade etiquetada sai do
/// estoque. Sem esse passo o cliente não tinha um `stock_item_id` real para
/// enviar, e mandava o id do EPI no lugar.
enum DeliveryStep { employee, epi, item, details, signature }

/// Impedimentos que a TELA traduz. O cubit não guarda texto voltado ao
/// usuário: o app fala cinco idiomas, e uma string em português no estado
/// chegaria assim a todos eles.
enum DeliveryBlock { none, employeeWithoutUnit, qrFromAnotherEpi }

/// Carregadores injetáveis — os testes exercitam o fluxo sem rede.
typedef UnitEpisLoader = Future<List<Epi>> Function(int unitId);
typedef UnitItemsLoader = Future<List<StockItem>> Function(int unitId, int epiId);
typedef UnitQrLookup = Future<StockItem> Function(int unitId, String qrCode);

// ── State ──────────────────────────────────────────────────────────────────

class NewDeliveryState extends Equatable {
  const NewDeliveryState({
    this.step = DeliveryStep.employee,
    this.selectedEmployee,
    this.selectedEpi,
    this.selectedItem,
    this.unitEpis = const [],
    this.availableItems = const [],
    this.isLoadingEpis = false,
    this.isLoadingItems = false,
    this.block = DeliveryBlock.none,
    this.quantity = 1,
    this.deliveryDate,
    this.nextReplacementDate,
    this.sector,
    this.roleName,
    this.isSubmitting = false,
    this.error,
    this.successId,
    this.offlineQueued = false,
  });

  final DeliveryStep step;
  final Employee? selectedEmployee;
  final Epi? selectedEpi;

  /// A unidade etiquetada que vai sair do estoque. É daqui que sai o
  /// `stock_item_id` REAL da entrega — nunca do `Epi`, que é catálogo.
  final StockItem? selectedItem;

  /// EPIs com saldo NA UNIDADE do colaborador. Carregados depois que ele é
  /// escolhido, porque é ele quem determina a Unidade.
  final List<Epi> unitEpis;

  /// Itens físicos `in_stock` do EPI escolhido, naquela Unidade, em ordem FEFO
  /// definida pelo servidor.
  final List<StockItem> availableItems;

  final bool isLoadingEpis;
  final bool isLoadingItems;

  /// Impedimento a exibir, já traduzido pela tela.
  final DeliveryBlock block;

  final int quantity;
  final String? deliveryDate;
  final String? nextReplacementDate;
  final String? sector;
  final String? roleName;
  final bool isSubmitting;
  final String? error;
  final int? successId;
  final bool offlineQueued;

  /// Unidade operacional do colaborador, resolvida PELO BACKEND
  /// (`current_unit_id`, com movimentação temporária vigente aplicada).
  ///
  /// Entrega é operação física: ela sai do estoque de UMA Unidade, e essa
  /// Unidade é a de quem recebe. Não há seletor de Unidade neste fluxo — teria
  /// de ser preenchido com o que o colaborador já determina, criando uma
  /// segunda fonte para o mesmo fato.
  int? get unitId => selectedEmployee?.unitId;

  /// Sem colaborador não há Unidade, e sem Unidade não há entrega local. O
  /// passo de EPI não abre — em vez de abrir e recusar no fim.
  bool get canProceedFromEmployee => selectedEmployee != null && unitId != null;

  bool get canProceedFromEpi => selectedEpi != null;

  /// A entrega exige item etiquetado: sem item físico escolhido não avança.
  bool get canProceedFromItem => selectedItem != null;
  bool get canProceedFromDetails =>
      quantity > 0 &&
      deliveryDate != null &&
      nextReplacementDate != null &&
      (sector?.isNotEmpty ?? false) &&
      (roleName?.isNotEmpty ?? false);

  NewDeliveryState copyWith({
    DeliveryStep? step,
    Employee? selectedEmployee,
    Epi? selectedEpi,
    StockItem? selectedItem,
    List<Epi>? unitEpis,
    List<StockItem>? availableItems,
    bool? isLoadingEpis,
    bool? isLoadingItems,
    DeliveryBlock? block,
    bool clearItem = false,
    int? quantity,
    String? deliveryDate,
    String? nextReplacementDate,
    String? sector,
    String? roleName,
    bool? isSubmitting,
    String? error,
    int? successId,
    bool? offlineQueued,
    bool clearError = false,
  }) =>
      NewDeliveryState(
        step: step ?? this.step,
        selectedEmployee: selectedEmployee ?? this.selectedEmployee,
        selectedEpi: selectedEpi ?? this.selectedEpi,
        // Trocar de EPI invalida o item escolhido: ele pertence ao EPI
        // anterior, e o backend recusaria a combinação.
        selectedItem: clearItem ? null : (selectedItem ?? this.selectedItem),
        unitEpis: unitEpis ?? this.unitEpis,
        availableItems: availableItems ?? this.availableItems,
        isLoadingEpis: isLoadingEpis ?? this.isLoadingEpis,
        isLoadingItems: isLoadingItems ?? this.isLoadingItems,
        block: clearError ? DeliveryBlock.none : (block ?? this.block),
        quantity: quantity ?? this.quantity,
        deliveryDate: deliveryDate ?? this.deliveryDate,
        nextReplacementDate: nextReplacementDate ?? this.nextReplacementDate,
        sector: sector ?? this.sector,
        roleName: roleName ?? this.roleName,
        isSubmitting: isSubmitting ?? this.isSubmitting,
        error: clearError ? null : (error ?? this.error),
        successId: successId ?? this.successId,
        offlineQueued: offlineQueued ?? this.offlineQueued,
      );

  @override
  List<Object?> get props => [
        step,
        selectedEmployee,
        selectedEpi,
        selectedItem?.id,
        unitEpis.map((e) => e.id).toList(),
        availableItems.map((i) => i.id).toList(),
        isLoadingEpis,
        isLoadingItems,
        block,
        quantity,
        deliveryDate,
        nextReplacementDate,
        sector,
        roleName,
        isSubmitting,
        error,
        successId,
        offlineQueued,
      ];
}

// ── Cubit ──────────────────────────────────────────────────────────────────

class NewDeliveryCubit extends Cubit<NewDeliveryState> {
  NewDeliveryCubit({
    DeliveriesRepository? repository,
    OfflineQueue? offlineQueue,
    UnitEpisLoader? episLoader,
    UnitItemsLoader? itemsLoader,
    UnitQrLookup? qrLookup,
  })  : _repository = repository ??
            const DeliveriesRepositoryImpl(ApiDeliveriesRemoteDataSource()),
        _offlineQueue = offlineQueue ?? const SyncDatabaseQueue(),
        _episLoader = episLoader ?? _carregarEpisDaUnidade,
        _itemsLoader = itemsLoader ?? _carregarItensDaUnidade,
        _qrLookup = qrLookup ?? _resolverQr,
        super(const NewDeliveryState());

  final DeliveriesRepository _repository;
  final OfflineQueue _offlineQueue;
  final UnitEpisLoader _episLoader;
  final UnitItemsLoader _itemsLoader;
  final UnitQrLookup _qrLookup;

  static Future<List<Epi>> _carregarEpisDaUnidade(int unitId) =>
      ApiClient.stock.fetchUnitStockEpis(
        actorUserId: ApiClient.actorUserId,
        unitId: unitId,
      );

  static Future<List<StockItem>> _carregarItensDaUnidade(
    int unitId,
    int epiId,
  ) =>
      ApiClient.stock.fetchUnitAvailableItems(
        actorUserId: ApiClient.actorUserId,
        unitId: unitId,
        epiId: epiId,
      );

  static Future<StockItem> _resolverQr(int unitId, String qrCode) =>
      ApiClient.stock.lookupQr(
        actorUserId: ApiClient.actorUserId,
        unitId: unitId,
        qrCode: qrCode,
      );

  /// Escolher o colaborador é o que RESOLVE a Unidade da entrega, e por isso
  /// dispara a carga do estoque local. Antes da #278 este passo só guardava a
  /// pessoa, e o passo seguinte listava o catálogo corporativo inteiro.
  Future<void> selectEmployee(Employee employee) async {
    final unidade = employee.unitId;
    if (unidade == null) {
      // Colaborador sem Unidade não tem estoque de onde a entrega sairia.
      // Recusar aqui é mais honesto do que deixar avançar e falhar no fim.
      emit(state.copyWith(
        selectedEmployee: employee,
        sector: employee.sector,
        roleName: employee.role,
        block: DeliveryBlock.employeeWithoutUnit,
      ));
      return;
    }
    emit(state.copyWith(
      selectedEmployee: employee,
      sector: employee.sector,
      roleName: employee.role,
      step: DeliveryStep.epi,
      isLoadingEpis: true,
      unitEpis: const [],
      availableItems: const [],
      clearItem: true,
      clearError: true,
    ));
    try {
      final epis = await _episLoader(unidade);
      if (isClosed) return;
      emit(state.copyWith(isLoadingEpis: false, unitEpis: epis));
    } on Exception catch (e) {
      if (isClosed) return;
      emit(state.copyWith(isLoadingEpis: false, error: e.toString()));
    }
  }

  /// Escolher o EPI abre o passo do ITEM: quais unidades etiquetadas daquele
  /// EPI existem nesta Unidade, em ordem FEFO decidida pelo servidor.
  Future<void> selectEpi(Epi epi) async {
    final unidade = state.unitId;
    if (unidade == null) return;
    emit(state.copyWith(
      selectedEpi: epi,
      step: DeliveryStep.item,
      isLoadingItems: true,
      availableItems: const [],
      clearItem: true,
      clearError: true,
    ));
    try {
      final itens = await _itemsLoader(unidade, epi.id);
      if (isClosed) return;
      emit(state.copyWith(isLoadingItems: false, availableItems: itens));
    } on Exception catch (e) {
      if (isClosed) return;
      emit(state.copyWith(isLoadingItems: false, error: e.toString()));
    }
  }

  /// Seleção manual entre os itens disponíveis da Unidade.
  void selectItem(StockItem item) {
    emit(state.copyWith(selectedItem: item, step: DeliveryStep.details));
  }

  /// Leitura de QR. Quem resolve o código é o BACKEND, restrito à Unidade e à
  /// empresa — um QR de outra Unidade simplesmente não encontra item.
  Future<void> selectItemByQr(String qrCode) async {
    final unidade = state.unitId;
    final epi = state.selectedEpi;
    if (unidade == null || epi == null) return;
    emit(state.copyWith(isLoadingItems: true, clearError: true));
    try {
      final item = await _qrLookup(unidade, qrCode);
      if (isClosed) return;
      if (item.epiId != epi.id) {
        // O item existe e está nesta Unidade, mas é de outro EPI. O backend
        // recusaria igual; dizer isso aqui evita percorrer o resto do fluxo.
        emit(state.copyWith(
          isLoadingItems: false,
          block: DeliveryBlock.qrFromAnotherEpi,
        ));
        return;
      }
      emit(state.copyWith(
        isLoadingItems: false,
        selectedItem: item,
        step: DeliveryStep.details,
      ));
    } on Exception catch (e) {
      if (isClosed) return;
      emit(state.copyWith(isLoadingItems: false, error: e.toString()));
    }
  }

  void setDetails({
    int? quantity,
    String? deliveryDate,
    String? nextReplacementDate,
    String? sector,
    String? roleName,
  }) {
    emit(state.copyWith(
      quantity: quantity,
      deliveryDate: deliveryDate,
      nextReplacementDate: nextReplacementDate,
      sector: sector,
      roleName: roleName,
    ));
  }

  void goToSignature() {
    emit(state.copyWith(step: DeliveryStep.signature));
  }

  void goBack() {
    final prev = switch (state.step) {
      DeliveryStep.epi => DeliveryStep.employee,
      DeliveryStep.item => DeliveryStep.epi,
      DeliveryStep.details => DeliveryStep.item,
      DeliveryStep.signature => DeliveryStep.details,
      DeliveryStep.employee => DeliveryStep.employee,
    };
    emit(state.copyWith(step: prev));
  }

  Future<bool> submit({
    required int companyId,
    required String signatureData,
  }) async {
    final s = state;
    // O item físico é obrigatório: a entrega baixa UMA unidade etiquetada, e o
    // backend exige uma linha de `epi_stock_items` que confira em empresa,
    // Unidade, EPI, QR e status.
    if (s.selectedEmployee == null ||
        s.selectedEpi == null ||
        s.selectedItem == null) {
      return false;
    }

    emit(state.copyWith(isSubmitting: true, clearError: true));
    final sector    = s.sector ?? s.selectedEmployee!.sector ?? '';
    final roleName  = s.roleName ?? s.selectedEmployee!.role ?? '';
    // `stock_item_id` e `stock_qr_code` vêm do ITEM, não do EPI.
    //
    // Até a #278 iam `s.selectedEpi!.id` e `s.selectedEpi!.code` — o id do
    // catálogo e o código de compra do EPI. O backend procura esse id em
    // `epi_stock_items` e compara o código com `qr_code_value`: dois
    // identificadores de outro domínio, que só casariam por coincidência. A
    // entrega pelo app não podia dar certo.
    final stockItemId = s.selectedItem!.id;
    final qrCode      = s.selectedItem!.qrCodeValue ?? '';
    // Uma chave por **tentativa de entrega**, não por requisição HTTP: ela vai
    // junto no payload da fila, então o reenvio depois de uma resposta perdida
    // repete a MESMA chave e o backend devolve a entrega original. Sem isso o
    // reenvio esbarrava no item já entregue e a fila nunca drenava.
    final idempotencyKey = _novaChaveDeIdempotencia();
    final Map<String, dynamic> payload = {
      'idempotency_key': idempotencyKey,
      'company_id': companyId,
      'employee_id': s.selectedEmployee!.id,
      'epi_id': s.selectedEpi!.id,
      'quantity': s.quantity,
      'sector': sector,
      'role_name': roleName,
      'delivery_date': s.deliveryDate!,
      'next_replacement_date': s.nextReplacementDate!,
      'stock_item_id': stockItemId,
      'stock_qr_code': qrCode,
    };
    try {
      final id = await _repository.createDelivery(
        companyId: companyId,
        employeeId: s.selectedEmployee!.id,
        epiId: s.selectedEpi!.id,
        quantity: s.quantity,
        sector: sector,
        roleName: roleName,
        deliveryDate: s.deliveryDate!,
        nextReplacementDate: s.nextReplacementDate!,
        stockItemId: stockItemId,
        stockQrCode: qrCode,
        idempotencyKey: idempotencyKey,
      );
      emit(state.copyWith(isSubmitting: false, successId: id));
      return true;
    } on DioException catch (e) {
      if (e.type == DioExceptionType.connectionError ||
          e.type == DioExceptionType.connectionTimeout) {
        await _offlineQueue.enqueue(
          opType: 'delivery_create',
          payload: payload,
        );
        emit(state.copyWith(isSubmitting: false, offlineQueued: true));
        return true;
      }
      emit(state.copyWith(isSubmitting: false, error: e.toString()));
      return false;
    } on Exception catch (e) {
      emit(state.copyWith(isSubmitting: false, error: e.toString()));
      return false;
    }
  }

  /// Aleatória, não derivada de relógio: dois aparelhos podem enviar no mesmo
  /// milissegundo, e um relógio atrasado repetiria uma chave já usada — o que
  /// faria uma entrega nova ser confundida com o reenvio de outra.
  static String _novaChaveDeIdempotencia() {
    final random = Random.secure();
    final bytes = List<int>.generate(16, (_) => random.nextInt(256));
    return 'entrega-${base64Url.encode(bytes).replaceAll('=', '')}';
  }
}
