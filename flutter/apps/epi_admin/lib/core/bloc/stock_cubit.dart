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
  });

  final bool isLoading;
  final String? error;
  final List<Epi> epis;
  final String query;

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
  }) =>
      StockState(
        isLoading: isLoading ?? this.isLoading,
        error: error,
        epis: epis ?? this.epis,
        query: query ?? this.query,
      );

  @override
  List<Object?> get props => [isLoading, error, epis, query];
}

class StockCubit extends Cubit<StockState> {
  StockCubit() : super(const StockState());

  Future<void> load() async {
    emit(const StockState(isLoading: true));
    try {
      final bootstrap = await ApiClient.auth.bootstrap();
      final epis = bootstrap.epis.map(Epi.fromJson).toList();
      emit(StockState(epis: epis));
    } on Exception catch (e) {
      emit(StockState(error: e.toString()));
    }
  }

  void search(String query) {
    emit(state._copyWith(query: query));
  }

  /// Optimistic local move — positive delta = stock in, negative = stock out.
  void moveStock({required int epiId, required int delta}) {
    final updated = state.epis.map((e) {
      if (e.id != epiId) return e;
      final newQty = (e.stockQuantity + delta).clamp(0, 99999);
      return e.copyWith(stockQuantity: newQty);
    }).toList();
    emit(state._copyWith(epis: updated));
  }
}
