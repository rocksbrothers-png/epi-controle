import 'package:dio/dio.dart';

/// Cliente REST de EPIs (CRUD). Espelha [UsersApi]/[EmployeesApi].
/// Endpoints: GET/POST /api/epis · GET/PUT/DELETE /api/epis/{id}.
class EpisApi {
  const EpisApi(this._dio);
  final Dio _dio;

  Future<Map<String, dynamic>> getEpi(int id, {required int actorUserId}) async {
    final res = await _dio.get<Map<String, dynamic>>(
      '/api/epis/$id',
      queryParameters: {'actor_user_id': actorUserId},
    );
    return (res.data?['epi'] as Map?)?.cast<String, dynamic>() ?? {};
  }

  Future<Map<String, dynamic>> createEpi(Map<String, dynamic> body) async {
    final res = await _dio.post<Map<String, dynamic>>('/api/epis', data: body);
    return res.data ?? {};
  }

  Future<Map<String, dynamic>> updateEpi(int id, Map<String, dynamic> body) async {
    final res = await _dio.put<Map<String, dynamic>>('/api/epis/$id', data: body);
    return res.data ?? {};
  }

  /// Arquiva o EPI (soft delete): desativado para novas operações,
  /// histórico preservado pelo período mínimo de retenção (>= 5 anos).
  Future<Map<String, dynamic>> archiveEpi(
    int id, {
    required int actorUserId,
    String reason = '',
  }) async {
    final res = await _dio.post<Map<String, dynamic>>(
      '/api/epis/$id/archive',
      data: {'actor_user_id': actorUserId, 'reason': reason},
    );
    return res.data ?? {};
  }

  /// Desarquiva o EPI, que volta ao status ativo.
  Future<Map<String, dynamic>> restoreEpi(int id, {required int actorUserId}) async {
    final res = await _dio.post<Map<String, dynamic>>(
      '/api/epis/$id/restore',
      data: {'actor_user_id': actorUserId},
    );
    return res.data ?? {};
  }

  /// EPIs arquivados do tenant, com motivo e retenção restante.
  Future<List<Map<String, dynamic>>> getArchivedEpis({required int actorUserId}) async {
    final res = await _dio.get<Map<String, dynamic>>(
      '/api/epis/archived',
      queryParameters: {'actor_user_id': actorUserId},
    );
    final items = res.data?['epis'];
    if (items is List) {
      return items.whereType<Map<String, dynamic>>().toList();
    }
    return const [];
  }

  /// O backend não remove mais fisicamente: DELETE arquiva o EPI preservando
  /// o histórico (política de retenção). Prefira [archiveEpi].
  Future<void> deleteEpi(int id, {required int actorUserId}) async {
    await _dio.delete(
      '/api/epis/$id',
      queryParameters: {'actor_user_id': actorUserId},
    );
  }
}
