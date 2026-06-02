/// Resposta do GET /api/bootstrap — espelha exatamente o payload UBX.
/// Filtrado pelo canary (units/employees/epis/users já filtrados por visibilidade).
class BootstrapResponse {
  const BootstrapResponse({
    required this.units,
    required this.employees,
    required this.epis,
    required this.users,
    required this.alerts,
    required this.deliveries,
    this.preferredLocale,
    this.companyLocale,
  });

  final List<Map<String, dynamic>> units;
  final List<Map<String, dynamic>> employees;
  final List<Map<String, dynamic>> epis;
  final List<Map<String, dynamic>> users;
  final List<Map<String, dynamic>> alerts;
  final List<Map<String, dynamic>> deliveries;
  final String? preferredLocale;  // user.locale
  final String? companyLocale;    // company.default_locale

  factory BootstrapResponse.fromJson(Map<String, dynamic> json) {
    // Backend wraps payload in {'ok': true, 'data': {...}}
    final data = (json['data'] as Map<String, dynamic>?) ?? json;
    List<Map<String, dynamic>> _list(String key) =>
        (data[key] as List? ?? []).cast<Map<String, dynamic>>();
    return BootstrapResponse(
      units:      _list('units'),
      employees:  _list('employees'),
      epis:       _list('epis'),
      users:      _list('users'),
      alerts:     _list('alerts'),
      deliveries: _list('deliveries'),
      preferredLocale: data['preferred_locale'] as String?,
      companyLocale:   data['company_locale']   as String?,
    );
  }
}
