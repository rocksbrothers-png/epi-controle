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
    this.searchResults = const [],
    this.isSearching = false,
    this.searchQuery = '',
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

  // ── Fluxo de vinculação a esta Unidade (ADR-0002 §12, F6B da #226) ───────
  //
  // Vive em campos PRÓPRIOS, separado de [companies], por um motivo que não é
  // organização: `companies` traz só o que esta Unidade já vinculou, enquanto
  // a busca traz o tenant inteiro — inclusive empresas mascaradas, sem
  // contratos nem colaboradores. Misturar as duas listas faria a tela
  // principal exibir registros incompletos como se fossem gerenciáveis.

  /// Resultado de `GET /api/outsourced-companies/search`.
  ///
  /// Chega com os dois tipos misturados; quem separa é
  /// [OutsourcedCompany.isMaskedForLinking]. A tela **não** refiltra: o
  /// recorte e o mascaramento são do servidor.
  final List<OutsourcedCompany> searchResults;

  final bool isSearching;
  final String searchQuery;

  /// Empresas que ESTA Unidade já vinculou — bloco de cima da busca.
  List<OutsourcedCompany> get searchLinked =>
      searchResults.where((c) => !c.isMaskedForLinking).toList(growable: false);

  /// Empresas do tenant ainda **não** vinculadas a esta Unidade — bloco de
  /// baixo, o que resolve o problema de origem: a Unidade nova não enxerga a
  /// empresa pela listagem comum justamente por não ter vínculo, e sem este
  /// bloco a saída do operador seria cadastrá-la de novo.
  List<OutsourcedCompany> get searchAvailable =>
      searchResults.where((c) => c.isMaskedForLinking).toList(growable: false);

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
    List<OutsourcedCompany>? searchResults,
    bool? isSearching,
    String? searchQuery,
  }) =>
      OutsourcedCompaniesState(
        isLoading: isLoading ?? this.isLoading,
        error: clearError ? null : (error ?? this.error),
        companies: companies ?? this.companies,
        archivedCompanies: archivedCompanies ?? this.archivedCompanies,
        showArchived: showArchived ?? this.showArchived,
        query: query ?? this.query,
        searchResults: searchResults ?? this.searchResults,
        isSearching: isSearching ?? this.isSearching,
        searchQuery: searchQuery ?? this.searchQuery,
      );

  // Os campos da busca PRECISAM entrar aqui: `Equatable` compara por `props`,
  // e um campo de fora não conta como mudança de estado — o `BlocBuilder`
  // simplesmente não reconstruiria. O sintoma seria "vinculei e a tela não
  // atualizou", que pareceria bug de backend.
  @override
  List<Object?> get props => [
        isLoading, error, companies, archivedCompanies, showArchived, query,
        searchResults, isSearching, searchQuery,
      ];
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

  // ── Vínculo da empresa com esta Unidade (ADR-0002 §12, F6B da #226) ─────
  //
  // Resolve o caso que a listagem comum não alcança: a Unidade que ainda não
  // trabalha com a empresa não a enxerga justamente por não ter vínculo. Sem
  // a busca, a saída do operador seria cadastrar a empresa outra vez — e o
  // desenho existe para que o cadastro corporativo seja ÚNICO no tenant.

  /// Busca empresas do tenant pelo nome.
  ///
  /// Termo vazio limpa o resultado em vez de buscar tudo: uma busca vazia
  /// devolveria o tenant inteiro num diálogo feito para localizar uma empresa
  /// específica.
  Future<void> searchInTenant(String query) async {
    final term = query.trim();
    if (term.isEmpty) {
      emit(state.copyWith(searchResults: const [], searchQuery: '', isSearching: false));
      return;
    }
    emit(state.copyWith(isSearching: true, searchQuery: term, clearError: true));
    try {
      final results = await _outsourced.searchOutsourcedCompanies(
        actorUserId: ApiClient.actorUserId,
        query: term,
      );
      emit(state.copyWith(isSearching: false, searchResults: results, clearError: true));
    } on Exception catch (e) {
      emit(state.copyWith(isSearching: false, error: _errorMessage(e)));
    }
  }

  void clearTenantSearch() =>
      emit(state.copyWith(searchResults: const [], searchQuery: '', isSearching: false));

  /// "Vincular a esta Unidade" — cria APENAS o vínculo local.
  ///
  /// Não escreve em `outsourced_companies`: o cadastro corporativo continua
  /// intacto e único, e esta Unidade não herda contratos, colaboradores nem
  /// notas de nenhuma outra.
  Future<bool> linkCompanyToUnit(int id) => _companyLinkOperation(
        () => _outsourced.linkOutsourcedCompanyToUnit(id, actorUserId: ApiClient.actorUserId),
      );

  /// "Reativar nesta Unidade" — reaproveita o vínculo existente e o histórico.
  Future<bool> activateCompanyUnitLink(int id) => _companyLinkOperation(
        () => _outsourced.activateOutsourcedCompanyUnitLink(
          id,
          actorUserId: ApiClient.actorUserId,
        ),
      );

  /// "Arquivar nesta Unidade" — alcance de UMA Unidade.
  ///
  /// Não arquiva o cadastro corporativo (isso é [archiveCompany]) e não afeta
  /// as outras Unidades vinculadas.
  Future<bool> deactivateCompanyUnitLink(int id, {String reason = ''}) =>
      _companyLinkOperation(
        () => _outsourced.deactivateOutsourcedCompanyUnitLink(
          id,
          actorUserId: ApiClient.actorUserId,
          reason: reason,
        ),
      );

  /// Recarrega a lista principal E a busca depois de cada operação.
  ///
  /// As duas, porque a operação muda o que cada uma mostra: a empresa recém
  /// vinculada passa a aparecer na listagem da Unidade, e na busca deixa de
  /// ser "disponível" para virar "vinculada". Atualizar só uma deixaria a
  /// outra mentindo até o próximo refresh manual.
  ///
  /// O estado novo vem do backend — não é montado a partir da resposta da
  /// operação, que traria de volta a dedução local que a #226 eliminou.
  Future<bool> _companyLinkOperation(Future<void> Function() operation) async {
    emit(state.copyWith(isLoading: true, clearError: true));
    try {
      await operation();
      await _reload();
      if (state.searchQuery.isNotEmpty) {
        await searchInTenant(state.searchQuery);
      }
      return true;
    } on Exception catch (e) {
      emit(state.copyWith(isLoading: false, error: _errorMessage(e)));
      return false;
    }
  }

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
