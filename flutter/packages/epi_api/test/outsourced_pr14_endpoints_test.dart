import 'dart:convert';
import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:epi_api/epi_api.dart';
import 'package:flutter_test/flutter_test.dart';

/// Contrato dos endpoints novos do Cadastro de Colaboradores simplificado e
/// arquivamento de empresas terceirizadas/prestadoras (ADR-0002 §10, PR 14).
class _RecordingAdapter implements HttpClientAdapter {
  _RecordingAdapter({this.responseByPath = const {}});

  final Map<String, Map<String, dynamic>> responseByPath;
  final List<String> paths = [];
  final List<String> methods = [];
  final List<Object?> bodies = [];
  final List<Map<String, dynamic>> queries = [];

  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? requestStream,
    Future<void>? cancelFuture,
  ) async {
    paths.add(options.path);
    methods.add(options.method);
    bodies.add(options.data);
    queries.add(options.queryParameters);
    final canned = responseByPath[options.path];
    return ResponseBody.fromString(
      jsonEncode(canned ?? {'ok': true}),
      200,
      headers: const {
        Headers.contentTypeHeader: ['application/json'],
      },
    );
  }

  @override
  void close({bool force = false}) {}
}

void main() {
  group('OutsourcedCompaniesApi — arquivamento e relatório', () {
    test('getArchivedOutsourcedCompanies chama GET /api/outsourced-companies/archived', () async {
      final adapter = _RecordingAdapter(responseByPath: {
        '/api/outsourced-companies/archived': {
          'outsourced_companies': [
            {'id': 1, 'legal_name': 'Terceirizada X', 'archived_at': '2026-01-01T00:00:00'},
          ],
        },
      });
      final api = OutsourcedCompaniesApi(Dio()..httpClientAdapter = adapter);
      final result = await api.getArchivedOutsourcedCompanies(actorUserId: 1);
      expect(adapter.paths.single, '/api/outsourced-companies/archived');
      expect(result.single['legal_name'], 'Terceirizada X');
    });

    test('archiveOutsourcedCompany faz POST com motivo', () async {
      final adapter = _RecordingAdapter();
      final api = OutsourcedCompaniesApi(Dio()..httpClientAdapter = adapter);
      await api.archiveOutsourcedCompany(9, actorUserId: 1, reason: 'Contrato encerrado');
      expect(adapter.paths.single, '/api/outsourced-companies/9/archive');
      expect(adapter.methods.single, 'POST');
      final body = adapter.bodies.single! as Map<String, dynamic>;
      expect(body['reason'], 'Contrato encerrado');
      expect(body['actor_user_id'], 1);
    });

    test('restoreOutsourcedCompany faz POST', () async {
      final adapter = _RecordingAdapter();
      final api = OutsourcedCompaniesApi(Dio()..httpClientAdapter = adapter);
      await api.restoreOutsourcedCompany(9, actorUserId: 1);
      expect(adapter.paths.single, '/api/outsourced-companies/9/restore');
      expect(adapter.methods.single, 'POST');
    });

    test('getOutsourcedEmployeesSummary chama GET /api/outsourced-companies/employees-summary', () async {
      final adapter = _RecordingAdapter(responseByPath: {
        '/api/outsourced-companies/employees-summary': {
          'outsourced_employees_summary': [
            {'outsourced_company_id': 1, 'legal_name': 'X', 'active_count': 2, 'archived_count': 1},
          ],
        },
      });
      final api = OutsourcedCompaniesApi(Dio()..httpClientAdapter = adapter);
      final result = await api.getOutsourcedEmployeesSummary(actorUserId: 1);
      expect(adapter.paths.single, '/api/outsourced-companies/employees-summary');
      expect(result.single['active_count'], 2);
    });
  });

  group('EmployeesApi — Cadastro de Colaboradores simplificado', () {
    test('createEmployeeOutsourcedSimplified faz POST /api/employees/outsourced-simplified', () async {
      final adapter = _RecordingAdapter();
      final api = EmployeesApi(Dio()..httpClientAdapter = adapter);
      await api.createEmployeeOutsourcedSimplified({
        'actor_user_id': 1,
        'company_id': 1,
        'unit_id': 2,
        'outsourced_company_id': 9,
        'name': 'Trabalhador X',
        'cpf': '111.444.777-35',
        'role_name': 'Auxiliar',
        'tipo_vinculo': 'Terceirizado',
        'admission_date': '2026-01-01',
      });
      expect(adapter.paths.single, '/api/employees/outsourced-simplified');
      expect(adapter.methods.single, 'POST');
      final body = adapter.bodies.single! as Map<String, dynamic>;
      expect(body['tipo_vinculo'], 'Terceirizado');
    });

    test('updateEmployeeOutsourcedSimplified faz PUT /api/employees/outsourced-simplified/{id}', () async {
      final adapter = _RecordingAdapter();
      final api = EmployeesApi(Dio()..httpClientAdapter = adapter);
      await api.updateEmployeeOutsourcedSimplified(7, {'name': 'Trabalhador Y'});
      expect(adapter.paths.single, '/api/employees/outsourced-simplified/7');
      expect(adapter.methods.single, 'PUT');
    });

    test('getArchivedEmployees sem outsourcedOnly não manda o parâmetro', () async {
      final adapter = _RecordingAdapter(responseByPath: {
        '/api/employees/archived': {'employees': <Map<String, dynamic>>[]},
      });
      final api = EmployeesApi(Dio()..httpClientAdapter = adapter);
      await api.getArchivedEmployees(actorUserId: 1);
      final uri = Uri.parse(adapter.paths.single);
      expect(uri.path, '/api/employees/archived');
    });

    test('getArchivedEmployees(outsourcedOnly: true) manda outsourced_only=1', () async {
      final adapter = _RecordingAdapter(responseByPath: {
        '/api/employees/archived': {'employees': <Map<String, dynamic>>[]},
      });
      final api = EmployeesApi(Dio()..httpClientAdapter = adapter);
      await api.getArchivedEmployees(actorUserId: 1, outsourcedOnly: true);
      expect(adapter.queries.single['outsourced_only'], '1');
    });
  });

  group('SettingsApi — module_visibility (issue #148 / visibilidade por Unidade)', () {
    test('getModuleVisibility chama GET /api/module-visibility', () async {
      final adapter = _RecordingAdapter(responseByPath: {
        '/api/module-visibility': {
          'module_visibility': {
            'admin': {
              '*': {'terceirizados_colaboradores': true},
            },
          },
        },
      });
      final api = SettingsApi(Dio()..httpClientAdapter = adapter);
      final result = await api.getModuleVisibility();
      expect(adapter.paths.single, '/api/module-visibility');
      expect(result['module_visibility'], isNotEmpty);
    });

    test('saveModuleVisibility faz POST com role e modules, sem unit_id por padrão', () async {
      final adapter = _RecordingAdapter();
      final api = SettingsApi(Dio()..httpClientAdapter = adapter);
      await api.saveModuleVisibility(
        actorUserId: 1,
        role: 'admin',
        modules: {'terceirizados_colaboradores': true},
      );
      expect(adapter.paths.single, '/api/module-visibility');
      expect(adapter.methods.single, 'POST');
      final body = adapter.bodies.single! as Map<String, dynamic>;
      expect(body['role'], 'admin');
      expect(body['modules'], {'terceirizados_colaboradores': true});
      expect(body.containsKey('unit_id'), isFalse);
    });

    test('saveModuleVisibility inclui unit_id no POST quando informado', () async {
      final adapter = _RecordingAdapter();
      final api = SettingsApi(Dio()..httpClientAdapter = adapter);
      await api.saveModuleVisibility(
        actorUserId: 1,
        role: 'admin',
        modules: {'estoque': false},
        unitId: 10,
      );
      final body = adapter.bodies.single! as Map<String, dynamic>;
      expect(body['unit_id'], 10);
    });
  });
}
