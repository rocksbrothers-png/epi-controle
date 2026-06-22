import '../../domain/repositories/deliveries_repository.dart';
import '../datasources/deliveries_remote_datasource.dart';

class DeliveriesRepositoryImpl implements DeliveriesRepository {
  const DeliveriesRepositoryImpl(this._remoteDataSource);

  final DeliveriesRemoteDataSource _remoteDataSource;

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
  }) =>
      _remoteDataSource.createDelivery(
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
      );
}
