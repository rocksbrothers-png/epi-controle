import 'package:epi_api/epi_api.dart';

/// Contrato de dados de Compras (domain). O Cubit depende desta abstração.
/// A injeção do `actor_user_id` nas Ordens de Compra fica no datasource.
abstract class PurchasesRepository {
  Future<List<PurchaseRequest>> getPurchaseRequests({String? status});
  Future<List<PurchaseDemand>> getPurchaseDemands();
  Future<int> createPurchaseRequest({
    required int unitId,
    required List<Map<String, dynamic>> items,
    required String title,
    String notes,
  });

  // Ordens de Compra (PO)
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
