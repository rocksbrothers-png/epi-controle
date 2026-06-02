import 'package:dio/dio.dart';
import '../models/delivery.dart';

/// Cliente HTTP manual para endpoints de entregas.
class DeliveriesApi {
  const DeliveriesApi(this._dio);
  final Dio _dio;

  Future<List<Delivery>> getDeliveries({int? limit}) async {
    final res = await _dio.get<Map<String, dynamic>>(
      '/api/deliveries',
      queryParameters: limit != null ? {'limit': limit} : null,
    );
    final raw = res.data;
    final list =
        (raw?['data'] ?? raw?['deliveries'] ?? raw ?? []) as List;
    return list
        .cast<Map<String, dynamic>>()
        .map(Delivery.fromJson)
        .toList();
  }

  Future<int> createDelivery({
    required int companyId,
    required int employeeId,
    required int epiId,
    required int quantity,
    required String sector,
    required String roleName,
    required String deliveryDate,
    required String nextReplacementDate,
    required int stockItemId,
    required String stockQrCode,
  }) async {
    final res = await _dio.post<Map<String, dynamic>>(
      '/api/deliveries',
      data: {
        'company_id': companyId,
        'employee_id': employeeId,
        'epi_id': epiId,
        'quantity': quantity,
        'sector': sector,
        'role_name': roleName,
        'delivery_date': deliveryDate,
        'next_replacement_date': nextReplacementDate,
        'stock_item_id': stockItemId,
        'stock_qr_code': stockQrCode,
      },
    );
    return (res.data?['id'] ?? 0) as int;
  }
}
