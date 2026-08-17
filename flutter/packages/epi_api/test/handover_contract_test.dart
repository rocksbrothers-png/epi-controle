import 'dart:convert';
import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:epi_api/epi_api.dart';
import 'package:flutter_test/flutter_test.dart';

/// Item 4 — contrato do QR híbrido de entrega (handover). Trava caminho, query,
/// corpo e chaves de resposta que o cliente Flutter consome. A REGRA (projeção
/// segura, idempotência, multi-tenant) é do backend — o app só repassa.
class _CapturingAdapter implements HttpClientAdapter {
  _CapturingAdapter(this.body);
  final Object body;
  RequestOptions? lastRequest;

  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? requestStream,
    Future<void>? cancelFuture,
  ) async {
    lastRequest = options;
    return ResponseBody.fromString(
      jsonEncode(body),
      200,
      headers: {
        Headers.contentTypeHeader: [Headers.jsonContentType],
      },
    );
  }

  @override
  void close({bool force = false}) {}
}

void main() {
  group('DeliveriesApi.handoverLookup', () {
    test('bate no endpoint e lê a chave `handover` (projeção segura)', () async {
      final adapter = _CapturingAdapter({
        'ok': true,
        'handover': {
          'delivery_id': 100,
          'employee_first_name': 'Maria',
          'employee_last_name': 'da Silva Souza',
          'employee_registration': 'MAT-007',
          'epi_name': 'Luva Nitrílica',
          'size': 'M',
          'lot_code': 'LOTE-42',
          'request_id': 1,
          'request_status': 'aprovado',
          'already_confirmed': false,
        },
      });
      final dio = Dio(BaseOptions(baseUrl: 'http://test.local'))
        ..httpClientAdapter = adapter;
      final data = await DeliveriesApi(dio)
          .handoverLookup(actorUserId: 1, code: 'ENTREGA-tok-abc');

      expect(adapter.lastRequest?.path, '/api/deliveries/handover-lookup');
      expect(adapter.lastRequest?.queryParameters['code'], 'ENTREGA-tok-abc');
      expect(adapter.lastRequest?.queryParameters['actor_user_id'], 1);
      expect(data['employee_first_name'], 'Maria');
      expect(data['employee_registration'], 'MAT-007');
      expect(data['lot_code'], 'LOTE-42');
      // Projeção segura: sem CPF/dado pessoal direto.
      expect(data.keys.any((k) => k.toLowerCase().contains('cpf')), isFalse);
    });
  });

  group('DeliveriesApi.handoverConfirm', () {
    test('envia code + actor e lê o resultado', () async {
      final adapter = _CapturingAdapter({
        'ok': true,
        'confirmed': true,
        'already_confirmed': false,
        'confirmed_at': '2026-07-19T10:00:00Z',
      });
      final dio = Dio(BaseOptions(baseUrl: 'http://test.local'))
        ..httpClientAdapter = adapter;
      final res = await DeliveriesApi(dio).handoverConfirm(
        actorUserId: 1,
        code: 'ENTREGA-tok-abc',
        signatureName: 'Maria',
        signatureData: 'data:img',
      );

      expect(adapter.lastRequest?.path, '/api/deliveries/handover-confirm');
      final data = adapter.lastRequest?.data as Map;
      expect(data['code'], 'ENTREGA-tok-abc');
      expect(data['actor_user_id'], 1);
      expect(data['signature_name'], 'Maria');
      expect(res['confirmed'], isTrue);
      expect(res['already_confirmed'], isFalse);
    });

    test('omite assinatura quando vazia', () async {
      final adapter = _CapturingAdapter({'ok': true, 'confirmed': true});
      final dio = Dio(BaseOptions(baseUrl: 'http://test.local'))
        ..httpClientAdapter = adapter;
      await DeliveriesApi(dio)
          .handoverConfirm(actorUserId: 5, code: 'ENTREGA-x');
      final data = adapter.lastRequest?.data as Map;
      expect(data.containsKey('signature_name'), isFalse);
      expect(data.containsKey('signature_data'), isFalse);
    });
  });
}
