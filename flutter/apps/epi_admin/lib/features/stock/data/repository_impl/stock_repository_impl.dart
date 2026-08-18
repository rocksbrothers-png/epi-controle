import 'package:epi_api/epi_api.dart';

import '../../domain/repositories/stock_repository.dart';
import '../datasources/stock_remote_datasource.dart';

class StockRepositoryImpl implements StockRepository {
  const StockRepositoryImpl(this._remoteDataSource);

  final StockRemoteDataSource _remoteDataSource;

  @override
  Future<int> currentActorUserId() => _remoteDataSource.currentActorUserId();

  @override
  Future<StockSnapshot> fetchStock() => _remoteDataSource.fetchStock();

  @override
  Future<List<Epi>> fetchStockEpis({
    String? name,
    String? section,
    String? manufacturer,
    String? ca,
    String? protection,
  }) =>
      _remoteDataSource.fetchStockEpis(
        name: name,
        section: section,
        manufacturer: manufacturer,
        ca: ca,
        protection: protection,
      );

  @override
  Future<List<StockItem>> fetchAvailableItems({
    required int actorUserId,
    required int epiId,
  }) =>
      _remoteDataSource.fetchAvailableItems(
        actorUserId: actorUserId,
        epiId: epiId,
      );

  @override
  Future<BlockedStockItems> fetchBlockedItems({required int actorUserId}) =>
      _remoteDataSource.fetchBlockedItems(actorUserId: actorUserId);

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
