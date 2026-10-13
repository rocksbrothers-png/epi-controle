import 'package:epi_admin/core/bloc/stock_cubit.dart';
import 'package:epi_api/epi_api.dart';
import 'package:flutter_test/flutter_test.dart';

Epi mixed() => Epi.fromJson({
  'id': 1,
  'name': 'EPI mixed',
  'effective_validity_date': '2026-10-02',
  'epi_validity_date': '2099-01-01',
  'available_quantity': 1,
  'physical_validity_summary': {
    'physical_pieces': 4,
    'eligible_pieces': 1,
    'valid': 1,
    'expiring': 1,
    'expired': 1,
    'unknown': 1,
    'as_of_date': '2026-10-12',
    'warning_days': 30,
    'timezone': 'UTC',
  },
});

void main() {
  test(
    'mixed lots retain each category; distinct-EPI counts do not claim individual eligibility',
    () {
      final epi = mixed();
      final state = StockState(epis: [epi]);
      expect(state.manufacturerExpiredCount, 1);
      expect(state.manufacturerExpiringCount, 1);
      expect(state.manufacturerUnknownCount, 1);
      expect(epi.isBlockedForDelivery, isFalse);
      for (final filter in [
        StockComplianceFilter.manufacturerExpired,
        StockComplianceFilter.manufacturerExpiring,
        StockComplianceFilter.manufacturerUnknown,
      ]) {
        expect(
          StockState(epis: [epi], compliance: filter).filtered.map((e) => e.id),
          [1],
        );
      }
    },
  );

  test(
    'no pieces: physical expired and unknown filters stay empty despite expired catalog',
    () {
      final epi = Epi.fromJson({
        'id': 2,
        'name': 'Empty EPI',
        'epi_validity_date': '2000-01-01',
        'available_quantity': 0,
        'physical_validity_summary': {
          'physical_pieces': 0,
          'eligible_pieces': 0,
          'valid': 0,
          'expiring': 0,
          'expired': 0,
          'unknown': 0,
          'as_of_date': '2026-10-12',
          'warning_days': 30,
          'timezone': 'UTC',
        },
      });
      final state = StockState(epis: [epi]);
      expect(state.manufacturerExpiredCount, 0);
      expect(state.manufacturerUnknownCount, 0);
      expect(state.noPhysicalStockCount, 1);
      expect(
        StockState(
          epis: [epi],
          compliance: StockComplianceFilter.manufacturerExpired,
        ).filtered,
        isEmpty,
      );
      expect(
        StockState(
          epis: [epi],
          compliance: StockComplianceFilter.noPhysicalStock,
        ).filtered.map((e) => e.id),
        [2],
      );
    },
  );
}
