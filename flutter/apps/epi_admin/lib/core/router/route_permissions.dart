import 'routes.dart';

/// Mapa **rota → permissão exigida** (espelha `core/permissions.py` do backend).
///
/// Rota ausente deste mapa = sem guarda de permissão além de estar logado
/// (ex.: rotas públicas `login`/`qr`/`portal`). `dashboard` é o destino do
/// redirect guard e por isso é tratado como fallback (ver [requiredPermissionFor]).
///
/// Mantido como unidade pura (sem dependência de Flutter/go_router) para ser
/// testável de forma isolada — é a matriz RBAC do app e precisa casar com o
/// backend para não liberar/negar telas indevidamente.
const Set<String> publicRoutes = <String>{
  Routes.login,
  Routes.qr,
  Routes.portal,
};

const Map<String, String> routePermissions = <String, String>{
  Routes.dashboard: 'dashboard:view',
  Routes.employees: 'employees:view',
  Routes.epis: 'epis:view',
  Routes.deliveries: 'deliveries:view',
  Routes.handover: 'deliveries:view',
  Routes.returns: 'deliveries:view',
  Routes.records: 'fichas:view',
  Routes.stock: 'stock:view',
  Routes.purchases: 'purchase_requests:view',
  Routes.companies: 'companies:view',
  Routes.reports: 'reports:view',
  Routes.users: 'users:view',
  Routes.units: 'units:view',
  Routes.legalEntities: 'legal_entities:view',
  // Reaproveita o mesmo piso técnico de criar colaborador (ADR-0002) — sem
  // permissão dedicada, por decisão explícita do ADR.
  Routes.outsourcedCompanies: 'employees:create',
  Routes.feedback: 'epi_feedback:view',
  Routes.myCompany: 'company_settings:view',
  Routes.settings: 'settings:view',
  Routes.subscription: 'settings:view',
  Routes.invoices: 'settings:view',
};

/// Resolve a permissão exigida para [location], considerando subrotas
/// (ex.: `/epis/123` → `epis:view`). Retorna `null` quando a rota não exige
/// permissão específica.
///
/// `dashboard` (`/`) retorna `null` de propósito: é o fallback universal do
/// redirect guard; exigir `dashboard:view` aqui causaria loop de redirect para
/// usuários sem essa permissão.
String? requiredPermissionFor(String location) {
  if (location == Routes.dashboard) return null;
  for (final entry in routePermissions.entries) {
    if (entry.key == Routes.dashboard) continue;
    if (location.startsWith(entry.key)) return entry.value;
  }
  return null;
}

/// Permissão alternativa que também libera [routePermissions] — só para
/// rotas onde mais de um piso técnico dá acesso a partes diferentes da
/// mesma tela (ex.: Terceirizados e Prestadores, ADR-0002 §10: a aba
/// Empresas usa `employees:create`, a aba Cadastro de Colaboradores usa
/// `employees:create_simplified` — `admin`/`user` têm só a segunda).
///
/// Mantido separado de [routePermissions] (em vez de um valor composto) para
/// não quebrar o formato `recurso:ação` que os testes de RBAC já travam.
const Map<String, String> routePermissionAlternatives = <String, String>{
  Routes.outsourcedCompanies: 'employees:create_simplified',
};

/// Decisão final de acesso: a permissão primária OU a alternativa (quando
/// houver) libera a rota. Ponto único usado pelo redirect guard e pelo menu
/// para nunca divergirem.
bool hasRoutePermission(String location, List<String> permissions) {
  final required = requiredPermissionFor(location);
  if (required == null || permissions.contains(required)) return true;
  final alternative = _alternativePermissionFor(location);
  return alternative != null && permissions.contains(alternative);
}

String? _alternativePermissionFor(String location) {
  for (final entry in routePermissionAlternatives.entries) {
    if (location.startsWith(entry.key)) return entry.value;
  }
  return null;
}
