class Employee {
  const Employee({
    required this.id,
    required this.name,
    this.code,
    this.sector,
    this.role,
    this.unitName,
    this.admissionDate,
    this.schedule,
    this.photoUrl,
    this.isActive = true,
  });

  final int id;
  final String name;
  final String? code;
  final String? sector;
  final String? role;
  final String? unitName;
  final String? admissionDate;
  final String? schedule;
  final String? photoUrl;
  final bool isActive;

  factory Employee.fromJson(Map<String, dynamic> json) => Employee(
        id: (json['id'] as num).toInt(),
        name: json['name'] as String? ?? '',
        code: json['code'] as String?,
        sector: json['sector'] as String?,
        role: json['role'] as String?,
        unitName: json['unit_name'] as String? ?? json['unit'] as String?,
        admissionDate: json['admission_date'] as String?,
        schedule: json['schedule'] as String?,
        photoUrl: json['photo_url'] as String?,
        isActive: (json['is_active'] as bool?) ?? true,
      );
}
