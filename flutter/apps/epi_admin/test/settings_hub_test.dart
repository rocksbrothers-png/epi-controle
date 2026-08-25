import 'dart:io';

import 'package:epi_admin/core/router/routes.dart';
import 'package:epi_admin/features/settings/widgets/settings_tile.dart';
import 'package:epi_design/epi_design.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

/// Configurações deixou de ser UMA tela.
///
/// Tema, idioma, Ficha, política de arquivamento, visibilidade por módulo e a
/// faixa de atenção viviam empilhados na mesma lista: para chegar à Ficha era
/// preciso rolar por um formulário de retenção e por uma matriz de switches.
/// Agora cada assunto é uma subtela (`/settings/...`) alcançada por um item
/// com ícone e descrição.
///
/// O que estes testes travam é o que a divisão pode perder em silêncio:
/// uma subrota declarada e nunca oferecida (o defeito da tela de CNPJs), uma
/// subtela sem o guarda de empresa do master_admin — que editaria o tenant
/// errado — e a volta de um formulário para dentro do hub.
String _read(String path) => File(path).readAsStringSync();

const _dir = 'lib/features/settings';

void main() {
  group('itens do hub', () {
    testWidgets('mostram ícone, título, descrição e chevron', (tester) async {
      await tester.pumpWidget(MaterialApp(
        theme: EpiTheme.light,
        home: Scaffold(
          body: SettingsTile(
            icon: Icons.assignment_rounded,
            title: 'Ficha de EPI',
            subtitle: 'Título, declaração, observações e rastreabilidade',
            onTap: () {},
          ),
        ),
      ));

      expect(find.text('Ficha de EPI'), findsOneWidget);
      expect(
        find.text('Título, declaração, observações e rastreabilidade'),
        findsOneWidget,
      );
      expect(find.byIcon(Icons.assignment_rounded), findsOneWidget);
      // O chevron é o que diz "isto abre outra tela" — sem ele o item parece
      // um rótulo inerte.
      expect(find.byIcon(Icons.chevron_right_rounded), findsOneWidget);
    });

    testWidgets('navegam ao toque', (tester) async {
      var toques = 0;
      await tester.pumpWidget(MaterialApp(
        theme: EpiTheme.light,
        home: Scaffold(
          body: SettingsTile(
            icon: Icons.archive_rounded,
            title: 'Arquivamento e retenção',
            subtitle: 'Anos de preservação',
            onTap: () => toques++,
          ),
        ),
      ));

      await tester.tap(find.byType(SettingsTile));
      await tester.pump();
      expect(toques, 1);
    });

    testWidgets('a seção separa os itens por divisor', (tester) async {
      await tester.pumpWidget(MaterialApp(
        theme: EpiTheme.light,
        home: Scaffold(
          body: SettingsSection(
            label: 'Operação',
            children: [
              SettingsTile(
                icon: Icons.assignment_rounded,
                title: 'Um',
                subtitle: 'a',
                onTap: () {},
              ),
              SettingsTile(
                icon: Icons.inventory_2_rounded,
                title: 'Dois',
                subtitle: 'b',
                onTap: () {},
              ),
            ],
          ),
        ),
      ));

      expect(find.text('Operação'), findsOneWidget);
      expect(find.byType(SettingsTile), findsNWidgets(2));
      // Dois itens → UM divisor. `n` divisores para `n` itens deixaria uma
      // linha solta na borda do cartão.
      expect(find.byType(Divider), findsOneWidget);
    });
  });

  group('subtelas × hub × rotas', () {
    /// Subrota → arquivo da subtela e classe que o router constrói.
    const subtelas = <String, (String arquivo, String classe)>{
      Routes.settingsAppearance: ('appearance_screen.dart', 'AppearanceScreen'),
      Routes.settingsFicha: ('ficha_config_screen.dart', 'FichaConfigScreen'),
      Routes.settingsStock: ('stock_defaults_screen.dart', 'StockDefaultsScreen'),
      Routes.settingsModules: (
        'module_visibility_screen.dart',
        'ModuleVisibilityScreen'
      ),
      Routes.settingsArchival: (
        'archival_policy_screen.dart',
        'ArchivalPolicyScreen'
      ),
    };

    test('cada subtela existe e declara a sua classe', () {
      for (final entry in subtelas.entries) {
        final (arquivo, classe) = entry.value;
        final fonte = File('$_dir/$arquivo');
        expect(fonte.existsSync(), isTrue, reason: 'ausente: $arquivo');
        expect(fonte.readAsStringSync(), contains('class $classe'));
      }
    });

    test('o router registra todas as subrotas', () {
      final router = _read('lib/core/router/app_router.dart');
      for (final entry in subtelas.entries) {
        final constante = entry.key.replaceFirst('/settings/', '');
        expect(
          router,
          contains(entry.value.$2),
          reason: 'subtela sem GoRoute: $constante',
        );
      }
      expect(router, contains('Routes.settingsFicha'));
      expect(router, contains('Routes.settingsArchival'));
    });

    test('o hub oferece um caminho de clique para cada subrota', () {
      // Rota registrada e nunca oferecida é tela que não existe para o
      // usuário — foi assim que a tela de CNPJs ficou meses inalcançável.
      final hub = _read('$_dir/settings_screen.dart');
      for (final rota in subtelas.keys) {
        final nome = _constanteDe(rota);
        expect(hub, contains('Routes.$nome'), reason: 'sem item no hub: $rota');
      }
    });

    test('o hub não voltou a ser formulário', () {
      // O hub decide o que aparece; quem edita é a subtela. Um `TextField`
      // aqui é o primeiro passo de volta para a tela única.
      final hub = _read('$_dir/settings_screen.dart');
      expect(hub, isNot(contains('TextField(')));
      expect(hub, isNot(contains('SwitchListTile(')));
    });
  });

  group('guardas que a divisão não pode perder', () {
    test('toda subtela por empresa exige a empresa do master_admin', () {
      // O master_admin não pertence a uma empresa: sem `?company_id=` a
      // subtela não sabe QUAL tenant está editando. O guarda mostra o aviso
      // em vez de abrir o formulário — inclusive para quem chega por URL
      // direta, que não passa pelo seletor do hub.
      for (final arquivo in [
        'ficha_config_screen.dart',
        'stock_defaults_screen.dart',
        'module_visibility_screen.dart',
        'archival_policy_screen.dart',
      ]) {
        final fonte = _read('$_dir/$arquivo');
        expect(fonte, contains('settingsCompanyMissing'), reason: arquivo);
        expect(fonte, contains('companyId'), reason: arquivo);
      }
    });

    test('a subtela de Aparência não pede empresa', () {
      // Tema e idioma são do aparelho, não do tenant: exigir empresa ali
      // deixaria o master_admin sem trocar o próprio tema.
      final fonte = _read('$_dir/appearance_screen.dart');
      expect(fonte, isNot(contains('settingsCompanyMissing')));
      expect(fonte, isNot(contains('company_id')));
    });

    test('o padrão de estoque continua exigindo settings:update', () {
      // Mesma permissão que o backend cobra em
      // `/api/stock/company-attention-percentage`. Sem ela o controle sempre
      // terminaria em 403 — e o padrão alterado é herdado por TODAS as
      // Unidades que não definiram o seu.
      final fonte = _read('$_dir/stock_defaults_screen.dart');
      expect(fonte, contains("hasPermission('settings:update')"));
      expect(fonte, contains('podeConfigurarEstoque'));
    });

    test('o hub esconde o item de estoque de quem não pode configurá-lo', () {
      final hub = _read('$_dir/settings_screen.dart');
      expect(hub, contains('if (podeConfigurarEstoque(context))'));
    });
  });
}

/// Nome da constante em `Routes` para uma subrota `/settings/<x>`.
String _constanteDe(String rota) {
  final sufixo = rota.substring('/settings/'.length);
  return 'settings${sufixo[0].toUpperCase()}${sufixo.substring(1)}';
}
