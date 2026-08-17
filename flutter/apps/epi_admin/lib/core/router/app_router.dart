import 'package:epi_api/epi_api.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../../features/auth/login_screen.dart';
import '../../features/auth/change_password_screen.dart';
import '../../features/companies/companies_screen.dart';
import '../../features/dashboard/dashboard_screen.dart';
import '../../features/deliveries/deliveries_screen.dart';
import '../../features/employees/employees_screen.dart';
import '../../features/employees/employee_detail_screen.dart';
import '../../features/epis/epis_screen.dart';
import '../../features/epis/epi_detail_screen.dart';
import '../../features/purchases/purchases_screen.dart';
import '../../features/records/records_screen.dart';
import '../../features/reports/reports_screen.dart';
import '../../features/portal/portal_screen.dart';
import '../../features/returns/returns_screen.dart';
import '../../features/settings/settings_screen.dart';
import '../../features/settings/my_company_screen.dart';
import '../../features/subscription/subscription_screen.dart';
import '../../features/subscription/invoices_screen.dart';
import '../../features/stock/stock_screen.dart';
import '../../features/qr/qr_scanner_screen.dart';
import '../../features/deliveries/handover_conference_screen.dart';
import '../../features/users/users_screen.dart';
import '../../features/units/units_screen.dart';
import '../../features/legal_entities/legal_entities_screen.dart';
import '../../features/outsourced_companies/outsourced_companies_screen.dart';
import '../../features/feedback/feedback_screen.dart';
import '../i18n/locale_provider.dart';
import '../i18n/theme_mode_notifier.dart';
import '../shell/app_shell.dart';
import 'navigation_policy.dart';
import 'route_permissions.dart';
import 'routes.dart';

export 'routes.dart';

// Feature flag: set USAR_FLUTTER_LOGIN=true via --dart-define to enable.
const _kUsarFlutterLogin =
    bool.fromEnvironment('USAR_FLUTTER_LOGIN', defaultValue: true);

GoRouter buildRouter({
  required ValueNotifier<bool> isAuthenticated,
  required ValueNotifier<List<String>> permissions,
  required ValueNotifier<Map<String, bool>> moduleVisibility,
  required ValueNotifier<bool> mustChangePassword,
  required LocaleProvider localeProvider,
  required ThemeModeNotifier themeNotifier,
}) {
  return GoRouter(
    initialLocation: Routes.login,
    refreshListenable: Listenable.merge(
        [isAuthenticated, permissions, moduleVisibility, mustChangePassword]),
    redirect: (context, state) {
      if (!_kUsarFlutterLogin) return null;
      final isLoggedIn = isAuthenticated.value;
      final isOnLogin = state.matchedLocation == Routes.login;
      final isPublicRoute = publicRoutes.contains(state.matchedLocation);
      if (!isLoggedIn && !isOnLogin && !isPublicRoute) return Routes.login;
      if (isLoggedIn && isOnLogin) return Routes.dashboard;
      // Gate de senha temporária: enquanto a troca é obrigatória, prende o
      // usuário na tela de troca e bloqueia qualquer outra rota privada.
      if (isLoggedIn && mustChangePassword.value) {
        return state.matchedLocation == Routes.changePassword
            ? null
            : Routes.changePassword;
      }
      // Já trocou (ou não precisa): não deixa ficar preso na tela de troca.
      if (isLoggedIn &&
          !mustChangePassword.value &&
          state.matchedLocation == Routes.changePassword) {
        return Routes.dashboard;
      }
      // Permission guard: redirect to dashboard when the user lacks the
      // required permission for this route. Empty permissions never unlock
      // private screens; this prevents a transient permissive state during
      // session hydration.
      if (isLoggedIn) {
        if (!hasRoutePermission(state.matchedLocation, permissions.value)) {
          return Routes.dashboard;
        }
        // Camada de visibilidade estrutural (menu/rotas/deep links): a
        // configuração do Administrador Geral pode desligar um módulo para
        // o perfil mesmo quando a permissão técnica acima libera — cobre
        // navegação direta por URL/deep link, não só o menu.
        if (!isModuleLocationAccessible(
          state.matchedLocation,
          moduleVisibility.value,
        )) {
          return Routes.dashboard;
        }
      }
      return null;
    },
    routes: [
      GoRoute(
        path: Routes.login,
        name: 'login',
        builder: (ctx, state) => const LoginScreen(),
      ),
      GoRoute(
        path: Routes.changePassword,
        name: 'changePassword',
        builder: (ctx, state) => const ChangePasswordScreen(),
      ),
      GoRoute(
        path: Routes.qr,
        name: 'qr',
        builder: (ctx, state) => const QrScannerScreen(),
      ),
      GoRoute(
        path: Routes.handover,
        name: 'handover',
        builder: (ctx, state) => const HandoverConferenceScreen(),
      ),
      GoRoute(
        path: Routes.portal,
        name: 'portal',
        builder: (ctx, state) => const PortalScreen(),
      ),
      ShellRoute(
        builder: (ctx, state, child) => AppShell(
          location: state.matchedLocation,
          child: child,
        ),
        routes: [
          GoRoute(
            path: Routes.dashboard,
            builder: (c, s) => DashboardScreen(localeProvider: localeProvider),
          ),
          GoRoute(
            path: Routes.employees,
            builder: (c, s) => const EmployeesScreen(),
          ),
          GoRoute(
            path: Routes.employeeDetail,
            builder: (c, s) => EmployeeDetailScreen(
              employee: s.extra as Employee,
            ),
          ),
          GoRoute(
            path: Routes.epis,
            builder: (c, s) => const EpisScreen(),
          ),
          GoRoute(
            path: Routes.epiDetail,
            builder: (c, s) => EpiDetailScreen(epi: s.extra as Epi),
          ),
          GoRoute(
            path: Routes.stock,
            builder: (c, s) => const StockScreen(),
          ),
          GoRoute(
            path: Routes.deliveries,
            builder: (c, s) => const DeliveriesScreen(),
          ),
          GoRoute(
            path: Routes.returns,
            builder: (c, s) => const ReturnsScreen(),
          ),
          GoRoute(
            path: Routes.records,
            builder: (c, s) => const RecordsScreen(),
          ),
          GoRoute(
            path: Routes.purchases,
            builder: (c, s) => const PurchasesScreen(),
          ),
          GoRoute(
            path: Routes.reports,
            builder: (c, s) => const ReportsScreen(),
          ),
          GoRoute(
            path: Routes.settings,
            builder: (c, s) => SettingsScreen(
              localeProvider: localeProvider,
              themeNotifier: themeNotifier,
            ),
          ),
          GoRoute(
            path: Routes.companies,
            builder: (c, s) => const CompaniesScreen(),
          ),
          GoRoute(
            path: Routes.myCompany,
            builder: (c, s) => const MyCompanyScreen(),
          ),
          GoRoute(
            path: Routes.users,
            builder: (c, s) => const UsersScreen(),
          ),
          GoRoute(
            path: Routes.units,
            builder: (c, s) => const UnitsScreen(),
          ),
          GoRoute(
            path: Routes.legalEntities,
            // `?company_id=` recorta a tela num cliente — caminho do Admin
            // Master a partir da lista de empresas. Ausente, a tela usa a
            // empresa do próprio usuário, como sempre.
            builder: (c, s) => LegalEntitiesScreen(
              companyId: int.tryParse(
                s.uri.queryParameters['company_id'] ?? '',
              ),
              companyName: s.uri.queryParameters['company_name'],
            ),
          ),
          GoRoute(
            path: Routes.outsourcedCompanies,
            builder: (c, s) => const OutsourcedCompaniesScreen(),
          ),
          GoRoute(
            path: Routes.feedback,
            builder: (c, s) => const FeedbackScreen(),
          ),
          GoRoute(
            path: Routes.subscription,
            builder: (c, s) => const SubscriptionScreen(),
          ),
          GoRoute(
            path: Routes.invoices,
            builder: (c, s) => const InvoicesScreen(),
          ),
        ],
      ),
    ],
  );
}
