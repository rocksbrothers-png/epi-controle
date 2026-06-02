/// Model for a feedback/avaliação item returned by the backend.
class FeedbackItem {
  const FeedbackItem({
    required this.id,
    required this.epiName,
    required this.status,
    required this.createdAt,
    this.employeeName,
    this.description,
    this.unitName,
  });

  final int id;
  final String epiName;
  final String status;
  final String createdAt;
  final String? employeeName;
  final String? description;
  final String? unitName;

  factory FeedbackItem.fromJson(Map<String, dynamic> json) => FeedbackItem(
        id: json['id'] as int,
        epiName: (json['epi_name'] ?? json['epi'] ?? '') as String,
        status: (json['status'] ?? 'open') as String,
        createdAt: (json['created_at'] ?? '') as String,
        employeeName: json['employee_name'] as String?,
        description: (json['description'] ?? json['notes']) as String?,
        unitName: json['unit_name'] as String?,
      );
}
