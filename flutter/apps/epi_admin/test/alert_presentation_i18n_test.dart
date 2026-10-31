import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:intl/intl.dart';
import 'package:intl/date_symbol_data_local.dart';
import 'package:epi_admin/core/i18n/generated/app_localizations.dart';
import 'package:epi_admin/features/dashboard/alert_presentation.dart';

Map<String, dynamic> alert(
  String title,
  String description,
  Map<String, Object?> params,
) => {
  'title': 'Legacy title',
  'description': 'Legacy complete description',
  'category': 'stock',
  'company_id': 41,
  'unit_id': 42,
  'epi_id': 43,
  'presentation': {
    'title_key': 'operationalAlerts.$title',
    'description_key': 'operationalAlerts.$description',
    'params': params,
  },
};

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  setUpAll(() => initializeDateFormatting());
  const locales = [
    Locale('pt', 'BR'),
    Locale('en', 'US'),
    Locale('es', 'ES'),
    Locale('fr', 'FR'),
    Locale('no', 'NO'),
  ];
  for (final locale in locales) {
    test(
      'all operational alert branches, plurals and original scope $locale',
      () async {
        final l = await AppLocalizations.delegate.load(locale);
        final p = {
          'epi': 'Original <Luva> {count}',
          'company': 'Empresa Original',
          'unit': 'Unidade Original',
          'stock': 1234,
          'minimum': 7,
          'measure': 'par',
        };
        for (final title in [
          'nearMinimum',
          'negative',
          'zero',
          'belowMinimum',
          'atMinimum',
        ]) {
          final item = alert('stock.$title', 'stock.description', p);
          item['size_balances'] = [
            {
              'glove_size': 'M',
              'size': 'N/A',
              'uniform_size': 'G',
              'quantity': 1234,
            },
          ];
          final before = jsonEncode(item);
          final actual = presentOperationalAlert(item, l);
          expect(actual.title, contains('Original <Luva> {count}'));
          expect(
            actual.description,
            contains(NumberFormat.decimalPattern(l.localeName).format(1234)),
          );
          expect(
            actual.description,
            contains(l.operationalAlertMeasurePair(1234)),
          );
          expect(
            actual.description,
            contains(l.operationalAlertSizeGlove('M')),
          );
          expect(
            actual.description,
            contains(l.operationalAlertSizeUniform('G')),
          );
          expect(actual.description, isNot(contains('N/A')));
          expect(jsonEncode(item), before);
        }
        for (final count in [0, 1, 2, 1234, -1, 0.5]) {
          final item = alert('physical_unknown.title', 'physicalDescription', {
            'epi': 'Original',
            'count': count,
          });
          final result = presentOperationalAlert(item, l);
          expect(result.title, l.operationalAlertPhysicalUnknownTitle);
          expect(
            result.description,
            l.operationalAlertPhysicalDescription(
              count,
              NumberFormat.decimalPattern(l.localeName).format(count),
              'Original',
            ),
          );
          expect(result.description, isNot(contains('{count}')));
        }
        final params = {...p, 'date': '2026-12-21', 'days': 3};
        for (final pair in [
          ('ca.title', 'ca.description'),
          ('manufacturer.expiredTitle', 'manufacturer.expiredDescription'),
          ('manufacturer.expiringTitle', 'manufacturer.expiringDescription'),
        ]) {
          final result = presentOperationalAlert(
            alert(pair.$1, pair.$2, params),
            l,
          );
          expect(
            result.description,
            contains(
              DateFormat.yMd(l.localeName).format(DateTime(2026, 12, 21)),
            ),
          );
          expect(result.description, isNot(contains('{daysLabel}')));
          if (pair.$1.contains('expiring')) {
            expect(
              result.description,
              contains(l.operationalAlertDays(3, '3')),
            );
          }
        }
        final physical = presentOperationalAlert(
          alert('physical_expiring.title', 'physicalDescription', {
            'epi': 'Original',
            'count': 2,
          }),
          l,
        );
        expect(physical.title, l.operationalAlertPhysicalExpiringTitle);
      },
    );
  }
  test(
    'unknown keys, malformed metadata and missing params keep full legacy messages',
    () async {
      final l = await AppLocalizations.delegate.load(const Locale('en', 'US'));
      final cases = [
        {'title': 'Legacy title', 'description': 'Legacy complete description'},
        alert('future.title', 'physicalDescription', {
          'epi': 'Original',
          'count': 1,
        }),
        alert('physical_unknown.title', 'future.description', {}),
        alert('stock.zero', 'stock.description', {'epi': 'Original'}),
        alert('physical_unknown.title', 'physicalDescription', {
          'epi': 'Original',
          'count': '1',
        }),
        alert('physical_unknown.title', 'physicalDescription', {
          'epi': 'Original',
          'count': double.nan,
        }),
      ];
      for (final item in cases) {
        final result = presentOperationalAlert(item, l);
        expect(result.title, 'Legacy title');
        expect(result.description, 'Legacy complete description');
      }
    },
  );
  testWidgets(
    'effective language change refreshes the same alert without changing its metadata',
    (tester) async {
      final item = alert('physical_unknown.title', 'physicalDescription', {
        'epi': 'Original',
        'count': 1234,
      });
      final before = jsonEncode(item);
      for (final locale in [
        const Locale('en', 'US'),
        const Locale('fr', 'FR'),
        const Locale('en', 'US'),
      ]) {
        final l = (await tester.runAsync(
          () => AppLocalizations.delegate.load(locale),
        ))!;
        await tester.pumpWidget(
          MaterialApp(
            locale: locale,
            localizationsDelegates: AppLocalizations.localizationsDelegates,
            supportedLocales: AppLocalizations.supportedLocales,
            home: Builder(
              builder: (context) {
                final result = presentOperationalAlert(
                  item,
                  AppLocalizations.of(context),
                );
                return Scaffold(
                  body: Text('${result.title}\n${result.description}'),
                );
              },
            ),
          ),
        );
        await tester.pumpAndSettle();
        expect(
          find.textContaining(l.operationalAlertPhysicalUnknownTitle),
          findsOneWidget,
        );
        expect(
          find.textContaining(
            NumberFormat.decimalPattern(l.localeName).format(1234),
          ),
          findsOneWidget,
        );
        expect(jsonEncode(item), before);
      }
    },
  );
}
