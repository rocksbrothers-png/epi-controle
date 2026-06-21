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
}
