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

  // ── Fornecedores e catálogo (Fase F1/F3) ─────────────────────────────────

  Future<List<Map<String, dynamic>>> getAuthorizedSuppliers() async {
    final res =
        await _dio.get<Map<String, dynamic>>('/api/authorized-suppliers');
    final items = (res.data?['items'] as List?) ?? [];
    return items.map((e) => (e as Map).cast<String, dynamic>()).toList();
  }

  Future<Map<String, dynamic>> createAuthorizedSupplier(
      Map<String, dynamic> body) async {
    final res = await _dio.post<Map<String, dynamic>>(
        '/api/authorized-suppliers',
        data: body);
    return ((res.data?['item'] as Map?) ?? {}).cast<String, dynamic>();
  }

  Future<void> updateAuthorizedSupplier(
      int id, Map<String, dynamic> body) async {
    await _dio.put('/api/authorized-suppliers/$id', data: body);
  }

  Future<void> updateSupplierProcurement(
      int id, Map<String, dynamic> body) async {
    await _dio.put('/api/authorized-suppliers/$id/procurement', data: body);
  }

  Future<List<Map<String, dynamic>>> getSupplierProducts(int supplierId,
      {bool includeInactive = false}) async {
    final res = await _dio.get<Map<String, dynamic>>(
      '/api/authorized-suppliers/$supplierId/products',
      queryParameters: includeInactive ? {'include_inactive': '1'} : null,
    );
    final items = (res.data?['items'] as List?) ?? [];
    return items.map((e) => (e as Map).cast<String, dynamic>()).toList();
  }

  Future<Map<String, dynamic>> upsertSupplierProduct(
      int supplierId, Map<String, dynamic> body) async {
    final res = await _dio.post<Map<String, dynamic>>(
        '/api/authorized-suppliers/$supplierId/products',
        data: body);
    return ((res.data?['item'] as Map?) ?? {}).cast<String, dynamic>();
  }

  Future<void> deactivateSupplierProduct(int productId) async {
    await _dio.delete('/api/supplier-products/$productId');
  }

  // ── Cotações (RFQ) ────────────────────────────────────────────────────────

  Future<Map<String, dynamic>> getQuotesForRequest(int prId) async {
    final res = await _dio
        .get<Map<String, dynamic>>('/api/purchase-requests/$prId/quotes');
    return res.data ?? {};
  }

  Future<List<Map<String, dynamic>>> createQuotesForRequest(
      int prId, Map<String, dynamic> body) async {
    final res = await _dio.post<Map<String, dynamic>>(
        '/api/purchase-requests/$prId/quotes',
        data: body);
    final items = (res.data?['items'] as List?) ?? [];
    return items.map((e) => (e as Map).cast<String, dynamic>()).toList();
  }

  Future<void> sendQuote(int quoteId, Map<String, dynamic> body) async {
    await _dio.post('/api/quotes/$quoteId/send', data: body);
  }

  Future<void> sendQuotePortalLink(
      int quoteId, Map<String, dynamic> body) async {
    await _dio.post('/api/quotes/$quoteId/portal-link', data: body);
  }

  Future<void> answerQuote(int quoteId, Map<String, dynamic> body) async {
    await _dio.post('/api/quotes/$quoteId/answer', data: body);
  }

  Future<Map<String, dynamic>> selectQuote(
      int quoteId, Map<String, dynamic> body) async {
    final res = await _dio
        .post<Map<String, dynamic>>('/api/quotes/$quoteId/select', data: body);
    return res.data ?? {};
  }

  // ── PO: envio ao fornecedor, confirmação e acompanhamento ───────────────

  Future<void> sendPurchaseOrderToSupplier(
      int id, Map<String, dynamic> body) async {
    await _dio.post('/api/purchase-orders/$id/send', data: body);
  }

  Future<void> sendPurchaseOrderPortalLink(
      int id, Map<String, dynamic> body) async {
    await _dio.post('/api/purchase-orders/$id/portal-link', data: body);
  }

  Future<void> registerPurchaseOrderConfirmation(
      int id, Map<String, dynamic> body) async {
    await _dio.post('/api/purchase-orders/$id/confirmation', data: body);
  }

  Future<Map<String, dynamic>> getPurchaseOrderTracking(int id) async {
    final res = await _dio
        .get<Map<String, dynamic>>('/api/purchase-orders/$id/tracking');
    return ((res.data?['item'] as Map?) ?? {}).cast<String, dynamic>();
  }
}
