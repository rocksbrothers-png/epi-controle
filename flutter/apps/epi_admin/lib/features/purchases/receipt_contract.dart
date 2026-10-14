import '../../core/session/session_context.dart';

/// Quantity published by the backend, without substituting requested units.
int effectiveReceiptQuantity(Object? value) =>
    value is num && value.isFinite && value > 0 && value == value.toInt()
        ? value.toInt()
        : 0;

/// Only a consistent server receipt can produce the stock success message.
int? persistedReceiptCount(Map<String, dynamic> result) {
  final count = effectiveReceiptQuantity(result['stock_entries']);
  final labels = result['qr_labels'];
  if (result['ok'] != true || count == 0 || labels is! List || labels.length != count) {
    return null;
  }
  final ids = <int>{};
  for (final label in labels) {
    if (label is! Map) return null;
    final id = effectiveReceiptQuantity(label['stock_item_id']);
    if (id == 0 || !ids.add(id) ||
        label['qr_code_value'] is! String ||
        (label['qr_code_value'] as String).trim().isEmpty) {
      return null;
    }
  }
  return count;
}

/// Server-scoped requests still require the effective session permission.
/// Local operational profiles must match their current operational unit.
bool canConferReceipt(SessionContext session, {int? companyId, int? unitId}) {
  if (!session.isAuthenticated ||
      !session.hasPermission('purchase_requests:update') ||
      companyId == null || companyId <= 0 || companyId != session.companyId ||
      unitId == null || unitId <= 0) {
    return false;
  }
  if (session.role == 'admin' || session.role == 'user') {
    return session.unitId != null && session.unitId == unitId;
  }
  return true;
}
