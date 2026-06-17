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

  // ── Ordens de Compra (PO) ─────────────────────────────────────────────────

  Future<List<Map<String, dynamic>>> getPurchaseOrders({String? status}) async {
    final params = <String, String>{};
    if (status != null && status.isNotEmpty) params['status'] = status;
    final res = await _dio.get<Map<String, dynamic>>(
      '/api/purchase-orders',
      queryParameters: params.isEmpty ? null : params,
    );
    final items = (res.data?['items'] as List?) ?? [];
    return items.map((e) => (e as Map).cast<String, dynamic>()).toList();
  }

  Future<Map<String, dynamic>> getPurchaseOrder(int id) async {
    final res = await _dio.get<Map<String, dynamic>>('/api/purchase-orders/$id');
    return res.data ?? {};
  }

  Future<int> createPurchaseOrder(Map<String, dynamic> body) async {
    final res = await _dio.post<Map<String, dynamic>>('/api/purchase-orders', data: body);
    return (res.data?['id'] ?? 0) as int;
  }

  Future<void> reviewPurchaseOrder(int id, Map<String, dynamic> body) async {
    await _dio.post('/api/purchase-orders/$id/review', data: body);
  }

  Future<void> approvePurchaseOrder(int id, Map<String, dynamic> body) async {
    await _dio.post('/api/purchase-orders/$id/approve', data: body);
  }

  Future<void> receivePurchaseOrder(int id, Map<String, dynamic> body) async {
    await _dio.post('/api/purchase-orders/$id/receive', data: body);
  }

  Future<void> resubmitPurchaseOrder(int id, Map<String, dynamic> body) async {
    await _dio.post('/api/purchase-orders/$id/resubmit', data: body);
  }
}
