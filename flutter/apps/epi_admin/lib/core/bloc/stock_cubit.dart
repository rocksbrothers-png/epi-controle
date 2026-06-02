import 'package:equatable/equatable.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:epi_api/epi_api.dart';
import '../api/api_client.dart';

class StockState extends Equatable {
  const StockState({
    this.isLoading = false,
    this.error,
    this.epis = const [],
    this.query = '',
    this.companyId = 0,
    this.unitId = 0,
    this.actorUserId = 0,
  });

  final bool isLoading;
  final String? error;
  final List<Epi> epis;
  final String query;
  final int companyId;
  final int unitId;
  final int actorUserId;

  int get criticalCount => epis.where((e) => e.isCriticalStock).length;

  List<Epi> get filtered {
    var result = epis;
    if (query.isNotEmpty) {
      final q = query.toLowerCase();
      result =
          result.where((e) => e.name.toLowerCase().contains(q)).toList();
    }
    // Critical EPIs first, then alphabetical
    result = [...result]..sort((a, b) {
        if (a.isCriticalStock != b.isCriticalStock) {
          return a.isCriticalStock ? -1 : 1;
        }
        return a.name.compareTo(b.name);
      });
    return result;
  }

  StockState _copyWith({
    bool? isLoading,
    String? error,
    List<Epi>? epis,
    String? query,
    int? companyId,
    int? unitId,
    int? actorUserId,
  }) =>
      StockState(
        isLoading: isLoading ?? this.isLoading,
        error: error,
        epis: epis ?? this.epis,
        query: query ?? this.query,
        companyId: companyId ?? this.companyId,
        unitId: unitId ?? this.unitId,
        actorUserId: actorUserId ?? this.actorUserId,
      );

  @override
  List<Object?> get props => [isLoading, error, epis, query, companyId, unitId, actorUserId];
}

class StockCubit extends Cubit<StockState> {
  StockCubit() : super(const StockState());

  Future<void> load() async {
    emit(const StockState(isLoading: true));
    try {
      final bootstrap = await ApiClient.auth.bootstrap();
      final epis = bootstrap.epis.map(Epi.fromJson).toList();
      final companyId = bootstrap.units.isNotEmpty
          ? (bootstrap.units.first['company_id'] as int? ?? 0)
          : 0;
      final unitId = bootstrap.units.isNotEmpty
          ? (bootstrap.units.first['id'] as int? ?? 0)
          : 0;
      final actorUserId = bootstrap.users.isNotEmpty
          ? (bootstrap.users.first['id'] as int? ?? 0)
          : 0;
      emit(StockState(epis: epis, companyId: companyId, unitId: unitId, actorUserId: actorUserId));
    } on Exception catch (e) {
      emit(StockState(error: e.toString()));
    }
  }

  void search(String query) {
    emit(state._copyWith(query: query));
  }

  /// Persists the movement to the backend and updates stock optimistically.
  /// Positive delta = stock in, negative = stock out.
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

    // Persist to backend
    try {
      await ApiClient.stock.recordMovement(
        actorUserId: state.actorUserId,
        companyId: state.companyId,
        unitId: state.unitId,
        epiId: epiId,
        movementType: movementType,
        quantity: quantity,
      );
    } on Exception {
      // On failure: reload from server to restore real state
      await load();
    }
  }
}
