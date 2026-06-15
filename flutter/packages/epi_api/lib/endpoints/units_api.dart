import 'package:dio/dio.dart';

class UnitsApi {
  const UnitsApi(this._dio);
  final Dio _dio;

  Future<Map<String, dynamic>> createUnit(Map<String, dynamic> body) async {
    final res = await _dio.post<Map<String, dynamic>>('/api/units', data: body);
    return res.data ?? {};
  }

  Future<Map<String, dynamic>> updateUnit(int id, Map<String, dynamic> body) async {
    final res = await _dio.put<Map<String, dynamic>>('/api/units/$id', data: body);
    return res.data ?? {};
  }

  Future<void> deleteUnit(int id, {required int actorUserId}) async {
    await _dio.delete(
      '/api/units/$id',
      queryParameters: {'actor_user_id': actorUserId},
    );
  }
}
