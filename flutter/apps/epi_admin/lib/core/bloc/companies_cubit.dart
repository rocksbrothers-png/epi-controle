import 'package:equatable/equatable.dart';
import 'package:epi_api/epi_api.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import '../api/api_client.dart';

// ── State ──────────────────────────────────────────────────────────────────

class CompaniesState extends Equatable {
  const CompaniesState({
    this.isLoading = false,
    this.error,
    this.companies = const [],
    this.query = '',
  });

  final bool isLoading;
  final String? error;
  final List<Company> companies;
  final String query;

  List<Company> get filtered {
    if (query.isEmpty) return companies;
    final q = query.toLowerCase();
    return companies
        .where((c) =>
            c.name.toLowerCase().contains(q) ||
            (c.legalName?.toLowerCase().contains(q) ?? false) ||
            (c.cnpj?.contains(q) ?? false))
        .toList();
  }

  CompaniesState _copyWith({
    bool? isLoading,
    String? error,
    List<Company>? companies,
    String? query,
    bool clearError = false,
  }) =>
      CompaniesState(
        isLoading: isLoading ?? this.isLoading,
        error: clearError ? null : (error ?? this.error),
        companies: companies ?? this.companies,
        query: query ?? this.query,
      );

  @override
  List<Object?> get props => [isLoading, error, companies, query];
}

// ── Cubit ──────────────────────────────────────────────────────────────────

class CompaniesCubit extends Cubit<CompaniesState> {
  CompaniesCubit() : super(const CompaniesState());

  Future<void> load() async {
    emit(state._copyWith(isLoading: true, clearError: true));
    try {
      final items = await ApiClient.companies.getCompanies();
      emit(state._copyWith(isLoading: false, companies: items));
    } catch (e) {
      // `catch` amplo de propósito: um Error de parsing (ex.: _CastError)
      // deixaria a tela em loading eterno se só Exception fosse tratada.
      emit(state._copyWith(isLoading: false, error: e.toString()));
    }
  }

  void search(String q) => emit(state._copyWith(query: q));

  /// Cria uma empresa e recarrega a lista em caso de sucesso. Retorna `null`
  /// quando a criação foi bem-sucedida, ou a mensagem de erro do backend para
  /// a UI exibir.
  Future<String?> create(Map<String, dynamic> data) async {
    try {
      await ApiClient.createCompany(data);
    } catch (e) {
      // `catch` amplo: um Error não capturado deixaria o diálogo travado no
      // spinner (o `_submitting` nunca é resetado).
      return e.toString();
    }
    // Falha ao recarregar a lista não é falha da criação — a empresa já foi
    // persistida; o diálogo fecha e a tela mostra o erro de load, se houver.
    await load();
    return null;
  }
}
