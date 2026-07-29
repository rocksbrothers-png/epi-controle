/// Sugestão de migração Simplificado → Padrão (ADR-0002).
///
/// Puramente informativo — nunca bloqueia o uso normal da empresa
/// terceirizada ou dos colaboradores vinculados a ela.
class MigrationSuggestion {
  const MigrationSuggestion({
    required this.outsourcedCompanyId,
    required this.legalName,
    required this.registrationMode,
    required this.ageDays,
    required this.thresholdDays,
  });

  final int outsourcedCompanyId;
  final String legalName;
  final String registrationMode;
  final int ageDays;
  final int thresholdDays;

  factory MigrationSuggestion.fromJson(Map<String, dynamic> json) => MigrationSuggestion(
        outsourcedCompanyId: (json['outsourced_company_id'] as num?)?.toInt() ?? 0,
        legalName: json['legal_name']?.toString() ?? '',
        registrationMode: json['registration_mode']?.toString() ?? 'simplified',
        ageDays: (json['age_days'] as num?)?.toInt() ?? 0,
        thresholdDays: (json['threshold_days'] as num?)?.toInt() ?? 0,
      );
}
