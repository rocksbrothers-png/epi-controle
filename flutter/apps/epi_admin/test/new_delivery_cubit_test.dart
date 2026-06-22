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
  }) async {
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

NewDeliveryCubit _cubit({int id = 1, Object? error, OfflineQueue? offlineQueue}) =>
    NewDeliveryCubit(
      repository: _FakeDeliveriesRepository(id: id, error: error),
      offlineQueue: offlineQueue,
    );

void _fillForm(NewDeliveryCubit cubit) {
  cubit.selectEmployee(const Employee(id: 1, name: 'Ana', sector: 'RH', role: 'Op'));
  cubit.selectEpi(const Epi(id: 2, name: 'Luva', code: 'QR2'));
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
    test('selectEmployee avança e herda setor/função', () {
      final cubit = _cubit();
      expect(cubit.state.step, DeliveryStep.employee);
      cubit.selectEmployee(const Employee(id: 1, name: 'Ana', sector: 'RH', role: 'Op'));
      expect(cubit.state.step, DeliveryStep.epi);
      expect(cubit.state.sector, 'RH');
      expect(cubit.state.roleName, 'Op');
      expect(cubit.state.canProceedFromEmployee, isTrue);
    });

    test('selectEpi → details; goBack volta um passo', () {
      final cubit = _cubit();
      cubit.selectEmployee(const Employee(id: 1, name: 'Ana'));
      cubit.selectEpi(const Epi(id: 2, name: 'Luva'));
      expect(cubit.state.step, DeliveryStep.details);
      expect(cubit.state.canProceedFromEpi, isTrue);
      cubit.goBack();
      expect(cubit.state.step, DeliveryStep.epi);
    });

    test('canProceedFromDetails exige todos os campos', () {
      final cubit = _cubit();
      cubit.selectEmployee(const Employee(id: 1, name: 'Ana'));
      cubit.selectEpi(const Epi(id: 2, name: 'Luva'));
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

  group('NewDeliveryCubit — submit', () {
    test('sucesso emite successId do repositório', () async {
      final cubit = _cubit(id: 42);
      _fillForm(cubit);
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
      _fillForm(cubit);
      final ok = await cubit.submit(companyId: 1, signatureData: 'sig');
      expect(ok, isFalse);
      expect(cubit.state.error, isNotNull);
      expect(cubit.state.isSubmitting, isFalse);
    });

    test('falha de conexão enfileira offline e retorna true', () async {
      final queue = _RecordingQueue();
      final cubit = _cubit(
        error: DioException(
          requestOptions: RequestOptions(path: '/api/deliveries'),
          type: DioExceptionType.connectionError,
        ),
        offlineQueue: queue,
      );
      _fillForm(cubit);
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
      _fillForm(cubit);
      final ok = await cubit.submit(companyId: 1, signatureData: 'sig');

      expect(ok, isFalse);
      expect(cubit.state.offlineQueued, isFalse);
      expect(cubit.state.error, isNotNull);
      expect(queue.enqueued, isEmpty);
    });
  });
}
