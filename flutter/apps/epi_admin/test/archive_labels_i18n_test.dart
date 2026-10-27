import 'dart:convert';
import 'package:dio/dio.dart';
import 'package:epi_admin/core/api/api_client.dart';
import 'package:epi_admin/core/bloc/auth_cubit.dart';
import 'package:epi_admin/core/i18n/generated/app_localizations.dart';
import 'package:epi_admin/features/employees/employees_screen.dart';
import 'package:epi_design/epi_design.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:flutter_test/flutter_test.dart';

class EmployeesAdapter implements HttpClientAdapter {
  final requests = <RequestOptions>[];
  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? stream,
    Future<void>? cancel,
  ) async {
    requests.add(options);
    expect(options.method, 'GET');
    expect([
      '/api/bootstrap',
      '/api/employees/archived',
    ], contains(options.path));
    return ResponseBody.fromString(
      jsonEncode({
        'employees': options.path == '/api/bootstrap'
            ? [
                {
                  'id': 43,
                  'name': 'Original <name> {label}',
                  'employee_id_code': '00043',
                  'unit_id': 42,
                  'company_id': 41,
                  'active': 1,
                },
              ]
            : [],
      }),
      200,
      headers: {
        Headers.contentTypeHeader: ['application/json'],
      },
    );
  }

  @override
  void close({bool force = false}) {}
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  testWidgets(
    'real employee popup and archive dialog update existing labels without changing values or input',
    (tester) async {
      TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
          .setMockMethodCallHandler(
            const MethodChannel('plugins.it_nomads.com/flutter_secure_storage'),
            (call) async => null,
          );
      await ApiClient.init(baseUrl: 'https://synthetic.local');
      final adapter = EmployeesAdapter();
      ApiClient.debugDio.httpClientAdapter = adapter;
      final auth = AuthCubit();
      addTearDown(auth.close);
      final locale = ValueNotifier(const Locale('pt', 'BR'));
      addTearDown(locale.dispose);
      await tester.runAsync(() => AppLocalizations.delegate.load(locale.value));
      await tester.pumpWidget(
        ValueListenableBuilder<Locale>(
          valueListenable: locale,
          builder: (context, value, child) => MaterialApp(
            theme: EpiTheme.light,
            locale: value,
            localizationsDelegates: AppLocalizations.localizationsDelegates,
            supportedLocales: AppLocalizations.supportedLocales,
            home: BlocProvider.value(
              value: auth,
              child: const EmployeesScreen(),
            ),
          ),
        ),
      );
      await tester.runAsync(
        () => Future<void>.delayed(const Duration(milliseconds: 30)),
      );
      await tester.pumpAndSettle();
      expect(find.text('Original <name> {label}'), findsOneWidget);
      await tester.tap(find.byType(PopupMenuButton<String>));
      await tester.pumpAndSettle();
      final initialReads = adapter.requests.length;
      for (final target in [
        const Locale('pt', 'BR'),
        const Locale('en', 'US'),
        const Locale('es', 'ES'),
        const Locale('fr', 'FR'),
        const Locale('no', 'NO'),
      ]) {
        locale.value = target;
        await tester.pump();
        await tester.runAsync(
          () => Future<void>.delayed(const Duration(milliseconds: 30)),
        );
        await tester.pumpAndSettle();
        final l = AppLocalizations.of(
          tester.element(find.byType(EmployeesScreen)),
        );
        final item = find.ancestor(
          of: find.text(l.archive),
          matching: find.byType(PopupMenuItem<String>),
        );
        expect(item, findsOneWidget);
        expect(tester.widget<PopupMenuItem<String>>(item).value, 'archive');
        expect(adapter.requests.length, initialReads);
      }
      var l = AppLocalizations.of(tester.element(find.byType(EmployeesScreen)));
      await tester.tap(find.text(l.archive));
      await tester.pumpAndSettle();
      final field = find.descendant(
        of: find.byType(AlertDialog),
        matching: find.byType(TextField),
      );
      await tester.enterText(field, 'Original {reason} <unchanged>');
      for (final target in [
        const Locale('fr', 'FR'),
        const Locale('en', 'US'),
      ]) {
        locale.value = target;
        await tester.pump();
        await tester.runAsync(
          () => Future<void>.delayed(const Duration(milliseconds: 30)),
        );
        await tester.pumpAndSettle();
        l = AppLocalizations.of(tester.element(find.byType(EmployeesScreen)));
        expect(find.text(l.archiveReasonLabel), findsOneWidget);
        expect(find.text(l.archive), findsOneWidget);
        expect(find.text(l.cancel), findsOneWidget);
        expect(
          tester.widget<TextField>(field).controller!.text,
          'Original {reason} <unchanged>',
        );
        expect(adapter.requests.length, initialReads);
      }
      await tester.tap(find.text(l.cancel));
      await tester.pumpAndSettle();
      expect(
        adapter.requests.every((request) => request.method == 'GET'),
        isTrue,
      );
      expect(tester.takeException(), isNull);
      await tester.pumpWidget(const SizedBox());
    },
  );
}
