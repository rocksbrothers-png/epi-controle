import 'dart:convert';
import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:epi_admin/core/bloc/outsourced_companies_cubit.dart';
import 'package:epi_api/epi_api.dart';
import 'package:flutter_test/flutter_test.dart';

/// Cadastro Simplificado de Terceirizados e Prestadores (ADR-0002) — cubit.
class _RecordingAdapter implements HttpClientAdapter {
  _RecordingAdapter({this.responseByPath = const {}});

  final Map<String, Map<String, dynamic>> responseByPath;
  final List<String> paths = [];
  final List<Object?> bodies = [];

  static const _jsonHeaders = <String, List<String>>{
    Headers.contentTypeHeader: ['application/json'],
  };

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
      jsonEncode(canned ?? {'outsourced_companies': <Map<String, dynamic>>[]}),
      200,
      headers: _jsonHeaders,
    );
  }

  @override
  void close({bool force = false}) {}
}

void main() {
  late _RecordingAdapter adapter;
  late OutsourcedCompaniesApi api;

  setUp(() {
    adapter = _RecordingAdapter();
    api = OutsourcedCompaniesApi(Dio()..httpClientAdapter = adapter);
  });

  test('load busca a lista de ativas e a de arquivadas, escopadas à empresa do ator', () async {
    final cubit = OutsourcedCompaniesCubit(api: api);
    await cubit.load();
    await cubit.close();
    expect(adapter.paths, ['/api/outsourced-companies', '/api/outsourced-companies/archived']);
  });

  test('load publica as empresas devolvidas pelo backend', () async {
    adapter = _RecordingAdapter(responseByPath: {
      '/api/outsourced-companies': {
        'outsourced_companies': [
          {'id': 1, 'company_id': 1, 'legal_name': 'Terceirizada X'},
        ],
      },
    });
    api = OutsourcedCompaniesApi(Dio()..httpClientAdapter = adapter);
    final cubit = OutsourcedCompaniesCubit(api: api);
    await cubit.load();
    expect(cubit.state.companies, hasLength(1));
    expect(cubit.state.companies.single.legalName, 'Terceirizada X');
    expect(cubit.state.isLoading, isFalse);
    await cubit.close();
  });

  test('search filtra por nome/CNPJ sem nova chamada de rede', () async {
    adapter = _RecordingAdapter(responseByPath: {
      '/api/outsourced-companies': {
        'outsourced_companies': [
          {'id': 1, 'company_id': 1, 'legal_name': 'Terceirizada X', 'cnpj': '11.222.333/0001-81'},
          {'id': 2, 'company_id': 1, 'legal_name': 'Prestadora Y'},
        ],
      },
    });
    api = OutsourcedCompaniesApi(Dio()..httpClientAdapter = adapter);
    final cubit = OutsourcedCompaniesCubit(api: api);
    await cubit.load();
    cubit.search('prestadora');
    expect(cubit.state.visible, hasLength(1));
    expect(cubit.state.visible.single.legalName, 'Prestadora Y');
    expect(adapter.paths, hasLength(2)); // GET ativas + GET arquivadas, nenhuma extra
    await cubit.close();
  });

  test('createCompany envia o corpo e recarrega a lista', () async {
    final cubit = OutsourcedCompaniesCubit(api: api);
    final ok = await cubit.createCompany({'legal_name': 'Terceirizada Nova'});
    await cubit.close();
    expect(ok, isTrue);
    // POST + reload (ativas + arquivadas)
    expect(adapter.paths, [
      '/api/outsourced-companies',
      '/api/outsourced-companies',
      '/api/outsourced-companies/archived',
    ]);
    final post = adapter.bodies.first! as Map<String, dynamic>;
    expect(post['legal_name'], 'Terceirizada Nova');
  });

  test('promoteCompany chama a rota de promoção e recarrega', () async {
    final cubit = OutsourcedCompaniesCubit(api: api);
    final ok = await cubit.promoteCompany(9);
    await cubit.close();
    expect(ok, isTrue);
    expect(adapter.paths.first, '/api/outsourced-companies/9/promote');
  });

  test('erro do backend fica disponível em state.error e não derruba o cubit', () async {
    final failingAdapter = _FailingAdapter();
    final failingApi = OutsourcedCompaniesApi(Dio()..httpClientAdapter = failingAdapter);
    final cubit = OutsourcedCompaniesCubit(api: failingApi);
    final ok = await cubit.promoteCompany(9);
    expect(ok, isFalse);
    expect(cubit.state.error, contains('CNPJ'));
    expect(cubit.state.isLoading, isFalse);
    await cubit.close();
  });

  test('toggleArchivedView alterna a listagem entre ativas e arquivadas', () async {
    final cubit = OutsourcedCompaniesCubit(api: api);
    expect(cubit.state.showArchived, isFalse);
    cubit.toggleArchivedView();
    expect(cubit.state.showArchived, isTrue);
    cubit.toggleArchivedView();
    expect(cubit.state.showArchived, isFalse);
    await cubit.close();
  });

  test('archiveCompany chama a rota de arquivamento e recarrega', () async {
    final cubit = OutsourcedCompaniesCubit(api: api);
    final ok = await cubit.archiveCompany(9, reason: 'Contrato encerrado');
    await cubit.close();
    expect(ok, isTrue);
    expect(adapter.paths.first, '/api/outsourced-companies/9/archive');
    final post = adapter.bodies.first! as Map<String, dynamic>;
    expect(post['reason'], 'Contrato encerrado');
  });

  test('restoreCompany chama a rota de restauração e recarrega', () async {
    final cubit = OutsourcedCompaniesCubit(api: api);
    final ok = await cubit.restoreCompany(9);
    await cubit.close();
    expect(ok, isTrue);
    expect(adapter.paths.first, '/api/outsourced-companies/9/restore');
  });

  test('load tolera backend sem o endpoint de arquivadas (fail-safe)', () async {
    final partialAdapter = _PartialAdapter();
    final partialApi = OutsourcedCompaniesApi(Dio()..httpClientAdapter = partialAdapter);
    final cubit = OutsourcedCompaniesCubit(api: partialApi);
    await cubit.load();
    await cubit.close();
    expect(cubit.state.archivedCompanies, isEmpty);
    expect(cubit.state.error, isNull);
  });
}

/// Simula um backend anterior à rota de arquivadas: 404 só nessa rota.
class _PartialAdapter implements HttpClientAdapter {
  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? requestStream,
    Future<void>? cancelFuture,
  ) async {
    if (options.path.endsWith('/archived')) {
      throw DioException(
        requestOptions: options,
        response: Response(requestOptions: options, statusCode: 404),
      );
    }
    return ResponseBody.fromString(
      jsonEncode({'outsourced_companies': <Map<String, dynamic>>[]}),
      200,
      headers: const {
        Headers.contentTypeHeader: ['application/json'],
      },
    );
  }

  @override
  void close({bool force = false}) {}
}

/// Simula o backend recusando a promoção sem CNPJ preenchido.
class _FailingAdapter implements HttpClientAdapter {
  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? requestStream,
    Future<void>? cancelFuture,
  ) async {
    throw DioException(
      requestOptions: options,
      response: Response(
        requestOptions: options,
        statusCode: 400,
        data: {'error': 'CNPJ é obrigatório para promover ao Cadastro Padrão.'},
      ),
    );
  }

  @override
  void close({bool force = false}) {}
}
