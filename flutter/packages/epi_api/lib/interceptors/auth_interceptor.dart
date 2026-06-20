import 'package:dio/dio.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

/// Injeta o Bearer token e, em 401, limpa o token (sem refresh).
///
/// NOTA: este interceptor NÃO está cabeado no app `epi_admin` — a montagem do
/// Dio vive em `epi_admin/lib/core/api/api_client.dart`, cujo `_BearerInterceptor`
/// é quem faz o **refresh automático** em 401 (single-flight). Mantido aqui
/// apenas como utilitário do pacote; não faz refresh.
class AuthInterceptor extends Interceptor {
  AuthInterceptor({required this.storage, required this.dio});

  final FlutterSecureStorage storage;
  final Dio                  dio;

  @override
  Future<void> onRequest(RequestOptions options, RequestInterceptorHandler handler) async {
    final token = await storage.read(key: 'access_token');
    if (token != null) {
      options.headers['Authorization'] = 'Bearer $token';
    }
    options.headers['Accept-Language'] = await storage.read(key: 'locale') ?? 'pt-BR';
    handler.next(options);
  }

  @override
  Future<void> onError(DioException err, ErrorInterceptorHandler handler) async {
    if (err.response?.statusCode == 401) {
      // Limpa token e redireciona para login via evento global
      await storage.delete(key: 'access_token');
      // O app.dart ouve AuthStateNotifier e redireciona
    }
    handler.next(err);
  }
}
