import '../../../../core/api/api_client.dart';

abstract class DeliveriesRemoteDataSource {
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
    String idempotencyKey = '',
  });
}

class ApiDeliveriesRemoteDataSource implements DeliveriesRemoteDataSource {
  const ApiDeliveriesRemoteDataSource();

  @override
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
    String idempotencyKey = '',
  }) =>
      ApiClient.deliveries.createDelivery(
        companyId: companyId,
        employeeId: employeeId,
        epiId: epiId,
        quantity: quantity,
        sector: sector,
        roleName: roleName,
        deliveryDate: deliveryDate,
        nextReplacementDate: nextReplacementDate,
        stockItemId: stockItemId,
        stockQrCode: stockQrCode,
        idempotencyKey: idempotencyKey,
      );
}
