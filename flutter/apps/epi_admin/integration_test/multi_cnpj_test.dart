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

Future<HttpServer> _startFakeBackend() async {
  final server = await HttpServer.bind(InternetAddress.loopbackIPv4, 0);
  server.listen((request) async {
    _requestedPaths.add(request.uri.path);
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

/// Preenche usuário/senha e entra, aguardando o dashboard estabilizar.
Future<void> _login(WidgetTester tester) async {
  final fields = find.byType(TextField);
  await tester.enterText(fields.at(0), 'admin');
  await tester.enterText(fields.at(1), 'senha');
  await tester.tap(find.byType(EpiButton));
  await tester.pumpAndSettle();
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
      // A jornada real passou por login e bootstrap.
      expect(_requestedPaths, contains('/api/login'));
      expect(_requestedPaths, contains('/api/bootstrap'));
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
      await tester.tap(find.text('ACME Filial RJ — $_cnpjFilial').last);
      await tester.pumpAndSettle();

      // Abre o dropdown de Unidade: só a unidade da filial deve estar lá.
      await tester.tap(find.byType(DropdownButtonFormField<int?>).last);
      await tester.pumpAndSettle();
      expect(find.text('Filial RJ'), findsWidgets);
      expect(find.text('Base Santos'), findsNothing);
      expect(find.text('Matriz SP'), findsNothing);
    });
  });
}
