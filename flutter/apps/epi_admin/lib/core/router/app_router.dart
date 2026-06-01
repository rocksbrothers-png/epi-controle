import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

// Rotas da aplicação — nomes como constantes para evitar typos
abstract final class Routes {
  static const login      = '/login';
  static const dashboard  = '/';
  static const employees  = '/employees';
  static const employeeDetail = '/employees/:id';
  static const epis       = '/epis';
  static const stock      = '/stock';
  static const deliveries = '/deliveries';
  static const deliveryNew= '/deliveries/new';
  static const returns    = '/returns';
  static const records    = '/records';
  static const purchases  = '/purchases';
  static const reports    = '/reports';
  static const settings   = '/settings';
  static const companies  = '/companies';
  static const users      = '/users';
  static const units      = '/units';
  static const portal     = '/portal';
}

GoRouter buildRouter({required ValueNotifier<bool> isAuthenticated}) {
  return GoRouter(
    initialLocation: Routes.login,
    refreshListenable: isAuthenticated,
    redirect: (context, state) {
      final isLoggedIn = isAuthenticated.value;
      final isOnLogin  = state.matchedLocation == Routes.login;
      if (!isLoggedIn && !isOnLogin) return Routes.login;
      if (isLoggedIn  &&  isOnLogin) return Routes.dashboard;
      return null;
    },
    routes: [
      GoRoute(
        path: Routes.login,
        name: 'login',
        builder: (ctx, state) => const _PlaceholderScreen(label: 'Login'),
      ),
      ShellRoute(
        builder: (ctx, state, child) => _AppShellWrapper(child: child),
        routes: [
          GoRoute(path: Routes.dashboard,  builder: (c, s) => const _PlaceholderScreen(label: 'Dashboard')),
          GoRoute(path: Routes.employees,  builder: (c, s) => const _PlaceholderScreen(label: 'Colaboradores')),
          GoRoute(path: Routes.epis,       builder: (c, s) => const _PlaceholderScreen(label: 'EPIs')),
          GoRoute(path: Routes.stock,      builder: (c, s) => const _PlaceholderScreen(label: 'Estoque')),
          GoRoute(path: Routes.deliveries, builder: (c, s) => const _PlaceholderScreen(label: 'Entregas')),
          GoRoute(path: Routes.returns,    builder: (c, s) => const _PlaceholderScreen(label: 'Devoluções')),
          GoRoute(path: Routes.records,    builder: (c, s) => const _PlaceholderScreen(label: 'Fichas')),
          GoRoute(path: Routes.purchases,  builder: (c, s) => const _PlaceholderScreen(label: 'Compras')),
          GoRoute(path: Routes.reports,    builder: (c, s) => const _PlaceholderScreen(label: 'Relatórios')),
          GoRoute(path: Routes.settings,   builder: (c, s) => const _PlaceholderScreen(label: 'Configurações')),
          GoRoute(path: Routes.companies,  builder: (c, s) => const _PlaceholderScreen(label: 'Empresas')),
          GoRoute(path: Routes.users,      builder: (c, s) => const _PlaceholderScreen(label: 'Usuários')),
          GoRoute(path: Routes.units,      builder: (c, s) => const _PlaceholderScreen(label: 'Unidades')),
        ],
      ),
    ],
  );
}

// Placeholder — substituído em cada sprint pelo widget real
class _PlaceholderScreen extends StatelessWidget {
  const _PlaceholderScreen({required this.label});
  final String label;

  @override
  Widget build(BuildContext context) => Scaffold(
    body: Center(child: Text(label, style: Theme.of(context).textTheme.headlineLarge)),
  );
}

class _AppShellWrapper extends StatelessWidget {
  const _AppShellWrapper({required this.child});
  final Widget child;

  @override
  Widget build(BuildContext context) => child; // Shell real implementado no Sprint 1
}
