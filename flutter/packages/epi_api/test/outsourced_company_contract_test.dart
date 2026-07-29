import 'package:epi_api/epi_api.dart';
import 'package:flutter_test/flutter_test.dart';

/// Contrato dos modelos do Cadastro Simplificado de Terceirizados e
/// Prestadores (ADR-0002): OutsourcedCompany, ServiceContract,
/// MigrationSuggestion, EpiReimbursement.
void main() {
  group('OutsourcedCompany.fromJson', () {
    test('lê o payload completo de /api/outsourced-companies', () {
      final company = OutsourcedCompany.fromJson(const {
        'id': 9,
        'company_id': 1,
        'legal_name': 'Terceirizada X Ltda',
        'trade_name': 'Terceirizada X',
        'cnpj': '11.222.333/0001-81',
        'company_kind': 'outsourced',
        'epi_responsibility': 'Empresa Terceirizada',
        'registration_mode': 'standard',
        'registration_status': 'complete',
        'status': 'Ativa',
        'promoted_at': '2026-07-01T00:00:00',
        'created_at': '2026-01-01T00:00:00',
      });
      expect(company.id, 9);
      expect(company.companyId, 1);
      expect(company.legalName, 'Terceirizada X Ltda');
      expect(company.companyKind, 'outsourced');
      expect(company.epiResponsibility, 'Empresa Terceirizada');
      expect(company.registrationMode, 'standard');
      expect(company.isSimplified, isFalse);
    });

    test('defaults seguros quando os campos vêm vazios (Cadastro Simplificado)', () {
      final company = OutsourcedCompany.fromJson(const {
        'id': 1, 'company_id': 1, 'legal_name': 'Terceirizada Y',
      });
      expect(company.cnpj, '');
      expect(company.companyKind, 'outsourced');
      expect(company.epiResponsibility, 'Conforme Contrato');
      expect(company.registrationMode, 'simplified');
      expect(company.registrationStatus, 'pending_completion');
      expect(company.isSimplified, isTrue);
    });

    test('companyKindLabel traduz o valor técnico para PT-BR só na exibição', () {
      expect(
        OutsourcedCompany.fromJson(const {'id': 1, 'company_id': 1, 'legal_name': 'X', 'company_kind': 'outsourced'})
            .companyKindLabel,
        'Terceirizada',
      );
      expect(
        OutsourcedCompany.fromJson(const {'id': 1, 'company_id': 1, 'legal_name': 'X', 'company_kind': 'service_provider'})
            .companyKindLabel,
        'Prestadora de Serviço',
      );
      expect(
        OutsourcedCompany.fromJson(const {'id': 1, 'company_id': 1, 'legal_name': 'X', 'company_kind': 'other_contracted'})
            .companyKindLabel,
        'Outro',
      );
    });

    test('displayLabel prefere nome fantasia e inclui o CNPJ quando presente', () {
      final company = OutsourcedCompany.fromJson(const {
        'id': 1, 'company_id': 1, 'legal_name': 'Terceirizada X Ltda',
        'trade_name': 'Terceirizada X', 'cnpj': '11.222.333/0001-81',
      });
      expect(company.displayLabel, 'Terceirizada X — 11.222.333/0001-81');
    });

    test('displayLabel sem CNPJ (Cadastro Simplificado emergencial)', () {
      final company = OutsourcedCompany.fromJson(const {
        'id': 1, 'company_id': 1, 'legal_name': 'Terceirizada Sem CNPJ',
      });
      expect(company.displayLabel, 'Terceirizada Sem CNPJ');
    });
  });

  group('OutsourcedCompany.toJson', () {
    test('nunca inclui id/company_id — o backend resolve pelo tenant do ator', () {
      final json = OutsourcedCompany.fromJson(const {
        'id': 9, 'company_id': 1, 'legal_name': 'Terceirizada X',
      }).toJson();
      expect(json.containsKey('id'), isFalse);
      expect(json.containsKey('company_id'), isFalse);
      expect(json['legal_name'], 'Terceirizada X');
      expect(json['company_kind'], 'outsourced');
    });
  });

  group('ServiceContract', () {
    test('hasOverride reflete se há exceção de responsabilidade', () {
      final withOverride = ServiceContract.fromJson(const {
        'id': 1, 'outsourced_company_id': 9,
        'epi_responsibility_override': 'Empresa Contratante',
        'override_reason': 'Acordo pontual',
      });
      expect(withOverride.hasOverride, isTrue);

      final withoutOverride = ServiceContract.fromJson(const {
        'id': 2, 'outsourced_company_id': 9,
      });
      expect(withoutOverride.hasOverride, isFalse);
      expect(withoutOverride.status, 'Ativo');
    });

    test('toJson só inclui override_reason quando há override', () {
      final json = ServiceContract.fromJson(const {
        'id': 1, 'outsourced_company_id': 9,
      }).toJson();
      expect(json.containsKey('override_reason'), isFalse);
    });
  });

  group('MigrationSuggestion.fromJson', () {
    test('lê a sugestão de migração', () {
      final suggestion = MigrationSuggestion.fromJson(const {
        'outsourced_company_id': 9,
        'legal_name': 'Terceirizada X',
        'registration_mode': 'simplified',
        'age_days': 45,
        'threshold_days': 30,
      });
      expect(suggestion.outsourcedCompanyId, 9);
      expect(suggestion.ageDays, 45);
      expect(suggestion.thresholdDays, 30);
    });
  });

  group('EpiReimbursement.fromJson', () {
    test('lê o registro de ressarcimento com o enum de 8 estados', () {
      final reimbursement = EpiReimbursement.fromJson(const {
        'id': 1, 'delivery_id': 10, 'outsourced_company_id': 9,
        'unit_cost': 12.5, 'quantity': 3, 'total_value': 37.5,
        'status': 'Ressarcida',
      });
      expect(reimbursement.totalValue, 37.5);
      expect(reimbursement.status, 'Ressarcida');
    });

    test('status vazio cai para Não Aplicável', () {
      final reimbursement = EpiReimbursement.fromJson(const {
        'id': 1, 'delivery_id': 10, 'outsourced_company_id': 9,
      });
      expect(reimbursement.status, 'Não Aplicável');
    });
  });
}
