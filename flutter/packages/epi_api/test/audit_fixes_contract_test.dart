import 'dart:convert';
import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:epi_api/epi_api.dart';
import 'package:flutter_test/flutter_test.dart';

/// Testes de contrato das correções da auditoria portadas para o app SaaS/Flutter:
///  - Item 1: GET /api/epis/{id}/archival-state + block_and_archive no /archive.
///  - Item 2: GET /api/stock/compliance (fonte única de conformidade).
///
/// A REGRA de negócio é do backend. Aqui travamos apenas o CONTRATO que o
/// cliente Flutter consome (caminho, query, corpo e chaves de resposta), para
/// que Android/iOS/web-flutter falhem o CI se o contrato divergir — sem duplicar
/// lógica no app.
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
  group('StockApi.getStockCompliance (item 2 — fonte única)', () {
    test('bate no endpoint /api/stock/compliance e lê summary/categories',
        () async {
      final adapter = _CapturingAdapter({
        'warning_days': 30,
        'summary': {
          'ca_expired': 2,
          'ca_expiring': 1,
          'product_expired': 3,
          'product_expiring': 0,
          'missing_manufacture': 1,
          'missing_lot': 0,
          'admin_blocked': 4,
        },
        'categories': {
          'ca_expired': <dynamic>[
            {'stock_item_id': 10, 'epi_name': 'Luva'},
          ],
        },
      });
      final dio = Dio(BaseOptions(baseUrl: 'http://test.local'))
        ..httpClientAdapter = adapter;
      final api = StockApi(dio);

      final data = await api.getStockCompliance(
        actorUserId: 1,
        companyId: 7,
        unitId: 3,
      );

      expect(adapter.lastRequest?.path, '/api/stock/compliance');
      expect(adapter.lastRequest?.queryParameters['actor_user_id'], 1);
      expect(adapter.lastRequest?.queryParameters['company_id'], 7);
      expect(adapter.lastRequest?.queryParameters['unit_id'], 3);
      final summary = data['summary'] as Map;
      expect(summary['ca_expired'], 2);
      expect(summary['admin_blocked'], 4);
      expect((data['categories'] as Map)['ca_expired'], hasLength(1));
    });

    test('omite company_id/unit_id quando nulos (escopo do backend)', () async {
      final adapter = _CapturingAdapter({'summary': {}, 'categories': {}});
      final dio = Dio(BaseOptions(baseUrl: 'http://test.local'))
        ..httpClientAdapter = adapter;
      await StockApi(dio).getStockCompliance(actorUserId: 5);
      expect(adapter.lastRequest?.queryParameters.containsKey('company_id'),
          isFalse);
      expect(
          adapter.lastRequest?.queryParameters.containsKey('unit_id'), isFalse);
    });
  });

  group('EpisApi — arquivamento com guarda de saldo (item 1)', () {
    test('getEpiArchivalState lê a chave `archival_state`', () async {
      final adapter = _CapturingAdapter({
        'epi': {'id': 4, 'name': 'Bota', 'status': 'active'},
        'archival_state': {
          'available': 5,
          'in_transit': 1,
          'in_possession': 2,
          'blocked': 0,
          'pending_requests': 1,
          'pending_purchase': 0,
          'returns_total': 3,
          'blockable': 5,
          'has_open_links': true,
        },
      });
      final dio = Dio(BaseOptions(baseUrl: 'http://test.local'))
        ..httpClientAdapter = adapter;
      final state =
          await EpisApi(dio).getEpiArchivalState(4, actorUserId: 1);

      expect(adapter.lastRequest?.path, '/api/epis/4/archival-state');
      expect(state['has_open_links'], isTrue);
      expect(state['available'], 5);
      expect(state['blockable'], 5);
    });

    test('archiveEpi envia block_and_archive no corpo', () async {
      final adapter = _CapturingAdapter({
        'ok': true,
        'archived': true,
        'blocked_stock_items': 5,
      });
      final dio = Dio(BaseOptions(baseUrl: 'http://test.local'))
        ..httpClientAdapter = adapter;
      final res = await EpisApi(dio).archiveEpi(
        4,
        actorUserId: 1,
        reason: 'descontinuado',
        blockAndArchive: true,
      );

      expect(adapter.lastRequest?.path, '/api/epis/4/archive');
      final body = adapter.lastRequest?.data as Map;
      expect(body['block_and_archive'], isTrue);
      expect(body['reason'], 'descontinuado');
      expect(res['blocked_stock_items'], 5);
    });

    test('archiveEpi mantém block_and_archive=false por padrão', () async {
      final adapter = _CapturingAdapter({'ok': true, 'archived': true});
      final dio = Dio(BaseOptions(baseUrl: 'http://test.local'))
        ..httpClientAdapter = adapter;
      await EpisApi(dio).archiveEpi(9, actorUserId: 1);
      final body = adapter.lastRequest?.data as Map;
      expect(body['block_and_archive'], isFalse);
    });
  });
}
