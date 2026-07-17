import 'package:dio/dio.dart';
import '../models/ficha_config.dart';

class SettingsApi {
  const SettingsApi(this._dio);
  final Dio _dio;

  Future<FichaConfig> getFichaConfig() async {
    final res = await _dio.get<Map<String, dynamic>>('/api/ficha-config');
    return FichaConfig.fromJson(res.data ?? {});
  }

  Future<void> updateFichaConfig(FichaConfig config) async {
    await _dio.post<void>('/api/ficha-config', data: config.toJson());
  }

  /// Política de arquivamento por entidade (Configurações → Regras).
  /// Retenção em anos para Unidades, EPIs e Colaboradores (mínimo 5).
  /// A retenção da Ficha de EPI (5 anos, NR-6) tem regra própria e não é
  /// alterada por estes métodos.
  Future<Map<String, dynamic>> getArchivalPolicy({int? companyId}) async {
    final res = await _dio.get<Map<String, dynamic>>(
      '/api/archival-policy',
      queryParameters: companyId != null ? {'company_id': companyId} : null,
    );
    return res.data ?? {};
  }

  Future<Map<String, dynamic>> updateArchivalPolicy({
    required int actorUserId,
    required int unitRetentionYears,
    required int epiRetentionYears,
    required int employeeRetentionYears,
    int? companyId,
  }) async {
    final res = await _dio.put<Map<String, dynamic>>(
      '/api/archival-policy',
      data: {
        'actor_user_id': actorUserId,
        'unit_retention_years': unitRetentionYears,
        'epi_retention_years': epiRetentionYears,
        'employee_retention_years': employeeRetentionYears,
        if (companyId != null) 'company_id': companyId,
      },
    );
    return res.data ?? {};
  }
}
