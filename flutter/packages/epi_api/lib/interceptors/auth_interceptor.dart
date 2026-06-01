import 'package:dio/dio.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

/// Injeta Bearer token e faz refresh automático em 401.
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
