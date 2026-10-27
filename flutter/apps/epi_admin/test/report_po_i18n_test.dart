import 'dart:convert';
import 'package:dio/dio.dart';
import 'package:epi_admin/core/api/api_client.dart';
import 'package:epi_admin/core/i18n/generated/app_localizations.dart';
import 'package:epi_admin/features/purchases/po_supplier_screen.dart';
import 'package:epi_admin/features/reports/reports_screen.dart';
import 'package:epi_design/epi_design.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:intl/intl.dart';

class RecordingAdapter implements HttpClientAdapter {
  final writes = <RequestOptions>[];
  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? stream,
    Future<void>? cancel,
  ) async {
    if (options.method == 'POST') writes.add(options);
    final body = options.path.endsWith('/tracking')
        ? {'item': {}}
        : options.path == '/api/report-requests'
        ? {'items': []}
        : <String, dynamic>{};
    return ResponseBody.fromString(
      jsonEncode(body),
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
  final adapter = RecordingAdapter();
  setUpAll(() async {
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(
          const MethodChannel('plugins.it_nomads.com/flutter_secure_storage'),
          (call) async => null,
        );
    await ApiClient.init(baseUrl: 'https://synthetic.local');
    ApiClient.debugDio.httpClientAdapter = adapter;
  });
  setUp(adapter.writes.clear);
  Future<AppLocalizations> mount(
    WidgetTester tester,
    Locale locale,
    Widget home,
  ) async {
    await tester.runAsync(() => AppLocalizations.delegate.load(locale));
    await tester.pumpWidget(
      MaterialApp(
        theme: EpiTheme.light,
        locale: locale,
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        supportedLocales: AppLocalizations.supportedLocales,
        home: home,
      ),
    );
    await tester.runAsync(
      () => Future<void>.delayed(const Duration(milliseconds: 30)),
    );
    await tester.pumpAndSettle();
    return AppLocalizations.of(tester.element(find.byWidget(home)));
  }

  for (final locale in [
    const Locale('pt', 'BR'),
    const Locale('en', 'US'),
    const Locale('es', 'ES'),
    const Locale('fr', 'FR'),
    const Locale('no', 'NO'),
  ]) {
    testWidgets(
      'report month labels preserve numeric period and original notes $locale',
      (tester) async {
        final l = await mount(tester, locale, const ReportsScreen());
        await tester.tap(find.text(l.reportsGenerate));
        await tester.pumpAndSettle();
        var fields = find.byType(DropdownButton<int>);
        final year = tester.widget<DropdownButton<int>>(fields.at(0));
        final month = tester.widget<DropdownButton<int>>(fields.at(1));
        expect(
          month.items!.map((item) => item.value),
          List.generate(12, (i) => i + 1),
        );
        for (var index = 0; index < 12; index++) {
          expect(
            (month.items![index].child as Text).data,
            DateFormat.MMMM(l.localeName).format(DateTime(2000, index + 1)),
          );
        }
        year.onChanged!(2026);
        month.onChanged!(3);
        await tester.pump();
        await tester.enterText(find.byType(TextField), 'Original {notes}');
        await tester.tap(find.text(l.reportsRequestSubmit));
        await tester.runAsync(
          () => Future<void>.delayed(const Duration(milliseconds: 30)),
        );
        await tester.pumpAndSettle();
        expect(adapter.writes.length, 1);
        expect(adapter.writes.single.path, '/api/report-requests');
        expect(adapter.writes.single.data, {
          'period_year': 2026,
          'period_month': 3,
          'notes': 'Original {notes}',
        });
        expect(tester.takeException(), isNull);
      },
    );
    testWidgets(
      'PO translated labels retain canonical confirmation code $locale',
      (tester) async {
        final l = await mount(
          tester,
          locale,
          const PoSupplierScreen(
            order: {'id': 43, 'status': 'approved', 'po_number': 'Original-43'},
          ),
        );
        await tester.tap(find.text(l.poRegisterConfirmation));
        await tester.pumpAndSettle();
        final dropdown = tester.widget<DropdownButton<String>>(
          find.byType(DropdownButton<String>),
        );
        expect(dropdown.items!.map((item) => item.value), [
          'confirmed',
          'delivery_update',
          'rejected',
        ]);
        expect(dropdown.items!.map((item) => (item.child as Text).data), [
          l.poSupplierConfirmed,
          l.poSupplierDeliveryUpdated,
          l.poSupplierRejected,
        ]);
        dropdown.onChanged!('delivery_update');
        await tester.pump();
        final fields = find.byType(TextField);
        await tester.enterText(fields.at(0), '2026-12-21');
        await tester.enterText(fields.at(1), 'Original carrier');
        await tester.enterText(fields.at(2), '00123');
        await tester.enterText(fields.at(3), 'Original {comment}');
        await tester.tap(find.text(l.save));
        await tester.runAsync(
          () => Future<void>.delayed(const Duration(milliseconds: 30)),
        );
        await tester.pumpAndSettle();
        expect(adapter.writes.length, 1);
        expect(
          adapter.writes.single.path,
          '/api/purchase-orders/43/confirmation',
        );
        expect(adapter.writes.single.data, {
          'status': 'delivery_update',
          'delivery_forecast': '2026-12-21',
          'carrier': 'Original carrier',
          'tracking_code': '00123',
          'comment': 'Original {comment}',
          'actor_user_id': 0,
        });
        expect(tester.takeException(), isNull);
      },
    );
  }
}
