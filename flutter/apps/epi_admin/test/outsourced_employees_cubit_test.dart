import 'dart:convert';
import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:epi_admin/core/bloc/outsourced_employees_cubit.dart';
import 'package:epi_api/epi_api.dart';
import 'package:flutter_test/flutter_test.dart';

/// Cadastro de Colaboradores simplificado (ADR-0002 §10.2) — cubit.
class _RecordingAdapter implements HttpClientAdapter {
  _RecordingAdapter({this.responseByPath = const {}});

  final Map<String, Map<String, dynamic>> responseByPath;
  final List<String> paths = [];
  final List<Object?> bodies = [];

  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? requestStream,
    Future<void>? cancelFuture,
  ) async {
    paths.add(options.path);
    bodies.add(options.data);
    final canned = responseByPath[options.path];
    return ResponseBody.fromString(
      jsonEncode(canned ?? {}),
      200,
      headers: const {
        Headers.contentTypeHeader: ['application/json'],
      },
    );
  }

  @override
  void close({bool force = false}) {}
}

const _bootstrapPayload = {
  'units': <Map<String, dynamic>>[],
  'employees': [
    {'id': 1, 'name': 'CLT Fulano', 'tipo_vinculo': 'CLT'},
    {'id': 2, 'name': 'Terceirizado Beltrano', 'tipo_vinculo': 'Terceirizado', 'role_name': 'Auxiliar'},
    {'id': 3, 'name': 'Prestador Ciclano', 'tipo_vinculo': 'Prestador de Serviço'},
  ],
  'epis': <Map<String, dynamic>>[],
  'users': <Map<String, dynamic>>[],
};

void main() {
  late _RecordingAdapter adapter;
  late AuthApi authApi;
  late EmployeesApi employeesApi;

  setUp(() {
    adapter = _RecordingAdapter(responseByPath: {
      '/api/bootstrap': _bootstrapPayload,
      '/api/employees/archived': {'employees': <Map<String, dynamic>>[]},
    });
    final dio = Dio()..httpClientAdapter = adapter;
    authApi = AuthApi(dio);
    employeesApi = EmployeesApi(dio);
  });

  test('load filtra colaboradores CLT fora da lista (só terceirizado/prestador)', () async {
    final cubit = OutsourcedEmployeesCubit(employeesApi: employeesApi, authApi: authApi);
    await cubit.load();
    await cubit.close();
    expect(cubit.state.employees, hasLength(2));
    expect(cubit.state.employees.map((e) => e.name), ['Terceirizado Beltrano', 'Prestador Ciclano']);
  });

  test('load busca também os colaboradores arquivados com outsourced_only=1', () async {
    final cubit = OutsourcedEmployeesCubit(employeesApi: employeesApi, authApi: authApi);
    await cubit.load();
    await cubit.close();
    expect(adapter.paths, contains('/api/bootstrap'));
    expect(adapter.paths, contains('/api/employees/archived'));
  });

  test('search filtra por nome sem nova chamada de rede', () async {
    final cubit = OutsourcedEmployeesCubit(employeesApi: employeesApi, authApi: authApi);
    await cubit.load();
    final callsBefore = adapter.paths.length;
    cubit.search('Beltrano');
    expect(cubit.state.filtered, hasLength(1));
    expect(cubit.state.filtered.single.name, 'Terceirizado Beltrano');
    expect(adapter.paths, hasLength(callsBefore));
    await cubit.close();
  });

  test('toggleArchivedView alterna a listagem', () async {
    final cubit = OutsourcedEmployeesCubit(employeesApi: employeesApi, authApi: authApi);
    expect(cubit.state.showArchived, isFalse);
    cubit.toggleArchivedView();
    expect(cubit.state.showArchived, isTrue);
    await cubit.close();
  });

  test('createEmployee chama a rota simplificada e recarrega', () async {
    final cubit = OutsourcedEmployeesCubit(employeesApi: employeesApi, authApi: authApi);
    final ok = await cubit.createEmployee({
      'company_id': 1,
      'unit_id': 2,
      'outsourced_company_id': 9,
      'name': 'Novo Terceirizado',
      'cpf': '111.444.777-35',
      'role_name': 'Auxiliar',
      'tipo_vinculo': 'Terceirizado',
      'admission_date': '2026-01-01',
    });
    await cubit.close();
    expect(ok, isTrue);
    expect(adapter.paths, contains('/api/employees/outsourced-simplified'));
  });

  test('archiveEmployee chama a rota de arquivamento e recarrega', () async {
    final cubit = OutsourcedEmployeesCubit(employeesApi: employeesApi, authApi: authApi);
    final ok = await cubit.archiveEmployee(2, reason: 'Contrato encerrado');
    await cubit.close();
    expect(ok, isTrue);
    expect(adapter.paths, contains('/api/employees/2/archive'));
  });

  test('restoreEmployee chama a rota de restauração e recarrega', () async {
    final cubit = OutsourcedEmployeesCubit(employeesApi: employeesApi, authApi: authApi);
    final ok = await cubit.restoreEmployee(2);
    await cubit.close();
    expect(ok, isTrue);
    expect(adapter.paths, contains('/api/employees/2/restore'));
  });
}
