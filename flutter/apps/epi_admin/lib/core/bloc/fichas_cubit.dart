import 'package:equatable/equatable.dart';
import 'package:epi_api/epi_api.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import '../api/api_client.dart';

// ── State ──────────────────────────────────────────────────────────────────

class FichasState extends Equatable {
  const FichasState({
    this.isLoading = false,
    this.error,
    this.periods = const [],
    this.query = '',
  });

  final bool isLoading;
  final String? error;
  final List<FichaPeriod> periods;
  final String query;

  List<FichaPeriod> get filtered {
    if (query.isEmpty) return periods;
    final q = query.toLowerCase();
    return periods
        .where((p) =>
            p.employeeName.toLowerCase().contains(q) ||
            (p.employeeCode?.toLowerCase().contains(q) ?? false) ||
            p.unitName.toLowerCase().contains(q))
        .toList();
  }

  FichasState _copyWith({
    bool? isLoading,
    String? error,
    List<FichaPeriod>? periods,
    String? query,
    bool clearError = false,
  }) =>
      FichasState(
        isLoading: isLoading ?? this.isLoading,
        error: clearError ? null : (error ?? this.error),
        periods: periods ?? this.periods,
        query: query ?? this.query,
      );

  @override
  List<Object?> get props => [isLoading, error, periods, query];
}

// ── Cubit ──────────────────────────────────────────────────────────────────

class FichasCubit extends Cubit<FichasState> {
  FichasCubit() : super(const FichasState());

  Future<void> load() async {
    emit(state._copyWith(isLoading: true, clearError: true));
    try {
      final items = await ApiClient.fichas.getFichas();
      emit(state._copyWith(isLoading: false, periods: items));
    } on Exception catch (e) {
      emit(state._copyWith(isLoading: false, error: e.toString()));
    }
  }

  void search(String q) => emit(state._copyWith(query: q));
}
