// F3 — tema e idioma continuam por DISPOSITIVO, e a escolha explicita do
// dispositivo esta no topo do contrato.
//
// D1: o bootstrap nao pode sobrescrever escolha explicita. Hoje o backend nao
//     emite `preferred_locale` nem `company_locale`; a correcao e preservar a
//     escolha, NAO fabricar os campos no servidor.
// D2: falha na leitura do secure storage degrada para o default e deixa o app
//     iniciar — nunca aborta o startup.
//
// O mock do canal segue o padrao ja usado em `refresh_interceptor_test.dart`.

import 'package:epi_admin/core/i18n/locale_provider.dart';
import 'package:epi_admin/core/i18n/theme_mode_notifier.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  const storageChannel =
      MethodChannel('plugins.it_nomads.com/flutter_secure_storage');

  final store = <String, String>{};
  var leituraLanca = false;
  var escritas = 0;
  var remocoes = 0;

  void instalarMock() {
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(storageChannel, (call) async {
      final args = (call.arguments as Map?) ?? const {};
      switch (call.method) {
        case 'read':
          if (leituraLanca) {
            throw PlatformException(code: 'storage_indisponivel');
          }
          return store[args['key'] as String];
        case 'write':
          escritas++;
          store[args['key'] as String] = args['value'] as String;
          return null;
        case 'delete':
          remocoes++;
          store.remove(args['key'] as String);
          return null;
        case 'deleteAll':
          remocoes++;
          store.clear();
          return null;
        case 'readAll':
          if (leituraLanca) {
            throw PlatformException(code: 'storage_indisponivel');
          }
          return Map<String, String>.from(store);
        case 'containsKey':
          return store.containsKey(args['key'] as String);
        default:
          return null;
      }
    });
  }

  setUp(() {
    store.clear();
    leituraLanca = false;
    escritas = 0;
    remocoes = 0;
    instalarMock();
  });

  tearDown(() {
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(storageChannel, null);
  });

  // ── D1 ─────────────────────────────────────────────────────────────────────

  group('D1 — escolha explicita do dispositivo vence o fallback', () {
    test('bootstrap sem preferencia nao sobrescreve o locale persistido',
        () async {
      store['user_locale'] = 'es_ES';

      final provider = LocaleProvider();
      await provider.init();

      expect(provider.locale, const Locale('es', 'ES'),
          reason: 'o startup precisa resolver a escolha persistida');
      expect(provider.hasExplicitPreference, isTrue);

      // O cenario relatado: o backend nao emite os campos, entao chegam nulos.
      provider.applyUserPreference(null, null);

      expect(provider.locale, const Locale('es', 'ES'),
          reason: 'o fallback nao pode vencer a escolha explicita');
      expect(escritas, 0, reason: 'nada a regravar: nada mudou');
    });

    test('nem uma preferencia de empresa vence a escolha explicita', () async {
      // Deterministico: nao depende do locale da plataforma de teste.
      store['user_locale'] = 'es_ES';

      final provider = LocaleProvider();
      await provider.init();
      provider.applyUserPreference(null, 'fr-FR');

      expect(provider.locale, const Locale('es', 'ES'));
    });

    test('sem escolha explicita, a cascata do bootstrap vale', () async {
      final provider = LocaleProvider();
      await provider.init();

      expect(provider.hasExplicitPreference, isFalse);
      provider.applyUserPreference(null, 'fr-FR');

      expect(provider.locale, const Locale('fr', 'FR'),
          reason: 'sem escolha no dispositivo, a empresa decide');
    });

    test('valor persistido invalido nao conta como escolha explicita',
        () async {
      store['user_locale'] = 'zz_ZZ';

      final provider = LocaleProvider();
      await provider.init();

      expect(provider.hasExplicitPreference, isFalse);
      provider.applyUserPreference(null, 'fr-FR');
      expect(provider.locale, const Locale('fr', 'FR'));
    });

    test('o startup NAO persiste o valor que resolveu por fallback', () async {
      final provider = LocaleProvider();
      await provider.init();
      provider.applyUserPreference(null, 'fr-FR');

      expect(escritas, 0,
          reason: 'ausencia de preferencia nao pode virar valor explicito');
      expect(store.containsKey('user_locale'), isFalse);
    });

    test('escolher explicitamente o locale que ja valia por fallback persiste',
        () async {
      final provider = LocaleProvider();
      await provider.init();
      expect(provider.locale, const Locale('pt', 'BR'));
      expect(provider.hasExplicitPreference, isFalse);

      await provider.setLocale(const Locale('pt', 'BR'));

      expect(provider.hasExplicitPreference, isTrue,
          reason: 'escolher o mesmo valor ainda e uma escolha');
      expect(store['user_locale'], 'pt_BR');

      provider.applyUserPreference(null, 'fr-FR');
      expect(provider.locale, const Locale('pt', 'BR'));
    });

    test('setLocale nao regrava quando a escolha ja e a mesma', () async {
      final provider = LocaleProvider();
      await provider.init();
      await provider.setLocale(const Locale('es', 'ES'));
      expect(escritas, 1);

      await provider.setLocale(const Locale('es', 'ES'));
      expect(escritas, 1, reason: 'regravacao desnecessaria');
    });
  });

  // ── D2 ─────────────────────────────────────────────────────────────────────

  group('D2 — falha de storage degrada, nao aborta', () {
    test('LocaleProvider.init() sobrevive a excecao na leitura', () async {
      leituraLanca = true;
      final provider = LocaleProvider();

      await expectLater(provider.init(), completes);

      expect(provider.locale, const Locale('pt', 'BR'));
      expect(provider.hasExplicitPreference, isFalse);
    });

    test('ThemeModeNotifier.init() sobrevive a excecao na leitura', () async {
      leituraLanca = true;
      final notifier = ThemeModeNotifier();

      await expectLater(notifier.init(), completes);

      expect(notifier.mode, ThemeMode.system);
    });

    test('a falha de leitura nao apaga preferencia existente', () async {
      store['user_locale'] = 'es_ES';
      store['theme_mode'] = 'dark';
      leituraLanca = true;

      await LocaleProvider().init();
      await ThemeModeNotifier().init();

      expect(remocoes, 0, reason: 'nenhum efeito colateral de remocao');
      expect(escritas, 0, reason: 'nenhum efeito colateral de escrita');
      expect(store['user_locale'], 'es_ES');
      expect(store['theme_mode'], 'dark');
    });
  });
}
