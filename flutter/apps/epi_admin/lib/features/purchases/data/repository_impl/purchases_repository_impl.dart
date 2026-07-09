import 'package:epi_api/epi_api.dart';

import '../../domain/repositories/purchases_repository.dart';
import '../datasources/purchases_remote_datasource.dart';

class PurchasesRepositoryImpl implements PurchasesRepository {
  const PurchasesRepositoryImpl(this._remoteDataSource);

  final PurchasesRemoteDataSource _remoteDataSource;

  @override
  Future<List<PurchaseRequest>> getPurchaseRequests({String? status}) =>
      _remoteDataSource.getPurchaseRequests(status: status);

  @override
  Future<List<PurchaseDemand>> getPurchaseDemands() =>
      _remoteDataSource.getPurchaseDemands();

  @override
  Future<int> createPurchaseRequest({
    required int unitId,
    required List<Map<String, dynamic>> items,
    required String title,
    String notes = '',
  }) =>
      _remoteDataSource.createPurchaseRequest(
        unitId: unitId,
        items: items,
        title: title,
        notes: notes,
      );

  @override
  Future<List<Map<String, dynamic>>> getPurchaseOrders({String? status}) =>
      _remoteDataSource.getPurchaseOrders(status: status);

  @override
  Future<int> createPurchaseOrder(Map<String, dynamic> body) =>
      _remoteDataSource.createPurchaseOrder(body);

  @override
  Future<void> reviewPurchaseOrder(int id, Map<String, dynamic> body) =>
      _remoteDataSource.reviewPurchaseOrder(id, body);

  @override
  Future<void> approvePurchaseOrder(int id, Map<String, dynamic> body) =>
      _remoteDataSource.approvePurchaseOrder(id, body);

  @override
  Future<void> receivePurchaseOrder(int id, Map<String, dynamic> body) =>
      _remoteDataSource.receivePurchaseOrder(id, body);

  @override
  Future<void> resubmitPurchaseOrder(int id, Map<String, dynamic> body) =>
      _remoteDataSource.resubmitPurchaseOrder(id, body);

  // ── Fornecedores e catálogo (Fase F3) ────────────────────────────────────

  @override
  Future<List<Map<String, dynamic>>> getAuthorizedSuppliers() =>
      _remoteDataSource.getAuthorizedSuppliers();

  @override
  Future<Map<String, dynamic>> createAuthorizedSupplier(
          Map<String, dynamic> body) =>
      _remoteDataSource.createAuthorizedSupplier(body);

  @override
  Future<void> updateAuthorizedSupplier(int id, Map<String, dynamic> body) =>
      _remoteDataSource.updateAuthorizedSupplier(id, body);

  @override
  Future<void> updateSupplierProcurement(int id, Map<String, dynamic> body) =>
      _remoteDataSource.updateSupplierProcurement(id, body);

  @override
  Future<List<Map<String, dynamic>>> getSupplierProducts(int supplierId,
          {bool includeInactive = false}) =>
      _remoteDataSource.getSupplierProducts(supplierId,
          includeInactive: includeInactive);

  @override
  Future<Map<String, dynamic>> upsertSupplierProduct(
          int supplierId, Map<String, dynamic> body) =>
      _remoteDataSource.upsertSupplierProduct(supplierId, body);

  @override
  Future<void> deactivateSupplierProduct(int productId) =>
      _remoteDataSource.deactivateSupplierProduct(productId);

  // ── Cotações (RFQ) ────────────────────────────────────────────────────────

  @override
  Future<Map<String, dynamic>> getQuotesForRequest(int prId) =>
      _remoteDataSource.getQuotesForRequest(prId);

  @override
  Future<List<Map<String, dynamic>>> createQuotesForRequest(
          int prId, Map<String, dynamic> body) =>
      _remoteDataSource.createQuotesForRequest(prId, body);

  @override
  Future<void> sendQuote(int quoteId, Map<String, dynamic> body) =>
      _remoteDataSource.sendQuote(quoteId, body);

  @override
  Future<void> sendQuotePortalLink(int quoteId, Map<String, dynamic> body) =>
      _remoteDataSource.sendQuotePortalLink(quoteId, body);

  @override
  Future<void> answerQuote(int quoteId, Map<String, dynamic> body) =>
      _remoteDataSource.answerQuote(quoteId, body);

  @override
  Future<Map<String, dynamic>> selectQuote(
          int quoteId, Map<String, dynamic> body) =>
      _remoteDataSource.selectQuote(quoteId, body);

  // ── PO: envio ao fornecedor, confirmação e acompanhamento ───────────────

  @override
  Future<void> sendPurchaseOrderToSupplier(int id, Map<String, dynamic> body) =>
      _remoteDataSource.sendPurchaseOrderToSupplier(id, body);

  @override
  Future<void> sendPurchaseOrderPortalLink(
          int id, Map<String, dynamic> body) =>
      _remoteDataSource.sendPurchaseOrderPortalLink(id, body);

  @override
  Future<void> registerPurchaseOrderConfirmation(
          int id, Map<String, dynamic> body) =>
      _remoteDataSource.registerPurchaseOrderConfirmation(id, body);

  @override
  Future<Map<String, dynamic>> getPurchaseOrderTracking(int id) =>
      _remoteDataSource.getPurchaseOrderTracking(id);
}
