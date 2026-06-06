import 'package:epi_design/epi_design.dart' as ds;
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:epi_admin/core/i18n/generated/app_localizations.dart';
import 'package:go_router/go_router.dart';
import '../bloc/auth_cubit.dart';
import '../bloc/auth_state.dart';
import '../router/routes.dart';

/// Shell oficial do EPI Controle.
/// Delega completamente ao AppShell do Design System (sidebar colapsável,
/// breadcrumbs, dark mode). Breakpoints unificados via EpiBreakpoints.
/// Itens de navegação são filtrados pela lista de permissões do usuário.
class AppShell extends StatelessWidget {
  const AppShell({super.key, required this.location, required this.child});

  final String location;
  final Widget child;

  // Destinos ordenados: (rota, ícone-inativo, ícone-ativo, permissão)
  static const _destinations = [
    (Routes.dashboard,  Icons.dashboard_outlined,          Icons.dashboard_rounded,          'dashboard:view'),
    (Routes.employees,  Icons.people_outline_rounded,      Icons.people_rounded,             'employees:view'),
    (Routes.epis,       Icons.shield_outlined,             Icons.shield_rounded,             'epis:view'),
    (Routes.deliveries, Icons.local_shipping_outlined,     Icons.local_shipping_rounded,     'deliveries:view'),
    (Routes.returns,    Icons.assignment_return_outlined,  Icons.assignment_return_rounded,  'deliveries:view'),
    (Routes.records,    Icons.folder_outlined,             Icons.folder_rounded,             'fichas:view'),
    (Routes.stock,      Icons.inventory_2_outlined,        Icons.inventory_2_rounded,        'stock:view'),
    (Routes.purchases,  Icons.shopping_cart_outlined,      Icons.shopping_cart_rounded,      'purchase_requests:view'),
    (Routes.companies,  Icons.business_outlined,           Icons.business_rounded,           'companies:view'),
    (Routes.reports,    Icons.bar_chart_outlined,          Icons.bar_chart_rounded,          'reports:view'),
    (Routes.users,      Icons.manage_accounts_outlined,    Icons.manage_accounts_rounded,    'users:view'),
    (Routes.units,      Icons.location_on_outlined,        Icons.location_on_rounded,        'units:view'),
    (Routes.feedback,   Icons.rate_review_outlined,        Icons.rate_review_rounded,        'epi_feedback:view'),
    (Routes.settings,   Icons.settings_outlined,           Icons.settings_rounded,           'settings:view'),
  ];

  List<String> _allLabels(AppLocalizations l10n) => [
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

  int _selectedIndex(List<String> permissions) {
    var idx = 0;
    for (var i = 0; i < _destinations.length; i++) {
      if (!permissions.contains(_destinations[i].$4)) continue;
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

  List<ds.EpiNavItem> _buildNavItems(
      AppLocalizations l10n, List<String> permissions) {
    final labels = _allLabels(l10n);
    return [
      for (var i = 0; i < _destinations.length; i++)
        if (permissions.contains(_destinations[i].$4))
          ds.EpiNavItem(
            icon:  _destinations[i].$2,
            label: labels[i],
          ),
    ];
  }

  String _currentTitle(AppLocalizations l10n, List<String> permissions) {
    final items = _buildNavItems(l10n, permissions);
    if (items.isEmpty) return '';
    final idx = _selectedIndex(permissions);
    return items[idx < items.length ? idx : 0].label;
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final authState = context.watch<AuthCubit>().state;
    final permissions = authState is AuthAuthenticated
        ? authState.permissions
        : const <String>[];

    final visibleRoutes = [
      for (final d in _destinations)
        if (permissions.contains(d.$4)) d.$1,
    ];

    return ds.AppShell(
      selectedIndex: _selectedIndex(permissions),
      navItems:      _buildNavItems(l10n, permissions),
      onNavSelected: (i) {
        if (i < visibleRoutes.length) context.go(visibleRoutes[i]);
      },
      title:  _currentTitle(l10n, permissions),
      child:  child,
    );
  }
}
