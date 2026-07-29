/// Contrato de uma empresa terceirizada/prestadora (ADR-0002).
///
/// Uma [OutsourcedCompany] pode ter vários contratos (unidades/períodos
/// diferentes) sem duplicar seu cadastro. Cada contrato pode sobrescrever a
/// responsabilidade padrão de fornecimento de EPI da empresa, com motivo
/// auditável.
class ServiceContract {
  const ServiceContract({
    required this.id,
    required this.outsourcedCompanyId,
    this.unitId,
    this.contractRef = '',
    this.startDate = '',
    this.endDate = '',
    this.epiResponsibilityOverride = '',
    this.overrideReason = '',
    this.status = 'Ativo',
  });

  final int id;
  final int outsourcedCompanyId;

  /// Nulo = contrato vale para todas as unidades.
  final int? unitId;

  final String contractRef;
  final String startDate;
  final String endDate;

  /// Vazio = herda o default de [OutsourcedCompany.epiResponsibility].
  final String epiResponsibilityOverride;
  final String overrideReason;
  final String status;

  bool get hasOverride => epiResponsibilityOverride.trim().isNotEmpty;

  static String _asString(Object? value) => value?.toString() ?? '';

  factory ServiceContract.fromJson(Map<String, dynamic> json) => ServiceContract(
        id: (json['id'] as num).toInt(),
        outsourcedCompanyId: (json['outsourced_company_id'] as num?)?.toInt() ?? 0,
        unitId: (json['unit_id'] as num?)?.toInt(),
        contractRef: _asString(json['contract_ref']),
        startDate: _asString(json['start_date']),
        endDate: _asString(json['end_date']),
        epiResponsibilityOverride: _asString(json['epi_responsibility_override']),
        overrideReason: _asString(json['override_reason']),
        status: _asString(json['status']).isEmpty ? 'Ativo' : _asString(json['status']),
      );

  /// Corpo aceito por POST `/api/outsourced-companies/{id}/service-contracts`.
  Map<String, dynamic> toJson() => {
        if (unitId != null) 'unit_id': unitId,
        'contract_ref': contractRef,
        'start_date': startDate,
        'end_date': endDate,
        'epi_responsibility_override': epiResponsibilityOverride,
        if (hasOverride) 'override_reason': overrideReason,
        'status': status,
      };
}
