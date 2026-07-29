import 'package:dio/dio.dart';

import '../models/epi_reimbursement.dart';
import '../models/migration_suggestion.dart';
import '../models/outsourced_company.dart';
import '../models/service_contract.dart';

/// Cliente do Cadastro Simplificado de Terceirizados e Prestadores
/// (ADR-0002). A subpasta correspondente na UI nasce oculta por padrão —
/// só aparece quando o Administrador Geral liga o módulo `terceirizados`
/// em Configuração → Regras → Visualização (mesmo mecanismo de
/// `module_visibility` que já gateia CNPJs/Estoque/Entregas).
class OutsourcedCompaniesApi {
  const OutsourcedCompaniesApi(this._dio);
  final Dio _dio;

  static List<OutsourcedCompany> _parseCompanies(Map<String, dynamic>? data) {
    final raw = (data?['outsourced_companies'] as List?) ?? (data?['items'] as List?) ?? const [];
    return raw
        .cast<Map<String, dynamic>>()
        .map(OutsourcedCompany.fromJson)
        .toList(growable: false);
  }

  Future<List<OutsourcedCompany>> getOutsourcedCompanies({required int actorUserId}) async {
    final res = await _dio.get<Map<String, dynamic>>(
      '/api/outsourced-companies',
      queryParameters: {'actor_user_id': actorUserId},
    );
    return _parseCompanies(res.data);
  }

  Future<OutsourcedCompany?> getOutsourcedCompany(int id, {required int actorUserId}) async {
    final res = await _dio.get<Map<String, dynamic>>(
      '/api/outsourced-companies/$id',
      queryParameters: {'actor_user_id': actorUserId},
    );
    final raw = res.data?['outsourced_company'] as Map<String, dynamic>?;
    return raw == null ? null : OutsourcedCompany.fromJson(raw);
  }

  /// Cadastro Simplificado (CNPJ opcional) ou Padrão (CNPJ obrigatório) —
  /// mesma rota, a diferença é só quantos campos o formulário preenche.
  Future<Map<String, dynamic>> createOutsourcedCompany(
    Map<String, dynamic> body, {
    required int actorUserId,
  }) async {
    final res = await _dio.post<Map<String, dynamic>>(
      '/api/outsourced-companies',
      data: {...body, 'actor_user_id': actorUserId},
    );
    return res.data ?? {};
  }

  Future<Map<String, dynamic>> updateOutsourcedCompany(
    int id,
    Map<String, dynamic> body, {
    required int actorUserId,
  }) async {
    final res = await _dio.put<Map<String, dynamic>>(
      '/api/outsourced-companies/$id',
      data: {...body, 'actor_user_id': actorUserId},
    );
    return res.data ?? {};
  }

  /// Migração Simplificado → Padrão: mesma linha, mesmo id, sem duplicar
  /// nada. O backend exige CNPJ já preenchido antes de aceitar a promoção.
  Future<Map<String, dynamic>> promoteOutsourcedCompany(
    int id, {
    required int actorUserId,
  }) async {
    final res = await _dio.post<Map<String, dynamic>>(
      '/api/outsourced-companies/$id/promote',
      data: {'actor_user_id': actorUserId},
    );
    return res.data ?? {};
  }

  Future<List<ServiceContract>> getServiceContracts(
    int outsourcedCompanyId, {
    required int actorUserId,
  }) async {
    final res = await _dio.get<Map<String, dynamic>>(
      '/api/outsourced-companies/$outsourcedCompanyId/service-contracts',
      queryParameters: {'actor_user_id': actorUserId},
    );
    final raw = (res.data?['service_contracts'] as List?) ?? (res.data?['items'] as List?) ?? const [];
    return raw
        .cast<Map<String, dynamic>>()
        .map(ServiceContract.fromJson)
        .toList(growable: false);
  }

  Future<Map<String, dynamic>> createServiceContract(
    int outsourcedCompanyId,
    Map<String, dynamic> body, {
    required int actorUserId,
  }) async {
    final res = await _dio.post<Map<String, dynamic>>(
      '/api/outsourced-companies/$outsourcedCompanyId/service-contracts',
      data: {...body, 'actor_user_id': actorUserId},
    );
    return res.data ?? {};
  }

  /// Empresas ainda em Cadastro Simplificado além do limiar configurado —
  /// sugestão de promoção, nunca bloqueio.
  Future<List<MigrationSuggestion>> getMigrationSuggestions({required int actorUserId}) async {
    final res = await _dio.get<Map<String, dynamic>>(
      '/api/outsourced-companies/migration-suggestions',
      queryParameters: {'actor_user_id': actorUserId},
    );
    final raw = (res.data?['migration_suggestions'] as List?) ?? (res.data?['items'] as List?) ?? const [];
    return raw
        .cast<Map<String, dynamic>>()
        .map(MigrationSuggestion.fromJson)
        .toList(growable: false);
  }

  /// Ressarcimento: registro de apoio para conferência manual — nenhuma
  /// destas chamadas dispara cobrança ou integração de pagamento.
  Future<List<EpiReimbursement>> getReimbursements({
    required int actorUserId,
    int? outsourcedCompanyId,
    String? status,
  }) async {
    final res = await _dio.get<Map<String, dynamic>>(
      '/api/epi-reimbursements',
      queryParameters: {
        'actor_user_id': actorUserId,
        if (outsourcedCompanyId != null) 'outsourced_company_id': outsourcedCompanyId,
        if (status != null && status.isNotEmpty) 'status': status,
      },
    );
    final raw = (res.data?['epi_reimbursements'] as List?) ?? (res.data?['items'] as List?) ?? const [];
    return raw
        .cast<Map<String, dynamic>>()
        .map(EpiReimbursement.fromJson)
        .toList(growable: false);
  }

  Future<Map<String, dynamic>> createReimbursement(
    Map<String, dynamic> body, {
    required int actorUserId,
  }) async {
    final res = await _dio.post<Map<String, dynamic>>(
      '/api/epi-reimbursements',
      data: {...body, 'actor_user_id': actorUserId},
    );
    return res.data ?? {};
  }

  Future<Map<String, dynamic>> updateReimbursementStatus(
    int id,
    String status, {
    required int actorUserId,
  }) async {
    final res = await _dio.put<Map<String, dynamic>>(
      '/api/epi-reimbursements/$id/status',
      data: {'status': status, 'actor_user_id': actorUserId},
    );
    return res.data ?? {};
  }
}
