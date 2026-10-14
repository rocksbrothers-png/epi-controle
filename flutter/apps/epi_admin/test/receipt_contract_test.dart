import 'package:epi_admin/core/session/session_context.dart';
import 'package:epi_admin/features/purchases/receipt_contract.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('effective quantity rejects zero, null, negative and invalid values', () {
    for (final value in [0, null, -1, '5', 1.5, double.nan, double.infinity]) {
      expect(effectiveReceiptQuantity(value), 0);
    }
    expect(effectiveReceiptQuantity(3), 3); // partial receipt, never requested 5
  });

  Map<String, dynamic> receipt(int count, List<dynamic> labels) => {
    'ok': true, 'stock_entries': count, 'qr_labels': labels,
  };
  Map<String, dynamic> piece(int id) => {
    'stock_item_id': id, 'qr_code_value': 'QR-$id',
  };

  test('stock success requires the persisted pieces and server count', () {
    expect(persistedReceiptCount(receipt(0, [])), isNull);
    expect(persistedReceiptCount(receipt(3, [])), isNull);
    expect(persistedReceiptCount(receipt(3, [piece(1)])), isNull);
    expect(persistedReceiptCount(receipt(2, [piece(1), piece(1)])), isNull);
    expect(persistedReceiptCount(receipt(1, [{'stock_item_id': null}])), isNull);
    expect(persistedReceiptCount({'ok': false, 'stock_entries': 1, 'qr_labels': [piece(1)]}), isNull);
    expect(persistedReceiptCount(receipt(3, [piece(1), piece(2), piece(3)])), 3);
  });

  SessionContext session({String role = 'admin', int? unit = 10,
      List<String> permissions = const ['purchase_requests:update']}) =>
    SessionContext(userId: 1, companyId: 2, unitId: unit, role: role,
      permissions: permissions, tenantName: '', companySettings: const {});

  test('conference requires effective permission and company/unit scope', () {
    expect(canConferReceipt(session(), companyId: 2, unitId: 10), isTrue);
    expect(canConferReceipt(session(permissions: []), companyId: 2, unitId: 10), isFalse);
    expect(canConferReceipt(session(), companyId: 3, unitId: 10), isFalse);
    expect(canConferReceipt(session(), companyId: 2, unitId: 11), isFalse);
    expect(canConferReceipt(session(unit: null), companyId: 2, unitId: 10), isFalse);
    expect(canConferReceipt(session(role: 'user'), companyId: 2, unitId: 11), isFalse);
    expect(canConferReceipt(session(role: 'general_admin', unit: null), companyId: 2, unitId: 11), isTrue);
    expect(canConferReceipt(SessionContext.empty, companyId: 2, unitId: 10), isFalse);
  });
}
