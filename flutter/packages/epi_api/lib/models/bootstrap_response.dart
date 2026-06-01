/// Resposta do GET /api/bootstrap — espelha exatamente o payload UBX.
/// Filtrado pelo canary (units/employees/epis/users já filtrados por visibilidade).
class BootstrapResponse {
  const BootstrapResponse({
    required this.units,
    required this.employees,
    required this.epis,
    required this.users,
    required this.alerts,
    this.preferredLocale,
    this.companyLocale,
  });

  final List<Map<String, dynamic>> units;
  final List<Map<String, dynamic>> employees;
  final List<Map<String, dynamic>> epis;
  final List<Map<String, dynamic>> users;
  final List<Map<String, dynamic>> alerts;
  final String? preferredLocale;  // user.locale
  final String? companyLocale;    // company.default_locale

  factory BootstrapResponse.fromJson(Map<String, dynamic> json) {
    List<Map<String, dynamic>> _list(String key) =>
        (json[key] as List? ?? []).cast<Map<String, dynamic>>();
    return BootstrapResponse(
      units:     _list('units'),
      employees: _list('employees'),
      epis:      _list('epis'),
      users:     _list('users'),
      alerts:    _list('alerts'),
      preferredLocale: json['preferred_locale'] as String?,
      companyLocale:   json['company_locale']   as String?,
    );
  }
}
