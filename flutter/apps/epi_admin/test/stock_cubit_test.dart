import 'package:epi_api/epi_api.dart';
import 'package:epi_admin/core/bloc/stock_cubit.dart';
import 'package:epi_admin/features/stock/domain/repositories/stock_repository.dart';
import 'package:flutter_test/flutter_test.dart';

/// FASE 4 — valida a migração de dados do módulo stock para Cubit→Repository.
/// As leituras (bootstrap) e o movimento passam pelo StockRepository; a
/// orquestração offline (fila/conectividade/notificação) segue no cubit e é
/// coberta por testes de integração com platform-mock (follow-up).
class _FakeStockRepository implements StockRepository {
  _FakeStockRepository(this.snapshot, {this.throwOnFetch = false});

  final StockSnapshot snapshot;
  final bool throwOnFetch;

  @override
  Future<StockSnapshot> fetchStock() async {
    if (throwOnFetch) throw Exception('fetch failed');
    return snapshot;
  }

  @override
  Future<void> recordMovement({
    required int actorUserId,
    required int companyId,
    required int unitId,
    required int epiId,
    required String movementType,
    required int quantity,
  }) async {}
}

StockSnapshot _snap(List<Epi> epis) =>
    StockSnapshot(epis: epis, companyId: 1, unitId: 10, actorUserId: 5);

// stock > min → não crítico (evita o ramo de NotificationService no load()).
Epi _ok(int id, String name) =>
    Epi(id: id, name: name, stockQuantity: 10, minimumStock: 2);
Epi _critical(int id, String name) =>
    Epi(id: id, name: name, stockQuantity: 0, minimumStock: 5);

void main() {
  group('StockCubit (arquitetura Repository)', () {
    test('load() popula epis e contexto a partir do snapshot', () async {
      final cubit = StockCubit(repository: _FakeStockRepository(_snap([_ok(1, 'Capacete')])));
      await cubit.load();
      expect(cubit.state.isLoading, isFalse);
      expect(cubit.state.epis.map((e) => e.id), [1]);
      expect(cubit.state.companyId, 1);
      expect(cubit.state.unitId, 10);
      expect(cubit.state.actorUserId, 5);
    });

    test('load() captura erro em estado de erro', () async {
      final cubit = StockCubit(
        repository: _FakeStockRepository(_snap(const []), throwOnFetch: true),
      );
      await cubit.load();
      expect(cubit.state.error, isNotNull);
    });

    test('search() filtra por nome', () async {
      final cubit = StockCubit(
        repository: _FakeStockRepository(_snap([_ok(1, 'Capacete'), _ok(3, 'Bota')])),
      );
      await cubit.load();
      cubit.search('bot');
      expect(cubit.state.filtered.map((e) => e.id), [3]);
    });
  });

  group('StockState (getters)', () {
    test('criticalCount conta EPIs abaixo do mínimo', () {
      final state = StockState(epis: [_critical(2, 'Luva'), _ok(1, 'Capacete')]);
      expect(state.criticalCount, 1);
    });

    test('filtered ordena críticos primeiro', () {
      final state = StockState(epis: [_ok(1, 'Apar'), _critical(2, 'Zeta')]);
      expect(state.filtered.first.id, 2); // crítico antes mesmo com nome maior
    });
  });
}
