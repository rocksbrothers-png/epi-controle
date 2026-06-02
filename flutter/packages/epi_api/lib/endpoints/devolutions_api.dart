import 'package:dio/dio.dart';
import '../models/devolution.dart';

/// Cliente HTTP manual para endpoints de devoluções.
class DevolutionsApi {
  const DevolutionsApi(this._dio);
  final Dio _dio;

  Future<List<Devolution>> getDevolutions({
    int? employeeId,
    int? epiId,
    int? deliveryId,
  }) async {
    final params = <String, String>{};
    if (employeeId != null) params['employee_id'] = employeeId.toString();
    if (epiId != null) params['epi_id'] = epiId.toString();
    if (deliveryId != null) params['delivery_id'] = deliveryId.toString();
    final res = await _dio.get<Map<String, dynamic>>(
      '/api/devolutions',
      queryParameters: params.isEmpty ? null : params,
    );
    final items = (res.data?['items'] as List?) ?? [];
    return items
        .map((e) => Devolution.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  Future<List<OpenDelivery>> getOpenDeliveries({
    required int employeeId,
    required int epiId,
  }) async {
    final res = await _dio.get<Map<String, dynamic>>(
      '/api/devolutions/open-deliveries',
      queryParameters: {
        'employee_id': employeeId.toString(),
        'epi_id': epiId.toString(),
      },
    );
    final items = (res.data?['items'] as List?) ?? [];
    return items
        .map((e) => OpenDelivery.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  Future<int> createDevolution({
    required int deliveryId,
    required String returnedDate,
    required String condition,
    required String destination,
    required String signatureData,
    String? notes,
  }) async {
    final res = await _dio.post<Map<String, dynamic>>(
      '/api/devolutions',
      data: {
        'delivery_id': deliveryId,
        'returned_date': returnedDate,
        'condition': condition,
        'destination': destination,
        'signature_data': signatureData,
        if (notes != null && notes.isNotEmpty) 'notes': notes,
      },
    );
    return (res.data?['id'] ?? 0) as int;
  }
}
