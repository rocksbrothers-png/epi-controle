class Employee {
  const Employee({
    required this.id,
    required this.name,
    this.code,
    this.sector,
    this.role,
    this.unitName,
    this.admissionDate,
    this.schedule,
    this.photoUrl,
    this.isActive = true,
    this.legalEntityId,
    this.legalEntityCnpj,
    this.legalEntityName,
  });

  final int id;
  final String name;
  final String? code;
  final String? sector;
  final String? role;
  final String? unitName;
  final String? admissionDate;
  final String? schedule;
  final String? photoUrl;
  final bool isActive;

  /// CNPJ (LegalEntity) ao qual o colaborador pertence juridicamente.
  ///
  /// É o vínculo do contrato de trabalho: **imutável após a admissão**. A
  /// unidade é apenas a lotação operacional e pode mudar por transferência sem
  /// afetar este vínculo. Alterá-lo exige o processo administrativo auditado
  /// (`LegalEntitiesApi.transferEmployeeLegalEntity`).
  final int? legalEntityId;
  final String? legalEntityCnpj;
  final String? legalEntityName;

  factory Employee.fromJson(Map<String, dynamic> json) => Employee(
        id: (json['id'] as num).toInt(),
        name: json['name'] as String? ?? '',
        code: json['code'] as String?,
        sector: json['sector'] as String?,
        role: json['role'] as String?,
        unitName: json['unit_name'] as String? ?? json['unit'] as String?,
        admissionDate: json['admission_date'] as String?,
        schedule: json['schedule'] as String?,
        photoUrl: json['photo_url'] as String?,
        isActive: (json['is_active'] as bool?) ?? true,
        // Ausentes enquanto o schema Multi-CNPJ não estiver provisionado.
        legalEntityId: (json['legal_entity_id'] as num?)?.toInt(),
        legalEntityCnpj: json['legal_entity_cnpj'] as String?,
        legalEntityName: json['legal_entity_name'] as String?,
      );
}
