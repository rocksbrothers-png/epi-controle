import 'package:dio/dio.dart';
import 'package:retrofit/retrofit.dart';
import '../models/bootstrap_response.dart';

part 'auth_api.g.dart';

/// Endpoints de autenticação e bootstrap — espelham o backend UBX.
/// Gerado com: dart run build_runner build
@RestApi()
abstract class AuthApi {
  factory AuthApi(Dio dio, {String baseUrl}) = _AuthApi;

  /// POST /api/login → {token, user, permissions, refresh_token, ...}
  @POST('/api/login')
  Future<LoginResponse> login(@Body() Map<String, dynamic> body);

  /// GET /api/bootstrap → {units, employees, epis, users, alerts, ...}
  /// Consome os dados filtrados pelo canary (UBX enforced).
  @GET('/api/bootstrap')
  Future<BootstrapResponse> bootstrap();

  /// PATCH /api/user/locale → {ok: true}
  @PATCH('/api/user/locale')
  Future<void> setLocale(@Body() Map<String, String> body);
}

/// Helpers puros de parsing — tolerantes a chaves ausentes. Centralizam o
/// contrato real do backend (chaves de **topo**: `token`, `refresh_token`,
/// `permissions`), que já causou bug de paridade.
List<String> _parsePermissions(Object? raw) =>
    ((raw as List?) ?? const []).map((e) => e.toString()).toList();

Map<String, dynamic> _asMap(Object? raw) =>
    (raw as Map?)?.cast<String, dynamic>() ?? const {};

/// Resposta de `POST /api/login`.
class LoginResponse {
  const LoginResponse({
    required this.token,
    required this.user,
    this.refreshToken,
    this.permissions = const [],
    this.moduleVisibility = const {},
    this.mustChangePassword = false,
  });

  final String token;
  final Map<String, dynamic> user;

  /// Refresh token de topo — **antes era descartado** (causa do logout em 401).
  final String? refreshToken;

  /// Permissões de topo — **antes lidas erroneamente de `user['permissions']`**
  /// (que não existe), deixando o RBAC do app sem permissões.
  final List<String> permissions;

  /// Visibilidade estrutural por módulo (menu/rotas/deep links) — regra
  /// padrão + configuração do Administrador Geral, já clampada pela
  /// permissão técnica. Consumida pelo NavigationPolicy.
  final Map<String, dynamic> moduleVisibility;

  /// Credencial temporária provisionada por admin: exige troca no 1º acesso.
  /// Vem no topo da resposta (e espelhada em `user.must_change_password`).
  final bool mustChangePassword;

  factory LoginResponse.fromJson(Map<String, dynamic> json) => LoginResponse(
        token: json['token'] as String,
        user: _asMap(json['user']),
        refreshToken: json['refresh_token'] as String?,
        permissions: _parsePermissions(json['permissions']),
        moduleVisibility: _asMap(json['module_visibility']),
        mustChangePassword: _asBool(json['must_change_password']) ||
            _asBool(_asMap(json['user'])['must_change_password']),
      );
}

bool _asBool(Object? raw) {
  if (raw is bool) return raw;
  if (raw is num) return raw.toInt() == 1;
  if (raw is String) return raw == 'true' || raw == '1';
  return false;
}

/// Resposta de `POST /api/auth/refresh` (access + refresh rotacionado).
class RefreshResponse {
  const RefreshResponse({required this.token, this.refreshToken});

  final String token;
  final String? refreshToken;

  factory RefreshResponse.fromJson(Map<String, dynamic> json) => RefreshResponse(
        token: json['token'] as String,
        refreshToken: json['refresh_token'] as String?,
      );
}

/// Identidade do usuário a partir de `GET /api/auth/me` (envelope `data`).
class AuthIdentity {
  const AuthIdentity({
    required this.user,
    this.permissions = const [],
    this.moduleVisibility = const {},
  });

  final Map<String, dynamic> user;
  final List<String> permissions;
  final Map<String, dynamic> moduleVisibility;

  /// Desembrulha o envelope `{success, data:{user, permissions}}`; tolera
  /// também o formato plano `{user, permissions}` por robustez.
  factory AuthIdentity.fromMeJson(Map<String, dynamic> json) {
    final data = json.containsKey('data') ? _asMap(json['data']) : json;
    return AuthIdentity(
      user: _asMap(data['user']),
      permissions: _parsePermissions(data['permissions']),
      moduleVisibility: _asMap(data['module_visibility']),
    );
  }
}
