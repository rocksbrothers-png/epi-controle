import 'dart:convert';
import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:epi_api/epi_api.dart';
import 'package:flutter_test/flutter_test.dart';

/// Contrato do cliente `MyCompanyApi` (Configurações > Minha Empresa).
///
/// Trava as chaves de resposta (`company`, `domains`, `domain`) e o parsing
/// dos modelos — a mesma classe de bug de Empresas (#593): ler a chave errada
/// devolve dados vazios silenciosamente.
class _StubAdapter implements HttpClientAdapter {
  _StubAdapter(this.body, {this.status = 200});
  final Object body;
  final int status;

  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? requestStream,
    Future<void>? cancelFuture,
  ) async {
    return ResponseBody.fromString(
      jsonEncode(body),
      status,
      headers: {
        Headers.contentTypeHeader: [Headers.jsonContentType],
      },
    );
  }

  @override
  void close({bool force = false}) {}
}

Dio _dioReturning(Object body, {int status = 200}) {
  final dio = Dio(BaseOptions(baseUrl: 'http://test.local'));
  dio.httpClientAdapter = _StubAdapter(body, status: status);
  return dio;
}

const _companyJson = {
  'id': 7,
  'name': 'ACME',
  'legal_name': 'ACME LTDA',
  'cnpj': '04.252.011/0001-10',
  'state_registration': 'IE-1',
  'address': 'Rua A, 100',
  'contact_phone': '11 99999-0000',
  'contact_email': 'contato@acme.com.br',
  'display_name': 'ACME EPI',
  'primary_color': '#112233',
  'subdomain': 'acme',
  'timezone': 'America/Sao_Paulo',
  'plan_name': 'start',
  'user_limit': 25,
  'license_status': 'active',
  'onboarding_completed': 0,
};

void main() {
  group('MyCompanyApi', () {
    test('getMyCompany lê a chave `company`', () async {
      final api = MyCompanyApi(_dioReturning({'ok': true, 'company': _companyJson}));
      final profile = await api.getMyCompany();
      expect(profile.id, 7);
      expect(profile.name, 'ACME');
      expect(profile.legalName, 'ACME LTDA');
      expect(profile.subdomain, 'acme');
      expect(profile.planName, 'start');
      expect(profile.userLimit, 25);
      expect(profile.onboardingCompleted, isFalse);
    });

    test('updateMyCompany devolve o perfil atualizado', () async {
      final api = MyCompanyApi(_dioReturning({
        'ok': true,
        'company': {..._companyJson, 'name': 'ACME Nova'},
      }));
      final profile = await api.updateMyCompany({'name': 'ACME Nova'});
      expect(profile.name, 'ACME Nova');
    });

    test('getDomains lê a chave `domains` e o modelo TenantDomain', () async {
      final api = MyCompanyApi(_dioReturning({
        'ok': true,
        'domains': [
          {
            'id': 3,
            'domain': 'epi.acme.com.br',
            'domain_type': 'custom_domain',
            'full_host': 'epi.acme.com.br',
            'type_label': 'Domínio personalizado',
            'verification_status': 'pending',
            'ssl_status': 'pending',
            'verification_token': 'epi-verify-abc',
            'cname_target': 'app.epicontrole.com',
            'txt_record': '_epicontrole-verify.epi.acme.com.br',
            'is_primary': 0,
          },
        ],
      }));
      final domains = await api.getDomains();
      expect(domains, hasLength(1));
      expect(domains.first.id, 3);
      expect(domains.first.fullHost, 'epi.acme.com.br');
      expect(domains.first.isVerified, isFalse);
      expect(domains.first.cnameTarget, 'app.epicontrole.com');
    });

    test('registerDomain lê a chave `domain`', () async {
      final api = MyCompanyApi(_dioReturning({
        'ok': true,
        'domain': {
          'id': 9,
          'domain': 'acme',
          'domain_type': 'platform_subdomain',
          'full_host': 'acme.epicontrole.com',
          'verification_status': 'verified',
          'ssl_status': 'active',
          'is_primary': 1,
        },
      }));
      final domain = await api.registerDomain(
        domain: 'acme',
        domainType: 'platform_subdomain',
      );
      expect(domain.id, 9);
      expect(domain.isVerified, isTrue);
      expect(domain.isPrimary, isTrue);
    });

    test('chave errada → perfil vazio (guarda de contrato)', () async {
      final api = MyCompanyApi(_dioReturning({'ok': true, 'profile': _companyJson}));
      final profile = await api.getMyCompany();
      expect(profile.id, 0);
      expect(profile.name, isEmpty);
    });
  });
}
