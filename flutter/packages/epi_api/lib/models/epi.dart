class Epi {
  const Epi({
    required this.id,
    required this.name,
    this.code,
    this.caNumber,
    this.caExpiryDate,
    this.manufacturerValidityDate,
    this.validityDays,
    this.stockQuantity = 0,
    this.minimumStock = 0,
    this.photoUrl,
  });

  final int id;
  final String name;
  final String? code;
  final String? caNumber;

  /// Validade do Certificado de Aprovação (CA). Relevante na compra/aquisição
  /// do EPI (NT 146/2015).
  final String? caExpiryDate;

  /// Validade do produto informada pelo fabricante. Relevante para o uso/entrega
  /// do EPI: após a aquisição com CA válido, é esta data — e não mais o CA — que
  /// rege se o EPI pode ser entregue ao trabalhador (NT 146/2015).
  final String? manufacturerValidityDate;

  final int? validityDays;
  final int stockQuantity;
  final int minimumStock;
  final String? photoUrl;

  bool get isCriticalStock => stockQuantity <= minimumStock;

  /// 'expired' | 'expiring' | 'valid' | null (sem data) para uma data ISO.
  static String? _dateStatus(String? dateStr) {
    if (dateStr == null || dateStr.isEmpty) return null;
    final date = DateTime.tryParse(dateStr);
    if (date == null) return null;
    final now = DateTime.now();
    if (date.isBefore(now)) return 'expired';
    if (date.isBefore(now.add(const Duration(days: 30)))) return 'expiring';
    return 'valid';
  }

  static int? _daysUntil(String? dateStr) {
    if (dateStr == null || dateStr.isEmpty) return null;
    final date = DateTime.tryParse(dateStr);
    if (date == null) return null;
    return date.difference(DateTime.now()).inDays;
  }

  /// 'expired' | 'expiring' | 'valid' | null (no CA date)
  String? get caStatus => _dateStatus(caExpiryDate);

  int? get daysUntilCaExpiry => _daysUntil(caExpiryDate);

  /// 'expired' | 'expiring' | 'valid' | null (sem data do fabricante)
  String? get manufacturerValidityStatus =>
      _dateStatus(manufacturerValidityDate);

  int? get daysUntilManufacturerValidity =>
      _daysUntil(manufacturerValidityDate);

  /// True quando o EPI não pode ser entregue por validade do fabricante vencida
  /// (NT 146/2015). CA vencido NÃO impede a entrega.
  bool get isBlockedForDelivery => manufacturerValidityStatus == 'expired';

  Epi copyWith({int? stockQuantity}) => Epi(
        id: id,
        name: name,
        code: code,
        caNumber: caNumber,
        caExpiryDate: caExpiryDate,
        manufacturerValidityDate: manufacturerValidityDate,
        validityDays: validityDays,
        stockQuantity: stockQuantity ?? this.stockQuantity,
        minimumStock: minimumStock,
        photoUrl: photoUrl,
      );

  factory Epi.fromJson(Map<String, dynamic> json) => Epi(
        id: (json['id'] as num).toInt(),
        name: json['name'] as String? ?? '',
        // Aceita as chaves canônicas do backend e as legadas (compat.).
        code: (json['purchase_code'] ?? json['code']) as String?,
        caNumber: (json['ca'] ?? json['ca_number']) as String?,
        caExpiryDate: (json['ca_expiry'] ?? json['ca_expiry_date']) as String?,
        manufacturerValidityDate: (json['epi_validity_date'] ??
            json['manufacturer_validity_date']) as String?,
        validityDays: (json['validity_days'] as num?)?.toInt(),
        stockQuantity:
            ((json['stock'] ?? json['stock_quantity']) as num?)?.toInt() ?? 0,
        minimumStock: (json['minimum_stock'] as num?)?.toInt() ?? 0,
        photoUrl: (json['epi_photo_data'] ?? json['photo_url']) as String?,
      );
}
