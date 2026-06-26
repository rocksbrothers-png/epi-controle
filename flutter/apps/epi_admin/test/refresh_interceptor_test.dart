import 'dart:convert';

import 'package:dio/dio.dart';
import 'package:epi_admin/core/api/api_client.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';

/// Hardening — refresh-on-401 ponta-a-ponta.
///
/// Dirige o fluxo real do `_BearerInterceptor` (anexar Bearer → 401 → refresh
/// único → reexecutar a request com o novo token) sem rede nem plataforma:
///  - HTTP: um [HttpClientAdapter] roteirizado injetado nos Dios reais do
///    `ApiClient` (via `debugDio`/`debugRefreshDio`), que responde conforme o
///    token anexado;
///  - storage: o canal de método do `flutter_secure_storage` é mockado por um
///    `Map` em memória, então `saveToken`/`getRefreshToken` etc. funcionam.
///
/// Não exige `http_mock_adapter` nem device — roda no Flutter CI puro.
class _ScriptedAdapter implements HttpClientAdapter {
  _ScriptedAdapter();

  /// Quando true, `POST /api/auth/refresh` responde 401 (refresh inválido).
  bool failRefresh = false;

  /// Atraso opcional no refresh — usado para forçar concorrência (single-flight).
  Duration refreshDelay = Duration.zero;

  int refreshCalls = 0;
  int meCallsWithOldToken = 0;
  int meCallsWithNewToken = 0;

  static const _jsonHeaders = <String, List<String>>{
    Headers.contentTypeHeader: ['application/json'],
  };

  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? requestStream,
    Future<void>? cancelFuture,
  ) async {
    final path = options.path;
    final authorization = options.headers['Authorization'] as String?;

    if (path.contains('/api/auth/refresh')) {
      refreshCalls++;
      if (refreshDelay > Duration.zero) {
        await Future<void>.delayed(refreshDelay);
      }
      if (failRefresh) {
        return ResponseBody.fromString(
          jsonEncode({'error': 'invalid_refresh'}),
          401,
          headers: _jsonHeaders,
        );
      }
      return ResponseBody.fromString(
        jsonEncode({'token': 'new-access', 'refresh_token': 'new-refresh'}),
        200,
        headers: _jsonHeaders,
      );
    }

    if (path.contains('/api/auth/me')) {
      if (authorization == 'Bearer new-access') {
        meCallsWithNewToken++;
        return ResponseBody.fromString(
          jsonEncode({'user': {'id': 1, 'name': 'Ana'}}),
          200,
          headers: _jsonHeaders,
        );
      }
      meCallsWithOldToken++;
      return ResponseBody.fromString(
        jsonEncode({'error': 'expired'}),
        401,
        headers: _jsonHeaders,
      );
    }

    return ResponseBody.fromString('{}', 404, headers: _jsonHeaders);
  }

  @override
  void close({bool force = false}) {}
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  const storageChannel =
      MethodChannel('plugins.it_nomads.com/flutter_secure_storage');
  final store = <String, String>{};

  setUpAll(() async {
    await ApiClient.init(baseUrl: 'https://test.local');
  });

  late _ScriptedAdapter adapter;

  setUp(() async {
    store.clear();
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(storageChannel, (call) async {
      final args = (call.arguments as Map?) ?? const {};
      switch (call.method) {
        case 'read':
          return store[args['key'] as String];
        case 'write':
          store[args['key'] as String] = args['value'] as String;
          return null;
        case 'delete':
          store.remove(args['key'] as String);
          return null;
        case 'containsKey':
          return store.containsKey(args['key'] as String);
        case 'readAll':
          return Map<String, String>.from(store);
        case 'deleteAll':
          store.clear();
          return null;
        default:
          return null;
      }
    });

    adapter = _ScriptedAdapter();
    ApiClient.debugDio.httpClientAdapter = adapter;
    ApiClient.debugRefreshDio.httpClientAdapter = adapter;

    await ApiClient.saveToken('old-access');
    await ApiClient.saveRefreshToken('refresh-1');
  });

  tearDown(() {
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(storageChannel, null);
  });

  test('401 dispara refresh e reexecuta a request com o novo token', () async {
    final me = await ApiClient.fetchMe();

    expect(me['user'], isNotNull);
    expect(adapter.refreshCalls, 1);
    expect(adapter.meCallsWithOldToken, 1, reason: 'a 1ª tentativa leva o token velho');
    expect(adapter.meCallsWithNewToken, 1, reason: 'o retry leva o token renovado');
    // Tokens rotacionados foram persistidos.
    expect(await ApiClient.getToken(), 'new-access');
    expect(await ApiClient.getRefreshToken(), 'new-refresh');
  });

  test('requests concorrentes compartilham um único refresh (single-flight)',
      () async {
    adapter.refreshDelay = const Duration(milliseconds: 50);

    final results = await Future.wait([
      ApiClient.fetchMe(),
      ApiClient.fetchMe(),
      ApiClient.fetchMe(),
    ]);

    for (final r in results) {
      expect(r['user'], isNotNull);
    }
    expect(adapter.refreshCalls, 1, reason: 'um refresh em voo para todas');
    expect(adapter.meCallsWithNewToken, 3);
    expect(await ApiClient.getToken(), 'new-access');
  });

  test('refresh inválido limpa a sessão e propaga o 401', () async {
    adapter.failRefresh = true;

    await expectLater(ApiClient.fetchMe(), throwsA(isA<DioException>()));

    expect(adapter.refreshCalls, 1);
    // Sessão derrubada → o app redireciona ao login.
    expect(await ApiClient.getToken(), isNull);
    expect(await ApiClient.getRefreshToken(), isNull);
  });

  test('sem refresh token não tenta refresh e propaga o 401', () async {
    await ApiClient.clearRefreshToken();

    await expectLater(ApiClient.fetchMe(), throwsA(isA<DioException>()));

    expect(adapter.refreshCalls, 0);
    expect(await ApiClient.getToken(), isNull);
  });
}
