import 'package:dio/dio.dart';

import '../models/dashboard_summary.dart';

/// `GET /api/dashboard/summary` — a fonte única do painel (fatia 1.1D-B).
///
/// Substitui o padrão anterior, em que o Dashboard baixava `/api/bootstrap`
/// inteiro (colaboradores, entregas, EPIs, usuários, empresas, logs de
/// auditoria) e recomputava os KPIs e o recorte em Dart.
class DashboardApi {
  const DashboardApi(this._dio);
  final Dio _dio;

  /// Resumo já recortado e calculado pelo servidor.
  ///
  /// `legalEntityId`, `unitId` e `sector` são a SELEÇÃO do usuário no filtro em
  /// cascata. Para perfil travado o backend os ignora e devolve a Unidade do
  /// ator — o cliente pode enviá-los sem risco, porque a decisão é do servidor
  /// (`resolve_unit_scope`), não da tela.
  Future<DashboardSummary> summary({
    required int actorUserId,
    int? legalEntityId,
    int? unitId,
    String? sector,
  }) async {
    final res = await _dio.get<Map<String, dynamic>>(
      '/api/dashboard/summary',
      queryParameters: {
        'actor_user_id': actorUserId,
        if (legalEntityId != null) 'legal_entity_id': legalEntityId,
        if (unitId != null) 'unit_id': unitId,
        if (sector != null && sector.isNotEmpty) 'sector': sector,
      },
    );
    return DashboardSummary.fromJson(res.data ?? const {});
  }
}
