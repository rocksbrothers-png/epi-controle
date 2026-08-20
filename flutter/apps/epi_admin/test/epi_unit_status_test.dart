import 'package:epi_admin/core/utils/epi_status_utils.dart';
import 'package:epi_api/epi_api.dart';
import 'package:epi_design/epi_design.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

/// Consumo da classificação por Unidade (#271) no Flutter — fatia 1.1D-C2.
///
/// O cliente não classifica estoque. Ele transporta `stock_status`, decidido
/// pelo backend, até a cor e o rótulo. Estes testes travam essa fronteira: cada
/// estado tem uma apresentação, `disabled` nunca vira `normal`, e a ausência de
/// classificação não vira estado nenhum.
Epi _epi({
  String? stockStatus,
  String? underlyingStatus,
  int? unitStock,
  int? unitMinimum,
  int? attentionLimit,
  int stock = 100,
  int minimumStock = 100,
  bool? companyCritical,
  String? caExpiry,
}) =>
    Epi.fromJson({
      'id': 7,
      'name': 'Luva nitrílica',
      'stock': stock,
      'minimum_stock': minimumStock,
      if (companyCritical != null) 'is_company_stock_critical': companyCritical,
      if (unitStock != null) 'unit_stock_quantity': unitStock,
      if (unitMinimum != null) 'unit_minimum_stock': unitMinimum,
      if (attentionLimit != null) 'attention_limit': attentionLimit,
      if (stockStatus != null) 'stock_status': stockStatus,
      if (underlyingStatus != null) 'underlying_status': underlyingStatus,
      if (caExpiry != null) 'ca_expiry': caExpiry,
    });

/// Executa [corpo] com um `BuildContext` real sob um tema claro — as cores dos
/// estados dependem do `ColorScheme`, então um contexto de mentira mentiria
/// justamente sobre o que está em teste.
Future<void> _comContexto(
  WidgetTester tester,
  void Function(BuildContext context) corpo,
) async {
  await tester.pumpWidget(MaterialApp(
    theme: ThemeData.light(),
    home: Builder(builder: (context) {
      corpo(context);
      return const SizedBox.shrink();
    }),
  ));
}

void main() {
  group('epiUnitBadgeStatus — os quatro estados do backend', () {
    test('critical é o estado crítico, com o rótulo do estado', () {
      final status = epiUnitBadgeStatus(_epi(stockStatus: 'critical'));
      expect(status, EpiStockStatus.critical);
      expect(EpiStockBadge.defaultLabel(status!), 'Crítico');
      expect(epiIsUnitCritical(_epi(stockStatus: 'critical')), isTrue);
    });

    test('near_minimum é a faixa de atenção', () {
      expect(
        epiUnitBadgeStatus(_epi(stockStatus: 'near_minimum')),
        EpiStockStatus.nearMinimum,
      );
      expect(epiIsUnitCritical(_epi(stockStatus: 'near_minimum')), isFalse);
    });

    test('normal é normal e não conta como crítico', () {
      expect(
        epiUnitBadgeStatus(_epi(stockStatus: 'normal')),
        EpiStockStatus.normal,
      );
      expect(epiIsUnitCritical(_epi(stockStatus: 'normal')), isFalse);
    });

    test('disabled NÃO conta como crítico', () {
      final epi = _epi(stockStatus: 'disabled');
      expect(epiUnitBadgeStatus(epi), EpiStockStatus.disabled);
      expect(epiIsUnitCritical(epi), isFalse);
    });

    test('underlying_status critical + stock_status disabled continua disabled',
        () {
      // O EPI está de fato abaixo do mínimo daquela Unidade. O que está
      // desligado é o alerta, não o problema — e a tela mostra o que a Unidade
      // escolheu ver.
      final epi = _epi(
        stockStatus: 'disabled',
        underlyingStatus: 'critical',
        unitStock: 2,
        unitMinimum: 20,
      );
      expect(epi.underlyingStatus, 'critical');
      expect(epiUnitBadgeStatus(epi), EpiStockStatus.disabled);
      expect(epiUnitBadgeStatus(epi), isNot(EpiStockStatus.critical));
      expect(epiIsUnitCritical(epi), isFalse);
    });
  });

  group('cores dos estados', () {
    testWidgets('critical vermelho, near_minimum laranja, normal verde',
        (tester) async {
      await _comContexto(tester, (context) {
        expect(
          EpiStockBadge.accentColor(EpiStockStatus.critical, context),
          EpiColors.danger,
        );
        expect(
          EpiStockBadge.accentColor(EpiStockStatus.nearMinimum, context),
          EpiColors.warning,
        );
        expect(
          EpiStockBadge.accentColor(EpiStockStatus.normal, context),
          EpiColors.success,
        );
      });
    });

    testWidgets('disabled é cinza — nunca verde de "normal"', (tester) async {
      await _comContexto(tester, (context) {
        final cor = EpiStockBadge.accentColor(EpiStockStatus.disabled, context);
        expect(cor, Theme.of(context).colorScheme.outline);
        expect(cor, isNot(EpiColors.success));
        expect(cor, isNot(EpiColors.warning));
        expect(cor, isNot(EpiColors.danger));
        expect(
          cor,
          isNot(EpiStockBadge.accentColor(EpiStockStatus.normal, context)),
        );
      });
    });

    testWidgets('o badge de disabled desenha o próprio rótulo', (tester) async {
      await tester.pumpWidget(const MaterialApp(
        home: Scaffold(
          body: EpiStockBadge(status: EpiStockStatus.disabled),
        ),
      ));
      expect(find.text('Alertas desativados'), findsOneWidget);
      expect(find.text('Normal'), findsNothing);
    });
  });

  group('ausência de classificação', () {
    test('stock_status nulo NÃO vira normal', () {
      final epi = _epi(unitStock: 8, unitMinimum: 20);
      expect(epi.stockStatus, isNull);
      expect(epiUnitBadgeStatus(epi), isNull);
      expect(epiUnitBadgeStatus(epi), isNot(EpiStockStatus.normal));
      expect(epiIsUnitCritical(epi), isFalse);
    });

    test('saldo abaixo do mínimo da Unidade não produz crítico sozinho', () {
      // 2 <= 20 e ainda assim NÃO é crítico: quem classifica é o servidor.
      // Sem `stock_status` não há veredicto — nem crítico, nem normal.
      final epi = _epi(unitStock: 2, unitMinimum: 20, stock: 2);
      expect(epiUnitBadgeStatus(epi), isNull);
      expect(epiIsUnitCritical(epi), isFalse);
    });

    test('status desconhecido de um backend mais novo também é null', () {
      expect(epiUnitBadgeStatus(_epi(stockStatus: 'quarantined')), isNull);
    });
  });

  group('epiUnitStockGauge — a barra mede a faixa de atenção', () {
    test('usa attention_limit, não o mínimo corporativo', () {
      // Mínimo da empresa 100, mínimo da Unidade 20, limite 24, saldo 12.
      // Metade da faixa da Unidade — e não 12/300 pela régua corporativa.
      final epi = _epi(
        unitStock: 12,
        unitMinimum: 20,
        attentionLimit: 24,
        minimumStock: 100,
        stockStatus: 'critical',
      );
      expect(epiUnitStockGauge(epi), closeTo(0.5, 0.0001));
      expect(epiUnitStockGauge(epi), isNot(closeTo(12 / 300, 0.0001)));
    });

    test('satura em 1.0 acima do limite', () {
      expect(epiUnitStockGauge(_epi(unitStock: 900, attentionLimit: 24)), 1.0);
    });

    test('limite zero enche a barra em vez de dividir por zero', () {
      expect(epiUnitStockGauge(_epi(unitStock: 0, attentionLimit: 0)), 1.0);
    });

    test('sem attention_limit não há barra', () {
      expect(epiUnitStockGauge(_epi(unitStock: 12, minimumStock: 100)), isNull);
    });
  });

  group('separação entre catálogo corporativo e Unidade', () {
    test('epiBadgeStatus usa a criticidade CORPORATIVA do backend', () {
      expect(
        epiBadgeStatus(_epi(companyCritical: true)),
        EpiBadgeStatus.critical,
      );
      expect(
        epiBadgeStatus(_epi(companyCritical: false)),
        EpiBadgeStatus.active,
      );
    });

    test('epiBadgeStatus ignora a classificação da Unidade', () {
      // Catálogo é corporativo: um EPI crítico numa Unidade e folgado na
      // empresa não pode aparecer como crítico na lista de EPIs.
      final epi = _epi(
        companyCritical: false,
        stockStatus: 'critical',
        unitStock: 1,
        unitMinimum: 20,
      );
      expect(epiBadgeStatus(epi), EpiBadgeStatus.active);
    });

    test('epiBadgeStatus não deduz criticidade quando o backend não a envia',
        () {
      // Sem `is_company_stock_critical` não há veredicto corporativo. Saldo 5
      // contra mínimo 100 continua `active`: o antigo `isCriticalStock` diria
      // `critical` aqui.
      expect(
        epiBadgeStatus(_epi(stock: 5, minimumStock: 100)),
        EpiBadgeStatus.active,
      );
    });

    test('validade e estoque são eixos independentes', () {
      final vencido = _epi(companyCritical: true, caExpiry: '2000-01-01');
      expect(epiValidityBadgeStatus(vencido), EpiBadgeStatus.expired);
      // Validade tem precedência no badge do catálogo, mas é outra função: a
      // tela de estoque desenha os dois eixos lado a lado.
      expect(epiBadgeStatus(vencido), EpiBadgeStatus.expired);
      expect(epiValidityBadgeStatus(_epi()), isNull);
    });
  });
}
