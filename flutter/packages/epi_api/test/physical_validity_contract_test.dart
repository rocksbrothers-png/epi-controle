import 'package:epi_api/epi_api.dart';
import 'package:flutter_test/flutter_test.dart';

Map<String, dynamic> summary({
  int pieces = 1,
  int valid = 0,
  int expiring = 1,
  int expired = 0,
  int unknown = 0,
  int eligible = 1,
  int days = 60,
}) => {
  'physical_pieces': pieces,
  'eligible_pieces': eligible,
  'valid': valid,
  'expiring': expiring,
  'expired': expired,
  'unknown': unknown,
  'as_of_date': '2026-10-12',
  'warning_days': days,
  'timezone': 'America/Sao_Paulo',
};

void main() {
  test('catalog never substitutes explicit null or absent physical expiry', () {
    for (final physical in [
      <String, dynamic>{},
      {'effective_validity_date': null},
    ]) {
      final epi = Epi.fromJson({
        'id': 1,
        'name': 'EPI',
        'epi_validity_date': '2099-01-01',
        ...physical,
      });
      expect(epi.manufacturerValidityDate, isNull);
      expect(epi.catalogValidityDate, '2099-01-01');
      expect(epi.isBlockedForDelivery, isTrue);
    }
  });

  test(
    'server calendar and counts override client clock and fixed 30-day windows',
    () {
      final epi = Epi.fromJson({
        'id': 1,
        'name': 'EPI',
        'effective_validity_date': '2026-12-11',
        'available_quantity': 1,
        'physical_validity_summary': summary(),
      });
      expect(epi.manufacturerValidityStatus, 'expiring');
      expect(epi.daysUntilManufacturerValidity, 60);
      expect(
        epi.copyWith(stockQuantity: 20).physicalValiditySummary?.warningDays,
        60,
      );
    },
  );

  test(
    'expiry today remains eligible during the entire backend calendar day',
    () {
      final epi = Epi.fromJson({
        'id': 1,
        'name': 'EPI',
        'effective_validity_date': '2026-10-12',
        'available_quantity': 1,
        'physical_validity_summary': summary(days: 0),
      });
      expect(epi.manufacturerValidityStatus, 'expiring');
      expect(epi.daysUntilManufacturerValidity, 0);
      expect(epi.isBlockedForDelivery, isFalse);
    },
  );

  test('empty physical stock never becomes expired by the catalog', () {
    final epi = Epi.fromJson({
      'id': 1,
      'name': 'EPI',
      'epi_validity_date': '2000-01-01',
      'available_quantity': 0,
      'physical_validity_summary': summary(pieces: 0, expiring: 0, eligible: 0),
    });
    expect(epi.manufacturerValidityStatus, 'empty');
    expect(epi.hasExpiredPhysicalPieces, isFalse);
    expect(epi.hasUnknownPhysicalPieces, isFalse);
  });

  test(
    'StockItem uses the physical date, preserving catalog as a separate field',
    () {
      final item = StockItem.fromJson({
        'id': 1,
        'epi_id': 1,
        'epi_name': 'EPI',
        'status': 'in_stock',
        'physical_expiry_date': '2026-10-11',
        'epi_validity_date': '2099-01-01',
        'eligible_for_delivery': false,
      });
      expect(item.physicalExpiryDate, '2026-10-11');
      expect(item.epiValidityDate, '2026-10-11');
      expect(item.catalogValidityDate, '2099-01-01');
      expect(item.isEligibleCandidate, isFalse);
    },
  );

  test(
    'unknown, invalid, blocked and unclassified items are never candidates',
    () {
      for (final values in [
        {'physical_expiry_date': null, 'eligible_for_delivery': true},
        {'physical_expiry_date': '2026-02-30', 'eligible_for_delivery': true},
        {
          'physical_expiry_date': '2099-01-01',
          'eligible_for_delivery': true,
          'status': 'discarded',
        },
        {'physical_expiry_date': '2099-01-01'},
      ]) {
        final item = StockItem.fromJson({
          'id': 1,
          'epi_id': 1,
          'epi_name': 'EPI',
          'status': 'in_stock',
          'epi_validity_date': '2099-01-01',
          ...values,
        });
        expect(item.isEligibleCandidate, isFalse);
      }
    },
  );
}
