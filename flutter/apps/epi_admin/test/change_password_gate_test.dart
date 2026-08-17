import 'dart:io';

import 'package:epi_admin/core/router/route_permissions.dart';
import 'package:epi_admin/core/router/routes.dart';
import 'package:flutter_test/flutter_test.dart';

/// Gate de senha temporária (Lote 1 de paridade com o `epi-controle-app`).
///
/// O backend provisiona credencial com `must_change_password`. Até este lote,
/// **este repositório ignorava a flag por completo**: o usuário entrava direto
/// e a senha temporária provisionada pelo administrador valia indefinidamente.
/// Não era uma tela faltando — era um furo de autenticação.
///
/// Sobre a forma destes testes: o `redirect` do GoRouter é um closure dentro de
/// `buildRouter`, e exercitá-lo de verdade exigiria montar o router inteiro,
/// com `LocaleProvider` (que abre `FlutterSecureStorage`) e os builders de
/// todas as telas. O que se trava aqui é a ESTRUTURA do gate — incluindo a
/// ordem em relação ao guard de permissão, que é uma propriedade de correção e
/// não de estilo. O comportamento ponta a ponta é coberto pelos jobs de build
/// Web/Android/iOS e por `auth_contract_test.dart`, que prova a leitura da flag
/// nas duas posições em que o backend a envia.
String _router() =>
    File('lib/core/router/app_router.dart').readAsStringSync();

String _semComentarios(String fonte) => fonte
    .replaceAll(RegExp(r'/\*.*?\*/', dotAll: true), '')
    .replaceAll(RegExp(r'//[^\n]*'), '');

void main() {
  group('a rota de troca de senha existe e é privada', () {
    test('Routes.changePassword está declarada e listada em `all`', () {
      expect(Routes.changePassword, '/change-password');
      expect(Routes.all, contains(Routes.changePassword));
    });

    test('NÃO é rota pública', () {
      // Pública significa alcançável sem sessão. A troca de senha acontece
      // COM sessão — é o primeiro ato dela. Marcá-la como pública abriria a
      // tela para quem nem autenticou.
      expect(publicRoutes, isNot(contains(Routes.changePassword)));
    });

    test('não exige permissão específica', () {
      // Exigir permissão aqui prenderia o usuário num impasse: ele precisa
      // trocar a senha para usar o sistema, mas não poderia abrir a tela que
      // permite trocá-la.
      expect(requiredPermissionFor(Routes.changePassword), isNull);
    });
  });

  group('o gate prende o usuário até a troca', () {
    test('redireciona qualquer rota privada para a tela de troca', () {
      final fonte = _semComentarios(_router());
      expect(fonte, contains('if (isLoggedIn && mustChangePassword.value)'));
      expect(fonte, contains(': Routes.changePassword'));
    });

    test('o gate vem ANTES do guard de permissão', () {
      // Ordem é correção, não estilo. Se o guard de permissão rodasse antes,
      // um usuário com senha temporária e sem permissão para a rota pedida
      // seria mandado ao dashboard — escapando da troca obrigatória.
      final fonte = _semComentarios(_router());
      final gate = fonte.indexOf('mustChangePassword.value');
      final permissao = fonte.indexOf('hasRoutePermission(');
      expect(gate, isNot(-1), reason: 'gate de senha não encontrado');
      expect(permissao, isNot(-1), reason: 'guard de permissão não encontrado');
      expect(gate, lessThan(permissao),
          reason: 'o gate de senha temporária precisa preceder o de permissão');
    });

    test('quem já trocou não fica preso na tela', () {
      // Sem esta saída, o usuário que trocou a senha continuaria sendo
      // devolvido à tela de troca a cada navegação.
      final fonte = _semComentarios(_router());
      expect(fonte, contains('!mustChangePassword.value &&'));
      expect(fonte, contains('return Routes.dashboard;'));
    });

    test('o gate reavalia quando a flag muda', () {
      // `refreshListenable` é o que faz o GoRouter reexecutar o `redirect`.
      // Fora dele, a troca de senha concluída não liberaria a navegação até
      // um restart do app — e o sintoma pareceria "travou depois de salvar".
      final fonte = _semComentarios(_router());
      final merge = RegExp(r'Listenable\.merge\(\s*\[([^\]]*)\]', dotAll: true)
          .firstMatch(fonte);
      expect(merge, isNotNull);
      expect(merge!.group(1), contains('mustChangePassword'));
    });
  });

  group('a flag atravessa o estado de autenticação', () {
    test('AuthAuthenticated carrega mustChangePassword em props', () {
      // `Equatable` compara por `props`. Fora dela, a mudança da flag não
      // conta como mudança de estado e nada reconstrói.
      final estado =
          File('lib/core/bloc/auth_state.dart').readAsStringSync();
      final props = RegExp(r'get props =>\s*\[([^\]]*)\]', dotAll: true)
          .allMatches(estado)
          .map((m) => m.group(1)!)
          .where((p) => p.contains('token'))
          .toList();
      expect(props, isNotEmpty, reason: 'props de AuthAuthenticated não achada');
      expect(props.first, contains('mustChangePassword'));
    });

    test('o login propaga a flag vinda da API', () {
      final cubit = File('lib/core/bloc/auth_cubit.dart').readAsStringSync();
      expect(cubit, contains('mustChangePassword: res.mustChangePassword'));
    });

    test('concluir a troca libera a navegação preservando a sessão', () {
      // Reautenticar seria o caminho errado: derrubaria token, permissões e
      // contexto de sessão logo depois de o usuário provar quem é.
      final cubit = File('lib/core/bloc/auth_cubit.dart').readAsStringSync();
      final metodo = RegExp(r'void completePasswordChange\(\) \{(.*?)\n  \}',
              dotAll: true)
          .firstMatch(cubit);
      expect(metodo, isNotNull, reason: 'completePasswordChange não encontrado');
      final corpo = metodo!.group(1)!;
      expect(corpo, contains('mustChangePassword: false'));
      for (final preservado in ['token:', 'permissions:', 'sessionContext:']) {
        expect(corpo, contains(preservado),
            reason: '$preservado precisa sobreviver à troca de senha');
      }
    });
  });
}
