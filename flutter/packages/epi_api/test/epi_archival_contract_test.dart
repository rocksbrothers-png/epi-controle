import 'dart:convert';
import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:epi_api/epi_api.dart';
import 'package:flutter_test/flutter_test.dart';

/// Contrato do arquivamento de EPI com guarda de saldo:
/// `GET /api/epis/{id}/archival-state` e `block_and_archive` no `/archive`.
///
/// A REGRA é do backend — quem decide se há vínculos vivos e se o saldo pode
/// ser bloqueado é `_archive_epi_with_stock_guard` em `modules/epis/service.py`.
/// Aqui se trava apenas o CONTRATO que o cliente Flutter consome (caminho,
/// query, corpo, chaves de resposta), para que Web/Android/iOS falhem no CI se
/// ele divergir, sem duplicar lógica no app.
///
/// No `epi-controle-app` a mesma cobertura vive em
/// `audit_fixes_contract_test.dart`, junto com o contrato de
/// `StockApi.getStockCompliance`. Aqui o arquivo é separado de propósito:
/// `getStockCompliance` ainda não existe neste repositório, e trazer o arquivo
/// inteiro faria o teste referenciar um método inexistente — transformando uma
/// sincronização de duas telas numa importação silenciosa de outra feature.
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
  group('EpisApi — arquivamento com guarda de saldo', () {
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
      final state = await EpisApi(dio).getEpiArchivalState(4, actorUserId: 1);

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
      // O padrão importa: bloquear saldo é ação deliberada, com motivo. Um
      // default `true` faria todo arquivamento comum mexer em estoque.
      final adapter = _CapturingAdapter({'ok': true, 'archived': true});
      final dio = Dio(BaseOptions(baseUrl: 'http://test.local'))
        ..httpClientAdapter = adapter;
      await EpisApi(dio).archiveEpi(9, actorUserId: 1);
      final body = adapter.lastRequest?.data as Map;
      expect(body['block_and_archive'], isFalse);
    });
  });
}
