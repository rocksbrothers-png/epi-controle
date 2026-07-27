import 'package:dio/dio.dart';

import '../models/legal_entity.dart';

/// Cliente dos CNPJs da empresa (Multi-CNPJ / Joint Venture).
///
/// O backend já escopa por papel: Administrador Geral/Registro veem todos os
/// CNPJs da empresa; Administrador Local vê apenas os autorizados; Usuário vê
/// somente o CNPJ do seu colaborador.
class LegalEntitiesApi {
  const LegalEntitiesApi(this._dio);
  final Dio _dio;

  static List<LegalEntity> _parseList(Map<String, dynamic>? data) {
    final raw = (data?['legal_entities'] as List?) ?? (data?['items'] as List?) ?? const [];
    return raw
        .cast<Map<String, dynamic>>()
        .map(LegalEntity.fromJson)
        .toList(growable: false);
  }

  Future<List<LegalEntity>> getLegalEntities({required int actorUserId}) async {
    final res = await _dio.get<Map<String, dynamic>>(
      '/api/legal-entities',
      queryParameters: {'actor_user_id': actorUserId},
    );
    return _parseList(res.data);
  }

  Future<List<LegalEntity>> getCompanyLegalEntities(
    int companyId, {
    required int actorUserId,
  }) async {
    final res = await _dio.get<Map<String, dynamic>>(
      '/api/companies/$companyId/legal-entities',
      queryParameters: {'actor_user_id': actorUserId},
    );
    return _parseList(res.data);
  }

  Future<Map<String, dynamic>> createLegalEntity(Map<String, dynamic> body) async {
    final res = await _dio.post<Map<String, dynamic>>('/api/legal-entities', data: body);
    return res.data ?? {};
  }

  Future<Map<String, dynamic>> updateLegalEntity(int id, Map<String, dynamic> body) async {
    final res = await _dio.put<Map<String, dynamic>>('/api/legal-entities/$id', data: body);
    return res.data ?? {};
  }

  /// Cadastro em lote — usado no onboarding de empresa com múltiplos CNPJs / JV.
  /// Erros vêm por índice em `errors`; os itens válidos são gravados.
  Future<Map<String, dynamic>> createLegalEntitiesBatch(
    List<Map<String, dynamic>> entities, {
    required int actorUserId,
    int? companyId,
  }) async {
    final res = await _dio.post<Map<String, dynamic>>(
      '/api/legal-entities/batch',
      data: {
        'actor_user_id': actorUserId,
        if (companyId != null) 'company_id': companyId,
        'legal_entities': entities,
      },
    );
    return res.data ?? {};
  }

  /// Importação de planilha. As linhas já vêm convertidas em mapas pelo app;
  /// o backend aceita cabeçalhos em português (com/sem acento) e inglês e
  /// devolve os erros por linha em `errors`.
  Future<Map<String, dynamic>> importLegalEntities(
    List<Map<String, dynamic>> rows, {
    required int actorUserId,
    int? companyId,
  }) async {
    final res = await _dio.post<Map<String, dynamic>>(
      '/api/legal-entities/import',
      data: {
        'actor_user_id': actorUserId,
        if (companyId != null) 'company_id': companyId,
        'rows': rows,
      },
    );
    return res.data ?? {};
  }

  /// Inativa o CNPJ. Nunca é exclusão física: o histórico jurídico/fiscal é
  /// preservado. O backend recusa o último CNPJ ativo e CNPJ com colaboradores
  /// vinculados.
  Future<Map<String, dynamic>> deactivateLegalEntity(
    int id, {
    required int actorUserId,
  }) async {
    final res = await _dio.delete<Map<String, dynamic>>(
      '/api/legal-entities/$id',
      data: {'actor_user_id': actorUserId},
    );
    return res.data ?? {};
  }

  /// CNPJs autorizados a um usuário (Administrador Local restrito).
  Future<List<int>> getUserLegalEntities(int userId, {required int actorUserId}) async {
    final res = await _dio.get<Map<String, dynamic>>(
      '/api/users/$userId/legal-entities',
      queryParameters: {'actor_user_id': actorUserId},
    );
    final raw = (res.data?['legal_entity_ids'] as List?) ?? const [];
    return raw.map((e) => (e as num).toInt()).toList(growable: false);
  }

  /// Define os CNPJs autorizados a um usuário. Lista vazia remove a restrição.
  Future<List<int>> setUserLegalEntities(
    int userId, {
    required int actorUserId,
    required List<int> legalEntityIds,
  }) async {
    final res = await _dio.put<Map<String, dynamic>>(
      '/api/users/$userId/legal-entities',
      data: {'actor_user_id': actorUserId, 'legal_entity_ids': legalEntityIds},
    );
    final raw = (res.data?['legal_entity_ids'] as List?) ?? const [];
    return raw.map((e) => (e as num).toInt()).toList(growable: false);
  }

  /// Histórico de vínculo jurídico do colaborador (mudanças de CNPJ).
  Future<List<Map<String, dynamic>>> getEmployeeLegalEntityMovements(
    int employeeId, {
    required int actorUserId,
  }) async {
    final res = await _dio.get<Map<String, dynamic>>(
      '/api/employees/$employeeId/legal-entity-movements',
      queryParameters: {'actor_user_id': actorUserId},
    );
    return ((res.data?['movements'] as List?) ?? const [])
        .cast<Map<String, dynamic>>();
  }

  /// Processo administrativo de mudança do CNPJ do colaborador.
  ///
  /// O CNPJ é imutável na edição comum do cadastro — esta é a única via de
  /// alteração e exige justificativa, gerando histórico e auditoria.
  Future<Map<String, dynamic>> transferEmployeeLegalEntity(
    int employeeId, {
    required int actorUserId,
    required int legalEntityId,
    required String reason,
    String effectiveDate = '',
  }) async {
    final res = await _dio.post<Map<String, dynamic>>(
      '/api/employees/$employeeId/legal-entity-transfer',
      data: {
        'actor_user_id': actorUserId,
        'legal_entity_id': legalEntityId,
        'reason': reason,
        if (effectiveDate.isNotEmpty) 'effective_date': effectiveDate,
      },
    );
    return res.data ?? {};
  }
}
