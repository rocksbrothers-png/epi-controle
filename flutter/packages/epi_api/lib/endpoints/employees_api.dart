import 'package:dio/dio.dart';

/// Cliente REST de Funcionários (CRUD). Espelha [UsersApi].
/// Endpoints: POST /api/employees · PUT /api/employees/{id} · DELETE /api/employees/{id}.
class EmployeesApi {
  const EmployeesApi(this._dio);
  final Dio _dio;

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
