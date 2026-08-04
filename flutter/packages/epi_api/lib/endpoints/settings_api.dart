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

  /// Visibilidade de módulo por perfil (Configuração → Regras →
  /// Visualização) — mesmo mecanismo que já gateia CNPJs/Estoque/Entregas,
  /// reaproveitado para os módulos opt-in `terceirizados` e
  /// `terceirizados_colaboradores` (ADR-0002 §10.3).
  ///
  /// Retorna `{module_visibility: {role: {module: bool}}, modules: [...]}`.
  Future<Map<String, dynamic>> getModuleVisibility({int? companyId}) async {
    final res = await _dio.get<Map<String, dynamic>>(
      '/api/module-visibility',
      queryParameters: companyId != null ? {'company_id': companyId} : null,
    );
    return res.data ?? {};
  }

  Future<Map<String, dynamic>> saveModuleVisibility({
    required int actorUserId,
    required String role,
    required Map<String, bool> modules,
    int? companyId,
  }) async {
    final res = await _dio.post<Map<String, dynamic>>(
      '/api/module-visibility',
      data: {
        'actor_user_id': actorUserId,
        'role': role,
        'modules': modules,
        if (companyId != null) 'company_id': companyId,
      },
    );
    return res.data ?? {};
  }

  /// Escopo por Unidade dos módulos opt-in unit-scopable (`terceirizados`,
  /// `terceirizados_colaboradores`) — ampliação do `module_visibility`
  /// (correção do ADR-0002 §10.3): quando a lista de unidades de um módulo
  /// não está vazia, `admin`/`user` só o veem nas unidades autorizadas.
  ///
  /// Retorna `{module_unit_scope: {module: [unit_id,...]}, unit_scopable_modules: [...]}`.
  Future<Map<String, dynamic>> getModuleUnitScope({int? companyId}) async {
    final res = await _dio.get<Map<String, dynamic>>(
      '/api/module-unit-scope',
      queryParameters: companyId != null ? {'company_id': companyId} : null,
    );
    return res.data ?? {};
  }

  Future<Map<String, dynamic>> saveModuleUnitScope({
    required int actorUserId,
    required String module,
    required List<int> unitIds,
    int? companyId,
  }) async {
    final res = await _dio.post<Map<String, dynamic>>(
      '/api/module-unit-scope',
      data: {
        'actor_user_id': actorUserId,
        'module': module,
        'unit_ids': unitIds,
        if (companyId != null) 'company_id': companyId,
      },
    );
    return res.data ?? {};
  }
}
