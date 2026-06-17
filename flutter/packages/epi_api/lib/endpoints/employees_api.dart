import 'package:dio/dio.dart';

/// Cliente REST de Funcionários (CRUD). Espelha [UsersApi].
/// Endpoints: GET/POST /api/employees · GET/PUT/DELETE /api/employees/{id}.
class EmployeesApi {
  const EmployeesApi(this._dio);
  final Dio _dio;

  Future<Map<String, dynamic>> getEmployee(int id, {required int actorUserId}) async {
    final res = await _dio.get<Map<String, dynamic>>(
      '/api/employees/$id',
      queryParameters: {'actor_user_id': actorUserId},
    );
    return (res.data?['employee'] as Map?)?.cast<String, dynamic>() ?? {};
  }

  Future<Map<String, dynamic>> createEmployee(Map<String, dynamic> body) async {
    final res = await _dio.post<Map<String, dynamic>>('/api/employees', data: body);
    return res.data ?? {};
  }

  Future<Map<String, dynamic>> updateEmployee(int id, Map<String, dynamic> body) async {
    final res = await _dio.put<Map<String, dynamic>>('/api/employees/$id', data: body);
    return res.data ?? {};
  }

  Future<void> deleteEmployee(int id, {required int actorUserId}) async {
    await _dio.delete(
      '/api/employees/$id',
      queryParameters: {'actor_user_id': actorUserId},
    );
  }
}
