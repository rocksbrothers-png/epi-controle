import 'package:epi_api/epi_api.dart';
import 'package:epi_admin/core/bloc/stock_cubit.dart';
import 'package:flutter_test/flutter_test.dart';

String _d(int daysFromNow) {
  final dt = DateTime.now().add(Duration(days: daysFromNow));
  return '${dt.year.toString().padLeft(4, '0')}-'
      '${dt.month.toString().padLeft(2, '0')}-'
      '${dt.day.toString().padLeft(2, '0')}';
}

/// Filtros de conformidade do estoque (NT 146/2015): CA vencido e validade do
/// fabricante próxima/vencida.
void main() {
  final epis = <Epi>[
    Epi(id: 1, name: 'CA vencido', stockQuantity: 5, minimumStock: 1,
        caExpiryDate: _d(-2), manufacturerValidityDate: _d(200)),
    Epi(id: 2, name: 'Fabricante vencido', stockQuantity: 5, minimumStock: 1,
        caExpiryDate: _d(200), manufacturerValidityDate: _d(-2)),
    Epi(id: 3, name: 'Fabricante proximo', stockQuantity: 5, minimumStock: 1,
        caExpiryDate: _d(200), manufacturerValidityDate: _d(10)),
    Epi(id: 4, name: 'Tudo ok', stockQuantity: 5, minimumStock: 1,
        caExpiryDate: _d(200), manufacturerValidityDate: _d(200)),
  ];

  test('contadores de conformidade', () {
    final s = StockState(epis: epis);
    expect(s.caExpiredCount, 1);
    expect(s.manufacturerExpiredCount, 1);
    expect(s.manufacturerExpiringCount, 1);
  });

  test('filtro CA vencido', () {
    final s = StockState(epis: epis, compliance: StockComplianceFilter.caExpired);
    expect(s.filtered.map((e) => e.id).toList(), [1]);
  });

  test('filtro validade do fabricante vencida', () {
    final s = StockState(
        epis: epis, compliance: StockComplianceFilter.manufacturerExpired);
    expect(s.filtered.map((e) => e.id).toList(), [2]);
  });

  test('filtro validade do fabricante próxima', () {
    final s = StockState(
        epis: epis, compliance: StockComplianceFilter.manufacturerExpiring);
    expect(s.filtered.map((e) => e.id).toList(), [3]);
  });

  test('sem filtro retorna todos', () {
    final s = StockState(epis: epis);
    expect(s.filtered.length, 4);
  });
}
