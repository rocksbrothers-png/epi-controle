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

  /// Estado de vínculos vivos do EPI (item 1). A UI usa isto para decidir entre
  /// arquivar direto ou oferecer "bloquear saldo e arquivar". A REGRA é do
  /// backend (has_open_links/blockable); o cliente apenas repassa o contrato.
  /// GET /api/epis/{id}/archival-state.
  Future<Map<String, dynamic>> getEpiArchivalState(
    int id, {
    required int actorUserId,
  }) async {
    final res = await _dio.get<Map<String, dynamic>>(
      '/api/epis/$id/archival-state',
      queryParameters: {'actor_user_id': actorUserId},
    );
    return (res.data?['archival_state'] as Map?)?.cast<String, dynamic>() ?? {};
  }

  /// Arquiva o EPI (soft delete): desativado para novas operações,
  /// histórico preservado pelo período mínimo de retenção (>= 5 anos).
  ///
  /// Quando o EPI tem saldo/vínculos vivos, o backend recusa o arquivamento
  /// direto (409 EPI_HAS_STOCK_LINKS). Passe [blockAndArchive] = true (com
  /// [reason] obrigatório) para autorizar o bloqueio do saldo disponível
  /// (movido para Estoque Bloqueado, rastreável) e então arquivar.
  Future<Map<String, dynamic>> archiveEpi(
    int id, {
    required int actorUserId,
    String reason = '',
    bool blockAndArchive = false,
  }) async {
    final res = await _dio.post<Map<String, dynamic>>(
      '/api/epis/$id/archive',
      data: {
        'actor_user_id': actorUserId,
        'reason': reason,
        'block_and_archive': blockAndArchive,
      },
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
