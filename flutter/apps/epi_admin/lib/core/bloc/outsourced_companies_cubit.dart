import 'package:dio/dio.dart';
import 'package:epi_api/epi_api.dart';
import 'package:equatable/equatable.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import '../api/api_client.dart';

// ── State ──────────────────────────────────────────────────────────────────

/// Estado da tela de Terceirizados e Prestadores (ADR-0002).
class OutsourcedCompaniesState extends Equatable {
  const OutsourcedCompaniesState({
    this.isLoading = false,
    this.error,
    this.companies = const [],
    this.archivedCompanies = const [],
    this.showArchived = false,
    this.query = '',
  });

  final bool isLoading;
  final String? error;

  /// Escopado pelo backend à empresa (tenant) do ator — nunca cross-tenant.
  final List<OutsourcedCompany> companies;

  /// Empresas arquivadas (soft delete) — aba "Empresas Arquivadas"
  /// (ADR-0002 §10.4). Mapa cru: carrega motivo/data/retenção, que o
  /// model [OutsourcedCompany] não modela.
  final List<Map<String, dynamic>> archivedCompanies;

  /// Alterna a listagem entre empresas ativas e arquivadas.
  final bool showArchived;
  final String query;

  List<OutsourcedCompany> get visible {
    if (query.isEmpty) return companies;
    final q = query.toLowerCase();
    return companies
        .where((c) =>
            c.legalName.toLowerCase().contains(q) ||
            c.tradeName.toLowerCase().contains(q) ||
            c.cnpj.toLowerCase().contains(q))
        .toList(growable: false);
  }

  List<Map<String, dynamic>> get visibleArchived {
    if (query.isEmpty) return archivedCompanies;
    final q = query.toLowerCase();
    return archivedCompanies.where((c) {
      final legalName = (c['legal_name'] as String? ?? '').toLowerCase();
      final tradeName = (c['trade_name'] as String? ?? '').toLowerCase();
      return legalName.contains(q) || tradeName.contains(q);
    }).toList(growable: false);
  }

  OutsourcedCompaniesState copyWith({
    bool? isLoading,
    String? error,
    bool clearError = false,
    List<OutsourcedCompany>? companies,
    List<Map<String, dynamic>>? archivedCompanies,
    bool? showArchived,
    String? query,
  }) =>
      OutsourcedCompaniesState(
        isLoading: isLoading ?? this.isLoading,
        error: clearError ? null : (error ?? this.error),
        companies: companies ?? this.companies,
        archivedCompanies: archivedCompanies ?? this.archivedCompanies,
        showArchived: showArchived ?? this.showArchived,
        query: query ?? this.query,
      );

  @override
  List<Object?> get props =>
      [isLoading, error, companies, archivedCompanies, showArchived, query];
}

// ── Cubit ──────────────────────────────────────────────────────────────────

class OutsourcedCompaniesCubit extends Cubit<OutsourcedCompaniesState> {
  /// [api] existe para o teste — sem ele não haveria como provar a chamada
  /// certa sem bater no cliente HTTP estático.
  OutsourcedCompaniesCubit({OutsourcedCompaniesApi? api})
      : _api = api,
        super(const OutsourcedCompaniesState());

  final OutsourcedCompaniesApi? _api;

  OutsourcedCompaniesApi get _outsourced => _api ?? ApiClient.outsourcedCompanies;

  Future<void> load() async {
    emit(state.copyWith(isLoading: true, clearError: true));
    await _reload();
  }

  Future<void> _reload() async {
    try {
      final companies =
          await _outsourced.getOutsourcedCompanies(actorUserId: ApiClient.actorUserId);
      final archived = await _loadArchivedSafe();
      emit(state.copyWith(
        isLoading: false,
        companies: companies,
        archivedCompanies: archived,
        clearError: true,
      ));
    } on Exception catch (e) {
      emit(state.copyWith(isLoading: false, error: _errorMessage(e)));
    }
  }

  Future<List<Map<String, dynamic>>> _loadArchivedSafe() async {
    try {
      return await _outsourced.getArchivedOutsourcedCompanies(actorUserId: ApiClient.actorUserId);
    } on Exception {
      return const [];
    }
  }

  /// Alterna entre a listagem de empresas ativas e a de arquivadas.
  void toggleArchivedView() => emit(state.copyWith(showArchived: !state.showArchived));

  void search(String query) => emit(state.copyWith(query: query));

  /// Arquiva a empresa terceirizada/prestadora (soft delete): colaboradores
  /// já vinculados não são afetados, mas novos colaboradores e novas
  /// entregas passam a ser bloqueados enquanto ela estiver arquivada.
  Future<bool> archiveCompany(int id, {String reason = ''}) async {
    emit(state.copyWith(isLoading: true, clearError: true));
    try {
      await _outsourced.archiveOutsourcedCompany(id, actorUserId: ApiClient.actorUserId, reason: reason);
      await _reload();
      return true;
    } on Exception catch (e) {
      emit(state.copyWith(isLoading: false, error: _errorMessage(e)));
      return false;
    }
  }

  /// Desarquiva a empresa: volta ao status ativo.
  Future<bool> restoreCompany(int id) async {
    emit(state.copyWith(isLoading: true, clearError: true));
    try {
      await _outsourced.restoreOutsourcedCompany(id, actorUserId: ApiClient.actorUserId);
      await _reload();
      return true;
    } on Exception catch (e) {
      emit(state.copyWith(isLoading: false, error: _errorMessage(e)));
      return false;
    }
  }

  /// Cadastro Simplificado (CNPJ opcional) ou Padrão (CNPJ obrigatório) —
  /// mesma função de gravação no backend, a diferença é só quantos campos
  /// o formulário preenche.
  Future<bool> createCompany(Map<String, dynamic> body) async {
    emit(state.copyWith(isLoading: true, clearError: true));
    try {
      await _outsourced.createOutsourcedCompany(body, actorUserId: ApiClient.actorUserId);
      await _reload();
      return true;
    } on Exception catch (e) {
      emit(state.copyWith(isLoading: false, error: _errorMessage(e)));
      return false;
    }
  }

  Future<bool> updateCompany(int id, Map<String, dynamic> body) async {
    emit(state.copyWith(isLoading: true, clearError: true));
    try {
      await _outsourced.updateOutsourcedCompany(id, body, actorUserId: ApiClient.actorUserId);
      await _reload();
      return true;
    } on Exception catch (e) {
      emit(state.copyWith(isLoading: false, error: _errorMessage(e)));
      return false;
    }
  }

  /// Migração Simplificado → Padrão: mesma linha, mesmo id, sem duplicar
  /// nada. O backend recusa quando o CNPJ ainda não foi preenchido.
  Future<bool> promoteCompany(int id) async {
    emit(state.copyWith(isLoading: true, clearError: true));
    try {
      await _outsourced.promoteOutsourcedCompany(id, actorUserId: ApiClient.actorUserId);
      await _reload();
      return true;
    } on Exception catch (e) {
      emit(state.copyWith(isLoading: false, error: _errorMessage(e)));
      return false;
    }
  }

  String _errorMessage(Exception e) {
    if (e is DioException) {
      final data = e.response?.data;
      if (data is Map) {
        final message = data['error'] ?? data['detail'];
        if (message != null) return message.toString();
      }
    }
    return e.toString();
  }
}
