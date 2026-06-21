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
}
