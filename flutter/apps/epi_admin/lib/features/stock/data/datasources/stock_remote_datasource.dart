import 'package:epi_api/epi_api.dart';

import '../../../../core/api/api_client.dart';
import '../../domain/repositories/stock_repository.dart';

abstract class StockRemoteDataSource {
  Future<List<Epi>> fetchStockEpis({
    String? name,
    String? section,
    String? manufacturer,
    String? ca,
    String? protection,
  });
  Future<int> currentActorUserId();
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

  /// Sessão, não bootstrap: `ApiClient` mantém o ator do login corrente e o
  /// zera no logout. Ler de `bootstrap.users.first` (como fazia `fetchStock`)
  /// só acertava porque o backend devolve o próprio usuário primeiro.
  @override
  Future<int> currentActorUserId() async => ApiClient.actorUserId;

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
  Future<List<Epi>> fetchStockEpis({
    String? name,
    String? section,
    String? manufacturer,
    String? ca,
    String? protection,
  }) =>
      ApiClient.stock.fetchStockEpis(
        // Ator vem da SESSÃO, não de bootstrap: é aqui, na camada de dados,
        // que o `actor_user_id` é resolvido — o cubit não conhece ApiClient.
        actorUserId: ApiClient.actorUserId,
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
