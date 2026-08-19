import 'package:epi_api/epi_api.dart';
import 'package:epi_admin/core/bloc/stock_cubit.dart';
import 'package:epi_admin/core/connectivity/connectivity_checker.dart';
import 'package:epi_admin/core/sync/offline_queue.dart';
import 'package:epi_admin/features/stock/domain/repositories/stock_repository.dart';
import 'package:flutter_test/flutter_test.dart';

/// FASE 4 — arquitetura Cubit→Repository do módulo stock.
///
/// Atualizado na fatia 1.1B (#258): a lista deixou de vir de `bootstrap.epis` e
/// passa por `/api/stock/epis`. O que mudou nestes testes não é cosmético —
/// empresa e unidade agora saem do escopo que o SERVIDOR resolveu por EPI
/// (`companyId`/`unitScopeId`), não de um retrato do login, e o saldo mostrado
/// e movimentado é o da UNIDADE (`unitStockQuantity`).
class _FakeStockRepository implements StockRepository {
  _FakeStockRepository(
    this.epis, {
    this.actorUserId = 5,
    this.throwOnFetch = false,
    this.throwOnMove = false,
  });

  final List<Epi> epis;
  final int actorUserId;
  final bool throwOnFetch;
  final bool throwOnMove;

  int movementCalls = 0;
  String? lastMovementType;
  int? lastQuantity;
  int? lastCompanyId;
  int? lastUnitId;
  int? lastActorUserId;
  final List<String?> nomesConsultados = [];

  @override
  Future<int> currentActorUserId() async => actorUserId;

  @override
  Future<List<Epi>> fetchStockEpis({
    String? name,
    String? section,
    String? manufacturer,
    String? ca,
    String? protection,
  }) async {
    nomesConsultados.add(name);
    if (throwOnFetch) throw Exception('fetch failed');
    return epis;
  }

  // `fetchStock()` (bootstrap) segue no contrato até a fatia 1.1E, mas o cubit
  // não pode mais chamá-lo. Lançar aqui é o teste: se alguém reintroduzir a
  // leitura do bootstrap, os casos de load() abaixo quebram em vez de passar
  // silenciosamente com dados de outra fonte.
  @override
  // ignore: deprecated_member_use_from_same_package
  Future<StockSnapshot> fetchStock() =>
      throw UnimplementedError('bootstrap.epis não é mais fonte de estoque');

  // Consultas da fatia 1.1 (#246). Estes testes cobrem a lista e o movimento;
  // lançar aqui é melhor que devolver lista vazia, que passaria despercebido
  // se alguém escrevesse um teste de consulta por engano contra este fake.
  @override
  Future<List<StockItem>> fetchAvailableItems({
    required int actorUserId,
    required int epiId,
  }) =>
      throw UnimplementedError('ver stock_query_cubit_test.dart');

  @override
  Future<BlockedStockItems> fetchBlockedItems({required int actorUserId}) =>
      throw UnimplementedError('ver stock_query_cubit_test.dart');

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
    lastCompanyId = companyId;
    lastUnitId = unitId;
    lastActorUserId = actorUserId;
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

// Saldo da unidade 10 dentro da empresa 1; criticidade CORPORATIVA vem pronta
// do backend — o cliente não recalcula.
Epi _ok(int id, String name) => Epi(
      id: id,
      name: name,
      companyId: 1,
      unitScopeId: 10,
      unitStockQuantity: 10,
      companyStockQuantity: 40,
      minimumStock: 2,
      stockQuantity: 40,
      isCompanyStockCritical: false,
    );

Epi _critical(int id, String name) => Epi(
      id: id,
      name: name,
      companyId: 1,
      unitScopeId: 10,
      unitStockQuantity: 0,
      companyStockQuantity: 3,
      minimumStock: 5,
      stockQuantity: 3,
      isCompanyStockCritical: true,
    );

void main() {
  group('StockCubit (fonte única: /api/stock/epis)', () {
    test('load() popula epis e deriva empresa/unidade do escopo do servidor',
        () async {
      final repo = _FakeStockRepository([_ok(1, 'Capacete')]);
      final cubit = StockCubit(repository: repo);
      await cubit.load();

      expect(cubit.state.isLoading, isFalse);
      expect(cubit.state.epis.map((e) => e.id), [1]);
      // Não vêm mais de um snapshot de login: saem do EPI que o servidor
      // devolveu, já com a unidade que ele usou para calcular o saldo.
      expect(cubit.state.companyId, 1);
      expect(cubit.state.unitId, 10);
      expect(cubit.state.actorUserId, 5);
    });

    test('load() carimba o ator que a camada de dados resolveu', () async {
      // Regressão da fatia 1.1B: o ator vinha junto do bootstrap. Sem ele, as
      // consultas de itens, o movimento e a fila offline sairiam com
      // `actor_user_id=0`. Um ator diferente do padrão prova que o valor
      // atravessa de verdade, em vez de coincidir com um default do teste.
      final repo = _FakeStockRepository([_ok(1, 'Capacete')], actorUserId: 99);
      final cubit = StockCubit(repository: repo);
      await cubit.load();

      expect(cubit.state.actorUserId, 99);
    });

    test('load() sem unidade resolvida não inventa escopo', () async {
      // master_admin/general_admin sem unidade selecionada: o backend manda
      // `unit_scope_id: null`. Cair num id qualquer faria a movimentação
      // incidir sobre uma unidade que ninguém escolheu.
      const semUnidade = Epi(
        id: 1,
        name: 'Capacete',
        companyId: 7,
        unitScopeId: null,
        unitStockQuantity: null,
        companyStockQuantity: 40,
        minimumStock: 2,
      );
      final cubit = StockCubit(repository: _FakeStockRepository([semUnidade]));
      await cubit.load();

      expect(cubit.state.companyId, 0);
      expect(cubit.state.unitId, 0);
    });

    test('load() captura erro em estado de erro', () async {
      final cubit = StockCubit(
        repository: _FakeStockRepository(const [], throwOnFetch: true),
      );
      await cubit.load();
      expect(cubit.state.error, isNotNull);
    });

    test('search() delega o filtro por nome ao servidor', () async {
      // O filtro é do backend. Refazê-lo aqui divergiria dele em acentuação e
      // maiúsculas, e mostraria resultado diferente da mesma busca no Web.
      final repo = _FakeStockRepository([_ok(3, 'Bota')]);
      final cubit = StockCubit(repository: repo);
      await cubit.load();
      await cubit.search('bot');

      expect(repo.nomesConsultados, [null, 'bot']);
      expect(cubit.state.query, 'bot');
      expect(cubit.state.filtered.map((e) => e.id), [3]);
    });
  });

  group('StockCubit.moveStock (online/offline)', () {
    test('offline: enfileira e não chama o repositório (UI otimista mantida)',
        () async {
      final repo = _FakeStockRepository([_ok(1, 'Capacete')]);
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
      // A operação é carimbada com o ator da sessão, não com 0.
      expect(op['actor_user_id'], 5);
      expect(op['unit_id'], 10);
      // UI otimista sobre o saldo da UNIDADE (10 - 3 = 7). O corporativo não
      // se move aqui: quem o recalcula é o backend.
      final epi = cubit.state.epis.firstWhere((e) => e.id == 1);
      expect(epi.unitStockQuantity, 7);
      expect(epi.companyStockQuantity, 40);
    });

    test('online com sucesso: persiste no repositório e não enfileira',
        () async {
      final repo = _FakeStockRepository([_ok(1, 'Capacete')]);
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
      expect(repo.lastActorUserId, 5);
      // O movimento incide sobre a unidade que o servidor resolveu para o EPI.
      expect(repo.lastCompanyId, 1);
      expect(repo.lastUnitId, 10);
      expect(queue.enqueued, isEmpty);
    });

    test('online com falha de rede: cai na fila offline', () async {
      final repo = _FakeStockRepository(
        [_ok(1, 'Capacete')],
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

    test('sem saldo de unidade o otimismo não inventa número', () async {
      // `unitStockQuantity == null` significa "não há unidade", não zero.
      // Somar delta a isso escreveria um saldo local que ninguém apurou.
      const semUnidade = Epi(
        id: 1,
        name: 'Capacete',
        companyId: 7,
        companyStockQuantity: 40,
        minimumStock: 2,
      );
      final cubit = StockCubit(
        repository: _FakeStockRepository([semUnidade]),
        connectivity: _FakeConnectivity(true),
        offlineQueue: _RecordingQueue(),
      );
      await cubit.load();
      await cubit.moveStock(epiId: 1, delta: -3);

      expect(cubit.state.epis.single.unitStockQuantity, isNull);
    });
  });

  group('StockState (getters)', () {
    test('criticalCount usa a criticidade corporativa do backend', () {
      final state = StockState(epis: [_critical(2, 'Luva'), _ok(1, 'Capacete')]);
      expect(state.criticalCount, 1);
    });

    test('criticalCount não recalcula a partir do saldo da unidade', () {
      // O caso que motivou a mudança: mínimo 100, quatro unidades com 50 cada.
      // A empresa tem 200 e está saudável; comparar 50 <= 100 marcaria como
      // crítico um EPI que só está distribuído.
      const distribuido = Epi(
        id: 1,
        name: 'Capacete',
        companyId: 1,
        unitScopeId: 10,
        unitStockQuantity: 50,
        companyStockQuantity: 200,
        stockQuantity: 200,
        minimumStock: 100,
        isCompanyStockCritical: false,
      );
      expect(StockState(epis: [distribuido]).criticalCount, 0);
    });

    test('filtered ordena críticos primeiro', () {
      final state = StockState(epis: [_ok(1, 'Apar'), _critical(2, 'Zeta')]);
      expect(state.filtered.first.id, 2); // crítico antes mesmo com nome maior
    });
  });
}
