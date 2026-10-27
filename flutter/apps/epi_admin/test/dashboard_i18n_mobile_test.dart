import 'dart:convert';
import 'package:dio/dio.dart';
import 'package:epi_admin/core/api/api_client.dart';
import 'package:epi_admin/core/bloc/auth_cubit.dart';
import 'package:epi_admin/core/i18n/generated/app_localizations.dart';
import 'package:epi_admin/features/dashboard/dashboard_screen.dart';
import 'package:epi_design/epi_design.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:intl/intl.dart';

class SummaryAdapter implements HttpClientAdapter {
  int requests = 0;
  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? stream,
    Future<void>? cancel,
  ) async {
    requests++;
    expect(options.path, '/api/dashboard/summary');
    return ResponseBody.fromString(
      jsonEncode({
        'scope': {'company_id': 41, 'unit_id': 42, 'locked': true},
        'kpis': {
          'deliveries_today': 12345678,
          'expiring_epis': 1234,
          'critical_stock': 1234,
          'pending_purchases': 1234,
        },
        'alerts': [
          {
            'title': 'Legacy title',
            'description': 'Legacy description',
            'type': 'warning',
            'category': 'physical_unknown',
            'company_id': 41,
            'unit_id': 42,
            'epi_id': 43,
            'presentation': {
              'title_key': 'operationalAlerts.physical_unknown.title',
              'description_key': 'operationalAlerts.physicalDescription',
              'params': {'epi': 'Original <Luva> {count}', 'count': 1234},
            },
          },
        ],
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
    'real dashboard in all five languages fits mobile and larger text without refetch',
    (tester) async {
      TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
          .setMockMethodCallHandler(
            const MethodChannel('plugins.it_nomads.com/flutter_secure_storage'),
            (call) async => null,
          );
      await ApiClient.init(baseUrl: 'https://synthetic.local');
      final adapter = SummaryAdapter();
      ApiClient.debugDio.httpClientAdapter = adapter;
      final auth = AuthCubit();
      addTearDown(auth.close);
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);
      tester.view.devicePixelRatio = 1;
      for (final size in [
        const Size(1000, 1600),
        const Size(390, 844),
        const Size(320, 640),
      ]) {
        tester.view.physicalSize = size;
        for (final scale in [1.0, 1.3]) {
          for (final locale in [
            const Locale('pt', 'BR'),
            const Locale('en', 'US'),
            const Locale('es', 'ES'),
            const Locale('fr', 'FR'),
            const Locale('no', 'NO'),
          ]) {
            await tester.pumpWidget(
              MaterialApp(
                theme: EpiTheme.light,
                locale: locale,
                localizationsDelegates: AppLocalizations.localizationsDelegates,
                supportedLocales: AppLocalizations.supportedLocales,
                builder: (context, child) => MediaQuery(
                  data: MediaQuery.of(
                    context,
                  ).copyWith(textScaler: TextScaler.linear(scale)),
                  child: child!,
                ),
                home: BlocProvider.value(
                  value: auth,
                  child: const DashboardScreen(),
                ),
              ),
            );
            await tester.runAsync(
              () => Future<void>.delayed(const Duration(milliseconds: 30)),
            );
            await tester.pumpAndSettle();
            final l = AppLocalizations.of(
              tester.element(find.byType(DashboardScreen)),
            );
            await tester.scrollUntilVisible(
              find.text(
                NumberFormat.decimalPattern(l.localeName).format(12345678),
              ),
              -300,
              scrollable: find.byType(Scrollable).first,
            );
            await tester.pumpAndSettle();
            expect(
              find.text(
                NumberFormat.decimalPattern(l.localeName).format(12345678),
              ),
              findsOneWidget,
            );
            await tester.scrollUntilVisible(
              find.text(l.operationalAlertPhysicalUnknownTitle),
              200,
              scrollable: find.byType(Scrollable).first,
            );
            await tester.pumpAndSettle();
            expect(
              find.text(
                l.operationalAlertPhysicalDescription(
                  1234,
                  NumberFormat.decimalPattern(l.localeName).format(1234),
                  'Original <Luva> {count}',
                ),
              ),
              findsOneWidget,
            );
            expect(
              tester.takeException(),
              isNull,
              reason: '$locale $size scale $scale',
            );
          }
        }
      }
      expect(adapter.requests, 1);
      await tester.pumpWidget(const SizedBox());
    },
  );
}
