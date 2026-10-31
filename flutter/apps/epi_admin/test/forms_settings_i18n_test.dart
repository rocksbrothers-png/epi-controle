import 'dart:convert';
import 'package:dio/dio.dart';
import 'package:epi_admin/core/api/api_client.dart';
import 'package:epi_admin/core/bloc/auth_cubit.dart';
import 'package:epi_admin/core/bloc/auth_state.dart';
import 'package:epi_admin/core/i18n/entity_labels.dart';
import 'package:epi_admin/core/i18n/generated/app_localizations.dart';
import 'package:epi_admin/core/session/session_context.dart';
import 'package:epi_admin/features/users/users_screen.dart';
import 'package:epi_admin/features/units/units_screen.dart';
import 'package:epi_admin/features/settings/archival_policy_screen.dart';
import 'package:epi_design/epi_design.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:flutter_test/flutter_test.dart';

SessionContext session(String role) => SessionContext(
  userId: 71,
  companyId: 41,
  unitId: 42,
  role: role,
  permissions: const [],
  tenantName: 'Original <company>',
  companySettings: const {},
);

class TestAuth extends AuthCubit {
  TestAuth(String role) {
    emit(
      AuthAuthenticated(
        token: 'synthetic-access',
        user: const {'id': 71},
        sessionContext: session(role),
      ),
    );
  }
}

class FormsAdapter implements HttpClientAdapter {
  final calls = <RequestOptions>[];
  String writeMode = 'success';
  bool loadDenied = false;
  @override
  Future<ResponseBody> fetch(
    RequestOptions o,
    Stream<Uint8List>? stream,
    Future<void>? cancel,
  ) async {
    calls.add(o);
    Object data;
    var status = 200;
    if (o.method != 'GET') {
      expect([
        '/api/users',
        '/api/units',
        '/api/archival-policy',
      ], contains(o.path));
      if (writeMode == 'generic') {
        status = 500;
        data = {};
      } else if (writeMode == 'specific') {
        status = 500;
        data = {
          'error': {'message': 'Original <server detail> {keep}'},
          'detail': 'Original <server detail> {keep}',
        };
      } else {
        data = {'id': 99};
      }
    } else if (o.path == '/api/bootstrap') {
      data = {
        'users': [
          {
            'id': 10,
            'username': 'original.user',
            'full_name': 'Original <name>',
            'role': 'registry_admin',
            'company_name': 'Original <company>',
            'company_id': 41,
          },
        ],
        'units': [],
      };
    } else if (o.path == '/api/units/archived') {
      data = {'items': []};
    } else if (o.path == '/api/companies') {
      data = {
        'items': [
          {
            'id': 41,
            'name': 'Original <company>',
            'active': 1,
            'license_status': 'active',
          },
        ],
      };
    } else if (o.path == '/api/companies/41/legal-entities') {
      data = {'items': []};
    } else if (o.path == '/api/archival-policy') {
      if (loadDenied) {
        status = 403;
        data = {'message': 'Original <denied>'};
      } else {
        data = {
          'unit_retention_years': 5,
          'epi_retention_years': 6,
          'employee_retention_years': 7,
        };
      }
    } else {
      throw StateError('Unexpected synthetic request: ${o.method} ${o.path}');
    }
    return ResponseBody.fromString(
      jsonEncode(data),
      status,
      headers: {
        Headers.contentTypeHeader: ['application/json'],
      },
    );
  }

  @override
  void close({bool force = false}) {}
  List<RequestOptions> get writes =>
      calls.where((o) => o.method != 'GET').toList();
}

Future<void> settle(WidgetTester t) async {
  await t.pump(const Duration(milliseconds: 100));
  await t.runAsync(
    () => Future<void>.delayed(const Duration(milliseconds: 30)),
  );
  await t.pumpAndSettle();
}

Finder input(String label) => find.descendant(
  of: find.byWidgetPredicate((w) => w is EpiInput && w.label == label),
  matching: find.byType(TextField),
);
Future<void> enter(WidgetTester t, String label, String value) async {
  await t.ensureVisible(input(label));
  await t.pumpAndSettle();
  await t.enterText(input(label), value);
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  const locales = [
    Locale('pt', 'BR'),
    Locale('en', 'US'),
    Locale('es', 'ES'),
    Locale('fr', 'FR'),
    Locale('no', 'NO'),
  ];
  var current = const Locale('pt', 'BR');
  String? clipboard;
  setUpAll(() async {
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(
          const MethodChannel('plugins.it_nomads.com/flutter_secure_storage'),
          (call) async =>
              call.method == 'read' && call.arguments['key'] == 'access_token'
              ? 'synthetic-access'
              : null,
        );
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(SystemChannels.platform, (call) async {
          if (call.method == 'Clipboard.setData') {
            clipboard = call.arguments['text'] as String;
            return null;
          }
          return null;
        });
    await ApiClient.init(
      baseUrl: 'https://synthetic.local',
      localeTag: () => current.toLanguageTag(),
    );
  });
  Future<ValueNotifier<Locale>> mount(
    WidgetTester t,
    Locale locale,
    Widget child,
    FormsAdapter adapter, {
    String role = 'general_admin',
  }) async {
    current = locale;
    final value = ValueNotifier(locale);
    value.addListener(() => current = value.value);
    addTearDown(value.dispose);
    final auth = TestAuth(role);
    addTearDown(auth.close);
    await ApiClient.saveSessionContext(session(role));
    ApiClient.debugDio.httpClientAdapter = adapter;
    t.view.physicalSize = const Size(390, 844);
    t.view.devicePixelRatio = 1;
    addTearDown(t.view.resetPhysicalSize);
    addTearDown(t.view.resetDevicePixelRatio);
    await t.runAsync(() => AppLocalizations.delegate.load(locale));
    await t.pumpWidget(
      ValueListenableBuilder<Locale>(
        valueListenable: value,
        builder: (context, loc, _) => MaterialApp(
          locale: loc,
          theme: EpiTheme.light,
          localizationsDelegates: AppLocalizations.localizationsDelegates,
          supportedLocales: AppLocalizations.supportedLocales,
          home: BlocProvider<AuthCubit>.value(value: auth, child: child),
        ),
      ),
    );
    await settle(t);
    return value;
  }

  for (var i = 0; i < locales.length; i++) {
    final target = locales[i];
    for (final users in [true, false]) {
      testWidgets(
        '${target.toLanguageTag()} ${users ? 'user' : 'unit'} form keeps fields, canonical choices and payloads',
        (t) async {
          final adapter = FormsAdapter();
          final value = await mount(
            t,
            target,
            users ? const UsersScreen() : const UnitsScreen(),
            adapter,
          );
          var l = (await t.runAsync(
            () => AppLocalizations.delegate.load(target),
          ))!;
          if (users) {
            expect(
              find.text(appRoleLabel('registry_admin', l)),
              findsOneWidget,
            );
          }
          await t.tap(find.byType(FloatingActionButton));
          await settle(t);
          expect(find.byType(AlertDialog), findsOneWidget);
          expect(
            find.text(users ? l.userNewTitle : l.unitNewTitle),
            findsOneWidget,
          );
          await t.tap(find.text(l.save));
          await settle(t);
          expect(
            find.text(users ? l.userIdentityRequired : l.unitFieldsRequired),
            findsOneWidget,
          );
          expect(adapter.writes, isEmpty);
          await enter(
            t,
            users ? l.loginUsername : l.formNameLabel,
            users ? 'synthetic.user' : 'Original <unit> {keep}',
          );
          await enter(
            t,
            users ? l.employeeNameLabel : l.formCityLabel,
            users ? 'Original <name> {keep}' : 'Macaé',
          );
          final dropdown = find.byType(DropdownButtonFormField<String>);
          expect(
            t
                .widget<DropdownButton<String>>(
                  find.descendant(
                    of: dropdown,
                    matching: find.byType(DropdownButton<String>),
                  ),
                )
                .items!
                .map((item) => item.value)
                .toList(),
            users
                ? [
                    'general_admin',
                    'registry_admin',
                    'admin',
                    'user',
                    'buyer',
                    'approver',
                    'employee',
                  ]
                : ['base', 'embarcacao', 'plataforma'],
          );
          await t.ensureVisible(dropdown);
          await t.pumpAndSettle();
          await t.tap(dropdown);
          await t.pumpAndSettle();
          final selected = users ? 'admin' : 'embarcacao';
          await t.tap(
            find
                .text(
                  users
                      ? appRoleLabel(selected, l)
                      : appUnitTypeLabel(selected, l),
                )
                .last,
          );
          await settle(t);
          if (users) {
            await enter(t, l.userEmployeeIdRequired, '42');
            await enter(t, l.userTemporaryPassword, 'Synthetic-only!41');
          } else {
            await enter(t, l.reportsRequestNotes, 'Original <notes> {keep}');
          }
          final fields = t
              .widgetList<TextField>(
                find.descendant(
                  of: find.byType(AlertDialog),
                  matching: find.byType(TextField),
                ),
              )
              .map((f) => f.controller!.text)
              .toList();
          final reads = adapter.calls.length;
          value.value = locales[(i + 1) % locales.length];
          await settle(t);
          l = (await t.runAsync(
            () => AppLocalizations.delegate.load(value.value),
          ))!;
          expect(
            t
                .widgetList<TextField>(
                  find.descendant(
                    of: find.byType(AlertDialog),
                    matching: find.byType(TextField),
                  ),
                )
                .map((f) => f.controller!.text)
                .toList(),
            fields,
          );
          expect(
            find.text(users ? l.userIdentityRequired : l.unitFieldsRequired),
            findsOneWidget,
          );
          expect(adapter.calls, hasLength(reads));
          if (users) {
            await t.ensureVisible(input(l.userTemporaryPassword));
            await t.pumpAndSettle();
            await t.tap(find.byTooltip(l.userCopyPassword));
            await settle(t);
            expect(clipboard, 'Synthetic-only!41');
            value.value = target;
            await settle(t);
            l = (await t.runAsync(
              () => AppLocalizations.delegate.load(value.value),
            ))!;
            expect(find.text(l.userPasswordCopied), findsOneWidget);
          }
          adapter.writeMode = 'generic';
          await t.tap(find.text(l.save));
          await settle(t);
          expect(find.text(l.formSaveFailed), findsOneWidget);
          value.value = locales[(i + 2) % locales.length];
          await settle(t);
          l = (await t.runAsync(
            () => AppLocalizations.delegate.load(value.value),
          ))!;
          expect(find.text(l.formSaveFailed), findsOneWidget);
          expect(adapter.writes, hasLength(1));
          adapter.writeMode = 'specific';
          await t.tap(find.text(l.save));
          await settle(t);
          expect(find.text('Original <server detail> {keep}'), findsOneWidget);
          value.value = target;
          await settle(t);
          l = (await t.runAsync(
            () => AppLocalizations.delegate.load(value.value),
          ))!;
          expect(find.text('Original <server detail> {keep}'), findsOneWidget);
          adapter.writeMode = 'success';
          await t.tap(find.text(l.save));
          await settle(t);
          expect(find.byType(AlertDialog), findsNothing);
          expect(adapter.writes, hasLength(3));
          final expected = users
              ? {
                  'username': 'synthetic.user',
                  'full_name': 'Original <name> {keep}',
                  'role': 'admin',
                  'company_id': 41,
                  'password': 'Synthetic-only!41',
                  'linked_employee_id': 42,
                  'actor_user_id': 71,
                }
              : {
                  'company_id': 41,
                  'name': 'Original <unit> {keep}',
                  'unit_type': 'embarcacao',
                  'city': 'Macaé',
                  'notes': 'Original <notes> {keep}',
                  'actor_user_id': 71,
                };
          for (final call in adapter.writes) {
            expect(call.method, 'POST');
            expect(call.path, users ? '/api/users' : '/api/units');
            expect(call.data, expected);
            expect(call.headers['Authorization'], 'Bearer synthetic-access');
          }
          expect(t.takeException(), isNull);
          await t.pumpWidget(const SizedBox());
        },
      );
    }
    for (final role in ['general_admin', 'user']) {
      testWidgets(
        '${target.toLanguageTag()} archival policy preserves minimum, scope and edit gate $role',
        (t) async {
          final adapter = FormsAdapter();
          final value = await mount(
            t,
            target,
            const ArchivalPolicyScreen(companyId: 41),
            adapter,
            role: role,
          );
          var l = (await t.runAsync(
            () => AppLocalizations.delegate.load(target),
          ))!;
          expect(find.text(l.archivalPolicyIntro), findsOneWidget);
          expect(find.text(l.archivalPpeRecordRule), findsOneWidget);
          expect(adapter.calls.single.queryParameters, {'company_id': 41});
          final fields = find.byType(TextField);
          expect(fields, findsNWidgets(3));
          expect(
            t.widgetList<TextField>(fields).map((f) => f.controller!.text),
            ['5', '6', '7'],
          );
          expect(
            t
                .widgetList<TextField>(fields)
                .every((f) => f.enabled == (role == 'general_admin')),
            isTrue,
          );
          if (role == 'user') {
            expect(find.text(l.archivalSave), findsNothing);
            expect(adapter.writes, isEmpty);
          } else {
            await t.enterText(fields.at(0), '4');
            await t.ensureVisible(find.text(l.archivalSave));
            await t.tap(find.text(l.archivalSave));
            await settle(t);
            expect(find.text(l.archivalInvalidPeriods), findsOneWidget);
            expect(adapter.writes, isEmpty);
            value.value = locales[(i + 1) % locales.length];
            await settle(t);
            l = (await t.runAsync(
              () => AppLocalizations.delegate.load(value.value),
            ))!;
            expect(find.text(l.archivalInvalidPeriods), findsOneWidget);
            expect(adapter.calls, hasLength(1));
            expect(t.widget<TextField>(fields.at(0)).controller!.text, '4');
            await t.enterText(fields.at(0), '10');
            await t.ensureVisible(find.text(l.archivalSave));
            await t.tap(find.text(l.archivalSave));
            await settle(t);
            expect(adapter.writes.single.method, 'PUT');
            expect(adapter.writes.single.data, {
              'actor_user_id': 71,
              'unit_retention_years': 10,
              'epi_retention_years': 6,
              'employee_retention_years': 7,
              'company_id': 41,
            });
            expect(find.text(l.archivalSaved), findsOneWidget);
            value.value = target;
            await settle(t);
            l = (await t.runAsync(
              () => AppLocalizations.delegate.load(value.value),
            ))!;
            expect(find.text(l.archivalSaved), findsOneWidget);
            expect(adapter.calls, hasLength(2));
          }
          expect(t.takeException(), isNull);
          await t.pumpWidget(const SizedBox());
        },
      );
    }
    testWidgets(
      '${target.toLanguageTag()} archival load failure follows locale without retrying',
      (t) async {
        final adapter = FormsAdapter()..loadDenied = true;
        final value = await mount(
          t,
          target,
          const ArchivalPolicyScreen(companyId: 41),
          adapter,
        );
        var l = (await t.runAsync(
          () => AppLocalizations.delegate.load(target),
        ))!;
        expect(find.text(l.archivalLoadFailed), findsOneWidget);
        value.value = locales[(i + 1) % locales.length];
        await settle(t);
        l = (await t.runAsync(
          () => AppLocalizations.delegate.load(value.value),
        ))!;
        expect(find.text(l.archivalLoadFailed), findsOneWidget);
        expect(adapter.calls, hasLength(1));
        expect(adapter.writes, isEmpty);
        expect(t.takeException(), isNull);
        await t.pumpWidget(const SizedBox());
      },
    );
  }
  test('unknown role and type labels remain opaque', () async {
    final l = await AppLocalizations.delegate.load(const Locale('en', 'US'));
    expect(appRoleLabel('unknown <role> {keep}', l), 'unknown <role> {keep}');
    expect(
      appUnitTypeLabel('unknown <type> {keep}', l),
      'unknown <type> {keep}',
    );
  });
}
