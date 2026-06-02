import 'package:epi_design/epi_design.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

Widget _wrap(Widget child) => MaterialApp(
      theme: EpiTheme.light,
      darkTheme: EpiTheme.dark,
      home: Scaffold(body: child),
    );

void main() {
  group('EpiTheme integration', () {
    test('light and dark themes are distinct', () {
      final light = EpiTheme.light;
      final dark = EpiTheme.dark;
      expect(light.brightness, Brightness.light);
      expect(dark.brightness, Brightness.dark);
      expect(
        light.scaffoldBackgroundColor,
        isNot(dark.scaffoldBackgroundColor),
      );
    });

    test('dark theme card color is dark', () {
      final cardColor = EpiTheme.dark.cardTheme.color!;
      expect(cardColor.computeLuminance(), lessThan(0.1));
    });
  });

  group('EpiKpiCard in light and dark', () {
    testWidgets('renders in light mode', (tester) async {
      await tester.pumpWidget(_wrap(
        const EpiKpiCard(label: 'Deliveries', value: '12'),
      ));
      expect(find.text('Deliveries'), findsOneWidget);
      expect(find.text('12'), findsOneWidget);
    });

    testWidgets('renders in dark mode without errors', (tester) async {
      await tester.pumpWidget(MaterialApp(
        darkTheme: EpiTheme.dark,
        themeMode: ThemeMode.dark,
        home: const Scaffold(
          body: EpiKpiCard(label: 'Stock', value: '5'),
        ),
      ));
      expect(find.text('Stock'), findsOneWidget);
    });
  });

  group('EpiBadge dark-mode colors', () {
    testWidgets('active badge renders in dark mode', (tester) async {
      await tester.pumpWidget(MaterialApp(
        darkTheme: EpiTheme.dark,
        themeMode: ThemeMode.dark,
        home: const Scaffold(body: EpiBadge(status: EpiBadgeStatus.active)),
      ));
      expect(find.byType(EpiBadge), findsOneWidget);
    });

    testWidgets('inactive badge renders in dark mode', (tester) async {
      await tester.pumpWidget(MaterialApp(
        darkTheme: EpiTheme.dark,
        themeMode: ThemeMode.dark,
        home: const Scaffold(body: EpiBadge(status: EpiBadgeStatus.inactive)),
      ));
      expect(find.byType(EpiBadge), findsOneWidget);
    });
  });

  group('EpiEmptyState', () {
    testWidgets('renders title in light mode', (tester) async {
      await tester.pumpWidget(_wrap(
        const EpiEmptyState(title: 'Nothing found'),
      ));
      expect(find.text('Nothing found'), findsOneWidget);
    });

    testWidgets('renders in dark mode', (tester) async {
      await tester.pumpWidget(MaterialApp(
        darkTheme: EpiTheme.dark,
        themeMode: ThemeMode.dark,
        home: const Scaffold(
          body: EpiEmptyState(title: 'Dark mode empty'),
        ),
      ));
      expect(find.text('Dark mode empty'), findsOneWidget);
    });
  });
}
