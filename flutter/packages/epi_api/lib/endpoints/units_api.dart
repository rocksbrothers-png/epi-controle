import 'package:dio/dio.dart';

import '../models/selectable_units.dart';

class UnitsApi {
  const UnitsApi(this._dio);
  final Dio _dio;

  Future<Map<String, dynamic>> createUnit(Map<String, dynamic> body) async {
    final res = await _dio.post<Map<String, dynamic>>('/api/units', data: body);
    return res.data ?? {};
  }

  Future<Map<String, dynamic>> updateUnit(int id, Map<String, dynamic> body) async {
    final res = await _dio.put<Map<String, dynamic>>('/api/units/$id', data: body);
    return res.data ?? {};
  }

  /// Arquiva a unidade (soft delete): bloqueia novas operações e preserva todo
  /// o histórico pelo período mínimo de retenção configurado (>= 5 anos).
  Future<Map<String, dynamic>> archiveUnit(
    int id, {
    required int actorUserId,
    String reason = '',
  }) async {
    final res = await _dio.post<Map<String, dynamic>>(
      '/api/units/$id/archive',
      data: {'actor_user_id': actorUserId, 'reason': reason},
    );
    return res.data ?? {};
  }

  /// Restaura uma unidade arquivada, reativando as operações.
  Future<Map<String, dynamic>> restoreUnit(int id, {required int actorUserId}) async {
    final res = await _dio.post<Map<String, dynamic>>(
      '/api/units/$id/restore',
      data: {'actor_user_id': actorUserId},
    );
    return res.data ?? {};
  }

  /// Unidades arquivadas do tenant, com motivo, responsável e retenção restante.
  Future<List<Map<String, dynamic>>> getArchivedUnits({required int actorUserId}) async {
    final res = await _dio.get<Map<String, dynamic>>(
      '/api/units/archived',
      queryParameters: {'actor_user_id': actorUserId},
    );
    final units = res.data?['units'];
    if (units is List) {
      return units.whereType<Map<String, dynamic>>().toList();
    }
    return const [];
  }

  /// O backend não remove mais fisicamente: DELETE arquiva a unidade
  /// preservando o histórico (política de retenção). Prefira [archiveUnit].
  Future<void> deleteUnit(int id, {required int actorUserId}) async {
    await _dio.delete(
      '/api/units/$id',
      queryParameters: {'actor_user_id': actorUserId},
    );
  }

  /// As Unidades que o ator pode ESCOLHER, já recortadas pelo servidor.
  ///
  /// Substitui `bootstrap.units` em todo seletor. Aquela lista é recortada por
  /// TENANT e mais nada: um perfil travado recebe dela a empresa inteira, e
  /// cada tela ficava encarregada de estreitá-la — autorização reconstruída no
  /// cliente.
  ///
  /// Aqui o recorte é do backend, com a MESMA regra de Compras: perfil travado
  /// só a própria; Comprador/Aprovador só a carteira, e **carteira vazia
  /// devolve lista vazia, nunca a empresa**; demais perfis, todas do tenant.
  ///
  /// Não recebe `unit_id` nem `company_id`: o escopo vem do ator. Mandar
  /// qualquer um dos dois daqui moveria a decisão para a tela.
  /// GET /api/units/selectable.
  Future<SelectableUnits> getSelectableUnits({required int actorUserId}) async {
    final res = await _dio.get<Map<String, dynamic>>(
      '/api/units/selectable',
      queryParameters: {'actor_user_id': actorUserId},
    );
    return SelectableUnits.fromJson(res.data ?? const {});
  }
}
