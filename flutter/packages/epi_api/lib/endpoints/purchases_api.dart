import 'package:dio/dio.dart';
import '../models/purchase_request.dart';

/// Cliente HTTP manual para endpoints de compras.
class PurchasesApi {
  const PurchasesApi(this._dio);
  final Dio _dio;

  Future<List<PurchaseRequest>> getPurchaseRequests({String? status}) async {
    final params = <String, String>{};
    if (status != null && status.isNotEmpty) params['status'] = status;
    final res = await _dio.get<Map<String, dynamic>>(
      '/api/purchase-requests',
      queryParameters: params.isEmpty ? null : params,
    );
    final items = (res.data?['items'] as List?) ?? [];
    return items
        .map((e) => PurchaseRequest.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  Future<int> createPurchaseRequest({
    required int unitId,
    required List<Map<String, dynamic>> items,
    required String title,
    String notes = '',
  }) async {
    final res = await _dio.post<Map<String, dynamic>>(
      '/api/purchase-requests',
      data: {
        'unit_id': unitId,
        'items': items,
        'title': title,
        'notes': notes,
      },
    );
    return (res.data?['id'] ?? 0) as int;
  }

  Future<List<PurchaseDemand>> getPurchaseDemands() async {
    final res = await _dio.get<Map<String, dynamic>>('/api/purchase-demands');
    final items = (res.data?['items'] as List?) ?? [];
    return items
        .map((e) => PurchaseDemand.fromJson(e as Map<String, dynamic>))
        .toList();
  }
}
