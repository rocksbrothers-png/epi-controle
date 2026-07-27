import 'package:dio/dio.dart';
import 'package:epi_api/epi_api.dart';
import 'package:equatable/equatable.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import '../api/api_client.dart';

// ── State ──────────────────────────────────────────────────────────────────

/// Estado da tela de CNPJs (LegalEntity) da empresa — Multi-CNPJ / JV.
class LegalEntitiesState extends Equatable {
  const LegalEntitiesState({
    this.isLoading = false,
    this.error,
    this.entities = const [],
    this.showInactive = false,
    this.query = '',
  });

  final bool isLoading;
  final String? error;

  /// Todos os CNPJs visíveis ao ator — o backend já aplica o escopo por papel
  /// (Administrador Local só vê os autorizados; Usuário, só o seu).
  final List<LegalEntity> entities;

  /// Inativos ficam ocultos por padrão: a inativação preserva o histórico
  /// jurídico, mas o CNPJ não deve mais ser usado em novas operações.
  final bool showInactive;
  final String query;

  List<LegalEntity> get visible {
    final base = showInactive ? entities : entities.where((e) => e.active);
    if (query.isEmpty) return base.toList(growable: false);
    final q = query.toLowerCase();
    return base
        .where((e) =>
            e.cnpj.toLowerCase().contains(q) ||
            e.legalName.toLowerCase().contains(q) ||
            e.tradeName.toLowerCase().contains(q))
        .toList(growable: false);
  }

  int get activeCount => entities.where((e) => e.active).length;

  LegalEntitiesState copyWith({
    bool? isLoading,
    String? error,
    bool clearError = false,
    List<LegalEntity>? entities,
    bool? showInactive,
    String? query,
  }) =>
      LegalEntitiesState(
        isLoading: isLoading ?? this.isLoading,
        error: clearError ? null : (error ?? this.error),
        entities: entities ?? this.entities,
        showInactive: showInactive ?? this.showInactive,
        query: query ?? this.query,
      );

  @override
  List<Object?> get props => [isLoading, error, entities, showInactive, query];
}

// ── Cubit ──────────────────────────────────────────────────────────────────

class LegalEntitiesCubit extends Cubit<LegalEntitiesState> {
  LegalEntitiesCubit() : super(const LegalEntitiesState());

  Future<void> load() async {
    emit(state.copyWith(isLoading: true, clearError: true));
    await _reload();
  }

  Future<void> _reload() async {
    try {
      final entities = await ApiClient.legalEntities
          .getLegalEntities(actorUserId: ApiClient.actorUserId);
      emit(state.copyWith(isLoading: false, entities: entities, clearError: true));
    } on Exception catch (e) {
      emit(state.copyWith(isLoading: false, error: _errorMessage(e)));
    }
  }

  void search(String query) => emit(state.copyWith(query: query));

  void toggleInactiveView() =>
      emit(state.copyWith(showInactive: !state.showInactive));

  Future<void> createEntity(Map<String, dynamic> body) async {
    emit(state.copyWith(isLoading: true, clearError: true));
    try {
      await ApiClient.legalEntities.createLegalEntity({
        ...body,
        'actor_user_id': ApiClient.actorUserId,
      });
      await _reload();
    } on Exception catch (e) {
      emit(state.copyWith(isLoading: false, error: _errorMessage(e)));
    }
  }

  Future<void> updateEntity(int id, Map<String, dynamic> body) async {
    emit(state.copyWith(isLoading: true, clearError: true));
    try {
      await ApiClient.legalEntities.updateLegalEntity(id, {
        ...body,
        'actor_user_id': ApiClient.actorUserId,
      });
      await _reload();
    } on Exception catch (e) {
      emit(state.copyWith(isLoading: false, error: _errorMessage(e)));
    }
  }

  /// Inativa o CNPJ. Nunca é exclusão física — o histórico jurídico/fiscal é
  /// preservado. O backend recusa o último CNPJ ativo e CNPJ com colaboradores
  /// vinculados, devolvendo a mensagem que exibimos ao operador.
  Future<void> deactivateEntity(int id) async {
    emit(state.copyWith(isLoading: true, clearError: true));
    try {
      await ApiClient.legalEntities
          .deactivateLegalEntity(id, actorUserId: ApiClient.actorUserId);
      await _reload();
    } on Exception catch (e) {
      emit(state.copyWith(isLoading: false, error: _errorMessage(e)));
    }
  }

  /// Importação de planilha: as linhas já vêm convertidas em mapas pela tela.
  /// Devolve o resumo do backend (`created_ids`, `updated_ids`, `errors`).
  Future<Map<String, dynamic>> importRows(List<Map<String, dynamic>> rows) async {
    emit(state.copyWith(isLoading: true, clearError: true));
    try {
      final result = await ApiClient.legalEntities
          .importLegalEntities(rows, actorUserId: ApiClient.actorUserId);
      await _reload();
      return result;
    } on Exception catch (e) {
      emit(state.copyWith(isLoading: false, error: _errorMessage(e)));
      return {'errors': <dynamic>[]};
    }
  }

  String _errorMessage(Exception e) {
    if (e is DioException) {
      final data = e.response?.data;
      if (data is Map) {
        // O backend responde ora {'error': ...} (rotas legadas), ora
        // {'detail': ...} (envelope UBX).
        final message = data['error'] ?? data['detail'];
        if (message != null) return message.toString();
      }
    }
    return e.toString();
  }
}
