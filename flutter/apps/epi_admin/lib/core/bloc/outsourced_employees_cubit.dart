import 'package:dio/dio.dart';
import 'package:epi_api/epi_api.dart';
import 'package:equatable/equatable.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import '../api/api_client.dart';

// ── State ──────────────────────────────────────────────────────────────────

/// Estado da aba "Cadastro de Colaboradores" — Cadastro Simplificado de
/// terceirizados/prestadores dentro de Terceirizados e Prestadores
/// (ADR-0002 §10.2). Escreve na mesma tabela `employees`; nunca CLT.
class OutsourcedEmployeesState extends Equatable {
  const OutsourcedEmployeesState({
    this.isLoading = false,
    this.error,
    this.employees = const [],
    this.archivedEmployees = const [],
    this.showArchived = false,
    this.query = '',
  });

  final bool isLoading;
  final String? error;

  /// Colaboradores de mão de obra **contratada** ativos, vindos de
  /// `GET /api/employees` — já escopados por tenant/Unidade pelo backend.
  ///
  /// A rota (e não o bootstrap) é a fonte porque só ela carrega
  /// `local_unit_link_status`: o bootstrap chama `fetch_employees` sem
  /// contexto de Unidade e devolve o estado do vínculo vazio para todos.
  ///
  /// O filtro usa [isContractedVinculo], não `!= 'CLT'`. Os dois davam no
  /// mesmo enquanto CLT era o único vínculo próprio; com Menor Aprendiz,
  /// Praticante e Estagiário deixaram de dar, e essas três pessoas passavam a
  /// aparecer nesta aba com ações que o backend rejeita.
  final List<Employee> employees;

  /// Arquivados: `GET /api/employees/archived?outsourced_only=1` (mesma
  /// rota do arquivamento geral de colaboradores, só filtrando).
  final List<Map<String, dynamic>> archivedEmployees;

  final bool showArchived;
  final String query;

  List<Employee> get filtered {
    if (query.isEmpty) return employees;
    final q = query.toLowerCase();
    return employees
        .where((e) =>
            e.name.toLowerCase().contains(q) ||
            (e.code?.toLowerCase().contains(q) ?? false) ||
            (e.role?.toLowerCase().contains(q) ?? false) ||
            (e.sourceCompany?.toLowerCase().contains(q) ?? false))
        .toList(growable: false);
  }

  List<Map<String, dynamic>> get filteredArchived {
    if (query.isEmpty) return archivedEmployees;
    final q = query.toLowerCase();
    return archivedEmployees.where((e) {
      final name = (e['name'] as String? ?? '').toLowerCase();
      final code = (e['employee_id_code'] as String? ?? '').toLowerCase();
      return name.contains(q) || code.contains(q);
    }).toList(growable: false);
  }

  OutsourcedEmployeesState copyWith({
    bool? isLoading,
    String? error,
    bool clearError = false,
    List<Employee>? employees,
    List<Map<String, dynamic>>? archivedEmployees,
    bool? showArchived,
    String? query,
  }) =>
      OutsourcedEmployeesState(
        isLoading: isLoading ?? this.isLoading,
        error: clearError ? null : (error ?? this.error),
        employees: employees ?? this.employees,
        archivedEmployees: archivedEmployees ?? this.archivedEmployees,
        showArchived: showArchived ?? this.showArchived,
        query: query ?? this.query,
      );

  @override
  List<Object?> get props =>
      [isLoading, error, employees, archivedEmployees, showArchived, query];
}

// ── Cubit ──────────────────────────────────────────────────────────────────

class OutsourcedEmployeesCubit extends Cubit<OutsourcedEmployeesState> {
  /// [employeesApi] existe para o teste.
  ///
  /// O `AuthApi` saiu junto com o consumo do bootstrap: a aba agora lê de
  /// `GET /api/employees`, que é a única rota que devolve o estado do vínculo
  /// local. Manter o parâmetro deixaria uma porta aberta para alguém voltar a
  /// alimentar esta tela pelo bootstrap sem perceber o que se perde.
  OutsourcedEmployeesCubit({EmployeesApi? employeesApi})
      : _employeesApi = employeesApi,
        super(const OutsourcedEmployeesState());

  final EmployeesApi? _employeesApi;

  EmployeesApi get _employees => _employeesApi ?? ApiClient.employees;

  Future<void> load() async {
    emit(state.copyWith(isLoading: true, clearError: true));
    await _reload();
  }

  Future<void> _reload() async {
    try {
      // `GET /api/employees`, NÃO o bootstrap: só esta rota resolve contexto
      // de Unidade e devolve `local_unit_link_status`. Lendo do bootstrap a
      // tela não falharia — apenas nunca ofereceria as ações de vínculo, em
      // silêncio, o que é bem pior de descobrir.
      final rows = await _employees.getEmployees(actorUserId: ApiClient.actorUserId);
      final employees = rows
          .map(Employee.fromJson)
          .where((e) => isContractedVinculo(e.employmentType))
          .toList(growable: false);
      final archived = await _loadArchivedSafe();
      emit(state.copyWith(
        isLoading: false,
        employees: employees,
        archivedEmployees: archived,
        clearError: true,
      ));
    } on Exception catch (e) {
      emit(state.copyWith(isLoading: false, error: _errorMessage(e)));
    }
  }

  Future<List<Map<String, dynamic>>> _loadArchivedSafe() async {
    try {
      return await _employees.getArchivedEmployees(
        actorUserId: ApiClient.actorUserId,
        outsourcedOnly: true,
      );
    } on Exception {
      return const [];
    }
  }

  void toggleArchivedView() => emit(state.copyWith(showArchived: !state.showArchived));

  void search(String query) => emit(state.copyWith(query: query));

  Future<bool> createEmployee(Map<String, dynamic> body) async {
    emit(state.copyWith(isLoading: true, clearError: true));
    try {
      await _employees.createEmployeeOutsourcedSimplified({
        ...body,
        'actor_user_id': ApiClient.actorUserId,
      });
      await _reload();
      return true;
    } on Exception catch (e) {
      emit(state.copyWith(isLoading: false, error: _errorMessage(e)));
      return false;
    }
  }

  Future<bool> updateEmployee(int id, Map<String, dynamic> body) async {
    emit(state.copyWith(isLoading: true, clearError: true));
    try {
      await _employees.updateEmployeeOutsourcedSimplified(id, {
        ...body,
        'actor_user_id': ApiClient.actorUserId,
      });
      await _reload();
      return true;
    } on Exception catch (e) {
      emit(state.copyWith(isLoading: false, error: _errorMessage(e)));
      return false;
    }
  }

  // ── Vínculo local por Unidade (ADR-0002 §13) ────────────────────────────
  //
  // As três operações são independentes do arquivamento GLOBAL logo abaixo, e
  // a diferença é o ponto todo da funcionalidade: arquivar o vínculo tira a
  // pessoa de UMA Unidade; arquivar o colaborador tira do tenant inteiro. A
  // tela usa palavras diferentes para as duas, e o cubit também.
  //
  // Nenhuma delas manda `unit_id`: para perfis escopados o backend usa a
  // Unidade operacional do ator, e para os demais a rota decide. Quem monta o
  // request não escolhe o próprio escopo.

  /// "Vincular à minha unidade" — `POST /api/employees/{id}/link`.
  Future<bool> linkToUnit(int id) => _linkOperation(
        () => _employees.linkEmployeeToUnit(id, actorUserId: ApiClient.actorUserId),
      );

  /// "Reativar nesta Unidade" — vínculo arquivado volta a ativo.
  Future<bool> activateUnitLink(int id) => _linkOperation(
        () => _employees.activateEmployeeUnitLink(id, actorUserId: ApiClient.actorUserId),
      );

  /// "Arquivar nesta Unidade" — o vínculo é arquivado, nunca apagado.
  ///
  /// [reason] vai para a auditoria junto com o ator. A linha permanece e
  /// continua sendo o que bloqueia a exclusão definitiva enquanto houver
  /// vínculo ativo em alguma Unidade.
  Future<bool> deactivateUnitLink(int id, {String reason = ''}) => _linkOperation(
        () => _employees.deactivateEmployeeUnitLink(
          id,
          actorUserId: ApiClient.actorUserId,
          reason: reason,
        ),
      );

  /// Vínculos de Unidade do colaborador — leitura sob demanda.
  ///
  /// Não entra no `state`: é consulta pontual de uma tela de detalhe, e
  /// guardá-la no estado da lista criaria uma segunda cópia do vínculo para
  /// manter em dia junto com `local_unit_link_status`. Duas cópias do mesmo
  /// fato divergem no primeiro arquivamento que uma delas não observar.
  ///
  /// A lista devolvida já vem recortada pelo servidor. **Não filtre aqui.**
  Future<List<Map<String, dynamic>>> loadUnitLinks(int id) =>
      _employees.getEmployeeUnitLinks(id, actorUserId: ApiClient.actorUserId);

  /// Recarrega a lista depois de cada operação de vínculo.
  ///
  /// O recarregamento é obrigatório, não uma cortesia: o novo
  /// `local_unit_link_status` é decidido pelo backend. Atualizar o item em
  /// memória a partir da resposta seria reconstruir o estado no cliente —
  /// exatamente o que a separação C1/C2 existe para impedir.
  Future<bool> _linkOperation(Future<void> Function() operation) async {
    emit(state.copyWith(isLoading: true, clearError: true));
    try {
      await operation();
      await _reload();
      return true;
    } on Exception catch (e) {
      emit(state.copyWith(isLoading: false, error: _errorMessage(e)));
      return false;
    }
  }

  /// Arquiva o colaborador (soft delete) — mesma rota/regra dos colaboradores
  /// CLT: histórico preservado pelo período mínimo de retenção configurado.
  ///
  /// Não confundir com [deactivateUnitLink]: esta remove do tenant, aquela de
  /// uma Unidade.
  Future<bool> archiveEmployee(int id, {String reason = ''}) async {
    emit(state.copyWith(isLoading: true, clearError: true));
    try {
      await _employees.archiveEmployee(id, actorUserId: ApiClient.actorUserId, reason: reason);
      await _reload();
      return true;
    } on Exception catch (e) {
      emit(state.copyWith(isLoading: false, error: _errorMessage(e)));
      return false;
    }
  }

  Future<bool> restoreEmployee(int id) async {
    emit(state.copyWith(isLoading: true, clearError: true));
    try {
      await _employees.restoreEmployee(id, actorUserId: ApiClient.actorUserId);
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
