import 'package:epi_api/epi_api.dart';
import 'package:flutter_test/flutter_test.dart';

/// Contrato do BootstrapResponse para o KPI `pending_purchases` (dashboard).
void main() {
  group('BootstrapResponse.pendingPurchases', () {
    test('lê pending_purchases do topo do payload', () {
      final res = BootstrapResponse.fromJson(const {
        'ok': true,
        'units': <dynamic>[],
        'employees': <dynamic>[],
        'epis': <dynamic>[],
        'users': <dynamic>[],
        'alerts': <dynamic>[],
        'deliveries': <dynamic>[],
        'pending_purchases': 7,
      });
      expect(res.pendingPurchases, 7);
    });

    test('default 0 quando ausente', () {
      final res = BootstrapResponse.fromJson(const {
        'units': <dynamic>[],
        'employees': <dynamic>[],
        'epis': <dynamic>[],
        'users': <dynamic>[],
        'alerts': <dynamic>[],
        'deliveries': <dynamic>[],
      });
      expect(res.pendingPurchases, 0);
    });

    test('tolera envelope {data:{...}}', () {
      final res = BootstrapResponse.fromJson(const {
        'data': {
          'units': <dynamic>[],
          'employees': <dynamic>[],
          'epis': <dynamic>[],
          'users': <dynamic>[],
          'alerts': <dynamic>[],
          'deliveries': <dynamic>[],
          'pending_purchases': 3,
        },
      });
      expect(res.pendingPurchases, 3);
    });
  });
}
