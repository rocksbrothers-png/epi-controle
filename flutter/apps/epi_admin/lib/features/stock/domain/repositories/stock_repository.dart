import 'package:epi_api/epi_api.dart';

/// Snapshot de estoque derivado do bootstrap: EPIs + contexto do ator/escopo.
class StockSnapshot {
  const StockSnapshot({
    required this.epis,
    required this.companyId,
    required this.unitId,
    required this.actorUserId,
  });

  final List<Epi> epis;
  final int companyId;
  final int unitId;
  final int actorUserId;
}

/// Contrato de dados de Estoque (domain). O Cubit depende desta abstração.
/// A orquestração offline (fila/conectividade/notificação) permanece no cubit.
abstract class StockRepository {
  /// Fonte ÚNICA de estoque operacional: `/api/stock/epis`.
  /// Substitui `fetchStock()`, que lia `bootstrap.epis`.
  /// O `actor_user_id` é resolvido na camada de dados a partir da sessão —
  /// o cubit não conhece `ApiClient` nem o bootstrap.
  Future<List<Epi>> fetchStockEpis({
    String? name,
    String? section,
    String? manufacturer,
    String? ca,
    String? protection,
  });

  /// Ator da SESSÃO, resolvido na camada de dados.
  ///
  /// Antes o cubit tirava o ator do `bootstrap` junto com a lista de EPIs. Sem
  /// esse bootstrap, o ator precisa vir de algum lugar: as consultas de itens
  /// disponíveis/bloqueados e o movimento ainda o exigem, e a operação
  /// enfileirada offline é carimbada com quem a originou — quem replica a fila
  /// depois pode ser outro usuário logado no mesmo aparelho.
  ///
  /// Fica aqui, e não em `ApiClient` lido pelo cubit, para o cubit continuar
  /// dependendo só desta abstração.
  Future<int> currentActorUserId();

  @Deprecated('Lê bootstrap.epis (saldo corporativo, envelhece na sessão). '
      'Use fetchStockEpis. Remoção na fatia 1.1E.')
  Future<StockSnapshot> fetchStock();

  /// QRs disponíveis de um EPI, em ordem FEFO definida pelo backend.
  /// Sem `companyId`/`unitId`: o escopo é derivado do ator no servidor.
  Future<List<StockItem>> fetchAvailableItems({
    required int actorUserId,
    required int epiId,
  });

  /// Itens bloqueados no escopo do ator, com as chaves de status válidas.
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
