import 'package:epi_api/epi_api.dart';
import 'package:flutter_test/flutter_test.dart';

/// Contrato do modelo LegalEntity (CNPJ) e do vínculo jurídico do colaborador —
/// arquitetura Multi-CNPJ / Joint Venture.
void main() {
  group('LegalEntity.fromJson', () {
    test('lê o payload completo de /api/legal-entities', () {
      final entity = LegalEntity.fromJson(const {
        'id': 3,
        'company_id': 1,
        'cnpj': '11.222.333/0001-81',
        'legal_name': 'ACME Filial RJ Ltda',
        'trade_name': 'ACME RJ',
        'entity_type': 'filial',
        'parent_entity_id': 1,
        'state_registration': '123',
        'municipal_registration': '456',
        'cnae': '4321-5/00',
        'address': 'Rua X, 100',
        'municipality': 'Rio de Janeiro',
        'uf': 'RJ',
        'cep': '20000000',
        'opening_date': '2020-01-15',
        'registration_status': 'ativa',
        'is_headquarters': 0,
        'active': 1,
        'notes': 'obs',
      });
      expect(entity.id, 3);
      expect(entity.companyId, 1);
      expect(entity.cnpj, '11.222.333/0001-81');
      expect(entity.legalName, 'ACME Filial RJ Ltda');
      expect(entity.entityType, 'filial');
      expect(entity.parentEntityId, 1);
      expect(entity.uf, 'RJ');
      expect(entity.isHeadquarters, isFalse);
      expect(entity.active, isTrue);
    });

    test('aceita 0/1, bool e string nos campos booleanos', () {
      expect(LegalEntity.fromJson(const {'id': 1, 'active': true}).active, isTrue);
      expect(LegalEntity.fromJson(const {'id': 1, 'active': 0}).active, isFalse);
      expect(LegalEntity.fromJson(const {'id': 1, 'active': '1'}).active, isTrue);
      expect(LegalEntity.fromJson(const {'id': 1, 'is_headquarters': 1}).isHeadquarters, isTrue);
    });

    test('active assume true quando ausente', () {
      expect(LegalEntity.fromJson(const {'id': 1}).active, isTrue);
    });

    test('entity_type vazio cai para matriz', () {
      expect(LegalEntity.fromJson(const {'id': 1, 'entity_type': ''}).entityType, 'matriz');
    });

    test('displayLabel prefere nome fantasia e inclui o CNPJ', () {
      final entity = LegalEntity.fromJson(const {
        'id': 1, 'cnpj': '11.222.333/0001-81',
        'legal_name': 'ACME SA', 'trade_name': 'ACME',
      });
      expect(entity.displayLabel, 'ACME — 11.222.333/0001-81');
    });

    test('displayLabel cai para razão social sem nome fantasia', () {
      final entity = LegalEntity.fromJson(const {
        'id': 1, 'cnpj': '11.222.333/0001-81', 'legal_name': 'ACME SA', 'trade_name': '',
      });
      expect(entity.displayLabel, 'ACME SA — 11.222.333/0001-81');
    });
  });

  group('LegalEntity.toJson', () {
    test('serializa booleanos como 0/1, como o backend espera', () {
      final json = LegalEntity.fromJson(const {
        'id': 1, 'cnpj': '11.222.333/0001-81', 'legal_name': 'ACME SA',
        'active': 0, 'is_headquarters': 1,
      }).toJson();
      expect(json['active'], 0);
      expect(json['is_headquarters'], 1);
    });

    test('omite parent_entity_id quando não há controladora', () {
      final json = LegalEntity.fromJson(const {'id': 1, 'legal_name': 'X'}).toJson();
      expect(json.containsKey('parent_entity_id'), isFalse);
    });
  });

  group('BootstrapResponse.legalEntities', () {
    test('lê a seção legal_entities do bootstrap', () {
      final res = BootstrapResponse.fromJson(const {
        'units': <dynamic>[],
        'employees': <dynamic>[],
        'epis': <dynamic>[],
        'users': <dynamic>[],
        'alerts': <dynamic>[],
        'deliveries': <dynamic>[],
        'legal_entities': [
          {'id': 1, 'cnpj': '11.222.333/0001-81', 'legal_name': 'ACME SA'},
        ],
      });
      expect(res.legalEntities, hasLength(1));
      expect(res.legalEntities.first['cnpj'], '11.222.333/0001-81');
    });

    test('lista vazia quando o backend ainda não expõe a seção', () {
      final res = BootstrapResponse.fromJson(const {
        'units': <dynamic>[],
        'employees': <dynamic>[],
        'epis': <dynamic>[],
        'users': <dynamic>[],
        'alerts': <dynamic>[],
        'deliveries': <dynamic>[],
      });
      expect(res.legalEntities, isEmpty);
    });
  });

  group('Employee — vínculo jurídico', () {
    test('lê o CNPJ do colaborador vindo de fetch_employees', () {
      final employee = Employee.fromJson(const {
        'id': 5,
        'name': 'Ana',
        'legal_entity_id': 3,
        'legal_entity_cnpj': '11.222.333/0001-81',
        'legal_entity_name': 'ACME Filial RJ Ltda',
      });
      expect(employee.legalEntityId, 3);
      expect(employee.legalEntityCnpj, '11.222.333/0001-81');
      expect(employee.legalEntityName, 'ACME Filial RJ Ltda');
    });

    test('vínculo nulo enquanto o schema Multi-CNPJ não estiver provisionado', () {
      final employee = Employee.fromJson(const {'id': 5, 'name': 'Ana'});
      expect(employee.legalEntityId, isNull);
      expect(employee.legalEntityCnpj, isNull);
    });
  });
}
