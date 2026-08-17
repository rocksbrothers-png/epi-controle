import 'package:dio/dio.dart';
import 'package:equatable/equatable.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:epi_api/epi_api.dart';
import '../api/api_client.dart';

class EpisState extends Equatable {
  const EpisState({
    this.isLoading = false,
    this.error,
    this.epis = const [],
    this.archivedEpis = const [],
    this.showArchived = false,
    this.query = '',
    this.filterCritical = false,
  });

  final bool isLoading;
  final String? error;
  final List<Epi> epis;

  /// EPIs arquivados (soft delete): desativados para novas operações, com
  /// histórico preservado. Podem ser desarquivados, voltando a ativos.
  final List<Map<String, dynamic>> archivedEpis;

  /// Alterna a listagem entre EPIs ativos e arquivados.
  final bool showArchived;
  final String query;
  final bool filterCritical;

  List<Map<String, dynamic>> get filteredArchived {
    if (query.isEmpty) return archivedEpis;
    final q = query.toLowerCase();
    return archivedEpis.where((e) {
      final name = (e['name'] as String? ?? '').toLowerCase();
      final ca = (e['ca'] as String? ?? '').toLowerCase();
      return name.contains(q) || ca.contains(q);
    }).toList();
  }

  List<Epi> get filtered {
    var result = epis;
    if (filterCritical) {
      result = result.where((e) => e.isCriticalStock).toList();
    }
    if (query.isNotEmpty) {
      final q = query.toLowerCase();
      result = result.where((e) {
        return e.name.toLowerCase().contains(q) ||
            (e.caNumber?.toLowerCase().contains(q) ?? false) ||
            (e.code?.toLowerCase().contains(q) ?? false);
      }).toList();
    }
    return result;
  }

  EpisState _copyWith({
    bool? isLoading,
    String? error,
    List<Epi>? epis,
    List<Map<String, dynamic>>? archivedEpis,
    bool? showArchived,
    String? query,
    bool? filterCritical,
  }) =>
      EpisState(
        isLoading: isLoading ?? this.isLoading,
        error: error,
        epis: epis ?? this.epis,
        archivedEpis: archivedEpis ?? this.archivedEpis,
        showArchived: showArchived ?? this.showArchived,
        query: query ?? this.query,
        filterCritical: filterCritical ?? this.filterCritical,
      );

  @override
  List<Object?> get props =>
      [isLoading, error, epis, archivedEpis, showArchived, query, filterCritical];
}

class EpisCubit extends Cubit<EpisState> {
  EpisCubit() : super(const EpisState());

  Future<void> load() async {
    emit(state._copyWith(isLoading: true));
    try {
      final bootstrap = await ApiClient.auth.bootstrap();
      final epis = bootstrap.epis.map(Epi.fromJson).toList();
      final archived = await _loadArchivedSafe();
      emit(state._copyWith(isLoading: false, epis: epis, archivedEpis: archived));
    } on Exception catch (e) {
      emit(state._copyWith(isLoading: false, error: e.toString()));
    }
  }

  /// Alterna entre a listagem de EPIs ativos e a de arquivados.
  void toggleArchivedView() =>
      emit(state._copyWith(showArchived: !state.showArchived));

  void search(String query) {
    emit(state._copyWith(query: query));
  }

  void toggleCriticalFilter() {
    emit(state._copyWith(filterCritical: !state.filterCritical));
  }

  Future<void> createEpi(Map<String, dynamic> body) async {
    emit(state._copyWith(isLoading: true));
    try {
      await ApiClient.epis.createEpi({
        ...body,
        'actor_user_id': ApiClient.actorUserId,
      });
      await _reloadEpis();
    } on Exception catch (e) {
      emit(state._copyWith(isLoading: false, error: _errorMessage(e)));
    }
  }

  Future<void> updateEpi(int id, Map<String, dynamic> body) async {
    emit(state._copyWith(isLoading: true));
    try {
      await ApiClient.epis.updateEpi(id, {
        ...body,
        'actor_user_id': ApiClient.actorUserId,
      });
      await _reloadEpis();
    } on Exception catch (e) {
      emit(state._copyWith(isLoading: false, error: _errorMessage(e)));
    }
  }

  /// Estado de vínculos vivos do EPI (item 1). A REGRA é do backend
  /// (`has_open_links`/`blockable`); a UI só decide entre arquivar direto ou
  /// oferecer "bloquear saldo e arquivar". Retorna `{}` em backends antigos
  /// sem o endpoint, deixando o fluxo seguir como arquivamento simples.
  Future<Map<String, dynamic>> loadArchivalState(int id) async {
    try {
      return await ApiClient.epis.getEpiArchivalState(
        id,
        actorUserId: ApiClient.actorUserId,
      );
    } on Exception {
      return const {};
    }
  }

  /// Arquiva o EPI (soft delete): o histórico permanece preservado pelo
  /// período mínimo de retenção configurado (>= 5 anos).
  ///
  /// Quando o EPI tem saldo/vínculos vivos, o backend recusa o arquivamento
  /// direto (409). Passe [blockAndArchive] = true (com [reason]) para autorizar
  /// o bloqueio do saldo disponível — movido para Estoque Bloqueado, rastreável
  /// — e então arquivar. A decisão de bloquear é sempre executada no backend.
  Future<void> archiveEpi(
    int id, {
    String reason = '',
    bool blockAndArchive = false,
  }) async {
    emit(state._copyWith(isLoading: true));
    try {
      await ApiClient.epis.archiveEpi(
        id,
        actorUserId: ApiClient.actorUserId,
        reason: reason,
        blockAndArchive: blockAndArchive,
      );
      await _reloadEpis();
    } on Exception catch (e) {
      emit(state._copyWith(isLoading: false, error: _errorMessage(e)));
    }
  }

  /// Desarquiva o EPI: volta ao status ativo, com histórico intacto.
  Future<void> restoreEpi(int id) async {
    emit(state._copyWith(isLoading: true));
    try {
      await ApiClient.epis.restoreEpi(id, actorUserId: ApiClient.actorUserId);
      await _reloadEpis();
    } on Exception catch (e) {
      emit(state._copyWith(isLoading: false, error: _errorMessage(e)));
    }
  }

  Future<List<Map<String, dynamic>>> _loadArchivedSafe() async {
    // Backends anteriores à política de arquivamento não têm o endpoint.
    try {
      return await ApiClient.epis.getArchivedEpis(
        actorUserId: ApiClient.actorUserId,
      );
    } on Exception {
      return const [];
    }
  }

  Future<void> _reloadEpis() async {
    final bootstrap = await ApiClient.auth.bootstrap();
    final epis = bootstrap.epis.map(Epi.fromJson).toList();
    final archived = await _loadArchivedSafe();
    emit(state._copyWith(isLoading: false, epis: epis, archivedEpis: archived));
  }

  String _errorMessage(Exception e) {
    if (e is DioException) {
      final data = e.response?.data;
      if (data is Map && data['error'] is Map && data['error']['message'] != null) {
        return data['error']['message'].toString();
      }
      if (data is Map && data['error'] != null) {
        return data['error'].toString();
      }
    }
    return e.toString();
  }
}
