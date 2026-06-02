class ReportData {
  const ReportData({
    required this.totalQuantity,
    required this.byUnit,
    required this.bySector,
    required this.byEpi,
    required this.deliveries,
  });

  final int totalQuantity;
  final Map<String, int> byUnit;
  final Map<String, int> bySector;
  final Map<String, int> byEpi;
  final List<Map<String, dynamic>> deliveries;

  List<MapEntry<String, int>> get topEpis {
    final entries = byEpi.entries.toList()
      ..sort((a, b) => b.value.compareTo(a.value));
    return entries.take(8).toList();
  }

  List<MapEntry<String, int>> get topSectors {
    final entries = bySector.entries.toList()
      ..sort((a, b) => b.value.compareTo(a.value));
    return entries.take(8).toList();
  }

  factory ReportData.fromJson(Map<String, dynamic> json) {
    Map<String, int> _toIntMap(dynamic raw) {
      if (raw is Map) {
        return raw.map((k, v) => MapEntry(k.toString(), (v as num).toInt()));
      }
      return {};
    }

    return ReportData(
      totalQuantity: (json['total_quantity'] ?? 0) as int,
      byUnit: _toIntMap(json['by_unit']),
      bySector: _toIntMap(json['by_sector']),
      byEpi: _toIntMap(json['by_epi']),
      deliveries: ((json['deliveries'] as List?) ?? [])
          .cast<Map<String, dynamic>>(),
    );
  }
}

class ReportRequest {
  const ReportRequest({
    required this.id,
    required this.status,
    required this.requesterName,
    required this.createdAt,
    this.unitId,
    this.unitName,
    this.periodYear,
    this.periodMonth,
    this.notes,
  });

  final int id;
  final String status;
  final String requesterName;
  final String createdAt;
  final int? unitId;
  final String? unitName;
  final int? periodYear;
  final int? periodMonth;
  final String? notes;

  factory ReportRequest.fromJson(Map<String, dynamic> json) => ReportRequest(
        id: json['id'] as int,
        status: json['status'] as String? ?? 'pending',
        requesterName:
            json['requester_name'] as String? ?? json['created_by'] as String? ?? '',
        createdAt: json['created_at'] as String? ?? '',
        unitId: json['unit_id'] as int?,
        unitName: json['unit_name'] as String?,
        periodYear: json['period_year'] as int?,
        periodMonth: json['period_month'] as int?,
        notes: json['notes'] as String?,
      );
}
