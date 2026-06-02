class Epi {
  const Epi({
    required this.id,
    required this.name,
    this.code,
    this.caNumber,
    this.caExpiryDate,
    this.validityDays,
    this.stockQuantity = 0,
    this.minimumStock = 0,
    this.photoUrl,
  });

  final int id;
  final String name;
  final String? code;
  final String? caNumber;
  final String? caExpiryDate;
  final int? validityDays;
  final int stockQuantity;
  final int minimumStock;
  final String? photoUrl;

  bool get isCriticalStock => stockQuantity <= minimumStock;

  /// 'expired' | 'expiring' | 'valid' | null (no CA date)
  String? get caStatus {
    if (caExpiryDate == null) return null;
    final expiry = DateTime.tryParse(caExpiryDate!);
    if (expiry == null) return null;
    final now = DateTime.now();
    if (expiry.isBefore(now)) return 'expired';
    if (expiry.isBefore(now.add(const Duration(days: 30)))) return 'expiring';
    return 'valid';
  }

  int? get daysUntilCaExpiry {
    if (caExpiryDate == null) return null;
    final expiry = DateTime.tryParse(caExpiryDate!);
    if (expiry == null) return null;
    return expiry.difference(DateTime.now()).inDays;
  }

  Epi copyWith({int? stockQuantity}) => Epi(
        id: id,
        name: name,
        code: code,
        caNumber: caNumber,
        caExpiryDate: caExpiryDate,
        validityDays: validityDays,
        stockQuantity: stockQuantity ?? this.stockQuantity,
        minimumStock: minimumStock,
        photoUrl: photoUrl,
      );

  factory Epi.fromJson(Map<String, dynamic> json) => Epi(
        id: (json['id'] as num).toInt(),
        name: json['name'] as String? ?? '',
        code: json['code'] as String?,
        caNumber: json['ca_number'] as String?,
        caExpiryDate: json['ca_expiry_date'] as String?,
        validityDays: (json['validity_days'] as num?)?.toInt(),
        stockQuantity: (json['stock_quantity'] as num?)?.toInt() ?? 0,
        minimumStock: (json['minimum_stock'] as num?)?.toInt() ?? 0,
        photoUrl: json['photo_url'] as String?,
      );
}
