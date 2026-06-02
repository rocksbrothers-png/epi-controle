import 'package:flutter/material.dart';
import 'package:flutter_gen/gen_l10n/app_localizations.dart';
import 'package:go_router/go_router.dart';
import '../router/routes.dart';

class AppShell extends StatelessWidget {
  const AppShell({super.key, required this.location, required this.child});

  final String location;
  final Widget child;

  // Bottom nav bar destinations (mobile, max 5)
  static const _bottomDestinations = [
    Routes.dashboard,
    Routes.employees,
    Routes.epis,
    Routes.deliveries,
    Routes.settings,
  ];

  // All destinations for desktop rail + drawer (in grouped order)
  // Group 1: [dashboard]
  // Group 2: [employees, epis, deliveries, returns, records]
  // Group 3: [stock, purchases, companies]
  // Group 4: [reports, users, units]
  // Group 5: [settings]
  static const _allDestinations = [
    Routes.dashboard,
    Routes.employees,
    Routes.epis,
    Routes.deliveries,
    Routes.returns,
    Routes.records,
    Routes.stock,
    Routes.purchases,
    Routes.companies,
    Routes.reports,
    Routes.users,
    Routes.units,
    Routes.settings,
  ];

  int _selectedBottomIndex() {
    for (var i = 0; i < _bottomDestinations.length; i++) {
      final dest = _bottomDestinations[i];
      if (dest == Routes.dashboard) {
        if (location == dest) return i;
      } else if (location.startsWith(dest)) {
        return i;
      }
    }
    return 0;
  }

  int _selectedRailIndex() {
    for (var i = 0; i < _allDestinations.length; i++) {
      final dest = _allDestinations[i];
      if (dest == Routes.dashboard) {
        if (location == dest) return i;
      } else if (location.startsWith(dest)) {
        return i;
      }
    }
    return 0;
  }

  void _navigate(BuildContext context, String route) {
    context.go(route);
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);

    // Labels and icons for each destination in _allDestinations order
    final allLabels = [
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
      l10n.navSettings,
    ];

    const allIcons = [
      (Icons.dashboard_outlined, Icons.dashboard_rounded),
      (Icons.people_outline_rounded, Icons.people_rounded),
      (Icons.shield_outlined, Icons.shield_rounded),
      (Icons.local_shipping_outlined, Icons.local_shipping_rounded),
      (Icons.assignment_return_outlined, Icons.assignment_return_rounded),
      (Icons.folder_outlined, Icons.folder_rounded),
      (Icons.inventory_2_outlined, Icons.inventory_2_rounded),
      (Icons.shopping_cart_outlined, Icons.shopping_cart_rounded),
      (Icons.business_outlined, Icons.business_rounded),
      (Icons.bar_chart_outlined, Icons.bar_chart_rounded),
      (Icons.manage_accounts_outlined, Icons.manage_accounts_rounded),
      (Icons.location_on_outlined, Icons.location_on_rounded),
      (Icons.settings_outlined, Icons.settings_rounded),
    ];

    // Bottom bar labels and icons (matching _bottomDestinations order)
    final bottomLabels = [
      l10n.navDashboard,
      l10n.navEmployees,
      l10n.navEpis,
      l10n.navDeliveries,
      l10n.navSettings,
    ];

    const bottomIcons = [
      (Icons.dashboard_outlined, Icons.dashboard_rounded),
      (Icons.people_outline_rounded, Icons.people_rounded),
      (Icons.shield_outlined, Icons.shield_rounded),
      (Icons.local_shipping_outlined, Icons.local_shipping_rounded),
      (Icons.settings_outlined, Icons.settings_rounded),
    ];

    return LayoutBuilder(
      builder: (context, constraints) {
        final isWide = constraints.maxWidth >= 600;

        if (isWide) {
          return Scaffold(
            body: Row(
              children: [
                NavigationRail(
                  selectedIndex: _selectedRailIndex(),
                  onDestinationSelected: (i) =>
                      _navigate(context, _allDestinations[i]),
                  labelType: NavigationRailLabelType.all,
                  destinations: [
                    for (var i = 0; i < _allDestinations.length; i++)
                      NavigationRailDestination(
                        icon: Icon(allIcons[i].$1),
                        selectedIcon: Icon(allIcons[i].$2),
                        label: Text(allLabels[i]),
                      ),
                  ],
                ),
                const VerticalDivider(width: 1),
                Expanded(child: child),
              ],
            ),
          );
        }

        // Mobile layout: bottom bar (5 items) + drawer for the rest
        final drawerDestinations = _allDestinations
            .where((d) => !_bottomDestinations.contains(d))
            .toList();

        return Scaffold(
          drawer: Drawer(
            child: SafeArea(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Padding(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 16,
                      vertical: 12,
                    ),
                    child: Text(
                      l10n.appName,
                      style: Theme.of(context).textTheme.titleMedium?.copyWith(
                            fontWeight: FontWeight.w700,
                          ),
                    ),
                  ),
                  const Divider(height: 1),
                  Expanded(
                    child: ListView(
                      padding: const EdgeInsets.symmetric(vertical: 8),
                      children: [
                        for (final dest in drawerDestinations)
                          _buildDrawerItem(
                            context,
                            dest: dest,
                            allIcons: allIcons,
                            allLabels: allLabels,
                          ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ),
          body: child,
          bottomNavigationBar: NavigationBar(
            selectedIndex: _selectedBottomIndex(),
            onDestinationSelected: (i) =>
                _navigate(context, _bottomDestinations[i]),
            destinations: [
              for (var i = 0; i < _bottomDestinations.length; i++)
                NavigationDestination(
                  icon: Icon(bottomIcons[i].$1),
                  selectedIcon: Icon(bottomIcons[i].$2),
                  label: bottomLabels[i],
                ),
            ],
          ),
        );
      },
    );
  }

  Widget _buildDrawerItem(
    BuildContext context, {
    required String dest,
    required List<(IconData, IconData)> allIcons,
    required List<String> allLabels,
  }) {
    final idx = _allDestinations.indexOf(dest);
    if (idx < 0) return const SizedBox.shrink();
    final isSelected = location == dest ||
        (dest != Routes.dashboard && location.startsWith(dest));
    return ListTile(
      leading: Icon(
        isSelected ? allIcons[idx].$2 : allIcons[idx].$1,
        color: isSelected ? Theme.of(context).colorScheme.primary : null,
      ),
      title: Text(allLabels[idx]),
      selected: isSelected,
      onTap: () {
        Navigator.of(context).pop(); // close drawer
        context.go(dest);
      },
    );
  }
}
