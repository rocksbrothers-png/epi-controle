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
}
