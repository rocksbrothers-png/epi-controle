import 'package:dio/dio.dart';

/// Cliente REST de EPIs (CRUD). Espelha [UsersApi]/[EmployeesApi].
/// Endpoints: POST /api/epis · PUT /api/epis/{id} · DELETE /api/epis/{id}.
class EpisApi {
  const EpisApi(this._dio);
  final Dio _dio;

  Future<Map<String, dynamic>> createEpi(Map<String, dynamic> body) async {
    final res = await _dio.post<Map<String, dynamic>>('/api/epis', data: body);
    return res.data ?? {};
  }

  Future<Map<String, dynamic>> updateEpi(int id, Map<String, dynamic> body) async {
    final res = await _dio.put<Map<String, dynamic>>('/api/epis/$id', data: body);
    return res.data ?? {};
  }

  Future<void> deleteEpi(int id, {required int actorUserId}) async {
    await _dio.delete(
      '/api/epis/$id',
      queryParameters: {'actor_user_id': actorUserId},
    );
  }
}
