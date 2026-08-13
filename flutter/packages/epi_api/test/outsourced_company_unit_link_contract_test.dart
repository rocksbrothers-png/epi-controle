import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:epi_api/epi_api.dart';
import 'package:flutter_test/flutter_test.dart';

/// Contrato Dart do vínculo de EMPRESA com a Unidade (ADR-0002 §12, F6A da
/// #226).
///
/// A empresa terceirizada é única no tenant e pode ter vínculo com várias
/// Unidades, cada um com estado próprio. O que esta camada precisa acertar não
/// é o caminho das rotas — é a leitura de dois estados que o backend expressa
/// de forma diferente da do colaborador, e que colapsados dariam à tela uma
/// visão errada de quem está vinculado a quê.
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

/// Item completo, como o backend devolve para uma empresa JÁ vinculada.
Map<String, dynamic> _linkedItem({String localStatus = 'active'}) => {
      'id': 7,
      'company_id': 1,
      'legal_name': 'Terceirizada Alfa LTDA',
      'trade_name': 'Alfa',
      'cnpj': '11.222.333/0001-81',
      'status': 'Ativa',
      'local_status': localStatus,
      'unit_link_id': 42,
    };

/// Item MASCARADO, como o backend devolve para uma empresa que a Unidade
/// ainda não vinculou: sem notas, contratos ou colaboradores de outra
/// Unidade — só o suficiente para decidir se vale reaproveitar o cadastro.
Map<String, dynamic> _maskedItem() => {
      'id': 9,
      'legal_name': 'Terceirizada Beta LTDA',
      'trade_name': 'Beta',
      'cnpj': '**.***.***/0001-**',
      'company_kind': 'outsourced',
      'registration_mode': 'simplified',
      'registration_status': 'pending_completion',
      'origin_unit_name': 'Base Santos',
      'linked_units_count': 3,
    };

void main() {
  group('OutsourcedCompany — os dois tipos de item da busca', () {
    test('empresa já vinculada traz o estado do vínculo', () {
      final company = OutsourcedCompany.fromJson(_linkedItem());
      expect(company.localUnitLinkStatus, 'active');
      expect(company.unitLinkId, 42);
      expect(company.isMaskedForLinking, isFalse);
    });

    test('vínculo arquivado nesta Unidade não é "sem vínculo"', () {
      // Distinção que decide o rótulo: "Reativar nesta Unidade" contra
      // "Vincular a esta Unidade". Reativar reaproveita a linha e o histórico;
      // vincular criaria outra.
      final company = OutsourcedCompany.fromJson(_linkedItem(localStatus: 'inactive'));
      expect(company.localUnitLinkStatus, 'inactive');
      expect(company.isMaskedForLinking, isFalse);
    });

    test('empresa disponível para vincular vem mascarada', () {
      final company = OutsourcedCompany.fromJson(_maskedItem());
      expect(company.isMaskedForLinking, isTrue);
      expect(company.localUnitLinkStatus, isNull);
      expect(company.linkedUnitsCount, 3);
      expect(company.originUnitName, 'Base Santos');
    });

    test('o mascarado expõe quem já usa a empresa, de propósito', () {
      // Reversão explícita da máscara original: a Unidade que está decidindo
      // se vincula precisa saber que outras três já usam o cadastro — sem
      // isso, reaproveitar parece mais arriscado do que criar um novo.
      final company = OutsourcedCompany.fromJson(_maskedItem());
      expect(company.linkedUnitsCount, greaterThan(0));
      expect(company.originUnitName, isNotEmpty);
    });

    test('ausência de local_status NÃO é normalizada para "none"', () {
      // A rota de busca só anota o estado para perfis escopados por Unidade.
      // Para Administrador Geral, de Registro e Master os itens voltam SEM
      // anotação — e tratá-los como "não vinculada" ofereceria "Vincular"
      // para empresa já vinculada, além de sugerir que ninguém a usa.
      final unannotated = OutsourcedCompany.fromJson({
        'id': 7,
        'company_id': 1,
        'legal_name': 'Terceirizada Alfa LTDA',
      });
      expect(unannotated.localUnitLinkStatus, isNull);
      expect(unannotated.isMaskedForLinking, isFalse,
          reason: 'sem linked_units_count não é item mascarado');
    });

    test('o discriminador de mascaramento mora num lugar só', () {
      // A detecção é indireta (presença de `linked_units_count`) porque o
      // backend não manda sinalizador explícito. Concentrá-la no modelo é o
      // que permite trocá-la numa linha se o servidor passar a mandar um
      // campo próprio — espalhada pela UI, seriam N lugares para achar.
      final source = File('lib/models/outsourced_company.dart').readAsStringSync();
      expect(
        RegExp(r"linked_units_count'\]").allMatches(source).length,
        1,
        reason: 'linked_units_count deve ser lido uma única vez, no fromJson',
      );
      expect(source, contains('bool get isMaskedForLinking'));
    });
  });

  group('OutsourcedCompaniesApi.searchOutsourcedCompanies', () {
    test('chama GET /api/outsourced-companies/search com o termo', () async {
      final adapter = _RecordingAdapter(responseByPath: {
        '/api/outsourced-companies/search': {
          'outsourced_companies': [_linkedItem(), _maskedItem()],
        },
      });
      final api = OutsourcedCompaniesApi(Dio()..httpClientAdapter = adapter);
      final result = await api.searchOutsourcedCompanies(actorUserId: 7, query: 'alfa');
      expect(adapter.paths.single, '/api/outsourced-companies/search');
      expect(adapter.methods.single, 'GET');
      expect(adapter.queries.single['q'], 'alfa');
      expect(result.map((c) => c.id), [7, 9]);
    });

    test('a busca devolve vinculadas e disponíveis na mesma lista', () async {
      // O backend usa `split=False` nesta rota: os dois tipos chegam juntos, e
      // é o cliente que os distingue por `isMaskedForLinking`. Se a tela
      // assumir que tudo que voltou está vinculado, mostrará dados
      // "faltando" para as disponíveis — que na verdade foram mascarados.
      final adapter = _RecordingAdapter(responseByPath: {
        '/api/outsourced-companies/search': {
          'outsourced_companies': [_linkedItem(), _maskedItem()],
        },
      });
      final api = OutsourcedCompaniesApi(Dio()..httpClientAdapter = adapter);
      final result = await api.searchOutsourcedCompanies(actorUserId: 7, query: '');
      expect(result.where((c) => c.isMaskedForLinking).map((c) => c.id), [9]);
      expect(result.where((c) => !c.isMaskedForLinking).map((c) => c.id), [7]);
    });

    test('resposta vazia devolve lista vazia', () async {
      final adapter = _RecordingAdapter(responseByPath: {
        '/api/outsourced-companies/search': {},
      });
      final api = OutsourcedCompaniesApi(Dio()..httpClientAdapter = adapter);
      expect(await api.searchOutsourcedCompanies(actorUserId: 7, query: 'x'), isEmpty);
    });
  });

  group('OutsourcedCompaniesApi — as três ações de vínculo', () {
    test('linkOutsourcedCompanyToUnit faz POST em /link', () async {
      final adapter = _RecordingAdapter(responseByPath: {
        '/api/outsourced-companies/9/link': {'ok': true, 'id': 55, 'unit_id': 11},
      });
      final api = OutsourcedCompaniesApi(Dio()..httpClientAdapter = adapter);
      final result = await api.linkOutsourcedCompanyToUnit(9, actorUserId: 7, unitId: 11);
      expect(adapter.paths.single, '/api/outsourced-companies/9/link');
      expect(adapter.methods.single, 'POST');
      expect((adapter.bodies.single! as Map)['unit_id'], 11);
      expect(result['unit_id'], 11);
    });

    test('sem unitId a chave não vai no corpo', () async {
      // Perfil escopado não escolhe Unidade; o backend usa a operacional dele.
      final adapter = _RecordingAdapter();
      final api = OutsourcedCompaniesApi(Dio()..httpClientAdapter = adapter);
      await api.linkOutsourcedCompanyToUnit(9, actorUserId: 7);
      expect((adapter.bodies.single! as Map).containsKey('unit_id'), isFalse);
    });

    test('activate bate em unit-link/activate', () async {
      final adapter = _RecordingAdapter(responseByPath: {
        '/api/outsourced-companies/9/unit-link/activate': {'ok': true, 'local_status': 'active'},
      });
      final api = OutsourcedCompaniesApi(Dio()..httpClientAdapter = adapter);
      final result = await api.activateOutsourcedCompanyUnitLink(9, actorUserId: 7);
      expect(adapter.paths.single, '/api/outsourced-companies/9/unit-link/activate');
      expect(result['local_status'], 'active');
    });

    test('deactivate leva o motivo e devolve inactive', () async {
      final adapter = _RecordingAdapter(responseByPath: {
        '/api/outsourced-companies/9/unit-link/deactivate': {
          'ok': true,
          'local_status': 'inactive',
        },
      });
      final api = OutsourcedCompaniesApi(Dio()..httpClientAdapter = adapter);
      final result = await api.deactivateOutsourcedCompanyUnitLink(
        9,
        actorUserId: 7,
        reason: 'Contrato encerrado nesta base',
      );
      expect(adapter.paths.single, '/api/outsourced-companies/9/unit-link/deactivate');
      expect((adapter.bodies.single! as Map)['reason'], 'Contrato encerrado nesta base');
      expect(result['local_status'], 'inactive');
    });

    test('deactivate sem motivo manda string vazia, não omite a chave', () async {
      final adapter = _RecordingAdapter();
      final api = OutsourcedCompaniesApi(Dio()..httpClientAdapter = adapter);
      await api.deactivateOutsourcedCompanyUnitLink(9, actorUserId: 7);
      expect((adapter.bodies.single! as Map)['reason'], '');
    });
  });

  group('limites', () {
    test('não existe rota para APAGAR o vínculo da empresa', () {
      // Mesma governança do vínculo de colaborador: arquivar o vínculo local
      // é como a Unidade declara que não usa mais a empresa, com ator e motivo
      // registrados. A exclusão definitiva segue exclusiva do fluxo de
      // retenção e purga.
      final source =
          File('lib/endpoints/outsourced_companies_api.dart').readAsStringSync();
      final offenders = RegExp(r"_dio\.delete[^;]*(unit-link|/link')")
          .allMatches(source)
          .map((m) => m.group(0))
          .toList();
      expect(offenders, isEmpty, reason: 'rota de remoção de vínculo: $offenders');
    });

    test('o cliente não recorta o que o servidor devolveu', () {
      // O mascaramento e o recorte por Unidade acontecem no backend
      // (`annotate_outsourced_company_visibility`). Refiltrar aqui criaria
      // uma segunda regra de visibilidade para manter em dia.
      final source =
          File('lib/endpoints/outsourced_companies_api.dart').readAsStringSync();
      final method = RegExp(
        r'searchOutsourcedCompanies\(.*?\}\s*\)\s*async \{(.*?)\n  \}',
        dotAll: true,
      ).firstMatch(source);
      expect(method, isNotNull, reason: 'searchOutsourcedCompanies não encontrado');
      expect(method!.group(1), isNot(contains('.where(')));
    });
  });
}
