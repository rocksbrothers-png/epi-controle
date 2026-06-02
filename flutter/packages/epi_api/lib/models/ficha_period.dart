class FichaPeriod {
  const FichaPeriod({
    required this.id,
    required this.employeeId,
    required this.employeeName,
    required this.unitName,
    required this.periodStart,
    required this.status,
    required this.totalItems,
    required this.pendingItems,
    this.employeeCode,
  });

  final int id;
  final int employeeId;
  final String employeeName;
  final String? employeeCode;
  final String unitName;
  final String periodStart;
  final String status;
  final int totalItems;
  final int pendingItems;

  bool get isComplete => pendingItems == 0 && totalItems > 0;
  bool get hasPending => pendingItems > 0;

  String get periodLabel {
    if (periodStart.length >= 7) {
      final parts = periodStart.substring(0, 7).split('-');
      if (parts.length == 2) {
        final months = [
          '', 'Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun',
          'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'
        ];
        final m = int.tryParse(parts[1]) ?? 0;
        return '${months[m]} ${parts[0]}';
      }
    }
    return periodStart;
  }

  factory FichaPeriod.fromJson(Map<String, dynamic> json) => FichaPeriod(
        id: json['id'] as int,
        employeeId: (json['employee_id'] ?? 0) as int,
        employeeName: json['employee_name'] as String? ?? '',
        employeeCode: json['employee_id_code'] as String?,
        unitName: json['unit_name'] as String? ?? '',
        periodStart: json['period_start'] as String? ?? '',
        status: json['status'] as String? ?? 'open',
        totalItems: (json['total_items'] ?? 0) as int,
        pendingItems: (json['pending_items'] ?? 0) as int,
      );
}
