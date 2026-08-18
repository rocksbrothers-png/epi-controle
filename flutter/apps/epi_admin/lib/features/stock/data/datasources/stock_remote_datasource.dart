import 'package:epi_api/epi_api.dart';

import '../../../../core/api/api_client.dart';
import '../../domain/repositories/stock_repository.dart';

abstract class StockRemoteDataSource {
  Future<StockSnapshot> fetchStock();
  Future<List<StockItem>> fetchAvailableItems({
    required int actorUserId,
    required int epiId,
  });
  Future<BlockedStockItems> fetchBlockedItems({required int actorUserId});
  Future<void> recordMovement({
    required int actorUserId,
    required int companyId,
    required int unitId,
    required int epiId,
    required String movementType,
    required int quantity,
  });
}

/// Implementação sobre `epi_api`. A lista de estoque vem do bootstrap (mesma
/// fonte/escopo multi-tenant do backend); o movimento usa `StockApi`.
class ApiStockRemoteDataSource implements StockRemoteDataSource {
  const ApiStockRemoteDataSource();

  @override
  Future<StockSnapshot> fetchStock() async {
    final bootstrap = await ApiClient.auth.bootstrap();
    final epis = bootstrap.epis.map(Epi.fromJson).toList();
    final companyId = bootstrap.units.isNotEmpty
        ? (bootstrap.units.first['company_id'] as int? ?? 0)
        : 0;
    final unitId = bootstrap.units.isNotEmpty
        ? (bootstrap.units.first['id'] as int? ?? 0)
        : 0;
    final actorUserId = bootstrap.users.isNotEmpty
        ? (bootstrap.users.first['id'] as int? ?? 0)
        : 0;
    return StockSnapshot(
      epis: epis,
      companyId: companyId,
      unitId: unitId,
      actorUserId: actorUserId,
    );
  }

  @override
  Future<List<StockItem>> fetchAvailableItems({
    required int actorUserId,
    required int epiId,
  }) =>
      ApiClient.stock.fetchAvailableItems(
        actorUserId: actorUserId,
        epiId: epiId,
      );

  @override
  Future<BlockedStockItems> fetchBlockedItems({required int actorUserId}) =>
      ApiClient.stock.fetchBlockedItems(actorUserId: actorUserId);

  @override
  Future<void> recordMovement({
    required int actorUserId,
    required int companyId,
    required int unitId,
    required int epiId,
    required String movementType,
    required int quantity,
  }) =>
      ApiClient.stock.recordMovement(
        actorUserId: actorUserId,
        companyId: companyId,
        unitId: unitId,
        epiId: epiId,
        movementType: movementType,
        quantity: quantity,
      );
}
