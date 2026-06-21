import 'package:epi_api/epi_api.dart';

abstract class EmployeesRepository {
  Future<List<Employee>> fetchEmployees();
  Future<Map<String, dynamic>> fetchEmployee(int id);
  Future<void> createEmployee(Map<String, dynamic> body);
  Future<void> updateEmployee(int id, Map<String, dynamic> body);
  Future<void> deleteEmployee(int id);
}
