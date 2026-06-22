// Integration smoke tests — run on a real device or emulator (NÃO no `flutter test`
// puro, que não tem device):
//
//   flutter test integration_test/smoke_test.dart
//
// No CI roda no job "Integration (Android emulator)" do flutter.yml.
//
// Todos os fluxos abaixo são **backend-free** e determinísticos: o app sobe na
// tela de login (tryAutoLogin sai cedo quando não há token guardado) e os casos
// cobertos (render, validação de formulário vazio, toggle de senha, tema) não
// tocam a rede — por isso são estáveis no emulador do CI.

import 'package:epi_design/epi_design.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';

import 'package:epi_admin/app.dart';
import 'package:epi_admin/core/api/api_client.dart';
import 'package:epi_admin/core/i18n/locale_provider.dart';
import 'package:epi_admin/core/i18n/theme_mode_notifier.dart';

/// Sobe o `EpiAdminApp` real (router + AuthCubit + tema/locale) e aguarda
/// estabilizar na tela de login. Não chama `main()` de propósito: evita o
/// `Firebase.initializeApp` (sem `google-services.json` no CI).
Future<void> _bootApp(WidgetTester tester, {ThemeMode? mode}) async {
  final themeNotifier = ThemeModeNotifier();
  await themeNotifier.init();
  if (mode != null) await themeNotifier.setMode(mode);
  final localeProvider = LocaleProvider();
  await localeProvider.init();

  await tester.pumpWidget(EpiAdminApp(
    themeNotifier: themeNotifier,
    localeProvider: localeProvider,
  ));
  await tester.pumpAndSettle();
}

void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  setUpAll(() async {
    // Porta morta: o app não deve tocar a rede nestes fluxos; se tocar, falha
    // rápido em vez de pendurar o teste.
    await ApiClient.init(baseUrl: 'http://127.0.0.1:1');
  });

  setUp(() async {
    // Garante boot deslogado → tela de login (tryAutoLogin retorna sem token).
    await ApiClient.clearSession();
  });

  group('Boot & login', () {
    testWidgets('app sobe na tela de login com campos e botão', (tester) async {
      await _bootApp(tester);

      // usuário + senha
      expect(find.byType(TextField), findsNWidgets(2));
      // botão de entrar (design system)
      expect(find.byType(EpiButton), findsOneWidget);
      // marca visual da tela de login
      expect(find.byIcon(Icons.shield_outlined), findsOneWidget);
    });

    testWidgets('login com formulário vazio mostra erro de validação',
        (tester) async {
      await _bootApp(tester);

      await tester.tap(find.byType(EpiButton));
      await tester.pump(); // emite AuthError('empty') → BlocListener
      await tester.pump(const Duration(milliseconds: 400)); // anima o snackbar

      // Não dependemos do texto (i18n): basta que o feedback de erro apareça
      // sem ter tocado a rede.
      expect(find.byType(SnackBar), findsOneWidget);
    });

    testWidgets('toggle de visibilidade da senha alterna o ícone',
        (tester) async {
      await _bootApp(tester);

      // senha começa oculta → ícone "mostrar"
      expect(find.byIcon(Icons.visibility_outlined), findsOneWidget);
      await tester.tap(find.byIcon(Icons.visibility_outlined));
      await tester.pump();
      // agora visível → ícone "ocultar"
      expect(find.byIcon(Icons.visibility_off_outlined), findsOneWidget);
    });
  });

  group('Tema', () {
    testWidgets('tema escuro aplica fundo escuro no scaffold', (tester) async {
      await _bootApp(tester, mode: ThemeMode.dark);

      final scaffoldFinder = find.byType(Scaffold).first;
      final scaffold = tester.widget<Scaffold>(scaffoldFinder);
      final bg = scaffold.backgroundColor ??
          Theme.of(tester.element(scaffoldFinder)).scaffoldBackgroundColor;
      expect(bg.computeLuminance(), lessThan(0.2));
    });
  });
}
