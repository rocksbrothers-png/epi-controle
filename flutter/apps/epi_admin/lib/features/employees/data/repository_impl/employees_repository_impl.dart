import 'package:epi_api/epi_api.dart';

import '../../domain/repositories/employees_repository.dart';
import '../datasources/employees_remote_datasource.dart';

class EmployeesRepositoryImpl implements EmployeesRepository {
  const EmployeesRepositoryImpl(this._remoteDataSource);

  final EmployeesRemoteDataSource _remoteDataSource;

  @override
  Future<List<Employee>> fetchEmployees() => _remoteDataSource.fetchEmployees();

  @override
  Future<Map<String, dynamic>> fetchEmployee(int id) =>
      _remoteDataSource.fetchEmployee(id);

  @override
  Future<void> createEmployee(Map<String, dynamic> body) =>
      _remoteDataSource.createEmployee(body);

  @override
  Future<void> updateEmployee(int id, Map<String, dynamic> body) =>
      _remoteDataSource.updateEmployee(id, body);

  @override
  Future<void> deleteEmployee(int id) => _remoteDataSource.deleteEmployee(id);
}
