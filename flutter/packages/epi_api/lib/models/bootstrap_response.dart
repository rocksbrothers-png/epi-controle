/// Resposta do GET /api/bootstrap — espelha exatamente o payload UBX.
/// Filtrado pelo canary (units/employees/epis/users já filtrados por visibilidade).
class BootstrapResponse {
  const BootstrapResponse({
    required this.units,
    this.legalEntities = const [],
    required this.employees,
    required this.epis,
    required this.users,
    required this.alerts,
    required this.deliveries,
    this.pendingPurchases = 0,
    this.preferredLocale,
    this.companyLocale,
  });

  final List<Map<String, dynamic>> units;

  /// CNPJs (LegalEntity) visíveis ao ator — já escopados por papel pelo
  /// backend. Alimentam o filtro em cascata Empresa → CNPJ → Unidade → Setor
  /// e o seletor de CNPJ no cadastro de colaborador.
  final List<Map<String, dynamic>> legalEntities;

  final List<Map<String, dynamic>> employees;
  final List<Map<String, dynamic>> epis;
  final List<Map<String, dynamic>> users;
  final List<Map<String, dynamic>> alerts;
  final List<Map<String, dynamic>> deliveries;

  /// KPI do dashboard: requisições de compra pendentes (não terminais) no
  /// escopo do ator. Vem de `pending_purchases` do bootstrap.
  final int pendingPurchases;
  final String? preferredLocale;  // user.locale
  final String? companyLocale;    // company.default_locale

  factory BootstrapResponse.fromJson(Map<String, dynamic> json) {
    // Backend wraps payload in {'ok': true, 'data': {...}}
    final data = (json['data'] as Map<String, dynamic>?) ?? json;
    List<Map<String, dynamic>> _list(String key) =>
        (data[key] as List? ?? []).cast<Map<String, dynamic>>();
    return BootstrapResponse(
      units:      _list('units'),
      legalEntities: _list('legal_entities'),
      employees:  _list('employees'),
      epis:       _list('epis'),
      users:      _list('users'),
      alerts:     _list('alerts'),
      deliveries: _list('deliveries'),
      pendingPurchases: (data['pending_purchases'] as num?)?.toInt() ?? 0,
      preferredLocale: data['preferred_locale'] as String?,
      companyLocale:   data['company_locale']   as String?,
    );
  }
}
