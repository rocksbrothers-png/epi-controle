import 'package:intl/intl.dart';
import '../../core/i18n/generated/app_localizations.dart';

/// Formats additive server metadata only. Classification, scope and legacy
/// messages stay server-owned; unsupported/incomplete metadata keeps both
/// complete legacy strings for compatibility with older/newer servers.
({String title, String? description}) presentOperationalAlert(
  Map<String, dynamic> alert,
  AppLocalizations l,
) {
  final fallback = (
    title: alert['title'] as String? ?? alert['message'] as String? ?? '—',
    description: alert['description'] as String?,
  );
  final metadata = alert['presentation'];
  if (metadata is! Map || metadata['params'] is! Map) return fallback;
  final v = Map<Object?, Object?>.from(metadata['params'] as Map);
  final number = NumberFormat.decimalPattern(l.localeName);
  for (final key in ['stock', 'minimum', 'count', 'days']) {
    final raw = v[key];
    if (raw is num && raw.isFinite) {
      v[key == 'count' ? 'countLabel' : key] = number.format(raw);
    } else if (v.containsKey(key)) {
      return fallback;
    }
  }
  final stock = (metadata['params'] as Map)['stock'];
  if (v.containsKey('measure')) {
    if (stock is! num || v['measure'] is! String) return fallback;
    v['measure'] = switch (v['measure']) {
      'unidade' || 'un' => l.operationalAlertMeasureUnit(stock),
      'par' => l.operationalAlertMeasurePair(stock),
      _ => v['measure'],
    };
  }
  final days = (metadata['params'] as Map)['days'];
  if (days is num) {
    v['daysLabel'] = l.operationalAlertDays(days, number.format(days));
  }
  if (v.containsKey('date')) {
    final raw = v['date'];
    if (raw is! String) return fallback;
    final date = DateTime.tryParse(raw);
    // Keep invalid or non-calendar values verbatim, without timezone shifts.
    if (date != null &&
        RegExp(r'^\d{4}-\d{2}-\d{2}$').hasMatch(raw) &&
        DateFormat('yyyy-MM-dd').format(date) == raw) {
      v['date'] = DateFormat.yMd(l.localeName).format(date);
    }
  }
  String? render(Object? key) => switch (key) {
    'operationalAlerts.stock.nearMinimum' =>
      v['epi'] is String
          ? l.operationalAlertStockNearMinimum(v['epi'] as String)
          : null,
    'operationalAlerts.stock.negative' =>
      v['epi'] is String
          ? l.operationalAlertStockNegative(v['epi'] as String)
          : null,
    'operationalAlerts.stock.zero' =>
      v['epi'] is String
          ? l.operationalAlertStockZero(v['epi'] as String)
          : null,
    'operationalAlerts.stock.belowMinimum' =>
      v['epi'] is String
          ? l.operationalAlertStockBelowMinimum(v['epi'] as String)
          : null,
    'operationalAlerts.stock.atMinimum' =>
      v['epi'] is String
          ? l.operationalAlertStockAtMinimum(v['epi'] as String)
          : null,
    'operationalAlerts.stock.description' =>
      v['company'] is String &&
              v['unit'] is String &&
              v['stock'] is String &&
              v['measure'] is String &&
              v['minimum'] is String
          ? l.operationalAlertStockDescription(
              v['company'] as String,
              v['unit'] as String,
              v['stock'] as String,
              v['measure'] as String,
              v['minimum'] as String,
            )
          : null,
    'operationalAlerts.ca.title' =>
      v['epi'] is String ? l.operationalAlertCaTitle(v['epi'] as String) : null,
    'operationalAlerts.ca.description' =>
      v['company'] is String && v['date'] is String
          ? l.operationalAlertCaDescription(
              v['company'] as String,
              v['date'] as String,
            )
          : null,
    'operationalAlerts.manufacturer.expiredTitle' =>
      v['epi'] is String
          ? l.operationalAlertManufacturerExpiredTitle(v['epi'] as String)
          : null,
    'operationalAlerts.manufacturer.expiringTitle' =>
      v['epi'] is String
          ? l.operationalAlertManufacturerExpiringTitle(v['epi'] as String)
          : null,
    'operationalAlerts.manufacturer.expiredDescription' =>
      v['company'] is String &&
              v['date'] is String &&
              v['stock'] is String &&
              v['measure'] is String
          ? l.operationalAlertManufacturerExpiredDescription(
              v['company'] as String,
              v['date'] as String,
              v['stock'] as String,
              v['measure'] as String,
            )
          : null,
    'operationalAlerts.manufacturer.expiringDescription' =>
      v['company'] is String &&
              v['date'] is String &&
              v['daysLabel'] is String &&
              v['stock'] is String &&
              v['measure'] is String
          ? l.operationalAlertManufacturerExpiringDescription(
              v['company'] as String,
              v['date'] as String,
              v['daysLabel'] as String,
              v['stock'] as String,
              v['measure'] as String,
            )
          : null,
    'operationalAlerts.physical_unknown.title' =>
      l.operationalAlertPhysicalUnknownTitle,
    'operationalAlerts.physical_expiring.title' =>
      l.operationalAlertPhysicalExpiringTitle,
    'operationalAlerts.physicalDescription' =>
      v['count'] is num && v['countLabel'] is String && v['epi'] is String
          ? l.operationalAlertPhysicalDescription(
              v['count'] as num,
              v['countLabel'] as String,
              v['epi'] as String,
            )
          : null,
    _ => null,
  };
  final title = render(metadata['title_key']);
  var description = render(metadata['description_key']);
  if (title == null || description == null) return fallback;
  if (alert['category'] == 'stock' && alert['size_balances'] is List) {
    final sizes = <String>[];
    for (final balance in alert['size_balances'] as List) {
      if (balance is! Map) continue;
      final labels = <String>[];
      for (final key in ['glove_size', 'size', 'uniform_size']) {
        final value = balance[key];
        if (value is! String || value.isEmpty || value == 'N/A') continue;
        labels.add(switch (key) {
          'glove_size' => l.operationalAlertSizeGlove(value),
          'size' => l.operationalAlertSizeSize(value),
          _ => l.operationalAlertSizeUniform(value),
        });
      }
      final quantity = balance['quantity'] ?? 0;
      if (quantity is! num || !quantity.isFinite) return fallback;
      final label = labels.isEmpty
          ? l.operationalAlertSizeUnspecified
          : labels.join(' ');
      sizes.add('$label×${number.format(quantity)}');
    }
    if (sizes.isNotEmpty) {
      description += ' | ${l.operationalAlertSizes} ${sizes.join(', ')}';
    }
  }
  return (title: title, description: description);
}
