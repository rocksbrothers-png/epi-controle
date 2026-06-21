import 'package:equatable/equatable.dart';

/// Contexto canônico da sessão autenticada no Flutter.
///
/// O Flutter continua consumindo apenas a API REST; este objeto apenas
/// normaliza o contrato retornado por `POST /api/login`, `GET /api/auth/me` e
/// `GET /api/bootstrap` para que telas/cubits não precisem conhecer chaves
/// legadas como `operational_unit_id`.
class SessionContext extends Equatable {
  const SessionContext({
    required this.userId,
    required this.companyId,
    required this.unitId,
    required this.role,
    required this.permissions,
    required this.tenantName,
    required this.companySettings,
  });

  static const empty = SessionContext(
    userId: null,
    companyId: null,
    unitId: null,
    role: '',
    permissions: <String>[],
    tenantName: '',
    companySettings: <String, dynamic>{},
  );

  final int? userId;
  final int? companyId;
  final int? unitId;
  final String role;
  final List<String> permissions;
  final String tenantName;
  final Map<String, dynamic> companySettings;

  bool get isAuthenticated => userId != null;
  bool get isTenantScoped => companyId != null;
  bool hasPermission(String permission) => permissions.contains(permission);

  factory SessionContext.fromAuthPayload({
    required Map<String, dynamic> user,
    required List<String> permissions,
    Map<String, dynamic>? company,
    Map<String, dynamic>? companySettings,
  }) {
    final normalizedCompany = company ?? _asMap(user['company']);
    final normalizedSettings = companySettings ??
        _asMap(user['company_settings']).ifEmpty(_asMap(user['settings']));

    return SessionContext(
      userId: _asInt(user['id'] ?? user['user_id']),
      companyId: _asInt(user['company_id'] ?? normalizedCompany['id']),
      unitId: _asInt(user['unit_id'] ?? user['operational_unit_id']),
      role: (user['role'] ?? '').toString(),
      permissions: List<String>.unmodifiable(permissions),
      tenantName: (user['tenant_name'] ??
              user['company_name'] ??
              normalizedCompany['name'] ??
              '')
          .toString(),
      companySettings: Map<String, dynamic>.unmodifiable(normalizedSettings),
    );
  }

  factory SessionContext.fromJson(Map<String, dynamic> json) => SessionContext(
        userId: _asInt(json['userId']),
        companyId: _asInt(json['companyId']),
        unitId: _asInt(json['unitId']),
        role: (json['role'] ?? '').toString(),
        permissions: ((json['permissions'] as List?) ?? const [])
            .map((item) => item.toString())
            .toList(growable: false),
        tenantName: (json['tenantName'] ?? '').toString(),
        companySettings: Map<String, dynamic>.unmodifiable(
          _asMap(json['companySettings']),
        ),
      );

  Map<String, dynamic> toJson() => <String, dynamic>{
        'userId': userId,
        'companyId': companyId,
        'unitId': unitId,
        'role': role,
        'permissions': permissions,
        'tenantName': tenantName,
        'companySettings': companySettings,
      };

  @override
  List<Object?> get props => [
        userId,
        companyId,
        unitId,
        role,
        permissions,
        tenantName,
        companySettings,
      ];
}

Map<String, dynamic> _asMap(Object? raw) =>
    (raw as Map?)?.cast<String, dynamic>() ?? const <String, dynamic>{};

int? _asInt(Object? raw) {
  if (raw == null) return null;
  if (raw is int) return raw;
  return int.tryParse(raw.toString());
}

extension _MapFallback on Map<String, dynamic> {
  Map<String, dynamic> ifEmpty(Map<String, dynamic> fallback) =>
      isEmpty ? fallback : this;
}
