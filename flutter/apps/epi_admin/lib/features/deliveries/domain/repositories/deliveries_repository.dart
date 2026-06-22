/// Contrato de dados de Entregas (domain). O Cubit depende desta abstração; a
/// orquestração offline (fila em falha de conexão) permanece no cubit.
abstract class DeliveriesRepository {
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
  });
}
