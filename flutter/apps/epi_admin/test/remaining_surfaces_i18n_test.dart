import 'package:epi_admin/core/bloc/companies_cubit.dart';
import 'package:epi_admin/core/widgets/create_company_dialog.dart';
import 'package:epi_admin/features/epis/epi_detail_screen.dart';
import 'package:epi_admin/features/employees/employee_detail_screen.dart';
import 'package:epi_api/epi_api.dart';
import 'dart:convert';
import 'package:dio/dio.dart';
import 'package:epi_admin/core/api/api_client.dart';
import 'package:epi_admin/core/bloc/auth_cubit.dart';
import 'package:epi_admin/core/bloc/auth_state.dart';
import 'package:epi_admin/core/i18n/entity_labels.dart';
import 'package:epi_admin/core/i18n/generated/app_localizations.dart';
import 'package:epi_admin/core/i18n/presentation_formatters.dart';
import 'package:epi_admin/core/notifications/notification_overlay.dart';
import 'package:epi_admin/core/notifications/notification_service.dart';
import 'package:epi_admin/core/session/session_context.dart';
import 'package:epi_admin/features/employees/employees_screen.dart';
import 'package:epi_admin/features/epis/epis_screen.dart';
import 'package:epi_admin/features/units/units_screen.dart';
import 'package:epi_admin/features/settings/module_visibility_screen.dart';
import 'package:epi_design/epi_design.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:intl/date_symbol_data_local.dart';

const locales = [
  Locale('pt', 'BR'),
  Locale('en', 'US'),
  Locale('es', 'ES'),
  Locale('fr', 'FR'),
  Locale('no', 'NO'),
];
const originalName = 'Original <name> {name}';
const originalReason = 'Original <reason> {reason}';
const original = <String, dynamic>{
  'id': 43,
  'name': originalName,
  'employee_id_code': '00043',
  'company_id': 41,
  'unit_id': 42,
  'unit_name': 'Original Unit',
  'active': 1,
  'ca': '000CA',
  'unit_type': 'base',
  'company_name': 'Original Company',
  'archived_at': '2026-03-02T23:45:00Z',
  'archive_reason': originalReason,
  'retention_days_remaining': 1234,
};
SessionContext session(String role) => SessionContext(
  userId: 71,
  companyId: 41,
  unitId: 42,
  role: role,
  permissions: const ['employees:create', 'epis:create', 'units:create'],
  tenantName: 'Original Company',
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

class SurfaceAdapter implements HttpClientAdapter {
  final calls = <RequestOptions>[];
  bool failModuleLoad = false;
  bool emptyArchives = false;
  @override
  Future<ResponseBody> fetch(
    RequestOptions o,
    Stream<Uint8List>? stream,
    Future<void>? cancel,
  ) async {
    calls.add(o);
    Map<String, dynamic> data = {};
    var status = 200;
    if (o.path == '/api/bootstrap') {
      data = {
        'employees': [original],
        'epis': [original],
        'units': [original],
      };
    } else if (o.path.endsWith('/archived')) {
      data = {
        'items': emptyArchives ? [] : [original],
        'employees': emptyArchives ? [] : [original],
        'epis': emptyArchives ? [] : [original],
        'units': emptyArchives ? [] : [original],
      };
    } else if (o.path.endsWith('/archival-state')) {
      data = {
        'archival_state': {'has_open_links': false},
      };
    } else if (o.path == '/api/module-visibility') {
      if (failModuleLoad) {
        status = 500;
      } else {
        data = {
          'module_visibility': {
            'admin': {
              '*': {'estoque': false},
            },
          },
          'default_module_visibility': {
            'admin': {'dashboard': true},
          },
        };
      }
    } else if (o.path == '/api/companies' && o.method == 'GET') {
      data = {'items': []};
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
}

Future<void> settle(WidgetTester t) async {
  await t.runAsync(
    () => Future<void>.delayed(const Duration(milliseconds: 40)),
  );
  await t.pumpAndSettle();
}

Future<void> mount(
  WidgetTester t,
  Widget child,
  ValueNotifier<Locale> locale,
  AuthCubit auth,
) async {
  await t.runAsync(() => AppLocalizations.delegate.load(locale.value));
  await t.pumpWidget(
    ValueListenableBuilder<Locale>(
      valueListenable: locale,
      builder: (_, value, __) => MaterialApp(
        locale: value,
        theme: EpiTheme.light,
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        supportedLocales: AppLocalizations.supportedLocales,
        home: BlocProvider.value(value: auth, child: child),
      ),
    ),
  );
  await settle(t);
}

Future<AppLocalizations> switchLocale(
  WidgetTester t,
  ValueNotifier<Locale> locale,
  Locale target,
) async {
  final l = await t.runAsync(() => AppLocalizations.delegate.load(target));
  locale.value = target;
  await t.pump();
  await settle(t);
  return l!;
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  setUpAll(() => initializeDateFormatting());
  late SurfaceAdapter adapter;
  var initialized = false;
  setUp(() async {
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(
          const MethodChannel('plugins.it_nomads.com/flutter_secure_storage'),
          (call) async =>
              call.method == 'read' && call.arguments['key'] == 'access_token'
              ? 'synthetic-access'
              : null,
        );
    if (!initialized) {
      await ApiClient.init(baseUrl: 'https://synthetic.local');
      initialized = true;
    }
    await ApiClient.saveSessionContext(session('general_admin'));
    adapter = SurfaceAdapter();
    ApiClient.debugDio.httpClientAdapter = adapter;
  });
  for (final entity in ['employee', 'epi', 'unit']) {
    testWidgets('$entity archive dialog accommodates mobile text scale in five locales', (t) async {
      t.view.physicalSize = const Size(390, 844); t.view.devicePixelRatio = 1;
      t.platformDispatcher.textScaleFactorTestValue = 1.3;
      addTearDown(t.view.resetPhysicalSize); addTearDown(t.view.resetDevicePixelRatio);
      addTearDown(t.platformDispatcher.clearTextScaleFactorTestValue);
      final auth = TestAuth('general_admin'); addTearDown(auth.close);
      final locale = ValueNotifier(locales.first); addTearDown(locale.dispose);
      final Widget screen = switch (entity) { 'employee' => const EmployeesScreen(), 'epi' => const EpisScreen(), _ => const UnitsScreen() };
      await mount(t, screen, locale, auth);
      await t.tap(find.byType(PopupMenuButton<String>)); await settle(t);
      final initial = AppLocalizations.of(t.element(find.byType(screen.runtimeType)));
      await t.tap(find.text(initial.archive)); await settle(t);
      final reads = adapter.calls.length;
      for (final target in locales) {
        final l = await switchLocale(t, locale, target);
        expect(find.text(switch (entity) { 'employee' => l.employeeArchiveTitle, 'epi' => l.epiArchiveTitle, _ => l.unitArchiveTitle }), findsOneWidget);
        expect(find.descendant(of: find.byType(AlertDialog), matching: find.text(l.cancel)), findsOneWidget);
        expect(t.takeException(), isNull);
        expect(adapter.calls.length, reads);
      }
    });
  }
  for (final entity in ['employee', 'epi', 'unit']) {
    testWidgets(
      '$entity archive and restore locale preserves reason and mutation identity',
      (t) async {
        final auth = TestAuth('general_admin');
        addTearDown(auth.close);
        final locale = ValueNotifier(locales.first);
        addTearDown(locale.dispose);
        final Widget screen = switch (entity) {
          'employee' => const EmployeesScreen(),
          'epi' => const EpisScreen(),
          _ => const UnitsScreen(),
        };
        await mount(t, screen, locale, auth);
        expect(find.text(originalName), findsOneWidget);
        await t.tap(find.byType(PopupMenuButton<String>));
        await settle(t);
        var l = AppLocalizations.of(t.element(find.byType(screen.runtimeType)));
        final menuReads = adapter.calls.length;
        for (final target in locales) {
          l = await switchLocale(t, locale, target);
          expect(find.text(l.edit), findsOneWidget);
          expect(find.text(l.archive), findsOneWidget);
          final entries = t.widgetList<PopupMenuItem<String>>(find.byType(PopupMenuItem<String>));
          expect(entries.map((item) => item.value).toSet(), {'edit', 'archive'});
          expect(adapter.calls.length, menuReads);
        }
        await t.tap(find.text(l.archive));
        await settle(t);
        final field = find.descendant(
          of: find.byType(AlertDialog),
          matching: find.byType(TextField),
        );
        await t.enterText(field, originalReason);
        final reads = adapter.calls.length;
        for (final target in locales) {
          l = await switchLocale(t, locale, target);
          final title = switch (entity) {
            'employee' => l.employeeArchiveTitle,
            'epi' => l.epiArchiveTitle,
            _ => l.unitArchiveTitle,
          };
          final body = switch (entity) {
            'employee' => l.employeeArchiveBody(originalName),
            'epi' => l.epiArchiveBody(originalName),
            _ => l.unitArchiveBody(originalName),
          };
          expect(find.text(title), findsOneWidget);
          expect(find.text(body), findsOneWidget);
          expect(t.widget<TextField>(field).controller!.text, originalReason);
          expect(adapter.calls.length, reads);
        }
        await t.tap(
          find.descendant(
            of: find.byType(AlertDialog),
            matching: find.text(l.archive),
          ),
        );
        await settle(t);
        final writes = adapter.calls.where((o) => o.method != 'GET').toList();
        expect(writes, hasLength(1));
        expect(writes.single.method, 'POST');
        final path = switch (entity) {
          'employee' => 'employees',
          'epi' => 'epis',
          _ => 'units',
        };
        expect(writes.single.path, '/api/$path/43/archive');
        expect(writes.single.data['actor_user_id'], 71);
        expect(writes.single.data['reason'], originalReason);
        expect(
          writes.single.headers['Authorization'],
          'Bearer synthetic-access',
        );
        final tooltip = switch (entity) {
          'employee' => l.employeeShowArchived,
          'epi' => l.epiShowArchived,
          _ => l.unitShowArchived,
        };
        await t.tap(find.byTooltip(tooltip));
        await settle(t);
        final beforeRestore = adapter.calls.length;
        for (final target in locales) {
          l = await switchLocale(t, locale, target);
          expect(find.textContaining(originalReason), findsOneWidget);
          expect(
            find.textContaining(
              l.retentionRemainingDays(
                1234,
                formatDisplayCount(1234, l.localeName),
              ),
            ),
            findsOneWidget,
          );
          expect(
            find.textContaining(
              (entity == 'unit' ? l.unitArchivedOnDate : l.archivedOnDate)(formatDisplayDate('2026-03-02', l.localeName)),
            ),
            findsOneWidget,
          );
          expect(adapter.calls.length, beforeRestore);
        }
        await t.tap(find.text(l.restore));
        await settle(t);
        for (final target in locales) {
          l = await switchLocale(t, locale, target);
          expect(
            find.text(switch (entity) {
              'employee' => l.employeeRestoreTitle,
              'epi' => l.epiRestoreTitle,
              _ => l.unitRestoreTitle,
            }),
            findsOneWidget,
          );
        }
        await t.tap(
          find.descendant(
            of: find.byType(AlertDialog),
            matching: find.text(l.restore),
          ),
        );
        await settle(t);
        final last = adapter.calls.lastWhere((o) => o.method != 'GET');
        expect(last.path, '/api/$path/43/restore');
        expect(last.data, {'actor_user_id': 71});
      },
    );
  }
  testWidgets(
    'module labels, defaults and scoped canonical toggle survive locale changes',
    (t) async {
      final auth = TestAuth('general_admin');
      addTearDown(auth.close);
      final locale = ValueNotifier(locales.first);
      addTearDown(locale.dispose);
      await mount(t, const ModuleVisibilityScreen(companyId: 41), locale, auth);
      final reads = adapter.calls.length;
      for (final target in locales) {
        final l = await switchLocale(t, locale, target);
        expect(find.text(l.moduleRequests), findsOneWidget);
        expect(find.text(l.moduleAdministration), findsOneWidget);
        expect(find.text(l.roleLocalAdmin), findsOneWidget);
        expect(adapter.calls.length, reads);
      }
      final tile = t.widget<SwitchListTile>(find.byType(SwitchListTile).at(2));
      tile.onChanged!(true);
      await settle(t);
      final write = adapter.calls.singleWhere((o) => o.method != 'GET');
      expect(write.method, 'POST');
      expect(write.data['role'], 'admin');
      expect(write.data, {
        'actor_user_id': 71,
        'role': 'admin',
        'modules': {'estoque': true},
        'company_id': 41,
      });
    },
  );
  testWidgets(
    'visible local notification retranslates; remote content stays opaque',
    (t) async {
      final auth = TestAuth('general_admin');
      addTearDown(auth.close);
      final locale = ValueNotifier(locales.first);
      addTearDown(locale.dispose);
      await mount(
        t,
        const Scaffold(body: NotificationOverlay(child: SizedBox())),
        locale,
        auth,
      );
      NotificationService().simulateNotification(
        const AppNotification(
          title: 'legacy',
          body: 'legacy',
          data: {'original': 'value'},
          criticalStockCount: 1234,
        ),
      );
      await t.pump();
      await t.pump(const Duration(milliseconds: 300));
      for (final target in locales) {
        final l = await switchLocale(t, locale, target);
        expect(find.text(l.criticalStockTitle), findsOneWidget);
        expect(
          find.text(
            l.criticalStockBody(1234, formatDisplayCount(1234, l.localeName)),
          ),
          findsOneWidget,
        );
      }
      NotificationService().simulateNotification(
        const AppNotification(
          title: 'Original título',
          body: 'Original message {count}',
          data: {'criticalStockCount': 1234},
        ),
      );
      await t.pump();
      await t.pump(const Duration(milliseconds: 300));
      for (final target in locales) {
        await switchLocale(t, locale, target);
        expect(find.text('Original título'), findsOneWidget);
        expect(find.text('Original message {count}'), findsOneWidget);
      }
      expect(adapter.calls, isEmpty);
      await t.pump(const Duration(seconds: 6));
      await t.pumpAndSettle();
    },
  );
  for (final entity in ['employee', 'epi', 'unit']) {
    testWidgets('$entity empty archived state follows five locales without refetch', (t) async {
      final auth = TestAuth('general_admin'); addTearDown(auth.close);
      final locale = ValueNotifier(locales.first); addTearDown(locale.dispose);
      adapter.emptyArchives = true;
      final Widget screen = switch (entity) { 'employee' => const EmployeesScreen(), 'epi' => const EpisScreen(), _ => const UnitsScreen() };
      await mount(t, screen, locale, auth);
      var l = AppLocalizations.of(t.element(find.byType(screen.runtimeType)));
      await t.tap(find.byTooltip(switch (entity) { 'employee' => l.employeeShowArchived, 'epi' => l.epiShowArchived, _ => l.unitShowArchived }));
      await settle(t); final reads = adapter.calls.length;
      for (final target in locales) {
        l = await switchLocale(t, locale, target);
        expect(find.text(switch (entity) { 'employee' => l.employeeArchivedEmpty, 'epi' => l.epiArchivedEmpty, _ => l.unitArchivedEmpty }), findsOneWidget);
        expect(adapter.calls.length, reads);
        expect(adapter.calls.every((o) => o.method == 'GET'), true);
      }
    });
  }
  testWidgets(
    'company dialog live validation and selected plan keep canonical creation contract',
    (t) async {
      final auth = TestAuth('master_admin');
      addTearDown(auth.close);
      final cubit = CompaniesCubit();
      addTearDown(cubit.close);
      final locale = ValueNotifier(locales.first);
      addTearDown(locale.dispose);
      await mount(
        t,
        Scaffold(
          body: Builder(
            builder: (context) => TextButton(
              onPressed: () => CreateCompanyDialog.show(context, cubit, 71),
              child: const Text('open'),
            ),
          ),
        ),
        locale,
        auth,
      );
      await t.tap(find.text('open'));
      await settle(t);
      var l = AppLocalizations.of(t.element(find.byType(CreateCompanyDialog)));
      await t.tap(find.text(l.add));
      await settle(t);
      expect(find.text(l.required), findsWidgets);
      l = await switchLocale(t, locale, locales[3]);
      expect(find.text(l.required), findsWidgets);
      expect(find.text(l.companyNewTitle), findsOneWidget);
      final fields = find.byType(TextFormField);
      expect(fields, findsNWidgets(6));
      for (final entry in {
        0: 'Original Company',
        1: 'Original Legal',
        2: '11.222.333/0001-81',
        4: 'Original Owner',
        5: 'Owner@Example.Test',
      }.entries) {
        await t.ensureVisible(fields.at(entry.key));
        await t.enterText(fields.at(entry.key), entry.value);
      }
      final dropdown = t.widget<DropdownButtonFormField<String>>(
        find.byType(DropdownButtonFormField<String>),
      );
      dropdown.onChanged!('business');
      await settle(t);
      expect(t.widget<TextFormField>(fields.at(3)).controller!.text, '11');
      for (final target in locales) {
        l = await switchLocale(t, locale, target);
        expect(
          t.widget<TextFormField>(fields.at(0)).controller!.text,
          'Original Company',
        );
        expect(t.widget<TextFormField>(fields.at(3)).controller!.text, '11');
        expect(adapter.calls, isEmpty);
      }
      await t.tap(find.text(l.add));
      await settle(t);
      final write = adapter.calls.singleWhere((o) => o.method != 'GET');
      expect(write.path, '/api/companies');
      expect(write.method, 'POST');
      expect(write.headers['Authorization'], 'Bearer synthetic-access');
      expect(write.data, {
        'actor_user_id': 71,
        'name': 'Original Company',
        'legal_name': 'Original Legal',
        'cnpj': '11222333000181',
        'plan_name': 'business',
        'user_limit': 11,
        'license_status': 'active',
        'active': 1,
        'general_admin_email': 'owner@example.test',
        'general_admin_name': 'Original Owner',
      });
    },
  );
  testWidgets(
    'real detail widgets localize sections and days without translating identity',
    (t) async {
      final auth = TestAuth('general_admin');
      addTearDown(auth.close);
      final locale = ValueNotifier(locales.first);
      addTearDown(locale.dispose);
      final epi = Epi.fromJson({
        ...original,
        'code': '000CODE',
        'validity_days': 1234,
      });
      await mount(t, EpiDetailScreen(epi: epi), locale, auth);
      for (final target in locales) {
        final l = await switchLocale(t, locale, target);
        await t.drag(find.byType(ListView), const Offset(0, -500));
        await settle(t);
        expect(find.text('000CA'), findsOneWidget);
        expect(find.text('000CODE'), findsOneWidget);
        expect(find.text(l.epiIdentificationSection), findsOneWidget);
        expect(
          find.text(
            l.operationalAlertDays(
              1234,
              formatDisplayCount(1234, l.localeName),
            ),
          ),
          findsOneWidget,
        );
      }
      await mount(
        t,
        EmployeeDetailScreen(employee: Employee.fromJson(original)),
        locale,
        auth,
      );
      for (final target in locales) {
        final l = await switchLocale(t, locale, target);
        expect(find.text(l.employeeDetailsSection), findsOneWidget);
        expect(find.text('00043'), findsOneWidget);
      }
      expect(adapter.calls, isEmpty);
    },
  );
  testWidgets(
    'module load failure retranslates and read-only actor never gets enabled switches',
    (t) async {
      final auth = TestAuth('user');
      addTearDown(auth.close);
      final locale = ValueNotifier(locales.first);
      addTearDown(locale.dispose);
      adapter.failModuleLoad = true;
      await mount(t, const ModuleVisibilityScreen(), locale, auth);
      final reads = adapter.calls.length;
      for (final target in locales) {
        final l = await switchLocale(t, locale, target);
        expect(find.text(l.moduleVisibilityLoadError), findsOneWidget);
        expect(
          t
              .widgetList<SwitchListTile>(find.byType(SwitchListTile))
              .every((w) => w.onChanged == null),
          true,
        );
        expect(adapter.calls.length, reads);
        expect(adapter.calls.every((o) => o.method == 'GET'), true);
      }
    },
  );

  for (final target in locales) {
    test(
      'presentation $target preserves periods, unknown codes, labels and plural counts',
      () async {
        final l = await AppLocalizations.delegate.load(target);
        for (final iso in ['', 'original', '2026-00-01', '2026-13-01']) {
          expect(formatDisplayPeriod(iso, l.localeName), iso);
        }
        expect(
          formatDisplayPeriod('2026-02-28T23:00:00-03:00', l.localeName),
          isNot(contains('Mar')),
        );
        for (final code in ['unknown {name}', 'custom/company', '000CA']) {
          expect(appModuleLabel(code, l), code);
          expect(appReturnConditionLabel(code, l), code);
          expect(appResponsibilityLabel(code, l), code);
        }
        expect(
          appResponsibilityLabel('Conforme Contrato', l),
          l.responsibilityContract,
        );
        expect(
          appCompanyKindLabel('outsourced', l),
          l.outsourcedCompanyKindOutsourced,
        );
        expect(
          appCompanyKindLabel('other_contracted', l),
          l.outsourcedCompanyKindOther,
        );
        expect(
          appCompanyKindLabel('service_provider', l),
          l.outsourcedCompanyKindServiceProvider,
        );
        for (final count in [0, 1, 2, 1234]) {
          final text = l.retentionRemainingDays(
            count,
            formatDisplayCount(count, l.localeName),
          );
          expect(text, contains(formatDisplayCount(count, l.localeName)));
          expect(text, isNot(contains('{count')));
        }
      },
    );
  }
}
