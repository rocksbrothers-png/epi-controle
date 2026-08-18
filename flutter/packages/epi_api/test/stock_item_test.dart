import 'package:epi_api/epi_api.dart';
import 'package:flutter_test/flutter_test.dart';

/// Parsing de `StockItem` — o modelo compartilhado por
/// `/api/stock/available-items` e `/api/stock/blocked-items` (#246 Lote 1.1).
///
/// O que estes testes protegem: as duas rotas leem a MESMA linha de
/// `epi_stock_items`, e a de bloqueados só acrescenta colunas. Um modelo que
/// exigisse os campos extras quebraria na rota de disponíveis, e dois modelos
/// separados divergiriam no primeiro campo alterado de um lado só.
void main() {
  group('StockItem.fromJson', () {
    test('lê a linha completa de blocked-items', () {
      final item = StockItem.fromJson(const {
        'id': 7,
        'qr_code_value': 'QR-123',
        'epi_id': 42,
        'epi_name': 'Luva nitrílica',
        'status': 'blocked_expired',
        'glove_size': 'M',
        'size': null,
        'uniform_size': null,
        'lot_code': 'L-2026-01',
        'manufacture_date': '2026-01-10',
        'epi_validity_date': '2027-01-10',
        'unit_measure': 'par',
        'unit_name': 'Unidade Centro',
        'unit_id': 3,
        'updated_at': '2026-08-01T10:00:00Z',
      });

      expect(item.id, 7);
      expect(item.epiId, 42);
      expect(item.epiName, 'Luva nitrílica');
      expect(item.status, 'blocked_expired');
      expect(item.qrCodeValue, 'QR-123');
      expect(item.gloveSize, 'M');
      expect(item.lotCode, 'L-2026-01');
      expect(item.unitName, 'Unidade Centro');
      expect(item.unitId, 3);
    });

    test('lê a linha reduzida de available-items sem exigir os extras', () {
      // available-items não seleciona lot_code, unit_name, unit_id nem
      // updated_at. Exigi-los aqui quebraria a aba de disponíveis.
      final item = StockItem.fromJson(const {
        'id': 1,
        'qr_code_value': 'QR-1',
        'epi_id': 9,
        'epi_name': 'Capacete',
        'status': 'in_stock',
        'glove_size': null,
        'size': '58',
        'uniform_size': null,
        'manufacture_date': '2026-02-01',
        'epi_validity_date': '2028-02-01',
      });

      expect(item.status, 'in_stock');
      expect(item.size, '58');
      expect(item.lotCode, isNull);
      expect(item.unitName, isNull);
      expect(item.unitId, isNull);
    });

    test('status ausente cai no default do próprio backend', () {
      // O SQL usa COALESCE(LOWER(esi.status), 'in_stock'); um status vazio no
      // cliente viraria rótulo "desconhecido" para item que está disponível.
      final item = StockItem.fromJson(const {
        'id': 1, 'epi_id': 1, 'epi_name': 'X',
      });
      expect(item.status, 'in_stock');
    });

    test('campos textuais vazios viram null em vez de string vazia', () {
      // Sem isto a UI mostraria separadores soltos (' · · ') para campos que o
      // banco devolve como '' em vez de NULL.
      final item = StockItem.fromJson(const {
        'id': 1, 'epi_id': 1, 'epi_name': 'X', 'status': 'in_stock',
        'qr_code_value': '   ', 'lot_code': '',
      });
      expect(item.qrCodeValue, isNull);
      expect(item.lotCode, isNull);
    });

    test('id e epi_id ausentes não explodem o parsing da lista inteira', () {
      // Uma linha malformada não pode derrubar a tela toda — o resto da lista
      // continua útil.
      final item = StockItem.fromJson(const {'epi_name': 'Sem ids'});
      expect(item.id, 0);
      expect(item.epiId, 0);
    });
  });

  group('displaySize', () {
    test('usa a primeira grade preenchida entre luva, tamanho e uniforme', () {
      expect(
        StockItem.fromJson(const {
          'id': 1, 'epi_id': 1, 'epi_name': 'X', 'glove_size': 'G',
          'size': '42', 'uniform_size': 'GG',
        }).displaySize,
        'G',
      );
      expect(
        StockItem.fromJson(const {
          'id': 1, 'epi_id': 1, 'epi_name': 'X', 'size': '42',
        }).displaySize,
        '42',
      );
    });

    test("'N/A' do backend não vira grade exibida", () {
      // `fetch_epi_size_balance` usa 'N/A' como marcador de ausência; exibi-lo
      // ao operador seria pior que omitir o campo.
      expect(
        StockItem.fromJson(const {
          'id': 1, 'epi_id': 1, 'epi_name': 'X', 'glove_size': 'N/A',
          'size': 'N/A', 'uniform_size': 'N/A',
        }).displaySize,
        isNull,
      );
    });

    test('sem grade nenhuma retorna null', () {
      expect(
        StockItem.fromJson(const {'id': 1, 'epi_id': 1, 'epi_name': 'X'})
            .displaySize,
        isNull,
      );
    });
  });
}
