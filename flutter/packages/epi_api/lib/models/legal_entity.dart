/// Pessoa jurídica (CNPJ) vinculada à empresa — arquitetura Multi-CNPJ / JV.
///
/// Uma empresa (tenant) pode possuir um ou vários CNPJs: matriz, filiais,
/// subsidiárias, SPEs e empresas sócias de Joint Venture. O CNPJ é o vínculo
/// jurídico do contrato de trabalho do colaborador — imutável após a admissão.
class LegalEntity {
  const LegalEntity({
    required this.id,
    required this.companyId,
    required this.cnpj,
    required this.legalName,
    this.tradeName = '',
    this.entityType = 'matriz',
    this.parentEntityId,
    this.stateRegistration = '',
    this.municipalRegistration = '',
    this.cnae = '',
    this.address = '',
    this.municipality = '',
    this.uf = '',
    this.cep = '',
    this.openingDate = '',
    this.registrationStatus = 'ativa',
    this.isHeadquarters = false,
    this.active = true,
    this.notes = '',
  });

  final int id;
  final int companyId;
  final String cnpj;
  final String legalName;
  final String tradeName;

  /// `matriz`, `filial`, `subsidiaria`, `spe`, `jv_partner`, `consorciada`, `outro`.
  final String entityType;

  /// Controladora, quando a estrutura é holding/grupo empresarial.
  final int? parentEntityId;

  final String stateRegistration;
  final String municipalRegistration;
  final String cnae;
  final String address;
  final String municipality;
  final String uf;
  final String cep;
  final String openingDate;
  final String registrationStatus;
  final bool isHeadquarters;
  final bool active;
  final String notes;

  /// Rótulo curto para seletores: nome fantasia (ou razão social) + CNPJ.
  String get displayLabel {
    final name = tradeName.trim().isNotEmpty ? tradeName.trim() : legalName.trim();
    return name.isEmpty ? cnpj : '$name — $cnpj';
  }

  static bool _asBool(Object? value, {bool fallback = false}) => switch (value) {
        final bool b => b,
        final num n => n.toInt() == 1,
        final String s => s == '1' || s.toLowerCase() == 'true',
        _ => fallback,
      };

  static String _asString(Object? value) => value?.toString() ?? '';

  factory LegalEntity.fromJson(Map<String, dynamic> json) => LegalEntity(
        id: (json['id'] as num).toInt(),
        companyId: (json['company_id'] as num?)?.toInt() ?? 0,
        cnpj: _asString(json['cnpj']),
        legalName: _asString(json['legal_name']),
        tradeName: _asString(json['trade_name']),
        entityType: _asString(json['entity_type']).isEmpty
            ? 'matriz'
            : _asString(json['entity_type']),
        parentEntityId: (json['parent_entity_id'] as num?)?.toInt(),
        stateRegistration: _asString(json['state_registration']),
        municipalRegistration: _asString(json['municipal_registration']),
        cnae: _asString(json['cnae']),
        address: _asString(json['address']),
        municipality: _asString(json['municipality']),
        uf: _asString(json['uf']),
        cep: _asString(json['cep']),
        openingDate: _asString(json['opening_date']),
        registrationStatus: _asString(json['registration_status']),
        isHeadquarters: _asBool(json['is_headquarters']),
        active: _asBool(json['active'], fallback: true),
        notes: _asString(json['notes']),
      );

  /// Corpo aceito por POST/PUT `/api/legal-entities`.
  Map<String, dynamic> toJson() => {
        'cnpj': cnpj,
        'legal_name': legalName,
        'trade_name': tradeName,
        'entity_type': entityType,
        if (parentEntityId != null) 'parent_entity_id': parentEntityId,
        'state_registration': stateRegistration,
        'municipal_registration': municipalRegistration,
        'cnae': cnae,
        'address': address,
        'municipality': municipality,
        'uf': uf,
        'cep': cep,
        'opening_date': openingDate,
        'registration_status': registrationStatus,
        'is_headquarters': isHeadquarters ? 1 : 0,
        'active': active ? 1 : 0,
        'notes': notes,
      };
}
