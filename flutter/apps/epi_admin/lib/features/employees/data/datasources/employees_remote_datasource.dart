import 'package:epi_api/epi_api.dart';

import '../../../../core/api/api_client.dart';

abstract class EmployeesRemoteDataSource {
  Future<List<Employee>> fetchEmployees();
  Future<Map<String, dynamic>> fetchEmployee(int id);
  Future<void> createEmployee(Map<String, dynamic> body);
  Future<void> updateEmployee(int id, Map<String, dynamic> body);
  Future<void> deleteEmployee(int id);
  Future<void> archiveEmployee(int id, {String reason});
  Future<void> restoreEmployee(int id);
  Future<List<Map<String, dynamic>>> fetchArchivedEmployees();
}

class ApiEmployeesRemoteDataSource implements EmployeesRemoteDataSource {
  const ApiEmployeesRemoteDataSource();

  @override
  Future<List<Employee>> fetchEmployees() async {
    final bootstrap = await ApiClient.auth.bootstrap();
    if (bootstrap.users.isNotEmpty) {
      ApiClient.actorUserId =
          (bootstrap.users.first['id'] as num?)?.toInt() ?? 0;
    }
    return bootstrap.employees.map(Employee.fromJson).toList();
  }

  @override
  Future<Map<String, dynamic>> fetchEmployee(int id) =>
      ApiClient.employees.getEmployee(id, actorUserId: ApiClient.actorUserId);

  @override
  Future<void> createEmployee(Map<String, dynamic> body) async {
    await ApiClient.employees.createEmployee({
      ...body,
      'actor_user_id': ApiClient.actorUserId,
    });
  }

  @override
  Future<void> updateEmployee(int id, Map<String, dynamic> body) async {
    await ApiClient.employees.updateEmployee(id, {
      ...body,
      'actor_user_id': ApiClient.actorUserId,
    });
  }

  @override
  Future<void> deleteEmployee(int id) =>
      ApiClient.employees.deleteEmployee(id, actorUserId: ApiClient.actorUserId);

  @override
  Future<void> archiveEmployee(int id, {String reason = ''}) async {
    await ApiClient.employees.archiveEmployee(
      id,
      actorUserId: ApiClient.actorUserId,
      reason: reason,
    );
  }

  @override
  Future<void> restoreEmployee(int id) async {
    await ApiClient.employees.restoreEmployee(
      id,
      actorUserId: ApiClient.actorUserId,
    );
  }

  @override
  Future<List<Map<String, dynamic>>> fetchArchivedEmployees() =>
      ApiClient.employees.getArchivedEmployees(actorUserId: ApiClient.actorUserId);
}
