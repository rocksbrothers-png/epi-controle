import 'package:intl/intl.dart';

/// Locale changes presentation only. Currency codes and amounts are never
/// converted; retain the previous two-decimal rounding before adding separators.
String formatDisplayMoney(double value, String currency, String locale) {
  if (!value.isFinite) return '$currency ${value.toStringAsFixed(2)}';
  final rounded = double.parse(value.toStringAsFixed(2));
  return NumberFormat.currency(
    locale: locale,
    name: currency,
    symbol: currency == 'BRL' ? r'R$' : currency,
    decimalDigits: 2,
  ).format(rounded);
}

/// Stored calendar dates retain their date, without a timezone conversion.
String formatDisplayDate(String iso, String locale) {
  if (iso.isEmpty) return '—';
  final raw = iso.length >= 10 ? iso.substring(0, 10) : iso;
  final date = DateTime.tryParse(raw);
  if (date == null ||
      !RegExp(r'^\d{4}-\d{2}-\d{2}$').hasMatch(raw) ||
      DateFormat('yyyy-MM-dd').format(date) != raw) {
    return iso;
  }
  return DateFormat.yMd(locale).format(date);
}
