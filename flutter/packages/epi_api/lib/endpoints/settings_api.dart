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

  /// Visibilidade de módulo por perfil e, para `admin`/`user`, por Unidade
  /// (Configuração → Regras → Visualização) — mesmo mecanismo que já gateia
  /// CNPJs/Estoque/Entregas, cobrindo todos os módulos (issue #148),
  /// `module_visibility` é a única fonte de verdade para
  /// `tenant + perfil + unidade + módulo` (substituiu o antigo
  /// `module_unit_scope`, retirado do backend).
  ///
  /// Retorna `{module_visibility: {role: {"*": {module: bool},
  /// "unit_id": {module: bool}}}, modules: [...]}` (a chave do bucket por
  /// Unidade é o id numérico da Unidade, como string). Um módulo ausente do
  /// bucket da Unidade herda o valor do bucket `"*"` do mesmo perfil.
  Future<Map<String, dynamic>> getModuleVisibility({int? companyId}) async {
    final res = await _dio.get<Map<String, dynamic>>(
      '/api/module-visibility',
      queryParameters: companyId != null ? {'company_id': companyId} : null,
    );
    return res.data ?? {};
  }

  /// [unitId] é opcional e só é aceito pelo backend para os perfis com
  /// vínculo de unidade única (`admin`/`user`) — grava no bucket daquela
  /// Unidade em vez do bucket padrão `"*"`. Omitido (ou `null`), grava no
  /// bucket `"*"`, preservando o comportamento anterior à extensão por
  /// Unidade.
  Future<Map<String, dynamic>> saveModuleVisibility({
    required int actorUserId,
    required String role,
    required Map<String, bool> modules,
    int? unitId,
    int? companyId,
  }) async {
    final res = await _dio.post<Map<String, dynamic>>(
      '/api/module-visibility',
      data: {
        'actor_user_id': actorUserId,
        'role': role,
        'modules': modules,
        if (unitId != null) 'unit_id': unitId,
        if (companyId != null) 'company_id': companyId,
      },
    );
    return res.data ?? {};
  }
}
