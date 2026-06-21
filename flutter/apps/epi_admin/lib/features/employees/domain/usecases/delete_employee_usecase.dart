import '../repositories/employees_repository.dart';

class DeleteEmployeeUseCase {
  const DeleteEmployeeUseCase(this._repository);

  final EmployeesRepository _repository;

  Future<void> call(int id) => _repository.deleteEmployee(id);
}
