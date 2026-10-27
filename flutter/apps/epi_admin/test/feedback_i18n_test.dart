import 'dart:async';
import 'dart:convert';
import 'package:dio/dio.dart';
import 'package:epi_admin/core/api/api_client.dart';
import 'package:epi_admin/core/i18n/generated/app_localizations.dart';
import 'package:epi_admin/features/feedback/feedback_screen.dart';
import 'package:epi_admin/features/feedback/feedback_presentation.dart';
import 'package:epi_design/epi_design.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:intl/date_symbol_data_local.dart';

class FeedbackAdapter implements HttpClientAdapter {
  FeedbackAdapter(this.mode);
  final String mode;
  final requests = <RequestOptions>[];
  final responseReady = Completer<void>();
  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? stream,
    Future<void>? cancel,
  ) async {
    requests.add(options);
    expect(options.method, 'GET');
    expect(options.path, '/api/feedbacks');
    await responseReady.future;
    return ResponseBody.fromString(
      jsonEncode(
        mode == 'error'
            ? {'message': 'Opaque <server detail> {keep}'}
            : {
                'items': mode == 'empty'
                    ? []
                    : [
                        {
                          'id': 7,
                          'epi_name': 'Original <EPI> {name}',
                          'status':
                              options.queryParameters['status'] ??
                              (mode == 'rows-manager'
                                  ? 'recebido'
                                  : 'aguardando_aprovacao_admin'),
                          'type': 'sugestao',
                          'created_at': '2026-04-18T23:00:00-03:00',
                          'employee_name': 'Original <employee>',
                          'unit_name': 'Original <unit>',
                          'description':
                              'Original <description> {not a template}',
                        },
                      ],
              },
      ),
      mode == 'error' ? 403 : 200,
      headers: {
        Headers.contentTypeHeader: ['application/json'],
      },
    );
  }

  @override
  void close({bool force = false}) {}
}

Future<void> settle(WidgetTester tester) async {
  await tester.pump();
  await tester.runAsync(
    () => Future<void>.delayed(const Duration(milliseconds: 30)),
  );
  await tester.pumpAndSettle();
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
  var activeLocaleTag = 'pt-BR';
  setUpAll(() async {
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(
          const MethodChannel('plugins.it_nomads.com/flutter_secure_storage'),
          (call) async => null,
        );
    await ApiClient.init(
      baseUrl: 'https://synthetic.local',
      localeTag: () => activeLocaleTag,
    );
  });
  for (var i = 0; i < locales.length; i++) {
    final target = locales[i];
    for (final mode in ['rows', 'rows-manager', 'empty', 'error']) {
      testWidgets(
        'feedback ${target.toLanguageTag()} $mode keeps canonical filters and input',
        (tester) async {
          tester.view.physicalSize = const Size(390, 844);
          tester.view.devicePixelRatio = 1;
          addTearDown(tester.view.resetPhysicalSize);
          addTearDown(tester.view.resetDevicePixelRatio);
          final locale = ValueNotifier(target);
          addTearDown(locale.dispose);
          activeLocaleTag = target.toLanguageTag();
          locale.addListener(
            () => activeLocaleTag = locale.value.toLanguageTag(),
          );
          await tester.runAsync(() => AppLocalizations.delegate.load(target));
          final adapter = FeedbackAdapter(mode);
          ApiClient.debugDio.httpClientAdapter = adapter;
          await tester.pumpWidget(
            ValueListenableBuilder<Locale>(
              valueListenable: locale,
              builder: (context, value, child) => MaterialApp(
                theme: EpiTheme.light,
                locale: value,
                localizationsDelegates: AppLocalizations.localizationsDelegates,
                supportedLocales: AppLocalizations.supportedLocales,
                home: const FeedbackScreen(),
              ),
            ),
          );
          for (
            var attempt = 0;
            attempt < 20 && find.byType(EpiSkeletonCard).evaluate().isEmpty;
            attempt++
          ) {
            await tester.runAsync(
              () => Future<void>.delayed(const Duration(milliseconds: 10)),
            );
            await tester.pump(const Duration(milliseconds: 100));
          }
          expect(
            find.byType(EpiSkeletonCard),
            findsWidgets,
            reason: tester.allWidgets
                .whereType<Text>()
                .map((w) => w.data)
                .join(' | '),
          );
          adapter.responseReady.complete();
          await settle(tester);
          var l = AppLocalizations.of(
            tester.element(find.byType(FeedbackScreen)),
          );
          expect(find.text(l.feedbackTitle), findsOneWidget);
          expect(adapter.requests.single.queryParameters, isEmpty);
          expect(
            adapter.requests.single.headers['Accept-Language'],
            target.toLanguageTag(),
          );
          if (mode.startsWith('rows')) {
            expect(
              find.text(
                mode == 'rows-manager'
                    ? l.feedbackStatusReceived
                    : l.feedbackStatusAwaitingAdmin,
              ),
              findsOneWidget,
            );
            expect(find.text('Original <EPI> {name}'), findsOneWidget);
            expect(
              find.text('Original <description> {not a template}'),
              findsOneWidget,
            );
            expect(find.textContaining('Original <employee>'), findsOneWidget);
            expect(find.textContaining('Original <unit>'), findsOneWidget);
            await tester.tap(find.text(l.feedbackReject));
            await tester.pumpAndSettle();
            final field = find.descendant(
              of: find.byType(AlertDialog),
              matching: find.byType(TextField),
            );
            await tester.enterText(field, 'Original <reason> {literal}');
            locale.value = locales[(i + 1) % locales.length];
            await settle(tester);
            l = AppLocalizations.of(
              tester.element(find.byType(FeedbackScreen)),
            );
            expect(
              find.text(
                mode == 'rows-manager'
                    ? l.feedbackRejectReason
                    : l.feedbackJustification,
              ),
              findsOneWidget,
            );
            expect(
              tester.widget<TextField>(field).controller!.text,
              'Original <reason> {literal}',
            );
            expect(adapter.requests, hasLength(1));
            await tester.tap(find.text(l.cancel));
            await tester.pumpAndSettle();
            await tester.tap(find.text(l.feedbackStatusOpen));
            await settle(tester);
            expect(adapter.requests, hasLength(2));
            expect(adapter.requests.last.queryParameters, {'status': 'open'});
            expect(
              adapter.requests.last.headers['Accept-Language'],
              locale.value.toLanguageTag(),
            );
            locale.value = target;
            await settle(tester);
            expect(adapter.requests, hasLength(2));
            l = AppLocalizations.of(
              tester.element(find.byType(FeedbackScreen)),
            );
            final chip = find.ancestor(
              of: find.text(l.feedbackStatusOpen).first,
              matching: find.byType(EpiChip),
            );
            expect(tester.widget<EpiChip>(chip).selected, isTrue);
          } else if (mode == 'empty') {
            expect(find.text(l.feedbackEmpty), findsOneWidget);
          } else {
            expect(find.text(l.feedbackLoadFailed), findsOneWidget);
            expect(find.text(l.retry), findsOneWidget);
            expect(find.text(l.feedbackApprove), findsNothing);
          }
          expect(adapter.requests.every((r) => r.method == 'GET'), isTrue);
          expect(tester.takeException(), isNull);
          await tester.pumpWidget(const SizedBox());
        },
      );
    }
  }
  test(
    'known current and legacy statuses are labels while unknown values stay opaque',
    () async {
      final l = await AppLocalizations.delegate.load(const Locale('en', 'US'));
      await initializeDateFormatting();
      expect(formatFeedbackDate('2026-04-18T23:00:00-03:00', l.localeName), '4/19/2026');
      expect(formatFeedbackDate('2026-04-18T00:30:00+03:00', l.localeName), '4/17/2026');
      expect(formatFeedbackDate('not a date', l.localeName), 'not a date');
      expect(formatFeedbackDate('', l.localeName), '');
      const expected = {
        'open': 'Open',
        'in_review': 'In review',
        'resolved': 'Resolved',
        'closed': 'Closed',
        'rejected': 'Rejected',
        'recebido': 'Received',
        'em_analise_gestor': 'Under review by the PPE manager',
        'aguardando_hseq': 'Awaiting HSEQ review',
        'analise_hseq_concluida': 'HSEQ review completed',
        'encaminhado_administracao': 'Forwarded to administration',
        'aguardando_aprovacao_admin': 'Awaiting administrative approval',
        'aprovado': 'Approved',
        'reprovado': 'Not approved',
        'acao_corretiva_aberta': 'Corrective action open',
        'encerrado': 'Concluded',
        'solicitada_mais_informacao': 'More information requested',
        'pendente': 'Pending',
        'em análise': 'In review',
        'aprovada': 'Approved',
        'rejeitada': 'Not approved',
        'arquivada': 'Archived',
      };
      for (final e in expected.entries) {
        expect(feedbackStatusLabel(e.key, l), e.value);
      }
      expect(
        feedbackStatusLabel('Original <status> {literal}', l),
        'Original <status> {literal}',
      );
    },
  );
}
