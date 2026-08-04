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
