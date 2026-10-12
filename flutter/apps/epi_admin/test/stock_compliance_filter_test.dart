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

  // EST-V3.5-F (G02): os contadores/filtro de conformidade do fabricante vêm da
  // validade FÍSICA do lote (effective_validity_date), não do catálogo.
  test('conformidade por LOTE: effective_validity_date rege contadores e filtro', () {
    final porLote = <Epi>[
      Epi.fromJson({
        'id': 10, 'name': 'Lote vencido', 'stock': 5, 'minimum_stock': 1,
        'ca_expiry': _d(200), 'effective_validity_date': _d(-2), 'epi_validity_date': _d(200),
      }),
      Epi.fromJson({
        'id': 11, 'name': 'Lote valido, catalogo vencido', 'stock': 5, 'minimum_stock': 1,
        'ca_expiry': _d(200), 'effective_validity_date': _d(200), 'epi_validity_date': _d(-2),
      }),
    ];
    final s = StockState(epis: porLote);
    expect(s.manufacturerExpiredCount, 1); // só o lote físico vencido conta
    final filtrado = StockState(
        epis: porLote, compliance: StockComplianceFilter.manufacturerExpired);
    expect(filtrado.filtered.map((e) => e.id).toList(), [10]);
  });
}
