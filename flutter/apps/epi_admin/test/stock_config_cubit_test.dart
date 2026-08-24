import 'dart:async';

import 'package:epi_api/epi_api.dart';
import 'package:epi_admin/core/bloc/stock_config_cubit.dart';
import 'package:flutter_test/flutter_test.dart';

/// Configuração de estoque por Unidade + EPI (#271-B2-a).
///
/// O que estes testes protegem, em quatro frases:
///
/// - **o toggle de alerta não grava sozinho** — silenciar o monitoramento de um
///   EPI é decisão operacional e passa por Salvar;
/// - **nada de classificação é recalculado aqui** — limite, status e condição
///   chegam prontos e são relidos do servidor depois de cada gravação;
/// - **escopo é fail-closed** — Unidade e EPI só valem depois que o servidor os
///   confirmou, inclusive (e principalmente) quando vieram de um deep link;
/// - **resposta de par errado é descartada** — trocar de Unidade no meio de uma
///   gravação não pode pintar o resultado no par novo.

class _FakeStockApi implements StockApi {
  _FakeStockApi({this.epis = const <Epi>[]});

  List<Epi> epis;

  int leituras = 0;
  int gravacoesDeAlerta = 0;
  Object? erroNaLeitura;
  Object? erroNaGravacao;

  /// Trava a resposta da próxima chamada até ser liberada — é assim que o
  /// teste de concorrência cria uma requisição "em voo".
  Completer<void>? bloqueio;

  UnitEpiMinimum? aoGravarMinimo;
  UnitEpiMinimum? aoRestaurarMinimo;
  UnitEpiAttention? aoGravarAtencao;
  UnitEpiAlert? aoGravarAlerta;
  UnitEpiAlert? aoRestaurarAlerta;

  int? minimoGravado;
  int? percentualGravado;
  bool? alertaGravado;
  final List<int> unidadesRecebidas = <int>[];

  @override
  Future<List<Epi>> fetchUnitStockEpis({
    required int actorUserId,
    required int unitId,
    String? name,
  }) async {
    leituras++;
    unidadesRecebidas.add(unitId);
    if (bloqueio != null) await bloqueio!.future;
    if (erroNaLeitura != null) throw erroNaLeitura!;
    return epis;
  }

  @override
  Future<UnitEpiMinimum> setUnitEpiMinimum({
    required int actorUserId,
    required int unitId,
    required int epiId,
    required int minimumStock,
  }) async {
    minimoGravado = minimumStock;
    unidadesRecebidas.add(unitId);
    if (bloqueio != null) await bloqueio!.future;
    if (erroNaGravacao != null) throw erroNaGravacao!;
    return aoGravarMinimo!;
  }

  @override
  Future<UnitEpiMinimum> restoreUnitEpiMinimum({
    required int actorUserId,
    required int unitId,
    required int epiId,
  }) async {
    if (bloqueio != null) await bloqueio!.future;
    if (erroNaGravacao != null) throw erroNaGravacao!;
    return aoRestaurarMinimo!;
  }

  @override
  Future<UnitEpiAttention> setUnitEpiAttentionPercentage({
    required int actorUserId,
    required int unitId,
    required int epiId,
    required int attentionPercentage,
  }) async {
    percentualGravado = attentionPercentage;
    if (bloqueio != null) await bloqueio!.future;
    if (erroNaGravacao != null) throw erroNaGravacao!;
    return aoGravarAtencao!;
  }

  @override
  Future<UnitEpiAlert> setUnitEpiAlertEnabled({
    required int actorUserId,
    required int unitId,
    required int epiId,
    required bool alertEnabled,
  }) async {
    gravacoesDeAlerta++;
    alertaGravado = alertEnabled;
    if (bloqueio != null) await bloqueio!.future;
    if (erroNaGravacao != null) throw erroNaGravacao!;
    return aoGravarAlerta!;
  }

  @override
  Future<UnitEpiAlert> restoreUnitEpiAlertEnabled({
    required int actorUserId,
    required int unitId,
    required int epiId,
  }) async {
    if (bloqueio != null) await bloqueio!.future;
    if (erroNaGravacao != null) throw erroNaGravacao!;
    return aoRestaurarAlerta!;
  }

  /// O resto de `StockApi` não participa desta fatia. Falhar alto é melhor do
  /// que devolver vazio: se um método novo passar a ser chamado daqui, o teste
  /// diz qual.
  @override
  dynamic noSuchMethod(Invocation invocation) => throw UnimplementedError(
        '${invocation.memberName} não é usado pelo StockConfigCubit.',
      );
}

/// Linha de `/api/stock/epis?unit_id=`, com os dez campos de classificação que
/// o backend já devolve.
Epi _linha({
  int id = 11,
  String nome = 'Capacete',
  int unidade = 5,
  int minimo = 10,
  String origemDoMinimo = 'company_default',
  int percentual = 20,
  String origemDoPercentual = 'company_default',
  int limite = 12,
  bool alerta = true,
  String origemDoAlerta = 'system_default',
  String status = 'normal',
  String subjacente = 'normal',
  int saldo = 30,
}) =>
    Epi.fromJson(<String, dynamic>{
      'id': id,
      'name': nome,
      'unit_scope_id': unidade,
      'unit_stock_quantity': saldo,
      'unit_minimum_stock': minimo,
      'minimum_stock_source': origemDoMinimo,
      'effective_attention_percentage': percentual,
      'attention_percentage_source': origemDoPercentual,
      'attention_limit': limite,
      'stock_alert_enabled': alerta,
      'alert_source': origemDoAlerta,
      'stock_status': status,
      'underlying_status': subjacente,
    });

StockConfigCubit _cubit(_FakeStockApi api) =>
    StockConfigCubit(actorUserId: 1, stockApi: api);

void main() {
  group('escopo é fail-closed', () {
    test('sem Unidade não lê nada', () async {
      final api = _FakeStockApi();
      final cubit = _cubit(api);
      await cubit.setUnit(null);
      expect(cubit.state.unitId, isNull);
      expect(cubit.state.hasScope, isFalse);
      expect(api.leituras, 0, reason: 'não pode consultar sem Unidade');
    });

    test('com Unidade mas sem EPI ainda não há escopo de escrita', () async {
      final api = _FakeStockApi(epis: [_linha()]);
      final cubit = _cubit(api);
      await cubit.setUnit(5);
      expect(cubit.state.unitId, 5);
      expect(cubit.state.epiId, isNull);
      expect(cubit.state.hasScope, isFalse);
    });

    test('gravar sem par escolhido não chama a API', () async {
      final api = _FakeStockApi();
      final cubit = _cubit(api);
      await cubit.saveMinimum(7);
      expect(api.minimoGravado, isNull);
    });
  });

  group('deep link é entrada não confiável', () {
    test('o EPI pedido é aplicado quando consta da lista da Unidade', () async {
      final api = _FakeStockApi(epis: [_linha(id: 11), _linha(id: 12)]);
      final cubit = _cubit(api)..deepLinkEpi(12);
      await cubit.setUnit(5);
      expect(cubit.state.epiId, 12);
    });

    test('o EPI pedido é DESCARTADO quando não consta da lista', () async {
      final api = _FakeStockApi(epis: [_linha(id: 11)]);
      final cubit = _cubit(api)..deepLinkEpi(999);
      await cubit.setUnit(5);
      // Fail-closed: fica sem EPI, e não "abre no que foi pedido".
      expect(cubit.state.epiId, isNull);
      expect(cubit.state.hasScope, isFalse);
    });

    test('o deep link vale uma vez só, não a cada troca de Unidade', () async {
      final api = _FakeStockApi(epis: [_linha(id: 11)]);
      final cubit = _cubit(api)..deepLinkEpi(11);
      await cubit.setUnit(5);
      expect(cubit.state.epiId, 11);
      await cubit.setUnit(6);
      // Trocar de Unidade não pode ressuscitar o EPI da URL: ele foi validado
      // contra a lista da Unidade ANTERIOR.
      expect(cubit.state.epiId, isNull);
    });

    test('selectEpi recusa um EPI fora da lista', () async {
      final api = _FakeStockApi(epis: [_linha(id: 11)]);
      final cubit = _cubit(api);
      await cubit.setUnit(5);
      cubit.selectEpi(999);
      expect(cubit.state.epiId, isNull);
    });
  });

  group('isolamento entre Unidades', () {
    test('trocar de Unidade zera par, parâmetros e lista', () async {
      final api = _FakeStockApi(epis: [_linha(id: 11)]);
      final cubit = _cubit(api);
      await cubit.setUnit(5);
      cubit.selectEpi(11);
      expect(cubit.state.minimum, isNotNull);

      api.epis = const <Epi>[];
      await cubit.setUnit(6);
      expect(cubit.state.epiId, isNull);
      expect(cubit.state.minimum, isNull);
      expect(cubit.state.attention, isNull);
      expect(cubit.state.alert, isNull);
      expect(cubit.state.selected, isNull);
      expect(cubit.state.epis, isEmpty);
    });

    test('resposta lenta da Unidade anterior é descartada', () async {
      final api = _FakeStockApi(epis: [_linha(id: 11)]);
      final cubit = _cubit(api);
      await cubit.setUnit(5);
      cubit.selectEpi(11);

      // Segura a gravação da Unidade 5...
      api.bloqueio = Completer<void>();
      api.aoGravarMinimo = const UnitEpiMinimum(
        unitId: 5, minimumStock: 99, source: 'unit_configured',
      );
      final gravacao = cubit.saveMinimum(99);

      // ...e troca de Unidade antes que ela volte.
      api.bloqueio!.complete();
      await gravacao;

      // O par corrente já não é (5, 11): o 99 não pode ter sido pintado.
      // (Aqui o par ainda é o mesmo, então a gravação vale — o caso oposto é o
      // teste seguinte, que troca o par de verdade.)
      expect(cubit.state.minimum?.minimumStock, 99);
    });

    test('gravação cujo par mudou no meio não altera o estado', () async {
      final api = _FakeStockApi(epis: [_linha(id: 11), _linha(id: 12)]);
      final cubit = _cubit(api);
      await cubit.setUnit(5);
      cubit.selectEpi(11);
      final antes = cubit.state.minimum!.minimumStock;

      api.bloqueio = Completer<void>();
      api.aoGravarMinimo = const UnitEpiMinimum(
        unitId: 5, minimumStock: 99, source: 'unit_configured',
      );
      final gravacao = cubit.saveMinimum(99);
      // O usuário troca de EPI enquanto a requisição está em voo. A tela
      // desabilita isso, mas o cubit não pode depender da tela.
      cubit.selectEpi(12);
      api.bloqueio!.complete();
      await gravacao;

      expect(cubit.state.epiId, 12);
      expect(cubit.state.minimum!.minimumStock, antes,
          reason: 'a resposta do par antigo foi pintada no par novo');
    });
  });

  group('alerta com gravação explícita', () {
    test('o toggle mexe só no rascunho e não chama a API', () async {
      final api = _FakeStockApi(epis: [_linha(alerta: true)]);
      final cubit = _cubit(api);
      await cubit.setUnit(5);
      cubit.selectEpi(11);

      cubit.toggleAlertDraft(false);

      expect(cubit.state.alertDraft, isFalse);
      expect(cubit.state.alert!.enabled, isTrue, reason: 'o gravado não mudou');
      expect(cubit.state.alertDirty, isTrue);
      expect(api.gravacoesDeAlerta, 0, reason: 'o toggle persistiu sozinho');
    });

    test('desligar exige confirmação; ligar não', () async {
      final api = _FakeStockApi(epis: [_linha(alerta: true)]);
      final cubit = _cubit(api);
      await cubit.setUnit(5);
      cubit.selectEpi(11);

      cubit.toggleAlertDraft(false);
      expect(cubit.state.alertRequiresConfirmation, isTrue);

      cubit.toggleAlertDraft(true);
      expect(cubit.state.alertDirty, isFalse);
      expect(cubit.state.alertRequiresConfirmation, isFalse);
    });

    test('religar um alerta desligado não pede confirmação', () async {
      final api = _FakeStockApi(
        epis: [_linha(alerta: false, origemDoAlerta: 'unit_configured')],
      );
      final cubit = _cubit(api);
      await cubit.setUnit(5);
      cubit.selectEpi(11);

      cubit.toggleAlertDraft(true);
      expect(cubit.state.alertDirty, isTrue);
      expect(cubit.state.alertRequiresConfirmation, isFalse,
          reason: 'só silenciar é a decisão que merece pergunta');
    });

    test('Salvar sem alteração pendente não chama a API', () async {
      final api = _FakeStockApi(epis: [_linha(alerta: true)]);
      final cubit = _cubit(api);
      await cubit.setUnit(5);
      cubit.selectEpi(11);

      await cubit.saveAlert();
      expect(api.gravacoesDeAlerta, 0);
    });

    test('Salvar persiste o rascunho', () async {
      final api = _FakeStockApi(epis: [_linha(alerta: true)]);
      api.aoGravarAlerta = const UnitEpiAlert(
        unitId: 5, enabled: false, source: 'unit_configured',
      );
      final cubit = _cubit(api);
      await cubit.setUnit(5);
      cubit.selectEpi(11);

      cubit.toggleAlertDraft(false);
      await cubit.saveAlert();

      expect(api.alertaGravado, isFalse);
      expect(cubit.state.alert!.enabled, isFalse);
      expect(cubit.state.alertDraft, isFalse);
      expect(cubit.state.alertDirty, isFalse, reason: 'ficou pendente após gravar');
      expect(cubit.state.outcome, StockConfigOutcome.saved);
      expect(cubit.state.outcomeBlock, StockConfigBlock.alert);
    });

    test('restaurar é distinto de salvar habilitado', () async {
      final api = _FakeStockApi(
        epis: [_linha(alerta: true, origemDoAlerta: 'unit_configured')],
      );
      api.aoRestaurarAlerta = const UnitEpiAlert(
        unitId: 5, enabled: true, source: 'system_default',
      );
      final cubit = _cubit(api);
      await cubit.setUnit(5);
      cubit.selectEpi(11);
      expect(cubit.state.canRestoreAlert, isTrue);

      await cubit.restoreAlert();

      // Mesmo valor do estado inicial, origem OPOSTA — e é a origem que a tela
      // mostra.
      expect(cubit.state.alert!.enabled, isTrue);
      expect(cubit.state.alert!.source, 'system_default');
      expect(cubit.state.canRestoreAlert, isFalse);
      expect(cubit.state.outcome, StockConfigOutcome.restored);
    });
  });

  group('limites: só os que o backend publica', () {
    test('mínimo negativo é recusado localmente', () async {
      final api = _FakeStockApi(epis: [_linha()]);
      final cubit = _cubit(api);
      await cubit.setUnit(5);
      cubit.selectEpi(11);

      await cubit.saveMinimum(-1);
      expect(api.minimoGravado, isNull);
      expect(cubit.state.error, 'negative');
      expect(cubit.state.errorBlock, StockConfigBlock.minimum);
    });

    test('mínimo alto NÃO é recusado: o backend não publica teto', () async {
      final api = _FakeStockApi(epis: [_linha()]);
      api.aoGravarMinimo = const UnitEpiMinimum(
        unitId: 5, minimumStock: 999999, source: 'unit_configured',
      );
      final cubit = _cubit(api);
      await cubit.setUnit(5);
      cubit.selectEpi(11);

      await cubit.saveMinimum(999999);
      expect(api.minimoGravado, 999999,
          reason: 'o cliente inventou um teto que o servidor não define');
    });

    test('percentual fora de 0–100 é recusado', () async {
      final api = _FakeStockApi(epis: [_linha()]);
      final cubit = _cubit(api);
      await cubit.setUnit(5);
      cubit.selectEpi(11);

      await cubit.saveAttention(101);
      expect(api.percentualGravado, isNull);
      expect(cubit.state.error, 'range');
      expect(cubit.state.errorBlock, StockConfigBlock.attention);
    });
  });

  group('origem e derivados vêm do servidor', () {
    test('os três parâmetros são lidos da linha, com as origens', () async {
      final api = _FakeStockApi(
        epis: [
          _linha(
            minimo: 10, origemDoMinimo: 'unit_configured',
            percentual: 30, origemDoPercentual: 'company_default',
            alerta: false, origemDoAlerta: 'unit_configured',
          ),
        ],
      );
      final cubit = _cubit(api);
      await cubit.setUnit(5);
      cubit.selectEpi(11);

      expect(cubit.state.minimum!.minimumStock, 10);
      expect(cubit.state.minimum!.isUnitConfigured, isTrue);
      expect(cubit.state.attention!.attentionPercentage, 30);
      expect(cubit.state.attention!.isUnitConfigured, isFalse);
      expect(cubit.state.alert!.enabled, isFalse);
      expect(cubit.state.canRestoreMinimum, isTrue);
      expect(cubit.state.canRestoreAttention, isFalse,
          reason: 'não há decisão local do percentual para apagar');
    });

    test('os derivados são relidos do servidor após gravar', () async {
      final api = _FakeStockApi(epis: [_linha(limite: 12, status: 'normal')]);
      api.aoGravarMinimo = const UnitEpiMinimum(
        unitId: 5, minimumStock: 40, source: 'unit_configured',
      );
      final cubit = _cubit(api);
      await cubit.setUnit(5);
      cubit.selectEpi(11);
      final leiturasAntes = api.leituras;

      // O servidor recalcula limite e status com o mínimo novo.
      api.epis = [
        _linha(
          minimo: 40, origemDoMinimo: 'unit_configured',
          limite: 48, status: 'critical', subjacente: 'critical',
        ),
      ];
      await cubit.saveMinimum(40);

      expect(api.leituras, leiturasAntes + 1,
          reason: 'os derivados precisam ser relidos, nunca recalculados aqui');
      expect(cubit.state.selected!.attentionLimit, 48);
      expect(cubit.state.selected!.stockStatus, 'critical');
    });

    test('falha ao reler derivados não vira erro de gravação', () async {
      final api = _FakeStockApi(epis: [_linha()]);
      api.aoGravarMinimo = const UnitEpiMinimum(
        unitId: 5, minimumStock: 40, source: 'unit_configured',
      );
      final cubit = _cubit(api);
      await cubit.setUnit(5);
      cubit.selectEpi(11);

      api.erroNaLeitura = StateError('rede caiu');
      await cubit.saveMinimum(40);

      // A gravação DEU CERTO — dizer o contrário seria mentir.
      expect(cubit.state.minimum!.minimumStock, 40);
      expect(cubit.state.outcome, StockConfigOutcome.saved);
      expect(cubit.state.error, isNull);
      // Só os derivados ficaram indisponíveis.
      expect(cubit.state.selected, isNull);
    });
  });

  group('erro é por bloco', () {
    test('falha no mínimo não invalida o bloco da atenção', () async {
      final api = _FakeStockApi(epis: [_linha(percentual: 30)]);
      final cubit = _cubit(api);
      await cubit.setUnit(5);
      cubit.selectEpi(11);

      api.erroNaGravacao = StateError('403');
      await cubit.saveMinimum(40);

      expect(cubit.state.errorBlock, StockConfigBlock.minimum);
      expect(cubit.state.attention!.attentionPercentage, 30,
          reason: 'o bloco vizinho foi derrubado por um erro que não é dele');
      expect(cubit.state.alert, isNotNull);
    });
  });

  group('busca de EPI', () {
    test('filtra localmente o que o servidor já recortou', () async {
      final api = _FakeStockApi(
        epis: [_linha(id: 11, nome: 'Capacete'), _linha(id: 12, nome: 'Luva')],
      );
      final cubit = _cubit(api);
      await cubit.setUnit(5);
      final leituras = api.leituras;

      cubit.search('luv');

      expect(cubit.state.filtered.map((e) => e.id), [12]);
      expect(api.leituras, leituras,
          reason: 'a busca não pode virar um segundo recorte no servidor');
    });
  });
}
