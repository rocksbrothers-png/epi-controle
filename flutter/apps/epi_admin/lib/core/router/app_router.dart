import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../../features/auth/login_screen.dart';
import '../../features/dashboard/dashboard_screen.dart';
import '../shell/app_shell.dart';
import 'routes.dart';

export 'routes.dart';

// Feature flag: set USAR_FLUTTER_LOGIN=true via --dart-define to enable.
const _kUsarFlutterLogin =
    bool.fromEnvironment('USAR_FLUTTER_LOGIN', defaultValue: true);

GoRouter buildRouter({required ValueNotifier<bool> isAuthenticated}) {
  return GoRouter(
    initialLocation: Routes.login,
    refreshListenable: isAuthenticated,
    redirect: (context, state) {
      if (!_kUsarFlutterLogin) return null;
      final isLoggedIn = isAuthenticated.value;
      final isOnLogin = state.matchedLocation == Routes.login;
      if (!isLoggedIn && !isOnLogin) return Routes.login;
      if (isLoggedIn && isOnLogin) return Routes.dashboard;
      return null;
    },
    routes: [
      GoRoute(
        path: Routes.login,
        name: 'login',
        builder: (ctx, state) => const LoginScreen(),
      ),
      ShellRoute(
        builder: (ctx, state, child) => AppShell(
          location: state.matchedLocation,
          child: child,
        ),
        routes: [
          GoRoute(
            path: Routes.dashboard,
            builder: (c, s) => const DashboardScreen(),
          ),
          GoRoute(
            path: Routes.employees,
            builder: (c, s) => const _PlaceholderScreen(label: 'Colaboradores'),
          ),
          GoRoute(
            path: Routes.epis,
            builder: (c, s) => const _PlaceholderScreen(label: 'EPIs'),
          ),
          GoRoute(
            path: Routes.stock,
            builder: (c, s) => const _PlaceholderScreen(label: 'Estoque'),
          ),
          GoRoute(
            path: Routes.deliveries,
            builder: (c, s) => const _PlaceholderScreen(label: 'Entregas'),
          ),
          GoRoute(
            path: Routes.returns,
            builder: (c, s) => const _PlaceholderScreen(label: 'Devoluções'),
          ),
          GoRoute(
            path: Routes.records,
            builder: (c, s) => const _PlaceholderScreen(label: 'Fichas'),
          ),
          GoRoute(
            path: Routes.purchases,
            builder: (c, s) => const _PlaceholderScreen(label: 'Compras'),
          ),
          GoRoute(
            path: Routes.reports,
            builder: (c, s) => const _PlaceholderScreen(label: 'Relatórios'),
          ),
          GoRoute(
            path: Routes.settings,
            builder: (c, s) => const _PlaceholderScreen(label: 'Configurações'),
          ),
          GoRoute(
            path: Routes.companies,
            builder: (c, s) => const _PlaceholderScreen(label: 'Empresas'),
          ),
          GoRoute(
            path: Routes.users,
            builder: (c, s) => const _PlaceholderScreen(label: 'Usuários'),
          ),
          GoRoute(
            path: Routes.units,
            builder: (c, s) => const _PlaceholderScreen(label: 'Unidades'),
          ),
        ],
      ),
    ],
  );
}

class _PlaceholderScreen extends StatelessWidget {
  const _PlaceholderScreen({required this.label});
  final String label;

  @override
  Widget build(BuildContext context) => Scaffold(
        body: Center(
          child: Text(
            label,
            style: Theme.of(context).textTheme.headlineLarge,
          ),
        ),
      );
}
