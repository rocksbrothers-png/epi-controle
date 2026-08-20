// E2E do Multi-CNPJ — roda em device/emulador (NÃO no `flutter test` puro):
//
//   flutter test integration_test/multi_cnpj_test.dart
//
// No CI roda no job "Integration (Android emulator)" do flutter.yml.
//
// Diferente do smoke (que é backend-free), aqui a jornada **precisa** de dados:
// não dá para provar a cascata Empresa → CNPJ → Unidade sem CNPJs e unidades.
// Em vez de mockar o cliente HTTP, sobe-se um `HttpServer` de verdade em
// 127.0.0.1 com respostas canônicas. O caminho exercitado é o real e inteiro:
// Dio + interceptors → HTTP → parsing dos modelos → cubits → widgets. E
// continua determinístico, porque o "backend" é local e fixo.

import 'dart:convert';
import 'dart:io';

import 'package:epi_design/epi_design.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';

import 'package:epi_admin/app.dart';
import 'package:epi_admin/core/api/api_client.dart';
import 'package:epi_admin/core/i18n/locale_provider.dart';
import 'package:epi_admin/core/i18n/theme_mode_notifier.dart';

// ── Dados do cenário ────────────────────────────────────────────────────────
//
// Uma empresa (tenant) com dois CNPJs — o caso que a arquitetura existe para
// suportar. A unidade pertence a um CNPJ (`legal_entity_id`): é esse elo que
// liga os dois níveis da cascata.

const _cnpjMatriz = '11.222.333/0001-81';
const _cnpjFilial = '45.723.174/0001-10';

const _legalEntities = [
  {
    'id': 10,
    'company_id': 1,
    'cnpj': _cnpjMatriz,
    'legal_name': 'ACME SA',
    'trade_name': 'ACME Matriz',
    'entity_type': 'matriz',
    'active': 1,
  },
  {
    'id': 20,
    'company_id': 1,
    'cnpj': _cnpjFilial,
    'legal_name': 'ACME Filial RJ LTDA',
    'trade_name': 'ACME Filial RJ',
    'entity_type': 'filial',
    'active': 1,
  },
];

const _units = [
  {'id': 1, 'company_id': 1, 'name': 'Matriz SP', 'legal_entity_id': 10},
  {'id': 2, 'company_id': 1, 'name': 'Base Santos', 'legal_entity_id': 10},
  {'id': 3, 'company_id': 1, 'name': 'Filial RJ', 'legal_entity_id': 20},
];

const _employees = [
  {'id': 100, 'name': 'Ana', 'unit_id': 1, 'sector': 'Operação', 'legal_entity_id': 10},
  {'id': 101, 'name': 'Bruno', 'unit_id': 3, 'sector': 'Manutenção', 'legal_entity_id': 20},
];

/// Permissões do Administrador Geral: enxerga todos os CNPJs da empresa.
const _permissions = [
  'legal_entities:view',
  'legal_entities:manage',
  'employees:view',
  'units:view',
];

// ── Backend canônico ────────────────────────────────────────────────────────

/// Rotas atendidas, com o caminho pedido registrado para asserção.
final _requestedPaths = <String>[];

/// URIs completas, com query. A fatia 1.1D-C2 moveu o recorte do Dashboard
/// para o servidor: provar a cascata agora exige olhar o que o cliente PEDIU,
/// não só qual rota ele tocou.
final _requestedUris = <Uri>[];

/// Resposta canônica de `GET /api/dashboard/summary`.
///
/// SEM envelope `{ok, data}` — o backend real responde
/// `send_json(handler, 200, resumo)` (modules/dashboard/routes.py).
///
/// O recorte é do SERVIDOR: ele lê a seleção da query e devolve escopo, KPIs e
/// as fontes do filtro. `filters.units` não é filtrado por CNPJ aqui, porque o
/// backend só o restringe para perfil travado — a cascata CNPJ → Unidade é do
/// cliente (`DashboardFilters.unitsFor`).
Map<String, dynamic> _resumoDoDashboard(Uri uri) {
  final cnpjId = int.tryParse(uri.queryParameters['legal_entity_id'] ?? '');
  final unitId = int.tryParse(uri.queryParameters['unit_id'] ?? '');
  final setor = uri.queryParameters['sector'];
  return {
    'scope': {
      'unit_id': unitId,
      'unit_scope_source': unitId == null ? 'none' : 'selected',
      'locked': false,
      'company_id': 1,
      'legal_entity_id': cnpjId,
      'sector': setor,
    },
    'kpis': {
      'deliveries_today': 3,
      'expiring_epis': 1,
      // `null` sem Unidade resolvida — e não `0`. Zero afirmaria "nenhum EPI
      // crítico"; sem Unidade escolhida a pergunta não se aplica.
      'critical_stock': unitId == null ? null : 7,
      'near_minimum_stock': unitId == null ? null : 2,
      'pending_purchases': 0,
    },
    'filters': {
      // Rótulo já composto pelo servidor (`_rotulo_cnpj`): nome + número.
      // O número desambigua CNPJs de nome parecido dentro do mesmo grupo.
      'legal_entities': [
        for (final e in _legalEntities)
          {'id': e['id'], 'name': '${e['trade_name']} — ${e['cnpj']}'},
      ],
      'units': [
        for (final u in _units)
          {
            'id': u['id'],
            'name': u['name'],
            'legal_entity_id': u['legal_entity_id'],
          },
      ],
      'sectors': const ['Manutenção', 'Operação'],
    },
    'alerts': const [],
    'compliance': const {'summary': <String, int>{}},
  };
}

Future<HttpServer> _startFakeBackend() async {
  final server = await HttpServer.bind(InternetAddress.loopbackIPv4, 0);
  server.listen((request) async {
    _requestedPaths.add(request.uri.path);
    _requestedUris.add(request.uri);
    Object? body;
    switch (request.uri.path) {
      case '/api/login':
        body = {
          'token': 'token-e2e',
          'refresh_token': 'refresh-e2e',
          // Permissões e refresh vêm no TOPO — contrato real do backend.
          'permissions': _permissions,
          'user': {
            'id': 1,
            'username': 'admin',
            'full_name': 'Admin Geral',
            'role': 'general_admin',
            'company_id': 1,
          },
        };
      case '/api/bootstrap':
        body = {
          'ok': true,
          'data': {
            'units': _units,
            'legal_entities': _legalEntities,
            'employees': _employees,
            'epis': const [],
            'users': const [],
            'alerts': const [],
            'deliveries': const [],
            'pending_purchases': 0,
          },
        };
      case '/api/dashboard/summary':
        body = _resumoDoDashboard(request.uri);
      case '/api/legal-entities':
        body = {'legal_entities': _legalEntities};
      default:
        // Qualquer outra chamada responde vazio: a jornada não deve depender
        // dela, e um 404 viraria erro de rede difícil de diagnosticar.
        body = {'ok': true, 'data': const <String, dynamic>{}};
    }
    request.response
      ..statusCode = HttpStatus.ok
      ..headers.contentType = ContentType.json
      ..write(jsonEncode(body));
    await request.response.close();
  });
  return server;
}

// ── Boot ────────────────────────────────────────────────────────────────────

Future<void> _bootApp(WidgetTester tester) async {
  final themeNotifier = ThemeModeNotifier();
  await themeNotifier.init();
  final localeProvider = LocaleProvider();
  await localeProvider.init();

  await tester.pumpWidget(EpiAdminApp(
    themeNotifier: themeNotifier,
    localeProvider: localeProvider,
  ));
  await tester.pumpAndSettle();
}

/// Espera até que [caminho] tenha sido pedido ao backend, ou falha por timeout.
///
/// `pumpAndSettle` garante apenas que não há mais frames agendados — NÃO que
/// uma requisição HTTP já saiu. Enquanto o Dashboard emitia o pedido no mesmo
/// turno em que o cubit era criado, a diferença não aparecia; com o
/// carregamento em duas etapas (idioma e resumo) ela vira corrida, e o teste
/// passava ou falhava por sorte de escalonamento.
Future<void> _aguardaPedido(
  WidgetTester tester,
  String caminho, {
  Duration limite = const Duration(seconds: 15),
}) async {
  final fim = DateTime.now().add(limite);
  while (!_requestedPaths.contains(caminho)) {
    if (DateTime.now().isAfter(fim)) {
      fail('A rota $caminho não foi pedida em ${limite.inSeconds}s. '
          'Pedidas até aqui: $_requestedPaths');
    }
    await tester.pump(const Duration(milliseconds: 50));
  }
  await tester.pumpAndSettle();
}

/// Preenche usuário/senha e entra, aguardando o dashboard ficar PRONTO.
///
/// Pronto = o resumo já chegou. Sem isso, cada caso decidiria sobre uma tela
/// ainda em carregamento.
Future<void> _login(WidgetTester tester) async {
  final fields = find.byType(TextField);
  await tester.enterText(fields.at(0), 'admin');
  await tester.enterText(fields.at(1), 'senha');
  await tester.tap(find.byType(EpiButton));
  await tester.pumpAndSettle();
  await _aguardaPedido(tester, '/api/dashboard/summary');
}

void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  late HttpServer server;

  setUpAll(() async {
    server = await _startFakeBackend();
    await ApiClient.init(baseUrl: 'http://127.0.0.1:${server.port}');
  });

  tearDownAll(() async => server.close(force: true));

  setUp(() async {
    _requestedPaths.clear();
    _requestedUris.clear();
    // Cada caso começa deslogado, na tela de login.
    await ApiClient.clearSession();
  });

  group('Jornada Multi-CNPJ', () {
    testWidgets('login carrega o bootstrap com os CNPJs da empresa',
        (tester) async {
      await _bootApp(tester);
      await _login(tester);

      // Saiu da tela de login (o app navegou para o dashboard).
      expect(find.byIcon(Icons.shield_outlined), findsNothing);
      // A jornada real passou por login e bootstrap...
      expect(_requestedPaths, contains('/api/login'));
      // ...e o bootstrap ainda é tocado, mas só pela preferência de idioma:
      // os dados do painel não vêm mais de lá (fatia 1.1D-C2).
      expect(_requestedPaths, contains('/api/bootstrap'));
      // O painel foi montado pela rota do resumo.
      expect(_requestedPaths, contains('/api/dashboard/summary'));
    });

    testWidgets('dashboard mostra a barra de filtros quando há CNPJs',
        (tester) async {
      await _bootApp(tester);
      await _login(tester);

      // A barra só existe quando a empresa tem CNPJs cadastrados; os dropdowns
      // de CNPJ, Unidade e Setor são o filtro em cascata.
      expect(find.byType(DropdownButtonFormField<int?>), findsNWidgets(2));
      expect(find.byType(DropdownButtonFormField<String?>), findsOneWidget);
    });

    testWidgets('selecionar um CNPJ restringe as unidades da cascata',
        (tester) async {
      await _bootApp(tester);
      await _login(tester);

      // Abre o dropdown de CNPJ (o primeiro int? da barra) e escolhe a filial.
      await tester.tap(find.byType(DropdownButtonFormField<int?>).first);
      await tester.pumpAndSettle();
      // O rótulo vem PRONTO do servidor (`_rotulo_cnpj`), com o número junto.
      // Compor o texto virou responsabilidade de quem conhece os dados; o
      // cliente só exibe.
      await tester.tap(find.text('ACME Filial RJ — $_cnpjFilial').last);
      await tester.pumpAndSettle();

      // A escolha vira uma CONSULTA ao servidor, com o CNPJ na query e sem
      // unidade nem setor — a cascata limpa os níveis abaixo.
      final consulta = _requestedUris
          .where((u) => u.path == '/api/dashboard/summary')
          .last;
      expect(consulta.queryParameters['legal_entity_id'], '20');
      expect(consulta.queryParameters.containsKey('unit_id'), isFalse);
      expect(consulta.queryParameters.containsKey('sector'), isFalse);

      // Abre o dropdown de Unidade: só a unidade da filial deve estar lá.
      await tester.tap(find.byType(DropdownButtonFormField<int?>).last);
      await tester.pumpAndSettle();
      expect(find.text('Filial RJ'), findsWidgets);
      expect(find.text('Base Santos'), findsNothing);
      expect(find.text('Matriz SP'), findsNothing);
    });

    testWidgets('KPI de estoque crítico é "—" sem Unidade e número com ela',
        (tester) async {
      // O contrato da #271 atravessando a pilha inteira: sem Unidade resolvida
      // o servidor manda `critical_stock: null`, e a tela mostra "—". Exibir 0
      // ali afirmaria que nenhum EPI está crítico.
      await _bootApp(tester);
      await _login(tester);

      expect(find.text('—'), findsWidgets);
      expect(find.text('7'), findsNothing);

      // Escolhe CNPJ e Unidade: agora existe contexto, e o número é o que o
      // servidor contou — o cliente não recontou EPI nenhum.
      await tester.tap(find.byType(DropdownButtonFormField<int?>).first);
      await tester.pumpAndSettle();
      await tester.tap(find.text('ACME Filial RJ — $_cnpjFilial').last);
      await tester.pumpAndSettle();
      await tester.tap(find.byType(DropdownButtonFormField<int?>).last);
      await tester.pumpAndSettle();
      await tester.tap(find.text('Filial RJ').last);
      await tester.pumpAndSettle();

      final comUnidade = _requestedUris
          .where((u) => u.path == '/api/dashboard/summary')
          .last;
      expect(comUnidade.queryParameters['unit_id'], '3');
      expect(find.text('7'), findsOneWidget);
    });
  });
}
