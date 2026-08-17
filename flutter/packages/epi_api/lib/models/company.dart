class Company {
  const Company({
    required this.id,
    required this.name,
    required this.licenseStatus,
    required this.active,
    this.legalName,
    this.cnpj,
    this.planName,
    this.userLimit,
    this.userCount,
  });

  final int id;
  final String name;
  final String licenseStatus;
  final bool active;
  final String? legalName;
  final String? cnpj;
  final String? planName;
  final int? userLimit;
  final int? userCount;

  bool get isActive => active && licenseStatus == 'active';
  bool get isSuspended => licenseStatus == 'suspended';

  factory Company.fromJson(Map<String, dynamic> json) => Company(
        id: (json['id'] as num).toInt(),
        name: json['name'] as String? ?? '',
        licenseStatus: json['license_status'] as String? ?? 'active',
        // O backend serializa `active` como inteiro 0/1 (coluna INTEGER);
        // aceitar bool mantém compatibilidade com payloads antigos.
        active: json['active'] is bool
            ? json['active'] as bool
            : ((json['active'] as num?)?.toInt() ?? 1) == 1,
        legalName: json['legal_name'] as String?,
        cnpj: json['cnpj'] as String?,
        planName: json['plan_name'] as String?,
        userLimit: (json['user_limit'] as num?)?.toInt(),
        userCount: (json['user_count'] as num?)?.toInt(),
      );
}
