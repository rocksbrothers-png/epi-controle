import 'package:epi_api/epi_api.dart';
import 'package:epi_admin/core/bloc/stock_cubit.dart';
import 'package:epi_admin/core/connectivity/connectivity_checker.dart';
import 'package:epi_admin/core/sync/offline_queue.dart';
import 'package:epi_admin/features/stock/domain/repositories/stock_repository.dart';
import 'package:flutter_test/flutter_test.dart';

/// FASE 4 — valida a migração de dados do módulo stock para Cubit→Repository.
/// As leituras (bootstrap) e o movimento passam pelo StockRepository; a
/// orquestração offline (conectividade + fila) é injetada (ConnectivityChecker
/// + OfflineQueue), então os 3 ramos de moveStock são cobertos sem platform
/// channels.
class _FakeStockRepository implements StockRepository {
  _FakeStockRepository(this.snapshot,
      {this.throwOnFetch = false, this.throwOnMove = false});

  final StockSnapshot snapshot;
  final bool throwOnFetch;
  final bool throwOnMove;

  int movementCalls = 0;
  String? lastMovementType;
  int? lastQuantity;

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
  }) async {
    movementCalls++;
    lastMovementType = movementType;
    lastQuantity = quantity;
    if (throwOnMove) throw Exception('network down');
  }
}

/// Conectividade controlada para dirigir os ramos online/offline.
class _FakeConnectivity implements ConnectivityChecker {
  _FakeConnectivity(this._online);
  final bool _online;
  @override
  Future<bool> get isOnline async => _online;
}

/// Fila offline que apenas registra o que foi enfileirado.
class _RecordingQueue implements OfflineQueue {
  final List<Map<String, dynamic>> enqueued = [];
  @override
  Future<void> enqueue({
    required String opType,
    required Map<String, dynamic> payload,
  }) async {
    enqueued.add({'op_type': opType, ...payload});
  }
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

  group('StockCubit.moveStock (online/offline)', () {
    test('offline: enfileira e não chama o repositório (UI otimista mantida)',
        () async {
      final repo = _FakeStockRepository(_snap([_ok(1, 'Capacete')]));
      final queue = _RecordingQueue();
      final cubit = StockCubit(
        repository: repo,
        connectivity: _FakeConnectivity(false),
        offlineQueue: queue,
      );
      await cubit.load();
      await cubit.moveStock(epiId: 1, delta: -3);

      expect(repo.movementCalls, 0, reason: 'offline não toca a rede');
      expect(queue.enqueued, hasLength(1));
      final op = queue.enqueued.first;
      expect(op['op_type'], 'stock_movement');
      expect(op['epi_id'], 1);
      expect(op['movement_type'], 'out');
      expect(op['quantity'], 3);
      // UI otimista: 10 - 3 = 7
      expect(cubit.state.epis.firstWhere((e) => e.id == 1).stockQuantity, 7);
    });

    test('online com sucesso: persiste no repositório e não enfileira',
        () async {
      final repo = _FakeStockRepository(_snap([_ok(1, 'Capacete')]));
      final queue = _RecordingQueue();
      final cubit = StockCubit(
        repository: repo,
        connectivity: _FakeConnectivity(true),
        offlineQueue: queue,
      );
      await cubit.load();
      await cubit.moveStock(epiId: 1, delta: 5);

      expect(repo.movementCalls, 1);
      expect(repo.lastMovementType, 'in');
      expect(repo.lastQuantity, 5);
      expect(queue.enqueued, isEmpty);
    });

    test('online com falha de rede: cai na fila offline', () async {
      final repo = _FakeStockRepository(
        _snap([_ok(1, 'Capacete')]),
        throwOnMove: true,
      );
      final queue = _RecordingQueue();
      final cubit = StockCubit(
        repository: repo,
        connectivity: _FakeConnectivity(true),
        offlineQueue: queue,
      );
      await cubit.load();
      await cubit.moveStock(epiId: 1, delta: -2);

      expect(repo.movementCalls, 1, reason: 'tentou a rede primeiro');
      expect(queue.enqueued, hasLength(1));
      expect(queue.enqueued.first['op_type'], 'stock_movement');
      expect(queue.enqueued.first['quantity'], 2);
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
