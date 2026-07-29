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
    this.query = '',
  });

  final bool isLoading;
  final String? error;

  /// Escopado pelo backend à empresa (tenant) do ator — nunca cross-tenant.
  final List<OutsourcedCompany> companies;
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

  OutsourcedCompaniesState copyWith({
    bool? isLoading,
    String? error,
    bool clearError = false,
    List<OutsourcedCompany>? companies,
    String? query,
  }) =>
      OutsourcedCompaniesState(
        isLoading: isLoading ?? this.isLoading,
        error: clearError ? null : (error ?? this.error),
        companies: companies ?? this.companies,
        query: query ?? this.query,
      );

  @override
  List<Object?> get props => [isLoading, error, companies, query];
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
      emit(state.copyWith(isLoading: false, companies: companies, clearError: true));
    } on Exception catch (e) {
      emit(state.copyWith(isLoading: false, error: _errorMessage(e)));
    }
  }

  void search(String query) => emit(state.copyWith(query: query));

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
