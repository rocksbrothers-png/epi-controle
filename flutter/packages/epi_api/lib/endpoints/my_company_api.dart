import 'package:dio/dio.dart';

import '../models/my_company_profile.dart';
import '../models/tenant_domain.dart';

/// Cliente de "Minha Empresa" — configuração da própria tenant pelo
/// Administrador Geral (Owner). O backend deriva a empresa do usuário
/// autenticado (JWT): nenhum company_id é enviado pelo app.
class MyCompanyApi {
  const MyCompanyApi(this._dio);
  final Dio _dio;

  Future<MyCompanyProfile> getMyCompany() async {
    final res = await _dio.get<Map<String, dynamic>>('/api/my-company');
    return MyCompanyProfile.fromJson(
      (res.data?['company'] as Map<String, dynamic>?) ?? const {},
    );
  }

  /// Update parcial: envie apenas os campos alterados (whitelist no backend).
  Future<MyCompanyProfile> updateMyCompany(Map<String, dynamic> fields) async {
    final res =
        await _dio.put<Map<String, dynamic>>('/api/my-company', data: fields);
    return MyCompanyProfile.fromJson(
      (res.data?['company'] as Map<String, dynamic>?) ?? const {},
    );
  }

  Future<void> completeOnboarding() async {
    await _dio.post<void>('/api/my-company/onboarding-complete', data: const {});
  }

  Future<List<TenantDomain>> getDomains() async {
    final res = await _dio.get<Map<String, dynamic>>('/api/my-company/domains');
    final items = (res.data?['domains'] as List?) ?? const [];
    return items
        .map((e) => TenantDomain.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  Future<TenantDomain> registerDomain({
    required String domain,
    required String domainType,
  }) async {
    final res = await _dio.post<Map<String, dynamic>>(
      '/api/my-company/domains',
      data: {'domain': domain, 'domain_type': domainType},
    );
    return TenantDomain.fromJson(
      (res.data?['domain'] as Map<String, dynamic>?) ?? const {},
    );
  }

  Future<TenantDomain> verifyDomain(int id) async {
    final res = await _dio.post<Map<String, dynamic>>(
      '/api/my-company/domains/$id/verify',
      data: const {},
    );
    return TenantDomain.fromJson(
      (res.data?['domain'] as Map<String, dynamic>?) ?? const {},
    );
  }

  Future<void> deleteDomain(int id) async {
    await _dio.delete<void>('/api/my-company/domains/$id');
  }
}
