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
    this.archivedUnits = const [],
    this.showArchived = false,
    this.query = '',
  });

  final bool isLoading;
  final String? error;
  final List<Map<String, dynamic>> units;

  /// Unidades arquivadas (soft delete): desativadas para novas operações,
  /// com histórico preservado. Podem ser desarquivadas, voltando a ativas.
  final List<Map<String, dynamic>> archivedUnits;

  /// Alterna a listagem entre unidades ativas e arquivadas.
  final bool showArchived;
  final String query;

  List<Map<String, dynamic>> get filtered => _applyQuery(units);

  List<Map<String, dynamic>> get filteredArchived => _applyQuery(archivedUnits);

  List<Map<String, dynamic>> _applyQuery(List<Map<String, dynamic>> source) {
    if (query.isEmpty) return source;
    final q = query.toLowerCase();
    return source.where((u) {
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
    List<Map<String, dynamic>>? archivedUnits,
    bool? showArchived,
    String? query,
    bool clearError = false,
  }) =>
      UnitsState(
        isLoading: isLoading ?? this.isLoading,
        error: clearError ? null : (error ?? this.error),
        units: units ?? this.units,
        archivedUnits: archivedUnits ?? this.archivedUnits,
        showArchived: showArchived ?? this.showArchived,
        query: query ?? this.query,
      );

  @override
  List<Object?> get props =>
      [isLoading, error, units, archivedUnits, showArchived, query];
}

// ── Cubit ──────────────────────────────────────────────────────────────────

class UnitsCubit extends Cubit<UnitsState> {
  UnitsCubit() : super(const UnitsState());

  Future<void> load() async {
    emit(state._copyWith(isLoading: true, clearError: true));
    try {
      final bootstrap = await ApiClient.auth.bootstrap();
      final archived = await _loadArchivedSafe();
      emit(state._copyWith(
        isLoading: false,
        units: bootstrap.units,
        archivedUnits: archived,
      ));
    } on Exception catch (e) {
      emit(state._copyWith(isLoading: false, error: e.toString()));
    }
  }

  void search(String query) => emit(state._copyWith(query: query));

  void toggleArchivedView() =>
      emit(state._copyWith(showArchived: !state.showArchived));

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

  /// Desarquiva a unidade: ela volta ao status ativo e pode receber novas
  /// operações. O histórico preservado permanece intacto.
  Future<void> restoreUnit(int id) async {
    emit(state._copyWith(isLoading: true, clearError: true));
    try {
      await ApiClient.units.restoreUnit(id, actorUserId: ApiClient.actorUserId);
      await _reloadUnits();
    } on Exception catch (e) {
      emit(state._copyWith(isLoading: false, error: _errorMessage(e)));
    }
  }

  Future<List<Map<String, dynamic>>> _loadArchivedSafe() async {
    // Backends anteriores à política de arquivamento não têm o endpoint;
    // nesse caso a listagem de arquivadas apenas fica vazia.
    try {
      return await ApiClient.units.getArchivedUnits(
        actorUserId: ApiClient.actorUserId,
      );
    } on Exception {
      return const [];
    }
  }

  Future<void> _reloadUnits() async {
    final bootstrap = await ApiClient.auth.bootstrap();
    final archived = await _loadArchivedSafe();
    emit(state._copyWith(
      isLoading: false,
      units: bootstrap.units,
      archivedUnits: archived,
    ));
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
