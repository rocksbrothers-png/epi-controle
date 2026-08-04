import 'package:epi_design/epi_design.dart' as ds;
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:epi_admin/core/i18n/generated/app_localizations.dart';
import 'package:go_router/go_router.dart';
import '../bloc/auth_cubit.dart';
import '../bloc/auth_state.dart';
import '../router/navigation_policy.dart';
import '../router/route_permissions.dart';
import '../router/routes.dart';

/// Shell oficial do EPI Controle.
/// Delega completamente ao AppShell do Design System (sidebar colapsável,
/// breadcrumbs, dark mode). Breakpoints unificados via EpiBreakpoints.
/// Itens de navegação são filtrados pela lista de permissões do usuário.
class AppShell extends StatelessWidget {
  const AppShell({super.key, required this.location, required this.child});

  final String location;
  final Widget child;

  /// Destino do menu lateral.
  ///
  /// O rótulo é um **seletor** de `AppLocalizations`, não uma string em lista
  /// separada. Antes havia duas listas casadas por índice, e foi por isso que a
  /// tela de CNPJs ficou sem entrada de menu: o destino entrou numa, o rótulo
  /// não entrou na outra, e nada acusou. Aqui os dois nascem juntos.
  static const _destinations = <(String, IconData, IconData, String, String Function(AppLocalizations))>[
    (Routes.dashboard,  Icons.dashboard_outlined,          Icons.dashboard_rounded,          'dashboard:view',        _navDashboard),
    (Routes.employees,  Icons.people_outline_rounded,      Icons.people_rounded,             'employees:view',        _navEmployees),
    (Routes.epis,       Icons.shield_outlined,             Icons.shield_rounded,             'epis:view',             _navEpis),
    (Routes.deliveries, Icons.local_shipping_outlined,     Icons.local_shipping_rounded,     'deliveries:view',       _navDeliveries),
    (Routes.returns,    Icons.assignment_return_outlined,  Icons.assignment_return_rounded,  'deliveries:view',       _navReturns),
    (Routes.records,    Icons.folder_outlined,             Icons.folder_rounded,             'fichas:view',           _navRecords),
    (Routes.stock,      Icons.inventory_2_outlined,        Icons.inventory_2_rounded,        'stock:view',            _navStock),
    (Routes.purchases,  Icons.shopping_cart_outlined,      Icons.shopping_cart_rounded,      'purchase_requests:view', _navPurchases),
    (Routes.companies,  Icons.business_outlined,           Icons.business_rounded,           'companies:view',        _navCompanies),
    (Routes.reports,    Icons.bar_chart_outlined,          Icons.bar_chart_rounded,          'reports:view',          _navReports),
    (Routes.users,      Icons.manage_accounts_outlined,    Icons.manage_accounts_rounded,    'users:view',            _navUsers),
    (Routes.units,      Icons.location_on_outlined,        Icons.location_on_rounded,        'units:view',            _navUnits),
    // CNPJ fica ao lado de Unidades: é o nível imediatamente acima dela na
    // hierarquia Empresa → CNPJ → Unidade.
    (Routes.legalEntities, Icons.domain_outlined,          Icons.domain_rounded,             'legal_entities:view',   _navLegalEntities),
    // Terceirizados e Prestadores (ADR-0002) — subpasta de Colaboradores.
    // Reaproveita o piso técnico de criar colaborador (employees:create);
    // a visibilidade real é module_visibility (oculto por padrão até o
    // Administrador Geral ligar em Configuração → Regras → Visualização).
    (Routes.outsourcedCompanies, Icons.groups_outlined,    Icons.groups_rounded,              'employees:create',      _navTerceirizados),
    (Routes.feedback,   Icons.rate_review_outlined,        Icons.rate_review_rounded,        'epi_feedback:view',     _navFeedback),
    (Routes.settings,   Icons.settings_outlined,           Icons.settings_rounded,           'settings:view',         _navSettings),
  ];

  // Seletores de rótulo. Precisam ser funções de topo para caber num `const`.
  static String _navDashboard(AppLocalizations l) => l.navDashboard;
  static String _navEmployees(AppLocalizations l) => l.navEmployees;
  static String _navEpis(AppLocalizations l) => l.navEpis;
  static String _navDeliveries(AppLocalizations l) => l.navDeliveries;
  static String _navReturns(AppLocalizations l) => l.navReturns;
  static String _navRecords(AppLocalizations l) => l.navRecords;
  static String _navStock(AppLocalizations l) => l.navStock;
  static String _navPurchases(AppLocalizations l) => l.navPurchases;
  static String _navCompanies(AppLocalizations l) => l.navCompanies;
  static String _navReports(AppLocalizations l) => l.navReports;
  static String _navUsers(AppLocalizations l) => l.navUsers;
  static String _navUnits(AppLocalizations l) => l.navUnits;
  static String _navLegalEntities(AppLocalizations l) => l.navLegalEntities;
  static String _navTerceirizados(AppLocalizations l) => l.navTerceirizados;
  static String _navFeedback(AppLocalizations l) => l.navFeedback;
  static String _navSettings(AppLocalizations l) => l.navSettings;

  /// Rotas alcançáveis pelo menu — usado pelo teste que confronta navegação
  /// com as rotas gateadas.
  static List<String> get destinationRoutes =>
      [for (final d in _destinations) d.$1];

  /// Permissões que liberam cada destino.
  static List<String> get destinationPermissions =>
      [for (final d in _destinations) d.$4];

  static int get destinationCount => _destinations.length;

  /// Mantido para o teste de simetria; com a lista única, é sempre igual.
  static int get labelCount => _destinations.length;

  /// Permissão técnica (piso) AND visibilidade de módulo (configuração do
  /// Administrador Geral) — mesma combinação usada no guarda de rota do
  /// GoRouter, agora também no menu, para os dois nunca divergirem.
  bool _isDestinationVisible(
    (String, IconData, IconData, String, String Function(AppLocalizations)) d,
    List<String> permissions,
    Map<String, bool> moduleVisibility,
  ) {
    if (!hasRoutePermission(d.$1, permissions)) return false;
    return isModuleLocationAccessible(d.$1, moduleVisibility);
  }

  int _selectedIndex(List<String> permissions, Map<String, bool> moduleVisibility) {
    var idx = 0;
    for (var i = 0; i < _destinations.length; i++) {
      if (!_isDestinationVisible(_destinations[i], permissions, moduleVisibility)) continue;
      final route = _destinations[i].$1;
      if (route == Routes.dashboard) {
        if (location == route) return idx;
      } else if (location.startsWith(route)) {
        return idx;
      }
      idx++;
    }
    return 0;
  }

  List<ds.EpiNavItem> _buildNavItems(AppLocalizations l10n, List<String> permissions,
      Map<String, bool> moduleVisibility) {
    return [
      for (final d in _destinations)
        if (_isDestinationVisible(d, permissions, moduleVisibility))
          ds.EpiNavItem(icon: d.$2, label: d.$5(l10n)),
    ];
  }

  String _currentTitle(AppLocalizations l10n, List<String> permissions,
      Map<String, bool> moduleVisibility) {
    final items = _buildNavItems(l10n, permissions, moduleVisibility);
    if (items.isEmpty) return '';
    final idx = _selectedIndex(permissions, moduleVisibility);
    return items[idx < items.length ? idx : 0].label;
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final authState = context.watch<AuthCubit>().state;
    final permissions = authState is AuthAuthenticated
        ? authState.permissions
        : const <String>[];
    final moduleVisibility = authState is AuthAuthenticated
        ? authState.sessionContext.moduleVisibility
        : const <String, bool>{};

    final visibleRoutes = [
      for (final d in _destinations)
        if (_isDestinationVisible(d, permissions, moduleVisibility)) d.$1,
    ];

    return ds.AppShell(
      selectedIndex: _selectedIndex(permissions, moduleVisibility),
      navItems:      _buildNavItems(l10n, permissions, moduleVisibility),
      onNavSelected: (i) {
        if (i < visibleRoutes.length) context.go(visibleRoutes[i]);
      },
      title:  _currentTitle(l10n, permissions, moduleVisibility),
      child:  child,
    );
  }
}
