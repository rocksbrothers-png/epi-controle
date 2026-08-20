import 'package:epi_api/epi_api.dart';
import 'package:flutter_test/flutter_test.dart';

/// Contrato Dart da fatia 1.1D-C1 — parsing, sem consumo.
///
/// A D-C1 entrega só o contrato: nenhum Cubit ou tela lê estes campos ainda.
/// Os testes existem para que a troca dos consumidores (D-C2/D-C3) parta de um
/// modelo já provado contra o payload real do backend.
void main() {
  group('Epi — classificação por Unidade (#271)', () {
    test('lê todos os campos de /api/stock/epis sem recalcular nenhum', () {
      final epi = Epi.fromJson(const {
        'id': 7,
        'name': 'Luva nitrílica',
        'stock': 100,
        'minimum_stock': 100,
        'company_stock_quantity': 100,
        'unit_stock_quantity': 8,
        'unit_scope_id': 10,
        'unit_minimum_stock': 20,
        'minimum_stock_source': 'unit_configured',
        'effective_attention_percentage': 20,
        'attention_percentage_source': 'company_default',
        'attention_limit': 24,
        'stock_alert_enabled': false,
        'alert_source': 'unit_configured',
        'underlying_status': 'critical',
        'stock_status': 'disabled',
        'stock_condition': 'below_minimum',
      });

      expect(epi.unitMinimumStock, 20);
      expect(epi.minimumStockSource, 'unit_configured');
      expect(epi.effectiveAttentionPercentage, 20);
      expect(epi.attentionPercentageSource, 'company_default');
      expect(epi.attentionLimit, 24);
      expect(epi.stockAlertEnabled, isFalse);
      expect(epi.alertSource, 'unit_configured');
      expect(epi.underlyingStatus, 'critical');
      expect(epi.stockStatus, 'disabled');
      expect(epi.stockCondition, 'below_minimum');
    });

    test('o mínimo da Unidade é distinto do padrão da empresa', () {
      // O caso que a 1.1D-B0 corrigiu: `minimum_stock` é o padrão corporativo
      // (100) e `unit_minimum_stock` é o daquela Unidade (20). Uma tela que
      // exiba o primeiro mostra um número que não vale para o operador.
      final epi = Epi.fromJson(const {
        'id': 7,
        'name': 'Luva',
        'minimum_stock': 100,
        'unit_minimum_stock': 20,
      });
      expect(epi.minimumStock, 100);
      expect(epi.unitMinimumStock, 20);
      expect(epi.minimumStock, isNot(epi.unitMinimumStock));
    });

    test('disabled preserva underlying_status — nunca vira normal', () {
      final epi = Epi.fromJson(const {
        'id': 7,
        'name': 'Luva',
        'unit_stock_quantity': 8,
        'unit_minimum_stock': 20,
        'underlying_status': 'critical',
        'stock_status': 'disabled',
      });
      expect(epi.stockStatus, 'disabled');
      expect(epi.underlyingStatus, 'critical');
      expect(epi.stockStatus, isNot('normal'));
    });

    test('payload do bootstrap deixa a classificação nula, não zerada', () {
      // O bootstrap não tem semântica de Unidade. Zero afirmaria "mínimo zero"
      // e 'normal' afirmaria "estoque saudável" — duas mentiras sobre uma
      // Unidade que não foi resolvida.
      final epi = Epi.fromJson(const {
        'id': 7,
        'name': 'Luva',
        'stock': 100,
        'minimum_stock': 100,
      });
      expect(epi.unitMinimumStock, isNull);
      expect(epi.attentionLimit, isNull);
      expect(epi.stockAlertEnabled, isNull);
      expect(epi.underlyingStatus, isNull);
      expect(epi.stockStatus, isNull);
      expect(epi.stockCondition, isNull);
      expect(epi.minimumStockSource, isNull);
      expect(epi.alertSource, isNull);
    });

    test('copyWith preserva a classificação', () {
      final epi = Epi.fromJson(const {
        'id': 7,
        'name': 'Luva',
        'stock_status': 'near_minimum',
        'attention_limit': 24,
        'alert_source': 'system_default',
      });
      final copia = epi.copyWith(stockQuantity: 999);
      expect(copia.stockStatus, 'near_minimum');
      expect(copia.attentionLimit, 24);
      expect(copia.alertSource, 'system_default');
    });
  });

  group('DashboardSummary', () {
    const payload = {
      'scope': {
        'unit_id': 10,
        'unit_scope_source': 'actor',
        'locked': true,
        'company_id': 1,
        'legal_entity_id': 4,
        'sector': null,
      },
      'kpis': {
        'deliveries_today': 12,
        'expiring_epis': 3,
        'critical_stock': 5,
        'near_minimum_stock': 2,
        'pending_purchases': 7,
      },
      'filters': {
        'legal_entities': [
          {'id': 4, 'name': 'Skandi'},
        ],
        'units': [
          {'id': 10, 'name': 'Paraty', 'legal_entity_id': 4},
          {'id': 11, 'name': 'Amazonas', 'legal_entity_id': 4},
          {'id': 12, 'name': 'Alpha', 'legal_entity_id': 5},
        ],
        'sectors': ['Convés', 'Máquinas'],
      },
      'alerts': [
        {'type': 'danger', 'title': 'Estoque abaixo do mínimo: Luva'},
      ],
      'compliance': {
        'summary': {'ca_expired': 2, 'ca_expiring': 1},
      },
    };

    test('o escopo vem do servidor, inclusive `locked`', () {
      final resumo = DashboardSummary.fromJson(payload);
      expect(resumo.scope.unitId, 10);
      expect(resumo.scope.unitScopeSource, 'actor');
      expect(resumo.scope.locked, isTrue);
      expect(resumo.scope.legalEntityId, 4);
    });

    test('os KPIs vêm calculados', () {
      final kpis = DashboardSummary.fromJson(payload).kpis;
      expect(kpis.deliveriesToday, 12);
      expect(kpis.expiringEpis, 3);
      expect(kpis.criticalStock, 5);
      expect(kpis.nearMinimumStock, 2);
      expect(kpis.pendingPurchases, 7);
    });

    test('sem Unidade resolvida os KPIs de estoque são null, não 0', () {
      final kpis = DashboardSummary.fromJson(const {
        'kpis': {
          'deliveries_today': 4,
          'critical_stock': null,
          'near_minimum_stock': null,
        },
      }).kpis;
      expect(kpis.criticalStock, isNull);
      expect(kpis.nearMinimumStock, isNull);
      expect(kpis.deliveriesToday, 4);
    });

    test('a cascata CNPJ -> Unidade usa os dados do servidor', () {
      final filtros = DashboardSummary.fromJson(payload).filters;
      expect(filtros.unitsFor(null).length, 3);
      expect(filtros.unitsFor(4).map((u) => u.id), [10, 11]);
      expect(filtros.unitsFor(5).map((u) => u.id), [12]);
    });

    test('os setores vêm prontos — não são derivados de employees', () {
      expect(DashboardSummary.fromJson(payload).filters.sectors,
          ['Convés', 'Máquinas']);
    });

    test('compliance é lido de `summary`', () {
      expect(DashboardSummary.fromJson(payload).compliance,
          {'ca_expired': 2, 'ca_expiring': 1});
    });

    test('payload vazio degrada sem quebrar', () {
      final resumo = DashboardSummary.fromJson(const {});
      expect(resumo.scope.locked, isFalse);
      expect(resumo.scope.unitScopeSource, 'none');
      expect(resumo.kpis.criticalStock, isNull);
      expect(resumo.filters.units, isEmpty);
      expect(resumo.alerts, isEmpty);
      expect(resumo.compliance, isEmpty);
    });
  });
}
