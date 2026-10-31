import 'package:epi_admin/core/i18n/presentation_formatters.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:intl/date_symbol_data_local.dart';

void main() {
  setUpAll(() => initializeDateFormatting());
  const expected = {
    'pt_BR': ('1.234,56', '02/01/2027'),
    'en_US': ('1,234.56', '1/2/2027'),
    'es_ES': ('1.234,56', '2/1/2027'),
    'fr_FR': ('1\u202f234,56', '02/01/2027'),
    'no_NO': ('1\u00a0234,56', '2.1.2027'),
  };
  for (final entry in expected.entries) {
    test(
      'locale ${entry.key} changes separators/calendar display without converting value or currency',
      () {
        const value = 1234.56;
        final text = formatDisplayMoney(value, 'BRL', entry.key);
        expect(text, contains('R\$'));
        // Intl versions use a narrow or regular non-breaking group separator.
        expect(
          text.replaceAll('\u202f', '\u00a0'),
          contains(entry.value.$1.replaceAll('\u202f', '\u00a0')),
        );
        expect(value, 1234.56);
        expect(
          formatDisplayDate('2027-01-02T23:59:59-12:00', entry.key),
          entry.value.$2,
        );
        expect(formatDisplayDate('2027-01-02', entry.key), entry.value.$2);
        expect(formatDisplayDate('', entry.key), '—');
        for (final raw in [
          '2026-02-31',
          'Original invalid date',
          '2026-13-01',
        ]) {
          expect(formatDisplayDate(raw, entry.key), raw);
        }
        expect(formatDisplayMoney(value, 'USD', entry.key), contains('USD'));
      },
    );
  }
  test('display preserves the preexisting two-decimal double rounding', () {
    expect(formatDisplayMoney(2.675, 'BRL', 'en_US'), contains('2.67'));
    expect(formatDisplayMoney(2.675, 'BRL', 'fr_FR'), contains('2,67'));
  });
}
