import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:epi_admin/core/bloc/outsourced_companies_cubit.dart';
import 'package:epi_api/epi_api.dart';
import 'package:flutter_test/flutter_test.dart';

/// Vínculo da empresa terceirizada com a Unidade (ADR-0002 §12, F6B da #226).
///
/// O ponto do F6B não é exibir vínculos: é dar a uma Unidade a capacidade de
/// localizar uma empresa JÁ cadastrada no tenant e criar apenas o seu vínculo
/// local — sem duplicar o cadastro corporativo e sem herdar contratos ou
/// colaboradores de outra Unidade. Boa parte destes testes, por isso, prova o
/// que o fluxo NÃO faz.
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
      jsonEncode(responseByPath[options.path] ?? {'outsourced_companies': <Map<String, dynamic>>[]}),
      200,
      headers: const {
        Headers.contentTypeHeader: ['application/json'],
      },
    );
  }

  @override
  void close({bool force = false}) {}
}

String _readScreen() => File(
      'lib/features/outsourced_companies/outsourced_companies_screen.dart',
    ).readAsStringSync();

String _readCubit() =>
    File('lib/core/bloc/outsourced_companies_cubit.dart').readAsStringSync();

/// Corpo de uma classe, do cabeçalho até a próxima declaração de topo.
///
/// Fatiar por `split` no nome da classe arrastaria o resto do arquivo junto e
/// faria qualquer varredura passar por acidente — foi exatamente assim que uma
/// checagem anterior deixou de detectar o que procurava.
String _classBody(String source, String className) {
  final start = source.indexOf('class $className');
  expect(start, isNot(-1), reason: 'classe $className não encontrada');
  final rest = source.substring(start + 1);
  final next = rest.indexOf('\nclass ');
  return next == -1 ? rest : rest.substring(0, next);
}

/// Empresa já vinculada a esta Unidade: vem completa, com `local_status`.
Map<String, dynamic> _linked(int id, String status) => {
      'id': id,
      'company_id': 1,
      'legal_name': 'Vinculada $id',
      'cnpj': '11.222.333/000$id-81',
      'local_status': status,
      'unit_link_id': 900 + id,
    };

/// Empresa do tenant ainda não vinculada: chega MASCARADA do backend —
/// só identificação, Unidade de origem e quantas Unidades já a usam.
Map<String, dynamic> _available(int id) => {
      'id': id,
      'company_id': 1,
      'legal_name': 'Disponível $id',
      'origin_unit_name': 'Unidade Central',
      'linked_units_count': 2,
    };

void main() {
  late _RecordingAdapter adapter;
  late OutsourcedCompaniesApi api;

  void useResponses(Map<String, Map<String, dynamic>> responses) {
    adapter = _RecordingAdapter(responseByPath: responses);
    api = OutsourcedCompaniesApi(Dio()..httpClientAdapter = adapter);
  }

  setUp(() => useResponses(const {}));

  group('busca no tenant', () {
    test('searchInTenant chama GET /api/outsourced-companies/search com o termo', () async {
      final cubit = OutsourcedCompaniesCubit(api: api);
      await cubit.searchInTenant('Alfa');
      await cubit.close();
      expect(adapter.paths, ['/api/outsourced-companies/search']);
      expect(adapter.methods.single, 'GET');
    });

    test('termo vazio limpa o resultado sem ir à rede', () async {
      // Buscar "" devolveria o tenant inteiro num diálogo feito para localizar
      // UMA empresa — e ainda vazaria a lista completa para quem só deveria
      // encontrar o que procura pelo nome.
      final cubit = OutsourcedCompaniesCubit(api: api);
      await cubit.searchInTenant('   ');
      expect(adapter.paths, isEmpty);
      expect(cubit.state.searchResults, isEmpty);
      expect(cubit.state.searchQuery, '');
      await cubit.close();
    });

    test('a separação dos dois blocos vem do backend, não de regra da tela', () async {
      useResponses({
        '/api/outsourced-companies/search': {
          'outsourced_companies': [
            _linked(1, kUnitLinkStatusActive),
            _available(2),
            _linked(3, kUnitLinkStatusInactive),
            _available(4),
          ],
        },
      });
      final cubit = OutsourcedCompaniesCubit(api: api);
      await cubit.searchInTenant('a');
      expect(cubit.state.searchLinked.map((c) => c.id), [1, 3]);
      expect(cubit.state.searchAvailable.map((c) => c.id), [2, 4]);
      await cubit.close();
    });

    test('o bloco "disponíveis" existe justamente para quem não tem vínculo', () async {
      // Este é o caso que a listagem comum não alcança: a Unidade nova não
      // enxerga a empresa em `/api/outsourced-companies` porque ainda não a
      // vinculou. Sem este bloco, a saída do operador seria cadastrá-la outra
      // vez — e o cadastro corporativo deve ser ÚNICO no tenant.
      useResponses({
        '/api/outsourced-companies': {'outsourced_companies': <Map<String, dynamic>>[]},
        '/api/outsourced-companies/search': {
          'outsourced_companies': [_available(7)],
        },
      });
      final cubit = OutsourcedCompaniesCubit(api: api);
      await cubit.load();
      await cubit.searchInTenant('Disp');
      expect(cubit.state.companies, isEmpty);
      expect(cubit.state.searchAvailable.single.id, 7);
      expect(cubit.state.searchAvailable.single.isMaskedForLinking, isTrue);
      await cubit.close();
    });

    test('clearTenantSearch zera resultado, termo e indicador', () async {
      useResponses({
        '/api/outsourced-companies/search': {
          'outsourced_companies': [_available(2)],
        },
      });
      final cubit = OutsourcedCompaniesCubit(api: api);
      await cubit.searchInTenant('Disp');
      expect(cubit.state.searchResults, isNotEmpty);
      cubit.clearTenantSearch();
      expect(cubit.state.searchResults, isEmpty);
      expect(cubit.state.searchQuery, '');
      expect(cubit.state.isSearching, isFalse);
      await cubit.close();
    });

    test('falha da busca reporta a mensagem do backend', () async {
      final dio = Dio()
        ..httpClientAdapter = _RecordingAdapter()
        ..interceptors.add(
          InterceptorsWrapper(
            onRequest: (options, handler) => handler.reject(
              DioException(
                requestOptions: options,
                response: Response(
                  requestOptions: options,
                  statusCode: 403,
                  data: const {'error': 'Sem permissão para consultar empresas do tenant.'},
                ),
              ),
            ),
          ),
        );
      final cubit = OutsourcedCompaniesCubit(api: OutsourcedCompaniesApi(dio));
      await cubit.searchInTenant('Alfa');
      expect(cubit.state.error, 'Sem permissão para consultar empresas do tenant.');
      expect(cubit.state.isSearching, isFalse);
      await cubit.close();
    });
  });

  group('as três operações batem nas rotas certas', () {
    test('linkCompanyToUnit → POST /api/outsourced-companies/{id}/link', () async {
      final cubit = OutsourcedCompaniesCubit(api: api);
      final ok = await cubit.linkCompanyToUnit(5);
      await cubit.close();
      expect(ok, isTrue);
      expect(adapter.paths, contains('/api/outsourced-companies/5/link'));
    });

    test('activateCompanyUnitLink → POST .../unit-link/activate', () async {
      final cubit = OutsourcedCompaniesCubit(api: api);
      final ok = await cubit.activateCompanyUnitLink(5);
      await cubit.close();
      expect(ok, isTrue);
      expect(adapter.paths, contains('/api/outsourced-companies/5/unit-link/activate'));
    });

    test('deactivateCompanyUnitLink → POST .../unit-link/deactivate, com motivo', () async {
      final cubit = OutsourcedCompaniesCubit(api: api);
      final ok = await cubit.deactivateCompanyUnitLink(5, reason: 'Contrato encerrado nesta base');
      await cubit.close();
      expect(ok, isTrue);
      final index = adapter.paths.indexOf('/api/outsourced-companies/5/unit-link/deactivate');
      expect(index, isNot(-1));
      expect((adapter.bodies[index]! as Map)['reason'], 'Contrato encerrado nesta base');
    });

    test('vincular NÃO cria nem edita o cadastro corporativo', () async {
      // Se a tela caísse em `POST /api/outsourced-companies`, o resultado
      // seria a empresa duplicada no tenant — o problema que o F6B existe
      // para eliminar.
      final cubit = OutsourcedCompaniesCubit(api: api);
      await cubit.linkCompanyToUnit(5);
      await cubit.close();
      final writes = [
        for (var i = 0; i < adapter.paths.length; i++)
          if (adapter.methods[i] != 'GET') adapter.paths[i],
      ];
      expect(writes, ['/api/outsourced-companies/5/link']);
    });

    test('nenhuma delas manda unit_id — quem escopa é o backend', () async {
      // Mandar a Unidade daqui deixaria o escopo nas mãos de quem monta o
      // request; o backend já a deriva do ator.
      final cubit = OutsourcedCompaniesCubit(api: api);
      await cubit.linkCompanyToUnit(5);
      await cubit.close();
      final index = adapter.paths.indexOf('/api/outsourced-companies/5/link');
      expect((adapter.bodies[index]! as Map).containsKey('unit_id'), isFalse);
    });
  });

  group('a tela se atualiza sozinha depois do vínculo', () {
    test('a operação recarrega a listagem E refaz a busca', () async {
      // As duas, porque a operação muda o que cada uma mostra: a empresa
      // recém-vinculada passa a aparecer na listagem da Unidade e, na busca,
      // deixa de ser "disponível" para virar "vinculada". Atualizar só uma
      // deixaria a outra mentindo até o próximo refresh manual.
      useResponses({
        '/api/outsourced-companies/search': {
          'outsourced_companies': [_available(5)],
        },
      });
      final cubit = OutsourcedCompaniesCubit(api: api);
      await cubit.searchInTenant('Disp');
      await cubit.linkCompanyToUnit(5);
      await cubit.close();
      final linkAt = adapter.paths.indexOf('/api/outsourced-companies/5/link');
      expect(linkAt, isNot(-1));
      final after = adapter.paths.sublist(linkAt + 1);
      expect(after, contains('/api/outsourced-companies'));
      expect(after, contains('/api/outsourced-companies/search'));
    });

    test('o estado novo vem do backend, não é montado a partir da resposta', () async {
      // Compor o item em memória com o `local_status` devolvido pela operação
      // traria de volta a dedução local que a #226 eliminou: a tela passaria a
      // acreditar num estado que ela mesma escreveu.
      //
      // As duas fontes discordam de propósito: a operação responde `active`,
      // a busca responde `inactive`. Quem prevalece denuncia de onde a tela
      // tirou o estado — e tem que ser a busca.
      useResponses({
        '/api/outsourced-companies/5/link': {'ok': true, 'local_status': kUnitLinkStatusActive},
        '/api/outsourced-companies/search': {
          'outsourced_companies': [_linked(5, kUnitLinkStatusInactive)],
        },
      });
      final cubit = OutsourcedCompaniesCubit(api: api);
      await cubit.searchInTenant('Disp');
      await cubit.linkCompanyToUnit(5);
      expect(cubit.state.searchLinked.single.localUnitLinkStatus, kUnitLinkStatusInactive);
      // Duas buscas: a do operador e a de depois da operação.
      expect(
        adapter.paths.where((p) => p == '/api/outsourced-companies/search'),
        hasLength(2),
      );
      await cubit.close();
    });

    test('sem busca ativa, a operação não dispara busca nenhuma', () async {
      final cubit = OutsourcedCompaniesCubit(api: api);
      await cubit.linkCompanyToUnit(5);
      await cubit.close();
      expect(adapter.paths, isNot(contains('/api/outsourced-companies/search')));
    });

    test('falha da operação reporta o erro e não recarrega', () async {
      final dio = Dio()
        ..httpClientAdapter = _RecordingAdapter()
        ..interceptors.add(
          InterceptorsWrapper(
            onRequest: (options, handler) => handler.reject(
              DioException(
                requestOptions: options,
                response: Response(
                  requestOptions: options,
                  statusCode: 403,
                  data: const {'error': 'Empresa não pertence a esta empresa.'},
                ),
              ),
            ),
          ),
        );
      final cubit = OutsourcedCompaniesCubit(api: OutsourcedCompaniesApi(dio));
      final ok = await cubit.linkCompanyToUnit(5);
      expect(ok, isFalse);
      expect(cubit.state.error, 'Empresa não pertence a esta empresa.');
      expect(cubit.state.isLoading, isFalse);
      await cubit.close();
    });

    test('os campos da busca contam como mudança de estado', () async {
      // `Equatable` compara por `props`. Um campo de fora não conta como
      // mudança e o `BlocBuilder` não reconstrói — o sintoma seria "vinculei e
      // a tela não atualizou", que pareceria bug de backend.
      const base = OutsourcedCompaniesState();
      expect(base == base.copyWith(searchQuery: 'Alfa'), isFalse);
      expect(base == base.copyWith(isSearching: true), isFalse);
      expect(
        base ==
            base.copyWith(
              searchResults: [OutsourcedCompany.fromJson(_available(2))],
            ),
        isFalse,
      );
    });
  });

  group('a tela lê o estado, não o deduz', () {
    test('os dois blocos saem dos getters, sem refiltrar na tela', () {
      // Refiltrar aqui sugeriria que o recorte é de apresentação. O
      // mascaramento é decisão do servidor: a próxima pessoa a mexer removeria
      // o filtro "redundante" achando que o backend não protege.
      final dialog = _classBody(_readScreen(), '_LinkCompanyToUnitDialogState');
      expect(dialog, contains('state.searchLinked'));
      expect(dialog, contains('state.searchAvailable'));
      expect(dialog, isNot(contains('searchResults.where(')));
      expect(RegExp(r'\.where\(').hasMatch(dialog), isFalse);
    });

    test('null é "não informado", nunca "sem vínculo"', () {
      // Para Administrador Geral, de Registro e Master a busca não anota o
      // vínculo local. Oferecer "Vincular" nesse caso agiria sobre uma empresa
      // que pode já estar vinculada.
      final tile = _classBody(_readScreen(), '_LinkableCompanyTile');
      expect(
        tile,
        contains('if (!company.isMaskedForLinking && company.localUnitLinkStatus == null)'),
      );
      expect(tile, contains('l10n.outsourcedCompanyLinkNotInformed'));
    });

    test('cada estado leva à ação certa — arquivado recebe Reativar', () {
      // Colapsar arquivado com inexistente faria a tela chamar `link`, que
      // criaria uma linha nova em vez de reaproveitar a existente e o seu
      // histórico.
      final tile = _classBody(_readScreen(), '_LinkableCompanyTile');
      for (final (state, expectedLabel) in const [
        ('kUnitLinkStatusActive', 'outsourcedCompanyLinkDeactivate'),
        ('kUnitLinkStatusInactive', 'outsourcedCompanyLinkActivate'),
      ]) {
        final match = RegExp('$state\\s*=>.*?l10n\\.(\\w+)', dotAll: true).firstMatch(tile);
        expect(match, isNotNull, reason: 'ramo $state não encontrado');
        expect(match!.group(1), expectedLabel, reason: '$state deveria oferecer $expectedLabel');
      }
    });

    test('o fluxo de vínculo não compara unitId para adivinhar o estado', () {
      // Restrito ao fluxo de vínculo de propósito: o formulário de cadastro
      // corporativo compara `unitId` legitimamente, para pré-selecionar a
      // Unidade de origem da empresa — nada a ver com deduzir vínculo local.
      final screen = _readScreen();
      final linkFlow = _classBody(screen, '_LinkCompanyToUnitDialogState') +
          _classBody(screen, '_LinkableCompanyTile');
      expect(RegExp(r'unitId\s*==').hasMatch(linkFlow), isFalse);
    });
  });

  group('nada de exclusão, nada de duplicação', () {
    test('o diálogo de vínculo não oferece ação de alcance global', () {
      // Arquivar o cadastro corporativo atinge TODAS as Unidades; o diálogo
      // trata de UMA. Misturar as duas aqui deixaria um clique de distância
      // entre "não uso mais nesta base" e "tirei do ar para o tenant inteiro".
      final dialog = _classBody(_readScreen(), '_LinkCompanyToUnitDialogState');
      for (final forbidden in const [
        'archiveCompany',
        'restoreCompany',
        'promoteCompany',
        'createCompany',
        'updateCompany',
        '_OutsourcedCompanyFormDialog',
      ]) {
        expect(dialog, isNot(contains(forbidden)), reason: '$forbidden não pertence a este fluxo');
      }
    });

    test('o cubit não expõe forma de APAGAR o vínculo', () {
      // Arquivar deixa ator e motivo registrados; apagar destravaria a
      // exclusão definitiva sem rastro. A exclusão segue exclusiva da purga,
      // regida pela retenção configurada pelo Administrador do Sistema.
      final cubit = _readCubit();
      for (final forbidden in const [
        'deleteCompanyUnitLink',
        'removeCompanyUnitLink',
        'deleteUnitLink',
        'removeUnitLink',
        'purge',
      ]) {
        expect(cubit, isNot(contains(forbidden)));
      }
    });

    test('nenhum DELETE sai do fluxo de vínculo', () {
      final source = '${_readCubit()}${_classBody(_readScreen(), '_LinkCompanyToUnitDialogState')}';
      expect(RegExp(r'\.delete\(|_dio\.delete').hasMatch(source), isFalse);
    });

    test('o botão de vincular é distinto do botão de novo cadastro', () {
      // Duas portas visíveis ao mesmo tempo: procurar o que já existe e criar
      // o que não existe. Sem a primeira, criar é a única saída — e foi assim
      // que a duplicação passou a acontecer.
      final screen = _readScreen();
      expect(screen, contains("heroTag: 'link-company-to-unit'"));
      expect(screen, contains("heroTag: 'new-company'"));
      expect(screen, contains('_openLinkFlow'));
      expect(screen, contains('_openForm'));
    });
  });
}
