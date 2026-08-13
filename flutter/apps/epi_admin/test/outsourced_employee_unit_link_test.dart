import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:epi_admin/core/bloc/outsourced_employees_cubit.dart';
import 'package:epi_api/epi_api.dart';
import 'package:flutter_test/flutter_test.dart';

/// UI e operações do vínculo local por Unidade (ADR-0002 §13, F3 da #226).
///
/// Metade destes testes prova o que a tela NÃO faz. Um indicador que trata
/// `null` como "não vinculado", ou uma ação que oferece "Vincular" onde o
/// backend espera "Reativar", passaria em qualquer teste feliz — e só
/// apareceria como erro 400 na mão do operador.
class _RecordingAdapter implements HttpClientAdapter {
  _RecordingAdapter({this.responseByPath = const {}});

  final Map<String, Map<String, dynamic>> responseByPath;
  final List<String> paths = [];
  final List<String> methods = [];
  final List<Object?> bodies = [];

  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? requestStream,
    Future<void>? cancelFuture,
  ) async {
    paths.add(options.path);
    methods.add(options.method);
    bodies.add(options.data);
    return ResponseBody.fromString(
      jsonEncode(responseByPath[options.path] ?? {'ok': true}),
      200,
      headers: const {
        Headers.contentTypeHeader: ['application/json'],
      },
    );
  }

  @override
  void close({bool force = false}) {}
}

String _readTab() => File(
      'lib/features/outsourced_companies/outsourced_employees_tab.dart',
    ).readAsStringSync();

void main() {
  late _RecordingAdapter adapter;
  late EmployeesApi employeesApi;

  setUp(() {
    adapter = _RecordingAdapter(responseByPath: {
      '/api/employees': {
        'employees': [
          {
            'id': 2,
            'name': 'Terceirizado Beltrano',
            'tipo_vinculo': 'Terceirizado',
            'local_unit_link_status': 'none',
          },
        ],
      },
      '/api/employees/archived': {'employees': <Map<String, dynamic>>[]},
    });
    employeesApi = EmployeesApi(Dio()..httpClientAdapter = adapter);
  });

  group('as três operações batem nas rotas certas', () {
    test('linkToUnit → POST /api/employees/{id}/link', () async {
      final cubit = OutsourcedEmployeesCubit(employeesApi: employeesApi);
      final ok = await cubit.linkToUnit(2);
      await cubit.close();
      expect(ok, isTrue);
      expect(adapter.paths, contains('/api/employees/2/link'));
    });

    test('activateUnitLink → POST .../unit-link/activate', () async {
      final cubit = OutsourcedEmployeesCubit(employeesApi: employeesApi);
      final ok = await cubit.activateUnitLink(2);
      await cubit.close();
      expect(ok, isTrue);
      expect(adapter.paths, contains('/api/employees/2/unit-link/activate'));
    });

    test('deactivateUnitLink → POST .../unit-link/deactivate, com motivo', () async {
      final cubit = OutsourcedEmployeesCubit(employeesApi: employeesApi);
      final ok = await cubit.deactivateUnitLink(2, reason: 'Contrato encerrado nesta base');
      await cubit.close();
      expect(ok, isTrue);
      final index = adapter.paths.indexOf('/api/employees/2/unit-link/deactivate');
      expect(index, isNot(-1));
      expect((adapter.bodies[index]! as Map)['reason'], 'Contrato encerrado nesta base');
    });

    test('nenhuma delas manda unit_id — quem escopa é o backend', () async {
      // Mandar a Unidade daqui deixaria o escopo nas mãos de quem monta o
      // request; `resolve_actor_unit_context` já a deriva do ator.
      final cubit = OutsourcedEmployeesCubit(employeesApi: employeesApi);
      await cubit.linkToUnit(2);
      await cubit.close();
      final index = adapter.paths.indexOf('/api/employees/2/link');
      expect((adapter.bodies[index]! as Map).containsKey('unit_id'), isFalse);
    });
  });

  group('cada operação recarrega a lista', () {
    test('o novo estado vem do backend, não é montado localmente', () async {
      // Atualizar o item em memória a partir da resposta seria reconstruir o
      // estado no cliente — o que a divisão C1/C2 existe para impedir. Por
      // isso cada operação refaz `GET /api/employees`.
      final cubit = OutsourcedEmployeesCubit(employeesApi: employeesApi);
      await cubit.linkToUnit(2);
      await cubit.close();
      expect(adapter.paths.where((p) => p == '/api/employees'), hasLength(1));
      expect(
        adapter.paths.indexOf('/api/employees'),
        greaterThan(adapter.paths.indexOf('/api/employees/2/link')),
        reason: 'o recarregamento precisa vir DEPOIS da operação',
      );
    });

    test('falha da operação não recarrega e reporta o erro', () async {
      final failing = _RecordingAdapter();
      final dio = Dio()
        ..httpClientAdapter = failing
        ..interceptors.add(
          InterceptorsWrapper(
            onRequest: (options, handler) => handler.reject(
              DioException(
                requestOptions: options,
                response: Response(
                  requestOptions: options,
                  statusCode: 400,
                  data: const {'error': 'Colaborador não pode ser vinculado a Unidades.'},
                ),
              ),
            ),
          ),
        );
      final cubit = OutsourcedEmployeesCubit(employeesApi: EmployeesApi(dio));
      final ok = await cubit.linkToUnit(2);
      expect(ok, isFalse);
      // A mensagem do backend chega inteira à tela: "não pode ser vinculado"
      // explica o motivo; um "erro ao vincular" genérico não explicaria nada.
      expect(cubit.state.error, 'Colaborador não pode ser vinculado a Unidades.');
      expect(cubit.state.isLoading, isFalse);
      await cubit.close();
    });
  });

  group('a tela lê o estado, não o deduz', () {
    test('o indicador e as ações dependem de localUnitLinkStatus', () {
      final tab = _readTab();
      expect(tab, contains('employee.localUnitLinkStatus'));
    });

    test('null não renderiza indicador nem ação', () {
      // "Não se aplica" (mão de obra própria, ou sem Unidade em contexto) não
      // pode parecer com "não vinculado", que é um estado acionável.
      final tab = _readTab();
      expect(tab, contains('if (linkStatus != null) _UnitLinkBadge(status: linkStatus)'));
      expect(tab, contains('if (canManageUnitLink && linkStatus != null)'));
    });

    test('cada estado leva à ação certa — arquivado recebe Reativar', () {
      // Colapsar arquivado com inexistente faria a tela chamar `link`, que
      // criaria uma linha nova em vez de reaproveitar a existente e o seu
      // histórico. A verificação casa o estado com o rótulo que o segue,
      // tolerando reformatação: travar indentação exata quebraria no próximo
      // `dart format` sem que nada de real tivesse mudado.
      final tab = _readTab();
      for (final (state, expectedLabel) in const [
        ('kUnitLinkStatusActive', 'employeeUnitLinkDeactivate'),
        ('kUnitLinkStatusInactive', 'employeeUnitLinkActivate'),
      ]) {
        final match = RegExp('$state\\s*=>.*?l10n\\.(\\w+)', dotAll: true).firstMatch(tab);
        expect(match, isNotNull, reason: 'ramo $state não encontrado');
        expect(match!.group(1), expectedLabel, reason: '$state deveria oferecer $expectedLabel');
      }
      // E o ramo padrão (`'none'`) é o único que oferece "Vincular".
      expect(tab, contains('tooltip: l10n.employeeUnitLink,'));
    });

    test('a tela não compara unitId para adivinhar o vínculo', () {
      final tab = _readTab();
      expect(RegExp(r'unitId\s*==').hasMatch(tab), isFalse);
    });
  });

  group('permissão e limites', () {
    test('as ações exigem employees:update OU employees:update_simplified', () {
      // A dupla espelha `authorize_action_any` do backend. Exigir só a
      // primeira esconderia a ação de Administrador Local e Gestor de EPI,
      // que têm apenas a segunda — e são quem mais usa esta tela.
      final tab = _readTab();
      expect(tab, contains("hasPermission('employees:update')"));
      expect(tab, contains("hasPermission('employees:update_simplified')"));
    });

    test('o cubit não expõe forma de APAGAR o vínculo', () {
      // Governança do PR E: arquivar deixa ator e motivo registrados; apagar
      // destravaria a exclusão definitiva sem rastro.
      final cubit = File('lib/core/bloc/outsourced_employees_cubit.dart').readAsStringSync();
      expect(cubit, isNot(contains('deleteUnitLink')));
      expect(cubit, isNot(contains('removeUnitLink')));
    });

    test('arquivar o vínculo é distinto de arquivar o colaborador', () {
      // Duas ações com alcances diferentes — uma Unidade contra o tenant
      // inteiro — e a tela precisa manter as duas separadas.
      final tab = _readTab();
      expect(tab, contains('_confirmUnitLinkDeactivate'));
      expect(tab, contains('_confirmArchive'));
      expect(tab, contains('onDeactivateUnitLink'));
      expect(tab, contains('onArchive'));
    });
  });
}
