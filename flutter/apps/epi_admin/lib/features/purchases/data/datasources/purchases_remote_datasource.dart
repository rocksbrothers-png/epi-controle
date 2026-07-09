import 'package:epi_api/epi_api.dart';

import '../../../../core/api/api_client.dart';

abstract class PurchasesRemoteDataSource {
  Future<List<PurchaseRequest>> getPurchaseRequests({String? status});
  Future<List<PurchaseDemand>> getPurchaseDemands();
  Future<int> createPurchaseRequest({
    required int unitId,
    required List<Map<String, dynamic>> items,
    required String title,
    String notes,
  });
  Future<List<Map<String, dynamic>>> getPurchaseOrders({String? status});
  Future<int> createPurchaseOrder(Map<String, dynamic> body);
  Future<void> reviewPurchaseOrder(int id, Map<String, dynamic> body);
  Future<void> approvePurchaseOrder(int id, Map<String, dynamic> body);
  Future<void> receivePurchaseOrder(int id, Map<String, dynamic> body);
  Future<void> resubmitPurchaseOrder(int id, Map<String, dynamic> body);

  // Fornecedores e catálogo (Fase F3)
  Future<List<Map<String, dynamic>>> getAuthorizedSuppliers();
  Future<Map<String, dynamic>> createAuthorizedSupplier(
      Map<String, dynamic> body);
  Future<void> updateAuthorizedSupplier(int id, Map<String, dynamic> body);
  Future<void> updateSupplierProcurement(int id, Map<String, dynamic> body);
  Future<List<Map<String, dynamic>>> getSupplierProducts(int supplierId,
      {bool includeInactive});
  Future<Map<String, dynamic>> upsertSupplierProduct(
      int supplierId, Map<String, dynamic> body);
  Future<void> deactivateSupplierProduct(int productId);

  // Cotações (RFQ)
  Future<Map<String, dynamic>> getQuotesForRequest(int prId);
  Future<List<Map<String, dynamic>>> createQuotesForRequest(
      int prId, Map<String, dynamic> body);
  Future<void> sendQuote(int quoteId, Map<String, dynamic> body);
  Future<void> sendQuotePortalLink(int quoteId, Map<String, dynamic> body);
  Future<void> answerQuote(int quoteId, Map<String, dynamic> body);
  Future<Map<String, dynamic>> selectQuote(
      int quoteId, Map<String, dynamic> body);

  // PO: envio ao fornecedor, confirmação e acompanhamento
  Future<void> sendPurchaseOrderToSupplier(int id, Map<String, dynamic> body);
  Future<void> sendPurchaseOrderPortalLink(int id, Map<String, dynamic> body);
  Future<void> registerPurchaseOrderConfirmation(
      int id, Map<String, dynamic> body);
  Future<Map<String, dynamic>> getPurchaseOrderTracking(int id);
}

/// Implementação sobre `epi_api`. Injeta `actor_user_id` nas ações de PO
/// (mesma semântica do antigo `_withActor` do cubit).
class ApiPurchasesRemoteDataSource implements PurchasesRemoteDataSource {
  const ApiPurchasesRemoteDataSource();

  Map<String, dynamic> _withActor(Map<String, dynamic> body) =>
      {...body, 'actor_user_id': ApiClient.actorUserId};

  @override
  Future<List<PurchaseRequest>> getPurchaseRequests({String? status}) =>
      ApiClient.purchases.getPurchaseRequests(status: status);

  @override
  Future<List<PurchaseDemand>> getPurchaseDemands() =>
      ApiClient.purchases.getPurchaseDemands();

  @override
  Future<int> createPurchaseRequest({
    required int unitId,
    required List<Map<String, dynamic>> items,
    required String title,
    String notes = '',
  }) =>
      ApiClient.purchases.createPurchaseRequest(
        unitId: unitId,
        items: items,
        title: title,
        notes: notes,
      );

  @override
  Future<List<Map<String, dynamic>>> getPurchaseOrders({String? status}) =>
      ApiClient.purchases.getPurchaseOrders(status: status);

  @override
  Future<int> createPurchaseOrder(Map<String, dynamic> body) =>
      ApiClient.purchases.createPurchaseOrder(_withActor(body));

  @override
  Future<void> reviewPurchaseOrder(int id, Map<String, dynamic> body) =>
      ApiClient.purchases.reviewPurchaseOrder(id, _withActor(body));

  @override
  Future<void> approvePurchaseOrder(int id, Map<String, dynamic> body) =>
      ApiClient.purchases.approvePurchaseOrder(id, _withActor(body));

  @override
  Future<void> receivePurchaseOrder(int id, Map<String, dynamic> body) =>
      ApiClient.purchases.receivePurchaseOrder(id, _withActor(body));

  @override
  Future<void> resubmitPurchaseOrder(int id, Map<String, dynamic> body) =>
      ApiClient.purchases.resubmitPurchaseOrder(id, _withActor(body));

  // ── Fornecedores e catálogo (Fase F3) ────────────────────────────────────

  @override
  Future<List<Map<String, dynamic>>> getAuthorizedSuppliers() =>
      ApiClient.purchases.getAuthorizedSuppliers();

  @override
  Future<Map<String, dynamic>> createAuthorizedSupplier(
          Map<String, dynamic> body) =>
      ApiClient.purchases.createAuthorizedSupplier(_withActor(body));

  @override
  Future<void> updateAuthorizedSupplier(int id, Map<String, dynamic> body) =>
      ApiClient.purchases.updateAuthorizedSupplier(id, _withActor(body));

  @override
  Future<void> updateSupplierProcurement(int id, Map<String, dynamic> body) =>
      ApiClient.purchases.updateSupplierProcurement(id, _withActor(body));

  @override
  Future<List<Map<String, dynamic>>> getSupplierProducts(int supplierId,
          {bool includeInactive = false}) =>
      ApiClient.purchases
          .getSupplierProducts(supplierId, includeInactive: includeInactive);

  @override
  Future<Map<String, dynamic>> upsertSupplierProduct(
          int supplierId, Map<String, dynamic> body) =>
      ApiClient.purchases.upsertSupplierProduct(supplierId, _withActor(body));

  @override
  Future<void> deactivateSupplierProduct(int productId) =>
      ApiClient.purchases.deactivateSupplierProduct(productId);

  // ── Cotações (RFQ) ────────────────────────────────────────────────────────

  @override
  Future<Map<String, dynamic>> getQuotesForRequest(int prId) =>
      ApiClient.purchases.getQuotesForRequest(prId);

  @override
  Future<List<Map<String, dynamic>>> createQuotesForRequest(
          int prId, Map<String, dynamic> body) =>
      ApiClient.purchases.createQuotesForRequest(prId, _withActor(body));

  @override
  Future<void> sendQuote(int quoteId, Map<String, dynamic> body) =>
      ApiClient.purchases.sendQuote(quoteId, _withActor(body));

  @override
  Future<void> sendQuotePortalLink(int quoteId, Map<String, dynamic> body) =>
      ApiClient.purchases.sendQuotePortalLink(quoteId, _withActor(body));

  @override
  Future<void> answerQuote(int quoteId, Map<String, dynamic> body) =>
      ApiClient.purchases.answerQuote(quoteId, _withActor(body));

  @override
  Future<Map<String, dynamic>> selectQuote(
          int quoteId, Map<String, dynamic> body) =>
      ApiClient.purchases.selectQuote(quoteId, _withActor(body));

  // ── PO: envio ao fornecedor, confirmação e acompanhamento ───────────────

  @override
  Future<void> sendPurchaseOrderToSupplier(int id, Map<String, dynamic> body) =>
      ApiClient.purchases.sendPurchaseOrderToSupplier(id, _withActor(body));

  @override
  Future<void> sendPurchaseOrderPortalLink(
          int id, Map<String, dynamic> body) =>
      ApiClient.purchases.sendPurchaseOrderPortalLink(id, _withActor(body));

  @override
  Future<void> registerPurchaseOrderConfirmation(
          int id, Map<String, dynamic> body) =>
      ApiClient.purchases
          .registerPurchaseOrderConfirmation(id, _withActor(body));

  @override
  Future<Map<String, dynamic>> getPurchaseOrderTracking(int id) =>
      ApiClient.purchases.getPurchaseOrderTracking(id);
}
