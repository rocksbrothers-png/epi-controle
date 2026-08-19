import 'package:dio/dio.dart';
import 'package:epi_api/epi_api.dart';
import 'package:epi_admin/core/bloc/stock_cubit.dart';
import 'package:epi_admin/features/stock/domain/repositories/stock_repository.dart';
import 'package:flutter_test/flutter_test.dart';

/// Estados das consultas de estoque (#246 Lote 1.1): itens disponíveis e
/// bloqueados.
///
/// O caso que dá nome a estes testes é o 403. O backend responde
/// `PermissionError` quando um perfil `admin`/`user` não tem unidade
/// operacional ativa — e isso NÃO é falha: é contexto ausente. Tratar como
/// erro genérico ofereceria "tentar de novo" para algo que tentar de novo não
/// resolve, e esconderia do operador o que ele precisa pedir ao administrador.

class _FakeRepository implements StockRepository {
  _FakeRepository({this.items, this.blocked, this.erro});

  final List<StockItem>? items;
  final BlockedStockItems? blocked;
  final Object? erro;

  int chamadasDisponiveis = 0;
  int? ultimoEpiId;
  int? atorRecebidoDisponiveis;
  int? atorRecebidoBloqueados;

  @override
  Future<List<StockItem>> fetchAvailableItems({
    required int actorUserId,
    required int epiId,
  }) async {
    chamadasDisponiveis++;
    ultimoEpiId = epiId;
    atorRecebidoDisponiveis = actorUserId;
    if (erro != null) throw erro!;
    return items ?? const [];
  }

  @override
  Future<BlockedStockItems> fetchBlockedItems({required int actorUserId}) async {
    atorRecebidoBloqueados = actorUserId;
    if (erro != null) throw erro!;
    return blocked ?? const BlockedStockItems(items: [], statusKeys: []);
  }

  /// Ator da sessão (fatia 1.1B): antes vinha junto do bootstrap carregado por
  /// `load()`. Agora é resolvido na camada de dados, e estas consultas passaram
  /// a funcionar mesmo sem `load()` ter rodado antes.
  @override
  Future<int> currentActorUserId() async => 7;

  @override
  Future<List<Epi>> fetchStockEpis({
    String? name,
    String? section,
    String? manufacturer,
    String? ca,
    String? protection,
  }) async =>
      const [];

  @override
  // ignore: deprecated_member_use_from_same_package
  Future<StockSnapshot> fetchStock() =>
      throw UnimplementedError('bootstrap.epis não é mais fonte de estoque');

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

DioException _http(int status) => DioException(
      requestOptions: RequestOptions(path: '/api/stock/blocked-items'),
      response: Response<void>(
        requestOptions: RequestOptions(path: '/api/stock/blocked-items'),
        statusCode: status,
      ),
    );

StockItem _item(int id, {String status = 'in_stock'}) => StockItem.fromJson({
      'id': id, 'epi_id': 1, 'epi_name': 'EPI $id', 'status': status,
    });

void main() {
  group('itens disponíveis', () {
    test('idle antes de qualquer consulta — não é lista vazia', () {
      // Sem esta distinção a tela diria "nenhum item disponível" antes de o
      // operador ter escolhido um EPI, o que é simplesmente falso.
      final cubit = StockCubit(repository: _FakeRepository());
      expect(cubit.state.availableStatus, StockListStatus.idle);
      expect(cubit.state.availableItems, isEmpty);
    });

    test('carrega e guarda o EPI consultado', () async {
      final repo = _FakeRepository(items: [_item(1), _item(2)]);
      final cubit = StockCubit(repository: repo);

      await cubit.loadAvailableItems(42);

      expect(cubit.state.availableStatus, StockListStatus.ready);
      expect(cubit.state.availableItems.length, 2);
      expect(cubit.state.availableEpiId, 42);
      expect(repo.ultimoEpiId, 42);
    });

    test('lista vazia é ready, não erro', () async {
      final cubit = StockCubit(repository: _FakeRepository(items: const []));
      await cubit.loadAvailableItems(1);
      expect(cubit.state.availableStatus, StockListStatus.ready);
      expect(cubit.state.availableItems, isEmpty);
    });

    test('403 vira forbidden, não error', () async {
      final cubit = StockCubit(repository: _FakeRepository(erro: _http(403)));
      await cubit.loadAvailableItems(1);
      expect(cubit.state.availableStatus, StockListStatus.forbidden);
    });

    test('500 vira error', () async {
      final cubit = StockCubit(repository: _FakeRepository(erro: _http(500)));
      await cubit.loadAvailableItems(1);
      expect(cubit.state.availableStatus, StockListStatus.error);
      expect(cubit.state.availableError, isNotNull);
    });

    test('400 (EPI obrigatório) vira error, não forbidden', () async {
      // O backend responde 400 quando `epi_id` falta. Confundir com 403
      // mostraria "sem unidade operacional" para um erro de parâmetro.
      final cubit = StockCubit(repository: _FakeRepository(erro: _http(400)));
      await cubit.loadAvailableItems(0);
      expect(cubit.state.availableStatus, StockListStatus.error);
    });

    test('consulta com o ator da sessão mesmo sem load() antes', () async {
      // Regressão da fatia 1.1B: o ator vinha do bootstrap carregado por
      // `load()`. Sem `load()` (deep-link, ou o operador abrindo a aba antes),
      // a consulta sairia com `actor_user_id=0` e o backend recusaria — o
      // mesmo defeito que a lista de colaboradores já teve.
      final repo = _FakeRepository(items: [_item(1)]);
      final cubit = StockCubit(repository: repo);

      await cubit.loadAvailableItems(42);

      expect(repo.atorRecebidoDisponiveis, 7);
      expect(cubit.state.actorUserId, 7, reason: 'ator resolvido fica no estado');
      expect(cubit.state.availableStatus, StockListStatus.ready);
    });

    test('trocar de EPI limpa a lista anterior antes de carregar', () async {
      // Sem limpar, a lista do EPI anterior fica visível sob o spinner e o
      // operador pode ler QRs que não são do EPI que ele acabou de abrir.
      final repo = _FakeRepository(items: [_item(1)]);
      final cubit = StockCubit(repository: repo);
      await cubit.loadAvailableItems(1);
      expect(cubit.state.availableItems, isNotEmpty);

      final estados = <StockListStatus>[];
      final itensDurante = <int>[];
      final sub = cubit.stream.listen((s) {
        estados.add(s.availableStatus);
        itensDurante.add(s.availableItems.length);
      });
      await cubit.loadAvailableItems(2);
      await sub.cancel();

      expect(estados.first, StockListStatus.loading);
      expect(itensDurante.first, 0, reason: 'lista do EPI anterior sobreviveu');
    });
  });

  group('itens bloqueados', () {
    test('carrega itens e chaves de status', () async {
      final cubit = StockCubit(
        repository: _FakeRepository(
          blocked: BlockedStockItems(
            items: [_item(1, status: 'blocked_expired')],
            statusKeys: const ['blocked_expired', 'blocked_discard'],
          ),
        ),
      );

      await cubit.loadBlockedItems();

      expect(cubit.state.blockedStatus, StockListStatus.ready);
      expect(cubit.state.blockedItems.single.status, 'blocked_expired');
      expect(cubit.state.blockedStatusKeys, contains('blocked_discard'));
    });

    test('403 vira forbidden', () async {
      final cubit = StockCubit(repository: _FakeRepository(erro: _http(403)));
      await cubit.loadBlockedItems();
      expect(cubit.state.blockedStatus, StockListStatus.forbidden);
    });

    test('consulta com o ator da sessão mesmo sem load() antes', () async {
      final repo = _FakeRepository();
      final cubit = StockCubit(repository: repo);
      await cubit.loadBlockedItems();
      expect(repo.atorRecebidoBloqueados, 7);
    });

    test('vazio é ready com lista vazia', () async {
      final cubit = StockCubit(repository: _FakeRepository());
      await cubit.loadBlockedItems();
      expect(cubit.state.blockedStatus, StockListStatus.ready);
      expect(cubit.state.blockedItems, isEmpty);
    });
  });

  group('isolamento entre as duas listas', () {
    test('erro em bloqueados não contamina disponíveis', () async {
      // As abas são independentes: uma falha de rede numa não pode apagar o
      // que a outra já carregou.
      final cubit = StockCubit(repository: _FakeRepository(items: [_item(1)]));
      await cubit.loadAvailableItems(1);
      expect(cubit.state.availableStatus, StockListStatus.ready);

      final comErro = StockCubit(repository: _FakeRepository(erro: _http(500)));
      await comErro.loadBlockedItems();
      expect(comErro.state.availableStatus, StockListStatus.idle);
      expect(comErro.state.blockedStatus, StockListStatus.error);
    });
  });
}
