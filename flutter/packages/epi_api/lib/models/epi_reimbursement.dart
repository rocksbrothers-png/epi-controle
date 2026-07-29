/// Registro de ressarcimento de EPI a empresa terceirizada (ADR-0002).
///
/// Registro de apoio para conferência manual — NUNCA cobrança automática.
/// Uma entrega tem no máximo um registro (o backend garante a unicidade).
class EpiReimbursement {
  const EpiReimbursement({
    required this.id,
    required this.deliveryId,
    required this.outsourcedCompanyId,
    this.unitCost = 0,
    this.quantity = 1,
    this.totalValue = 0,
    this.reason = '',
    this.contractRef = '',
    this.status = 'Não Aplicável',
  });

  final int id;
  final int deliveryId;
  final int outsourcedCompanyId;
  final double unitCost;
  final int quantity;
  final double totalValue;
  final String reason;
  final String contractRef;

  /// Um dos 8 estados: `Não Aplicável`, `Pendente de Análise`, `Passível de
  /// Ressarcimento`, `Apta para Cobrança`, `Incluída em Relatório`,
  /// `Ressarcida`, `Contestada`, `Dispensada`.
  final String status;

  static double _asDouble(Object? value) =>
      value is num ? value.toDouble() : double.tryParse('$value') ?? 0;

  factory EpiReimbursement.fromJson(Map<String, dynamic> json) => EpiReimbursement(
        id: (json['id'] as num).toInt(),
        deliveryId: (json['delivery_id'] as num?)?.toInt() ?? 0,
        outsourcedCompanyId: (json['outsourced_company_id'] as num?)?.toInt() ?? 0,
        unitCost: _asDouble(json['unit_cost']),
        quantity: (json['quantity'] as num?)?.toInt() ?? 1,
        totalValue: _asDouble(json['total_value']),
        reason: json['reason']?.toString() ?? '',
        contractRef: json['contract_ref']?.toString() ?? '',
        status: (json['status']?.toString().isEmpty ?? true)
            ? 'Não Aplicável'
            : json['status'].toString(),
      );
}
