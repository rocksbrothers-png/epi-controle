import 'package:epi_admin/core/router/navigation_policy.dart';
import 'package:epi_admin/core/router/routes.dart';
import 'package:flutter_test/flutter_test.dart';

/// Testes da política de visibilidade estrutural por módulo (Configuração →
/// Regras → Visualização, personalização pelo Administrador Geral).
///
/// Espelha `MODULE_REQUIRED_PERMISSIONS`/`routeModules` do backend
/// (`epi_backend/rule_engine.py`) — uma rota nova coberta por um módulo
/// precisa entrar aqui e lá, senão um lado libera o que o outro nega.
void main() {
  group('requiredModuleFor', () {
    test('cada rota coberta resolve para o módulo esperado', () {
      const expected = <String, String>{
        Routes.purchases: 'compras',
        Routes.stock: 'estoque',
        Routes.deliveries: 'entregas',
        Routes.returns: 'entregas',
        Routes.records: 'fichas',
        Routes.reports: 'relatorios',
        Routes.companies: 'administracao',
        Routes.users: 'administracao',
        Routes.legalEntities: 'administracao',
        Routes.outsourcedCompanies: 'terceirizados',
        Routes.settings: 'configuracoes',
        Routes.subscription: 'configuracoes',
        Routes.invoices: 'configuracoes',
      };
      expected.forEach((route, module) {
        expect(requiredModuleFor(route), module, reason: 'rota $route');
      });
    });

    test('resolve subrotas para o mesmo módulo da raiz', () {
      expect(requiredModuleFor('/purchases/123'), 'compras');
      expect(requiredModuleFor('/stock/9'), 'estoque');
    });

    test('dashboard (/) não exige módulo (evita loop do redirect guard)', () {
      expect(requiredModuleFor(Routes.dashboard), isNull);
    });

    test('rota não coberta pela camada de módulos devolve null (sem regressão)', () {
      // Employees/EPIs/Units/Feedback continuam gateados só pela permissão
      // técnica — não fazem parte da configuração do Administrador Geral.
      expect(requiredModuleFor(Routes.employees), isNull);
      expect(requiredModuleFor(Routes.epis), isNull);
      expect(requiredModuleFor(Routes.units), isNull);
      expect(requiredModuleFor(Routes.feedback), isNull);
    });
  });

  group('isModuleLocationAccessible', () {
    test('módulo desligado bloqueia a rota mesmo com permissão técnica', () {
      expect(
        isModuleLocationAccessible(Routes.stock, const {'estoque': false}),
        isFalse,
      );
    });

    test('módulo ligado libera a rota', () {
      expect(
        isModuleLocationAccessible(Routes.stock, const {'estoque': true}),
        isTrue,
      );
    });

    test('rota fora do mapa de módulos nunca é bloqueada por esta camada', () {
      expect(isModuleLocationAccessible(Routes.employees, const {}), isTrue);
    });

    test('módulo ausente do mapa (resposta antiga/degradada) é tratado como visível', () {
      // Fail-open de propósito: quem protege de verdade é a permissão
      // técnica (já aplicada antes desta checagem no redirect guard).
      expect(isModuleLocationAccessible(Routes.purchases, const {}), isTrue);
    });

    test('dashboard nunca é bloqueado por esta camada', () {
      expect(
        isModuleLocationAccessible(Routes.dashboard, const {'dashboard': false}),
        isTrue,
      );
    });

    test('terceirizados (opt-in, ADR-0002) fica oculto quando desligado, mesmo com permissão técnica', () {
      // Os dois módulos opt-in da tela (Empresas e Cadastro de
      // Colaboradores) precisam estar explicitamente desligados — só
      // "terceirizados": false não basta mais desde que a tela ganhou a
      // segunda aba (ver `routeModuleAlternatives`).
      expect(
        isModuleLocationAccessible(
          Routes.outsourcedCompanies,
          const {'terceirizados': false, 'terceirizados_colaboradores': false},
        ),
        isFalse,
      );
    });

    test('terceirizados aparece assim que o Administrador Geral liga o módulo', () {
      expect(
        isModuleLocationAccessible(
          Routes.outsourcedCompanies,
          const {'terceirizados': true, 'terceirizados_colaboradores': false},
        ),
        isTrue,
      );
    });

    test('terceirizados_colaboradores (módulo alternativo, ADR-0002 §10) também libera a tela', () {
      // admin/user só têm employees:create_simplified — sem esta camada,
      // ligar só o Cadastro de Colaboradores nunca abriria a rota.
      expect(
        isModuleLocationAccessible(
          Routes.outsourcedCompanies,
          const {'terceirizados': false, 'terceirizados_colaboradores': true},
        ),
        isTrue,
      );
    });
  });

  group('routeModuleAlternatives', () {
    test('só cobre a rota de Terceirizados e Prestadores', () {
      expect(routeModuleAlternatives.keys, [Routes.outsourcedCompanies]);
      expect(routeModuleAlternatives[Routes.outsourcedCompanies], 'terceirizados_colaboradores');
    });
  });
}
