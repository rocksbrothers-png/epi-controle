import 'package:epi_design/epi_design.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  for (final scale in [1.0, 1.3, 1.6]) {
    testWidgets(
      'long translated action wraps and stays operable at scale $scale',
      (tester) async {
        var pressed = 0;
        const label = 'Enregistrer le nouveau mot de passe';
        await tester.pumpWidget(
          MaterialApp(
            theme: EpiTheme.light,
            home: Scaffold(
              body: MediaQuery(
                data: MediaQueryData(textScaler: TextScaler.linear(scale)),
                child: Center(
                  child: SizedBox(
                    width: 220,
                    child: EpiButton(
                      label: label,
                      icon: Icons.save,
                      onPressed: () => pressed++,
                      fullWidth: true,
                    ),
                  ),
                ),
              ),
            ),
          ),
        );
        await tester.pumpAndSettle();
        expect(tester.takeException(), isNull);
        expect(find.text(label), findsOneWidget);
        expect(
          tester.getSize(find.byType(EpiButton)).height,
          greaterThanOrEqualTo(40),
        );
        await tester.tap(find.text(label));
        expect(pressed, 1);
      },
    );
    testWidgets('localized long KPI value fits a narrow card at scale $scale', (
      tester,
    ) async {
      const value = '12 345 678';
      await tester.pumpWidget(
        MaterialApp(
          theme: EpiTheme.light,
          home: Scaffold(
            body: MediaQuery(
              data: MediaQueryData(textScaler: TextScaler.linear(scale)),
              child: const Center(
                child: SizedBox(
                  width: 140,
                  height: 200,
                  child: EpiKpiCard(
                    label: 'Commandes en attente',
                    value: value,
                    icon: Icons.inventory,
                  ),
                ),
              ),
            ),
          ),
        ),
      );
      await tester.pumpAndSettle();
      expect(find.text(value), findsOneWidget);
      expect(tester.takeException(), isNull);
    });
  }
}
