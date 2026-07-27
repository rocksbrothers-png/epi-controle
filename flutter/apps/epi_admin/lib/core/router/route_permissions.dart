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
  Routes.returns: 'deliveries:view',
  Routes.records: 'fichas:view',
  Routes.stock: 'stock:view',
  Routes.purchases: 'purchase_requests:view',
  Routes.companies: 'companies:view',
  Routes.reports: 'reports:view',
  Routes.users: 'users:view',
  Routes.units: 'units:view',
  Routes.legalEntities: 'legal_entities:view',
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
