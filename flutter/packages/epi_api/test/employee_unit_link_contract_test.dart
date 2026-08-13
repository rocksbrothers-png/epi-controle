import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:epi_api/epi_api.dart';
import 'package:flutter_test/flutter_test.dart';

/// Contrato Dart do vínculo local por Unidade (ADR-0002 §13, issue #226 — F1).
///
/// Esta camada não desenha tela nenhuma. O que ela trava é o que a tela vai
/// poder assumir depois: que os quatro estados chegam distintos do backend,
/// que `null` não vira `'none'` no caminho, e que as três rotas batem nos
/// caminhos que o servidor realmente registra.
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

Employee _employeeFrom(Map<String, dynamic> extra) => Employee.fromJson({
      'id': 100,
      'name': 'Terceirizado',
      'tipo_vinculo': 'Terceirizado',
      ...extra,
    });

void main() {
  group('Employee — os quatro estados chegam distintos', () {
    test('ativo', () {
      final employee = _employeeFrom({
        'local_unit_link_status': 'active',
        'is_linked_to_actor_unit': true,
      });
      expect(employee.localUnitLinkStatus, kUnitLinkStatusActive);
      expect(employee.isLinkedToActorUnit, isTrue);
    });

    test('arquivado não é "sem vínculo"', () {
      // A distinção decide o rótulo do botão: "Reativar" contra "Vincular".
      // Colapsar os dois é o jeito mais fácil de a tela mentir sobre o estado.
      final employee = _employeeFrom({
        'local_unit_link_status': 'inactive',
        'is_linked_to_actor_unit': false,
      });
      expect(employee.localUnitLinkStatus, kUnitLinkStatusInactive);
      expect(employee.isLinkedToActorUnit, isFalse);
    });

    test('aplicável mas inexistente vem como "none"', () {
      final employee = _employeeFrom({
        'local_unit_link_status': 'none',
        'is_linked_to_actor_unit': false,
      });
      expect(employee.localUnitLinkStatus, kUnitLinkStatusNone);
      expect(employee.isLinkedToActorUnit, isFalse);
    });

    test('ausente permanece null e NÃO vira "none"', () {
      // `null` = não se aplica (mão de obra própria, ou nenhuma Unidade em
      // contexto). Se o parsing normalizasse para 'none', a tela ofereceria
      // "Vincular" para quem o backend recusa com 400.
      final employee = _employeeFrom({});
      expect(employee.localUnitLinkStatus, isNull);
      expect(employee.isLinkedToActorUnit, isFalse);
    });

    test('is_linked_to_actor_unit ausente é false, não null', () {
      final employee = _employeeFrom({'local_unit_link_status': 'active'});
      expect(employee.isLinkedToActorUnit, isFalse);
    });
  });

  group('kContractedVinculos — paridade com o backend', () {
    test('é exatamente a tripla de CONTRACTED_VINCULOS, na mesma ordem', () {
      // `modules/employees/service.py` e
      // `static/js/views/outsourced-employees-view.js` carregam a mesma lista.
      // O teste de paridade cruzada (Dart × Python × JS) entra no F2, junto
      // com o consumo; aqui fica travado o valor que esta camada publica.
      expect(kContractedVinculos, const [
        'Terceirizado',
        'Prestador de Serviço',
        'Temporário',
      ]);
    });

    test('Temporário conta como contratado', () {
      // Ele estava fora da lista que o formulário Flutter oferecia, embora o
      // backend sempre o tenha aceitado.
      expect(isContractedVinculo('Temporário'), isTrue);
    });

    test('mão de obra própria fica de fora — inclusive a que não é CLT', () {
      // O ponto inteiro de existir uma lista: `!= 'CLT'` classificaria estes
      // três como contratados.
      for (final vinculo in const ['CLT', 'Menor Aprendiz', 'Praticante', 'Estagiário']) {
        expect(isContractedVinculo(vinculo), isFalse, reason: vinculo);
      }
    });

    test('espaços em volta não mudam a resposta', () {
      expect(isContractedVinculo('  Terceirizado  '), isTrue);
    });

    test('null e vazio não são contratados', () {
      expect(isContractedVinculo(null), isFalse);
      expect(isContractedVinculo(''), isFalse);
    });
  });

  group('EmployeesApi.getEmployees', () {
    test('chama GET /api/employees e devolve a lista', () async {
      final adapter = _RecordingAdapter(responseByPath: {
        '/api/employees': {
          'employees': [
            {'id': 100, 'name': 'Terceirizado', 'local_unit_link_status': 'active'},
          ],
        },
      });
      final api = EmployeesApi(Dio()..httpClientAdapter = adapter);
      final result = await api.getEmployees(actorUserId: 7);
      expect(adapter.paths.single, '/api/employees');
      expect(adapter.methods.single, 'GET');
      expect(result.single['local_unit_link_status'], 'active');
    });

    test('sem unitId a query não carrega unit_id', () async {
      // Omitir é o caso normal: perfil escopado recebe a própria Unidade do
      // backend. Mandar `unit_id: null` viraria `unit_id=` na URL.
      final adapter = _RecordingAdapter();
      final api = EmployeesApi(Dio()..httpClientAdapter = adapter);
      await api.getEmployees(actorUserId: 7);
      expect(adapter.queries.single.containsKey('unit_id'), isFalse);
      expect(adapter.queries.single['actor_user_id'], 7);
    });

    test('com unitId a sugestão de contexto vai na query', () async {
      final adapter = _RecordingAdapter();
      final api = EmployeesApi(Dio()..httpClientAdapter = adapter);
      await api.getEmployees(actorUserId: 7, unitId: 11);
      expect(adapter.queries.single['unit_id'], 11);
    });

    test('resposta sem a chave employees devolve lista vazia', () async {
      final adapter = _RecordingAdapter(responseByPath: {'/api/employees': {}});
      final api = EmployeesApi(Dio()..httpClientAdapter = adapter);
      expect(await api.getEmployees(actorUserId: 7), isEmpty);
    });
  });

  group('EmployeesApi — as três rotas de vínculo', () {
    test('linkEmployeeToUnit faz POST em /api/employees/{id}/link', () async {
      final adapter = _RecordingAdapter(responseByPath: {
        '/api/employees/100/link': {'ok': true, 'id': 5, 'unit_id': 11},
      });
      final api = EmployeesApi(Dio()..httpClientAdapter = adapter);
      final result = await api.linkEmployeeToUnit(100, actorUserId: 7, unitId: 11);
      expect(adapter.paths.single, '/api/employees/100/link');
      expect(adapter.methods.single, 'POST');
      expect((adapter.bodies.single! as Map)['unit_id'], 11);
      expect(result['unit_id'], 11);
    });

    test('linkEmployeeToUnit sem unitId não manda a chave', () async {
      // Perfil escopado não escolhe Unidade; mandar `unit_id: null` faria o
      // resolvedor do backend receber um valor onde ele espera ausência.
      final adapter = _RecordingAdapter();
      final api = EmployeesApi(Dio()..httpClientAdapter = adapter);
      await api.linkEmployeeToUnit(100, actorUserId: 7);
      expect((adapter.bodies.single! as Map).containsKey('unit_id'), isFalse);
      expect((adapter.bodies.single! as Map)['actor_user_id'], 7);
    });

    test('activateEmployeeUnitLink bate em unit-link/activate', () async {
      final adapter = _RecordingAdapter(responseByPath: {
        '/api/employees/100/unit-link/activate': {'ok': true, 'local_status': 'active'},
      });
      final api = EmployeesApi(Dio()..httpClientAdapter = adapter);
      final result = await api.activateEmployeeUnitLink(100, actorUserId: 7);
      expect(adapter.paths.single, '/api/employees/100/unit-link/activate');
      expect(adapter.methods.single, 'POST');
      expect(result['local_status'], kUnitLinkStatusActive);
    });

    test('deactivateEmployeeUnitLink leva o motivo no corpo', () async {
      final adapter = _RecordingAdapter(responseByPath: {
        '/api/employees/100/unit-link/deactivate': {'ok': true, 'local_status': 'inactive'},
      });
      final api = EmployeesApi(Dio()..httpClientAdapter = adapter);
      final result = await api.deactivateEmployeeUnitLink(
        100,
        actorUserId: 7,
        reason: 'Contrato encerrado nesta base',
      );
      expect(adapter.paths.single, '/api/employees/100/unit-link/deactivate');
      expect((adapter.bodies.single! as Map)['reason'], 'Contrato encerrado nesta base');
      expect(result['local_status'], kUnitLinkStatusInactive);
    });

    test('deactivate sem motivo manda string vazia, não omite a chave', () async {
      // O backend lê `payload.get('reason')` e registra o valor na auditoria;
      // manter a chave deixa explícito que o motivo foi deixado em branco.
      final adapter = _RecordingAdapter();
      final api = EmployeesApi(Dio()..httpClientAdapter = adapter);
      await api.deactivateEmployeeUnitLink(100, actorUserId: 7);
      expect((adapter.bodies.single! as Map)['reason'], '');
    });

    test('o cliente não expõe nenhuma forma de APAGAR o vínculo', () {
      // Governança do PR E: o vínculo local nunca é removido automaticamente
      // para destravar a exclusão definitiva. Quem quer excluir ARQUIVA o
      // vínculo em cada Unidade, deliberadamente, deixando ator e motivo
      // registrados. Um DELETE em `.../link` ou `.../unit-link` daria a essa
      // decisão um atalho sem rastro — e o backend nem sequer registra a rota.
      final source = File('lib/endpoints/employees_api.dart').readAsStringSync();
      final offenders = RegExp(r'_dio\.delete[^;]*unit-link|_dio\.delete[^;]*/link')
          .allMatches(source)
          .map((m) => m.group(0))
          .toList();
      expect(offenders, isEmpty, reason: 'rota de remoção de vínculo introduzida: $offenders');
    });
  });

  group('EmployeesApi.getEmployeeDeletionSummary', () {
    test('chama GET /api/employees/{id}/deletion-summary', () async {
      final adapter = _RecordingAdapter(responseByPath: {
        '/api/employees/100/deletion-summary': {
          'deletion_readiness': {
            'eligible': false,
            'blocking_reasons': ['active_unit_links'],
            'blocking_unit_links': [
              {'unit_id': 10, 'unit_name': 'Base Santos'},
              {'unit_id': 11, 'unit_name': 'Plataforma P-50'},
            ],
          },
        },
      });
      final api = EmployeesApi(Dio()..httpClientAdapter = adapter);
      final result = await api.getEmployeeDeletionSummary(100, actorUserId: 7);
      expect(adapter.paths.single, '/api/employees/100/deletion-summary');
      expect(adapter.methods.single, 'GET');

      final readiness = result['deletion_readiness'] as Map;
      expect(readiness['eligible'], isFalse);
      // Todas as Unidades bloqueadoras vêm nomeadas: bloquear sem dizer onde
      // obrigaria o operador a caçar Unidade por Unidade.
      expect((readiness['blocking_unit_links'] as List).length, 2);
    });
  });

  group('EmployeesApi.getEmployeeUnitLinks (F5B)', () {
    test('chama GET /api/employees/{id}/unit-links', () async {
      final adapter = _RecordingAdapter(responseByPath: {
        '/api/employees/100/unit-links': {
          'unit_links': [
            {'unit_id': 10, 'unit_name': 'Base Santos', 'local_status': 'active'},
            {'unit_id': 11, 'unit_name': 'Plataforma P-50', 'local_status': 'inactive'},
          ],
        },
      });
      final api = EmployeesApi(Dio()..httpClientAdapter = adapter);
      final result = await api.getEmployeeUnitLinks(100, actorUserId: 7);
      expect(adapter.paths.single, '/api/employees/100/unit-links');
      expect(adapter.methods.single, 'GET');
      expect(result.map((e) => e['unit_name']), ['Base Santos', 'Plataforma P-50']);
    });

    test('resposta sem a chave unit_links devolve lista vazia', () async {
      final adapter = _RecordingAdapter(responseByPath: {
        '/api/employees/100/unit-links': {},
      });
      final api = EmployeesApi(Dio()..httpClientAdapter = adapter);
      expect(await api.getEmployeeUnitLinks(100, actorUserId: 7), isEmpty);
    });

    test('o cliente NÃO filtra o que o servidor devolveu', () {
      // O recorte por Unidade é regra de AUTORIZAÇÃO, aplicada no backend
      // antes da resposta. Refiltrar aqui sugeriria que a lista completa
      // chegou e está só escondida — e a próxima pessoa a mexer removeria o
      // filtro "redundante" achando que o servidor não protege.
      final source = File('lib/endpoints/employees_api.dart').readAsStringSync();
      final method = RegExp(
        r'getEmployeeUnitLinks\(.*?\}\s*\)\s*async \{(.*?)\n  \}',
        dotAll: true,
      ).firstMatch(source);
      expect(method, isNotNull, reason: 'getEmployeeUnitLinks não encontrado');
      final body = method!.group(1)!;
      for (final forbidden in const ['.where(', 'unit_id ==', 'local_status ==']) {
        expect(body, isNot(contains(forbidden)),
            reason: 'o cliente não pode recortar a resposta: $forbidden');
      }
    });

    test('não existe verbo de escrita para unit-links', () {
      final source = File('lib/endpoints/employees_api.dart').readAsStringSync();
      for (final verb in const ['_dio.post', '_dio.put', '_dio.patch', '_dio.delete']) {
        final offenders = RegExp('$verb' r"[^;]*unit-links'").allMatches(source);
        expect(offenders, isEmpty, reason: '$verb apontando para unit-links');
      }
    });
  });
}
