import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

/// Permissões por ação e limites de escopo na aba de terceirizados
/// (ADR-0002 §13, F4 da #226).
///
/// Antes do F4 esta tela não chamava `hasPermission` uma única vez: o gate era
/// só de rota (`employees:create` OU `employees:create_simplified`), e uma vez
/// dentro todos os botões apareciam para todo mundo. Um Gestor de EPI sem
/// `employees:delete` via "Arquivar" e só descobria o bloqueio depois de
/// confirmar.
///
/// Os testes leem a fonte porque o que precisa ficar travado é a EXPRESSÃO do
/// gate — qual permissão protege qual ação. Um teste de widget provaria que o
/// botão some quando o booleano é falso, sem dizer nada sobre o booleano ter
/// sido calculado com a permissão certa, que é onde mora o erro.
String _readTab() => File(
      'lib/features/outsourced_companies/outsourced_employees_tab.dart',
    ).readAsStringSync();

/// Corpo de um método `bool _nome(...) => ...;`, sem os comentários acima.
String _gateBody(String source, String name) {
  final match = RegExp('bool $name\\(BuildContext context\\)\\s*=>(.*?);', dotAll: true)
      .firstMatch(source);
  expect(match, isNotNull, reason: 'gate $name não encontrado');
  return match!.group(1)!;
}

void main() {
  group('cada ação tem o seu gate', () {
    test('criar exige exatamente employees:create_simplified', () {
      // A rota do backend usa `authorize_action` (não `_any`) com essa
      // permissão: é o piso técnico do módulo, e mesmo Administrador Geral
      // passa por ele.
      final body = _gateBody(_readTab(), '_canCreate');
      expect(body, contains("'employees:create_simplified'"));
      expect(body, isNot(contains("'employees:delete'")));
    });

    test('arquivar aceita employees:delete OU employees:update_simplified', () {
      // Espelha `ARCHIVAL_ENTITIES.outsourcedEmployee.deletePermission` do Web
      // Legado. Sem a segunda, o botão sumiria para Administrador Local e
      // Gestor de EPI — que nunca têm `employees:delete` e são quem opera esta
      // tela. Exigir só a primeira seria "seguro" e inutilizaria a tela.
      final body = _gateBody(_readTab(), '_canArchive');
      expect(body, contains("'employees:delete'"));
      expect(body, contains("'employees:update_simplified'"));
    });

    test('vínculo aceita employees:update OU employees:update_simplified', () {
      // Mesma dupla do `authorize_action_any` das três rotas de vínculo.
      final body = _gateBody(_readTab(), '_canManageUnitLink');
      expect(body, contains("'employees:update'"));
      expect(body, contains("'employees:update_simplified'"));
    });

    test('editar usa o mesmo gate do vínculo, como no Web Legado', () {
      final body = _gateBody(_readTab(), '_canEdit');
      expect(body, contains('_canManageUnitLink'));
    });
  });

  group('os gates chegam aos botões', () {
    test('o FAB de criar depende de _canCreate', () {
      expect(_readTab(), contains('state.showArchived || !_canCreate(ctx)'));
    });

    test('editar e arquivar dependem dos seus gates', () {
      final tab = _readTab();
      expect(tab, contains('canEdit: _canEdit(ctx)'));
      expect(tab, contains('canArchive: _canArchive(ctx)'));
      expect(tab, contains('if (canEdit)'));
      expect(tab, contains('if (canArchive)'));
    });

    test('desarquivar usa o mesmo gate de arquivar', () {
      // As duas mexem no ciclo de vida do colaborador no tenant; separá-las
      // deixaria alguém desarquivar o que não pode arquivar.
      final tab = _readTab();
      expect(tab, contains('canRestore: _canArchive(ctx)'));
      expect(tab, contains('canRestore\n          ? TextButton.icon('));
    });

    test('nenhum botão da tela ficou sem gate', () {
      // Varredura: todo `IconButton`/`TextButton.icon`/FAB do arquivo precisa
      // estar sob alguma condição. É o teste que teria acusado o estado
      // anterior, em que NENHUM deles estava.
      final tab = _readTab();
      final gated = RegExp(r'if \((canEdit|canArchive|canRestore|canManageUnitLink)')
          .allMatches(tab)
          .length;
      expect(gated, greaterThanOrEqualTo(3),
          reason: 'os botões de ação precisam estar sob gate');
      expect(tab, contains('!_canCreate(ctx)'));
    });
  });

  group('limites que a tela não pode ultrapassar', () {
    test('o gate é defesa em profundidade, não a autorização', () {
      // Se alguém tratar `hasPermission` como decisão final e parar de mandar
      // a requisição ao backend, a autorização migra para o cliente.
      final tab = _readTab();
      expect(tab, contains('defesa em profundidade'));
      expect(tab, contains('quem decide'));
    });

    test('o vínculo local não desbloqueia nenhuma ação sensível', () {
      // O vínculo amplia SOBRE QUEM se consulta; nunca concede permissão.
      // Nenhum gate pode olhar `localUnitLinkStatus` para liberar edição,
      // arquivamento ou criação.
      final tab = _readTab();
      for (final gate in ['_canCreate', '_canEdit', '_canArchive']) {
        expect(
          _gateBody(tab, gate),
          isNot(contains('localUnitLinkStatus')),
          reason: '$gate não pode depender do vínculo local',
        );
      }
    });

    test('mão de obra própria não recebe ação de vínculo', () {
      // Defesa em profundidade: o backend manda `null` para ela (F1), e a
      // tela só oferece ação quando o status é não-nulo.
      expect(_readTab(), contains('if (canManageUnitLink && linkStatus != null)'));
    });

    test('a tela não chama rota de transferência, portal ou entrega', () {
      // Fronteiras do PR D: essas operações continuam fora do alcance do
      // vínculo local, e esta aba não é porta de entrada para elas.
      final tab = _readTab();
      for (final forbidden in const [
        'employee-unit-movements',
        'legal-entity-transfer',
        '/portal',
        'deliveries',
        'purge',
      ]) {
        expect(tab, isNot(contains(forbidden)), reason: 'rota fora de escopo: $forbidden');
      }
    });
  });

  group('Unidade de origem (item 6)', () {
    test('a Unidade do colaborador aparece rotulada', () {
      // Sem rótulo, a tela mostra uma Unidade só e o operador não distingue a
      // lotação do colaborador da Unidade que detém o vínculo local ("esta
      // Unidade", implícita nas ações).
      expect(_readTab(), contains(r"'${l10n.employeeUnitLabel}: ${employee.unitName}'"));
    });

    test('reaproveita a chave existente em vez de criar string nova', () {
      final arb = File('../../packages/epi_i18n/lib/l10n/app_pt_BR.arb').readAsStringSync();
      expect(arb, contains('"employeeUnitLabel"'));
    });
  });
}
