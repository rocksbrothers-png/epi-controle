import 'package:equatable/equatable.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:epi_api/epi_api.dart';
import '../connectivity/connectivity_checker.dart';
import '../notifications/notification_service.dart';
import '../sync/offline_queue.dart';
import '../../features/stock/data/datasources/stock_remote_datasource.dart';
import '../../features/stock/data/repository_impl/stock_repository_impl.dart';
import '../../features/stock/domain/repositories/stock_repository.dart';

/// Filtros de conformidade do estoque, conforme NT 146/2015: o CA é relevante
/// na compra, e a validade do fabricante rege a entrega do EPI.
enum StockComplianceFilter { none, caExpired, manufacturerExpiring, manufacturerExpired }

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
  });

  final bool isLoading;
  final String? error;
  final List<Epi> epis;
  final String query;
  final StockComplianceFilter compliance;
  final int companyId;
  final int unitId;
  final int actorUserId;

  int get criticalCount => epis.where((e) => e.isCriticalStock).length;

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
    var result = epis.where(_matchesCompliance);
    if (query.isNotEmpty) {
      final q = query.toLowerCase();
      result = result.where((e) => e.name.toLowerCase().contains(q));
    }
    // Critical EPIs first, then alphabetical
    final sorted = result.toList()
      ..sort((a, b) {
        if (a.isCriticalStock != b.isCriticalStock) {
          return a.isCriticalStock ? -1 : 1;
        }
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
      );

  @override
  List<Object?> get props =>
      [isLoading, error, epis, query, compliance, companyId, unitId, actorUserId];
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

  Future<void> load() async {
    emit(const StockState(isLoading: true));
    try {
      final snapshot = await _repository.fetchStock();
      final epis = snapshot.epis;
      emit(StockState(
        epis: epis,
        companyId: snapshot.companyId,
        unitId: snapshot.unitId,
        actorUserId: snapshot.actorUserId,
      ));
      // Emit local notification if any EPI is below minimum stock
      final critical = epis.where((e) => e.isCriticalStock).toList();
      if (critical.isNotEmpty) {
        NotificationService().simulateNotification(AppNotification(
          title: 'Estoque Crítico',
          body: '${critical.length} EPI(s) abaixo do estoque mínimo',
          data: const {},
        ));
      }
    } on Exception catch (e) {
      emit(StockState(error: e.toString()));
    }
  }

  void search(String query) {
    emit(state._copyWith(query: query));
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

    // Optimistic UI update immediately
    final optimistic = state.epis.map((e) {
      if (e.id != epiId) return e;
      final newQty = (e.stockQuantity + delta).clamp(0, 99999);
      return e.copyWith(stockQuantity: newQty);
    }).toList();
    emit(state._copyWith(epis: optimistic));

    // Check connectivity before attempting the network call
    final isOnline = await _connectivity.isOnline;

    if (!isOnline) {
      // Queue for later sync; UI already updated optimistically
      await _offlineQueue.enqueue(
        opType: 'stock_movement',
        payload: {
          'actor_user_id': state.actorUserId,
          'company_id': state.companyId,
          'unit_id': state.unitId,
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
        actorUserId: state.actorUserId,
        companyId: state.companyId,
        unitId: state.unitId,
        epiId: epiId,
        movementType: movementType,
        quantity: quantity,
      );
    } on Exception {
      // Network failure while online: queue for later sync
      await _offlineQueue.enqueue(
        opType: 'stock_movement',
        payload: {
          'actor_user_id': state.actorUserId,
          'company_id': state.companyId,
          'unit_id': state.unitId,
          'epi_id': epiId,
          'movement_type': movementType,
          'quantity': quantity,
        },
      );
    }
  }
}
