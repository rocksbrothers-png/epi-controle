import '../repositories/employees_repository.dart';

class CreateEmployeeUseCase {
  const CreateEmployeeUseCase(this._repository);

  final EmployeesRepository _repository;

  Future<void> call(Map<String, dynamic> body) =>
      _repository.createEmployee(body);
}
