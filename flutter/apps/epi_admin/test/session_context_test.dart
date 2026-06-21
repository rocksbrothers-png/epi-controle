import 'package:epi_admin/core/session/session_context.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('SessionContext', () {
    test('normaliza contrato de login/auth-me com company_id e operational_unit_id', () {
      final context = SessionContext.fromAuthPayload(
        user: const {
          'id': 9,
          'role': 'general_admin',
          'company_id': 12,
          'company_name': 'Empresa ACME',
          'operational_unit_id': 34,
        },
        permissions: const ['employees:view', 'stock:view'],
      );

      expect(context.userId, 9);
      expect(context.companyId, 12);
      expect(context.unitId, 34);
      expect(context.role, 'general_admin');
      expect(context.tenantName, 'Empresa ACME');
      expect(context.hasPermission('stock:view'), isTrue);
    });

    test('aceita aliases user_id, unit_id e company aninhada', () {
      final context = SessionContext.fromAuthPayload(
        user: const {
          'user_id': '7',
          'role': 'registry_admin',
          'unit_id': '55',
        },
        company: const {'id': '22', 'name': 'Tenant X'},
        companySettings: const {'stock_negative': false},
        permissions: const ['reports:view'],
      );

      expect(context.userId, 7);
      expect(context.companyId, 22);
      expect(context.unitId, 55);
      expect(context.tenantName, 'Tenant X');
      expect(context.companySettings['stock_negative'], isFalse);
    });

    test('serializa e restaura sem perder escopo tenant', () {
      const original = SessionContext(
        userId: 1,
        companyId: 2,
        unitId: 3,
        role: 'master_admin',
        permissions: ['companies:view'],
        tenantName: 'Plataforma',
        companySettings: {'theme': 'light'},
      );

      expect(SessionContext.fromJson(original.toJson()), original);
    });
  });
}
