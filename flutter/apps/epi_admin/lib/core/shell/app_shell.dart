import 'package:flutter/material.dart';
import 'package:flutter_gen/gen_l10n/app_localizations.dart';
import 'package:go_router/go_router.dart';
import '../router/routes.dart';

class AppShell extends StatelessWidget {
  const AppShell({super.key, required this.location, required this.child});

  final String location;
  final Widget child;

  static const _destinations = [
    Routes.dashboard,
    Routes.employees,
    Routes.epis,
    Routes.deliveries,
    Routes.settings,
  ];

  int get _selectedIndex {
    for (var i = 0; i < _destinations.length; i++) {
      final dest = _destinations[i];
      if (dest == Routes.dashboard) {
        if (location == dest) return i;
      } else if (location.startsWith(dest)) {
        return i;
      }
    }
    return 0;
  }

  void _onDestinationSelected(BuildContext context, int index) {
    context.go(_destinations[index]);
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final idx = _selectedIndex;
    final destinations = [
      (Icons.dashboard_outlined, Icons.dashboard_rounded, l10n.navDashboard),
      (Icons.people_outline_rounded, Icons.people_rounded, l10n.navEmployees),
      (Icons.shield_outlined, Icons.shield_rounded, l10n.navEpis),
      (Icons.local_shipping_outlined, Icons.local_shipping_rounded, l10n.navDeliveries),
      (Icons.settings_outlined, Icons.settings_rounded, l10n.navSettings),
    ];

    return LayoutBuilder(
      builder: (context, constraints) {
        final isWide = constraints.maxWidth >= 600;
        if (isWide) {
          return Scaffold(
            body: Row(
              children: [
                NavigationRail(
                  selectedIndex: idx,
                  onDestinationSelected: (i) => _onDestinationSelected(context, i),
                  labelType: NavigationRailLabelType.selected,
                  destinations: [
                    for (final d in destinations)
                      NavigationRailDestination(
                        icon: Icon(d.$1),
                        selectedIcon: Icon(d.$2),
                        label: Text(d.$3),
                      ),
                  ],
                ),
                const VerticalDivider(width: 1),
                Expanded(child: child),
              ],
            ),
          );
        }
        return Scaffold(
          body: child,
          bottomNavigationBar: NavigationBar(
            selectedIndex: idx,
            onDestinationSelected: (i) => _onDestinationSelected(context, i),
            destinations: [
              for (final d in destinations)
                NavigationDestination(
                  icon: Icon(d.$1),
                  selectedIcon: Icon(d.$2),
                  label: d.$3,
                ),
            ],
          ),
        );
      },
    );
  }
}
