import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

void main() {
  const locales = ['pt_BR', 'en_US', 'es_ES', 'fr_FR', 'no_NO'];
  const arbDir = 'lib/l10n';

  Map<String, dynamic> _loadArb(String locale) {
    final file = File('$arbDir/app_$locale.arb');
    return jsonDecode(file.readAsStringSync()) as Map<String, dynamic>;
  }

  Set<String> _keys(Map<String, dynamic> arb) => arb.keys
      .where((k) => !k.startsWith('@'))
      .toSet();

  group('ARB consistency', () {
    late Map<String, Set<String>> keysByLocale;

    setUpAll(() {
      keysByLocale = {
        for (final locale in locales) locale: _keys(_loadArb(locale)),
      };
    });

    test('all locales have the same keys as pt_BR', () {
      final reference = keysByLocale['pt_BR']!;
      for (final locale in locales.skip(1)) {
        final keys = keysByLocale[locale]!;
        final missing = reference.difference(keys);
        final extra   = keys.difference(reference);
        expect(missing, isEmpty,
            reason: '$locale is missing keys: $missing');
        expect(extra, isEmpty,
            reason: '$locale has orphan keys: $extra');
      }
    });

    test('no locale has the navCommercial orphan key', () {
      for (final locale in locales) {
        expect(keysByLocale[locale], isNot(contains('navCommercial')),
            reason: '$locale still contains orphan key navCommercial');
      }
    });

    test('all locales have navFeedback', () {
      for (final locale in locales) {
        expect(keysByLocale[locale], contains('navFeedback'),
            reason: '$locale is missing navFeedback');
      }
    });

    test('all locales have returnSuccess and returnOfflineQueued', () {
      for (final locale in locales) {
        expect(keysByLocale[locale], contains('returnSuccess'),
            reason: '$locale is missing returnSuccess');
        expect(keysByLocale[locale], contains('returnOfflineQueued'),
            reason: '$locale is missing returnOfflineQueued');
      }
    });

    test('placeholder metadata (@key) exists for parameterised strings', () {
      for (final locale in locales) {
        final arb = _loadArb(locale);
        final paramKeys = arb.keys
            .where((k) => !k.startsWith('@'))
            .where((k) => (arb[k] as String).contains('{'))
            .toSet();
        for (final key in paramKeys) {
          expect(arb, contains('@$key'),
              reason: '$locale: parameterised key "$key" has no @$key metadata');
        }
      }
    });
  });
}
