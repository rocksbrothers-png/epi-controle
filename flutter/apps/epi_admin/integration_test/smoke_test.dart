// Integration smoke tests — run on a real device or emulator:
//   flutter test integration_test/smoke_test.dart

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';

import 'package:epi_admin/app.dart';
import 'package:epi_admin/core/api/api_client.dart';
import 'package:epi_admin/core/i18n/locale_provider.dart';
import 'package:epi_admin/core/i18n/theme_mode_notifier.dart';

void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  setUpAll(() async {
    await ApiClient.init(baseUrl: 'http://localhost:8000');
  });

  group('Login screen', () {
    testWidgets('renders username and password fields', (tester) async {
      final themeNotifier = ThemeModeNotifier();
      await themeNotifier.init();
      final localeProvider = LocaleProvider();
      await localeProvider.init();

      await tester.pumpWidget(EpiAdminApp(
        themeNotifier: themeNotifier,
        localeProvider: localeProvider,
      ));
      await tester.pumpAndSettle(const Duration(seconds: 2));

      expect(find.byType(TextField), findsAtLeastNWidgets(1));
    });

    testWidgets('sign-in button is present', (tester) async {
      final themeNotifier = ThemeModeNotifier();
      await themeNotifier.init();
      final localeProvider = LocaleProvider();
      await localeProvider.init();

      await tester.pumpWidget(EpiAdminApp(
        themeNotifier: themeNotifier,
        localeProvider: localeProvider,
      ));
      await tester.pumpAndSettle(const Duration(seconds: 2));

      expect(find.byType(ElevatedButton).evaluate().isNotEmpty ||
          find.byType(OutlinedButton).evaluate().isNotEmpty, isTrue);
    });
  });

  group('Theme switching', () {
    testWidgets('dark theme scaffold has dark background', (tester) async {
      final themeNotifier = ThemeModeNotifier();
      await themeNotifier.init();
      await themeNotifier.setMode(ThemeMode.dark);
      final localeProvider = LocaleProvider();
      await localeProvider.init();

      await tester.pumpWidget(EpiAdminApp(
        themeNotifier: themeNotifier,
        localeProvider: localeProvider,
      ));
      await tester.pumpAndSettle(const Duration(seconds: 2));

      final scaffold = tester.widget<Scaffold>(find.byType(Scaffold).first);
      final bg = scaffold.backgroundColor ??
          Theme.of(tester.element(find.byType(Scaffold).first))
              .scaffoldBackgroundColor;
      expect(bg.computeLuminance(), lessThan(0.1));
    });
  });
}
