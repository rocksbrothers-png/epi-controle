import 'package:dio/dio.dart';

/// Cliente REST de Funcionários (CRUD). Espelha [UsersApi].
/// Endpoints: GET/POST /api/employees · GET/PUT/DELETE /api/employees/{id}.
class EmployeesApi {
  const EmployeesApi(this._dio);
  final Dio _dio;

  Future<Map<String, dynamic>> getEmployee(int id, {required int actorUserId}) async {
    final res = await _dio.get<Map<String, dynamic>>(
      '/api/employees/$id',
      queryParameters: {'actor_user_id': actorUserId},
    );
    return (res.data?['employee'] as Map?)?.cast<String, dynamic>() ?? {};
  }

  /// Listagem de colaboradores do tenant.
  ///
  /// Esta rota — e **não** o payload de bootstrap — é a que carrega
  /// `local_unit_link_status` e `is_linked_to_actor_unit` (ADR-0002 §13). O
  /// bootstrap chama `fetch_employees` sem contexto de Unidade, então lá o
  /// estado do vínculo vem `null` para todo mundo: uma tela que precise do
  /// vínculo e leia do bootstrap não falha, apenas nunca oferece as ações.
  ///
  /// [unitId] é uma **sugestão** de contexto, não uma escolha. Para perfis
  /// escopados por Unidade o backend a descarta e usa a Unidade do ator
  /// (`resolve_actor_unit_context`); quem monta o request não decide o próprio
  /// escopo. Omitir é o normal: Administrador Local e Gestor de EPI recebem a
  /// própria Unidade de qualquer forma.
  Future<List<Map<String, dynamic>>> getEmployees({
    required int actorUserId,
    int? unitId,
  }) async {
    final res = await _dio.get<Map<String, dynamic>>(
      '/api/employees',
      queryParameters: {
        'actor_user_id': actorUserId,
        if (unitId != null) 'unit_id': unitId,
      },
    );
    final items = res.data?['employees'];
    if (items is List) {
      return items.whereType<Map<String, dynamic>>().toList();
    }
    return const [];
  }

  Future<Map<String, dynamic>> createEmployee(Map<String, dynamic> body) async {
    final res = await _dio.post<Map<String, dynamic>>('/api/employees', data: body);
    return res.data ?? {};
  }

  Future<Map<String, dynamic>> updateEmployee(int id, Map<String, dynamic> body) async {
    final res = await _dio.put<Map<String, dynamic>>('/api/employees/$id', data: body);
    return res.data ?? {};
  }

  /// Arquiva o colaborador (soft delete): desativado para novas operações,
  /// histórico preservado pelo período mínimo de retenção (>= 5 anos).
  Future<Map<String, dynamic>> archiveEmployee(
    int id, {
    required int actorUserId,
    String reason = '',
  }) async {
    final res = await _dio.post<Map<String, dynamic>>(
      '/api/employees/$id/archive',
      data: {'actor_user_id': actorUserId, 'reason': reason},
    );
    return res.data ?? {};
  }

  /// Desarquiva o colaborador, que volta ao status ativo.
  Future<Map<String, dynamic>> restoreEmployee(int id, {required int actorUserId}) async {
    final res = await _dio.post<Map<String, dynamic>>(
      '/api/employees/$id/restore',
      data: {'actor_user_id': actorUserId},
    );
    return res.data ?? {};
  }

  /// Colaboradores arquivados do tenant, com motivo e retenção restante.
  ///
  /// [outsourcedOnly] filtra para só terceirizado/prestador (nunca CLT) —
  /// aba "Colaboradores Arquivados" do Cadastro de Colaboradores
  /// (ADR-0002 §10.4). Mesma rota do arquivamento geral, sem rota nova.
  Future<List<Map<String, dynamic>>> getArchivedEmployees({
    required int actorUserId,
    bool outsourcedOnly = false,
  }) async {
    final res = await _dio.get<Map<String, dynamic>>(
      '/api/employees/archived',
      queryParameters: {
        'actor_user_id': actorUserId,
        if (outsourcedOnly) 'outsourced_only': '1',
      },
    );
    final items = res.data?['employees'];
    if (items is List) {
      return items.whereType<Map<String, dynamic>>().toList();
    }
    return const [];
  }

  /// Cadastro de Colaboradores simplificado (ADR-0002 §10.2) — só
  /// terceirizado/prestador, nunca CLT (o backend recusa). Escreve na mesma
  /// tabela `employees`, sem estrutura paralela.
  Future<Map<String, dynamic>> createEmployeeOutsourcedSimplified(
    Map<String, dynamic> body,
  ) async {
    final res = await _dio.post<Map<String, dynamic>>(
      '/api/employees/outsourced-simplified',
      data: body,
    );
    return res.data ?? {};
  }

  Future<Map<String, dynamic>> updateEmployeeOutsourcedSimplified(
    int id,
    Map<String, dynamic> body,
  ) async {
    final res = await _dio.put<Map<String, dynamic>>(
      '/api/employees/outsourced-simplified/$id',
      data: body,
    );
    return res.data ?? {};
  }

  /// O backend não remove mais fisicamente: DELETE arquiva o colaborador
  /// preservando o histórico (política de retenção). Prefira [archiveEmployee].
  Future<void> deleteEmployee(int id, {required int actorUserId}) async {
    await _dio.delete(
      '/api/employees/$id',
      queryParameters: {'actor_user_id': actorUserId},
    );
  }

  // ── Vínculo local por Unidade (ADR-0002 §13) ────────────────────────────
  //
  // As três rotas abaixo operam sobre `employee_unit_links`, uma tabela
  // PARALELA: elas nunca tocam `employees.unit_id`. Vincular a Unidade B não
  // move ninguém da Unidade A — é isso que permite que duas Unidades usem o
  // mesmo terceirizado sem duplicar a pessoa no cadastro.
  //
  // Nenhuma delas concede permissão. Elas ampliam apenas SOBRE QUEM um perfil
  // pode consultar; a permissão funcional continua sendo exigida antes, no
  // backend, e o vínculo local não abre update, transferência, arquivamento
  // global, exclusão, purga, finalização de ficha, portal ou entrega de EPI.

  /// Vincula o colaborador a uma Unidade ("Vincular à minha unidade").
  ///
  /// Só vale para mão de obra contratada — o backend recusa mão de obra
  /// própria (`ensure_employee_is_linkable_to_units`) com 400.
  ///
  /// [unitId] é ignorado para perfis escopados por Unidade, que sempre
  /// vinculam à própria Unidade operacional. Passá-lo não é uma forma de
  /// escolher: é uma sugestão que o backend aceita apenas de quem não é
  /// escopado.
  Future<Map<String, dynamic>> linkEmployeeToUnit(
    int id, {
    required int actorUserId,
    int? unitId,
  }) async {
    final res = await _dio.post<Map<String, dynamic>>(
      '/api/employees/$id/link',
      data: {
        'actor_user_id': actorUserId,
        if (unitId != null) 'unit_id': unitId,
      },
    );
    return res.data ?? {};
  }

  /// Reativa o vínculo local arquivado ("Reativar nesta Unidade").
  ///
  /// Devolve `{'ok': true, 'local_status': 'active'}`.
  Future<Map<String, dynamic>> activateEmployeeUnitLink(
    int id, {
    required int actorUserId,
  }) async {
    final res = await _dio.post<Map<String, dynamic>>(
      '/api/employees/$id/unit-link/activate',
      data: {'actor_user_id': actorUserId},
    );
    return res.data ?? {};
  }

  /// Arquiva o vínculo local ("Arquivar nesta Unidade").
  ///
  /// **Arquivar não é apagar.** A linha permanece com [reason], ator e
  /// carimbo de tempo — e continua sendo o que bloqueia a exclusão definitiva
  /// enquanto estiver ativa em alguma Unidade. Não existe rota para remover o
  /// vínculo: quem quer excluir o colaborador arquiva o vínculo em cada
  /// Unidade, deliberadamente, deixando rastro — em vez de sumir com a linha
  /// para destravar um botão.
  ///
  /// Devolve `{'ok': true, 'local_status': 'inactive'}`.
  Future<Map<String, dynamic>> deactivateEmployeeUnitLink(
    int id, {
    required int actorUserId,
    String reason = '',
  }) async {
    final res = await _dio.post<Map<String, dynamic>>(
      '/api/employees/$id/unit-link/deactivate',
      data: {'actor_user_id': actorUserId, 'reason': reason},
    );
    return res.data ?? {};
  }

  /// Resumo de exclusão do colaborador, incluindo o aviso antecipado
  /// `deletion_readiness` (ADR-0002 §13.5): elegibilidade, motivos de bloqueio
  /// e as Unidades com vínculo ativo que impedem a exclusão definitiva.
  ///
  /// Mostra TODOS os impedimentos de uma vez — retenção, bloqueio legal e
  /// vínculos ativos — em vez de um por vez, que obrigaria o operador a
  /// resolver, tentar de novo e descobrir o seguinte.
  Future<Map<String, dynamic>> getEmployeeDeletionSummary(
    int id, {
    required int actorUserId,
  }) async {
    final res = await _dio.get<Map<String, dynamic>>(
      '/api/employees/$id/deletion-summary',
      queryParameters: {'actor_user_id': actorUserId},
    );
    return res.data ?? {};
  }

  /// Movimentação de unidade operacional (transferência), temporária ou
  /// definitiva. Só o Administrador Local (`employees:transfer`) executa —
  /// o backend valida que origem e destino pertencem à mesma empresa e que
  /// o destino é diferente da unidade atual.
  Future<Map<String, dynamic>> createUnitMovement({
    required int actorUserId,
    required int employeeId,
    required int targetUnitId,
    required String movementType,
    required String startDate,
    String endDate = '',
    String notes = '',
  }) async {
    final res = await _dio.post<Map<String, dynamic>>(
      '/api/employee-unit-movements',
      data: {
        'actor_user_id': actorUserId,
        'employee_id': employeeId,
        'target_unit_id': targetUnitId,
        'movement_type': movementType,
        'start_date': startDate,
        if (endDate.isNotEmpty) 'end_date': endDate,
        if (notes.isNotEmpty) 'notes': notes,
      },
    );
    return res.data ?? {};
  }
}
