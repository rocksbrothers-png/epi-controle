import 'package:epi_admin/core/i18n/generated/app_localizations.dart';
import 'package:epi_admin/core/i18n/localized_epi_badge.dart';
import 'package:epi_design/epi_design.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  testWidgets(
    'all status labels follow live locale changes and retain status colors',
    (tester) async {
      final locale = ValueNotifier(const Locale('pt', 'BR'));
      addTearDown(locale.dispose);
      final expected = {
        const Locale('pt', 'BR'): [
          'Ativo',
          'Inativo',
          'Vencido',
          'Vencendo',
          'Pendente',
          'Aprovado',
          'Rejeitado',
          'Em análise',
          'Sem estoque',
          'Crítico',
          'Normal',
          'Próximo do mínimo',
          'Crítico',
          'Alerta desabilitado',
        ],
        const Locale('en', 'US'): [
          'Active',
          'Inactive',
          'Expired',
          'Expiring',
          'Pending',
          'Approved',
          'Rejected',
          'In review',
          'Out of stock',
          'Critical',
          'Normal',
          'Near minimum',
          'Critical',
          'Alert disabled',
        ],
        const Locale('es', 'ES'): [
          'Activo',
          'Inactivo',
          'Vencido',
          'Por vencer',
          'Pendiente',
          'Aprobado',
          'Rechazado',
          'En revisión',
          'Sin stock',
          'Crítico',
          "Normal",
          "Cerca del mínimo",
          "Crítico",
          "Alerta desactivada",
        ],
        const Locale('fr', 'FR'): [
          'Actif',
          'Inactif',
          'Expiré',
          'Expire bientôt',
          'En attente',
          'Approuvé',
          'Rejeté',
          "En cours d'examen",
          'Rupture de stock',
          'Critique',
          "Normal",
          "Proche du minimum",
          "Critique",
          "Alerte désactivée",
        ],
        const Locale('no', 'NO'): [
          'Aktiv',
          'Inaktiv',
          'Utløpt',
          'Utløper snart',
          'Venter',
          'Godkjent',
          'Avvist',
          'Under vurdering',
          'Ikke på lager',
          'Kritisk',
          "Normal",
          "Nær minimum",
          "Kritisk",
          "Varsel deaktivert",
        ],
      };
      await tester.runAsync(() async {
        for (final target in expected.keys) {
          await AppLocalizations.delegate.load(target);
        }
      });
      // Keep the same child instances as the inherited locale changes.
      final badges = Column(
        children: [
          for (final status in EpiBadgeStatus.values)
            Row(
              children: [
                LocalizedEpiBadge(status: status),
                EpiBadge(status: status, label: 'Original <label> {status}'),
              ],
            ),
          for (final status in EpiStockStatus.values)
            Row(
              children: [
                LocalizedEpiStockBadge(status: status),
                EpiStockBadge(
                  status: status,
                  label: 'Original <label> {status}',
                ),
              ],
            ),
        ],
      );
      for (final theme in [EpiTheme.light, EpiTheme.dark]) {
        await tester.pumpWidget(
          ValueListenableBuilder<Locale>(
            valueListenable: locale,
            child: badges,
            builder: (context, value, child) => MaterialApp(
              theme: theme,
              locale: value,
              localizationsDelegates: AppLocalizations.localizationsDelegates,
              supportedLocales: AppLocalizations.supportedLocales,
              home: Scaffold(body: child),
            ),
          ),
        );
        for (final entry in expected.entries) {
          locale.value = entry.key;
          await tester.pump();
          await tester.runAsync(
            () => Future<void>.delayed(const Duration(milliseconds: 30)),
          );
          await tester.pumpAndSettle();
          final statuses = [...EpiBadgeStatus.values, ...EpiStockStatus.values];
          for (var i = 0; i < statuses.length; i++) {
            final status = statuses[i];
            final localized = find.byWidgetPredicate(
              (widget) =>
                  (widget is LocalizedEpiBadge && widget.status == status) ||
                  (widget is LocalizedEpiStockBadge && widget.status == status),
            );
            final text = find.descendant(
              of: localized,
              matching: find.byType(Text),
            );
            expect(tester.widget<Text>(text).data, entry.value[i]);
            final row = find.ancestor(
              of: localized,
              matching: find.byType(Row),
            );
            final containers = tester
                .widgetList<Container>(
                  find.descendant(of: row, matching: find.byType(Container)),
                )
                .toList();
            expect(containers, hasLength(2));
            expect(containers.first.decoration, containers.last.decoration);
            final texts = tester
                .widgetList<Text>(
                  find.descendant(of: row, matching: find.byType(Text)),
                )
                .toList();
            expect(texts.first.style, texts.last.style);
          }
          expect(find.text('Original <label> {status}'), findsNWidgets(14));
          expect(tester.takeException(), isNull);
        }
      }
    },
  );
}
