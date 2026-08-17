import 'package:epi_admin/core/router/route_permissions.dart';
import 'package:epi_admin/core/router/routes.dart';
import 'package:flutter_test/flutter_test.dart';

/// Testes da matriz RBAC de rotas (Sprint 3 do plano de migração).
///
/// Travam o mapa rota → permissão (que precisa casar com `core/permissions.py`
/// do backend) e a resolução de subrotas. Uma rota gateada que perca sua
/// permissão passaria a ficar acessível indevidamente — aqui isso falha o CI.
void main() {
  group('requiredPermissionFor', () {
    test('cada rota gateada resolve para a permissão esperada', () {
      const expected = <String, String>{
        Routes.employees: 'employees:view',
        Routes.epis: 'epis:view',
        Routes.deliveries: 'deliveries:view',
        Routes.handover: 'deliveries:view',
        Routes.returns: 'deliveries:view',
        Routes.records: 'fichas:view',
        Routes.stock: 'stock:view',
        Routes.purchases: 'purchase_requests:view',
        Routes.companies: 'companies:view',
        Routes.reports: 'reports:view',
        Routes.users: 'users:view',
        Routes.units: 'units:view',
        Routes.feedback: 'epi_feedback:view',
        Routes.settings: 'settings:view',
        Routes.myCompany: 'company_settings:view',
      };
      expected.forEach((route, perm) {
        expect(requiredPermissionFor(route), perm, reason: 'rota $route');
      });
    });

    test('resolve subrotas (detalhe) para a mesma permissão da raiz', () {
      expect(requiredPermissionFor('/epis/123'), 'epis:view');
      expect(requiredPermissionFor('/employees/9'), 'employees:view');
    });

    test('dashboard (/) não exige permissão (evita loop do redirect guard)', () {
      expect(requiredPermissionFor(Routes.dashboard), isNull);
    });

    test('rotas públicas não exigem permissão de tela', () {
      expect(requiredPermissionFor(Routes.login), isNull);
      expect(requiredPermissionFor(Routes.qr), isNull);
      expect(requiredPermissionFor(Routes.portal), isNull);
    });

    test('rotas públicas são explicitamente liberadas pelo redirect guard', () {
      expect(publicRoutes, containsAll({Routes.login, Routes.qr, Routes.portal}));
      expect(publicRoutes, isNot(contains(Routes.dashboard)));
    });
  });

  group('rota de CNPJs (Multi-CNPJ)', () {
    test('/legal-entities exige legal_entities:view', () {
      // Sem o gate, qualquer usuário autenticado abriria a tela de CNPJs e só
      // tomaria 403 do backend — tela carregada e chamada falhando.
      expect(requiredPermissionFor(Routes.legalEntities), 'legal_entities:view');
    });

    test('subrota de CNPJ herda a mesma permissão', () {
      expect(requiredPermissionFor('${Routes.legalEntities}/7'), 'legal_entities:view');
    });

    test('rota de CNPJs não colide com o prefixo de outra rota gateada', () {
      // `startsWith` casaria errado se alguma rota anterior fosse prefixo desta.
      expect(requiredPermissionFor(Routes.legalEntities), isNot('units:view'));
    });
  });

  group('routePermissions (cobertura do mapa)', () {
    test('cobre exatamente as rotas gateadas esperadas', () {
      expect(
        routePermissions.keys.toSet(),
        {
          Routes.dashboard,
          Routes.employees,
          Routes.epis,
          Routes.deliveries,
          Routes.handover,
          Routes.returns,
          Routes.records,
          Routes.stock,
          Routes.purchases,
          Routes.companies,
          Routes.reports,
          Routes.users,
          Routes.units,
          Routes.legalEntities,
          Routes.outsourcedCompanies,
          Routes.feedback,
          Routes.settings,
          Routes.myCompany,
          Routes.subscription,
          Routes.invoices,
        },
      );
    });

    test('todas as permissões usam o formato `recurso:ação`', () {
      for (final perm in routePermissions.values) {
        expect(perm, matches(RegExp(r'^[a-z_]+:[a-z_]+$')), reason: perm);
      }
    });
  });

  group('lógica do gate (permissões do usuário × rota)', () {
    /// Espelha o redirect guard: a rota é navegável se não exige permissão
    /// ou se o usuário a possui.
    bool canNavigate(String location, Set<String> perms) {
      final required = requiredPermissionFor(location);
      return required == null || perms.contains(required);
    }

    test('usuário sem a permissão é barrado da rota gateada', () {
      const perms = {'dashboard:view', 'deliveries:view'};
      expect(canNavigate(Routes.users, perms), isFalse);
      expect(canNavigate(Routes.companies, perms), isFalse);
    });

    test('usuário com a permissão acessa a rota', () {
      const perms = {'deliveries:view', 'stock:view'};
      expect(canNavigate(Routes.deliveries, perms), isTrue);
      expect(canNavigate(Routes.returns, perms), isTrue); // mesma perm de deliveries
      expect(canNavigate(Routes.stock, perms), isTrue);
    });

    test('dashboard e rotas públicas são sempre navegáveis', () {
      const perms = <String>{};
      expect(canNavigate(Routes.dashboard, perms), isTrue);
      expect(canNavigate(Routes.login, perms), isTrue);
      expect(canNavigate(Routes.portal, perms), isTrue);
    });
  });

  group('hasRoutePermission / routePermissionAlternatives (ADR-0002 §10)', () {
    test('a permissão primária libera a rota', () {
      expect(hasRoutePermission(Routes.outsourcedCompanies, const ['employees:create']), isTrue);
    });

    test('a permissão alternativa (Cadastro de Colaboradores) também libera a rota', () {
      // admin/user têm só employees:create_simplified, nunca employees:create.
      expect(
        hasRoutePermission(Routes.outsourcedCompanies, const ['employees:create_simplified']),
        isTrue,
      );
    });

    test('sem nenhuma das duas, a rota fica bloqueada', () {
      expect(hasRoutePermission(Routes.outsourcedCompanies, const ['employees:view']), isFalse);
    });

    test('routePermissionAlternatives só cobre a rota de Terceirizados e Prestadores', () {
      expect(routePermissionAlternatives.keys, [Routes.outsourcedCompanies]);
      expect(routePermissionAlternatives[Routes.outsourcedCompanies], 'employees:create_simplified');
    });

    test('rota sem permissão exigida é sempre navegável, alternativa ou não', () {
      expect(hasRoutePermission(Routes.dashboard, const []), isTrue);
    });
  });
}
