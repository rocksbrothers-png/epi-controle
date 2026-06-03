import 'package:equatable/equatable.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:epi_api/epi_api.dart';
import '../api/api_client.dart';

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
  EmployeesCubit() : super(const EmployeesState());

  Future<void> load() async {
    emit(const EmployeesState(isLoading: true));
    try {
      final bootstrap = await ApiClient.auth.bootstrap();
      final employees = bootstrap.employees.map(Employee.fromJson).toList();
      // Cache actorUserId globally so downstream screens (e.g. employee detail)
      // can use it without an extra bootstrap call.
      if (bootstrap.users.isNotEmpty) {
        ApiClient.actorUserId =
            (bootstrap.users.first['id'] as num?)?.toInt() ?? 0;
      }
      emit(EmployeesState(employees: employees));
    } on Exception catch (e) {
      emit(EmployeesState(error: e.toString()));
    }
  }

  void search(String query) {
    emit(state._copyWith(query: query));
  }
}
