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
  Future<StockSnapshot> fetchStock();
  Future<void> recordMovement({
    required int actorUserId,
    required int companyId,
    required int unitId,
    required int epiId,
    required String movementType,
    required int quantity,
  });
}
