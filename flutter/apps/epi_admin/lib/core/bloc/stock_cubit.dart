import 'package:dio/dio.dart';
import 'package:equatable/equatable.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:epi_api/epi_api.dart';
import '../connectivity/connectivity_checker.dart';
import '../utils/epi_status_utils.dart';
import '../notifications/notification_service.dart';
import '../sync/offline_queue.dart';
import '../../features/stock/data/datasources/stock_remote_datasource.dart';
import '../../features/stock/data/repository_impl/stock_repository_impl.dart';
import '../../features/stock/domain/repositories/stock_repository.dart';

/// Filtros de conformidade do estoque, conforme NT 146/2015: o CA é relevante
/// na compra, e a validade do fabricante rege a entrega do EPI.
enum StockComplianceFilter { none, caExpired, manufacturerExpiring, manufacturerExpired }

/// Estado de cada lista carregada sob demanda (itens disponíveis, bloqueados).
///
/// `forbidden` é separado de `error` de propósito: o backend responde 403 para
/// perfil `admin`/`user` sem unidade operacional ativa, e isso não é falha —
/// é ausência de contexto, que pede uma mensagem diferente e não oferece
/// "tentar de novo", porque tentar de novo não resolve.
enum StockListStatus { idle, loading, ready, error, forbidden }

class StockState extends Equatable {
  const StockState({
    this.isLoading = false,
    this.error,
    this.epis = const [],
    this.query = '',
    this.compliance = StockComplianceFilter.none,
    this.companyId = 0,
    this.unitId = 0,
    this.actorUserId = 0,
    this.availableStatus = StockListStatus.idle,
    this.availableItems = const [],
    this.availableEpiId = 0,
    this.availableError,
    this.blockedStatus = StockListStatus.idle,
    this.blockedItems = const [],
    this.blockedStatusKeys = const [],
    this.blockedError,
  });

  final bool isLoading;
  final String? error;
  final List<Epi> epis;
  final String query;
  final StockComplianceFilter compliance;
  final int companyId;
  final int unitId;
  final int actorUserId;

  /// QRs disponíveis do EPI selecionado (`availableEpiId`). Vazio enquanto
  /// nenhum EPI foi escolhido — `idle`, não `ready`, para a UI não mostrar
  /// "nenhum item" antes de a consulta existir.
  final StockListStatus availableStatus;
  final List<StockItem> availableItems;
  final int availableEpiId;
  final String? availableError;

  /// Itens bloqueados no escopo do ator, e as chaves de status que o backend
  /// reconhece. Guardamos as CHAVES; o rótulo vem do ARB.
  final StockListStatus blockedStatus;
  final List<StockItem> blockedItems;
  final List<String> blockedStatusKeys;
  final String? blockedError;

  /// EPIs críticos NA UNIDADE, pela classificação do backend (`stock_status`).
  ///
  /// Esta tela é operacional: o número tem de ser o da Unidade. Até a fatia
  /// 1.1D-C2 contava por `is_company_stock_critical` — criticidade da empresa
  /// inteira exibida a quem opera uma Unidade só.
  ///
  /// EPI com alerta desligado é `disabled` e **não** entra na contagem, mesmo
  /// com `underlying_status == 'critical'`: o operador daquela Unidade decidiu
  /// não ser alertado sobre ele.
  int get criticalCount => epis.where(epiIsUnitCritical).length;

  /// EPIs cuja validade do fabricante já venceu — não podem ser entregues e
  /// devem ser retirados do estoque (NT 146/2015).
  int get manufacturerExpiredCount =>
      epis.where((e) => e.manufacturerValidityStatus == 'expired').length;

  /// EPIs com validade do fabricante próxima do vencimento — devem sair primeiro
  /// do estoque (PEPS — primeiro a expirar, primeiro a sair).
  int get manufacturerExpiringCount =>
      epis.where((e) => e.manufacturerValidityStatus == 'expiring').length;

  /// EPIs com CA vencido (relevante na compra de novos lotes).
  int get caExpiredCount =>
      epis.where((e) => e.caStatus == 'expired').length;

  bool _matchesCompliance(Epi e) => switch (compliance) {
        StockComplianceFilter.none => true,
        StockComplianceFilter.caExpired => e.caStatus == 'expired',
        StockComplianceFilter.manufacturerExpiring =>
          e.manufacturerValidityStatus == 'expiring',
        StockComplianceFilter.manufacturerExpired =>
          e.manufacturerValidityStatus == 'expired',
      };

  List<Epi> get filtered {
    // Só o filtro de conformidade fica no cliente: ele deriva de datas já
    // presentes no payload e não tem equivalente no servidor. A busca por nome
    // vai para `/api/stock/epis` — refazê-la aqui filtraria de novo o que o
    // backend já filtrou, e divergiria dele em acentuação e maiúsculas.
    final result = epis.where(_matchesCompliance);
    // Críticos primeiro, depois alfabético.
    final sorted = result.toList()
      ..sort((a, b) {
        final aCritico = epiIsUnitCritical(a);
        final bCritico = epiIsUnitCritical(b);
        if (aCritico != bCritico) return aCritico ? -1 : 1;
        return a.name.compareTo(b.name);
      });
    return sorted;
  }

  StockState _copyWith({
    bool? isLoading,
    String? error,
    List<Epi>? epis,
    String? query,
    StockComplianceFilter? compliance,
    int? companyId,
    int? unitId,
    int? actorUserId,
    StockListStatus? availableStatus,
    List<StockItem>? availableItems,
    int? availableEpiId,
    String? availableError,
    StockListStatus? blockedStatus,
    List<StockItem>? blockedItems,
    List<String>? blockedStatusKeys,
    String? blockedError,
  }) =>
      StockState(
        isLoading: isLoading ?? this.isLoading,
        error: error,
        epis: epis ?? this.epis,
        query: query ?? this.query,
        compliance: compliance ?? this.compliance,
        companyId: companyId ?? this.companyId,
        unitId: unitId ?? this.unitId,
        actorUserId: actorUserId ?? this.actorUserId,
        availableStatus: availableStatus ?? this.availableStatus,
        availableItems: availableItems ?? this.availableItems,
        availableEpiId: availableEpiId ?? this.availableEpiId,
        availableError: availableError,
        blockedStatus: blockedStatus ?? this.blockedStatus,
        blockedItems: blockedItems ?? this.blockedItems,
        blockedStatusKeys: blockedStatusKeys ?? this.blockedStatusKeys,
        blockedError: blockedError,
      );

  @override
  List<Object?> get props => [
        isLoading, error, epis, query, compliance, companyId, unitId, actorUserId,
        // Sem estes em props, trocar de aba ou recarregar uma lista não
        // reconstruiria a tela: dois estados diferentes compararia como iguais.
        availableStatus, availableItems, availableEpiId, availableError,
        blockedStatus, blockedItems, blockedStatusKeys, blockedError,
      ];
}

class StockCubit extends Cubit<StockState> {
  StockCubit({
    StockRepository? repository,
    ConnectivityChecker? connectivity,
    OfflineQueue? offlineQueue,
  })  : _repository = repository ??
            const StockRepositoryImpl(ApiStockRemoteDataSource()),
        _connectivity = connectivity ?? const RealConnectivityChecker(),
        _offlineQueue = offlineQueue ?? const SyncDatabaseQueue(),
        super(const StockState());

  final StockRepository _repository;
  final ConnectivityChecker _connectivity;
  final OfflineQueue _offlineQueue;

  /// Carrega o estoque a partir de `/api/stock/epis` — fonte ÚNICA.
  ///
  /// Antes vinha de `bootstrap.epis`, que trazia só o total da empresa,
  /// resolvia a visibilidade GLOBAL/JV no login e envelhecia durante a sessão.
  /// Agora saldo da unidade e saldo corporativo chegam em campos separados, a
  /// visibilidade é reavaliada a cada consulta, e o filtro por nome é do
  /// servidor.
  Future<void> load() async {
    emit(state._copyWith(isLoading: true, error: null));
    try {
      final epis = await _repository.fetchStockEpis(
        name: state.query.isEmpty ? null : state.query,
      );
      // Empresa e unidade saem do escopo que o SERVIDOR resolveu, não de um
      // retrato do login: `unitScopeId` é a unidade usada para calcular o
      // saldo, e é nela que a movimentação deve incidir.
      final comEscopo = epis.where((e) => e.unitScopeId != null);
      // O ator continua vindo da sessão (antes vinha junto do bootstrap). Sem
      // isto as consultas de itens e o movimento sairiam com `actor_user_id=0`.
      final actorUserId = await _repository.currentActorUserId();
      emit(state._copyWith(
        isLoading: false,
        epis: epis,
        companyId: comEscopo.isEmpty ? 0 : (comEscopo.first.companyId ?? 0),
        unitId: comEscopo.isEmpty ? 0 : (comEscopo.first.unitScopeId ?? 0),
        actorUserId: actorUserId,
      ));
      // Alerta de estoque crítico — DA UNIDADE, classificado pelo backend.
      // Notificar por criticidade corporativa avisava o operador sobre um
      // problema que podia não existir no estoque dele.
      final criticos = epis.where(epiIsUnitCritical).toList();
      if (criticos.isNotEmpty) {
        NotificationService().simulateNotification(AppNotification(
          title: 'Estoque Crítico',
          body: '${criticos.length} EPI(s) abaixo do estoque mínimo',
          data: const {},
        ));
      }
    } on Exception catch (e) {
      emit(state._copyWith(isLoading: false, error: e.toString()));
    }
  }

  /// 403 do backend = perfil sem unidade operacional ativa (`PermissionError`).
  /// Não é falha de rede nem bug: é contexto ausente, e a UI trata diferente —
  /// sem botão de "tentar de novo", que não resolveria nada.
  static bool _isForbidden(Object error) =>
      error is DioException && error.response?.statusCode == 403;

  /// Ator da sessão, resolvido sob demanda.
  ///
  /// As abas de itens disponíveis/bloqueados podem ser abertas antes de
  /// `load()` (deep-link, ou o operador tocando a aba primeiro). Depender de
  /// `load()` ter rodado mandaria `actor_user_id=0` e o backend recusaria — o
  /// mesmo defeito que a lista de colaboradores já teve.
  Future<int> _actor() async {
    if (state.actorUserId != 0) return state.actorUserId;
    final actorUserId = await _repository.currentActorUserId();
    if (actorUserId != 0) emit(state._copyWith(actorUserId: actorUserId));
    return actorUserId;
  }

  /// Carrega os QRs disponíveis do EPI. O backend devolve em ordem FEFO e
  /// aplica o escopo de empresa/unidade a partir do ator — por isso nenhum
  /// `companyId`/`unitId` sai daqui.
  Future<void> loadAvailableItems(int epiId) async {
    emit(state._copyWith(
      availableStatus: StockListStatus.loading,
      availableEpiId: epiId,
      availableItems: const [],
    ));
    try {
      final items = await _repository.fetchAvailableItems(
        actorUserId: await _actor(),
        epiId: epiId,
      );
      emit(state._copyWith(
        availableStatus: StockListStatus.ready,
        availableItems: items,
      ));
    } on Object catch (e) {
      emit(state._copyWith(
        availableStatus:
            _isForbidden(e) ? StockListStatus.forbidden : StockListStatus.error,
        availableError: e.toString(),
      ));
    }
  }

  Future<void> loadBlockedItems() async {
    emit(state._copyWith(blockedStatus: StockListStatus.loading));
    try {
      final result =
          await _repository.fetchBlockedItems(actorUserId: await _actor());
      emit(state._copyWith(
        blockedStatus: StockListStatus.ready,
        blockedItems: result.items,
        blockedStatusKeys: result.statusKeys,
      ));
    } on Object catch (e) {
      emit(state._copyWith(
        blockedStatus:
            _isForbidden(e) ? StockListStatus.forbidden : StockListStatus.error,
        blockedError: e.toString(),
      ));
    }
  }

  /// Busca por nome. Reconsulta o servidor: o filtro é dele, não do cliente.
  Future<void> search(String query) {
    emit(state._copyWith(query: query));
    return load();
  }

  void setCompliance(StockComplianceFilter value) {
    emit(state._copyWith(compliance: value));
  }

  /// Persists the movement to the backend and updates stock optimistically.
  /// Positive delta = stock in, negative = stock out.
  /// When offline, the operation is queued locally and replayed on reconnect.
  Future<void> moveStock({
    required int epiId,
    required int delta, // positive = in, negative = out
  }) async {
    final movementType = delta > 0 ? 'in' : 'out';
    final quantity = delta.abs();
    // Resolvido ANTES do enfileiramento: a operação offline é carimbada com
    // quem a originou, não com quem estiver logado quando a fila drenar.
    final actorUserId = await _actor();

    // O movimento incide sobre a unidade que o SERVIDOR resolveu para este EPI.
    final alvo = state.epis.where((e) => e.id == epiId).toList();
    final companyId = alvo.isEmpty ? state.companyId : (alvo.first.companyId ?? state.companyId);
    final unitId = alvo.isEmpty ? state.unitId : (alvo.first.unitScopeId ?? state.unitId);

    // Atualização otimista do saldo da UNIDADE — é ele que a tela mostra.
    final optimistic = state.epis.map((e) {
      if (e.id != epiId) return e;
      final atual = e.unitStockQuantity;
      if (atual == null) return e;
      return e.copyWith(unitStockQuantity: (atual + delta).clamp(0, 99999));
    }).toList();
    emit(state._copyWith(epis: optimistic));

    // Check connectivity before attempting the network call
    final isOnline = await _connectivity.isOnline;

    if (!isOnline) {
      // Queue for later sync; UI already updated optimistically
      await _offlineQueue.enqueue(
        opType: 'stock_movement',
        payload: {
          'actor_user_id': actorUserId,
          'company_id': companyId,
          'unit_id': unitId,
          'epi_id': epiId,
          'movement_type': movementType,
          'quantity': quantity,
        },
      );
      return;
    }

    // Online path: persist to backend, queue on network failure
    try {
      await _repository.recordMovement(
        actorUserId: actorUserId,
        companyId: companyId,
        unitId: unitId,
        epiId: epiId,
        movementType: movementType,
        quantity: quantity,
      );
    } on Exception {
      // Network failure while online: queue for later sync
      await _offlineQueue.enqueue(
        opType: 'stock_movement',
        payload: {
          'actor_user_id': actorUserId,
          'company_id': companyId,
          'unit_id': unitId,
          'epi_id': epiId,
          'movement_type': movementType,
          'quantity': quantity,
        },
      );
    }
  }
}
