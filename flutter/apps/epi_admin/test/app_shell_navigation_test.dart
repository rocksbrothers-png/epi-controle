import 'package:epi_admin/core/router/route_permissions.dart';
import 'package:epi_admin/core/router/routes.dart';
import 'package:epi_admin/core/shell/app_shell.dart';
import 'package:flutter_test/flutter_test.dart';

/// Toda tela gateada precisa de um caminho de navegação.
///
/// Estes testes existem por causa de um defeito real: a tela de CNPJs foi
/// construída, a rota registrada e a permissão criada — mas o item de menu
/// nunca foi adicionado. A funcionalidade só era alcançável digitando a URL,
/// e por várias versões ninguém conseguiu usá-la.
///
/// O teste de cobertura de permissões não pegou isso: ele comparava o mapa de
/// permissões com uma lista esperada, e a rota estava ausente **dos dois**
/// lados. Faltava justamente confrontar a navegação com as rotas.
void main() {
  group('menu × rotas gateadas', () {
    /// Rotas gateadas que **não** ficam no menu lateral de propósito, com o
    /// caminho real de acesso anotado. A lista é fechada: uma rota nova que
    /// não esteja aqui nem no menu faz o teste falhar, que é o ponto.
    ///
    /// Verifiquei cada uma no código antes de isentar — não são exceções de
    /// conveniência.
    const reachableElsewhere = <String, String>{
      '/my-company': 'settings_screen.dart → context.push(Routes.myCompany)',
      '/subscription': 'settings_screen.dart → context.push(Routes.subscription)',
      '/invoices': 'settings_screen.dart → context.push(Routes.invoices)',
      '/deliveries/handover':
          'deliveries_screen.dart → context.push(Routes.handover)',
      // Configuração por Unidade + EPI (#271-B2-a). Fora do menu de propósito:
      // é um detour a partir de Controle de Estoque, com o par já no contexto,
      // e não um destino de primeiro nível. Dois pontos de partida, ambos em
      // stock_screen.dart e ambos gateados por `stock:adjust`: a ação da AppBar
      // (sem EPI escolhido) e o ícone de cada linha (com `?epi_id=`).
      '/stock/config':
          'stock_screen.dart → context.push(Routes.stockConfig)',
    };

    test('toda rota gateada é alcançável por clique', () {
      final navigable = AppShell.destinationRoutes.toSet()
        ..addAll(reachableElsewhere.keys);
      final unreachable = routePermissions.keys.toSet().difference(navigable);

      expect(
        unreachable,
        isEmpty,
        reason: 'Rotas gateadas sem nenhum caminho de navegação: $unreachable. '
            'Uma tela inalcançável por clique é uma tela que não existe para o '
            'usuário — foi exatamente o caso da tela de CNPJs. Se a rota é '
            'alcançável por uma tela interna, declare-a em `reachableElsewhere` '
            'com o arquivo que navega até ela.',
      );
    });

    test('as isenções apontam para telas reais, não para conveniência', () {
      // Impede que a lista de isenções vire depósito: toda entrada precisa
      // documentar de onde a navegação parte.
      for (final entry in reachableElsewhere.entries) {
        expect(routePermissions.keys, contains(entry.key));
        expect(entry.value, contains('.dart'));
        expect(AppShell.destinationRoutes, isNot(contains(entry.key)));
      }
    });

    test('a rota de CNPJs está no menu', () {
      // Regressão direta do defeito relatado.
      expect(AppShell.destinationRoutes, contains(Routes.legalEntities));
    });

    test('todo destino do menu aponta para rota conhecida', () {
      for (final route in AppShell.destinationRoutes) {
        expect(
          Routes.all,
          contains(route),
          reason: 'Menu aponta para rota inexistente: $route',
        );
      }
    });

    test('nenhum destino aparece duas vezes', () {
      final routes = AppShell.destinationRoutes;
      expect(routes.toSet().length, routes.length);
    });

    test('todo destino declara a permissão que o libera', () {
      for (final permission in AppShell.destinationPermissions) {
        expect(permission, isNotEmpty);
        expect(
          permission,
          matches(RegExp(r'^[a-z_]+:[a-z_]+$')),
          reason: 'Permissão fora do formato `recurso:ação`: $permission',
        );
      }
    });
  });

  group('listas paralelas do menu', () {
    test('destinos e rótulos têm o mesmo tamanho', () {
      // As duas listas são casadas por índice. Divergir desloca todos os
      // rótulos a partir do ponto da inserção — um menu inteiro com nomes
      // trocados, que passa despercebido em revisão de diff.
      expect(
        AppShell.destinationCount,
        AppShell.labelCount,
        reason: 'Incluiu destino sem incluir o rótulo na mesma posição '
            '(ou vice-versa).',
      );
    });
  });
}
