import 'dart:convert';
import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:epi_api/epi_api.dart';
import 'package:flutter_test/flutter_test.dart';

/// Contrato de paridade Flutter da transferência de unidade operacional
/// (`POST /api/employee-unit-movements`, permissão `employees:transfer`) —
/// já existente no web legado ("Gestão de Colaborador").
class _CapturingAdapter implements HttpClientAdapter {
  _CapturingAdapter(this.body);
  final Object body;
  RequestOptions? lastRequest;

  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? requestStream,
    Future<void>? cancelFuture,
  ) async {
    lastRequest = options;
    return ResponseBody.fromString(
      jsonEncode(body),
      200,
      headers: {
        Headers.contentTypeHeader: [Headers.jsonContentType],
      },
    );
  }

  @override
  void close({bool force = false}) {}
}

void main() {
  group('Employee.fromJson — current_unit_id', () {
    test('lê unitId de current_unit_id (movimentação temporária ativa)', () {
      final employee = Employee.fromJson(const {
        'id': 1,
        'name': 'Ana',
        'unit_id': 5,
        'current_unit_id': 9,
      });
      expect(employee.unitId, 9);
    });

    test('cai para unit_id quando current_unit_id está ausente', () {
      final employee = Employee.fromJson(const {
        'id': 1,
        'name': 'Ana',
        'unit_id': 5,
      });
      expect(employee.unitId, 5);
    });

    test('unitId nulo quando nenhum dos dois campos está presente', () {
      final employee = Employee.fromJson(const {'id': 1, 'name': 'Ana'});
      expect(employee.unitId, isNull);
    });
  });

  group('EmployeesApi.createUnitMovement', () {
    test('bate no endpoint /api/employee-unit-movements com o corpo completo',
        () async {
      final adapter = _CapturingAdapter({'ok': true, 'id': 42});
      final dio = Dio(BaseOptions(baseUrl: 'http://test.local'))
        ..httpClientAdapter = adapter;
      final api = EmployeesApi(dio);

      final result = await api.createUnitMovement(
        actorUserId: 7,
        employeeId: 100,
        targetUnitId: 9,
        movementType: 'temporary',
        startDate: '2026-08-01',
        endDate: '2026-08-15',
        notes: 'Cobertura de férias',
      );

      expect(adapter.lastRequest?.path, '/api/employee-unit-movements');
      expect(adapter.lastRequest?.method, 'POST');
      final body = adapter.lastRequest?.data as Map;
      expect(body['actor_user_id'], 7);
      expect(body['employee_id'], 100);
      expect(body['target_unit_id'], 9);
      expect(body['movement_type'], 'temporary');
      expect(body['start_date'], '2026-08-01');
      expect(body['end_date'], '2026-08-15');
      expect(body['notes'], 'Cobertura de férias');
      expect(result['ok'], isTrue);
    });

    test('omite end_date/notes quando vazios (opcionais no backend)',
        () async {
      final adapter = _CapturingAdapter({'ok': true, 'id': 43});
      final dio = Dio(BaseOptions(baseUrl: 'http://test.local'))
        ..httpClientAdapter = adapter;
      final api = EmployeesApi(dio);

      await api.createUnitMovement(
        actorUserId: 7,
        employeeId: 100,
        targetUnitId: 9,
        movementType: 'definitive',
        startDate: '2026-08-01',
      );

      final body = adapter.lastRequest?.data as Map;
      expect(body.containsKey('end_date'), isFalse);
      expect(body.containsKey('notes'), isFalse);
    });
  });
}
