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

  // ── Vínculo da empresa com a Unidade (ADR-0002 §12) ─────────────────────
  //
  // Existe para resolver o mesmo problema do vínculo de colaborador, um nível
  // acima: a empresa terceirizada é ÚNICA no tenant, e uma Unidade que ainda
  // não trabalha com ela precisa localizar o cadastro existente e criar o seu
  // próprio vínculo — sem duplicar a empresa e sem herdar contratos,
  // colaboradores ou notas de outra Unidade.
  //
  // Não há rota de remoção, aqui como lá: arquivar o vínculo local é a forma
  // de a Unidade declarar que não usa mais a empresa, e a exclusão definitiva
  // segue exclusiva do fluxo de retenção e purga.

  /// Busca empresas do tenant pelo nome, para o fluxo de vinculação.
  ///
  /// É o que permite a uma Unidade **sem vínculo** encontrar a empresa: a
  /// listagem comum (`getOutsourcedCompanies`) mostra só o que a Unidade já
  /// vinculou, então sem esta busca o cadastro existente seria invisível
  /// justamente para quem precisa vinculá-lo — e a saída do operador seria
  /// cadastrar a empresa de novo, que é o que o desenho existe para evitar.
  ///
  /// Os itens vêm de dois tipos, distinguidos por
  /// [OutsourcedCompany.isMaskedForLinking]: já vinculados (completos, com
  /// [OutsourcedCompany.localUnitLinkStatus]) e disponíveis para vincular
  /// (mascarados — só identificação, CNPJ ofuscado, Unidade de origem e
  /// quantas Unidades já usam).
  Future<List<OutsourcedCompany>> searchOutsourcedCompanies({
    required int actorUserId,
    required String query,
  }) async {
    final res = await _dio.get<Map<String, dynamic>>(
      '/api/outsourced-companies/search',
      queryParameters: {'actor_user_id': actorUserId, 'q': query},
    );
    return _parseCompanies(res.data);
  }

  /// "Vincular a esta Unidade" — `POST /api/outsourced-companies/{id}/link`.
  ///
  /// [unitId] é ignorado para perfis escopados, que sempre vinculam à própria
  /// Unidade operacional. Não duplica cadastro: cria uma linha em
  /// `outsourced_company_unit_links` apontando para a empresa existente.
  Future<Map<String, dynamic>> linkOutsourcedCompanyToUnit(
    int id, {
    required int actorUserId,
    int? unitId,
  }) async {
    final res = await _dio.post<Map<String, dynamic>>(
      '/api/outsourced-companies/$id/link',
      data: {
        'actor_user_id': actorUserId,
        if (unitId != null) 'unit_id': unitId,
      },
    );
    return res.data ?? {};
  }

  /// "Reativar nesta Unidade" — reaproveita o vínculo existente e o seu
  /// histórico, em vez de criar outro.
  Future<Map<String, dynamic>> activateOutsourcedCompanyUnitLink(
    int id, {
    required int actorUserId,
  }) async {
    final res = await _dio.post<Map<String, dynamic>>(
      '/api/outsourced-companies/$id/unit-link/activate',
      data: {'actor_user_id': actorUserId},
    );
    return res.data ?? {};
  }

  /// "Arquivar nesta Unidade" — alcance de UMA Unidade.
  ///
  /// Não arquiva o cadastro corporativo nem afeta as outras Unidades
  /// vinculadas: `local_status` é deliberadamente separado do `status` de
  /// arquivamento corporativo.
  Future<Map<String, dynamic>> deactivateOutsourcedCompanyUnitLink(
    int id, {
    required int actorUserId,
    String reason = '',
  }) async {
    final res = await _dio.post<Map<String, dynamic>>(
      '/api/outsourced-companies/$id/unit-link/deactivate',
      data: {'actor_user_id': actorUserId, 'reason': reason},
    );
    return res.data ?? {};
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

  /// Empresas terceirizadas/prestadoras arquivadas (soft delete) — aba
  /// "Empresas Arquivadas" do Cadastro de Colaboradores (ADR-0002 §10.4).
  Future<List<Map<String, dynamic>>> getArchivedOutsourcedCompanies({
    required int actorUserId,
  }) async {
    final res = await _dio.get<Map<String, dynamic>>(
      '/api/outsourced-companies/archived',
      queryParameters: {'actor_user_id': actorUserId},
    );
    final raw = (res.data?['outsourced_companies'] as List?) ?? const [];
    return raw.whereType<Map<String, dynamic>>().toList(growable: false);
  }

  Future<Map<String, dynamic>> archiveOutsourcedCompany(
    int id, {
    required int actorUserId,
    String reason = '',
  }) async {
    final res = await _dio.post<Map<String, dynamic>>(
      '/api/outsourced-companies/$id/archive',
      data: {'actor_user_id': actorUserId, 'reason': reason},
    );
    return res.data ?? {};
  }

  /// Desarquiva a empresa terceirizada/prestadora, que volta ao status ativo.
  Future<Map<String, dynamic>> restoreOutsourcedCompany(
    int id, {
    required int actorUserId,
  }) async {
    final res = await _dio.post<Map<String, dynamic>>(
      '/api/outsourced-companies/$id/restore',
      data: {'actor_user_id': actorUserId},
    );
    return res.data ?? {};
  }

  /// Relatório de headcount por empresa terceirizada/prestadora (ativos vs.
  /// arquivados, por tipo de vínculo) — aba "Relatórios" (ADR-0002 §10.4).
  Future<List<Map<String, dynamic>>> getOutsourcedEmployeesSummary({
    required int actorUserId,
  }) async {
    final res = await _dio.get<Map<String, dynamic>>(
      '/api/outsourced-companies/employees-summary',
      queryParameters: {'actor_user_id': actorUserId},
    );
    final raw = (res.data?['outsourced_employees_summary'] as List?) ?? const [];
    return raw.whereType<Map<String, dynamic>>().toList(growable: false);
  }
}
