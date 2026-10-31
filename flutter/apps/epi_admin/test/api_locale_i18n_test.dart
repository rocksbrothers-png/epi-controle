import 'dart:convert';
import 'package:dio/dio.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:epi_admin/core/api/api_client.dart';

class CaptureAdapter implements HttpClientAdapter {
  final requests = <RequestOptions>[];
  bool expireOnce = false;
  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? stream,
    Future<void>? cancel,
  ) async {
    requests.add(options);
    if (expireOnce && options.path == '/api/probe') {
      expireOnce = false;
      return ResponseBody.fromString(
        '{"error":"expired"}',
        401,
        headers: {
          Headers.contentTypeHeader: ['application/json'],
        },
      );
    }
    final body = options.path == '/api/auth/refresh'
        ? {'token': 'new-access', 'refresh_token': 'new-refresh'}
        : {'ok': true};
    return ResponseBody.fromString(
      jsonEncode(body),
      200,
      headers: {
        Headers.contentTypeHeader: ['application/json'],
      },
    );
  }

  @override
  void close({bool force = false}) {}
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  var locale = 'pt-BR';
  final store = <String, String>{};
  late CaptureAdapter main, refresh;
  setUpAll(() async {
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(
          const MethodChannel('plugins.it_nomads.com/flutter_secure_storage'),
          (call) async {
            final args = (call.arguments as Map?) ?? {};
            final key = args['key'] as String?;
            switch (call.method) {
              case 'read':
                return store[key];
              case 'write':
                store[key!] = args['value'] as String;
                return null;
              case 'delete':
                store.remove(key);
                return null;
            }
            return null;
          },
        );
    await ApiClient.init(
      baseUrl: 'https://test.local',
      localeTag: () => locale,
    );
  });
  setUp(() async {
    main = CaptureAdapter();
    refresh = CaptureAdapter();
    ApiClient.debugDio.httpClientAdapter = main;
    ApiClient.debugRefreshDio.httpClientAdapter = refresh;
    store.clear();
    locale = 'pt-BR';
    await ApiClient.saveToken('old-access');
    await ApiClient.saveRefreshToken('old-refresh');
  });
  test(
    'each request uses effective existing Flutter locale without changing body or actor',
    () async {
      final payload = {
        'actor_user_id': 42,
        'company_id': 41,
        'unit_id': 43,
        'price': 1234.56,
        'status': 'confirmed',
      };
      final before = jsonEncode(payload);
      for (final tag in ['pt-BR', 'en-US', 'es-ES', 'fr-FR', 'no-NO']) {
        locale = tag;
        await ApiClient.debugDio.post(
          '/api/probe',
          data: payload,
          options: Options(headers: {'X-Probe': 'original'}),
        );
        final request = main.requests.last;
        expect(request.headers['Accept-Language'], tag);
        expect(request.headers['Authorization'], 'Bearer old-access');
        expect(request.headers['X-Probe'], 'original');
        expect(request.data, payload);
        expect(jsonEncode(payload), before);
      }
    },
  );
  test(
    '401 refresh and retry keep locale and canonical payload; refresh carries no Bearer',
    () async {
      locale = 'no-NO';
      main.expireOnce = true;
      final payload = {'actor_user_id': 42, 'quantity': 7};
      await ApiClient.debugDio.post('/api/probe', data: payload);
      expect(main.requests.length, 2);
      expect(refresh.requests.length, 1);
      expect(refresh.requests.single.headers['Accept-Language'], 'no-NO');
      expect(
        refresh.requests.single.headers.containsKey('Authorization'),
        isFalse,
      );
      expect(refresh.requests.single.data, {'refresh_token': 'old-refresh'});
      expect(main.requests.last.headers['Accept-Language'], 'no-NO');
      expect(main.requests.last.headers['Authorization'], 'Bearer new-access');
      expect(main.requests.last.data, payload);
    },
  );
  test(
    'unsupported callback value cannot introduce an arbitrary language header',
    () async {
      locale = 'zz-ZZ';
      await ApiClient.debugDio.get('/api/probe');
      expect(
        main.requests.single.headers.containsKey('Accept-Language'),
        isFalse,
      );
    },
  );
}
