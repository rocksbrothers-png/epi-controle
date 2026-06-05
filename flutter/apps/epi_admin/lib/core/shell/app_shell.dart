import 'package:epi_design/epi_design.dart' as ds;
import 'package:flutter/material.dart';
import 'package:epi_admin/core/i18n/generated/app_localizations.dart';
import 'package:go_router/go_router.dart';
import '../router/routes.dart';

/// Shell oficial do EPI Controle.
/// Delega completamente ao AppShell do Design System (sidebar colapsável,
/// breadcrumbs, dark mode). Breakpoints unificados via EpiBreakpoints.
class AppShell extends StatelessWidget {
  const AppShell({super.key, required this.location, required this.child});

  final String location;
  final Widget child;

  // Destinos ordenados: (rota, ícone-inativo, ícone-ativo)
  static const _destinations = [
    (Routes.dashboard,  Icons.dashboard_outlined,        Icons.dashboard_rounded),
    (Routes.employees,  Icons.people_outline_rounded,    Icons.people_rounded),
    (Routes.epis,       Icons.shield_outlined,           Icons.shield_rounded),
    (Routes.deliveries, Icons.local_shipping_outlined,   Icons.local_shipping_rounded),
    (Routes.returns,    Icons.assignment_return_outlined, Icons.assignment_return_rounded),
    (Routes.records,    Icons.folder_outlined,           Icons.folder_rounded),
    (Routes.stock,      Icons.inventory_2_outlined,      Icons.inventory_2_rounded),
    (Routes.purchases,  Icons.shopping_cart_outlined,    Icons.shopping_cart_rounded),
    (Routes.companies,  Icons.business_outlined,         Icons.business_rounded),
    (Routes.reports,    Icons.bar_chart_outlined,        Icons.bar_chart_rounded),
    (Routes.users,      Icons.manage_accounts_outlined,  Icons.manage_accounts_rounded),
    (Routes.units,      Icons.location_on_outlined,      Icons.location_on_rounded),
    (Routes.feedback,   Icons.rate_review_outlined,      Icons.rate_review_rounded),
    (Routes.settings,   Icons.settings_outlined,         Icons.settings_rounded),
  ];

  int _selectedIndex() {
    for (var i = 0; i < _destinations.length; i++) {
      final route = _destinations[i].$1;
      if (route == Routes.dashboard) {
        if (location == route) return i;
      } else if (location.startsWith(route)) {
        return i;
      }
    }
    return 0;
  }

  List<ds.EpiNavItem> _buildNavItems(AppLocalizations l10n) {
    final labels = [
      l10n.navDashboard,
      l10n.navEmployees,
      l10n.navEpis,
      l10n.navDeliveries,
      l10n.navReturns,
      l10n.navRecords,
      l10n.navStock,
      l10n.navPurchases,
      l10n.navCompanies,
      l10n.navReports,
      l10n.navUsers,
      l10n.navUnits,
      l10n.navFeedback,
      l10n.navSettings,
    ];
    return [
      for (var i = 0; i < _destinations.length; i++)
        ds.EpiNavItem(
          icon:  _destinations[i].$2,
          label: labels[i],
        ),
    ];
  }

  String _currentTitle(AppLocalizations l10n) {
    final idx = _selectedIndex();
    return _buildNavItems(l10n)[idx].label;
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return ds.AppShell(
      selectedIndex: _selectedIndex(),
      navItems:      _buildNavItems(l10n),
      onNavSelected: (i) => context.go(_destinations[i].$1),
      title:         _currentTitle(l10n),
      child:         child,
    );
  }
}
