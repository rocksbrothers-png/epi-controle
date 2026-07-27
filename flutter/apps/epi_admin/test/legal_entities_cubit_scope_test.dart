import 'dart:convert';
import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:epi_admin/core/bloc/legal_entities_cubit.dart';
import 'package:epi_api/epi_api.dart';
import 'package:flutter_test/flutter_test.dart';

/// O recorte por empresa precisa **mudar o endpoint chamado**, não só o título.
///
/// Se o cubit recortado continuasse batendo em `/api/legal-entities`, o Admin
/// Master veria os CNPJs de todos os clientes sob o nome de um só — e
/// cadastraria no cliente errado sem nenhum sinal na tela.
class _RecordingAdapter implements HttpClientAdapter {
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
    return ResponseBody.fromString(
      jsonEncode({'legal_entities': <Map<String, dynamic>>[]}),
      200,
      headers: _jsonHeaders,
    );
  }

  @override
  void close({bool force = false}) {}
}

void main() {
  late _RecordingAdapter adapter;
  late LegalEntitiesApi api;

  setUp(() {
    adapter = _RecordingAdapter();
    api = LegalEntitiesApi(Dio()..httpClientAdapter = adapter);
  });

  test('sem recorte usa a rota da própria empresa do usuário', () async {
    final cubit = LegalEntitiesCubit(api: api);
    await cubit.load();
    await cubit.close();
    expect(adapter.paths.single, '/api/legal-entities');
  });

  test('com recorte busca os CNPJs daquela empresa', () async {
    final cubit = LegalEntitiesCubit(companyId: 42, api: api);
    await cubit.load();
    await cubit.close();
    expect(adapter.paths.single, '/api/companies/42/legal-entities');
  });

  test('cadastro no recorte informa a empresa ao backend', () async {
    // O Admin Master não tem empresa própria: sem `company_id` no corpo, o
    // backend recusa com "Campo obrigatório: company_id".
    final cubit = LegalEntitiesCubit(companyId: 42, api: api);
    await cubit.createEntity({'cnpj': '11.222.333/0001-81', 'legal_name': 'X'});
    await cubit.close();

    final post = adapter.bodies.first! as Map<String, dynamic>;
    expect(post['company_id'], 42);
    expect(post['cnpj'], '11.222.333/0001-81');
  });

  test('cadastro sem recorte não inventa company_id', () async {
    // Usuário comum: quem decide a empresa é o backend, pelo ator. Enviar um
    // palpite daqui seria uma forma de escrever na empresa errada.
    final cubit = LegalEntitiesCubit(api: api);
    await cubit.createEntity({'cnpj': '11.222.333/0001-81', 'legal_name': 'X'});
    await cubit.close();

    final post = adapter.bodies.first! as Map<String, dynamic>;
    expect(post.containsKey('company_id'), isFalse);
  });

  test('importação de planilha respeita o mesmo recorte do cadastro', () async {
    final cubit = LegalEntitiesCubit(companyId: 42, api: api);
    await cubit.importRows([
      {'CNPJ': '11.222.333/0001-81'},
    ]);
    await cubit.close();

    final post = adapter.bodies.first! as Map<String, dynamic>;
    expect(post['company_id'], 42);
  });
}
