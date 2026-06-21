import 'package:epi_api/epi_api.dart';
import 'package:epi_admin/core/bloc/purchases_cubit.dart';
import 'package:epi_admin/features/purchases/domain/repositories/purchases_repository.dart';
import 'package:flutter_test/flutter_test.dart';

/// FASE 6 — valida a migração do módulo purchases para Cubit→Repository com um
/// repositório fake (sem ApiClient estático). O `actor_user_id` das POs passou
/// a ser injetado no datasource, então o cubit fica testável sem ApiClient.
class _FakePurchasesRepository implements PurchasesRepository {
  _FakePurchasesRepository({
    this.requests = const [],
    this.orders = const [],
    this.throwOnLoad = false,
  });

  List<PurchaseRequest> requests;
  List<PurchaseDemand> demands = const [];
  List<Map<String, dynamic>> orders;
  bool throwOnLoad;
  Object? throwOnWrite;
  final List<String> calls = [];

  @override
  Future<List<PurchaseRequest>> getPurchaseRequests({String? status}) async {
    calls.add('getRequests');
    if (throwOnLoad) throw Exception('load failed');
    return requests;
  }

  @override
  Future<List<PurchaseDemand>> getPurchaseDemands() async {
    calls.add('getDemands');
    return demands;
  }

  @override
  Future<int> createPurchaseRequest({
    required int unitId,
    required List<Map<String, dynamic>> items,
    required String title,
    String notes = '',
  }) async {
    calls.add('createRequest:$unitId:${items.length}');
    if (throwOnWrite != null) throw throwOnWrite!;
    return 1;
  }

  @override
  Future<List<Map<String, dynamic>>> getPurchaseOrders({String? status}) async {
    calls.add('getOrders:$status');
    if (throwOnLoad) throw Exception('load failed');
    return orders;
  }

  @override
  Future<int> createPurchaseOrder(Map<String, dynamic> body) async {
    calls.add('createPO');
    if (throwOnWrite != null) throw throwOnWrite!;
    return 1;
  }

  @override
  Future<void> reviewPurchaseOrder(int id, Map<String, dynamic> body) async => calls.add('review:$id');

  @override
  Future<void> approvePurchaseOrder(int id, Map<String, dynamic> body) async {
    calls.add('approve:$id');
    if (throwOnWrite != null) throw throwOnWrite!;
  }

  @override
  Future<void> receivePurchaseOrder(int id, Map<String, dynamic> body) async => calls.add('receive:$id');

  @override
  Future<void> resubmitPurchaseOrder(int id, Map<String, dynamic> body) async => calls.add('resubmit:$id');
}

PurchaseRequest _req(int id, {String status = 'open'}) => PurchaseRequest(
      id: id,
      title: 'R$id',
      status: status,
      unitId: 1,
      unitName: 'U',
      createdAt: '2026-01-01',
      items: const [],
    );

void main() {
  group('PurchasesCubit (arquitetura Repository)', () {
    test('load() popula requests', () async {
      final repo = _FakePurchasesRepository(requests: [_req(1), _req(2)]);
      final cubit = PurchasesCubit(repository: repo);
      await cubit.load();
      expect(cubit.state.isLoading, isFalse);
      expect(cubit.state.requests.map((r) => r.id), [1, 2]);
    });

    test('load() captura erro', () async {
      final cubit = PurchasesCubit(repository: _FakePurchasesRepository(throwOnLoad: true));
      await cubit.load();
      expect(cubit.state.error, isNotNull);
      expect(cubit.state.isLoading, isFalse);
    });

    test('loadWithDemands() carrega requests e demands em paralelo', () async {
      final repo = _FakePurchasesRepository(requests: [_req(1)]);
      final cubit = PurchasesCubit(repository: repo);
      await cubit.loadWithDemands();
      expect(cubit.state.requests, hasLength(1));
      expect(repo.calls, containsAll(['getRequests', 'getDemands']));
    });

    test('filterByStatus() filtra a lista exibida', () async {
      final repo = _FakePurchasesRepository(requests: [_req(1, status: 'open'), _req(2, status: 'closed')]);
      final cubit = PurchasesCubit(repository: repo);
      await cubit.load();
      cubit.filterByStatus('open');
      expect(cubit.state.filtered.map((r) => r.id), [1]);
    });

    test('createRequest() chama o repositório e retorna true', () async {
      final repo = _FakePurchasesRepository();
      final cubit = PurchasesCubit(repository: repo);
      final ok = await cubit.createRequest(
        unitId: 3,
        items: const [PurchaseRequestItem(epiId: 1, epiName: 'Luva', quantity: 2)],
        title: 'Reposição',
      );
      expect(ok, isTrue);
      expect(cubit.state.successMessage, isNotNull);
      expect(repo.calls, contains('createRequest:3:1'));
    });

    test('createRequest() em erro retorna false e seta error', () async {
      final repo = _FakePurchasesRepository()..throwOnWrite = Exception('boom');
      final cubit = PurchasesCubit(repository: repo);
      final ok = await cubit.createRequest(unitId: 1, items: const [], title: 'X');
      expect(ok, isFalse);
      expect(cubit.state.error, isNotNull);
      expect(cubit.state.isSubmitting, isFalse);
    });

    test('loadPurchaseOrders() popula POs com filtro de status', () async {
      final repo = _FakePurchasesRepository(orders: [
        {'id': 1, 'status': 'pending_review'},
      ]);
      final cubit = PurchasesCubit(repository: repo);
      await cubit.loadPurchaseOrders(status: 'pending_review');
      expect(cubit.state.purchaseOrders, hasLength(1));
      expect(repo.calls, contains('getOrders:pending_review'));
    });

    test('approvePurchaseOrder() executa a ação e retorna true', () async {
      final repo = _FakePurchasesRepository();
      final cubit = PurchasesCubit(repository: repo);
      final ok = await cubit.approvePurchaseOrder(5, {'decision': 'approved'});
      expect(ok, isTrue);
      expect(repo.calls, contains('approve:5'));
      expect(cubit.state.successMessage, 'OK');
    });

    test('clearMessages() limpa erro e sucesso', () async {
      final repo = _FakePurchasesRepository()..throwOnWrite = Exception('x');
      final cubit = PurchasesCubit(repository: repo);
      await cubit.createRequest(unitId: 1, items: const [], title: 'X');
      expect(cubit.state.error, isNotNull);
      cubit.clearMessages();
      expect(cubit.state.error, isNull);
      expect(cubit.state.successMessage, isNull);
    });
  });
}
