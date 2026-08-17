import 'dart:convert';

import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart' show visibleForTesting;
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:epi_api/epi_api.dart';
import '../observability/app_monitoring.dart';
import '../session/session_context.dart';

const _kTokenKey       = 'access_token';
const _kRefreshKey     = 'refresh_token';
const _kPermissionsKey = 'user_permissions';
const _kSessionContextKey = 'session_context';

class ApiClient {
  ApiClient._();

  /// Dio principal (com interceptors) — usado para reexecutar a request
  /// original após um refresh bem-sucedido.
  static late final Dio _dio;

  /// Dio "cru" (sem interceptors) exclusivo para `POST /api/auth/refresh`.
  /// Separado para nunca enviar o access token expirado nem recursar no
  /// interceptor de Bearer/refresh.
  static late final Dio _refreshDio;

  static late final AuthApi auth;
  static late final CompaniesApi companies;
  static late final LegalEntitiesApi legalEntities;
  static late final OutsourcedCompaniesApi outsourcedCompanies;
  static late final DeliveriesApi deliveries;
  static late final DevolutionsApi devolutions;
  static late final FichasApi fichas;
  static late final PortalApi portal;
  static late final PurchasesApi purchases;
  static late final ReportsApi reports;
  static late final SettingsApi settings;
  static late final FeedbackApi feedback;
  static late final StockApi stock;
  static late final UsersApi users;
  static late final UnitsApi units;
  static late final EmployeesApi employees;
  static late final EpisApi epis;
  static late final SubscriptionsApi subscriptions;
  static late final MyCompanyApi myCompany;
  static late final FlutterSecureStorage _storage;

  /// Usuário autenticado, enviado como `actor_user_id` nas rotas de admin.
  ///
  /// Vem **da sessão** — nunca de uma lista de usuários. O backend compara este
  /// valor com o `sub` do JWT e recusa com "Dados de autenticação
  /// inconsistentes" se divergirem, então qualquer outra origem produz 401.
  ///
  /// Antes ele só era preenchido como efeito colateral de abrir a tela de
  /// Colaboradores, e com `bootstrap.users.first` — o primeiro usuário da
  /// empresa, não quem estava logado. Quem abrisse CNPJs (ou qualquer tela que
  /// não passasse por Colaboradores antes) mandava `actor_user_id=0` e tomava
  /// 401. É por isso que a lista aparecia vazia.
  ///
  /// Mantido `private set` para que o único caminho de escrita seja
  /// [_applySessionActor], chamado por todo ponto que grava, lê ou limpa a
  /// sessão.
  static int get actorUserId => _actorUserId;
  static int _actorUserId = 0;

  static void _applySessionActor(SessionContext? context) {
    _actorUserId = context?.userId ?? 0;
  }

  /// Base URL configurada no init — usada para montar links autenticados por
  /// querystring (ex.: download de PDF aberto pelo navegador).
  static String baseUrl = '';

  static Future<void> init({required String baseUrl}) async {
    ApiClient.baseUrl = baseUrl;
    _storage = const FlutterSecureStorage();
    final dio = Dio(BaseOptions(
      baseUrl: baseUrl,
      connectTimeout: const Duration(seconds: 10),
      receiveTimeout: const Duration(seconds: 30),
    ));
    _dio = dio;
    _refreshDio = Dio(BaseOptions(
      baseUrl: baseUrl,
      connectTimeout: const Duration(seconds: 10),
      receiveTimeout: const Duration(seconds: 30),
    ));
    dio.interceptors.add(_BearerInterceptor());
    dio.interceptors.add(_RetryInterceptor(dio));
    auth = AuthApi(dio, baseUrl: baseUrl);
    companies = CompaniesApi(dio);
    legalEntities = LegalEntitiesApi(dio);
    outsourcedCompanies = OutsourcedCompaniesApi(dio);
    deliveries = DeliveriesApi(dio);
    devolutions = DevolutionsApi(dio);
    fichas = FichasApi(dio);
    portal = PortalApi(dio);
    purchases = PurchasesApi(dio);
    reports = ReportsApi(dio);
    settings = SettingsApi(dio);
    feedback = FeedbackApi(dio);
    stock = StockApi(dio);
    users = UsersApi(dio);
    units = UnitsApi(dio);
    employees = EmployeesApi(dio);
    epis = EpisApi(dio);
    subscriptions = SubscriptionsApi(dio);
    myCompany = MyCompanyApi(dio);
  }

  static Future<void> saveToken(String token) =>
      _storage.write(key: _kTokenKey, value: token);

  static Future<String?> getToken() => _storage.read(key: _kTokenKey);

  static Future<void> clearToken() => _storage.delete(key: _kTokenKey);

  static Future<void> saveRefreshToken(String token) =>
      _storage.write(key: _kRefreshKey, value: token);

  static Future<String?> getRefreshToken() => _storage.read(key: _kRefreshKey);

  static Future<void> clearRefreshToken() => _storage.delete(key: _kRefreshKey);

  /// Limpa toda a sessão local (token, refresh e permissões).
  static Future<void> clearSession() async {
    await clearToken();
    await clearRefreshToken();
    await clearPermissions();
    await clearSessionContext();
  }

  static Future<void> savePermissions(List<String> permissions) =>
      _storage.write(key: _kPermissionsKey, value: permissions.join(','));

  static Future<List<String>> getPermissions() async {
    final raw = await _storage.read(key: _kPermissionsKey);
    if (raw == null || raw.isEmpty) return const [];
    return raw.split(',');
  }

  static Future<void> clearPermissions() =>
      _storage.delete(key: _kPermissionsKey);

  static Future<void> saveSessionContext(SessionContext context) {
    _applySessionActor(context);
    return _storage.write(
      key: _kSessionContextKey,
      value: jsonEncode(context.toJson()),
    );
  }

  static Future<SessionContext> getSessionContext() async {
    final raw = await _storage.read(key: _kSessionContextKey);
    if (raw == null || raw.isEmpty) return SessionContext.empty;
    try {
      final context = SessionContext.fromJson(
        (jsonDecode(raw) as Map).cast<String, dynamic>(),
      );
      // Restaurar a sessão do armazenamento também restaura o ator: sem
      // isto, reabrir o app com sessão válida voltaria a mandar 0.
      _applySessionActor(context);
      return context;
    } on Object {
      return SessionContext.empty;
    }
  }

  static Future<void> clearSessionContext() {
    _applySessionActor(null);
    return _storage.delete(key: _kSessionContextKey);
  }

  /// Reexecuta uma request (usado pelo interceptor após refresh bem-sucedido).
  static Future<Response<dynamic>> retry(RequestOptions options) =>
      _dio.fetch(options);

  /// Seam de teste: expõe o Dio principal (com os interceptors de Bearer/refresh)
  /// para que um teste possa trocar o `httpClientAdapter` e dirigir o fluxo
  /// 401 → refresh → retry ponta-a-ponta. Não usar em produção.
  @visibleForTesting
  static Dio get debugDio => _dio;

  /// Seam de teste: expõe o Dio "cru" do refresh (`POST /api/auth/refresh`).
  @visibleForTesting
  static Dio get debugRefreshDio => _refreshDio;

  /// Chama `POST /api/auth/refresh` pelo Dio cru (sem interceptors).
  static Future<RefreshResponse> refreshSession(String refreshToken) async {
    final resp = await _refreshDio.post<Map<String, dynamic>>(
      '/api/auth/refresh',
      data: {'refresh_token': refreshToken},
    );
    return RefreshResponse.fromJson(resp.data ?? const {});
  }

  /// Chama `GET /api/auth/me` pelo Dio principal (com interceptors: anexa o
  /// Bearer e faz refresh transparente em 401). Fora do retrofit de propósito —
  /// o gerador não lida bem com retorno `Map<String, dynamic>`.
  static Future<Map<String, dynamic>> fetchMe() async {
    final resp = await _dio.get<Map<String, dynamic>>('/api/auth/me');
    return resp.data ?? const {};
  }

  /// Cria uma empresa (tenant) via `POST /api/companies`. Fora do retrofit de
  /// propósito — evita regenerar o cliente gerado (`.g.dart`) apenas para um
  /// endpoint de escrita. Retorna a mensagem de erro do backend (envelope
  /// `{"error":{"message":...}}`) numa `ApiException` quando a request falha.
  static Future<void> createCompany(Map<String, dynamic> data) async {
    try {
      await _dio.post<Map<String, dynamic>>('/api/companies', data: data);
    } on DioException catch (e) {
      throw ApiException(_extractErrorMessage(e));
    }
  }

  /// Troca a senha do próprio usuário (encerra a política de senha temporária
  /// no backend). Usado pela tela de troca obrigatória no 1º acesso.
  static Future<void> changePassword({
    required String currentPassword,
    required String newPassword,
  }) async {
    try {
      await _dio.post<Map<String, dynamic>>('/api/change-password', data: {
        'actor_user_id': actorUserId,
        'current_password': currentPassword,
        'new_password': newPassword,
      });
    } on DioException catch (e) {
      throw ApiException(_extractErrorMessage(e));
    }
  }

  /// Extrai a mensagem do envelope de erro do backend. Tolera os dois formatos
  /// em uso: `{"error":{"message":...}}` e `{"error":"..."}`.
  static String _extractErrorMessage(DioException e) {
    final data = e.response?.data;
    if (data is Map) {
      final err = data['error'];
      if (err is Map && err['message'] is String) {
        return err['message'] as String;
      }
      if (err is String && err.isNotEmpty) return err;
      if (data['message'] is String) return data['message'] as String;
    }
    return e.message ?? 'Erro ao comunicar com o servidor';
  }
}

/// Erro de negócio devolvido pela API, já com a mensagem pronta para exibição.
class ApiException implements Exception {
  ApiException(this.message);
  final String message;
  @override
  String toString() => message;
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

/// Injeta o Bearer token e, em 401, tenta **refresh automático** do access
/// token via `POST /api/auth/refresh`, reexecutando a request original. Só
/// desloga (limpa a sessão) quando não há refresh token ou o refresh falha.
///
/// Single-flight: múltiplas requests que recebem 401 ao mesmo tempo compartilham
/// um único refresh em voo (evita "estouro" de chamadas a `/auth/refresh`).
class _BearerInterceptor extends Interceptor {
  /// Refresh em andamento, compartilhado entre requests concorrentes.
  static Future<bool>? _inFlightRefresh;

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
    final options = err.requestOptions;
    // Observabilidade: registra a instabilidade da API (status 0 = rede).
    AppMonitoring.instance
        .recordApiResult(options.path, err.response?.statusCode ?? 0);
    final isUnauthorized = err.response?.statusCode == 401;
    final alreadyRetried = options.extra['_retriedAfterRefresh'] == true;

    // Não tentar refresh para os próprios endpoints de auth (evita recursão)
    // nem repetir após uma tentativa já feita nesta request.
    if (!isUnauthorized || alreadyRetried || _isAuthEndpoint(options.path)) {
      return handler.next(err);
    }

    final refreshed = await _ensureRefreshed();
    if (!refreshed) {
      // Refresh impossível/falhou → derruba a sessão; o app redireciona ao login.
      await ApiClient.clearSession();
      return handler.next(err);
    }

    // Reexecuta a request original (o onRequest reanexa o novo Bearer).
    options.extra['_retriedAfterRefresh'] = true;
    try {
      handler.resolve(await ApiClient.retry(options));
    } on DioException catch (e) {
      handler.next(e);
    }
  }

  bool _isAuthEndpoint(String path) =>
      path.contains('/api/auth/refresh') ||
      path.endsWith('/api/login') ||
      path.endsWith('/api/auth/login');

  /// Garante no máximo um refresh em voo por vez.
  Future<bool> _ensureRefreshed() =>
      _inFlightRefresh ??= _doRefresh().whenComplete(() => _inFlightRefresh = null);

  Future<bool> _doRefresh() async {
    final refreshToken = await ApiClient.getRefreshToken();
    if (refreshToken == null || refreshToken.isEmpty) return false;
    try {
      final resp = await ApiClient.refreshSession(refreshToken);
      final token = resp.token;
      if (token.isEmpty) return false;
      await ApiClient.saveToken(token);
      final rotated = resp.refreshToken;
      if (rotated != null && rotated.isNotEmpty) {
        await ApiClient.saveRefreshToken(rotated);
      }
      return true;
    } on DioException {
      return false;
    } on Object {
      return false;
    }
  }
}
