import 'package:equatable/equatable.dart';

class Devolution extends Equatable {
  const Devolution({
    required this.id,
    required this.deliveryId,
    required this.employeeId,
    required this.employeeName,
    required this.epiId,
    required this.epiName,
    required this.condition,
    required this.destination,
    required this.returnedDate,
    this.notes,
  });

  final int id;
  final int deliveryId;
  final int employeeId;
  final String employeeName;
  final int epiId;
  final String epiName;
  final String condition;
  final String destination;
  final String returnedDate;
  final String? notes;

  factory Devolution.fromJson(Map<String, dynamic> json) => Devolution(
        id: json['id'] as int,
        deliveryId: (json['delivery_id'] ?? 0) as int,
        employeeId: (json['employee_id'] ?? 0) as int,
        employeeName: json['employee_name'] as String? ?? '',
        epiId: (json['epi_id'] ?? 0) as int,
        epiName: json['epi_name'] as String? ?? '',
        condition: json['condition'] as String? ?? '',
        destination: json['destination'] as String? ?? '',
        returnedDate: json['returned_date'] as String? ?? '',
        notes: json['notes'] as String?,
      );

  @override
  List<Object?> get props => [
        id,
        deliveryId,
        employeeId,
        epiId,
        condition,
        destination,
        returnedDate,
      ];
}

class OpenDelivery extends Equatable {
  const OpenDelivery({
    required this.id,
    required this.employeeId,
    required this.employeeName,
    required this.epiId,
    required this.epiName,
    required this.quantity,
    required this.deliveryDate,
    this.sector,
    this.roleName,
  });

  final int id;
  final int employeeId;
  final String employeeName;
  final int epiId;
  final String epiName;
  final int quantity;
  final String deliveryDate;
  final String? sector;
  final String? roleName;

  factory OpenDelivery.fromJson(Map<String, dynamic> json) => OpenDelivery(
        id: json['id'] as int,
        employeeId: (json['employee_id'] ?? 0) as int,
        employeeName: json['employee_name'] as String? ?? '',
        epiId: (json['epi_id'] ?? 0) as int,
        epiName: json['epi_name'] as String? ?? '',
        quantity: (json['quantity'] ?? 1) as int,
        deliveryDate: json['delivery_date'] as String? ?? '',
        sector: json['sector'] as String?,
        roleName: json['role_name'] as String?,
      );

  @override
  List<Object?> get props => [id, employeeId, epiId, quantity, deliveryDate];
}
