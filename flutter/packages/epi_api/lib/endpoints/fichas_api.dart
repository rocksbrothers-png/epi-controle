import 'package:dio/dio.dart';
import '../models/ficha_period.dart';

class FichasApi {
  const FichasApi(this._dio);
  final Dio _dio;

  Future<List<FichaPeriod>> getFichas({int? employeeId}) async {
    final params = <String, String>{};
    if (employeeId != null) params['employee_id'] = employeeId.toString();
    final res = await _dio.get<Map<String, dynamic>>(
      '/api/fichas',
      queryParameters: params.isEmpty ? null : params,
    );
    final items = (res.data?['items'] as List?) ?? [];
    return items
        .map((e) => FichaPeriod.fromJson(e as Map<String, dynamic>))
        .toList();
  }
}
