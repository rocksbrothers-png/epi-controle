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

  /// Colaboradores terceirizados/prestadores ativos — filtro client-side
  /// (`employmentType != CLT`) sobre a lista de `employees` do bootstrap,
  /// já escopada por tenant/unidade pelo backend.
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
  /// [employeesApi]/[authApi] existem para o teste.
  OutsourcedEmployeesCubit({EmployeesApi? employeesApi, AuthApi? authApi})
      : _employeesApi = employeesApi,
        _authApi = authApi,
        super(const OutsourcedEmployeesState());

  final EmployeesApi? _employeesApi;
  final AuthApi? _authApi;

  EmployeesApi get _employees => _employeesApi ?? ApiClient.employees;
  AuthApi get _auth => _authApi ?? ApiClient.auth;

  Future<void> load() async {
    emit(state.copyWith(isLoading: true, clearError: true));
    await _reload();
  }

  Future<void> _reload() async {
    try {
      final bootstrap = await _auth.bootstrap();
      final employees = bootstrap.employees
          .map(Employee.fromJson)
          .where((e) => (e.employmentType ?? '').isNotEmpty && e.employmentType != 'CLT')
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

  /// Arquiva o colaborador (soft delete) — mesma rota/regra dos colaboradores
  /// CLT: histórico preservado pelo período mínimo de retenção configurado.
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
