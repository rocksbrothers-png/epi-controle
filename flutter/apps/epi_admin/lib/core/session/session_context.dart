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
    this.moduleVisibility = const <String, bool>{},
  });

  static const empty = SessionContext(
    userId: null,
    companyId: null,
    unitId: null,
    role: '',
    permissions: <String>[],
    tenantName: '',
    companySettings: <String, dynamic>{},
    moduleVisibility: <String, bool>{},
  );

  final int? userId;
  final int? companyId;
  final int? unitId;
  final String role;
  final List<String> permissions;
  final String tenantName;
  final Map<String, dynamic> companySettings;

  /// Visibilidade estrutural por módulo (menu/rotas/deep links), já
  /// combinando a regra padrão + a configuração do Administrador Geral com
  /// a permissão técnica do ator (vem de `module_visibility` no login,
  /// `/api/auth/me` e `/api/bootstrap`). Consumida pelo NavigationPolicy —
  /// nunca pela autorização de dados, que continua exclusivamente no backend.
  final Map<String, bool> moduleVisibility;

  bool get isAuthenticated => userId != null;
  bool get isTenantScoped => companyId != null;
  bool hasPermission(String permission) => permissions.contains(permission);

  /// Módulo ausente do mapa (backend antigo, resposta degradada) é tratado
  /// como visível — só a permissão técnica (já refletida em [permissions])
  /// segue protegendo a rota; esta camada só restringe quando o backend
  /// explicitamente diz que o módulo está desligado para o perfil.
  bool isModuleVisible(String module) => moduleVisibility[module] ?? true;

  factory SessionContext.fromAuthPayload({
    required Map<String, dynamic> user,
    required List<String> permissions,
    Map<String, dynamic>? company,
    Map<String, dynamic>? companySettings,
    Map<String, dynamic>? moduleVisibility,
  }) {
    final normalizedCompany = company ?? _asMap(user['company']);
    final normalizedSettings = companySettings ??
        _asMap(user['company_settings']).ifEmpty(_asMap(user['settings']));

    return SessionContext(
      userId: _asInt(user['id'] ?? user['user_id']),
      companyId: _asInt(user['company_id'] ?? normalizedCompany['id']),
      // `operational_unit_id` PRIMEIRO, sempre (1.1D-A). É o único campo que o
      // backend resolve: sai de `actor_operational_unit_id`, já honrando
      // movimento temporário vigente. `unit_id` é o vínculo cru do colaborador
      // e não conhece movimentação — lê-lo primeiro devolveria a unidade de
      // origem de quem está temporariamente em outra, e a sessão passaria a
      // divergir do recorte que o servidor aplica nas consultas.
      //
      // Hoje nenhuma resposta de auth emite `unit_id` (a tabela `users` não tem
      // essa coluna), então a ordem não muda nada em produção. Está invertida
      // aqui para que continuar assim não dependa de ninguém lembrar disso ao
      // acrescentar um campo.
      unitId: _asInt(user['operational_unit_id'] ?? user['unit_id']),
      role: (user['role'] ?? '').toString(),
      permissions: List<String>.unmodifiable(permissions),
      tenantName: (user['tenant_name'] ??
              user['company_name'] ??
              normalizedCompany['name'] ??
              '')
          .toString(),
      companySettings: Map<String, dynamic>.unmodifiable(normalizedSettings),
      moduleVisibility: _asBoolMap(moduleVisibility),
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
        moduleVisibility: _asBoolMap(_asMap(json['moduleVisibility'])),
      );

  Map<String, dynamic> toJson() => <String, dynamic>{
        'userId': userId,
        'companyId': companyId,
        'unitId': unitId,
        'role': role,
        'permissions': permissions,
        'tenantName': tenantName,
        'companySettings': companySettings,
        'moduleVisibility': moduleVisibility,
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
        moduleVisibility,
      ];
}

Map<String, dynamic> _asMap(Object? raw) =>
    (raw as Map?)?.cast<String, dynamic>() ?? const <String, dynamic>{};

Map<String, bool> _asBoolMap(Object? raw) {
  final map = raw is Map ? raw.cast<String, dynamic>() : const <String, dynamic>{};
  return Map<String, bool>.unmodifiable(
    map.map((key, value) => MapEntry(key, value == true)),
  );
}

int? _asInt(Object? raw) {
  if (raw == null) return null;
  if (raw is int) return raw;
  return int.tryParse(raw.toString());
}

extension _MapFallback on Map<String, dynamic> {
  Map<String, dynamic> ifEmpty(Map<String, dynamic> fallback) =>
      isEmpty ? fallback : this;
}
