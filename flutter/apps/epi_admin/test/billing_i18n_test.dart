import 'dart:convert';
import 'package:dio/dio.dart';
import 'package:epi_admin/core/api/api_client.dart';
import 'package:epi_admin/core/i18n/generated/app_localizations.dart';
import 'package:epi_admin/core/i18n/presentation_formatters.dart';
import 'package:epi_admin/features/subscription/invoices_screen.dart';
import 'package:epi_admin/features/subscription/subscription_screen.dart';
import 'package:epi_design/epi_design.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';

const locales = [
  Locale('pt', 'BR'),
  Locale('en', 'US'),
  Locale('es', 'ES'),
  Locale('fr', 'FR'),
  Locale('no', 'NO'),
];
Map<String, dynamic> subscription() => {
  'subscription_id': 'Original-123',
  'plan_key': 'business',
  'payment_cycle': 'annual',
  'payment_method': 'card',
  'status': 'active',
  'mp_status': 'authorized',
  'amount': 1234.56,
  'currency': 'BRL',
  'next_payment_date': '2027-01-02T23:59:00-12:00',
  'last_payment_date': '2026-01-02',
  'created_at': '2026-01-02',
  'company_id': 41,
  'tenant_id': 'Original tenant',
  'preapproval_id': '00123',
};

class BillingAdapter implements HttpClientAdapter {
  final calls = <RequestOptions>[];
  bool empty = false, denied = false, cancelled = false;
  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? stream,
    Future<void>? cancel,
  ) async {
    calls.add(options);
    expect(options.headers['Authorization'], 'Bearer synthetic-token');
    final headers = {
      Headers.contentTypeHeader: ['application/json'],
    };
    if (denied) {
      return ResponseBody.fromString(
        '{"error":{"code":"FORBIDDEN","message":"Original denied detail"}}',
        403,
        headers: headers,
      );
    }
    if (options.path == '/api/subscriptions/cancel') {
      expect(options.method, 'POST');
      expect(options.data, {'reason': ''});
      cancelled = true;
    }
    final item = subscription();
    if (cancelled) item['status'] = 'cancelled';
    final data = options.path == '/api/subscriptions/invoices'
        ? {
            'invoices': empty
                ? []
                : [
                    {
                      'subscription_id': 'Original-123',
                      'mp_payment_id': '00041',
                      'payment_method': 'card',
                      'amount': 12345678.90,
                      'currency': 'BRL',
                      'status': options.queryParameters['status'] ?? 'paid',
                      'created_at': '2027-01-02T23:00:00Z',
                      'receipt_url':
                          'https://synthetic.local/receipt?original=00123',
                    },
                  ],
          }
        : {'subscription': empty ? null : item};
    return ResponseBody.fromString(jsonEncode(data), 200, headers: headers);
  }

  @override
  void close({bool force = false}) {}
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  var current = locales.first;
  final adapter = BillingAdapter();
  final launches = <Map<String, dynamic>>[];
  var receiptResult = true;
  setUpAll(() async {
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(
          const MethodChannel('plugins.it_nomads.com/flutter_secure_storage'),
          (call) async {
            return call.method == 'read' &&
                    call.arguments['key'] == 'access_token'
                ? 'synthetic-token'
                : null;
          },
        );
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(
          const MethodChannel('plugins.flutter.io/url_launcher'),
          (call) async {
            if (call.method != 'launch') {
              throw PlatformException(code: 'unexpected', message: call.method);
            }
            launches.add(Map<String, dynamic>.from(call.arguments as Map));
            return receiptResult;
          },
        );
    await ApiClient.init(
      baseUrl: 'https://synthetic.local',
      localeTag: () => current.toLanguageTag(),
    );
    ApiClient.debugDio.httpClientAdapter = adapter;
  });
  setUp(() {
    adapter.calls.clear();
    launches.clear();
    receiptResult = true;
    adapter.empty = false;
    adapter.denied = false;
    adapter.cancelled = false;
  });
  Future<AppLocalizations> mount(
    WidgetTester tester,
    Locale locale,
    Widget home,
  ) async {
    current = locale;
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

  for (final locale in locales) {
    testWidgets(
      'subscription details and explicit cancellation $locale use only existing authenticated action',
      (tester) async {
        final original = jsonEncode(subscription());
        final l = await mount(tester, locale, const SubscriptionScreen());
        expect(find.text(l.settingsSubscriptionTileTitle), findsOneWidget);
        expect(find.text(l.billingAnnual), findsOneWidget);
        expect(find.text(l.billingRecurringCard), findsOneWidget);
        expect(
          find.text(formatDisplayMoney(1234.56, 'BRL', l.localeName)),
          findsOneWidget,
        );
        expect(find.text('Original tenant'), findsOneWidget);
        expect(find.text('00123'), findsOneWidget);
        final action = find.text(l.billingCancelAction);
        await tester.scrollUntilVisible(
          action,
          200,
          scrollable: find.byType(Scrollable).first,
        );
        await tester.tap(action);
        await tester.pumpAndSettle();
        expect(find.text(l.billingConfirmBody), findsOneWidget);
        expect(
          adapter.calls.where((request) => request.method == 'POST'),
          isEmpty,
        );
        await tester.tap(find.text(l.back));
        await tester.pumpAndSettle();
        expect(
          adapter.calls.where((request) => request.method == 'POST'),
          isEmpty,
        );
        await tester.tap(action);
        await tester.pumpAndSettle();
        await tester.tap(find.text(l.billingConfirmCancel));
        await tester.runAsync(
          () => Future<void>.delayed(const Duration(milliseconds: 30)),
        );
        await tester.pumpAndSettle();
        expect(
          adapter.calls.where((request) => request.method == 'POST').length,
          1,
        );
        expect(find.text(l.billingCancelledNotice), findsOneWidget);
        expect(jsonEncode(subscription()), original);
        expect(tester.takeException(), isNull);
      },
    );
    testWidgets(
      'invoice labels, large BRL values and canonical filter $locale fit mobile',
      (tester) async {
        tester.view.physicalSize = const Size(390, 844);
        tester.view.devicePixelRatio = 1;
        addTearDown(tester.view.resetPhysicalSize);
        addTearDown(tester.view.resetDevicePixelRatio);
        final l = await mount(tester, locale, const InvoicesScreen());
        expect(find.text(l.settingsInvoicesTileTitle), findsOneWidget);
        expect(
          find.text(formatDisplayMoney(12345678.90, 'BRL', l.localeName)),
          findsOneWidget,
        );
        expect(find.byTooltip(l.billingOpenReceipt), findsOneWidget);
        await tester.tap(find.byTooltip(l.billingOpenReceipt));
        await tester.pumpAndSettle();
        expect(
          launches.single['url'],
          'https://synthetic.local/receipt?original=00123',
        );
        expect(launches.single['useWebView'], isFalse);
        expect(launches.single['useSafariVC'], isFalse);
        receiptResult = false;
        await tester.tap(find.byTooltip(l.billingOpenReceipt));
        await tester.pumpAndSettle();
        expect(find.text(l.billingReceiptOpenFailed), findsOneWidget);
        final chip = find.widgetWithText(ChoiceChip, l.billingInvoicePending);
        await tester.ensureVisible(chip);
        await tester.tap(chip);
        await tester.runAsync(
          () => Future<void>.delayed(const Duration(milliseconds: 30)),
        );
        await tester.pumpAndSettle();
        expect(adapter.calls.last.queryParameters, {
          'limit': '50',
          'offset': '0',
          'status': 'pending',
        });
        expect(
          adapter.calls.where((request) => request.method == 'POST'),
          isEmpty,
        );
        expect(tester.takeException(), isNull);
      },
    );
    testWidgets(
      'empty and denied subscription have localized title without actions $locale',
      (tester) async {
        adapter.empty = true;
        var l = await mount(tester, locale, const SubscriptionScreen());
        expect(find.text(l.billingEmptyTitle), findsOneWidget);
        expect(find.text(l.billingEmptyBody), findsOneWidget);
        expect(find.text(l.billingCancelAction), findsNothing);
        await tester.pumpWidget(const SizedBox());
        adapter.denied = true;
        l = await mount(tester, locale, const SubscriptionScreen());
        expect(find.text(l.billingLoadFailed), findsOneWidget);
        expect(find.text(l.billingCancelAction), findsNothing);
        expect(
          adapter.calls.where((request) => request.method == 'POST'),
          isEmpty,
        );
        expect(tester.takeException(), isNull);
      },
    );
  }
  testWidgets(
    'locale change preserves selected filter and open confirmation without fetching or writing',
    (tester) async {
      final locale = ValueNotifier(locales.first);
      addTearDown(locale.dispose);
      current = locale.value;
      Widget app(Widget home) => ValueListenableBuilder<Locale>(
        valueListenable: locale,
        builder: (context, value, child) => MaterialApp(
          theme: EpiTheme.light,
          locale: value,
          localizationsDelegates: AppLocalizations.localizationsDelegates,
          supportedLocales: AppLocalizations.supportedLocales,
          home: home,
        ),
      );
      await tester.pumpWidget(app(const InvoicesScreen()));
      await tester.runAsync(
        () => Future<void>.delayed(const Duration(milliseconds: 30)),
      );
      await tester.pumpAndSettle();
      var l = AppLocalizations.of(tester.element(find.byType(InvoicesScreen)));
      await tester.tap(
        find.widgetWithText(ChoiceChip, l.billingInvoicePending),
      );
      await tester.runAsync(
        () => Future<void>.delayed(const Duration(milliseconds: 30)),
      );
      await tester.pumpAndSettle();
      final before = adapter.calls.length;
      for (final target in locales.skip(1)) {
        locale.value = target;
        current = target;
        await tester.pump();
        await tester.runAsync(
          () => Future<void>.delayed(const Duration(milliseconds: 30)),
        );
        await tester.pumpAndSettle();
        l = AppLocalizations.of(tester.element(find.byType(InvoicesScreen)));
        expect(
          tester
              .widget<ChoiceChip>(
                find.widgetWithText(ChoiceChip, l.billingInvoicePending),
              )
              .selected,
          isTrue,
        );
        expect(adapter.calls.length, before);
      }
      await tester.pumpWidget(const SizedBox());
      await tester.pumpWidget(app(const SubscriptionScreen()));
      await tester.runAsync(
        () => Future<void>.delayed(const Duration(milliseconds: 30)),
      );
      await tester.pumpAndSettle();
      l = AppLocalizations.of(tester.element(find.byType(SubscriptionScreen)));
      final action = find.text(l.billingCancelAction);
      await tester.scrollUntilVisible(
        action,
        200,
        scrollable: find.byType(Scrollable).first,
      );
      await tester.tap(action);
      await tester.pumpAndSettle();
      final beforeDialog = adapter.calls.length;
      locale.value = locales[3];
      current = locale.value;
      await tester.pump();
      await tester.runAsync(
        () => Future<void>.delayed(const Duration(milliseconds: 30)),
      );
      await tester.pumpAndSettle();
      l = AppLocalizations.of(tester.element(find.byType(SubscriptionScreen)));
      expect(find.text(l.billingConfirmBody), findsOneWidget);
      expect(adapter.calls.length, beforeDialog);
      expect(
        adapter.calls.where((request) => request.method == 'POST'),
        isEmpty,
      );
      await tester.tap(find.text(l.back));
      await tester.pumpAndSettle();
      expect(tester.takeException(), isNull);
    },
  );
}
