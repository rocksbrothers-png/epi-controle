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

/// Resposta de `GET /api/employees` — a rota que a aba passou a consumir no
/// F2 da #226, no lugar do bootstrap.
///
/// A amostra cobre os sete vínculos de propósito. Os três de mão de obra
/// própria que NÃO são CLT (`Menor Aprendiz`, `Praticante`, `Estagiário`) são
/// o motivo de o filtro ter deixado de ser `!= 'CLT'`: com a comparação
/// antiga eles entravam nesta aba e ganhavam botões de Editar/Arquivar que
/// batem nas rotas `.../outsourced-simplified`, que o backend recusa.
const _employeesPayload = {
  'employees': [
    {'id': 1, 'name': 'CLT Fulano', 'tipo_vinculo': 'CLT'},
    {
      'id': 2,
      'name': 'Terceirizado Beltrano',
      'tipo_vinculo': 'Terceirizado',
      'role_name': 'Auxiliar',
      'local_unit_link_status': 'active',
      'is_linked_to_actor_unit': true,
    },
    {'id': 3, 'name': 'Prestador Ciclano', 'tipo_vinculo': 'Prestador de Serviço'},
    {'id': 4, 'name': 'Temporário Deltrano', 'tipo_vinculo': 'Temporário'},
    {'id': 5, 'name': 'Aprendiz Epsilano', 'tipo_vinculo': 'Menor Aprendiz'},
    {'id': 6, 'name': 'Praticante Zetano', 'tipo_vinculo': 'Praticante'},
    {'id': 7, 'name': 'Estagiário Etano', 'tipo_vinculo': 'Estagiário'},
  ],
};

void main() {
  late _RecordingAdapter adapter;
  late EmployeesApi employeesApi;

  setUp(() {
    adapter = _RecordingAdapter(responseByPath: {
      '/api/employees': _employeesPayload,
      '/api/employees/archived': {'employees': <Map<String, dynamic>>[]},
    });
    employeesApi = EmployeesApi(Dio()..httpClientAdapter = adapter);
  });

  test('load traz apenas mão de obra contratada — os três vínculos, e só eles', () async {
    final cubit = OutsourcedEmployeesCubit(employeesApi: employeesApi);
    await cubit.load();
    await cubit.close();
    expect(cubit.state.employees.map((e) => e.name), [
      'Terceirizado Beltrano',
      'Prestador Ciclano',
      'Temporário Deltrano',
    ]);
  });

  test('mão de obra própria que não é CLT também fica fora', () async {
    // O caso que `!= 'CLT'` deixava passar. Sem este teste, alguém pode
    // reintroduzir a comparação antiga e os testes de "CLT fora" continuariam
    // verdes — que foi exatamente como o defeito sobreviveu.
    final cubit = OutsourcedEmployeesCubit(employeesApi: employeesApi);
    await cubit.load();
    await cubit.close();
    final names = cubit.state.employees.map((e) => e.name).toList();
    for (final excluded in const [
      'CLT Fulano',
      'Aprendiz Epsilano',
      'Praticante Zetano',
      'Estagiário Etano',
    ]) {
      expect(names, isNot(contains(excluded)), reason: excluded);
    }
  });

  test('a lista vem de GET /api/employees, não do bootstrap', () async {
    // A distinção não é cosmética: o bootstrap chama `fetch_employees` sem
    // contexto de Unidade, então `local_unit_link_status` viria nulo para
    // todos e a tela nunca ofereceria ação de vínculo — em silêncio.
    final cubit = OutsourcedEmployeesCubit(employeesApi: employeesApi);
    await cubit.load();
    await cubit.close();
    expect(adapter.paths, contains('/api/employees'));
    expect(adapter.paths, isNot(contains('/api/bootstrap')));
  });

  test('o estado do vínculo local chega até o state', () async {
    final cubit = OutsourcedEmployeesCubit(employeesApi: employeesApi);
    await cubit.load();
    await cubit.close();
    final beltrano = cubit.state.employees.firstWhere((e) => e.id == 2);
    expect(beltrano.localUnitLinkStatus, kUnitLinkStatusActive);
    expect(beltrano.isLinkedToActorUnit, isTrue);
    // Quem veio sem o campo permanece em "não se aplica", sem virar 'none'.
    final ciclano = cubit.state.employees.firstWhere((e) => e.id == 3);
    expect(ciclano.localUnitLinkStatus, isNull);
  });

  test('load busca também os colaboradores arquivados com outsourced_only=1', () async {
    final cubit = OutsourcedEmployeesCubit(employeesApi: employeesApi);
    await cubit.load();
    await cubit.close();
    expect(adapter.paths, contains('/api/employees/archived'));
  });

  test('search filtra por nome sem nova chamada de rede', () async {
    final cubit = OutsourcedEmployeesCubit(employeesApi: employeesApi);
    await cubit.load();
    final callsBefore = adapter.paths.length;
    cubit.search('Beltrano');
    expect(cubit.state.filtered, hasLength(1));
    expect(cubit.state.filtered.single.name, 'Terceirizado Beltrano');
    expect(adapter.paths, hasLength(callsBefore));
    await cubit.close();
  });

  test('toggleArchivedView alterna a listagem', () async {
    final cubit = OutsourcedEmployeesCubit(employeesApi: employeesApi);
    expect(cubit.state.showArchived, isFalse);
    cubit.toggleArchivedView();
    expect(cubit.state.showArchived, isTrue);
    await cubit.close();
  });

  test('createEmployee chama a rota simplificada e recarrega', () async {
    final cubit = OutsourcedEmployeesCubit(employeesApi: employeesApi);
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
    final cubit = OutsourcedEmployeesCubit(employeesApi: employeesApi);
    final ok = await cubit.archiveEmployee(2, reason: 'Contrato encerrado');
    await cubit.close();
    expect(ok, isTrue);
    expect(adapter.paths, contains('/api/employees/2/archive'));
  });

  test('restoreEmployee chama a rota de restauração e recarrega', () async {
    final cubit = OutsourcedEmployeesCubit(employeesApi: employeesApi);
    final ok = await cubit.restoreEmployee(2);
    await cubit.close();
    expect(ok, isTrue);
    expect(adapter.paths, contains('/api/employees/2/restore'));
  });
}
