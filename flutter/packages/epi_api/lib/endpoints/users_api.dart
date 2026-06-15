import 'package:dio/dio.dart';

class UsersApi {
  const UsersApi(this._dio);
  final Dio _dio;

  Future<Map<String, dynamic>> createUser(Map<String, dynamic> body) async {
    final res = await _dio.post<Map<String, dynamic>>('/api/users', data: body);
    return res.data ?? {};
  }

  Future<Map<String, dynamic>> updateUser(int id, Map<String, dynamic> body) async {
    final res = await _dio.put<Map<String, dynamic>>('/api/users/$id', data: body);
    return res.data ?? {};
  }

  Future<void> deleteUser(int id, {required int actorUserId}) async {
    await _dio.delete(
      '/api/users/$id',
      queryParameters: {'actor_user_id': actorUserId},
    );
  }
}
