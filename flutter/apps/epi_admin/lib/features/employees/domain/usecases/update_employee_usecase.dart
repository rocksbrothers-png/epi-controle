import '../repositories/employees_repository.dart';

class UpdateEmployeeUseCase {
  const UpdateEmployeeUseCase(this._repository);

  final EmployeesRepository _repository;

  Future<void> call(int id, Map<String, dynamic> body) =>
      _repository.updateEmployee(id, body);
}
