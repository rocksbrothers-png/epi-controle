class PortalDelivery {
  const PortalDelivery({
    required this.id,
    required this.epiName,
    required this.deliveryDate,
    required this.quantity,
    required this.signed,
    this.signedAt,
    this.caNumber,
  });

  final int id;
  final String epiName;
  final String deliveryDate;
  final int quantity;
  final bool signed;
  final String? signedAt;
  final String? caNumber;

  factory PortalDelivery.fromJson(Map<String, dynamic> json) => PortalDelivery(
        id: (json['id'] as num).toInt(),
        epiName: json['epi_name'] as String? ?? '',
        deliveryDate: json['delivery_date'] as String? ?? '',
        quantity: (json['quantity'] as num?)?.toInt() ?? 1,
        signed: (json['signed'] as bool?) ?? false,
        signedAt: json['signed_at'] as String?,
        caNumber: json['ca_number'] as String?,
      );
}

class PortalFicha {
  const PortalFicha({
    required this.id,
    required this.periodLabel,
    required this.status,
    required this.totalItems,
    required this.signedItems,
    this.deliveryIds = const [],
  });

  final int id;
  final String periodLabel;
  final String status;
  final int totalItems;
  final int signedItems;
  final List<int> deliveryIds;

  bool get isFullySigned => totalItems > 0 && signedItems >= totalItems;
  bool get hasUnsigned => totalItems > signedItems;

  factory PortalFicha.fromJson(Map<String, dynamic> json) => PortalFicha(
        id: (json['id'] as num).toInt(),
        periodLabel: json['period_label'] as String? ?? '',
        status: json['status'] as String? ?? 'pending',
        totalItems: (json['total_items'] as num?)?.toInt() ?? 0,
        signedItems: (json['signed_items'] as num?)?.toInt() ?? 0,
        deliveryIds: ((json['delivery_ids'] as List?) ?? [])
            .map((e) => (e as num).toInt())
            .toList(),
      );
}

class PortalAccess {
  const PortalAccess({
    required this.employeeName,
    required this.unitName,
    required this.deliveries,
    required this.fichas,
    this.employeeCode,
    this.photoUrl,
    this.companyName = '',
    this.legalEntityCnpj = '',
    this.legalEntityName = '',
  });

  final String employeeName;
  final String unitName;

  /// Empresa contratante do colaborador.
  final String companyName;

  /// CNPJ (LegalEntity) do vínculo jurídico do colaborador. Vazio enquanto o
  /// schema Multi-CNPJ não estiver provisionado.
  final String legalEntityCnpj;
  final String legalEntityName;
  final String? employeeCode;
  final String? photoUrl;
  final List<PortalDelivery> deliveries;
  final List<PortalFicha> fichas;

  int get unsignedCount =>
      deliveries.where((d) => !d.signed).length;

  factory PortalAccess.fromJson(Map<String, dynamic> json) {
    List<T> _list<T>(String key, T Function(Map<String, dynamic>) fn) =>
        ((json[key] as List?) ?? [])
            .map((e) => fn(e as Map<String, dynamic>))
            .toList();
    // GET /api/employee-access aninha os dados do colaborador em `employee`;
    // lemos de lá com o topo como fallback, para tolerar ambos os formatos.
    final employee = (json['employee'] as Map<String, dynamic>?) ?? const {};
    String field(String key) =>
        (employee[key] ?? json[key])?.toString() ?? '';

    return PortalAccess(
      employeeName: field('employee_name').isNotEmpty
          ? field('employee_name')
          : field('name'),
      unitName: field('unit_name'),
      companyName: field('company_name'),
      legalEntityCnpj: field('legal_entity_cnpj'),
      legalEntityName: field('legal_entity_name'),
      employeeCode: field('employee_code').isNotEmpty
          ? field('employee_code')
          : (field('employee_id_code').isNotEmpty
              ? field('employee_id_code')
              : null),
      photoUrl: field('photo_url').isNotEmpty ? field('photo_url') : null,
      deliveries: _list('deliveries', PortalDelivery.fromJson),
      fichas: _list('fichas', PortalFicha.fromJson),
    );
  }
}
