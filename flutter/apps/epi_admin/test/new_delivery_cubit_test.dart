import 'package:dio/dio.dart';
import 'package:epi_api/epi_api.dart';
import 'package:epi_admin/core/bloc/new_delivery_cubit.dart';
import 'package:epi_admin/core/sync/offline_queue.dart';
import 'package:epi_admin/features/deliveries/domain/repositories/deliveries_repository.dart';
import 'package:flutter_test/flutter_test.dart';

/// FASE 5 — valida o NewDeliveryCubit (stepper + submit) com um
/// DeliveriesRepository fake. A criação de entrega passa pelo repositório; a
/// fila offline (em falha de conexão) é injetada (OfflineQueue) e coberta aqui.
class _FakeDeliveriesRepository implements DeliveriesRepository {
  _FakeDeliveriesRepository({this.id = 1, this.error});

  final int id;
  final Object? error;

  /// Chaves recebidas, para conferir que a entrega é identificável e que o
  /// reenvio da fila repete a mesma.
  final List<String> idempotencyKeys = [];

  /// O que foi enviado como item físico. É o coração da #278: o backend
  /// procura este id em `epi_stock_items` e compara o código com
  /// `qr_code_value`.
  final List<int> stockItemIds = [];
  final List<String> stockQrCodes = [];

  @override
  Future<int> createDelivery({
    required int companyId,
    required int employeeId,
    required int epiId,
    required int quantity,
    required String sector,
    required String roleName,
    required String deliveryDate,
    required String nextReplacementDate,
    required int stockItemId,
    required String stockQrCode,
    String idempotencyKey = '',
  }) async {
    idempotencyKeys.add(idempotencyKey);
    stockItemIds.add(stockItemId);
    stockQrCodes.add(stockQrCode);
    if (error != null) throw error!;
    return id;
  }
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

/// Colaborador com Unidade — `unitId` é `current_unit_id`, resolvido pelo
/// backend com movimentação temporária vigente. É ele que define de qual
/// estoque a entrega sai (#278).
const _ana = Employee(id: 1, name: 'Ana', sector: 'RH', role: 'Op', unitId: 10);

/// Item FÍSICO em `epi_stock_items` — a unidade etiquetada que sai do estoque.
const _item = StockItem(
  id: 555,
  epiId: 2,
  epiName: 'Luva',
  status: 'in_stock',
  qrCodeValue: 'QR-REAL-555',
);

const _luva = Epi(id: 2, name: 'Luva', code: 'CODIGO-DO-CATALOGO');

NewDeliveryCubit _cubit({
  int id = 1,
  Object? error,
  OfflineQueue? offlineQueue,
  _FakeDeliveriesRepository? repository,
  List<Epi>? epis,
  List<StockItem>? itens,
  StockItem? porQr,
  Object? erroQr,
}) =>
    NewDeliveryCubit(
      repository: repository ?? _FakeDeliveriesRepository(id: id, error: error),
      offlineQueue: offlineQueue,
      episLoader: (unitId) async => epis ?? const [_luva],
      itemsLoader: (unitId, epiId) async => itens ?? const [_item],
      qrLookup: (unitId, qrCode) async {
        if (erroQr != null) throw Exception('$erroQr');
        return porQr ?? _item;
      },
    );

/// Percorre o fluxo até os detalhes, passando pelo passo do ITEM.
Future<void> _fillForm(NewDeliveryCubit cubit) async {
  await cubit.selectEmployee(_ana);
  await cubit.selectEpi(_luva);
  cubit.selectItem(_item);
  cubit.setDetails(
    quantity: 3,
    deliveryDate: '2026-01-01',
    nextReplacementDate: '2026-06-01',
    sector: 'RH',
    roleName: 'Op',
  );
}

void main() {
  group('NewDeliveryCubit — stepper', () {
    test('selectEmployee avança, herda setor/função e resolve a Unidade',
        () async {
      final cubit = _cubit();
      expect(cubit.state.step, DeliveryStep.employee);
      await cubit.selectEmployee(_ana);
      expect(cubit.state.step, DeliveryStep.epi);
      expect(cubit.state.sector, 'RH');
      expect(cubit.state.roleName, 'Op');
      // A Unidade da entrega é a do COLABORADOR — não há seletor de Unidade
      // neste fluxo, e o ator não a determina.
      expect(cubit.state.unitId, 10);
      expect(cubit.state.canProceedFromEmployee, isTrue);
      // E o estoque carregado é o daquela Unidade.
      expect(cubit.state.unitEpis, [_luva]);
    });

    test('colaborador sem Unidade não abre o passo de EPI', () async {
      // Sem Unidade não há estoque de onde a entrega sairia. Recusar aqui é
      // melhor do que deixar percorrer o fluxo e falhar no envio.
      final cubit = _cubit();
      await cubit.selectEmployee(const Employee(id: 9, name: 'Sem Unidade'));
      expect(cubit.state.step, DeliveryStep.employee);
      expect(cubit.state.canProceedFromEmployee, isFalse);
      expect(cubit.state.block, DeliveryBlock.employeeWithoutUnit);
      expect(cubit.state.unitEpis, isEmpty);
    });

    test('selectEpi → item; goBack volta um passo', () async {
      final cubit = _cubit();
      await cubit.selectEmployee(_ana);
      await cubit.selectEpi(_luva);
      // O EPI não leva direto aos detalhes: falta escolher QUAL unidade
      // etiquetada sai do estoque.
      expect(cubit.state.step, DeliveryStep.item);
      expect(cubit.state.canProceedFromEpi, isTrue);
      expect(cubit.state.availableItems, [_item]);
      cubit.goBack();
      expect(cubit.state.step, DeliveryStep.epi);
    });

    test('selectItem → details', () async {
      final cubit = _cubit();
      await cubit.selectEmployee(_ana);
      await cubit.selectEpi(_luva);
      expect(cubit.state.canProceedFromItem, isFalse);
      cubit.selectItem(_item);
      expect(cubit.state.step, DeliveryStep.details);
      expect(cubit.state.canProceedFromItem, isTrue);
      cubit.goBack();
      expect(cubit.state.step, DeliveryStep.item);
    });

    test('trocar de EPI invalida o item já escolhido', () async {
      // O item pertence ao EPI anterior; o backend recusaria a combinação.
      final cubit = _cubit();
      await cubit.selectEmployee(_ana);
      await cubit.selectEpi(_luva);
      cubit.selectItem(_item);
      expect(cubit.state.selectedItem, isNotNull);
      await cubit.selectEpi(const Epi(id: 3, name: 'Capacete'));
      expect(cubit.state.selectedItem, isNull);
      expect(cubit.state.canProceedFromItem, isFalse);
    });

    test('canProceedFromDetails exige todos os campos', () async {
      final cubit = _cubit();
      await cubit.selectEmployee(_ana);
      await cubit.selectEpi(_luva);
      cubit.selectItem(_item);
      expect(cubit.state.canProceedFromDetails, isFalse);
      cubit.setDetails(
        quantity: 2,
        deliveryDate: '2026-01-01',
        nextReplacementDate: '2026-02-01',
        sector: 'RH',
        roleName: 'Op',
      );
      expect(cubit.state.canProceedFromDetails, isTrue);
    });
  });

  group('NewDeliveryCubit — item físico (#278)', () {
    test('a entrega envia o id REAL de epi_stock_items, não o id do EPI',
        () async {
      // O defeito que a #278 corrigiu: iam `epi.id` e `epi.code` — um id de
      // catálogo e um código de compra. O backend procura o id em
      // `epi_stock_items` e compara o código com `qr_code_value`; os dois só
      // casariam por coincidência, e a entrega pelo app não podia dar certo.
      final repository = _FakeDeliveriesRepository();
      final cubit = _cubit(repository: repository);
      await _fillForm(cubit);

      await cubit.submit(companyId: 1, signatureData: 'sig');

      expect(repository.stockItemIds.single, 555);
      expect(repository.stockQrCodes.single, 'QR-REAL-555');
      // E explicitamente NÃO os do EPI.
      expect(repository.stockItemIds.single, isNot(_luva.id));
      expect(repository.stockQrCodes.single, isNot(_luva.code));
    });

    test('sem item físico escolhido a entrega não é enviada', () async {
      final repository = _FakeDeliveriesRepository();
      final cubit = _cubit(repository: repository);
      await cubit.selectEmployee(_ana);
      await cubit.selectEpi(_luva);
      cubit.setDetails(
        quantity: 1,
        deliveryDate: '2026-01-01',
        nextReplacementDate: '2026-06-01',
        sector: 'RH',
        roleName: 'Op',
      );

      final ok = await cubit.submit(companyId: 1, signatureData: 'sig');

      expect(ok, isFalse);
      expect(repository.stockItemIds, isEmpty);
    });

    test('QR lido resolve o item pelo backend e avança', () async {
      final cubit = _cubit();
      await cubit.selectEmployee(_ana);
      await cubit.selectEpi(_luva);

      await cubit.selectItemByQr('QR-REAL-555');

      expect(cubit.state.selectedItem?.id, 555);
      expect(cubit.state.step, DeliveryStep.details);
    });

    test('QR de outro EPI é recusado antes de seguir', () async {
      // O item existe e está na Unidade, mas é de outro EPI. O backend
      // recusaria igual; dizer aqui evita percorrer o resto do fluxo.
      const outro = StockItem(
        id: 777,
        epiId: 99,
        epiName: 'Capacete',
        status: 'in_stock',
        qrCodeValue: 'QR-777',
      );
      final cubit = _cubit(porQr: outro);
      await cubit.selectEmployee(_ana);
      await cubit.selectEpi(_luva);

      await cubit.selectItemByQr('QR-777');

      expect(cubit.state.selectedItem, isNull);
      expect(cubit.state.step, DeliveryStep.item);
      expect(cubit.state.block, DeliveryBlock.qrFromAnotherEpi);
    });

    test('a Unidade nunca vem do saldo corporativo', () async {
      // Um EPI com saldo corporativo alto e saldo local zero não pode ser
      // entregue: quem manda é `unit_stock_quantity`.
      const distribuido = Epi(
        id: 2,
        name: 'Luva',
        stockQuantity: 500,
        companyStockQuantity: 500,
        unitStockQuantity: 0,
      );
      final cubit = _cubit(epis: const [distribuido], itens: const []);
      await cubit.selectEmployee(_ana);
      await cubit.selectEpi(distribuido);

      // Sem item físico na Unidade não há o que entregar, por mais alto que
      // seja o número da empresa.
      expect(cubit.state.availableItems, isEmpty);
      expect(cubit.state.canProceedFromItem, isFalse);
    });
  });

  group('NewDeliveryCubit — submit', () {
    test('sucesso emite successId do repositório', () async {
      final cubit = _cubit(id: 42);
      await _fillForm(cubit);
      final ok = await cubit.submit(companyId: 1, signatureData: 'sig');
      expect(ok, isTrue);
      expect(cubit.state.successId, 42);
      expect(cubit.state.isSubmitting, isFalse);
    });

    test('sem colaborador/EPI selecionado retorna false', () async {
      final cubit = _cubit();
      final ok = await cubit.submit(companyId: 1, signatureData: 'sig');
      expect(ok, isFalse);
    });

    test('erro genérico seta error e retorna false', () async {
      final cubit = _cubit(error: Exception('boom'));
      await _fillForm(cubit);
      final ok = await cubit.submit(companyId: 1, signatureData: 'sig');
      expect(ok, isFalse);
      expect(cubit.state.error, isNotNull);
      expect(cubit.state.isSubmitting, isFalse);
    });

    test('falha de conexão enfileira offline e retorna true', () async {
      final queue = _RecordingQueue();
      final repository = _FakeDeliveriesRepository(
        error: DioException(
          requestOptions: RequestOptions(path: '/api/deliveries'),
          type: DioExceptionType.connectionError,
        ),
      );
      final cubit = _cubit(repository: repository, offlineQueue: queue);
      await _fillForm(cubit);
      final ok = await cubit.submit(companyId: 7, signatureData: 'sig');

      expect(ok, isTrue);
      expect(cubit.state.offlineQueued, isTrue);
      expect(cubit.state.isSubmitting, isFalse);
      expect(cubit.state.error, isNull);
      expect(queue.enqueued, hasLength(1));
      final op = queue.enqueued.first;
      expect(op['op_type'], 'delivery_create');
      expect(op['company_id'], 7);
      expect(op['employee_id'], 1);
      expect(op['epi_id'], 2);
      // A chave precisa viajar com a operação: sem ela o reenvio bate no item
      // já entregue, falha para sempre e a fila nunca drena.
      expect(op['idempotency_key'], isNotEmpty);
      expect(op['idempotency_key'], repository.idempotencyKeys.single,
          reason: 'a tentativa online e a enfileirada são a MESMA entrega');
    });

    test('a chave identifica a tentativa, não a requisição', () async {
      // Duas entregas distintas não podem compartilhar chave — a segunda seria
      // descartada como se fosse reenvio da primeira.
      final repository = _FakeDeliveriesRepository();
      for (var i = 0; i < 2; i++) {
        final cubit = _cubit(repository: repository);
        await _fillForm(cubit);
        await cubit.submit(companyId: 1, signatureData: 'sig');
      }
      expect(repository.idempotencyKeys, hasLength(2));
      expect(repository.idempotencyKeys.toSet(), hasLength(2));
      expect(repository.idempotencyKeys.every((k) => k.isNotEmpty), isTrue);
    });

    test('erro de servidor (badResponse) seta error e não enfileira', () async {
      final queue = _RecordingQueue();
      final cubit = _cubit(
        error: DioException(
          requestOptions: RequestOptions(path: '/api/deliveries'),
          type: DioExceptionType.badResponse,
          response: Response(
            requestOptions: RequestOptions(path: '/api/deliveries'),
            statusCode: 500,
          ),
        ),
        offlineQueue: queue,
      );
      await _fillForm(cubit);
      final ok = await cubit.submit(companyId: 1, signatureData: 'sig');

      expect(ok, isFalse);
      expect(cubit.state.offlineQueued, isFalse);
      expect(cubit.state.error, isNotNull);
      expect(queue.enqueued, isEmpty);
    });
  });
}
