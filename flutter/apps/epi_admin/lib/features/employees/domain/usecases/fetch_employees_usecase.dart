import 'package:epi_api/epi_api.dart';

import '../repositories/employees_repository.dart';

class FetchEmployeesUseCase {
  const FetchEmployeesUseCase(this._repository);

  final EmployeesRepository _repository;

  Future<List<Employee>> call() => _repository.fetchEmployees();
}
