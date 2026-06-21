import '../../domain/repositories/stock_repository.dart';
import '../datasources/stock_remote_datasource.dart';

class StockRepositoryImpl implements StockRepository {
  const StockRepositoryImpl(this._remoteDataSource);

  final StockRemoteDataSource _remoteDataSource;

  @override
  Future<StockSnapshot> fetchStock() => _remoteDataSource.fetchStock();

  @override
  Future<void> recordMovement({
    required int actorUserId,
    required int companyId,
    required int unitId,
    required int epiId,
    required String movementType,
    required int quantity,
  }) =>
      _remoteDataSource.recordMovement(
        actorUserId: actorUserId,
        companyId: companyId,
        unitId: unitId,
        epiId: epiId,
        movementType: movementType,
        quantity: quantity,
      );
}
