import 'package:dio/dio.dart';
import 'package:equatable/equatable.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:epi_api/epi_api.dart';

import '../../data/datasources/employees_remote_datasource.dart';
import '../../data/repository_impl/employees_repository_impl.dart';
import '../../domain/repositories/employees_repository.dart';
import '../../domain/usecases/create_employee_usecase.dart';
import '../../domain/usecases/fetch_employees_usecase.dart';
import '../../domain/usecases/update_employee_usecase.dart';

class EmployeesState extends Equatable {
  const EmployeesState({
    this.isLoading = false,
    this.error,
    this.employees = const [],
    this.archivedEmployees = const [],
    this.showArchived = false,
    this.query = '',
  });

  final bool isLoading;
  final String? error;
  final List<Employee> employees;

  /// Colaboradores arquivados (soft delete): desativados para novas operações,
  /// com histórico preservado. Podem ser desarquivados, voltando a ativos.
  final List<Map<String, dynamic>> archivedEmployees;

  /// Alterna a listagem entre colaboradores ativos e arquivados.
  final bool showArchived;
  final String query;

  List<Map<String, dynamic>> get filteredArchived {
    if (query.isEmpty) return archivedEmployees;
    final q = query.toLowerCase();
    return archivedEmployees.where((e) {
      final name = (e['name'] as String? ?? '').toLowerCase();
      final code = (e['employee_id_code'] as String? ?? '').toLowerCase();
      return name.contains(q) || code.contains(q);
    }).toList();
  }

  List<Employee> get filtered {
    if (query.isEmpty) return employees;
    final q = query.toLowerCase();
    return employees.where((e) {
      return e.name.toLowerCase().contains(q) ||
          (e.code?.toLowerCase().contains(q) ?? false) ||
          (e.sector?.toLowerCase().contains(q) ?? false) ||
          (e.role?.toLowerCase().contains(q) ?? false);
    }).toList();
  }

  EmployeesState _copyWith({
    bool? isLoading,
    String? error,
    List<Employee>? employees,
    List<Map<String, dynamic>>? archivedEmployees,
    bool? showArchived,
    String? query,
  }) =>
      EmployeesState(
        isLoading: isLoading ?? this.isLoading,
        error: error,
        employees: employees ?? this.employees,
        archivedEmployees: archivedEmployees ?? this.archivedEmployees,
        showArchived: showArchived ?? this.showArchived,
        query: query ?? this.query,
      );

  @override
  List<Object?> get props =>
      [isLoading, error, employees, archivedEmployees, showArchived, query];
}

class EmployeesCubit extends Cubit<EmployeesState> {
  EmployeesCubit({EmployeesRepository? repository})
      : _repository = repository ??
            const EmployeesRepositoryImpl(ApiEmployeesRemoteDataSource()),
        super(const EmployeesState());

  final EmployeesRepository _repository;

  FetchEmployeesUseCase get _fetchEmployees => FetchEmployeesUseCase(_repository);
  CreateEmployeeUseCase get _createEmployee => CreateEmployeeUseCase(_repository);
  UpdateEmployeeUseCase get _updateEmployee => UpdateEmployeeUseCase(_repository);

  Future<void> load() async {
    emit(state._copyWith(isLoading: true));
    try {
      final employees = await _fetchEmployees();
      final archived = await _loadArchivedSafe();
      emit(state._copyWith(
        isLoading: false,
        employees: employees,
        archivedEmployees: archived,
      ));
    } on Exception catch (e) {
      emit(state._copyWith(isLoading: false, error: e.toString()));
    }
  }

  /// Alterna entre a listagem de colaboradores ativos e a de arquivados.
  void toggleArchivedView() =>
      emit(state._copyWith(showArchived: !state.showArchived));

  void search(String query) {
    emit(state._copyWith(query: query));
  }

  Future<void> createEmployee(Map<String, dynamic> body) async {
    emit(state._copyWith(isLoading: true));
    try {
      await _createEmployee(body);
      await _reloadEmployees();
    } on Exception catch (e) {
      emit(state._copyWith(isLoading: false, error: _errorMessage(e)));
    }
  }

  Future<void> updateEmployee(int id, Map<String, dynamic> body) async {
    emit(state._copyWith(isLoading: true));
    try {
      await _updateEmployee(id, body);
      await _reloadEmployees();
    } on Exception catch (e) {
      emit(state._copyWith(isLoading: false, error: _errorMessage(e)));
    }
  }

  /// Arquiva o colaborador (soft delete): histórico preservado pelo período
  /// mínimo de retenção configurado (>= 5 anos).
  Future<void> archiveEmployee(int id, {String reason = ''}) async {
    emit(state._copyWith(isLoading: true));
    try {
      await _repository.archiveEmployee(id, reason: reason);
      await _reloadEmployees();
    } on Exception catch (e) {
      emit(state._copyWith(isLoading: false, error: _errorMessage(e)));
    }
  }

  /// Desarquiva o colaborador: volta ao status ativo, com histórico intacto.
  Future<void> restoreEmployee(int id) async {
    emit(state._copyWith(isLoading: true));
    try {
      await _repository.restoreEmployee(id);
      await _reloadEmployees();
    } on Exception catch (e) {
      emit(state._copyWith(isLoading: false, error: _errorMessage(e)));
    }
  }

  Future<List<Map<String, dynamic>>> _loadArchivedSafe() async {
    // Backends anteriores à política de arquivamento não têm o endpoint.
    try {
      return await _repository.fetchArchivedEmployees();
    } on Exception {
      return const [];
    }
  }

  Future<void> _reloadEmployees() async {
    final employees = await _fetchEmployees();
    final archived = await _loadArchivedSafe();
    emit(state._copyWith(
      isLoading: false,
      employees: employees,
      archivedEmployees: archived,
    ));
  }

  String _errorMessage(Exception e) {
    if (e is DioException) {
      final data = e.response?.data;
      if (data is Map &&
          data['error'] is Map &&
          data['error']['message'] != null) {
        return data['error']['message'].toString();
      }
      if (data is Map && data['error'] != null) {
        return data['error'].toString();
      }
    }
    return e.toString();
  }
}
