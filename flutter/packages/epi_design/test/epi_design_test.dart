import 'package:epi_design/epi_design.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

Widget _wrap(Widget child, {Brightness brightness = Brightness.light}) =>
    MaterialApp(
      theme: EpiTheme.light,
      darkTheme: EpiTheme.dark,
      themeMode: brightness == Brightness.dark ? ThemeMode.dark : ThemeMode.light,
      home: Scaffold(body: Center(child: child)),
    );

void main() {
  // ── EpiButton ──────────────────────────────────────────────────────────────

  group('EpiButton', () {
    testWidgets('renders label', (tester) async {
      await tester.pumpWidget(_wrap(
        EpiButton(label: 'Save', onPressed: () {}),
      ));
      expect(find.text('Save'), findsOneWidget);
    });

    testWidgets('shows spinner when loading', (tester) async {
      await tester.pumpWidget(_wrap(
        const EpiButton(label: 'Save', onPressed: null, loading: true),
      ));
      expect(find.byType(CircularProgressIndicator), findsOneWidget);
      expect(find.text('Save'), findsNothing);
    });

    testWidgets('is disabled when onPressed is null', (tester) async {
      await tester.pumpWidget(_wrap(
        const EpiButton(label: 'Save', onPressed: null),
      ));
      final btn = tester.widget<OutlinedButton>(find.byType(OutlinedButton));
      expect(btn.onPressed, isNull);
    });

    testWidgets('renders with icon', (tester) async {
      await tester.pumpWidget(_wrap(
        EpiButton(
          label: 'Add',
          onPressed: () {},
          icon: Icons.add,
        ),
      ));
      expect(find.byIcon(Icons.add), findsOneWidget);
    });

    testWidgets('fullWidth fills available width', (tester) async {
      await tester.pumpWidget(_wrap(
        EpiButton(label: 'Wide', onPressed: () {}, fullWidth: true),
      ));
      final box = tester.renderObject<RenderBox>(find.byType(EpiButton));
      expect(box.size.width, greaterThan(200));
    });

    testWidgets('ghost variant renders', (tester) async {
      await tester.pumpWidget(_wrap(
        EpiButton(
          label: 'Cancel',
          onPressed: () {},
          variant: EpiButtonVariant.ghost,
        ),
      ));
      expect(find.text('Cancel'), findsOneWidget);
    });

    testWidgets('renders in dark mode', (tester) async {
      await tester.pumpWidget(_wrap(
        EpiButton(label: 'Dark', onPressed: () {}),
        brightness: Brightness.dark,
      ));
      expect(find.text('Dark'), findsOneWidget);
    });
  });

  // ── EpiBadge ───────────────────────────────────────────────────────────────

  group('EpiBadge', () {
    for (final status in EpiBadgeStatus.values) {
      testWidgets('renders status $status with default label', (tester) async {
        await tester.pumpWidget(_wrap(EpiBadge(status: status)));
        expect(
          find.text(EpiBadge.defaultLabel(status)),
          findsOneWidget,
          reason: 'defaultLabel for $status should render',
        );
      });
    }

    testWidgets('renders custom label', (tester) async {
      await tester.pumpWidget(_wrap(
        const EpiBadge(status: EpiBadgeStatus.active, label: 'Custom'),
      ));
      expect(find.text('Custom'), findsOneWidget);
    });

    testWidgets('renders all statuses in dark mode without overflow', (tester) async {
      for (final s in EpiBadgeStatus.values) {
        await tester.pumpWidget(_wrap(
          EpiBadge(status: s),
          brightness: Brightness.dark,
        ));
        expect(find.byType(EpiBadge), findsOneWidget);
      }
    });
  });

  // ── EpiKpiCard ─────────────────────────────────────────────────────────────

  group('EpiKpiCard', () {
    testWidgets('renders label and value', (tester) async {
      await tester.pumpWidget(_wrap(
        const EpiKpiCard(label: 'Deliveries', value: '42'),
      ));
      expect(find.text('Deliveries'), findsOneWidget);
      expect(find.text('42'), findsOneWidget);
    });

    testWidgets('renders icon when provided', (tester) async {
      await tester.pumpWidget(_wrap(
        const EpiKpiCard(
          label: 'Stock',
          value: '10',
          icon: Icons.inventory_2_outlined,
        ),
      ));
      expect(find.byIcon(Icons.inventory_2_outlined), findsOneWidget);
    });

    testWidgets('renders delta trend up', (tester) async {
      await tester.pumpWidget(_wrap(
        const EpiKpiCard(
          label: 'Sales',
          value: '99',
          delta: '+5%',
          deltaPositive: true,
        ),
      ));
      expect(find.text('+5%'), findsOneWidget);
      expect(find.byIcon(Icons.trending_up_rounded), findsOneWidget);
    });

    testWidgets('renders in dark mode', (tester) async {
      await tester.pumpWidget(_wrap(
        const EpiKpiCard(label: 'X', value: '0'),
        brightness: Brightness.dark,
      ));
      expect(find.text('X'), findsOneWidget);
      expect(find.text('0'), findsOneWidget);
    });

    testWidgets('calls onTap when tapped', (tester) async {
      var tapped = false;
      await tester.pumpWidget(_wrap(
        EpiKpiCard(
          label: 'Tap me',
          value: '1',
          onTap: () => tapped = true,
        ),
      ));
      await tester.tap(find.byType(EpiKpiCard));
      expect(tapped, isTrue);
    });
  });

  // ── EpiAvatar ──────────────────────────────────────────────────────────────

  group('EpiAvatar', () {
    testWidgets('shows initials for two-word name', (tester) async {
      await tester.pumpWidget(_wrap(const EpiAvatar(name: 'João Silva')));
      expect(find.text('JS'), findsOneWidget);
    });

    testWidgets('shows initials for single-word name', (tester) async {
      await tester.pumpWidget(_wrap(const EpiAvatar(name: 'Admin')));
      expect(find.text('AD'), findsOneWidget);
    });
  });

  // ── EpiEmptyState ──────────────────────────────────────────────────────────

  group('EpiEmptyState', () {
    testWidgets('renders title', (tester) async {
      await tester.pumpWidget(_wrap(
        const EpiEmptyState(title: 'Nothing here'),
      ));
      expect(find.text('Nothing here'), findsOneWidget);
    });

    testWidgets('renders subtitle when provided', (tester) async {
      await tester.pumpWidget(_wrap(
        const EpiEmptyState(title: 'Empty', subtitle: 'Add something'),
      ));
      expect(find.text('Add something'), findsOneWidget);
    });

    testWidgets('renders CTA button when label and callback provided', (tester) async {
      var pressed = false;
      await tester.pumpWidget(_wrap(
        EpiEmptyState(
          title: 'Empty',
          ctaLabel: 'Add',
          onCtaPressed: () => pressed = true,
        ),
      ));
      await tester.tap(find.text('Add'));
      expect(pressed, isTrue);
    });

    testWidgets('renders in dark mode', (tester) async {
      await tester.pumpWidget(_wrap(
        const EpiEmptyState(title: 'Dark empty'),
        brightness: Brightness.dark,
      ));
      expect(find.text('Dark empty'), findsOneWidget);
    });
  });

  // ── EpiTheme ───────────────────────────────────────────────────────────────

  group('EpiTheme', () {
    test('light theme uses light brightness', () {
      expect(EpiTheme.light.brightness, Brightness.light);
    });

    test('dark theme uses dark brightness', () {
      expect(EpiTheme.dark.brightness, Brightness.dark);
    });

    test('dark scaffold background differs from light', () {
      expect(
        EpiTheme.dark.scaffoldBackgroundColor,
        isNot(EpiTheme.light.scaffoldBackgroundColor),
      );
    });
  });
}
