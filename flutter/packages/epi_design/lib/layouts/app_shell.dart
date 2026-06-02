/// Shell de aplicação responsivo: sidebar em desktop, drawer em mobile.
import 'package:flutter/material.dart';
import '../tokens/colors.dart';
import '../tokens/spacing.dart';
import '../components/organisms/epi_sidebar.dart';
import '../components/organisms/epi_app_bar.dart';

class AppShell extends StatefulWidget {
  const AppShell({
    super.key,
    required this.child,
    required this.selectedIndex,
    required this.navItems,
    required this.onNavSelected,
    this.title           = '',
    this.actions,
    this.breadcrumbs     = const [],
    this.showBreadcrumb  = false,
  });

  final Widget            child;
  final int               selectedIndex;
  final List<EpiNavItem>  navItems;
  final ValueChanged<int> onNavSelected;
  final String            title;
  final List<Widget>?     actions;
  final List<String>      breadcrumbs;
  final bool              showBreadcrumb;

  static const double _mobileBreakpoint = 768;

  @override
  State<AppShell> createState() => _AppShellState();
}

class _AppShellState extends State<AppShell> {
  bool _collapsed = false;

  @override
  Widget build(BuildContext context) {
    final isDark    = Theme.of(context).brightness == Brightness.dark;
    final bgColor   = isDark ? EpiColors.darkBackground : EpiColors.background;

    return LayoutBuilder(
      builder: (context, constraints) {
        final isDesktop = constraints.maxWidth >= AppShell._mobileBreakpoint;

        if (isDesktop) {
          return Scaffold(
            backgroundColor: bgColor,
            body: Row(
              children: [
                EpiSidebar(
                  items: widget.navItems,
                  selectedIndex: widget.selectedIndex,
                  onItemSelected: widget.onNavSelected,
                  collapsed: _collapsed,
                  onCollapse: () => setState(() => _collapsed = !_collapsed),
                ),
                Expanded(
                  child: Column(
                    children: [
                      EpiAppBar(
                        title: widget.title,
                        actions: widget.actions,
                        showBreadcrumb: widget.showBreadcrumb,
                        breadcrumbs: widget.breadcrumbs,
                      ),
                      Expanded(child: widget.child),
                    ],
                  ),
                ),
              ],
            ),
          );
        }

        // Mobile layout
        return Scaffold(
          backgroundColor: bgColor,
          appBar: EpiAppBar(
            title: widget.title,
            actions: widget.actions,
            showBreadcrumb: widget.showBreadcrumb,
            breadcrumbs: widget.breadcrumbs,
            leading: Builder(
              builder: (ctx) => IconButton(
                icon: const Icon(Icons.menu_rounded),
                onPressed: () => Scaffold.of(ctx).openDrawer(),
                color: EpiColors.textPrimary,
              ),
            ),
          ),
          drawer: Drawer(
            child: EpiSidebar(
              items: widget.navItems,
              selectedIndex: widget.selectedIndex,
              onItemSelected: (i) {
                Navigator.of(context).pop();
                widget.onNavSelected(i);
              },
            ),
          ),
          body: widget.child,
        );
      },
    );
  }
}
