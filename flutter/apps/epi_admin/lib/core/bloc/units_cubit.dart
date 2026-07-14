import 'package:dio/dio.dart';
import 'package:equatable/equatable.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import '../api/api_client.dart';

// ── State ──────────────────────────────────────────────────────────────────

class UnitsState extends Equatable {
  const UnitsState({
    this.isLoading = false,
    this.error,
    this.units = const [],
    this.query = '',
  });

  final bool isLoading;
  final String? error;
  final List<Map<String, dynamic>> units;
  final String query;

  List<Map<String, dynamic>> get filtered {
    if (query.isEmpty) return units;
    final q = query.toLowerCase();
    return units.where((u) {
      final name = (u['name'] as String? ?? '').toLowerCase();
      final companyName = (u['company_name'] as String? ?? '').toLowerCase();
      final type = (u['type'] as String? ?? '').toLowerCase();
      return name.contains(q) || companyName.contains(q) || type.contains(q);
    }).toList();
  }

  UnitsState _copyWith({
    bool? isLoading,
    String? error,
    List<Map<String, dynamic>>? units,
    String? query,
    bool clearError = false,
  }) =>
      UnitsState(
        isLoading: isLoading ?? this.isLoading,
        error: clearError ? null : (error ?? this.error),
        units: units ?? this.units,
        query: query ?? this.query,
      );

  @override
  List<Object?> get props => [isLoading, error, units, query];
}

// ── Cubit ──────────────────────────────────────────────────────────────────

class UnitsCubit extends Cubit<UnitsState> {
  UnitsCubit() : super(const UnitsState());

  Future<void> load() async {
    emit(state._copyWith(isLoading: true, clearError: true));
    try {
      final bootstrap = await ApiClient.auth.bootstrap();
      emit(state._copyWith(isLoading: false, units: bootstrap.units));
    } on Exception catch (e) {
      emit(state._copyWith(isLoading: false, error: e.toString()));
    }
  }

  void search(String query) => emit(state._copyWith(query: query));

  Future<void> createUnit(Map<String, dynamic> body) async {
    emit(state._copyWith(isLoading: true, clearError: true));
    try {
      await ApiClient.units.createUnit({
        ...body,
        'actor_user_id': ApiClient.actorUserId,
      });
      await _reloadUnits();
    } on Exception catch (e) {
      emit(state._copyWith(isLoading: false, error: _errorMessage(e)));
    }
  }

  Future<void> updateUnit(int id, Map<String, dynamic> body) async {
    emit(state._copyWith(isLoading: true, clearError: true));
    try {
      await ApiClient.units.updateUnit(id, {
        ...body,
        'actor_user_id': ApiClient.actorUserId,
      });
      await _reloadUnits();
    } on Exception catch (e) {
      emit(state._copyWith(isLoading: false, error: _errorMessage(e)));
    }
  }

  /// Arquiva a unidade (soft delete): o histórico permanece preservado pelo
  /// período mínimo de retenção configurado (>= 5 anos).
  Future<void> archiveUnit(int id, {String reason = ''}) async {
    emit(state._copyWith(isLoading: true, clearError: true));
    try {
      await ApiClient.units.archiveUnit(
        id,
        actorUserId: ApiClient.actorUserId,
        reason: reason,
      );
      await _reloadUnits();
    } on Exception catch (e) {
      emit(state._copyWith(isLoading: false, error: _errorMessage(e)));
    }
  }

  Future<void> _reloadUnits() async {
    final bootstrap = await ApiClient.auth.bootstrap();
    emit(state._copyWith(isLoading: false, units: bootstrap.units));
  }

  String _errorMessage(Exception e) {
    if (e is DioException) {
      final data = e.response?.data;
      if (data is Map && data['detail'] != null) {
        return data['detail'].toString();
      }
    }
    return e.toString();
  }
}
