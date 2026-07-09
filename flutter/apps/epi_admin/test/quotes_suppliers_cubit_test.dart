import 'package:epi_admin/features/purchases/domain/repositories/purchases_repository.dart';
import 'package:epi_admin/features/purchases/presentation/quotes_cubit.dart';
import 'package:epi_admin/features/purchases/presentation/suppliers_cubit.dart';
import 'package:flutter_test/flutter_test.dart';

/// FASE F3 — cubits de fornecedores e cotações. O app não tem regra de
/// negócio local: os testes validam apenas orquestração de estado e as
/// chamadas ao repositório (comparação/preços vêm prontos do backend).
class _StubRepo implements PurchasesRepository {
  final List<String> calls = [];
  bool throwOnLoad = false;
  List<Map<String, dynamic>> suppliers = const [];
  List<Map<String, dynamic>> products = const [];
  Map<String, dynamic> quotesResponse = const {'items': [], 'comparison': {}};
  Map<String, dynamic> selectResponse = const {'po_draft': {}};

  @override
  dynamic noSuchMethod(Invocation invocation) =>
      throw UnimplementedError('${invocation.memberName}');

  @override
  Future<List<Map<String, dynamic>>> getAuthorizedSuppliers() async {
    calls.add('getSuppliers');
    if (throwOnLoad) throw Exception('load failed');
    return suppliers;
  }

  @override
  Future<Map<String, dynamic>> createAuthorizedSupplier(
      Map<String, dynamic> body) async {
    calls.add('createSupplier:${body['name']}');
    return body;
  }

  @override
  Future<void> updateAuthorizedSupplier(
      int id, Map<String, dynamic> body) async {
    calls.add('updateSupplier:$id');
  }

  @override
  Future<void> updateSupplierProcurement(
      int id, Map<String, dynamic> body) async {
    calls.add('updateSupplierProcurement:$id');
  }

  @override
  Future<List<Map<String, dynamic>>> getSupplierProducts(int supplierId,
      {bool includeInactive = false}) async {
    calls.add('getProducts:$supplierId');
    return products;
  }

  @override
  Future<Map<String, dynamic>> upsertSupplierProduct(
      int supplierId, Map<String, dynamic> body) async {
    calls.add('upsertProduct:$supplierId');
    return body;
  }

  @override
  Future<void> deactivateSupplierProduct(int productId) async {
    calls.add('deactivateProduct:$productId');
  }

  @override
  Future<Map<String, dynamic>> getQuotesForRequest(int prId) async {
    calls.add('getQuotes:$prId');
    if (throwOnLoad) throw Exception('load failed');
    return quotesResponse;
  }

  @override
  Future<List<Map<String, dynamic>>> createQuotesForRequest(
      int prId, Map<String, dynamic> body) async {
    calls.add('createQuotes:$prId:${(body['supplier_ids'] as List).length}');
    return const [];
  }

  @override
  Future<void> sendQuote(int quoteId, Map<String, dynamic> body) async {
    calls.add('sendQuote:$quoteId');
  }

  @override
  Future<void> sendQuotePortalLink(
      int quoteId, Map<String, dynamic> body) async {
    calls.add('sendQuotePortal:$quoteId');
  }

  @override
  Future<void> answerQuote(int quoteId, Map<String, dynamic> body) async {
    calls.add('answerQuote:$quoteId');
  }

  @override
  Future<Map<String, dynamic>> selectQuote(
      int quoteId, Map<String, dynamic> body) async {
    calls.add('selectQuote:$quoteId');
    return selectResponse;
  }

  @override
  Future<int> createPurchaseOrder(Map<String, dynamic> body) async {
    calls.add('createPO');
    return 42;
  }
}

void main() {
  group('SuppliersCubit', () {
    test('loadSuppliers popula estado', () async {
      final repo = _StubRepo()
        ..suppliers = [
          {'id': 1, 'name': 'Loja EPI'},
        ];
      final cubit = SuppliersCubit(repository: repo);
      await cubit.loadSuppliers();
      expect(cubit.state.isLoading, isFalse);
      expect(cubit.state.suppliers, hasLength(1));
      expect(repo.calls, contains('getSuppliers'));
    });

    test('loadSuppliers com falha registra erro', () async {
      final repo = _StubRepo()..throwOnLoad = true;
      final cubit = SuppliersCubit(repository: repo);
      await cubit.loadSuppliers();
      expect(cubit.state.error, isNotNull);
    });

    test('saveSupplier cria quando não há id', () async {
      final repo = _StubRepo();
      final cubit = SuppliersCubit(repository: repo);
      final ok = await cubit.saveSupplier(
        legacyFields: {'name': 'Nova Loja'},
        procurementFields: {'integration_level': 'portal'},
      );
      expect(ok, isTrue);
      expect(repo.calls, contains('createSupplier:Nova Loja'));
      expect(repo.calls.where((c) => c.startsWith('updateSupplier')), isEmpty);
    });

    test('saveSupplier atualiza legado + procurement quando há id', () async {
      final repo = _StubRepo();
      final cubit = SuppliersCubit(repository: repo);
      final ok = await cubit.saveSupplier(
        supplierId: 7,
        legacyFields: {'name': 'Loja'},
        procurementFields: {'phone': '11 9'},
      );
      expect(ok, isTrue);
      expect(repo.calls, contains('updateSupplier:7'));
      expect(repo.calls, contains('updateSupplierProcurement:7'));
    });

    test('saveProduct recarrega o catálogo', () async {
      final repo = _StubRepo();
      final cubit = SuppliersCubit(repository: repo);
      final ok = await cubit.saveProduct(3, {'supplier_sku': 'S1'});
      expect(ok, isTrue);
      expect(repo.calls, containsAllInOrder(['upsertProduct:3', 'getProducts:3']));
    });
  });

  group('QuotesCubit', () {
    test('load popula cotações e comparação do backend', () async {
      final repo = _StubRepo()
        ..quotesResponse = {
          'items': [
            {'id': 10, 'status': 'answered'},
          ],
          'comparison': {
            'suppliers': [
              {'quote_id': 10, 'total_with_freight': 99.9},
            ],
          },
        };
      final cubit = QuotesCubit(100, repository: repo);
      await cubit.load();
      expect(cubit.state.quotes, hasLength(1));
      expect(
          (cubit.state.comparison['suppliers'] as List), hasLength(1));
    });

    test('createQuotes envia fornecedores e recarrega', () async {
      final repo = _StubRepo();
      final cubit = QuotesCubit(100, repository: repo);
      final ok = await cubit.createQuotes([1, 2]);
      expect(ok, isTrue);
      expect(repo.calls, contains('createQuotes:100:2'));
      expect(repo.calls, contains('getQuotes:100'));
    });

    test('sendQuote escolhe canal e-mail ou portal', () async {
      final repo = _StubRepo();
      final cubit = QuotesCubit(100, repository: repo);
      await cubit.sendQuote(5, viaPortal: false);
      await cubit.sendQuote(5, viaPortal: true);
      expect(repo.calls, contains('sendQuote:5'));
      expect(repo.calls, contains('sendQuotePortal:5'));
    });

    test('selectQuote devolve o rascunho de PO do backend', () async {
      final repo = _StubRepo()
        ..selectResponse = {
          'po_draft': {'supplier': 'Loja EPI', 'items': []},
        };
      final cubit = QuotesCubit(100, repository: repo);
      final draft = await cubit.selectQuote(9);
      expect(draft, isNotNull);
      expect(draft!['supplier'], 'Loja EPI');
    });

    test('createPurchaseOrderFromDraft usa o fluxo existente de PO', () async {
      final repo = _StubRepo();
      final cubit = QuotesCubit(100, repository: repo);
      final id = await cubit.createPurchaseOrderFromDraft({'supplier': 'X'});
      expect(id, 42);
      expect(repo.calls, contains('createPO'));
    });

    test('erro de load fica no estado', () async {
      final repo = _StubRepo()..throwOnLoad = true;
      final cubit = QuotesCubit(100, repository: repo);
      await cubit.load();
      expect(cubit.state.error, isNotNull);
    });
  });
}
