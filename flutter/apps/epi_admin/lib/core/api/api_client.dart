import 'package:dio/dio.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:epi_api/epi_api.dart';

const _kTokenKey       = 'access_token';
const _kPermissionsKey = 'user_permissions';

class ApiClient {
  ApiClient._();

  static late final AuthApi auth;
  static late final CompaniesApi companies;
  static late final DeliveriesApi deliveries;
  static late final DevolutionsApi devolutions;
  static late final FichasApi fichas;
  static late final PortalApi portal;
  static late final PurchasesApi purchases;
  static late final ReportsApi reports;
  static late final SettingsApi settings;
  static late final FeedbackApi feedback;
  static late final StockApi stock;
  static late final FlutterSecureStorage _storage;

  /// Cached actor user ID — set after bootstrap, used by all admin actions.
  static int actorUserId = 0;

  static Future<void> init({required String baseUrl}) async {
    _storage = const FlutterSecureStorage();
    final dio = Dio(BaseOptions(
      baseUrl: baseUrl,
      connectTimeout: const Duration(seconds: 10),
      receiveTimeout: const Duration(seconds: 30),
    ));
    dio.interceptors.add(_BearerInterceptor());
    dio.interceptors.add(_RetryInterceptor(dio));
    auth = AuthApi(dio, baseUrl: baseUrl);
    companies = CompaniesApi(dio);
    deliveries = DeliveriesApi(dio);
    devolutions = DevolutionsApi(dio);
    fichas = FichasApi(dio);
    portal = PortalApi(dio);
    purchases = PurchasesApi(dio);
    reports = ReportsApi(dio);
    settings = SettingsApi(dio);
    feedback = FeedbackApi(dio);
    stock = StockApi(dio);
  }

  static Future<void> saveToken(String token) =>
      _storage.write(key: _kTokenKey, value: token);

  static Future<String?> getToken() => _storage.read(key: _kTokenKey);

  static Future<void> clearToken() => _storage.delete(key: _kTokenKey);

  static Future<void> savePermissions(List<String> permissions) =>
      _storage.write(key: _kPermissionsKey, value: permissions.join(','));

  static Future<List<String>> getPermissions() async {
    final raw = await _storage.read(key: _kPermissionsKey);
    if (raw == null || raw.isEmpty) return const [];
    return raw.split(',');
  }

  static Future<void> clearPermissions() =>
      _storage.delete(key: _kPermissionsKey);
}

class _RetryInterceptor extends Interceptor {
  _RetryInterceptor(this._dio);
  final Dio _dio;

  static const _maxAttempts = 3;
  static const _baseDelayMs = 1000;

  @override
  Future<void> onError(DioException err, ErrorInterceptorHandler handler) async {
    final attempt = (err.requestOptions.extra['_retryAttempt'] as int?) ?? 0;
    if (attempt >= _maxAttempts || !_isRetryable(err)) {
      return handler.next(err);
    }
    // Exponential backoff: 1s, 2s, 4s
    final delayMs = _baseDelayMs * (1 << attempt);
    await Future.delayed(Duration(milliseconds: delayMs));
    err.requestOptions.extra['_retryAttempt'] = attempt + 1;
    try {
      handler.resolve(await _dio.fetch(err.requestOptions));
    } on DioException catch (e) {
      handler.next(e);
    }
  }

  bool _isRetryable(DioException err) {
    switch (err.type) {
      case DioExceptionType.connectionTimeout:
      case DioExceptionType.receiveTimeout:
      case DioExceptionType.connectionError:
        return true;
      case DioExceptionType.badResponse:
        final status = err.response?.statusCode ?? 0;
        return status == 502 || status == 503 || status == 504;
      default:
        return false;
    }
  }
}

class _BearerInterceptor extends Interceptor {
  @override
  Future<void> onRequest(
    RequestOptions options,
    RequestInterceptorHandler handler,
  ) async {
    final token = await ApiClient.getToken();
    if (token != null) {
      options.headers['Authorization'] = 'Bearer $token';
    }
    handler.next(options);
  }

  @override
  Future<void> onError(
    DioException err,
    ErrorInterceptorHandler handler,
  ) async {
    if (err.response?.statusCode == 401) {
      await ApiClient.clearToken();
    }
    handler.next(err);
  }
}
