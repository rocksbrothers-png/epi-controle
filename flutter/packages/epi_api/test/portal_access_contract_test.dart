import 'package:epi_api/epi_api.dart';
import 'package:flutter_test/flutter_test.dart';

/// Contrato do PortalAccess — portal do colaborador com Empresa / CNPJ / Unidade.
///
/// `GET /api/employee-access` aninha os dados do colaborador em `employee`;
/// o modelo lê de lá com o topo como fallback.
void main() {
  group('PortalAccess.fromJson', () {
    test('lê os dados aninhados em `employee` (formato real da API)', () {
      final access = PortalAccess.fromJson(const {
        'employee': {
          'employee_name': 'Ana Souza',
          'unit_name': 'Base Santos',
          'company_name': 'ACME',
          'legal_entity_cnpj': '11.222.333/0001-81',
          'legal_entity_name': 'ACME Filial RJ Ltda',
        },
        'deliveries': <dynamic>[],
        'fichas': <dynamic>[],
      });
      expect(access.employeeName, 'Ana Souza');
      expect(access.unitName, 'Base Santos');
      expect(access.companyName, 'ACME');
      expect(access.legalEntityCnpj, '11.222.333/0001-81');
      expect(access.legalEntityName, 'ACME Filial RJ Ltda');
    });

    test('tolera o formato plano, sem o envelope `employee`', () {
      final access = PortalAccess.fromJson(const {
        'employee_name': 'Ana Souza',
        'unit_name': 'Base Santos',
        'deliveries': <dynamic>[],
        'fichas': <dynamic>[],
      });
      expect(access.employeeName, 'Ana Souza');
      expect(access.unitName, 'Base Santos');
    });

    test('cai para `name` quando não há `employee_name`', () {
      final access = PortalAccess.fromJson(const {
        'employee': {'name': 'Ana Souza'},
        'deliveries': <dynamic>[],
        'fichas': <dynamic>[],
      });
      expect(access.employeeName, 'Ana Souza');
    });

    test('CNPJ vazio enquanto o schema Multi-CNPJ não estiver provisionado', () {
      final access = PortalAccess.fromJson(const {
        'employee': {'employee_name': 'Ana', 'unit_name': 'Base'},
        'deliveries': <dynamic>[],
        'fichas': <dynamic>[],
      });
      expect(access.legalEntityCnpj, isEmpty);
      expect(access.companyName, isEmpty);
    });

    test('aceita employee_id_code como código do colaborador', () {
      final access = PortalAccess.fromJson(const {
        'employee': {'employee_name': 'Ana', 'employee_id_code': 'E-001'},
        'deliveries': <dynamic>[],
        'fichas': <dynamic>[],
      });
      expect(access.employeeCode, 'E-001');
    });

    test('código nulo quando ausente, em vez de string vazia', () {
      final access = PortalAccess.fromJson(const {
        'employee': {'employee_name': 'Ana'},
        'deliveries': <dynamic>[],
        'fichas': <dynamic>[],
      });
      expect(access.employeeCode, isNull);
      expect(access.photoUrl, isNull);
    });

    test('listas de entregas e fichas seguem lidas do topo', () {
      final access = PortalAccess.fromJson(const {
        'employee': {'employee_name': 'Ana'},
        'deliveries': [
          {'id': 1, 'epi_name': 'Luva', 'signed': false},
        ],
        'fichas': <dynamic>[],
      });
      expect(access.deliveries, hasLength(1));
      expect(access.unsignedCount, 1);
    });
  });
}
