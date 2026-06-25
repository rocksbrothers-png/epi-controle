import 'package:epi_api/epi_api.dart';
import 'package:flutter_test/flutter_test.dart';

String _d(int daysFromNow) {
  final dt = DateTime.now().add(Duration(days: daysFromNow));
  return '${dt.year.toString().padLeft(4, '0')}-'
      '${dt.month.toString().padLeft(2, '0')}-'
      '${dt.day.toString().padLeft(2, '0')}';
}

void main() {
  group('Epi — validade do CA e do fabricante (NT 146/2015)', () {
    test('fromJson lê as chaves canônicas do backend', () {
      final epi = Epi.fromJson({
        'id': 1,
        'name': 'Luva Nitrílica',
        'ca': 'CA-1',
        'purchase_code': 'P-1',
        'ca_expiry': _d(40),
        'epi_validity_date': _d(5),
        'stock': 7,
        'minimum_stock': 2,
      });
      expect(epi.caNumber, 'CA-1');
      expect(epi.code, 'P-1');
      expect(epi.stockQuantity, 7);
      expect(epi.caStatus, 'valid');
      expect(epi.manufacturerValidityStatus, 'expiring');
      expect(epi.isBlockedForDelivery, isFalse);
    });

    test('validade do fabricante vencida bloqueia a entrega', () {
      final epi = Epi.fromJson({
        'id': 2,
        'name': 'Bota',
        'ca_expiry': _d(100),
        'epi_validity_date': _d(-3),
        'stock': 1,
      });
      expect(epi.manufacturerValidityStatus, 'expired');
      expect(epi.isBlockedForDelivery, isTrue);
    });

    test('CA vencido com fabricante válido não bloqueia a entrega', () {
      final epi = Epi.fromJson({
        'id': 3,
        'name': 'Capacete',
        'ca_expiry': _d(-10),
        'epi_validity_date': _d(200),
        'stock': 4,
      });
      expect(epi.caStatus, 'expired');
      expect(epi.manufacturerValidityStatus, 'valid');
      expect(epi.isBlockedForDelivery, isFalse);
    });

    test('compat: aceita chaves legadas (ca_expiry_date / stock_quantity)', () {
      final epi = Epi.fromJson({
        'id': 4,
        'name': 'X',
        'ca_expiry_date': _d(-1),
        'stock_quantity': 9,
      });
      expect(epi.stockQuantity, 9);
      expect(epi.caStatus, 'expired');
      expect(epi.manufacturerValidityStatus, isNull);
    });
  });
}
