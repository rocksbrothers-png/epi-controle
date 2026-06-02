class Delivery {
  const Delivery({
    required this.id,
    required this.employeeName,
    required this.epiName,
    required this.quantity,
    required this.deliveryDate,
    this.sector,
    this.roleName,
    this.signatureData,
  });

  final int id;
  final String employeeName;
  final String epiName;
  final int quantity;
  final String deliveryDate;
  final String? sector;
  final String? roleName;
  final String? signatureData;

  factory Delivery.fromJson(Map<String, dynamic> json) => Delivery(
        id: json['id'] as int,
        employeeName: (json['employee_name'] ??
                json['full_name'] ??
                json['employee'] ??
                '') as String,
        epiName: (json['epi_name'] ?? json['epi'] ?? '') as String,
        quantity: (json['quantity'] ?? 1) as int,
        deliveryDate: (json['delivery_date'] ?? '') as String,
        sector: json['sector'] as String?,
        roleName: json['role_name'] as String?,
        signatureData: json['signature_data'] as String?,
      );
}
