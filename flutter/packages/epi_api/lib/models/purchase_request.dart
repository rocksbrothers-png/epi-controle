class PurchaseRequest {
  const PurchaseRequest({
    required this.id,
    required this.title,
    required this.status,
    required this.unitId,
    required this.unitName,
    required this.createdAt,
    required this.items,
    this.notes,
    this.updatedAt,
  });

  final int id;
  final String title;
  final String status;
  final int unitId;
  final String unitName;
  final String createdAt;
  final List<PurchaseRequestItem> items;
  final String? notes;
  final String? updatedAt;

  int get totalQuantity => items.fold(0, (s, i) => s + i.quantity);

  factory PurchaseRequest.fromJson(Map<String, dynamic> json) =>
      PurchaseRequest(
        id: json['id'] as int,
        title: json['title'] as String? ?? '',
        status: json['status'] as String? ?? 'draft',
        unitId: (json['unit_id'] ?? 0) as int,
        unitName: json['unit_name'] as String? ?? '',
        createdAt: json['created_at'] as String? ?? '',
        updatedAt: json['updated_at'] as String?,
        notes: json['notes'] as String?,
        items: ((json['items'] as List?) ?? [])
            .map((e) => PurchaseRequestItem.fromJson(e as Map<String, dynamic>))
            .toList(),
      );
}

class PurchaseRequestItem {
  const PurchaseRequestItem({
    required this.epiId,
    required this.epiName,
    required this.quantity,
    this.id,
  });

  final int? id;
  final int epiId;
  final String epiName;
  final int quantity;

  factory PurchaseRequestItem.fromJson(Map<String, dynamic> json) =>
      PurchaseRequestItem(
        id: json['id'] as int?,
        epiId: (json['epi_id'] ?? 0) as int,
        epiName: json['epi_name'] as String? ?? '',
        quantity: (json['quantity'] ?? 1) as int,
      );

  Map<String, dynamic> toJson() => {
        'epi_id': epiId,
        'quantity': quantity,
      };
}

class PurchaseDemand {
  const PurchaseDemand({
    required this.epiId,
    required this.epiName,
    required this.currentStock,
    required this.minimumStock,
    required this.unitId,
    required this.unitName,
  });

  final int epiId;
  final String epiName;
  final int currentStock;
  final int minimumStock;
  final int unitId;
  final String unitName;

  int get deficit => (minimumStock - currentStock).clamp(0, 99999);

  factory PurchaseDemand.fromJson(Map<String, dynamic> json) => PurchaseDemand(
        epiId: (json['epi_id'] ?? 0) as int,
        epiName: json['epi_name'] as String? ?? json['name'] as String? ?? '',
        currentStock:
            (json['stock_quantity'] ?? json['current_stock'] ?? 0) as int,
        minimumStock: (json['minimum_stock'] ?? 0) as int,
        unitId: (json['unit_id'] ?? 0) as int,
        unitName: json['unit_name'] as String? ?? '',
      );
}
