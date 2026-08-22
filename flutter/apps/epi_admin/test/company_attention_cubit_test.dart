import 'package:epi_api/epi_api.dart';
import 'package:epi_admin/core/bloc/company_attention_cubit.dart';
import 'package:flutter_test/flutter_test.dart';

/// Padrão CORPORATIVO da faixa de atenção (#271-B2-b).
///
/// O que estes testes protegem, em uma frase: **salvar 20% e restaurar o
/// padrão de 20% terminam com o mesmo número e significam coisas opostas.**
/// Toda a fatia existe para não perder essa distinção — no backend ela é uma
/// linha que existe ou não existe; aqui ela é a origem que o servidor devolve
/// e que a tela nunca pode deduzir do botão clicado.

class _FakeStockApi implements StockApi {
  _FakeStockApi({this.aoLer, this.aoGravar, this.aoRestaurar, this.erro});

  final CompanyAttentionSetting? aoLer;
  final CompanyAttentionSetting? aoGravar;
  final CompanyAttentionSetting? aoRestaurar;
  final Object? erro;

  int leituras = 0;
  int gravacoes = 0;
  int restauracoes = 0;
  int? percentualGravado;
  int? empresaRecebidaNaLeitura;
  int? empresaRecebidaNaGravacao;
  bool empresaEnviadaNaLeitura = false;

  @override
  Future<CompanyAttentionSetting> getCompanyAttentionPercentage({
    required int actorUserId,
    int? companyId,
  }) async {
    leituras++;
    empresaRecebidaNaLeitura = companyId;
    empresaEnviadaNaLeitura = companyId != null;
    if (erro != null) throw erro!;
    return aoLer!;
  }

  @override
  Future<CompanyAttentionSetting> setCompanyAttentionPercentage({
    required int actorUserId,
    required int attentionPercentage,
    int? companyId,
  }) async {
    gravacoes++;
    percentualGravado = attentionPercentage;
    empresaRecebidaNaGravacao = companyId;
    if (erro != null) throw erro!;
    return aoGravar!;
  }

  @override
  Future<CompanyAttentionSetting> restoreCompanyAttentionPercentage({
    required int actorUserId,
    int? companyId,
  }) async {
    restauracoes++;
    if (erro != null) throw erro!;
    return aoRestaurar!;
  }

  /// O resto de `StockApi` não participa desta fatia. Falhar alto é melhor do
  /// que devolver vazio: se um método novo passar a ser chamado daqui, o teste
  /// diz qual.
  @override
  dynamic noSuchMethod(Invocation invocation) => throw UnimplementedError(
        '${invocation.memberName} não é usado pelo CompanyAttentionCubit.',
      );
}

CompanyAttentionSetting _config({
  int valor = 20,
  String origem = CompanyAttentionSetting.sourceSystemDefault,
  int padraoDoSistema = 20,
  int teto = 100,
  bool? temConfig,
}) =>
    CompanyAttentionSetting(
      companyId: 7,
      attentionPercentage: valor,
      source: origem,
      hasCompanyConfig:
          temConfig ?? (origem == CompanyAttentionSetting.sourceCompanyConfigured),
      systemDefaultPercentage: padraoDoSistema,
      maxPercentage: teto,
    );

/// Resposta de POST: o backend devolve valor e origem, e NÃO repete
/// `system_default_percentage` nem `max_percentage`.
CompanyAttentionSetting _respostaDePost({
  required int valor,
  required String origem,
}) =>
    CompanyAttentionSetting.fromJson({
      'ok': true,
      'company_id': 7,
      'attention_percentage': valor,
      'source': origem,
    });

void main() {
  group('leitura', () {
    test('carrega valor, origem e os limites vindos do servidor', () async {
      final api = _FakeStockApi(
        aoLer: _config(valor: 30, origem: 'company_configured'),
      );
      final cubit = CompanyAttentionCubit(actorUserId: 1, stockApi: api);

      await cubit.load();

      expect(cubit.state.status, CompanyAttentionStatus.ready);
      expect(cubit.state.setting!.attentionPercentage, 30);
      expect(cubit.state.setting!.isCompanyConfigured, isTrue);
      expect(cubit.state.setting!.maxPercentage, 100);
      expect(cubit.state.setting!.systemDefaultPercentage, 20);
    });

    test('sem empresa escolhida, company_id não é enviado', () async {
      final api = _FakeStockApi(aoLer: _config());
      final cubit = CompanyAttentionCubit(actorUserId: 1, stockApi: api);

      await cubit.load();

      expect(api.empresaEnviadaNaLeitura, isFalse,
          reason: 'a tela não escolhe a empresa de um admin de empresa');
    });

    test('master_admin: a empresa escolhida é transportada', () async {
      final api = _FakeStockApi(aoLer: _config());
      final cubit = CompanyAttentionCubit(actorUserId: 1, stockApi: api);

      await cubit.load(companyId: 42);

      expect(api.empresaRecebidaNaLeitura, 42);
    });

    test('erro na leitura não inventa configuração', () async {
      final api = _FakeStockApi(erro: StateError('500'));
      final cubit = CompanyAttentionCubit(actorUserId: 1, stockApi: api);

      await cubit.load();

      expect(cubit.state.status, CompanyAttentionStatus.error);
      expect(cubit.state.setting, isNull);
    });
  });

  group('salvar não é restaurar', () {
    test('salvar 20 deixa a empresa company_configured', () async {
      final api = _FakeStockApi(
        aoLer: _config(valor: 20, origem: 'system_default'),
        aoGravar: _respostaDePost(valor: 20, origem: 'company_configured'),
      );
      final cubit = CompanyAttentionCubit(actorUserId: 1, stockApi: api);
      await cubit.load();

      await cubit.save(20);

      expect(api.gravacoes, 1);
      expect(cubit.state.setting!.attentionPercentage, 20);
      expect(cubit.state.setting!.source, 'company_configured');
      expect(cubit.state.savedFeedback, CompanyAttentionOutcome.saved);
    });

    test('restaurar deixa a empresa system_default com o MESMO número',
        () async {
      final api = _FakeStockApi(
        aoLer: _config(valor: 20, origem: 'company_configured'),
        aoRestaurar: _respostaDePost(valor: 20, origem: 'system_default'),
      );
      final cubit = CompanyAttentionCubit(actorUserId: 1, stockApi: api);
      await cubit.load();

      await cubit.restoreSystemDefault();

      expect(api.restauracoes, 1);
      expect(cubit.state.setting!.attentionPercentage, 20,
          reason: 'mesmo valor de salvar 20');
      expect(cubit.state.setting!.source, 'system_default',
          reason: 'e origem OPOSTA — é isso que a fatia protege');
      expect(cubit.state.savedFeedback, CompanyAttentionOutcome.restored);
    });

    test('restaurar não é save(padrão do sistema)', () async {
      final api = _FakeStockApi(
        aoLer: _config(valor: 35, origem: 'company_configured'),
        aoRestaurar: _respostaDePost(valor: 20, origem: 'system_default'),
      );
      final cubit = CompanyAttentionCubit(actorUserId: 1, stockApi: api);
      await cubit.load();

      await cubit.restoreSystemDefault();

      expect(api.gravacoes, 0,
          reason: 'restaurar APAGA a linha; gravar 20 criaria outra');
      expect(api.restauracoes, 1);
    });

    test('a origem vem do servidor, não da ação executada', () async {
      // Servidor teimoso: responde `system_default` a um POST de gravação.
      // A tela precisa acreditar nele, não no botão que foi clicado.
      final api = _FakeStockApi(
        aoLer: _config(origem: 'company_configured'),
        aoGravar: _respostaDePost(valor: 20, origem: 'system_default'),
      );
      final cubit = CompanyAttentionCubit(actorUserId: 1, stockApi: api);
      await cubit.load();

      await cubit.save(20);

      expect(cubit.state.setting!.source, 'system_default');
      expect(cubit.state.canRestore, isFalse);
    });
  });

  group('restaurar só quando há o que apagar', () {
    test('system_default: restaurar desabilitado', () async {
      final api = _FakeStockApi(aoLer: _config(origem: 'system_default'));
      final cubit = CompanyAttentionCubit(actorUserId: 1, stockApi: api);

      await cubit.load();

      expect(cubit.state.canRestore, isFalse);
    });

    test('company_configured: restaurar habilitado', () async {
      final api = _FakeStockApi(aoLer: _config(origem: 'company_configured'));
      final cubit = CompanyAttentionCubit(actorUserId: 1, stockApi: api);

      await cubit.load();

      expect(cubit.state.canRestore, isTrue);
    });
  });

  group('limites e validação', () {
    test('o teto sobrevive ao POST que não o repete', () async {
      final api = _FakeStockApi(
        aoLer: _config(teto: 100, padraoDoSistema: 20),
        aoGravar: _respostaDePost(valor: 30, origem: 'company_configured'),
      );
      final cubit = CompanyAttentionCubit(actorUserId: 1, stockApi: api);
      await cubit.load();

      await cubit.save(30);

      expect(cubit.state.setting!.maxPercentage, 100,
          reason: 'sem o merge, o teto viraria 0 e tudo passaria a ser inválido');
      expect(cubit.state.setting!.systemDefaultPercentage, 20);
    });

    test('acima do teto é recusado sem ida ao servidor', () async {
      final api = _FakeStockApi(aoLer: _config(teto: 100));
      final cubit = CompanyAttentionCubit(actorUserId: 1, stockApi: api);
      await cubit.load();

      await cubit.save(101);

      expect(api.gravacoes, 0);
      expect(cubit.state.status, CompanyAttentionStatus.error);
      expect(cubit.state.error, 'range');
    });

    test('o teto é o do SERVIDOR, não uma constante do cliente', () async {
      // Servidor com teto 50: 60 tem de ser recusado, mesmo sendo < 100.
      final api = _FakeStockApi(aoLer: _config(teto: 50));
      final cubit = CompanyAttentionCubit(actorUserId: 1, stockApi: api);
      await cubit.load();

      await cubit.save(60);

      expect(api.gravacoes, 0);
      expect(cubit.state.error, 'range');
    });

    test('zero é valor VÁLIDO e chega ao servidor', () async {
      final api = _FakeStockApi(
        aoLer: _config(valor: 20, origem: 'system_default'),
        aoGravar: _respostaDePost(valor: 0, origem: 'company_configured'),
      );
      final cubit = CompanyAttentionCubit(actorUserId: 1, stockApi: api);
      await cubit.load();

      await cubit.save(0);

      expect(api.gravacoes, 1);
      expect(api.percentualGravado, 0,
          reason: '0 significa "sem faixa laranja, só crítico"');
      expect(cubit.state.setting!.attentionPercentage, 0);
      expect(cubit.state.setting!.isCompanyConfigured, isTrue,
          reason: '0 configurado não é ausência de configuração');
    });

    test('negativo é recusado', () async {
      final api = _FakeStockApi(aoLer: _config());
      final cubit = CompanyAttentionCubit(actorUserId: 1, stockApi: api);
      await cubit.load();

      await cubit.save(-1);

      expect(api.gravacoes, 0);
      expect(cubit.state.error, 'range');
    });
  });

  group('fail-closed', () {
    test('sem leitura prévia não grava nada', () async {
      final api = _FakeStockApi(aoLer: _config());
      final cubit = CompanyAttentionCubit(actorUserId: 1, stockApi: api);

      await cubit.save(30);

      expect(api.gravacoes, 0,
          reason: 'sem os limites do servidor não há régua para validar contra');
      expect(api.leituras, 0);
    });

    test('sem leitura prévia não restaura nada', () async {
      final api = _FakeStockApi(aoLer: _config());
      final cubit = CompanyAttentionCubit(actorUserId: 1, stockApi: api);

      await cubit.restoreSystemDefault();

      expect(api.restauracoes, 0);
    });

    test('a empresa do master é reusada ao gravar', () async {
      final api = _FakeStockApi(
        aoLer: _config(),
        aoGravar: _respostaDePost(valor: 30, origem: 'company_configured'),
      );
      final cubit = CompanyAttentionCubit(actorUserId: 1, stockApi: api);
      await cubit.load(companyId: 42);

      await cubit.save(30);

      expect(api.empresaRecebidaNaGravacao, 42,
          reason: 'gravar na empresa que foi lida, nunca noutra');
    });
  });

  group('contrato do modelo', () {
    test('has_company_config ausente no POST é derivado da origem', () {
      final gravado =
          _respostaDePost(valor: 30, origem: 'company_configured');
      final restaurado =
          _respostaDePost(valor: 20, origem: 'system_default');

      expect(gravado.hasCompanyConfig, isTrue);
      expect(restaurado.hasCompanyConfig, isFalse);
    });

    test('o GET traz has_company_config explícito e ele manda', () {
      final lido = CompanyAttentionSetting.fromJson({
        'company_id': 7,
        'attention_percentage': 20,
        'source': 'system_default',
        'has_company_config': false,
        'system_default_percentage': 20,
        'max_percentage': 100,
      });

      expect(lido.hasCompanyConfig, isFalse);
      expect(lido.isSystemDefault, isTrue);
      expect(lido.attentionPercentage, 20);
    });
  });
}
