import 'package:dio/dio.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:epi_api/epi_api.dart';

const _kTokenKey = 'access_token';

class ApiClient {
  ApiClient._();

  static late final AuthApi auth;
  static late final CompaniesApi companies;
  static late final DeliveriesApi deliveries;
  static late final DevolutionsApi devolutions;
  static late final FichasApi fichas;
  static late final PurchasesApi purchases;
  static late final ReportsApi reports;
  static late final SettingsApi settings;
  static late final FlutterSecureStorage _storage;

  static Future<void> init({required String baseUrl}) async {
    _storage = const FlutterSecureStorage();
    final dio = Dio(BaseOptions(
      baseUrl: baseUrl,
      connectTimeout: const Duration(seconds: 10),
      receiveTimeout: const Duration(seconds: 30),
    ));
    dio.interceptors.add(_BearerInterceptor());
    auth = AuthApi(dio, baseUrl: baseUrl);
    companies = CompaniesApi(dio);
    deliveries = DeliveriesApi(dio);
    devolutions = DevolutionsApi(dio);
    fichas = FichasApi(dio);
    purchases = PurchasesApi(dio);
    reports = ReportsApi(dio);
    settings = SettingsApi(dio);
  }

  static Future<void> saveToken(String token) =>
      _storage.write(key: _kTokenKey, value: token);

  static Future<String?> getToken() => _storage.read(key: _kTokenKey);

  static Future<void> clearToken() => _storage.delete(key: _kTokenKey);
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
