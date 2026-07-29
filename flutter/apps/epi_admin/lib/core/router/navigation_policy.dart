import 'routes.dart';

/// Mapa **rota → módulo estrutural** (espelha `MODULE_REQUIRED_PERMISSIONS`
/// em `epi_backend/rule_engine.py`). Cobre só os módulos que o
/// Administrador Geral pode configurar em Configuração → Regras →
/// Visualização; rota ausente daqui continua gateada só pela permissão
/// técnica ([routePermissions]), sem mudança de comportamento.
///
/// Ponto único de verdade para menu lateral, menu inferior, atalhos do
/// dashboard e o guarda de rota do GoRouter — Web, Android e iOS, incluindo
/// deep link / URL direta, já que todos passam pelo mesmo `redirect`.
const Map<String, String> routeModules = <String, String>{
  Routes.dashboard: 'dashboard',
  Routes.purchases: 'compras',
  Routes.stock: 'estoque',
  Routes.deliveries: 'entregas',
  Routes.returns: 'entregas',
  Routes.records: 'fichas',
  Routes.reports: 'relatorios',
  Routes.companies: 'administracao',
  Routes.users: 'administracao',
  Routes.legalEntities: 'administracao',
  // Cadastro Simplificado de Terceirizados e Prestadores (ADR-0002) — módulo
  // opt-in: oculto por padrão para todo papel até o Administrador Geral
  // ligá-lo explicitamente por tenant (ver rule_engine.py _OPT_IN_MODULES).
  Routes.outsourcedCompanies: 'terceirizados',
  Routes.settings: 'configuracoes',
  Routes.subscription: 'configuracoes',
  Routes.invoices: 'configuracoes',
};

/// Resolve o módulo estrutural exigido para [location], considerando
/// subrotas (ex.: `/purchases/123` → `compras`). Retorna `null` quando a
/// rota não é coberta por esta camada.
///
/// `dashboard` retorna `null` de propósito, no mesmo padrão de
/// [requiredPermissionFor] em `route_permissions.dart`: é o destino do
/// redirect guard, e gateá-lo aqui causaria loop de redirect para um
/// perfil cujo módulo "dashboard" tenha sido desligado por engano.
String? requiredModuleFor(String location) {
  if (location == Routes.dashboard) return null;
  for (final entry in routeModules.entries) {
    if (entry.key == Routes.dashboard) continue;
    if (location.startsWith(entry.key)) return entry.value;
  }
  return null;
}

/// Decisão final de navegação para [location]: permissão técnica (piso,
/// já resolvida em `permissions`/`requiredPermissionFor`) AND visibilidade
/// de módulo (configuração do Administrador Geral, já clampada pela
/// permissão técnica no backend). O backend segue como autoridade final —
/// esta função só orienta menu/rotas/deep links, nunca autoriza dados.
bool isModuleLocationAccessible(
  String location,
  Map<String, bool> moduleVisibility,
) {
  final module = requiredModuleFor(location);
  if (module == null) return true;
  return moduleVisibility[module] ?? true;
}
