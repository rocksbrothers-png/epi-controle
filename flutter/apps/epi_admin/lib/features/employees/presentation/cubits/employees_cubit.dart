import 'package:dio/dio.dart';
import 'package:equatable/equatable.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:epi_api/epi_api.dart';

import '../../data/datasources/employees_remote_datasource.dart';
import '../../data/repository_impl/employees_repository_impl.dart';
import '../../domain/repositories/employees_repository.dart';
import '../../domain/usecases/create_employee_usecase.dart';
import '../../domain/usecases/delete_employee_usecase.dart';
import '../../domain/usecases/fetch_employees_usecase.dart';
import '../../domain/usecases/update_employee_usecase.dart';

class EmployeesState extends Equatable {
  const EmployeesState({
    this.isLoading = false,
    this.error,
    this.employees = const [],
    this.query = '',
  });

  final bool isLoading;
  final String? error;
  final List<Employee> employees;
  final String query;

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
    String? query,
  }) =>
      EmployeesState(
        isLoading: isLoading ?? this.isLoading,
        error: error,
        employees: employees ?? this.employees,
        query: query ?? this.query,
      );

  @override
  List<Object?> get props => [isLoading, error, employees, query];
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
  DeleteEmployeeUseCase get _deleteEmployee => DeleteEmployeeUseCase(_repository);

  Future<void> load() async {
    emit(const EmployeesState(isLoading: true));
    try {
      emit(EmployeesState(employees: await _fetchEmployees()));
    } on Exception catch (e) {
      emit(EmployeesState(error: e.toString()));
    }
  }

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

  Future<void> deleteEmployee(int id) async {
    emit(state._copyWith(isLoading: true));
    try {
      await _deleteEmployee(id);
      await _reloadEmployees();
    } on Exception catch (e) {
      emit(state._copyWith(isLoading: false, error: _errorMessage(e)));
    }
  }

  Future<void> _reloadEmployees() async {
    emit(EmployeesState(employees: await _fetchEmployees()));
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
