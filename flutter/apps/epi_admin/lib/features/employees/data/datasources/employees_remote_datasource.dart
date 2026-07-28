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
    // O ator NÃO é definido aqui. Ele vem da sessão autenticada
    // (`ApiClient.actorUserId`, escrito ao salvar/restaurar a sessão).
    //
    // Antes esta linha fazia duas coisas erradas ao mesmo tempo: definia o ator
    // como `bootstrap.users.first` — o primeiro usuário da empresa, não quem
    // estava logado — e só o fazia quando alguém abria Colaboradores. Quem
    // fosse direto a outra tela mandava `actor_user_id=0` e tomava 401.
    final bootstrap = await ApiClient.auth.bootstrap();
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
