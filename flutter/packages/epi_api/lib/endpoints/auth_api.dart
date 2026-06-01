import 'package:dio/dio.dart';
import 'package:retrofit/retrofit.dart';
import '../models/bootstrap_response.dart';

part 'auth_api.g.dart';

/// Endpoints de autenticação e bootstrap — espelham o backend UBX.
/// Gerado com: dart run build_runner build
@RestApi()
abstract class AuthApi {
  factory AuthApi(Dio dio, {String baseUrl}) = _AuthApi;

  /// POST /api/login → {token, user}
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

class LoginResponse {
  const LoginResponse({required this.token, required this.user});
  final String             token;
  final Map<String, dynamic> user;

  factory LoginResponse.fromJson(Map<String, dynamic> json) => LoginResponse(
    token: json['token'] as String,
    user:  json['user']  as Map<String, dynamic>,
  );
}
