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
  });

  final String employeeName;
  final String unitName;
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
    return PortalAccess(
      employeeName: json['employee_name'] as String? ?? '',
      unitName: json['unit_name'] as String? ?? '',
      employeeCode: json['employee_code'] as String?,
      photoUrl: json['photo_url'] as String?,
      deliveries: _list('deliveries', PortalDelivery.fromJson),
      fichas: _list('fichas', PortalFicha.fromJson),
    );
  }
}
